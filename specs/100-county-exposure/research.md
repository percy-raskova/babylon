# Phase 0 Research — spec-100 County-Exposure Loader

All findings verified against the live reference DB
`/media/user/data/babylon-data/sqlite/marxist-data-3NF.sqlite` on 2026-07-03.

## R1 — Import-coefficient source

**Decision**: `import_coeff[bea, year]` = `fact_bea_io_coefficient.coefficient`
WHERE `source_industry_id` = the BEA industry "Noncomparable imports and
rest-of-the-world adjustment" (`bea_industry_id` resolved by name/`bea_code`,
not hardcoded), `table_type_id` = the USE table (`dim_bea_io_table_type.table_type
= 'USE'`), and `time_id` = the annual `time_id` for `year`.

**Rationale**: In the BEA USE table, the "Noncomparable imports" row as a *source*
against each consuming industry (*target*) is the import intensity of that
industry's production — imports consumed per unit of the industry's use. This is
the "BEA I-O imports" the phi_distribution docstring names. Verified: 66 consuming
industries per year, 2010–2024 (time_id 14–28).

**Alternatives considered**: TOTAL_REQ (Leontief inverse) — rejected, it is the
domestic-requirements table, not imports. A dedicated import matrix — not present
in the DB (only USE + TOTAL_REQ table types exist).

**Grounding (III.8)**: the coefficient is a measured material ratio (imported
inputs / output) published by BEA; resolved by dimension lookup, never literal.

## R2 — NAICS↔BEA concordance + antichain proof

**Decision**: use `bridge_naics_bea` (462 rows, all `mapping_quality = 'exact'`).
Join QCEW `industry_id` → `bea_industry_id`. For a NAICS mapped to >1 BEA (a
split), apportion by `COALESCE(weight, 1.0/split_count)`.

**Rationale**: this is the DB's own grounded concordance (III.4 data-catalog). It
mixes NAICS levels 2–6 (a double-count risk), but it was **verified an antichain**:
a scan of every bridge NAICS's parent chain found **0 cases** where one bridge
NAICS is an ancestor of another. Therefore summing QCEW employment over the bridge
NAICS for a BEA industry never double-counts. Exactly one NAICS (`industry_id`
379) splits to 2 BEAs; `weight` is NULL for all rows, so the split defaults to
0.5/0.5.

**Alternatives considered**: (a) direct `bea_code` == NAICS-prefix matching — gives
fuller coverage but requires hand-coding the ~15 BEA aggregate codes (GFGD, 4A0,
5412OP, 111CA…), which fabricates a concordance not in the DB (III.8 violation);
rejected. (b) extending `bridge_naics_bea` to services — out of scope (a future
data-program spec), same III.8 concern.

**Consequence (disclosed)**: the bridge is goods-biased. Of the 66 import-coefficient
industries, **18 have nonzero QCEW employment through the bridge** (2024):
manufacturing core (334 computers, 3361MV motor vehicles, 331 primary metals, 333
machinery, 335 electrical, 325 chemicals, 332 fabricated metals, 337 furniture,
339 misc mfg, 311FT food mfg, 322 paper, 324 petroleum, 327 nonmetallic, 3364OT
other transport equip) + a few services (5415 computer-systems design, 722 food
services, 524 insurance, 213 mining support). The covered coefficient mass is
0.044 of the total 0.292 (≈15%). **This is theoretically apt**: unequal-exchange
imperial rent is a tradeable-commodity phenomenon (Amin *Law of Worldwide Value*,
Cope *Divided World Divided Class*) — the map is a manufacturing/tradeable-goods
import-exposure map. Coverage is reported as an audit metric.

## R3 — QCEW ownership slice

**Decision**: sum QCEW employment over ownership `own_code ∈ {1, 2, 3, 5}`
(federal, state, local, private).

**Rationale**: at the detailed NAICS levels the bridge uses, `own_code = 0`
("Total Covered") is **absent** — verified: for bridge NAICS in 2024 only owns
{1,2,3,5} appear (private own_code 5 dominates 18.5M employment vs ~97k
government). Summing {1,2,3,5} is the county industry total and avoids the
double-count that `own_code 0` + components would cause. Government ownership is
included because BEA import coefficients include government industries.

**Alternatives considered**: private-only (own_code 5) — rejected, drops
government import-competing employment; `own_code 0` total — rejected, not present
at detailed NAICS.

## R4 — Year alignment

**Decision**: cover 2010–2024. Verified all three sources span it: BEA I-O import
coefficients (time_id 14–28), QCEW annual (~1M rows/year), trade monthly (15
years). Annual facts share one `time_id` per year. A year missing from BEA I-O or
QCEW is skipped for exposure with a recorded reason (never fabricated).

## R5 — Reconciliation gate (±2%, from the DB's own BEA import rows)

