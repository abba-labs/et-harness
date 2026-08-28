import { createHash } from 'node:crypto'
import type {
  ExecutionEventV01,
  JsonValue,
  TaskSupervisionContractV01,
} from './contracts.js'

const canonicalize = (value: unknown): JsonValue => {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') {
    return value
  }
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new Error('Canonical JSON rejects non-finite numbers')
    return value
  }
  if (Array.isArray(value)) return value.map(item => canonicalize(item))
  if (typeof value === 'object') {
    const result: Record<string, JsonValue> = {}
    for (const key of Object.keys(value as Record<string, unknown>).sort()) {
      const candidate = (value as Record<string, unknown>)[key]
      if (candidate === undefined) continue
      result[key] = canonicalize(candidate)
    }
    return result
  }
  throw new Error(`Canonical JSON rejects ${typeof value}`)
}

export const canonicalJson = (value: unknown): string =>
  JSON.stringify(canonicalize(value))

export const sha256Canonical = (value: unknown): string =>
  createHash('sha256').update(canonicalJson(value)).digest('hex')

export const computeTaskSupervisionContractHash = (
  contract: TaskSupervisionContractV01,
): string => sha256Canonical(contract)

export const computeExecutionEventHash = (
  event: ExecutionEventV01,
): string => sha256Canonical({
  ...event,
  integrity: {
    ...event.integrity,
    eventHash: '',
  },
})
