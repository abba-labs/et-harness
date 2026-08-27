import type { GovernanceSemanticRequest } from '@agent-harness/governance-runtime'
import type { GovernedModelWorkRequest } from './contracts.js'

const stringArray = (): Readonly<Record<string, unknown>> => ({
  type: 'array',
  items: { type: 'string' },
})

const candidateSchema = (domain: string): Readonly<Record<string, unknown>> => ({
  type: 'object',
  additionalProperties: false,
  required: [
    'domain',
    'title',
    'factOrProposal',
    'scopeDecision',
    'rationale',
    'provenanceRefs',
    'evidenceRefs',
    'relatedRefs',
    'confidence',
  ],
  properties: {
    domain: { const: domain },
    title: { type: 'string', minLength: 1 },
    factOrProposal: { type: 'string', minLength: 1 },
    scopeDecision: { enum: ['PROJECT', 'PUBLIC', 'BOTH'] },
    rationale: { type: 'string', minLength: 1 },
    provenanceRefs: stringArray(),
    evidenceRefs: stringArray(),
    relatedRefs: stringArray(),
    confidence: { type: 'number', minimum: 0, maximum: 1 },
  },
})

const scopedSection = (domain: string): Readonly<Record<string, unknown>> => ({
  type: 'object',
  additionalProperties: false,
  required: ['scopeDecision', 'rationale', 'candidates'],
  properties: {
    scopeDecision: { enum: ['NONE', 'PROJECT', 'PUBLIC', 'BOTH'] },
    rationale: { type: 'string', minLength: 1 },
    candidates: {
      type: 'array',
      items: candidateSchema(domain),
    },
  },
})

export const TURN_REFLECTION_JSON_SCHEMA: Readonly<Record<string, unknown>> = {
  type: 'object',
  additionalProperties: false,
  required: [
    'contractVersion',
    'taskId',
    'turnId',
    'context',
    'knowledge',
    'experience',
    'architecture',
    'rules',
    'evidence',
    'workingSet',
    'obligations',
  ],
  properties: {
    contractVersion: { const: '0.1' },
    taskId: { type: 'string', minLength: 1 },
    turnId: { type: 'string', minLength: 1 },
    context: {
      type: 'object',
      additionalProperties: false,
      required: [
        'progress',
        'decisions',
        'confirmed',
        'assumptions',
        'openIssues',
        'next',
        'touchedRefs',
      ],
      properties: {
        progress: { type: 'string', minLength: 1 },
        decisions: stringArray(),
        confirmed: stringArray(),
        assumptions: stringArray(),
        openIssues: stringArray(),
        next: stringArray(),
        touchedRefs: stringArray(),
      },
    },
    knowledge: scopedSection('knowledge'),
    experience: scopedSection('experience'),
    architecture: scopedSection('architecture'),
    rules: scopedSection('rules'),
    evidence: scopedSection('evidence'),
    workingSet: {
      type: 'object',
      additionalProperties: false,
      required: ['keep', 'add', 'remove'],
      properties: {
        keep: stringArray(),
        add: stringArray(),
        remove: stringArray(),
      },
    },
    obligations: {
      type: 'object',
      additionalProperties: false,
      required: ['opened', 'resolved', 'unchanged'],
      properties: {
        opened: stringArray(),
        resolved: stringArray(),
        unchanged: stringArray(),
      },
    },
  },
}

export const renderGovernedWorkPrompt = (request: GovernedModelWorkRequest): {
  readonly systemText: string
  readonly userText: string
} => ({
  systemText: [
    'You are the business-work model inside a governed software-engineering runtime.',
    'Complete the user business task using the supplied Governance Context as binding project context.',
    'MUST/MUST_NOT rules and mandatory gates in that context are binding.',
    'Knowledge consultation is governed by the supplied Knowledge Decision: OPTIONAL means use only when useful; REQUIRED means consider the routed knowledge, but you may reject it when evidence or task context shows it is not applicable.',
    'Do not perform Governance Reflection or persistence classification here; the Runtime performs that automatically after work.',
    'Return only the user-visible work answer. Do not expose hidden chain-of-thought or private reasoning.',
  ].join(' '),
  userText: [
    'BUSINESS TASK (verbatim):',
    request.taskText,
    '',
    'KNOWLEDGE ENGAGEMENT DECISION:',
    JSON.stringify(request.knowledgeDecision),
    '',
    'AUTOMATIC GOVERNANCE CONTEXT:',
    request.context.text,
  ].join('\n'),
})

export const renderGovernanceReflectionPrompt = (request: GovernanceSemanticRequest): {
  readonly systemText: string
  readonly userText: string
} => ({
  systemText: [
    'You are the semantic Reflection executor for a host/model-independent governance runtime.',
    'Return exactly one JSON object matching the supplied TurnReflectionResult schema.',
    'Use only the supplied Governance Context and bounded Turn Observations as evidence.',
    'Never expose or invent hidden chain-of-thought. Rationale fields must be short decision summaries, not reasoning transcripts.',
    'Do not wrap the JSON in Markdown and do not add prose before or after it.',
  ].join(' '),
  userText: JSON.stringify({
    runtimeRequest: request,
    outputSchema: TURN_REFLECTION_JSON_SCHEMA,
  }),
})
