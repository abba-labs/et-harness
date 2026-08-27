import {
  appendFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  renameSync,
  writeFileSync,
} from 'node:fs'
import { createHash, randomUUID } from 'node:crypto'
import { dirname, join } from 'node:path'
import type {
  EvidenceQuery,
  EvidenceRecord,
  EvidenceRecordInput,
  EvidenceResult,
  ProjectStateSnapshot,
  StateRecord,
  StateUpdateInput,
} from './contracts.js'

const PROJECT_ID_RE = /^[a-z0-9][a-z0-9._-]{1,63}$/
const VALID_RESULTS = new Set<EvidenceResult>(['PASS', 'FAIL', 'INFO', 'SKIP'])
const nonEmpty = (value: string): boolean => value.trim().length > 0

const assertProjectId = (projectId: string): void => {
  if (!PROJECT_ID_RE.test(projectId)) throw new Error(`非法 projectId: ${projectId}`)
}

const assertStringArray = (value: readonly string[] | undefined, field: string): void => {
  if (value === undefined) return
  if (!Array.isArray(value) || value.some(item => typeof item !== 'string' || !item.trim())) {
    throw new Error(`${field} 必须是非空字符串数组`)
  }
}

const assertJsonSerializable = (value: unknown, field: string): void => {
  let serialized: string | undefined
  try {
    serialized = JSON.stringify(value)
  } catch (error) {
    throw new Error(`${field} 必须可 JSON 序列化: ${error instanceof Error ? error.message : String(error)}`)
  }
  if (serialized === undefined) throw new Error(`${field} 必须可 JSON 序列化`)
}

const taskFileKey = (taskId: string): string =>
  createHash('sha256').update(taskId).digest('hex').slice(0, 20)

const stateRecordKey = (scope: string, key: string): string => `${scope}\u0000${key}`

interface PersistedProjectState {
  projectId: string
  records: Record<string, StateRecord>
}

export class EvidenceStateEngine {
  private readonly evidenceIds = new Map<string, Set<string>>()

  constructor(private readonly storageRoot: string) {}

  getStorageRoot(): string {
    return this.storageRoot
  }

  recordEvidence(input: EvidenceRecordInput): EvidenceRecord {
    assertProjectId(input.projectId)
    if (!nonEmpty(input.taskId)) throw new Error('taskId 不能为空')
    if (!nonEmpty(input.kind)) throw new Error('evidence kind 不能为空')
    if (!VALID_RESULTS.has(input.result)) throw new Error(`非法 evidence result: ${input.result}`)
    if (!nonEmpty(input.summary)) throw new Error('evidence summary 不能为空')
    if (!nonEmpty(input.source)) throw new Error('evidence source 不能为空')
    if (input.gateId !== undefined && !nonEmpty(input.gateId)) throw new Error('gateId 不能为空字符串')
    assertStringArray(input.artifactRefs, 'artifactRefs')
    if (input.metadata !== undefined) assertJsonSerializable(input.metadata, 'evidence metadata')

    const record: EvidenceRecord = {
      ...input,
      evidenceId: `EV-${new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)}-${randomUUID()}`,
      recordedAt: new Date().toISOString(),
    }

    assertJsonSerializable(record, 'Evidence')
    const file = this.evidenceTaskFile(input.projectId, input.taskId)
    mkdirSync(dirname(file), { recursive: true })
    appendFileSync(file, `${JSON.stringify(record)}\n`, 'utf-8')

    const ids = this.evidenceIds.get(input.projectId) ?? new Set<string>()
    ids.add(record.evidenceId)
    this.evidenceIds.set(input.projectId, ids)
    return record
  }

  listEvidence(query: EvidenceQuery): readonly EvidenceRecord[] {
    assertProjectId(query.projectId)
    if (query.taskId !== undefined && !nonEmpty(query.taskId)) throw new Error('taskId 不能为空字符串')
    if (query.result !== undefined && !VALID_RESULTS.has(query.result)) throw new Error(`非法 evidence result: ${query.result}`)
    if (query.gateId !== undefined && !nonEmpty(query.gateId)) throw new Error('gateId 不能为空字符串')

    let records: EvidenceRecord[] = []
    if (query.taskId) {
      records = this.readEvidenceFile(this.evidenceTaskFile(query.projectId, query.taskId))
    } else {
      const dir = this.projectEvidenceDir(query.projectId)
      if (existsSync(dir)) {
        for (const file of readdirSync(dir).filter(name => name.endsWith('.jsonl')).sort()) {
          records.push(...this.readEvidenceFile(join(dir, file)))
        }
      }
    }

    records = records.filter(record =>
      (!query.result || record.result === query.result)
      && (!query.gateId || record.gateId === query.gateId),
    )
    records.sort((a, b) => b.recordedAt.localeCompare(a.recordedAt))
    const limit = Math.max(1, query.limit ?? 100)
    return records.slice(0, limit)
  }

