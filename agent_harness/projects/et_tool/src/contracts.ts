export type EtToolProjectResourceKind = 'architecture' | 'rules' | 'knowledge' | 'gates'

export interface EtToolProjectResourceValidation {
  readonly valid: boolean
  readonly checked: readonly string[]
  readonly missing: readonly string[]
}
