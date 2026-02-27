# Deviation Log: Constants Remediation Sweep

Feature 028 — Phase 3 (US1, FR-005).

Documents all behavioral deviations from pre-remediation baselines.

## Regression Test Results

**Date**: 2026-02-27
**Baselines**: Generated at Phase 1 (T001), regenerated after Phase 2 TopologyDefines changes.
**Comparison**: `mise run qa:regression` — 5/5 scenarios PASS.

| Scenario | Status | Notes |
|----------|--------|-------|
| imperial_circuit | PASS | No deviation |
| two_node | PASS | No deviation |
| starvation | PASS | No deviation |
| glut | PASS | No deviation |
| fascist_bifurcation | PASS | No deviation |

## Phase 2 (US2) Deviations

**None.** Tier B elimination (constant deletion and import redirects) produced
zero behavioral change. All 5 regression scenarios match Phase 1 baselines
after baseline regeneration for GameDefines hash changes (5 new TopologyDefines
fields changed the `defines_hash`).

### Baseline Regeneration Events

1. **After T005** (add 5 TopologyDefines fields): `defines_hash` changed from
   pre-remediation value. Baselines regenerated with `mise run qa:regression-generate`.
   No metric values changed — only the hash metadata.

## Phase 3 (US1) Deviations

**None.** The Tier A constant hydration functions only activate when
`Simulation.from_sqlite()` is called with actual FIPS codes pointing to
populated database records. The standard regression test scenarios use
`GameDefines()` defaults directly and do not trigger the hydration path.

### Why No Deviation

The wiring code in `simulation.py:from_sqlite()` follows the safe override pattern:

```python
if economy_data.get("extraction_efficiency") is not None:
    updates["economy"] = defines.economy.model_copy(
        update={"extraction_efficiency": economy_data["extraction_efficiency"]}
    )
```

This only overrides when data is successfully derived. If no data is found,
the GameDefines defaults are preserved unchanged. The regression scenarios
do not connect to the SQLite reference database, so the hydration path
is never exercised.

### Integration Test Validation

The hydration functions are validated by dedicated integration tests in
`tests/integration/test_constant_hydration.py` which run against the
actual `marxist-data-3NF.sqlite` database:

- `test_wayne_county_returns_valid_shares` — class shares from QCEW
- `test_shares_sum_to_one` — class distribution completeness
- `test_wayne_county_extraction_efficiency` — extraction from tensor
- `test_wayne_county_shadow_wage` — wage derivation from QCEW
- `test_wayne_county_sigmoid_r0` — unemployment proxy

## Summary

| Phase | Constants Changed | Regressions | Deviations | Action |
|-------|------------------|-------------|------------|--------|
| Phase 2 (US2) | 0 (deletions only) | 5/5 PASS | 0 | None required |
| Phase 3 (US1) | 3 wired (conditional) | 5/5 PASS | 0 | None required |

**Conclusion**: All remediation work through Phase 3 is behavior-preserving for
existing regression scenarios. Data-derived values are only injected when
the full `from_sqlite()` initialization path is used with valid database data.
