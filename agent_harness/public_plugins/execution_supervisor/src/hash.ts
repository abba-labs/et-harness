import { createHash } from 'node:crypto'

const unsupported = (value: unknown): never => {
  const tag = Object.prototype.toString.call(value)
  throw new TypeError(`Value is not canonical JSON: ${tag}`)
}

const canonicalize = (value: unknown, active: Set<object>): string => {
  if (value === null) return 'null'
  if (typeof value === 'string') return JSON.stringify(value)
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return unsupported(value)
    return Object.is(value, -0) ? '0' : JSON.stringify(value)
  }
  if (typeof value !== 'object') return unsupported(value)
  if (active.has(value)) throw new TypeError('Value is not canonical JSON: cycle')
  active.add(value)
  try {
    if (Array.isArray(value)) {
      return `[${value.map(item => canonicalize(item, active)).join(',')}]`
    }
    const prototype = Object.getPrototypeOf(value)
    if (prototype !== Object.prototype && prototype !== null) {
      return unsupported(value)
    }
    const record = value as Record<string, unknown>
    const keys = Object.keys(record).sort()
    return `{${keys.map(key => {
      const item = record[key]
      if (item === undefined) return unsupported(item)
      return `${JSON.stringify(key)}:${canonicalize(item, active)}`
    }).join(',')}}`
  } finally {
    active.delete(value)
  }
}

export const canonicalJson = (value: unknown): string =>
  canonicalize(value, new Set<object>())

export const sha256Hex = (value: string | Uint8Array): string =>
  createHash('sha256').update(value).digest('hex')

export const hashCanonicalJson = (value: unknown): string =>
  sha256Hex(canonicalJson(value))

export const canonicalJsonBytes = (value: unknown): number =>
  Buffer.byteLength(canonicalJson(value), 'utf8')
