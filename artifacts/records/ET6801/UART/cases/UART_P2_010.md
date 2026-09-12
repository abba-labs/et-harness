# UART_P2_010 — UART 9-bit 地址匹配对应的 NINE_BIT_ADDRESS 中断事件路径测试

历史整理声明：2026-09-11 21:00 CST；原“对照本轮 Canonical Session”声明未获当前证据支持，撤回其已核实含义。

适用基线：ET6801 / FPGA；源码与运行对应关系未核实，不作为当前版本验证结论。

来源状态：UNVERIFIED

来源修正（2026-09-12 17:09 CST）：来源工作区现存 Session 为 `1e7bf0dc-1d5d-4f47-b1e2-a3f41a483fa0`，源码 `228df5bd75a11f7b27c691698d77e65d517fea99`；与本文原基线不一致。该 Session 包含本 Case，但不能据此证明旧正文描述的轮次、方法及观测属于它。本次仅标记来源冲突，未重跑测试、未改原始结果、未完成发布确认。以下原声明保留为历史，不能当作本轮已核实 PASS。

历史基线声明：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

**本Case有明确的修复史**。2026-08-05 09:46独立HIL连续两次FAIL：`enabled_mask=0x40`但`event_count`、`pending_mask`、`active_mask`全为0，而地址匹配数据路径本身正确——结论是"地址匹配数据路径PASS不等于地址IRQ PASS"。定位为ET6801 UART Test Driver软件事件分类缺陷：未把LSR `ADDR_RCVD`解析为9-bit地址事件；修复在隔离测试扩展区增加IIR/LSR原子快照，真实OE/PE/FE/BI/RFE错误保留为ERROR；未动UART1/UART2数据路径、bitfile、BootROM、OTP/NVR/fuse。2026-08-05 11:12修复后HIL PASS：`pending_mask=0x40`、`event_count=1`、`event_count_delta=1`、`overflow_count=0`，清理后enabled/pending/active均归0；IRQ影响回归（RX data available、parity error、IRQ mask/priority/clear）3项PASS。2026-08-13与08-28全量运行本Case均PASS。

## 复测要点与判断边界

- 判定：NINE_BIT_ADDRESS event_count_delta>0且fault增量=0；PENDING/ACTIVE mask取证中断来源被识别；匹配数据正确且关闭后Service pending/active无该source。
- 数据路径与中断路径必须分别取证；修复时的定位顺序（先确认刺激与观测条件具备、排除SKIP可能，再查事件分类层）值得复用。
- 修复只涉及测试扩展区，公共协议未变；复测若FAIL应先查Driver事件分类是否回退，不先怀疑RTL。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P2_010`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)。修复史证据：[P2-010与P3-007独立HIL](../../../../../report/validation/dut/20260805_uart_split_cases_hil.md)、[9-bit地址中断Driver修复HIL](../../../../../report/validation/dut/20260805_uart_address_irq_driver_fix_hil.md)（本文件引用的实测值均来自这两份报告）；历史结果与证据缺失声明见[历史来源与版本](../README.md)。

- 2026-09-09 10:13 CST：从0805两份报告与三轮全量运行状态提炼修复史、实测值与方法边界；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
