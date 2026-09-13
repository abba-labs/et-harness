# UART_P1_006 — UART character timeout 中断和低于阈值数据的收取测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：把RX FIFO threshold配置为14；使能CHARACTER_TIMEOUT中断并读取IRQ session基线；开启内部loopback并先启动2 Byte Capture；发送仅2字节Payload，使数据不足以到达RX阈值，靠"RX FIFO非空且停止接收"的字符超时路径收取。

## 复测要点与判断边界

- 判定：2 Byte数据完整一致；CHARACTER_TIMEOUT event_count_delta>0；fault_count_delta=0。
- 触发条件是"低于阈值+接收停止"两条同时成立；发满14字节走阈值路径就测不到本Feature，超时与阈值路径不可混用。
- Capture要在发送前启动，否则超时收取期间的数据可能已被读走，中断事实链断裂。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P1_006`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
