# Architecture Interface Standard v0.1

> 标准 ID：`architecture-v0.1`  
> Node 前缀：`A`  
> 主文件格式：`NNN_<name>.md`  
> 继承：`Project Resource Routing Meta Standard v0.1`

## 1. 本标准只规定接口，不规定项目架构

Architecture Navigator 不规定项目应该有哪些模块、层次或文件。

项目自行决定架构内容如何分类。

公共标准只保证：

```text
00_INDEX.md
   ↓
NNN_*.md
   ↓
Axxx 编号树
   ↓
Architecture Node
```

---

## 2. 总入口

必须存在：

```text
architecture/00_INDEX.md
```

`00_INDEX.md` 的 YAML Front Matter 是正式机器路由接口，正文只用于可选说明。

最小格式：

```yaml
---
interface: project-resource-index-v0.1
resource: architecture
standard: architecture-v0.1
files:
  - id: A010
    file: 010_xxx.md
    title: <短标题>
    summary: <一句话说明>
    aliases: [<route-hint>, <route-hint>]
---
```

Index 必须覆盖全部正式可路由 Architecture 文件。

每个 entry 至少提供：

```text
File ID
File
Title
Summary
Aliases
```

`xxx` 的业务含义完全由项目决定。

Architecture Navigator 正常路由不得依赖解析 Index 正文中的自然语言表格。

---

## 3. 文件命名与 File ID

```text
010_xxx.md → A010
020_xxx.md → A020
```

要求：

```text
三位数字前缀
File ID = A + 文件编号
编号稳定，不因标题变化而改变
文件必须被 00_INDEX.md 显式索引
```

---

## 4. 文件内部使用 Architecture Tree

正式 Architecture 主文件中的 Markdown 标题必须携带稳定 Node ID：

```markdown
# [A010] <文件主题>

## [A010.010] <分支>

### [A010.010.010] <节点>

### [A010.010.020] <节点>

## [A010.020] <分支>
```

要求：

```text
每级编号固定三位
Node 第一段必须等于 File ID
Markdown 标题层级必须与 Node ID 深度一致
父 Node 必须存在
同项目 Architecture Node ID 必须唯一
标题名称可以改，Node ID 不随标题变化
分支节点允许只承担导航作用
```

这样 Router 可以只解析标题行就建立 Architecture Tree，不需要先理解正文。

---

## 5. Architecture Node 最小表达

真正需要 Agent 理解的节点必须短而明确。

推荐：

```markdown
### [A010.010.010] <短标题>

Role: <负责什么>
Boundary: <明确不负责什么；没有可省略>
Resources: <真实源码 / 配置 / 文档入口>
Relations: <相关 Architecture Node ID；需要时>
```

最低要求是：

```text
Node ID
短标题
Role 或明确的导航意义
```

`Relations` 中凡是符合 Architecture Node ID 形式的 `Axxx[.xxx...]`，都必须指向同项目中真实存在的 Architecture Node。允许跨 Architecture 文件引用，但不允许悬空关系。

核心目标：

```text
Agent 命中 Node 后快速知道：
它是什么
负责什么
边界是什么
去哪里看真实实现
还能沿哪些稳定关系继续导航
```

禁止把长篇教程、Rule 正文、Gate 定义塞进 Architecture Node。
需要更深背景时通过稳定 ID / resource path 继续路由。

---

## 6. 路由方式

接入/刷新阶段：

```text
读取 00_INDEX Front Matter
        ↓
校验全部编号文件
        ↓
只解析 Markdown 标题树 + 最小节点字段
        ↓
校验 Architecture Relations 不悬空
        ↓
建立 Route Index Cache
```

Agent 查询阶段：

```text
Agent query
   ↓
Architecture Navigator 使用缓存 Index
   ↓
命中少量 Axxx File
   ↓
命中相关 Axxx.xxx Node / Branch
   ↓
只返回最小相关节点
```

高频查询阶段不得反复全文扫描整个 Architecture 目录。

---

## 7. 基础接入校验

Hard Reject：

```text
缺少 architecture/00_INDEX.md
Index Front Matter 不符合母规范
正式文件不符合 NNN_<name>.md
File ID 与文件编号不一致
Architecture Node ID 重复
Node ID 与所在文件编号不一致
Markdown 标题层级与 Node ID 深度不一致
父 Node 缺失
Architecture Relation 指向不存在的 Axxx Node
Index 漏掉正式可路由文件
Index 指向不存在文件
无法解析编号树
```

Warning：

```text
节点描述过长
Aliases 太弱
Resources 可能失效
可能存在重复架构语义
```

出现 Hard Reject 时，该项目 Architecture Resource 不进入 READY，Architecture Navigator 拒绝正式路由。

---

## 8. 与其他资源边界

```text
Architecture → 项目是什么、组成关系、真实资源入口
Rule         → 必须 / 禁止怎样做
Knowledge    → 可复用认知、经验、事实、决策
Gate         → 怎样验证
```

Architecture 只引用其他资源 ID，不复制其他资源正文。
