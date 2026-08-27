import { describe, expect, it } from 'vitest'
import {
  classifyEtToolChangeScope,
  reviewGuidanceFor,
} from '../src/review-service.js'

describe('ET-TOOL Code Review Adapter helpers', () => {
  it('识别 chip-local UART GUI 修改且不误判为 shared', () => {
    const scope = classifyEtToolChangeScope([
      'source/apps/gui/chips/et6003/uart/et6003_uart_panel.cpp',
    ])
    expect(scope.chips).toEqual(['ET6003'])
    expect(scope.routes).toEqual(['UART'])
    expect(scope.layers).toEqual(['GUI'])
    expect(scope.sharedLayerChange).toBe(false)
  })

  it('识别无 chip 归属的 shared protocol/transport 修改', () => {
    const scope = classifyEtToolChangeScope([
      'source/protocol/can/can_frame_codec.cpp',
      'source/transport/can/zlg_can_transport.cpp',
    ])
    expect(scope.routes).toEqual(['CAN'])
    expect(scope.layers).toEqual(['PROTOCOL', 'TRANSPORT'])
    expect(scope.sharedLayerChange).toBe(true)
  })

  it('validation.plan guidance 明确只规划不执行验证', () => {
    expect(reviewGuidanceFor('validation.plan').join(' ')).toContain('do not execute it')
  })
})
