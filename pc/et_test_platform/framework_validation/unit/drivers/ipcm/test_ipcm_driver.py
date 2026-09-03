# IPCM Driver 与固件 Wire 的软件合同测试。
# 职责：检查全部命令编号、边界、原子请求及统一 Deadline。
# 边界：测试替身只证明软件逻辑，不是双核硬件证据。
# 依赖：本 IP 模块、pytest、公共消息模型。

from collections import deque
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.core.deadline import OperationDeadline
from et_test_platform.core.errors import ProtocolError, RequestTimeout
from et_test_platform.drivers.ipcm import IpcmDriver
from et_test_platform.drivers.ipcm import driver as driver_module
from et_test_platform.drivers.ipcm.codec import (
    decode_capabilities,
    decode_event,
    decode_mailbox,
    encode_config,
)
from et_test_platform.drivers.ipcm.contract import CAPABILITIES, EVENT_HEADER, IpcmCommand
from et_test_platform.drivers.ipcm.driver import IpcmCaptureError
from et_test_platform.drivers.ipcm.models import (
    IpcmAckMode,
    IpcmCaptureState,
    IpcmConfig,
    IpcmEventStage,
    IpcmLinkMode,
)

ROOT = Path(__file__).resolve().parents[6]
CONFIG = IpcmConfig(
    2, 1, 6, frozenset((7,)), frozenset((6, 7)), IpcmAckMode.AUTO, IpcmLinkMode.SINGLE
)


# 严格消费显式请求序列，未知命令或隐式动作立即失败，不提供宽松默认响应。
class ScriptedTarget:
    # 每项固定命令、请求体、响应或异常，以及是否允许重试。
    def __init__(self, steps: list[tuple[IpcmCommand, bytes, bytes | Exception, bool]]) -> None:

        self.steps = deque(steps)
        self.timeouts: list[float | None] = []

    # 与实际 Target 请求参数一致，拒绝任何额外隐式事务。
    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int,
        body: bytes,
        timeout_s: float | None,
        retry_safe: bool,
    ) -> tuple[ServiceMessage, object]:

        assert service_id == 0x0109 and instance_id == 4
        command, expected, response, safe = self.steps.popleft()
        assert (command_id, body, retry_safe) == (command, expected, safe)
        self.timeouts.append(timeout_s)
        if isinstance(response, Exception):
            raise response
        return ServiceMessage(service_id, command_id, instance_id, body=response), object()


# 为软件边界测试构造明确的事件响应，不模拟硬件中断来源。
def event_body(state: IpcmCaptureState, *, fault: int = 0) -> bytes:

    payload = b"abc" if state is IpcmCaptureState.READY else b""
    return (
        EVENT_HEADER.pack(
            2, 4, 4, 4, 1, 0, 0, fault, 7, 2, len(payload), state, IpcmEventStage.MESSAGE
        )
        + payload
    )


# 测试 Feature：IPCM 双端命令编号、结构版本和代表性 Golden Vector。
# 测试方法：逐项读取固件公开枚举，比较真实 Codec 输出。
# 通过条件：全部命令一致，配置字段和长度字节序完全一致。
def test_ipcm_wire_matches_firmware() -> None:

    header = (ROOT / "firmware/services/include/et_ipcm_service.h").read_text(encoding="utf-8")
    for command in IpcmCommand:
        assert f"ET_IPCM_COMMAND_{command.name} = 0x{int(command):04x}u" in header
    assert "#define ET_IPCM_SERVICE_EVENT_HEADER_SIZE 42u" in header
    assert encode_config(CONFIG).hex() == "020001004000000080000000c000000001000000"
    caps = decode_capabilities(bytes.fromhex("01001000080009000500140004008000"))
    assert (
        caps.mailbox_count,
        caps.channel_count,
        caps.data_word_count,
        caps.mailbox_payload_bytes,
    ) == (8, 9, 5, 20)


