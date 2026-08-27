# Project Knowledge Library Standard v0.2

> 标准 ID：`knowledge-library-v0.2`  
> Knowledge Node 标准：继续使用 `knowledge-v0.1` 的稳定 K-ID / Status / Fact / Provenance 基础字段。  
> 定位：定义项目知识库如何分类、索引、检索和自动生成目录；不规定项目具体有哪些知识类别。

## 1. 设计目标

项目知识库必须在 1 万乃至更多 Knowledge Node 下仍然满足：

```text
不全文遍历
稳定地址
分类清晰
索引可重建
查询可解释
正文是唯一事实源
```

公共 Knowledge Manager 只规定图书馆机制；项目自行定义分类内容。

---

## 2. Source of Truth

v0.2 中只有以下内容属于项目知识库的 canonical source：

```text
knowledge/TAXONOMY.yaml
knowledge/NNN_*.md
```

以下全部是生成物：

```text
knowledge/00_INDEX.md
Machine Search Index
Category Index
Keyword Index
Relation Index
```

生成物必须可以全部删除并由脚本完整重建。

`00_INDEX.md` 禁止人工和 Agent 手工维护。

---

## 3. 分类树 `TAXONOMY.yaml`

项目必须定义稳定分类树：

```yaml
standard: knowledge-library-v0.2
categories:
  - id: C010
    title: <项目定义>
    aliases: [<可选检索词>]
    summary: <一句话，可选>
    children:
      - id: C010.010
        title: <项目定义>
        aliases: []
```

公共层不规定：

```text
C010 是什么
项目有几个一级分类
分类叫“芯片 / 工具 / 调试 / 验证”还是其他名称
```

这些全部由项目决定。

---

## 4. Classification ID

分类地址统一使用 `C-ID`：

```text
C010
C010.020
C010.020.030
```

要求：

```text
每级固定三位编号
同项目唯一
父子 ID 必须与树结构一致
标题可以修改，C-ID 不随标题变化
已废弃 C-ID 不允许复用给新的分类语义
```

分类 ID 只表达稳定地址，不编码业务语义。

---

## 5. Knowledge Leaf 必须挂到分类树

启用 `knowledge-library-v0.2` 时，每个 Knowledge Leaf 除 `knowledge-v0.1` 基础字段外必须显式提供：

```text
Category: <C-ID>
```

推荐：

```text
Tags: [tag-a, tag-b]
```

示例：

```markdown
### [K030.020.010] <短标题>

Status: VALIDATED
Category: C010.020.030
Fact: <短、明确、可复用的知识>
Scope: <可选>
Provenance: <来源>
Tags: [<可选>]
Refs: [<可选稳定 ID>]
```

规则：

```text
每条 Knowledge Leaf 只有一个 Primary Category
同一 Knowledge 不得为了多分类而复制正文
跨分类检索通过 Tags / Scope / Refs / Search Index 实现
```

---

## 6. `00_INDEX.md` 是生成目录

`knowledge/00_INDEX.md` 由 Knowledge Manager 自动生成。

必须携带生成标记：

```yaml
---
interface: project-resource-index-v0.1
resource: knowledge
standard: knowledge-v0.1
generated: true
generator: knowledge-manager-v0.2
source_fingerprint: <hash>
files: [...]
---
```

正文用于 Agent 快速浏览知识库：

```text
分类树
各分类 Knowledge 数量
各 Knowledge File 数量
状态统计
```

任何人工修改都不是 canonical 修改；下一次 reindex 可以覆盖。

---

## 7. 自动机器索引

Knowledge Manager 在 Admission / Reindex 阶段从 `TAXONOMY.yaml + Knowledge Files` 自动建立：

```text
ID Index
Category Index
Keyword Inverted Index
Status Index
Scope / Tag Index
Relation Index
Back Reference Index
```

### ID Index

```text
K030.020.010 → 030_xxx.md#K030.020.010
```

### Category Index

```text
C010.020 → [K..., K..., K...]
```

查询一个分类时默认可以选择是否包含所有子分类。

### Keyword Index

从以下内容生成标准化检索词：

```text
Knowledge title
Fact
Scope
Tags
分类标题和分类 aliases
祖先分类标题和 aliases
```

### Relation Index

从 `Refs` 自动建立正向和反向关系。

---

## 8. 查询顺序

已知 K-ID：

```text
K-ID
→ ID Index
→ O(1) 精确寻址
```

自然语言查询：

```text
query
 ↓
Keyword Inverted Index
 ↓
Category / Status / Scope / Tag Filters
 ↓
确定性 Ranking
 ↓
Top-N Knowledge
 ↓
Agent
```

需要扩展时：

```text
Knowledge Node
 ↓
Relation Index 1-hop
 ↓
相关 Knowledge / Architecture / Rule / Gate
```

正常查询禁止扫描全部 Knowledge Markdown。

---

## 9. Search API

公共 Knowledge Manager 至少提供：

```text
getTaxonomy(projectId)
listCategories(projectId, parentId?)
searchKnowledge(request)
getNode(projectId, knowledgeId)
getRelated(projectId, knowledgeId)
getLibraryStats(projectId)
reindexProject(projectId)
validateProjectLibrary(projectId)
```

Search request 支持：

```text
query
category
includeDescendants
status
scope
limit
```

默认自然语言查询仍只返回 `VALIDATED`。

---

## 10. Script / CLI

公共插件必须提供脚本检索入口：

```text
knowledge tree <knowledge-root>
knowledge search <knowledge-root> <query>
knowledge get <knowledge-root> <K-ID>
knowledge related <knowledge-root> <K-ID>
knowledge validate <knowledge-root>
knowledge reindex <knowledge-root>
```

脚本和 Harness Service 必须调用同一套 Parser / Index / Search Engine，禁止维护两套检索逻辑。

---

## 11. Admission / Reindex

```text
读取 TAXONOMY.yaml
 ↓
校验 C-ID Tree
 ↓
扫描 NNN_*.md
 ↓
解析 K Tree
 ↓
校验每个 Leaf 的 Category
 ↓
校验 Category 存在
 ↓
校验 K-ID 唯一
 ↓
建立 Machine Index
 ↓
生成 source_fingerprint
 ↓
重写 00_INDEX.md
 ↓
READY
```

任何结构错误必须拒绝进入 READY。

---

## 12. Hard Reject

至少包括：

```text
缺少 TAXONOMY.yaml
taxonomy standard 错误
C-ID 非法 / 重复 / 父子关系错误
正式 Knowledge Leaf 没有 Category
Category 指向不存在或已废弃分类
K-ID 重复
Knowledge File 命名错误
Knowledge Tree 错误
Status / Fact / Provenance 缺失
Refs 格式错误
```

---

## 13. 核心原则

```text
TAXONOMY = 图书分类法
C-ID     = 分类号
K-ID     = 索书号
Knowledge Node = 正文
00_INDEX = 自动生成的总目录
Machine Index = 自动生成的检索系统
Knowledge Manager = 图书馆管理系统
```

目标不是让 Agent 阅读更多 Knowledge，而是：

> **让 Agent 在巨大项目知识库中用最少查找成本得到最少、最相关、可追溯的 Knowledge。**
