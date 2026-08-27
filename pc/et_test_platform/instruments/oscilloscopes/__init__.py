# 外部测试设备适配层的命名空间入口。
#
# 职责：为后续仪器/烧录器实现保留按设备类型分层的稳定包边界。
# 边界：当前入口不执行 Test Case、不包含芯片业务策略，也不隐式创建跨 IP 流程。
# 依赖：仅依赖公共 SignalObserver 契约；具体型号由 Bench/Factory 选择。

from .interface import SignalEdge, SignalObservation, SignalObserver

__all__ = ["SignalEdge", "SignalObservation", "SignalObserver"]
