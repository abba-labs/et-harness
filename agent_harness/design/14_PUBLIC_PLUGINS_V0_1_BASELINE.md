# Public Plugins v0.1 Baseline

> 状态：IMPLEMENTATION BASELINE  
> 原则：**Agent 是实施主体；公共插件提供标准、路由、工具和硬约束；Project Plugin 提供符合规范的私有内容。**

## 1. 第一版公共插件

| 插件 | 核心职责 | 是否定义 Project Interface |
|---|---|---|
| Project Manager | 项目发现、注册、ProjectContext | 是：project.yaml |
| Architecture Navigator | 架构接口校验与高速路由 | 是：architecture-v0.1 |
| Rule Manager | 规则接口校验与高速路由 | 是：rule-v0.1 |
| Knowledge Manager | 正式知识校验与 validated-first 路由 | 是：knowledge-v0.1 |
| Gate Manager | Gate 校验、路由、Execution Plan | 是：gate-v0.1 |
| Context Builder | 组装 Agent 已选择的最小上下文 | 否 |
| Evidence / State Manager | 不可变 Evidence + 版本化 State | 否 |
| Experience / Memory Manager | 经验候选、跨任务记忆、受控 Knowledge 晋级 | 否 |

## 2. Project-facing Router 统一模型

```text
Project Resource
   ↓
00_INDEX Front Matter
   ↓
NNN File
   ↓
Numbered Tree
   ↓
Stable Node ID
   ↓
Route Cache
```

接入/变更阶段重校验；Agent 高频查询只走 Cache。

不符合接口标准：

```text
REJECT
```

## 3. Agent 工作链

```text
Human Task
   ↓
Agent
   ↓
Project Manager
   ↓
Architecture Navigator
   ↓
Agent 理解任务归属
   ↓
Rule / Knowledge / Gate Router
   ↓
Agent 选择相关 Node
   ↓
Context Builder
   ↓
Agent 开发 / 调用 Tool
   ↓
Evidence / State
   ↓
Agent 总结经验
   ↓
Experience / Memory
   ↓
显式晋级到 Knowledge
```

每一步的理解、判断、开发和最终语义选择仍由 Agent 完成。

## 4. 关键可靠性约束

```text
Project ID 隔离
Stable Node ID
Index ↔ File 一致性
Router Cache 失效策略
MUST Rule 不静默裁剪
MUST Gate 不静默绕过
Knowledge 默认只返回 VALIDATED
Evidence append-only
State optimistic version
Experience 必须引用 Evidence
Knowledge 晋级必须显式指定 K 地址
Knowledge 写入失败必须回滚
```

## 5. 当前不属于公共插件第一版范围

```text
项目具体 Architecture 内容
项目具体 Rule 内容
项目具体 Knowledge 内容
项目具体 Gate 内容
具体编译器 / J-Link / Vivado / 仪器 Tool Plugin
LLM 自主任务理解算法
插件市场 / 推荐算法
复杂多 Agent Workflow
```

这些在公共 baseline 通过以后再继续。

## 6. ET-TOOL 边界

ET-TOOL 当前只保留：

```text
project.yaml
architecture/00_INDEX.md  files: []
rules/00_INDEX.md         files: []
knowledge/00_INDEX.md     files: []
gates/00_INDEX.md         files: []
```

公共插件总 Gate 关闭以前，不填 ET-TOOL 项目内容。

## 7. 公共 Baseline 验收

最终必须用一个完全虚拟项目完成：

```text
项目注册
→ Architecture 路由
→ Rule 路由
→ Knowledge 路由
→ Gate 路由
→ Context Pack
→ Agent 模拟执行 Tool
→ Evidence
→ State
→ Experience Candidate
→ Memory 查询
→ Knowledge 晋级
→ 再次 Knowledge 校验
→ 插件卸载清理
```

最终唯一关闭标记：

```text
PHASE3_PUBLIC_PLUGINS_V0_1_INTEGRATION=PASS
```

在真实 Gate 未执行前不得伪造该 PASS。
