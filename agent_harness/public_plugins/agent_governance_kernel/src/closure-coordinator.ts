import { createHash, randomUUID } from 'node:crypto'
import {
  MANDATORY_CLOSURE_MODULE_IDS,
  TURN_CLOSURE_CONTRACT_VERSION,
  type ClosureModule,
  type ClosureModuleInput,
  type ClosureModuleReceipt,
  type TurnClosureReceipt,
  type TurnJournalRecord,
  type TurnReflectionRecord,
} from './contracts.js'
import { ClosureModuleRegistry } from './closure-module-registry.js'
import { contentAddressedReadinessBindingEquals } from './reflection.js'
import { TurnClosureStore } from './turn-closure-store.js'
import { TurnJournalStore } from './turn-journal-store.js'
import { TurnReflectionStore } from './turn-reflection-store.js'

const successful = (receipt: ClosureModuleReceipt): boolean =>
  receipt.status === 'APPLIED' || receipt.status === 'NO_CHANGE'

const sha256 = (value: unknown): string =>
  createHash('sha256').update(JSON.stringify(value)).digest('hex')

const journalRef = (journal: TurnJournalRecord): string =>
  `governance-journal://task/${journal.taskId}/turn/${journal.turnId}`

const closureInputFingerprint = (
  journal: TurnJournalRecord,
  reflection: TurnReflectionRecord,
): string => sha256({
  taskId: journal.taskId,
  turnId: journal.turnId,
  projectBinding: journal.projectBinding,
  reflectionRef: journal.reflectionRef,
  reflectionInputFingerprint: journal.reflectionInputFingerprint,
  readinessBinding: reflection.readinessBinding,
  mandatoryModuleIds: MANDATORY_CLOSURE_MODULE_IDS,
})

const idempotencyKeyFor = (inputFingerprint: string, module: ClosureModule): string =>
  `closure:${sha256({ inputFingerprint, moduleId: module.id, moduleVersion: module.version })}`

const failedReceipt = (
  module: ClosureModule,
  input: ClosureModuleInput,
  reason: string,
): ClosureModuleReceipt => ({
  moduleId: module.id,
  moduleVersion: module.version,
  taskId: input.taskId,
  turnId: input.turnId,
  idempotencyKey: input.idempotencyKey,
  status: 'FAILED',
  writes: [],
  candidateRefs: [],
  evidenceRefs: [],
  reason,
})

const validateModuleReceipt = (
  module: ClosureModule,
  input: ClosureModuleInput,
  raw: ClosureModuleReceipt,
): ClosureModuleReceipt => {
  if (!raw || typeof raw !== 'object') throw new Error('module returned a non-object receipt')
  if (raw.moduleId !== module.id) throw new Error(`moduleId mismatch: expected ${module.id}, got ${raw.moduleId}`)
  if (raw.moduleVersion !== module.version) {
    throw new Error(`moduleVersion mismatch for ${module.id}: expected ${module.version}, got ${raw.moduleVersion}`)
  }
  if (raw.taskId !== input.taskId || raw.turnId !== input.turnId) {
    throw new Error(`task/turn identity mismatch for ${module.id}`)
  }
  if (raw.idempotencyKey !== input.idempotencyKey) {
    throw new Error(`idempotencyKey mismatch for ${module.id}`)
  }
  if (!['APPLIED', 'NO_CHANGE', 'BLOCKED', 'FAILED'].includes(raw.status)) {
    throw new Error(`invalid status for ${module.id}: ${String(raw.status)}`)
  }
  for (const [label, values] of [
    ['writes', raw.writes],
    ['candidateRefs', raw.candidateRefs],
    ['evidenceRefs', raw.evidenceRefs],
  ] as const) {
    if (!Array.isArray(values) || values.some(value => typeof value !== 'string')) {
      throw new Error(`${module.id}.${label} must be a string array`)
    }
  }
  if ((raw.status === 'BLOCKED' || raw.status === 'FAILED') && !raw.reason?.trim()) {
    throw new Error(`${module.id} ${raw.status} receipt requires reason`)
  }
  return raw
}

export class ClosureCoordinator {
  constructor(
    private readonly journal: TurnJournalStore,
    private readonly reflections: TurnReflectionStore,
    private readonly modules: ClosureModuleRegistry,
    private readonly closures: TurnClosureStore,
  ) {}

  registerModule(module: ClosureModule): () => void {
    return this.modules.register(module)
  }

  listModules(): readonly ClosureModule[] {
    return this.modules.list()
  }

  getReceipt(taskId: string, turnId: string): TurnClosureReceipt | undefined {
    return this.closures.get(taskId, turnId)
  }

