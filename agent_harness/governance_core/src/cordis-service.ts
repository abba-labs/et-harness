import { Service, type Context } from '@deepseek-ai/cordis'
import './events.js'
import { GovernanceCatalogEngine } from './catalog-engine.js'
import type {
  GovernanceAdmissionDecision,
  GovernanceCapabilityContract,
  GovernanceCatalogSnapshot,
  GovernanceManifest,
  GovernancePluginRecord,
  GovernancePluginState,
  GovernanceProjectRegistration,
  GovernanceProviderRegistration,
} from './contracts.js'

export class GovernanceCatalogService extends Service {
  private readonly runtimeContext: Context
  private readonly engine = new GovernanceCatalogEngine()

  constructor(ctx: Context) {
    super(ctx, 'governanceCatalog')
    this.runtimeContext = ctx
  }

  admit(manifest: GovernanceManifest): GovernanceAdmissionDecision {
    const decision = this.engine.admit(manifest)
    if (decision.status === 'admitted') {
      this.runtimeContext.emit('governance/plugin-admitted', manifest)
    } else {
      this.runtimeContext.emit('governance/plugin-rejected', manifest, decision.reasons)
    }
    return decision
  }

  removePlugin(pluginId: string): boolean {
    const removed = this.engine.removePlugin(pluginId)
    if (removed) this.runtimeContext.emit('governance/plugin-removed', pluginId)
    return removed
  }

  registerProvider(provider: GovernanceProviderRegistration): () => void {
    this.engine.registerProvider(provider)
    this.runtimeContext.emit('governance/provider-registered', provider)

    return () => {
      if (this.engine.unregisterProvider(provider.providerId)) {
        this.runtimeContext.emit('governance/provider-removed', provider.providerId)
      }
    }
  }

  registerProject(project: GovernanceProjectRegistration): () => void {
    this.engine.registerProject(project)
    this.runtimeContext.emit('governance/project-registered', project)

    return () => {
      if (this.engine.unregisterProject(project.projectId)) {
        this.runtimeContext.emit('governance/project-removed', project.projectId)
      }
    }
  }

  setPluginState(pluginId: string, state: GovernancePluginState): void {
    this.engine.setPluginState(pluginId, state)
    this.runtimeContext.emit('governance/plugin-state-changed', pluginId, state)
  }

  getCapability(capabilityId: string): GovernanceCapabilityContract | undefined {
    return this.engine.getCapability(capabilityId)
  }

  listCapabilities(): readonly GovernanceCapabilityContract[] {
    return this.engine.listCapabilities()
  }

  listProviders(capabilityId: string): readonly GovernanceProviderRegistration[] {
    return this.engine.listProviders(capabilityId)
  }

  listPlugins(): readonly GovernancePluginRecord[] {
    return this.engine.listPlugins()
  }

  listProjects(): readonly GovernanceProjectRegistration[] {
    return this.engine.listProjects()
  }

  snapshot(): GovernanceCatalogSnapshot {
    return this.engine.snapshot()
  }
}

declare module '@deepseek-ai/cordis' {
  interface Context {
    governanceCatalog: GovernanceCatalogService
  }
}

export default GovernanceCatalogService
