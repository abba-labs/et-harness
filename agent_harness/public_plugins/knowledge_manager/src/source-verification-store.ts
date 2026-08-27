import { randomUUID } from 'node:crypto'
import {
  appendFileSync,
  existsSync,
  readFileSync,
  readdirSync,
  renameSync,
  writeFileSync,
} from 'node:fs'
import { join } from 'node:path'
import { parse, stringify } from 'yaml'
import { parseKnowledgeFile } from './knowledge-parser.js'
import { knowledgeClaimFingerprint } from './validation-policy.js'
import type {
  KnowledgeLibraryScope,
  KnowledgeResolvedSource,
  KnowledgeSourceInput,
  KnowledgeSourceKind,
  KnowledgeSourceRecord,
  KnowledgeVerificationBasisKind,
  KnowledgeVerificationInput,
  KnowledgeVerificationRecord,
  KnowledgeVerificationValidationClass,
  KnowledgeVerificationSummary,
} from './contracts.js'

const SOURCE_ID_RE = /^SRC\d{6}$/
const SOURCE_URI_RE = /^source:\/\/(global|project\/[^/]+)\/(SRC\d{6})$/i
const EVIDENCE_URI_RE = /^evidence:\/\/project\/([^/]+)\/(EV-.+)$/
const KNOWLEDGE_URI_RE = /^knowledge:\/\/(?:global|project\/[^/]+)\/(K\d{3}(?:\.\d{3})*)$/i
const PROJECT_ID_RE = /^[a-z0-9][a-z0-9._-]{1,63}$/
const VALID_SOURCE_KINDS = new Set<KnowledgeSourceKind>(['DOCUMENT', 'SPEC', 'SVD', 'CODE', 'RTL', 'WEB', 'OTHER'])

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const line = (name: string, value: string): string => {
  const trimmed = value.trim()
  if (!trimmed || /[\r\n]/.test(trimmed)) throw new Error(`${name} 必须是非空单行文本`)
  return trimmed
}

const atomicWrite = (file: string, content: string): void => {
  const temp = `${file}.${process.pid}.${randomUUID()}.tmp`
  writeFileSync(temp, content, 'utf-8')
  renameSync(temp, file)
}

export function qualifySourceId(scope: KnowledgeLibraryScope, sourceId: string): string {
  const normalized = sourceId.toUpperCase()
  if (!SOURCE_ID_RE.test(normalized)) throw new Error(`非法 Source ID: ${sourceId}`)
  return scope.kind === 'global'
    ? `source://global/${normalized}`
    : `source://project/${scope.projectId}/${normalized}`
}

export function parseSourceReference(reference: string): {
  readonly scope: KnowledgeLibraryScope
  readonly sourceId: string
} {
  const match = SOURCE_URI_RE.exec(reference.trim())
  if (!match?.[1] || !match[2]) throw new Error(`无法解析 Source reference: ${reference}`)
  const sourceId = match[2].toUpperCase()
  if (match[1].toLowerCase() === 'global') return { scope: { kind: 'global' }, sourceId }
  const projectId = match[1].slice('project/'.length)
  if (!PROJECT_ID_RE.test(projectId)) throw new Error(`非法 project source URI: ${reference}`)
  return { scope: { kind: 'project', projectId }, sourceId }
}

export function qualifyEvidenceId(projectId: string, evidenceId: string): string {
  if (!PROJECT_ID_RE.test(projectId)) throw new Error(`非法 evidence projectId: ${projectId}`)
  if (!evidenceId.startsWith('EV-')) throw new Error(`非法 Evidence ID: ${evidenceId}`)
  return `evidence://project/${projectId}/${evidenceId}`
}

export function parseEvidenceReference(reference: string): {
  readonly projectId: string
  readonly evidenceId: string
} {
  const match = EVIDENCE_URI_RE.exec(reference.trim())
  if (!match?.[1] || !match[2] || !PROJECT_ID_RE.test(match[1])) {
    throw new Error(`无法解析 Evidence reference: ${reference}`)
  }
  return { projectId: match[1], evidenceId: match[2] }
}

interface PersistedSourceRegistry {
  readonly standard: 'knowledge-source-registry-v0.1'
  readonly sources: readonly KnowledgeSourceRecord[]
}

