# Project Contract v0.1 — 场景验证

> 状态：VALIDATION  
> 目的：验证 Project Contract v0.1 是否既能服务 ET-TOOL，也能服务完全不同类型项目，而不把 Agent 的语义理解固化进框架。

---

## 1. 场景 A：ET-TOOL UI 设计风格修改

用户输入：

```text
修改 ET-TOOL 的 UI 设计风格
```

### Step 1 — Agent 找项目

```text
Agent
→ Project Manager.list_projects()
→ Project Manager.get_project_context(et-tool)
```

Project Manager 只负责返回：

```text
project_id
project_root
architecture handle
rules handle
knowledge handle
gates handle
```

不判断 UI 属于哪里。

### Step 2 — Agent 借助 Architecture Navigator 理解项目

```text
Architecture Navigator.search_architecture(
  project_id=et-tool,
  query="UI 设计风格"
)
```

返回候选：

```text
arch.gui
arch.gui.theme
arch.gui.layout
```

并带：

```text
project_id
location
relevance
match_reasons
provenance
```

Agent 阅读候选与相关源码后形成自己的理解：

```text
module = gui
concern = visual-style
可能影响 theme/layout
```

### Step 3 — Agent 找规则

```text
Rule Manager.search_rules(
  project_id=et-tool,
  query="GUI visual style theme layout",
  scope={module: gui, concern: visual-style}
)
```

Rule Manager 返回少量候选规则。

Agent 阅读规则并决定真正适用范围。

### Step 4 — Agent 查项目经验

```text
Knowledge Manager.search_knowledge(
  project_id=et-tool,
  query="GUI 视觉风格 theme layout 历史经验",
  scope={module: gui}
)
```

返回历史经验 / 决策 / 已知问题候选。

### Step 5 — Agent 开发

Agent 根据：

```text
架构理解
规则
历史知识
真实源码
```

自己完成修改。

### Step 6 — Agent 查门禁

```text
Gate Manager.resolve_gates(
  project_id=et-tool,
  change_scope={module: gui, concern: visual-style}
)
```

项目 GateSource 决定这类修改要求哪些门禁。

公共 Gate Manager 负责执行和标准化结果。

### Step 7 — 经验写回

任务完成后 Agent 总结新经验：

```text
Experience / Knowledge Manager
→ record_candidate(project_id=et-tool, ...)
```

经验进入 ET-TOOL 私有 Knowledge Base。

### 场景 A 结论

```text
PASS
```

Contract 不要求用户一开始给出完整 TaskSpec；Agent 可以通过公共插件逐步探索、理解、收敛。

---

## 2. 场景 B：FPGA / RTL 验证项目

虚拟项目：

```text
project_id = fpga-soc-validation
```

项目没有 ET-TOOL 的：

```text
GUI
CLI
CAN
source/apps
CMake
```

它的资源可能是：

```text
rtl/
tb/
constraints/
scripts/
wave/
```

用户输入：

```text
给 DDR 控制器增加一个 ILA trigger，方便定位偶发读超时
```

### project.yaml

```yaml
contract_version: "0.1"

project:
  id: fpga-soc-validation
  name: FPGA SoC Validation
  type: fpga-validation

root:
  markers:
    - top.xpr

resources:
  architecture:
    path: architecture/
  rules:
    path: rules/
  knowledge:
    path: knowledge/
  gates:
    path: gates/

adapters:
  hardware:
    provider: fpga.vivado
```

### Agent 使用相同公共插件

```text
Project Manager
→ 找到 fpga-soc-validation

Architecture Navigator.search_architecture(
  query="DDR ILA trigger read timeout"
)
→ 返回 DDR / ILA / debug instrumentation 架构候选

Rule Manager.search_rules(...)
→ 返回 ILA 插入、时钟域、资源预算、debug build 规则

Knowledge Manager.search_knowledge(...)
→ 返回历史 timeout / waveform / trigger 经验

Agent 修改 RTL / debug 配置

Gate Manager.resolve_gates(...)
→ synthesis
→ implementation
→ timing
→ bitstream
→ hardware smoke
```

### 场景 B 结论

```text
PASS
```

公共插件接口不依赖软件项目目录结构，也不依赖 ET-TOOL 领域词汇。

---

## 3. 两个场景共同证明了什么

Project Contract 只需要知道：

```text
Project 是谁
Architecture 在哪里
Rules 在哪里
Knowledge 在哪里
Gates 在哪里
特殊能力 Adapter 在哪里
```

公共插件统一提供：

```text
search
get
list
locate
resolve
run
record
```

Agent 负责：

```text
理解
判断
继续查询
阅读
开发
失败分析
经验总结
```

因此不需要在 Contract 中定义：

```text
ET6002
GUI
CAN
DDR
ILA
RTL
```

这些都属于具体 Project 的私有知识。

---

## 4. 验证中确认的最小公共语义

v0.1 只保留以下跨项目公共概念：

```text
project
query
scope
candidate
resource
rule
knowledge
gate
adapter
provenance
```

其中 `scope` 是开放 hint，不建立全行业固定枚举。

这样可以避免 Generic Framework 被某一类项目绑死。

---

## 5. 当前结论

Project Contract v0.1 在两个差异很大的场景下都能工作：

```text
ET-TOOL 软件/硬件工具项目      PASS
FPGA / RTL 验证项目             PASS
```

没有发现必须写入公共 Contract 的 ET-TOOL 专有字段。

因此下一步可以开始实现最小代码骨架：

```text
Project Contract Schema
        ↓
Project Manager
        ↓
Standard File Resource Provider
        ↓
Architecture / Rule / Knowledge / Gate 公共查询接口
```

第一版仍然坚持：

> 不做自动语义决策；只给 Agent 提供快速、准确、可追溯的项目路由能力。