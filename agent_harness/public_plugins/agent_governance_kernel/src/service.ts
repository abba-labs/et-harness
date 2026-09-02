import { homedir } from 'node:os'
import { join } from 'node:path'
import { Service, type Context } from '@deepseek-ai/cordis'
import type {
  AbortTurnInput,
  AppendTurnRefsInput,
  BeginTurnInput,
  ClosureModule,
  ClosureReplayRequirement,
  MandatoryClosureModuleId,
  MarkClosurePendingInput,
  TurnClosureReceipt,
  TurnJournalRecord,
  TurnReflectionProvider,
  TurnReflectionRecord,
  TurnReflectionRequest,
  TurnStartGuardResult,
} from './contracts.js'
import { ClosureCoordinator } from './closure-coordinator.js'
import { ClosureModuleRegistry } from './closure-module-registry.js'
import { closureReplayTurns, guardNewTurn } from './lifecycle.js'
import { TurnClosureStore } from './turn-closure-store.js'
import { TurnJournalStore } from './turn-journal-store.js'
import { TurnReflectionController } from './turn-reflection-controller.js'
import { TurnReflectionStore } from './turn-reflection-store.js'

const defaultKernelStorageRoot = (): string =>
  join(process.env.AGENT_HARNESS_STATE_ROOT ?? join(homedir(), '.agent-harness', 'runtime'), 'agent-governance-kernel')

export class AgentGovernanceKernelService extends Service {
  private readonly journal: TurnJournalStore
  private readonly reflection: TurnReflectionController
  private readonly closureModules: ClosureModuleRegistry
  private readonly closure: ClosureCoordinator

  constructor(ctx: Context) {
    super(ctx, 'agentGovernanceKernel')
    const root = defaultKernelStorageRoot()
    this.journal = new TurnJournalStore(root)
    const reflectionStore = new TurnReflectionStore(root)
    this.reflection = new TurnReflectionController(this.journal, reflectionStore)
    this.closureModules = new ClosureModuleRegistry()
    this.closure = new ClosureCoordinator(
      this.journal,
      reflectionStore,
      this.closureModules,
      new TurnClosureStore(root),
    )
  }

  getStorageRoot(): string {
    return this.journal.getStorageRoot()
  }

  registerReflectionProvider(provider: TurnReflectionProvider): () => void {
    return this.reflection.registerProvider(provider)
  }

  listReflectionProviders(): readonly TurnReflectionProvider[] {
    return this.reflection.listProviders()
  }

  reflectTurn(taskId: string, turnId: string, request: TurnReflectionRequest = {}): Promise<TurnReflectionRecord> {
    return this.reflection.reflectTurn(taskId, turnId, request)
  }

  getReflection(taskId: string, turnId: string): TurnReflectionRecord | undefined {
    return this.reflection.getReflection(taskId, turnId)
  }

  registerClosureModule(module: ClosureModule): () => void {
    return this.closure.registerModule(module)
  }

  listClosureModules(): readonly ClosureModule[] {
    return this.closure.listModules()
  }

  getMissingMandatoryClosureModules(): readonly MandatoryClosureModuleId[] {
    return this.closureModules.missingMandatory()
  }

  getClosureReceipt(taskId: string, turnId: string): TurnClosureReceipt | undefined {
    return this.closure.getReceipt(taskId, turnId)
  }

  closeTurn(taskId: string, turnId: string): Promise<TurnClosureReceipt> {
    return this.closure.closeTurn(taskId, turnId)
  }

  guardTurnStart(taskId: string, turnId: string): TurnStartGuardResult {
    return guardNewTurn(this.journal.listTurns(taskId), turnId)
  }

  beginTurn(input: BeginTurnInput): TurnJournalRecord {
    const existing = this.journal.getTurn(input.taskId, input.turnId)
    if (existing) {
      if (existing.status !== 'OPEN') {
        throw new Error(`Turn ${input.turnId} already exists with status ${existing.status}`)
      }
      return this.journal.beginTurn(input)
    }
    const guard = this.guardTurnStart(input.taskId, input.turnId)
    if (!guard.allowed) throw new Error(guard.reason ?? 'Previous Turn closure is unresolved')
    return this.journal.beginTurn(input)
  }

  abortTurn(taskId: string, turnId: string, input: AbortTurnInput): TurnJournalRecord {
    return this.journal.abortTurn(taskId, turnId, input)
  }

  appendTurnRefs(taskId: string, turnId: string, input: AppendTurnRefsInput): TurnJournalRecord {
    return this.journal.appendRefs(taskId, turnId, input)
  }

  bindProject(taskId: string, turnId: string, projectId: string): TurnJournalRecord {
    return this.journal.bindProject(taskId, turnId, projectId)
  }

  sealTurn(taskId: string, turnId: string, closingAt?: string): TurnJournalRecord {
    return this.journal.sealTurn(taskId, turnId, closingAt)
  }

  markClosurePending(
    taskId: string,
    turnId: string,
    input: MarkClosurePendingInput,
  ): TurnJournalRecord {
    return this.journal.markClosurePending(taskId, turnId, input)
  }

  getTurn(taskId: string, turnId: string): TurnJournalRecord | undefined {
    return this.journal.getTurn(taskId, turnId)
  }

  listTurns(taskId: string): readonly TurnJournalRecord[] {
    return this.journal.listTurns(taskId)
  }

  getClosureReplayRequirement(taskId: string): ClosureReplayRequirement {
    const turns = closureReplayTurns(this.journal.listTurns(taskId))
    return {
      required: turns.length > 0,
      turnIds: turns.map(turn => turn.turnId),
      statuses: turns.map(turn => turn.status),
    }
  }

  getUnresolvedTurns(taskId: string): readonly TurnJournalRecord[] {
    return this.journal.listUnresolvedTurns(taskId)
  }
}

declare module '@deepseek-ai/cordis' {
  interface Context {
    agentGovernanceKernel: AgentGovernanceKernelService
  }
}

export default AgentGovernanceKernelService
