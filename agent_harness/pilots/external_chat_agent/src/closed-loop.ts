#!/usr/bin/env node

import { randomUUID } from 'node:crypto'
import { writeFileSync } from 'node:fs'
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
import { GenericModelPilotDriver } from '@agent-harness/generic-model-pilot'
import { GitHubIssueModelClient } from './github-issue-client.js'
import { createEtToolProjectSnapshot } from './et-tool-snapshot.js'
import { AuditedExternalAgentClient } from './audit.js'

const tick = (): Promise<void> => new Promise(resolveTick => setTimeout(resolveTick, 0))

const requireEnv = (name: string): string => {
  const value = process.env[name]?.trim()
  if (!value) throw new Error(`${name} is required for External Chat Agent Closed-Loop Pilot`)
  return value
}

const safeRunId = (): string =>
  `CHAT-LOOP-${new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)}-${randomUUID().slice(0, 8)}`

async function applyPlugin(ctx: Context, fibers: Array<{ dispose(): Promise<void> | void }>, plugin: unknown): Promise<void> {
  const fiber = await ctx.plugin(plugin as never, undefined as never)
  fibers.push(fiber)
  await tick()
}

const allKnowledgeIds = (index: any): string[] =>
  (index.files ?? []).flatMap((file: any) => file.nodes ?? [])

const activeCategory = (index: any, categoryId: string | undefined): boolean =>
  !!categoryId && index.taxonomy?.categories?.[categoryId]?.status === 'ACTIVE'

