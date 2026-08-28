import {
  EXECUTION_EVENT_SCHEMA,
  EXECUTION_SUPERVISOR_CONTRACT_VERSION,
  TASK_SUPERVISION_CONTRACT_SCHEMA,
  type ExecutionEvent,
  type ExecutionEventDraft,
  type TaskSupervisionContract,
} from './contracts.js'
import {
  executionEventPayloadHash,
  sealExecutionEvent,
  taskSupervisionContractHash,
} from './canonical.js'

export type TaskSupervisionContractInput = Omit<
  TaskSupervisionContract,
  'schema' | 'contractVersion' | 'contractHash'
>

export const createTaskSupervisionContract = (
  input: TaskSupervisionContractInput,
): TaskSupervisionContract => {
  const unsigned: Omit<TaskSupervisionContract, 'contractHash'> = {
    schema: TASK_SUPERVISION_CONTRACT_SCHEMA,
    contractVersion: EXECUTION_SUPERVISOR_CONTRACT_VERSION,
    ...input,
  }
  return {
    ...unsigned,
    contractHash: taskSupervisionContractHash(unsigned),
  }
}

export type ExecutionEventInput = Omit<
  ExecutionEventDraft,
  'schema' | 'contractVersion' | 'payloadHash'
>

export const createExecutionEvent = (
  input: ExecutionEventInput,
): ExecutionEvent => sealExecutionEvent({
  schema: EXECUTION_EVENT_SCHEMA,
  contractVersion: EXECUTION_SUPERVISOR_CONTRACT_VERSION,
  ...input,
  payloadHash: executionEventPayloadHash(input.payload),
})
