# Project Contract v0.1 — 项目接口与高效路由基线

> 状态：IMPLEMENTATION BASELINE  
> 目标：让任意项目以最小成本接入公共插件，并让公共插件依赖统一、可靠、可拒绝、可高速路由的项目接口。  
> 核心原则：**Agent 负责理解与决策；公共插件负责规范、校验与路由；Project Plugin 负责提供符合规范的项目私有内容。**

---

## 1. 系统关系

```text
Human Task
   ↓
Agent
   ↓
Public Plugin
   ↓
Project Interface Standard
   ↓
Project Plugin
   ↓
Project Private Content
```

公共插件不是项目知识本身，也不是任务决策者。

它面向 Project Plugin 只承担：

```text
制定接口规范
校验接口
拒绝不合规接口
建立路由索引
高速返回候选内容
```

---

## 2. 最小 Project Plugin

```text
project.yaml
architecture/
rules/
knowledge/
gates/
adapters/        # optional
```

项目不复制公共 Manager / Navigator / Router 代码。

项目只实现自己的私有接口内容。

---

## 3. project.yaml v0.1

```yaml
contract_version: "0.1"

project:
  id: et-tool
  name: ET-TOOL

root:
  markers:
    - source/CMakeLists.txt

resources:
  architecture:
    path: architecture/
    standard: architecture-v0.1
  rules:
    path: rules/
    standard: rule-v0.1
  knowledge:
    path: knowledge/
    standard: knowledge-v0.1
  gates:
    path: gates/
    standard: gate-v0.1

adapters: {}
```

`standard` 是运行时兼容协议，不是说明文字。

标准缺失、错误或公共插件不支持该版本时，资源不得正式接入。

---

## 4. ProjectContext

Project Manager 读取合法 `project.yaml` 后生成：

```text
ProjectContext
├ project_id
├ display_name
├ project_root
├ contract_version
├ resources
├ resource_standards
└ adapters
```

公共插件只通过 ProjectContext 获取资源入口，不自行猜项目路径。

---

## 5. Project Resource Routing Meta Standard

所有直接消费 Project Plugin 私有资源的公共插件统一继承：

```text
Project Resource Routing Meta Standard v0.1
```

正式文件：

```text
agent_harness/project_contract/standards/
00_RESOURCE_INTERFACE_STANDARD_V0_1.md
```

它定义统一机器寻址协议：

```text
00_INDEX.md Front Matter
        ↓
NNN_<project-defined-name>.<ext>
        ↓
固定三位编号 Tree
        ↓
稳定 Node ID
        ↓
Minimal Content
```

公共层不规定项目具体有哪些类别。

---

## 6. `00_INDEX.md` 是资源唯一总入口

每类资源必须存在：

```text
00_INDEX.md
```

YAML Front Matter 是正式机器接口：

```yaml
---
interface: project-resource-index-v0.1
resource: rules
standard: rule-v0.1
files:
  - id: R010
    file: 010_xxx.md
    title: <short title>
    summary: <one sentence>
    aliases: [<route hint>]
---
```

Markdown 正文仅为可选说明。

Router 不依赖读取 Index 正文才能工作。

---

## 7. 编号文件与 Node ID

统一主文件命名：

```text
NNN_<project-defined-name>.<ext>
```

例如：

```text
010_xxx.md
020_xxx.md
120_xxx.yaml
```

每类资源使用固定 Node 前缀：

```text
Architecture → A
Rule         → R
Knowledge    → K
Gate         → G
```

Node ID：

```text
<PREFIX><FILE-NNN>[.<NNN>...]
```

例如：

```text
R010
R010.010
R010.010.020
R010.010.020.010
```

固定三位编号使：

```text
排序稳定
地址稳定
层级清晰
机器解析简单
跨资源引用可靠
```

---

## 8. 四类项目资源子规范

### Architecture Navigator

```text
standard: architecture-v0.1
prefix: A
file: NNN_*.md
```

只补充 Architecture Tree 和 Architecture Node 最小表达。

不规定项目有哪些模块。

### Rule Manager

