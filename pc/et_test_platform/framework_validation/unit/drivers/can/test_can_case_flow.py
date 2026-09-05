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
from et_test_platform.test_cases.can.test_can_p1 import (
    test_can_p1_008_tx_fifo_queue_order as run_tx_order_case,
)
from et_test_platform.test_cases.can.test_can_p1 import (
    test_can_p1_009_tx_event_fifo_watermark_full_and_recovery as run_tx_event_case,
)
from et_test_platform.test_cases.can.test_can_p1 import (
    test_can_p1_015_clock_stop_and_recovery as run_clock_stop_case,
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
    mapping = SimpleNamespace(CAN_RAM_HEADER_BYTES=8, CAN_STD_FILTER_BYTES=4, CAN_EVENT_BYTES=8)
    support = CanSupport(
        "can0",
        CanDriver(target, 0),
        crg,
        CanRamLimits(16384, 128, 64, 32, 64, 32, 64),
        CanTiming(CanPhaseTiming(512, 256, 128, 128), CanPhaseTiming(32, 32, 16, 16)),
        mapping,
        40_000_000,
    )
    return support, resource, target, calls


# 独立构造TX Event Case的硬件响应序列；事件内容与发送Expected不互相读取。


# 测试Feature：停钟应答顺序与恢复数据，禁止以请求回显或旧帧代替实际结果。
# 测试方法：固定Wire响应模拟正常、INIT错误、恢复数据错误三种路径，运行真实Case。
# 通过条件：正常通过、两种错误均失败；每次退出复位，解除ACK后才能清INIT。
@pytest.mark.parametrize("fault", (None, "init", "payload"))
def test_clock_stop_case_preserves_handshake_and_recovery(fault, tmp_path) -> None:

    support, resource, target, calls = dependencies()
    target.responses = responses()[:10]
    for index, data in enumerate(
        (
            bytes.fromhex("31 42 53 64 75 86 97 A8"),
            bytes.fromhex("CE BD AC 9B 8A 79 68 57"),
        )
    ):
        if index == 1 and fault == "payload":
            data = bytes(8)
        target.responses.extend(
            [
                b"",
                b"",
                pack("<7I", 0, 1, 0, 1, 0, 0, 0),
                pack("<5I", 1, index, index + 1, 0, 0),
                pack("<8I", 0x123, 0, 8, 0, 0, 0, 8, index) + data + bytes(56),
                b"",
                pack("<5I", 0, index + 1, index + 1, 0, 0),
            ]
        )
        if index == 0:
            target.responses.extend(
                [
                    b"",
                    pack("<I", 1),
                    pack("<I", 0 if fault == "init" else 1),
                    b"",
                    pack("<I", 0),
                    b"",
                    pack("<I", 0),
                ]
            )
    properties = []

    def record(key, value):
        properties.append((key, value))

    if fault:
        with pytest.raises(AssertionError):
            run_clock_stop_case(support, resource, record)
    else:
        run_clock_stop_case(support, resource, record)
        assert not target.responses

    # 逐条核对实际命令；模式切换前后的写请求不得隐式重试。
    assert calls == [("can", 0), ("resource",), ("can", 0), ("resource",)]
    commands = [item["command"] for item in target.requests]
    request_index = commands.index(33)
    if fault != "init":
        assert commands[request_index : request_index + 7] == [33, 34, 2, 33, 34, 1, 2]
    for item in target.requests:
        if item["command"] == 33:
            assert item["retry_safe"] is False
    values = dict(properties)
    assert len(values["frame_text"]) == (1 if fault == "init" else 2)
    assert len(values["clock_states"]) == (1 if fault == "init" else 2)
    if fault == "payload":
        assert values["frame_text"][-1] == "帧2：00 00 00 00 00 00 00 00"

    # 用实际Case记录验证JSON往返和报告，避免只用理想标量掩盖嵌套Byte数据问题。
    from pathlib import Path

    from et_test_platform.results.case_report import build_case_report_model
    from et_test_platform.results.recorder import write_json_result
    from et_test_platform.scheduling.run_context import _case_observations, _case_recorded_outputs

    item = SimpleNamespace(user_properties=properties)
    measurements, _ = _case_recorded_outputs(item)
    status = "FAIL" if fault else "PASS"
    write_json_result(
        tmp_path / "session.json",
        {
            "schema_version": 1,
            "run_id": "software-clock-stop",
            "chip_id": "et6801",
            "finished_at": "2026-09-05T03:35:00Z",
            "exitstatus": int(bool(fault)),
        },
    )
    write_json_result(
        tmp_path / "cases/node/result.json",
        {
            "schema_version": 1,
            "run_id": "software-clock-stop",
            "case_run_id": "node",
            "case_id": "CAN_P1_015",
            "status": status,
            "duration_s": 0.01,
            "measurements": measurements,
            "observations": _case_observations(item),
            "evidence_complete": True,
            "evidence_sources": ["dut"],
            "missing_evidence_sources": [],
            "error": "software-injected mismatch" if fault else None,
        },
    )
    model = build_case_report_model(
        Path(__file__).resolve().parents[6] / "test_case_doc/can/can.md", tmp_path
    )
    row = next(row for row in model["cases"] if row["case_id"] == "CAN_P1_015")
    assert row["status"] == status


# 独立构造TX Event Case的硬件响应序列；事件内容与发送Expected不互相读取。
def tx_event_responses():
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
        b"",
        b"",
        pack("<I", 0),
    ]
    payloads = (
        bytes.fromhex("01 10 CE BD AC 9B 8A 79"),
        bytes.fromhex("02 11 31 42 53 64 75 86"),
        bytes.fromhex("03 12 CE BD AC 9B 8A 79"),
        bytes.fromhex("04 13 31 42 53 64 75 86"),
        bytes.fromhex("05 14 CE BD AC 9B 8A 79"),
    )
    event_status = (
        (1, 0, 1, 0, 0),
        (2, 0, 2, 0, 0),
        (3, 0, 3, 0, 0),
        (4, 0, 0, 1, 0),
        (4, 0, 0, 1, 1),
    )
    irq_status = {1: 1 << 12, 2: (1 << 12) | (1 << 13), 4: 1 << 14, 5: 1 << 15}
    for sequence, (payload, status) in enumerate(zip(payloads, event_status, strict=True), start=1):
        result.extend(
            [
                b"",
                b"",
                pack("<7I", 0, 1, 0, 0, 0, 0, 0),
                pack("<5I", 1, 0, 1, 0, 0),
                pack("<8I", 0x369, 0, 8, 0, 0, 0, 8, 0) + payload + bytes(56),
                b"",
                pack("<5I", *status),
            ]
        )
        if sequence in irq_status:
            result.extend([pack("<4I", irq_status[sequence], 0, 0, 0), b""])
    for index, marker in enumerate((0x10, 0x11, 0x12, 0x13)):
        result.extend([pack("<7I", 0x369, 0, 8, 0x100 + index, 1, marker, index), b""])
    recovery_payload = bytes.fromhex("A5 20 31 42 53 64 75 86")
    result.extend(
        [
            pack("<5I", 0, 0, 0, 0, 1),
            b"",
            b"",
            pack("<7I", 0, 1, 0, 0, 0, 0, 0),
            pack("<5I", 1, 0, 1, 0, 0),
            pack("<8I", 0x369, 0, 8, 0, 0, 0, 8, 0) + recovery_payload + bytes(56),
            b"",
            pack("<5I", 1, 0, 1, 0, 1),
            pack("<7I", 0x369, 0, 8, 0x200, 1, 0x20, 0),
            b"",
            pack("<5I", 0, 1, 1, 0, 1),
        ]
    )
    return result


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


