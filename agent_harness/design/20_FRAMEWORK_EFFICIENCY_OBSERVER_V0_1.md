# Framework Efficiency Observer v0.1

## 1. 定位

`Framework Efficiency Observer` 是 **可选 Observation Plane**，用于量化 Agent 工作时各框架环节的真实效率。

核心约束：

```text
Observability may observe the Framework.
The Framework must never depend on Observability.
```

因此：

```text
安装 Observer   -> 主框架行为不变
卸载 Observer   -> 主框架行为不变
Observer 故障   -> 主框架继续工作
Metrics 丢失    -> 允许
Agent 被阻塞    -> 禁止
```

---

## 2. 架构位置

```text
                    Execution Plane

Human
  ↓
Context ↔ Agent ↔ Public Plugins ↔ Project / Tools
                    │
                    │ optional low-frequency metric events
                    ↓
             Observation Plane
        ┌────────────────────────────┐
        │ Framework Efficiency       │
        │ Observer                   │
        │                            │
        │ bounded memory buffer      │
        │ async batch writer         │
        │ offline analyzer           │
        └────────────────────────────┘
```

依赖只允许：

```text
Observer -> Governance Core / Cordis
```

禁止：

```text
Project Manager -> Observer
Context Manager -> Observer
Rule Manager -> Observer
Knowledge Manager -> Observer
Gate Manager -> Observer
Agent -> Observer 才能完成任务
```

执行插件只调用 Governance Core 的 fail-open metric helper，不 import / inject Observer。

---

## 3. 零观测 Fast Path

Observer 未安装时：

```text
metricsActive == false
→ observeFrameworkOperation() 直接执行原 action
```

不会执行：

```text
Date.now()
metric summary
framework/metric 广播
Buffer
磁盘 I/O
```

Observer 自己在加载时激活 metrics，卸载时关闭。

这保证：

```text
Observer absent ≈ 原框架执行路径 + 一次极轻布尔判断
```

---

## 4. 热路径原则

Observer 安装后，运行中只允许：

```text
低频 framework operation event
small numeric values
small stable tags
memory push
async batch append
```

禁止：

```text
实时 LLM 分析
读取额外项目文件
复制 Context 正文
复制 Tool 输出正文
复制 Agent 推理
同步磁盘写
复杂聚合
反压 Agent
高频 assistant/chunk 监听
```

Buffer 有上限；满时丢 Metrics，不等待 Agent。

---

## 5. 数据来源

### 5.1 Framework 低频事件

标准：

```text
framework-metric-v0.1
```

当前主要 Component：

```text
project
context
architecture
rule
knowledge
gate
evidence
state
experience
tool
runtime
```

运行时只记录框架操作的：

```text
timestamp
duration
outcome
small counters
project/task/session correlation id
```

### 5.2 Agent / Token / Tool：离线读取 Harness Session Log

**不实时监听 `session/event`。**

任务结束后读取 Harness 已经存在的 Session Events：

```text
turn/start + turn/end       -> Agent turn duration
step/start + step/end       -> Agent step duration
assistant usage             -> Token Usage
tool/call + tool/result     -> Tool duration / failure
```

这样 Agent 运行期不会因为 token-level `assistant/chunk` 增加额外 Observer callback。

只计算数字和小标签，不复制 User / Assistant / Reasoning / Tool Result 正文。

---

## 6. v0.1 可分析问题

```text
Context
- frame size
- omitted count
- over-budget

Architecture / Rule / Gate
- search count
- route miss
- search duration

Gate
- blocking count
- PASS / FAIL

Evidence / State
- write duration
- update count

Knowledge
- validation duration
- READY / BLOCKED / INSUFFICIENT
- promotion duration

Agent Runtime（离线）
- turn / step duration
- input / output / cache tokens

Tools（离线）
- call count
- duration
- failure count
```

目标不是替 Agent 判断，而是回答：

> **当前任务慢在哪里、返工在哪里、路由哪里命中差、Context 哪里膨胀、哪个 Gate 或 Tool 是瓶颈。**

---

## 7. 存储与分析

Framework Metrics 默认存储：

```text
~/.agent-harness/metrics/framework-events.jsonl
```

可用：

```text
AGENT_HARNESS_METRICS_ROOT
AGENT_HARNESS_METRICS_BUFFER
AGENT_HARNESS_METRICS_FLUSH_MS
```

任务结束后：

```text
frameworkEfficiencyObserver.analyze({ projectId?, taskId?, sessionId? })
```

Agent Session：

```text
frameworkEfficiencyObserver.analyzeSessionEvents(sessionId, events)
frameworkEfficiencyObserver.analyzeLiveSession(sessionId)
```

第一版不生成单一“效率分”，优先保留原始指标和问题定位。

---

## 8. 卸载不变量

Observer 必须满足：

```text
Before unload framework result == After unload framework result
```

专门 Integration Gate 验证：

```text
Observer 未安装 -> metrics fast-path OFF
Observer installed -> Router 正常 / metrics ON
Broken metric listener -> Router 仍正常
高频 session/event -> Observer 不实时订阅
Session Log -> 可离线算 Agent / Token / Tool
Observer unloaded -> metrics OFF / Router 结果不变
Observer provider removed -> Core providers 仍存在
```

验收脚本：

```text
agent_harness/validation/phase3_framework_efficiency_observer_v0_1_integration.sh
```

关闭标记：

```text
PHASE3_FRAMEWORK_EFFICIENCY_OBSERVER_V0_1_INTEGRATION=PASS
```
