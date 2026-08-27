# Phase 1：治理层最小骨架设计

> 阶段：Phase 1 最小骨架 v0.4  
> 架构基线：`00_AGENT_HARNESS_SYSTEM_ARCHITECTURE.md` v0.3  
> Phase 0 输入：`02_PHASE0_DEEPSEEK_HARNESS_CAPABILITY_ASSESSMENT.md`  
> 第一运行基座：DeepSeek Harness / Cordis  
> 当前状态：**DONE**  
> 真实验收基线：DeepSeek Harness `0.1.0-rc.8` / Cordis `4.0.1`  
> 本阶段目标：**建立最小可运行治理层，不实现 Rule / Memory / Test 等具体业务治理。**

---

# 1. Phase 1 结论

Phase 1 已完成并通过真实 DeepSeek Harness / Cordis 运行时验收。

最终链路已经证明：

```text
DeepSeek Harness / Cordis
        ↓
治理目录服务 ctx.governanceCatalog
        ↓
治理清单准入
        ↓
能力契约
        ↓
Provider 绑定
        ↓
插件运行
        ↓
插件卸载
        ↓
Provider / 治理记录 / Service 自动清理
```

本阶段确认：治理层可以建立在 DeepSeek Harness / Cordis 公开扩展点之上，无需修改 DeepSeek Harness Core。

---

# 2. 核心边界

治理层从第一版开始保持两层分离：

```text
纯治理核心
    不依赖 Cordis
    负责：
    - 数据模型
    - Governance Manifest 校验
    - Capability Catalog
    - Provider 关系
    - Project Registration

Cordis 适配层
    负责：
    - 暴露 ctx.governanceCatalog
    - 生命周期接入
    - Typed Governance Events
    - 插件卸载清理
```

因此未来可以继续增加：

```text
MCP Adapter
Codex Adapter
其他 Harness Adapter
```

而不需要重写纯治理核心。

---

# 3. 第一批治理能力契约

Phase 1 冻结第一批公共能力名称：

```text
governance.project
rule.resolve
memory.context
test.resolve
evidence.record
state.read
state.update
```

能力契约描述稳定语义，不绑定具体实现。

例如：

```text
memory.context
    ↓
Graph Memory Provider / 未来其他 Provider

rule.resolve
    ↓
ET-TOOL Rule Provider / 未来其他 Project Provider
```

---

# 4. Governance Manifest

任何希望进入正式治理体系的插件，都必须提交治理清单。

当前清单至少包含：

```text
插件身份
插件版本
作用域
可信等级
权限声明
提供的能力
新增能力契约（如果需要）
```

静态 Schema：

```text
agent_harness/governance_core/schemas/
  governance-manifest-v0.1.schema.json
```

最小门禁已经实现：

```text
清单版本合法
插件 ID 合法
插件版本合法
作用域合法
权限 ID 合法且无重复
能力声明无重复
未知能力必须携带新能力契约
新能力契约 ID 必须与声明一致
已存在能力禁止静默重定义
```

DeepSeek Harness 能加载一个插件，不代表治理系统必须接受它。

---

# 5. Governance Catalog

Cordis 中统一暴露：

```text
ctx.governanceCatalog
```

第一批接口：

```text
admit(manifest)
removePlugin(pluginId)
registerProvider(provider)
unregisterProvider(providerId)
registerProject(project)
unregisterProject(projectId)
setPluginState(pluginId, state)
getCapability(capabilityId)
listCapabilities()
listProviders(capabilityId)
listPlugins()
listProjects()
snapshot()
```

插件状态：

```text
active
degraded
disabled
```

本阶段不负责插件推荐，不负责自动 Provider 选择。

---

# 6. 治理事件

Cordis 适配层已经定义第一批类型化事件：

```text
governance/plugin-admitted
governance/plugin-rejected
governance/plugin-removed
governance/provider-registered
governance/provider-removed
governance/project-registered
governance/project-removed
governance/plugin-state-changed
```

治理事件用于运行时观察；Governance Catalog 仍然是当前状态查询入口。

---

# 7. 工程结构

```text
agent_harness/
  governance_core/
    package.json
    tsconfig.json
    cordis.patch.yml
    schemas/
      governance-manifest-v0.1.schema.json
    src/
      contracts.ts
      validator.ts
      catalog-engine.ts
      cordis-service.ts
      events.ts
      index.ts
    tests/
      catalog-engine.test.ts

  examples/
    governance_demo_plugin/
      package.json
      governance.manifest.json
      cordis.patch.yml
      src/index.ts

  validation/
    phase1_real_dsh_integration.sh

.github/workflows/
  agent-harness-phase1-integration.yml
```

架构约束继续成立：

> `catalog-engine.ts` 不依赖 Cordis；`cordis-service.ts` 只是第一宿主适配层。

---

# 8. 真实 DeepSeek Harness 集成验收

标准验收入口：

```bash
bash agent_harness/validation/phase1_real_dsh_integration.sh
```

验收链：

```text
构建 / 单测 governance_core
→ npm pack
→ 构建 / pack governance_demo_plugin
→ 安装真实 @deepseek-ai/dsh
→ dsh plugin --profile phase1 add 两个 Bundle
→ dsh --profile phase1 --dump-config
→ 使用真实 @deepseek-ai/cordis Context
→ 验证 ctx.governanceCatalog
→ 加载 demo plugin
→ 验证治理准入和 rule.resolve Provider
→ dispose demo Fiber
→ 验证 Provider / 插件治理记录被清理
→ dispose core Fiber
→ 验证 governanceCatalog Service 被清理
```

真实运行结果：

```text
ctx.governanceCatalog = PASS
demo admission/provider = PASS
demo unload cleanup = PASS
core service unload cleanup = PASS

PHASE1_REAL_DSH_INTEGRATION=PASS
DSH_VERSION=0.1.0-rc.8
CORDIS_VERSION=4.0.1
```

因此以下门槛均已关闭：

```text
DSH Bundle Install / Composition = PASS
ctx.governanceCatalog Real Runtime = PASS
Demo Provider Real Runtime = PASS
Unload Cleanup Real Runtime = PASS
```

---

# 9. Phase 1 最终验收结果

```text
1. 纯治理核心可独立测试                         PASS
2. 合法治理清单可以准入                         PASS
3. 非法治理清单被拒绝                           PASS
4. Provider 不能绑定未声明能力                  PASS
5. Provider 可以按 capability 查询              PASS
6. 项目可以登记和删除                           PASS
7. Cordis Service 可以暴露治理目录               PASS
8. 治理事件具备类型定义                         PASS
9. Bundle 可以真实安装到 DeepSeek Harness        PASS
10. 示例插件卸载后运行时绑定被自动清理           PASS
11. 核心逻辑未写死 ET-TOOL / Graph Memory / Workflow PASS
```

Phase 1 最终状态：

```text
DONE
```

---

# 10. 下一阶段

正式进入：

```text
Phase 2 — ET-TOOL Project Plugin 骨架
```

Phase 2 不立即实现完整 Rule / Memory / Test 系统，而先让 ET-TOOL 成为治理系统中的正式 Project Plugin，建立：

```text
项目身份
项目根目录
当前设计知识入口
规则入口
源码导航入口
测试入口
当前状态 / Open Gap 入口
项目级治理策略入口
```

Phase 2 仍然遵循同一原则：

> 先建立最小真实项目接入，再进入 Phase 3 的核心治理闭环。