# TX Event Case必须执行真实Driver命令链，验证水位/满/丢失并在排空后恢复。
def test_tx_event_case_request_sequence_and_evidence():
    support, resource, target, calls = dependencies()
    target.responses = tx_event_responses()
    properties = []

    run_tx_event_case(support, resource, lambda key, value: properties.append((key, value)))

    assert target.responses == []
    assert calls == [("can", 0), ("resource",), ("can", 0), ("resource",)]
    commands = [row["command"] for row in target.requests]
    assert commands.count(44) == 8
    assert commands.count(45) == 5
    assert commands.count(46) == 5
    assert commands.count(21) == 6 and commands.count(22) == 6
    observations = [
        value for _, value in properties if isinstance(value, dict) and "endpoint" in value
    ]
    assert {row["endpoint"] for row in observations} >= {
        "TX_EVENT.STATUS",
        "IRQ.RAW.TX_EVENT",
        "TX_EVENT.STATUS_AFTER_DRAIN",
        "TX_EVENT.DATA",
        "TX_EVENT.STATUS_AFTER_FINAL_ACK",
        "RX_FIFO[0].FRAME",
        "TX_EVENT[0]",
        "TX_EVENT[3]",
    }


# 测试Feature：TX Event失败现场在断言前保留，未执行恢复不能伪造为成功。
# 测试方法：分别损坏首项Marker和最后FILL，驱动真实Case后检查对应Observation。
# 通过条件：两种错误均FAIL，错误值仍在证据中，硬件与资源退出复位均执行。
@pytest.mark.parametrize("fault", ("marker", "final_fill"))
def test_tx_event_failure_keeps_actual_observation(fault: str, tmp_path) -> None:

    support, resource, target, calls = dependencies()
    target.responses = tx_event_responses()
    if fault == "marker":
        index = target.responses.index(pack("<7I", 0x369, 0, 8, 0x100, 1, 0x10, 0))
        target.responses[index] = pack("<7I", 0x369, 0, 8, 0x100, 1, 0xFF, 0)
    else:
        target.responses[-1] = pack("<5I", 1, 1, 1, 0, 1)
    properties = []

    with pytest.raises(AssertionError):
        run_tx_event_case(support, resource, lambda key, value: properties.append((key, value)))

    observations = {
        value["key"]: value
        for _, value in properties
        if isinstance(value, dict) and "endpoint" in value
    }
    assert calls == [("can", 0), ("resource",), ("can", 0), ("resource",)]
    assert "tx_event_status" in observations and "tx_event_irq" in observations
    if fault == "marker":
        assert observations["tx_event"]["value"]["marker"] == 0xFF
        assert observations["tx_event"]["endpoint"] == "TX_EVENT[0]"
    else:
        assert observations["tx_event_status"]["value"]["fill"] == 1
        assert observations["tx_event_status"]["endpoint"] == "TX_EVENT.STATUS_AFTER_FINAL_ACK"
        assert "rx_data" not in observations["tx_event"]["value"]

    # 真实Case观测经过Canonical写入/重读和正式报告模型，错误现场必须仍显示为FAIL。
    from pathlib import Path

    from et_test_platform.results.case_report import build_case_report_model
    from et_test_platform.results.recorder import write_json_result
    from et_test_platform.scheduling.run_context import _case_observations, _case_recorded_outputs

    item = SimpleNamespace(user_properties=properties)
    measurements, _ = _case_recorded_outputs(item)
    # 摘要按采样追加，每个值只出现一次；不允许累计快照再次嵌套造成报告膨胀。
    assert len(measurements["event_trace"]) == (1 if fault == "marker" else 5)
    assert len(measurements["status_trace"]) == (5 if fault == "marker" else 8)
    assert len(measurements["irq_trace"]) == 4
    assert len(measurements["rx_trace"]) == (5 if fault == "marker" else 6)
    write_json_result(
        tmp_path / "session.json",
        {
            "schema_version": 1,
            "run_id": "software-can-fault",
            "chip_id": "et6801",
            "finished_at": "2026-09-05T03:00:00Z",
            "exitstatus": 1,
        },
    )
    write_json_result(
        tmp_path / "cases" / "fault" / "result.json",
        {
            "schema_version": 1,
            "run_id": "software-can-fault",
            "case_run_id": "fault",
            "case_id": "CAN_P1_009",
            "status": "FAIL",
            "duration_s": 0.01,
            "measurements": measurements,
            "observations": _case_observations(item),
            "evidence_complete": True,
            "evidence_sources": ["dut"],
            "missing_evidence_sources": [],
            "error": "injected software response fault",
        },
    )
    document = Path(__file__).resolve().parents[6] / "test_case_doc/can/can.md"
    model = build_case_report_model(document, tmp_path)
    row = next(row for row in model["cases"] if row["case_id"] == "CAN_P1_009")
    assert row["status"] == "FAIL"


