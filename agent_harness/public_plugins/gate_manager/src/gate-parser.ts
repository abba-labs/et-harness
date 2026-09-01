import { parse } from 'yaml'
import type {
  GateExecution,
  GateLevel,
  GateNode,
  GateStep,
  GateStepRole,
} from './contracts.js'

const VALID_LEVELS = new Set<GateLevel>(['MUST', 'MAY'])
const VALID_STEP_ROLES = new Set<GateStepRole>(['REVIEW', 'EVIDENCE_PRODUCER'])
const TOOL_CAPABILITY_RE = /^[a-z][a-z0-9_-]*(?:\.[a-z0-9_-]+)+$/
const NODE_ID_RE = /^G\d{3}(?:\.\d{3})+$/

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const nonEmpty = (value: unknown): value is string =>
  typeof value === 'string' && value.trim().length > 0

const nodeDepth = (id: string): number => id.split('.').length

const expectedParentId = (id: string): string =>
  id.split('.').slice(0, -1).join('.')

const parseRefs = (value: unknown, path: string): readonly string[] => {
  if (value === undefined) return []
  if (!Array.isArray(value) || value.some(item => !nonEmpty(item))) {
    throw new Error(`${path}.refs 必须是字符串数组`)
  }
  return value as string[]
}

const parseSteps = (value: unknown, path: string): readonly GateStep[] => {
  if (!Array.isArray(value) || value.length === 0) {
    throw new Error(`${path}.steps 必须是非空数组`)
  }

  const seen = new Set<string>()
  return value.map((raw, index) => {
    const stepPath = `${path}.steps[${index}]`
    if (!isRecord(raw)) throw new Error(`${stepPath} 必须是对象`)
    if (!nonEmpty(raw.id)) throw new Error(`${stepPath}.id 不能为空`)
    if (seen.has(raw.id)) throw new Error(`${path} Step ID 重复: ${raw.id}`)
    seen.add(raw.id)

    if (!nonEmpty(raw.tool) || !TOOL_CAPABILITY_RE.test(raw.tool)) {
      throw new Error(`${stepPath}.tool 必须是合法 Tool Capability`)
    }
    let role: GateStepRole | undefined
    if (raw.role !== undefined) {
      const normalizedRole = typeof raw.role === 'string' ? raw.role.toUpperCase() : ''
      if (!VALID_STEP_ROLES.has(normalizedRole as GateStepRole)) {
        throw new Error(`${stepPath}.role 必须为 REVIEW | EVIDENCE_PRODUCER`)
      }
      role = normalizedRole as GateStepRole
    }
    if (raw.args !== undefined && !isRecord(raw.args)) {
      throw new Error(`${stepPath}.args 必须是对象`)
    }

    return {
      id: raw.id,
      tool: raw.tool,
      ...(role ? { role } : {}),
      ...(raw.args ? { args: raw.args } : {}),
    }
  })
}

const parseExecution = (value: unknown, path: string): GateExecution => {
  if (!isRecord(value)) throw new Error(`${path}.gate 必须是对象`)
  const rawLevel = typeof value.level === 'string' ? value.level.toUpperCase() : ''
  if (!VALID_LEVELS.has(rawLevel as GateLevel)) {
    throw new Error(`${path}.gate.level 必须为 MUST | MAY`)
  }
  if (!nonEmpty(value.when)) throw new Error(`${path}.gate.when 不能为空`)
  const steps = parseSteps(value.steps, `${path}.gate`)
  if (value.pass === undefined || value.pass === null) {
    throw new Error(`${path}.gate.pass 不能为空`)
  }
  if (typeof value.pass === 'string' && !value.pass.trim()) {
    throw new Error(`${path}.gate.pass 不能为空`)
  }

  return {
    level: rawLevel as GateLevel,
    when: value.when,
    steps,
    pass: value.pass,
    refs: parseRefs(value.refs, `${path}.gate`),
  }
}

