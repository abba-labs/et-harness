# 公共插件 ↔ Project Plugin 协议设计

> 版本：v0.1  
> 目标：定义公共管理插件如何以统一方式访问任意 Project Plugin。  
> 核心原则：**Agent 做理解和决策；公共插件做路由、检索、工具和强制约束；Project Plugin 提供项目私有数据。**

---

# 1. 为什么需要 Contract

公共插件不能知道：

```text
ET-TOOL 的目录在哪里
ET6002 是什么
GUI 规则放在哪个文件
某个项目使用 CMake 还是其他构建系统
```

否则每接一个项目都要修改公共插件。

因此统一采用：

```text
Agent
  ↓
Public Plugin
  ↓
Project Contract
  ↓
Project Plugin
```

Project Plugin 只需要按 Contract 暴露项目私有资源。

---

# 2. 两级 Contract

## 2.1 Project Contract

所有 Project Plugin 必须实现的最小公共协议。

```text
ProjectContract
├ project_id
├ display_name
├ project_type
├ project_root
├ root_markers
├ resource_sources
├ supported_capabilities
└ adapter_sources
```

加载后形成：

```text
ProjectContext
```

公共插件统一从 Project Manager 获取 ProjectContext。

---

## 2.2 专业 Resource Contract

每个公共插件定义自己需要的专业接口：

```text
Architecture Navigator → ArchitectureSource Contract
Rule Manager           → RuleSource Contract
Knowledge Manager      → KnowledgeSource Contract
Gate Manager           → GateSource Contract
Tool System            → Adapter Contract
```

Project Plugin 可以：

```text
直接提供标准文件资源
或
通过 Adapter 提供特殊资源
```

---

# 3. ProjectContext

建议最小模型：

```yaml
project_id: et-tool
display_name: ET-TOOL
project_type: software-hardware-tool
project_root: /repo/et-tool

resources:
  architecture: architecture/
  rules: rules/
  knowledge: knowledge/
  gates: gates/

adapters:
  source: optional
  build: optional
  test: optional
  hardware: optional
```

公共插件不得自己拼接项目私有路径。

只能通过 ProjectContext 获取资源入口。

---

# 4. Project Manager Contract

Project Manager 是所有项目访问的第一入口。

提供给 Agent：

```text
list_projects()
resolve_project(query)
get_project_context(project_id)
get_project_capabilities(project_id)
```

它负责：

```text
项目发现
项目注册
ProjectContext 返回
项目生命周期
```

它不负责判断用户任务最终应该修改哪个模块。

---

# 5. ArchitectureSource Contract

Project Plugin 提供项目私有架构资源。

最小内容：

```text
项目总体架构入口
模块清单
模块别名 / 关键词
模块关系
资源 / 源码入口
```

Architecture Navigator 给 Agent 提供：

```text
list_modules(project)
search_architecture(project, query)
get_module(project, module_id)
locate_resources(project, query_or_module)
```

返回的是：

```text
候选模块
候选架构资料
候选源码 / 资源入口
匹配依据
```

最终理解和选择由 Agent 完成。

---

# 6. RuleSource Contract

Rule 内容属于项目私有数据。

Rule 至少具有：

```text
rule_id
scope
module / capability / concern
tags / aliases
resource bindings
priority
status
version
content_location
```

Rule Manager 给 Agent 提供：

```text
search_rules(project, query, scope?)
list_rules(project, scope?)
get_rule(project, rule_id)
trace_rules(project, resource)
```

典型链路：

```text
Agent 已理解任务约为 GUI / visual-style
        ↓
search_rules(et-tool, "GUI visual style", scope)
        ↓
Rule Manager 查询 ET-TOOL RuleSource
        ↓
返回少量 Rule 候选
        ↓
Agent 阅读并判断最终适用规则
```

Rule Manager 的任务是快速定位，不是替 Agent 完成规则语义判断。

---

# 7. KnowledgeSource Contract

每个 Project Plugin 拥有独立私有 Knowledge Base。

项目提供：

```text
knowledge namespace
storage / source location
knowledge metadata
read/write policy
```

Knowledge Manager 提供：

```text
search_knowledge(project, query, scope?)
get_knowledge(project, knowledge_id)
list_related(project, object_id)
record_candidate(project, candidate)
update_knowledge(project, change)
```

知识内容可以包括：

```text
历史经验
设计决策
已知问题
模块背景
调试经验
历史变更结果
开发注意事项
```

知识管理方式必须公共，知识内容必须 Project-scoped。

---

# 8. GateSource Contract

Gate Definition 属于项目私有数据。

项目定义：

```text
什么范围的修改
必须执行哪些门禁
门禁是否 mandatory
门禁依赖什么环境
调用什么 Adapter / Tool
```

