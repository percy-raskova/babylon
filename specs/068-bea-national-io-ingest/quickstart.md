# Quickstart: BEA National Industry I-O Ingest

**Audience**: Babylon operator running the spec-068 ingest.
**Time budget**: ~15 minutes end-to-end (SC-007).
**Reversible**: Yes, via `--rollback`.

---

## Prerequisites

1. **Reference DB present**: `data/sqlite/marxist-data-3NF.sqlite`
   exists and is on the post-spec-067 schema (verify via
   `ls -lh data/sqlite/marxist-data-3NF.sqlite` — expect ≥ 8 GB).
2. **BEA source files present**: `data/input-output/` exists with
   the three subdirectories (`make-use/`, `supply-use/`,
   `total-domestic-requirements/`).
3. **BEA concordance bundle present**:
   `data/bea/MAKE-USE-IMPORTS (BEFORE REDEFINITIONS).zip`.
4. **Loader stubs present**: `data/bea/{io_loader.py, loader_national.py,
   loader_concordance.py, loader_county.py}` and `data/bea/parser.py`.
5. **Branch on `068-bea-national-io-ingest` or a descendant of it**:
   `git branch --show-current`.

Verify with:

```bash
ls data/sqlite/marxist-data-3NF.sqlite \
   data/input-output/make-use/IOUse_Before_Redefinitions_PRO_Summary.xlsx \
   data/input-output/supply-use/Use_Summary.xlsx \
   data/input-output/total-domestic-requirements/IxI_TR_Summary.xlsx \
   "data/bea/MAKE-USE-IMPORTS (BEFORE REDEFINITIONS).zip"
```

All five paths should exist with non-zero size.

---

## Step 1: Dry run (no DB writes)

```bash
poetry run python tools/load_bea_io.py --dry-run --years 2010-2024
```

This parses every BEA XLSX file, builds the in-memory Pydantic
record set, validates the BEA accounting identity (FR-002) and the
Leontief column-sum identity (FR-004) — but does NOT touch the DB.

Expected output: a summary line per (table, year) showing row count,
identity-violation count, and parse time. Should complete in < 60s.

If any identity check fails: investigate via the dry-run audit report
written to `reports/ingest/bea_io_dryrun_<timestamp>.{md,json}`
before proceeding to the live ingest.

---

## Step 2: Live ingest

```bash
poetry run python tools/load_bea_io.py --years 2010-2024
```

This:

1. Opens the reference DB in WAL mode (already set per spec-067).
2. Adds the `vintage_published_date` column to `fact_bea_national_industry`
   and `fact_bea_io_coefficient` if absent (idempotent).
3. Populates `bridge_naics_bea` from the concordance bundle (UPSERT).
4. Writes `fact_bea_national_industry` rows from Supply-Use
   (UPSERT keyed on `(bea_industry_id, time_id)`).
5. Writes `fact_bea_io_coefficient` rows from Make+Use Use_Summary
   (UPSERT keyed on the existing unique constraint), plus
   Total Domestic Requirements as `table_type='TOTAL_REQ'`
   for validation cross-checks.
6. Emits the audit report to
   `reports/ingest/bea_io_<timestamp>.{md,json}`.

**SC-007 budget**: full live run < 15 minutes wallclock on the
target dev host (32 GB RAM, WAL + 12 GB mmap + 2 GiB cache_size,
SQLite WAL mode).

---

## Step 3: Read the audit report

```bash
ls -t reports/ingest/bea_io_*.md | head -1 | xargs cat
```

Look for the **Validation Gates** section:

- `SC-001 row count ≥ 800`: PASS / FAIL
- `SC-002 row count ≥ 50000`: PASS / FAIL
- `SC-003 accounting identity (FR-002) ≤ 0.01 residual`: PASS / FAIL
- `SC-004 column-sum identity (FR-004) ≤ 0.001 residual`: PASS / FAIL
- `SC-008 stale_share_fallback employment fraction < 0.01`: PASS / FAIL
- `SC-007 wallclock < 15 min`: PASS / FAIL

If **all PASS**: proceed to Step 4.

If **any FAIL**: the failure mode determines next action:

