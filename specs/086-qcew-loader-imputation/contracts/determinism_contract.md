# Determinism Contract (FR-008 / SC-008)

**Definition**: Two runs of the loader over identical source files and identical target-DB starting state MUST produce **identical logical table content**, verified as equal SHA-256 digests of the full ordered projection of each output table.

The database *file* is explicitly NOT the comparison unit (WAL checkpoint state, freelist pages, and page-allocation order are legitimate non-determinism at the file layer).

## Canonical verification commands

```bash
DB=data/sqlite/marxist-data-3NF.sqlite   # directory symlink → the canonical trove DB

sqlite3 "file:${DB}?mode=ro" \
  "SELECT county_id,industry_id,ownership_id,time_id,establishments,employment,
          total_wages_usd,avg_weekly_wage_usd,avg_annual_pay_usd,
          lq_employment,lq_annual_pay,disclosure_code,is_imputed
   FROM fact_qcew_annual
   ORDER BY county_id,industry_id,ownership_id,time_id" | sha256sum

sqlite3 "file:${DB}?mode=ro" \
  "SELECT county_id,time_id,ownership_id,establishments,employment,
          total_wages_usd,disclosure_code,is_imputed
   FROM fact_qcew_county_rollup
   ORDER BY county_id,time_id,ownership_id" | sha256sum
```

Both digests are recorded in the audit report (`run_metadata.table_hashes`). SC-008 passes when a second `--apply` run (or a `--dry-run` recomputation) reproduces both digests exactly.

## Sources of determinism (implementation obligations)

1. **Pure integer arithmetic** end-to-end for imputed magnitudes (no float accumulation; wages held as int cents or int dollars consistently — int dollars, matching BLS source units).
2. **Fixed sibling ordering** in every apportionment group: `(own_code, industry_code)` ascending.
3. **Largest-remainder rounding** with the deterministic tie-break: larger fractional remainder first, then lower `industry_code`.
4. **Deterministic insert order** per year: `(county_id, ownership_id, industry_id)`.
5. **No RNG, no wall-clock values** in any persisted magnitude (timestamps appear only in audit metadata, which is outside the hashed projection).
6. Chunked pandas reads MUST NOT influence values or ordering (classification is row-local; the tree is assembled per county-year regardless of chunk boundaries).

## Idempotency (FR-007)

Re-running `--apply` against an already-swapped table rebuilds the staging table from source and swaps again; the post-swap digests MUST equal the prior run's digests. The composite PK (restored by the rebuild) structurally forbids silent duplication.
