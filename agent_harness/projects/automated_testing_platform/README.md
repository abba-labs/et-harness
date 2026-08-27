# Automated Testing Platform Project Plugin

本目录是 `Automated Testing Platform` 接入 ET Harness 公共插件体系的最小 Project Plugin。

## 定位

```text
Automated Testing Platform
= 继续拥有项目代码、规则、测试和业务逻辑

本 Project Plugin
= 项目标识 + Architecture / Rule / Knowledge / Gate 标准投影视图

ET Harness 公共插件
= Project 识别、资源路由、Context、Evidence、Reflection 与 Closure 治理
```

本插件只做识别、路由、引用和 Project-scoped Knowledge 挂载，不复制项目实现，也不形成第二套项目规则。

## 权威来源

项目事实和项目规则仍由以下资源拥有：

```text
AGENTS.md
project-governance/system-map.yaml
project-governance/modules/*.yaml
report/design/rule_owner_catalog.yaml
report/design/rules/Rxxx_*.md
当前源码与测试
```

本目录中的 Architecture 和 Rule 文件仅提供短路由。Knowledge 保存带 K-ID、状态、Scope 和 Provenance 的短事实。

## 明确边界

```yaml
adapters: {}
```

本阶段不提供 Build、Firmware、J-Link、Flash、FPGA、Hardware Evidence 或项目专属 Review Adapter。

## 分支模型

```text
main
= 公共 Harness 唯一上游

project/automated-testing-platform
= 公共 Harness + ATP 完整项目 + 本 Project Plugin

test/automated-testing-platform-harness-integration-v0.1
= 本轮基础接入与测试分支
```

项目分支定期合并 `main`，不得整体反向合入 `main`。
