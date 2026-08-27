import type { ContextManagementService, ContextReference } from '@agent-harness/context-builder'
import type { ExperienceMemoryManagerService } from '@agent-harness/experience-memory-manager'
import type { KnowledgeManagerService, KnowledgeProjectIndex } from '@agent-harness/knowledge-manager'
import type {
  ClosureModule,
  ClosureModuleInput,
  ClosureModuleReceipt,
  ReflectionCandidate,
} from '@agent-harness/agent-governance-kernel'

const MODULE_VERSION = '0.1.0'

const unique = (values: readonly string[]): string[] =>
  [...new Set(values.map(value => value.trim()).filter(Boolean))]

const normalizeFact = (value: string): string =>
  value.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g, '')

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

const contextWorkingSet = (input: ClosureModuleInput, projectId: string): ContextReference[] => {
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

export function createContextClosureModule(
  manager: Pick<ContextManagementService, 'getTask' | 'updateTaskLedger' | 'updateProgressLedger' | 'replaceWorkingSet'>,
): ClosureModule {
  const module: ClosureModule = {
    id: 'context-closure',
    version: MODULE_VERSION,
    mandatory: true,
    domains: ['context', 'working-set'],
    apply(input) {
      if (input.projectBinding.kind === 'UNBOUND') {
        return blockedReceipt(
          module,
          input,
          'Context Manager v0.2 is project-scoped; UNBOUND public Context persistence is not wired yet',
        )
      }
      const projectId = input.projectBinding.projectId
      try {
        manager.getTask(projectId, input.taskId)
      } catch (error) {
        return blockedReceipt(
          module,
          input,
          `Context task must be bootstrapped before Turn Closure: ${error instanceof Error ? error.message : String(error)}`,
        )
      }

      const refs = unique(input.reflection.context.touchedRefs)
      const confirmed = [
        ...input.reflection.context.decisions.map(text => ({ text: `Decision: ${text}`, refs })),
        ...input.reflection.context.confirmed.map(text => ({ text, refs })),
      ]
      manager.updateTaskLedger(projectId, input.taskId, {
        confirmed,
        assumptions: input.reflection.context.assumptions.map(text => ({ text, refs })),
        openIssues: input.reflection.context.openIssues.map(text => ({ text, refs })),
        plan: input.reflection.context.next,
      })
      manager.updateProgressLedger(projectId, input.taskId, {
        lastAction: `Close governed Turn ${input.turnId}`,
        lastResult: input.reflection.context.progress,
        touchedRefs: refs,
        next: input.reflection.context.next,
        evidenceRefs: unique(input.reflection.evidence.candidates.flatMap(candidate => candidate.evidenceRefs)),
      })
      const final = manager.replaceWorkingSet(projectId, input.taskId, contextWorkingSet(input, projectId))
      return successfulReceipt(module, input, {
        status: 'APPLIED',
        writes: [`context://project/${projectId}/task/${input.taskId}/state/${final.stateVersion}`],
        stateVersionAfter: final.stateVersion,
      })
    },
  }
  return module
}

const projectCategoryRef = (candidate: ReflectionCandidate): string | undefined =>
  candidate.relatedRefs
    .find(ref => ref.toLowerCase().startsWith('knowledge-category://project/'))
    ?.slice('knowledge-category://project/'.length)
    .trim()

const publicCategoryRef = (candidate: ReflectionCandidate): string | undefined =>
  candidate.relatedRefs
    .find(ref => ref.toLowerCase().startsWith('knowledge-category://public/'))
    ?.slice('knowledge-category://public/'.length)
    .trim()

const categoryActive = (index: KnowledgeProjectIndex, categoryId: string): boolean =>
  !!index.taxonomy?.categories[categoryId] && index.taxonomy.categories[categoryId]?.status === 'ACTIVE'

const singleLine = (value: string): boolean => !!value.trim() && !/[\r\n]/.test(value)

const contentRefs = (candidate: ReflectionCandidate, journalRef: string): string[] =>
  unique([
    journalRef,
    ...candidate.provenanceRefs,
    ...candidate.evidenceRefs,
    ...candidate.relatedRefs.filter(ref => !ref.toLowerCase().startsWith('knowledge-category://')),
  ]).filter(singleLine)

const findProjectDuplicate = (
  manager: Pick<KnowledgeManagerService, 'getIndex' | 'getNode'>,
  projectId: string,
  fact: string,
): string | undefined => {
  const normalized = normalizeFact(fact)
  for (const file of manager.getIndex(projectId).files) {
    for (const id of file.nodes) {
      const node = manager.getNode(projectId, id)?.node
      if (node?.isLeaf && node.status !== 'DEPRECATED' && node.fact && normalizeFact(node.fact) === normalized) return node.id
    }
  }
  return undefined
}

const findGlobalDuplicate = (
  manager: Pick<KnowledgeManagerService, 'getGlobalIndex' | 'getGlobalNode'>,
  fact: string,
): string | undefined => {
  const normalized = normalizeFact(fact)
  for (const file of manager.getGlobalIndex().files) {
    for (const id of file.nodes) {
      const node = manager.getGlobalNode(id)?.node
      if (node?.isLeaf && node.status !== 'DEPRECATED' && node.fact && normalizeFact(node.fact) === normalized) return node.id
    }
  }
  return undefined
}

export function createKnowledgeClosureModule(
  manager: Pick<KnowledgeManagerService,
    | 'isGlobalLibraryMounted'
    | 'getGlobalIndex'
    | 'getGlobalNode'
    | 'submitGlobalKnowledgeCandidate'
    | 'getIndex'
    | 'getNode'
    | 'submitKnowledgeCandidate'>,
): ClosureModule {
  const module: ClosureModule = {
    id: 'knowledge-closure',
    version: MODULE_VERSION,
    mandatory: true,
    domains: ['knowledge'],
    apply(input) {
      const candidates = input.reflection.knowledge.candidates
      if (candidates.length === 0) return successfulReceipt(module, input, { status: 'NO_CHANGE' })

      for (const candidate of candidates) {
        if (!singleLine(candidate.title) || !singleLine(candidate.factOrProposal)) {
          return blockedReceipt(module, input, `Knowledge Candidate must use single-line title/fact: ${candidate.title}`)
        }
        if ((candidate.scopeDecision === 'PROJECT' || candidate.scopeDecision === 'BOTH')) {
          if (input.projectBinding.kind === 'UNBOUND') {
            return blockedReceipt(module, input, 'PROJECT/BOTH Knowledge Candidate cannot close while Turn is UNBOUND')
          }
          const categoryId = projectCategoryRef(candidate)
          if (!categoryId || !categoryActive(manager.getIndex(input.projectBinding.projectId), categoryId)) {
            return blockedReceipt(
              module,
              input,
              `Knowledge Candidate requires ACTIVE knowledge-category://project/<categoryId>: ${candidate.title}`,
            )
          }
        }
        if (candidate.scopeDecision === 'PUBLIC' || candidate.scopeDecision === 'BOTH') {
          if (!manager.isGlobalLibraryMounted()) {
            return blockedReceipt(module, input, 'PUBLIC/BOTH Knowledge Candidate requires mounted Global Knowledge Library')
          }
          const categoryId = publicCategoryRef(candidate)
          if (!categoryId || !categoryActive(manager.getGlobalIndex(), categoryId)) {
            return blockedReceipt(
              module,
              input,
              `Knowledge Candidate requires ACTIVE knowledge-category://public/<categoryId>: ${candidate.title}`,
            )
          }
        }
      }

      const writes: string[] = []
      const candidateRefs: string[] = []
      const evidenceRefs: string[] = []
      for (const candidate of candidates) {
        const refs = contentRefs(candidate, input.journalRef)
        const provenance = candidate.provenanceRefs.find(singleLine) ?? input.journalRef
        evidenceRefs.push(...candidate.evidenceRefs)

        if (candidate.scopeDecision === 'PROJECT' || candidate.scopeDecision === 'BOTH') {
          const projectId = (input.projectBinding as { kind: 'BOUND'; projectId: string }).projectId
          const duplicate = findProjectDuplicate(manager, projectId, candidate.factOrProposal)
          if (duplicate) {
            candidateRefs.push(`knowledge://project/${projectId}/${duplicate}`)
          } else {
            const mutation = manager.submitKnowledgeCandidate(projectId, {
              categoryId: projectCategoryRef(candidate)!,
              title: candidate.title,
              fact: candidate.factOrProposal,
              provenance,
              scope: candidate.scopeDecision,
              tags: ['agent-reflection', 'turn-closure'],
              refs,
            })
            const uri = `knowledge://project/${projectId}/${mutation.knowledgeId}`
            candidateRefs.push(uri)
            writes.push(`file://${mutation.file}`)
          }
        }

        if (candidate.scopeDecision === 'PUBLIC' || candidate.scopeDecision === 'BOTH') {
          const duplicate = findGlobalDuplicate(manager, candidate.factOrProposal)
          if (duplicate) {
            candidateRefs.push(`knowledge://global/${duplicate}`)
          } else {
            const mutation = manager.submitGlobalKnowledgeCandidate({
              categoryId: publicCategoryRef(candidate)!,
              title: candidate.title,
              fact: candidate.factOrProposal,
              provenance,
              scope: candidate.scopeDecision,
              tags: ['agent-reflection', 'turn-closure'],
              refs,
            })
            candidateRefs.push(`knowledge://global/${mutation.knowledgeId}`)
            writes.push(`file://${mutation.file}`)
          }
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

const evidenceIdForProject = (reference: string, projectId: string): string | undefined => {
  const trimmed = reference.trim()
  if (/^EV-.+/.test(trimmed)) return trimmed
  const prefix = `evidence://project/${projectId}/`
  if (!trimmed.toLowerCase().startsWith(prefix.toLowerCase())) return undefined
  const id = trimmed.slice(prefix.length)
  return /^EV-.+/.test(id) ? id : undefined
}

export function createExperienceMemoryClosureModule(
  manager: Pick<ExperienceMemoryManagerService, 'listCandidates' | 'recordCandidate'>,
): ClosureModule {
  const module: ClosureModule = {
    id: 'experience-memory-closure',
    version: MODULE_VERSION,
    mandatory: true,
    domains: ['experience'],
    apply(input) {
      const candidates = input.reflection.experience.candidates
      if (candidates.length === 0) return successfulReceipt(module, input, { status: 'NO_CHANGE' })
      if (input.projectBinding.kind === 'UNBOUND') {
        return blockedReceipt(
          module,
          input,
          'Experience / Memory Manager v0.2 is project-scoped; UNBOUND Experience persistence is not wired yet',
        )
      }
      if (candidates.some(candidate => candidate.scopeDecision !== 'PROJECT')) {
        return blockedReceipt(
          module,
          input,
          'PUBLIC/BOTH Experience requires a global Experience store; Step 4 only wires project Experience Candidates',
        )
      }
      const projectId = input.projectBinding.projectId
      const evidenceByCandidate = new Map<ReflectionCandidate, string[]>()
      for (const candidate of candidates) {
        const evidenceIds = unique(candidate.evidenceRefs
          .map(ref => evidenceIdForProject(ref, projectId))
          .filter((id): id is string => !!id))
        if (evidenceIds.length === 0) {
          return blockedReceipt(module, input, `Experience Candidate requires project Evidence: ${candidate.title}`)
        }
        evidenceByCandidate.set(candidate, evidenceIds)
      }

      const existing = manager.listCandidates(projectId)
      const writes: string[] = []
      const candidateRefs: string[] = []
      const evidenceRefs: string[] = []
      for (const candidate of candidates) {
        const duplicate = existing.find(item =>
          item.status !== 'REJECTED' && normalizeFact(item.fact) === normalizeFact(candidate.factOrProposal),
        )
        if (duplicate) {
          candidateRefs.push(`experience://project/${projectId}/${duplicate.candidateId}`)
          evidenceRefs.push(...duplicate.evidenceRefs)
          continue
        }
        const evidenceIds = evidenceByCandidate.get(candidate)!
        const recorded = manager.recordCandidate({
          projectId,
          taskId: input.taskId,
          title: candidate.title,
          fact: candidate.factOrProposal,
          scope: 'PROJECT',
          evidenceRefs: evidenceIds,
          refs: unique([input.journalRef, ...candidate.provenanceRefs, ...candidate.relatedRefs]),
        })
        const uri = `experience://project/${projectId}/${recorded.candidateId}`
        candidateRefs.push(uri)
        writes.push(uri)
        evidenceRefs.push(...recorded.evidenceRefs)
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
