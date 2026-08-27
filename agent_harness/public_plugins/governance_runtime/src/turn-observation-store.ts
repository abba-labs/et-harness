import { createHash } from 'node:crypto'
import type { GovernanceTurnObservation, GovernanceTurnObservationKind } from './contracts.js'

export const MAX_GOVERNANCE_OBSERVATION_CHARS = 12_000
export const MAX_GOVERNANCE_TURN_OBSERVATION_CHARS = 64_000
export const MAX_GOVERNANCE_TURN_OBSERVATIONS = 64

interface PutObservationInput {
  readonly taskId: string
  readonly turnId: string
  readonly kind: GovernanceTurnObservationKind
  readonly text?: string | undefined
  readonly refs?: readonly string[] | undefined
  readonly sourceName?: string | undefined
  readonly isError?: boolean | undefined
}

const keyOf = (taskId: string, turnId: string): string => `${taskId}::${turnId}`

const unique = (values: readonly string[]): string[] =>
  [...new Set(values.map(value => value.trim()).filter(Boolean))]

const digestOf = (value: unknown): string =>
  createHash('sha256').update(JSON.stringify(value)).digest('hex')

export class GovernanceTurnObservationStore {
  private readonly observations = new Map<string, GovernanceTurnObservation[]>()

  put(input: PutObservationInput): GovernanceTurnObservation {
    const key = keyOf(input.taskId, input.turnId)
    const current = this.observations.get(key) ?? []
    if (current.length >= MAX_GOVERNANCE_TURN_OBSERVATIONS) {
      throw new Error(
        `Turn ${input.turnId} exceeded ${MAX_GOVERNANCE_TURN_OBSERVATIONS} governed observations`,
      )
    }

    const alreadyStoredChars = current.reduce((sum, item) => sum + item.text.length, 0)
    const remainingTurnChars = Math.max(
      0,
      MAX_GOVERNANCE_TURN_OBSERVATION_CHARS - alreadyStoredChars,
    )
    const rawText = input.text?.trim() ?? ''
    const permittedChars = Math.min(MAX_GOVERNANCE_OBSERVATION_CHARS, remainingTurnChars)
    const text = rawText.slice(0, permittedChars)
    const truncated = text.length < rawText.length
    const refs = unique(input.refs ?? [])
    const sourceName = input.sourceName?.trim() || undefined
    const sequence = current.length + 1
    const digest = digestOf({
      taskId: input.taskId,
      turnId: input.turnId,
      sequence,
      kind: input.kind,
      text,
      refs,
      sourceName,
      isError: input.isError === true,
      truncated,
    })
    const observationId = `OBS-${String(sequence).padStart(4, '0')}`
    const observationRef =
      `governance-observation://task/${input.taskId}/turn/${input.turnId}/${observationId}/sha256:${digest}`
    const observation: GovernanceTurnObservation = {
      observationId,
      observationRef,
      kind: input.kind,
      text,
      refs,
      truncated,
      ...(sourceName ? { sourceName } : {}),
      ...(input.isError !== undefined ? { isError: input.isError } : {}),
    }
    this.observations.set(key, [...current, observation])
    return observation
  }

  list(taskId: string, turnId: string): readonly GovernanceTurnObservation[] {
    return [...(this.observations.get(keyOf(taskId, turnId)) ?? [])]
  }

  clearTurn(taskId: string, turnId: string): void {
    this.observations.delete(keyOf(taskId, turnId))
  }

  clear(): void {
    this.observations.clear()
  }
}
