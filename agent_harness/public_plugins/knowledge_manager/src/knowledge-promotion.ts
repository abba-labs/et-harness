import { randomUUID } from 'node:crypto'
import { readFileSync, renameSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { KnowledgeManagerEngine } from './knowledge-manager-engine.js'
import type { KnowledgeMutationResult, KnowledgeProjectIndex } from './contracts.js'

const atomicWrite = (file: string, content: string): void => {
  const temp = `${file}.${process.pid}.${randomUUID()}.tmp`
  writeFileSync(temp, content, 'utf-8')
  renameSync(temp, file)
}

const replaceStatus = (text: string, nodeId: string, status: string): string => {
  const lines = text.replaceAll('\r\n', '\n').split('\n')
  const escaped = nodeId.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const heading = new RegExp(`^(#{1,6})\\s+\\[${escaped}\\]\\s+`)
  const start = lines.findIndex(line => heading.test(line))
  if (start < 0) throw new Error(`Knowledge Node 标题不存在: ${nodeId}`)
  let end = start + 1
  while (end < lines.length && !/^#{1,6}\s+/.test(lines[end] ?? '')) end += 1
  const relative = lines.slice(start + 1, end).findIndex(line => /^Status:\s*/.test(line))
  if (relative < 0) throw new Error(`${nodeId} 缺少 Status`)
  lines[start + 1 + relative] = `Status: ${status}`
  return lines.join('\n')
}

export function promoteKnowledgeStatus(input: {
  readonly engine: KnowledgeManagerEngine
  readonly libraryKey: string
  readonly root: string
  readonly knowledgeId: string
  readonly targetStatus: 'VALIDATED' | 'FULL_VALIDATED'
  readonly reindex: () => KnowledgeProjectIndex
}): KnowledgeMutationResult {
  const node = input.engine.getNode(input.libraryKey, input.knowledgeId)?.node
  if (!node?.isLeaf || !node.category || !node.status) {
    throw new Error(`Knowledge 不存在: ${input.knowledgeId}`)
  }
  const validTransition = (node.status === 'CANDIDATE'
      && (input.targetStatus === 'VALIDATED' || input.targetStatus === 'FULL_VALIDATED'))
    || (node.status === 'VALIDATED' && input.targetStatus === 'FULL_VALIDATED')
  if (!validTransition) {
    throw new Error(`非法 Knowledge 晋级: ${node.status} -> ${input.targetStatus}: ${input.knowledgeId}`)
  }
  const route = input.engine.listFiles(input.libraryKey).find(file => file.id === node.fileId)
  if (!route) throw new Error(`Knowledge File 不存在: ${node.fileId}`)
  const file = join(input.root, route.file)
  const original = readFileSync(file, 'utf-8')

  atomicWrite(file, replaceStatus(original, input.knowledgeId, input.targetStatus))
  try {
    const snapshot = input.reindex()
    const promoted = input.engine.getNode(input.libraryKey, input.knowledgeId)?.node
    if (!promoted?.isLeaf || promoted.status !== input.targetStatus) {
      throw new Error(`Knowledge 晋级后未得到 ${input.targetStatus}: ${input.knowledgeId}`)
    }
    return {
      knowledgeId: input.knowledgeId,
      file: route.file,
      status: promoted.status,
      categoryId: promoted.category ?? node.category,
      ...(snapshot.sourceFingerprint ? { sourceFingerprint: snapshot.sourceFingerprint } : {}),
    }
  } catch (error) {
    atomicWrite(file, original)
    try { input.reindex() } catch { /* preserve original error */ }
    throw error
  }
}

/** Backward-compatible document-level promotion helper. */
export function promoteKnowledgeCandidate(input: {
  readonly engine: KnowledgeManagerEngine
  readonly libraryKey: string
  readonly root: string
  readonly knowledgeId: string
  readonly reindex: () => KnowledgeProjectIndex
}): KnowledgeMutationResult {
  return promoteKnowledgeStatus({ ...input, targetStatus: 'VALIDATED' })
}
