# UART_P3_009 — UART Direct FIFO 访问（FAR/TFR/RFW）测试

历史整理声明：2026-09-11 21:00 CST；原“对照本轮 Canonical Session”声明未获当前证据支持，撤回其已核实含义。

适用基线：ET6801 / FPGA；源码与运行对应关系未核实，不作为当前版本验证结论。

来源状态：UNVERIFIED

来源修正（2026-09-12 17:09 CST）：来源工作区现存 Session 为 `1e7bf0dc-1d5d-4f47-b1e2-a3f41a483fa0`，源码 `228df5bd75a11f7b27c691698d77e65d517fea99`；与本文原基线不一致。该 Session 包含本 Case，但不能据此证明旧正文描述的轮次、方法及观测属于它。本次仅标记来源冲突，未重跑测试、未改原始结果、未完成发布确认。以下原声明保留为历史，不能当作本轮已核实 PASS。

历史基线声明：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

三轮运行（2026-08-10、2026-08-13、2026-08-28）本Case均被正式门禁判定SKIP：ET6801当前UART组件参数未声明Direct FIFO Access支持，Case未执行FAR/TFR/RFW访问——目标芯片不具备该可执行能力，属能力边界而非硬件缺陷。Case方法意图：Gate UartFeature.FIFO_ACCESS；开启Direct FIFO access并记录UART_FIFO_ACCESS.ENABLED；Halt TX后向TX FIFO写入0x5A经TFR读回；经RFW向RX FIFO注入0xA5后用普通read_exact读回，验证直访与普通路径的一致性。

## 判断边界与复测条件

- 有能力时判定为：FIFO_ACCESS feature存在；TFR读回0x5A；RFW注入后普通RX读回0xA5。
- SKIP原因：Capability未声明该Feature，Gate在修改任何状态前失败关闭；这与"测了但失败"完全不同，不能记为FAIL或弱化PASS。
- 复测条件：仅当后续RTL/芯片Capability明确支持Direct FIFO Access时复测；不得绕过Capability Gate强行执行。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P3_009`；芯片适配与SKIP归因见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)状态块；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼SKIP归因与复测条件；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本轮 SKIP：`skip_by_runtime_feature: UART DUT feature FIFO_ACCESS unavailable`。与既有能力边界一致。
