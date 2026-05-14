# Data Model: Vol II Circulation System with LODES OD Integration

**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)
**Research**: [research.md](./research.md)
**Date**: 2026-05-13

This document specifies the data shapes and ownership relations for the spec 063 implementation. All entities use frozen Pydantic 2.x models per project standard. Postgres tables follow spec 062's `immutable_reference_*` and `dynamic_*` naming conventions and the per-subsystem ownership rule from Constitution II.11.

---

## §1 — Entity Catalog

### 1.1 LODESCommuteMatrixLoader (new — economics subsystem)

**Purpose**: Read the on-disk LODES OD CSV files for a single simulated year, build the H3-indexed sparse OD matrix, and serve the matrix to the `Vol2CirculationStep` per FR-001 / FR-001a / FR-001b / FR-002 / FR-007.

**Construction**:
```
LODESCommuteMatrixLoader(
    lodes_root: pathlib.Path,            # /media/user/data/babylon-data/lodes
    crosswalk_path: pathlib.Path,        # /media/user/data/babylon-data/lodes/us_xwalk.csv.gz
    study_area_hexes: frozenset[str],    # H3 res-7 cells of the study area
    study_area_states: frozenset[str],   # FIPS 2-digit state codes (e.g. {"26"} for Michigan)
)
```

**Public methods**:

| Method | Signature | Purpose |
|---|---|---|
| `load_year(year: int)` | `→ LODESYearMatrix` | Load + cache the matrix for one year. Idempotent within a process. |
| `available_years()` | `→ tuple[int, ...]` | Return the set of years for which `_main_` files exist on disk. |
| `clamp_to_available(target_year: int)` | `→ int` | If `target_year` not in `available_years()`, return the nearest available year per FR-004. |

