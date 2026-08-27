export type GovernanceScopeKind = 'global' | 'domain' | 'project';
export interface GovernanceScope {
    readonly kind: GovernanceScopeKind;
    readonly id?: string;
}
export type GovernanceTrustLevel = 'builtin' | 'trusted' | 'reviewed' | 'untrusted';
export type GovernancePluginState = 'active' | 'degraded' | 'disabled';
export type GovernanceCriticality = 'core' | 'important' | 'optional';
export interface GovernanceCapabilityContract {
    readonly id: string;
    readonly version: string;
    readonly summary: string;
    readonly criticality: GovernanceCriticality;
    readonly inputSchema?: string;
    readonly outputSchema?: string;
}
export interface GovernanceCapabilityDeclaration {
    readonly capability: string;
    readonly contract?: GovernanceCapabilityContract;
}
export interface GovernanceManifest {
    readonly manifestVersion: '0.1';
    readonly pluginId: string;
    readonly pluginVersion: string;
    readonly displayName: string;
    readonly scope: GovernanceScope;
    readonly trust: GovernanceTrustLevel;
    readonly permissions: readonly string[];
    readonly provides: readonly GovernanceCapabilityDeclaration[];
}
export interface GovernanceAdmissionDecision {
    readonly status: 'admitted' | 'rejected';
    readonly reasons: readonly string[];
}
export interface GovernanceProviderRegistration {
    readonly providerId: string;
    readonly pluginId: string;
    readonly capability: string;
    readonly priority?: number;
    readonly metadata?: Readonly<Record<string, unknown>>;
}
export interface GovernanceProjectRegistration {
    readonly projectId: string;
    readonly displayName: string;
    readonly rootPath: string;
    readonly metadata?: Readonly<Record<string, unknown>>;
}
export interface GovernancePluginRecord {
    readonly manifest: GovernanceManifest;
    readonly state: GovernancePluginState;
}
export interface GovernanceCatalogSnapshot {
    readonly capabilities: readonly GovernanceCapabilityContract[];
    readonly plugins: readonly GovernancePluginRecord[];
    readonly providers: readonly GovernanceProviderRegistration[];
    readonly projects: readonly GovernanceProjectRegistration[];
}
export declare const CORE_GOVERNANCE_CAPABILITIES: readonly GovernanceCapabilityContract[];
