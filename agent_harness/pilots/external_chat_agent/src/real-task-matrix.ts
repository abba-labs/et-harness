#!/usr/bin/env node

import { randomUUID } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import {
  mkdirSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { join, resolve } from 'node:path'
import { tmpdir } from 'node:os'
import { Context } from '@deepseek-ai/cordis'
import GovernanceCatalogService from '@agent-harness/governance-core'
import * as projectManagerPlugin from '@agent-harness/project-manager'
import * as architecturePlugin from '@agent-harness/architecture-navigator'
import * as rulePlugin from '@agent-harness/rule-manager'
import * as evidencePlugin from '@agent-harness/evidence-state-manager'
import * as knowledgePlugin from '@agent-harness/knowledge-manager'
import * as gatePlugin from '@agent-harness/gate-manager'
import * as contextPlugin from '@agent-harness/context-builder'
import * as experiencePlugin from '@agent-harness/experience-memory-manager'
import * as kernelPlugin from '@agent-harness/agent-governance-kernel'
import * as closurePlugin from '@agent-harness/agent-governance-closure-adapters'
import * as enginePlugin from '@agent-harness/auto-governance-engine'
import * as runtimePlugin from '@agent-harness/governance-runtime'
import * as etToolProjectPlugin from '@agent-harness/project-et-tool'
import * as etToolReviewPlugin from '@agent-harness/project-et-tool/review-adapter'
import {
  GENERIC_MODEL_ADAPTER_CONTRACT_VERSION,
  createGovernanceSemanticExecutor,
  type GenericModelClient,
  type GenericModelGenerateRequest,
  type GenericModelGenerateResponse,
} from '@agent-harness/generic-model-adapter'
import { GenericModelPilotDriver } from '@agent-harness/generic-model-pilot'
import {
  createEtToolProjectSnapshot,
  type EtToolProjectSnapshot,
} from './et-tool-snapshot.js'

const tick = (): Promise<void> => new Promise(resolveTick => setTimeout(resolveTick, 0))

interface DisposableFiber {
  dispose(): Promise<void> | void
}

interface MatrixEnvironment {
  readonly ctx: Context
  readonly fibers: DisposableFiber[]
  readonly snapshot: EtToolProjectSnapshot
  readonly runtime: import('@agent-harness/governance-runtime').GovernanceRuntimeService
  readonly knowledge: import('@agent-harness/knowledge-manager').KnowledgeManagerService
  readonly evidence: import('@agent-harness/evidence-state-manager').EvidenceStateManagerService
  readonly contextManager: {
    buildFrame(projectId: string, taskId: string): { readonly stateVersion: number }
  }
  readonly model: MatrixModelClient
}

interface ScenarioResult {
  readonly assertions: Readonly<Record<string, boolean>>
  readonly diagnostics: Readonly<Record<string, unknown>>
}

const unique = (values: readonly string[]): string[] =>
  [...new Set(values.map(value => value.trim()).filter(Boolean))]

const allKnowledgeIds = (index: any): string[] =>
  (index.files ?? []).flatMap((file: any) => file.nodes ?? [])

const runGit = (root: string, args: readonly string[]): string =>
  execFileSync('git', ['-C', root, ...args], {
    encoding: 'utf8',
    windowsHide: true,
  }).trim()

const initializeSnapshotGit = (root: string): void => {
  runGit(root, ['init', '-q'])
  runGit(root, ['config', 'user.name', 'agent-harness-matrix'])
  runGit(root, ['config', 'user.email', 'agent-harness-matrix@example.invalid'])
  runGit(root, ['add', '.'])
  runGit(root, ['commit', '-qm', 'matrix baseline'])
}

const commitSnapshot = (root: string, message: string): void => {
  runGit(root, ['add', '.'])
  const status = runGit(root, ['status', '--porcelain=v1', '--untracked-files=all'])
  if (status) runGit(root, ['commit', '-qm', message])
}

const cleanSnapshot = (root: string): void => {
  runGit(root, ['reset', '--hard', 'HEAD'])
  runGit(root, ['clean', '-fd'])
}

async function applyPlugin(
  ctx: Context,
  fibers: DisposableFiber[],
  plugin: unknown,
): Promise<void> {
  const fiber = await ctx.plugin(plugin as never, undefined as never)
  fibers.push(fiber)
  await tick()
}

const emptySection = (rationale: string) => ({
  scopeDecision: 'NONE' as const,
  rationale,
  candidates: [],
})

class MatrixModelClient implements GenericModelClient {
  readonly clientId = 'real-task-matrix-model'
  readonly calls: GenericModelGenerateRequest[] = []

  async generate(request: GenericModelGenerateRequest): Promise<GenericModelGenerateResponse> {
    this.calls.push(request)
    if (request.purpose === 'WORK') {
      const task = request.userText
        .split('BUSINESS TASK (verbatim):\n')[1]
        ?.split('\n\nKNOWLEDGE ENGAGEMENT DECISION:')[0]
        ?.trim() ?? 'governed task'
      return {
        contractVersion: GENERIC_MODEL_ADAPTER_CONTRACT_VERSION,
        requestId: request.requestId,
        outputText: `Completed governed work for: ${task}`,
        providerId: 'deterministic-matrix-provider',
        modelId: 'matrix-model-v0.1',
      }
    }

    const parsed = JSON.parse(request.userText) as {
      runtimeRequest: import('@agent-harness/governance-runtime').GovernanceSemanticRequest
    }
    const runtimeRequest = parsed.runtimeRequest
    const touchedRefs = unique(runtimeRequest.turnObservations.flatMap(item => item.refs))
    let knowledge: ReturnType<typeof emptySection> | {
      readonly scopeDecision: 'PROJECT'
      readonly rationale: string
      readonly candidates: readonly [{
        readonly domain: 'knowledge'
        readonly title: string
        readonly factOrProposal: string
        readonly scopeDecision: 'PROJECT'
        readonly rationale: string
        readonly provenanceRefs: readonly string[]
        readonly evidenceRefs: readonly string[]
        readonly relatedRefs: readonly string[]
        readonly confidence: number
      }]
    } = emptySection('No durable Knowledge change was produced by this Turn.')

    let knowledgeVerifications: Array<{
      knowledgeRef: string
      relation: 'SUPPORT' | 'CONTRADICT'
      basisRefs: string[]
      rationale: string
    }> = []
    if (runtimeRequest.turnId === 'CANDIDATE-SUPPORT' || runtimeRequest.turnId === 'CANDIDATE-CONTRADICT') {
      const observedRefs = unique(runtimeRequest.turnObservations.flatMap(item => item.refs))
      const knowledgeRef = observedRefs.find(item => item.startsWith('knowledge://'))
      const evidenceRef = observedRefs.find(item => item.startsWith('evidence://'))
      if (!knowledgeRef || !evidenceRef) {
        throw new Error(`Matrix Reflection missing candidate/evidence refs for ${runtimeRequest.turnId}`)
      }
      const relation = runtimeRequest.turnId === 'CANDIDATE-SUPPORT' ? 'SUPPORT' : 'CONTRADICT'
      knowledgeVerifications = [{
        knowledgeRef,
        relation,
        basisRefs: [evidenceRef],
        rationale: relation === 'SUPPORT'
          ? 'The real test supports the routed exploratory claim.'
          : 'The real test contradicts the routed claim and must block trusted use.',
      }]
    }

    if (runtimeRequest.turnId === 'KNOWLEDGE-1') {
      const source = runtimeRequest.knowledgeValidation.projectSources.find(
        item => item.title === 'Harness P0 P1 Efficiency Boundary',
      )
      const category = runtimeRequest.knowledgeClassification.projectCategories.find(
        item => item.categoryId === 'C070.040',
      )
      if (!source || !category) {
        throw new Error('Matrix Reflection could not resolve the registered Source/category.')
      }
      knowledge = {
        scopeDecision: 'PROJECT',
        rationale: 'The authoritative project handoff confirms a reusable ET-TOOL Harness policy.',
        candidates: [{
          domain: 'knowledge',
          title: 'High-risk tool errors trigger review without forced knowledge spam',
          factOrProposal:
            'In the ET-TOOL Harness P0/P1 baseline, a high-risk tool error triggers Knowledge CHECK and EVIDENCE_CHECK, but does not force a Knowledge Candidate unless a durable fact exists.',
          scopeDecision: 'PROJECT',
          rationale: 'This is a stable project governance boundary confirmed by the P0/P1 handoff.',
          provenanceRefs: [source.sourceRef],
          evidenceRefs: [],
          relatedRefs: [category.categoryRef],
          confidence: 1,
        }],
      }
    }

    return {
      contractVersion: GENERIC_MODEL_ADAPTER_CONTRACT_VERSION,
      requestId: request.requestId,
      outputJson: {
        contractVersion: '0.1',
        taskId: runtimeRequest.taskId,
        turnId: runtimeRequest.turnId,
        context: {
          progress: `Completed ${runtimeRequest.turnId}.`,
          decisions: [],
          confirmed: [],
          assumptions: [],
          openIssues: [],
          next: [],
          touchedRefs,
        },
        knowledge,
        knowledgeVerifications,
        experience: emptySection('No reusable Experience candidate was produced.'),
        architecture: emptySection('No Architecture change was proposed.'),
        rules: emptySection('No Rule change was proposed.'),
        evidence: emptySection('No new durable Evidence candidate was produced by Reflection.'),
        workingSet: {
          keep: touchedRefs.slice(0, 8),
          add: [],
          remove: [],
        },
        obligations: {
          opened: [],
          resolved: [],
          unchanged: [],
        },
      },
      providerId: 'deterministic-matrix-provider',
      modelId: 'matrix-model-v0.1',
    }
  }
}

async function setupEnvironment(runId: string): Promise<MatrixEnvironment> {
  const stateRoot = join(tmpdir(), 'et-tool-real-task-matrix-state', runId)
  process.env.AGENT_HARNESS_STATE_ROOT = stateRoot
  delete process.env.AGENT_HARNESS_GLOBAL_KNOWLEDGE_ROOT

  const ctx = new Context()
  const fibers: DisposableFiber[] = []
  await applyPlugin(ctx, fibers, GovernanceCatalogService)
  for (const plugin of [
    projectManagerPlugin,
    architecturePlugin,
    rulePlugin,
    evidencePlugin,
    knowledgePlugin,
    gatePlugin,
    contextPlugin,
    experiencePlugin,
    kernelPlugin,
    closurePlugin,
    enginePlugin,
    runtimePlugin,
  ]) await applyPlugin(ctx, fibers, plugin)

  const snapshot = createEtToolProjectSnapshot(resolve(process.cwd()))
  initializeSnapshotGit(snapshot.root)
  process.env.ET_TOOL_PROJECT_ROOT = snapshot.root
  await applyPlugin(ctx, fibers, etToolProjectPlugin)
  await applyPlugin(ctx, fibers, etToolReviewPlugin)

  const runtime = ctx.get('governanceRuntime') as
    import('@agent-harness/governance-runtime').GovernanceRuntimeService | undefined
  const knowledge = ctx.get('knowledgeManager') as
    import('@agent-harness/knowledge-manager').KnowledgeManagerService | undefined
  const evidence = ctx.get('evidenceStateManager') as
    import('@agent-harness/evidence-state-manager').EvidenceStateManagerService | undefined
  const contextManager = ctx.get('contextManager') as MatrixEnvironment['contextManager'] | undefined
  if (!runtime || !knowledge || !evidence || !contextManager) {
    throw new Error('Matrix setup could not resolve required Governance services.')
  }

  return {
    ctx,
    fibers,
    snapshot,
    runtime,
    knowledge,
    evidence,
    contextManager,
    model: new MatrixModelClient(),
  }
}

async function disposeEnvironment(environment: MatrixEnvironment): Promise<void> {
  for (const fiber of environment.fibers.reverse()) await fiber.dispose()
  environment.snapshot.dispose()
  const stateRoot = process.env.AGENT_HARNESS_STATE_ROOT
  if (stateRoot) rmSync(stateRoot, { recursive: true, force: true })
}

async function runReadOnlyAndContextReuse(
  environment: MatrixEnvironment,
  runId: string,
): Promise<ScenarioResult> {
  const { runtime, knowledge, model, snapshot, contextManager } = environment
  const driver = new GenericModelPilotDriver(runtime, model)
  const runtimeId = `${runId}-read-only`
  const actorId = `${runId}-read-agent`
  const beforeCount = allKnowledgeIds(knowledge.getIndex('et-tool')).length

  const turn1 = await driver.runTurn({
    runtimeId,
    turnId: 'READ-1',
    taskText:
      'Review the ET-TOOL J-Link connection cleanup boundary and summarize the relevant architecture and rules without modifying code.',
    projectId: 'et-tool',
    workspacePath: snapshot.root,
    actorId,
  })
  const frame1 = contextManager.buildFrame('et-tool', turn1.open.taskId)

  const turn2 = await driver.runTurn({
    runtimeId,
    turnId: 'READ-2',
    taskText:
      'Continue the same analysis: explain why host resource cleanup and target MCU recovery must remain separate.',
    projectId: 'et-tool',
    workspacePath: snapshot.root,
    actorId,
  })
  const frame2 = contextManager.buildFrame('et-tool', turn2.open.taskId)
  const completion = runtime.completeTask(runtimeId)
  const afterCount = allKnowledgeIds(knowledge.getIndex('et-tool')).length

  return {
    assertions: {
      readOnlyProjectResolved: turn1.open.projectId === 'et-tool',
      readOnlyArchitectureRouted: turn1.open.context.route.architectureIds.length > 0,
      readOnlyRulesRouted: turn1.open.context.route.ruleIds.length > 0,
      readOnlyTurn1Closed: turn1.close.closure.status === 'COMPLETE',
      readOnlyTurn2Closed: turn2.close.closure.status === 'COMPLETE',
      readOnlyTaskReused: turn1.open.taskId === turn2.open.taskId,
      readOnlyContextAdvanced:
        frame1.stateVersion > turn1.open.context.stateVersion
        && frame2.stateVersion >= turn2.open.context.stateVersion,
      readOnlyNoKnowledgeSpam: beforeCount === afterCount,
      readOnlyTaskCompleted: completion.status === 'COMPLETED',
    },
    diagnostics: {
      taskId: turn1.open.taskId,
      turn1Route: turn1.open.context.route,
      turn2Route: turn2.open.context.route,
      stateVersions: {
        turn1Open: turn1.open.context.stateVersion,
        afterTurn1: frame1.stateVersion,
        turn2Open: turn2.open.context.stateVersion,
        afterTurn2: frame2.stateVersion,
      },
      completion,
    },
  }
}

async function runKnowledgeCaptureAndReuse(
  environment: MatrixEnvironment,
  runId: string,
): Promise<ScenarioResult> {
  const { runtime, knowledge, model, snapshot } = environment
  const source = knowledge.registerProjectSource('et-tool', {
    kind: 'DOCUMENT',
    title: 'Harness P0 P1 Efficiency Boundary',
    location: 'agent_harness/progress_context/20260826_P0_P1_HARDENING.md',
    revision: runId,
    note: 'Authoritative project handoff used by the real-task matrix.',
  })
  const beforeIds = new Set(allKnowledgeIds(knowledge.getIndex('et-tool')))
  const driver = new GenericModelPilotDriver(runtime, model)
  const runtimeId = `${runId}-knowledge`
  const actorId = `${runId}-knowledge-agent`

  const turn1 = await driver.runTurn({
    runtimeId,
    turnId: 'KNOWLEDGE-1',
    taskText:
      'Read the P0/P1 handoff and preserve the stable policy for high-risk tool errors without forcing unnecessary knowledge candidates.',
    projectId: 'et-tool',
    workspacePath: snapshot.root,
    actorId,
    additionalToolResults: [{
      name: 'document-consult',
      summary:
        'The P0/P1 handoff says high-risk tool errors trigger CHECK plus EVIDENCE_CHECK, while routine errors must not force junk Knowledge candidates.',
      resourceRefs: [source.sourceUri],
    }],
  })

  const afterTurn1Index = knowledge.getIndex('et-tool')
  const newIds = allKnowledgeIds(afterTurn1Index).filter(id => !beforeIds.has(id))
  const learned = newIds
    .map(id => knowledge.getNode('et-tool', id)?.node)
    .find(node => node?.isLeaf && node.status !== 'DEPRECATED')

  const turn2 = await driver.runTurn({
    runtimeId,
    turnId: 'KNOWLEDGE-2',
    taskText:
      'According to ET-TOOL Harness knowledge, must every high-risk tool error create a Knowledge Candidate?',
    projectId: 'et-tool',
    workspacePath: snapshot.root,
    actorId,
  })
  const completion = runtime.completeTask(runtimeId)
  commitSnapshot(snapshot.root, 'matrix knowledge baseline')

  return {
    assertions: {
      knowledgeTurn1Closed: turn1.close.closure.status === 'COMPLETE',
      knowledgeCandidateCreated: !!learned,
      knowledgeCandidateProjectScoped: learned?.category === 'C070.040',
      knowledgeCandidateDocumentValidated: learned?.status === 'VALIDATED',
      knowledgeCandidatePromotedByRuntime:
        turn1.close.knowledgePromotions.some(item => item.knowledgeUri.endsWith(`/${learned?.id ?? ''}`)),
      learnedKnowledgeReused:
        !!learned && turn2.open.context.route.knowledgeIds.includes(learned.id),
      knowledgeTurn2Closed: turn2.close.closure.status === 'COMPLETE',
      knowledgeTaskCompleted: completion.status === 'COMPLETED',
    },
    diagnostics: {
      sourceUri: source.sourceUri,
      candidateId: learned?.id,
      candidateStatus: learned?.status,
      promotions: turn1.close.knowledgePromotions,
      promotionWarnings: turn1.close.knowledgePromotionWarnings,
      turn2KnowledgeRoute: turn2.open.context.route.knowledgeIds,
      completion,
    },
  }
}

async function passCurrentReviews(
  runtime: import('@agent-harness/governance-runtime').GovernanceRuntimeService,
  runtimeId: string,
  reviews: readonly import('@agent-harness/auto-governance-engine').AutoGovernancePendingReview[],
): Promise<{
  readonly passWithBlockingFindingRejected: boolean
  readonly decisions: readonly import('@agent-harness/auto-governance-engine').AutoGovernanceReviewDecisionResult[]
}> {
  let passWithBlockingFindingRejected = false
  const first = reviews[0]
  if (first) {
    try {
      runtime.recordReviewDecision({
        runtimeId,
        packetId: first.packetId,
        result: 'PASS',
        summary: 'Invalid PASS attempt with a blocking finding.',
        reviewerId: 'matrix-reviewer',
        findings: [{
          severity: 'BLOCK',
          summary: 'Synthetic blocking finding.',
        }],
      })
    } catch {
      passWithBlockingFindingRejected = true
    }
  }

  const decisions = reviews.map(review => runtime.recordReviewDecision({
    runtimeId,
    packetId: review.packetId,
    result: 'PASS',
    summary: `Matrix review PASS for ${review.capability}.`,
    reviewerId: 'matrix-reviewer',
    findings: [],
  }))
  return { passWithBlockingFindingRejected, decisions }
}

async function runMutationReviewAndRelease(
  environment: MatrixEnvironment,
  runId: string,
): Promise<ScenarioResult> {
  const { runtime, model, snapshot } = environment
  const runtimeId = `${runId}-mutation`
  const actorId = `${runId}-mutation-agent`
  const semanticExecutor = createGovernanceSemanticExecutor(model)
  const open = await runtime.openTurn({
    runtimeId,
    turnId: 'MUTATION-1',
    taskText:
      'Make a small ET-TOOL GUI implementation change, complete all Code Gate reviews, then use the formal Release entry.',
    projectId: 'et-tool',
    workspacePath: snapshot.root,
    actorId,
    semanticExecutor,
  })

  let shellExecutions = 0
  let writeExecutions = 0
  const gateway = runtimePlugin.createGovernedToolGateway(runtime, [{
    name: 'write_file',
    execute: invocation => {
      const args = invocation.arguments as { path?: string; content?: string } | undefined
      const relative = args?.path?.trim() || 'source/apps/gui/matrix_probe.cpp'
      const absolute = join(snapshot.root, relative)
      mkdirSync(resolve(absolute, '..'), { recursive: true })
      writeFileSync(absolute, args?.content ?? '// matrix probe\n', 'utf8')
      writeExecutions += 1
      return {
        value: relative,
        summary: `Wrote ${relative}.`,
        resourceRefs: [`file://${relative}`],
      }
    },
  }, {
    name: 'shell',
    execute: invocation => {
      shellExecutions += 1
      return {
        value: invocation.arguments,
        summary: 'Formal Release entry accepted by the governed executor.',
      }
    },
  }])

  const firstWrite = await gateway.execute<string>({
    runtimeId,
    turnId: 'MUTATION-1',
    name: 'write_file',
    arguments: {
      path: 'source/apps/gui/matrix_probe.cpp',
      content: 'int matrix_probe_value() { return 1; }\n',
    },
  })
  const firstReviews = firstWrite.status === 'EXECUTED'
    ? firstWrite.observation.context.pendingReviews
    : []
  const buildBeforeReview = await gateway.execute({
    runtimeId,
    turnId: 'MUTATION-1',
    name: 'shell',
    arguments: { command: 'source/release/release_gui.bat --mode dev' },
  })
  const firstReviewOutcome = await passCurrentReviews(runtime, runtimeId, firstReviews)
  const firstBuildAfterReview = await gateway.execute({
    runtimeId,
    turnId: 'MUTATION-1',
    name: 'shell',
    arguments: { command: 'source/release/release_gui.bat --mode dev' },
  })

  const secondWrite = await gateway.execute<string>({
    runtimeId,
    turnId: 'MUTATION-1',
    name: 'write_file',
    arguments: {
      path: 'source/apps/gui/matrix_probe.cpp',
      content: 'int matrix_probe_value() { return 2; }\n',
    },
  })
  const secondReviews = secondWrite.status === 'EXECUTED'
    ? secondWrite.observation.context.pendingReviews
    : []
  const secondBuildBeforeReview = await gateway.execute({
    runtimeId,
    turnId: 'MUTATION-1',
    name: 'shell',
    arguments: { command: 'source/release/release_gui.bat --mode dev' },
  })
  const secondReviewOutcome = await passCurrentReviews(runtime, runtimeId, secondReviews)
  const secondBuildAfterReview = await gateway.execute({
    runtimeId,
    turnId: 'MUTATION-1',
    name: 'shell',
    arguments: { command: 'source/release/release_gui.bat --mode dev' },
  })

  runtime.observeWork({
    kind: 'assistant-message',
    runtimeId,
    turnId: 'MUTATION-1',
    messageRefs: [`model-output://${runtimeId}/MUTATION-1`],
    text: 'Implemented the small GUI change, completed current reviews, and used the formal Release entry.',
  })
  const close = await runtime.closeTurn({
    runtimeId,
    turnId: 'MUTATION-1',
  })
  const completion = runtime.completeTask(runtimeId)
  commitSnapshot(snapshot.root, 'matrix accepted mutation')

  return {
    assertions: {
      mutationWriteExecuted: firstWrite.status === 'EXECUTED' && writeExecutions >= 1,
      mutationReviewsPrepared: firstReviews.length > 0,
      mutationBuildBlockedBeforeReview:
        buildBeforeReview.status === 'BLOCKED' && !buildBeforeReview.executorCalled,
      passCannotHideBlockingFinding: firstReviewOutcome.passWithBlockingFindingRejected,
      mutationAllFirstReviewsPassed:
        firstReviewOutcome.decisions.length === firstReviews.length
        && firstReviewOutcome.decisions.every(item => item.result === 'PASS'),
      mutationBuildAllowedAfterReview: firstBuildAfterReview.status === 'EXECUTED',
      secondMutationCreatedNewReviewEpoch:
        secondReviews.length > 0
        && secondReviews.every(item => item.epoch > (firstReviews[0]?.epoch ?? 0)),
      staleReviewEvidenceCannotAuthorizeNextChange: secondBuildBeforeReview.status === 'BLOCKED',
      mutationAllSecondReviewsPassed:
        secondReviewOutcome.decisions.length === secondReviews.length
        && secondReviewOutcome.decisions.every(item => item.result === 'PASS'),
      secondBuildAllowedAfterCurrentReview: secondBuildAfterReview.status === 'EXECUTED',
      mutationTurnClosed: close.closure.status === 'COMPLETE',
      mutationTaskCompleted: completion.status === 'COMPLETED',
    },
    diagnostics: {
      taskId: open.taskId,
      firstReviewCount: firstReviews.length,
      firstReviewEpoch: firstReviews[0]?.epoch,
      secondReviewCount: secondReviews.length,
      secondReviewEpoch: secondReviews[0]?.epoch,
      firstWriteStatus: firstWrite.status,
      secondWriteStatus: secondWrite.status,
      secondWriteError: secondWrite.status === 'ERROR' ? secondWrite.error : undefined,
      buildBeforeReview: { status: buildBeforeReview.status, reason: buildBeforeReview.preflight.reason },
      firstBuildAfterReview: { status: firstBuildAfterReview.status, reason: firstBuildAfterReview.preflight.reason },
      secondBuildBeforeReview: { status: secondBuildBeforeReview.status, reason: secondBuildBeforeReview.preflight.reason },
      secondBuildAfterReview: { status: secondBuildAfterReview.status, reason: secondBuildAfterReview.preflight.reason },
      shellExecutions,
      writeExecutions,
      completion,
    },
  }
}

async function closeNoCandidateTurn(
  runtime: import('@agent-harness/governance-runtime').GovernanceRuntimeService,
  runtimeId: string,
  turnId: string,
  model: MatrixModelClient,
): Promise<void> {
  runtime.observeWork({
    kind: 'assistant-message',
    runtimeId,
    turnId,
    messageRefs: [`model-output://${runtimeId}/${turnId}`],
    text: 'Completed matrix validation step.',
  })
  await runtime.closeTurn({
    runtimeId,
    turnId,
    semanticExecutor: createGovernanceSemanticExecutor(model),
  })
}

async function runBuildAndMutationBypassMatrix(
  environment: MatrixEnvironment,
  runId: string,
): Promise<ScenarioResult> {
  const { runtime, model, snapshot } = environment
  cleanSnapshot(snapshot.root)

  const commandRuntimeId = `${runId}-command-matrix`
  await runtime.openTurn({
    runtimeId: commandRuntimeId,
    turnId: 'COMMAND-1',
    taskText: 'Validate all ET-TOOL product build entry variants.',
    projectId: 'et-tool',
    workspacePath: snapshot.root,
    actorId: `${runId}-command-agent`,
    semanticExecutor: createGovernanceSemanticExecutor(model),
  })

  const commandCases = {
    canonicalRelease: 'source/release/release_gui.bat --mode dev',
    canonicalWindowsSeparators: 'source\\release\\release_gui.bat --mode dev',
    directCmake: 'cmake -S . -B build',
    directCmakeExe: '"C:\\Program Files\\CMake\\bin\\cmake.exe" --build build',
    directNinjaExe: 'ninja.exe -C build',
    powershellWrappedCmake: '& cmake --build build',
    chainedReleaseAndCmake:
      'source/release/release_gui.bat --mode dev && cmake --build build',
    fakeReleaseSuffix: 'source/release/release_gui.bat.exe --mode dev',
    traversedReleasePath: '../evil/source/release/release_gui.bat --mode dev',
    prefixedReleasePath: 'tools/source/release/release_gui.bat --mode dev',
    msbuildDirect: 'msbuild ET-TOOL.sln /m',
    devenvDirect: 'devenv ET-TOOL.sln /Build Release',
    nmakeDirect: 'nmake /f Makefile',
  } as const
  const commandResults = Object.fromEntries(
    Object.entries(commandCases).map(([name, command]) => [
      name,
      runtime.preflightAction({
        runtimeId: commandRuntimeId,
        turnId: 'COMMAND-1',
        name: 'shell',
        arguments: { command },
      }),
    ]),
  ) as Record<keyof typeof commandCases, import('@agent-harness/governance-runtime').GovernanceActionPreflightResult>
  await closeNoCandidateTurn(runtime, commandRuntimeId, 'COMMAND-1', model)

  const runMutationToolCase = async (input: {
    readonly suffix: string
    readonly toolName: string
    readonly arguments: unknown
    readonly file: string
    readonly throwAfterWrite?: boolean
  }) => {
    cleanSnapshot(snapshot.root)
    const runtimeId = `${runId}-${input.suffix}`
    await runtime.openTurn({
      runtimeId,
      turnId: `${input.suffix}-1`,
      taskText: `Validate mutation detection for ${input.toolName}.`,
      projectId: 'et-tool',
      workspacePath: snapshot.root,
      actorId: `${runId}-${input.suffix}-agent`,
      semanticExecutor: createGovernanceSemanticExecutor(model),
    })
    const gateway = runtimePlugin.createGovernedToolGateway(runtime, [{
      name: input.toolName,
      execute: () => {
        const absolute = join(snapshot.root, input.file)
        mkdirSync(resolve(absolute, '..'), { recursive: true })
        writeFileSync(absolute, `// ${input.suffix}\n`, 'utf8')
        if (input.throwAfterWrite) throw new Error(`${input.toolName} failed after a partial write`)
        return {
          value: input.file,
          summary: `${input.toolName} changed ${input.file}.`,
          resourceRefs: [`file://${input.file}`],
        }
      },
    }])
    const execution = await gateway.execute({
      runtimeId,
      turnId: `${input.suffix}-1`,
      name: input.toolName,
      arguments: input.arguments,
    })
    const status = runtime.getStatus(runtimeId)
    const release = runtime.preflightAction({
      runtimeId,
      turnId: `${input.suffix}-1`,
      name: 'shell',
      arguments: { command: 'source/release/release_gui.bat --mode dev' },
    })
    await closeNoCandidateTurn(runtime, runtimeId, `${input.suffix}-1`, model)
    return {
      execution,
      codeChangeSeen: status?.autoGovernance.codeChangeSeen === true,
      pendingReviewCount: status?.autoGovernance.pendingReviews.length ?? 0,
      release,
    }
  }

  const pythonMutation = await runMutationToolCase({
    suffix: 'PYTHON-MUTATION',
    toolName: 'python',
    arguments: {
      code:
        "from pathlib import Path; Path('source/apps/gui/python_probe.cpp').write_text('// changed')",
    },
    file: 'source/apps/gui/python_probe.cpp',
  })
  const githubUpdateMutation = await runMutationToolCase({
    suffix: 'GITHUB-UPDATE',
    toolName: 'GitHub.update_file',
    arguments: {
      path: 'source/apps/gui/github_update_probe.cpp',
      content: '// changed',
    },
    file: 'source/apps/gui/github_update_probe.cpp',
  })
  const partialFailureMutation = await runMutationToolCase({
    suffix: 'PARTIAL-FAILURE',
    toolName: 'write_file',
    arguments: {
      path: 'source/apps/gui/partial_failure_probe.cpp',
      content: '// partial',
    },
    file: 'source/apps/gui/partial_failure_probe.cpp',
    throwAfterWrite: true,
  })

  return {
    assertions: {
      canonicalReleaseAllowed: commandResults.canonicalRelease.allowed,
      canonicalWindowsReleaseAllowed: commandResults.canonicalWindowsSeparators.allowed,
      directCmakeBlocked: !commandResults.directCmake.allowed,
      directCmakeExeBlocked: !commandResults.directCmakeExe.allowed,
      directNinjaExeBlocked: !commandResults.directNinjaExe.allowed,
      powershellWrappedCmakeBlocked: !commandResults.powershellWrappedCmake.allowed,
      chainedReleaseAndCmakeBlocked: !commandResults.chainedReleaseAndCmake.allowed,
      fakeReleaseSuffixBlocked: !commandResults.fakeReleaseSuffix.allowed,
      traversedReleasePathBlocked: !commandResults.traversedReleasePath.allowed,
      prefixedReleasePathBlocked: !commandResults.prefixedReleasePath.allowed,
      msbuildBlocked: !commandResults.msbuildDirect.allowed,
      devenvBlocked: !commandResults.devenvDirect.allowed,
      nmakeBlocked: !commandResults.nmakeDirect.allowed,
      pythonMutationDetected:
        pythonMutation.execution.status === 'EXECUTED'
        && pythonMutation.codeChangeSeen
        && pythonMutation.pendingReviewCount > 0
        && !pythonMutation.release.allowed,
      githubUpdateMutationDetected:
        githubUpdateMutation.execution.status === 'EXECUTED'
        && githubUpdateMutation.codeChangeSeen
        && githubUpdateMutation.pendingReviewCount > 0
        && !githubUpdateMutation.release.allowed,
      partialFailedMutationDetected:
        partialFailureMutation.execution.status === 'ERROR'
        && partialFailureMutation.codeChangeSeen
        && !partialFailureMutation.release.allowed,
    },
    diagnostics: {
      commandResults,
      pythonMutation,
      githubUpdateMutation,
      partialFailureMutation,
    },
  }
}

async function runRuntimeBoundaryMatrix(
  environment: MatrixEnvironment,
  runId: string,
): Promise<ScenarioResult> {
  const { runtime, model, knowledge, snapshot } = environment
  cleanSnapshot(snapshot.root)

  const runtimeA = `${runId}-isolation-a`
  const runtimeB = `${runId}-isolation-b`
  await runtime.openTurn({
    runtimeId: runtimeA,
    turnId: 'ISO-A-1',
    taskText: 'Modify one isolated GUI file.',
    projectId: 'et-tool',
    workspacePath: snapshot.root,
    actorId: `${runId}-isolation-agent-a`,
    semanticExecutor: createGovernanceSemanticExecutor(model),
  })
  await runtime.openTurn({
    runtimeId: runtimeB,
    turnId: 'ISO-B-1',
    taskText: 'Perform a read-only ET-TOOL analysis.',
    projectId: 'et-tool',
    workspacePath: snapshot.root,
    actorId: `${runId}-isolation-agent-b`,
    semanticExecutor: createGovernanceSemanticExecutor(model),
  })

  runtime.observeWork({
    kind: 'tool-result',
    runtimeId: runtimeA,
    turnId: 'ISO-A-1',
    name: 'write_file',
    arguments: { path: 'source/apps/gui/isolation_a.cpp' },
    summary: 'Runtime A changed code.',
    resourceRefs: ['file://source/apps/gui/isolation_a.cpp'],
    isError: false,
  })
  const aRelease = runtime.preflightAction({
    runtimeId: runtimeA,
    turnId: 'ISO-A-1',
    name: 'shell',
    arguments: { command: 'source/release/release_gui.bat --mode dev' },
  })
  const bRelease = runtime.preflightAction({
    runtimeId: runtimeB,
    turnId: 'ISO-B-1',
    name: 'shell',
    arguments: { command: 'source/release/release_gui.bat --mode dev' },
  })
  const completionWhileOpen = runtime.completeTask(runtimeB)

  let wrongTurnRejected = false
  try {
    runtime.preflightAction({
      runtimeId: runtimeB,
      turnId: 'WRONG-TURN',
      name: 'read_file',
      arguments: { path: 'README.md' },
    })
  } catch {
    wrongTurnRejected = true
  }

  await closeNoCandidateTurn(runtime, runtimeA, 'ISO-A-1', model)
  await closeNoCandidateTurn(runtime, runtimeB, 'ISO-B-1', model)

  let observationAfterCloseRejected = false
  try {
    runtime.observeWork({
      kind: 'assistant-message',
      runtimeId: runtimeB,
      turnId: 'ISO-B-1',
      messageRefs: ['model-output://late'],
      text: 'late output',
    })
  } catch {
    observationAfterCloseRejected = true
  }
  const bCompletion = runtime.completeTask(runtimeB)

  const beforeKnowledgeCount = allKnowledgeIds(knowledge.getIndex('et-tool')).length
  const errorDriver = new GenericModelPilotDriver(runtime, model)
  const errorTurn = await errorDriver.runTurn({
    runtimeId: `${runId}-tool-error`,
    turnId: 'TOOL-ERROR-1',
    taskText: 'Inspect a failing hardware probe and report the failure without inventing durable knowledge.',
    projectId: 'et-tool',
    workspacePath: snapshot.root,
    actorId: `${runId}-tool-error-agent`,
    additionalToolResults: [{
      name: 'hardware_probe',
      summary: 'Probe connection failed before any hardware observation was produced.',
      resourceRefs: ['tool-event://matrix/hardware-probe-failure'],
      isError: true,
    }],
  })
  const afterKnowledgeCount = allKnowledgeIds(knowledge.getIndex('et-tool')).length
  const errorCompletion = runtime.completeTask(`${runId}-tool-error`)

  const invalidRuntimeId = `${runId}-invalid-category`
  const invalidExecutor: import('@agent-harness/governance-runtime').GovernanceSemanticExecutor = {
    executorId: 'matrix-invalid-category-executor',
    reflect: request => ({
      contractVersion: '0.1',
      taskId: request.taskId,
      turnId: request.turnId,
      context: {
        progress: 'Attempted invalid category persistence.',
        decisions: [],
        confirmed: [],
        assumptions: [],
        openIssues: [],
        next: [],
        touchedRefs: [],
      },
      knowledge: {
        scopeDecision: 'PROJECT',
        rationale: 'Negative test.',
        candidates: [{
          domain: 'knowledge',
          title: 'Invalid category candidate',
          factOrProposal: 'This candidate must not enter canonical Knowledge.',
          scopeDecision: 'PROJECT',
          rationale: 'Negative test.',
          provenanceRefs: [],
          evidenceRefs: [],
          relatedRefs: ['knowledge-category://project/C999.999'],
          confidence: 1,
        }],
      },
      experience: emptySection('None.'),
      architecture: emptySection('None.'),
      rules: emptySection('None.'),
      evidence: emptySection('None.'),
      workingSet: { keep: [], add: [], remove: [] },
      obligations: { opened: [], resolved: [], unchanged: [] },
    }),
  }
  await runtime.openTurn({
    runtimeId: invalidRuntimeId,
    turnId: 'INVALID-CATEGORY-1',
    taskText: 'Attempt to persist Knowledge into a nonexistent project category.',
    projectId: 'et-tool',
    workspacePath: snapshot.root,
    actorId: `${runId}-invalid-category-agent`,
    semanticExecutor: invalidExecutor,
  })
  runtime.observeWork({
    kind: 'assistant-message',
    runtimeId: invalidRuntimeId,
    turnId: 'INVALID-CATEGORY-1',
    messageRefs: ['model-output://invalid-category'],
    text: 'Attempting invalid category persistence.',
  })
  let invalidCategoryRejected = false
  let invalidClosureStatus: string | undefined
  try {
    const close = await runtime.closeTurn({
      runtimeId: invalidRuntimeId,
      turnId: 'INVALID-CATEGORY-1',
    })
    invalidClosureStatus = close.closure.status
    invalidCategoryRejected = close.closure.status !== 'COMPLETE'
  } catch {
    invalidCategoryRejected = true
  }
  const invalidCompletion = runtime.completeTask(invalidRuntimeId)

  return {
    assertions: {
      distinctRuntimesIsolated: !aRelease.allowed && bRelease.allowed,
      activeTurnBlocksCompletion: completionWhileOpen.status === 'BLOCKED',
      wrongTurnRejected,
      observationAfterCloseRejected,
      readOnlyRuntimeCompletes: bCompletion.status === 'COMPLETED',
      toolErrorTurnClosed: errorTurn.close.closure.status === 'COMPLETE',
      toolErrorDoesNotCreateJunkKnowledge: beforeKnowledgeCount === afterKnowledgeCount,
      invalidKnowledgeCategoryFailsClosed:
        invalidCategoryRejected && invalidCompletion.status === 'BLOCKED',
    },
    diagnostics: {
      aRelease,
      bRelease,
      completionWhileOpen,
      bCompletion,
      toolErrorKnowledgeDecision: errorTurn.close.knowledgeDecision,
      toolErrorCompletion: errorCompletion,
      invalidClosureStatus,
      invalidCompletion,
    },
  }
}


async function runTieredKnowledgeFeedback(
  environment: MatrixEnvironment,
  runId: string,
): Promise<ScenarioResult> {
  const { runtime, knowledge, evidence, model, snapshot } = environment
  const mutation = knowledge.submitKnowledgeCandidate('et-tool', {
    categoryId: 'C070.040',
    title: `Candidate Probe Sentinel ${runId}`,
    fact: `Candidate Probe Sentinel ${runId}: a governed real test can validate or contradict an exploratory Knowledge claim.`,
    provenance: `matrix://${runId}/candidate-feedback`,
    scope: 'agent-harness candidate feedback loop',
    tags: ['candidate-probe-sentinel', 'knowledge-feedback'],
    refs: [],
  })
  const knowledgeUri = `knowledge://project/et-tool/${mutation.knowledgeId}`
  const runtimeId = `${runId}-tiered-knowledge`
  const actorId = `${runId}-tiered-knowledge-agent`
  const semanticExecutor = createGovernanceSemanticExecutor(model)

  const supportOpen = await runtime.openTurn({
    runtimeId,
    turnId: 'CANDIDATE-SUPPORT',
    taskText: `Test Candidate Probe Sentinel ${runId} and use it only as an exploratory hypothesis until Evidence exists.`,
    projectId: 'et-tool',
    workspacePath: snapshot.root,
    actorId,
    semanticExecutor,
  })
  const candidateRouted = supportOpen.context.route.knowledgeIds.some(
    reference => reference === mutation.knowledgeId || reference.endsWith(`/${mutation.knowledgeId}`),
  )
  const exploratoryMarked = supportOpen.context.text.includes(`knowledge://project/et-tool/${mutation.knowledgeId}`)
    && supportOpen.context.text.includes('TrustTier: EXPLORATORY')
    && supportOpen.context.text.includes('Hypothesis, investigation lead, or test target only.')
  const supportEvidence = evidence.recordEvidence({
    projectId: 'et-tool',
    taskId: supportOpen.taskId,
    kind: 'test',
    result: 'PASS',
    summary: 'The candidate feedback real-test scenario passed.',
    source: 'real-task-matrix',
    metadata: { knowledgeValidationClass: 'REAL_TEST' },
  })
  const supportEvidenceUri = `evidence://project/et-tool/${supportEvidence.evidenceId}`
  runtime.observeWork({
    kind: 'tool-result',
    runtimeId,
    turnId: 'CANDIDATE-SUPPORT',
    name: 'candidate-real-test',
    summary: 'A real test produced SUPPORT evidence for the exploratory Knowledge item.',
    resourceRefs: [knowledgeUri, supportEvidenceUri],
  })
  runtime.observeWork({
    kind: 'assistant-message',
    runtimeId,
    turnId: 'CANDIDATE-SUPPORT',
    messageRefs: [`model-output://${runtimeId}/CANDIDATE-SUPPORT`],
    text: 'The candidate was treated as a hypothesis and tested before trusted use.',
  })
  const supportClose = await runtime.closeTurn({ runtimeId, turnId: 'CANDIDATE-SUPPORT' })
  const afterSupport = knowledge.resolveKnowledgeReference(knowledgeUri, 'et-tool')?.result.node

  const contradictOpen = await runtime.openTurn({
    runtimeId,
    turnId: 'CANDIDATE-CONTRADICT',
    taskText: `Re-test Candidate Probe Sentinel ${runId}; record contradictory evidence instead of silently trusting it.`,
    projectId: 'et-tool',
    workspacePath: snapshot.root,
    actorId,
    semanticExecutor,
  })
  const contradictEvidence = evidence.recordEvidence({
    projectId: 'et-tool',
    taskId: contradictOpen.taskId,
    kind: 'test',
    result: 'PASS',
    summary: 'The negative real-test scenario passed and disproved the current claim.',
    source: 'real-task-matrix',
    metadata: { knowledgeValidationClass: 'REAL_TEST' },
  })
  const contradictEvidenceUri = `evidence://project/et-tool/${contradictEvidence.evidenceId}`
  runtime.observeWork({
    kind: 'tool-result',
    runtimeId,
    turnId: 'CANDIDATE-CONTRADICT',
    name: 'candidate-negative-real-test',
    summary: 'A real test produced CONTRADICT evidence for the routed Knowledge item.',
    resourceRefs: [knowledgeUri, contradictEvidenceUri],
  })
  runtime.observeWork({
    kind: 'assistant-message',
    runtimeId,
    turnId: 'CANDIDATE-CONTRADICT',
    messageRefs: [`model-output://${runtimeId}/CANDIDATE-CONTRADICT`],
    text: 'The contradictory result was attached to the existing K-ID.',
  })
  const contradictClose = await runtime.closeTurn({ runtimeId, turnId: 'CANDIDATE-CONTRADICT' })
  const evaluationAfterContradict = (environment.ctx.get('knowledgeValidationPolicy') as {
    evaluate(reference: string, currentProjectId?: string): { decision: string; contradictCount: number }
  }).evaluate(knowledgeUri, 'et-tool')

  const disputedOpen = await runtime.openTurn({
    runtimeId,
    turnId: 'CANDIDATE-DISPUTED',
    taskText: `Review Candidate Probe Sentinel ${runId} after contradictory verification.`,
    projectId: 'et-tool',
    workspacePath: snapshot.root,
    actorId,
    semanticExecutor,
  })
  const disputedMarked = disputedOpen.context.text.includes(knowledgeUri)
    && disputedOpen.context.text.includes('TrustTier: DISPUTED')
    && disputedOpen.context.text.includes('validation=BLOCKED')
  await closeNoCandidateTurn(runtime, runtimeId, 'CANDIDATE-DISPUTED', model)
  const completion = runtime.completeTask(runtimeId)
  commitSnapshot(snapshot.root, 'matrix tiered knowledge feedback baseline')

  return {
    assertions: {
      candidateAutomaticallyRouted: candidateRouted,
      candidateClearlyMarkedExploratory: exploratoryMarked,
      supportVerificationApplied:
        supportClose.knowledgeVerifications.some(item =>
          item.knowledgeUri === knowledgeUri && item.relation === 'SUPPORT'),
      supportEvidencePromotedCandidate: afterSupport?.status === 'FULL_VALIDATED',
      contradictionVerificationApplied:
        contradictClose.knowledgeVerifications.some(item =>
          item.knowledgeUri === knowledgeUri && item.relation === 'CONTRADICT'),
      contradictionBlocksTrustedUse:
        evaluationAfterContradict.decision === 'BLOCKED'
        && evaluationAfterContradict.contradictCount > 0,
      disputedKnowledgeRemainsVisibleWithWarning: disputedMarked,
      tieredKnowledgeTaskCompleted: completion.status === 'COMPLETED',
    },
    diagnostics: {
      knowledgeUri,
      supportRoute: supportOpen.context.route.knowledgeIds,
      supportVerifications: supportClose.knowledgeVerifications,
      supportPromotions: supportClose.knowledgePromotions,
      afterSupportStatus: afterSupport?.status,
      contradictionVerifications: contradictClose.knowledgeVerifications,
      evaluationAfterContradict,
      disputedRoute: disputedOpen.context.route.knowledgeIds,
      completion,
    },
  }
}

async function main(): Promise<number> {
  const iteration = process.env.REAL_TASK_MATRIX_ITERATION?.trim() || '1'
  const runId = `REAL-MATRIX-${iteration}-${randomUUID().slice(0, 8)}`
  const environment = await setupEnvironment(runId)

  try {
    const scenarios = {
      readOnlyAndContextReuse: await runReadOnlyAndContextReuse(environment, runId),
      knowledgeCaptureAndReuse: await runKnowledgeCaptureAndReuse(environment, runId),
      tieredKnowledgeFeedback: await runTieredKnowledgeFeedback(environment, runId),
      mutationReviewAndRelease: await runMutationReviewAndRelease(environment, runId),
      buildAndMutationBypassMatrix: await runBuildAndMutationBypassMatrix(environment, runId),
      runtimeBoundaryMatrix: await runRuntimeBoundaryMatrix(environment, runId),
    }

    const assertions = Object.fromEntries(
      Object.entries(scenarios).flatMap(([scenario, result]) =>
        Object.entries(result.assertions).map(([name, passed]) => [`${scenario}.${name}`, passed]),
      ),
    )
    const failed = Object.entries(assertions)
      .filter(([, passed]) => !passed)
      .map(([name]) => name)
    const report = {
      runId,
      iteration,
      assertionCount: Object.keys(assertions).length,
      assertions,
      failed,
      scenarios,
      modelCalls: environment.model.calls.map(item => ({
        requestId: item.requestId,
        purpose: item.purpose,
      })),
    }

    const reportDir = resolve(process.env.REAL_TASK_MATRIX_REPORT_DIR?.trim() || tmpdir())
    mkdirSync(reportDir, { recursive: true })
    const reportFile = join(reportDir, `${runId}.json`)
    writeFileSync(reportFile, `${JSON.stringify(report, null, 2)}\n`, 'utf8')
    process.stdout.write(`REAL_TASK_MATRIX_REPORT=${reportFile}\n`)
    process.stdout.write(`REAL_TASK_MATRIX_SUMMARY=${JSON.stringify({ runId, iteration, assertionCount: report.assertionCount, failed })}\n`)
    for (const [name, passed] of Object.entries(assertions)) {
      process.stdout.write(
        `REAL_TASK_MATRIX_${name.toUpperCase().replace(/[^A-Z0-9]+/g, '_')}=${passed ? 'PASS' : 'FAIL'}\n`,
      )
    }
    process.stdout.write(`REAL_TASK_MATRIX_ASSERTION_COUNT=${report.assertionCount}\n`)
    process.stdout.write(`REAL_TASK_MATRIX_FAILED_COUNT=${failed.length}\n`)
    return failed.length === 0 ? 0 : 4
  } finally {
    await disposeEnvironment(environment)
  }
}

main().then(
  code => { process.exitCode = code },
  error => {
    process.stderr.write(
      `[Real Task Matrix] fatal: ${error instanceof Error ? error.stack ?? error.message : String(error)}\n`,
    )
    process.exitCode = 1
  },
)
