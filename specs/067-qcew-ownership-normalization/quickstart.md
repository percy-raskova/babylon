# Spec-067 Quickstart — QCEW Normalization Operator Guide

**Branch**: `067-qcew-ownership-normalization` | **Plan**: [plan.md](./plan.md) | **Estimated wallclock**: ~10–15 minutes

This guide walks an operator through running the spec-067 migration end-to-end, from pre-flight checks through the regenerated michigan-e2e baseline. Every step is recorded; every step is reversible until the explicit cleanup at the end.

---

## Prerequisites

| Check | Command | Expected |
|---|---|---|
| On the right branch | `git branch --show-current` | `067-qcew-ownership-normalization` |
| Reference DB present | `ls -lh data/sqlite/marxist-data-3NF.sqlite` | ~8.79 GB |
| Disk space free | `df -h .` (the project directory) | ≥ 15 GB free (peak during backup is ~12 GB SQLite + ~1 GB working) |
| Python env synced | `poetry env info` | python 3.12+, project venv active |
| pre-commit installed | `git config --get core.hooksPath || ls .git/hooks/pre-commit` | hook present (per CLAUDE.md setup) |

If any check fails, STOP. The migration assumes a clean working environment.

---

## Phase 1 — Pre-flight dry-run

Verify the migration's predicate matches the current data before any DELETE.

```bash
poetry run python tools/normalize_qcew_rollups.py --dry-run --scope=michigan
```

**Expected output** (numbers approximate):

```
[spec-067 dry-run] reference DB: data/sqlite/marxist-data-3NF.sqlite (8.79 GB)
[spec-067 dry-run] fact_qcew_annual: 10,234,567 rows pre-migration

Rollup-row counts by class:
  NAICS-only rollups (naics_level != 6 AND own_code != '0'):    2,856,321
  Ownership-only rollups (naics_level = 6 AND own_code = '0'):    198,444
  Both-axes rollups (naics_level != 6 AND own_code = '0'):         20,900
  TOTAL to be excluded:                                          3,075,665

Canonical rows that will SURVIVE:                                7,158,902

Integrity check (pre == post + excluded):
  10,234,567 == 7,158,902 + 3,075,665  ✅

[spec-067 dry-run] NAICS vintages detected per year:
  2010: NAICS 2007    2011: NAICS 2007
  2012: NAICS 2012    2013: NAICS 2012    2014: NAICS 2012
  2015: NAICS 2012    2016: NAICS 2012
  2017: NAICS 2017    2018: NAICS 2017    2019: NAICS 2017
  2020: NAICS 2017    2021: NAICS 2017
  2022: NAICS 2022    2023: NAICS 2022    2024: NAICS 2022  ✅

[spec-067 dry-run] BLS-suppressed county-years in Michigan scope: <N>
[spec-067 dry-run] No changes written. Run without --dry-run to apply.
```

**Stop conditions**:
- Integrity check fails ❌ → the dim-table predicates are not matching the data as expected. Check that `dim_industry.naics_level` is populated and that `dim_ownership.own_code` uses the BLS codes documented in `contracts/normalization_migration.sql` Step 0. Do NOT proceed.
- NAICS vintages missing for some years → spec-067 has not been updated for a new NAICS revision. Update `NAICS_VINTAGE_BY_YEAR` in `tools/normalize_qcew_rollups.py`.
- BLS-suppressed count is > 5% of Michigan county-years → unusual; review the supplementary report and proceed only if explainable.

---

## Phase 2 — Run the migration

```bash
poetry run python tools/normalize_qcew_rollups.py --apply --keep-backup
```

This:
1. Creates `fact_qcew_annual__pre_067` backup table (~3 GB).
2. Runs the two DELETEs inside a single transaction.
3. Asserts the integrity check (pre == post + excluded).
4. COMMITs.
5. Emits the audit report (`.md` + `.json`) to `reports/ingest/qcew_normalization_YYYYMMDD-HHMMSS.{md,json}`.
6. Prints the report path and Wayne County 2010 spot-check.

**Expected output** (tail):

```
[spec-067 apply] Migration committed.
[spec-067 apply] Audit report:
  reports/ingest/qcew_normalization_20260517-093421.md
  reports/ingest/qcew_normalization_20260517-093421.json

[spec-067 apply] Wayne County 2010 spot-check (SC-001):
  SELECT SUM(employment) FROM fact_qcew_annual ... WHERE fips_code='26163' AND year=2010;
  = 658,734
  BLS-published value: ~660,000
  Delta: -0.19%  ✅ (within ±5% band)

[spec-067 apply] Backup retained at fact_qcew_annual__pre_067 (drop manually after qa:e2e-regression passes).
[spec-067 apply] DONE in 287.4 seconds.
```

