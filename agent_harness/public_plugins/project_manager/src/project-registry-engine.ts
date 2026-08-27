import type {
  ProjectContext,
  ProjectManifestV01,
  ProjectResolutionCandidate,
  ProjectResourceKind,
} from '@agent-harness/project-contract'
import {
  createProjectContext,
  resolveProjectResourcePath,
} from '@agent-harness/project-contract'

interface ProjectRecord {
  readonly manifest: ProjectManifestV01
  readonly context: ProjectContext
}

const normalize = (value: string): string => value.trim().toLowerCase()

export class ProjectRegistryEngine {
  private readonly projects = new Map<string, ProjectRecord>()

  register(manifest: ProjectManifestV01, projectRoot: string): () => void {
    const projectId = manifest.project.id
    if (this.projects.has(projectId)) {
      throw new Error(`Project 已注册: ${projectId}`)
    }

    const context = createProjectContext(manifest, projectRoot)
    this.projects.set(projectId, { manifest, context })

    return () => {
      this.unregister(projectId)
    }
  }

  unregister(projectId: string): boolean {
    return this.projects.delete(projectId)
  }

  clear(): void {
    this.projects.clear()
  }

  list(): readonly ProjectContext[] {
    return [...this.projects.values()]
      .map(record => record.context)
      .sort((a, b) => a.projectId.localeCompare(b.projectId))
  }

  get(projectId: string): ProjectContext | undefined {
    return this.projects.get(projectId)?.context
  }

  getManifest(projectId: string): ProjectManifestV01 | undefined {
    return this.projects.get(projectId)?.manifest
  }

  getResourcePath(projectId: string, kind: ProjectResourceKind): string | undefined {
    const record = this.projects.get(projectId)
    if (!record) return undefined
    return resolveProjectResourcePath(record.manifest, record.context.projectRoot, kind)
  }

  resolve(query: string, limit = 5): readonly ProjectResolutionCandidate[] {
    const needle = normalize(query)
    if (!needle) return []

    const candidates = [...this.projects.values()]
      .map(({ context }) => this.scoreProject(context, needle))
      .filter((item): item is ProjectResolutionCandidate => item !== undefined)
      .sort((a, b) => b.relevance - a.relevance || a.projectId.localeCompare(b.projectId))

    return candidates.slice(0, Math.max(1, limit))
  }

  private scoreProject(
    context: ProjectContext,
    needle: string,
  ): ProjectResolutionCandidate | undefined {
    const id = normalize(context.projectId)
    const name = normalize(context.displayName)
    const aliases = context.aliases.map(normalize)
    const reasons: string[] = []
    let relevance = 0

    if (needle === id) {
      relevance = 1
      reasons.push('project_id 精确匹配')
    } else if (needle === name) {
      relevance = 0.98
      reasons.push('项目名称精确匹配')
    } else if (aliases.includes(needle)) {
      relevance = 0.96
      reasons.push('项目别名精确匹配')
    } else {
      const haystacks = [id, name, ...aliases]
      const containing = haystacks.find(value => value.includes(needle) || needle.includes(value))
      if (containing) {
        relevance = 0.8
        reasons.push('项目名称/别名包含匹配')
      } else {
        const tokens = needle.split(/[^a-z0-9\u4e00-\u9fff]+/).filter(Boolean)
        const matched = tokens.filter(token => haystacks.some(value => value.includes(token)))
        if (matched.length > 0) {
          relevance = 0.5 + 0.3 * (matched.length / tokens.length)
          reasons.push(`命中关键词: ${matched.join(', ')}`)
        }
      }
    }

    if (relevance <= 0) return undefined

    return {
      projectId: context.projectId,
      displayName: context.displayName,
      relevance,
      matchReasons: reasons,
    }
  }
}
