import { Service, type Context } from '@deepseek-ai/cordis'
import { observeFrameworkOperation } from '@agent-harness/governance-core'
import '@agent-harness/project-manager'
import '@agent-harness/architecture-navigator'
import '@agent-harness/rule-manager'
import '@agent-harness/knowledge-manager'
import type { KnowledgeStatus } from '@agent-harness/knowledge-manager'
import '@agent-harness/gate-manager'
import { ContextBuilderEngine } from './context-builder-engine.js'
import type {
  ContextBuildRequest,
  ContextPack,
  ContextPriority,
  ContextReference,
  ContextResolvedItem,
} from './contracts.js'

const priorityOf = (reference: ContextReference): ContextPriority =>
  reference.priority ?? 'normal'

const joinOptional = (values: readonly string[]): string => values.length > 0 ? values.join(', ') : '-'

const taskIdFromRequest = (request: ContextBuildRequest): string | undefined => {
  for (const item of request.inlineItems ?? []) {
    const match = /\/context\/([^/]+)\/(?:task-ledger|progress-ledger|recent-tail|handles)$/.exec(item.provenance)
    if (match?.[1]) return match[1]
  }
  return undefined
}

interface ValidationPolicyLookup {
  evaluate(reference: string, currentProjectId?: string): {
    readonly decision: 'INSUFFICIENT' | 'READY' | 'BLOCKED'
    readonly distinctSupportCount: number
    readonly documentSupportCount: number
    readonly realTestSupportCount: number
    readonly contradictCount: number
    readonly reasons: readonly string[]
  }
}

const knowledgeTrustTier = (
  status: KnowledgeStatus | undefined,
  validationDecision: 'INSUFFICIENT' | 'READY' | 'BLOCKED' | undefined,
): string => {
  if (validationDecision === 'BLOCKED') return 'DISPUTED'
  if (status === 'FULL_VALIDATED') return 'VERIFIED'
  if (status === 'VALIDATED') return 'SUPPORTED'
  if (status === 'CANDIDATE') return 'EXPLORATORY'
  if (status === 'DEPRECATED') return 'HISTORICAL'
  return 'UNCLASSIFIED'
}

const knowledgeUsePolicy = (trustTier: string): string => {
  if (trustTier === 'VERIFIED') return 'Primary reference within stated scope.'
  if (trustTier === 'SUPPORTED') return 'Reference with scope and source awareness.'
  if (trustTier === 'EXPLORATORY') return 'Hypothesis, investigation lead, or test target only.'
  if (trustTier === 'DISPUTED') return 'Conflicting claim; inspect SUPPORT/CONTRADICT evidence before use.'
  if (trustTier === 'HISTORICAL') return 'Historical context or anti-pattern only.'
  return 'Do not rely on this item without clarification.'
}

export class ContextBuilderService extends Service {
  private readonly runtimeContext: Context
  private readonly engine = new ContextBuilderEngine()

  constructor(ctx: Context) {
    super(ctx, 'contextBuilder')
    this.runtimeContext = ctx
  }

  buildContext(request: ContextBuildRequest): ContextPack {
    const taskId = taskIdFromRequest(request)
    return observeFrameworkOperation(
      this.runtimeContext,
      {
        component: 'context',
        operation: 'buildFrame',
        projectId: request.projectId,
        ...(taskId ? { taskId } : {}),
      },
      () => {
        if (!this.runtimeContext.projectManager.getProjectContext(request.projectId)) {
          throw new Error(`Context Builder 找不到项目: ${request.projectId}`)
        }

        const items: ContextResolvedItem[] = request.references.map(reference =>
          this.resolveReference(request.projectId, reference),
        )

        for (const inline of request.inlineItems ?? []) {
          if (!inline.content.trim()) continue
          const priority = inline.priority ?? 'normal'
          items.push({
            projectId: request.projectId,
            kind: 'inline',
            id: inline.id,
            title: inline.title,
            content: inline.content,
            priority,
            required: priority === 'required',
            provenance: inline.provenance,
            warnings: [],
          })
        }

        return this.engine.build(request, items)
      },
      result => ({
        outcome: result.overBudget ? 'FAIL' : 'OK',
        values: {
          contextChars: result.charCount,
          itemCount: result.items.length,
          omittedCount: result.omitted.length,
          overBudgetCount: result.overBudget ? 1 : 0,
        },
      }),
    )
  }

