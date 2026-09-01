# 智能体支撑框架

本目录用于开发一套与具体项目解耦、以插件化为核心的通用智能体支撑框架。

ET-TOOL 作为第一套项目插件和试点工程，用于验证总线、插件协议、治理体系、上下文记忆、测试知识、持续集成和自我迭代等能力。

## First read: Real Requirements

在设计或修改某项 Host / Agent / Project Plugin 能力前，先阅读与任务相关的真实需求：

```text
requirements/
```

这里记录“真正要做什么、为什么要做、哪些方向已经明确否决”，避免新 Agent 只根据历史实现或阶段性设计反推用户目标。

当前 ChatGPT 网页版 Host 的真实定位见：

```text
requirements/001_WEB_CHATGPT_HOST_REAL_REQUIREMENTS.md
```

核心原则：

- 一切皆插件；
- 插件支持递归扩展、安装、卸载、升级和替换；
- 插件通过统一总线连接；
- 总线只负责快速发现、寻址、连接和传输；
- 不符合系统协议、标准和治理规则的插件禁止接入。

## Knowledge scopes

Harness 直接拥有一套与项目生命周期解耦的共享知识库：

```text
agent_harness/global_knowledge/
```

公共 `Knowledge Manager` 插件统一管理两种 Scope：

```text
Global Knowledge  -> Harness 共享、跨项目复用
Project Knowledge -> Project Plugin 私有、随项目装卸
```

默认知识归属原则：离开当前项目仍成立的知识进入 Global；只有项目实现、路径、设计决策或项目特有限制进入 Project。

完整引用：

```text
knowledge://global/K...
knowledge://project/<project-id>/K...
```

## Optional Observation Plane

框架提供可选的轻量效率观测层：

```text
Execution Plane
Context ↔ Agent ↔ Public Plugins ↔ Project / Tools
                  │
                  └── optional framework-metric-v0.1
                               ↓
                    Framework Efficiency Observer
```

硬边界：

```text
主框架不依赖 Observer
Observer 卸载后主框架行为不变
Observer 故障不得阻塞 Agent
运行时只采轻量元数据
复杂分析在任务结束后进行
```

设计见：

```text
design/20_FRAMEWORK_EFFICIENCY_OBSERVER_V0_1.md
```
