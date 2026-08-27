# Agent Harness P0 / P1 Minimal Hardening — 2026-08-26

> 本文件是 `20260826_HARNESS_CURRENT_STATE.md` 和
> `20260826_TEST_STRATEGY_AND_RESULTS.md` 的后续增量 Handoff。

## 冻结目标

Harness 优先提升 Agent 工作效率，只修复会造成以下结果的真实漏洞：

- Agent 绕过 Framework 直接执行；
- Project 经验污染 Global Knowledge；
- Evidence / Knowledge Manager 被 Agent 直接写入；
- Turn / Closure 状态因后处理失败而不一致。

不建设复杂零信任沙箱，也不强制每次错误生成 Knowledge Candidate。

## 本轮修复

1. Project REAL_TEST 只能把 Project Knowledge 晋级 `FULL_VALIDATED`；单个 Project
   Evidence 不得把 Global Knowledge 晋级 `FULL_VALIDATED`。
2. Governed Tool Gateway 改为内部注册 raw executor；模型调用时只传 invocation。
3. `recordEvidence`、Knowledge Verification / Promotion 等 Framework mutation API
   禁止注册为 Agent-facing Tool。
4. Turn 8/8 Closure 完成后先固定 `CLOSED`；Knowledge Promotion 失败只产生
   `knowledgePromotionWarnings`。
5. Round A 的高风险错误验收改为必须触发 `CHECK + EVIDENCE_CHECK`，不再要求
   每次强制创建 Candidate。
6. Round A / Round B 脚本增加相关包单元测试。
7. 同步 Knowledge Validation、Scope、Source Verification 和 Runtime 接口文档。

## 明确暂缓

- 多项目 empirical quorum；
- Evidence Producer 签名或 Permit；
- 完整 Runtime State Store；
- 自动 Knowledge Scope Arbiter；
- 每个 Tool Error 强制 Knowledge Capture。

## 验证

Apply / focused regression run: `32951278309`。

本文件只在 build、unit tests、Round A 和 Round B 全部通过后进入分支。
