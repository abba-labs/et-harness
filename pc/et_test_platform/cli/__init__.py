# 自动化平台命令行诊断入口。
#
# 职责：解析用户参数并调用稳定 Framework/Target API 完成最小软件诊断。
# 边界：不嵌入 IP 专用 Wire、不替代 pytest Formal Case，也不维护隐藏运行状态。
# 依赖：仅依赖 argparse 和平台稳定公共 API。