| Failure | Likely cause | Mitigation |
|---|---|---|
| SC-001 row count low | A year's XLSX missing/corrupt | Re-fetch from BEA, re-run |
| SC-003 accounting violations | XLSX parse error (column misalignment) | Inspect violation list in audit; fix parser |
| SC-004 column-sum violations | Make+Use vs Supply-Use vintage mismatch | Inspect `vintage_supersessions` |
| SC-008 fallback fraction > 1 % | Concordance bundle incomplete | Re-extract `bridge_naics_bea` from BEA concordance |

---

## Step 4: Verify the hex_hydrator wiring

```bash
poetry run pytest tests/integration/reference/bea/test_hex_hydrator_wired.py -v
```

Expected: `test_county_c_v_stddev_post_wiring` passes with measured
stddev ≥ 0.2 (SC-005 directional threshold).

For a deeper read, run a canonical Michigan e2e regen and inspect the
per-county c/v distribution:

```bash
mise run sim:e2e-michigan
poetry run python tools/inspect_per_county_c_v.py \
    --run reports/sim-runs/$(ls -t reports/sim-runs | head -1)
```

Expected: distribution shows heterogeneity across the 83 counties
(financial services lower c/v, manufacturing higher c/v, etc.).

---

## Step 5: Rollback (if needed)

If post-ingest validation flags critical mismatches:

```bash
poetry run python tools/load_bea_io.py --rollback
```

This truncates both fact tables to their empty pre-spec-068 state
(`DELETE FROM fact_bea_national_industry; DELETE FROM
fact_bea_io_coefficient; VACUUM;`). The `vintage_published_date`
column remains (it's a no-op schema artifact when the tables are empty).
The `bridge_naics_bea` table is NOT rolled back — concordance data is
considered independently useful and is shared with spec-025.

Post-rollback, the hex_hydrator's `_INTERMEDIATE_INPUTS_FRACTION = 0.5`
fallback path is automatically used (FR-010): the
`DefaultBEAShareLookupService` detects the empty tables and returns
`fallback_reason="global_default"` for every lookup. Spec-066/067
baseline behavior is restored.

---

## Step 6: Commit the ingest

```bash
git add data/sqlite/marxist-data-3NF.sqlite  # if tracking DB checksum
git add reports/ingest/bea_io_*.{md,json}
git commit -m "feat(spec-068): BEA national I-O ingest — fact_bea_* populated, hex_hydrator wired"
```

Per project convention (CLAUDE.md "Commit after each unit of work"),
the ingest and the hex_hydrator wiring may be split into two commits
if the wiring requires non-trivial test updates.

---

## Troubleshooting

### "Reference DB locked"

Another process (likely `mise run web:dev` or a stuck pytest worker)
holds an exclusive lock. Check with:

```bash
lsof data/sqlite/marxist-data-3NF.sqlite
```

Stop the offending process; WAL mode should otherwise allow concurrent
readers + one writer.

### "Parse error in Sheet '2024'"

BEA's most recent year is sometimes published in a preliminary format
with extra blank rows or revised column headers. Inspect the sheet
manually:

```bash
poetry run python -c "
from openpyxl import load_workbook
wb = load_workbook('data/input-output/supply-use/Use_Summary.xlsx', read_only=True)
ws = wb['2024']
for row in list(ws.iter_rows(min_row=1, max_row=10, values_only=True)):
    print(row)
"
```

If the header format has changed, file a follow-up to update the
parser's header-detection logic.

### "AccountingViolation residual > 0.01"

Likely a units mismatch (BEA publishes in millions of dollars but
some Supply-Use sheets are in thousands). Verify cell A2 of each
sheet reads `(Millions of dollars)`. If not, the loader's units
conversion is wrong.

### "Coverage fraction < 99 %"

The `bridge_naics_bea` table doesn't cover all NAICS codes present
in `fact_qcew_annual`. Re-extract the BEA concordance bundle and
re-run with the `--reload-concordance` flag.

---

## Related documents

- [spec.md](./spec.md) — requirements and success criteria
- [plan.md](./plan.md) — architectural overview
- [research.md](./research.md) — implementation-decision rationale
- [data-model.md](./data-model.md) — schema and entities
- [contracts/bea_share_lookup_service.md](./contracts/bea_share_lookup_service.md)
  — the II.11 cross-subsystem contract
