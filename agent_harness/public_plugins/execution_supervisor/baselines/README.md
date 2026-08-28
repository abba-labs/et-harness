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