**Validation rules**:
- `lodes_root` and `crosswalk_path` MUST exist and be readable; loader raises `FileNotFoundError` at construction if not (FR-026 fail-fast).
- `study_area_hexes` MUST be non-empty (loader can't prune without a study area).
- `study_area_states` MUST be a subset of valid FIPS state codes; loader raises `ValueError` on invalid prefixes.

### 1.2 LODESYearMatrix (new — economics subsystem)

**Purpose**: Frozen wrapper around the loaded `scipy.sparse.csr_matrix` for one year. Carries the row/column index mapping so callers can resolve hex IDs to matrix positions.

**Pydantic model** (with `arbitrary_types_allowed=True` for the scipy.sparse field):
```
LODESYearMatrix:
    year:                int                       # The simulated year this matrix represents
    matrix:              scipy.sparse.csr_matrix   # Shape: (n_origins, n_destinations); dtype=float64
    origin_hex_to_row:   dict[str, int]            # H3 res-7 index → matrix row
    dest_to_col:         dict[str, int]            # destination ID (hex or boundary bucket) → matrix col
    dest_kind_by_col:    tuple[NodeKind, ...]      # one entry per matrix col, indicating hex/external/etc.
    dest_node_id_by_col: tuple[str, ...]           # one entry per matrix col, gives the dest_node_id string
    row_sums:            numpy.ndarray             # cached row-sum vector (length n_origins) for FR-009 normalization
```

**Validation rules**:
- `matrix` MUST be CSR (Constitution II.12, GATE-4); enforced by validator.
- `origin_hex_to_row` and `dest_to_col` MUST be consistent with `matrix.shape`.
- `len(dest_kind_by_col) == len(dest_node_id_by_col) == matrix.shape[1]`.
- `row_sums.shape == (matrix.shape[0],)` and `numpy.allclose(row_sums, matrix.sum(axis=1).A1)`.
- All entries in `matrix.data` MUST be `>= 0` (worker counts are non-negative).
- The matrix is **immutable**: instances are frozen and the underlying `scipy.sparse.csr_matrix` is wrapped with a no-op-write guard (the frozen class refuses `setattr`, and any caller mutating `.data` directly violates the contract per FR-006).

### 1.3 Vol2CirculationStep (new — engine subsystem)

**Purpose**: The per-tick transformation that consumes the year's `LODESYearMatrix` plus current hex `v` vector and produces (a) the next-tick hex `v` vector and (b) the boundary register rows for cross-boundary commute. Sub-stage 5c of the per-tick pipeline (spec 062 FR-053 / spec 063 FR-015).

**Construction**:
```
Vol2CirculationStep(
    od_loader: LODESCommuteMatrixLoader,
    classifier: CrossBorderCommuteClassifier,
)
```

**Public method**:
```
step(
    graph: GraphProtocol,
    services: ServiceContainer,
    context: TickContext,
    register: BoundaryFlowRegister,
) → CirculationStepResult
```

**`CirculationStepResult`** (frozen Pydantic):
```
CirculationStepResult:
    tick:                       int
    pre_total_v:                Currency
    post_total_v_in_area:       Currency
    boundary_out_total_v:       Currency
    rows_emitted:               int      # total boundary register rows added (COMMUTE_OUT + paired TRADE_EDGE)
    od_year_used:               int      # the LODES year actually consumed (post FR-004 clamp)
    conservation_residual:      float    # |pre_total_v - (post_total_v_in_area + boundary_out_total_v)|
```

**Validation rules**:
- `pre_total_v` MUST equal `post_total_v_in_area + boundary_out_total_v` within `1e-9 × pre_total_v` (FR-010, SC-002).
- `rows_emitted` MUST equal `2 × <count of cross-boundary OD entries fired this tick>` because each `COMMUTE_OUT` is paired with a `TRADE_EDGE` per FR-030a.
- `od_year_used` MUST be in `od_loader.available_years()`.

### 1.4 CrossBorderCommuteClassifier (new — engine subsystem)

**Purpose**: Classify a LODES destination identifier into one of the three boundary categories per FR-023 / FR-024 / FR-025 / FR-028.

**Construction**:
```
CrossBorderCommuteClassifier(
    study_area_hexes:   frozenset[str],   # in-study-area H3 res-7 cells
    study_area_states:  frozenset[str],   # in-study-area FIPS state codes
    domestic_states:    frozenset[str],   # FIPS state codes considered "rest of USA"
)
```

**Public method**:
```
classify(dest_id: str) → CrossBorderClassification
```

**`CrossBorderClassification`** (frozen Pydantic):
```
CrossBorderClassification:
    dest_kind:    NodeKind   # one of {hex, external}
    dest_node_id: str        # H3 cell ID, "canada", or "rest_of_usa"
```

**Classification rule** (per FR-025 / research §4) — the `domestic_states` constructor parameter is the single source of truth for what counts as US-domestic:
1. If `dest_id` is an H3 res-7 cell in `study_area_hexes` → `(NodeKind.HEX, dest_id)`.
2. Else if `dest_id` is a 15-digit Census 2020 block code with state-prefix (first 2 digits) in **`domestic_states`** → US-domestic → `(NodeKind.EXTERNAL, "rest_of_usa")` (FR-024 — out-of-study-area but domestic).
3. Else if `dest_id` is a 15-digit code with state-prefix NOT in **`domestic_states`** → non-US → `(NodeKind.EXTERNAL, "canada")` (FR-023 — only Canadian destinations expected; spec 064 will extend if Mexico/etc. arrive).
4. Else (unrecognized destination format — non-numeric, wrong length, etc.) → `(NodeKind.EXTERNAL, "rest_of_usa")` + emit one audit log entry per unique unmapped destination (FR-028).

A typical `domestic_states` value for the Detroit scenario is the full set of US FIPS state codes `{"01", "02", "04", ..., "56", "60", "66", "69", "72", "78"}` (50 states + DC + 5 territories per Census 2020). Sessions that need to model additional countries as boundary nodes can extend `domestic_states` to exclude those ranges, automatically routing them through step 3.

**Validation rules**:
- All three frozensets MUST be non-empty.
- `domestic_states` MUST be a superset of `study_area_states` (the study area is, definitionally, domestic).
- Every entry in `domestic_states` MUST match `^[0-9]{2}$` (2-digit FIPS state code).

### 1.5 BoundaryFlowRegister (extended — economics subsystem, no schema change)

**No new fields.** The existing schema from spec 062 (`source_node_id`, `source_kind`, `dest_node_id`, `dest_kind`, `flow_type`, `magnitude`) covers all spec-063 emissions. The `flow_type` enum already includes `COMMUTE_OUT`, `TRADE_EDGE`, and `DRAIN_EDGE`.

**New emission patterns** introduced by this spec:
- One `COMMUTE_OUT` row per cross-boundary OD entry (`source_kind=hex`, `dest_kind=external`)
- One paired `TRADE_EDGE` row per `COMMUTE_OUT` (FR-030a — swapped source/dest, `source_kind=external`, `dest_kind=hex`, equal magnitude)
- One `DRAIN_EDGE` row per (external source, county dest) Φ distribution (`source_kind=external`, `dest_kind=county` — wired by T079 from existing helper)

**Pairing invariant** (FR-030c) is enforced by the conservation auditor (spec 062's `ConservationAuditor` extended with one new evaluator `PairedCrossBorderEmissionEvaluator`).

### 1.5b BorderCommuteSynthesisLoader (new — economics subsystem, Option B scope)

**Purpose**: Synthesize aggregate Detroit-Windsor cross-border commute rows by combining BTS Border Crossing Data (US-bound personal vehicles) with StatCan Frontier Counts (Canada-bound personal vehicles) and applying the `border_commute_share` anchor from the WWE 2017 Cross-Border Employment Report. Produces ~52 weekly Canadian-bound aggregate flow rows per simulated year that merge into the `LODESYearMatrix` at session-init time.

Implements FR-031 / FR-032 / FR-033 / FR-034 / FR-035 / FR-036.

**Construction**:
```
BorderCommuteSynthesisLoader(
    bts_csv_path:           pathlib.Path | None,    # data-trove/border_crossings/bts_border_crossings.csv
    statcan_csv_path:       pathlib.Path | None,    # data-trove/border_crossings/statcan_frontier_counts.csv
    border_commute_share:   float,                  # default 0.50 from GameDefines (WWE 2017 anchor)
    detroit_port_codes:     frozenset[str],         # BTS port codes for Ambassador Bridge + DW Tunnel
    tri_county_aggregate_hex: str,                  # representative H3 cell for the tri-county aggregate
    enabled:                bool = False,           # gated by GameDefines.enable_border_commute_synthesis
)
```

**Public methods**:

| Method | Signature | Purpose |
|---|---|---|
| `synthesize_year(year: int)` | `→ tuple[BorderCommuteFlow, ...]` | Produce ~52 weekly Canadian-bound aggregate rows for the given year (one per direction per week) |
| `merge_into_year_matrix(matrix: LODESYearMatrix, year: int)` | `→ LODESYearMatrix` | Return a new immutable matrix with synthesized rows added as additional sparse entries; `dest_node_id='canada'`, `dest_kind=external` |
| `is_enabled()` | `→ bool` | Returns True iff `enabled` AND BTS file present (per FR-036 fail-fast) |

**`BorderCommuteFlow`** (frozen Pydantic):
```
BorderCommuteFlow:
    year:               int
    week_of_year:       int = Field(ge=1, le=52)
    direction:          Literal["us_to_canada", "canada_to_us"]
    aggregate_origin:   str         # H3 cell (representative tri-county aggregate)
    aggregate_dest:     str         # "canada" or H3 cell
    magnitude_workers:  float       # commuter count for this week (vehicle_count × border_commute_share / 4.33 weeks/month)
    source_anchor:      str         # citation: "WWE 2017; BTS port_code=3801,3802"
```

**Validation rules**:
- `border_commute_share ∈ (0, 1]`; raises `ValueError` if 0 or > 1.
- When `enabled=True` and `bts_csv_path` is None or missing, raises `FileNotFoundError` at construction (FR-036 fail-fast).
- When `enabled=False`, all methods become no-ops (`synthesize_year` returns empty tuple, `merge_into_year_matrix` returns the input matrix unchanged).
- The synthesized flow magnitudes for any year MUST be deterministic given the same input CSVs (FR-005 inheritance via determinism principle).

### 1.6 ImperialRentSystem (extended — engine subsystem, no schema change)

**Step body** post-spec-063 wiring:
```
def step(self, graph, services, context):
    # Sub-stage 5b — Imperial Rent inflow (existing)
    distribute_phi_week_to_counties(
        external_nodes=self._external_nodes_from_graph(graph),
        county_exposure_weights=self._exposure_weights_from_services(services),
        register=context.boundary_flow_register,
        tick=context.tick,
        session_id=context.session_id,
    )  # T079 — newly invoked from step body

    # Sub-stage 5c — Vol II Circulation (new)
    self._vol2_step.step(
        graph=graph,
        services=services,
        context=context,
        register=context.boundary_flow_register,
    )  # T055 — invoked at the right pipeline position per FR-015

    # Sub-stages 5d (Equalization) and 5e (Distribution) continue as already-wired
```

**No new state fields** — all new behavior is functional invocation of new collaborators.

---

## §2 — Postgres Schema (new migration `0014_lodes_od_matrix.py`)

### 2.1 `immutable_reference_lodes_od_matrix`

**Owner subsystem**: economics (sibling of `immutable_reference_qcew_employment` per spec 062 ownership table).

```sql
CREATE TABLE immutable_reference_lodes_od_matrix (
    session_id         UUID    NOT NULL,
    year               INTEGER NOT NULL,
    home_hex           TEXT    NOT NULL,            -- H3 res-7 origin cell ID
    workplace_dest     TEXT    NOT NULL,            -- H3 cell, "canada", or "rest_of_usa"
    workplace_dest_kind TEXT   NOT NULL,            -- NodeKind enum: 'hex' | 'external'
    s000_workers       BIGINT  NOT NULL CHECK (s000_workers >= 0),
    PRIMARY KEY (session_id, year, home_hex, workplace_dest)
);

CREATE INDEX ix_lodes_od_session_year ON immutable_reference_lodes_od_matrix (session_id, year);
CREATE INDEX ix_lodes_od_year_home    ON immutable_reference_lodes_od_matrix (year, home_hex);
```

**Population**:
- Written once per session by `LODESCommuteMatrixLoader.persist_to_postgres()` after the on-disk LODES files for the scenario's years are processed.
- Read once per year-rollover by `LODESCommuteMatrixLoader.load_year_from_postgres()` for sessions resumed from a checkpoint (so hot-restart doesn't require re-parsing the on-disk LODES files).
- **Never mutated at runtime** — Constitution II.6 + spec 062 GATE-2.

**Why this table** (despite the on-disk LODES files): once a session is initialized, the on-disk files are no longer the authority; the Postgres copy is. This matches spec 062's `immutable_reference_*` pattern exactly: SQLite is read at init only; the Postgres copy is the runtime source. For LODES, the on-disk gzip CSVs are the equivalent of SQLite — read at init, copied to Postgres, never re-read from disk during a tick.

### 2.2 `immutable_reference_border_commute_synthesis` (new — Option B scope)

**Owner subsystem**: economics.

```sql
CREATE TABLE immutable_reference_border_commute_synthesis (
    session_id              UUID    NOT NULL,
    year                    INTEGER NOT NULL,
    week_of_year            INTEGER NOT NULL CHECK (week_of_year BETWEEN 1 AND 52),
    direction               TEXT    NOT NULL CHECK (direction IN ('us_to_canada', 'canada_to_us')),
    aggregate_origin        TEXT    NOT NULL,
    aggregate_dest          TEXT    NOT NULL,
    magnitude_workers       DOUBLE PRECISION NOT NULL CHECK (magnitude_workers >= 0),
    source_anchor           TEXT    NOT NULL,
    PRIMARY KEY (session_id, year, week_of_year, direction)
);

CREATE INDEX ix_border_synth_session_year ON immutable_reference_border_commute_synthesis (session_id, year);
```

**Population**: written once per session by `BorderCommuteSynthesisLoader.persist_to_postgres()` after BTS + StatCan CSVs are processed at session-init time. Read once per year-rollover by `Vol2CirculationStep` indirectly via `BorderCommuteSynthesisLoader.merge_into_year_matrix()`. **Never mutated at runtime** per Constitution II.6 + spec 062 GATE-2.

**Why this table** (vs computing on-the-fly each tick): like LODES, the synthesis is a year-scoped immutable input. Caching to Postgres lets a hot-restart resume without re-parsing BTS + StatCan CSVs and preserves the determinism contract (FR-035 — identical inputs produce identical synthesized rows; the cached table acts as the canonical record).

### 2.3 No `dynamic_*` table changes

All per-tick output from this feature lands in the existing `boundary_flow_register` (spec 062 migration 0013). No new dynamic tables.

---

## §3 — Subsystem Ownership Table (Constitution II.11 / GATE-3)

| Table / Module | Owner Subsystem | Cross-Subsystem Access | Notes |
|---|---|---|---|
| `immutable_reference_lodes_od_matrix` (Postgres) | economics | via `LODESCommuteMatrixLoader.load_year_from_postgres()` | No raw SQL allowed from non-economics callers |
| `immutable_reference_border_commute_synthesis` (Postgres) | economics | via `BorderCommuteSynthesisLoader.synthesize_year()` | No raw SQL allowed from non-economics callers |
| `LODESCommuteMatrixLoader` (Python class) | economics | via constructor injection into `Vol2CirculationStep` | Loader is the engine's only access path to the matrix |
| `BorderCommuteSynthesisLoader` (Python class) | economics | injected into `LODESCommuteMatrixLoader` for matrix merging | Loader is the engine's only access path to the synthesis |
| `LODESYearMatrix` (Python class) | economics | shared with engine via the Loader's `load_year()` return | Frozen; safe to share |
| `BorderCommuteFlow` (Python class) | economics | shared via `synthesize_year()` return | Frozen; safe to share |
| `Vol2CirculationStep` (Python class) | engine | invoked by `ImperialRentSystem.step()` only | Sub-stage 5c |
| `CrossBorderCommuteClassifier` (Python class) | engine | injected into `Vol2CirculationStep` via constructor | Stateless; no inter-tick state |
| `boundary_flow_register` table (Postgres) | economics (per spec 062) | via `BoundaryFlowRegister.record()` | Inherited; no change |
| `PairedCrossBorderEmissionEvaluator` (new evaluator) | economics | registered with `ConservationAuditor` at session init | One audit row per failure per tick |

**No cross-subsystem table reads bypass the loader/register APIs.** GATE-3 closed.

---

## §4 — Determinism Hash Contract (Constitution III.7 / GATE-1)

The per-tick determinism hash from spec 062 (SHA-256 over canonicalized hex state) extends naturally to spec 063:

- Circulation post-state is the in-place mutation of `v` on hex graph nodes; already in the hash domain.
- New `COMMUTE_OUT` and `TRADE_EDGE` boundary register rows committed at end-of-tick are part of the per-tick envelope; included in the existing tick hash via the envelope's row digest (spec 062 FR-008a).
- The OD matrix used for the tick is identified by `od_year_used` in `CirculationStepResult`; the year is part of the tick context and contributes to the input-hash side of the determinism contract.

**Property**: same `(v_pre, OD_matrix, classifier_config)` → bit-identical `(v_post, boundary_register_rows)`. Verified by SC-005.

---

## §5 — Lifecycle / State Transitions

### 5.1 LODES year rollover at tick boundary

When the simulated date crosses a calendar year boundary (e.g., tick 51 → tick 52 maps to year 2010 → 2011):

1. **At the tick boundary (between ticks)**: The engine asks `od_loader.load_year(new_year)`.
2. **Loader**: Returns the cached `LODESYearMatrix` if present; otherwise loads from Postgres `immutable_reference_lodes_od_matrix` (or, if Postgres is empty, from the on-disk LODES files at session-init phase).
3. **Engine**: Updates the `Vol2CirculationStep` instance's reference to the new `LODESYearMatrix`.
4. **Audit log**: One entry per year rollover recording `(prev_year, new_year, matrix_nnz)` for forensic tracking.

**Within a tick**: the matrix MUST NOT change (FR-006). Mid-tick rollover is forbidden.

### 5.2 Year clamp (FR-004)

When the scenario's simulated year exceeds the LODES coverage window (e.g., simulated year 2025, LODES covers 2010-2021):

1. `od_loader.clamp_to_available(2025)` returns `2021` (the latest available year).
2. One audit log entry per session per clamped year naming the substitution.
3. Ticks proceed normally with the clamped matrix.

### 5.3 Session initialization order

1. `initialize_session()` opens Postgres connection + creates session row.
2. `_bootstrap_external_nodes()` writes the 9 external nodes incl. canada (spec 062 T078, already shipped).
3. **NEW** `_hydrate_lodes_od_matrices()` loads the on-disk LODES files for each scenario year and persists to `immutable_reference_lodes_od_matrix`.
4. **NEW** Optional `_validate_canada_in_external_nodes_if_lodes_has_canadian_dests()` fires the FR-026 fail-fast check: if any `workplace_dest_kind='external'` row was added with `workplace_dest='canada'` AND `canada` is missing from `dynamic_external_node_state`, refuse to start.

---

## §6 — Migration Order

| Step | Action | Reversibility |
|---|---|---|
| 1 | `0014_lodes_od_matrix.py` migration creates `immutable_reference_lodes_od_matrix` table + 2 indexes | Reversible (drop table) |
| 2 | Loader, classifier, circulation step modules added to `src/babylon/` | Reversible (delete files) |
| 3 | `ImperialRentSystem.step()` updated to invoke `distribute_phi_week_to_counties()` + `Vol2CirculationStep.step()` | Reversible (revert system module) |
| 4 | `postgres_initialization.py` extended to call `_hydrate_lodes_od_matrices()` | Reversible (revert init module) |
| 5 | `ConservationAuditor` extended with `PairedCrossBorderEmissionEvaluator` | Reversible (deregister evaluator) |

No data backfill needed for existing sessions — the new immutable-reference table is empty for sessions started before this feature; new sessions populate it at init.
