# SYSCNT_P0_002 — 启停与续计数测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

最近一轮PASS，无FAIL记录。方法：停止态装载起始计数后只置CONTROL.ENABLE并读回使能位（不再次装载）；等待10ms读COUNT.READ确认相对起始值增加；停止后两次读数确认精确相等（冻结）；恢复使能确认从停止值续计。

## 复测要点与判断边界

- 判定：运行读数大于装载值；恢复读数大于停止值且无意外回绕；停止后两次读数精确相等。
- "只置使能位不再装载"是续计数语义的关键——重新装载就测不出续计。
- 停止冻结判据与P0_001停止装载共用机制，本Case聚焦运行态启停。

## 依据与变化

方法权威：[公共SYSCNT契约](../../../../../test_case_doc/syscnt/syscnt.md)中的`SYSCNT_P0_002`；芯片适配见[ET6801 SYSCNT文档](../../../../../test_case_doc/syscnt/ET6801_syscnt.md)。

- 2026-09-09 12:05 CST：从run 20260904_063646 Canonical事实与公共契约提炼；未进行硬件复测。
- 2026-09-10 22:44 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
