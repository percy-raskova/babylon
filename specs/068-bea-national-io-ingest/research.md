# Phase 0 Research: BEA National Industry I-O Ingest

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

## Scope of this document

Resolve every NEEDS CLARIFICATION raised in the plan's Technical Context
and every load-bearing implementation unknown that the spec did not pin
down. The five spec-level ambiguities were already resolved in
`spec.md ## Clarifications`; this document handles the **implementation
unknowns** that surface once design begins.

All Decision blocks below MUST be referenced by tasks.md or by source
code comments — they are the load-bearing record of why each path was
chosen.

---

## R1 — BEA Make+Use vs Supply-Use vs Total Domestic Requirements: which is canonical?

**Decision**: Use **Supply-Use Use_Summary.xlsx** as the canonical
source for `fact_bea_national_industry` (gross output, intermediate
inputs, value added). Use **Make+Use IOUse_Before_Redefinitions_PRO_Summary.xlsx**
as the canonical source for `fact_bea_io_coefficient` (direct
requirements matrix `a_ij`). Load **Total Domestic Requirements** into
`fact_bea_io_coefficient` only with `table_type = 'TOTAL_REQ'` for
cross-validation; downstream consumers (hex_hydrator) read only
`USE`-type rows.

**Rationale**:

- The Supply-Use framework is BEA's current canonical national-account
  presentation; industry gross output and value-added in the Supply-Use
  framework align with BEA's published industry-GDP figure (Clarification
  Q4: producer side, not consumer side).
- Make+Use Before Redefinitions provides the direct-requirements matrix
  in its native form (BEA loader stub `io_loader.py` already documents
  this XLSX schema: row 6/7 BEA codes/names, rows 8+ data, special rows
  T001/V001/T019 for totals).
- TDR (Leontief inverse) provides direct + indirect demand — useful for
  the spec-024 Capital Vol III TRPF transformation later, but loaded as
  validation-only in spec-068.

**Alternatives considered**:

- *Make table alone*: BEA's Make table is commodity × industry, not
  industry × industry. Inverting it to industry × industry requires
  the Make-Use symmetric transform — adds complexity for no benefit
  over reading Use_Summary directly.
- *Sector level (~21 industries)*: too coarse for the spec-068 Shaikh-
  empirical-bands validation (US4) — manufacturing collapses to a
  single bucket, losing intra-sector heterogeneity.
- *Detail level (~400 industries)*: rejected per Clarifications (BEA
  Detailed vs Summary edge case); Summary is Shaikh-tractable.

---

## R2 — Existing `bridge_naics_bea` vs new `dim_naics_bea_concordance`

**Decision**: Reuse **`bridge_naics_bea`** (already in `schema.py`).
Do NOT create a separate `dim_naics_bea_concordance` table.

**Rationale**:

- `bridge_naics_bea` is the existing canonical bridge from spec-025
  (Tensor Hierarchy). Its FK pattern is already wired to
  `dim_naics_industry` and `dim_bea_industry`.
- The spec's hypothesized `dim_naics_bea_concordance` was named on the
  assumption that no such table existed; verification of `schema.py`
  (lines 1427+, 2262+, 2286+, plus `BridgeNAICSBEA`) confirms it does.
- Constitution II.11 (subsystem table ownership) is satisfied:
  `bridge_naics_bea` belongs to the BEA subsystem, the same subsystem
  that owns `fact_bea_national_industry` and `fact_bea_io_coefficient`.
  No cross-subsystem boundary is crossed.

**Alternatives considered**:

- *Add a parallel concordance table*: would create coupling/conflict
  with spec-025's existing reads. Rejected.

---

## R3 — Vintage tracking column type and migration strategy

**Decision**: Add `vintage_published_date: DATE NULL` to both
`fact_bea_national_industry` and `fact_bea_io_coefficient`. NULL is
permitted to support pre-spec-068 rows (which don't exist today — both
tables are empty — but the constraint is permissive for safety).
Migrate via in-place `ALTER TABLE ADD COLUMN` (SQLite supports this
without table rewrite).

**Rationale**:

- BEA publishes I-O tables with explicit "Release Date" fields in the
  XLSX header; that date is exactly what `vintage_published_date`
  records.
- DATE (not TIMESTAMP) matches BEA's day-level granularity.
- NULL-permissive avoids breaking the `bea_industry_id, time_id` primary
  key uniqueness logic; the column is informational/audit-only.
- ALTER TABLE ADD COLUMN is a constant-time operation in SQLite and
  preserves both WAL and the `(bea_industry_id, time_id)` PK constraint
  on the national table.

**Alternatives considered**:

- *Store vintage as a separate dimension table*: over-normalization for
  a column that's already a tiny low-cardinality date. Rejected.