  getEvidence(projectId: string, evidenceId: string): EvidenceRecord | undefined {
    if (!nonEmpty(evidenceId)) throw new Error('evidenceId 不能为空')
    return this.listEvidence({ projectId, limit: Number.MAX_SAFE_INTEGER })
      .find(record => record.evidenceId === evidenceId)
  }

  updateState(input: StateUpdateInput): StateRecord {
    assertProjectId(input.projectId)
    if (!nonEmpty(input.scope)) throw new Error('state scope 不能为空')
    if (!nonEmpty(input.key)) throw new Error('state key 不能为空')
    if (!nonEmpty(input.reason)) throw new Error('state reason 不能为空')
    if (input.expectedVersion !== undefined && (!Number.isInteger(input.expectedVersion) || input.expectedVersion < 0)) {
      throw new Error('expectedVersion 必须是非负整数')
    }
    assertStringArray(input.evidenceRefs, 'state evidenceRefs')
    assertJsonSerializable(input.value, 'state value')

    for (const evidenceId of input.evidenceRefs ?? []) {
      if (!this.evidenceExists(input.projectId, evidenceId)) {
        throw new Error(`State 引用不存在或不属于当前项目的 Evidence: ${evidenceId}`)
      }
    }

    const state = this.readPersistedState(input.projectId)
    const recordKey = stateRecordKey(input.scope, input.key)
    const current = state.records[recordKey]
    const currentVersion = current?.version ?? 0

    if (input.expectedVersion !== undefined && input.expectedVersion !== currentVersion) {
      throw new Error(
        `State version conflict: ${input.scope}/${input.key} expected=${input.expectedVersion} actual=${currentVersion}`,
      )
    }

    const record: StateRecord = {
      projectId: input.projectId,
      scope: input.scope,
      key: input.key,
      value: input.value,
      version: currentVersion + 1,
      reason: input.reason,
      evidenceRefs: [...(input.evidenceRefs ?? [])],
      updatedAt: new Date().toISOString(),
    }

    state.records[recordKey] = record
    this.writePersistedState(state)
    return record
  }

  readState(projectId: string, scope: string, key: string): StateRecord | undefined {
    assertProjectId(projectId)
    if (!nonEmpty(scope) || !nonEmpty(key)) throw new Error('state scope / key 不能为空')
    return this.readPersistedState(projectId).records[stateRecordKey(scope, key)]
  }

  snapshot(projectId: string): ProjectStateSnapshot {
    assertProjectId(projectId)
    const state = this.readPersistedState(projectId)
    return {
      projectId,
      records: Object.values(state.records).sort((a, b) =>
        a.scope.localeCompare(b.scope) || a.key.localeCompare(b.key),
      ),
    }
  }

  private evidenceExists(projectId: string, evidenceId: string): boolean {
    let ids = this.evidenceIds.get(projectId)
    if (!ids) {
      ids = new Set(this.listEvidence({ projectId, limit: Number.MAX_SAFE_INTEGER }).map(item => item.evidenceId))
      this.evidenceIds.set(projectId, ids)
    }
    return ids.has(evidenceId)
  }

  private projectEvidenceDir(projectId: string): string {
    return join(this.storageRoot, 'evidence', projectId)
  }

  private evidenceTaskFile(projectId: string, taskId: string): string {
    return join(this.projectEvidenceDir(projectId), `task-${taskFileKey(taskId)}.jsonl`)
  }

  private stateFile(projectId: string): string {
    return join(this.storageRoot, 'state', `${projectId}.json`)
  }

  private readEvidenceFile(file: string): EvidenceRecord[] {
    if (!existsSync(file)) return []
    const text = readFileSync(file, 'utf-8')
    const records: EvidenceRecord[] = []
    for (const [index, line] of text.split('\n').entries()) {
      if (!line.trim()) continue
      try {
        records.push(JSON.parse(line) as EvidenceRecord)
      } catch {
        throw new Error(`Evidence 数据损坏: ${file}:${index + 1}`)
      }
    }
    return records
  }

  private readPersistedState(projectId: string): PersistedProjectState {
    const file = this.stateFile(projectId)
    if (!existsSync(file)) return { projectId, records: {} }
    try {
      const parsed = JSON.parse(readFileSync(file, 'utf-8')) as PersistedProjectState
      if (parsed.projectId !== projectId || typeof parsed.records !== 'object' || parsed.records === null) {
        throw new Error('invalid state shape')
      }
      return parsed
    } catch (error) {
      throw new Error(`State 数据损坏: ${file}; ${error instanceof Error ? error.message : String(error)}`)
    }
  }

  private writePersistedState(state: PersistedProjectState): void {
    const file = this.stateFile(state.projectId)
    mkdirSync(dirname(file), { recursive: true })
    const temp = `${file}.${process.pid}.${randomUUID()}.tmp`
    writeFileSync(temp, `${JSON.stringify(state, null, 2)}\n`, 'utf-8')
    renameSync(temp, file)
  }
}
