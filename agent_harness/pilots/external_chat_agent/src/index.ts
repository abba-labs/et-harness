#!/usr/bin/env node

import { randomUUID } from 'node:crypto'
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
import {
  AuditedExternalAgentClient,
  buildExternalChatAudit,
  writeExternalChatAudit,
} from './audit.js'

const tick = (): Promise<void> => new Promise(resolveTick => setTimeout(resolveTick, 0))
const defaultTask = '分析 ET-TOOL 中 Code Gate、Release 构建与验证证据之间的执行关系，并给出简洁结论。'

const requireEnv = (name: string): string => {
  const value = process.env[name]?.trim()
  if (!value) throw new Error(`${name} is required for External Chat Agent Pilot`)
  return value
}

const safeRunId = (): string =>
  `CHAT-${new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)}-${randomUUID().slice(0, 8)}`

const assertPlainBusinessTask = (task: string): void => {
  const forbidden = [
    'Context Manager',
    'Knowledge Manager',
    'Unified Reflection',
    'Closure Coordinator',
    '8/8 Closure',
    'NONE / PROJECT / PUBLIC / BOTH',
  ]
  for (const hint of forbidden) {
    if (task.includes(hint)) throw new Error(`Business task contains governance hint: ${hint}`)
  }
}

async function applyPlugin(ctx: Context, fibers: Array<{ dispose(): Promise<void> | void }>, plugin: unknown): Promise<void> {
  const fiber = await ctx.plugin(plugin as never, undefined as never)
  fibers.push(fiber)
  await tick()
}

async function main(): Promise<number> {
  const token = requireEnv('EXTERNAL_AGENT_GITHUB_TOKEN')
  const repository = requireEnv('EXTERNAL_AGENT_REPOSITORY')
  const issueNumber = Number(requireEnv('EXTERNAL_AGENT_ISSUE_NUMBER'))
  if (!Number.isInteger(issueNumber) || issueNumber <= 0) throw new Error('EXTERNAL_AGENT_ISSUE_NUMBER must be positive')

  const runId = process.env.EXTERNAL_AGENT_RUN_ID?.trim() || safeRunId()
  const runtimeId = process.env.EXTERNAL_AGENT_RUNTIME_ID?.trim() || `${runId}-et-tool`
  const turnId = process.env.EXTERNAL_AGENT_TURN_ID?.trim() || 'TURN-1'
  const taskText = process.env.EXTERNAL_AGENT_TASK?.trim() || defaultTask
  assertPlainBusinessTask(taskText)

  const auditRoot = resolve(
    process.env.AGENT_HARNESS_EXTERNAL_CHAT_AUDIT_ROOT?.trim()
      || join(tmpdir(), 'et-tool-external-chat-agent-audits'),
  )
  const stateRoot = resolve(
    process.env.AGENT_HARNESS_STATE_ROOT?.trim()
      || join(tmpdir(), 'et-tool-external-chat-agent-state', runId),
  )
  process.env.AGENT_HARNESS_STATE_ROOT = stateRoot
  delete process.env.AGENT_HARNESS_GLOBAL_KNOWLEDGE_ROOT

  const ctx = new Context()
  const fibers: Array<{ dispose(): Promise<void> | void }> = []
  let snapshot: ReturnType<typeof createEtToolProjectSnapshot> | undefined
  let runtime: import('@agent-harness/governance-runtime').GovernanceRuntimeService | undefined
  let kernel: import('@agent-harness/agent-governance-kernel').AgentGovernanceKernelService | undefined
  let auditedClient: AuditedExternalAgentClient | undefined
  let visibleOutput: string | undefined
  let pilotError: Error | undefined

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
    ]) {
      await applyPlugin(ctx, fibers, plugin)
    }

    runtime = ctx.get('governanceRuntime') as import('@agent-harness/governance-runtime').GovernanceRuntimeService | undefined
    kernel = ctx.get('agentGovernanceKernel') as import('@agent-harness/agent-governance-kernel').AgentGovernanceKernelService | undefined
    if (!runtime || !kernel) throw new Error('Required public governance services are unavailable')

    const sourceProjectRoot = resolve(process.env.EXTERNAL_AGENT_PROJECT_ROOT?.trim() || process.cwd())
    snapshot = createEtToolProjectSnapshot(sourceProjectRoot)
    process.env.ET_TOOL_PROJECT_ROOT = snapshot.root
    await applyPlugin(ctx, fibers, etToolProjectPlugin)

    const bridgeClient = new GitHubIssueModelClient({
      token,
      repository,
      issueNumber,
      timeoutMs: Number(process.env.EXTERNAL_AGENT_RESPONSE_TIMEOUT_MS || 15 * 60_000),
      pollIntervalMs: Number(process.env.EXTERNAL_AGENT_POLL_INTERVAL_MS || 2_000),
    })
    auditedClient = new AuditedExternalAgentClient(bridgeClient)
    const driver = new GenericModelPilotDriver(runtime, auditedClient)
    const result = await driver.runTurn({
      runtimeId,
      turnId,
      taskText,
      projectId: 'et-tool',
      workspacePath: snapshot.root,
      actorId: 'external-chat-agent',
    })
    visibleOutput = result.work.visibleOutput
    process.stdout.write(`${visibleOutput}\n`)
  } catch (error) {
    pilotError = error instanceof Error ? error : new Error(String(error))
  }

  try {
    if (!runtime || !kernel || !auditedClient) throw pilotError ?? new Error('Pilot did not initialize far enough to audit')
    const audit = buildExternalChatAudit({
      runId,
      runtimeId,
      turnId,
      taskText,
      modelClient: auditedClient,
      runtime,
      kernel,
      ...(visibleOutput ? { visibleOutput } : {}),
      ...(pilotError ? { error: pilotError } : {}),
    })
    const files = writeExternalChatAudit(auditRoot, runId, audit.receipt)
    process.stderr.write(`[External Chat Agent] audit=${files.file}\n`)
    process.stderr.write(`[External Chat Agent] latest=${files.latest}\n`)
    if (!audit.pass) {
      process.stderr.write(`[External Chat Agent] FAIL: ${audit.blockingReasons.join('; ')}\n`)
      return 1
    }
    process.stderr.write('EXTERNAL_CHAT_AGENT_GOVERNANCE_PILOT=PASS\n')
    return 0
  } finally {
    for (const fiber of fibers.reverse()) await fiber.dispose()
    snapshot?.dispose()
  }
}

main().then(
  code => { process.exitCode = code },
  error => {
    process.stderr.write(`[External Chat Agent] fatal: ${error instanceof Error ? error.message : String(error)}\n`)
    process.exitCode = 1
  },
)
