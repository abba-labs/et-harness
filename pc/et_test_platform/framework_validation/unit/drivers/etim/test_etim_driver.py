# ETIM共享Golden、Driver和失败路径的软件回归。
# 职责：验证PC请求/响应、禁止重试和总Deadline。
# 边界：不证明芯片时序或真实IRQ投递。
# 依赖：pytest、本IP公共API和严格TargetClient Fake。

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from et_test_platform.clients.target import TargetClient
from et_test_platform.communication.protocols.et_frame import Frame, MessageType
from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.core.deadline import OperationDeadline
from et_test_platform.core.errors import ProtocolError, RequestTimeout, TargetRejected
from et_test_platform.drivers.etim import (
    EtimCapabilities,
    EtimCount,
    EtimCountObservation,
    EtimDriver,
    EtimEnable,
    EtimIrq,
    EtimIrqSnapshot,
    EtimOperationError,
    EtimTimebase,
    codec,
)
from et_test_platform.drivers.etim.contract import ETIM_SERVICE_ID, EtimCommand

VECTORS = json.loads(Path(__file__).with_name("etim_wire_golden.json").read_text(encoding="utf-8"))
CAPS = bytes.fromhex(VECTORS[0]["response"])


# Fake严格匹配动作、通道、Body及retry属性，拒绝未计划请求。
class StrictTarget(TargetClient):
    def __init__(self, expected: list[tuple[int, bytes, int, bytes]], instance: int = 7) -> None:
        self.expected = list(expected)
        self.instance = instance
        self.timeouts: list[float] = []
        self.on_request: Callable[[], None] = lambda: None

    # 签名保持真实TargetClient边界，失败使用真实TargetRejected类型。
    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
        timeout_s: float | None = None,
        session_id: int | None = None,
        retry_safe: bool = False,
    ) -> tuple[ServiceMessage, Frame]:
        assert service_id == ETIM_SERVICE_ID and instance_id == self.instance
        assert timeout_s is not None and timeout_s > 0 and session_id is None
        assert self.expected, "unexpected extra request or retry"
        command, request, status, response = self.expected.pop(0)
        assert command_id == command and body == request
        assert retry_safe == (command in (1, 3, 5, 6, 10))
        self.timeouts.append(timeout_s)
        self.on_request()
        if status:
            raise TargetRejected(
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
                status=status,
                body=response,
            )
        message = ServiceMessage(service_id, command_id, instance_id, body=response)
        return message, Frame(MessageType.RESPONSE, 0, 1, 1, message.encode())


def invoke(driver: EtimDriver, command: int) -> object:
    actions: dict[int, Callable[[], object]] = {
        1: driver.capabilities_get,
        2: lambda: driver.timebase_configure(EtimTimebase(64, 1 << 32)),
        3: driver.timebase_get,
        4: lambda: driver.enable_set(EtimEnable.PWM, True),
        5: lambda: driver.enable_get(EtimEnable.MODULE),
        6: driver.count_get,
        7: lambda: driver.count_latch(4),
        8: lambda: driver.count_clear(4),
        9: lambda: driver.irq_configure(EtimIrq.CAPTURE_4, EtimIrq.COMPARE_ERROR),
        10: driver.irq_snapshot_get,
        11: lambda: driver.irq_force(EtimIrq.PERIOD),
        12: lambda: driver.irq_clear(EtimIrq.COMPARE_ERROR),
    }
    return actions[command]()


