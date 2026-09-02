# Governance Behavioral Validation V1 Defect Backlog

No defect below was repaired during this campaign.

## GBV1-001 — ATP natural-intent classification is unstable

- Severity: P0 for automatic governance routing
- Classification: Project Plugin / wrong decision
- Expected: ET6801 XBAR task resolves `ip=xbar`.
- Actual: the English conjunction `and` was resolved as `ip=and`; governance-rich Chinese intents also returned `CONTEXT_CONTRIBUTOR_UNAVAILABLE`, while simplified intents succeeded.
- First failing boundary: ATP Task Classification / Context Contributor.
- Reproduction: `gbv1-xbar-analysis`, `gbv1-contradictory-knowledge`, `gbv1-reusable-project-knowledge`.
- Minimum review: token/alias extraction and contributor error propagation; do not weaken fail-closed routing.

## GBV1-002 — Context updates are not automatically consumed across tasks

- Severity: P0 for long-running project governance
- Classification: Public Context integration / downstream not updated
- Expected: a versioned open issue persisted at Closure is injected into a later relevant Task Context.
- Actual: the Context receipt and external state contain the issue, but a separate follow-up task receives no prior issue.
- First failing boundary: new-task Context assembly/injection.
- Reproduction: `gbv1-context-later-consumption` then `gbv1-context-later-consumption-followup`.
- Minimum review: existing Context query/merge call chain only; do not add a second Context store.

## GBV1-003 — Completion failure can poison a Turn before Reflection validation succeeds

- Severity: P0
- Classification: Public Runtime lifecycle / atomicity
- Expected: malformed Reflection is rejected before seal/state transition; corrected request can retry.
- Actual: missing `contractVersion` returned ERROR, but the Turn entered `CLOSURE_PENDING` and was sealed; corrected input was rejected.
- First failing boundary: ordering between Reflection validation and irreversible journal seal.
- Reproduction: `gbv1-restart-replay` after successful active-state rehydrate.
- Minimum review: validate complete Reflection first, then perform one idempotent seal/closure transition; preserve existing Runtime/Kernel authority.

## GBV1-004 — Persisted Project Knowledge cannot be demonstrated as consumable by the next task

- Severity: P0 for Knowledge lifecycle
- Classification: Public Knowledge + Project bootstrap integration
- Expected: Closure persists K001.014, then a later relevant task can begin and consult it.
- Actual: candidate and index persistence succeeded, but immediate next `harness_begin` returned `CONTEXT_CONTRIBUTOR_UNAVAILABLE` before context creation.
- First failing boundary: post-candidate new-task bootstrap.
- Evidence: Scenario C snapshots and closure receipt.
- Suspected condition: Knowledge Manager writes tracked project files and changes repository/project inputs; the public Gateway error hides the nested cause. This remains a hypothesis until the contributor exposes a typed reason.
- Minimum review: reconcile existing canonical Knowledge persistence with project revision/cleanliness checks and propagate the real nested error; do not create an external second Knowledge store.

## GBV1-005 — Observation-stage Knowledge contradiction is not surfaced

- Severity: P1
- Classification: Public Runtime / missed trigger
- Expected: a source-backed contradiction to routed K001.006 produces a visible CHECK/disputed decision at the appropriate governance point.
- Actual: ordinary Observation returned `knowledgeCaptureMode=NONE`; only Agent-authored Closure Reflection caused CONTRADICT persistence.
- First failing boundary: Work Observation to Knowledge Decision propagation.
- Minimum review: clarify the contractually correct trigger. If Closure-only is intentional, Task Context/Agent instructions must make that deterministic and observable; otherwise wire the existing decision path without duplicating policy.

## GBV1-006 — Experience Memory positive path is unreachable/unobservable through real MCP

- Severity: P1
- Classification: Public integration / trusted-input and observability gap
- Expected: a real evidence-backed experience candidate can be submitted, persisted, replayed and later consumed.
- Actual: MCP exposes trusted execution-event refs but no queryable Evidence State `evidence://` reference suitable for the Experience contract; `searchMemory` consumption was not observed in Context assembly.
- First failing boundary: trusted Evidence State to Reflection/Experience input bridge.
- Minimum review: expose or derive only Runtime-owned evidence references through existing contracts; never accept caller-forged evidence.

## GBV1-007 — Route and provider decisions lack sufficient direct evidence

- Severity: P1
- Classification: Public observability gap
- Affected: live Catalog, Architecture candidate trace, Rule rejection trace, Knowledge consultation trust tier, Gate provider/evidence packet, Auto Governance decision trace.
- Actual: final selected IDs/obligations are visible, but exact candidates, rejection reasons and provider identities are not queryable or durable.
- Minimum review: bounded read-only receipts/traces from existing owners; no watcher, daemon or second Runtime.

## GBV1-008 — Ordinary work observation body is not proven durable

- Severity: P1
- Classification: Public Runtime replay gap
- Expected: stateful observation semantics required for later governance decisions survive restart.
- Actual: journal persists observation/event/resource references, but not the submitted semantic summary; replay of the body cannot be proven.
- Minimum review: define which observation fields are durable and bind them to the existing Event Store if required.

## GBV1-009 — Codex Desktop stale MCP transport does not reconnect after Gateway appears

- Severity: Host integration issue; excluded from Framework acceptance
- Classification: Codex Desktop transport lifecycle
- Expected: optional MCP worker reconnects after external Gateway becomes available.
- Actual: Desktop calls timed out while direct MCP and `/health` passed.
- Boundary: request did not enter Gateway/Runtime.
- This must not be repaired in Framework, Runtime or ATP Project Plugin.

## Project-content gaps, not Framework defects

- `K001.006` is stale: it says six modules while the current map has nine. The Knowledge Verification path correctly persisted a CONTRADICT when supplied at Closure.
- XBAR public/chip contract documents are absent. A2 checkpoint correctly failed closed; this is an ATP project artifact gap, not a governance failure.
