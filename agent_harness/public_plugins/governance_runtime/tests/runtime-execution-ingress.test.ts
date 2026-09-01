import { describe, expect, it } from 'vitest'
import {
  enqueueRuntimeExecutionEvent,
  type RuntimeExecutionIngressState,
} from '../src/runtime-execution-ingress.js'

const createState = () => {
  let cursor = { sequence: 0, stateHash: '0'.repeat(64) }
  let clockTick = 0
  const durable = new Map<string, unknown>()
  const seenSequences: number[] = []
  const binding = {
    requestId: 'request-1', runtimeId: 'runtime-1', turnId: 'turn-1',
    contract: {
      projectId: 'project-1', taskId: 'task-1', agentId: 'agent-1', contextHash: 'c'.repeat(64),
    },
  }
  const eventStore = {
    binding,
    get cursor() { return cursor },
  }
  const ledger = {
    binding,
    async ingest(event: { eventId: string; sequence: number }) {
      seenSequences.push(event.sequence)
      const existing = durable.get(event.eventId)
      if (existing !== undefined) {
        const exact = JSON.stringify(existing) === JSON.stringify(event)
        return {
          eventId: event.eventId, sequence: event.sequence,
          status: exact ? 'DUPLICATE' : 'REJECTED',
          acceptedAt: '2026-08-30T00:00:00.000Z',
          reasons: exact ? [] : ['EVENT_ID_INTEGRITY_CONFLICT'],
        }
      }
      if (event.sequence !== cursor.sequence + 1) {
        return {
          eventId: event.eventId, sequence: event.sequence, status: 'REJECTED',
          acceptedAt: '2026-08-30T00:00:00.000Z', reasons: ['SEQUENCE_GAP'],
        }
      }
      durable.set(event.eventId, structuredClone(event))
      cursor = { sequence: event.sequence, stateHash: String(event.sequence).padStart(64, '0') }
      return {
        eventId: event.eventId, sequence: event.sequence, status: 'ACCEPTED',
        acceptedAt: '2026-08-30T00:00:00.000Z', reasons: [], stateHash: cursor.stateHash,
      }
    },
  }
  const state: RuntimeExecutionIngressState = {
    eventStore: eventStore as never,
    ledger: ledger as never,
    eventsById: new Map(),
    ingestTail: Promise.resolve(),
  }
  const dependencies = {
    schema: 'agent-harness.execution-event.v0.1' as const,
    hashPayload: (payload: Readonly<Record<string, unknown>>) => JSON.stringify(payload).padEnd(64, '0').slice(0, 64),
    now: () => `2026-08-30T00:00:0${clockTick++}.000Z`,
    cleanEventId: (value: string) => value,
  }
  return { state, dependencies, seenSequences }
}

describe('Runtime-owned execution event ingress', () => {
  it('serializes concurrent Host facts and assigns canonical identities and sequences', async () => {
    const { state, dependencies, seenSequences } = createState()
    const [first, second] = await Promise.all([
      enqueueRuntimeExecutionEvent(state, {
        runtimeId: 'ignored-host-runtime', turnId: 'ignored-host-turn', eventId: 'event-1',
        kind: 'TOOL_RESULT', payload: { value: 1 },
      }, dependencies),
      enqueueRuntimeExecutionEvent(state, {
        runtimeId: 'ignored-host-runtime', turnId: 'ignored-host-turn', eventId: 'event-2',
        kind: 'TOOL_RESULT', payload: { value: 2 },
      }, dependencies),
    ])

    expect(first.acceptance.status).toBe('ACCEPTED')
    expect(second.acceptance.status).toBe('ACCEPTED')
    expect(seenSequences).toEqual([1, 2])
    expect(state.eventsById.get('event-1')).toMatchObject({
      sequence: 1, kind: 'TOOL_RESULT',
    })
    expect(state.eventsById.get('event-1')).not.toHaveProperty('payload')
  })

  it('reuses the original sequence and timestamp for exact idempotent retry', async () => {
    const { state, dependencies } = createState()
    const input = { runtimeId: 'runtime-1', turnId: 'turn-1', eventId: 'event-1', kind: 'TOOL_RESULT' as const, payload: { value: 1 } }
    const first = await enqueueRuntimeExecutionEvent(state, input, dependencies)
    const duplicate = await enqueueRuntimeExecutionEvent(state, input, dependencies)

    expect(first.acceptance.status).toBe('ACCEPTED')
    expect(duplicate.acceptance).toMatchObject({ status: 'DUPLICATE', sequence: 1 })
    expect(state.eventsById.get('event-1')?.timestamp).toBe('2026-08-30T00:00:00.000Z')
  })

  it('rejects a conflicting retry without advancing the durable cursor', async () => {
    const { state, dependencies } = createState()
    await enqueueRuntimeExecutionEvent(state, {
      runtimeId: 'runtime-1', turnId: 'turn-1', eventId: 'event-1', kind: 'TOOL_RESULT', payload: { value: 1 },
    }, dependencies)
    const conflict = await enqueueRuntimeExecutionEvent(state, {
      runtimeId: 'runtime-1', turnId: 'turn-1', eventId: 'event-1', kind: 'TOOL_RESULT', payload: { value: 999 },
    }, dependencies)

    expect(conflict.acceptance.status).toBe('REJECTED')
    expect(conflict.acceptance.reasons).toContain('EVENT_ID_INTEGRITY_CONFLICT')
    expect(state.eventStore.cursor.sequence).toBe(1)
  })
})
