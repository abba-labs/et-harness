# RIGOL MSO5204 顶层运行控制命令。
#
# 职责：映射 AUToscale、CLEar、RUN、STOP、SINGle 和 TFORce 六个顶层原子动作。
# 边界：每个公开 API 只发送一条 SCPI 命令，不等待波形稳定或执行测试判定。
# 依赖：仅依赖公共 ScpiSession。

from __future__ import annotations

from ..._internal.scpi import ScpiSession


# 提供示波器运行状态原子控制；每个公开方法只发送一条顶层 SCPI 命令，不追加等待、测量或判定动作。
class Mso5204BasicControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 自动设置当前波形显示参数；只发送一次 :AUToscale，不追加等待或测量。
    def autoscale(self) -> None:
        self._session.write(":AUToscale")

    # 清除屏幕上的波形显示；只发送一次 :CLEar，不改变采集配置。
    def clear(self) -> None:
        self._session.write(":CLEar")

    # 启动连续采集；只发送一次 :RUN，不等待触发完成。
    def run(self) -> None:
        self._session.write(":RUN")

    # 停止采集；只发送一次 :STOP，便于后续读取 RAW 内存波形。
    def stop(self) -> None:
        self._session.write(":STOP")

    # 切换到单次触发采集；只发送一次 :SINGle，不强制产生触发。
    def single(self) -> None:
        self._session.write(":SINGle")

    # 强制产生一次触发；只发送一次 :TFORce，不修改触发条件。
    def force_trigger(self) -> None:
        self._session.write(":TFORce")
