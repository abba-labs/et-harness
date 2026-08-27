import { createHash } from 'node:crypto'
import type {
  ContextLedgerEntry,
  ContextManagementService,
  ContextReference,
} from '@agent-harness/context-builder'
import type { EvidenceStateManagerService } from '@agent-harness/evidence-state-manager'
import type { GateManagerService } from '@agent-harness/gate-manager'
import type {
  ClosureModule,
  ClosureModuleInput,
  ClosureModuleReceipt,
  ReflectionCandidate,
} from '@agent-harness/agent-governance-kernel'
import {
  GovernanceChangeCandidateStore,
  type GovernanceChangeDomain,
  type GovernanceChangeScope,
} from './change-candidate-store.js'

const MODULE_VERSION = '0.1.0'

const unique = (values: readonly string[]): string[] =>
  [...new Set(values.map(value => value.trim()).filter(Boolean))]

const successfulReceipt = (
  module: ClosureModule,
  input: ClosureModuleInput,
  details: {
    status: 'APPLIED' | 'NO_CHANGE'
    writes?: readonly string[]
    candidateRefs?: readonly string[]
    evidenceRefs?: readonly string[]
    stateVersionAfter?: number
  },
): ClosureModuleReceipt => ({
  moduleId: module.id,
  moduleVersion: module.version,
  taskId: input.taskId,
  turnId: input.turnId,
  idempotencyKey: input.idempotencyKey,
  status: details.status,
  writes: details.writes ?? [],
  candidateRefs: details.candidateRefs ?? [],
  evidenceRefs: details.evidenceRefs ?? [],
  ...(details.stateVersionAfter !== undefined ? { stateVersionAfter: details.stateVersionAfter } : {}),
})

const blockedReceipt = (
  module: ClosureModule,
  input: ClosureModuleInput,
  reason: string,
): ClosureModuleReceipt => ({
  moduleId: module.id,
  moduleVersion: module.version,
  taskId: input.taskId,
  turnId: input.turnId,
  idempotencyKey: input.idempotencyKey,
  status: 'BLOCKED',
  writes: [],
  candidateRefs: [],
  evidenceRefs: [],
  reason,
})

const same = (left: unknown, right: unknown): boolean => JSON.stringify(left) === JSON.stringify(right)

const refId = (reference: string, prefix: string, idPattern: RegExp): string | undefined => {
  const trimmed = reference.trim()
  if (idPattern.test(trimmed)) return trimmed.toUpperCase()
  if (!trimmed.toLowerCase().startsWith(`${prefix}://`)) return undefined
  return trimmed.split('/').map(part => part.trim()).reverse().find(part => idPattern.test(part))?.toUpperCase()
}

const toContextReference = (reference: string, projectId: string): ContextReference | undefined => {
  const architecture = refId(reference, 'architecture', /^A\d{3}(?:\.\d{3})*$/i)
  if (architecture) return { kind: 'architecture', id: architecture }
  const rule = refId(reference, 'rule', /^R\d{3}(?:\.\d{3})*$/i)
  if (rule) return { kind: 'rule', id: rule }
  const gate = refId(reference, 'gate', /^G\d{3}(?:\.\d{3})*$/i)
  if (gate) return { kind: 'gate', id: gate }
  const trimmed = reference.trim()
  if (/^K\d{3}(?:\.\d{3})*$/i.test(trimmed)) return { kind: 'knowledge', id: trimmed.toUpperCase() }
  const projectPrefix = `knowledge://project/${projectId}/`
  if (trimmed.toLowerCase().startsWith(projectPrefix.toLowerCase())) {
    const id = trimmed.slice(projectPrefix.length)
    if (/^K\d{3}(?:\.\d{3})*$/i.test(id)) return { kind: 'knowledge', id: id.toUpperCase() }
  }
  return undefined
}

