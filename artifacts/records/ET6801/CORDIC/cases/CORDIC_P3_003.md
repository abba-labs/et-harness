# CORDIC_P3_003 — CORDIC零开销原子窗口抗IRQ干扰测试

整理时间：2026-09-10 22:08 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:11 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean，来自芯片文档状态块）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：CORDIC_F_044、CORDIC_F_026；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：原子事务使用双参数PHASE_MODULUS或等价可暴露中断插入风险的零开销事务，Expected由atan2/hypot独立计算；干扰源为平台已审核的可控目标侧IRQ（固定seed/固定轮数），在关键窗口尝试插入另一个CORDIC请求，但干扰源不得直接越层访问CORDIC实现。执行：无干扰执行基线事务确认满足Golden→配置可控IRQ并记录干扰event_count基线（不在ISR中直接绕过公共CORDIC路径）→经公共zero_overhead_execute进入受保护write→read窗口同时触发IRQ干扰→窗口结束后绑定当前request_id的Raw结果并记录干扰是否延后交付→固定seed/轮数重复原子窗口与IRQ交错覆盖多个触发相位→每轮结果必须与本轮PM Golden对应→汇总结果、request_id、IRQ event_count与异常状态，确认无ARG2_ERROR/ARG_OVERFLOW误触发→停止干扰会话并确认普通事务恢复。历史FPGATest case35用GPIO ISR直接访问CORDIC的跨层写法不复制。

## 复测要点与判断边界

- 判定：基线正确；受控IRQ交错下所有受保护事务保持request/result对应且数学结果正确；合法受保护事务不产生PM_ARG2_ERROR或ARG_OVERFLOW；压力结束后普通CORDIC事务仍可正确完成。
- 分层红线：干扰注入只经公共IRQ控制接口，IRQ event_count/latched来源按软件事实保存、不冒充CORDIC寄存器Observation。
- 边界：本Case闭合的是受控Pending隔离（Test Extension保存/恢复PRIMASK、Wrap只走该Driver入口）；更强异步ISR干扰仍由独立Gap保留，不在本Case宣称。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P3_003`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
