# Framework Efficiency Observer v0.1

可拔插的轻量 Framework Efficiency Observer。

## 核心原则

```text
Execution Plane  ──optional metric event──→  Observer
Observer         ───────────X──────────────→  Execution Plane
```

硬要求：

```text
主框架不依赖 Observer
Observer 未安装时框架行为不变
Observer 卸载后框架行为不变
Observer 异常不得阻塞 Agent
监听回调不做文件 I/O
缓冲区满时丢 Metrics，不反压主链
复杂统计只在任务结束后离线执行
不保存 Context 正文 / Tool 大输出 / 推理过程
```

## 零观测 Fast Path

Observer 未安装时：

```text
observeFrameworkOperation()
→ 只检查 metricsActive == false
→ 直接执行原 action
```

不会执行：

```text
Date.now()
summary 计算
framework/metric 广播
磁盘 I/O
```

Observer 加载时由 Observer 自己激活 metrics；卸载时立即关闭。

## 运行时采集

主框架通过 Governance Core 的：

```text
emitFrameworkMetric(ctx, event)
```

发送低频 `framework-metric-v0.1` 事件。

Observer 热路径只监听这一种低频事件：

```text
framework/metric
→ bounded memory buffer
→ async batch append
→ framework-events.jsonl
```

**Observer 不实时监听 `session/event`。**

原因：`assistant/chunk` 属于高频 Session Event；为了不增加 Agent 长任务的逐 chunk 回调成本，Agent / Token / Tool 指标统一从 Harness 已有 Session Log 在任务结束后离线计算。

默认 Metrics 位置：

```text
$AGENT_HARNESS_METRICS_ROOT/framework-events.jsonl
```

未设置时：

```text
~/.agent-harness/metrics/framework-events.jsonl
```

## 离线分析

框架 Metrics：

```text
frameworkEfficiencyObserver.analyze({
  projectId?,
  taskId?,
  sessionId?,
})
```

Agent Session：

```text
frameworkEfficiencyObserver.analyzeSessionEvents(sessionId, events)
frameworkEfficiencyObserver.analyzeLiveSession(sessionId)
```

Session 离线分析只读取 Harness 已经存在的：

```text
turn/start + turn/end
step/start + step/end
assistant usage
 tool/call + tool/result
```

得到：

```text
Agent turn / step duration
Input / Output / Cache Tokens
Tool call count / duration / failure
```

不持久化 User / Assistant / Reasoning / Tool Result 正文。

## Framework 分析

可汇总：

```text
总事件数
观测时间跨度
各框架 Component 的观测耗时
ERROR / FAIL / MISS 数
各 Operation 调用次数
Context size / over-budget
Route miss
Gate PASS / FAIL
Evidence / State 写入
Knowledge validation / promotion
主要问题提示
```

第一版不生成虚假的“总效率分”。保留原始指标优先。

## 可观测 Component

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

该插件不是公共执行链的必需依赖，不加入主框架的强依赖闭环。