# 与C Native使用同一组独立固定字节，测试完整Driver请求及类型结果。
@pytest.mark.parametrize("index", range(len(VECTORS)), ids=[v["name"] for v in VECTORS])
def test_shared_golden_driver(index: int) -> None:
    vector = VECTORS[index]
    command = vector["command"]
    expected = []
    if command in (2, 7, 8, 9, 11, 12):
        expected.append((1, b"", 0, CAPS))
    expected.append(
        (
            command,
            bytes.fromhex(vector["request"]),
            vector["status"],
            bytes.fromhex(vector["response"]),
        )
    )
    target = StrictTarget(expected)
    driver = EtimDriver(target, 7)
    results = {
        1: EtimCapabilities(64, 1 << 32, 1024, EtimIrq.ALL),
        2: None,
        3: EtimTimebase(8, 1),
        4: None,
        5: True,
        6: EtimCount(40, 7),
        7: EtimCountObservation(45, 7, 45, 45, 3),
        8: EtimCountObservation(40, 7, 7, 0, 3),
        9: None,
        10: EtimIrqSnapshot(
            EtimIrq.CAPTURE_4, EtimIrq.COMPARE_ERROR, EtimIrq.CAPTURE_1, EtimIrq.COUNTER_OVERFLOW
        ),
        11: None,
        12: None,
    }
    if vector["status"]:
        with pytest.raises(EtimOperationError) as caught:
            invoke(driver, command)
        assert caught.value.protocol_status == vector["status"]
        if vector["status"] == 5:
            assert caught.value.detail == -3
            assert caught.value.observation == EtimCountObservation(40, 7, 7, 1, 3)
        else:
            assert caught.value.detail == -6
            assert caught.value.observation == EtimCountObservation(40, 7, 7, 40, 4)
        assert isinstance(caught.value.__cause__, TargetRejected)
    else:
        assert invoke(driver, command) == results[command]
    assert not target.expected


DECODERS: dict[int, Callable[[bytes], object]] = {
    1: codec.decode_capabilities,
    2: codec.decode_ack,
    3: codec.decode_timebase,
    4: codec.decode_ack,
    5: codec.decode_enable,
    6: codec.decode_count,
    7: codec.decode_observation,
    8: codec.decode_observation,
    9: codec.decode_ack,
    10: codec.decode_irq_snapshot,
    11: codec.decode_ack,
    12: codec.decode_ack,
}


# 所有成功Body拒绝截断、尾随字节及非零详细状态。
@pytest.mark.parametrize("index", [i for i, v in enumerate(VECTORS) if v["status"] == 0])
def test_success_body_strict(index: int) -> None:
    vector = VECTORS[index]
    body = bytes.fromhex(vector["response"])
    decode = DECODERS[vector["command"]]
    for malformed in (body[:-1], body + b"\0", b"\xff" + body[1:]):
        with pytest.raises(ProtocolError):
            decode(malformed)


# 参数错误在任何设备调用前拒绝。
@pytest.mark.parametrize(
    "action",
    [
        lambda d: d.timebase_configure(EtimTimebase(True, 1)),
        lambda d: d.timebase_configure(EtimTimebase(1, 0)),
        lambda d: d.timebase_configure(EtimTimebase(1, 1 << 64)),
        lambda d: d.enable_set(EtimEnable.PWM, 1),
        lambda d: d.enable_get(0),
        lambda d: d.count_latch(True),
        lambda d: d.count_clear(0),
        lambda d: d.irq_force(EtimIrq.NONE),
        lambda d: d.irq_clear(EtimIrq(1 << 12)),
    ],
)
def test_invalid_parameters_no_io(action: Callable[[EtimDriver], object]) -> None:
    target = StrictTarget([])
    with pytest.raises(ValueError):
        action(EtimDriver(target, 7))
    assert not target.timeouts


# Runtime上限不回退到隐式芯片默认值，也不发送不合法动作。
@pytest.mark.parametrize(
    "action",
    [
        lambda d: d.timebase_configure(EtimTimebase(65, 1)),
        lambda d: d.timebase_configure(EtimTimebase(1, (1 << 32) + 1)),
        lambda d: d.count_latch(1025),
    ],
)
def test_runtime_limits(action: Callable[[EtimDriver], object]) -> None:
    target = StrictTarget([(1, b"", 0, CAPS)])
    with pytest.raises(ValueError, match="runtime capability"):
        action(EtimDriver(target, 7))
    assert not target.expected


