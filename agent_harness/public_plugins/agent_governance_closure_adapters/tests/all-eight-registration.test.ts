import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const source = (): string => readFileSync(
  resolve(process.cwd(), 'src/service.ts'),
  'utf-8',
)

describe('all fixed Mandatory Closure Modules registration', () => {
  it('registers exactly one factory for each of the eight fixed mandatory responsibilities', () => {
    const text = source()
    const factories = [
      'createContextLedgerClosureModule',
      'createKnowledgeClosureModule',
      'createExperienceMemoryClosureModule',
      'createArchitectureClosureModule',
      'createRulesClosureModule',
      'createEvidenceStateClosureModule',
      'createWorkingSetClosureModule',
      'createObligationGateReconcileModule',
    ]
    for (const factory of factories) {
      expect(text.match(new RegExp(`${factory}\\(`, 'g'))?.length).toBeGreaterThanOrEqual(1)
    }
    expect(text.match(/registerClosureModule\(/g)?.length).toBe(8)
  })
})
