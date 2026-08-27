import '@deepseek-ai/cordis';
import type { GovernanceManifest, GovernancePluginState, GovernanceProjectRegistration, GovernanceProviderRegistration } from './contracts.js';
declare module '@deepseek-ai/cordis' {
    interface Events {
        'governance/plugin-admitted': (manifest: GovernanceManifest) => void;
        'governance/plugin-rejected': (manifest: GovernanceManifest, reasons: readonly string[]) => void;
        'governance/plugin-removed': (pluginId: string) => void;
        'governance/provider-registered': (provider: GovernanceProviderRegistration) => void;
        'governance/provider-removed': (providerId: string) => void;
        'governance/project-registered': (project: GovernanceProjectRegistration) => void;
        'governance/project-removed': (projectId: string) => void;
        'governance/plugin-state-changed': (pluginId: string, state: GovernancePluginState) => void;
    }
}
