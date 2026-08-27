# Architecture Navigator — Project Interface

> 支持标准：`architecture-v0.1`

项目只有满足本接口，Architecture Navigator 才允许正式接入。

## 1. 目录

```text
architecture/
├─ 00_INDEX.md
├─ 010_<project-defined-name>.md
├─ 020_<project-defined-name>.md
└─ ...
```

公共插件不规定 `<project-defined-name>` 的业务含义，也不规定项目应该有哪些架构文件。

## 2. `00_INDEX.md`

YAML Front Matter 是机器接口：

```yaml
---
interface: project-resource-index-v0.1
resource: architecture
standard: architecture-v0.1
files:
  - id: A010
    file: 010_xxx.md
    title: <短标题>
    summary: <一句话摘要>
    aliases: [<route-hint>]
---
```

所有正式编号文件都必须进入 `files[]`。

## 3. 编号文件

格式：

```text
NNN_<name>.md
```

映射：

```text
010_xxx.md → A010
020_xxx.md → A020
```

编号发布后保持稳定。

## 4. 文件内 Architecture Tree

所有 Markdown 标题携带 Node ID：

```markdown
# [A010] <主题>
## [A010.010] <分支>
### [A010.010.010] <节点>
```

要求：

```text
每级固定三位数字
标题层级 = Node ID 深度
父 Node 必须存在
第一段必须等于所在 File ID
项目 Architecture Node ID 唯一
```

## 5. Node 内容

Agent-first，保持最小：

```text
Role: 负责什么
Boundary: 不负责什么（可选）
Resources: 真实资源入口（需要时）
Relations: 其他 Node ID（需要时）
```

`Relations` 中符合 `Axxx[.xxx...]` 形式的 Architecture Node ID 必须指向同项目已存在节点；允许跨文件引用，不允许悬空关系。

禁止在 Architecture Node 中复制 Rule、Knowledge、Gate 正文。

## 6. Hard Reject

以下任一情况拒绝该项目 Architecture Resource：

```text
缺少 00_INDEX.md
Index Front Matter 非法
standard != architecture-v0.1
编号文件命名非法
File ID 不匹配文件编号
Index 漏文件或指向不存在文件
标题缺少合法 Axxx Node ID
Node ID 重复
Node ID 与文件不一致
标题层级与 Node 深度不一致
父 Node 缺失
Architecture Relation 指向不存在的 Axxx Node
```

## 7. Router 行为

接入/刷新时：

```text
重校验 → 解析标题树 → 校验跨节点 Relations → 建缓存
```

查询时：

```text
query → Index Cache → File → Node → CandidateResult
```

Architecture Navigator 返回候选和来源，不替 Agent 判断哪个 Node 最终适用。
