import { randomUUID } from 'node:crypto'
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import {
  TURN_CLOSURE_CONTRACT_VERSION,
  type ClosureModuleReceipt,
  type MandatoryClosureModuleId,
  type TurnClosureReceipt,
} from './contracts.js'
import { assertKernelIdentifier } from './lifecycle.js'
import {
  contentAddressedReadinessBindingEquals,
  validateContentAddressedReadinessBinding,
} from './reflection.js'

const atomicWriteJson = (file: string, value: unknown): void => {
  mkdirSync(dirname(file), { recursive: true })
  const temp = `${file}.${process.pid}.${randomUUID()}.tmp`
  writeFileSync(temp, `${JSON.stringify(value, null, 2)}\n`, 'utf-8')
  renameSync(temp, file)
}

const stringArray = (value: unknown, label: string): readonly string[] => {
  if (!Array.isArray(value) || value.some(item => typeof item !== 'string')) {
    throw new Error(`${label} must be a string array`)
  }
  return value
}

const validateModuleReceipt = (raw: unknown, taskId: string, turnId: string): ClosureModuleReceipt => {
  if (!raw || typeof raw !== 'object') throw new Error('Closure Module Receipt must be an object')
  const value = raw as Partial<ClosureModuleReceipt>
  if (typeof value.moduleId !== 'string' || typeof value.moduleVersion !== 'string') {
    throw new Error('Closure Module Receipt requires moduleId/moduleVersion')
  }
  assertKernelIdentifier('closure module id', value.moduleId)
  assertKernelIdentifier('closure module version', value.moduleVersion)
  if (value.taskId !== taskId || value.turnId !== turnId) {
    throw new Error(`Closure Module Receipt identity mismatch: ${value.moduleId}`)
  }
  if (typeof value.idempotencyKey !== 'string' || value.idempotencyKey.length === 0) {
    throw new Error(`Closure Module Receipt ${value.moduleId} requires idempotencyKey`)
  }
  if (!['APPLIED', 'NO_CHANGE', 'BLOCKED', 'FAILED'].includes(String(value.status))) {
    throw new Error(`Closure Module Receipt ${value.moduleId} has invalid status`)
  }
  stringArray(value.writes, `${value.moduleId}.writes`)
  stringArray(value.candidateRefs, `${value.moduleId}.candidateRefs`)
  stringArray(value.evidenceRefs, `${value.moduleId}.evidenceRefs`)
  if (value.stateVersionAfter !== undefined
      && (!Number.isInteger(value.stateVersionAfter) || value.stateVersionAfter < 0)) {
    throw new Error(`Closure Module Receipt ${value.moduleId} has invalid stateVersionAfter`)
  }
  if (value.reason !== undefined && typeof value.reason !== 'string') {
    throw new Error(`Closure Module Receipt ${value.moduleId} has invalid reason`)
  }
  return value as ClosureModuleReceipt
}

export class TurnClosureStore {
  constructor(private readonly storageRoot: string) {
    mkdirSync(storageRoot, { recursive: true })
  }

  getClosureRef(taskId: string, turnId: string): string {
    assertKernelIdentifier('taskId', taskId)
    assertKernelIdentifier('turnId', turnId)
    return `governance-closure://task/${taskId}/turn/${turnId}`
  }

  get(taskId: string, turnId: string): TurnClosureReceipt | undefined {
    const file = this.file(taskId, turnId)
    if (!existsSync(file)) return undefined
    const raw = JSON.parse(readFileSync(file, 'utf-8')) as Partial<TurnClosureReceipt>
    if (raw.contractVersion !== TURN_CLOSURE_CONTRACT_VERSION
        || raw.taskId !== taskId
        || raw.turnId !== turnId
        || typeof raw.attemptId !== 'string'
        || typeof raw.createdAt !== 'string'
        || typeof raw.journalRef !== 'string'
        || typeof raw.reflectionRef !== 'string'
        || typeof raw.inputFingerprint !== 'string'
        || !['COMPLETE', 'PENDING'].includes(String(raw.status))) {
      throw new Error(`Invalid Turn Closure Receipt: ${taskId}/${turnId}`)
    }
    const moduleReceipts = Array.isArray(raw.moduleReceipts)
      ? raw.moduleReceipts.map(item => validateModuleReceipt(item, taskId, turnId))
      : (() => { throw new Error('Turn Closure Receipt moduleReceipts must be an array') })()
    const missingMandatoryModuleIds = stringArray(
      raw.missingMandatoryModuleIds,
      'missingMandatoryModuleIds',
    ) as readonly MandatoryClosureModuleId[]
    const blockingReasons = stringArray(raw.blockingReasons, 'blockingReasons')
    const readinessBinding = raw.readinessBinding === undefined
      ? undefined
      : validateContentAddressedReadinessBinding(raw.readinessBinding)
    return {
      ...raw,
      ...(readinessBinding ? { readinessBinding } : {}),
      moduleReceipts,
      missingMandatoryModuleIds,
      blockingReasons,
    } as TurnClosureReceipt
  }

  put(receipt: TurnClosureReceipt): TurnClosureReceipt {
    const readinessBinding = receipt.readinessBinding === undefined
      ? undefined
      : validateContentAddressedReadinessBinding(receipt.readinessBinding)
    const normalized = {
      ...receipt,
      ...(readinessBinding ? { readinessBinding } : {}),
    }
    const existing = this.get(receipt.taskId, receipt.turnId)
    if (existing?.status === 'COMPLETE') {
      if (existing.inputFingerprint === receipt.inputFingerprint
          && contentAddressedReadinessBindingEquals(existing.readinessBinding, readinessBinding)) return existing
      throw new Error(`Completed Turn Closure Receipt cannot be replaced: ${receipt.taskId}/${receipt.turnId}`)
    }
    if (existing && (existing.inputFingerprint !== receipt.inputFingerprint
        || !contentAddressedReadinessBindingEquals(existing.readinessBinding, readinessBinding))) {
      throw new Error(`Turn Closure replay input changed: ${receipt.taskId}/${receipt.turnId}`)
    }
    atomicWriteJson(this.file(receipt.taskId, receipt.turnId), normalized)
    return normalized
  }

  private file(taskId: string, turnId: string): string {
    assertKernelIdentifier('taskId', taskId)
    assertKernelIdentifier('turnId', turnId)
    return join(this.storageRoot, 'turn-closure', taskId, `${turnId}.json`)
  }
}
