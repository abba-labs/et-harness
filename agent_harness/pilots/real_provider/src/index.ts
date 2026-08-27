#!/usr/bin/env node

import { randomUUID } from 'node:crypto'
import { createRequire } from 'node:module'
import { dirname, join, resolve } from 'node:path'
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
import { JsonProcessModelClient } from '@agent-harness/json-process-model-client'
import { GenericModelPilotDriver } from '@agent-harness/generic-model-pilot'
import {
  AuditedModelClient,
  buildRealProviderAudit,
  writeRealProviderAudit,
} from './audit.js'
import { createEtToolProjectSnapshot } from './et-tool-snapshot.js'
import { createSyntheticProjectFixture } from './synthetic-project.js'

const PROVIDER_ENV_NAMES = [
  'OPENAI_COMPAT_BASE_URL',
  'OPENAI_COMPAT_API_KEY',
  'OPENAI_COMPAT_MODEL',
  'OPENAI_COMPAT_API_STYLE',
  'OPENAI_COMPAT_PROVIDER_ID',
  'OPENAI_COMPAT_CHAT_JSON_MODE',
  'OPENAI_COMPAT_TIMEOUT_MS',
  'OPENAI_COMPAT_MAX_RESPONSE_BYTES',
  'OPENAI_COMPAT_MAX_OUTPUT_TOKENS',
  'OPENAI_COMPAT_EXTRA_BODY_JSON',
  'OPENAI_COMPAT_EXTRA_HEADERS_JSON',
] as const

const tick = (): Promise<void> => new Promise(resolveTick => setTimeout(resolveTick, 0))

const requireEnv = (name: string): string => {
  const value = process.env[name]?.trim()
  if (!value) throw new Error(`${name} is required for Level 2C real-provider pilot`)
  return value
}

const safeRunId = (): string =>
  `L2C-${new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)}-${randomUUID().slice(0, 8)}`

const laneFromEnv = (): 'synthetic' | 'et-tool' => {
  const lane = process.env.REAL_PROVIDER_LANE?.trim() || 'synthetic'
  if (lane !== 'synthetic' && lane !== 'et-tool') {
    throw new Error('REAL_PROVIDER_LANE must be synthetic or et-tool')
  }
  return lane
}

const defaultTask = (lane: 'synthetic' | 'et-tool'): string => lane === 'et-tool'
  ? '分析 ET-TOOL 中 Code Gate、Release 构建与验证证据之间的执行关系，并给出简洁结论。'
  : '分析当前项目中 Code Gate、Release 构建与验证证据之间的执行关系，并给出简洁结论。'

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

const providerEnv = (): Record<string, string> => {
  const result: Record<string, string> = {}
  for (const name of PROVIDER_ENV_NAMES) {
    const value = process.env[name]
    if (value !== undefined) result[name] = value
  }
  return result
}

const redactText = (error: unknown, secrets: readonly string[]): string => {
  let text = error instanceof Error ? error.message : String(error)
  for (const secret of secrets.filter(Boolean)) text = text.split(secret).join('[REDACTED]')
  return text
}

const wrapperCliPath = (): string => {
  const require = createRequire(import.meta.url)
  const indexPath = require.resolve('@agent-harness/openai-compatible-model-wrapper')
  return join(dirname(indexPath), 'cli.js')
}

async function applyPlugin(ctx: Context, fibers: Array<{ dispose(): Promise<void> | void }>, plugin: unknown): Promise<void> {
  const fiber = await ctx.plugin(plugin as never, undefined as never)
  fibers.push(fiber)
  await tick()
}

