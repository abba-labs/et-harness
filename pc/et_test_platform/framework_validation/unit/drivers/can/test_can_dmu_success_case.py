# CAN DMU成功路径与决定性反例的软件回归。
# 职责：运行真实Case/Driver，校验DMA元素配置、队列推进及Canonical报告。
# 边界：独立Wire向量不模拟总线或硬件IRQ，不形成HIL结论。
# 依赖：严格DMA/Resource替身、公共模型及既有Case报告验证器。

from struct import pack
from types import SimpleNamespace

import pytest
from et_test_platform.drivers.dma import DmaBurst, DmaTransferType
from et_test_platform.drivers.dma.models import (
    DmaChannelSnapshot,
    DmaChannelStatus,
    DmaFifoMode,
    DmaIrqEvent,
)
from et_test_platform.framework_validation.unit.drivers.can.test_can_case_flow import (
    assert_case_report,
    dependencies,
)
from et_test_platform.test_cases.can.test_can_p2_dmu import (
    test_can_p2_002_dmu_tx_event as run_event,
)
from et_test_platform.test_cases.can.test_can_p2_dmu_errors import FAULTS
from et_test_platform.test_cases.can.test_can_p2_dmu_errors import (
    test_can_p2_007_dmu_illegal_irq as run_error,
)


# FREE不隐式解除配置；旧通道未deconfigure时必须拒绝下一次configure。
class ElementDma:
    def __init__(self, words):
        self.words = words
        self.configured = {}
        self.starts = []

    def configure(self, config):
        assert config.channel not in self.configured
        assert config.transfer_count == self.words
        assert config.source_burst == config.destination_burst == DmaBurst.ITEMS_32
        assert config.transfer_type in (
            DmaTransferType.PERIPHERAL_TO_MEMORY,
            DmaTransferType.MEMORY_TO_PERIPHERAL,
        )
        self.configured[config.channel] = config

    def start(self, channel):
        assert channel in self.configured
        self.starts.append(channel)

    def wait_channel_free(self, channel, *, timeout_s):
        assert channel in self.starts and timeout_s > 0
        return DmaChannelStatus(True, True, DmaIrqEvent(0))

    def wait_channels_free(self, channels, *, timeout_s):
        assert channels == (0, 1) and self.starts == [1, 0]
        return {
            channel: self.wait_channel_free(channel, timeout_s=timeout_s) for channel in channels
        }

    def channel_snapshot_get(self, channel):
        config = self.configured[channel]
        return DmaChannelSnapshot(
            config.source_address + self.words * 4,
            config.destination_address + self.words * 4,
            0,
            0,
            self.words,
            0,
            0,
            0,
            0,
            DmaBurst.ITEMS_32,
            DmaBurst.ITEMS_32,
            self.words,
            DmaFifoMode.SINGLE,
        )

    def stop(self, channel):
        assert channel in (0, 1)

    def deconfigure(self, channel):
        self.configured.pop(channel, None)

    def controller_enable(self):
        pass

    def controller_disable(self):
        pass


# 实读固定镜像与TX输入无关；分别保留两项Event，不由write回显构造RX。
class ElementResource:
    def __init__(self):
        self.count = 0

    def reset(self):
        self.count = 0

    def create(self, length):
        assert length == 16
        self.count += 1
        return SimpleNamespace(address=0x3000 + self.count * 0x100)

    def write(self, handle, data):
        assert handle.address in (0x3100, 0x3200) and len(data) == 16

    def read(self, handle, *, size=16, offset=0):
        assert handle.address in (0x3100, 0x3200)
        assert (size, offset) in ((16, 0), (8, 0), (8, 8))
        return (bytes([0x12]) * 8 + bytes([0x34]) * 8)[offset : offset + size]


def transport(dma):
    return SimpleNamespace(
        dma=dma,
        controller=0,
        capabilities=SimpleNamespace(max_transfer_count=4095),
        sysctrl=SimpleNamespace(
            configure_dma_request_v2=lambda controller, interface, request: None,
            release_dma_request=lambda controller, interface: None,
        ),
    )


