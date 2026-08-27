# Project Resource Routing Meta Standard v0.1

> 状态：DESIGN BASELINE  
> 作用：所有面向 Project Plugin 私有资源的公共插件必须继承的母规范。  
> 核心原则：**公共插件负责制定接口规范、校验接入质量并提供高效可靠路由；项目负责按规范组织自己的私有内容；Agent 负责理解与决策。**

---

## 1. 公共插件的两项核心职责

任何直接消费项目私有资源的公共插件，只承担两类公共责任：

```text
A. Interface Standard Owner
   定义项目接口必须怎样设计
   校验项目是否符合标准
   不符合标准 → 拒绝该资源接入

B. High-efficiency Router
   Index → Numbered File → Numbered Tree → Node
   用最短寻址路径返回最小相关内容
```

公共插件不得：

```text
替项目定义具体业务分类
把某个项目的模块 / 规则 / 知识 / Gate 写进公共层
要求 Agent 全量阅读项目资源
为了兼容项目私有格式而增加项目专属分支
替 Agent 做最终语义判断
```

---

## 2. 统一寻址骨架

所有可路由 Project Resource 必须遵守同一种寻址模型：

```text
<resource>/
├─ 00_INDEX.md
├─ 010_<project-defined-name>.<ext>
├─ 020_<project-defined-name>.<ext>
├─ 030_<project-defined-name>.<ext>
└─ ...

00_INDEX.md
    ↓
编号文件
    ↓
文件内编号树
    ↓
稳定 Node ID
    ↓
最小必要正文 / 数据
```

公共层只规定结构，不规定：

```text
010 是什么内容
020 是什么内容
项目应该分成哪些类别
项目应该拥有多少文件
```

这些全部由项目决定。

v0.1 中，正式可路由主文件直接位于资源根目录，不使用多级目录作为路由语义。

---

## 3. `00_INDEX.md` 是唯一总入口

每种项目资源根目录必须存在：

```text
00_INDEX.md
```

### 3.1 YAML Front Matter 是机器接口

`00_INDEX.md` 必须使用 YAML Front Matter 提供机器路由表：

```yaml
---
interface: project-resource-index-v0.1
resource: <resource-kind>
standard: <resource-standard-id>
files:
  - id: X010
    file: 010_xxx.md
    title: <短标题>
    summary: <一句话说明>
    aliases: [<route-hint>, <route-hint>]

  - id: X020
    file: 020_xxx.md
    title: <短标题>
    summary: <一句话说明>
    aliases: [<route-hint>]
---
```

其中：

```text
Front Matter = 正式机器接口
Markdown 正文 = 可选人工说明
```

公共 Router 正常工作不得依赖解析 Index 正文中的自然语言表格。

### 3.2 Index 要求

所有正式可路由文件必须被 `files[]` 索引。

每个 entry 必须提供：

```text
id
file
title
summary
aliases
```

要求：

```text
File ID 唯一
file 唯一
Index 不指向不存在文件
正式可路由文件不能游离于 Index 之外
summary 只允许一句话级摘要
aliases 只用于路由提示，不承载业务规则
```

公共插件正常查询时必须先使用 Index，不允许默认全目录全文扫描。

---

## 4. 编号文件命名规范

所有可路由主文件必须使用三位数字前缀：

```text
NNN_<project-defined-name>.<ext>
```

例如：

```text
010_xxx.md
020_xxx.md
120_xxx.yaml
```

统一要求：

```text
NNN 固定三位数字
000 保留，不作为正式主文件编号
推荐以 010 / 020 / 030 ... 递增
名称只用于可读性，不作为稳定地址
名称使用小写字母、数字、`-`、`_`
禁止空格
禁止无编号的正式可路由主文件
```

推荐预留编号间隔，以便后续插入：

```text
010
020
030

需要插入时可以使用：
015
025
```

文件编号一旦发布为稳定接口，不得随意重编号。

---

## 5. 稳定 Node ID

真正稳定的机器地址是 Node ID，不是标题和自然语言名称。

每类资源由对应公共插件定义一个固定前缀：

```text
Architecture → A
Rule         → R
Knowledge    → K
Gate         → G
```

通用格式：

```text
<PREFIX><FILE-NNN>[.<NNN>...]
```

示例：

```text
R010
R010.010
R010.010.020
R010.010.020.010
```

要求：

```text
每级编号固定三位
Node ID 项目内、同资源类型唯一
Node ID 第一段必须与所在文件编号一致
标题修改不得改变 Node ID
Node ID 不承载自然语言语义
已废弃 ID 不允许复用给新语义
```

这样编号本身就是稳定路由地址。