const emptyRegistry = (): PersistedSourceRegistry => ({
  standard: 'knowledge-source-registry-v0.1',
  sources: [],
})

export class KnowledgeSourceVerificationStore {
  constructor(
    private readonly root: string,
    private readonly scope: KnowledgeLibraryScope,
  ) {}

  listSources(): readonly KnowledgeSourceRecord[] {
    return this.readRegistry().sources
  }

  getSource(sourceId: string): KnowledgeSourceRecord | undefined {
    const normalized = sourceId.toUpperCase()
    if (!SOURCE_ID_RE.test(normalized)) throw new Error(`非法 Source ID: ${sourceId}`)
    return this.readRegistry().sources.find(source => source.sourceId === normalized)
  }

  resolveSource(reference: string): KnowledgeResolvedSource | undefined {
    const parsed = parseSourceReference(reference)
    if (JSON.stringify(parsed.scope) !== JSON.stringify(this.scope)) return undefined
    const source = this.getSource(parsed.sourceId)
    return source
      ? { libraryScope: this.scope, sourceUri: qualifySourceId(this.scope, source.sourceId), source }
      : undefined
  }

  registerSource(input: KnowledgeSourceInput): KnowledgeResolvedSource {
    const kind = input.kind.toUpperCase() as KnowledgeSourceKind
    if (!VALID_SOURCE_KINDS.has(kind)) throw new Error(`非法 Source kind: ${input.kind}`)
    const title = line('Source title', input.title)
    const location = line('Source location', input.location)
    const revision = input.revision?.trim() ? line('Source revision', input.revision) : undefined
    const contentHash = input.contentHash?.trim() ? line('Source contentHash', input.contentHash) : undefined
    const note = input.note?.trim() ? line('Source note', input.note) : undefined

    const registry = this.readRegistry()
    const duplicate = registry.sources.find(source =>
      source.location === location && (source.revision ?? '') === (revision ?? ''),
    )
    if (duplicate) throw new Error(`重复 Source: ${duplicate.sourceId}`)

    const used = new Set(registry.sources.map(source => Number.parseInt(source.sourceId.slice(3), 10)))
    let number = 1
    while (used.has(number) && number <= 999999) number += 1
    if (number > 999999) throw new Error('Source ID 空间已满')
    const sourceId = `SRC${String(number).padStart(6, '0')}`
    const source: KnowledgeSourceRecord = {
      sourceId,
      kind,
      title,
      location,
      status: 'ACTIVE',
      registeredAt: new Date().toISOString(),
      ...(revision ? { revision } : {}),
      ...(contentHash ? { contentHash } : {}),
      ...(note ? { note } : {}),
    }
    this.writeRegistry({
      standard: 'knowledge-source-registry-v0.1',
      sources: [...registry.sources, source],
    })
    return { libraryScope: this.scope, sourceUri: qualifySourceId(this.scope, sourceId), source }
  }

  appendVerification(
    input: KnowledgeVerificationInput,
    basisKind: KnowledgeVerificationBasisKind,
    knowledgeFingerprint?: string,
    validationClass: KnowledgeVerificationValidationClass = 'REFERENCE',
  ): KnowledgeVerificationRecord {
    const note = input.note?.trim() ? line('Verification note', input.note) : undefined
    const fingerprint = knowledgeFingerprint ?? this.currentKnowledgeFingerprint(input.knowledgeUri)
    const record: KnowledgeVerificationRecord = {
      knowledgeUri: line('knowledgeUri', input.knowledgeUri),
      basisRef: line('basisRef', input.basisRef),
      relation: input.relation,
      basisKind,
      validationClass,
      knowledgeFingerprint: line('knowledgeFingerprint', fingerprint),
      verificationId: `VR-${new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)}-${randomUUID()}`,
      recordedAt: new Date().toISOString(),
      ...(note ? { note } : {}),
    }
    const file = join(this.root, 'VERIFICATIONS.jsonl')
    appendFileSync(file, `${JSON.stringify(record)}\n`, 'utf-8')
    return record
  }

