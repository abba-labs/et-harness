# Framework Communication Formal Case显式执行白名单。
#
# 职责：声明允许进入正式pytest执行集合的框架通信稳定Case ID。
# 边界：不导入Case函数、不执行测试、不保存启停状态或通信会话。
# 依赖：仅依赖Case稳定命名契约。

FRAMEWORK_COMMUNICATION_CASE_REGISTRY = ("framework_communication_p3_001",)