async function main(): Promise<number> {
  const lane = laneFromEnv()
  const runId = process.env.REAL_PROVIDER_RUN_ID?.trim() || safeRunId()
  const runtimeId = process.env.REAL_PROVIDER_RUNTIME_ID?.trim() || `${runId}-${lane}`
  const turnId = process.env.REAL_PROVIDER_TURN_ID?.trim() || 'TURN-1'
  const taskText = process.env.REAL_PROVIDER_TASK?.trim() || defaultTask(lane)
  assertPlainBusinessTask(taskText)

  const baseUrl = requireEnv('OPENAI_COMPAT_BASE_URL')
  const apiKey = requireEnv('OPENAI_COMPAT_API_KEY')
  const model = requireEnv('OPENAI_COMPAT_MODEL')
  const apiStyle = requireEnv('OPENAI_COMPAT_API_STYLE')
  const providerId = process.env.OPENAI_COMPAT_PROVIDER_ID?.trim() || 'openai-compatible'
  const baseOrigin = new URL(baseUrl).origin
  const auditRoot = resolve(
    process.env.AGENT_HARNESS_REAL_PROVIDER_AUDIT_ROOT?.trim()
      || join(tmpdir(), 'et-tool-agent-harness-real-provider-audits'),
  )
  const stateRoot = resolve(
    process.env.AGENT_HARNESS_STATE_ROOT?.trim()
      || join(tmpdir(), 'et-tool-agent-harness-real-provider-state', runId),
  )
  process.env.AGENT_HARNESS_STATE_ROOT = stateRoot
  if (process.env.REAL_PROVIDER_ENABLE_GLOBAL_KNOWLEDGE !== '1') {
    delete process.env.AGENT_HARNESS_GLOBAL_KNOWLEDGE_ROOT
  }

  const ctx = new Context()
  const fibers: Array<{ dispose(): Promise<void> | void }> = []
  let disposeBeforeFibers: (() => void) | undefined
  let disposeAfterFibers: (() => void) | undefined
  let visibleOutput: string | undefined
  let pilotError: Error | undefined
  let runtime: import('@agent-harness/governance-runtime').GovernanceRuntimeService | undefined
  let kernel: import('@agent-harness/agent-governance-kernel').AgentGovernanceKernelService | undefined
  let auditedClient: AuditedModelClient | undefined

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
    const projectManager = ctx.get('projectManager') as import('@agent-harness/project-manager').ProjectManagerService | undefined
    if (!runtime || !kernel || !projectManager) throw new Error('Required public governance services are unavailable')

    let projectId: string
    let workspacePath: string
    if (lane === 'synthetic') {
      const fixture = createSyntheticProjectFixture()
      const disposeProject = projectManager.registerProject(fixture.manifest, fixture.root)
      disposeBeforeFibers = () => {
        disposeProject()
        fixture.dispose()
      }
      projectId = fixture.manifest.project.id
      workspacePath = fixture.root
    } else {
      const sourceProjectRoot = resolve(process.env.REAL_PROVIDER_PROJECT_ROOT?.trim() || process.cwd())
      const snapshot = createEtToolProjectSnapshot(sourceProjectRoot)
      disposeAfterFibers = () => snapshot.dispose()
      process.env.ET_TOOL_PROJECT_ROOT = snapshot.root
      await applyPlugin(ctx, fibers, etToolProjectPlugin)
      projectId = 'et-tool'
      workspacePath = snapshot.root
    }

    const client = new JsonProcessModelClient({
      clientId: `level2c:${providerId}`,
      command: process.execPath,
      args: [wrapperCliPath()],
      env: providerEnv(),
      timeoutMs: Number(process.env.REAL_PROVIDER_MODEL_TIMEOUT_MS || 180_000),
      maxOutputBytes: Number(process.env.REAL_PROVIDER_MODEL_MAX_OUTPUT_BYTES || 4 * 1024 * 1024),
    })
    auditedClient = new AuditedModelClient(client, error => redactText(error, [apiKey]))
    const driver = new GenericModelPilotDriver(runtime, auditedClient)
    const result = await driver.runTurn({
      runtimeId,
      turnId,
      taskText,
      projectId,
      workspacePath,
    })
    visibleOutput = result.work.visibleOutput
    process.stdout.write(`${visibleOutput}\n`)
  } catch (error) {
    pilotError = new Error(redactText(error, [apiKey]))
  }

  try {
    if (!runtime || !kernel || !auditedClient) throw pilotError ?? new Error('Pilot did not initialize far enough to audit')
    const audit = buildRealProviderAudit({
      lane,
      runId,
      runtimeId,
      turnId,
      taskText,
      provider: {
        baseOrigin,
        apiStyle,
        configuredModel: model,
        configuredProviderId: providerId,
      },
      modelClient: auditedClient,
      runtime,
      kernel,
      ...(visibleOutput ? { visibleOutput } : {}),
      ...(pilotError ? { error: pilotError } : {}),
    })
    const files = writeRealProviderAudit(auditRoot, runId, audit.receipt)
    process.stderr.write(`[Level 2C] audit=${files.file}\n`)
    process.stderr.write(`[Level 2C] latest=${files.latest}\n`)
    if (!audit.pass) {
      process.stderr.write(`[Level 2C] FAIL: ${audit.blockingReasons.join('; ')}\n`)
      return 1
    }
    process.stderr.write('[Level 2C] PASS\n')
    return 0
  } finally {
    disposeBeforeFibers?.()
    for (const fiber of fibers.reverse()) await fiber.dispose()
    disposeAfterFibers?.()
  }
}

main().then(
  code => { process.exitCode = code },
  error => {
    process.stderr.write(`[Level 2C] fatal: ${error instanceof Error ? error.message : String(error)}\n`)
    process.exitCode = 1
  },
)
