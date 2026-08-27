import { CORE_GOVERNANCE_CAPABILITIES, } from './contracts.js';
import { validateGovernanceManifest } from './validator.js';
export class GovernanceCatalogError extends Error {
    code = 'GOVERNANCE_CATALOG';
    constructor(message) {
        super(message);
        this.name = 'GovernanceCatalogError';
    }
}
export class GovernanceCatalogEngine {
    capabilities = new Map();
    coreCapabilityIds = new Set();
    plugins = new Map();
    providers = new Map();
    projects = new Map();
    constructor() {
        for (const contract of CORE_GOVERNANCE_CAPABILITIES) {
            this.capabilities.set(contract.id, contract);
            this.coreCapabilityIds.add(contract.id);
        }
    }
    admit(manifest) {
        if (this.plugins.has(manifest.pluginId)) {
            return {
                status: 'rejected',
                reasons: [`插件 ${manifest.pluginId} 已经准入，禁止重复登记`],
            };
        }
        const decision = validateGovernanceManifest(manifest, this.capabilities);
        if (decision.status === 'rejected')
            return decision;
        for (const declaration of manifest.provides) {
            if (!this.capabilities.has(declaration.capability) && declaration.contract) {
                this.capabilities.set(declaration.capability, declaration.contract);
            }
        }
        this.plugins.set(manifest.pluginId, { manifest, state: 'active' });
        return decision;
    }
    removePlugin(pluginId) {
        if (!this.plugins.delete(pluginId))
            return false;
        for (const [providerId, provider] of this.providers) {
            if (provider.pluginId === pluginId)
                this.providers.delete(providerId);
        }
        for (const capabilityId of [...this.capabilities.keys()]) {
            if (this.coreCapabilityIds.has(capabilityId))
                continue;
            const stillDeclared = [...this.plugins.values()].some(record => record.manifest.provides.some(item => item.capability === capabilityId));
            if (!stillDeclared)
                this.capabilities.delete(capabilityId);
        }
        return true;
    }
    registerProvider(provider) {
        if (this.providers.has(provider.providerId)) {
            throw new GovernanceCatalogError(`Provider ${provider.providerId} 已存在`);
        }
        const plugin = this.plugins.get(provider.pluginId);
        if (!plugin) {
            throw new GovernanceCatalogError(`Provider ${provider.providerId} 所属插件 ${provider.pluginId} 尚未通过治理准入`);
        }
        if (plugin.state === 'disabled') {
            throw new GovernanceCatalogError(`插件 ${provider.pluginId} 已禁用，不能注册 Provider`);
        }
        const declared = plugin.manifest.provides.some(item => item.capability === provider.capability);
        if (!declared) {
            throw new GovernanceCatalogError(`插件 ${provider.pluginId} 未声明能力 ${provider.capability}`);
        }
        if (!this.capabilities.has(provider.capability)) {
            throw new GovernanceCatalogError(`能力 ${provider.capability} 不存在`);
        }
        this.providers.set(provider.providerId, provider);
    }
    unregisterProvider(providerId) {
        return this.providers.delete(providerId);
    }
    registerProject(project) {
        if (!project.projectId.trim())
            throw new GovernanceCatalogError('projectId 不能为空');
        if (!project.displayName.trim())
            throw new GovernanceCatalogError('项目显示名称不能为空');
        if (!project.rootPath.trim())
            throw new GovernanceCatalogError('项目 rootPath 不能为空');
        if (this.projects.has(project.projectId)) {
            throw new GovernanceCatalogError(`项目 ${project.projectId} 已登记`);
        }
        this.projects.set(project.projectId, project);
    }
    unregisterProject(projectId) {
        return this.projects.delete(projectId);
    }
    setPluginState(pluginId, state) {
        const record = this.plugins.get(pluginId);
        if (!record)
            throw new GovernanceCatalogError(`插件 ${pluginId} 尚未准入`);
        this.plugins.set(pluginId, { manifest: record.manifest, state });
    }
    getCapability(capabilityId) {
        return this.capabilities.get(capabilityId);
    }
    listCapabilities() {
        return [...this.capabilities.values()].sort((a, b) => a.id.localeCompare(b.id));
    }
    listProviders(capabilityId) {
        return [...this.providers.values()]
            .filter(provider => provider.capability === capabilityId)
            .filter(provider => this.plugins.get(provider.pluginId)?.state !== 'disabled')
            .sort((a, b) => (b.priority ?? 0) - (a.priority ?? 0) || a.providerId.localeCompare(b.providerId));
    }
    listPlugins() {
        return [...this.plugins.values()].sort((a, b) => a.manifest.pluginId.localeCompare(b.manifest.pluginId));
    }
    listProjects() {
        return [...this.projects.values()].sort((a, b) => a.projectId.localeCompare(b.projectId));
    }
    snapshot() {
        return {
            capabilities: this.listCapabilities(),
            plugins: this.listPlugins(),
            providers: [...this.providers.values()].sort((a, b) => a.providerId.localeCompare(b.providerId)),
            projects: this.listProjects(),
        };
    }
}
