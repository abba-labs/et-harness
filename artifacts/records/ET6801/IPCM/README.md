# ET6801 IPCM Case知识

更新时间：2026-09-11 10:00 CST。

本目录长期保留每Case一份提炼型Markdown，由Agent审阅Canonical事实后维护；脚本只检查与生成导航，不自动编写结论。适用范围、问题、修复依据与未执行边界见各Case。本目录历史PASS不替代当前回归；当前测试结果以运行工作区Canonical Session为准。

本次迁移覆盖IPCM注册表全部13个已注册Case。本目录不表示公共IPCM全部测试目标已实现。

<!-- ET_RECORD_AUTO_BEGIN -->

## Case知识索引

本索引不汇总测试状态；当前测试结果见运行工作区。

- [IPCM_P0_001 — IPCM能力与Mailbox配置读回测试](cases/IPCM_P0_001.md)
- [IPCM_P0_002 — IPCM双Core Manual ACK变长Payload测试](cases/IPCM_P0_002.md)
- [IPCM_P1_001 — IPCM Manual ACK Payload更新测试](cases/IPCM_P1_001.md)
- [IPCM_P1_002 — IPCM Auto ACK触发条件测试](cases/IPCM_P1_002.md)
- [IPCM_P1_003 — IPCM IRQ与Polling状态测试](cases/IPCM_P1_003.md)
- [IPCM_P1_004 — IPCM全Mailbox释放与复用测试](cases/IPCM_P1_004.md)
- [IPCM_P1_005 — IPCM双向双Mailbox通信测试](cases/IPCM_P1_005.md)
- [IPCM_P1_006 — IPCM多Mailbox同时Pending测试](cases/IPCM_P1_006.md)
- [IPCM_P1_007 — IPCM Multi-destination独立释放测试](cases/IPCM_P1_007.md)
- [IPCM_P1_008 — IPCM Auto ACK模式显式ACK测试](cases/IPCM_P1_008.md)
- [IPCM_P2_001 — IPCM Auto Link Manual ACK长Payload测试](cases/IPCM_P2_001.md)
- [IPCM_P2_002 — IPCM Auto ACK Link长Payload测试](cases/IPCM_P2_002.md)
- [IPCM_P2_003 — IPCM同Mailbox连续分段传输测试](cases/IPCM_P2_003.md)

<!-- ET_RECORD_AUTO_END -->

## 教训：ET6801 FPGA IPCM 双核 Peer 后禁止 start_target

检索：HIL / IPCM / 双核 Peer / `et6801_fpga_ipcm` / `ET6801_CORE1_ITCM_IPCM_PEER` / `execute.start_target` / J-Link `r` / `peer_cancel` / PEER_RESULT。

适用条件：仅 ET6801 FPGA IPCM 双核 Peer。Profile `et6801_fpga_ipcm`，Core1 `ET6801_CORE1_ITCM_IPCM_PEER`。不得外推 Silicon，不得外推 SPINLOCK 或其他 Peer。

操作：Peer 部署成功且 Mailbox Ready 后，禁止再对 Core0 执行会复位的 `pipeline.execute.start_target` 或 J-Link `r`。应直接跑 IPCM Formal Case。

违反后果：Core1 Peer 被连带打死 → Case 前 `peer_cancel` / PEER_RESULT 超时 → 34/34 FAIL，无 DUT 功能观测。这不是 IPCM 寄存器功能失败，也不是各 Case 方法缺陷。

对照（不得伪造 PASS；dirty 轮不得写成 Exact-SHA PASS）：

- 2026-09-03：clean `7d0d4a408cdc92f6837d4626b399619d4459ecfe`，`start_target=false`，34/34 PASS。
- 2026-09-11 09:15：同 Peer，Peer 后再 `start_target`，34/34 FAIL（`peer_cancel` / PEER_RESULT 超时）。
- 2026-09-11 10:00：同树跳过 `start_target`，34/34 PASS（source `758bb73bb673998999347ce8d2bb59800950e681`，source_dirty=true）。

权威流程：[ET6801 IPCM 芯片文档 6.1.1](../../../../../test_case_doc/ipcm/ET6801_ipcm.md)。Pipeline 警告与互斥见 `tools/profiles/pipeline/et6801_fpga_ipcm.yaml`。代表性 Case：[IPCM_P0_001](cases/IPCM_P0_001.md)。

## 历史来源与版本

以下为本次提炼依据，不是第二份活动状态：

- 最近一次运行：FPGA Lane 2026-09-11 10:00 CST，Source `758bb73bb673998999347ce8d2bb59800950e681`（dirty），13 Case/34 执行=13 PASS/0 FAIL/0 SKIP。Profile `et6801_fpga_ipcm`，Peer 部署后跳过 `start_target`。
- 历史对照：2026-09-03 clean FPGA（`7d0d4a408cdc92f6837d4626b399619d4459ecfe`）亦 34 PASS，当时同样 `start_target=false`。2026-09-11 09:15 同树在 Peer 后再跑 `start_target` 则 34 FAIL（peer_cancel / PEER_RESULT 超时）。
- **本树证据锚**：Canonical Session 为 `artifacts/records/ET6801/IPCM/current`（session.json + 34 份 result.json）。旧 `artifacts/runs/20260903_191100_603939_ipcm_formal_cases/tests/ipcm/` 仅作历史。
- IPCM为双核通信IP：执行依赖片内Peer Core Ready，P2级链式/分段Case都在双核真实通信上完成。
- 方法权威：[公共IPCM契约](../../../../../test_case_doc/ipcm/ipcm.md)各Case的`ET_CASE_SPEC`；芯片适配见[ET6801 IPCM芯片文档](../../../../../test_case_doc/ipcm/ET6801_ipcm.md)。

## 未闭环问题

- 当前无未闭环 FPGA 功能失败。本轮 34/34 PASS。
- 09-10 / 09-11 的 Case 前 `peer_cancel` 失败已关闭：那是错误 Peer 或 Peer Ready 后再 `start_target` 的部署问题，不是 Case 方法缺口。对照保留；不得外推 Silicon。

## 关键变化

- 2026-09-11 10:00 CST：对照本轮 Canonical Session（`758bb73bb673998999347ce8d2bb59800950e681`，source_dirty=true）。跳过 start_target 后 34 PASS。
- 2026-09-11 09:15 CST：正确 IPCM Peer 仍 34 FAIL（PEER_RESULT 超时）；当时同 Pipeline 执行了 start_target。
- 2026-09-10 22:04 CST：对照当时 Canonical Session（`7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true）更新未闭环问题与适用基线。

- 2026-09-09 12:40 CST：建立IPCM固定Case档案，按R130 §8.1与R500 §6从Canonical Session（run 20260903_191100）与公共契约提炼13个已注册Case知识；未执行任何测试或硬件动作，未修改公共契约与芯片文档状态块。
