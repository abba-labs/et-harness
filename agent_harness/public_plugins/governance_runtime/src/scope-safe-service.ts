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
    // Preserve the canonical Runtime identity/Turn/policy checks first. Under
    // ENFORCE this already performs the scope check and also verifies the Host
    // interception/event-identity contract.
    const base = super.preflightAction(input)
    if (!base.allowed || input.effect?.kind !== 'MUTATION') return base

    // AUDIT cannot claim universal Host interception, but an explicit preflight
    // still has a frozen Task Contract and therefore must answer scope truthfully.
    const contract = this.getStatus(input.runtimeId)?.supervision?.ledger.binding.contract
    if (!contract) return base
    const scope = evaluateMutationPreflight(contract, input.effect.intent)
    if (!scope.allowed) {
      return {
        allowed: false,
        reason: scope.reason ?? 'Mutation is outside the governed WRITE_SCOPE.',
      }
    }
    return base
  }
}

export default ScopeSafeGovernanceRuntimeService
