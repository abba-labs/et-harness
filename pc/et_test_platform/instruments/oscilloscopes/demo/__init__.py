# 示波器库可运行示例包入口。
#
# 职责：把示例标记为一个包，使 `python -m oscilloscopes.demo.demos` 可用。
# 边界：不参与驱动本体，不被 mso5204/wrapper 导入；导入本包不连接仪器。
# 依赖：仅依赖本库 wrapper 与 mso5204 公开 API。
#
# 注意：这里刻意不在包级导入 demos 子模块。否则 `python -m oscilloscopes.demo.demos`
# 会先在包 __init__ 里加载该模块，再由 runpy 重复执行，触发 RuntimeWarning。
