# Knowledge Tiered Reference And Evidence Feedback — 2026-08-26

## Goal

让 Agent 能看到所有相关知识状态，同时不把未验证知识伪装成事实，也不扩大 Context 成本。

## Retrieval

```text
FULL_VALIDATED -> VERIFIED
VALIDATED      -> SUPPORTED
CANDIDATE      -> EXPLORATORY
DEPRECATED     -> HISTORICAL
CONTRADICT     -> DISPUTED overlay
```

默认查询不再隐藏 CANDIDATE/DEPRECATED。Context 采用分层限额与低优先级：可靠知识优先，探索知识最多占少量位置，历史知识最多保留一条；预算不足时先省略探索/历史项。

## Feedback loop

```text
Agent receives routed K-ID with trust tier
→ treats CANDIDATE as hypothesis
→ trusted tool/test records real Evidence
→ Reflection proposes SUPPORT or CONTRADICT for that K-ID
→ Runtime verifies K-ID, Evidence URI and project boundary
→ Verification is appended
→ Policy may promote SUPPORTED claim
→ CONTRADICT keeps the item visible but marks it DISPUTED/BLOCKED
```

Agent owns semantic proposal. Framework owns evidence validation, append-only verification, promotion and blocking.

## Non-goals

- no percentage confidence score;
- no automatic Fact rewrite;
- no automatic deletion on contradiction;
- no forced Knowledge Candidate for every error;
- no unlimited Context expansion.


## Efficiency and claim-version guards

Review handles keep at most three visible paths plus a preserved remaining-file count and a hard length cap. Verification deduplication is scoped to the current Knowledge claim fingerprint, so evidence for an older Fact/Scope does not silently suppress verification of a revised claim.