例如：

```yaml
gate_id: ettool.gui.basic
scope:
  module: gui
mandatory: true
steps:
  - build
  - gui-unit-test
```

Gate Manager 提供：

```text
resolve_gates(project, task_scope, change_scope)
get_gate(project, gate_id)
run_gate(project, gate_id)
run_required_gates(project, change_scope)
```

Agent 可以分析失败并修改代码，但 mandatory gate 不能被普通任务直接绕过。

---

# 9. Adapter Contract

默认项目应尽量不写代码 Adapter。

只有标准资源和 Tool Plugin 无法满足时才提供，例如：

```text
特殊 Build Adapter
特殊 Test Adapter
特殊 Hardware Adapter
特殊 Source Resolver
特殊配置系统 Adapter
```

公共插件只依赖 Adapter Contract，不依赖项目具体实现。

---

# 10. Context Builder 的位置

Context Builder 不拥有项目私有数据。

它接受 Agent 已经选择或请求的资源：

```text
Architecture candidates
Rules
Knowledge
Current source/resource snippets
Gate hints
```

然后提供：

```text
assemble_context(...)
trim_context(...)
package_handoff(...)
```

Context Builder 负责整理上下文，不负责替 Agent 决定任务是什么。

---

# 11. Evidence / State Contract

Evidence / State Manager 是公共插件。

项目可以定义项目专属状态字段或证据要求，但统一管理机制公共。

接口方向：

```text
record_evidence(project, task, evidence)
read_state(project, scope)
update_state(project, scope, state_change)
```

所有数据必须带：

```text
project_id
task_id
scope
source
result / state
provenance
```

---

# 12. Experience / Memory Contract

任务完成后：

```text
Agent
  ↓
总结本次开发中的新经验
  ↓
Experience Manager
  ↓
去重 / 分类 / 关联
  ↓
Knowledge Candidate
  ↓
写回当前 Project Knowledge Base
```

公共插件管理：

```text
经验提议
经验去重
关联已有知识
版本
候选晋级
```

项目只拥有自己的经验内容。

---

# 13. 完整调用例子：修改 ET-TOOL UI 设计风格

```text
用户需求
“修改 ET-TOOL 的 UI 设计风格”
        ↓
Agent 理解原始需求
        ↓
Project Manager.list_projects()
        ↓
Agent 选择 et-tool
        ↓
Project Manager.get_project_context(et-tool)
        ↓
Architecture Navigator.search_architecture(
  project=et-tool,
  query="UI design style"
)
        ↓
返回 GUI / theme / layout / source 候选
        ↓
Agent 阅读架构并细化任务
        ↓
Rule Manager.search_rules(
  project=et-tool,
  query="GUI visual style theme",
  scope=<Agent理解后的scope>
)
        ↓
Agent 阅读相关 Rule
        ↓
Knowledge Manager.search_knowledge(...)
        ↓
Agent 获取历史经验
        ↓
Context Builder.assemble_context(...)
        ↓
Agent 修改代码
        ↓
Gate Manager.resolve_gates(...)
        ↓
Gate Manager.run_required_gates(...)
        ↓
Agent 根据失败继续修复
        ↓
Evidence Manager.record_evidence(...)
        ↓
Experience Manager.record_candidate(...)
```

整个过程中：

```text
Agent = 理解 / 判断 / 选择 / 开发
Plugin = 查询 / 路由 / 读取 / 执行 / 记录
Project Plugin = 私有数据源
```

---

# 14. 新项目最小接入要求

第一版目标是让一个普通项目只需：

```text
project.yaml
architecture/
rules/
knowledge/
gates/
```

即可被公共插件使用。

`adapters/` 为可选。

禁止要求每个项目复制一套：

```text
ProjectService
Rule Manager
Knowledge Manager
Context Builder
Gate Engine
```

这些都必须公共复用。

---

# 15. 设计验收标准

这套 Contract 只有满足以下条件才算合理：

```text
1. 公共插件代码中没有 ET-TOOL 专有逻辑；
2. ET-TOOL 与 Project-B 可以使用同一套公共插件；
3. 普通项目无需写 TypeScript 即可接入；
4. 特殊项目只通过 Adapter 扩展；
5. Agent 可以从模糊人类需求逐步调用工具形成自己的任务理解；
6. Rule Manager / Navigator 返回候选，不冒充 Agent 做最终语义判断；
7. 项目私有规则、知识和门禁不能串到其他项目；
8. Mandatory Gate 可以被 Governance 强制执行；
9. 开发经验可以回写当前项目私有知识库。
```

这份协议是后续公共插件和所有 Project Plugin 的统一连接边界。