# 测试 Feature：配置参数边界和公共模式。
# 测试方法：只改变一个非法字段，尝试编码，避免依赖目标固件兜底。
# 通过条件：非法范围、空目标、Source重复及非公开模式都明确拒绝。
@pytest.mark.parametrize(
    "config",
    [
        replace(CONFIG, first_mailbox=-1),
        replace(CONFIG, mailbox_count=0),
        replace(CONFIG, mailbox_count=2),
        replace(CONFIG, first_mailbox=31, mailbox_count=2, link_mode=IpcmLinkMode.LINKED),
        replace(CONFIG, destination_endpoints=frozenset()),
        replace(CONFIG, destination_endpoints=frozenset((6,))),
        replace(CONFIG, irq_enabled_endpoints=frozenset((8,))),
        replace(CONFIG, source_endpoint=32),
        replace(CONFIG, source_endpoint=True),
        replace(CONFIG, ack_mode=True),
        replace(CONFIG, link_mode=99),
    ],
)
def test_ipcm_config_rejects_invalid_fields(config: IpcmConfig) -> None:

    with pytest.raises(ValueError):
        encode_config(config)


# 测试 Feature：响应严格解码，不接受缺数据、未知版本、非零保留位。
# 测试方法：构造三类不兼容响应，调用真实 Codec。
# 通过条件：全部抛出 ProtocolError，不截断或伪造默认值。
def test_ipcm_response_validation() -> None:

    for body in (
        b"",
        CAPABILITIES.pack(2, 16, 8, 9, 5, 20, 4, 128),
        CAPABILITIES.pack(1, 16, 8, 9, 5, 19, 4, 128),
    ):
        with pytest.raises(ProtocolError):
            decode_capabilities(body)
    with pytest.raises(ProtocolError):
        decode_mailbox(bytes(15) + b"\x01")
    for body in (
        event_body(IpcmCaptureState.READY)[:-1],
        event_body(IpcmCaptureState.WAITING) + b"x",
        event_body(IpcmCaptureState.READY, fault=1),
    ):
        with pytest.raises(ProtocolError):
            decode_event(body)


# 测试 Feature：准备 Payload、SEND、ACK、Clear、Release 没有隐式合并。
# 测试方法：脚本替身仅接受所列请求，按公开 API 逐个调用。
# 通过条件：请求次序完全一致，控制命令不重试，读取允许安全重试。
def test_ipcm_actions_are_atomic() -> None:

    target = ScriptedTarget(
        [
            (IpcmCommand.CONFIGURE, encode_config(CONFIG), b"", False),
            (IpcmCommand.PAYLOAD_WRITE, bytes.fromhex("020001000300") + b"abc", b"", False),
            (IpcmCommand.MESSAGE_SEND, b"\x02\x00", b"", False),
            (IpcmCommand.PAYLOAD_READ, b"\x02\x00\x03\x00", b"abc", True),
            (IpcmCommand.ACK_SEND, b"\x02\x00", b"", False),
            (IpcmCommand.INTERRUPT_CLEAR, b"\x02\x00", b"", False),
            (IpcmCommand.DESTINATION_RELEASE, b"\x02\x00\x07\x00", b"", False),
            (IpcmCommand.MAILBOX_RELEASE, b"\x02\x00\x01\x00", b"", False),
            (IpcmCommand.STATE_RESET, b"", b"", False),
        ]
    )
    ipcm = IpcmDriver(target, 4)
    ipcm.configure(CONFIG)
    ipcm.payload_write(2, 1, b"abc")
    ipcm.message_send(2)
    assert ipcm.payload_read(2, 3) == b"abc"
    ipcm.ack_send(2)
    ipcm.interrupt_clear(2)
    ipcm.destination_release(2, 7)
    ipcm.mailbox_release(2, 1)
    ipcm.state_reset()
    assert not target.steps


