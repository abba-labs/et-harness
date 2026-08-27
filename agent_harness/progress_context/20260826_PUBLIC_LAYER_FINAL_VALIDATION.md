# Public Layer Final Validation

Date: 2026-08-26
Branch: `fix/public-layer-validation-smoke-v0.1`
Status: VALIDATION IN PROGRESS

## Confirmed root cause

`phase3_knowledge_validation_policy_v0_1_integration.sh` registered its second Global SUPPORT as a `CODE` Source. The production policy intentionally classifies `CODE` as `REFERENCE`; only `DOCUMENT`, `SPEC`, and `SVD` count toward the document-validation quorum. The old Smoke therefore expected `READY` from data that could only produce one document-level SUPPORT.

## Minimal correction

- Keep production policy unchanged.
- Assert that a CODE SUPPORT remains visible but does not satisfy document quorum.
- Add a second independent SVD Source before expecting Global `READY`.
- Keep the CONTRADICT test on a candidate that already has enough document-level SUPPORT.

## Required final gates

- Public Layer v0.2 full workflow.
- Real Task Matrix.
- Positive Runtime / closed-loop validation.
- Round A adversarial governance.
- Round B knowledge adversarial.
- Post-merge main-branch regression.

Final run IDs, commit SHAs, and results will be appended after all gates complete.
