# CAN正式Case的软件调用链回归。
# 职责：用独立响应驱动真实CanDriver和Case，核对命令顺序、强断言与异常清理。
# 边界：响应是软件夹具，不执行硬件，也不形成CAN HIL结果。
# 依赖：pytest、真实CAN公共Case/Driver和本模块显式响应队列。

from struct import pack
from types import SimpleNamespace

import pytest
from et_test_platform.core.errors import ConfigurationError
from et_test_platform.drivers.can import (
    CanDriver,
    CanFilterAction,
    CanFilterType,
    CanFrameFlags,
    CanHighPriorityStatus,
    CanHighPriorityStorage,
    CanIrqSource,
    CanPhaseTiming,
    CanRamLimits,
    CanRxBufferStatus,
    CanRxFifoStatus,
    CanRxFrame,
    CanTiming,
)
from et_test_platform.framework_validation.unit.drivers.can.test_can_driver import TargetStub
from et_test_platform.test_cases.can._support import CanSupport, loopback_ram, phase_timing
from et_test_platform.test_cases.can.test_can_p0 import (
    test_can_p0_002_internal_loopback as run_case,
)
from et_test_platform.test_cases.can.test_can_p1 import (
    EXTENDED_FILTER_NODES,
    STANDARD_FILTER_NODES,
)
from et_test_platform.test_cases.can.test_can_p1 import (
    test_can_p1_001_frame_formats as run_format_case,
)
from et_test_platform.test_cases.can.test_can_p1 import (
    test_can_p1_002_standard_id_filter_and_routing as run_standard_filter_case,
)
from et_test_platform.test_cases.can.test_can_p1 import (
    test_can_p1_003_extended_id_filter_and_mask as run_extended_filter_case,
)
from et_test_platform.test_cases.can.test_can_p1 import (
    test_can_p1_004_remote_frame_policy as run_remote_policy_case,
)
from et_test_platform.test_cases.can.test_can_p1 import (
    test_can_p1_005_rx_fifo_watermark_full_and_wrap as run_fifo_boundary_case,
)
from et_test_platform.test_cases.can.test_can_p1 import (
    test_can_p1_006_rx_fifo_blocking_and_overwrite as run_fifo_mode_case,
)
from et_test_platform.test_cases.can.test_can_p1 import (
    test_can_p1_007_dedicated_rx_buffer_boundaries as run_rx_buffer_case,
)


# 明确序列化两帧独立RX Golden；不从Case刚发送的请求取回数据制造一致性。
def responses(*, corrupt_second=False):
    phase = (4, 15, 4, 4, 1, 15, 4, 4)
    result = [
        b"",
        pack("<I", 1),
        b"",
        b"",
        b"",
        b"",
        b"",
        b"",
        b"",
        pack("<I", 0),
        pack("<I", 1),
        pack("<8I", *phase),
    ]
    for index, data in enumerate(
        (
            bytes.fromhex("31 42 53 64 75 86 97 A8"),
            bytes.fromhex("CE BD AC 9B 8A 79 68 57"),
        )
    ):
        if corrupt_second and index == 1:
            data = bytes.fromhex("00 BD AC 9B 8A 79 68 57")
        result.extend(
            [
                pack("<5I", 0, index, index, 0, 0),
                b"",
                b"",
                pack("<7I", 0, 1, 0, 1, 0, 0, 0),
                pack("<5I", 1, index, index + 1, 0, 0),
                pack("<8I", 0x123, 0, 8, 0, 0, 0, 8, index) + data + bytes(56),
                b"",
                pack("<5I", 0, index + 1, index + 1, 0, 0),
            ]
        )
    return result


# 只构造显式依赖；复位替身保存调用次序，实际CAN请求仍经过真实Driver/Codec。
def dependencies(corrupt_second=False):
    target = TargetStub(responses(corrupt_second=corrupt_second))
    calls = []
    crg = SimpleNamespace(
        reset=lambda peripheral, **kwargs: calls.append(("can", kwargs["instance"]))
    )
    resource = SimpleNamespace(reset=lambda: calls.append(("resource",)))
    mapping = SimpleNamespace(CAN_RAM_HEADER_BYTES=8, CAN_STD_FILTER_BYTES=4)
    support = CanSupport(
        "can0",
        CanDriver(target, 0),
        crg,
        None,
        (),
        CanRamLimits(16384, 128, 64, 32, 64, 32, 64),
        CanTiming(CanPhaseTiming(512, 256, 128, 128), CanPhaseTiming(32, 32, 16, 16)),
        mapping,
        40_000_000,
    )
    return support, resource, target, calls


