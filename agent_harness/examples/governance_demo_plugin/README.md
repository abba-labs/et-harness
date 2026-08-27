# 治理接入示例插件

这是 Phase 1 的最小示例插件，只用于验证治理接入链路。

它演示：

```text
DeepSeek Harness 加载插件
→ Cordis 等待 governanceCatalog 服务
→ 插件提交治理清单
→ 治理目录完成准入
→ 插件登记 rule.resolve Provider
→ 插件卸载
→ Provider 撤销
→ 插件治理记录移除
```

该插件不实现真实规则解析逻辑。

## 静态清单

`governance.manifest.json` 是未来插件安装前治理检查的输入之一。

当前运行时代码中保留同样的最小清单对象，仅用于 Phase 1 骨架验证。后续会由统一清单加载器消除重复声明。

## 依赖

运行前必须先加载：

```text
@agent-harness/governance-core
```

插件通过 Cordis：

```text
inject = ['governanceCatalog']
```

等待治理目录服务可用。
