import { readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const sourceRoot = resolve(import.meta.dirname, '../src')
const sourceText = readdirSync(sourceRoot)
  .filter(name => name.endsWith('.ts'))
  .sort()
  .map(name => readFileSync(resolve(sourceRoot, name), 'utf8'))
  .join('\n')

describe('Execution Supervisor public boundary', () => {
  it('contains no validation-project or frozen-task business logic', () => {
    expect(sourceText).not.toMatch(/ET6801|eTimer|automated[-_]testing[-_]platform/i)
  })

  it('contains no model-provider, Host or external Tool SDK dependency', () => {
    expect(sourceText).not.toMatch(/from\s+['"](?:openai|anthropic|@anthropic|@google|github|octokit|axios|undici)/i)
    expect(sourceText).not.toMatch(/\b(?:fetch|spawn|execFile|readFileSync|writeFileSync)\s*\(/)
  })

  it('keeps Phase 0 deterministic and synchronous', () => {
    expect(sourceText).not.toMatch(/\basync\s+(?:function|\()/)
    expect(sourceText).not.toMatch(/new\s+Promise\s*\(/)
    expect(sourceText).not.toMatch(/setTimeout\s*\(/)
  })
})