# 正常软件序列必须消费所有响应，两个独立Pattern均比较，Evidence四个端点分别存在。
def test_loopback_case_request_sequence_and_evidence():
    support, resource, target, calls = dependencies()
    properties = []
    run_case(support, resource, lambda key, value: properties.append((key, value)))
    assert target.responses == []
    assert calls == [("can", 0), ("resource",), ("can", 0), ("resource",)]
    assert [row["command"] for row in target.requests] == [
        1,
        2,
        4,
        6,
        10,
        25,
        14,
        12,
        1,
        2,
        15,
        5,
        20,
        17,
        18,
        19,
        20,
        21,
        22,
        20,
        20,
        17,
        18,
        19,
        20,
        21,
        22,
        20,
    ]
    observations = [
        value for _, value in properties if isinstance(value, dict) and "endpoint" in value
    ]
    assert {row["endpoint"] for row in observations} == {
        "RX.FRAME",
        "RX0.FILL",
        "RX0.LOST",
        "TX.COMPLETED",
    }
    assert len(observations) == 8


# 第二帧一个Byte错误必须使真实Case失败，同时两项清理均执行，不能只核对第一帧。
def test_loopback_case_rejects_bad_payload_and_resets():
    support, resource, target, calls = dependencies(corrupt_second=True)
    with pytest.raises(AssertionError):
        run_case(support, resource, lambda key, value: None)
    assert target.responses == []
    assert calls == [("can", 0), ("resource",), ("can", 0), ("resource",)]


# 纯配置不得把不精确时钟取整，也不得把芯片RAM容量不足降级为SKIP。
def test_can_timing_and_ram_configuration_bounds():
    support, _, target, _ = dependencies()
    phase = phase_timing(40_000_000, 500_000, support.timing_limits.nominal)
    assert phase == CanPhaseTiming(4, 15, 4, 4)
    with pytest.raises(ConfigurationError):
        phase_timing(40_000_001, 500_000, support.timing_limits.nominal)
    layout = loopback_ram(support)
    assert (layout.std_offset, layout.tx_offset, layout.rx0_offset, layout.rx_buffer_offset) == (
        0,
        4,
        20,
        84,
    )
    assert layout.rx0_count == 4
    assert target.requests == []


# 构造独立协议Oracle响应：数值flags/DLC表不从Case或Driver编码实现导入。
# 最后64-byte节点可独立损坏最后Byte，验证Case不会只比较首Byte或前8-byte。
def format_responses(flags, identifier, *, corrupt_last=False):
    result = []
    lengths = (0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 20, 24, 32, 48, 64)
    golden = bytes.fromhex(
        "31 42 53 64 75 86 97 A8 B9 CA DB EC FD 0E 1F 30 "
        "41 52 63 74 85 96 A7 B8 C9 DA EB FC 0D 1E 2F 40 "
        "51 62 73 84 95 A6 B7 C8 D9 EA FB 0C 1D 2E 3F 50 "
        "61 72 83 94 A5 B6 C7 D8 E9 FA 0B 1C 2D 3E 4F 60"
    )
    for dlc, fd_length in enumerate(lengths):
        length = fd_length if flags & 4 else min(dlc, 8)
        result.extend(
            [b"", pack("<I", 1), b"", b"", b"", b"", b"", b"", b"", pack("<I", 0), pack("<I", 1)]
        )
        for inverse in (False, True):
            payload = bytes(byte ^ (255 if inverse else 0) for byte in golden[:length])
            if corrupt_last and dlc == 15 and inverse:
                payload = payload[:-1] + bytes([payload[-1] ^ 1])
            index = int(inverse)
            result.extend(
                [
                    b"",
                    b"",
                    pack("<7I", 0, 1, 0, 1, 0, 0, 0),
                    pack("<5I", 1, index, index + 1, 0, 0),
                    pack("<8I", identifier, flags, dlc, 0, 0, 1, length, index)
                    + payload
                    + bytes(64 - length),
                    b"",
                    pack("<5I", 0, index + 1, index + 1, 0, 0),
                ]
            )
    return result


