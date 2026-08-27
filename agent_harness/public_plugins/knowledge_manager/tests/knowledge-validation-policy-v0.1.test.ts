import { describe, expect, it } from 'vitest'
import KnowledgeValidationPolicyService from '../src/validation-service.js'
import {
  evaluateKnowledgeValidationPolicy,
  knowledgeClaimFingerprint,
} from '../src/validation-policy.js'
import type {
  KnowledgeVerificationRecord,
  KnowledgeVerificationValidationClass,
} from '../src/contracts.js'

const record = (
  basisRef: string,
  relation: 'SUPPORT' | 'CONTRADICT',
  fingerprint: string,
  validationClass: KnowledgeVerificationValidationClass = 'REFERENCE',
): KnowledgeVerificationRecord => ({
  verificationId: `VR-${basisRef}-${relation}`,
  knowledgeUri: 'knowledge://global/K001.001',
  basisRef,
  basisKind: basisRef.startsWith('evidence://') ? 'EVIDENCE' : 'SOURCE',
  validationClass,
  relation,
  knowledgeFingerprint: fingerprint,
  recordedAt: '2026-08-21T00:00:00.000Z',
})

describe('Knowledge Validation Policy v0.1', () => {
  const fingerprint = knowledgeClaimFingerprint({ fact: 'DMA cannot access DTCM.', scope: 'chip-x' })

  it('Service 显式声明 Knowledge Manager 运行时依赖', () => {
    expect(KnowledgeValidationPolicyService.inject).toContain('knowledgeManager')
  })

  it('Project 1 个文档级 SUPPORT 可晋级 VALIDATED', () => {
    const empty = evaluateKnowledgeValidationPolicy({
      knowledgeUri: 'knowledge://project/demo/K001.001',
      libraryScope: { kind: 'project', projectId: 'demo' },
      currentStatus: 'CANDIDATE',
      knowledgeFingerprint: fingerprint,
      records: [],
    })
    expect(empty.decision).toBe('INSUFFICIENT')

    const ready = evaluateKnowledgeValidationPolicy({
      ...empty,
      records: [record('source://global/SRC000001', 'SUPPORT', fingerprint, 'DOCUMENT')],
    })
    expect(ready.decision).toBe('READY')
    expect(ready.targetStatus).toBe('VALIDATED')
    expect(ready.requiredSupportCount).toBe(1)
    expect(ready.documentSupportCount).toBe(1)
  })

  it('Global 需要 2 个不同文档级 SUPPORT 才可晋级 VALIDATED', () => {
    const one = evaluateKnowledgeValidationPolicy({
      knowledgeUri: 'knowledge://global/K001.001',
      libraryScope: { kind: 'global' },
      currentStatus: 'CANDIDATE',
      knowledgeFingerprint: fingerprint,
      records: [record('source://global/SRC000001', 'SUPPORT', fingerprint, 'DOCUMENT')],
    })
    expect(one.decision).toBe('INSUFFICIENT')

    const referenceEvidenceDoesNotCount = evaluateKnowledgeValidationPolicy({
      ...one,
      records: [
        record('source://global/SRC000001', 'SUPPORT', fingerprint, 'DOCUMENT'),
        record('evidence://project/demo/EV-1', 'SUPPORT', fingerprint, 'REFERENCE'),
      ],
    })
    expect(referenceEvidenceDoesNotCount.decision).toBe('INSUFFICIENT')

    const twoDocuments = evaluateKnowledgeValidationPolicy({
      ...one,
      records: [
        record('source://global/SRC000001', 'SUPPORT', fingerprint, 'DOCUMENT'),
        record('source://global/SRC000002', 'SUPPORT', fingerprint, 'DOCUMENT'),
      ],
    })
    expect(twoDocuments.decision).toBe('READY')
    expect(twoDocuments.targetStatus).toBe('VALIDATED')
    expect(twoDocuments.requiredSupportCount).toBe(2)
  })

  it('Project 1 个真实测试 SUPPORT 可直接晋级 FULL_VALIDATED', () => {
    const evaluation = evaluateKnowledgeValidationPolicy({
      knowledgeUri: 'knowledge://project/demo/K001.001',
      libraryScope: { kind: 'project', projectId: 'demo' },
      currentStatus: 'CANDIDATE',
      knowledgeFingerprint: fingerprint,
      records: [record('evidence://project/demo/EV-REAL-1', 'SUPPORT', fingerprint, 'REAL_TEST')],
    })
    expect(evaluation.decision).toBe('READY')
    expect(evaluation.targetStatus).toBe('FULL_VALIDATED')
    expect(evaluation.realTestSupportCount).toBe(1)
  })

  it('Global 单项目 REAL_TEST 不能晋级 FULL_VALIDATED', () => {
    const evaluation = evaluateKnowledgeValidationPolicy({
      knowledgeUri: 'knowledge://global/K001.001',
      libraryScope: { kind: 'global' },
      currentStatus: 'CANDIDATE',
      knowledgeFingerprint: fingerprint,
      records: [record('evidence://project/demo/EV-REAL-GLOBAL-1', 'SUPPORT', fingerprint, 'REAL_TEST')],
    })
    expect(evaluation.decision).toBe('INSUFFICIENT')
    expect(evaluation.targetStatus).toBeUndefined()
    expect(evaluation.realTestSupportCount).toBe(1)
  })

  it('Global VALIDATED 也不能因单项目 REAL_TEST 晋级 FULL_VALIDATED', () => {
    const evaluation = evaluateKnowledgeValidationPolicy({
      knowledgeUri: 'knowledge://global/K001.001',
      libraryScope: { kind: 'global' },
      currentStatus: 'VALIDATED',
      knowledgeFingerprint: fingerprint,
      records: [record('evidence://project/demo/EV-REAL-GLOBAL-2', 'SUPPORT', fingerprint, 'REAL_TEST')],
    })
    expect(evaluation.decision).toBe('INSUFFICIENT')
    expect(evaluation.targetStatus).toBeUndefined()
  })

  it('VALIDATED 获得真实测试 SUPPORT 后可继续晋级 FULL_VALIDATED', () => {
    const evaluation = evaluateKnowledgeValidationPolicy({
      knowledgeUri: 'knowledge://project/demo/K001.001',
      libraryScope: { kind: 'project', projectId: 'demo' },
      currentStatus: 'VALIDATED',
      knowledgeFingerprint: fingerprint,
      records: [record('evidence://project/demo/EV-REAL-2', 'SUPPORT', fingerprint, 'REAL_TEST')],
    })
    expect(evaluation.decision).toBe('READY')
    expect(evaluation.targetStatus).toBe('FULL_VALIDATED')
  })

  it('重复同一文档 basisRef 不重复计数', () => {
    const evaluation = evaluateKnowledgeValidationPolicy({
      knowledgeUri: 'knowledge://global/K001.001',
      libraryScope: { kind: 'global' },
      currentStatus: 'CANDIDATE',
      knowledgeFingerprint: fingerprint,
      records: [
        record('source://global/SRC000001', 'SUPPORT', fingerprint, 'DOCUMENT'),
        { ...record('source://global/SRC000001', 'SUPPORT', fingerprint, 'DOCUMENT'), verificationId: 'VR-2' },
      ],
    })
    expect(evaluation.distinctSupportCount).toBe(1)
    expect(evaluation.documentSupportCount).toBe(1)
    expect(evaluation.decision).toBe('INSUFFICIENT')
  })

  it('任何当前 Claim CONTRADICT 都阻塞，即使同时存在文档或实测 SUPPORT', () => {
    const evaluation = evaluateKnowledgeValidationPolicy({
      knowledgeUri: 'knowledge://global/K001.001',
      libraryScope: { kind: 'global' },
      currentStatus: 'CANDIDATE',
      knowledgeFingerprint: fingerprint,
      records: [
        record('source://global/SRC000001', 'SUPPORT', fingerprint, 'DOCUMENT'),
        record('evidence://project/demo/EV-1', 'SUPPORT', fingerprint, 'REAL_TEST'),
        record('evidence://project/demo/EV-2', 'CONTRADICT', fingerprint, 'REAL_TEST'),
      ],
    })
    expect(evaluation.decision).toBe('BLOCKED')
    expect(evaluation.contradictCount).toBe(1)
  })

  it('Fact / Scope 改动后旧 Claim Verification 不计入', () => {
    const newFingerprint = knowledgeClaimFingerprint({ fact: 'DMA access depends on bus mapping.', scope: 'chip-x' })
    const evaluation = evaluateKnowledgeValidationPolicy({
      knowledgeUri: 'knowledge://project/demo/K001.001',
      libraryScope: { kind: 'project', projectId: 'demo' },
      currentStatus: 'CANDIDATE',
      knowledgeFingerprint: newFingerprint,
      records: [record('source://global/SRC000001', 'SUPPORT', fingerprint, 'DOCUMENT')],
    })
    expect(evaluation.decision).toBe('INSUFFICIENT')
    expect(evaluation.records).toHaveLength(0)
    expect(evaluation.reasons.some(reason => reason.includes('旧 Claim'))).toBe(true)
  })
})