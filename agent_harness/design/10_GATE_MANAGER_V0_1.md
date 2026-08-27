# Gate Manager v0.1

> 状态：IMPLEMENTATION BASELINE  
> 公共能力：`gate.navigate`  
> 项目接口：`gate-v0.1`

## 1. 定位

Gate Manager 是项目验证定义的公共规范制定者和 Router。

它负责：

```text
Gate 接口校验
Gate Tree Cache
稳定 G ID 寻址
自然语言 / Change Scope 候选路由
Execution Plan 输出
```

它不负责：

```text
规定项目有哪些 Gate
直接执行编译器 / 测试工具 / 硬件工具
替 Agent 判断最终适用 Gate
记录最终 Evidence
```

## 2. 标准链路

```text
Agent
  ↓
Gate Manager
  ↓
Project Manager / ProjectContext
  ↓
gates/00_INDEX.md
  ↓
Gxxx YAML
  ↓
Gate Tree Cache
  ↓
Gate Candidate / Execution Plan
  ↓
Agent 调用 Tool Capability
```

## 3. Mandatory 语义

```text
MUST
MAY
```

`MUST` 一旦确认适用于 Change，普通 Agent 不能自行跳过。

真正的完成状态和例外授权由 Governance + Evidence/State 层负责。

## 4. Execution Plan

```text
Gate ID
Level
When
Steps[]
Pass
Refs[]
```

Step 只引用稳定 Tool Capability。

## 5. API

```text
refreshProject(projectId)
getIndex(projectId)
listFiles(projectId)
searchGates(request)
getNode(projectId, gateId)
listChildren(projectId, nodeId)
getExecutionPlan(projectId, gateId)
removeProject(projectId)
```

## 6. ET-TOOL 边界

ET-TOOL 当前仍只有空 `gates/00_INDEX.md`。

本阶段不定义 ET-TOOL 的任何具体 Gate。

## 7. 最终 Gate

```text
PHASE3_GATE_MANAGER_INTEGRATION=PASS
```

仅真实 Cordis Gate 运行成功后允许记录 PASS。