**Decision**: for each covered year, compute the conservation residual
`Σ_C raw_exposure[C]` vs `Σ_bea∈covered import_coeff[bea]` and require it within
±2%.

**Rationale**: because county shares `s[C,b] = emp[C,b]/nat_emp[b]` sum to 1.0 per
covered industry b, `Σ_C raw[C] = Σ_b coeff[b]·(Σ_C s[C,b]) = Σ_b coeff[b]`. So
the residual is ~0 by construction and any deviation exposes a real bug — a county
missing from the national total, a broken antichain, or a split-weight error.
Verified 2024: residual = +0.000000% against covered coefficients. The comparison
is sourced entirely from the DB's own BEA import rows (per the task wording). The
audit ALSO records `concordance_coverage = Σcovered / Σall` (≈15% in 2024) as the
data-quality metric that documents the goods-bias — this is the number a reviewer
reads to understand the map's scope, distinct from the ±2% correctness gate.

**Alternatives considered**: reconciling against an external published US-imports
total — rejected: it would require turning coefficients into levels (industry
output not in the DB) and the blocs overlap so `fact_trade_monthly` cannot be
summed to a clean national total. The task explicitly says "source the comparison
from the DB's own BEA import rows."

## R6 — Bloc keying + bloc-invariance

**Decision**: key exposure on `dim_country` rows with `is_region = 1` (spec-100's
named bloc set: EU, Advanced Technology Products, North America, Europe, Africa,
Pacific Rim, Asia, Australia & Oceania). Store per-bloc rows. The county
distribution is **currently identical across all blocs** and the audit records
`bloc_invariant = true`.

**Rationale**: `fact_trade_monthly` carries no bloc×industry resolution (bloc-level
total USD only; one "bloc" is the product category "Advanced Technology Products";
blocs geographically overlap). So no grounded bloc-specific distribution exists
(III.8 forbids fabricating one). Storing per-bloc matches the
`county_exposure_by_external` consumer shape and lets a future bloc×industry spec
differentiate without a schema migration; the invariance is disclosed, not hidden.

**Note for spec-101**: the engine's 8 external node ids (`canada, china, eu, india,
sub_saharan_africa, latin_america, russia_csi, southeast_asia` —
`postgres_initialization._EXTERNAL_PARTNER_KEYS`) differ from these 8 dim_country
blocs. Because the distribution is bloc-invariant, the crosswalk choice does not
affect weights — spec-101 may broadcast a single map to all engine nodes. Forcing
a lossy dim_country↔engine-node crosswalk here would fabricate specificity (III.8).

## R7 — `world_system_tier` is NULL for blocs

**Finding**: all 8 `is_region = 1` rows have `world_system_tier = NULL`. This is
**by original-loader design**: `TradeLoader._load_country_dimension` only calls
`classify_world_system_tier` for `is_region = 0` countries. The Program 09 §2
parenthetical "(+ world_system_tier core/semi_periphery/periphery)" does not hold
for region rows. This spec does not populate the tier.

## R8 — Trade units: USD, not tons

**Finding**: `fact_trade_monthly` columns are `imports_usd_millions` /
`exports_usd_millions` — USD, not tonnage. The engine's `ExternalNode` has TWO
fields: `bilateral_trade_value` (USD) and `bilateral_trade_tons` (tonnage,
currently hardcoded 0.0). The Program 09 §2 phrase "bilateral_trade_tons
aggregation from fact_trade_monthly" is imprecise: this source can only produce a
USD aggregate.

**Decision**: aggregate to `fact_bilateral_trade_annual` with honest USD columns
(`imports_usd_millions`, `exports_usd_millions`, `total_trade_usd_millions`). This
feeds the engine's `bilateral_trade_value` (USD). True `bilateral_trade_tons`
needs FAF freight tonnage (a future 098-family slice, out of scope). Flagged for
spec-101.

## R9 — Table naming + persistence pattern

**Decision**: `fact_county_exposure_by_external` and `fact_bilateral_trade_annual`
(SQLite reference `fact_` convention, as QCEW rollups use). Additive ORM classes
in `src/babylon/reference/schema.py`. Persistence mirrors spec-086 `writer.py`:
staged `__new` tables from ORM DDL, per-year transactional writes, atomic swap
retaining a `__pre_100` backup, rollback-from-backup, drop-backup, and
`logical_table_hash` (SHA-256 over an ordered projection, tolerant of
physical-schema drift; an absent table hashes as `sha256("absent:<name>")`).

**Note**: the runtime Postgres `immutable_reference_*` prefix (from spec-062) is a
different namespace — those are hydration tables. spec-100 writes SQLite reference
tables (`fact_`/`dim_`/`bridge_`), which the engine hydrates from later. The
phi_distribution docstring's "hydrated immutable_reference_bea_io /
immutable_reference_qcew_employment" refers to that later Postgres hydration, not
this spec's SQLite source.
