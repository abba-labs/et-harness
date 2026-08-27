import { Service, type Context } from '@deepseek-ai/cordis'
import { observeFrameworkOperation } from '@agent-harness/governance-core'
import type { KnowledgeManagerService } from './service.js'
import { KnowledgeManagerEngine } from './knowledge-manager-engine.js'
import { knowledgeLibraryKey } from './knowledge-address.js'
import { promoteKnowledgeStatus } from './knowledge-promotion.js'
import {
  evaluateKnowledgeValidationPolicy,
  knowledgeClaimFingerprint,
} from './validation-policy.js'
import type {
  KnowledgePromotionResult,
  KnowledgeValidationEvaluation,
} from './contracts.js'

interface KnowledgeManagerLookup {
  resolveKnowledgeReference(reference: string, currentProjectId?: string): ReturnType<KnowledgeManagerService['resolveKnowledgeReference']>
  listVerifications(knowledgeUri: string): ReturnType<KnowledgeManagerService['listVerifications']>
  getGlobalIndex(): ReturnType<KnowledgeManagerService['getGlobalIndex']>
  getIndex(projectId: string): ReturnType<KnowledgeManagerService['getIndex']>
  reindexGlobalLibrary(): ReturnType<KnowledgeManagerService['reindexGlobalLibrary']>
  reindexProject(projectId: string): ReturnType<KnowledgeManagerService['reindexProject']>
}

export class KnowledgeValidationPolicyService extends Service {
  static inject = ['knowledgeManager']

  private readonly runtimeContext: Context

  constructor(ctx: Context) {
    super(ctx, 'knowledgeValidationPolicy')
    this.runtimeContext = ctx
  }

  evaluate(reference: string, currentProjectId?: string): KnowledgeValidationEvaluation {
    return observeFrameworkOperation(
      this.runtimeContext,
      {
        component: 'knowledge',
        operation: 'validate',
        ...(currentProjectId ? { projectId: currentProjectId } : {}),
      },
      () => {
        const manager = this.manager()
        const target = manager.resolveKnowledgeReference(reference, currentProjectId)
        const node = target?.result.node
        if (!target || !node?.isLeaf || !node.status) throw new Error(`Knowledge 不存在: ${reference}`)
        const fingerprint = knowledgeClaimFingerprint(node)
        return evaluateKnowledgeValidationPolicy({
          knowledgeUri: target.knowledgeUri,
          libraryScope: target.libraryScope,
          currentStatus: node.status,
          knowledgeFingerprint: fingerprint,
          records: manager.listVerifications(target.knowledgeUri),
        })
      },
      result => ({
        outcome: result.decision === 'READY' ? 'PASS' : result.decision === 'BLOCKED' ? 'FAIL' : 'MISS',
        values: {
          supportCount: result.distinctSupportCount,
          contradictCount: result.contradictCount,
          requiredSupportCount: result.requiredSupportCount,
        },
      }),
    )
  }

  promote(reference: string, currentProjectId?: string): KnowledgePromotionResult {
    return observeFrameworkOperation(
      this.runtimeContext,
      {
        component: 'knowledge',
        operation: 'promote',
        ...(currentProjectId ? { projectId: currentProjectId } : {}),
      },
      () => {
        const manager = this.manager()
        const target = manager.resolveKnowledgeReference(reference, currentProjectId)
        const node = target?.result.node
        if (!target || !node?.isLeaf || !node.status) throw new Error(`Knowledge 不存在: ${reference}`)
        if (node.status !== 'CANDIDATE' && node.status !== 'VALIDATED') {
          throw new Error(`只有 CANDIDATE / VALIDATED 可以晋级: ${target.knowledgeUri}`)
        }

        const evaluation = this.evaluate(target.knowledgeUri)
        if (evaluation.decision !== 'READY' || !evaluation.targetStatus) {
          throw new Error(`Knowledge 尚不可晋级: ${evaluation.decision}; ${evaluation.reasons.join('; ')}`)
        }

        const root = target.libraryScope.kind === 'global'
          ? manager.getGlobalIndex().resourcePath
          : manager.getIndex(target.libraryScope.projectId).resourcePath
        const libraryKey = knowledgeLibraryKey(target.libraryScope)
        const resourceHandle = target.libraryScope.kind === 'global'
          ? 'knowledge://global'
          : `knowledge://project/${target.libraryScope.projectId}`
        const localEngine = new KnowledgeManagerEngine()
        localEngine.refreshProject(libraryKey, root, resourceHandle)

        const mutation = promoteKnowledgeStatus({
          engine: localEngine,
          libraryKey,
          root,
          knowledgeId: node.id,
          targetStatus: evaluation.targetStatus,
          reindex: () => localEngine.reindexProject(libraryKey, root, resourceHandle),
        })

        if (target.libraryScope.kind === 'global') manager.reindexGlobalLibrary()
        else manager.reindexProject(target.libraryScope.projectId)

        return { evaluation, mutation }
      },
      result => ({
        outcome: result.mutation.status === result.evaluation.targetStatus ? 'PASS' : 'FAIL',
        values: { promotionCount: result.mutation.status === result.evaluation.targetStatus ? 1 : 0 },
      }),
    )
  }

  private manager(): KnowledgeManagerLookup {
    const manager = (this.runtimeContext as unknown as {
      knowledgeManager?: KnowledgeManagerLookup
    }).knowledgeManager
    if (!manager) throw new Error('Knowledge Manager 未加载')
    return manager
  }
}

declare module '@deepseek-ai/cordis' {
  interface Context {
    knowledgeValidationPolicy: KnowledgeValidationPolicyService
  }
}

export default KnowledgeValidationPolicyService
