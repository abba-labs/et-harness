# Knowledge Library Mutation Standard v0.2

> 标准：`knowledge-library-v0.2` 的写治理补充。  
> 目标：**知识可以持续增长，但分类、地址和索引不能随增长失控。**

## 1. 六条硬规则

```text
1. Canonical Knowledge 只能通过 Knowledge Manager 修改。
2. 00_INDEX.md 永远只生成，禁止手改。
3. 分类不会因为一次知识贡献自动创建；只能显式修改 TAXONOMY。
4. 新知识必须挂到已存在且 ACTIVE 的 C-ID。
5. 每次 canonical 修改后必须 validate + reindex；失败整次回滚。
6. v0.2 只做确定性精确去重，不用不透明模型自动合并/删除知识。
```

## 2. 分类与存储解耦

```text
C-ID / TAXONOMY
= 知识的语义分类树

K-ID / NNN_library.md
= 知识的稳定存储地址
```

公共插件不要求 Knowledge File 与业务分类一一对应。

这样知识重新分类时：

```text
只修改 Category: Cxxx
K-ID 不变
文件不搬迁
引用不失效
```

## 3. Knowledge Manager Managed Shard

通过 Knowledge Manager 新增的知识写入自动管理分片：

```text
001_library.md
002_library.md
003_library.md
...
```

每个分片使用扁平地址：

```markdown
# [K001] Managed Knowledge Shard

## [K001.001] <Knowledge>
...

## [K001.002] <Knowledge>
...
```

要求：

```text
文件三位编号自动分配
Leaf 三位编号自动分配
项目 / Agent 不手工指定新 K-ID
一个 managed shard 最多 999 个直接 Knowledge Leaf
满后自动创建下一分片
```

已有项目自定义 Knowledge File 仍可读取；Knowledge Manager 的自动写入只写 managed shard。

## 4. 新知识只进入 CANDIDATE

Agent 阅读资料、代码或任务后贡献新知识时：

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

Knowledge Manager 自动：

```text
校验 ACTIVE Category
精确 Fact 去重
分配 K-ID
写入 managed shard
validate
reindex
生成 00_INDEX
```

新贡献固定：

```text
Status: CANDIDATE
```

本标准不允许“读完资料直接写成 VALIDATED”。

## 5. 轻量去重

v0.2 只执行确定性去重：

```text
normalize(Fact) 完全相同
+
现有知识不是 DEPRECATED
→ REJECT，返回已有 K-ID
```

不做：

```text
自动语义合并
LLM 相似度自动删除
自动覆盖旧 Knowledge
```

复杂语义重复只作为后续治理问题。

## 6. 修改规则

### CANDIDATE 内容更新

允许修改：

```text
Title
Fact
Scope
Tags
Refs
Provenance
```

K-ID 不变。

### VALIDATED 内容

v0.2 不允许直接改 Fact。

如果认为 VALIDATED Knowledge 错误：

```text
提交新的 CANDIDATE
→ 后续验证
→ 再决定替换 / 废弃旧知识
```

避免静默改写已被其他 Agent 信任的事实。

### Reclassify

允许：

```text
Category: Cold → Cnew
```

条件：

```text
Cnew 存在且 ACTIVE
```

只改分类，不改 K-ID，不搬文件。

### Deprecate

允许显式把 Knowledge 改为：

```text
Status: DEPRECATED
```

不删除 K-ID，不复用 ID。

## 7. 分类树修改

分类只能通过 Knowledge Manager 显式操作：

```text
category add
category rename
category deprecate
```

不允许 Knowledge Contribution 自动创建 Category。

### Add

```text
父 C-ID（或 root）
+ title
+ aliases / summary（可选）
```

Knowledge Manager 分配新的稳定 C-ID。

### Rename

只修改：

```text
title
aliases
summary
```

C-ID 不变。

### Deprecate

只有该分类整棵子树不存在非 DEPRECATED Knowledge 时才允许。

### 不支持 Move

v0.2 不提供 Category Move。

原因：C-ID 编码父子地址，Move 会导致大规模 ID 重写。

需要调整分类时使用：

```text
新建目标 Category
→ reclassify Knowledge
→ deprecate 旧 Category
```

这是更慢但更可靠的显式过程。

## 8. 单次写事务

任何 canonical 修改：

```text
Precheck
  ↓
备份受影响 canonical file
  ↓
原子写入
  ↓
完整 validate + reindex
  ↓
生成 00_INDEX
  ↓
PASS → commit result
FAIL → rollback canonical file → reindex old state
```

禁止留下：

```text
正文已改但 Index 未更新
Taxonomy 已改但 Knowledge 不可路由
半写入 Markdown / YAML
```

## 9. 最小公共 API

```text
submitKnowledgeCandidate(...)
updateKnowledgeCandidate(...)
reclassifyKnowledge(...)
deprecateKnowledge(...)

addCategory(...)
renameCategory(...)
deprecateCategory(...)

reindexProject(...)
validateProjectLibrary(...)
```

v0.2 不增加复杂审批流、自动分类、向量写治理或多阶段事务系统。

核心目标只有：

> **每次写入都简单、可预测、可回滚，知识越多仍然保持一个 canonical 条目 + 一个稳定分类 + 一个稳定地址。**