async function main(): Promise<number> {
  const token = requireEnv('EXTERNAL_AGENT_GITHUB_TOKEN')
  const repository = requireEnv('EXTERNAL_AGENT_REPOSITORY')
  const issueNumber = Number(requireEnv('EXTERNAL_AGENT_ISSUE_NUMBER'))
  if (!Number.isInteger(issueNumber) || issueNumber <= 0) throw new Error('EXTERNAL_AGENT_ISSUE_NUMBER must be positive')

  const runId = process.env.EXTERNAL_AGENT_RUN_ID?.trim() || safeRunId()
  const runtimeId = process.env.EXTERNAL_AGENT_RUNTIME_ID?.trim() || `${runId}-et-tool`
  const actorId = 'external-chat-agent-closed-loop'
  const task1 = '说明本次 External Chat Agent 正向闭环试点中，GitHub Issue mailbox 与 Public Governance Runtime 各自应该承担什么职责。'
  const task2 = '根据项目治理知识回答：External Chat Agent mailbox 是否可以自行决定 Rule、Knowledge 或 Gate 路由？为什么？'
  const reportFile = resolve(
    process.env.EXTERNAL_CHAT_AGENT_CLOSED_LOOP_REPORT?.trim()
      || join(tmpdir(), `${runId}-closed-loop.json`),
  )
  const stateRoot = resolve(
    process.env.AGENT_HARNESS_STATE_ROOT?.trim()
      || join(tmpdir(), 'et-tool-external-chat-agent-closed-loop-state', runId),
  )
  process.env.AGENT_HARNESS_STATE_ROOT = stateRoot
  delete process.env.AGENT_HARNESS_GLOBAL_KNOWLEDGE_ROOT

  const ctx = new Context()
  const fibers: Array<{ dispose(): Promise<void> | void }> = []
  let snapshot: ReturnType<typeof createEtToolProjectSnapshot> | undefined

  try {
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

    const runtime = ctx.get('governanceRuntime') as import('@agent-harness/governance-runtime').GovernanceRuntimeService | undefined
    const knowledge = ctx.get('knowledgeManager') as import('@agent-harness/knowledge-manager').KnowledgeManagerService | undefined
    const context = ctx.get('contextManager') as any
    if (!runtime || !knowledge || !context) throw new Error('Required Public Governance services are unavailable')

    const sourceProjectRoot = resolve(process.env.EXTERNAL_AGENT_PROJECT_ROOT?.trim() || process.cwd())
    snapshot = createEtToolProjectSnapshot(sourceProjectRoot)
    process.env.ET_TOOL_PROJECT_ROOT = snapshot.root
    await applyPlugin(ctx, fibers, etToolProjectPlugin)

    const validationSource = knowledge.registerProjectSource('et-tool', {
      kind: 'DOCUMENT',
      title: 'Public Governance Runtime and External Boundaries v0.1',
      location: 'agent_harness/design/21_PUBLIC_GOVERNANCE_RUNTIME_AND_EXTERNAL_BOUNDARIES_V0_1.md',
      note: 'Authoritative project governance design source for the external-agent mailbox boundary.',
    })

    const beforeIndex = knowledge.getIndex('et-tool')
    const beforeIds = new Set(allKnowledgeIds(beforeIndex))
    const beforeFingerprint = beforeIndex.sourceFingerprint

    const bridge = new GitHubIssueModelClient({
      token,
      repository,
      issueNumber,
      timeoutMs: Number(process.env.EXTERNAL_AGENT_RESPONSE_TIMEOUT_MS || 15 * 60_000),
      pollIntervalMs: Number(process.env.EXTERNAL_AGENT_POLL_INTERVAL_MS || 2_000),
    })
    const auditedClient = new AuditedExternalAgentClient(bridge)
    const driver = new GenericModelPilotDriver(runtime, auditedClient)

    const turn1 = await driver.runTurn({
      runtimeId,
      turnId: 'TURN-1',
      taskText: task1,
      projectId: 'et-tool',
      workspacePath: snapshot.root,
      actorId,
      additionalToolResults: [{
        name: 'governance-document-consult',
        summary: 'The authoritative project governance design states that the External Chat Agent GitHub Issue mailbox is transport only; governance routing and lifecycle decisions belong to Public Governance Runtime.',
        resourceRefs: [validationSource.sourceUri],
      }],
    })

    const afterTurn1Index = knowledge.getIndex('et-tool')
    const newIds = allKnowledgeIds(afterTurn1Index).filter(id => !beforeIds.has(id))
    const newNodes = newIds
      .map(id => knowledge.getNode('et-tool', id)?.node)
      .filter((node): node is NonNullable<typeof node> => !!node?.isLeaf)
    const learnedKnowledge = newNodes.find(node => node.status !== 'DEPRECATED')
    const frameAfterTurn1 = context.buildFrame('et-tool', turn1.open.taskId)
    const learnedSearch = learnedKnowledge
      ? knowledge.searchKnowledge({
          projectId: 'et-tool',
          query: task2,
          limit: 16,
        })
      : []

    const turn2 = await driver.runTurn({
      runtimeId,
      turnId: 'TURN-2',
      taskText: task2,
      projectId: 'et-tool',
      workspacePath: snapshot.root,
      actorId,
    })

    const frameAfterTurn2 = context.buildFrame('et-tool', turn2.open.taskId)
    const autoRoutedIds = turn2.open.context.route.knowledgeIds
    const learnedKnowledgeRouted = !!learnedKnowledge && autoRoutedIds.includes(learnedKnowledge.id)
    const learnedKnowledgeSearchable = !!learnedKnowledge && learnedSearch.some(item => item.id === learnedKnowledge.id)
    const learnedCategoryIsActive = !!learnedKnowledge && activeCategory(afterTurn1Index, learnedKnowledge.category)
    const fingerprintChanged = !!beforeFingerprint
      && !!afterTurn1Index.sourceFingerprint
      && beforeFingerprint !== afterTurn1Index.sourceFingerprint
    const contextAdvanced = frameAfterTurn1.stateVersion > turn1.open.context.stateVersion
      && frameAfterTurn2.stateVersion >= turn2.open.context.stateVersion

    const closure1 = turn1.close.closure as any
    const closure2 = turn2.close.closure as any
    const knowledgeReceipt = (closure1.moduleReceipts ?? []).find((item: any) => item.moduleId === 'knowledge-closure')

    const report = {
      runId,
      runtimeId,
      taskId: turn1.open.taskId,
      externalAgentCalls: auditedClient.calls.map(item => ({ purpose: item.purpose, requestId: item.requestId })),
      turn1: {
        stateVersionOpen: turn1.open.context.stateVersion,
        stateVersionAfter: frameAfterTurn1.stateVersion,
        route: turn1.open.context.route,
        closureStatus: closure1.status,
        knowledgeReceipt,
      },
      knowledgeMutation: {
        beforeFingerprint,
        afterFingerprint: afterTurn1Index.sourceFingerprint,
        fingerprintChanged,
        newKnowledgeIds: newIds,
        candidateId: learnedKnowledge?.id,
        candidateStatus: learnedKnowledge?.status,
        candidateCategory: learnedKnowledge?.category,
        learnedCategoryIsActive,
        learnedKnowledgeSearchableWithExplicitCandidateFilter: learnedKnowledgeSearchable,
      },
      turn2: {
        stateVersionOpen: turn2.open.context.stateVersion,
        stateVersionAfter: frameAfterTurn2.stateVersion,
        route: turn2.open.context.route,
        closureStatus: closure2.status,
        candidateAutomaticallyRouted: learnedKnowledgeRouted,
      },
      assertions: {
        fourModelCalls: auditedClient.calls.length === 4
          && auditedClient.calls.map(item => item.purpose).join(',') === 'WORK,GOVERNANCE_REFLECTION,WORK,GOVERNANCE_REFLECTION',
        turn1Closed: closure1.status === 'COMPLETE',
        knowledgeClosureApplied: knowledgeReceipt?.status === 'APPLIED',
        knowledgeCandidateCreated: !!learnedKnowledge,
        knowledgeCategoryForcedActive: learnedCategoryIsActive,
        knowledgeAutomaticallyValidated: learnedKnowledge?.status === 'VALIDATED' || learnedKnowledge?.status === 'FULL_VALIDATED',
        knowledgeIndexRefreshed: fingerprintChanged && learnedKnowledgeSearchable,
        contextAutomaticallyAdvanced: contextAdvanced,
        turn2Closed: closure2.status === 'COMPLETE',
        knowledgeAutomaticallyReusedByDefaultRoute: learnedKnowledgeRouted,
      },
    }

    writeFileSync(reportFile, `${JSON.stringify(report, null, 2)}\n`, 'utf-8')
    process.stdout.write(`EXTERNAL_CHAT_AGENT_CLOSED_LOOP_REPORT=${reportFile}\n`)
    process.stdout.write(`${JSON.stringify(report.assertions)}\n`)

    const foundationalPass = report.assertions.fourModelCalls
      && report.assertions.turn1Closed
      && report.assertions.knowledgeClosureApplied
      && report.assertions.knowledgeCandidateCreated
      && report.assertions.knowledgeCategoryForcedActive
      && report.assertions.knowledgeAutomaticallyValidated
      && report.assertions.knowledgeIndexRefreshed
      && report.assertions.contextAutomaticallyAdvanced
      && report.assertions.turn2Closed

    if (!foundationalPass) return 2
    if (!report.assertions.knowledgeAutomaticallyReusedByDefaultRoute) return 3
    return 0
  } finally {
    for (const fiber of fibers.reverse()) await fiber.dispose()
    snapshot?.dispose()
  }
}

main().then(
  code => { process.exitCode = code },
  error => {
    process.stderr.write(`[External Chat Agent Closed Loop] fatal: ${error instanceof Error ? error.message : String(error)}\n`)
    process.exitCode = 1
  },
)
