import type {
  ExecutionEventAcceptanceV01,
  ExecutionEventEnvelopeV01,
  ExecutionEventStoreV01,
  ExecutionObligationLedgerV01,
} from '@agent-harness/execution-supervisor'
import type { GovernanceHostExecutionEventInput } from './contracts.js'

export interface RuntimeExecutionIngressState {
  readonly eventStore: ExecutionEventStoreV01
  readonly ledger: ExecutionObligationLedgerV01
  readonly eventsById: Map<string, RuntimeExecutionEventIdentity>
  ingestTail: Promise<void>
}

export type RuntimeExecutionEventIdentity = Pick<
  ExecutionEventEnvelopeV01,
  'sequence' | 'timestamp' | 'kind' | 'payloadHash'
>

export interface RuntimeExecutionIngressResult {
  readonly eventRef: string
  readonly acceptance: ExecutionEventAcceptanceV01
}

interface RuntimeExecutionIngressDependencies {
  readonly schema: ExecutionEventEnvelopeV01['schema']
  readonly hashPayload: (payload: Readonly<Record<string, unknown>>) => string
  readonly now: () => string
  readonly cleanEventId: (value: string) => string
}

export const enqueueRuntimeExecutionEvent = (
  state: RuntimeExecutionIngressState,
  input: GovernanceHostExecutionEventInput,
  dependencies: RuntimeExecutionIngressDependencies,
): Promise<RuntimeExecutionIngressResult> => {
  const operation = state.ingestTail.then(async () => {
    const eventId = dependencies.cleanEventId(input.eventId)
    const existing = state.eventsById.get(eventId)
    const binding = state.eventStore.binding
    const contract = binding.contract
    const event: ExecutionEventEnvelopeV01 = {
      schema: dependencies.schema,
      requestId: binding.requestId,
      runtimeId: binding.runtimeId,
      projectId: contract.projectId,
      taskId: contract.taskId,
      turnId: binding.turnId,
      agentId: contract.agentId,
      contextHash: contract.contextHash,
      sequence: existing?.sequence ?? state.eventStore.cursor.sequence + 1,
      eventId,
      timestamp: existing?.timestamp ?? dependencies.now(),
      kind: input.kind,
      payloadHash: dependencies.hashPayload(input.payload),
      payload: structuredClone(input.payload),
    }
    const acceptance = await state.ledger.ingest(event)
    if (acceptance.status === 'ACCEPTED') state.eventsById.set(eventId, {
      sequence: event.sequence,
      timestamp: event.timestamp,
      kind: event.kind,
      payloadHash: event.payloadHash,
    })
    return { eventRef: `execution-event://${eventId}`, acceptance }
  })
  state.ingestTail = operation.then(() => undefined, () => undefined)
  return operation
}