const desiredWorkingSet = (input: ClosureModuleInput, projectId: string): ContextReference[] => {
  const remove = new Set(
    input.reflection.workingSet.remove
      .map(ref => toContextReference(ref, projectId))
      .filter((ref): ref is ContextReference => !!ref)
      .map(ref => `${ref.kind}:${ref.id}`),
  )
  const selected = [...input.reflection.workingSet.keep, ...input.reflection.workingSet.add]
    .map(ref => toContextReference(ref, projectId))
    .filter((ref): ref is ContextReference => !!ref)
    .filter(ref => !remove.has(`${ref.kind}:${ref.id}`))
  const deduped = new Map(selected.map(ref => [`${ref.kind}:${ref.id}`, ref]))
  return [...deduped.values()]
}

export function createContextLedgerClosureModule(
  manager: Pick<ContextManagementService, 'getTask' | 'updateTaskLedger' | 'updateProgressLedger'>,
): ClosureModule {
  const module: ClosureModule = {
    id: 'context-closure',
    version: MODULE_VERSION,
    mandatory: true,
    domains: ['context'],
    apply(input) {
      if (input.projectBinding.kind === 'UNBOUND') {
        return blockedReceipt(
          module,
          input,
          'Context Manager v0.2 is project-scoped; UNBOUND public Context persistence is not wired yet',
        )
      }
      const projectId = input.projectBinding.projectId
      let snapshot
      try {
        snapshot = manager.getTask(projectId, input.taskId)
      } catch (error) {
        return blockedReceipt(
          module,
          input,
          `Context task must be bootstrapped before Turn Closure: ${error instanceof Error ? error.message : String(error)}`,
        )
      }

      const refs = unique(input.reflection.context.touchedRefs)
      const confirmed: ContextLedgerEntry[] = [
        ...input.reflection.context.decisions.map(text => ({ text: `Decision: ${text}`, refs })),
        ...input.reflection.context.confirmed.map(text => ({ text, refs })),
      ]
      const assumptions = input.reflection.context.assumptions.map(text => ({ text, refs }))
      const openIssues = input.reflection.context.openIssues.map(text => ({ text, refs }))
      const plan = unique(input.reflection.context.next)

      let changed = false
      let stateVersion = snapshot.stateVersion
      const taskLedgerChanged = !same(snapshot.session.taskLedger.confirmed, confirmed)
        || !same(snapshot.session.taskLedger.assumptions, assumptions)
        || !same(snapshot.session.taskLedger.openIssues, openIssues)
        || !same(snapshot.session.taskLedger.plan, plan)
      if (taskLedgerChanged) {
        const updated = manager.updateTaskLedger(projectId, input.taskId, {
          confirmed,
          assumptions,
          openIssues,
          plan,
        })
        snapshot = updated
        stateVersion = updated.stateVersion
        changed = true
      }

      const evidenceRefs = unique(input.reflection.evidence.candidates.flatMap(candidate => candidate.evidenceRefs))
      const progressChanged = snapshot.session.progressLedger.lastAction !== `Close governed Turn ${input.turnId}`
        || snapshot.session.progressLedger.lastResult !== input.reflection.context.progress
        || !same(snapshot.session.progressLedger.touchedRefs, refs)
        || !same(snapshot.session.progressLedger.next, plan)
        || !same(snapshot.session.progressLedger.evidenceRefs, evidenceRefs)
      if (progressChanged) {
        const updated = manager.updateProgressLedger(projectId, input.taskId, {
          lastAction: `Close governed Turn ${input.turnId}`,
          lastResult: input.reflection.context.progress,
          touchedRefs: refs,
          next: plan,
          evidenceRefs,
        })
        stateVersion = updated.stateVersion
        changed = true
      }

      return successfulReceipt(module, input, {
        status: changed ? 'APPLIED' : 'NO_CHANGE',
        writes: changed ? [`context://project/${projectId}/task/${input.taskId}/state/${stateVersion}`] : [],
        stateVersionAfter: stateVersion,
        evidenceRefs,
      })
    },
  }
  return module
}

