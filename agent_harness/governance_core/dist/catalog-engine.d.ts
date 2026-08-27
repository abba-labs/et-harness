import { type GovernanceAdmissionDecision, type GovernanceCapabilityContract, type GovernanceCatalogSnapshot, type GovernanceManifest, type GovernancePluginRecord, type GovernancePluginState, type GovernanceProjectRegistration, type GovernanceProviderRegistration } from './contracts.js';
export declare class GovernanceCatalogError extends Error {
    readonly code = "GOVERNANCE_CATALOG";
    constructor(message: string);
}
export declare class GovernanceCatalogEngine {
    private readonly capabilities;
    private readonly coreCapabilityIds;
    private readonly plugins;
    private readonly providers;
    private readonly projects;
    constructor();
    admit(manifest: GovernanceManifest): GovernanceAdmissionDecision;
    removePlugin(pluginId: string): boolean;
    registerProvider(provider: GovernanceProviderRegistration): void;
    unregisterProvider(providerId: string): boolean;
    registerProject(project: GovernanceProjectRegistration): void;
    unregisterProject(projectId: string): boolean;
    setPluginState(pluginId: string, state: GovernancePluginState): void;
    getCapability(capabilityId: string): GovernanceCapabilityContract | undefined;
    listCapabilities(): readonly GovernanceCapabilityContract[];
    listProviders(capabilityId: string): readonly GovernanceProviderRegistration[];
    listPlugins(): readonly GovernancePluginRecord[];
    listProjects(): readonly GovernanceProjectRegistration[];
    snapshot(): GovernanceCatalogSnapshot;
}
