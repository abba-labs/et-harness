# Phase 2：ET-TOOL 轻量 Project Plugin 试点

> 版本：v0.5  
> 上游：Phase 1 `PHASE1_REAL_DSH_INTEGRATION=PASS`  
> 当前状态：**DESIGN UPDATED；现有 0.2.0 Skeleton 已验证基础 Project 生命周期，但仍需按新 Contract 收敛。**

---

# 1. Phase 2 的正确目标

Phase 2 不负责建设完整 ET-TOOL 知识体系。

真正目标是：

> **用 ET-TOOL 验证一套足够轻的 Project Plugin 接入方式。**

Project Plugin 只回答：

```text
我是谁？
项目根在哪里？
架构资料在哪里？
项目规则在哪里？
私有知识库在哪里？
项目门禁定义在哪里？
有没有特殊 Adapter？
```

项目插件不负责自己实现：

```text
Rule Manager
Knowledge Manager
Context Builder
Gate Engine
Evidence Manager
Memory Manager
```

这些属于公共插件。

---

# 2. 系统关系

```text
Agent
  ↓
Public Management Plugins
  ↓
Project Contract / ProjectContext
  ↓
ET-TOOL Project Plugin
  ↓
ET-TOOL 私有项目内容
```

ET-TOOL 是第一套实例，不是公共框架本身。

---

# 3. ET-TOOL Project Plugin 最终目标形态

推荐收敛到：

```text
projects/et_tool/
├── project.yaml
├── architecture/
├── rules/
├── knowledge/
├── gates/
└── adapters/          # 可选
```

职责：

```text
project.yaml   项目身份、根目录、资源入口、能力声明
architecture/  ET-TOOL 私有架构与模块地图
rules/         ET-TOOL 私有开发规则
a knowledge/   ET-TOOL 私有历史知识与经验
gates/         ET-TOOL 私有门禁定义
adapters/      标准公共工具无法满足时的特殊适配
```

普通项目应尽量做到：

```text
配置 + 私有资料
```

即可接入，不要求复制一套 TypeScript Service。

---

# 4. 当前 0.2.0 Skeleton 的定位

当前代码已经验证：

```text
project.et-tool 可注册
ctx.etToolProject 可暴露
Project Root 可发现
Project Provider 生命周期可运行
旧文档可以与新入口隔离
```

当前存在的 14 层：

```text
project
facts
navigation
context
rules
playbooks
tests
validation
evidence
memory
state
changes
decisions
source_map
```

现在重新定义为：

> **过渡性 Knowledge Skeleton，不是未来所有 Project Plugin 的强制公共结构。**

原因：其中混合了两类东西。

项目私有数据：

```text
Architecture / Facts
Rules
Knowledge / Decisions / Experience
Gate / Test Definitions
```

公共管理机制：

```text
Navigation
Context Assembly
Validation Execution
Evidence Management
Memory Management
State Management
Change Management
```

后者应该逐步迁移到公共插件职责。

---

# 5. Project Contract

Phase 2 后续工程实现必须以：

```text
05_PUBLIC_PLUGIN_PROJECT_CONTRACT.md
```

为接口边界。

最小 ProjectContext：

```text
project_id
project_root
project_type
resource_sources
supported_capabilities
adapter_sources
```

公共插件禁止硬编码 ET-TOOL 私有目录和业务名称。

---

# 6. Agent 使用 ET-TOOL 的目标体验

例如用户说：

```text
修改 ET-TOOL 的 UI 设计风格
```

正确链路：

```text
Agent
 ↓
Project Manager
→ 找到 et-tool / ProjectContext
 ↓
Architecture Navigator
→ 返回 UI / GUI 架构和源码候选
 ↓
Agent 阅读并细化任务
 ↓
Rule Manager
→ 返回 ET-TOOL UI 相关 Rule 候选
 ↓
Agent 阅读规则
 ↓
Knowledge Manager
→ 返回历史经验
 ↓
Agent 开发
 ↓
Gate Manager
→ 根据 ET-TOOL gates 执行必需门禁
 ↓
Agent 修复
 ↓
Experience Manager
→ 写回 ET-TOOL 私有 Knowledge Base
```

Phase 2 的 Project Plugin 负责提供这些私有数据入口，不负责替 Agent 完成上述理解过程。

---

# 7. Phase 2 新验收标准

Phase 2 最终关闭时必须证明：

```text
1. ET-TOOL 可以通过标准 Project Contract 注册；
2. 可以获得标准 ProjectContext；
3. ET-TOOL 私有 Architecture / Rules / Knowledge / Gates 都有稳定入口；
4. 公共接口中不存在 ET3101 / ET6002 / CAN / GUI 等硬编码业务逻辑；
5. 普通项目接入不要求复制 ET-TOOL Service 代码；
6. Optional Adapter 可以扩展特殊项目能力；
7. Project 生命周期仍由 DSH/Cordis + Governance Core 正确管理；
8. Project 私有数据与公共管理机制边界清晰。
```

当前已有运行证据仍可证明：

```text
Project registration
Provider registration
ctx.etToolProject
unload cleanup
```

但新的 Project Contract 仍需实现和验证。

因此当前正式状态：

```text
PHASE 2 = CONTRACT REFACTOR REQUIRED
```

---

# 8. Phase 2 完成后的下一步

Phase 3 不再直接围绕 ET-TOOL 写一堆项目专属 Provider。

而是实现公共管理插件：

```text
Project Manager
Architecture Navigator
Rule Manager
Knowledge Manager
Context Builder
Gate / Validation Manager
Evidence / State Manager
Experience / Memory Manager
```

然后继续用 ET-TOOL 作为第一套真实数据源验证这些公共插件。

核心原则：

> **Project Plugin 越薄越好；公共管理能力越通用越好；最终理解、判断和开发始终由 Agent 完成。**