# 六种格式乘两个ID边界，必须遍历每个DLC的两组Expected且执行每节点复位。
@pytest.mark.parametrize("flags", (0, 1, 4, 5, 12, 13))
@pytest.mark.parametrize("upper", (False, True))
def test_format_case_complete_matrix(flags, upper):
    support, resource, target, calls = dependencies()
    identifier = (0x1FFFFFFF if flags & 1 else 0x7FF) if upper else 0
    target.responses = format_responses(flags, identifier)
    properties = []
    run_format_case(
        support,
        resource,
        lambda key, value: properties.append((key, value)),
        "format",
        CanFrameFlags(flags),
        "maximum" if upper else "minimum",
    )
    assert target.responses == []
    assert len(target.requests) == 16 * (11 + 2 * 7)
    assert calls == [("can", 0), ("resource",)] * 17
    assert ("completed_nodes", 32) in properties
    assert sum(key == "format_text" for key, _ in properties) == 32


# FD64的最后Byte损坏必须失败；全部合法软件响应完成不等于数据正确。
def test_format_case_checks_last_payload_byte():
    support, resource, target, calls = dependencies()
    target.responses = format_responses(12, 0x7FF, corrupt_last=True)
    with pytest.raises(AssertionError):
        run_format_case(
            support, resource, lambda key, value: None, "fd_brs_std", CanFrameFlags(12), "maximum"
        )
    assert target.responses == []
    assert calls == [("can", 0), ("resource",)] * 17


