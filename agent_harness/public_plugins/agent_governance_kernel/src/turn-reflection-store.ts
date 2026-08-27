import { randomUUID } from 'node:crypto'
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import {
  TURN_REFLECTION_CONTRACT_VERSION,
  type TurnJournalRecord,
  type TurnReflectionRecord,
  type TurnReflectionResult,
} from './contracts.js'
import { assertKernelIdentifier } from './lifecycle.js'
import { validateTurnReflectionResult } from './reflection.js'

const atomicWriteJson = (file: string, value: unknown): void => {
  mkdirSync(dirname(file), { recursive: true })
  const temp = `${file}.${process.pid}.${randomUUID()}.tmp`
  writeFileSync(temp, `${JSON.stringify(value, null, 2)}\n`, 'utf-8')
  renameSync(temp, file)
}

export class TurnReflectionStore {
  constructor(private readonly storageRoot: string) {
    mkdirSync(storageRoot, { recursive: true })
  }

  getReflectionRef(taskId: string, turnId: string): string {
    assertKernelIdentifier('taskId', taskId)
    assertKernelIdentifier('turnId', turnId)
    return `governance-reflection://task/${taskId}/turn/${turnId}`
  }

  get(taskId: string, turnId: string, journal: TurnJournalRecord): TurnReflectionRecord | undefined {
    const file = this.file(taskId, turnId)
    if (!existsSync(file)) return undefined
    const raw = JSON.parse(readFileSync(file, 'utf-8')) as Partial<TurnReflectionRecord>
    if (raw.contractVersion !== TURN_REFLECTION_CONTRACT_VERSION
        || raw.taskId !== taskId
        || raw.turnId !== turnId
        || typeof raw.providerId !== 'string'
        || typeof raw.createdAt !== 'string'
        || typeof raw.journalRef !== 'string'
        || typeof raw.inputFingerprint !== 'string') {
      throw new Error(`Invalid Turn Reflection record: ${taskId}/${turnId}`)
    }
    const result = validateTurnReflectionResult(raw.result, journal)
    return { ...raw, result } as TurnReflectionRecord
  }

  put(input: {
    readonly journal: TurnJournalRecord
    readonly providerId: string
    readonly inputFingerprint: string
    readonly result: TurnReflectionResult
  }): TurnReflectionRecord {
    const { journal, providerId, inputFingerprint, result } = input
    assertKernelIdentifier('providerId', providerId)
    const existing = this.get(journal.taskId, journal.turnId, journal)
    if (existing) {
      if (existing.inputFingerprint === inputFingerprint && existing.providerId === providerId) return existing
      throw new Error(`Turn Reflection already exists with a different input/provider: ${journal.taskId}/${journal.turnId}`)
    }
    const record: TurnReflectionRecord = {
      contractVersion: TURN_REFLECTION_CONTRACT_VERSION,
      taskId: journal.taskId,
      turnId: journal.turnId,
      providerId,
      createdAt: new Date().toISOString(),
      journalRef: `governance-journal://task/${journal.taskId}/turn/${journal.turnId}`,
      inputFingerprint,
      result,
    }
    atomicWriteJson(this.file(journal.taskId, journal.turnId), record)
    return record
  }

  private file(taskId: string, turnId: string): string {
    assertKernelIdentifier('taskId', taskId)
    assertKernelIdentifier('turnId', turnId)
    return join(this.storageRoot, 'turn-reflection', taskId, `${turnId}.json`)
  }
}