If anything fails between steps 1 and 4, the transaction ROLLBACKs and the database is unchanged. If step 5 (audit report write) fails after COMMIT, the database IS changed but the backup table is your recovery surface — re-run with `--rollback-from-backup` to revert.

---

## Phase 3 — Inspect the audit report

```bash
cat reports/ingest/qcew_normalization_20260517-093421.md | head -80
```

Read the per-county delta summary. Acceptance criteria:

- **SC-007**: `summary_stats.counties_within_5pct_band_pct ≥ 95.0`
- **SC-008**: integrity check shows `naics_only + ownership_only + both_axes == total`
- **FR-007**: NAICS vintages listed per year; BLS-suppressed county-years enumerated

If the JSON sidecar is needed for tooling:

```bash
jq '.row_counts' reports/ingest/qcew_normalization_20260517-093421.json
jq '.per_county_deltas.summary_stats' reports/ingest/qcew_normalization_20260517-093421.json
jq '.per_county_deltas.outliers' reports/ingest/qcew_normalization_20260517-093421.json
```

---

## Phase 4 — Refactor downstream consumer queries

This is the FR-003 / FR-004 / SC-004 part. The migration script has DELETEd the rollup rows but the consumer code still has `WHERE industry_id = 1 AND ownership_id = 1` filters that would now return zero rows.

```bash
# Verify the filters are still present (should be — we haven't refactored yet).
rg "WHERE industry_id\s*=\s*1|WHERE ownership_id\s*=\s*1" src/babylon/persistence/
```

Expected matches in:
- `src/babylon/persistence/hex_hydrator.py` (around line 463-480 — 3 filter occurrences in c-calc and wages queries)
- `src/babylon/persistence/county_aggregation.py` (around line 348-397 — 2 filter occurrences in fetch_employment_proxy_for_county_at_tick)

Edit each occurrence per `contracts/post_067_query_contract.md`:
1. Remove the `AND industry_id = 1 AND ownership_id = 1` clauses.
2. Replace `SELECT total_wages_usd / SELECT employment` with `SELECT SUM(total_wages_usd) / SELECT SUM(employment)`.
3. The query becomes a GROUP-BY-aggregate; the result is still a single row per (county_id, time_id).

Verify zero matches remain in production code paths:

```bash
rg "WHERE industry_id\s*=\s*1|WHERE ownership_id\s*=\s*1" src/babylon/persistence/
# Expected: no matches (SC-004)
```

Run the unit + integration tests:

```bash
mise run test:unit && mise run test:int
```

Expected: all pass. The pre-067 baseline tests have been updated alongside the query refactor (FR-008 / FR-009).

---

## Phase 5 — Tighten the rate-of-profit band (FR-009 / SC-003)

Edit `tests/slow/test_michigan_canada_rate_of_profit_band.py` (or its current name `tests/test_state_rate_of_profit_in_relaxed_band.py`):

```python
# Before (spec-066 relaxed band):
RATE_OF_PROFIT_BAND = (0.05, 0.80)

# After (spec-067 tightened back to spec-original):
RATE_OF_PROFIT_BAND = (0.05, 0.50)
```

This single-line change is the visible knob; the actual band is enforced through the integration test that consumes the canonical Michigan-Canada trace.

---

## Phase 6 — Regenerate the michigan-e2e baseline (FR-008 / SC-006)

The post-067 simulation produces materially different trace values (because v changes when the c+v denominator changes). Regenerate:

```bash
mise run sim:e2e-michigan -- --regenerate-baseline
```

Expected duration: 60–90 minutes (the spec-066 relaxed budget). The output writes:
- `reports/sim-runs/YYYY-MM-DDTHH-MM-SSZ/trace.csv`
- `reports/sim-runs/YYYY-MM-DDTHH-MM-SSZ/summary.json`
- `reports/sim-runs/YYYY-MM-DDTHH-MM-SSZ/manifest.json`

Copy the trace + summary into the baseline location:

```bash
cp reports/sim-runs/2026-05-17T*Z/*.{csv,json} tests/baselines/
# Then update the JSON pointer at tests/baselines/michigan-e2e.json
```

Re-run the slow gate to confirm the new baseline:

```bash
mise run qa:e2e-regression
```

Expected: passes.

Run the rate-of-profit band test specifically:

```bash
poetry run pytest tests/slow/test_michigan_canada_rate_of_profit_band.py -v
```

Expected: passes against the tightened `[0.05, 0.50]` band.

---

## Phase 7 — Commit the work

The spec-067 delivery is one well-bounded change set. Per CLAUDE.md "commit after each unit of work":