# FIFO和Dedicated Buffer软件流程替身只模拟公开CAN语义，不读取Case Expected。
class CanStorageStub:
    def __init__(self):
        self.instance_id = 0
        self.layout = None
        self.filters = {False: {}, True: {}}
        self.extended_mask = 0x1FFFFFFF
        self.bus_config = None
        self.pending_frame = None
        self.fifo_entries = {0: [], 1: []}
        self.fifo_put = {0: 0, 1: 0}
        self.fifo_lost = {0: False, 1: False}
        self.irq_raw = 0
        self.buffers = {}
        self.new_data_low = 0
        self.new_data_high = 0
        self.high_priority = CanHighPriorityStatus(0, CanHighPriorityStorage.NO_FIFO, 0, False)

    # CRG软件替身恢复整个CAN硬件状态，模拟Formal Case要求的Case级隔离。
    def reset(self):
        self.__init__()

    # 配置方法仅保存Case下发的公开参数；不制造额外硬件状态。
    def initializing_set(self, _enabled):
        return None

    def wait_initializing(self, _enabled, *, timeout_s):
        return None

    def timing_set(self, _timing):
        return None

    def options_set(self, _options):
        return None

    def ram_layout_set(self, layout):
        self.layout = layout

    def filter_set(self, index, item, *, extended):
        self.filters[bool(extended)][index] = item

    def extended_mask_set(self, mask):
        self.extended_mask = mask

    def loopback_set(self, _mode):
        return None

    def bus_config_set(self, config):
        self.bus_config = config

    def irq_mask_set(self, _sources, _masked):
        return None

    def irq_clear(self, sources):
        self.irq_raw &= ~int(sources)
        lost_sources = CanIrqSource.RX_FIFO0_LOST | CanIrqSource.RX_FIFO1_LOST
        if sources & lost_sources:
            for fifo in (0, 1):
                self.fifo_lost[fifo] = False

    # 独立执行公开Filter语义；全局XIDAM只作用于普通扩展Range。
    def _match_filter(self, frame):
        extended = bool(frame.flags & CanFrameFlags.EXTENDED)
        received_id = frame.identifier
        for index, item in self.filters[extended].items():
            if item.action is CanFilterAction.DISABLED:
                continue
            if item.action is CanFilterAction.BUFFER:
                matched = received_id == item.id1
            elif item.type is CanFilterType.RANGE:
                compared_id = received_id & self.extended_mask if extended else received_id
                matched = item.id1 <= compared_id <= item.id2
            elif item.type is CanFilterType.RANGE_NO_MASK:
                matched = item.id1 <= received_id <= item.id2
            elif item.type is CanFilterType.DUAL:
                matched = received_id in (item.id1, item.id2)
            elif item.type is CanFilterType.MASK:
                matched = (received_id & item.id2) == (item.id1 & item.id2)
            else:
                matched = False
            if matched:
                return index, item
        return None, None

    # TX请求把预装帧按Remote策略和Filter首匹配结果送入目标存储。
    def tx_write(self, _index, frame):
        self.pending_frame = frame

    def tx_request(self, _mask):
        frame = self.pending_frame
        extended = bool(frame.flags & CanFrameFlags.EXTENDED)
        if frame.flags & CanFrameFlags.REMOTE:
            rejected = (
                self.bus_config.reject_remote_ext if extended else self.bus_config.reject_remote_std
            )
            if rejected:
                return

        filter_index, matched = self._match_filter(frame)
        nonmatching = matched is None
        if matched is None:
            policy = self.bus_config.unmatched_ext if extended else self.bus_config.unmatched_std
            if int(policy) == 2:
                return
            action = CanFilterAction.FIFO0 if int(policy) == 0 else CanFilterAction.FIFO1
        else:
            action = matched.action
        if action in (CanFilterAction.REJECT, CanFilterAction.PRIORITY):
            if action is CanFilterAction.PRIORITY:
                self.high_priority = CanHighPriorityStatus(
                    0,
                    CanHighPriorityStorage.NO_FIFO,
                    filter_index,
                    extended,
                )
                self.irq_raw |= int(CanIrqSource.HIGH_PRIORITY)
            return

        if action in (CanFilterAction.PRIORITY_FIFO0, CanFilterAction.PRIORITY_FIFO1):
            storage = (
                CanHighPriorityStorage.FIFO0
                if action is CanFilterAction.PRIORITY_FIFO0
                else CanHighPriorityStorage.FIFO1
            )
            self.high_priority = CanHighPriorityStatus(0, storage, filter_index, extended)
            self.irq_raw |= int(CanIrqSource.HIGH_PRIORITY)

        if action is CanFilterAction.BUFFER:
            self.buffers[matched.buffer_index] = frame
            if matched.buffer_index < 32:
                self.new_data_low |= 1 << matched.buffer_index
            else:
                self.new_data_high |= 1 << (matched.buffer_index - 32)
            return

        fifo = 0 if action in (CanFilterAction.FIFO0, CanFilterAction.PRIORITY_FIFO0) else 1
        entries = self.fifo_entries[fifo]
        depth = self.layout.rx0_count if fifo == 0 else self.layout.rx1_count
        overwrite = self.layout.rx0_overwrite if fifo == 0 else self.layout.rx1_overwrite
        if len(entries) == depth:
            if overwrite:
                entries.pop(0)
            else:
                self.fifo_lost[fifo] = True
                lost_irq = CanIrqSource.RX_FIFO0_LOST if fifo == 0 else CanIrqSource.RX_FIFO1_LOST
                self.irq_raw |= int(lost_irq)
                return
        index = self.fifo_put[fifo]
        entries.append((index, frame, filter_index or 0, nonmatching))
        self.fifo_put[fifo] = (index + 1) % depth
        new_irq = CanIrqSource.RX_FIFO0_NEW if fifo == 0 else CanIrqSource.RX_FIFO1_NEW
        watermark_irq = (
            CanIrqSource.RX_FIFO0_WATERMARK if fifo == 0 else CanIrqSource.RX_FIFO1_WATERMARK
        )
        full_irq = CanIrqSource.RX_FIFO0_FULL if fifo == 0 else CanIrqSource.RX_FIFO1_FULL
        self.irq_raw |= int(new_irq)
        watermark = self.layout.rx0_watermark if fifo == 0 else self.layout.rx1_watermark
        if watermark and len(entries) >= watermark:
            self.irq_raw |= int(watermark_irq)
        if len(entries) == depth:
            self.irq_raw |= int(full_irq)

    def wait_tx_complete(self, _mask, *, timeout_s):
        return None

    # FIFO状态、读取和Ack保持真实环形索引，不按Case期望序列生成。
    def rx_fifo_status_get(self, fifo):
        entries = self.fifo_entries[fifo]
        depth = self.layout.rx0_count if fifo == 0 else self.layout.rx1_count
        get_index = entries[0][0] if entries else self.fifo_put[fifo]
        return CanRxFifoStatus(
            len(entries),
            get_index,
            self.fifo_put[fifo],
            len(entries) == depth,
            self.fifo_lost[fifo],
        )

    def wait_rx_available(self, fifo, *, minimum=1, timeout_s):
        status = self.rx_fifo_status_get(fifo)
        if status.fill < minimum:
            raise AssertionError("software FIFO did not reach requested fill")
        return status

    def rx_read(self, source, index=0):
        if int(source) == 0:
            frame = self.buffers[index]
            return CanRxFrame(
                frame.identifier, frame.flags, frame.dlc, 0, 0, False, index, frame.data
            )
        fifo = int(source) - 1
        slot, frame, filter_index, nonmatching = self.fifo_entries[fifo][0]
        return CanRxFrame(
            frame.identifier,
            frame.flags,
            frame.dlc,
            0,
            filter_index,
            nonmatching,
            slot,
            frame.data,
        )

    def rx_fifo_ack(self, fifo, index):
        assert self.fifo_entries[fifo][0][0] == index
        self.fifo_entries[fifo].pop(0)

    def irq_snapshot_get(self):
        return SimpleNamespace(raw_status=self.irq_raw)

    def high_priority_status_get(self):
        return self.high_priority

    # Dedicated Buffer状态和Ack分别维护低/高32-bit New Data位图。
    def rx_buffer_status_get(self):
        return CanRxBufferStatus(self.new_data_low, self.new_data_high)

    def rx_buffer_ack(self, low, high):
        self.new_data_low &= ~low
        self.new_data_high &= ~high