# 两项Event均真实完成解码；错误类型或第二项Marker都必须失败，保留已读两项证据。
@pytest.mark.parametrize("fault", (None, "event_type", "second_marker"))
def test_event_dma_complete_report(fault, tmp_path):
    support, _, target, _ = dependencies()
    support.mapping.CAN_DMU_WORD_BYTES = 4
    support.mapping.CAN_DMU_REQUESTS = {0: {"tx": 3, "rx": 4}}
    target.responses = (
        [b"", pack("<I", 1)]
        + [b""] * 8
        + [
            pack("<I", 2),
            pack("<I", 0x2000),
            b"",
            pack("<I", 0),
            pack("<3I", 0, 1, 0),
            pack("<5I", 0, 0, 0, 0, 256),
            bytes(20),
        ]
    )
    for index, marker in enumerate((0x12, 0x34)):
        target.responses += [
            pack("<7I", 0, 0, 0, 4, 0, index, 0),
            b"",
            b"",
            pack("<7I", 0, 1 << index, 0, 4, 0, index, 0),
            pack("<5I", 1, index, index + 1, 0, 0),
            pack(
                "<12I",
                0x123,
                12,
                15,
                0,
                1 if fault == "event_type" else 2,
                0 if fault == "second_marker" and index else marker,
                0xFFFFFFFF,
                1,
                0,
                0,
                0,
                0,
            ),
            pack("<5I", 0, index + 1, index + 1, 0, 0),
            pack("<3I", 0, 1, 0),
        ]
    target.responses.append(pack("<5I", 0, 0, 0, 2, 256))
    dma, resource, properties = ElementDma(2), ElementResource(), []
    args = (support, transport(dma), resource, lambda k, v: properties.append((k, v)))
    if fault:
        with pytest.raises(AssertionError):
            run_event(*args)
    else:
        run_event(*args)
        assert not target.responses and dma.starts == [0, 0]
        assert len(dict(properties)["events"]) == len(dict(properties)["status"]) == 2
    assert not dma.configured and resource.count == 0
    assert_case_report(properties, "CAN_P2_002", "FAIL" if fault else "PASS", tmp_path)


# 九种违规均进入同一恢复路径；嵌套DMA状态必须在成功和坏数据失败时完成JSON往返。
@pytest.mark.parametrize("fault,error", FAULTS)
@pytest.mark.parametrize("corrupt", (False, True))
def test_dmu_error_recovery_report(fault, error, corrupt, tmp_path):
    support, _, target, _ = dependencies()
    support.mapping.CAN_DMU_WORD_BYTES = 4
    support.mapping.CAN_DMU_REQUESTS = {0: {"tx": 3, "rx": 4}}
    target.responses = []
    for recovery in (False, True):
        config = fault == "configuration" and not recovery
        target.responses += [b"", b"", pack("<I", 1)] + [b""] * 8
        target.responses += [b""] if config else [b"", pack("<I", 0)]
        target.responses += [
            pack("<3I", 0, 1, 0),
            pack("<5I", 0, 0, 0, 0, 256),
            bytes(20),
            bytes(20),
            pack("<7I", 0, 0, 0, 2, 0, 0, 0),
            pack("<I", config),
            pack("<21I", 16, *([0] * 20)),
        ]
        if recovery:
            continue
        if fault == "tx_dlc":
            target.responses.append(pack("<21I", 72, *([0] * 20)))
        target.responses += [b"", pack("<9I", 0, 0, 0, 0, 0, 0, 1, 0, 0)]
        target.responses += [pack("<I", 0)] * (2 if fault in ("tx_dlc", "tx_sequence") else 1)
        target.responses += [pack("<9I", error, error, error, 1, 0, 0, 1, 0, 0), b""]
    payload = bytes(8) if corrupt else bytes.fromhex("31 42 53 64 75 86 97 A8")
    target.responses += [
        pack("<I", 0x1000),
        pack("<I", 0x2000),
        pack("<7I", 0, 1, 0, 2, 0, 0, 0),
        pack("<8I", 0x123, 0, 8, 0, 0, 0, 8, 0xFFFFFFFF) + payload + bytes(56 + 20),
        pack("<3I", 0, 1, 0),
        pack("<5I", 1, 0, 1, 0, 256),
        pack("<5I", 0, 1, 1, 0, 0),
        b"",
    ]
    dma, resource, properties = ElementDma(4), ElementResource(), []
    args = (support, transport(dma), resource, lambda k, v: properties.append((k, v)), fault, error)
    if corrupt:
        with pytest.raises(AssertionError):
            run_error(*args)
    else:
        run_error(*args)
    assert not target.responses and not dma.configured and resource.count == 0
    assert set(dict(properties)["recovery"]["dma"]) == {"0", "1"}
    assert_case_report(properties, "CAN_P2_007", "FAIL" if corrupt else "PASS", tmp_path)
