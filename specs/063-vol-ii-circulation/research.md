# Research: Vol II Circulation System with LODES OD Integration

**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)
**Date**: 2026-05-13

This document resolves the four open research items deferred from spec/plan to this phase. Each section follows the **Decision / Rationale / Alternatives** format. Findings amend the spec where they materially change scope.

---

## §1 — LODES File Layout (Phase 0 Verification)

**Decision**: The on-disk LODES dataset at `/media/user/data/babylon-data/lodes/od/` follows the canonical LODES naming convention and the established LEHD column schema. The loader (`LODESCommuteMatrixLoader`) consumes the per-state `_main_` files for in-state origin-destination pairs at the JT00 (all-jobs) job-type and S000 (all-workers) segment, both decisions ratified in spec Clarifications session 2026-05-13.

**Verified file shape** (Michigan 2010 sample):

```text
File:    /media/user/data/babylon-data/lodes/od/mi_od_main_JT00_2010.csv.gz
Header:  w_geocode,h_geocode,S000,SA01,SA02,SA03,SE01,SE02,SE03,SI01,SI02,SI03,createdate
Sample:  260010001001045,260010001002013,1,1,0,0,1,0,0,0,0,1,20230321
         (workplace block 26-001-0001-001-1045, home block 26-001-0001-002-2013, 1 worker)
```

- `w_geocode` / `h_geocode` are 15-digit 2020 Census block identifiers (state(2) + county(3) + tract(6) + block(4))
- `S000` is the all-workers count; loader consumes this column only
- Coverage: Michigan 2010-2021 (12 years). Years 2022-2025 hit the FR-004 nearest-year clamp (clamp to 2021).

**Loader flow per simulated year**:

1. Resolve `<state>_od_main_JT00_<year>.csv.gz` for each in-study-area state. For Detroit tri-county that's only `mi_od_main_JT00_<year>.csv.gz` (in-state pairs only).
2. Stream-read with `gzip` + `csv.reader`; skip rows where neither `w_geocode` nor `h_geocode` falls in the study area's block-group set (FR-007 row pruning).
3. Map both block-codes → H3 res-7 cells via the `us_xwalk.csv.gz` crosswalk (§6 below).
4. Aggregate `S000` by `(home_hex, workplace_hex)` pair (multi-row aggregation when several blocks share a hex).
5. Build a `scipy.sparse.csr_matrix` with rows = home_hex (origin), cols = workplace_hex (destination + boundary buckets), values = aggregated worker counts.

**Rationale**: The LODES file format is stable across LEHD's annual releases. Stream-reading bounds memory; per-state file scoping keeps the loader simple. JT00 + S000 (the spec Clarification) means we read exactly one column of one file per state per year — minimal input volume.

**Alternatives considered**:

