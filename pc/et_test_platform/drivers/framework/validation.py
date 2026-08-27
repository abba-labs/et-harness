# FRAMEWORK PC Driver Package 的validation层。
#
# 职责：提供 FRAMEWORK 的本 IP 参数类型、范围和组合校验。
# 边界：不判断跨 IP 关系、不读取 Bench/Profile，也不发送硬件命令。
# 依赖：仅依赖本 IP Model 与平台配置异常。

from __future__ import annotations

from ...core.errors import ProtocolError


# 校验 Framework Session ID 是非零 uint32。
def require_session_id(value: object) -> int:

    if isinstance(value, bool) or not isinstance(value, int):
        raise ProtocolError("session_id_factory must return a nonzero uint32")
    if not 0 < value <= 0xFFFFFFFF:
        raise ProtocolError("session_id_factory must return a nonzero uint32")
    return value
