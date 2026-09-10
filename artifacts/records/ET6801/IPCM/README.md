# ET6801 IPCM Case知识

更新时间：2026-09-10 22:04 CST。

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

## 历史来源与版本

以下为本次提炼依据，不是第二份活动状态：

- 最近一次运行：FPGA Lane 2026-09-03 19:11 CST，Source `7d0d4a408cdc92f6837d4626b399619d4459ecfe`（clean），13 Case/34 执行=13 PASS/0 FAIL/0 SKIP（状态块更新 2026-09-03 19:15 CST）。同日早前一轮（19:08）6执行亦PASS，为子集冒烟。
- **本树证据锚在仓库内**：Canonical Session为`artifacts/runs/20260903_191100_603939_ipcm_formal_cases/tests/ipcm/`（session.json + 34份cases/<id>/result.json）。该run属删除保留集——清理runs前须先评估本链接。
- IPCM为双核通信IP：执行依赖片内Peer Core Ready，P2级链式/分段Case都在双核真实通信上完成。
- 方法权威：[公共IPCM契约](../../../../../test_case_doc/ipcm/ipcm.md)各Case的`ET_CASE_SPEC`；芯片适配见[ET6801 IPCM芯片文档](../../../../../test_case_doc/ipcm/ET6801_ipcm.md)。

## 未闭环问题

- 2026-09-10 22:04 CST 本轮 13 Case / 34 execution 全部 FAIL：`peer_cancel` 被目标 `service=0x0109 command=0x0022 status=INTERNAL_ERROR` 拒绝，无 DUT 观测。见各 Case 同一问题段。历史 2026-09-03 PASS 不得当作本轮已验证。

## 关键变化

- 2026-09-10 22:04 CST：对照本轮 Canonical Session（`7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true）更新未闭环问题与适用基线。

- 2026-09-09 12:40 CST：建立IPCM固定Case档案，按R130 §8.1与R500 §6从Canonical Session（run 20260903_191100）与公共契约提炼13个已注册Case知识；未执行任何测试或硬件动作，未修改公共契约与芯片文档状态块。
