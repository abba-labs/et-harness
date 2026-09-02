import { describe, expect, it } from 'vitest'
import {
  KNOWLEDGE_TRIGGER_CONTRACT,
  KNOWLEDGE_TRIGGER_CONTRACT_VERSION,
  evaluateKnowledgeGovernanceDecision,
} from '../src/knowledge-governance-decision.js'

const context = (knowledgeIds: readonly string[] = []) => ({
  route: {
    architectureIds: [],
    ruleIds: [],
    knowledgeIds: [...knowledgeIds],
    gateIds: [],
  },
  applicableGateIds: [],
}) as any

const observation = (overrides: Record<string, unknown> = {}) => ({
  observationId: 'OBS-1',
  observationRef: 'observation://OBS-1',
  kind: 'ASSISTANT_MESSAGE',
  text: 'Agent says the routed knowledge may be wrong.',
  refs: [],
  truncated: false,
  ...overrides,
}) as any

describe('Knowledge Trigger Contract v0.1', () => {
  it('freezes the public trust boundary', () => {
    expect(KNOWLEDGE_TRIGGER_CONTRACT_VERSION).toBe('0.1')
    expect(KNOWLEDGE_TRIGGER_CONTRACT.agentProse).toBe('SEMANTIC_CANDIDATE_ONLY')
    expect(KNOWLEDGE_TRIGGER_CONTRACT.trustedVerificationBasis).toEqual(['source://', 'evidence://'])
  })

  it('does not treat ordinary Agent prose as a trusted automatic CHECK signal', () => {
    const decision = evaluateKnowledgeGovernanceDecision({
      stage: 'OBSERVE',
      context: context(['K001']),
      observations: [observation()],
    })
    expect(decision.consultMode).toBe('OPTIONAL')
    expect(decision.captureMode).toBe('NONE')
    expect(decision.validationMode).toBe('NONE')
    expect(decision.deterministicSignals).not.toContain('DOCUMENT_SOURCE_OBSERVED')
    expect(decision.deterministicSignals).not.toContain('EVIDENCE_OBSERVED')
  })

  it('escalates registered source and evidence refs through deterministic CHECK paths', () => {
    const source = evaluateKnowledgeGovernanceDecision({
      stage: 'OBSERVE',
      context: context(),
      observations: [observation({ refs: ['source://project/p1/SRC001'] })],
    })
    expect(source.captureMode).toBe('CHECK')
    expect(source.validationMode).toBe('DOCUMENT')
    expect(source.deterministicSignals).toContain('DOCUMENT_SOURCE_OBSERVED')

    const evidence = evaluateKnowledgeGovernanceDecision({
      stage: 'OBSERVE',
      context: context(),
      observations: [observation({ refs: ['evidence://project/p1/EV-001'] })],
    })
    expect(evidence.captureMode).toBe('CHECK')
    expect(evidence.validationMode).toBe('EVIDENCE_CHECK')
    expect(evidence.deterministicSignals).toContain('EVIDENCE_OBSERVED')
  })

  it('uses tool failure as a CHECK trigger without inventing verification evidence', () => {
    const decision = evaluateKnowledgeGovernanceDecision({
      stage: 'OBSERVE',
      context: context(),
      observations: [observation({ kind: 'TOOL_RESULT', isError: true })],
    })
    expect(decision.captureMode).toBe('CHECK')
    expect(decision.validationMode).toBe('NONE')
    expect(decision.deterministicSignals).toContain('TOOL_ERROR_OBSERVED')
  })
})