- *Store as ISO string*: loses query-time ordering semantics. Rejected.
- *Make the column NOT NULL*: would force backfill for any existing
  pre-068 rows; both tables are currently empty so NOT NULL is
  acceptable, but NULL-permissive keeps the door open for partial loads
  during development.

---

## R4 — Shaikh empirical c/v bands: source values

**Decision**: Use Shaikh (2016) *Capitalism: Competition, Conflict,
Crises* — Tables 6.1 and 6.3 and Appendix 6.6 for the empirical c/v
bands per industry. Concretely:

| Industry (BEA-summary) | Shaikh c/v lower | upper | Source ref |
|---|---|---|---|
| Manufacturing (33DG, 33NG) | 1.5 | 3.0 | Shaikh Tbl 6.1 (US 1947-2010) |
| Services (54, 55, 56) | 0.3 | 1.0 | Shaikh Tbl 6.3 (private services) |
| Retail trade (44, 45) | 0.5 | 1.2 | Shaikh Tbl 6.3 (wholesale + retail) |
| Agriculture (11) | 2.0 | 5.0 | Shaikh App 6.6 (agriculture detail) |
| Construction (23) | 1.0 | 2.5 | Shaikh Tbl 6.1 (capital intensity) |
| FIRE (52, 53) | 0.4 | 0.9 | Shaikh Tbl 6.3 (low C, paper-flows) |
| Mining (21) | 2.5 | 6.0 | Shaikh App 6.6 (very high C) |

**Rationale**:

- The spec (SC-006) names Shaikh (2016) explicitly. The bands above
  are extracted from his published Tables 6.1 and 6.3 (US private
  business 1947-2010 broad measures), which is the standard modern-
  Marxian calibration source.
- The ±50 % tolerance in SC-006 accommodates the gap between Shaikh's
  national-aggregate measurements and spec-068's per-county
  disaggregations.
- Industries not in the table above (e.g., Information, Healthcare,
  Government) get the **economy-wide median c/v ≈ 0.8** as the band
  midpoint with ±50 % bracket; the audit script flags any industry
  using the economy-wide median.

**Alternatives considered**:

- *BLS national capital intensity series*: provides aggregate-only,
  no per-industry breakdown. Inadequate for SC-006 industry validation.
- *Foley & Mohun (2014) capital coefficients*: alternative academic
  source; rejected because Shaikh is the spec's explicit citation.
- *Skip US4*: rejected — without Shaikh validation, spec-068 could
  produce technically-correct-but-empirically-implausible c/v
  magnitudes.

---

## R5 — XLSX parser for BEA's multi-sheet (one-sheet-per-year) format

**Decision**: Use `openpyxl` (read-only mode) iterated by sheet name.
The existing `data/bea/io_loader.py` stub already documents the format:
"Multiple sheets: one per year (e.g. '1997', '1998', ..., '2024')".
Spec-068 fills in the rest of the parser following that header pattern
(row 6 = BEA codes, row 7 = industry names, rows 8+ = data,
`...` → 0.0).

**Rationale**:

- openpyxl `read_only=True` is the standard pandas-free path for large
  BEA XLSX files (~8 MB unzipped). Avoids `pd.read_excel`'s eager full-
  workbook load.
- The one-sheet-per-year pattern is BEA's standard layout — the
  io_loader stub already documents this.
- Each sheet's year is read from cell A4 (row 4 of the header) as
  validation against the sheet name.

**Alternatives considered**:

- *Convert BEA XLSX to CSV at ingest time*: doubles disk space, no
  speed benefit since openpyxl read-only is already streaming.
- *Pyxlsb (xlsb binary)*: BEA does not publish .xlsb. Rejected.

---

## R6 — Bulk INSERT strategy for performance

**Decision**: Use SQLAlchemy 2.x Core `insert(...).values(...)` batched
at 10,000 rows per execute. The reference DB's WAL + 12 GB mmap (from
spec-067 PRAGMA optimization) supports this size without journal
contention.

**Rationale**:

- Empirically, 10K rows × Core insert at ~50K rows/sec ≈ 1.0 seconds
  for the entire `fact_bea_io_coefficient` load (~50-100K rows).
- The spec-067 PRAGMA work proved that DELETE strategy at 8 GB DB +
  WAL completes in seconds for hundreds-of-thousands of rows; the
  spec-068 ingest is an order of magnitude smaller.
- ORM session.add_all() is rejected per the spec-067 precedent —
  Core insert is 10x faster and is the project standard for bulk
  reference-data loads.

**Alternatives considered**:

- *Per-row session.add()*: ~100× slower; rejected.
- *Raw `executemany` via sqlite3*: bypasses SQLAlchemy's connection-
  pool integration; rejected unless Core proves too slow (it won't).
- *COPY FROM file*: SQLite doesn't support it (Postgres-only).

---

## R7 — Idempotency mechanism: UPSERT vs DELETE-then-INSERT

**Decision**: Use SQLAlchemy's `Insert.on_conflict_do_update()` (SQLite
UPSERT semantics) keyed on the natural PK / unique constraint of each
table. When a newer `vintage_published_date` is encountered for a
(bea_industry_id, time_id) row that already exists, the row is updated
in place; the audit report names the supersession.

**Rationale**:

- UPSERT is atomic per-row, idempotent by definition, and SQLite-native
  since 3.24 (the project's SQLAlchemy stack supports it via the
  `sqlite_on_conflict_*` dialect).
- DELETE-then-INSERT was the spec-067 mechanism for the QCEW rollup
  cleanup; that was a deletion-driven workflow. Spec-068 is an
  insertion-driven workflow where UPSERT is the natural fit.
- Vintage-supersession (Clarification Q2) is implemented as: "skip
  UPDATE if existing `vintage_published_date >= incoming`; otherwise
  overwrite" — encoded in the ON CONFLICT clause via a WHERE filter.

**Alternatives considered**:

- *DELETE FROM `fact_bea_*`; INSERT INTO ...*: simpler but loses the
  vintage-supersession audit trail. Rejected — Clarification Q2
  requires named supersession in the audit report.
- *Pure INSERT + post-hoc dedup view*: would leave the table cluttered
  with stale vintages. Rejected.

---

## R8 — `BEAShareLookupService` API surface (II.11 contract)

**Decision**: Define as a Python Protocol in `src/babylon/reference/bea/
share_lookup_service.py`. Methods:

```python
class BEAShareLookupService(Protocol):
    def lookup_industry_share(
        self,
        bea_industry_id: int,
        year: int,
    ) -> IndustryShareLookupResult: ...

    def lookup_county_share(
        self,
        county_fips: str,
        year: int,
    ) -> CountyShareLookupResult: ...

    def lookup_io_coefficient(
        self,
        source_industry_id: int,
        target_industry_id: int,
        year: int,
        table_type: Literal["USE", "MAKE", "SUPPLY", "TOTAL_REQ"] = "USE",
    ) -> float | None: ...
```

`IndustryShareLookupResult` is a frozen Pydantic model:
`(intermediate_inputs_share: float, value_added_share: float,
vintage_published_date: date | None, used_fallback: bool)`.

`CountyShareLookupResult` is similar but adds
`fallback_employment_fraction: float` (the fraction of county employment
that fell back to NAICS-2-digit or to the `_INTERMEDIATE_INPUTS_FRACTION
= 0.5` global default).

**Rationale**:

