# Public Context Manager / Builder

公共 `Context v0.2`。

## 核心定位

```text
Context 不是长期记忆。
Context = 当前任务的可重建最小充分工作视图。
```

长期信息继续属于：

```text
Architecture / Rules / Knowledge / Gate / Evidence / State / Experience
```

Context 只保存任务状态和稳定引用，不保存已展开的资源正文。

## 两个职责

```text
Context Manager
= 生命周期
= Bootstrap / Ledger / Working Set / Recent Tail / Handles / Rebuild / Handoff

Context Builder
= 当前 Frame 的解析与装配
= Resolve / Deduplicate / Priority / Budget
```

## Context Frame

```text
Project Compass   # required，防止 Agent 迷路
Task Ledger       # required，任务目标 / 范围 / 已确认 / 假设 / 问题 / 计划
Progress Ledger   # high，上一步 / 结果 / 当前问题 / 下一步
Working Set       # Agent 显式 attach 的 A/R/K/G 引用
Recent Tail       # 最近少量关键动作 / 观察，固定环形上限
Available Handles # 可按需展开的轻量引用
```

## 生命周期

```text
beginTask
  ↓
Bootstrap Frame
  ↓
Agent 分析 / Navigator 查询
  ↓
attach / detach / addHandles
  ↓
buildFrame
  ↓
update Task / Progress Ledger
  ↓
recordRecent
  ↓
rebuild（阶段切换 / 上下文过大 / 需要干净重建）
  ↓
pause / resume / handoff
  ↓
complete
```

`buildFrame()` 每次都会重新解析 Working Set 引用，因此旧资源正文不会永久留在 Context State。

## Knowledge

支持：

```text
K001.001                              # 当前 Project
knowledge://project/<id>/K001.001    # 当前 Project
knowledge://global/K001.001          # Harness Global
```

禁止把另一个 Project 的私有 Knowledge 装进当前项目 Context。

## 预算

Context Builder 保留：

```text
MUST / MUST_NOT Rule
MUST Gate
required Context item
```

非 required 内容按优先级在预算不足时退出 Frame。

## Context Rules

唯一正式规则源：

```text
agent_harness/project_contract/standards/11_CONTEXT_RECORD_STANDARD_V0_1.md
```

插件内快速入口：`CONTEXT_RULES.md`。

规则核心：

```text
固定结构
短句单义
Confirmed / Assumption 分离
稳定引用优先
当前状态替换旧状态
Recent Tail 有上限
Context 可重建，不保存完整历史
```

Context Lifecycle 接口见 `CONTEXT_LIFECYCLE_INTERFACE.md`。
