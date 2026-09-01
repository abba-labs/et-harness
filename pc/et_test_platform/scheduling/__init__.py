# 测试运行上下文、Evidence 与产物路径管理。
#
# 职责：维护一次 pytest Session/Case 的元数据、证据来源和结果附件路径。
# 边界：不决定 IP 测试逻辑、不发送设备命令，也不形成第二套 PASS/FAIL 判定。
# 依赖：仅依赖配置、文件系统和稳定 Evidence/Result 数据模型。
