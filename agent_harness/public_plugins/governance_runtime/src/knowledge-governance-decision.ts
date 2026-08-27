import type { TurnReflectionResult } from '@agent-harness/agent-governance-kernel'
import type { AutoGovernanceContextEnvelope } from '@agent-harness/auto-governance-engine'
import type {
  GovernanceKnowledgeDecision,
  GovernanceTurnObservation,
} from './contracts.js'

const unique = (values: readonly string[]): string[] =>
  [...new Set(values.map(value => value.trim()).filter(Boolean))]

const rankConsult = { NONE: 0, OPTIONAL: 1, REQUIRED: 2 } as const
const rankCapture = { NONE: 0, CHECK: 1, REQUIRED: 2 } as const
const rankValidation = { NONE: 0, DOCUMENT: 1, EVIDENCE_CHECK: 2, REAL_TEST: 3 } as const

const maxByRank = <T extends string>(left: T, right: T, rank: Readonly<Record<T, number>>): T =>
  rank[right] > rank[left] ? right : left

const refsFromCandidate = (candidate: TurnReflectionResult['knowledge']['candidates'][number]): string[] =>
  unique([...candidate.provenanceRefs, ...candidate.evidenceRefs, ...candidate.relatedRefs])

export function evaluateKnowledgeGovernanceDecision(input: {
  readonly stage: GovernanceKnowledgeDecision['stage']
  readonly context: AutoGovernanceContextEnvelope
  readonly observations: readonly GovernanceTurnObservation[]
  readonly reflection?: TurnReflectionResult
}): GovernanceKnowledgeDecision {
  let consultMode: GovernanceKnowledgeDecision['consultMode'] = 'NONE'
  let captureMode: GovernanceKnowledgeDecision['captureMode'] = 'NONE'
  let validationMode: GovernanceKnowledgeDecision['validationMode'] = 'NONE'
  const deterministicSignals: string[] = []
  const semanticSignals: string[] = []
  const reasons: string[] = []

  if (input.context.route.knowledgeIds.length > 0) {
    consultMode = 'OPTIONAL'
    deterministicSignals.push('ROUTED_KNOWLEDGE_AVAILABLE')
    reasons.push('Knowledge Router found relevant tiered knowledge; Agent may use it according to TrustTier and UsePolicy.')
  }
  if (input.context.applicableGateIds.length > 0
      && (input.context.route.architectureIds.length > 0 || input.context.route.ruleIds.length > 0)
      && input.context.route.knowledgeIds.length > 0) {
    consultMode = 'REQUIRED'
    deterministicSignals.push('GOVERNED_CHANGE_WITH_KNOWLEDGE')
    reasons.push('Governed architecture/rule/gate work has relevant knowledge; consideration is required, acceptance is not.')
  }

  for (const observation of input.observations) {
    const refs = observation.refs
    if (refs.some(ref => ref.startsWith('source://'))) {
      captureMode = maxByRank(captureMode, 'CHECK', rankCapture)
      validationMode = maxByRank(validationMode, 'DOCUMENT', rankValidation)
      deterministicSignals.push('DOCUMENT_SOURCE_OBSERVED')
    }
    if (refs.some(ref => ref.startsWith('evidence://'))) {
      captureMode = maxByRank(captureMode, 'CHECK', rankCapture)
      validationMode = maxByRank(validationMode, 'EVIDENCE_CHECK', rankValidation)
      deterministicSignals.push('EVIDENCE_OBSERVED')
    }
    if (observation.kind === 'TOOL_RESULT' && observation.isError) {
      captureMode = maxByRank(captureMode, 'CHECK', rankCapture)
      deterministicSignals.push('TOOL_ERROR_OBSERVED')
    }
  }

  const knowledge = input.reflection?.knowledge
  if (knowledge) {
    if (knowledge.scopeDecision !== 'NONE' || knowledge.candidates.length > 0) {
      captureMode = maxByRank(captureMode, 'CHECK', rankCapture)
      semanticSignals.push('REFLECTION_RECOMMENDS_KNOWLEDGE_CAPTURE')
      reasons.push('Unified Reflection identified a possible durable knowledge contribution.')
    } else {
      semanticSignals.push('REFLECTION_RECOMMENDS_NO_KNOWLEDGE')
    }
    for (const candidate of knowledge.candidates) {
      const refs = refsFromCandidate(candidate)
      if (refs.some(ref => ref.startsWith('source://'))) {
        validationMode = maxByRank(validationMode, 'DOCUMENT', rankValidation)
        semanticSignals.push('REFLECTION_CITES_DOCUMENT_SOURCE')
      }
      if (refs.some(ref => ref.startsWith('evidence://'))) {
        validationMode = maxByRank(validationMode, 'EVIDENCE_CHECK', rankValidation)
        semanticSignals.push('REFLECTION_CITES_EVIDENCE')
      }
    }
  }

  return {
    stage: input.stage,
    consultMode,
    captureMode,
    validationMode,
    deterministicSignals: unique(deterministicSignals),
    semanticSignals: unique(semanticSignals),
    reasons: unique(reasons),
  }
}
