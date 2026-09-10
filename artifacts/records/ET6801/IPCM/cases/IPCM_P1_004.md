# IPCM_P1_004 — IPCM全Mailbox释放与复用测试

整理时间：2026-09-10 22:04 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA；本轮 2026-09-10 22:04 CST，源码 `7106a1562269da95d060e2cd756d53eef7e156d4`（source_dirty=true，不得外推）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮失败写成 Silicon 结论。关联 Feature 与方法仍以公共 IPCM 契约为准。

## 问题：peer_cancel 被目标 INTERNAL_ERROR 拒绝，本轮无 DUT 观测

现象：本轮已选参数（`mailbox_0`、`mailbox_1`、`mailbox_2`、`mailbox_3`、`mailbox_4`、`mailbox_5`、`mailbox_6`、`mailbox_7`、`mailbox_8`、`mailbox_9`、`mailbox_10`、`mailbox_11`、`mailbox_12`、`mailbox_13`、`mailbox_14`、`mailbox_15`）均在进入本 Case 刺激前于 `local.peer_cancel(expected_identity=support.peer_identity)` 失败。错误文本（不是根因）：`TargetRejected: target rejected service=0x0109 command=0x0022 instance=0 status=INTERNAL_ERROR`。`evidence_complete=false`，`observations=[]`，没有 Mailbox/能力/Payload 读回。

证据指针：本轮 13 Case / 34 execution 全部同一失败点与同一错误文本；本 Case 全部已选参数均如此。禁止链接 `current/`。

未关闭问题：双核 Peer 会话未能完成 `peer_cancel`，本轮不能判定本 Case 功能本身。不得从 INTERNAL_ERROR 摘要自动发明根因。

适用条件：chip=ET6801，Lane=FPGA（Manifest `target_kind=fpga`），source=`7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，firmware=`et6801-silicon-common-v0.1`，parameter_id=`mailbox_0`、`mailbox_1`、`mailbox_2`、`mailbox_3`、`mailbox_4`、`mailbox_5`、`mailbox_6`、`mailbox_7`、`mailbox_8`、`mailbox_9`、`mailbox_10`、`mailbox_11`、`mailbox_12`、`mailbox_13`、`mailbox_14`、`mailbox_15`。bitstream/设备身份未知。

已试过 / 还缺：本轮未换 IPCM 专用 Peer Profile 复测。`run_config` 注释写明默认双核 Peer，若 IPCM FAIL 再换 `et6801_fpga_ipcm`——这是配置提示，不是已验证根因。还缺：Peer Core 是否 Ready、service `0x0109` command `0x0022` 的目标侧原因、本轮实际加载的 Peer 固件/Profile。未跑到本 Case 的功能断言。

## 历史 PASS 边界

2026-09-03 clean FPGA（源码 `7d0d4a408cdc92f6837d4626b399619d4459ecfe`）曾 PASS。本轮未对照已消失的旧 current 重新确认旧结论；旧 PASS 不得当作本轮已验证。

## 依据与变化

方法权威：[公共IPCM契约](../../../../../test_case_doc/ipcm/ipcm.md)中的`IPCM_P1_004`；芯片适配见[ET6801 IPCM文档](../../../../../test_case_doc/ipcm/ET6801_ipcm.md)。

- 2026-09-09 12:40 CST：从 run 20260903_191100 提炼方法；当时 PASS。
- 2026-09-10 22:04 CST：本轮 34/34 FAIL，合并为同一 `peer_cancel` 问题段；不新开按参数复制的根因段。
