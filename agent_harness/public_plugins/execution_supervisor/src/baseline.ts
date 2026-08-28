import {
  MAX_EXECUTION_EVENT_PAYLOAD_BYTES,
  MAX_TASK_SUPERVISION_CONTRACT_BYTES,
  PERFORMANCE_BASELINE_REPORT_SCHEMA,
  type PerformanceBaselineReportV01,
  type PerformanceBaselineSampleV01,
} from './contracts.js'

const round = (value: number): number => Number(value.toFixed(3))

export const percentile = (
  values: readonly number[],
  fraction: number,
): number => {
  if (values.length === 0) throw new Error('Cannot calculate a percentile from an empty sample')
  if (!Number.isFinite(fraction) || fraction < 0 || fraction > 1) {
    throw new Error('Percentile fraction must be between zero and one')
  }
  const sorted = [...values].sort((left, right) => left - right)
  const position = (sorted.length - 1) * fraction
  const lower = Math.floor(position)
  const upper = Math.ceil(position)
  const lowerValue = sorted[lower]!
  const upperValue = sorted[upper]!
  if (lower === upper) return lowerValue
  return lowerValue + (upperValue - lowerValue) * (position - lower)
}

export const summarizeDurationsMicros = (input: {
  readonly scenario: string
  readonly warmupIterations: number
  readonly inputBytes: number
  readonly durationsMicros: readonly number[]
}): PerformanceBaselineSampleV01 => {
  if (!input.scenario.trim()) throw new Error('scenario cannot be empty')
  if (!Number.isSafeInteger(input.warmupIterations) || input.warmupIterations < 0) {
    throw new Error('warmupIterations must be a non-negative safe integer')
  }
  if (!Number.isSafeInteger(input.inputBytes) || input.inputBytes < 1) {
    throw new Error('inputBytes must be a positive safe integer')
  }
  if (input.durationsMicros.length === 0) {
    throw new Error('durationsMicros cannot be empty')
  }
  if (input.durationsMicros.some(value => !Number.isFinite(value) || value < 0)) {
    throw new Error('durationsMicros must contain finite non-negative numbers')
  }
  const total = input.durationsMicros.reduce((sum, value) => sum + value, 0)
  return {
    scenario: input.scenario,
    warmupIterations: input.warmupIterations,
    sampleIterations: input.durationsMicros.length,
    inputBytes: input.inputBytes,
    p50Micros: round(percentile(input.durationsMicros, 0.50)),
    p95Micros: round(percentile(input.durationsMicros, 0.95)),
    p99Micros: round(percentile(input.durationsMicros, 0.99)),
    meanMicros: round(total / input.durationsMicros.length),
    maxMicros: round(Math.max(...input.durationsMicros)),
  }
}

export const createPhase0PerformanceBaseline = (input: {
  readonly baselineId: string
  readonly capturedAt: string
  readonly sourceRevision: string
  readonly nodeVersion: string
  readonly platform: string
  readonly architecture: string
  readonly samples: readonly PerformanceBaselineSampleV01[]
  readonly notes?: readonly string[]
}): PerformanceBaselineReportV01 => ({
  schema: PERFORMANCE_BASELINE_REPORT_SCHEMA,
  baselineId: input.baselineId,
  capturedAt: input.capturedAt,
  sourceRevision: input.sourceRevision,
  environment: {
    nodeVersion: input.nodeVersion,
    platform: input.platform,
    architecture: input.architecture,
  },
  thresholdsFrozen: false,
  invariants: {
    noSemanticCallOnHotPath: true,
    noFullRerouteForOrdinaryRead: true,
    maxUnifiedReflectionsPerTurn: 1,
    maxEventPayloadBytes: MAX_EXECUTION_EVENT_PAYLOAD_BYTES,
    maxTaskContractBytes: MAX_TASK_SUPERVISION_CONTRACT_BYTES,
  },
  samples: input.samples,
  notes: input.notes ?? [],
})
