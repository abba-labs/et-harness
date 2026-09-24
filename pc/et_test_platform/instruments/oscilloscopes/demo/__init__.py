# 示波器库可运行示例包入口。
#
# 职责：暴露示例清单与运行入口，供 `python -m oscilloscopes.demo.demos` 使用。
# 边界：不参与驱动本体，不被驱动代码导入；导入本包不连接仪器。
# 依赖：仅依赖本库 wrapper 与 mso5204 公开 API。

from .demos import DEMOS, main, run

__all__ = ["DEMOS", "main", "run"]