  async closeTurn(taskId: string, turnId: string): Promise<TurnClosureReceipt> {
    let journal = this.requireJournal(taskId, turnId)
    if (journal.status === 'OPEN') {
      throw new Error(`Turn ${turnId} must be SEALED and reflected before Closure`)
    }
    if (!journal.reflectionRef || !journal.reflectionInputFingerprint) {
      const attemptId = `closure:${turnId}:missing-reflection`
      if (journal.status !== 'CLOSED') {
        this.journal.markClosurePending(taskId, turnId, {
          attemptId,
          reason: 'Unified Turn Reflection is required before Closure Coordinator can run',
        })
      }
      throw new Error(`Turn ${turnId} requires Unified Reflection before Closure`)
    }

    const reflection = this.requireReflection(journal)
    const inputFingerprint = closureInputFingerprint(journal, reflection)
    const existing = this.closures.get(taskId, turnId)
    if (existing && (existing.inputFingerprint !== inputFingerprint
        || !contentAddressedReadinessBindingEquals(existing.readinessBinding, reflection.readinessBinding))) {
      throw new Error(`Turn Closure replay input changed: ${taskId}/${turnId}`)
    }
    if (existing?.status === 'COMPLETE') {
      if (journal.status !== 'CLOSED') {
        journal = this.journal.closeTurn(taskId, turnId, {
          closureReceiptRef: this.closures.getClosureRef(taskId, turnId),
        })
      }
      return existing
    }
    if (journal.status === 'CLOSED') {
      throw new Error(`CLOSED Turn ${turnId} is missing its persisted COMPLETE Closure Receipt`)
    }

    const attemptId = `closure:${turnId}:${randomUUID()}`
    const missingMandatoryModuleIds = this.modules.missingMandatory()
    if (missingMandatoryModuleIds.length > 0) {
      const blockingReasons = [
        `Mandatory Closure Modules unavailable: ${missingMandatoryModuleIds.join(', ')}`,
      ]
      const receipt = this.closures.put({
        contractVersion: TURN_CLOSURE_CONTRACT_VERSION,
        taskId,
        turnId,
        attemptId,
        createdAt: new Date().toISOString(),
        journalRef: journalRef(journal),
        reflectionRef: journal.reflectionRef,
        inputFingerprint,
        readinessBinding: reflection.readinessBinding,
        status: 'PENDING',
        moduleReceipts: existing?.moduleReceipts ?? [],
        missingMandatoryModuleIds,
        blockingReasons,
      })
      this.journal.markClosurePending(taskId, turnId, {
        attemptId,
        reason: blockingReasons.join('; '),
      })
      return receipt
    }

    const priorSuccessful = new Map<string, ClosureModuleReceipt>()
    for (const receipt of existing?.moduleReceipts ?? []) {
      if (successful(receipt)) priorSuccessful.set(receipt.moduleId, receipt)
    }

    const moduleReceipts: ClosureModuleReceipt[] = []
    for (const module of this.modules.list()) {
      const idempotencyKey = idempotencyKeyFor(inputFingerprint, module)
      const prior = priorSuccessful.get(module.id)
      if (prior
          && prior.moduleVersion === module.version
          && prior.idempotencyKey === idempotencyKey) {
        moduleReceipts.push(prior)
        continue
      }

      const input: ClosureModuleInput = {
        taskId,
        turnId,
        projectBinding: journal.projectBinding,
        journalRef: journalRef(journal),
        reflection: reflection.result,
        idempotencyKey,
        readinessBinding: reflection.readinessBinding,
      }
      try {
        const raw = await module.apply(input)
        moduleReceipts.push(validateModuleReceipt(module, input, raw))
      } catch (error) {
        const reason = error instanceof Error ? error.message : String(error)
        moduleReceipts.push(failedReceipt(module, input, reason))
      }
    }

    const moduleById = new Map(this.modules.list().map(module => [module.id, module]))
    const blockingReasons = moduleReceipts
      .filter(receipt => moduleById.get(receipt.moduleId)?.mandatory && !successful(receipt))
      .map(receipt => `${receipt.moduleId}: ${receipt.reason ?? receipt.status}`)
    const status = blockingReasons.length === 0 ? 'COMPLETE' : 'PENDING'
    const receipt = this.closures.put({
      contractVersion: TURN_CLOSURE_CONTRACT_VERSION,
      taskId,
      turnId,
      attemptId,
      createdAt: new Date().toISOString(),
      journalRef: journalRef(journal),
      reflectionRef: journal.reflectionRef,
      inputFingerprint,
      readinessBinding: reflection.readinessBinding,
      status,
      moduleReceipts,
      missingMandatoryModuleIds: [],
      blockingReasons,
    })

    if (status === 'COMPLETE') {
      this.journal.closeTurn(taskId, turnId, {
        closureReceiptRef: this.closures.getClosureRef(taskId, turnId),
      })
    } else {
      this.journal.markClosurePending(taskId, turnId, {
        attemptId,
        reason: blockingReasons.join('; '),
      })
    }
    return receipt
  }

  private requireJournal(taskId: string, turnId: string): TurnJournalRecord {
    const journal = this.journal.getTurn(taskId, turnId)
    if (!journal) throw new Error(`Turn Journal not found: ${taskId}/${turnId}`)
    return journal
  }

  private requireReflection(journal: TurnJournalRecord): TurnReflectionRecord {
    const reflection = this.reflections.get(journal.taskId, journal.turnId, journal)
    if (!reflection) {
      throw new Error(`Turn Reflection record not found: ${journal.taskId}/${journal.turnId}`)
    }
    if (reflection.inputFingerprint !== journal.reflectionInputFingerprint) {
      throw new Error(`Turn Reflection fingerprint mismatch: ${journal.taskId}/${journal.turnId}`)
    }
    return reflection
  }
}
