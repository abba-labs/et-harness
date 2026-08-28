export type GovernanceScopeKind = 'global' | 'domain' | 'project'

export interface GovernanceScope {
  readonly kind: GovernanceScopeKind
  readonly id?: string
}

export type GovernanceTrustLevel = 'builtin' | 'trusted' | 'reviewed' | 'untrusted'

export type GovernancePluginState = 'active' | 'degraded' | 'disabled'

export type GovernanceCriticality = 'core' | 'important' | 'optional'

export interface GovernanceCapabilityContract {
  readonly id: string
  readonly version: string
  readonly summary: string
  readonly criticality: GovernanceCriticality
  readonly inputSchema?: string
  readonly outputSchema?: string
}

export interface GovernanceCapabilityDeclaration {
  readonly capability: string
  readonly contract?: GovernanceCapabilityContract
}

export interface GovernanceManifest {
  readonly manifestVersion: '0.1'
  readonly pluginId: string
  readonly pluginVersion: string
  readonly displayName: string
  readonly scope: GovernanceScope
  readonly trust: GovernanceTrustLevel
  readonly permissions: readonly string[]
  readonly provides: readonly GovernanceCapabilityDeclaration[]
}

export interface GovernanceAdmissionDecision {
  readonly status: 'admitted' | 'rejected'
  readonly reasons: readonly string[]
}

export interface GovernanceProviderRegistration {
  readonly providerId: string
  readonly pluginId: string
  readonly capability: string
  readonly priority?: number
  readonly metadata?: Readonly<Record<string, unknown>>
}

export interface GovernanceProjectRegistration {
  readonly projectId: string
  readonly displayName: string
  readonly rootPath: string
  readonly metadata?: Readonly<Record<string, unknown>>
}

export interface GovernancePluginRecord {
  readonly manifest: GovernanceManifest
  readonly state: GovernancePluginState
}

export interface GovernanceCatalogSnapshot {
  readonly capabilities: readonly GovernanceCapabilityContract[]
  readonly plugins: readonly GovernancePluginRecord[]
  readonly providers: readonly GovernanceProviderRegistration[]
  readonly projects: readonly GovernanceProjectRegistration[]
}

export const CORE_GOVERNANCE_CAPABILITIES: readonly GovernanceCapabilityContract[] = [
  {
    id: 'governance.lifecycle',
    version: '0.1',
    summary: '强制 Agent / Task / Turn 公共治理生命周期；项目动作不能决定治理是否发生',
    criticality: 'core',
  },
  {
    id: 'governance.turn-journal',
    version: '0.1',
    summary: '持久化每轮 Turn Journal，并为强制 Closure、失败重放和不可跳过的下一轮准入提供事实基础',
    criticality: 'core',
  },
  {
    id: 'governance.turn-reflection',
    version: '0.1',
    summary: '每轮结束后强制触发一次统一 Agent 语义 Reflection，并结构化判断 Context、Knowledge、Experience、Architecture、Rules、Evidence、Working Set 与 Obligations',
    criticality: 'core',
  },
  {
    id: 'governance.turn-closure',
    version: '0.1',
    summary: '在每轮 Reflection 后强制执行固定 Mandatory Closure Modules，持久化可重放 Receipt，并且只有全部 Mandatory 模块成功后才允许 Turn CLOSED',
    criticality: 'core',
  },
  {
    id: 'governance.project',
    version: '0.1',
    summary: '项目身份、项目范围和项目治理入口',
    criticality: 'core',
  },
  {
    id: 'architecture.navigate',
    version: '0.1',
    summary: '按项目 Architecture Contract 校验、索引并返回架构候选节点',
    criticality: 'core',
  },
  {
    id: 'rule.navigate',
    version: '0.1',
    summary: '按项目 Rule Contract 校验、索引并返回规则候选节点',
    criticality: 'core',
  },
  {
    id: 'knowledge.navigate',
    version: '0.2',
    summary: '在 Harness Global 与当前 Project Knowledge Scope 中返回可追溯知识候选节点',
    criticality: 'core',
  },
  {
    id: 'knowledge.library',
    version: '0.2',
    summary: '管理 Global / Project Knowledge Taxonomy、自动目录、机器索引、确定性检索和轻量事务写治理',
    criticality: 'core',
  },
  {
    id: 'gate.navigate',
    version: '0.1',
    summary: '按项目 Gate Contract 校验、索引并返回验证 Gate / Execution Plan',
    criticality: 'core',
  },
  {
    id: 'context.build',
    version: '0.2',
    summary: '解析当前有效资源引用并按优先级、预算组装最小充分 Context Frame',
    criticality: 'core',
  },
  {
    id: 'context.manage',
    version: '0.1',
    summary: '管理 Bootstrap、Task/Progress Ledger、Working Set、Recent Tail、Handles、Rebuild 与 Handoff 生命周期',
    criticality: 'core',
  },
  {
    id: 'context.contribute',
    version: '0.1',
    summary: '允许项目通过可选 Provider 在初始 A/R/K/G 路由后贡献任务特定 Context、Scope、Validation 与 Output Contract；未声明 Provider 的项目保持原行为',
    criticality: 'optional',
    inputSchema: 'agent-harness.project-context-contribution-request.v0.1',
    outputSchema: 'agent-harness.project-context-contribution.v0.1',
  },
  {
    id: 'experience.manage',
    version: '0.1',
    summary: '管理 Agent 提交的项目经验候选和跨任务经验状态',
    criticality: 'core',
  },
  {
    id: 'rule.resolve',
    version: '0.1',
    summary: '兼容旧设计的规则解析能力；后续由 Agent 基于 rule.navigate 候选进行最终判断',
    criticality: 'important',
  },
  {
    id: 'memory.context',
    version: '0.1',
    summary: '检索项目跨任务的未决经验记忆，供 Agent 判断是否需要复用或晋级',
    criticality: 'core',
  },
  {
    id: 'test.resolve',
    version: '0.1',
    summary: '根据任务和改动解析所需测试',
    criticality: 'core',
  },
  {
    id: 'evidence.record',
    version: '0.1',
    summary: '追加记录不可变验证证据并返回稳定 Evidence ID',
    criticality: 'core',
  },
  {
    id: 'evidence.read',
    version: '0.1',
    summary: '按项目 / 任务读取可追溯验证证据',
    criticality: 'important',
  },
  {
    id: 'state.read',
    version: '0.1',
    summary: '读取项目受治理运行状态',
    criticality: 'core',
  },
  {
    id: 'state.update',
    version: '0.1',
    summary: '以版本化方式更新项目运行状态并保留 Evidence 引用',
    criticality: 'core',
  },
] as const
