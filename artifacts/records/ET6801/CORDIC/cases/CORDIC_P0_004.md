# CORDIC_P0_004 — CORDIC复位后重新配置与运算恢复测试

整理时间：2026-09-10 22:08 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:11 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean，来自芯片文档状态块）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：CORDIC_F_046；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：使用结果易判别的Float32 SQRT(1.0)固定输入作恢复向量，两轮Expected均由独立PC数学Oracle计算。流程：复位前建立已知配置并执行第一组输入→读取结果与第一轮Golden比较（基线可用）→由PC Case调用外层CRG时钟/复位Owner执行CORDIC复位并记录动作结果（CORDIC Service不跨IP直接调用复位实现）→复位后完整重新配置并清状态，不把旧完成/错误状态当本轮Evidence→提交同一确定性输入→比较复位前后Actual并确认清除后状态归零。芯片映射经CRG专属Driver/Service/Wrap用生成CMSIS的GTEN0/SRST0 CORDIC0 bit20建立。

## 复测要点与判断边界

- 判定：复位前后Actual分别满足各自独立Golden与accuracy budget；复位后完整重新配置即恢复运算，不依赖复位前会话；第二轮结果与状态对应第二轮输入，不复用第一轮残留；分层正确（复位由外层Owner编排）。
- 复位后旧完成/错误状态不作为Evidence；判定前先清状态再取新快照。
- 复位动作归属外层CRG Owner是硬边界：若在CORDIC Service内直接实现复位即为分层违规，须整改而不是接受。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P0_004`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
