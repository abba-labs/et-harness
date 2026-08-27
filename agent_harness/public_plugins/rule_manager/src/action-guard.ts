import type { RuleNode } from './contracts.js'

export type RuleActionKind = 'PRODUCT_BUILD'

export interface RuleActionGuardInput {
  readonly actionKind: RuleActionKind
  readonly actionText: string
}

export interface RuleActionGuardResult {
  readonly allowed: boolean
  readonly ruleId?: string
  readonly reason?: string
}

interface RuleActionGuardSpec {
  readonly ruleId: string
  readonly actionKind: RuleActionKind
  readonly allow: readonly string[]
  readonly deny: readonly string[]
}

const extractField = (content: string, name: string): string | undefined => {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return new RegExp(`^${escaped}:\\s*(.+)$`, 'im').exec(content)?.[1]?.trim()
}

const parseListValue = (value: string): string[] => {
  const trimmed = value.trim()
  if (!trimmed) return []
  const unwrapped = trimmed.startsWith('[') && trimmed.endsWith(']')
    ? trimmed.slice(1, -1)
    : trimmed
  return unwrapped
    .split(/[,;，；]/)
    .map(item => item.trim())
    .filter(Boolean)
}

const normalize = (value: string): string =>
  value
    .replaceAll('\\', '/')
    .replace(/\/{2,}/g, '/')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()

const escapedToken = (value: string): string =>
  value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

const commandTokenMatch = (text: string, token: string): boolean => {
  const normalizedToken = normalize(token)
  if (!normalizedToken) return false
  return new RegExp(
    `(^|[^a-z0-9_-])${escapedToken(normalizedToken)}(?=$|[^a-z0-9_-])`,
    'i',
  ).test(text)
}

const governedEntrypointMatch = (text: string, entrypoint: string): boolean => {
  const normalizedEntrypoint = normalize(entrypoint)
  if (!normalizedEntrypoint) return false
  return new RegExp(
    `(^|[^a-z0-9_./-])(?:\\./)?${escapedToken(normalizedEntrypoint)}(?=$|[^a-z0-9_./-])`,
    'i',
  ).test(text)
}

export function parseRuleActionGuard(node: RuleNode): RuleActionGuardSpec | undefined {
  if (!node.isLeaf) return undefined
  const enforcement = extractField(node.directContent, 'Enforcement')?.toUpperCase()
  if (enforcement !== 'ACTION_GUARD') return undefined

  const action = extractField(node.directContent, 'Action')?.toUpperCase()
  if (action !== 'PRODUCT_BUILD') {
    throw new Error(`Rule ${node.id} ACTION_GUARD 缺少合法 Action: PRODUCT_BUILD`)
  }

  const allow = parseListValue(extractField(node.directContent, 'Allow') ?? '')
  const deny = parseListValue(extractField(node.directContent, 'Deny') ?? '')
  if (allow.length === 0 && deny.length === 0) {
    throw new Error(`Rule ${node.id} ACTION_GUARD 必须声明 Allow 或 Deny`)
  }

  return { ruleId: node.id, actionKind: action, allow, deny }
}

export function evaluateRuleActionGuards(
  nodes: readonly RuleNode[],
  input: RuleActionGuardInput,
): RuleActionGuardResult {
  const text = normalize(input.actionText)
  for (const node of nodes) {
    const guard = parseRuleActionGuard(node)
    if (!guard || guard.actionKind !== input.actionKind) continue

    const denied = guard.deny.find(pattern => commandTokenMatch(text, pattern))
    if (denied) {
      return {
        allowed: false,
        ruleId: guard.ruleId,
        reason: `Action contains forbidden direct entrypoint '${denied}'.`,
      }
    }

    if (guard.allow.length > 0 && !guard.allow.some(pattern => governedEntrypointMatch(text, pattern))) {
      return {
        allowed: false,
        ruleId: guard.ruleId,
        reason: `Action must use one of the governed entrypoints: ${guard.allow.join(', ')}.`,
      }
    }
  }
  return { allowed: true }
}
