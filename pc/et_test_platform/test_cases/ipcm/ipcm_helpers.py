# IPCM纯数据与Case退出动作清单。
# 职责：确定性Payload、原始集合显示和声明式清理动作。
# 边界：不执行设备I/O、不隐藏配置/刺激/等待，不包含最终断言。
# 依赖：标准库、本IP枚举及CRG公共枚举。

from ...drivers.ipcm.models import IpcmCaptureState


# 公开契约P(n,seed)：每个字节增加37并截断到8位，跨段内容容易区分。
def pattern(length: int, seed: int) -> bytes:

    return bytes((seed + 37 * index) & 0xFF for index in range(length))


# 将逻辑Endpoint集合还原为无损位集合，供同一硬件字段的报告显示。
def endpoint_mask(endpoints) -> int:

    return sum(1 << endpoint for endpoint in endpoints)


# 只比较已取得事件的独立字段；不进行任何硬件操作或内部assert。
def event_matches(event, payload: bytes, mailbox: int, endpoint: int, *, irq: bool) -> bool:

    return (
        event.state is IpcmCaptureState.READY
        and event.payload == payload
        and event.length == len(payload)
        and event.mailbox == mailbox
        and event.endpoint == endpoint
        and event.raw_status == 1 << mailbox
        and event.masked_status == (1 << mailbox if irq else 0)
        and event.callback_count == int(irq)
        and event.unexpected_count == event.overflow_count == event.fault_flags == 0
    )


# 差异位置-1代表完全相同；长度差异返回较短一侧的长度，不丢失尾部截断信息。
def first_mismatch(actual: bytes, expected: bytes) -> int:

    return next(
        (
            index
            for index, (left, right) in enumerate(zip(actual, expected, strict=False))
            if left != right
        ),
        -1 if len(actual) == len(expected) else min(len(actual), len(expected)),
    )
