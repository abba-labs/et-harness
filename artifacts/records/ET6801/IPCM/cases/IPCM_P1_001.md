# IPCM_P1_001 — IPCM Manual ACK Payload更新测试

整理时间：2026-09-11 10:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA；本轮 2026-09-11 10:00 CST，源码 `758bb73bb673998999347ce8d2bb59800950e681`（source_dirty=true，不得外推）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA PASS 写成 Silicon 结论。关联 Feature 与方法仍以公共 IPCM 契约为准。

## 本轮结果

本轮已选参数（无参数）均 PASS。Session `12d611fe-cdff-47d0-96a8-95a4d2246e3b`。

## 方法问题：peer_cancel（已关闭）

09-10 / 09-11 的 Case 前 `peer_cancel` 失败不是本 Case 功能缺陷。正确 Peer 后若再 `start_target`，PEER_RESULT 超时、无 DUT 观测；跳过该复位后本 Case 功能断言通过。流程见 [IP 教训索引](../README.md) 与 [ET6801 IPCM 6.1.1](../../../../../test_case_doc/ipcm/ET6801_ipcm.md)。

## 依据与变化

方法权威：[公共IPCM契约](../../../../../test_case_doc/ipcm/ipcm.md)中的`IPCM_P1_001`；芯片适配见[ET6801 IPCM文档](../../../../../test_case_doc/ipcm/ET6801_ipcm.md)。

- 2026-09-09 12:40 CST：从 run 20260903_191100 提炼方法；当时 PASS。
- 2026-09-10 22:04 CST：34/34 FAIL，合并为同一 `peer_cancel` 问题段。
- 2026-09-11 09:15 CST：正确 IPCM Peer 仍 34 FAIL（PEER_RESULT 超时）；当时同 Pipeline 执行了 start_target。
- 2026-09-11 10:00 CST：对照本轮 Canonical Session（`758bb73bb673998999347ce8d2bb59800950e681`，source_dirty=true）。跳过 start_target 后本 Case PASS；该方法问题对本轮关闭。
