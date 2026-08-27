import type {
  TurnJournalRecord,
  TurnReflectionProvider,
  TurnReflectionProviderInput,
  TurnReflectionRecord,
  TurnReflectionRequest,
} from './contracts.js'
import { reflectionInputFingerprint, validateTurnReflectionResult } from './reflection.js'
import { TurnJournalStore } from './turn-journal-store.js'
import { TurnReflectionStore } from './turn-reflection-store.js'

const unique = (values: readonly string[]): string[] =>
  [...new Set(values.map(value => value.trim()).filter(Boolean))]

export class TurnReflectionController {
  private readonly providers = new Map<string, TurnReflectionProvider>()

  constructor(
    private readonly journal: TurnJournalStore,
    private readonly reflections: TurnReflectionStore,
  ) {}

  registerProvider(provider: TurnReflectionProvider): () => void {
    if (!provider.providerId.trim()) throw new Error('Reflection providerId cannot be empty')
    if (this.providers.has(provider.providerId)) throw new Error(`Reflection provider already registered: ${provider.providerId}`)
    this.providers.set(provider.providerId, provider)
    return () => { this.providers.delete(provider.providerId) }
  }

  listProviders(): readonly TurnReflectionProvider[] {
    return [...this.providers.values()].sort((a, b) =>
      (b.priority ?? 0) - (a.priority ?? 0) || a.providerId.localeCompare(b.providerId),
    )
  }

  getReflection(taskId: string, turnId: string): TurnReflectionRecord | undefined {
    const journal = this.requireJournal(taskId, turnId)
    return this.reflections.get(taskId, turnId, journal)
  }

  async reflectTurn(
    taskId: string,
    turnId: string,
    request: TurnReflectionRequest = {},
  ): Promise<TurnReflectionRecord> {
    let journal = this.requireJournal(taskId, turnId)
    if (journal.status === 'OPEN') journal = this.journal.sealTurn(taskId, turnId)
    if (journal.status === 'CLOSED') {
      const existing = this.reflections.get(taskId, turnId, journal)
      if (!existing) throw new Error(`CLOSED Turn ${turnId} is missing its required Reflection record`)
      return existing
    }

    const input = this.providerInput(journal, request)
    const fingerprint = reflectionInputFingerprint(input)
    const existing = this.reflections.get(taskId, turnId, journal)
    if (existing) {
      if (existing.inputFingerprint !== fingerprint) {
        throw new Error(`Turn ${turnId} already has Reflection for a different sealed input`)
      }
      return existing
    }

    const provider = this.listProviders()[0]
    const attemptId = `reflection:${turnId}:${fingerprint}`
    if (!provider) {
      this.journal.markClosurePending(taskId, turnId, {
        attemptId,
        reason: 'Unified Turn Reflection provider unavailable',
      })
      throw new Error('Unified Turn Reflection provider unavailable')
    }

    try {
      const raw = await provider.reflect(input)
      const result = validateTurnReflectionResult(raw, journal)
      const record = this.reflections.put({
        journal,
        providerId: provider.providerId,
        inputFingerprint: fingerprint,
        result,
      })
      this.journal.attachReflection(taskId, turnId, {
        reflectionRef: this.reflections.getReflectionRef(taskId, turnId),
        inputFingerprint: fingerprint,
      })
      return record
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error)
      this.journal.markClosurePending(taskId, turnId, { attemptId, reason })
      throw error
    }
  }

  private requireJournal(taskId: string, turnId: string): TurnJournalRecord {
    const journal = this.journal.getTurn(taskId, turnId)
    if (!journal) throw new Error(`Turn Journal not found: ${taskId}/${turnId}`)
    return journal
  }

  private providerInput(journal: TurnJournalRecord, request: TurnReflectionRequest): TurnReflectionProviderInput {
    const projectCandidateRefs = unique(request.projectCandidateRefs ?? [])
    if (journal.projectBinding.kind === 'UNBOUND' && projectCandidateRefs.length > 0) {
      throw new Error('UNBOUND Turn cannot provide projectCandidateRefs to Unified Reflection')
    }
    return {
      journal,
      ...(request.taskContextRef?.trim() ? { taskContextRef: request.taskContextRef.trim() } : {}),
      publicCandidateRefs: unique(request.publicCandidateRefs ?? []),
      projectCandidateRefs,
    }
  }
}