  private resolveReference(
    projectId: string,
    reference: ContextReference,
  ): ContextResolvedItem {
    const priority = priorityOf(reference)

    if (reference.kind === 'architecture') {
      const result = this.runtimeContext.architectureNavigator.getNode(projectId, reference.id)
      if (!result) throw new Error(`Context Builder 找不到 Architecture Node: ${reference.id}`)
      const node = result.node
      const content = [
        node.role ? `Role: ${node.role}` : '',
        node.boundary ? `Boundary: ${node.boundary}` : '',
        `Resources: ${joinOptional(node.resources)}`,
        `Relations: ${joinOptional(node.relations)}`,
        node.children.length > 0 ? `Children: ${node.children.join(', ')}` : '',
      ].filter(Boolean).join('\n')
      return {
        projectId,
        kind: 'architecture',
        id: node.id,
        title: node.title,
        content,
        priority,
        required: priority === 'required',
        provenance: `project://${projectId}/architecture#${node.id}`,
        warnings: [],
      }
    }

    if (reference.kind === 'rule') {
      const result = this.runtimeContext.ruleManager.getNode(projectId, reference.id)
      if (!result) throw new Error(`Context Builder 找不到 Rule Node: ${reference.id}`)
      const node = result.node
      const required = priority === 'required'
        || node.level === 'MUST'
        || node.level === 'MUST_NOT'
      const content = node.isLeaf
        ? [
            `Level: ${node.level}`,
            `When: ${node.when}`,
            `Rule: ${node.rule}`,
            `Refs: ${joinOptional(node.refs)}`,
          ].join('\n')
        : `Children: ${joinOptional(node.children)}`
      return {
        projectId,
        kind: 'rule',
        id: node.id,
        title: node.title,
        content,
        priority: required ? 'required' : priority,
        required,
        provenance: `project://${projectId}/rules#${node.id}`,
        warnings: [],
      }
    }

    if (reference.kind === 'knowledge') {
      const result = this.runtimeContext.knowledgeManager.resolveKnowledgeReference(reference.id, projectId)
      if (!result) throw new Error(`Context Builder 找不到 Knowledge: ${reference.id}`)
      if (result.libraryScope.kind === 'project' && result.libraryScope.projectId !== projectId) {
        throw new Error(`Context Builder 拒绝跨项目 Knowledge: ${result.knowledgeUri}`)
      }
      const node = result.result.node
      const warnings: string[] = []
      const policy = (this.runtimeContext as unknown as {
        knowledgeValidationPolicy?: ValidationPolicyLookup
      }).knowledgeValidationPolicy
      const evaluation = policy && node.isLeaf
        ? policy.evaluate(result.knowledgeUri, projectId)
        : undefined
      let supportCount = 0
      let contradictCount = 0
      if (node.isLeaf) {
        try {
          const summary = this.runtimeContext.knowledgeManager.getVerificationSummary(result.knowledgeUri)
          supportCount = summary.supportCount
          contradictCount = summary.contradictCount
        } catch {
          // Legacy libraries may not have a verification store yet.
        }
      }
      const trustTier = knowledgeTrustTier(node.status, evaluation?.decision)
      const usePolicy = knowledgeUsePolicy(trustTier)
      if (trustTier === 'EXPLORATORY') {
        warnings.push(
          `Knowledge ${result.knowledgeUri} is EXPLORATORY; 可用于形成假设和测试，但不得独立支持确定性结论或高风险操作`,
        )
      } else if (trustTier === 'HISTORICAL') {
        warnings.push(`Knowledge ${result.knowledgeUri} is HISTORICAL; 仅用于历史和反例`)
      } else if (trustTier === 'DISPUTED') {
        warnings.push(
          `Knowledge ${result.knowledgeUri} validation=BLOCKED: ${evaluation?.reasons.join('; ') ?? 'current claim has contradictory verification'}`,
        )
      }
      const effectivePriority = priority === 'required'
        ? priority
        : ['EXPLORATORY', 'HISTORICAL', 'DISPUTED'].includes(trustTier)
          ? 'low'
          : priority
      const content = node.isLeaf
        ? [
            `Status: ${node.status}`,
            `TrustTier: ${trustTier}`,
            `UsePolicy: ${usePolicy}`,
            `Validation: ${evaluation?.decision ?? 'UNAVAILABLE'}`,
            `Verification: support=${supportCount}, contradict=${contradictCount}`,
            `Fact: ${node.fact}`,
            node.scope ? `Scope: ${node.scope}` : '',
            `Provenance: ${node.provenance}`,
            `Refs: ${joinOptional(node.refs)}`,
          ].filter(Boolean).join('\n')
        : `Children: ${joinOptional(node.children)}`
      return {
        projectId,
        kind: 'knowledge',
        id: result.knowledgeUri,
        title: node.title,
        content,
        priority: effectivePriority,
        required: effectivePriority === 'required',
        provenance: result.knowledgeUri,
        warnings,
      }
    }

    const result = this.runtimeContext.gateManager.getNode(projectId, reference.id)
    if (!result) throw new Error(`Context Builder 找不到 Gate Node: ${reference.id}`)
    const node = result.node
    const required = priority === 'required' || node.gate?.level === 'MUST'
    const content = node.isGate && node.gate
      ? [
          `Level: ${node.gate.level}`,
          `When: ${node.gate.when}`,
          `Steps: ${node.gate.steps.map(step => `${step.id}:${step.tool}`).join(', ')}`,
          `Pass: ${JSON.stringify(node.gate.pass)}`,
          `Refs: ${joinOptional(node.gate.refs)}`,
        ].join('\n')
      : `Children: ${joinOptional(node.children)}`
    return {
      projectId,
      kind: 'gate',
      id: node.id,
      title: node.title,
      content,
      priority: required ? 'required' : priority,
      required,
      provenance: `project://${projectId}/gates#${node.id}`,
      warnings: [],
    }
  }
}

declare module '@deepseek-ai/cordis' {
  interface Context {
    contextBuilder: ContextBuilderService
  }
}

export default ContextBuilderService