# 测试 Feature：采样阶段、参数、单次等待以及剩余时间传递。
# 测试方法：ARM后先返回WAITING，再返回READY；最后显式Abort。
# 通过条件：Payload保存，后续请求预算递减，Driver没有自动ACK或Clear。
def test_ipcm_capture_wait_and_abort() -> None:

    target = ScriptedTarget(
        [
            (IpcmCommand.CAPTURE_ARM, bytes.fromhex("00000700020003000100"), b"", False),
            (IpcmCommand.CAPTURE_GET, b"\x00\x00", event_body(IpcmCaptureState.WAITING), True),
            (IpcmCommand.CAPTURE_GET, b"\x00\x00", event_body(IpcmCaptureState.READY), True),
            (IpcmCommand.CAPTURE_ABORT, b"\x00\x00", b"", False),
        ]
    )
    ipcm = IpcmDriver(target, 4)
    ipcm.capture_arm(0, 7, 2, 3, irq=True, stage=IpcmEventStage.MESSAGE)
    event = ipcm.capture_wait(0, timeout_s=1)
    assert event.payload == b"abc" and event.callback_count == 1
    ipcm.capture_abort(0)
    assert 0 < target.timeouts[2] < target.timeouts[1] <= 1
    assert not target.steps


# 测试 Feature：通信超时不能冒充“未产生ACK”，捕获故障必须保留现场。
# 测试方法：分别注入请求超时和FAULT响应，调用负向观察接口。
# 通过条件：超时继续抛出，FAULT异常中仍有原始Pending及fault字段。
def test_ipcm_negative_observation_does_not_hide_errors() -> None:

    target = ScriptedTarget(
        [(IpcmCommand.CAPTURE_GET, b"\x00\x00", RequestTimeout("link timeout"), True)]
    )
    with pytest.raises(RequestTimeout, match="link timeout"):
        IpcmDriver(target, 4).capture_observe(0, window_s=0.1, timeout_s=1)
    target = ScriptedTarget(
        [(IpcmCommand.CAPTURE_GET, b"\x00\x00", event_body(IpcmCaptureState.FAULT, fault=2), True)]
    )
    with pytest.raises(IpcmCaptureError) as caught:
        IpcmDriver(target, 4).capture_observe(0, window_s=0.1, timeout_s=1)
    assert caught.value.event.fault_flags == 2 and caught.value.event.raw_status == 4


# 测试 Feature：完整负向时间窗必须包含窗结束后发起的查询。
# 测试方法：用确定性单调时钟推进等待，记录每次查询时刻和预算。
# 通过条件：最后一次请求在窗口结束后发起，且始终使用同一个总Deadline。
def test_ipcm_negative_window_requires_final_sample(monkeypatch: pytest.MonkeyPatch) -> None:

    now = [0.0]
    query_times: list[float] = []

    # 模拟等待而不执行真实Sleep，测试时间边界而非操作系统调度精度。
    def sleep(seconds: float) -> None:

        now[0] += seconds

    def start(timeout_s: float, *, label: str) -> OperationDeadline:

        return OperationDeadline.start(timeout_s, clock=lambda: now[0], sleep=sleep, label=label)

    # 只允许观测读取；每次响应都是真实契约的WAITING格式。
    class Target(ScriptedTarget):
        def request(
            self,
            service_id: int,
            command_id: int,
            *,
            instance_id: int,
            body: bytes,
            timeout_s: float | None,
            retry_safe: bool,
        ) -> tuple[ServiceMessage, object]:

            query_times.append(now[0])
            self.steps.append(
                (IpcmCommand.CAPTURE_GET, b"\x00\x00", event_body(IpcmCaptureState.WAITING), True)
            )
            return super().request(
                service_id,
                command_id,
                instance_id=instance_id,
                body=body,
                timeout_s=timeout_s,
                retry_safe=retry_safe,
            )

    monkeypatch.setattr(driver_module, "monotonic", lambda: now[0])
    monkeypatch.setattr(driver_module, "OperationDeadline", SimpleNamespace(start=start))
    target = Target([])
    result = IpcmDriver(target, 4).capture_observe(0, window_s=0.01, timeout_s=0.1)
    assert result.state is IpcmCaptureState.WAITING
    assert query_times[-1] >= 0.01
    assert target.timeouts[-1] <= 0.09 < target.timeouts[0]
