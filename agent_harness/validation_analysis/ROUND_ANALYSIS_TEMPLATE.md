# <Round Title> — Final Analysis

## 0. Frozen Identity

- Canonical development branch:
- Tested source SHA:
- Evidence branch:
- Evidence SHA:
- Runtime release:
- Gateway PID / Environment:
- Product modifications during measurement: YES / NO
- Hardware/HIL executed: YES / NO / NOT_EXECUTED

## 1. Executive Conclusion

一句话结论：

> <单次链 / 连续治理 / 恢复 / 数据质量的总体判定>

### Category status

| Category | Result | Summary |
|---|---|---|
| CHAIN_EXECUTION | | |
| MODULE_TRIGGER_CORRECTNESS | | |
| MODULE_BEHAVIOR_CORRECTNESS | | |
| GOVERNANCE_CONTENT_QUALITY | | |
| CONTEXT_QUALITY | | |
| KNOWLEDGE_QUALITY | | |
| STATE_PERSISTENCE | | |
| CROSS_TASK_CONSUMPTION | | |
| TRUST_BOUNDARY | | |
| CLOSURE_AND_RETRY | | |
| REGRESSION | | |
| LONG_TERM_POLLUTION_RISK | | |

## 2. Evidence Inventory

只记录 Codex 已机械观测的事实，不做原因推断。

| Evidence ID | Scenario | Observed fact | Status | Evidence file/ref |
|---|---|---|---|---|

## 3. Evidence → Code Trace

| Evidence ID | First failing boundary | Owner | Exact source/function | What source proves | Confidence |
|---|---|---|---|---|---|

`Confidence`：`PROVEN` / `STRONG` / `HYPOTHESIS`。

## 4. Defect Provenance Matrix

| Defect | Classification | First known present SHA | Was owner modified last round? | Old baseline proven good? | Regression verdict |
|---|---|---|---|---|---|

Classification 必须使用：

- PRE_EXISTING_ROOT_DEFECT
- INCOMPLETE_PREVIOUS_FIX
- NEW_REGRESSION
- NEWLY_TESTED_CAPABILITY_GAP
- PROJECT_CONTENT_GAP
- OBSERVABILITY_GAP
- TEST_GAP

## 5. Why Previous Tests Missed It

逐项回答：

1. 上一轮测试测了什么；
2. 没测什么组合边界；
3. 是否使用 synthetic fixture 代替真实组合；
4. 是否只检查返回值，没有检查 durable state；
5. 是否只执行一次，没有测试 retry/replay；
6. 是否只测 happy path，没有故障注入；
7. 如何把本轮真实失败固化成永久 regression。

## 6. Root-Cause Grouping

不要按 FAIL 模块数量修。

| Repair Line | Symptoms covered | Root owner | Root transition / invariant |
|---|---|---|---|

## 7. Predictive Simulation

所有未实际执行的结论必须标记 `PREDICTED_NOT_OBSERVED`。

| Prediction | Basis in current Evidence/source | Probability | Impact | Minimal discriminating test |
|---|---|---|---|---|

必须至少覆盖：

- 对称状态：FAIL→PASS 与 PASS→mutation；
- retry / replay；
- failure between two durable writes；
- process restart / rehydrate；
- cross-task related / unrelated；
- Context budget saturation；
- state growth / long-term pollution；
- repair-induced risk。

## 8. Repair Decision Matrix

| Problem | Must repair? | Proposed owner | Minimal design | Why lightweight | Main risk | Decision |
|---|---|---|---|---|---|---|

Decision：`REPAIR_NOW` / `DEFER` / `OBSERVE_FIRST` / `PROJECT_OWNER`。

## 9. Repair Reliability Proof

每条 `REPAIR_NOW` 必须回答：

1. 为什么这个方案真正打到根因；
2. 为什么不是 workaround；
3. 为什么不需要新 Store / 新 daemon / 新 public tool；
4. 状态转换如何定义；
5. 异常路径如何收尾；
6. 幂等性如何保证；
7. 历史 Evidence 如何保留；
8. 哪些旧 PASS 能力最容易被破坏；
9. 如何机械证明没有破坏；
10. 如果不能证明，先做什么判别测试。

## 10. Fix Acceptance

只验证本轮目标修复：

- A1 ...
- A2 ...

## 11. Non-Regression Contract

必须重跑上一轮已 PASS 的稳定能力，例如：

- fixed Machine Environment；
- exact 8 MCP tools；
- Project Admission / TaskIntent fail-closed；
- Required Read trust；
- WRITE_SCOPE；
- forged validation rejection；
- premature completion block；
- Supervisor happy path；
- Reflection；
- 8-module one-shot Closure；
- Knowledge no-pollution negative boundary。

## 12. Do Not Fix In This Round

明确列出项目内容问题、纯观测优化、尚未隔离根因的问题，防止修复扩散。

## 13. Remaining Unknowns

所有没有机械证据支持的问题必须保留在这里，不能藏进 PASS。

## 14. Final Repair Readiness

- `REPAIR_READY`
- `REPAIR_NOT_YET_PROVEN`
- `ANALYSIS_BLOCKED`

并说明原因。
