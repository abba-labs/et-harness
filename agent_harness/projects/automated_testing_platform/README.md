# Automated Testing Platform Project Plugin

本目录是 `Automated Testing Platform` 接入 ET Harness 公共插件体系的 Project Plugin。

## 定位

```text
Automated Testing Platform
= 继续拥有项目代码、活动规则、Task Context Compiler、测试和业务事实

本 Project Plugin
= 项目标识
+ Architecture / Rule / Knowledge / Gate 标准投影
+ 项目级 context.contribute Provider

ET Harness 公共插件
= Project 识别、通用路由、Context 承载、Evidence、Reflection 与 Closure 治理
```

本插件不复制项目实现，也不形成第二套项目规则或第二套 Task Context 系统。

## Context Contributor

项目 Manifest 显式声明：

```yaml
adapters:
  task_context:
    provider: project.automated-testing-platform.context
    capability: context.contribute
```

当公共 Harness 识别到 ATP IP 分析任务后，Provider 会：

1. 从项目已有芯片注册表与原始任务解析 chip / ip；
2. 调用 `tools/governance/compile_task_context.py`；
3. 保存项目已有 `project-governance/runtime/current_task_context.json`；
4. 将 must_read、Rule Owner、A/R/K/G、读写范围、验证义务和项目输出合同贡献给公共 Context；
5. 在后续文档修改路由中校验并复用同一 Task Context，而不是重新编译第二份上下文；
6. 参数不确定、Compiler 失败、Scope 非法或引用资源不存在时失败关闭。

Provider 不执行 eTimer 业务分析，不读取私有外部资料，也不替 Agent 生成结论。它只把项目自己的确定性导航和约束交给受治理 Agent。

## 权威来源

项目事实和项目规则仍由以下资源拥有：

```text
AGENTS.md
project-governance/system-map.yaml
project-governance/modules/*.yaml
project-governance/ip-analysis-sources.yaml
report/design/rule_owner_catalog.yaml
report/design/rules/Rxxx_*.md
tools/governance/compile_task_context.py
当前源码与测试
```

本目录中的 Architecture 和 Rule 文件仅提供短路由。Knowledge 保存带 K-ID、状态、Scope 和 Provenance 的短事实。

## 明确边界

本阶段提供的是语义治理 Context Contribution，不提供或冒充：

```text
Build Adapter
Firmware Adapter
J-Link / Flash / FPGA Adapter
Hardware Evidence Adapter
ChatGPT Host Tool Gateway
```

连接器访问必须形成 Source Receipt；没有机械 Tool Bridge 时，只能声明语义治理，不能声明每次工具调用都被 Harness 机械拦截。

## 分支模型

```text
main
= 公共 Harness 唯一上游

project/automated-testing-platform
= 公共 Harness + ATP 完整项目 + 本 Project Plugin

feat/atp-context-contributor-clean-v0.1
= 当前干净 Provider 实现与聚焦测试分支
```

项目分支定期合并 `main`，不得整体反向合入 `main`。
