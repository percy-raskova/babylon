# Proof: E:068 Completion Slice — BEA Share Wiring Baseline Change

**Spec**: 068-bea-national-io-ingest (T056-T058 completion)
**Branch**: `068-bea-io-completion-slice`
**Base**: `ee357172` (spec-102 post-fix HEAD)
**Date**: 2026-07-04

## What Changed

The hardcoded `_INTERMEDIATE_INPUTS_FRACTION = 0.5` in `hex_hydrator.py` was replaced with per-county BEA industry-mix lookups via `BEAShareLookupService.lookup_county_share(county_fips, year).intermediate_inputs_share`.

This changes the constant capital `c` computation for every county:
- **Pre-wiring**: `c = GDP × 0.5 / 52` (uniform fraction)
- **Post-wiring**: `c = GDP × bea_share / 52` (QCEW-employment-weighted BEA industry share)

No other economic primitive changed: `v` (QCEW wages), `s = max(0, GDP/52 - v)`, `k = 3.0 × GDP` are all independent of the intermediate inputs share.

## Why It's Correct

1. **Constitutional mandate (III.1 no-magic-numbers)**: The 0.5 constant was a spec-066 placeholder explicitly deferred to spec-068 ("deferred to spec-068" marker at `hex_hydrator.py:106`). The BEA share lookup replaces it with grounded, per-county data from `fact_bea_national_industry` (1,065 rows) via QCEW-employment-weighted concordance.

2. **Constitutional mandate (III.8 data-grounding)**: Every county's `c` value now traces to real BEA data through the concordance chain: `fact_qcew_annual → bridge_naics_bea → fact_bea_national_industry`. The 0.5 fallback remains only for `global_default` cases (no BEA data for that county/year — 0% of QCEW employment affected per SC-008).

3. **SC-005 gate**: stddev(c/v) across 83 MI counties increased from 0.271 (pre-wiring, constant 0.5) to 0.393 (post-wiring, per-county BEA shares). The 0.2 directional threshold is met. The pre-wiring 0.271 is genuine (GDP-to-wage ratio variation across counties), and the BEA wiring adds +0.122 of industry-mix variation on top.

4. **SC-008 gate**: 0% of QCEW employment affected by stale fallback (all 71 BEA industries have data for all years 2010-2024). Threshold < 1% met.

## Magnitude

| Baseline | total_c | total_v | total_s | total_k | max_tension | liveness |
|---|---|---|---|---|---|---|
| **Tri-county 5t (old)** | 1,759,843,202 | 1,496,702,270 | 2,022,984,134 | 549,071,079,000 | 0.667728 | 3/3 |
| **Tri-county 5t (new)** | 1,947,426,031 | 1,496,702,270 | 2,022,984,134 | 549,071,079,000 | 0.667728 | 3/3 |
| **Delta** | +10.66% | 0% | 0% | 0% | 0% | unchanged |
| **Michigan 520t (old)** | 3,780,573,500 | 3,126,580,386 | 4,434,566,613 | 1,179,538,932,000 | 0.667305 | 83/83 |
| **Michigan 520t (new)** | 4,107,365,647 | 3,126,580,386 | 4,434,566,613 | 1,179,538,932,000 | 0.667305 | 83/83 |
| **Delta** | +8.64% | 0% | 0% | 0% | 0% | unchanged |

The aggregate `total_c` increased because high-GDP counties tend to have manufacturing-heavy industry mixes with `ii_share > 0.5`. Individual counties moved in both directions (e.g., Oakland 26099: c +33.6%, Macomb 26125: c -10.5%), producing the heterogeneous c/v distribution SC-005 requires.

## Tri-County Baseline Structural Note

The `detroit-tri-county-5t.json` `external_node_flows` also changed structurally (3 county-FIPS entries → 6 external geographic entries). This is NOT from the BEA share wiring — the tri-county baseline was stale, last regenerated at spec-101's `e059e50e` commit. The E:068 refresh correctly picked up spec-101/102's external-node flow reporting changes (re-keying from county-FIPS to bloc-level entries per finding #5 of the spec-101 review). This is a one-time catch-up; the Michigan 520-tick baseline does not have this issue (its `external_node_flows` were already at external-node level).

## Determinism

The BEA lookup is a pure function of `(county_fips, year, SQLite reference state)`. The reference DB is immutable during runs. Determinism (III.7) is preserved — the same config + reference DB produces byte-identical output across runs.

## Bug Fix

A Python falsy-zero bug was found and fixed in `stale_share_summary.py:127-129`: `float(row.affected_fraction or 1.0)` returned 1.0 when the fraction was 0.0 (Python treats 0.0 as falsy). Replaced with explicit `None` check: `float(row.affected_fraction) if row.affected_fraction is not None else 1.0`. The unit test `test_full_coverage_yields_zero_affected_fraction` validates this fix (would FAIL against the buggy code).
