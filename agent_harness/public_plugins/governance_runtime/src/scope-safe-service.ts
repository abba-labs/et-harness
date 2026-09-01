import { evaluateMutationPreflight } from '@agent-harness/execution-supervisor'
import type {
  GovernanceActionPreflightInput,
  GovernanceActionPreflightResult,
} from './contracts.js'
import GovernanceRuntimeService from './service.js'

/**
 * Keeps deterministic Task Contract scope checks active for every explicit
 * Runtime preflight, even when a Host can only negotiate AUDIT supervision.
 *
 * AUDIT still does not claim that the Host intercepts every native tool call.
 * This only makes an explicit preflight truthful and fail-closed for mutations.
 */
export class ScopeSafeGovernanceRuntimeService extends GovernanceRuntimeService {
  override preflightAction(
    input: GovernanceActionPreflightInput,
  ): GovernanceActionPreflightResult {
    if (input.effect?.kind === 'MUTATION') {
      const contract = this.getStatus(input.runtimeId)?.supervision?.ledger.binding.contract
      if (contract) {
        const scope = evaluateMutationPreflight(contract, input.effect.intent)
        if (!scope.allowed) {
          return {
            allowed: false,
            reason: scope.reason ?? 'Mutation is outside the governed WRITE_SCOPE.',
          }
        }
      }
    }
    return super.preflightAction(input)
  }
}

export default ScopeSafeGovernanceRuntimeService
