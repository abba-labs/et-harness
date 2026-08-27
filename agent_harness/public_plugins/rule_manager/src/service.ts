import { Service, type Context } from '@deepseek-ai/cordis'
import { observeFrameworkOperation } from '@agent-harness/governance-core'
import '@agent-harness/project-manager'
import type { ProjectCandidateResult, ProjectQueryRequest } from '@agent-harness/project-contract'
import { RuleManagerEngine } from './rule-manager-engine.js'
import { evaluateRuleActionGuards, type RuleActionGuardInput, type RuleActionGuardResult } from './action-guard.js'
import type {
  RuleNode,
  RuleNodeResult,
  RuleProjectIndex,
  RuleRouteFile,
} from './contracts.js'

export class RuleManagerService extends Service {
  private readonly runtimeContext: Context
  private readonly engine = new RuleManagerEngine()

  constructor(ctx: Context) {
    super(ctx, 'ruleManager')
    this.runtimeContext = ctx

    ctx.effect(() => () => {
      this.engine.clear()
    })
  }

  refreshProject(projectId: string): RuleProjectIndex {
    const project = this.runtimeContext.projectManager.getProjectContext(projectId)
    if (!project) {
      this.engine.removeProject(projectId)
      throw new Error(`Rule Manager 找不到项目: ${projectId}`)
    }

    if (project.resourceStandards.rules !== 'rule-v0.1') {
      this.engine.removeProject(projectId)
      throw new Error(`${projectId} Rule 接口拒绝接入: 不支持标准 ${project.resourceStandards.rules}`)
    }

    const resourcePath = this.runtimeContext.projectManager.getResourcePath(projectId, 'rules')
    if (!resourcePath) {
      this.engine.removeProject(projectId)
      throw new Error(`${projectId} Rule 接口拒绝接入: 无法解析资源路径`)
    }

    try {
      return this.engine.refreshProject(projectId, resourcePath, project.resources.rules)
    } catch (error) {
      this.engine.removeProject(projectId)
      throw error
    }
  }

  getIndex(projectId: string): RuleProjectIndex {
    return this.ensureReady(projectId)
  }

  listFiles(projectId: string): readonly RuleRouteFile[] {
    this.ensureReady(projectId)
    return this.engine.listFiles(projectId)
  }

  searchRules(request: ProjectQueryRequest): readonly ProjectCandidateResult[] {
    return observeFrameworkOperation(
      this.runtimeContext,
      {
        component: 'rule',
        operation: 'search',
        projectId: request.projectId,
        ...(typeof request.scope?.taskId === 'string' ? { taskId: request.scope.taskId } : {}),
      },
      () => {
        this.ensureReady(request.projectId)
        return this.engine.search(request)
      },
      result => ({
        outcome: result.length > 0 ? 'OK' : 'MISS',
        values: { resultCount: result.length },
      }),
    )
  }

  guardAction(projectId: string, input: RuleActionGuardInput): RuleActionGuardResult {
    this.ensureReady(projectId)
    const nodes = this.engine.listFiles(projectId)
      .flatMap(file => file.nodes)
      .map(ruleId => this.engine.getNode(projectId, ruleId)?.node)
      .filter((node): node is RuleNode => node !== undefined)
    return evaluateRuleActionGuards(nodes, input)
  }

  getNode(projectId: string, ruleId: string): RuleNodeResult | undefined {
    this.ensureReady(projectId)
    return this.engine.getNode(projectId, ruleId)
  }

  listChildren(projectId: string, nodeId: string): readonly RuleNode[] {
    this.ensureReady(projectId)
    return this.engine.listChildren(projectId, nodeId)
  }

  removeProject(projectId: string): boolean {
    return this.engine.removeProject(projectId)
  }

  private ensureReady(projectId: string): RuleProjectIndex {
    const project = this.runtimeContext.projectManager.getProjectContext(projectId)
    if (!project) {
      this.engine.removeProject(projectId)
      throw new Error(`Rule Manager 找不到项目: ${projectId}`)
    }
    return this.engine.getIndex(projectId) ?? this.refreshProject(projectId)
  }
}

declare module '@deepseek-ai/cordis' {
  interface Context {
    ruleManager: RuleManagerService
  }
}

export default RuleManagerService
