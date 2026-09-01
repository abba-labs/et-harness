import type {
  ProjectContextContributionProviderResult,
  ProjectContextContributionRequestV01,
} from '@agent-harness/auto-governance-engine'
import {
  ATP_REQUIRED_RESOURCE_PROVIDER_ID,
  AtpContextContributorService,
} from './context-contributor.js'

/**
 * Explicitly allows the built-in ET Harness checkpoint executor to satisfy
 * ATP validation obligations. Project-owned Gate providers remain accepted;
 * this adds one Host-independent trusted producer rather than a Codex-specific
 * provider identity.
 */
export class AtpCheckpointContextContributorService extends AtpContextContributorService {
  override contributeContext(
    request: ProjectContextContributionRequestV01,
  ): ProjectContextContributionProviderResult {
    const result = super.contributeContext(request)
    if (!result.applicable || !result.contribution.supervision) return result

    const supervision = result.contribution.supervision
    const evidencePolicies = supervision.evidencePolicies.map(policy =>
      policy.acceptedProviderKinds.includes('VALIDATOR')
        ? {
            ...policy,
            acceptedProviderIds: [
              ...new Set([
                ...policy.acceptedProviderIds,
                ATP_REQUIRED_RESOURCE_PROVIDER_ID,
              ]),
            ],
          }
        : policy,
    )

    return {
      applicable: true,
      contribution: {
        ...result.contribution,
        supervision: {
          ...supervision,
          evidencePolicies,
        },
      },
    }
  }
}

export default AtpCheckpointContextContributorService
