# CORDIC_P0_003 — CORDIC浮点核心数学函数矩阵测试

整理时间：2026-09-10 22:08 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:11 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean，来自芯片文档状态块）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：CORDIC_F_001～F_009、CORDIC_F_011；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：九类函数各取确定性合法域节点（PM按x后y提交），Expected由独立数学定义产生并转为IEEE-754 Float32 Raw bits；每个函数节点独立重新配置FLOAT32 Polling路径并清除历史状态，不共享配置；在统一轮询上限内等待自然COMPLETE（不用固定sleep），读取RESULT.PRIMARY（SINCOS/PHASE_MODULUS/HSINCOS加读RESULT.SECONDARY），硬件Raw解码为Float32后与独立Golden按1e-4绝对误差预算逐项比较，并确认无错误状态；对COMPLETE执行W1C并复读归零，保证下一节点无残留。

## 复测要点与判断边界

- 判定：Runtime声明的九类Float32函数节点分别执行，缺失函数明确Skip、不得由其他函数PASS代替；全部主结果与已声明第二结果满足1e-4预算；每节点只产生COMPLETE且W1C后清零。
- 能力门禁前置：Runtime未声明的函数节点跳过是合法SKIP路径，不是失败；不能用其他函数的结果冒充覆盖。
- 完成状态清除采用"读1→清→复读0"闭环，不以只看最终0证明W1C语义。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P0_003`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
