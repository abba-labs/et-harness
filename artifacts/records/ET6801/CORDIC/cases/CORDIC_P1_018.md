# CORDIC_P1_018 — CORDIC IRQ Mask/Unmask与Raw/Status分层测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：Source选择至少覆盖一个可安全Force的逻辑IRQ Source（Capability允许则参数化全部Source）；Mask对照为保持Source Enable、先Mask后Force、再Unmask同一pending Source；记录Mask前后event_count delta（软件计数不替代Raw/Status）。执行：Enable当前Source、Clear pending并记录event_count起点→Mask后执行一次Force→在Clear前读取IRQ_RAW/STATUS.<Source>并记录event_count delta→判定Raw保留刺激事实、Status/Delivery被Mask抑制→不重新Force直接Unmask同一pending Source→等待规定有效投递并读取Service latch/Status→Clear目标Source确认Raw/Status恢复0并恢复Mask配置。ET6801对应INT_MASK（1=Mask）与INT_RAW_RPT/INT_STATUS_RPT分层（低3bit）。

## 复测要点与判断边界

- 判定：Mask阶段必须同时满足Raw=1、Status=0；Mask阶段event_count不得增加；Unmask后不重新Force即可按目标IRQ语义形成有效投递；Clear后Raw/Status均恢复0。
- Unmask投递必须来自Unmask前已存在的同一pending，不得重新Force补投——否则"Mask保留来源事实"未被证明。
- Raw与Status是两个独立端点，禁止合并读取或用一个代替另一个；event_count只作Delivery旁证。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P1_018`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
