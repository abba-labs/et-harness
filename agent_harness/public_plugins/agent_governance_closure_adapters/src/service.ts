import { Service, type Context } from '@deepseek-ai/cordis'
import '@agent-harness/agent-governance-kernel'
import '@agent-harness/context-builder'
import '@agent-harness/knowledge-manager'
import '@agent-harness/experience-memory-manager'
import '@agent-harness/evidence-state-manager'
import '@agent-harness/gate-manager'
import { GovernanceChangeCandidateStore } from './change-candidate-store.js'
import {
  createExperienceMemoryClosureModule,
  createKnowledgeClosureModule,
} from './modules.js'
import {
  createArchitectureClosureModule,
  createContextLedgerClosureModule,
  createEvidenceStateClosureModule,
  createObligationGateReconcileModule,
  createRulesClosureModule,
  createWorkingSetClosureModule,
} from './remaining-modules.js'

export class AgentGovernanceClosureAdaptersService extends Service {
  constructor(ctx: Context) {
    super(ctx, 'agentGovernanceClosureAdapters')
    ctx.effect(() => {
      const changeCandidates = new GovernanceChangeCandidateStore()
      const disposers = [
        ctx.agentGovernanceKernel.registerClosureModule(createContextLedgerClosureModule(ctx.contextManager)),
        ctx.agentGovernanceKernel.registerClosureModule(createKnowledgeClosureModule(ctx.knowledgeManager)),
        ctx.agentGovernanceKernel.registerClosureModule(
          createExperienceMemoryClosureModule(ctx.experienceMemoryManager),
        ),
        ctx.agentGovernanceKernel.registerClosureModule(createArchitectureClosureModule(changeCandidates)),
        ctx.agentGovernanceKernel.registerClosureModule(createRulesClosureModule(changeCandidates)),
        ctx.agentGovernanceKernel.registerClosureModule(
          createEvidenceStateClosureModule(ctx.evidenceStateManager),
        ),
        ctx.agentGovernanceKernel.registerClosureModule(createWorkingSetClosureModule(ctx.contextManager)),
        ctx.agentGovernanceKernel.registerClosureModule(
          createObligationGateReconcileModule(ctx.evidenceStateManager, ctx.gateManager),
        ),
      ]
      return () => {
        for (const dispose of disposers.reverse()) dispose()
      }
    })
  }
}

declare module '@deepseek-ai/cordis' {
  interface Context {
    agentGovernanceClosureAdapters: AgentGovernanceClosureAdaptersService
  }
}

export default AgentGovernanceClosureAdaptersService
