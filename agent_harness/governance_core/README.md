# 治理层最小核心

`governance_core` 是智能体治理与进化系统 Phase 1 的最小治理骨架。

它不是 ET-TOOL 专用模块，也不实现具体 Rule、Memory、Test 或 CI 逻辑。

当前职责只有：

```text
治理能力契约
治理插件准入
Provider 绑定
项目登记
插件状态
治理事件
治理目录快照
```

## 架构边界

```text
纯治理核心
  contracts.ts
  validator.ts
  catalog-engine.ts
        │
        ▼
Cordis 适配层
  cordis-service.ts
  events.ts
        │
        ▼
DeepSeek Harness
```

`catalog-engine.ts` 不依赖 Cordis。未来 MCP、Codex App Server 或其他 Harness 接入时，应复用同一套纯治理核心。

## DeepSeek Harness 接入

该包声明了：

```json
"dsh": {
  "bundle": {
    "patch": "./cordis.patch.yml"
  }
}
```

加载后提供：

```text
ctx.governanceCatalog
```

## 治理插件接入示例

治理插件应在自己的 Cordis 生命周期中完成准入和 Provider 登记，并在卸载时撤销绑定。

```ts
export const inject = ['governanceCatalog']

export function apply(ctx) {
  ctx.effect(() => {
    const manifest = {
      manifestVersion: '0.1',
      pluginId: 'example.rule-provider',
      pluginVersion: '0.1.0',
      displayName: '示例规则 Provider',
      scope: { kind: 'global' },
      trust: 'reviewed',
      permissions: ['project.read'],
      provides: [{ capability: 'rule.resolve' }],
    }

    const decision = ctx.governanceCatalog.admit(manifest)
    if (decision.status !== 'admitted') {
      throw new Error(decision.reasons.join('; '))
    }

    const disposeProvider = ctx.governanceCatalog.registerProvider({
      providerId: 'example.rule-provider.default',
      pluginId: manifest.pluginId,
      capability: 'rule.resolve',
    })

    return () => {
      disposeProvider()
      ctx.governanceCatalog.removePlugin(manifest.pluginId)
    }
  })
}
```

正式插件规范会在后续阶段把这段生命周期模式封装成统一接入辅助能力，避免每个插件手写。

## 第一批内置能力

```text
governance.project
rule.resolve
memory.context
test.resolve
evidence.record
state.read
state.update
```

这些只是稳定能力名称和语义入口，不代表对应 Provider 已经实现。

## 当前不包含

```text
Rule Provider
Memory Provider
Test Provider
CI Provider
Evidence 状态机
插件推荐算法
多智能体编排
MCP Gateway
```

这些能力按实施路线图逐阶段接入。