```text
standard: rule-v0.1
prefix: R
file: NNN_*.md
```

只补充 Rule Tree 和 Agent-first Rule Node 格式。

不规定项目有哪些规则类别。

### Knowledge Manager

```text
standard: knowledge-v0.1
prefix: K
file: NNN_*.md
```

只补充 Knowledge Tree、Provenance 和最小 Fact 表达。

不规定项目有哪些知识类别。

### Gate Manager

```text
standard: gate-v0.1
prefix: G
file: NNN_*.yaml
```

只补充机器可解析 Gate Tree、触发条件、Tool Capability 与 PASS 条件。

不规定项目有哪些 Gate。

---

## 9. 接入阶段：重校验

项目资源加载或变化时：

```text
读取 00_INDEX Front Matter
        ↓
校验 standard
        ↓
校验编号文件
        ↓
校验 File ID
        ↓
校验 Index ↔ File
        ↓
校验 Node ID / Tree
        ↓
子插件资源特有校验
        ↓
建立 Route Index Cache
```

存在结构性错误：

```text
READY → 禁止
状态 → REJECTED
```

公共插件不得“尽量兼容”。

---

## 10. 查询阶段：轻路由

Agent 不需要先形成完美 TaskSpec。

可以直接：

```text
query
+
optional scope
```

公共插件使用已构建索引：

```text
Agent query
   ↓
Route Index Cache
   ↓
候选 NNN File
   ↓
候选 Tree Branch / Node
   ↓
读取最小相关 Node
   ↓
CandidateResult
```

正常高频查询不重新扫描整个资源目录。

---

## 11. CandidateResult

统一返回候选，不替 Agent 做最终判断：

```text
project_id
resource kind
node id
title
location
summary / minimal content
relevance
match reasons
provenance
warnings
```

Agent 根据候选继续：

```text
阅读
理解
判断
细化 query
或进入下一步开发
```

---

## 12. Agent-first 内容原则

接口内容服务对象是 Agent。

统一要求：

```text
短
直接
准确
结构稳定
引用代替复制
最小 Token
```

例如 Rule Node：

```text
[R010.010.010.010] <short name>
Level: MUST
When: <condition>
Rule: <constraint>
Refs: <optional>
```

需要背景时继续路由 Knowledge，不把长背景塞进 Rule。

同样原则适用于 Architecture / Knowledge / Gate。

---

## 13. 公共代码已经提供的基础约束

`@agent-harness/project-contract` 当前提供：

```text
Project Manifest 校验
Resource Standard 版本校验
统一 Resource Routing Spec
三位编号文件解析
稳定 Node ID 校验
00_INDEX 通用结构校验
Index ↔ 实际文件一致性校验
```

这些是所有项目资源公共插件后续实现时必须复用的基础能力。

子插件不能重新发明另一套编号和 Index 校验规则。

---

## 14. Interface Ownership

任何直接消费项目私有资源的公共插件必须随包发布：

```text
PROJECT_INTERFACE.md
```

并明确：

```text
继承的 Meta Standard
支持的 standard version
Node Prefix
主文件格式
Tree 表达
Node 最小字段
Hard Reject
Warning
Router API
```

公共接口文档和代码校验器必须一致。

---

## 15. ET-TOOL 当前状态

ET-TOOL 是第一套 Project Plugin 实例。

当前四类资源已经建立标准空索引：

```text
architecture/00_INDEX.md
rules/00_INDEX.md
knowledge/00_INDEX.md
gates/00_INDEX.md
```

全部：

```yaml
files: []
```

含义：

```text
接口结构已按标准建立
正式项目内容尚未填充
旧文档不自动迁移
后续逐项重新设计
```

---

## 16. 当前完成边界

```text
Project Contract                    DONE
Project Manager minimal router      DONE
Project Resource Routing Meta       DONE
Common Index / Address Validator    DONE
Architecture interface baseline     DONE
Rule interface baseline             DONE
Knowledge interface baseline        DONE
Gate interface baseline             DONE
ET-TOOL empty standard interfaces   DONE
```

下一阶段才开始实现具体公共 Router，例如 Architecture Navigator。