- **Pre-process LODES into Parquet files at session install time**: faster reads but adds a build step + new format outside the on-disk fixture. Rejected — the gzip CSV is fast enough at session-init scale (~30 sec/year per Michigan; spec 062's hydrator already operates at this scale).
- **Read all 12 years upfront at init**: simpler memory model but holds 12 sparse matrices. Rejected — load lazily per active simulated year (FR-006 immutability holds within a year, so per-year load + cache fits naturally).
- **Use the `_aux_` files for cross-state commute**: `mi_od_aux_JT00_*.csv.gz` does not exist in the on-disk dataset. If LODES `_aux_` data becomes available in the future for cross-state commuters into Michigan (e.g., Toledo → Detroit reverse commute), the loader can absorb it via the same path; for v1 we assume in-state only.

---

## §2 — GATE-2 Confirmation: No DB I/O During Tick Body

**Decision**: The Vol II Circulation step performs **zero** Postgres reads during the per-tick `step()` body. The OD matrix is loaded once at session init (or once per year-rollover at a tick boundary) into the `LODESCommuteMatrixLoader` instance held by the `ImperialRentSystem`. During `step()`, only in-memory operations occur:

1. Read `v` from the in-memory hex graph attributes (NetworkXAdapter).
2. Compute `v_post = OD.T @ (v_pre / row_sums)` via scipy.sparse matrix-vector multiplication.
3. Compute COMMUTE_OUT residuals from row-sum minus in-study-area destination column-sums.
4. For each out-of-area row, classify (canada / rest_of_usa) via the in-memory classifier (§4 below).
5. Append all emitted boundary register rows to the in-memory `BoundaryFlowRegister` buffer.
6. Write `v_post` back to graph attributes.

The buffered rows commit to Postgres at end-of-tick via `PostgresRuntime.persist_tick_atomic` per spec 062 FR-008a — **outside** the per-System tick body, in the engine's per-tick transaction envelope.

**Rationale**: Constitution II.6 mandates pure transformation in the tick body. Spec 062 GATE-2 explicitly forbids per-tick Postgres queries; this feature inherits the constraint. The in-memory matrix is immutable for the year, so the loader can keep a single CSR copy without locking concerns.

**Alternatives considered**:

- **Per-tick Postgres lookup of OD rows**: ~3M rows for Michigan tri-county would mean tens of MB transferred per tick. Rejected — violates GATE-2 and would dominate per-tick wall time.
- **Memory-mapped Parquet via Arrow**: faster than CSR for column-store reads but unnecessary — CSR matrix-vector multiplication is the only tick-time access pattern, and CSR is purpose-built for that.

---

## §3 — Vol II = Min-Cost Flow; Slime-Mold Deferred (GATE-5 Closure)

**Decision**: Vol II circulation in this feature implements only the **min-cost flow component** of Constitution II.13's Transport Substrate. The LODES OD matrix is the deterministic routing tableau (one annual matrix per simulated year, applied uniformly across the 52 weeks per spec 062 FR-028). The matrix is represented as `scipy.sparse.csr_matrix` per Constitution II.12. **Slime-mold conductivity routing** (the emergent informal-economy component of II.13) is **explicitly out of scope for this feature** and is deferred to spec 064.

This decision is inherited verbatim from spec 062 research §6, which explicitly named spec 063 or 064 as the integration point for slime-mold conductivity over the LODES base layer. Spec 063 honors that deferral: it lays the LODES base layer; slime-mold becomes the overlay in a later spec.

**Forward-pointer comment**: Both `LODESCommuteMatrixLoader` and `Vol2CirculationStep` implementations carry a docstring note at the class-level: `"This is the deterministic min-cost flow component of Constitution II.13 Transport Substrate. Slime-mold conductivity routing (the emergent informal-economy component) is implemented in spec 064 as an overlay; do not add conductivity logic here."` This makes the deferral discoverable from the source.

**Rationale**: Constitution II.13 names both mechanisms. The deterministic component is what's load-bearing for spec 062 SC-011 (per-stage conservation) and spec 063 User Story 1 acceptance scenarios. Adding slime-mold later as an overlay does not break any v1 invariants because its output would compose with this feature's CSR matrix via per-tick weighting at a separate sub-stage.

**Alternatives considered**:

- **Build full Transport Substrate (both mechanisms) in this spec**: scope creep per Constitution VI.3 ("Flag Scope Creep — Must trace to Detroit prediction or improve falsifiability. Otherwise DEFER."). Slime-mold needs informal-economy survey data not in the existing fixture catalog (Constitution III.4.1) and would require separate calibration work.
- **Skip Vol II entirely until full Transport Substrate is designed**: rejected — spec 062 FR-028 is load-bearing and the deterministic LODES component is well-defined, well-cited, and ready to integrate.

---

## §4 — Canadian Destination Classification: Critical Data Gap and Resolution

**Decision**: **LODES does NOT include Canadian destinations.** Verified empirically: Michigan LODES `_main_` files contain only US block-coded `w_geocode` rows (state code 26 = Michigan). No Canadian (Statistics Canada) origin-destination data is present in the LODES dataset on disk. Therefore the `CrossBorderCommuteClassifier` cannot route Detroit→Windsor flows from canonical LODES alone.

**Resolution for v1**: Implement the classifier as designed (FR-023 — encoded country/state code lookup), but for v1 the canonical LODES input will produce **zero `dest_node_id='canada'` rows** because the source data has none. The classifier becomes a conditional rule: *if* a Canadian-coded destination ever appears in any consumed OD source, *then* route it to canada — but in practice this branch will not fire from LODES alone.

**Two paths to actually populate Canada-bound rows** (both deferred to follow-up work, neither blocking spec 063):

1. **StatCan augmentation file**: Statistics Canada publishes Detroit-Windsor cross-border commute estimates via the Census Survey of Cross-Border Commuters. These could be ingested as a separate `cross_border_commute_supplement.csv` and merged into the OD matrix at load time. Schema design and acquisition are out of scope for spec 063 but become a natural follow-on task.
2. **Synthetic baseline**: A documented constant for Detroit→Windsor commute volume (~12,000 daily commuters per published municipal data circa 2010, reduced to ~6,000 post-COVID) could be hard-coded as a synthetic OD row. Rejected for v1 — Constitution III.1 (No Magic Constants) requires the value trace to a federal data series, and a hard-coded number does not satisfy that. A `GameDefines` field with a documented source citation would be acceptable, but introducing it without a calibration plan is premature.

**Spec amendment**: FR-023 / FR-026 / SC-004 / SC-008 in `spec.md` were written assuming Windsor-coded destinations exist in the OD source. They remain valid as design contracts, but this research finding adds one Assumption: **"Canada-bound LODES rows do not exist in the canonical on-disk LODES dataset. The FR-023 classification rule is implemented and tested with synthetic OD rows in unit tests; the integration test FR-026 fail-fast invariant is exercised by injecting a synthetic Canadian-coded row at test time. Production Canada-bound flow population requires a separate StatCan-or-equivalent ingestion step (spec 064 candidate)."** This is added to the spec's Assumptions section as a follow-up edit at the close of plan phase.

**Classification rule mechanics** (in case future input data carries Canadian destinations): the destination's encoded country code is the discriminator. Census 2020 block IDs are 15 digits, all numeric, with the 2-digit state prefix in `{01-56, 60-78}` (US states + territories). Any destination whose first two digits do NOT fall in that range is treated as non-US. Within non-US, the spec assumes a single classification: any non-US destination from a Detroit-area origin maps to `'canada'`. (If future ingestion brings Mexico-bound or trans-Atlantic commute data, this rule extends straightforwardly.)

**Rationale**: The empirical verification of LODES file contents is non-negotiable — building the classifier to match data that doesn't exist would be malpractice. Surfacing the gap explicitly here means the spec can ship with the correct contract and the correct behavioral test (synthetic rows in unit tests, fail-fast guarded in integration tests), with the data-acquisition follow-on cleanly named.

**Alternatives considered**:

- **Pretend Canada-bound LODES rows exist and just emit zero in production**: wastes the FR-023 contract and obscures the actual data dependency. Rejected.
- **Block spec 063 until StatCan ingestion is built**: rejected — that would defer the entire Vol II Circulation system (3 of 4 user stories) for one cross-border edge case. The proper sequence is: (a) ship Vol II circulation now, (b) ship cross-border commute data ingestion separately when StatCan integration is prioritized.
- **Use the `cbsa` field in `us_xwalk.csv.gz` to detect cross-border CBSAs**: the Detroit CBSA (33860 — "Montgomery, AL" in the sample, but Detroit's CBSA is 19820) does not include Windsor; CBSAs are US-only by definition. Doesn't solve the gap.

---

## §5 — Performance Budget Validation

**Decision**: The CSR matrix-vector multiplication cost for the Detroit tri-county scope is comfortably below the SC-007 budget. Estimated bound: per-tick Circulation step wall time ≤ 50ms on commodity hardware.

**Sizing**:

- ~1,700 study-area hexes (Detroit tri-county at H3 res-7)
- ~60K LODES OD pairs per year for Michigan tri-county (post-pruning per FR-007)
- After hex aggregation (multiple blocks per hex), expect ~10K–30K nonzero matrix entries per year
- CSR matrix-vector multiplication for an N=1,700 dense vector and an N×N sparse matrix with 30K nnz: ~30K floating-point multiplications + 30K additions per tick
- Even at 10ns per op (extremely conservative), that's 0.6ms per tick

**SC-007 holds with 100× headroom** — the existing four flow stages take ~500ms per tick; 10% of that is 50ms; 50ms ÷ 0.6ms = ~80× headroom.

**Risk**: if the loader fails to prune correctly per FR-007 (e.g., loads the full state Michigan matrix at ~1M nonzeros instead of the tri-county subset at ~30K), the budget tightens to ~10ms estimated, still under SC-007 but with much less headroom. The contract test for FR-007 (loader rejects rows with neither origin nor destination in the study area) is therefore load-bearing.

**Year-load wall time** (FR-006): per-state per-year file ~5–20MB compressed. Stream-read + h3 mapping + aggregation: ~10s on commodity hardware. Per-Detroit-scenario session: 12 years = ~2 minutes session-init add-on. Acceptable for an init-time operation.

**Rationale**: scipy.sparse CSR is the standard sparse representation for this exact workload — sparse linear algebra over an empirical OD matrix has decades of tooling. The sizing is well within library performance norms; benchmarks aren't necessary at the spec stage. Per-tick instrumentation will be added during Phase 2 implementation to confirm SC-007 empirically.

**Alternatives considered**:

- **Dense numpy matrix**: simpler API but ~10× memory and ~100× compute for a 99% sparse matrix. Rejected — violates Constitution II.12.
- **GPU acceleration via CuPy or JAX**: zero current need at this scale. Rejected — premature.
- **Distributed compute via Dask / Ray**: zero current need at this scale. Rejected — overkill for ~1,700-row matrices.

---

## §6 — Block-Group → H3 Res-7 Crosswalk Approach

**Decision**: Use the existing `us_xwalk.csv.gz` (143MB) as the authoritative LODES-block → H3-res-7 mapping. The crosswalk file does not directly carry an `h3_res7` column, but it carries `blklatdd` and `blklondd` (block-centroid latitude/longitude in decimal degrees) along with the 15-digit `tabblk2020` ID. The loader resolves blocks → hexes via `h3.latlng_to_cell(lat, lng, 7)` per block.

**Verified file shape** (sampled above in §1):

```text
File:    /media/user/data/babylon-data/lodes/us_xwalk.csv.gz (143 MB)
Header:  tabblk2020,st,stusps,stname,cty,ctyname,trct,trctname,bgrp,bgrpname,cbsa,cbsaname,
         zcta,zctaname,stplc,stplcname,ctycsub,ctycsubname,stcd119,stcd119name,...,
         blklatdd,blklondd,createdate
```

The relevant columns for this feature: `tabblk2020` (block ID, 15 digits), `cty` (5-digit FIPS county), `blklatdd`, `blklondd`. Per-row processing: `h3_index = h3.latlng_to_cell(blklatdd, blklondd, 7)`.

**Implementation**: cache the entire crosswalk in memory at first use (~200MB peak after parsing). One-time cost per process. Subsequent LODES-year loads consult the in-memory map without re-parsing the file.

**Rationale**: The crosswalk is part of the existing fixture set; using `h3.latlng_to_cell` produces deterministic, bit-identical results across runs (Constitution III.7); the in-memory map fits in the host's memory budget comfortably (~500MB total simulation memory budget per session per spec 062 §13).

**Alternatives considered**:

- **Pre-compute a `block → h3_res7` lookup table at install time** and ship it as a binary fixture: faster startup but adds a build step. Rejected — at-process-init parsing is cheap enough (~5–10s once per process).
- **Use county FIPS as a coarser surrogate when block-level mapping is missing**: relevant only for blocks not in the crosswalk, which the existing crosswalk covers comprehensively for tri-county. Edge case handled by FR-022 / spec 062 fallback to `rest_of_usa`.

---

---

## §7 — Border Commute Synthesis Approach (Option B Scope)

**Decision**: Per the 2026-05-13 clarification, spec 063 includes a `BorderCommuteSynthesisLoader` that produces aggregate Detroit-Windsor commute rows by combining:

1. **BTS Border Crossing Data** (free, monthly CSV, 1996-present): southbound personal-vehicle counts at the Ambassador Bridge (port_code `3801`) and Detroit-Windsor Tunnel (port_code `3802`). Source: `https://data.bts.gov/stories/s/Border-Crossing-Entry-Data/jswi-2e7b/`. Populates the US-bound direction.
2. **StatCan Frontier Counts** (free, monthly, 2017-present, table `71-607-X2023020`): northbound personal-vehicle counts at the Windsor port of entry. Source: `https://www150.statcan.gc.ca/n1/en/catalogue/71-607-X2023020`. Populates the Canada-bound direction. Optional — if absent, the loader emits a one-time audit warning and produces US-bound rows only.
3. **Workforce WindsorEssex 2017 Cross-Border Employment Report**: provides the `border_commute_share` anchor (~6,120 commuters / ~12K daily personal-vehicle crossings ≈ 0.50). Source: `https://www.workforcewindsoressex.com/cross-border-employment/`. The 0.50 default lives in `GameDefines.border_commute_share` with a docstring citation per Constitution III.1.

**Synthesis formula**:
```
weekly_commuters[week] = monthly_vehicles[month_containing(week)] × border_commute_share / 4.33
```
where `4.33 = 52 weeks / 12 months`. The result is one `BorderCommuteFlow` row per (year, week_of_year, direction). For the Detroit corridor that's 52 × 2 = 104 rows per simulated year.

**Geometry**: synthesized rows are aggregate — they map a single representative tri-county hex (configurable per session) to `dest_node_id='canada'` (us_to_canada) or vice versa. **No hex-level disaggregation** is attempted; that would require restricted-access StatCan RDC microdata which is out of scope.

**Rationale**: This is the only realistic synthesis given the public-data inventory established in §4. It accepts the disaggregation gap (CMA-level aggregate vs LODES hex-level) in exchange for shipping a calibrated, verifiable cross-border flow. The synthesis is gated behind `GameDefines.enable_border_commute_synthesis` (default `False`) so the spec's default behavior is unchanged from the LODES-only path; opting in becomes a per-session configuration choice.

**Verifiability** (Constitution III.8 Aleksandrov Test): every synthesized magnitude traces back to a specific BTS row + a documented commuter-share anchor + an arithmetic operation. The `source_anchor` field on each `BorderCommuteFlow` carries the citation string for forensic recall. No magic constants — `border_commute_share` is the only tunable, and it is sourced + documented.

**Alternatives considered**:

- **Pay for StatCan RDC microdata access**: would yield hex-level OD pairs but requires research approval, paid access, and ongoing renewal. Rejected — not appropriate as a v1 dependency; revisit if the project secures research-access funding.
- **Hard-code a single annual commuter count from the WWE report (~6,120)**: would skip BTS entirely. Rejected — loses the temporal dynamics (commute volume varies seasonally and across years; COVID dropped Detroit-Windsor commute by ~50% in 2020-21 — important signal for the simulation).
- **Use only NEXUS enrollment as proxy**: confirmed §4 dead end; CBP doesn't publish NEXUS enrollment as a downloadable time series.
- **Defer synthesis to a future spec**: rejected per the user's Option B selection 2026-05-13. Bundling the synthesis with spec 063 keeps the cross-border story coherent in one delivery; the synthesis loader is small (~200 LOC estimated) and the data is public.

**Data acquisition operator note**: the BTS CSV download requires a one-time fetch from `https://data.bts.gov/api/views/keg4-3bc2/rows.csv` (or the dataset's current export endpoint) and placement at `data-trove/border_crossings/bts_border_crossings.csv`. The StatCan CSV requires a similar fetch from the table's export interface. Both acquisitions are operator tasks documented in the quickstart and not part of the engine code.

---

## Summary of Phase 0 Outputs

| Item | Resolved? | Spec amendment? | Downstream spec spawned? |
|---|---|---|---|
| §1 LODES file layout | ✅ Verified empirically | No — matches FR-001/FR-001a/FR-001b assumptions | No |
| §2 GATE-2 no-DB-IO | ✅ Confirmed | No — already enforced by spec 062 inheritance | No |
| §3 Vol II = min-cost flow | ✅ Inherited from spec 062 research §6 | No | Yes — slime-mold spec 064 candidate |
| §4 Canadian classification gap | ⚠️ Critical finding | **Yes** — add Assumption that LODES has no Canadian rows; FR-023 implementation tested via synthetic rows | Yes — StatCan ingestion follow-on |
| §5 Performance budget | ✅ ~80× headroom on SC-007 | No — confirms SC-007 budget is realistic | No |
| §6 Block-to-hex crosswalk | ✅ `us_xwalk.csv.gz` + `h3.latlng_to_cell` | No — already implicit in FR-002 | No |
| §7 Border commute synthesis | ✅ Option B scope adopted | Already integrated via FR-031..FR-036 + SC-011/SC-012 | Future RDC-microdata spec optional (not blocking) |

**Phase 0 closes with one spec amendment required** (the §4 Canadian-classification Assumption). Application of that amendment happens as part of `/speckit.plan` Phase 1 when this research is integrated; the spec edit is a single-line addition to the Assumptions section.

**All Constitution Check gates remain closed** — no surprises moved a gate from Pass to Fail.

**Ready for Phase 1**: data-model.md, contracts/, quickstart.md.
