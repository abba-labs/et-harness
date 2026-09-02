# ET Harness Validation Analysis Archive

本目录保存每一轮真实验证结束后的 **Architecture Owner 分析**。

它与 `agent_harness/test_campaigns/**/evidence/` 的职责严格分离：

- `test_campaigns/**/evidence/`：Codex / Test Executor 产生的机械测试事实、原始日志、状态差异、模块矩阵和 Final Report；
- `validation_analysis/`：基于已冻结 Evidence 和对应源码进行的根因分析、缺陷来源判定、风险预测、修复决策与非回归边界；
- 产品代码、测试 Evidence 与分析结论不得互相冒充。

## 1. 核心原则

### 1.1 Evidence first

所有结论必须能够回指：

1. 精确测试 SHA；
2. 精确 Evidence SHA / Evidence 文件；
3. first failing boundary；
4. 对应产品 Owner / 源码；
5. 若是推断，必须明确标记为 `HYPOTHESIS` / `PREDICTED_NOT_OBSERVED`，不能写成已证实事实。

证据优先级保持：

`mechanical runtime/event/state evidence > exact source > deterministic unit/integration test > Agent/Test Executor narrative`

### 1.2 不允许把“新发现”自动等同于“新回归”

每个问题必须先分类：

- `PRE_EXISTING_ROOT_DEFECT`：缺陷在本轮修改前已经存在；
- `INCOMPLETE_PREVIOUS_FIX`：上一轮针对同一能力做了修复，但没有修到根；
- `NEW_REGRESSION`：有机械证据证明旧基线正常、本轮修改后变坏；
- `NEWLY_TESTED_CAPABILITY_GAP`：以前从未覆盖该能力，本轮首次深入测试发现缺口；
- `PROJECT_CONTENT_GAP`：项目/SDK/Rule/Knowledge/Requirement/Capability 内容问题，不属于公共 Framework；
- `OBSERVABILITY_GAP`：行为可能正确，但现有公共/持久证据不足以证明；
- `TEST_GAP`：之前测试模型本身没有覆盖真实组合边界。

只有 `NEW_REGRESSION` 才能称为“本轮修复引入的新问题”。

### 1.3 根因未隔离，不允许直接修代码

如果一个现象存在多个可解释根因，必须先设计 **最小判别测试**。在机械证据能够区分候选原因前，不允许凭感觉修改多个模块。

### 1.4 先修状态机根因，再修表面症状

同一根因可能在多个模块上表现为多个 FAIL。分析时必须先归并到最小 Owner/状态转换，避免按模块计数逐个打补丁。

### 1.5 修复必须轻量、单 Owner、可回滚

优先：

- 复用现有 Runtime / Ledger / Event Store / Context Store；
- 修正已有状态转换和调用顺序；
- 增加精确 regression / composed integration test；
- 不新增第二套状态系统；
- 不新增 watcher / daemon / polling；
- 不扩大公共 MCP tool surface；
- 不以“多加一层兼容补丁”替代根因修复。

## 2. 每轮分析固定流程

1. **Evidence Inventory**：梳理所有 PASS / FAIL / NOT_EXECUTED / OBSERVABILITY_GAP、状态差异和负控；
2. **Trace to Code**：从 first failing boundary 映射到对应源码、状态机、Owner 和历史 commit；
3. **Defect Provenance**：判定旧缺陷、修复不完整、新回归、新能力缺口或项目内容缺口；
4. **Test-gap Analysis**：解释为什么上一轮测试没有抓到本轮问题；
5. **Counterfactual / Predictive Simulation**：沿当前代码和 Codex 的真实测试习惯，模拟下一层高概率故障；
6. **Root-cause Grouping**：把多个模块症状归并为最少的根因修复线；
7. **Repair Decision**：判断是否必须修、修哪个 Owner、最小方案是什么、哪些方案禁止；
8. **Risk Analysis**：分析修复会不会破坏已经 PASS 的 Trust/Scope/Closure/Environment 等能力；
9. **Acceptance Contract**：先写修复验收与非回归测试，再允许改产品；
10. **Freeze**：记录精确分析基线、Evidence SHA、最终结论与 Remaining Unknowns。

## 3. 每轮目录命名

```text
rounds/YYYY-MM-DD_<scope>_<campaign>/
└─ FINAL_ANALYSIS.md
```

`FINAL_ANALYSIS.md` 必须包含：

- Frozen identities；
- Codex Evidence map；
- Proven / unproven boundaries；
- Defect provenance matrix；
- Root-cause analysis；
- Why previous tests missed it；
- Predicted next failures；
- Repair decision matrix；
- Minimal repair architecture；
- Repair risks；
- Required fix acceptance；
- Required non-regression；
- Do-not-fix / defer list；
- Remaining unknowns。

## 4. 修复可靠性判定

只有同时满足以下条件，方案才允许进入实现：

1. first failing boundary 可机械复现；
2. 根因已由源码和 Evidence 共同支持，或已通过判别测试隔离；
3. 修改限定在真实 Owner，不跨层补丁；
4. 状态转换定义明确，失败路径也明确；
5. 幂等性、重试、异常中断、跨进程/跨任务边界已考虑；
6. 不破坏 append-only Evidence / Trust Boundary；
7. 不创建第二套 canonical state；
8. regression test 覆盖“原问题”；
9. composed integration test 覆盖“真实模块组合”；
10. non-regression 重跑上一轮已 PASS 能力；
11. 真实 Project Task 再执行；
12. State diff 证明无新增长期污染。

如果任一项无法证明，则结论只能是 `REPAIR_NOT_YET_PROVEN`，不能宣布“修复方案可靠”。
