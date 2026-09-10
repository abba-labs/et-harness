# CORDIC_P1_007 — CORDIC轮询完成状态机测试

整理时间：2026-09-10 22:08 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:11 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean，来自芯片文档状态块）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：CORDIC_F_024、CORDIC_F_028；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：选择一个单结果函数（SQRT）和一个双结果函数（PM）的确定性合法输入；使用统一deadline与轮询间隔策略，不允许无限while或固定sleep替代状态条件。执行：显式清除上一事务COMPLETE并确认STATUS.COMPLETE=0→配置POLLING工作模式（ET6801 CTRL0.WORK_MODE=01）与稳定数据格式精度→提交输入并记录Expected→重复读取STATUS.COMPLETE直到为1或deadline到期（记录poll_count与完成时间）→完成后读取结果保存Raw→解码Actual与独立Golden比较并确认无目标错误状态→显式Clear COMPLETE并复读=0恢复基线。ET6801观测STATUS_RPT.RRDY_FLG_RPT（W1C）；公共Wrap先经无副作用CORDIC_getStatus()保存Snapshot再显式Clear（SDK的CORIDC_IsRReady()读后自动清COMPLETE，禁止作为Formal getter）。

## 复测要点与判断边界

- 判定：每个节点在统一deadline内观察到STATUS.COMPLETE=1；Actual满足对应独立Golden与accuracy budget；Clear前COMPLETE=1且Clear后=0，不以只看最终0证明W1C。
- 旧SDK Helper（CORIDC_IsRReady）读后清COMPLETE，会把"等待完成"变成"顺带清除"，破坏显式Clear复核，禁止进入测试路径。
- 轮询次数poll_count是Measurement证据，可与硬件状态快照配合定位阻塞，但不替代STATUS.COMPLETE=1的完成判据。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P1_007`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
