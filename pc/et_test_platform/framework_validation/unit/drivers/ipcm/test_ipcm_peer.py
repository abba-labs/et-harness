# IPCM Peer原子转发合同测试。
# 职责：固定Wire向量、票据/身份拒绝与取消确认。
# 边界：只使用严格Target替身，不是双核硬件证据。
# 依赖：本IP Driver/Codec与公共异常。

import pytest

from et_test_platform.core.errors import ProtocolError, RequestTimeout, TargetRejected
from et_test_platform.drivers.ipcm import IpcmDriver
from et_test_platform.drivers.ipcm.codec import decode_peer_result
from et_test_platform.drivers.ipcm.contract import PEER_RESULT, PEER_TICKET, IpcmCommand

from .test_ipcm_driver import ScriptedTarget


# 固定不同于芯片的执行身份，证明Driver不依赖Core编号常量。
def result_body(*, ticket=7, state=2, status=0, identity=19, payload=b"", reserved=0):

    return PEER_RESULT.pack(ticket, state, status, len(payload), reserved, identity, 31) + payload


# 提交一次非幂等SEND，只轮询结果，绝不重复提交；整个操作预算递减。
def test_peer_atomic_submit_and_deadline():

    target = ScriptedTarget(
        [
            (IpcmCommand.PEER_SUBMIT, bytes.fromhex("08000200"), PEER_TICKET.pack(7), False),
            (IpcmCommand.PEER_RESULT, b"", result_body(state=1), True),
            (IpcmCommand.PEER_RESULT, b"", result_body(), True),
        ]
    )
    IpcmDriver(target, 4, peer_identity=19).message_send(2, timeout_s=0.5)
    assert not target.steps
    assert 0 < target.timeouts[2] < target.timeouts[1] < target.timeouts[0] <= 0.5


# 错票据/错执行核/取消或远端拒绝均不可被解释成动作成功。
@pytest.mark.parametrize(
    "response,exception",
    [
        (result_body(ticket=8), ProtocolError),
        (result_body(identity=20), ProtocolError),
        (result_body(state=3), ProtocolError),
        (result_body(status=3), TargetRejected),
        (RequestTimeout("peer link timeout"), RequestTimeout),
    ],
)
def test_peer_mismatched_or_failed_result_is_rejected(response, exception):

    target = ScriptedTarget(
        [
            (IpcmCommand.PEER_SUBMIT, bytes.fromhex("08000200"), PEER_TICKET.pack(7), False),
            (IpcmCommand.PEER_RESULT, b"", response, True),
        ]
    )
    with pytest.raises(exception):
        IpcmDriver(target, 4, peer_identity=19).message_send(2, timeout_s=0.5)
    assert not target.steps


# 取消必须等Peer同票据确认，不能仅收到Core0返回就提前复位共享硬件。
def test_peer_cancel_waits_for_acknowledged_cleanup():

    target = ScriptedTarget(
        [
            (IpcmCommand.PEER_CANCEL, b"", PEER_TICKET.pack(7), False),
            (IpcmCommand.PEER_RESULT, b"", result_body(state=1), True),
            (IpcmCommand.PEER_RESULT, b"", result_body(state=3), True),
        ]
    )
    IpcmDriver(target, 4).peer_cancel(expected_identity=19)
    assert not target.steps


# Codec拒绝短头、多余字节、未知状态、保留字和未完成事务夹带的旧数据。
@pytest.mark.parametrize(
    "body",
    [
        b"",
        result_body() + b"x",
        result_body(state=4),
        result_body(reserved=1),
        result_body(state=1, payload=b"old"),
    ],
)
def test_peer_codec_rejects_malformed_body(body):

    with pytest.raises(ProtocolError):
        decode_peer_result(body)
