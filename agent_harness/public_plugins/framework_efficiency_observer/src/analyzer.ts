import type {
  FrameworkMetricComponent,
  FrameworkMetricEvent,
} from '@agent-harness/governance-core'
import type {
  FrameworkEfficiencyComponentSummary,
  FrameworkEfficiencyQuery,
  FrameworkEfficiencyReport,
} from './contracts.js'

interface MutableComponentSummary {
  component: FrameworkMetricComponent
  eventCount: number
  observedDurationMs: number
  okCount: number
  missCount: number
  passCount: number
  failCount: number
  errorCount: number
  operationCounts: Record<string, number>
  values: Record<string, number>
}

const emptyComponent = (component: FrameworkMetricComponent): MutableComponentSummary => ({
  component,
  eventCount: 0,
  observedDurationMs: 0,
  okCount: 0,
  missCount: 0,
  passCount: 0,
  failCount: 0,
  errorCount: 0,
  operationCounts: {},
  values: {},
})

const parseTime = (value: string): number | undefined => {
  const parsed = Date.parse(value)
  return Number.isFinite(parsed) ? parsed : undefined
}

export function analyzeFrameworkMetrics(
  events: readonly FrameworkMetricEvent[],
  query: FrameworkEfficiencyQuery = {},
): FrameworkEfficiencyReport {
  const filtered = events.filter(event =>
    (!query.projectId || event.projectId === query.projectId)
    && (!query.taskId || event.taskId === query.taskId)
    && (!query.sessionId || event.sessionId === query.sessionId),
  )
  const components = new Map<FrameworkMetricComponent, MutableComponentSummary>()

  for (const event of filtered) {
    const summary = components.get(event.component) ?? emptyComponent(event.component)
    summary.eventCount += 1
    summary.observedDurationMs += event.durationMs ?? 0
    summary.operationCounts[event.operation] = (summary.operationCounts[event.operation] ?? 0) + 1
    for (const [name, value] of Object.entries(event.values ?? {})) {
      summary.values[name] = (summary.values[name] ?? 0) + value
    }
    if (event.outcome === 'OK') summary.okCount += 1
    else if (event.outcome === 'MISS') summary.missCount += 1
    else if (event.outcome === 'PASS') summary.passCount += 1
    else if (event.outcome === 'FAIL') summary.failCount += 1
    else if (event.outcome === 'ERROR') summary.errorCount += 1
    components.set(event.component, summary)
  }

  const componentList: FrameworkEfficiencyComponentSummary[] = [...components.values()]
    .sort((a, b) => b.observedDurationMs - a.observedDurationMs || a.component.localeCompare(b.component))
    .map(item => ({
      ...item,
      operationCounts: { ...item.operationCounts },
      values: { ...item.values },
    }))

  const times = filtered.map(event => parseTime(event.at)).filter((value): value is number => value !== undefined)
  const firstMs = times.length > 0 ? Math.min(...times) : undefined
  const lastMs = times.length > 0 ? Math.max(...times) : undefined
  const observedFrameworkDurationMs = componentList.reduce((sum, item) => sum + item.observedDurationMs, 0)
  const findings: string[] = []

  const slowest = componentList[0]
  if (slowest && slowest.observedDurationMs > 0) {
    findings.push(`Observed framework time highest in ${slowest.component}: ${slowest.observedDurationMs} ms`)
  }
  for (const item of componentList) {
    if (item.errorCount > 0) findings.push(`${item.component}: ${item.errorCount} ERROR event(s)`)
    if (item.failCount > 0) findings.push(`${item.component}: ${item.failCount} FAIL event(s)`)
    const routeQueries = item.operationCounts.search ?? 0
    if (routeQueries > 0 && item.missCount > 0) {
      findings.push(`${item.component}: route miss ${item.missCount}/${routeQueries}`)
    }
  }
  const context = components.get('context')
  if (context) {
    const rebuilds = context.operationCounts.rebuild ?? 0
    const frames = context.operationCounts.buildFrame ?? 0
    if (rebuilds > 0) findings.push(`context: ${rebuilds} rebuild(s) across ${frames} frame build(s)`)
    const overBudget = context.values.overBudgetCount ?? 0
    if (overBudget > 0) findings.push(`context: ${overBudget} over-budget frame(s)`)
  }
  const runtime = components.get('runtime')
  if (runtime) {
    const input = runtime.values.inputTokens ?? 0
    const output = runtime.values.outputTokens ?? 0
    const cacheRead = runtime.values.cacheReadTokens ?? 0
    if (input + output + cacheRead > 0) {
      findings.push(`agent tokens: input=${input}, output=${output}, cacheRead=${cacheRead}`)
    }
  }

  return {
    standard: 'framework-efficiency-report-v0.1',
    ...(query.projectId ? { projectId: query.projectId } : {}),
    ...(query.taskId ? { taskId: query.taskId } : {}),
    ...(query.sessionId ? { sessionId: query.sessionId } : {}),
    eventCount: filtered.length,
    ...(firstMs !== undefined ? { firstAt: new Date(firstMs).toISOString() } : {}),
    ...(lastMs !== undefined ? { lastAt: new Date(lastMs).toISOString() } : {}),
    ...(firstMs !== undefined && lastMs !== undefined ? { wallSpanMs: Math.max(0, lastMs - firstMs) } : {}),
    observedFrameworkDurationMs,
    components: componentList,
    findings,
  }
}
