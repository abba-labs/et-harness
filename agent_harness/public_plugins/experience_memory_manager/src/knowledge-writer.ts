import type { ExperienceCandidate } from './contracts.js'

const HEADING_RE = /^(#{1,6})\s+\[(K\d{3}(?:\.\d{3})*)\]\s+(.+?)\s*$/
const KNOWLEDGE_ID_RE = /^K\d{3}(?:\.\d{3})+$/

const parentIdOf = (id: string): string => id.split('.').slice(0, -1).join('.')

export function renderPromotedKnowledgeLeaf(
  candidate: ExperienceCandidate,
  nodeId: string,
  title: string,
  headingLevel: number,
): string {
  if (!KNOWLEDGE_ID_RE.test(nodeId)) throw new Error(`非法 Knowledge Node ID: ${nodeId}`)
  if (headingLevel < 2 || headingLevel > 6) throw new Error(`非法 Knowledge 标题层级: ${headingLevel}`)

  const lines = [
    `${'#'.repeat(headingLevel)} [${nodeId}] ${title.trim()}`,
    '',
    'Status: VALIDATED',
    `Fact: ${candidate.fact.trim()}`,
    candidate.scope?.trim() ? `Scope: ${candidate.scope.trim()}` : '',
    `Provenance: ${candidate.evidenceRefs.join(', ')}`,
    candidate.refs && candidate.refs.length > 0 ? `Refs: [${candidate.refs.join(', ')}]` : '',
    '',
  ].filter((line, index, all) => line !== '' || index === 1 || index === all.length - 1)

  return `${lines.join('\n')}\n`
}

export function insertKnowledgeLeaf(
  originalText: string,
  parentNodeId: string,
  nodeId: string,
  title: string,
  candidate: ExperienceCandidate,
): string {
  if (parentIdOf(nodeId) !== parentNodeId) {
    throw new Error(`Knowledge Node ${nodeId} 必须是父节点 ${parentNodeId} 的直接子节点`)
  }

  const lines = originalText.replaceAll('\r\n', '\n').split('\n')
  let parentLine = -1
  let parentLevel = 0

  for (const [index, line] of lines.entries()) {
    const match = HEADING_RE.exec(line)
    if (!match) continue
    if (match[2] === nodeId) throw new Error(`Knowledge Node 已存在: ${nodeId}`)
    if (match[2] === parentNodeId) {
      parentLine = index
      parentLevel = match[1]!.length
    }
  }

  if (parentLine < 0) throw new Error(`Knowledge 父节点不存在: ${parentNodeId}`)
  if (parentLevel >= 6) throw new Error(`Knowledge 父节点层级过深，无法添加子节点: ${parentNodeId}`)

  let insertAt = lines.length
  for (let index = parentLine + 1; index < lines.length; index += 1) {
    const match = HEADING_RE.exec(lines[index] ?? '')
    if (match && match[1]!.length <= parentLevel) {
      insertAt = index
      break
    }
  }

  const block = renderPromotedKnowledgeLeaf(candidate, nodeId, title, parentLevel + 1)
    .replace(/\n$/, '')
    .split('\n')

  const before = lines.slice(0, insertAt)
  while (before.length > 0 && before[before.length - 1] === '') before.pop()
  const after = lines.slice(insertAt)
  while (after.length > 0 && after[0] === '') after.shift()

  return [...before, '', ...block, '', ...after].join('\n').replace(/\n+$/, '\n')
}