---

## 6. 文件内部必须可生成编号树

公共插件不要求所有资源使用同一种正文格式，但必须能够从文件中得到：

```text
File ID
  ↓
Branch Node
  ↓
Branch Node
  ↓
Leaf / Routable Node
```

例如：

```text
X010
├─ X010.010
│  ├─ X010.010.010
│  └─ X010.010.020
└─ X010.020
```

子规范负责定义：

```text
Markdown 标题怎样携带 Node ID
或 YAML 怎样表达树节点
节点最小字段是什么
哪些节点具备实际语义
```

母规范只要求：

> **Router 可以不理解完整正文，就先得到树结构和 Node 地址。**

---

## 7. Agent-first 内容原则

项目接口是服务 Agent 的，不是为了写漂亮的人类说明书。

可路由节点正文必须优先：

```text
短
直接
准确
结构稳定
最小必要信息
引用代替复制
```

禁止默认写入：

```text
长篇背景介绍
重复上下文
与当前节点无关的历史说明
为了“完整”复制其他节点内容
```

需要更多背景时，通过稳定 ID / resource path / knowledge reference 继续路由。

核心目标：

> **Agent 命中一个 Node 后，尽可能用最少 Token 理解它。**

---

## 8. 两阶段工作方式：接入时重校验，查询时轻路由

### 8.1 Admission / Index Build

项目资源接入或发生变更时：

```text
读取 00_INDEX Front Matter
校验 standard version
校验文件命名
校验编号唯一性
校验 Node ID
校验 Index ↔ File 对应关系
校验必要引用
解析文件内部编号树
建立 / 刷新内部 Route Index
```

这是相对重的阶段，但不应在每次 Agent 查询时重复执行。

### 8.2 Runtime Route

Agent 查询时：

```text
query / scope
   ↓
已构建 Route Index
   ↓
候选编号文件
   ↓
候选 Node / Branch
   ↓
只读取最相关节点
   ↓
CandidateResult
```

因此：

> **重校验发生在接入/变更阶段；高频查询只走缓存后的短路径。**

---

## 9. Hard Reject 与 Warning

结构性错误属于 Hard Reject：

```text
缺少 00_INDEX.md
Index Front Matter 无法解析
interface != project-resource-index-v0.1
resource kind 不匹配
standard version 不兼容
文件命名不符合规范
文件编号重复
Node ID 重复
Node ID 与所在文件编号不一致
Index 指向不存在文件
存在未被 Index 管理的正式可路由文件
必填机器字段缺失
无法解析文件内路由树
```

项目资源出现 Hard Reject 时：

```text
该资源接口不得进入 READY
公共插件拒绝提供正式路由
返回明确校验错误
```

以下问题第一版可以先 Warning：

```text
可能存在语义重复
可能存在内容冲突
aliases 质量较低
描述过长
潜在失效引用
```

后续能力成熟后可升级为 Hard Reject。

---

## 10. 统一路由返回原则

所有项目资源 Router 都返回候选，不返回“最终判断”。

至少包含：

```text
project_id
resource kind
node id
短标题
location
relevance / ranking
match reasons
provenance
```

公共插件负责：

```text
高速定位
排序
读取
结构校验
```

Agent负责：

```text
理解
选择
判断适用性
决定下一步查询或行动
```

---

## 11. 子规范的唯一职责

每个资源子规范只需要在母规范基础上补充：

```text
1. standard id
2. Node 前缀
3. 主文件扩展名
4. 文件内部树表示方法
5. Node 最小字段
6. 该资源特有的基础校验
```

子规范不得定义：

```text
项目具体应该有哪些类别
项目具体应该有哪些文件
ET-TOOL / FPGA / Web 等项目专属结构
```

---

## 12. 当前子规范

```text
Project Manager          → Project Contract / project.yaml
Architecture Navigator  → architecture-v0.1 / Axxx
Rule Manager            → rule-v0.1         / Rxxx
Knowledge Manager       → knowledge-v0.1    / Kxxx
Gate Manager            → gate-v0.1         / Gxxx
```

Project Plugin 必须声明自己遵循的标准版本。

公共插件只接收自己明确支持的标准版本。

---

## 13. 最终设计目标

一切设计都服务两个指标：

```text
查得快
理解快
```

标准寻址路径统一为：

```text
Project
  ↓
Resource
  ↓
00_INDEX Front Matter
  ↓
NNN File
  ↓
NNN Tree Node
  ↓
Minimal Content
  ↓
Agent
```

这套母规范不是文档排版规范，而是整个 Project Plugin 资源体系的**机器寻址协议**。
