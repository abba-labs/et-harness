# UART_P2_005 — UART 9-bit 硬件地址匹配和不匹配地址过滤测试

整理时间：2026-09-10 22:11 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：UART_F_029、UART_F_030、UART_F_031；资源等级 R0（Peer）。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：Gate两端NINE_BIT后初始化，DUT开启hardware address match=0x12；Peer发送匹配地址+数据，DUT读取普通RX数据并记录匹配实际值；清空/确认RX终态后由Peer发送不匹配地址+后续数据；进入覆盖完整帧到达时间的有界观察窗口，重复读取UART_FIFO.RX_LEVEL确认过滤生效。

## 复测要点与判断边界

- 判定：匹配地址路径数据正确；不匹配地址在完整观察窗口内所有RX level采样均为0；观察窗口有明确deadline且取得规定采样数。
- 过滤证明靠"有界窗口+多次采样"，固定sleep后单次读RX_LEVEL是SPEC点名的反模式——单次采样撞上时序尾巴会误判过滤失效。
- 0x12是SPEC固定匹配地址；改地址要同步改Peer刺激与期望，不能两端不一致。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P2_005`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
