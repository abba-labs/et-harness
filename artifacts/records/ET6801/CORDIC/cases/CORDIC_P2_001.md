# CORDIC_P2_001 — CORDIC DMA工作模式真实搬运等价性测试

历史整理声明：2026-09-11 21:00 CST；原“对照本轮 Canonical Session”声明未获当前证据支持，撤回其已核实含义。

适用基线：ET6801 / FPGA；源码与运行对应关系未核实，不作为当前版本验证结论。

来源状态：UNVERIFIED

来源修正（2026-09-12 17:09 CST）：来源工作区现存 Session 为 `18bbc66f-6b0d-4396-adcb-0e92d2a957fa`，源码 `228df5bd75a11f7b27c691698d77e65d517fea99`；与本文原基线不一致。该 Session 包含本 Case，但不能据此证明旧正文描述的轮次、方法及观测属于它。本次仅标记来源冲突，未重跑测试、未改原始结果、未完成发布确认。以下原声明保留为历史，不能当作本轮已核实 PASS。

历史基线声明：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case被正式门禁判定SKIP（NOT_APPLICABLE），不是Case逻辑FAIL，也不是外部接线阻塞：Runtime Capability明确拒绝CORDIC DMA工作模式，Case未向硬件发起DMA刺激。2026-08-28设计人员确认ET6801 CORDIC不支持DMA工作模式；此前历史运行（DMA双通道15秒未完成）只保留为历史证据，不再解释为ET6801 CORDIC DMA Feature故障。公共CORDIC_F_027与Case代码继续保留，服务于明确声明支持CORDIC DMA的后续芯片；SVD中CTRL0.WORK_MODE=11字段与历史Request39/40不能作为当前芯片支持证据（CORDIC_DRV_002按硬件事实关闭）。

## 判断边界与复测条件

- 复测资格：仅当设计人员重新确认ET6801硬件支持该模式时复测；在此之前不得通过放宽Capability、伪造SKIP/PASS或重新构造Request组合反复尝试。
- 复测前提：先冻结当前芯片CORDIC DMA Execution Mapping（Request ID、数据方向、端点宽度与Channel资源），禁止沿用历史Request ID；Mapping缺失时运行期失败关闭，不得伪造PASS或SKIP。
- 取得资格后的判定要点：先确认DMA work mode、Request ID、方向、端点与清理Owner在Mapping中齐全；先用非DMA路径取得CPU基线；配置Peer DMA Channel并启动后不以配置返回成功当作完成，须有界等待DMA_CHANNEL_STATUS完成且无Error；读取DMA_DESTINATION_WORD/Buffer按CORDIC Codec解码；DMA Actual同时与独立Golden和CPU基线比较（路径等价）。资源等级R2：需要片内DMA可访问的输入/输出测试内存与Peer DMA公共自动化链，无外部仪器。
- 事务结束必须停止/复位本Case DMA Channel并恢复CORDIC工作模式，避免残留配置污染后续Case。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P2_001`；芯片适配与SKIP归因见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)状态块；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼SKIP归因与复测条件；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本轮 setup SKIP：`running CORDIC service does not support DMA work m…`（Runtime Capability 拒绝 DMA 工作模式）。与既有 NOT_APPLICABLE 边界一致。
