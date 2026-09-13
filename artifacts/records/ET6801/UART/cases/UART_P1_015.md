# UART_P1_015 — UART 代表性波特率配置和双向收发测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：读取DUT与Peer Runtime Capability计算共同波特率区间；在共同区间生成去重后的最小/常用/高速/非整除分频候选集合；逐候选用独立生命周期把两端初始化为相同波特率并执行DUT→Peer短帧取证。

## 复测要点与判断边界

- 判定：共同范围内至少执行一个候选（范围不允许时全集缩为可用集是合法行为）；所有候选双向收发完整且数据一致。
- F_006在本芯片是PARTIAL_ADAPTATION：候选集由Capability约束，不是全波特率扫描；本Case只证"配置正确且能收发"，不证波特率精度——绝对位时序/误差ppm属F_048，需独立Observer（未实现，见P3_006 Gap）。
- 非整除分频候选保留在集合里，专门暴露分频误差问题，不要在裁剪候选时删掉。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P1_015`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
