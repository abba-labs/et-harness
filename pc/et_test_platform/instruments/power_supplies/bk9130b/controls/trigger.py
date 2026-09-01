# B&K Precision 9130B 触发控制。
#
# 职责：映射立即触发和触发延时的原子 SCPI 命令。
# 边界：不配置触发耦合通道、不等待触发后的稳定结果，也不执行测量判定。
# 依赖：仅依赖 ScpiSession 和 Validation。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..validation import require_range


# 提供 9130B 触发单命令控制；触发作用通道由独立 COUPle 配置决定。
class Bk9130bTriggerControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 产生一次立即触发；只发送 TRIGger:IMMediate，不执行后续读取。
    def immediate(self) -> None:
        self._session.write("TRIGger:IMMediate")

    # 设置触发延时 0.1~99999.9 秒；不会立即产生触发。
    def delay_set(self, delay_s: float) -> None:
        value = require_range(delay_s, 0.1, 99999.9, "delay_s")
        self._session.write(f"TRIGger:DELay {value:g}")

    # 查询触发延时；查询过程不会产生触发，也不会修改现有延时配置。
    def delay_get(self) -> float:
        return float(self._session.query_text("TRIGger:DELay?"))
