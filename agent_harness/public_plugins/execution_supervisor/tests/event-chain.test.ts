import { describe, expect, it } from 'vitest'
import { validateExecutionEventBatch } from '../src/index.js'
import { contractFixture, eventFixture } from './fixtures.js'

describe('Execution Supervisor event-chain validation', () => {
  it('accepts one ordered bounded batch and advances the replay cursor', () => {
    const contract = contractFixture()
    const first = eventFixture(contract, {
      type: 'LIFECYCLE',
      checkpoint: 'WORK_STARTED',
      refs: [],
    }, 0)
    const second = eventFixture(contract, {
      type: 'ASSISTANT_OUTPUT',
      messageRef: 'message://assistant/1',
      contentHash: '7'.repeat(64),
      summary: 'Visible bounded output.',
    }, 1, first.eventHash)
    const result = validateExecutionEventBatch(
      [first, second],
      contract,
      { nextSequence: 0 },
    )
    expect(result.valid).toBe(true)
    expect(result.acceptedEvents).toHaveLength(2)
    expect(result.nextCursor).toEqual({
      nextSequence: 2,
      chainHead: second.eventHash,
    })
  })

  it('rejects event gaps without partially advancing durable state', () => {
    const contract = contractFixture()
    const event = eventFixture(contract, {
      type: 'LIFECYCLE',
      checkpoint: 'WORK_STARTED',
      refs: [],
    }, 2)
    const cursor = { nextSequence: 0 }
    const result = validateExecutionEventBatch([event], contract, cursor)
    expect(result.valid).toBe(false)
    expect(result.acceptedEvents).toEqual([])
    expect(result.nextCursor).toEqual(cursor)
    expect(result.issues.map(item => item.code)).toContain('EVENT_GAP')
  })

  it('rejects a broken previous-event hash', () => {
    const contract = contractFixture()
    const first = eventFixture(contract, {
      type: 'LIFECYCLE',
      checkpoint: 'WORK_STARTED',
      refs: [],
    }, 0)
    const second = eventFixture(contract, {
      type: 'LIFECYCLE',
      checkpoint: 'READY_FOR_REFLECTION',
      refs: [],
    }, 1, 'f'.repeat(64))
    const result = validateExecutionEventBatch(
      [first, second],
      contract,
      { nextSequence: 0 },
    )
    expect(result.valid).toBe(false)
    expect(result.issues.map(item => item.code)).toContain('EVENT_CONFLICT')
  })
})