export function createWorkingSetClosureModule(
  manager: Pick<ContextManagementService, 'getTask' | 'replaceWorkingSet'>,
): ClosureModule {
  const module: ClosureModule = {
    id: 'working-set-closure',
    version: MODULE_VERSION,
    mandatory: true,
    domains: ['working-set'],
    apply(input) {
      if (input.projectBinding.kind === 'UNBOUND') {
        return blockedReceipt(
          module,
          input,
          'Working Set currently persists through project Context Manager; UNBOUND Working Set store is not wired yet',
        )
      }
      const projectId = input.projectBinding.projectId
      let snapshot
      try {
        snapshot = manager.getTask(projectId, input.taskId)
      } catch (error) {
        return blockedReceipt(
          module,
          input,
          `Context task must exist before Working Set Closure: ${error instanceof Error ? error.message : String(error)}`,
        )
      }
      const desired = desiredWorkingSet(input, projectId)
      if (same(snapshot.session.workingSet, desired)) {
        return successfulReceipt(module, input, {
          status: 'NO_CHANGE',
          stateVersionAfter: snapshot.stateVersion,
        })
      }
      const updated = manager.replaceWorkingSet(projectId, input.taskId, desired)
      return successfulReceipt(module, input, {
        status: 'APPLIED',
        writes: [`context://project/${projectId}/task/${input.taskId}/working-set/${updated.stateVersion}`],
        stateVersionAfter: updated.stateVersion,
      })
    },
  }
  return module
}

const targetsFor = (
  candidate: ReflectionCandidate,
  input: ClosureModuleInput,
): readonly { scope: GovernanceChangeScope; projectId?: string }[] => {
  if (candidate.scopeDecision === 'PUBLIC') return [{ scope: 'PUBLIC' }]
  if (candidate.scopeDecision === 'PROJECT') {
    if (input.projectBinding.kind === 'UNBOUND') throw new Error('PROJECT change candidate requires a bound project')
    return [{ scope: 'PROJECT', projectId: input.projectBinding.projectId }]
  }
  if (input.projectBinding.kind === 'UNBOUND') throw new Error('BOTH change candidate requires a bound project')
  return [
    { scope: 'PROJECT', projectId: input.projectBinding.projectId },
    { scope: 'PUBLIC' },
  ]
}

const createChangeClosureModule = (
  domain: GovernanceChangeDomain,
  moduleId: 'architecture-closure' | 'rules-closure',
  reflectionDomain: 'architecture' | 'rules',
  store: GovernanceChangeCandidateStore,
): ClosureModule => {
  const module: ClosureModule = {
    id: moduleId,
    version: MODULE_VERSION,
    mandatory: true,
    domains: [reflectionDomain],
    apply(input) {
      const candidates = input.reflection[reflectionDomain].candidates
      if (candidates.length === 0) return successfulReceipt(module, input, { status: 'NO_CHANGE' })
      if (input.projectBinding.kind === 'UNBOUND'
          && candidates.some(candidate => candidate.scopeDecision !== 'PUBLIC')) {
        return blockedReceipt(module, input, `${reflectionDomain} PROJECT/BOTH candidate requires a bound project`)
      }

      const writes: string[] = []
      const candidateRefs: string[] = []
      const evidenceRefs: string[] = []
      for (const candidate of candidates) {
        let targets: readonly { scope: GovernanceChangeScope; projectId?: string }[]
        try {
          targets = targetsFor(candidate, input)
        } catch (error) {
          return blockedReceipt(module, input, error instanceof Error ? error.message : String(error))
        }
        for (const target of targets) {
          const candidateInput = {
            domain,
            targetScope: target.scope,
            ...(target.projectId ? { projectId: target.projectId } : {}),
            title: candidate.title,
            proposal: candidate.factOrProposal,
            rationale: candidate.rationale,
            provenanceRefs: unique([input.journalRef, ...candidate.provenanceRefs]),
            evidenceRefs: unique(candidate.evidenceRefs),
            relatedRefs: unique(candidate.relatedRefs),
            confidence: candidate.confidence,
          } as const
          const existing = store.get(candidateInput)
          const persisted = store.put(candidateInput)
          candidateRefs.push(persisted.candidateRef)
          evidenceRefs.push(...persisted.evidenceRefs)
          if (!existing) writes.push(persisted.candidateRef)
        }
      }

      return successfulReceipt(module, input, {
        status: writes.length > 0 ? 'APPLIED' : 'NO_CHANGE',
        writes: unique(writes),
        candidateRefs: unique(candidateRefs),
        evidenceRefs: unique(evidenceRefs),
      })
    },
  }
  return module
}

