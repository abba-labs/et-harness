import { readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { validatePerformanceBaselineReport } from '../src/index.js'

describe('Execution Supervisor committed performance baselines', () => {
  it('keeps every reviewed baseline contract-valid and explicitly unfrozen', () => {
    const root = resolve(import.meta.dirname, '../baselines')
    const files = readdirSync(root)
      .filter(name => name.startsWith('phase0-') && name.endsWith('.json'))
      .sort()
    expect(files.length).toBeGreaterThan(0)
    for (const name of files) {
      const payload = JSON.parse(readFileSync(resolve(root, name), 'utf8')) as unknown
      const result = validatePerformanceBaselineReport(payload)
      expect(result, name).toMatchObject({ valid: true })
      if (result.valid) expect(result.value.thresholdsFrozen).toBe(false)
    }
  })

  it('keeps the independently frozen Phase 7 SLO profile explicit and auditable', () => {
    const path = resolve(import.meta.dirname, '../baselines/phase7-ci-linux-x64-node22-slo.json')
    const profile = JSON.parse(readFileSync(path, 'utf8')) as Record<string, any>
    expect(profile).toMatchObject({
      schema: 'agent-harness.execution-supervisor-phase7-slo.v0.1',
      environment: { nodeVersionPrefix: 'v22.', platform: 'linux', architecture: 'x64' },
      scenario: { eventCount: 1_000, replayPageLimit: 127 },
    })
    expect(profile.measurementEvidence).toHaveLength(3)
    for (const value of Object.values(profile.limits as Record<string, unknown>)) {
      expect(typeof value).toBe('number')
      if (typeof value !== 'number') throw new Error('Phase 7 SLO limits must be numeric')
      expect(Number.isFinite(value)).toBe(true)
      expect(value).toBeGreaterThan(0)
    }
    for (const sample of profile.measurementEvidence as Record<string, unknown>[]) {
      expect(sample.sha256).toMatch(/^[a-f0-9]{64}$/)
      for (const [name, value] of Object.entries(sample)) {
        if (name === 'sha256') continue
        expect(typeof value, name).toBe('number')
        if (typeof value !== 'number') throw new Error(`${name} must be numeric`)
        expect(Number.isFinite(value), name).toBe(true)
        expect(value, name).toBeGreaterThan(0)
      }
    }
  })
})