# 测试Feature：内部回环不依赖GPIO服务、引脚复用或外部接线冲突校验。
# 测试方法：只注册CAN/CRG，提供重复的未使用引脚，执行真实Fixture并记录Wire。
# 通过条件：仅发CAN容量/时序查询，不发GPIO命令；选定实例与芯片时钟保持不变。
def test_internal_support_does_not_query_gpio(monkeypatch) -> None:

    from et_test_platform.profiles.hardware_connections import (
        ConnectionEndpoint,
        HardwareConnections,
    )
    from et_test_platform.test_cases.can import conftest

    target = TargetStub(
        [
            pack("<7I", 16384, 128, 64, 32, 64, 32, 64),
            pack("<8I", 512, 256, 128, 128, 32, 32, 16, 16),
        ]
    )
    connection = HardwareConnections(
        "fpga", {"can": {"dut": ConnectionEndpoint("can0", {"rx": 58, "tx": 58})}}
    )
    monkeypatch.setattr(conftest, "load_hardware_connections", lambda **kwargs: connection)
    monkeypatch.setattr(
        conftest, "chip_mapping", lambda chip: SimpleNamespace(CAN_CLOCK_HZ={"fpga": 40_000_000})
    )
    framework = SimpleNamespace(
        target_client=target,
        runtime_services=[
            SimpleNamespace(service_id=conftest.CAN_SERVICE_ID, instance_id=0),
            SimpleNamespace(service_id=conftest.CRG_SERVICE_ID, instance_id=0),
        ],
    )
    capabilities = SimpleNamespace(chip_id="et6801", interrupt=lambda *args, **kwargs: None)

    support = conftest.can_support.__wrapped__(framework, capabilities)

    assert support.can.instance_id == 0 and support.clock_hz == 40_000_000
    assert [row["command"] for row in target.requests] == [9, 3]
    assert all(row["service"] == conftest.CAN_SERVICE_ID for row in target.requests)


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
def test_rx_buffer_boundary_case_complete_software_flow(tmp_path):
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

    # 一次执行具有多个同名物理观测；报告应绑定人工摘要，不要求同名观测唯一。
    from pathlib import Path

    from et_test_platform.results.case_report import build_case_report_model
    from et_test_platform.results.recorder import write_json_result
    from et_test_platform.scheduling.run_context import _case_observations, _case_recorded_outputs

    item = SimpleNamespace(user_properties=properties)
    measurements, _ = _case_recorded_outputs(item)
    assert len(measurements["buffer_frame_text"]) == 5
    write_json_result(
        tmp_path / "session.json",
        {
            "schema_version": 1,
            "run_id": "software-can-buffer",
            "chip_id": "et6801",
            "finished_at": "2026-09-05T05:08:00Z",
            "exitstatus": 0,
        },
    )
    write_json_result(
        tmp_path / "cases/buffer/result.json",
        {
            "schema_version": 1,
            "run_id": "software-can-buffer",
            "case_run_id": "buffer",
            "case_id": "CAN_P1_007",
            "status": "PASS",
            "duration_s": 0.01,
            "measurements": measurements,
            "observations": _case_observations(item),
            "evidence_complete": True,
            "evidence_sources": ["dut"],
            "missing_evidence_sources": [],
        },
    )
    model = build_case_report_model(
        Path(__file__).resolve().parents[6] / "test_case_doc/can/can.md", tmp_path
    )
    row = next(row for row in model["cases"] if row["case_id"] == "CAN_P1_007")
    assert row["status"] == "PASS"
    assert "RX Buffer 63" in row["remark"] and "再次接收" in row["remark"]


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


