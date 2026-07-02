# CLI Contract: `python -m babylon_data.qcew` / `mise run data:qcew`

**Entry point**: `src/babylon_data/qcew/__main__.py` (argparse; spec-067/068 house style). Runs inside babylon's poetry venv (`poetry run …`), which resolves both `babylon_data` (via the repointed `src/babylon_data` symlink) and `babylon.reference.*` (canonical ORM + session).

## Modes (mutually exclusive, exactly one required)

| Flag | Effect |
|---|---|
| `--dry-run` | Full parse + classification + imputation + validation for the selected years; NO writes to canonical tables (staging table built in a temp attach or skipped — implementation may compute in memory); audit report written with `mode="dry-run"` |
| `--apply` | Build/resume staging tables, per-year transactions + checkpoints; after all selected years validate: atomic swap with `__pre_086` backups, index recreation, `_cache_national_wages_bea` drop, legacy qcew file-checkpoint purge; audit report written |
| `--rollback-from-backup` | Restore `fact_qcew_annual__pre_086` (and rollup backup) to canonical; writes a small rollback report |
| `--drop-backup` | Remove `__pre_086` backups after operator verification; writes a small report |

## Options

| Flag | Default | Notes |
|---|---|---|
| `--years A-B` or `--years Y1,Y2` | `2010-2024` | Subset loads permitted; SC-gates in the audit are computed over the selected years |
| `--source-dir PATH` | `/media/user/data/babylon-data/qcew` | Must contain `<year>.annual.singlefile.csv` for every selected year; missing file = pre-flight hard error (FR-011: no download fallback) |
| `--db PATH` | resolved via `babylon.reference.database` (the repo's `data/sqlite` symlink) | Explicit override for fixture/testing runs |
| `--restart` | off | Drop staging tables + `annual_v086` checkpoints before loading (fixes the old loader's reset-vs-checkpoint deadlock by design) |
| `--report-dir PATH` | `reports/ingest/` | Audit artifacts `qcew_impute_<UTC>.{json,md}` |
| `--quiet` | off | Suppress per-chunk progress (flush-printed otherwise) |

## Exit codes

`0` success (all requested SC gates pass) · `1` validation failure (audit written; canonical tables untouched in `--apply` because the swap is gated on validation) · `2` pre-flight failure (missing source file/year, unknown non-pseudo fips, unknown NAICS code, dim tables empty) · `130` interrupted (staging + checkpoints persisted; re-run resumes).

## Pre-flight assertions (before any write)

1. Every selected year's singlefile exists and its 38-column header matches the expected layout exactly.
2. `dim_county`, `dim_industry`, `dim_ownership`, `dim_time` are populated; every own_code in {0,1,2,3,5} resolves; annual `time_id` rows exist (or are creatable) for the selected years.
3. Target DB is the canonical reference DB (path echo + sha256 into the audit); `is_imputed` column present in the ORM (schema.py updated) — the staging DDL comes from the ORM, so ORM/physical divergence cannot recur.

## mise task

```toml
[tasks."data:qcew"]
description = "Rebuild fact_qcew_annual 2010-2024 from staged BLS singlefiles with suppression imputation (spec-086)"
# usage-crate args mirroring data:bea-load: [years] default "2010-2024"; flags --dry-run/--apply/--restart/--rollback-from-backup/--drop-backup
run = "poetry run python -m babylon_data.qcew --years ${usage_years} ..."
```

`tools/ingest_qcew_full.py` (tombstone) message updated to name `mise run data:qcew` / `python -m babylon_data.qcew`.
