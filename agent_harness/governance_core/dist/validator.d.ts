import type { GovernanceAdmissionDecision, GovernanceCapabilityContract, GovernanceManifest } from './contracts.js';
export declare function validateGovernanceManifest(manifest: GovernanceManifest, knownCapabilities: ReadonlyMap<string, GovernanceCapabilityContract>): GovernanceAdmissionDecision;