# 三种TX组织的原子请求回归和故障证据。


# 三种组织使用独立Golden接收次序；倒序或残留帧必须被真实Case判为失败。
@pytest.mark.parametrize("mode", ("buffer", "fifo", "queue"))
@pytest.mark.parametrize("fault", (None, "order", "residual"))
def test_tx_order_case_atomic_request_and_evidence(mode, fault, tmp_path) -> None:
    support, resource, target, calls = dependencies()
    target.responses = responses()[:10]
    ids = (0x300, 0x100, 0x200)
    payloads = tuple(bytes([i, 0, 0, 0]) + bytes.fromhex("75 86 97 A8") for i in range(3))
    for i, identifier in enumerate(ids):
        target.responses.extend(
            [b"", pack("<5I", i, identifier, 0, 8, i) + payloads[i] + bytes(56)]
        )
    # 独立Golden：TFFL只用于FIFO；Queue组织按硬件定义读0。
    free = 3 if mode == "fifo" else 0
    target.responses.extend(
        [
            pack("<7I", 0, 0, 0, free, 0, 0, 0),
            b"",
            pack("<7I", 0, 7, 0, free, 0, 0, 0),
        ]
    )
    indices = (0, 1, 2) if mode == "fifo" else (1, 2, 0)
    if fault == "order":
        indices = tuple(reversed(indices))
    for received, source in enumerate(indices):
        target.responses.extend(
            [
                pack("<5I", 3 - received, received, 3, 0, 0),
                pack("<8I", ids[source], 0, 8, 0, 0, 0, 8, received) + payloads[source] + bytes(56),
                b"",
            ]
        )
    target.responses.extend(
        [
            pack("<7I", 0, 7, 0, free, 0, 0, 0),
            pack("<5I", int(fault == "residual"), 3, 3, 0, 0),
        ]
    )
    properties = []

    # 保留Case真实记录，不根据Golden补写硬件Evidence。
    def record(name, value):
        properties.append((name, value))

    if fault:
        with pytest.raises(AssertionError):
            run_tx_order_case(support, resource, record, mode)
    else:
        run_tx_order_case(support, resource, record, mode)
        assert not target.responses
    assert calls == [("can", 0), ("resource",), ("can", 0), ("resource",)]
    tx_requests = [request for request in target.requests if request["command"] == 18]
    assert len(tx_requests) == 1 and tx_requests[0]["retry_safe"] is False
    assert dict(properties)["preload_text"] and dict(properties)["order_text"]

    # 用实际Case记录验证JSON往返和报告，避免只用理想标量掩盖嵌套Byte数据问题。
    from pathlib import Path

    from et_test_platform.results.case_report import build_case_report_model
    from et_test_platform.results.recorder import write_json_result
    from et_test_platform.scheduling.run_context import _case_observations, _case_recorded_outputs

    item = SimpleNamespace(user_properties=properties)
    measurements, _ = _case_recorded_outputs(item)
    status = "FAIL" if fault else "PASS"
    write_json_result(
        tmp_path / "session.json",
        {
            "schema_version": 1,
            "run_id": "software-tx-order",
            "chip_id": "et6801",
            "finished_at": "2026-09-05T03:35:00Z",
            "exitstatus": int(bool(fault)),
        },
    )
    write_json_result(
        tmp_path / "cases/node/result.json",
        {
            "schema_version": 1,
            "run_id": "software-tx-order",
            "case_run_id": "node",
            "case_id": "CAN_P1_008",
            "status": status,
            "duration_s": 0.01,
            "measurements": measurements,
            "observations": _case_observations(item),
            "evidence_complete": True,
            "evidence_sources": ["dut"],
            "missing_evidence_sources": [],
            "error": "software-injected mismatch" if fault else None,
        },
    )
    model = build_case_report_model(
        Path(__file__).resolve().parents[6] / "test_case_doc/can/can.md", tmp_path
    )
    row = next(row for row in model["cases"] if row["case_id"] == "CAN_P1_008")
    assert row["status"] == status
