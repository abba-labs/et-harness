import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import {
  KnowledgeSourceVerificationStore,
  parseEvidenceReference,
  parseSourceReference,
  qualifyEvidenceId,
  qualifySourceId,
} from '../src/source-verification-store.js'

describe('Knowledge Source Registry v0.1', () => {
  it('Global / Project Source 使用相同本地 ID 但完整 URI 不冲突', () => {
    const globalRoot = mkdtempSync(join(tmpdir(), 'global-source-'))
    const projectRoot = mkdtempSync(join(tmpdir(), 'project-source-'))
    const globalStore = new KnowledgeSourceVerificationStore(globalRoot, { kind: 'global' })
    const projectStore = new KnowledgeSourceVerificationStore(projectRoot, {
      kind: 'project',
      projectId: 'example',
    })

    const global = globalStore.registerSource({
      kind: 'SPEC',
      title: 'ROM Spec',
      location: 'docs/rom-spec.pdf',
      revision: '1.0',
    })
    const project = projectStore.registerSource({
      kind: 'CODE',
      title: 'Project Backend',
      location: 'source/backend.ts',
    })

    expect(global.source.sourceId).toBe('SRC000001')
    expect(project.source.sourceId).toBe('SRC000001')
    expect(global.sourceUri).toBe('source://global/SRC000001')
    expect(project.sourceUri).toBe('source://project/example/SRC000001')
  })

  it('相同 location + revision 拒绝重复 Source', () => {
    const root = mkdtempSync(join(tmpdir(), 'source-duplicate-'))
    const store = new KnowledgeSourceVerificationStore(root, { kind: 'global' })
    store.registerSource({ kind: 'SPEC', title: 'Spec A', location: 'spec.pdf', revision: 'v1' })
    expect(() => store.registerSource({
      kind: 'SPEC',
      title: 'Spec A Copy',
      location: 'spec.pdf',
      revision: 'v1',
    })).toThrow('重复 Source: SRC000001')
  })
})

describe('Knowledge Verification v0.1 store', () => {
  it('Verification append-only 累计 SUPPORT / CONTRADICT', () => {
    const root = mkdtempSync(join(tmpdir(), 'verification-'))
    const store = new KnowledgeSourceVerificationStore(root, { kind: 'global' })
    const fingerprint = 'sha256:test-claim'
    store.appendVerification({
      knowledgeUri: 'knowledge://global/K001.001',
      basisRef: 'source://global/SRC000001',
      relation: 'SUPPORT',
    }, 'SOURCE', fingerprint)
    store.appendVerification({
      knowledgeUri: 'knowledge://global/K001.001',
      basisRef: 'evidence://project/example/EV-001',
      relation: 'CONTRADICT',
    }, 'EVIDENCE', fingerprint)

    const summary = store.verificationSummary('knowledge://global/K001.001')
    expect(summary.supportCount).toBe(1)
    expect(summary.contradictCount).toBe(1)
    expect(summary.records).toHaveLength(2)
    expect(summary.records.every(record => record.knowledgeFingerprint === fingerprint)).toBe(true)
  })

  it('Source / Evidence URI 可稳定解析', () => {
    expect(parseSourceReference(qualifySourceId({ kind: 'global' }, 'SRC000001'))).toEqual({
      scope: { kind: 'global' },
      sourceId: 'SRC000001',
    })
    const evidenceUri = qualifyEvidenceId('example', 'EV-20260821120000-test')
    expect(parseEvidenceReference(evidenceUri)).toEqual({
      projectId: 'example',
      evidenceId: 'EV-20260821120000-test',
    })
  })
})