export interface GateFileParseResult {
  readonly title: string
  readonly nodes: readonly GateNode[]
  readonly warnings: readonly string[]
}

export function parseGateFile(
  expectedFileId: string,
  fileName: string,
  text: string,
): GateFileParseResult {
  const raw: unknown = parse(text)
  if (!isRecord(raw)) throw new Error(`${fileName} Gate 文件必须是 YAML 对象`)
  if (raw.standard !== 'gate-v0.1') throw new Error(`${fileName} standard 必须为 gate-v0.1`)
  if (raw.file_id !== expectedFileId) {
    throw new Error(`${fileName} file_id 必须为 ${expectedFileId}`)
  }
  if (!nonEmpty(raw.title)) throw new Error(`${fileName} title 不能为空`)
  if (!Array.isArray(raw.nodes)) throw new Error(`${fileName} nodes 必须是数组`)

  const nodes = new Map<string, GateNode>()
  const warnings: string[] = []
  const root: GateNode = {
    id: expectedFileId,
    fileId: expectedFileId,
    title: raw.title,
    depth: 1,
    children: [],
    location: `${fileName}#${expectedFileId}`,
    isGate: false,
  }
  nodes.set(root.id, root)

  const parseNode = (
    value: unknown,
    parentId: string,
    path: string,
  ): GateNode => {
    if (!isRecord(value)) throw new Error(`${path} 必须是对象`)
    if (!nonEmpty(value.id) || !NODE_ID_RE.test(value.id)) {
      throw new Error(`${path}.id 必须是合法 Gxxx.xxx Node ID`)
    }
    if (!nonEmpty(value.title)) throw new Error(`${path}.title 不能为空`)
    if (value.id.split('.')[0] !== expectedFileId) {
      throw new Error(`${path}.id ${value.id} 不属于 File ID ${expectedFileId}`)
    }
    if (expectedParentId(value.id) !== parentId) {
      throw new Error(`${path}.id ${value.id} 的父地址必须为 ${parentId}`)
    }
    if (nodes.has(value.id)) throw new Error(`${fileName} Gate Node ID 重复: ${value.id}`)

    const rawChildren = value.children
    const hasChildren = rawChildren !== undefined
    const hasGate = value.gate !== undefined
    if (hasChildren && hasGate) {
      throw new Error(`${path} Branch 与 Executable Gate 不能同时定义 children 和 gate`)
    }
    if (!hasChildren && !hasGate) {
      throw new Error(`${path} 必须是 Branch(children) 或 Executable Gate(gate)`)
    }

    if (hasChildren) {
      if (!Array.isArray(rawChildren) || rawChildren.length === 0) {
        throw new Error(`${path}.children 必须是非空数组`)
      }
      const node: GateNode = {
        id: value.id,
        fileId: expectedFileId,
        title: value.title,
        depth: nodeDepth(value.id),
        parentId,
        children: [],
        location: `${fileName}#${value.id}`,
        isGate: false,
      }
      nodes.set(node.id, node)
      const children = rawChildren.map((child, index) =>
        parseNode(child, node.id, `${path}.children[${index}]`),
      )
      const complete: GateNode = { ...node, children: children.map(child => child.id) }
      nodes.set(node.id, complete)
      return complete
    }

    const gate = parseExecution(value.gate, path)
    if (gate.when.length > 300) {
      warnings.push(`${value.id} when 过长；应保持可快速判断的触发条件`)
    }
    const node: GateNode = {
      id: value.id,
      fileId: expectedFileId,
      title: value.title,
      depth: nodeDepth(value.id),
      parentId,
      children: [],
      location: `${fileName}#${value.id}`,
      isGate: true,
      gate,
    }
    nodes.set(node.id, node)
    return node
  }

  const topNodes = raw.nodes.map((node, index) =>
    parseNode(node, expectedFileId, `nodes[${index}]`),
  )
  nodes.set(root.id, { ...root, children: topNodes.map(node => node.id) })

  return {
    title: raw.title,
    nodes: [...nodes.values()],
    warnings,
  }
}
