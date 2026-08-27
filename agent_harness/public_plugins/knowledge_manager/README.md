# Public Knowledge Manager

公共 `Knowledge Manager v0.2`。

## 两层标准

```text
knowledge-v0.1
= Knowledge Node 基础格式与稳定 K-ID

knowledge-library-v0.2
= 分类树、自动目录、机器索引、检索和轻量写治理
```

## 两种 Library Scope

```text
Global Knowledge
= Harness 级共享知识库
= 不属于任何 Project Plugin

Project Knowledge
= 单项目私有知识库
= 随 Project Plugin 注册 / 卸载
```

标准 Harness 公共库位于：

```text
agent_harness/global_knowledge/
```

Knowledge Manager 通过 `AGENT_HARNESS_GLOBAL_KNOWLEDGE_ROOT` 或显式 `mountGlobalLibrary()` 挂载它；公共知识数据不存放在插件代码目录。

知识默认归属规则：

```text
离开当前项目仍成立 -> Global Candidate
只描述项目实现 / 路径 / 决策 / 特有限制 -> Project Candidate
```

完整引用：

```text
knowledge://global/K...
knowledge://project/<project-id>/K...
```

## Source of Truth

每个 Library 独立维护：

```text
TAXONOMY.yaml
SOURCES.yaml            # Source Registry，可在首条 Source 前不存在
VERIFICATIONS.jsonl     # append-only，可在首条 Verification 前不存在
NNN_*.md
```

`00_INDEX.md` 由插件自动生成，禁止人工维护。

## Source / Evidence / Verification

```text
Knowledge    = 当前认知
Source       = 参考依据
Evidence     = 实际发生的运行事实
Verification = Source / Evidence 对 Knowledge 的 SUPPORT / CONTRADICT 关系
```

归属：

```text
Knowledge / Source / Verification -> Knowledge Manager
Evidence / State                  -> Evidence / State Manager
```

Knowledge Manager 只读取 Evidence URI，不复制 Evidence 内容。

地址：

```text
source://global/SRC000001
source://project/<project-id>/SRC000001

evidence://project/<project-id>/EV-...
```

Verification 只有：

```text
SUPPORT
CONTRADICT
```

每条 Verification 自动绑定当时的：

```text
knowledgeFingerprint = sha256(Fact + Scope)
```

Candidate 修改 Fact / Scope 后，旧 Verification 保留历史，但不会继续验证新的 Claim。

## Validation Policy v0.1

Knowledge Manager 包内提供 `knowledgeValidationPolicy` 子服务：

```text
Project:
  document SUPPORT -> VALIDATED
  same-project REAL_TEST PASS -> FULL_VALIDATED

Global:
  2 个 Global document SUPPORT -> VALIDATED
  单 Project REAL_TEST 不得 -> FULL_VALIDATED

当前 Claim 有 CONTRADICT -> BLOCKED
```

Governance Runtime 可以在 8/8 Closure 后调用该 Policy 自动验证新 Candidate。
Promotion 失败只返回 Post-Closure warning，不破坏 CLOSED Turn。

接口：

```text
knowledgeValidationPolicy.evaluate(reference)
knowledgeValidationPolicy.promote(reference)
```

## 公共职责

```text
C-ID Taxonomy 校验
K-ID Knowledge 校验
Global / Project 双 Scope 管理
Global-first + Project-delta Combined Search
Qualified Knowledge URI 解析
Source Registry / Source URI
Verification append-only 记录
Claim Fingerprint
Evidence URI 存在性校验
Validation Policy: INSUFFICIENT / READY / BLOCKED
显式 Candidate -> VALIDATED Promote
自动生成 00_INDEX
K-ID / Category / Keyword / Relation Index
validated-first 检索
受控 Knowledge Candidate 写入
显式重分类 / 废弃
显式 Category 新增 / 改名 / 废弃
写后 validate + reindex
失败自动 rollback
CLI / Harness 共用同一个 Engine / Mutator
```

## 写入原则

```text
新知识固定 CANDIDATE
Contribution 不自动创建分类
Primary Category 只有一个
K-ID 自动分配且保持稳定
VALIDATED Fact 不直接改写
精确重复直接拒绝
不做 LLM 自动合并 / 删除 / 重分类
```

Knowledge Manager 自动写入 `NNN_library.md` 扁平分片；分类语义只由 `TAXONOMY.yaml` 的 C-ID 树表达，避免同时维护两套业务分类树。

## 查询原则

```text
searchGlobalKnowledge   -> Global only
searchKnowledge         -> 当前 Project only（兼容旧 API）
searchKnowledgeCombined -> Global first + Project second
```

默认检索允许召回所有相关状态，并分级标注：

```text
FULL_VALIDATED -> VERIFIED，主要依据
VALIDATED      -> SUPPORTED，带 Scope 使用
CANDIDATE      -> EXPLORATORY，只能作为假设、排查方向和测试目标
DEPRECATED     -> HISTORICAL，只能作为历史与反例
当前 Claim 有 CONTRADICT -> DISPUTED，不得静默当作可信事实
```

为了保持效率，Context 仍受预算控制：可靠知识优先保留，探索/历史知识使用低优先级并限制数量；被省略的项目仍可通过 K-ID 或搜索继续展开。

Combined Search 只做召回和 Scope 标记，不替 Agent 自动解决 Global / Project 语义冲突。

## 不负责

```text
自动判断一条知识属于 Global 还是 Project
自动跨库复制 Knowledge
自动跨库语义去重
自动解决 Global / Project 冲突
由 Knowledge Manager 单独自动 Promote Knowledge（Governance Runtime 可在 Closure 后依据 Policy 自动晋级）
自动根据 SUPPORT / CONTRADICT 改写 Fact
百分比置信度
LLM 自动可信判断
用生成索引替代 canonical Knowledge
自动推断和重构分类树
```

## CLI

查询：

```text
knowledge tree
knowledge search
knowledge get
knowledge related
knowledge validate
knowledge reindex
```

写入：

```text
knowledge add
knowledge update-candidate
knowledge reclassify
knowledge deprecate
knowledge category-add
knowledge category-rename
knowledge category-deprecate
```

项目接口见 `PROJECT_INTERFACE.md`，Global 接口见 `GLOBAL_INTERFACE.md`，Scope 规范见 `08_KNOWLEDGE_SCOPE_STANDARD_V0_2.md`，Source / Verification 规范见 `09_KNOWLEDGE_SOURCE_VERIFICATION_STANDARD_V0_1.md`，Validation Policy 见 `10_KNOWLEDGE_VALIDATION_POLICY_STANDARD_V0_1.md`。
