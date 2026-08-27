export type EvidenceResult = 'PASS' | 'FAIL' | 'INFO' | 'SKIP'

export interface EvidenceRecordInput {
  readonly projectId: string
  readonly taskId: string
  readonly kind: string
  readonly result: EvidenceResult
  readonly summary: string
  readonly source: string
  readonly gateId?: string
  readonly artifactRefs?: readonly string[]
  readonly metadata?: Readonly<Record<string, unknown>>
}

export interface EvidenceRecord extends EvidenceRecordInput {
  readonly evidenceId: string
  readonly recordedAt: string
}

export interface EvidenceQuery {
  readonly projectId: string
  readonly taskId?: string
  readonly result?: EvidenceResult
  readonly gateId?: string
  readonly limit?: number
}

export interface StateUpdateInput {
  readonly projectId: string
  readonly scope: string
  readonly key: string
  readonly value: unknown
  readonly reason: string
  readonly evidenceRefs?: readonly string[]
  readonly expectedVersion?: number
}

export interface StateRecord {
  readonly projectId: string
  readonly scope: string
  readonly key: string
  readonly value: unknown
  readonly version: number
  readonly reason: string
  readonly evidenceRefs: readonly string[]
  readonly updatedAt: string
}

export interface ProjectStateSnapshot {
  readonly projectId: string
  readonly records: readonly StateRecord[]
}
