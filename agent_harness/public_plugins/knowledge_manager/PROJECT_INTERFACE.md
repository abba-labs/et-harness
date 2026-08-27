# Knowledge Manager Project Interface v0.2

> Knowledge Node 标准：`knowledge-v0.1`  
> Library 标准：`knowledge-library-v0.2`  
> 写治理：`Knowledge Library Mutation Standard v0.2`

## 1. Source of Truth

```text
knowledge/
├─ TAXONOMY.yaml
├─ NNN_*.md
└─ 00_INDEX.md   # generated
```

Canonical：

```text
TAXONOMY.yaml
NNN_*.md
```

Generated：

```text
00_INDEX.md
Machine Index
```

`00_INDEX.md` 禁止人工和 Agent 手改。

Canonical 内容也应通过 Knowledge Manager API / CLI 修改，避免绕过校验、回滚和 reindex。

## 2. 分类树 TAXONOMY

项目自己决定有哪些分类；公共插件只规定稳定树结构。

```yaml
standard: knowledge-library-v0.2
categories:
  - id: C010
    title: <项目定义>
    status: ACTIVE
    aliases: []
    children:
      - id: C010.010
        title: <项目定义>
        status: ACTIVE
```

C-ID：

```text
C010
C010.020
C010.020.030
```

要求：

```text
每级固定三位
父子 ID 与树结构一致
ID 稳定
标题可改
DEPRECATED ID 不复用
```

Knowledge Contribution **不得自动创建分类**。

分类修改只有：

```text
category add
category rename
category deprecate
```

v0.2 不支持 category move。

## 3. Knowledge 与分类解耦

```text
C-ID = 语义分类地址
K-ID = Knowledge 稳定地址
```

一条 Knowledge 只有一个 Primary Category：

```text
Category: C010.020
```

重分类：

```text
只修改 Category
K-ID 不变
文件地址不变
Refs 不失效
```

禁止为了多分类复制 Knowledge；跨分类发现使用 Tags / Scope / Refs / Search Index。

## 4. Knowledge Manager Managed Shard

通过公共写 API 新增的 Knowledge 自动进入管理分片：

```text
001_library.md
002_library.md
...
```

内部使用扁平稳定地址：

```markdown
# [K001] Managed Knowledge Shard K001

## [K001.001] <Knowledge>
...

## [K001.002] <Knowledge>
...
```

文件和 Leaf 编号由 Knowledge Manager 自动分配。

项目 / Agent 不需要为了新增知识设计新文件，也不手工分配新 K-ID。

已有自定义 Knowledge File 可以继续读取；自动写 API 只修改 Knowledge Manager 自己管理的 shard。

## 5. Knowledge Candidate

AI 阅读资料、代码或任务后贡献知识时调用：

```text
submitKnowledgeCandidate
```

最少提供：

```text
Category
Title
Fact
Provenance
```

可选：

```text
Scope
Tags
Refs
```

新贡献固定：

```text
Status: CANDIDATE
```

禁止“读完资料直接写成 VALIDATED”。

## 6. 轻量去重

写入前执行确定性去重：

```text
normalize(Fact) 完全相同
+
已有 Knowledge != DEPRECATED
→ REJECT
```

v0.2 不使用 LLM / embedding 自动合并、覆盖或删除 Knowledge。

## 7. 修改边界

### Candidate

Knowledge Manager 管理的 CANDIDATE 可以直接更新：

```text
Title
Fact
Provenance
Scope
Tags
Refs
```

K-ID 不变。

### Validated

v0.2 禁止直接修改 VALIDATED Fact。

认为已有知识错误时应：

```text
提交新 Candidate
→ 后续验证
→ 再决定替换 / 废弃旧 Knowledge
```

### Reclassify

允许对 Knowledge 修改 Category，只能指向已有 ACTIVE C-ID。

### Deprecate

Knowledge 可以显式变为：

```text
DEPRECATED
```

不删除 K-ID，不复用 K-ID。

## 8. 分类修改边界

### Add

显式提供：

```text
parent C-ID（可选）
title
aliases / summary（可选）
```

C-ID 由 Knowledge Manager 分配。

### Rename

只修改：

```text
title
aliases
summary
```

C-ID 不变。

### Deprecate

只有该分类子树中：

```text
没有 ACTIVE 子分类
没有非 DEPRECATED Knowledge
```

才允许废弃。

需要“移动分类”时使用：

```text
新建目标分类
→ reclassify Knowledge
→ 废弃旧分类
```

## 9. 每次写入都是小事务

```text
Precheck
 ↓
备份受影响 canonical file
 ↓
atomic write
 ↓
validate + reindex
 ↓
regenerate 00_INDEX
 ↓
PASS
```

失败：

```text
rollback canonical file
→ reindex old state
→ 抛出原始错误
```

禁止出现正文、Taxonomy 和 Index 互相不同步的半状态。

## 10. Machine Index

Admission / Reindex 自动建立：

```text
ID Index
Category Index
Keyword Inverted Index
Scope / Tag filter
Relation Index
Back Reference Index
```

运行时自然语言查询禁止默认扫描全部 Markdown。

## 11. 查询 API

```text
refreshProject(projectId)
reindexProject(projectId)
validateProjectLibrary(projectId)
getTaxonomy(projectId)
listCategories(projectId, parentId?)
getLibraryStats(projectId)
searchKnowledge(request)
getNode(projectId, knowledgeId)
getRelated(projectId, knowledgeId)
```

默认自然语言查询：

```text
VALIDATED only
```

## 12. 写 API

```text
submitKnowledgeCandidate(projectId, input)
updateKnowledgeCandidate(projectId, K-ID, update)
reclassifyKnowledge(projectId, K-ID, C-ID)
deprecateKnowledge(projectId, K-ID)

addCategory(projectId, input)
renameCategory(projectId, C-ID, update)
deprecateCategory(projectId, C-ID)
```

## 13. CLI

```text
knowledge tree
knowledge search
knowledge get
knowledge related
knowledge validate
knowledge reindex

knowledge add
knowledge update-candidate
knowledge reclassify
knowledge deprecate

knowledge category-add
knowledge category-rename
knowledge category-deprecate
```

CLI 与 Harness Service 必须复用同一 Engine / Mutator。

## 14. 核心原则

```text
分类显式
地址稳定
单条 canonical
新知识先 Candidate
Validated 不静默改写
索引自动生成
写失败必回滚
```

目标不是做复杂 CMS，而是保证：

> **知识越积越多，但库结构不会因为 Agent 持续贡献而越来越乱。**
