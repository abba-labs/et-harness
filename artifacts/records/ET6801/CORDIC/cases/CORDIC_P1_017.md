# CORDIC_P1_017 — CORDIC IRQ使能/禁用与软件Force测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：Source矩阵参数化CALC_COMPLETE、ARG_OVERFLOW、PM_ARG2_ERROR三类Capability声明IRQ Source；每个Source先在Enable+Unmask下Force，再在Disable下Force，比较Delivery增量；每阶段记录Service event_count（软件计数是Measurement，不是寄存器Observation）。执行：对当前Source Clear并Unmask、记录event_count起点→Enable后执行一次Force→等待event_count增加，读取IRQ_RAW/STATUS与Service latch→Clear目标Source确认pending恢复→Disable同一Source（其余条件不变）后再次Force→读取IRQ_RAW/STATUS并记录event_count delta确认禁用语义→Clear残留并恢复Enable/Mask配置，对全部Source重复。ET6801对应INT_EN/INT_FORCE_IND低3bit；Force写1硬件自清。

## 复测要点与判断边界

- 判定：Capability声明的逻辑IRQ Source均完成Enable/Disable两阶段；Enable+Unmask时Force使event_count增加且锁存当前Source；Disable后同Source Force不产生新的有效Delivery；每Source结束后pending被清除且配置恢复。
- Disable语义靠"两阶段增量对照"证明：仅有Disable下Force后event_count不增的绝对事实不够，需与Enable阶段投递成立形成对照。
- SDK IRQ API不做完整合法位校验（CORDIC_DRV_005），公共Service/Wrap只接受稳定三Source掩码并拒绝额外bit；Force只验证控制路径，不代替P1_008/P1_015/P1_016的自然IRQ Case。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P1_017`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
