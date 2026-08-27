import type {
  ContextHandleInput,
  ContextLedgerEntry,
  ContextProgressLedger,
  ContextRecentEventInput,
  ContextSession,
  ContextTaskLedger,
} from './contracts.js'

export type ContextLintSeverity = 'ERROR' | 'WARNING'

export interface ContextLintIssue {
  readonly severity: ContextLintSeverity
  readonly code: string
  readonly field: string
  readonly message: string
}

export interface ContextLintResult {
  readonly valid: boolean
  readonly errors: readonly ContextLintIssue[]
  readonly warnings: readonly ContextLintIssue[]
}

const LIMITS = {
  goal: 400,
  ledgerEntry: 300,
  planItem: 220,
  progressField: 300,
  recentSummary: 300,
  handleTitle: 120,
  handleSummary: 220,
  reference: 500,
} as const

const UNCERTAINTY_RE = /(可能|猜测|似乎|预计|大概|也许|怀疑|maybe|probably|likely|seems?|suspect|assum(?:e|ed|ption))/i
const STABLE_REFERENCE_RE = /^(?:[ARKG]\d{3}(?:\.\d{3})*|(?:knowledge|source|evidence|project|file|runtime):\/\/\S+)$/i

const issue = (
  severity: ContextLintSeverity,
  code: string,
  field: string,
  message: string,
): ContextLintIssue => ({ severity, code, field, message })

const lintSingleLine = (
  value: string | undefined,
  field: string,
  max: number,
  issues: ContextLintIssue[],
): void => {
  if (value === undefined) return
  const trimmed = value.trim()
  if (!trimmed) {
    issues.push(issue('ERROR', 'EMPTY_TEXT', field, `${field} 不能为空`))
    return
  }
  if (/\r|\n/.test(trimmed)) {
    issues.push(issue('ERROR', 'MULTILINE_TEXT', field, `${field} 必须使用单行短句`))
  }
  if (trimmed.length > max) {
    issues.push(issue('ERROR', 'TEXT_TOO_LONG', field, `${field} 超过 ${max} 字符上限`))
  }
}

const lintReference = (value: string, field: string, issues: ContextLintIssue[]): void => {
  lintSingleLine(value, field, LIMITS.reference, issues)
  if (value.trim() && !STABLE_REFERENCE_RE.test(value.trim())) {
    issues.push(issue(
      'WARNING',
      'NON_STANDARD_REFERENCE',
      field,
      `${field} 不是已知稳定 ID / URI；优先使用 A/R/K/G ID 或 knowledge/source/evidence/project/file URI`,
    ))
  }
}

const lintEntryList = (
  entries: readonly ContextLedgerEntry[],
  field: string,
  issues: ContextLintIssue[],
  options: { confirmed?: boolean } = {},
): void => {
  const seen = new Set<string>()
  entries.forEach((entry, index) => {
    const itemField = `${field}[${index}]`
    lintSingleLine(entry.text, `${itemField}.text`, LIMITS.ledgerEntry, issues)
    const normalized = entry.text.trim().toLowerCase().replace(/\s+/g, ' ')
    if (seen.has(normalized)) {
      issues.push(issue('WARNING', 'DUPLICATE_ENTRY', itemField, `${field} 内存在重复记录`))
    }
    seen.add(normalized)

    if (options.confirmed && entry.refs.length === 0) {
      issues.push(issue('ERROR', 'CONFIRMED_WITHOUT_REF', itemField, 'Confirmed 必须至少包含一个可追溯 Ref'))
    }
    if (options.confirmed && UNCERTAINTY_RE.test(entry.text)) {
      issues.push(issue('ERROR', 'CONFIRMED_UNCERTAIN', itemField, 'Confirmed 不得包含可能、猜测、似乎、预计等不确定判断'))
    }
    entry.refs.forEach((ref, refIndex) => lintReference(ref, `${itemField}.refs[${refIndex}]`, issues))
  })
}

