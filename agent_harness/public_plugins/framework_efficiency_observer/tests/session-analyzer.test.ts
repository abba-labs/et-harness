import { describe, expect, it } from 'vitest'
import { analyzeHarnessSessionEvents, extractHarnessSessionMetrics } from '../src/session-analyzer.js'

describe('Harness Session offline efficiency analyzer', () => {
  it('离线统计 Agent turn/step、Token 与 Tool，不依赖正文', () => {
    const events = [
      { type: 'turn/start', time: 1000, data: { turn: 1 } },
      { type: 'step/start', time: 1010, data: { turn: 1, step: 1 } },
      {
        type: 'assistant/chunk',
        time: 1020,
        data: {
          turn: 1,
          step: 1,
          chunk: {
            type: 'usage',
            usage: {
              inputTokens: 120,
              outputTokens: 30,
              cacheReadTokens: 80,
              reasoningTokens: 12,
            },
          },
        },
      },
      {
        type: 'assistant/message',
        time: 1025,
        data: {
          turn: 1,
          step: 1,
          usage: { inputTokens: 120, outputTokens: 30, cacheReadTokens: 80 },
          content: 'THIS_TEXT_MUST_NOT_ENTER_METRICS',
        },
      },
      {
        type: 'tool/call',
        time: 1030,
        data: {
          turn: 1,
          step: 1,
          callId: 'CALL-1',
          name: 'test.execute',
          arguments: '{"large":"BODY_MUST_NOT_BE_COPIED"}',
        },
      },
      {
        type: 'tool/result',
        time: 1090,
        data: {
          turn: 1,
          step: 1,
          message: {
            source: { kind: 'tool', callId: 'CALL-1' },
            content: [{
              type: 'tool-result',
              toolCallId: 'CALL-1',
              content: ['TOOL_BODY_MUST_NOT_BE_COPIED'],
              isError: false,
            }],
          },
        },
      },
      { type: 'step/end', time: 1110, data: { turn: 1, step: 1 } },
      { type: 'turn/end', time: 1120, data: { turn: 1, reason: { kind: 'stop' } } },
    ]

    const metrics = extractHarnessSessionMetrics('S1', events)
    const text = JSON.stringify(metrics)
    expect(text).not.toContain('THIS_TEXT_MUST_NOT_ENTER_METRICS')
    expect(text).not.toContain('BODY_MUST_NOT_BE_COPIED')
    expect(text).not.toContain('TOOL_BODY_MUST_NOT_BE_COPIED')

    const report = analyzeHarnessSessionEvents('S1', events)
    const runtime = report.components.find(item => item.component === 'runtime')
    const tool = report.components.find(item => item.component === 'tool')
    expect(runtime?.values.inputTokens).toBe(120)
    expect(runtime?.values.outputTokens).toBe(30)
    expect(runtime?.values.cacheReadTokens).toBe(80)
    expect(runtime?.values.reasoningTokens).toBe(12)
    expect(runtime?.operationCounts.llmUsage).toBe(1)
    expect(runtime?.operationCounts.agentStep).toBe(1)
    expect(runtime?.operationCounts.agentTurn).toBe(1)
    expect(tool?.values.toolCallCount).toBe(1)
    expect(tool?.observedDurationMs).toBe(60)
  })

  it('没有 chunk usage 时使用 assistant/message usage fallback', () => {
    const report = analyzeHarnessSessionEvents('S2', [{
      type: 'assistant/message',
      time: 1000,
      data: {
        turn: 2,
        step: 3,
        usage: { inputTokens: 10, outputTokens: 4 },
      },
    }])
    const runtime = report.components.find(item => item.component === 'runtime')
    expect(runtime?.values.inputTokens).toBe(10)
    expect(runtime?.values.outputTokens).toBe(4)
    expect(runtime?.operationCounts.llmUsage).toBe(1)
  })
})
