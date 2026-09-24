# 示波器仪器库入口（自包含，可整包移植）。
#
# 分层：
#   interface.py  型号中立的观测契约（原厂，勿改）
#   _internal/    通信支撑层（SCPI/VISA/Deadline/异常）
#   mso5204/      厂商 MSO5204 驱动：997 个原子 API + 原厂 models/operations
#   wrapper/      封装层：台架对象、补充配置、波形分析
#   demos.py      可运行示例集
#   tests/        无硬件冒烟测试
#
# 职责：导出型号中立契约；具体型号能力请从各层子包导入。
# 边界：导入本包不打开仪器、不扫描 VISA 资源，也不发送任何 SCPI 命令。
# 依赖：仅依赖本包内部模块。

from .interface import SignalEdge, SignalObservation, SignalObserver

__all__ = ["SignalEdge", "SignalObservation", "SignalObserver"]
