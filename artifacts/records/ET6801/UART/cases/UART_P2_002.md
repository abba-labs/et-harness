# UART_P2_002 — UART RX DMA 从 UART RX 端点到带 Guard 的内存 Buffer 单次传输测试

整理时间：2026-09-10 22:11 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：UART_F_035、UART_F_036；资源等级 R0（Peer+DMA）。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：重置Resource并创建带前后Guard的Destination，选择空闲DMA Channel；初始化DUT/Peer并使能UART DMA request；配置SYSCTRL UART RX route与DMA P2M Channel；启动顺序为先使能TRANSFER_DONE并启动DMA RX，再由Peer发送32字节Payload。

## 复测要点与判断边界

- 判定：Peer完整发送32字节；Destination有效区数据一致；前后Guard均完整。
- Guard完整性是内存边界证据：DMA写越界会先破坏Guard，只看有效区一致会漏掉越界写缺陷。
- 启动顺序必须DMA先于数据（RX侧无数据时DMA先行等待），顺序颠倒会造成开头字节丢失。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P2_002`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
