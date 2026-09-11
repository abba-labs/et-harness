# IPCM_P0_001 — IPCM能力与Mailbox配置读回测试

整理时间：2026-09-11 10:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA；本轮 2026-09-11 10:00 CST，源码 `758bb73bb673998999347ce8d2bb59800950e681`（source_dirty=true，不得外推）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA PASS 写成 Silicon 结论。关联 Feature 与方法仍以公共 IPCM 契约为准。

## 本轮结果

本轮已选参数（无参数）均 PASS。Profile `et6801_fpga_ipcm`，Core1 `ET6801_CORE1_ITCM_IPCM_PEER`。Peer 部署成功后未再执行 `execute.start_target` / J-Link `r`。跑前 Mailbox magic=`0x45544331`、state=1、core_index=2、heartbeat 非 0 且相对部署后继续递增。HELLO 成功，service 0x0109 在册。Session `12d611fe-cdff-47d0-96a8-95a4d2246e3b`。本 IP 34 execution 全 PASS。

## 方法问题：peer_cancel（已关闭）

09-10 / 09-11 的 Case 前 `peer_cancel` 失败不是本 Case 功能缺陷。

- 2026-09-10：错误 Peer，`peer_cancel` INTERNAL_ERROR 0x0022，无 DUT 观测。
- 2026-09-11 09:15：正确 IPCM Peer 部署且 Mailbox Ready 后再跑 `start_target` / J-Link `r`，34/34 倒在 `peer_cancel` 的 PEER_RESULT（0x0021）超时。
- 2026-09-11 10:00：同树只跳过该复位步骤后，本 Case 功能断言通过。

这是部署顺序对照，不是对 J-Link reset 的寄存器级根因证明，也不得外推 Silicon。正确流程见 [IP 教训索引](../README.md) 与 [ET6801 IPCM 6.1.1](../../../../../test_case_doc/ipcm/ET6801_ipcm.md)。

## 历史边界

- 2026-09-03 clean FPGA（`7d0d4a408cdc92f6837d4626b399619d4459ecfe`）PASS，当时 `start_target=false`。

## 依据与变化

方法权威：[公共IPCM契约](../../../../../test_case_doc/ipcm/ipcm.md)中的`IPCM_P0_001`；芯片适配见[ET6801 IPCM文档](../../../../../test_case_doc/ipcm/ET6801_ipcm.md)。

- 2026-09-09 12:40 CST：从 run 20260903_191100 提炼方法；当时 PASS。
- 2026-09-10 22:04 CST：34/34 FAIL，合并为同一 `peer_cancel` 问题段。
- 2026-09-11 09:15 CST：正确 IPCM Peer 仍 34 FAIL（PEER_RESULT 超时）；当时同 Pipeline 执行了 start_target。
- 2026-09-11 10:00 CST：对照本轮 Canonical Session（`758bb73bb673998999347ce8d2bb59800950e681`，source_dirty=true）。跳过 start_target 后本 Case PASS；该方法问题对本轮关闭。