# 构造纯软件存储路径依赖；Case仍执行真实配置、证据和断言代码。
def storage_dependencies():
    can = CanStorageStub()
    calls = []

    # 记录复位责任链，同时让后续阶段看见真实复位后的空硬件状态。
    def reset_can(_peripheral, **kwargs):
        calls.append(("can", kwargs["instance"]))
        can.reset()

    crg = SimpleNamespace(reset=reset_can)
    resource = SimpleNamespace(reset=lambda: calls.append(("resource",)))
    mapping = SimpleNamespace(
        CAN_RAM_HEADER_BYTES=8,
        CAN_STD_FILTER_BYTES=4,
        CAN_EXT_FILTER_BYTES=8,
    )
    support = CanSupport(
        "can0",
        can,
        crg,
        None,
        (),
        CanRamLimits(16384, 128, 64, 32, 64, 32, 64),
        CanTiming(CanPhaseTiming(512, 256, 128, 128), CanPhaseTiming(32, 32, 16, 16)),
        mapping,
        40_000_000,
    )
    return support, resource, calls


# FIFO水位、满、索引环回Case必须在两个FIFO上完成并生成原子证据。
@pytest.mark.parametrize("fifo", (0, 1))
def test_fifo_boundary_case_complete_software_flow(fifo):
    support, resource, calls = storage_dependencies()
    properties = []
    run_fifo_boundary_case(
        support,
        resource,
        lambda key, value: properties.append((key, value)),
        fifo,
    )
    assert calls == [("can", 0), ("resource",), ("can", 0), ("resource",)]
    observation_keys = {value["key"] for key, value in properties if key == "et_observation"}
    assert {"first_status", "watermark_status", "full_status", "received_frame"} <= observation_keys


# Blocking和Overwrite必须分别保留不同序列，并在满后恢复接收。
@pytest.mark.parametrize("fifo", (0, 1))
@pytest.mark.parametrize("overwrite", (False, True))
def test_fifo_mode_case_complete_software_flow(fifo, overwrite):
    support, resource, calls = storage_dependencies()
    properties = []
    run_fifo_mode_case(
        support,
        resource,
        lambda key, value: properties.append((key, value)),
        fifo,
        overwrite,
    )
    expected = [1, 2, 3, 4] if overwrite else [0, 1, 2, 3]
    assert ("retained_sequence", expected) in properties
    assert calls == [("can", 0), ("resource",), ("can", 0), ("resource",)]


