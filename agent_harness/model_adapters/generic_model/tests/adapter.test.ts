import { describe, expect, it } from 'vitest'
import {
  GENERIC_MODEL_ADAPTER_CONTRACT_VERSION,
  createGovernanceSemanticExecutor,
  createGovernedModelWorkExecutor,
  type GenericModelGenerateRequest,
  type GenericModelGenerateResponse,
} from '../src/index.js'

class CapturingClient {
  readonly clientId = 'capture'
  readonly requests: GenericModelGenerateRequest[] = []

  constructor(private readonly responder: (request: GenericModelGenerateRequest) => GenericModelGenerateResponse) {}

  async generate(request: GenericModelGenerateRequest): Promise<GenericModelGenerateResponse> {
    this.requests.push(request)
    return this.responder(request)
  }
}

const semanticRequest = {
  contractVersion: '0.1',
  runtimeId: 'RUNTIME-1',
  actorId: 'ACTOR-1',
  projectId: 'project-1',
  taskId: 'TASK-1',
  turnId: 'TURN-1',
  journal: { taskId: 'TASK-1', turnId: 'TURN-1' },
  context: {
    actorId: 'ACTOR-1', projectId: 'project-1', taskId: 'TASK-1', goal: 'Analyze theme', stateVersion: 1,
    route: { architectureIds: ['A010'], ruleIds: ['R010'], knowledgeIds: ['K010'], gateIds: [] },
    applicableGateIds: [], pendingReviews: [], text: 'GOVERNANCE CONTEXT',
  },
  turnObservations: [{
    observationId: 'OBS-0001',
    observationRef: 'governance-observation://task/TASK-1/turn/TURN-1/OBS-0001/sha256:abc',
    kind: 'ASSISTANT_MESSAGE',
    text: 'Visible model output.',
    refs: ['message://assistant/1'],
    truncated: false,
  }],
  knowledgeClassification: {
    projectCategories: [], publicLibraryMounted: false, publicCategories: [],
  },
  requirements: ['Return valid reflection.'],
} as any

describe('generic model adapter', () => {
  it('keeps the business task verbatim while adding automatic Governance Context', async () => {
    const client = new CapturingClient(request => ({
      contractVersion: GENERIC_MODEL_ADAPTER_CONTRACT_VERSION,
      requestId: request.requestId,
      outputText: 'Visible answer',
    }))
    const executor = createGovernedModelWorkExecutor(client)
    const result = await executor.execute({
      runtimeId: 'RUNTIME-1',
      taskId: 'TASK-1',
      turnId: 'TURN-1',
      taskText: 'Analyze theme',
      context: semanticRequest.context,
    })
    expect(result.visibleOutput).toBe('Visible answer')
    expect(client.requests).toHaveLength(1)
    expect(client.requests[0]?.purpose).toBe('WORK')
    expect(client.requests[0]?.userText).toContain('Analyze theme')
    expect(client.requests[0]?.userText).toContain('GOVERNANCE CONTEXT')
  })

  it('passes bounded Turn Observations to the semantic model and accepts strict JSON', async () => {
    const output = {
      contractVersion: '0.1', taskId: 'TASK-1', turnId: 'TURN-1',
      context: { progress: 'done', decisions: [], confirmed: [], assumptions: [], openIssues: [], next: [], touchedRefs: [] },
      knowledge: { scopeDecision: 'NONE', rationale: 'none', candidates: [] },
      experience: { scopeDecision: 'NONE', rationale: 'none', candidates: [] },
      architecture: { scopeDecision: 'NONE', rationale: 'none', candidates: [] },
      rules: { scopeDecision: 'NONE', rationale: 'none', candidates: [] },
      evidence: { scopeDecision: 'NONE', rationale: 'none', candidates: [] },
      workingSet: { keep: [], add: [], remove: [] },
      obligations: { opened: [], resolved: [], unchanged: [] },
    }
    const client = new CapturingClient(request => ({
      contractVersion: GENERIC_MODEL_ADAPTER_CONTRACT_VERSION,
      requestId: request.requestId,
      outputText: JSON.stringify(output),
    }))
    const executor = createGovernanceSemanticExecutor(client)
    await expect(executor.reflect(semanticRequest)).resolves.toEqual(output)
    expect(client.requests[0]?.purpose).toBe('GOVERNANCE_REFLECTION')
    expect(client.requests[0]?.userText).toContain('Visible model output.')
    expect(client.requests[0]?.response.kind).toBe('JSON')
  })

  it('fails closed when a model adds prose around JSON', async () => {
    const client = new CapturingClient(request => ({
      contractVersion: GENERIC_MODEL_ADAPTER_CONTRACT_VERSION,
      requestId: request.requestId,
      outputText: 'Here is the JSON: {"x":1}',
    }))
    const executor = createGovernanceSemanticExecutor(client)
    await expect(executor.reflect(semanticRequest)).rejects.toThrow('one valid JSON object')
  })
})
