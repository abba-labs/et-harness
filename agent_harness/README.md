# 智能体支撑框架

本目录用于开发一套与具体项目解耦、以插件化为核心的通用智能体支撑框架。

ET-TOOL 作为第一套项目插件和试点工程，用于验证总线、插件协议、治理体系、上下文记忆、测试知识、持续集成和自我迭代等能力。

## 当前生产任务入口

当前优先级已经从“继续测试 Framework 本身”切换为“使用现有 ET Harness / ATP Project Plugin 支撑真实芯片 IP 分析与测试开发”。

下一对话、下一 Host 或新的 Agent 在继续 ET6801 IP 工作前，先读取：

```text
progress_context/20260901_IP_ANALYSIS_AND_TEST_DEVELOPMENT_HANDOFF_V0_1.md
```

该文档包含：

- 当前 ET Harness / ATP 基线；
- 当前哪些 Project Plugin / Rule / Knowledge / Context / Source Registry 能力可以直接使用；
- 哪些 Framework 问题暂时冻结、不阻塞生产任务；
- 统一 IP 分析流程；
- ET6801 XBAR 当前证据与已知冲突；
- XBAR Feature / Case / 测试代码的下一步实施顺序。

核心执行原则：

> Framework 作为治理基础设施使用；IP 分析正确性、测试设计质量和测试代码可执行性优先。不要等待 Portable Runtime 完成后才继续真实 IP 工作。

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
