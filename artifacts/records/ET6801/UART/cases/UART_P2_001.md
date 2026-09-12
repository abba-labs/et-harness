# UART_P2_001 — UART TX DMA 从内存到 UART TX 端点的单次传输测试

历史整理声明：2026-09-11 21:00 CST；原“对照本轮 Canonical Session”声明未获当前证据支持，撤回其已核实含义。

适用基线：ET6801 / FPGA；源码与运行对应关系未核实，不作为当前版本验证结论。

来源状态：UNVERIFIED

来源修正（2026-09-12 17:09 CST）：来源工作区现存 Session 为 `1e7bf0dc-1d5d-4f47-b1e2-a3f41a483fa0`，源码 `228df5bd75a11f7b27c691698d77e65d517fea99`；与本文原基线不一致。该 Session 包含本 Case，但不能据此证明旧正文描述的轮次、方法及观测属于它。本次仅标记来源冲突，未重跑测试、未改原始结果、未完成发布确认。以下原声明保留为历史，不能当作本轮已核实 PASS。

历史基线声明：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录（2026-08-10冻结全量HIL中UART+DMA链路亦无FAIL）。方法：准备Source Buffer/Payload并选择空闲DMA Channel；初始化DUT/Peer并使能UART DMA request；按Execution Mapping配置SYSCTRL UART TX request route与DMA M2P Channel；使能DMA TRANSFER_DONE中断并先启动Peer Capture；DMA完成内存到UART TX端点的32字节搬运。

## 复测要点与判断边界

- 判定：Peer实际数据与32字节Source一致；TRANSFER_DONE被锁存且irq_count≥1；unexpected/overflow=0且DMA Channel终态FREE。
- 路由配对由Execution Mapping声明，Case不自行拼SYSCTRL寄存器值；换板/换映射时要同步映射文档。
- Channel终态FREE与unexpected/overflow为零是链路干净的完整证据，只看数据一致会漏掉残留事务。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P2_001`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
