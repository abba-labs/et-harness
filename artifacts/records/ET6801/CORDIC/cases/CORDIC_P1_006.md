# CORDIC_P1_006 — CORDIC相位模长双参数顺序与当前计数测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：使用Float32精确节点x=1、y=0，严格按x后y提交；计数生命周期按事务开始、等待y、第二参数完成、结果消费后分别期望0、1、0、0冻结。执行：清残留状态并读ARG_COUNT.CURRENT确认初始态→提交PM的x参数后立即读ARG_COUNT.CURRENT记录等待第二参数阶段→提交y参数并有界等待完成→读取ARG_COUNT.CURRENT、STATUS.COMPLETE与RESULT.PRIMARY/SECONDARY→phase=0、modulus=1的实际Float32 Raw与独立Golden逐位比较→清除COMPLETE后执行SQRT(0.25)恢复事务，确认计数保持0且结果为0.5。ET6801主路径用PM_CAL连续x→y写入，计数观测WR_NARGS_CNT_RPT[1:0]（2-bit只读）。

## 复测要点与判断边界

- 判定：每组向量严格x→y提交并完成、不出现第二参数错误状态；各阶段ARG_COUNT.CURRENT严格满足0→1→0生命周期；phase、modulus与恢复SQRT均与精确Float32 Golden逐位一致；结果消费后可无残留开始单参数事务。
- 观测点位是判定核心：x后必须"立即"读计数，错过窗口即判据失效；计数Expected随结果消费而变，须按目标生命周期冻结，不能凭感觉改期望序列。
- packed xy输入属P1_002矩阵；本Case只走x→y顺序主路径。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P1_006`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
