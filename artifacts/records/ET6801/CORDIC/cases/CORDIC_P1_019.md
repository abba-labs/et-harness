# CORDIC_P1_019 — CORDIC IRQ单Source精确清除隔离测试

历史整理声明：2026-09-11 21:00 CST；原“对照本轮 Canonical Session”声明未获当前证据支持，撤回其已核实含义。

适用基线：ET6801 / FPGA；源码与运行对应关系未核实，不作为当前版本验证结论。

来源状态：UNVERIFIED

来源修正（2026-09-12 17:09 CST）：来源工作区现存 Session 为 `18bbc66f-6b0d-4396-adcb-0e92d2a957fa`，源码 `228df5bd75a11f7b27c691698d77e65d517fea99`；与本文原基线不一致。该 Session 包含本 Case，但不能据此证明旧正文描述的轮次、方法及观测属于它。本次仅标记来源冲突，未重跑测试、未改原始结果、未完成发布确认。以下原声明保留为历史，不能当作本轮已核实 PASS。

历史基线声明：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：选择两个不同且可安全Force的逻辑IRQ Source分别作target与neighbor；优先在Mask状态构造Raw pending，避免ISR自动清除破坏清除隔离现场。执行：Mask并Enable target/neighbor，Clear二者确认Raw均为0→分别Force target与neighbor，保持两者Raw pending共存→一次读取IRQ_RAW快照确认target=1且neighbor=1→只对target执行IRQ_CLEAR（不操作neighbor）→再次读取IRQ_RAW期望target=0且neighbor仍=1→Clear neighbor确认两Source最终均为0→恢复Mask/Enable配置并记录完整前后位图。ET6801对应INT_CLR低3bit（写1硬件自清）与INT_RAW_RPT位图。

## 复测要点与判断边界

- 判定：清除前两Source Raw均真实pending（共存前提）；Clear target后只有target归零；neighbor在target清除后继续保持pending直到自身被Clear；Case结束测试Source Raw均为0。
- 清除前后必须各取一次完整Raw快照形成位图链，逐位读改会破坏"一次快照"事实并给竞态留缝。
- 隔离前提是Mask状态下构造pending：未Mask时ISR可能抢先清Source，导致隔离判据假绿或假红。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P1_019`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
