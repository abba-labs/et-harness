# STIMER_P2_001 — STIMER事件触发真实DMA搬运测试

整理时间：2026-09-10 21:53 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次全量历史测试 2026-08-28，源码 `bedb44062af1d81b157cf980a7c7ca579061e4f0`（clean，0903复测轮身份）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：以状态块Feature目录为准；资源等级 R2（DMA跨IP）。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

历史各轮本Case均PASS，无FAIL记录。方法：配置Peer DMA Channel、Source/Destination和传输宽度，保持Channel就绪但尚未完成；选择当前dma_request_source，配置能确定产生该事件的period/compare参数并清理历史状态；先Arm DMA Channel再START STIMER（禁止事件先于DMA就绪）；等待DMA完成并核对搬运数据与计数。

## 复测要点与判断边界

- 判定：STIMER事件触发单笔DMA真实完成；搬运数据完整；事件/DMA各计一次不重复。
- Arm先于START的顺序是硬约束——事件先到而DMA未就绪会丢触发，测出的是方法错误不是硬件缺陷。
- dma_request_source要按Execution Mapping选择，不自行拼路由。

## 依据与变化

方法权威：[公共STIMER契约](../../../../../test_case_doc/stimer/stimer.md)中的`STIMER_P2_001`；芯片适配见[ET6801 STIMER文档](../../../../../test_case_doc/stimer/ET6801_stimer.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:45 CST：从人读历史报告与芯片文档状态块提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 21:53 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
