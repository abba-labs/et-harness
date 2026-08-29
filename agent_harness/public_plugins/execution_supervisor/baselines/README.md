# Phase 0 performance baselines

CI generates an environment-specific JSON report from:

```text
benchmarks/phase0-baseline.mjs
```

The report records:

```text
Node/platform/architecture
source revision
input bytes
warmup/sample count
p50/p95/p99/mean/max validation latency
mandatory efficiency invariants
```

Phase 0 does not freeze numeric SLOs. A reviewed CI report is committed only after it has been produced from the feature branch and validated by the same public contract package.

## Phase 7 regression SLO

`phase7-ci-linux-x64-node22-slo.json` is a separate reviewed profile for the
1,000-event durable Store/Ledger scenario. It does not reinterpret the Phase 0
measurement report. The benchmark fails closed unless Node, platform,
architecture, event count and replay-page limit match the profile exactly.

The initial limits come from three local WSL Node 22 linux-x64 captures. They
are deliberately an initial cross-machine guard, not a claim of multi-run
GitHub-hosted calibration. Ingest and Ledger limits are rounded above twice the
observed maximum; replay uses a conservative one-second cold-filesystem ceiling;
deterministic sizes use the next practical binary boundary. Hosted CI must bind
the report to the exact `${{ github.sha }}` before its result is described as a
CI pass.

The profile limits durable append p95, incremental Ledger transition p95,
replay duration, persisted bytes per event, compact Ledger projection bytes and
the bounded Supervisor Context delta. Runtime Context-envelope reuse, reroute,
semantic-call and Reflection invariants are enforced by the real Governance
Runtime integration test rather than inferred from the Store/Ledger benchmark.

```bash
PHASE7_TMP_ROOT=/absolute/temp/root \
PHASE7_SOURCE_REVISION=$(git rev-parse HEAD) \
npm run build

npm run benchmark:phase7 -- \
  --slo baselines/phase7-ci-linux-x64-node22-slo.json \
  --output /absolute/report/path/phase7-efficiency.json
```
