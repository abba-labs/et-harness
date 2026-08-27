import type {
  FrameworkMetricComponent,
  FrameworkMetricEvent,
} from '@agent-harness/governance-core'

export interface FrameworkEfficiencyQuery {
  readonly projectId?: string
  readonly taskId?: string
  readonly sessionId?: string
}

export interface FrameworkEfficiencyComponentSummary {
  readonly component: FrameworkMetricComponent
  readonly eventCount: number
  readonly observedDurationMs: number
  readonly okCount: number
  readonly missCount: number
  readonly passCount: number
  readonly failCount: number
  readonly errorCount: number
  readonly operationCounts: Readonly<Record<string, number>>
  readonly values: Readonly<Record<string, number>>
}

export interface FrameworkEfficiencyReport {
  readonly standard: 'framework-efficiency-report-v0.1'
  readonly projectId?: string
  readonly taskId?: string
  readonly sessionId?: string
  readonly eventCount: number
  readonly firstAt?: string
  readonly lastAt?: string
  readonly wallSpanMs?: number
  readonly observedFrameworkDurationMs: number
  readonly components: readonly FrameworkEfficiencyComponentSummary[]
  readonly findings: readonly string[]
}

export interface FrameworkObserverRuntimeStats {
  readonly storageFile: string
  readonly buffered: number
  readonly received: number
  readonly dropped: number
  readonly writeErrors: number
}

export interface FrameworkMetricBatch {
  readonly events: readonly FrameworkMetricEvent[]
}
