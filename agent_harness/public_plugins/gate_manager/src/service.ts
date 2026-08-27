import { Service, type Context } from '@deepseek-ai/cordis'
import { observeFrameworkOperation } from '@agent-harness/governance-core'
import '@agent-harness/project-manager'
import '@agent-harness/evidence-state-manager'
import type { ProjectCandidateResult, ProjectQueryRequest } from '@agent-harness/project-contract'
import { GateManagerEngine } from './gate-manager-engine.js'
import type {
  GateEvidenceStatus,
  GateExecutionPlan,
  GateNode,
  GateNodeResult,
  GateProjectIndex,
  GateRouteFile,
  GateSetEvidenceStatus,
} from './contracts.js'

export class GateManagerService extends Service {
  private readonly runtimeContext: Context
  private readonly engine = new GateManagerEngine()

  constructor(ctx: Context) {
    super(ctx, 'gateManager')
    this.runtimeContext = ctx
    ctx.effect(() => () => this.engine.clear())
  }

  refreshProject(projectId: string): GateProjectIndex {
    const project = this.runtimeContext.projectManager.getProjectContext(projectId)
    if (!project) {
      this.engine.removeProject(projectId)
      throw new Error(`Gate Manager 找不到项目: ${projectId}`)
    }
    if (project.resourceStandards.gates !== 'gate-v0.1') {
      this.engine.removeProject(projectId)
      throw new Error(`${projectId} Gate 接口拒绝接入: 不支持标准 ${project.resourceStandards.gates}`)
    }
    const resourcePath = this.runtimeContext.projectManager.getResourcePath(projectId, 'gates')
    if (!resourcePath) {
      this.engine.removeProject(projectId)
      throw new Error(`${projectId} Gate 接口拒绝接入: 无法解析资源路径`)
    }
    try {
      return this.engine.refreshProject(projectId, resourcePath, project.resources.gates)
    } catch (error) {
      this.engine.removeProject(projectId)
      throw error
    }
  }

  getIndex(projectId: string): GateProjectIndex {
    return this.ensureReady(projectId)
  }

  listFiles(projectId: string): readonly GateRouteFile[] {
    this.ensureReady(projectId)
    return this.engine.listFiles(projectId)
  }

  searchGates(request: ProjectQueryRequest): readonly ProjectCandidateResult[] {
    return observeFrameworkOperation(
      this.runtimeContext,
      {
        component: 'gate',
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

  getNode(projectId: string, gateId: string): GateNodeResult | undefined {
    this.ensureReady(projectId)
    return this.engine.getNode(projectId, gateId)
  }

  listChildren(projectId: string, nodeId: string): readonly GateNode[] {
    this.ensureReady(projectId)
    return this.engine.listChildren(projectId, nodeId)
  }

  getExecutionPlan(projectId: string, gateId: string): GateExecutionPlan | undefined {
    this.ensureReady(projectId)
    return this.engine.getExecutionPlan(projectId, gateId)
  }

  checkGateEvidence(projectId: string, taskId: string, gateId: string): GateEvidenceStatus {
    const plan = this.getExecutionPlan(projectId, gateId)
    if (!plan) throw new Error(`不是可执行 Gate: ${gateId}`)
    const passEvidence = this.runtimeContext.evidenceStateManager.listEvidence({
      projectId,
      taskId,
      gateId,
      result: 'PASS',
      limit: 100,
    })
    const satisfied = passEvidence.length > 0
    return {
      projectId,
      taskId,
      gateId,
      level: plan.level,
      satisfied,
      blocksCompletion: plan.level === 'MUST' && !satisfied,
      evidenceRefs: passEvidence.map(item => item.evidenceId),
    }
  }

  checkGateSetEvidence(
    projectId: string,
    taskId: string,
    applicableGateIds: readonly string[],
  ): GateSetEvidenceStatus {
    return observeFrameworkOperation(
      this.runtimeContext,
      { component: 'gate', operation: 'checkSetEvidence', projectId, taskId },
      () => {
        const gates = [...new Set(applicableGateIds)].map(gateId =>
          this.checkGateEvidence(projectId, taskId, gateId),
        )
        const blockingGateIds = gates.filter(item => item.blocksCompletion).map(item => item.gateId)
        return {
          projectId,
          taskId,
          gates,
          blockingGateIds,
          canComplete: blockingGateIds.length === 0,
        }
      },
      result => ({
        outcome: result.canComplete ? 'PASS' : 'FAIL',
        values: {
          gateCount: result.gates.length,
          blockingGateCount: result.blockingGateIds.length,
        },
      }),
    )
  }

  removeProject(projectId: string): boolean {
    return this.engine.removeProject(projectId)
  }

  private ensureReady(projectId: string): GateProjectIndex {
    const project = this.runtimeContext.projectManager.getProjectContext(projectId)
    if (!project) {
      this.engine.removeProject(projectId)
      throw new Error(`Gate Manager 找不到项目: ${projectId}`)
    }
    return this.engine.getIndex(projectId) ?? this.refreshProject(projectId)
  }
}

declare module '@deepseek-ai/cordis' {
  interface Context {
    gateManager: GateManagerService
  }
}

export default GateManagerService
