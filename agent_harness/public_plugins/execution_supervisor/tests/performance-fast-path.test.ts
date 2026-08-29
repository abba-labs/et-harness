import { stat } from 'node:fs/promises'
import { resolve } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import {
  createFileExecutionEventStore,
  percentile,
  type ExecutionReplayCursorV01,
} from '../src/index.js'
import {
  createSyntheticTempDirectory,
  removeSyntheticTempDirectory,
  syntheticBinding,
  syntheticEvent,
} from './fixtures/synthetic-fixtures.js'

const directories: string[] = []

afterEach(async () => {
  await Promise.all(directories.splice(0).map(removeSyntheticTempDirectory))
})

describe('Phase 1 bounded fast path', () => {
  it('measures 1000 durable appends and paginated replay without freezing an SLO', async () => {
    const directory = await createSyntheticTempDirectory('performance-')
    directories.push(directory)
    const eventCount = 1_000
    const replayLimit = 128
    const events = Array.from(
      { length: eventCount },
      (_, index) => syntheticEvent(index + 1),
    )
    const heapBefore = process.memoryUsage().heapUsed
    const totalStart = process.hrtime.bigint()
    const store = await createFileExecutionEventStore({
      directory,
      binding: syntheticBinding(),
      limits: {
        maxEvents: eventCount,
        maxStoreBytes: 32 * 1024 * 1024,
        maxReplayEvents: replayLimit,
      },
    })

    const appendDurationsMicros: number[] = []
    for (const event of events) {
      const start = process.hrtime.bigint()
      const acceptance = await store.append(event)
      appendDurationsMicros.push(Number(process.hrtime.bigint() - start) / 1_000)
      expect(acceptance.status).toBe('ACCEPTED')
    }
    const totalWallMillis = Number(process.hrtime.bigint() - totalStart) / 1_000_000

    const replayStart = process.hrtime.bigint()
    const replayed = []
    let after: ExecutionReplayCursorV01 | undefined
    let finalCursor = store.cursor
    let hasMore = true
    while (hasMore) {
      const page = await store.replay(after === undefined
        ? { limit: replayLimit }
        : { after, limit: replayLimit })
      replayed.push(...page.events)
      finalCursor = page.cursor
      hasMore = page.hasMore
      after = page.cursor
    }
    const replayWallMillis = Number(process.hrtime.bigint() - replayStart) / 1_000_000
    const heapDeltaBytes = Math.max(0, process.memoryUsage().heapUsed - heapBefore)
    const manifestBytes = (await stat(resolve(directory, 'manifest.json'))).size
    const eventBytes = (await stat(resolve(directory, 'events.jsonl'))).size
    const persistedBytesPerEvent = (manifestBytes + eventBytes) / eventCount
    const appendP50Micros = percentile(appendDurationsMicros, 0.50)
    const appendP95Micros = percentile(appendDurationsMicros, 0.95)

    expect(store.eventCount).toBe(eventCount)
    expect(replayed).toEqual(events)
    expect(replayed.map(event => event.sequence)).toEqual(
      Array.from({ length: eventCount }, (_, index) => index + 1),
    )
    expect(replayed.map(event => event.payloadHash)).toEqual(
      events.map(event => event.payloadHash),
    )
    expect(finalCursor).toEqual(store.cursor)
    expect(finalCursor.sequence).toBe(eventCount)
    for (const measurement of [
      appendP50Micros,
      appendP95Micros,
      replayWallMillis,
      totalWallMillis,
      persistedBytesPerEvent,
      heapDeltaBytes,
    ]) {
      expect(Number.isFinite(measurement)).toBe(true)
      expect(measurement).toBeGreaterThanOrEqual(0)
    }
    expect(appendP95Micros).toBeGreaterThanOrEqual(appendP50Micros)
    expect(persistedBytesPerEvent).toBeGreaterThan(0)
    await store.close()
  }, 120_000)
})
