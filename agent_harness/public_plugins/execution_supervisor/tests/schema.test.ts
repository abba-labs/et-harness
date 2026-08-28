import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import {
  ARTIFACT_ACTIONS,
  CLAIM_STATES,
  COMPLETION_STATUSES,
  EXECUTION_EVENT_KINDS,
  EXECUTION_EVENT_OUTCOMES,
  EXECUTION_RISK_LEVELS,
  EXECUTION_SUPERVISION_MODES,
  OBLIGATION_KINDS,
  OBLIGATION_LEVELS,
  OBLIGATION_STATUSES,
  RESOURCE_ACTIONS,
  RESOURCE_KINDS,
  SUPERVISION_VIOLATION_KINDS,
  VALIDATION_OUTCOMES,
} from '../src/contracts.js'

const schemaPath = resolve(
  import.meta.dirname,
  '../schemas/execution-supervisor-v0.1.schema.json',
)
const schema = JSON.parse(readFileSync(schemaPath, 'utf8')) as any
const definitions = schema.$defs as Record<string, any>

describe('Execution Supervisor language-neutral JSON Schema', () => {
  it('parses and exposes every public wire-contract root', () => {
    expect(schema.$schema).toBe('https://json-schema.org/draft/2020-12/schema')
    expect(schema.$id).toContain('execution-supervisor-v0.1.schema.json')
    expect(schema.oneOf.map((item: any) => item.$ref)).toEqual(expect.arrayContaining([
      '#/$defs/TaskSupervisionContract',
      '#/$defs/ExecutionEvent',
      '#/$defs/ExecutionEventBatch',
      '#/$defs/ExecutionReceipt',
      '#/$defs/ObligationLedger',
      '#/$defs/SupervisionViolation',
      '#/$defs/CompletionDecision',
    ]))
  })

  it('keeps TypeScript and JSON Schema enums in one semantic version', () => {
    expect(definitions.TaskSupervisionContract.properties.mode.enum)
      .toEqual([...EXECUTION_SUPERVISION_MODES])
    expect(definitions.ExecutionEvent.properties.kind.enum)
      .toEqual([...EXECUTION_EVENT_KINDS])
    expect(definitions.ExecutionEvent.properties.payload.properties.outcome.enum)
      .toEqual([...EXECUTION_EVENT_OUTCOMES])
    expect(definitions.ResourceDescriptor.properties.kind.enum)
      .toEqual([...RESOURCE_KINDS])
    expect(definitions.ResourceDescriptor.properties.action.enum)
      .toEqual([...RESOURCE_ACTIONS])
    expect(definitions.ArtifactDescriptor.properties.action.enum)
      .toEqual([...ARTIFACT_ACTIONS])
    expect(definitions.ValidationDescriptor.properties.outcome.enum)
      .toEqual([...VALIDATION_OUTCOMES])
    expect(definitions.ClaimDescriptor.properties.assertedState.enum)
      .toEqual([...CLAIM_STATES])
    expect(definitions.ObligationDefinition.properties.kind.enum)
      .toEqual([...OBLIGATION_KINDS])
    expect(definitions.ObligationDefinition.properties.level.enum)
      .toEqual([...OBLIGATION_LEVELS])
    expect(definitions.ObligationDefinition.properties.risk.enum)
      .toEqual([...EXECUTION_RISK_LEVELS])
    expect(definitions.ObligationState.properties.status.enum)
      .toEqual([...OBLIGATION_STATUSES])
    expect(definitions.SupervisionViolation.properties.kind.enum)
      .toEqual([...SUPERVISION_VIOLATION_KINDS])
    expect(definitions.CompletionDecision.properties.status.enum)
      .toEqual([...COMPLETION_STATUSES])
  })

  it('contains no ATP, chip, IP or model-provider specialization', () => {
    const text = readFileSync(schemaPath, 'utf8')
    expect(text).not.toMatch(/ET6801|eTimer|automated[-_]testing[-_]platform/i)
    expect(text).not.toMatch(/OpenAI|Anthropic|Claude|DeepSeek|Codex|ChatGPT/i)
  })
})
