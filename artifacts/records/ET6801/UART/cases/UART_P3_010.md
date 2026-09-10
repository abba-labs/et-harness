# UART_P3_010 — UART 双向混合收发 20 轮稳定性能力测试

整理时间：2026-09-10 22:11 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：UART_F_010、UART_F_017、UART_F_019、UART_F_047；资源等级 R0（Peer）。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录（08-13轮全批27.18s中本Case占主要耗时，是该轮长稳项）。方法：初始化DUT/Peer为相同默认帧格式并建立20轮结果容器；每轮按4/32/257字节循环选择长度，由round index生成两个方向不同Payload（固定随机种子可复现）；每轮先启动Peer Capture执行DUT→Peer传输，再启动DUT Capture执行Peer→DUT传输。

## 复测要点与判断边界

- 判定：20轮全部按4/32/257字节循环执行；每轮两个方向发送/接收完整且数据一致；总事务数=40。
- 长度三值循环覆盖了短帧/中帧/跨页大帧，257字节是超过常见缓冲页的跨页路径，不能裁剪。
- Payload由种子确定性生成：失败复现时相同round index产生相同数据，这是长稳Case可定位的前提。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P3_010`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
