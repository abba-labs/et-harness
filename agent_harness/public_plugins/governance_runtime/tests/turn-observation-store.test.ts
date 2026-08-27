import { describe, expect, it } from 'vitest'
import {
  GovernanceTurnObservationStore,
  MAX_GOVERNANCE_OBSERVATION_CHARS,
} from '../src/turn-observation-store.js'

describe('GovernanceTurnObservationStore', () => {
  it('binds visible content into a stable digest reference', () => {
    const store = new GovernanceTurnObservationStore()
    const first = store.put({
      taskId: 'TASK-1',
      turnId: 'TURN-1',
      kind: 'ASSISTANT_MESSAGE',
      text: 'Visible result',
      refs: ['message://assistant/1'],
    })
    expect(first.observationRef).toContain('sha256:')
    expect(store.list('TASK-1', 'TURN-1')).toEqual([first])

    const secondStore = new GovernanceTurnObservationStore()
    const same = secondStore.put({
      taskId: 'TASK-1',
      turnId: 'TURN-1',
      kind: 'ASSISTANT_MESSAGE',
      text: 'Visible result',
      refs: ['message://assistant/1'],
    })
    expect(same.observationRef).toBe(first.observationRef)
  })

  it('bounds model-visible content instead of storing unbounded outputs', () => {
    const store = new GovernanceTurnObservationStore()
    const observation = store.put({
      taskId: 'TASK-1',
      turnId: 'TURN-1',
      kind: 'TOOL_RESULT',
      text: 'x'.repeat(MAX_GOVERNANCE_OBSERVATION_CHARS + 100),
      sourceName: 'test-tool',
    })
    expect(observation.text).toHaveLength(MAX_GOVERNANCE_OBSERVATION_CHARS)
    expect(observation.truncated).toBe(true)
  })
})
