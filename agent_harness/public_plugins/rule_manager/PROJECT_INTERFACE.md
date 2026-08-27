# Rule Manager Project Interface

> 支持标准：`rule-v0.1`  
> 母规范：`Project Resource Routing Meta Standard v0.1`

## 1. 项目必须提供

```text
rules/
├─ 00_INDEX.md
├─ 010_<project-defined-name>.md
├─ 020_<project-defined-name>.md
└─ ...
```

项目自行决定规则文件数量、分类和业务含义。

Rule Manager 只规定机器寻址结构。

## 2. `00_INDEX.md`

Front Matter 是正式机器接口：

```yaml
---
interface: project-resource-index-v0.1
resource: rules
standard: rule-v0.1
files:
  - id: R010
    file: 010_xxx.md
    title: <短标题>
    summary: <一句话>
    aliases: [<route-hint>]
---
```

要求：

```text
所有正式规则文件必须进入 files[]
File ID 与三位文件编号一致
summary 保持一句话
aliases 只用于路由提示
```

## 3. 规则文件命名

```text
NNN_<project-defined-name>.md
```

例如：

```text
010_xxx.md → R010
025_xxx.md → R025
```

文件业务名称由项目决定，编号是稳定地址。

## 4. 文件内 Rule Tree

```markdown
# [R010] <主题>

## [R010.010] <分支>

### [R010.010.010] <子分支>

#### [R010.010.010.010] <规则名>
```

标题层级必须和 Node ID 深度一致。

分支只负责导航；Leaf 承载具体规则。

## 5. Rule Leaf 最小格式

```markdown
#### [R010.010.010.010] <短规则名>

Level: MUST
When: <适用条件>
Rule: <必须 / 禁止做什么>
Refs: <可选稳定引用>
```

`Level`：

```text
MUST
MUST_NOT
MAY
```

规则必须短、直接、准确、可验证。

## 6. Rule Manager 会拒绝

```text
缺少 00_INDEX.md
Index 标准错误
编号文件非法
Index 与文件不一致
Node ID 重复
Node ID 与文件编号不一致
父节点缺失
标题层级与编号深度不一致
Leaf 缺少 Level / When / Rule
Level 非法
```

## 7. 查询接口

Agent 可以：

```text
refreshProject(projectId)
searchRules({ projectId, query, scope?, limit? })
getNode(projectId, ruleId)
listChildren(projectId, nodeId)
listFiles(projectId)
getIndex(projectId)
```

有稳定 Rule ID 时优先直接寻址。

没有 ID 时：

```text
query → Index Cache → File → Rule Tree → Rule Leaf Candidates
```

Rule Manager 只返回候选，不替 Agent 判断最终适用规则。
