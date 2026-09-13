# CORDIC_P1_015 — CORDIC参数溢出IRQ自然投递测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：溢出刺激复用P1_011已审核的确定性未消费提交序列，不用软件Force制造ARG_OVERFLOW，也不声称测得最小容量；IRQ配置为Enable且Unmask ARG_OVERFLOW并记录Source级event_count基线。执行：清除ARG_OVERFLOW状态/IRQ并记录event_count起点→Enable并Unmask启动Source级IRQ会话→完成并消费一个合法事务确认无历史ARG_OVERFLOW投递→执行已审核未消费提交序列等待目标IRQ投递→读取STATUS.ARG_OVERFLOW、IRQ_RAW/STATUS.ARG_OVERFLOW与IRQ_DELIVERY.LATCHED_SOURCE→Clear目标状态与IRQ，确认event_count不再增长→执行合法数学事务检查结果正确。ET6801对应INT bit0（ARG_OVERFLOW），状态位STATUS_RPT.WR_NARGS_OVF_RPT。

## 复测要点与判断边界

- 判定：正常基线无投递，确定性未消费提交序列使ARG_OVERFLOW event_count增加（自然因果）；Status/IRQ/Service均对应ARG_OVERFLOW；清除后无新增残留投递且合法事务可再次正确运行。
- 自然刺激与Force分工：本Case只证明自然因果；软件Force路径归P1_017，不得互相替代。
- 投递证据四来源（Raw/Status/Service latch/event_count）分层保存；状态位在Clear前取证，避免先清后读使因果不可证。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P1_015`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
