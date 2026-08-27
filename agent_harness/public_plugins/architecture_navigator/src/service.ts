import { Service, type Context } from '@deepseek-ai/cordis'
import { observeFrameworkOperation } from '@agent-harness/governance-core'
import '@agent-harness/project-manager'
import type { ProjectCandidateResult, ProjectQueryRequest } from '@agent-harness/project-contract'
import { ArchitectureNavigatorEngine } from './navigator-engine.js'
import type {
  ArchitectureNode,
  ArchitectureNodeResult,
  ArchitectureProjectIndex,
  ArchitectureRouteFile,
} from './contracts.js'

export class ArchitectureNavigatorService extends Service {
  private readonly runtimeContext: Context
  private readonly engine = new ArchitectureNavigatorEngine()

  constructor(ctx: Context) {
    super(ctx, 'architectureNavigator')
    this.runtimeContext = ctx

    ctx.effect(() => () => {
      this.engine.clear()
    })
  }

  refreshProject(projectId: string): ArchitectureProjectIndex {
    const project = this.runtimeContext.projectManager.getProjectContext(projectId)
    if (!project) {
      this.engine.removeProject(projectId)
      throw new Error(`Architecture Navigator 找不到项目: ${projectId}`)
    }

    if (project.resourceStandards.architecture !== 'architecture-v0.1') {
      this.engine.removeProject(projectId)
      throw new Error(
        `${projectId} Architecture 接口拒绝接入: 不支持标准 ${project.resourceStandards.architecture}`,
      )
    }

    const resourcePath = this.runtimeContext.projectManager.getResourcePath(projectId, 'architecture')
    if (!resourcePath) {
      this.engine.removeProject(projectId)
      throw new Error(`${projectId} Architecture 接口拒绝接入: 无法解析资源路径`)
    }

    this.engine.removeProject(projectId)
    return this.engine.refreshProject(
      projectId,
      resourcePath,
      project.resources.architecture,
    )
  }

  getIndex(projectId: string): ArchitectureProjectIndex {
    return this.ensureReady(projectId)
  }

  listFiles(projectId: string): readonly ArchitectureRouteFile[] {
    this.ensureReady(projectId)
    return this.engine.listFiles(projectId)
  }

  searchArchitecture(request: ProjectQueryRequest): readonly ProjectCandidateResult[] {
    return observeFrameworkOperation(
      this.runtimeContext,
      {
        component: 'architecture',
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

  getNode(projectId: string, nodeId: string): ArchitectureNodeResult | undefined {
    this.ensureReady(projectId)
    return this.engine.getNode(projectId, nodeId)
  }

  listChildren(projectId: string, nodeId: string): readonly ArchitectureNode[] {
    this.ensureReady(projectId)
    return this.engine.listChildren(projectId, nodeId)
  }

  removeProject(projectId: string): boolean {
    return this.engine.removeProject(projectId)
  }

  private ensureReady(projectId: string): ArchitectureProjectIndex {
    const project = this.runtimeContext.projectManager.getProjectContext(projectId)
    if (!project) {
      this.engine.removeProject(projectId)
      throw new Error(`Architecture Navigator 找不到项目: ${projectId}`)
    }

    if (project.resourceStandards.architecture !== 'architecture-v0.1') {
      this.engine.removeProject(projectId)
      throw new Error(
        `${projectId} Architecture 接口拒绝接入: 不支持标准 ${project.resourceStandards.architecture}`,
      )
    }

    const resourcePath = this.runtimeContext.projectManager.getResourcePath(projectId, 'architecture')
    if (!resourcePath) {
      this.engine.removeProject(projectId)
      throw new Error(`${projectId} Architecture 接口拒绝接入: 无法解析资源路径`)
    }

    const cached = this.engine.getIndex(projectId)
    if (cached && cached.resourcePath === resourcePath) return cached

    this.engine.removeProject(projectId)
    return this.refreshProject(projectId)
  }
}

declare module '@deepseek-ai/cordis' {
  interface Context {
    architectureNavigator: ArchitectureNavigatorService
  }
}

export default ArchitectureNavigatorService
