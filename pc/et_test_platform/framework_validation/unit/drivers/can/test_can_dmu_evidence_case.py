# CAN DMU失败路径的软件证据回归。
# 职责：真实Case/Driver运行至解码拒绝，验证原始镜像和通道快照仍可形成报告。
# 边界：固定软件响应不模拟DMU硬件，不形成HIL结论。
# 依赖：公共Driver模型、严格响应队列及已有Canonical报告验证器。

from struct import pack
from types import SimpleNamespace
from unittest.mock import create_autospec

import pytest
from et_test_platform.drivers.dma import DmaDriver
from et_test_platform.drivers.dma.models import (
    DmaBurst,
    DmaChannelSnapshot,
    DmaChannelStatus,
    DmaFifoMode,
    DmaIrqEvent,
)
from et_test_platform.framework_validation.unit.drivers.can.test_can_case_flow import (
    assert_case_report,
    dependencies,
)
from et_test_platform.framework_validation.unit.drivers.can.test_can_watchdog_case import (
    ResourceStub,
)
from et_test_platform.test_cases.can.test_can_p2_dmu import (
    test_can_p2_001_dmu_tx_rx as run_dmu_case,
)
from et_test_platform.test_cases.can.test_can_p2_dmu_tsu import (
    test_can_p2_008_dmu_rx_timestamp as run_tsu_case,
)


# 两个FIFO均保留解码前真实Case取得的嵌套DMA状态；禁止整数键阻断Canonical写入。
@pytest.mark.parametrize("fifo", (0, 1))
def test_dmu_decode_failure_preserves_report(fifo, tmp_path, monkeypatch):
    support, _, target, calls = dependencies()
    support.mapping.CAN_DMU_WORD_BYTES = 4
    support.mapping.CAN_DMU_REQUESTS = {0: {"tx": 3, "rx": 4}}
    target.responses = (
        [b"", pack("<I", 1)]
        + [b""] * 8
        + [
            pack("<I", fifo),
            pack("<I", 0x1000),
            pack("<I", 0x2000),
            b"",
            pack("<I", 0),
            pack("<3I", 0, 1, 0),
            pack("<5I", 0, 0, 0, 0, 256),
            pack("<21I", 72, *([0] * 20)),
            pack("<5I", 0, 0, 0, 0, 0),
            pack("<7I", 0, 0, 0, 4, 0, 0, 0),
            pack("<7I", 0, 1, 0, 4, 0, 0, 0),
            pack("<5I", 0, 1, 1, 0, 0),
            pack("<3I", 0, 1, 0),
        ]
    )
    dma = create_autospec(DmaDriver, instance=True, spec_set=True)
    dma.wait_channels_free.return_value = {
        channel: DmaChannelStatus(True, True, DmaIrqEvent(0)) for channel in (0, 1)
    }
    dma.channel_snapshot_get.side_effect = [
        DmaChannelSnapshot(
            source,
            destination,
            0,
            0,
            18,
            0,
            0,
            0,
            0,
            DmaBurst.ITEMS_32,
            DmaBurst.ITEMS_32,
            18,
            DmaFifoMode.SINGLE,
        )
        for source, destination in ((0x3148, 0x1048), (0x2048, 0x3248))
    ]
    sysctrl = SimpleNamespace(
        configure_dma_request_v2=lambda controller, interface, request: calls.append(
            (controller, interface, request)
        ),
        release_dma_request=lambda controller, interface: calls.append(
            ("release", controller, interface)
        ),
    )
    resource = ResourceStub()

    # 注入点位于真实DMA完成和镜像读取之后，不允许Case提前跳过取证。
    def reject_decode(actual_fifo, raw, *, timeout_s):
        assert actual_fifo == fifo and raw == bytes(72) and timeout_s > 0
        assert not target.responses
        raise ValueError("software malformed DMU header")

    monkeypatch.setattr(support.can, "dmu_rx_image_decode", reject_decode)
    properties = []
    with pytest.raises(ValueError, match="software malformed DMU header"):
        run_dmu_case(
            support,
            SimpleNamespace(
                dma=dma,
                sysctrl=sysctrl,
                controller=0,
                capabilities=SimpleNamespace(max_transfer_count=4095),
            ),
            resource,
            lambda key, value: properties.append((key, value)),
            fifo,
        )
    observations = {v["key"]: v["value"] for k, v in properties if k == "et_observation"}
    assert observations["received_image"] == bytes(72).hex()
    assert observations["dma_free_0"] and observations["dma_free_1"]
    assert observations["tx_after"] == 1 and observations["rx_after"]["fill"] == 0
    assert resource.count == 0
    assert_case_report(properties, "CAN_P2_001", "FAIL", tmp_path)


# TSU五个参数在配置错误时仍明确报告未到达的读取阶段，不制造时间戳Observation。
@pytest.mark.parametrize(
    "fifo,tts,overwrite",
    ((0, False, False), (0, True, False), (1, False, False), (1, True, False), (1, True, True)),
)
def test_dmu_tsu_early_failure_report(fifo, tts, overwrite, tmp_path):
    support, _, target, _ = dependencies()
    support.mapping.CAN_DMU_WORD_BYTES = 4
    target.responses = (
        [b"", pack("<I", 1), pack("<3I", 4, 1, 1)]
        + [b""] * 8
        + [pack("<I", 0), pack("<4I", 1, 0, 0, 1)]
    )
    dma = create_autospec(DmaDriver, instance=True, spec_set=True)
    resource = ResourceStub()
    transport = SimpleNamespace(
        dma=dma,
        controller=0,
        sysctrl=SimpleNamespace(release_dma_request=lambda controller, interface: None),
    )
    properties = []
    with pytest.raises(AssertionError):
        run_tsu_case(
            support,
            transport,
            resource,
            lambda k, v: properties.append((k, v)),
            fifo,
            tts,
            overwrite,
        )
    assert not target.responses and resource.count == 0
    observations = {v["key"] for k, v in properties if k == "et_observation"}
    assert observations == {"filter_sync", "tsu_config"}
    assert dict(properties)["decoded"] == "NOT_OBSERVED"
    assert_case_report(properties, "CAN_P2_008", "FAIL", tmp_path)
