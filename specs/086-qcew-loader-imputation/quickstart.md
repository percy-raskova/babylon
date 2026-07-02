# Quickstart: QCEW Imputed Reload (spec-086)

Operator guide. Everything runs from the babylon repo root inside the poetry venv; the loader code lives in the babylon-data repo and is imported through the `src/babylon_data` symlink.

## 0. Preconditions

```bash
ls /media/user/data/babylon-data/qcew/ | grep -c 'annual.singlefile.csv'   # expect 15 (2010-2024)
readlink src/babylon_data    # expect /home/user/projects/game/babylon-data/src/babylon_data (post-086)
readlink data/sqlite         # expect /media/user/data/babylon-data/sqlite (canonical DB home)
```

## 1. Dry run (no writes; full parse + imputation + validation)

```bash
mise run data:qcew -- --dry-run --years 2010-2024
# or a fast single-year sanity pass first:
mise run data:qcew -- --dry-run --years 2010
```

Read the report at `reports/ingest/qcew_impute_<UTC>.md`. Check: suppression rate ~67–72 % of cells; reconciliation `within_2pct` ≥ 99 %; Wayne 2010 gate true; national check within ±1 %.

## 2. Apply (staged build → validate → atomic swap; ~≤90 min full range)

```bash
mise run data:qcew -- --apply --years 2010-2024
```

- Interrupted? Just re-run the same command — per-year checkpoints resume at the first incomplete year (FR-012).
- Start over: add `--restart`.
- The canonical table keeps serving consumers until validation passes; only then does the swap happen. Old data survives as `fact_qcew_annual__pre_086`.

## 3. Post-apply verification

```bash
# Wayne County MI 2010 — SC-003 (published: 657,150; pre-086 leaves: 561,173 = −14.6 %)
sqlite3 "file:data/sqlite/marxist-data-3NF.sqlite?mode=ro" "
  SELECT SUM(fq.employment) FROM fact_qcew_annual fq
  JOIN dim_county dc ON dc.county_id=fq.county_id
  JOIN dim_time t ON t.time_id=fq.time_id
  WHERE dc.fips='26163' AND t.year=2010;"          # expect within ±2% of 657150

# Provenance coverage — SC-006
sqlite3 "file:data/sqlite/marxist-data-3NF.sqlite?mode=ro" "
  SELECT is_imputed, COUNT(*) FROM fact_qcew_annual GROUP BY is_imputed;"

# Determinism digests — SC-008 (commands + expected procedure: contracts/determinism_contract.md)

# Gated test suite (skips in CI, runs locally)
poetry run pytest tests/integration/test_qcew_live_reconciliation.py -v
```

## 4. Downstream re-baselining (required — county v rises 10–30 %+ by design)

```bash
mise run sim:e2e-michigan          # regenerates tests/baselines/michigan-e2e.json (~45 min)
mise run qa:e2e-regression         # must pass against the regenerated baseline
poetry run pytest -k "rate_of_profit" -v   # structural invariants: s > 0, p' finite
```

Commit the regenerated baseline together with the reload's audit report reference (067 FR-008 pattern).

## 5. Rollback / cleanup

```bash
mise run data:qcew -- --rollback-from-backup   # restore pre-086 tables
mise run data:qcew -- --drop-backup            # after verification, reclaim ~5 GB
```

## Failure modes

| Symptom | Meaning | Action |
|---|---|---|
| exit 2, "missing singlefile for YEAR" | staged source incomplete | check `--source-dir`; no network fallback exists by design (FR-011) |
| exit 2, "unknown NAICS codes: […]" | new BLS vintage not in dim_industry | halt is intentional (FR-013); seed dim_industry, re-run |
| exit 1, reconciliation gate failed | imputation output off-band | read audit outliers; canonical tables were NOT swapped |
| exit 130 | interrupted | re-run; resumes from checkpoints |
