# ChatGPT Web Host Real Requirements v0.1

> Status: REAL REQUIREMENT BASELINE  
> Scope: ChatGPT 网页版参与 ET Harness 项目开发、分析、验证与知识/上下文贡献的真实目标  
> This document defines **what we actually want and why**. It is not an implementation plan.

## 1. 一句话目标

ChatGPT 网页版不是 ET Harness 外面的临时工具，而应当成为 **ET Harness 的一种正式 Host 形态**。

它要与 Codex、Claude Code、DeepSeek Harness 等本地 Agent/Harness 使用 **同一个项目、同一套 Project Plugin、同一套 Rules / Knowledge / Context / Evidence / Project Map** 工作。

区别只在治理强度：

```text
Local Host（Codex / Claude / DSH）
    = Framework 可做机械强制治理

ChatGPT Web Host
    = 无法由本地 Harness 机械强制
    = 依赖强模型能力 + Prompt / Requirement / Project Plugin 规则主动遵循同一治理协议
```

**治理语义应尽量一致，强制手段可以不同。**

---

## 2. 为什么必须支持网页版

网页版不是演示场景，而是长期真实工作入口。

实际使用中，本地 Codex / Claude 等 Harness 可能出现：

- 额度耗尽；
- 某一模型暂时不可用；
- 本地环境不方便启动；
- 用户希望直接通过 ChatGPT 网页聊天继续项目开发；
- 某些资料已经通过 ChatGPT 可访问的 GitHub / Google Drive 等工具存在。

此时用户不应该重新解释整个项目，也不应该重新搭建另一套知识、上下文和规则。

目标是：

```text
今天 Codex 做到一半
        ↓
Codex 没额度 / 暂不可用
        ↓
用户打开 ChatGPT Web
        ↓
GPT Web 读取同一个项目状态和 Project Plugin
        ↓
继续原任务或开始新任务
        ↓
产生的代码、Knowledge、Context、Evidence 等继续贡献回同一项目
        ↓
以后 Codex / Claude 再接手时直接继续
```

**Host 可以换，项目大脑不能换。**

---

## 3. 网页版的真实定位

ChatGPT Web 应被视为：

> **First-class Soft-Governed Host**

它不是：

- 只负责回答问题的聊天助手；
- 只把结果提交给本地 Harness 的外部 Worker；
- Mailbox Worker；
- 只产生候选文本、不参与项目治理的旁路 Agent；
- 与 Codex 使用不同项目状态的第二套系统；
- 必须等待本地 Harness 在线才能工作的前端。

它应该具备和本地 Agent 尽可能一致的工作职责：

```text
识别项目
→ 读取 Real Requirements
→ 加载 Project Plugin
→ 获取项目当前 Context / Working Set
→ 路由 Architecture / Rules / Knowledge / Gates
→ 读取 GitHub / Google Drive 等真实资料
→ 分析 / 开发 / Review / 验证
→ 形成 Evidence / Findings / Decisions
→ 更新项目 Context / Knowledge 等共享状态
→ 按同一项目治理语义完成本轮工作
```

---

## 4. 必须共用什么

不同 Host 不允许各自维护一套项目真相。

至少必须共用以下逻辑资源：

### 4.1 Project Plugin

Project Plugin 是项目专业化能力的核心，不属于 Codex、ChatGPT、Claude 或某个模型。

```text
ET Harness
   ↓
Project Plugin
   ├─ Project identity
   ├─ Architecture
   ├─ Rules
   ├─ Knowledge
   ├─ Context contribution
   ├─ Gates / Evidence policy
   └─ Project-specific capability
```

网页版必须按同一个 Project Plugin 理解和执行项目，而不是单独写一套 Web Prompt 复制项目规则。

### 4.2 Rules

网页版和本地 Harness 必须遵循相同项目规则。

Prompt 的作用是让网页版主动执行规则，不是重新定义规则。

### 4.3 Knowledge

网页版读取的项目知识和产生的新知识，必须进入同一 Knowledge 体系；不能存在 `Web Knowledge` 与 `Codex Knowledge` 两套平行库。

### 4.4 Context

网页版开始任务时，应能够恢复项目当前状态、已确认结论、当前问题、Working Set、下一步等；结束后产生的有效进展也应进入同一 Context 体系。

### 4.5 Evidence / Source

GitHub、Google Drive、代码、文档、测试结果等都应继续作为有来源、有版本、有证据等级的项目事实。

网页版不能因为模型能力强就把“推断”替代真实 Evidence。

---

## 5. GitHub 与 Google Drive 的角色

用户的真实项目资料已经大量存在于 GitHub 和 Google Drive。

ChatGPT Web 可以通过自身可用工具读取这些资料，因此网页版完全可以承担真实开发和分析工作。

目标不是把所有数据复制到浏览器，而是让不同 Host 对同一逻辑资源寻址：

```text
GitHub
  - 代码
  - Project Plugin
  - Rules
  - 结构化 Context / Knowledge / Evidence 状态
  - Commit / PR / CI

Google Drive
  - 芯片资料
  - 规格书
  - 设计资料
  - 项目外部文档
  - 其他真实 Source
```

存储位置可以不同，但必须由同一 Project Plugin / Source / Knowledge 体系组织，不能由某个 Host 私有化。

---

## 6. Web 与 Local 的关键差异

最大差异不是能力，而是 **可强制性**。

### Local Host

本地 Harness 可以通过 Runtime、Tool Gateway、Execution Supervisor、Gate 等做机械拦截和验证。

### ChatGPT Web

