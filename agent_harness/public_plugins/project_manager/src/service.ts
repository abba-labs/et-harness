import { Service, type Context } from '@deepseek-ai/cordis'
import { observeFrameworkOperation } from '@agent-harness/governance-core'
import type {
  ProjectContext,
  ProjectManifestV01,
  ProjectResolutionCandidate,
  ProjectResourceKind,
} from '@agent-harness/project-contract'
import { findProjectRoot } from '@agent-harness/project-contract'
import { loadProjectManifestFile } from './manifest-loader.js'
import { ProjectRegistryEngine } from './project-registry-engine.js'

export class ProjectManagerService extends Service {
  private readonly runtimeContext: Context
  private readonly engine = new ProjectRegistryEngine()
  private readonly governanceDisposers = new Map<string, () => void>()

  constructor(ctx: Context) {
    super(ctx, 'projectManager')
    this.runtimeContext = ctx

    ctx.effect(() => () => {
      this.disposeAllProjects()
    })
  }

  registerProject(manifest: ProjectManifestV01, projectRoot: string): () => void {
    const disposeEngine = this.engine.register(manifest, projectRoot)
    let disposeGovernance: (() => void) | undefined

    try {
      disposeGovernance = this.runtimeContext.governanceCatalog.registerProject({
        projectId: manifest.project.id,
        displayName: manifest.project.name,
        rootPath: projectRoot,
        metadata: {
          contractVersion: manifest.contract_version,
          projectType: manifest.project.type,
        },
      })
      this.governanceDisposers.set(manifest.project.id, disposeGovernance)
    } catch (error) {
      disposeEngine()
      throw error
    }

    return () => {
      this.governanceDisposers.get(manifest.project.id)?.()
      this.governanceDisposers.delete(manifest.project.id)
      disposeEngine()
    }
  }

  registerProjectFromManifestFile(
    manifestPath: string,
    rootSearchStart: string = process.cwd(),
  ): () => void {
    const manifest = loadProjectManifestFile(manifestPath)
    const projectRoot = findProjectRoot(manifest.root.markers, rootSearchStart)
    return this.registerProject(manifest, projectRoot)
  }

  listProjects(): readonly ProjectContext[] {
    return this.engine.list()
  }

  resolveProject(query: string, limit = 5): readonly ProjectResolutionCandidate[] {
    return observeFrameworkOperation(
      this.runtimeContext,
      { component: 'project', operation: 'resolve' },
      () => this.engine.resolve(query, limit),
      result => ({
        outcome: result.length > 0 ? 'OK' : 'MISS',
        values: { resultCount: result.length },
      }),
    )
  }

  getProjectContext(projectId: string): ProjectContext | undefined {
    return this.engine.get(projectId)
  }

  getResourcePath(projectId: string, kind: ProjectResourceKind): string | undefined {
    return this.engine.getResourcePath(projectId, kind)
  }

  private disposeAllProjects(): void {
    for (const dispose of this.governanceDisposers.values()) dispose()
    this.governanceDisposers.clear()
    this.engine.clear()
  }
}

declare module '@deepseek-ai/cordis' {
  interface Context {
    projectManager: ProjectManagerService
  }
}

export default ProjectManagerService