export function lintTaskLedger(ledger: ContextTaskLedger): ContextLintResult {
  const issues: ContextLintIssue[] = []
  lintSingleLine(ledger.goal, 'taskLedger.goal', LIMITS.goal, issues)
  ledger.scopeRefs.forEach((ref, index) => lintReference(ref, `taskLedger.scopeRefs[${index}]`, issues))
  ledger.constraintRefs.forEach((ref, index) => lintReference(ref, `taskLedger.constraintRefs[${index}]`, issues))
  lintEntryList(ledger.confirmed, 'taskLedger.confirmed', issues, { confirmed: true })
  lintEntryList(ledger.assumptions, 'taskLedger.assumptions', issues)
  lintEntryList(ledger.openIssues, 'taskLedger.openIssues', issues)
  ledger.plan.forEach((item, index) => lintSingleLine(item, `taskLedger.plan[${index}]`, LIMITS.planItem, issues))

  const confirmed = new Set(ledger.confirmed.map(entry => entry.text.trim().toLowerCase().replace(/\s+/g, ' ')))
  ledger.assumptions.forEach((entry, index) => {
    if (confirmed.has(entry.text.trim().toLowerCase().replace(/\s+/g, ' '))) {
      issues.push(issue(
        'ERROR',
        'FACT_ASSUMPTION_COLLISION',
        `taskLedger.assumptions[${index}]`,
        '同一内容不能同时存在于 Confirmed 与 Assumptions',
      ))
    }
  })

  return toResult(issues)
}

export function lintProgressLedger(ledger: ContextProgressLedger): ContextLintResult {
  const issues: ContextLintIssue[] = []
  lintSingleLine(ledger.lastAction, 'progressLedger.lastAction', LIMITS.progressField, issues)
  lintSingleLine(ledger.lastResult, 'progressLedger.lastResult', LIMITS.progressField, issues)
  lintSingleLine(ledger.currentProblem, 'progressLedger.currentProblem', LIMITS.progressField, issues)
  ledger.touchedRefs.forEach((ref, index) => lintReference(ref, `progressLedger.touchedRefs[${index}]`, issues))
  ledger.blockers.forEach((item, index) => lintSingleLine(item, `progressLedger.blockers[${index}]`, LIMITS.progressField, issues))
  ledger.next.forEach((item, index) => lintSingleLine(item, `progressLedger.next[${index}]`, LIMITS.planItem, issues))
  ledger.evidenceRefs.forEach((ref, index) => lintReference(ref, `progressLedger.evidenceRefs[${index}]`, issues))
  return toResult(issues)
}

export function lintRecentEvent(input: ContextRecentEventInput): ContextLintResult {
  const issues: ContextLintIssue[] = []
  lintSingleLine(input.summary, 'recent.summary', LIMITS.recentSummary, issues)
  input.refs?.forEach((ref, index) => lintReference(ref, `recent.refs[${index}]`, issues))
  input.evidenceRefs?.forEach((ref, index) => lintReference(ref, `recent.evidenceRefs[${index}]`, issues))
  return toResult(issues)
}

export function lintHandle(input: ContextHandleInput): ContextLintResult {
  const issues: ContextLintIssue[] = []
  lintReference(input.reference, 'handle.reference', issues)
  if (input.title !== undefined) lintSingleLine(input.title, 'handle.title', LIMITS.handleTitle, issues)
  if (input.summary !== undefined) lintSingleLine(input.summary, 'handle.summary', LIMITS.handleSummary, issues)
  return toResult(issues)
}

export function lintContextSession(session: ContextSession): ContextLintResult {
  const issues: ContextLintIssue[] = []
  const task = lintTaskLedger(session.taskLedger)
  const progress = lintProgressLedger(session.progressLedger)
  issues.push(...task.errors, ...task.warnings, ...progress.errors, ...progress.warnings)
  session.recentTail.forEach((event, index) => {
    const result = lintRecentEvent(event)
    for (const item of [...result.errors, ...result.warnings]) {
      issues.push({ ...item, field: `recentTail[${index}].${item.field.replace(/^recent\./, '')}` })
    }
  })
  session.handles.forEach((handle, index) => {
    const result = lintHandle(handle)
    for (const item of [...result.errors, ...result.warnings]) {
      issues.push({ ...item, field: `handles[${index}].${item.field.replace(/^handle\./, '')}` })
    }
  })
  return toResult(issues)
}

export function assertContextLint(result: ContextLintResult): void {
  if (result.errors.length === 0) return
  throw new Error(`Context Lint 拒绝写入: ${result.errors.map(item => `${item.code}@${item.field}: ${item.message}`).join('; ')}`)
}

const toResult = (issues: readonly ContextLintIssue[]): ContextLintResult => {
  const errors = issues.filter(item => item.severity === 'ERROR')
  const warnings = issues.filter(item => item.severity === 'WARNING')
  return { valid: errors.length === 0, errors, warnings }
}
