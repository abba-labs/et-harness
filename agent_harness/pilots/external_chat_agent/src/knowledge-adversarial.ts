#!/usr/bin/env node

import { randomUUID } from 'node:crypto'
import { cpSync, mkdirSync, rmSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { tmpdir } from 'node:os'
import { Context } from '@deepseek-ai/cordis'
import GovernanceCatalogService from '@agent-harness/governance-core'
import * as projectManagerPlugin from '@agent-harness/project-manager'
import * as evidencePlugin from '@agent-harness/evidence-state-manager'
import * as knowledgePlugin from '@agent-harness/knowledge-manager'
import * as etToolProjectPlugin from '@agent-harness/project-et-tool'
import { createEtToolProjectSnapshot } from './et-tool-snapshot.js'

const tick = (): Promise<void> => new Promise(resolveTick => setTimeout(resolveTick, 0))

async function applyPlugin(ctx: Context, fibers: Array<{ dispose(): Promise<void> | void }>, plugin: unknown): Promise<void> {
  const fiber = await ctx.plugin(plugin as never, undefined as never)
  fibers.push(fiber)
  await tick()
}

const throws = (fn: () => unknown): boolean => {
  try {
    fn()
    return false
  } catch {
    return true
  }
}

async function main(): Promise<number> {
  const runId = `KADV-${randomUUID().slice(0, 8)}`
  const repoRoot = resolve(process.cwd())
  const stateRoot = join(tmpdir(), 'et-tool-adversarial-knowledge', runId)
  const globalRoot = join(stateRoot, 'global-knowledge')
  mkdirSync(stateRoot, { recursive: true })
  cpSync(join(repoRoot, 'agent_harness', 'global_knowledge'), globalRoot, { recursive: true })
  process.env.AGENT_HARNESS_STATE_ROOT = stateRoot
  process.env.AGENT_HARNESS_GLOBAL_KNOWLEDGE_ROOT = globalRoot

  const ctx = new Context()
  const fibers: Array<{ dispose(): Promise<void> | void }> = []
  let snapshot: ReturnType<typeof createEtToolProjectSnapshot> | undefined

  try {
    await applyPlugin(ctx, fibers, GovernanceCatalogService)
    await applyPlugin(ctx, fibers, projectManagerPlugin)
    await applyPlugin(ctx, fibers, evidencePlugin)
    await applyPlugin(ctx, fibers, knowledgePlugin)

    snapshot = createEtToolProjectSnapshot(repoRoot)
    process.env.ET_TOOL_PROJECT_ROOT = snapshot.root
    await applyPlugin(ctx, fibers, etToolProjectPlugin)

    const manager = ctx.knowledgeManager
    const validator = ctx.knowledgeValidationPolicy

    const globalCandidate = manager.submitGlobalKnowledgeCandidate({
      categoryId: 'C020.020',
      title: 'Single Project Observation Must Not Become Universal Truth',
      fact: 'All projects must exhibit the exact behavior observed once on ET-TOOL hardware.',
      provenance: 'Adversarial single-project generalization probe.',
      scope: 'global',
      tags: ['adversarial', 'scope-generalization'],
    })
    const globalUri = `knowledge://global/${globalCandidate.knowledgeId}`

    const invalidCategoryRejected = throws(() => manager.submitGlobalKnowledgeCandidate({
      categoryId: 'C999.999',
      title: 'Invalid Category Probe',
      fact: 'This candidate must not be stored.',
      provenance: 'Adversarial category probe.',
    }))

    const nonexistentEvidenceRejected = throws(() => manager.recordVerification({
      knowledgeUri: globalUri,
      basisRef: 'evidence://project/et-tool/EV-NOT-REAL',
      relation: 'SUPPORT',
    }))

    const projectSource = manager.registerProjectSource('et-tool', {
      kind: 'SPEC',
      title: 'ET-TOOL private project spec',
      location: 'adversarial://private-et-tool-spec',
    })
    const privateProjectSourceCannotValidateGlobal = throws(() => manager.recordVerification({
      knowledgeUri: globalUri,
      basisRef: projectSource.sourceUri,
      relation: 'SUPPORT',
    }))

    const failEvidence = ctx.evidenceStateManager.recordEvidence({
      projectId: 'et-tool',
      taskId: runId,
      kind: 'hardware-validation',
      result: 'FAIL',
      summary: 'A failed hardware test must not count as REAL_TEST support.',
      source: 'adversarial-probe',
      metadata: { knowledgeValidationClass: 'REAL_TEST' },
    })
    const failRecord = manager.recordVerification({
      knowledgeUri: globalUri,
      basisRef: `evidence://project/et-tool/${failEvidence.evidenceId}`,
      relation: 'SUPPORT',
    })
    const failedEvidenceCannotMasqueradeAsRealTest = failRecord.validationClass !== 'REAL_TEST'

    const passEvidence = ctx.evidenceStateManager.recordEvidence({
      projectId: 'et-tool',
      taskId: runId,
      kind: 'hardware-validation',
      result: 'PASS',
      summary: 'One ET-TOOL hardware test passed.',
      source: 'adversarial-probe',
      metadata: { knowledgeValidationClass: 'REAL_TEST' },
    })
    manager.recordVerification({
      knowledgeUri: globalUri,
      basisRef: `evidence://project/et-tool/${passEvidence.evidenceId}`,
      relation: 'SUPPORT',
    })
    const singleProjectEvaluation = validator.evaluate(globalUri)
    const singleProjectRealTestCannotFullValidateGlobal = !(
      singleProjectEvaluation.decision === 'READY'
      && singleProjectEvaluation.targetStatus === 'FULL_VALIDATED'
    )

    const contradictionCandidate = manager.submitGlobalKnowledgeCandidate({
      categoryId: 'C020.020',
      title: 'Contradictory Global Claim Must Not Promote',
      fact: 'Contradictory evidence can be ignored during automatic promotion.',
      provenance: 'Adversarial contradiction probe.',
      scope: 'global',
    })
    const contradictionUri = `knowledge://global/${contradictionCandidate.knowledgeId}`
    const sourceA = manager.registerGlobalSource({
      kind: 'SPEC',
      title: 'Adversarial Global Spec A',
      location: `adversarial://global-spec-a-${runId}`,
    })
    const sourceB = manager.registerGlobalSource({
      kind: 'SPEC',
      title: 'Adversarial Global Spec B',
      location: `adversarial://global-spec-b-${runId}`,
    })
    const sourceConflict = manager.registerGlobalSource({
      kind: 'SPEC',
      title: 'Adversarial Global Contradiction',
      location: `adversarial://global-spec-conflict-${runId}`,
    })
    for (const source of [sourceA, sourceB]) {
      manager.recordVerification({ knowledgeUri: contradictionUri, basisRef: source.sourceUri, relation: 'SUPPORT' })
    }
    manager.recordVerification({ knowledgeUri: contradictionUri, basisRef: sourceConflict.sourceUri, relation: 'CONTRADICT' })
    const contradictionEvaluation = validator.evaluate(contradictionUri)
    const contradictionBlocksPromotion = contradictionEvaluation.decision === 'BLOCKED'

    const assertions = {
      invalidCategoryRejected,
      nonexistentEvidenceRejected,
      privateProjectSourceCannotValidateGlobal,
      failedEvidenceCannotMasqueradeAsRealTest,
      singleProjectRealTestCannotFullValidateGlobal,
      contradictionBlocksPromotion,
    }
    const failed = Object.entries(assertions).filter(([, ok]) => !ok).map(([key]) => key)

    process.stdout.write(`KNOWLEDGE_ADVERSARIAL=${JSON.stringify({
      assertions,
      failed,
      diagnostics: {
        globalCandidate: globalUri,
        failEvidenceValidationClass: failRecord.validationClass,
        singleProjectEvaluation,
        contradictionEvaluation,
      },
    })}\n`)
    for (const [key, value] of Object.entries(assertions)) {
      process.stdout.write(`KNOWLEDGE_ADVERSARIAL_${key.toUpperCase()}=${value ? 'PASS' : 'FAIL'}\n`)
    }
    process.stdout.write(`KNOWLEDGE_ADVERSARIAL_FAILED_COUNT=${failed.length}\n`)
    return failed.length === 0 ? 0 : 3
  } finally {
    for (const fiber of fibers.reverse()) await fiber.dispose()
    snapshot?.dispose()
    rmSync(stateRoot, { recursive: true, force: true })
  }
}

main().then(
  code => { process.exitCode = code },
  error => {
    process.stderr.write(`[Knowledge Adversarial] fatal: ${error instanceof Error ? error.stack ?? error.message : String(error)}\n`)
    process.exitCode = 1
  },
)
