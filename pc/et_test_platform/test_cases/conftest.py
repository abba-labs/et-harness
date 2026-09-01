# Formal Case的pytest Fixture入口。
#
# 职责：提供运行时事实门禁和Driver构造。
# 边界：不执行Feature动作、不拥有最终断言，也不隐藏完整Case。
# 依赖：仅依赖pytest、Profile、Capability和稳定Driver接口。

pytest_plugins = ("et_test_platform.pytest_plugin",)