网页版无法让本地 ET Harness 物理接管 ChatGPT 的工具调用，也无法可靠建立一个长期 Web → Local 的强控制通道。

因此 Web 模式必须接受这个现实：

```text
Framework Hard Enforcement = unavailable / limited
Model + Prompt Semantic Compliance = primary control
Shared Evidence / Project State = truth boundary
```

这不是把网页版降级为旁路 Agent。

它仍然应该执行同一项目流程，只是不能假装拥有本地 Harness 的机械拦截能力。

---

## 7. 已明确否决的方案

以下方向已经与真实需求不符，后续 Agent 不得再次把它们当作默认目标。

### 7.1 Web GPT 通过 Tunnel 直接连接本地 Harness

曾尝试通过 GPT Web / Tunnel / Local Service 建立直接治理通道，最终证明这条路线不可作为可靠架构基础。

**结论：不再把 Web → Local Tunnel 作为网页版成立的前提。**

网页版即使本地 Harness 未在线，也应该能够工作。

### 7.2 把网页版定义为“只提交结果的 External Untrusted Worker”

这会把网页版排除在 Project Plugin、Knowledge、Context 和真实项目工作流之外，违背真实目标。

网页版是 Host，不是结果邮箱。

### 7.3 用 API 模型代替网页版

用户需要的就是 ChatGPT 网页聊天工作方式。

OpenAI API、DeepSeek API 或其他 Model API 可以是其他 Host 的实现方式，但不能替代 ChatGPT Web Host 这个需求本身。

### 7.4 给网页版建立独立 Knowledge / Context

这会导致 Host 切换时迁移、同步和上下文漂移，直接违背 Harness-independent / Model-independent 的目标。

### 7.5 为了治理而禁止网页版继续工作

网页版缺少机械强制并不意味着它只能停止。

真实目标是利用强模型 + Prompt + 共享 Project Plugin 让它继续高质量工作，而不是为了形式上的强制治理牺牲可用性。

---

## 8. Prompt 的正确职责

Prompt 在 Web Host 中非常重要，但职责必须清晰。

Prompt 应负责：

- 告诉模型先读取 Real Requirements；
- 要求识别并加载正确 Project Plugin；
- 要求按项目 Rules / Context / Knowledge 路由工作；
- 要求 Evidence 与推断分离；
- 要求不自造项目事实；
- 要求完成后贡献 Context / Knowledge / Evidence；
- 要求不能把模型自己的“我认为完成了”当成超越项目规则的授权。

Prompt **不应该**：

- 复制整个项目规则体系；
- 变成第二套 Project Plugin；
- 写入大量项目私有知识；
- 假装自己具有本地 Tool Gateway 的机械强制能力。

原则：

> Prompt 负责让 Web Host 主动进入治理体系；Project Plugin 和共享状态负责定义项目本身。

---

## 9. 当前阶段真正要先做什么

当前不要先解决所有未来问题。

优先级是先让 **单个 ChatGPT Web 会话** 能可靠完成最基本的共享项目工作闭环：

```text
1. 找到正确项目
2. 先读 Real Requirements
3. 加载 Project Plugin
4. 恢复当前 Context
5. 路由 Rules / Knowledge / Sources
6. 使用 GitHub / Google Drive 做真实工作
7. 明确 Evidence / Assumption / Finding
8. 把有效成果贡献回同一项目状态
9. 后续 Codex / Claude 能直接继续
```

只要这条链稳定，网页版就真正成为 ET Harness 的可用 Host。

---

## 10. 多 Agent / 多线程问题：已确认，但暂缓

未来一定会出现：

```text
Codex Task A
GPT Web Task B
Claude Task C
另一个 Codex Task D
```

它们同时读写 Knowledge、Context、Evidence 时，会产生：

- 并发更新；
- Context 合并；
- Knowledge 去重；
- 冲突检测；
- 版本基线；
- 多 Agent Contribution Merge。

这是重要问题，但 **不是当前基础 Web Host 闭环的前置条件**。

当前阶段不为它设计复杂 Merge Framework，也不要因为未来并发问题阻塞网页版的基本可用性。

后续应单独立项设计 Multi-Agent Shared State / Merge Protocol。

---

## 11. 成功标准

未来看到这个需求的 Agent，应使用以下标准判断自己是否理解正确。

如果方案满足：

```text
ChatGPT Web 可以独立开始真实项目任务
+ 使用和 Codex 相同的 Project Plugin / Rules / Knowledge / Context
+ 可以访问 GitHub / Google Drive 真实 Source
+ 不依赖本地 Tunnel 在线
+ 不建立 Web 私有项目大脑
+ 能把有效工作贡献回共享项目
+ Host 切换无需重新迁移项目知识
```

则方向正确。

如果方案变成：

```text
Web GPT 只负责聊天
或
Web GPT 只把结果发给本地 Harness
或
必须先连通本地 Harness 才能工作
或
为 Web 单独复制一套规则 / Knowledge / Context
```

则已经偏离真实需求，应立即停止并重新阅读本文。

---

## 12. 最终原则

ET Harness 的目标不是把项目绑定到某个 Agent，而是让不同 Agent / Harness 都能进入同一个项目专业体系。

```text
Model 可替换
Host 可替换
Harness 可替换

Project Plugin 不迁移
Rules 不迁移
Knowledge 不迁移
Context 不迁移
Evidence 不迁移
```

对于 ChatGPT Web：

> **它不是例外，只是一个无法机械强制、但仍然必须完整参与同一项目治理与贡献体系的 Host。**
