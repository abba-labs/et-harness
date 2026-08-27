import { Service } from '@deepseek-ai/cordis';
import './events.js';
import { GovernanceCatalogEngine } from './catalog-engine.js';
export class GovernanceCatalogService extends Service {
    runtimeContext;
    engine = new GovernanceCatalogEngine();
    constructor(ctx) {
        super(ctx, 'governanceCatalog');
        this.runtimeContext = ctx;
    }
    admit(manifest) {
        const decision = this.engine.admit(manifest);
        if (decision.status === 'admitted') {
            this.runtimeContext.emit('governance/plugin-admitted', manifest);
        }
        else {
            this.runtimeContext.emit('governance/plugin-rejected', manifest, decision.reasons);
        }
        return decision;
    }
    removePlugin(pluginId) {
        const removed = this.engine.removePlugin(pluginId);
        if (removed)
            this.runtimeContext.emit('governance/plugin-removed', pluginId);
        return removed;
    }
    registerProvider(provider) {
        this.engine.registerProvider(provider);
        this.runtimeContext.emit('governance/provider-registered', provider);
        return () => {
            if (this.engine.unregisterProvider(provider.providerId)) {
                this.runtimeContext.emit('governance/provider-removed', provider.providerId);
            }
        };
    }
    registerProject(project) {
        this.engine.registerProject(project);
        this.runtimeContext.emit('governance/project-registered', project);
        return () => {
            if (this.engine.unregisterProject(project.projectId)) {
                this.runtimeContext.emit('governance/project-removed', project.projectId);
            }
        };
    }
    setPluginState(pluginId, state) {
        this.engine.setPluginState(pluginId, state);
        this.runtimeContext.emit('governance/plugin-state-changed', pluginId, state);
    }
    getCapability(capabilityId) {
        return this.engine.getCapability(capabilityId);
    }
    listCapabilities() {
        return this.engine.listCapabilities();
    }
    listProviders(capabilityId) {
        return this.engine.listProviders(capabilityId);
    }
    listPlugins() {
        return this.engine.listPlugins();
    }
    listProjects() {
        return this.engine.listProjects();
    }
    snapshot() {
        return this.engine.snapshot();
    }
}
export default GovernanceCatalogService;
