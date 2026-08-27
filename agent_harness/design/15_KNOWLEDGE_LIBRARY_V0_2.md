# Knowledge Library v0.2

> 状态：IMPLEMENTATION BASELINE  
> Node 标准：`knowledge-v0.1`  
> Library 标准：`knowledge-library-v0.2`  
> 公共插件：`@agent-harness/knowledge-manager` v0.2.0

## 1. 为什么需要 v0.2

单纯保存 K-Node 无法解决 1 万+ 知识条目下的管理问题。

v0.2 把项目知识库定义成机器图书馆：

```text
TAXONOMY
+ Canonical Knowledge
+ Generated Catalog
+ Machine Index
+ Search API / CLI
```

## 2. Source of Truth

```text
knowledge/TAXONOMY.yaml
knowledge/NNN_*.md
```

生成物：

```text
knowledge/00_INDEX.md
运行时 Machine Index
```

`00_INDEX.md` 每次 reindex 都可以完全覆盖。

## 3. 地址体系

```text
C-ID = 分类号
K-ID = Knowledge 索书号
```

示例：

```text
C010.020.030
K040.010.020
```

标题变化不改变稳定 ID。

## 4. Admission Build

```text
TAXONOMY.yaml
 ↓
C-ID Tree Validation
 ↓
scan NNN_*.md
 ↓
K-ID Tree Validation
 ↓
Category Binding Validation
 ↓
Build indexes
 ↓
source fingerprint
 ↓
generate 00_INDEX.md
 ↓
READY
```

## 5. Machine Index

当前 v0.2 运行时建立：

```text
K-ID Map
Category Map
Keyword Inverted Map
Refs Forward Map
Refs Back Reference Map
```

Status / Tags / Scope 在候选集合上进一步过滤。

长期运行的 Harness 只在 refresh / reindex 时读取 Knowledge Markdown；正常 query 只查内存索引。

## 6. 查询

```text
Known K-ID
→ O(1)

Natural Language
→ Keyword Index
→ Category / Status / Tags filter
→ deterministic ranking
→ Top-N
```

没有关键词索引命中时直接返回空，不退化成全库扫描。

## 7. 分类浏览

```text
getTaxonomy
listCategories
```

分类只用于稳定组织和过滤，不复制 Knowledge。

一个 Knowledge Leaf 只有一个 Primary Category；跨领域信息通过 Tags / Scope / Refs 搜索。

## 8. 自动目录

`00_INDEX.md` 包含：

```text
生成标记
source fingerprint
状态统计
分类树 + 数量
Knowledge File + Node 数量
```

它用于 Agent 快速理解“图书馆长什么样”，不作为 canonical source。

## 9. CLI

```text
knowledge tree
knowledge search
knowledge get
knowledge related
knowledge validate
knowledge reindex
```

CLI 与 Cordis Service 共用 `KnowledgeManagerEngine`。

## 10. 兼容策略

```text
存在 TAXONOMY.yaml
→ library-v0.2

不存在 TAXONOMY.yaml
→ legacy-v0.1
```

因此公共插件可以先升级，项目随后逐个显式迁移，不会要求 ET-TOOL 在本阶段提前定义分类。

## 11. 当前不解决的问题

v0.2 本阶段只解决图书馆结构和检索效率，不提前混入：

```text
Source Registry
Confidence Model
Verification Ledger
Knowledge Contribution Governance
```

这些需要在图书馆结构稳定后单独设计。