```bash
# Commit 1: migration tool + audit-report contract + SQL contract
git add tools/normalize_qcew_rollups.py contracts/audit_report.schema.json \
        specs/067-qcew-ownership-normalization/contracts/normalization_migration.sql \
        specs/067-qcew-ownership-normalization/contracts/post_067_query_contract.md \
        tests/integration/test_normalize_qcew_rollups.py
git commit -m "feat(spec-067): migration tool + audit-report contract"

# Commit 2: consumer-code refactor
git add src/babylon/persistence/hex_hydrator.py \
        src/babylon/persistence/county_aggregation.py \
        tests/integration/test_post_067_consumer_queries.py
git commit -m "feat(spec-067): refactor hex_hydrator + county_aggregation from SELECT(rollup) to SUM(leaves)"

# Commit 3: rate-of-profit band tightening
git add tests/slow/test_michigan_canada_rate_of_profit_band.py
git commit -m "feat(spec-067): tighten rate-of-profit band from [0.05, 0.80] back to [0.05, 0.50]"

# Commit 4: michigan-e2e baseline regeneration
git add tests/baselines/michigan-e2e.json reports/sim-runs/<new-date>/
git commit -m "chore(spec-067): regenerate michigan-e2e baseline against normalized fact_qcew_annual"

# Commit 5: audit-report artifact + ADR
git add reports/ingest/qcew_normalization_*.{md,json} \
        ai-docs/decisions/ADR045_qcew_normalization.yaml
git commit -m "docs(spec-067): audit report + ADR045"
```

---

## Phase 8 — Cleanup (after qa:e2e-regression passes)

Once the post-067 baseline is committed and CI is green, drop the backup table to reclaim disk:

```bash
poetry run python tools/normalize_qcew_rollups.py --drop-backup
```

This runs:
```sql
DROP TABLE fact_qcew_annual__pre_067;
VACUUM;
```

VACUUM reclaims ~3 GB of free space inside the SQLite file. The database returns to its ~5.5 GB post-067 size.

---

## Rollback (if anything goes catastrophically wrong)

If after COMMIT something is found to be broken (e.g., the audit report shows > 10% county-years exceeding BLS deviation), restore from the backup:

```bash
poetry run python tools/normalize_qcew_rollups.py --rollback-from-backup
```

This:
1. Drops the (broken) post-067 `fact_qcew_annual`.
2. Renames `fact_qcew_annual__pre_067` → `fact_qcew_annual`.
3. Restores the FK indices.
4. Logs the rollback to `reports/ingest/qcew_rollback_YYYYMMDD-HHMMSS.md`.

You are now back to pre-067 state. Investigate, fix, re-run.

---

## Verification checklist (mapped to spec SCs)

| Spec SC | Verification step | Phase |
|---|---|---|
| SC-001 | Wayne County 2010 spot-check shows ±5% of ~660K | 2 (apply output) + 6 (slow-gate re-run) |
| SC-002 | 520-tick Michigan-Canada s/v ∈ [0.05, 0.50] | 6 |
| SC-003 | `test_state_rate_of_profit_in_relaxed_band` passes with tightened band | 5 + 6 |
| SC-004 | `rg` finds zero filter matches in `hex_hydrator.py` and `county_aggregation.py` | 4 |
| SC-005 | Re-running migration produces byte-identical post-state | 2 (re-run to verify) |
| SC-006 | Two regeneration runs produce byte-identical trace.csv at same seed | 6 (run twice and diff) |
| SC-007 | Audit report shows ≥ 95% county-years within ±5% BLS band | 3 |
| SC-008 | Audit report integrity check passes (naics + ownership + both == total) | 3 |

All eight SCs verifiable from the operator workflow above.

---

## Common pitfalls

- **Forgetting `--keep-backup` in Phase 2**: the migration script defaults to keeping the backup, but if you pass `--drop-backup-immediately` (NOT recommended) and the post-migration verification fails, recovery requires re-ingestion from CSV (which is currently out of scope; see spec-086).
- **Running Phase 4 (consumer refactor) before Phase 2 (migration)**: the consumer queries hitting the new SUM-the-leaves pattern still work against the un-normalized table (they just include the rollup rows in the SUM, double-counting). Tests will fail with values 2× higher than expected. Always migrate first, then refactor.
- **Running Phase 6 (baseline regeneration) before Phase 5 (band tightening)**: the slow-gate run uses the band test; if the band is still `[0.05, 0.80]` when you regenerate, you don't know whether the new values would have passed the tighter band. Order: migrate → refactor → tighten band → regenerate baseline.
- **Skipping Phase 8 (cleanup)**: harmless but leaves 3 GB of dead bytes in the SQLite file. CI's disk-usage gate (if any) may complain.