export const createArchitectureClosureModule = (store: GovernanceChangeCandidateStore): ClosureModule =>
  createChangeClosureModule('architecture', 'architecture-closure', 'architecture', store)

export const createRulesClosureModule = (store: GovernanceChangeCandidateStore): ClosureModule =>
  createChangeClosureModule('rules', 'rules-closure', 'rules', store)

const fingerprint = (candidate: ReflectionCandidate, input: ClosureModuleInput): string =>
  createHash('sha256').update(JSON.stringify({
    journalRef: input.journalRef,
    title: candidate.title,
    fact: candidate.factOrProposal,
    rationale: candidate.rationale,
    relatedRefs: unique(candidate.relatedRefs),
  })).digest('hex')

export function createEvidenceStateClosureModule(
  manager: Pick<EvidenceStateManagerService, 'listEvidence' | 'recordEvidence'>,
): ClosureModule {
  const module: ClosureModule = {
    id: 'evidence-state-closure',
    version: MODULE_VERSION,
    mandatory: true,
    domains: ['evidence'],
    apply(input) {
      const candidates = input.reflection.evidence.candidates
      if (candidates.length === 0) return successfulReceipt(module, input, { status: 'NO_CHANGE' })
      if (input.projectBinding.kind === 'UNBOUND') {
        return blockedReceipt(module, input, 'Evidence / State Manager is project-scoped; UNBOUND Evidence persistence is not wired yet')
      }
      if (candidates.some(candidate => candidate.scopeDecision !== 'PROJECT')) {
        return blockedReceipt(
          module,
          input,
          'PUBLIC/BOTH Evidence requires a global Evidence store; Step 5 only records project INFO Evidence',
        )
      }

      const projectId = input.projectBinding.projectId
      const existing = manager.listEvidence({ projectId, taskId: input.taskId, limit: 1000 })
      const writes: string[] = []
      const evidenceRefs: string[] = []
      for (const candidate of candidates) {
        const key = fingerprint(candidate, input)
        const prior = existing.find(item => item.metadata?.governanceClosureFingerprint === key)
        if (prior) {
          evidenceRefs.push(`evidence://project/${projectId}/${prior.evidenceId}`)
          continue
        }
        const record = manager.recordEvidence({
          projectId,
          taskId: input.taskId,
          kind: 'agent.turn.reflection',
          result: 'INFO',
          summary: candidate.factOrProposal.trim(),
          source: input.journalRef,
          artifactRefs: unique([...candidate.provenanceRefs, ...candidate.relatedRefs]),
          metadata: {
            governanceClosureFingerprint: key,
            title: candidate.title,
            rationale: candidate.rationale,
            confidence: candidate.confidence,
            supportingEvidenceRefs: unique(candidate.evidenceRefs),
          },
        })
        const ref = `evidence://project/${projectId}/${record.evidenceId}`
        evidenceRefs.push(ref)
        writes.push(ref)
      }

      return successfulReceipt(module, input, {
        status: writes.length > 0 ? 'APPLIED' : 'NO_CHANGE',
        writes: unique(writes),
        evidenceRefs: unique(evidenceRefs),
      })
    },
  }
  return module
}

const GATE_ID_RE = /\bG\d{3}(?:\.\d{3})*\b/gi

const gateIdsFrom = (values: readonly string[]): string[] =>
  unique(values.flatMap(value => value.match(GATE_ID_RE) ?? []).map(value => value.toUpperCase()))

const asObligationState = (value: unknown): {
  readonly openObligations: readonly string[]
  readonly idempotencyKey?: string
} => {
  if (!value || typeof value !== 'object') return { openObligations: [] }
  const item = value as { openObligations?: unknown; idempotencyKey?: unknown }
  return {
    openObligations: Array.isArray(item.openObligations)
      ? item.openObligations.filter((entry): entry is string => typeof entry === 'string')
      : [],
    ...(typeof item.idempotencyKey === 'string' ? { idempotencyKey: item.idempotencyKey } : {}),
  }
}

