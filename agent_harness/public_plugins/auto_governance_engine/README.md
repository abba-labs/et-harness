# Public Auto Governance Engine v0.1

Host-independent 自动治理引擎。

它只负责治理业务，不监听任何 Agent/Harness 事件，也不注册模型可见 Tool。

```text
Host / Model Adapter
        ↓
Governance Runtime
        ↓
Auto Governance Engine
        ↓
Project / Context / A-R-K-G / Gate / Evidence
```

## 负责

- Project 解析；
- Context Task 建立 / 恢复；
- Architecture / Rule / Knowledge / Gate 自动路由；
- Context Envelope 构建；
- Tool failure / code mutation 观察后的 Context 更新；
- Code Gate Review Packet 准备；
- build/test preflight；
- Review PASS/BLOCK 记录；
- Task complete / pause。

显式 `role: REVIEW` 的 Gate Step 会在 Task bootstrap 和后续路由扩展时检查当前
Project 或公共 Review Provider 是否真实可用；缺失时立即失败，不再等到任务后段。
显式 `role: EVIDENCE_PRODUCER` 的 Step 不会被误建为 Review Packet。它只能通过
Governance Runtime 传入的受信 Gate/Step 绑定提前执行，普通 build/test 仍保持阻断。

## 不负责

- 不监听 `agent/pre-step` / `session/event` / `tools/result`；
- 不知道 DSH / Codex / Claude / GPT 的事件格式；
- 不生成 Harness message/source 结构；
- 不注册 `ctx.tools`；
- 不执行 Unified Reflection；
- 不执行 Turn Closure；
- 不管理外部工具插件。

Unified Reflection / Turn Closure 由上层 `Governance Runtime` 强制驱动。

## Host-neutral API

```text
resolveProject()
bootstrapTask()
buildContextEnvelope()
observeToolResult()
guardAction()
recordReviewDecision()
completeTask()
pauseTask()
getTaskStatus()
```

`AutoGovernanceContextEnvelope.text` 是治理 Context 的纯文本表达，不带任何 Host message metadata。具体 Host 如何把它交给 Agent，由 Host Adapter 决定。
