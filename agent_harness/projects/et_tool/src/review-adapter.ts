import type { Context } from '@deepseek-ai/cordis'
import '@agent-harness/governance-core'
import type { GovernanceManifest } from '@agent-harness/governance-core'
import EtToolCodeReviewAdapterService from './review-service.js'
import { ET_TOOL_REVIEW_CAPABILITIES, type EtToolReviewCapability } from './review-contracts.js'

export * from './review-contracts.js'
export * from './review-service.js'

export const name = 'agent-harness-project-et-tool-code-review-adapter'
export const inject = [
  'governanceCatalog',
  'projectManager',
  'architectureNavigator',
  'ruleManager',
  'knowledgeManager',
  'gateManager',
  'evidenceStateManager',
]

const summaries: Readonly<Record<EtToolReviewCapability, string>> = {
  'change.analyze': 'ET-TOOL 任务意图、实际 Diff、共享层与影响范围分析',
  'code.review': 'ET-TOOL 代码控制流、错误路径与静态代码风险审查',
  'architecture.review': 'ET-TOOL 架构分层、芯片/Route 隔离与正式产品链审查',
  'rule.review': 'ET-TOOL 当前变更适用 Rule 选择与 MUST/MUST_NOT 合规审查',
  'lifecycle.review': 'ET-TOOL 资源所有权、退出清理、异步与 Progress 生命周期审查',
  'contract.review': 'ET-TOOL CLI/Request/Result/Profile/Progress 等契约兼容性审查',
  'validation.plan': '根据 ET-TOOL 变更影响范围生成 Gate 之后的构建/测试/硬件验证计划，不执行验证',
}

export const governanceManifest: GovernanceManifest = {
  manifestVersion: '0.1',
  pluginId: 'project.et-tool.code-review-adapter',
  pluginVersion: '0.1.0',
  displayName: 'ET-TOOL Code Review Adapter',
  scope: { kind: 'project', id: 'et-tool' },
  trust: 'reviewed',
  permissions: [
    'project.read',
    'git.read',
    'architecture.read',
    'rule.read',
    'knowledge.read',
    'gate.read',
    'evidence.write',
  ],
  provides: ET_TOOL_REVIEW_CAPABILITIES.map(capability => ({
    capability,
    contract: {
      id: capability,
      version: '0.1',
      summary: summaries[capability],
      criticality: 'important',
      inputSchema: 'et-tool-review-request-v0.1',
      outputSchema: 'et-tool-review-packet-v0.1',
    },
  })),
}

interface DisposableFiber {
  dispose(): Promise<void> | void
}

export function apply(ctx: Context): void {
  ctx.effect(() => {
    const decision = ctx.governanceCatalog.admit(governanceManifest)
    if (decision.status !== 'admitted') {
      throw new Error(`ET-TOOL Code Review Adapter 治理准入失败: ${decision.reasons.join('; ')}`)
    }

    const providerDisposers: Array<() => void> = []
    let serviceFiber: DisposableFiber | undefined

    try {
      for (const capability of ET_TOOL_REVIEW_CAPABILITIES) {
        providerDisposers.push(ctx.governanceCatalog.registerProvider({
          providerId: `project.et-tool.code-review-adapter.${capability}`,
          pluginId: governanceManifest.pluginId,
          capability,
          priority: 1000,
          metadata: {
            projectId: 'et-tool',
            service: 'etToolCodeReviewAdapter',
            prepareMethod: 'prepareReview',
            decisionMethod: 'recordReviewDecision',
            semanticReviewer: 'agent-or-human',
            autoPass: false,
          },
        }))
      }
      serviceFiber = ctx.plugin(EtToolCodeReviewAdapterService) as DisposableFiber
    } catch (error) {
      for (const dispose of providerDisposers.reverse()) dispose()
      if (serviceFiber) void serviceFiber.dispose()
      ctx.governanceCatalog.removePlugin(governanceManifest.pluginId)
      throw error
    }

    return () => {
      for (const dispose of providerDisposers.reverse()) dispose()
      if (serviceFiber) void serviceFiber.dispose()
      ctx.governanceCatalog.removePlugin(governanceManifest.pluginId)
    }
  })
}
