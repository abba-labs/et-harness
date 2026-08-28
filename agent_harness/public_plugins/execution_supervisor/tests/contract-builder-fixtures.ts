import {
  EXECUTION_SUPERVISOR_CONTRACT_VERSION,
  PROJECT_SUPERVISION_CONTRIBUTION_SCHEMA,
  type ProjectSupervisionContribution,
  type TaskSupervisionBuildInput,
} from '../src/index.js'
import { correlation, hash } from './fixtures.js'

export const authorizedSourceRefs = [
  'architecture:A100',
  'rule:R100',
  'rule:R110',
  'knowledge:K100',
  'gate:G100',
  'provider://synthetic-project/context',
] as const

export const contributionFixture = (
  contributionId = 'synthetic-project-obligations',
): ProjectSupervisionContribution => ({
  schema: PROJECT_SUPERVISION_CONTRIBUTION_SCHEMA,
  contractVersion: EXECUTION_SUPERVISOR_CONTRACT_VERSION,
  contributionId,
  projectId: correlation.projectId,
  taskId: correlation.taskId,
  provenance: 'provider://synthetic-project/context',
  obligations: [
    {
      obligationId: 'PROJECT.READ.REQUIRED-SPEC',
      kind: 'RESOURCE_READ',
      level: 'MUST',
      title: 'Read the required project specification',
      description: 'The governed Agent must produce a source receipt for the required project specification.',
      sourceRefs: ['rule:R100'],
      target: {
        resourceRefs: ['source://project/synthetic-project/specification'],
      },
      evidencePolicy: {
        acceptableAuthorities: ['EXTERNAL_SOURCE', 'TOOL_GATEWAY'],
        acceptedOutcomes: ['FOUND'],
        minimumReceipts: 1,
        allowAgentDeclaration: false,
        requireCurrentRevision: true,
        requireContentHash: true,
      },
    },
    {
      obligationId: 'PROJECT.OUTPUT.REQUIRED',
      kind: 'OUTPUT_PRESENT',
      level: 'MUST',
      title: 'Create the required project output',
      description: 'The Host must report the required output as present with a stable content hash.',
      sourceRefs: ['rule:R110'],
      target: {
        outputIds: ['project-output'],
      },
      evidencePolicy: {
        acceptableAuthorities: ['HOST', 'TOOL_GATEWAY'],
        acceptedOutcomes: ['PRESENT'],
        minimumReceipts: 1,
        allowAgentDeclaration: false,
        requireContentHash: true,
      },
    },
    {
      obligationId: 'PROJECT.VALIDATION.REQUIRED',
      kind: 'VALIDATION',
      level: 'MUST',
      title: 'Run the project validator',
      description: 'Only the declared project validator may produce PASS Evidence for this obligation.',
      sourceRefs: ['gate:G100'],
      target: {
        validationIds: ['synthetic-project-validator'],
      },
      evidencePolicy: {
        acceptableAuthorities: ['PROJECT_VALIDATOR'],
        acceptedOutcomes: ['PASS'],
        minimumReceipts: 1,
        allowAgentDeclaration: false,
        requireCurrentRevision: true,
      },
    },
  ],
})

export const buildInputFixture = (): TaskSupervisionBuildInput => ({
  requestedMode: 'AUDIT',
  correlation,
  binding: {
    sourceHead: '0123456789abcdef',
    taskContextHash: hash('1'),
    contextHash: hash('2'),
    routeHash: hash('3'),
    scopeHash: hash('4'),
    outputContractHash: hash('5'),
  },
  authorizedSourceRefs,
  projectContributions: [contributionFixture()],
  hostCapabilities: {
    hostId: 'generic-external-chat-host',
    adapterId: 'generic-external-chat-adapter',
    executionEventStream: true,
    crossProcessReplay: true,
    preExecutionActionGuard: false,
    mechanicalToolInterception: false,
  },
  maxBatchEvents: 128,
})