  listVerifications(knowledgeUri?: string): readonly KnowledgeVerificationRecord[] {
    const file = join(this.root, 'VERIFICATIONS.jsonl')
    if (!existsSync(file)) return []
    return readFileSync(file, 'utf-8')
      .split('\n')
      .filter(Boolean)
      .map((lineText, index): KnowledgeVerificationRecord => {
        const value: unknown = JSON.parse(lineText)
        if (!isRecord(value)
          || typeof value.verificationId !== 'string'
          || typeof value.knowledgeUri !== 'string'
          || typeof value.basisRef !== 'string'
          || (value.basisKind !== 'SOURCE' && value.basisKind !== 'EVIDENCE')
          || (value.relation !== 'SUPPORT' && value.relation !== 'CONTRADICT')
          || typeof value.recordedAt !== 'string') {
          throw new Error(`VERIFICATIONS.jsonl:${index + 1} 非法 Verification Record`)
        }
        return {
          ...(value as unknown as KnowledgeVerificationRecord),
          validationClass: value.validationClass === 'DOCUMENT' || value.validationClass === 'REAL_TEST'
            ? value.validationClass
            : 'REFERENCE',
          knowledgeFingerprint: typeof value.knowledgeFingerprint === 'string'
            ? value.knowledgeFingerprint
            : 'legacy:unbound',
        }
      })
      .filter(record => !knowledgeUri || record.knowledgeUri === knowledgeUri)
  }

  verificationSummary(knowledgeUri: string): KnowledgeVerificationSummary {
    const records = this.listVerifications(knowledgeUri)
    return {
      knowledgeUri,
      supportCount: records.filter(record => record.relation === 'SUPPORT').length,
      contradictCount: records.filter(record => record.relation === 'CONTRADICT').length,
      records,
    }
  }

  private currentKnowledgeFingerprint(knowledgeUri: string): string {
    const match = KNOWLEDGE_URI_RE.exec(knowledgeUri.trim())
    const knowledgeId = match?.[1]?.toUpperCase()
    if (!knowledgeId) throw new Error(`无法从 Knowledge URI 解析 K-ID: ${knowledgeUri}`)
    const fileId = knowledgeId.split('.')[0]
    const number = fileId?.slice(1)
    if (!fileId || !number) throw new Error(`非法 Knowledge ID: ${knowledgeId}`)
    const file = readdirSync(this.root)
      .filter(name => new RegExp(`^${number}_[a-z0-9][a-z0-9_-]*\\.md$`).test(name))
      .sort()[0]
    if (!file) throw new Error(`Knowledge File 不存在: ${fileId}`)
    const parsed = parseKnowledgeFile(fileId, file, readFileSync(join(this.root, file), 'utf-8'))
    const node = parsed.nodes.find(item => item.id === knowledgeId && item.isLeaf)
    if (!node) throw new Error(`Knowledge Leaf 不存在: ${knowledgeId}`)
    return knowledgeClaimFingerprint(node)
  }

  private readRegistry(): PersistedSourceRegistry {
    const file = join(this.root, 'SOURCES.yaml')
    if (!existsSync(file)) return emptyRegistry()
    const raw: unknown = parse(readFileSync(file, 'utf-8'))
    if (!isRecord(raw) || raw.standard !== 'knowledge-source-registry-v0.1' || !Array.isArray(raw.sources)) {
      throw new Error('SOURCES.yaml 必须符合 knowledge-source-registry-v0.1')
    }
    const sources = raw.sources.map((value, index) => {
      if (!isRecord(value)
        || typeof value.sourceId !== 'string'
        || !SOURCE_ID_RE.test(value.sourceId)
        || typeof value.kind !== 'string'
        || !VALID_SOURCE_KINDS.has(value.kind as KnowledgeSourceKind)
        || typeof value.title !== 'string'
        || typeof value.location !== 'string'
        || (value.status !== 'ACTIVE' && value.status !== 'DEPRECATED')
        || typeof value.registeredAt !== 'string') {
        throw new Error(`SOURCES.yaml sources[${index}] 非法`)
      }
      return value as unknown as KnowledgeSourceRecord
    })
    const ids = new Set<string>()
    for (const source of sources) {
      if (ids.has(source.sourceId)) throw new Error(`Source ID 重复: ${source.sourceId}`)
      ids.add(source.sourceId)
    }
    return { standard: 'knowledge-source-registry-v0.1', sources }
  }

  private writeRegistry(registry: PersistedSourceRegistry): void {
    atomicWrite(join(this.root, 'SOURCES.yaml'), stringify(registry))
  }
}
