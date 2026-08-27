import { describe, expect, it } from 'vitest'
import {
  GovernanceCatalogEngine,
  GovernanceCatalogError,
  type GovernanceManifest,
} from '../src/index.js'

function manifest(overrides: Partial<GovernanceManifest> = {}): GovernanceManifest {
  return {
    manifestVersion: '0.1',
    pluginId: 'test.rule-provider',
    pluginVersion: '0.1.0',
    displayName: '测试规则 Provider',
    scope: { kind: 'global' },
    trust: 'reviewed',
    permissions: ['project.read'],
    provides: [{ capability: 'rule.resolve' }],
    ...overrides,
  }
}

describe('GovernanceCatalogEngine', () => {
  it('准入合法治理清单', () => {
    const engine = new GovernanceCatalogEngine()
    const decision = engine.admit(manifest())

    expect(decision.status).toBe('admitted')
    expect(engine.listPlugins()).toHaveLength(1)
  })

  it('拒绝没有契约的未知能力', () => {
    const engine = new GovernanceCatalogEngine()
    const decision = engine.admit(
      manifest({
        pluginId: 'test.unknown-provider',
        provides: [{ capability: 'custom.unknown' }],
      }),
    )

    expect(decision.status).toBe('rejected')
    expect(decision.reasons.join('\n')).toContain('必须携带能力契约')
  })

  it('允许插件声明新的能力契约', () => {
    const engine = new GovernanceCatalogEngine()
    const decision = engine.admit(
      manifest({
        pluginId: 'test.custom-provider',
        provides: [
          {
            capability: 'custom.resolve',
            contract: {
              id: 'custom.resolve',
              version: '0.1',
              summary: '测试自定义能力',
              criticality: 'optional',
            },
          },
        ],
      }),
    )

    expect(decision.status).toBe('admitted')
    expect(engine.getCapability('custom.resolve')?.summary).toBe('测试自定义能力')
  })

  it('拒绝对已有能力做同版本语义重定义', () => {
    const engine = new GovernanceCatalogEngine()
    const decision = engine.admit(
      manifest({
        pluginId: 'test.rule-redefine',
        provides: [
          {
            capability: 'rule.resolve',
            contract: {
              id: 'rule.resolve',
              version: '0.1',
              summary: '与内置定义不同的语义',
              criticality: 'core',
            },
          },
        ],
      }),
    )

    expect(decision.status).toBe('rejected')
    expect(decision.reasons.join('\n')).toContain('禁止静默重定义')
  })

  it('禁止 Provider 绑定未声明能力', () => {
    const engine = new GovernanceCatalogEngine()
    engine.admit(manifest())

    expect(() =>
      engine.registerProvider({
        providerId: 'provider.memory',
        pluginId: 'test.rule-provider',
        capability: 'memory.context',
      }),
    ).toThrow(GovernanceCatalogError)
  })

  it('可以按能力查询 Provider 并按优先级排序', () => {
    const engine = new GovernanceCatalogEngine()
    engine.admit(manifest())
    engine.admit(
      manifest({
        pluginId: 'test.rule-provider-secondary',
        displayName: '第二规则 Provider',
      }),
    )

    engine.registerProvider({
      providerId: 'provider.rule.secondary',
      pluginId: 'test.rule-provider-secondary',
      capability: 'rule.resolve',
      priority: 10,
    })
    engine.registerProvider({
      providerId: 'provider.rule.primary',
      pluginId: 'test.rule-provider',
      capability: 'rule.resolve',
      priority: 20,
    })

    expect(engine.listProviders('rule.resolve').map(item => item.providerId)).toEqual([
      'provider.rule.primary',
      'provider.rule.secondary',
    ])
  })

  it('登记项目并拒绝重复 projectId', () => {
    const engine = new GovernanceCatalogEngine()
    engine.registerProject({
      projectId: 'et-tool',
      displayName: 'ET-TOOL',
      rootPath: '/workspace/et-tool',
    })

    expect(engine.listProjects()).toHaveLength(1)
    expect(() =>
      engine.registerProject({
        projectId: 'et-tool',
        displayName: 'ET-TOOL Duplicate',
        rootPath: '/other',
      }),
    ).toThrow(GovernanceCatalogError)
  })

  it('移除唯一声明插件时清理其 Provider 和自定义能力', () => {
    const engine = new GovernanceCatalogEngine()
    engine.admit(
      manifest({
        pluginId: 'test.custom-provider',
        provides: [
          {
            capability: 'custom.resolve',
            contract: {
              id: 'custom.resolve',
              version: '0.1',
              summary: '测试自定义能力',
              criticality: 'optional',
            },
          },
        ],
      }),
    )
    engine.registerProvider({
      providerId: 'provider.custom',
      pluginId: 'test.custom-provider',
      capability: 'custom.resolve',
    })

    expect(engine.removePlugin('test.custom-provider')).toBe(true)
    expect(engine.listProviders('custom.resolve')).toHaveLength(0)
    expect(engine.getCapability('custom.resolve')).toBeUndefined()
  })

  it('仍有其他准入插件声明自定义能力时保留能力契约', () => {
    const engine = new GovernanceCatalogEngine()
    const customContract = {
      id: 'custom.resolve',
      version: '0.1',
      summary: '测试共享自定义能力',
      criticality: 'optional' as const,
    }

    engine.admit(
      manifest({
        pluginId: 'test.custom-owner',
        provides: [{ capability: 'custom.resolve', contract: customContract }],
      }),
    )
    engine.admit(
      manifest({
        pluginId: 'test.custom-secondary',
        provides: [{ capability: 'custom.resolve' }],
      }),
    )

    expect(engine.removePlugin('test.custom-owner')).toBe(true)
    expect(engine.getCapability('custom.resolve')).toEqual(customContract)
  })
})