export function createObligationGateReconcileModule(
  stateManager: Pick<EvidenceStateManagerService, 'readState' | 'updateState'>,
  gateManager: Pick<GateManagerService, 'getExecutionPlan' | 'checkGateEvidence'>,
): ClosureModule {
  const module: ClosureModule = {
    id: 'obligation-gate-reconcile',
    version: MODULE_VERSION,
    mandatory: true,
    domains: ['obligations'],
    apply(input) {
      const { opened, resolved, unchanged } = input.reflection.obligations
      if (input.projectBinding.kind === 'UNBOUND') {
        if (opened.length === 0 && resolved.length === 0 && unchanged.length === 0) {
          return successfulReceipt(module, input, { status: 'NO_CHANGE' })
        }
        return blockedReceipt(
          module,
          input,
          'Obligation / Gate state is project-scoped; UNBOUND obligation persistence is not wired yet',
        )
      }

      const projectId = input.projectBinding.projectId
      const scope = `task:${input.taskId}`
      const key = 'governance-obligations'
      const current = stateManager.readState(projectId, scope, key)
      const prior = asObligationState(current?.value)
      if (prior.idempotencyKey === input.idempotencyKey) {
        return successfulReceipt(module, input, {
          status: 'NO_CHANGE',
          stateVersionAfter: current?.version,
          evidenceRefs: current?.evidenceRefs ?? [],
        })
      }

      const openSet = new Set(unique(prior.openObligations))
      for (const value of unique(resolved)) openSet.delete(value)
      for (const value of unique(opened)) openSet.add(value)
      for (const value of unique(unchanged)) openSet.add(value)
      const openObligations = [...openSet]

      const resolvedGateIds = gateIdsFrom(resolved)
      const gateEvidenceRefs: string[] = []
      for (const gateId of resolvedGateIds) {
        const plan = gateManager.getExecutionPlan(projectId, gateId)
        if (!plan) continue
        const status = gateManager.checkGateEvidence(projectId, input.taskId, gateId)
        gateEvidenceRefs.push(...status.evidenceRefs.map(id => `evidence://project/${projectId}/${id}`))
        if (status.blocksCompletion) {
          return blockedReceipt(
            module,
            input,
            `Reflection cannot resolve MUST Gate ${gateId} without PASS Evidence`,
          )
        }
      }

      const openGateIds = gateIdsFrom(openObligations)
      const blockingGateIds: string[] = []
      for (const gateId of openGateIds) {
        const plan = gateManager.getExecutionPlan(projectId, gateId)
        if (!plan) continue
        const status = gateManager.checkGateEvidence(projectId, input.taskId, gateId)
        gateEvidenceRefs.push(...status.evidenceRefs.map(id => `evidence://project/${projectId}/${id}`))
        if (status.blocksCompletion) blockingGateIds.push(gateId)
      }

      const value = {
        openObligations,
        openedInTurn: unique(opened),
        resolvedInTurn: unique(resolved),
        unchangedInTurn: unique(unchanged),
        gateIds: unique([...openGateIds, ...resolvedGateIds]),
        blockingGateIds: unique(blockingGateIds),
        reconciledAtTurn: input.turnId,
        idempotencyKey: input.idempotencyKey,
      }
      if (!current && openObligations.length === 0 && resolved.length === 0) {
        return successfulReceipt(module, input, {
          status: 'NO_CHANGE',
          evidenceRefs: unique(gateEvidenceRefs),
        })
      }
      const updated = stateManager.updateState({
        projectId,
        scope,
        key,
        value,
        reason: `Reconcile governed Turn ${input.turnId} obligations and Gate evidence`,
        evidenceRefs: unique(gateEvidenceRefs),
        expectedVersion: current?.version ?? 0,
      })
      return successfulReceipt(module, input, {
        status: 'APPLIED',
        writes: [`state://project/${projectId}/${scope}/${key}/v${updated.version}`],
        stateVersionAfter: updated.version,
        evidenceRefs: unique(gateEvidenceRefs),
      })
    },
  }
  return module
}
