import { createHash, randomUUID } from 'node:crypto'
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { dirname, join } from 'node:path'

export type GovernanceChangeDomain = 'architecture' | 'rules'
export type GovernanceChangeScope = 'PROJECT' | 'PUBLIC'

export interface GovernanceChangeCandidateInput {
  readonly domain: GovernanceChangeDomain
  readonly targetScope: GovernanceChangeScope
  readonly projectId?: string
  readonly title: string
  readonly proposal: string
  readonly rationale: string
  readonly provenanceRefs: readonly string[]
  readonly evidenceRefs: readonly string[]
  readonly relatedRefs: readonly string[]
  readonly confidence: number
}

export interface GovernanceChangeCandidateRecord extends GovernanceChangeCandidateInput {
  readonly candidateId: string
  readonly candidateRef: string
  readonly status: 'CANDIDATE'
  readonly createdAt: string
}

const storageRoot = (): string =>
  join(
    process.env.AGENT_HARNESS_STATE_ROOT ?? join(homedir(), '.agent-harness', 'runtime'),
    'agent-governance-change-candidates',
  )

const atomicWriteJson = (file: string, value: unknown): void => {
  mkdirSync(dirname(file), { recursive: true })
  const temp = `${file}.${process.pid}.${randomUUID()}.tmp`
  writeFileSync(temp, `${JSON.stringify(value, null, 2)}\n`, 'utf-8')
  renameSync(temp, file)
}

const unique = (values: readonly string[]): string[] =>
  [...new Set(values.map(value => value.trim()).filter(Boolean))].sort()

const stableFingerprint = (input: GovernanceChangeCandidateInput): string =>
  createHash('sha256').update(JSON.stringify({
    domain: input.domain,
    targetScope: input.targetScope,
    projectId: input.projectId,
    title: input.title.trim(),
    proposal: input.proposal.trim(),
  })).digest('hex')

const candidateId = (input: GovernanceChangeCandidateInput): string => {
  const prefix = input.domain === 'architecture' ? 'ARCHC' : 'RULEC'
  return `${prefix}-${stableFingerprint(input).slice(0, 24)}`
}

const candidateRef = (input: GovernanceChangeCandidateInput, id: string): string => {
  const scheme = input.domain === 'architecture' ? 'architecture-change' : 'rule-change'
  if (input.targetScope === 'PUBLIC') return `${scheme}://public/${id}`
  if (!input.projectId?.trim()) throw new Error(`${input.domain} PROJECT candidate requires projectId`)
  return `${scheme}://project/${input.projectId.trim()}/${id}`
}

export class GovernanceChangeCandidateStore {
  constructor(private readonly root = storageRoot()) {
    mkdirSync(root, { recursive: true })
  }

  put(input: GovernanceChangeCandidateInput): GovernanceChangeCandidateRecord {
    if (!input.title.trim()) throw new Error('change candidate title cannot be empty')
    if (!input.proposal.trim()) throw new Error('change candidate proposal cannot be empty')
    if (!input.rationale.trim()) throw new Error('change candidate rationale cannot be empty')
    if (!Number.isFinite(input.confidence) || input.confidence < 0 || input.confidence > 1) {
      throw new Error('change candidate confidence must be in [0, 1]')
    }
    if (input.targetScope === 'PROJECT' && !input.projectId?.trim()) {
      throw new Error(`${input.domain} PROJECT candidate requires projectId`)
    }

    const normalized: GovernanceChangeCandidateInput = {
      ...input,
      title: input.title.trim(),
      proposal: input.proposal.trim(),
      rationale: input.rationale.trim(),
      ...(input.projectId?.trim() ? { projectId: input.projectId.trim() } : {}),
      provenanceRefs: unique(input.provenanceRefs),
      evidenceRefs: unique(input.evidenceRefs),
      relatedRefs: unique(input.relatedRefs),
    }
    const id = candidateId(normalized)
    const ref = candidateRef(normalized, id)
    const file = this.file(normalized, id)
    if (existsSync(file)) {
      const existing = JSON.parse(readFileSync(file, 'utf-8')) as GovernanceChangeCandidateRecord
      if (existing.candidateId !== id || existing.candidateRef !== ref || existing.status !== 'CANDIDATE') {
        throw new Error(`invalid persisted change candidate: ${ref}`)
      }
      return existing
    }

    const record: GovernanceChangeCandidateRecord = {
      ...normalized,
      candidateId: id,
      candidateRef: ref,
      status: 'CANDIDATE',
      createdAt: new Date().toISOString(),
    }
    atomicWriteJson(file, record)
    return record
  }

  get(input: GovernanceChangeCandidateInput): GovernanceChangeCandidateRecord | undefined {
    const id = candidateId(input)
    const file = this.file(input, id)
    if (!existsSync(file)) return undefined
    return JSON.parse(readFileSync(file, 'utf-8')) as GovernanceChangeCandidateRecord
  }

  private file(input: GovernanceChangeCandidateInput, id: string): string {
    const scope = input.targetScope === 'PUBLIC'
      ? 'public'
      : join('project', input.projectId?.trim() || '__missing__')
    return join(this.root, input.domain, scope, `${id}.json`)
  }
}
