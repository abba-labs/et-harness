# Knowledge Interface Standard v0.1

> 标准 ID：`knowledge-v0.1`  
> Node 前缀：`K`  
> 主文件格式：`NNN_<name>.md`  
> 继承：`Project Resource Routing Meta Standard v0.1`

## 1. 本标准只规定知识接口

Knowledge Manager 不规定项目应该积累哪些知识类别，也不规定知识分类体系。

项目自行设计知识内容和文件主题。

公共标准只保证：

```text
00_INDEX.md
   ↓
NNN_*.md
   ↓
Kxxx 编号知识树
   ↓
Knowledge Leaf
```

---

## 2. `knowledge/00_INDEX.md` 是唯一机器入口

必须存在：

```text
knowledge/00_INDEX.md
```

YAML Front Matter：

```yaml
---
interface: project-resource-index-v0.1
resource: knowledge
standard: knowledge-v0.1
files:
  - id: K010
    file: 010_xxx.md
    title: <短标题>
    summary: <一句话>
    aliases: [<route-hint>]
---
```

所有正式可路由知识文件必须进入 Index。

正常查询不允许默认扫描整个 knowledge 目录。

---

## 3. 文件命名与 File ID

```text
010_xxx.md → K010
020_xxx.md → K020
```

要求：

```text
三位数字前缀
File ID = K + 文件编号
编号稳定
文件业务含义由项目决定
```

---

## 4. 文件内部使用 Knowledge Tree

```markdown
# [K010] <知识文件主题>

## [K010.010] <分支>

### [K010.010.010] <知识节点>

### [K010.010.020] <知识节点>
```

要求：

```text
每级固定三位编号
Node ID 唯一
第一段与 File ID 一致
标题可改，ID 不变
Branch 只负责导航
Leaf 承载可复用知识
```

---

## 5. Knowledge Leaf 使用 Agent-first 最小格式

```markdown
### [K010.010.010] <短标题>

Status: VALIDATED
Fact: <已确认事实 / 结论>
Scope: <可选；适用范围>
Provenance: <来源引用>
Refs: <可选；其他稳定 ID / 资源>
```

`Status` v0.1 固定为：

```text
CANDIDATE
VALIDATED
DEPRECATED
```

最低要求：

```text
Status
Fact
Provenance
```

要求：

```text
Fact 短、明确、可复用
Provenance 可追溯
长日志 / 长证据只引用，不复制
Knowledge 不是 Rule
```

---

## 6. 查询安全边界

自然语言查询默认只返回：

```text
VALIDATED
```

不会把：

```text
CANDIDATE
DEPRECATED
```

默认作为项目事实交给 Agent。

Agent 明确指定稳定 K ID 时，可以读取任何状态，但返回结果必须携带 Status。

公共 API 可以通过显式 filter 查询 CANDIDATE，用于后续经验治理流程。

---

## 7. 知识演进

```text
新经验 / 新结论
   ↓
CANDIDATE
   ↓
验证 / 评审
   ↓
VALIDATED
   ↓
需要时 DEPRECATED
```

同一知识语义优先更新 canonical Knowledge Node，不复制近义知识。

旧 ID 不得复用给新语义。

经验提炼、去重、晋级和写回由公共 `Experience / Memory Manager` 负责；Knowledge Manager 负责提供规范化的知识读取、索引和状态边界。

---

## 8. 高效路由

已知稳定 Knowledge ID：

```text
K010.020.010
→ O(1) 精确寻址
```

自然语言：

```text
query / scope
   ↓
00_INDEX Cache
   ↓
候选 Kxxx File
   ↓
Knowledge Tree Cache
   ↓
VALIDATED Knowledge Leaf Candidates
   ↓
Agent
```

默认不向 Agent 灌入完整历史、完整聊天、完整日志。

---

## 9. 基础接入校验

Hard Reject：

```text
缺少 knowledge/00_INDEX.md
Index Front Matter 不符合母规范
正式文件不符合 NNN_<name>.md
File ID 与文件编号不一致
Knowledge Node ID 重复
Node ID 与所在文件编号不一致
父 Node 缺失
标题层级与编号深度不一致
Index 漏文件 / 指向不存在文件
Knowledge Leaf 缺少 Status / Fact / Provenance
Status 非法
```

Warning：

```text
Fact 过长
Scope 过于宽泛
可能存在语义重复
来源可能失效
知识可能过期
Route Hints 太弱
```

---

## 10. Knowledge Manager 的公共职责

负责：

```text
接口校验
索引构建
缓存刷新
稳定 ID 寻址
自然语言候选路由
状态过滤
来源返回
```

不负责：

```text
规定项目知识类别
替项目生成业务知识
自动把 CANDIDATE 当事实
完成经验提炼和晋级写回
```

---

## 11. 核心目标

```text
快速定位
最小上下文
稳定引用
状态可信
来源可追溯
```

Knowledge Manager 的价值不是保存更多文本，而是让 Agent **更快找到可信、值得知道的项目认知**。