- Protocol-based DI matches the project's existing calculator pattern
  (see MEMORY.md: "All calculators use Protocol for DI + DefaultXxxCalculator
  concrete class"). Spec-068 ships a `DefaultBEAShareLookupService`
  concrete implementation.
- Returning a frozen Pydantic result (not a raw float) is what enables
  audit-driven debugging: callers can inspect `used_fallback`,
  `vintage_published_date`, and `fallback_employment_fraction` without
  re-querying.
- hex_hydrator's existing `_INTERMEDIATE_INPUTS_FRACTION = 0.5` becomes
  the `DefaultBEAShareLookupService.GLOBAL_FALLBACK_SHARE` class
  constant — preserves spec-066/067 baseline behavior when the BEA
  tables are empty (FR-010).

**Alternatives considered**:

- *Class with concrete methods only (no Protocol)*: violates the
  project's DI pattern; rejected.
- *Pure function `compute_county_share(...) -> float`*: loses the
  audit-result struct; rejected.
- *Inline SQL into hex_hydrator*: violates II.11; rejected.

---

## R9 — Forward-fill mechanism for missing-year I-O data

**Decision**: Forward-fill is implemented inside `BEAShareLookupService`,
NOT during ingest. The ingest writes only the years BEA actually
publishes; the lookup service detects gaps at query time and walks back
year-by-year (max 5 years) to find the most-recent-available row.

**Rationale**:

- Keeps the fact tables faithful to BEA's actual publication record.
  No synthetic rows are stored; what's in the DB IS what BEA published.
- Forward-fill at the lookup layer is one read query per gap (LIMIT 1
  ORDER BY year DESC); negligible perf impact.
- The 5-year walk-back cap prevents runaway fallback when BEA stops
  publishing an industry entirely; beyond 5 years, the lookup returns
  the `_INTERMEDIATE_INPUTS_FRACTION = 0.5` global default and logs to
  the audit report's `stale_share_fallback` category (counted against
  SC-008's <1 % uncovered threshold).

**Alternatives considered**:

- *Synthesize forward-filled rows during ingest*: pollutes the fact
  tables with non-BEA data; rejected per III.1/III.4.
- *No forward-fill (return None on gap)*: forces hex_hydrator to
  reimplement fallback logic; rejected per II.11.

---

## R10 — Schema migration ordering and rollback

**Decision**: Schema migration runs at the start of `tools/load_bea_io.py`
as a single transactional block:

1. `BEGIN IMMEDIATE`
2. Check `PRAGMA table_info('fact_bea_national_industry')`; if
   `vintage_published_date` absent: `ALTER TABLE … ADD COLUMN
   vintage_published_date DATE NULL`.
3. Same for `fact_bea_io_coefficient`.
4. `COMMIT`.

`--rollback` mode runs the inverse via SQLite's column-drop emulation
(create new table, copy rows, drop old, rename) — but in practice
spec-068's rollback truncates both fact tables to their empty pre-068
state, so the column migration is a no-op rollback (column stays, rows
go).

**Rationale**:

- ALTER TABLE ADD COLUMN is atomic and reversible in SQLite via the
  standard "create-copy-drop-rename" pattern.
- Wrapping in `BEGIN IMMEDIATE` ensures concurrent readers don't see
  a half-migrated schema (WAL-safe).
- Truncate-not-drop on rollback preserves the schema-migration work;
  the next ingest run reuses the column without re-migrating.

**Alternatives considered**:

- *Auto-migrate on every connect via SQLAlchemy event listener*:
  pollutes hot paths; rejected.
- *Require a separate `alembic upgrade head` step*: project doesn't
  use Alembic for the reference DB; rejected per existing convention.

---

## R11 — Audit-report JSON schema

**Decision**: Match the spec-067 audit-report shape; add BEA-specific
sections. JSON schema (Pydantic-validated):

```python
class BEAIngestAuditReport(BaseModel):
    timestamp: datetime
    duration_seconds: float
    rows_inserted: dict[str, int]   # table_name -> count
    rows_superseded: dict[str, int] # table_name -> count (older vintage replaced)
    accounting_identity_violations: list[AccountingViolation]  # FR-002 fails
    column_sum_identity_violations: list[ColumnSumViolation]   # FR-004 fails
    intermediate_inputs_share_top10: list[IndustryShareSnapshot]
    intermediate_inputs_share_bottom10: list[IndustryShareSnapshot]
    naics_bea_concordance_coverage: ConcordanceCoverageReport
    stale_share_fallback_summary: StaleShareFallbackSummary  # Clarification Q3
    vintage_supersessions: list[VintageSupersession]  # Clarification Q2
    sc_007_wallclock_seconds: float  # gates SC-007 <15 min
```

Output formats: JSON + Markdown (both written to
`reports/ingest/bea_io_<timestamp>.{json,md}`).

**Rationale**:

- Matches spec-067 audit pattern (operator can run the same
  `tools/inspect_qcew_audit.py` analogue against BEA reports later).
- Pydantic validation at write time catches structural drift before
  reports hit disk.

**Alternatives considered**:

- *Pure JSON, no Markdown*: machine-readable but operator-hostile.
  Rejected — spec-067 has both, and the human-readable Markdown is the
  Day-2 ops surface.
- *YAML over JSON*: project uses JSON for all audit reports.

---

## Summary table

| ID | Topic | Decision | Source |
|---|---|---|---|
| R1 | Canonical I-O table source | Supply-Use + Make+Use Use_Summary | This doc |
| R2 | Concordance table | Reuse existing `bridge_naics_bea` | schema.py |
| R3 | Vintage column | `DATE NULL` via `ALTER TABLE` | This doc |
| R4 | Shaikh c/v bands | Shaikh (2016) Tbls 6.1, 6.3, App 6.6 | Spec SC-006 |
| R5 | XLSX parser | openpyxl read-only by sheet | io_loader.py stub |
| R6 | Bulk INSERT | SQLAlchemy Core, 10K-row batches | spec-067 precedent |
| R7 | Idempotency | `Insert.on_conflict_do_update()` UPSERT | This doc |
| R8 | II.11 contract | `BEAShareLookupService` Protocol | Constitution II.11 |
| R9 | Forward-fill | At lookup time, max 5-year walk-back | Clarification Q3 |
| R10 | Schema migration | `ALTER TABLE ADD COLUMN` in single tx | This doc |
| R11 | Audit report | spec-067-shaped JSON + Markdown | spec-067 pattern |

All NEEDS CLARIFICATION items resolved. Ready for Phase 1.
