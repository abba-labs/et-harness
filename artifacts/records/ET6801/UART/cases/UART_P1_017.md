# UART_P1_017 — UART 参数校验对非法输入的拒绝和合法路径恢复测试

整理时间：2026-09-10 22:11 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:14 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：UART_F_001；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史三轮运行本Case均PASS，无FAIL记录。方法：依次调用七项非法操作（非法波特率/数据位/停止位/校验等组合），要求公共Driver在设备传输前抛ValueError并逐项记录拒绝结果、累计rejected_count；随后以合法115200 8N1重新初始化，开启内部loopback做8字节Capture验证合法路径完全恢复。

## 复测要点与判断边界

- 判定：七项非法请求全部被ValueError拒绝；拒绝发生后合法初始化仍成功；8字节恢复收发完整一致。
- 拒绝必须发生在设备传输之前（Driver参数校验层）——如果非法参数已打到设备再报错，校验语义就失效了。
- "拒绝后还能正常工作"与"拒绝本身"是两个独立判定项；只验证拒绝不验证恢复会漏掉状态污染缺陷。

## 依据与变化

方法权威：[公共UART契约](../../../../../test_case_doc/uart/uart.md)中的`UART_P1_017`；芯片适配见[ET6801 UART文档](../../../../../test_case_doc/uart/ET6801_uart.md#uart-record-index)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 10:13 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:11 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