# Dedicated Buffer边界Case必须跨越两组New Data位图并读回每个真实槽。
def test_rx_buffer_boundary_case_complete_software_flow():
    support, resource, calls = storage_dependencies()
    properties = []
    run_rx_buffer_case(
        support,
        resource,
        lambda key, value: properties.append((key, value)),
    )
    payloads = next(value for key, value in properties if key == "buffer_payloads")
    assert set(payloads) == {"0", "31", "32", "63"}
    assert calls == [("can", 0), ("resource",), ("can", 0), ("resource",)]


# 标准Filter全部参数节点必须执行真实匹配、路由和High Priority软件语义。
@pytest.mark.parametrize(
    "node_name,filters,unmatched_policy,identifier,expected_fifo,expected_filter,high_priority",
    STANDARD_FILTER_NODES,
    ids=[node[0] for node in STANDARD_FILTER_NODES],
)
def test_standard_filter_case_complete_software_flow(
    monkeypatch,
    node_name,
    filters,
    unmatched_policy,
    identifier,
    expected_fifo,
    expected_filter,
    high_priority,
):
    monkeypatch.setattr("et_test_platform.test_cases.can.test_can_p1.sleep", lambda _seconds: None)
    support, resource, calls = storage_dependencies()
    properties = []
    run_standard_filter_case(
        support,
        resource,
        lambda key, value: properties.append((key, value)),
        node_name,
        filters,
        unmatched_policy,
        identifier,
        expected_fifo,
        expected_filter,
        high_priority,
    )
    observation_keys = {value["key"] for key, value in properties if key == "et_observation"}
    assert {"fifo0_status", "fifo1_status"} <= observation_keys
    assert calls == [("can", 0), ("resource",), ("can", 0), ("resource",)]


# 扩展Filter全部参数节点必须执行XIDAM、29-bit比较、路由和High Priority语义。
@pytest.mark.parametrize(
    "node_name,filters,extended_mask,unmatched_policy,identifier,expected_fifo,expected_filter,high_priority",
    EXTENDED_FILTER_NODES,
    ids=[node[0] for node in EXTENDED_FILTER_NODES],
)
def test_extended_filter_case_complete_software_flow(
    monkeypatch,
    node_name,
    filters,
    extended_mask,
    unmatched_policy,
    identifier,
    expected_fifo,
    expected_filter,
    high_priority,
):
    monkeypatch.setattr("et_test_platform.test_cases.can.test_can_p1.sleep", lambda _seconds: None)
    support, resource, calls = storage_dependencies()
    properties = []
    run_extended_filter_case(
        support,
        resource,
        lambda key, value: properties.append((key, value)),
        node_name,
        filters,
        extended_mask,
        unmatched_policy,
        identifier,
        expected_fifo,
        expected_filter,
        high_priority,
    )
    observation_keys = {value["key"] for key, value in properties if key == "et_observation"}
    assert {"fifo0_status", "fifo1_status"} <= observation_keys
    assert calls == [("can", 0), ("resource",), ("can", 0), ("resource",)]


# Remote策略四个参数节点必须先允许接收，再拒绝Remote并通过数据帧证明路径恢复。
@pytest.mark.parametrize("extended", (False, True), ids=("standard", "extended"))
@pytest.mark.parametrize("dlc", (0, 8), ids=("dlc0", "dlc8"))
def test_remote_policy_case_complete_software_flow(monkeypatch, extended, dlc):
    monkeypatch.setattr("et_test_platform.test_cases.can.test_can_p1.sleep", lambda _seconds: None)
    support, resource, calls = storage_dependencies()
    properties = []
    run_remote_policy_case(
        support,
        resource,
        lambda key, value: properties.append((key, value)),
        extended,
        dlc,
    )
    observation_keys = {value["key"] for key, value in properties if key == "et_observation"}
    assert {"remote_frame", "reject_fifo0_status", "recovery_frame"} <= observation_keys
    assert calls == [
        ("can", 0),
        ("resource",),
        ("can", 0),
        ("resource",),
        ("can", 0),
        ("resource",),
    ]
