import { existsSync, mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { resolve } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import { GovernanceCatalogEngine } from '@agent-harness/governance-core'
import { loadProjectManifestFile } from '@agent-harness/project-manager'
import {
  ATP_CONTEXT_CONTRIBUTOR_PROVIDER_ID,
  ATP_PROJECT_ID,
} from '../src/context-contributor.js'
import {
  apply,
  governanceManifest,
  inject,
} from '../src/index.js'
import {
  AUTOMATED_TESTING_PLATFORM_PROJECT_MANIFEST,
  AUTOMATED_TESTING_PLATFORM_REQUIRED_PATHS,
  findAutomatedTestingPlatformRoot,
  isAutomatedTestingPlatformRoot,
  validateAutomatedTestingPlatformResources,
} from '../src/root-discovery.js'

const temporaryRoots: string[] = []

afterEach(() => {
  delete process.env.AUTOMATED_TESTING_PLATFORM_PROJECT_ROOT
  for (const root of temporaryRoots.splice(0)) {
    rmSync(root, { recursive: true, force: true })
  }
})

describe('Automated Testing Platform Project Plugin', () => {
  it('discovers the repository root from nested project paths', () => {
    const root = findAutomatedTestingPlatformRoot()
    expect(isAutomatedTestingPlatformRoot(root)).toBe(true)
    expect(findAutomatedTestingPlatformRoot(resolve(root, 'pc', 'et_test_platform'))).toBe(root)
    expect(findAutomatedTestingPlatformRoot(resolve(root, 'firmware', 'services'))).toBe(root)
    expect(findAutomatedTestingPlatformRoot(resolve(root, 'agent_harness', 'projects'))).toBe(root)
  })

  it('supports an explicit valid root and rejects an invalid one', () => {
    const root = findAutomatedTestingPlatformRoot()
    process.env.AUTOMATED_TESTING_PLATFORM_PROJECT_ROOT = root
    expect(findAutomatedTestingPlatformRoot()).toBe(root)

    const invalid = mkdtempSync(resolve(tmpdir(), 'atp-project-root-'))
    temporaryRoots.push(invalid)
    process.env.AUTOMATED_TESTING_PLATFORM_PROJECT_ROOT = invalid
    expect(() => findAutomatedTestingPlatformRoot()).toThrow(/不是有效 ATP 项目根目录/)
  })

  it('validates all required Project Contract resources', () => {
    const root = findAutomatedTestingPlatformRoot()
    const validation = validateAutomatedTestingPlatformResources(root)
    expect(validation.valid).toBe(true)
    expect(validation.missing).toEqual([])
    expect(validation.checked).toHaveLength(AUTOMATED_TESTING_PLATFORM_REQUIRED_PATHS.length)
    expect(validation.checked.every(path => existsSync(path))).toBe(true)
  })

  it('fails closed when a required resource is missing', () => {
    const root = findAutomatedTestingPlatformRoot()
    const validation = validateAutomatedTestingPlatformResources(root, [
      AUTOMATED_TESTING_PLATFORM_PROJECT_MANIFEST,
      'agent_harness/projects/automated_testing_platform/knowledge/DOES_NOT_EXIST.md',
    ])
    expect(validation.valid).toBe(false)
    expect(validation.missing).toHaveLength(1)
  })

  it('loads the manifest with one explicit project Context Contributor', () => {
    const root = findAutomatedTestingPlatformRoot()
    const manifest = loadProjectManifestFile(
      resolve(root, AUTOMATED_TESTING_PLATFORM_PROJECT_MANIFEST),
    )

    expect(manifest.contract_version).toBe('0.1')
    expect(manifest.project.id).toBe(ATP_PROJECT_ID)
    expect(manifest.project.aliases).toContain('ATP')
    expect(manifest.adapters?.task_context).toMatchObject({
      provider: ATP_CONTEXT_CONTRIBUTOR_PROVIDER_ID,
      capability: 'context.contribute',
    })
    expect(manifest.resources.architecture.path).toContain(
      'agent_harness/projects/automated_testing_platform/architecture/',
    )
    expect(manifest.resources.knowledge.standard).toBe('knowledge-v0.1')
    expect(manifest.metadata?.adapter_kind).toBe('project-context-contributor')
  })

  it('admits the project-owned Gate capabilities without redefining public core contracts', () => {
    const catalog = new GovernanceCatalogEngine()
    expect(catalog.admit(governanceManifest)).toEqual({ status: 'admitted', reasons: [] })
    expect(catalog.listCapabilities().map(item => item.id)).toEqual(expect.arrayContaining([
      'context.contribute',
      'governance.context.compile',
      'governance.scope.check',
      'validation.software.execute',
    ]))
  })

  it('registers only project-owned providers and leaves project binding to the host owner', () => {
    let effect: (() => void | (() => void)) | undefined
    const registeredProviders: Record<string, unknown>[] = []
    let removedPlugin: string | undefined
    let disposedProviderCount = 0
    let disposedService = false
    const context = {
      governanceCatalog: {
        admit: () => ({ status: 'admitted', reasons: [] }),
        registerProvider: (provider: Record<string, unknown>) => {
          registeredProviders.push(provider)
          return () => { disposedProviderCount += 1 }
        },
        removePlugin: (pluginId: string) => { removedPlugin = pluginId },
      },
      effect: (callback: () => void | (() => void)) => { effect = callback },
      plugin: () => ({ dispose: () => { disposedService = true } }),
    }

    apply(context as never)
    const cleanup = effect?.()

    expect(inject).toEqual(['governanceCatalog'])
    expect(governanceManifest.permissions).not.toContain('project.register')
    expect(registeredProviders).toContainEqual(expect.objectContaining({
      providerId: ATP_CONTEXT_CONTRIBUTOR_PROVIDER_ID,
      capability: 'context.contribute',
      metadata: expect.objectContaining({ projectId: ATP_PROJECT_ID }),
    }))
    expect(registeredProviders).toEqual(expect.arrayContaining([
      expect.objectContaining({
        capability: 'governance.context.compile',
        metadata: expect.objectContaining({
          preflightMethod: 'matchGateEvidenceInvocation',
          resultMethod: 'buildValidationReceipt',
          executionMethod: 'executeGateEvidence',
        }),
      }),
      expect.objectContaining({ capability: 'governance.scope.check' }),
      expect.objectContaining({ capability: 'validation.software.execute' }),
    ]))
    expect(registeredProviders).toHaveLength(4)

    if (typeof cleanup === 'function') cleanup()
    expect(disposedProviderCount).toBe(4)
    expect(disposedService).toBe(true)
    expect(removedPlugin).toBe(governanceManifest.pluginId)
  })
})