# 嵌套能力请求与动作共享总Deadline，耗尽后不发动作。
@pytest.mark.parametrize("elapsed", [0.75, 2.0])
def test_one_deadline(monkeypatch: pytest.MonkeyPatch, elapsed: float) -> None:
    now = [0.0]
    start = OperationDeadline.start
    monkeypatch.setattr(
        OperationDeadline,
        "start",
        lambda timeout_s, *, label: start(timeout_s, clock=lambda: now[0], label=label),
    )
    expected = [(1, b"", 0, CAPS)]
    if elapsed < 2.0:
        expected.append((11, b"\x40\0\0\0", 0, b"\0" * 4))
    target = StrictTarget(expected)
    target.on_request = lambda: now.__setitem__(0, elapsed)
    driver = EtimDriver(target, 7)
    if elapsed == 2.0:
        with pytest.raises(RequestTimeout):
            driver.irq_force(EtimIrq.PERIOD)
    else:
        driver.irq_force(EtimIrq.PERIOD)
        assert target.timeouts == [2.0, 1.25]
    assert not target.expected


# 目标错误必须保持详细状态、协议映射和观测长度一致。
@pytest.mark.parametrize(
    "body,status",
    [
        (b"\xff", 3),
        (b"\0" * 4, 6),
        (b"\xfa\xff\xff\xff", 6),
        (b"\xfd\xff\xff\xff" + b"\0" * 20, 6),
        (b"\xfe\xff\xff\xff" + b"\0" * 20, 4),
    ],
)
def test_error_body_strict(body: bytes, status: int) -> None:
    with pytest.raises(ProtocolError):
        codec.decode_error(EtimCommand.COUNT_LATCH, status, body)


# 框架无Body拒绝和本IP不支持错误同样提供稳定异常而不重试。
@pytest.mark.parametrize("status,body,detail", [(1, b"", None), (4, b"\xfe\xff\xff\xff", -2)])
def test_target_error(status: int, body: bytes, detail: int | None) -> None:
    target = StrictTarget([(6, b"", status, body)])
    with pytest.raises(EtimOperationError) as caught:
        EtimDriver(target, 7).count_get()
    assert caught.value.detail == detail and caught.value.observation is None
    assert not target.expected


# 固定布局正确也不能掩盖错误版本、零能力或未知IRQ位。
@pytest.mark.parametrize(
    "offset,replacement",
    [
        (4, b"\x02\0"),
        (6, b"\x1b\0"),
        (8, b"\0" * 4),
        (12, b"\0" * 8),
        (20, b"\0" * 4),
        (24, b"\0\x10\0\0"),
    ],
)
def test_capabilities_semantic_validation(offset: int, replacement: bytes) -> None:
    invalid = CAPS[:offset] + replacement + CAPS[offset + len(replacement) :]
    with pytest.raises(ProtocolError):
        codec.decode_capabilities(invalid)


# Boolean及每个IRQ字段各自校验，不依赖相互一致来接受非法位。
@pytest.mark.parametrize("offset", [4, 8, 12, 16])
def test_snapshot_rejects_unknown_bits(offset: int) -> None:
    invalid = b"\0" * offset + b"\0\x10\0\0" + b"\0" * (16 - offset)
    with pytest.raises(ProtocolError):
        codec.decode_irq_snapshot(invalid)


# 构造阶段拒绝不合法目标及时间预算，不消耗设备请求。
@pytest.mark.parametrize(
    "instance,timeout",
    [
        (True, 2.0),
        (-1, 2.0),
        (65536, 2.0),
        (7, 0.0),
        (7, float("inf")),
        (7, True),
    ],
)
def test_constructor_validation(instance: int, timeout: float) -> None:
    with pytest.raises(ValueError):
        EtimDriver(StrictTarget([]), instance, timeout_s=timeout)


# 使能值必须是0或1；失败不丢失异常并转换为True。
def test_enable_response_boolean_only() -> None:
    with pytest.raises(ProtocolError):
        codec.decode_enable(b"\0" * 4 + b"\x02\0\0\0")
