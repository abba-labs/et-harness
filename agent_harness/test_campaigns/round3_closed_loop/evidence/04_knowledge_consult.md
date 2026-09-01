# R3-04 Knowledge consultation

- Runtime observe decision: `consultMode=OPTIONAL`, `captureMode=NONE`, `validationMode=NONE`.
- Deterministic signal: `ROUTED_KNOWLEDGE_AVAILABLE`.
- Routed IDs included `K001`, `K001.001`, `.002`, `.003`, `.004`, `.005`, `.007`, `.008`, `.012`.
- Normal project index resolved these to `agent_harness/projects/automated_testing_platform/knowledge/001_library.md`; routed VALIDATED facts were consulted without injecting them into the user task text.
- Result: `TRIGGERED_PASS`, enforcement `WORKFLOW_ENFORCED` for consultation. Runtime, not the Agent, classified capture as `NONE`.
