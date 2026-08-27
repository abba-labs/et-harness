# Project Contract

通用 Project Plugin 协议核心。

它定义：

```text
Project Manifest
Project Context
Resource Handle
Resource Interface Standard
Query / Candidate Contract
Root Discovery
Manifest Validation
```

核心原则：

> **Agent 负责理解和决策；公共插件负责工具、路由、接口规范和校验；Project Plugin 负责提供符合规范的项目私有内容。**

## 标准先于实现

公共插件必须先定义自己要求的项目接口，再实现搜索/路由逻辑。

当前标准：

```text
Project Manager          → project.yaml / Project Contract v0.1
Architecture Navigator  → architecture-v0.1
Rule Manager            → rule-v0.1
Knowledge Manager       → knowledge-v0.1
Gate Manager            → gate-v0.1
```

规范文档位于：

```text
standards/
├ 00_RESOURCE_INTERFACE_STANDARD_V0_1.md
├ 01_ARCHITECTURE_STANDARD_V0_1.md
├ 02_RULE_STANDARD_V0_1.md
├ 03_KNOWLEDGE_STANDARD_V0_1.md
└ 04_GATE_STANDARD_V0_1.md
```

Project Plugin 通过 `project.yaml` 的 `resources.*.standard` 声明遵循的接口版本。Project Contract 会校验声明是否兼容。

它仍然不负责：

```text
任务语义理解
最终规则判断
知识语义判断
Agent 开发决策
```

这些仍由 Agent 完成；对应公共插件只负责把正确、规范、可追溯的项目资料快速送到 Agent 面前。
