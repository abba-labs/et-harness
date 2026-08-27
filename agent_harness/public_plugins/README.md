# Public Plugins

公共插件分为主执行能力与可选旁路能力。

## 1. 项目接口 / Router

```text
Project Manager
Architecture Navigator
Rule Manager
Knowledge Manager
Gate Manager
```

其中后四项消费 Project Plugin 私有资源，并拥有对应 Project Interface Standard。

## 2. 公共运行能力

```text
Context Manager / Builder
Evidence / State Manager
Experience / Memory Manager
```

这些插件不定义项目业务文件分类。

## 3. 推荐技术加载顺序

```text
Governance Core
  ↓
Project Manager
  ↓
Architecture / Rule / Knowledge Routers
  ↓
Evidence / State Manager
  ↓
Gate Manager
  ↓
Context Manager / Builder
  ↓
Experience / Memory Manager
```

注意：这是插件技术依赖顺序，不是 Agent 任务认知顺序。任务开始后 Context Management 必须立即进入生命周期。

## 4. Optional Observation Plane

```text
Framework Efficiency Observer
```

它是可选 Sidecar，不属于主执行链的强依赖：

```text
Execution Plugins -> optional metric event -> Observer
Observer          -X-> Execution Plugins
```

主插件不得 `inject` 或依赖 Observer。Observer 卸载或故障不得改变主框架行为。

## 5. 统一原则

```text
Agent = 理解 / 判断 / 实施
Public Plugin = 标准 / 路由 / 工具 / 约束
Project Plugin = 项目私有内容
Observation Plane = 可选旁路效率观测
```

ET-TOOL 项目内容必须等公共插件 baseline 验收完成后再开始设计。
