import { readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { validatePerformanceBaselineReport } from '../src/index.js'

describe('Execution Supervisor committed performance baselines', () => {
  it('keeps every reviewed baseline contract-valid and explicitly unfrozen', () => {
    const root = resolve(import.meta.dirname, '../baselines')
    const files = readdirSync(root)
      .filter(name => name.endsWith('.json'))
      .sort()
    expect(files.length).toBeGreaterThan(0)
    for (const name of files) {
      const payload = JSON.parse(readFileSync(resolve(root, name), 'utf8')) as unknown
      const result = validatePerformanceBaselineReport(payload)
      expect(result, name).toMatchObject({ valid: true })
      if (result.valid) expect(result.value.thresholdsFrozen).toBe(false)
    }
  })
})
