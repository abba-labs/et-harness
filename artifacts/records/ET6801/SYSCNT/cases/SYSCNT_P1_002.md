# SYSCNT_P1_002 — 频率标识设置与读取测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

最近一轮PASS，无FAIL记录。方法：停止态先读FREQUENCY.ID与COUNT.READ保存应恢复的正式频率标识；写入第一个标识后读回FREQUENCY.ID、COUNT.READ和CONTROL.ENABLE；再写第二组标识并读回；最后恢复初态标识验证。

## 复测要点与判断边界

- 判定：两组写入值和恢复值都精确读回；计数值与使能位在本Case内保持停止初态（频率标识设置不扰动计数状态）。
- 恢复初态是本Case的收尾义务——留一个非正式标识会影响后续Case的频率语义。
- 频率标识是"声明值"不是实测频率，实测校准属P2_001（独立参考计时）。

## 依据与变化

方法权威：[公共SYSCNT契约](../../../../../test_case_doc/syscnt/syscnt.md)中的`SYSCNT_P1_002`；芯片适配见[ET6801 SYSCNT文档](../../../../../test_case_doc/syscnt/ET6801_syscnt.md)。原始参数级证据：[SYSCNT Session](../../../../../artifacts/runs/20260904_063646_997568_local_et6801_fpga_atp_testing/tests/syscnt/session.json)。

- 2026-09-09 12:05 CST：从run 20260904_063646 Canonical事实与公共契约提炼；未进行硬件复测。
- 2026-09-10 22:44 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
