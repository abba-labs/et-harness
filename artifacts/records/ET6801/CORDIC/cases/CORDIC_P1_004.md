# CORDIC_P1_004 — CORDIC迭代周期与精度表征测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：遍历Capability公开的precision_cycles选项（ET6801为CTRL0.NOI 5-bit，平台计划节点1..8由current Driver/FPGATest冻结；实际周期=配置+1），不假定历史Driver枚举就是硬件全部范围；挑战向量选对低迭代精度敏感且定义域安全的固定向量，Expected由PC double-precision独立计算且各节点输入完全相同。执行：逐节点配置→提交事务并有界等待完成→解码Actual计算绝对/相对误差（软件Error是Measurement，不冒充硬件Observation）→若Capability有该节点误差包络则逐节点核对，否则只保留表征值并保持Gap→汇总：要求最高精度节点满足正式accuracy budget并记录趋势，不强制数学上未承诺的严格单调性。硬件未公开的完整MAX_ITER_CYC数值不在本Case结论内。

## 复测要点与判断边界

- 判定：Capability公开的全部计划precision节点执行并记录误差；最高精度节点满足已冻结函数/格式accuracy budget；若Capability声明逐节点误差包络则所有对应节点不越界；所有合法节点在deadline内形成完成结果、不异常停滞。
- 不复制历史FPGATest的矛盾断言（其注释自认低迭代误差判断不通过却对1..8统一用同一历史容差）；判定只认逐节点表征+已发布包络+最高精度预算。
- ET6801使用人工复核批准的`1e-3`绝对误差预算作最高节点验收；逐节点正式包络未取得前保持Gap。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P1_004`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
