import { homedir } from 'node:os'
import { join } from 'node:path'
import { Service, type Context } from '@deepseek-ai/cordis'
import { observeFrameworkOperation } from '@agent-harness/governance-core'
import '@agent-harness/project-manager'
import { EvidenceStateEngine } from './evidence-state-engine.js'
import type {
  EvidenceQuery,
  EvidenceRecord,
  EvidenceRecordInput,
  ProjectStateSnapshot,
  StateRecord,
  StateUpdateInput,
} from './contracts.js'

const defaultStorageRoot = (): string =>
  process.env.AGENT_HARNESS_STATE_ROOT ?? join(homedir(), '.agent-harness', 'runtime')

const taskIdFromScope = (scope: string): string | undefined => {
  if (scope.startsWith('context:')) return scope.slice('context:'.length) || undefined
  if (scope.startsWith('task:')) return scope.slice('task:'.length) || undefined
  return undefined
}

export class EvidenceStateManagerService extends Service {
  private readonly runtimeContext: Context
  private readonly engine: EvidenceStateEngine

  constructor(ctx: Context) {
    super(ctx, 'evidenceStateManager')
    this.runtimeContext = ctx
    this.engine = new EvidenceStateEngine(defaultStorageRoot())
  }

  getStorageRoot(): string {
    return this.engine.getStorageRoot()
  }

  recordEvidence(input: EvidenceRecordInput): EvidenceRecord {
    return observeFrameworkOperation(
      this.runtimeContext,
      {
        component: 'evidence',
        operation: 'record',
        projectId: input.projectId,
        taskId: input.taskId,
        tags: { kind: input.kind, result: input.result },
      },
      () => {
        this.assertProject(input.projectId)
        return this.engine.recordEvidence(input)
      },
      result => ({
        outcome: result.result === 'PASS' ? 'PASS' : result.result === 'FAIL' ? 'FAIL' : 'OK',
        values: { artifactRefCount: result.artifactRefs?.length ?? 0 },
      }),
    )
  }

  listEvidence(query: EvidenceQuery): readonly EvidenceRecord[] {
    this.assertProject(query.projectId)
    return this.engine.listEvidence(query)
  }

  getEvidence(projectId: string, evidenceId: string): EvidenceRecord | undefined {
    this.assertProject(projectId)
    return this.engine.getEvidence(projectId, evidenceId)
  }

  updateState(input: StateUpdateInput): StateRecord {
    const taskId = taskIdFromScope(input.scope)
    return observeFrameworkOperation(
      this.runtimeContext,
      {
        component: 'state',
        operation: 'update',
        projectId: input.projectId,
        ...(taskId ? { taskId } : {}),
        tags: { scope: input.scope, key: input.key },
      },
      () => {
        this.assertProject(input.projectId)
        return this.engine.updateState(input)
      },
      result => ({
        outcome: 'OK',
        values: { version: result.version, evidenceRefCount: result.evidenceRefs.length },
      }),
    )
  }

  readState(projectId: string, scope: string, key: string): StateRecord | undefined {
    this.assertProject(projectId)
    return this.engine.readState(projectId, scope, key)
  }

  snapshot(projectId: string): ProjectStateSnapshot {
    this.assertProject(projectId)
    return this.engine.snapshot(projectId)
  }

  private assertProject(projectId: string): void {
    if (!this.runtimeContext.projectManager.getProjectContext(projectId)) {
      throw new Error(`Evidence / State Manager 找不到项目: ${projectId}`)
    }
  }
}

declare module '@deepseek-ai/cordis' {
  interface Context {
    evidenceStateManager: EvidenceStateManagerService
  }
}

export default EvidenceStateManagerService
