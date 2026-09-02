import { createHash } from 'node:crypto'

interface ProjectBootstrapProject {
  readonly projectId: string
  readonly displayName: string
  readonly aliases: readonly string[]
  readonly resources: { readonly architecture: string }
  readonly resourceStandards: { readonly architecture: string }
}

interface ArchitectureBootstrapNode {
  readonly id: string
  readonly title: string
  readonly role?: string
  readonly boundary?: string
  readonly resources: readonly string[]
  readonly relations: readonly string[]
}

interface ArchitectureBootstrapFile {
  readonly id: string
  readonly file: string
  readonly title: string
  readonly summary: string
  readonly aliases: readonly string[]
}

interface ArchitectureBootstrapNavigator {
  listFiles(projectId: string): readonly ArchitectureBootstrapFile[]
  getNode(projectId: string, nodeId: string): { readonly node: ArchitectureBootstrapNode } | undefined
  listChildren(projectId: string, nodeId: string): readonly ArchitectureBootstrapNode[]
}

const MAX_ARCHITECTURE_ROOTS = 32
const MAX_ARCHITECTURE_CHILDREN = 96
const MAX_BOOTSTRAP_BYTES = 32 * 1024

const compactNode = (node: ArchitectureBootstrapNode) => ({
  id: node.id,
  title: node.title,
  ...(node.role ? { role: node.role } : {}),
  ...(node.boundary ? { boundary: node.boundary } : {}),
  resources: [...node.resources],
  relations: [...node.relations],
})

export const buildProjectBootstrap = (
  project: ProjectBootstrapProject,
  navigator: ArchitectureBootstrapNavigator,
) => {
  if (project.resourceStandards.architecture !== 'architecture-v0.1') {
    throw new Error(`Project ${project.projectId} has unsupported Architecture standard`)
  }
  const files = navigator.listFiles(project.projectId)
  if (files.length === 0) {
    throw new Error(`Project ${project.projectId} has no Architecture bootstrap roots`)
  }
  if (files.length > MAX_ARCHITECTURE_ROOTS) {
    throw new Error(
      `Project ${project.projectId} Architecture bootstrap exceeds ${MAX_ARCHITECTURE_ROOTS} root files`,
    )
  }

  let childCount = 0
  const roots = files.map(file => {
    const root = navigator.getNode(project.projectId, file.id)?.node
    if (!root) throw new Error(`Architecture root node is missing for ${file.id}`)
    const children = navigator.listChildren(project.projectId, file.id)
    childCount += children.length
    if (childCount > MAX_ARCHITECTURE_CHILDREN) {
      throw new Error(
        `Project ${project.projectId} Architecture bootstrap exceeds ${MAX_ARCHITECTURE_CHILDREN} first-level children`,
      )
    }
    return {
      id: file.id,
      file: file.file,
      title: file.title,
      summary: file.summary,
      aliases: [...file.aliases],
      root: compactNode(root),
      children: children.map(compactNode),
    }
  })

  const payload = {
    schema: 'et-harness.project-bootstrap.v0.1' as const,
    projectId: project.projectId,
    displayName: project.displayName,
    aliases: [...project.aliases],
    architecture: {
      standard: project.resourceStandards.architecture,
      resource: project.resources.architecture,
      roots,
    },
  }
  const serialized = JSON.stringify(payload)
  const size = Buffer.byteLength(serialized, 'utf8')
  if (size > MAX_BOOTSTRAP_BYTES) {
    throw new Error(
      `Project ${project.projectId} Architecture bootstrap exceeds ${MAX_BOOTSTRAP_BYTES} bytes`,
    )
  }
  const fingerprint = `sha256:${createHash('sha256').update(serialized).digest('hex')}`
  return Object.freeze({ ...payload, fingerprint })
}
