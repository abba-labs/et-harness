import type { KnowledgeLibraryScope } from './contracts.js'

export const GLOBAL_KNOWLEDGE_LIBRARY_ID = '@global'

const KNOWLEDGE_ID_RE = /^K\d{3}(?:\.\d{3})*$/
const PROJECT_ID_RE = /^[a-z0-9][a-z0-9._-]{1,63}$/

const assertProjectId = (projectId: string): string => {
  if (!PROJECT_ID_RE.test(projectId)) throw new Error(`非法 projectId: ${projectId}`)
  return projectId
}

export function knowledgeLibraryKey(scope: KnowledgeLibraryScope): string {
  return scope.kind === 'global'
    ? GLOBAL_KNOWLEDGE_LIBRARY_ID
    : assertProjectId(scope.projectId)
}

export function qualifyKnowledgeId(scope: KnowledgeLibraryScope, knowledgeId: string): string {
  const normalizedId = knowledgeId.toUpperCase()
  if (!KNOWLEDGE_ID_RE.test(normalizedId)) throw new Error(`非法 Knowledge ID: ${knowledgeId}`)
  return scope.kind === 'global'
    ? `knowledge://global/${normalizedId}`
    : `knowledge://project/${assertProjectId(scope.projectId)}/${normalizedId}`
}

export function parseKnowledgeReference(
  reference: string,
  currentProjectId?: string,
): { readonly scope: KnowledgeLibraryScope; readonly knowledgeId: string } {
  const value = reference.trim()
  if (KNOWLEDGE_ID_RE.test(value.toUpperCase())) {
    if (!currentProjectId) throw new Error('裸 K-ID 需要 currentProjectId 才能解析')
    return {
      scope: { kind: 'project', projectId: assertProjectId(currentProjectId) },
      knowledgeId: value.toUpperCase(),
    }
  }

  const globalMatch = /^knowledge:\/\/global\/(K\d{3}(?:\.\d{3})*)$/i.exec(value)
  if (globalMatch?.[1]) {
    return { scope: { kind: 'global' }, knowledgeId: globalMatch[1].toUpperCase() }
  }

  const projectMatch = /^knowledge:\/\/project\/([^/]+)\/(K\d{3}(?:\.\d{3})*)$/i.exec(value)
  if (projectMatch?.[1] && projectMatch[2]) {
    return {
      scope: { kind: 'project', projectId: assertProjectId(projectMatch[1]) },
      knowledgeId: projectMatch[2].toUpperCase(),
    }
  }

  throw new Error(`无法解析 Knowledge reference: ${reference}`)
}
