import { Service, type Context } from '@deepseek-ai/cordis';
import './events.js';
import type { GovernanceAdmissionDecision, GovernanceCapabilityContract, GovernanceCatalogSnapshot, GovernanceManifest, GovernancePluginRecord, GovernancePluginState, GovernanceProjectRegistration, GovernanceProviderRegistration } from './contracts.js';
export declare class GovernanceCatalogService extends Service {
    private readonly runtimeContext;
    private readonly engine;
    constructor(ctx: Context);
    admit(manifest: GovernanceManifest): GovernanceAdmissionDecision;
    removePlugin(pluginId: string): boolean;
    registerProvider(provider: GovernanceProviderRegistration): () => void;
    registerProject(project: GovernanceProjectRegistration): () => void;
    setPluginState(pluginId: string, state: GovernancePluginState): void;
    getCapability(capabilityId: string): GovernanceCapabilityContract | undefined;
    listCapabilities(): readonly GovernanceCapabilityContract[];
    listProviders(capabilityId: string): readonly GovernanceProviderRegistration[];
    listPlugins(): readonly GovernancePluginRecord[];
    listProjects(): readonly GovernanceProjectRegistration[];
    snapshot(): GovernanceCatalogSnapshot;
}
declare module '@deepseek-ai/cordis' {
    interface Context {
        governanceCatalog: GovernanceCatalogService;
    }
}
export default GovernanceCatalogService;
