# Implementation Brief — Phase 6.2 `feat/spec-063-tail`: spec-063 honest gaps (T042 + T043 + 5 integration tests)

**Repo**: `/home/user/projects/game/babylon` (all paths below relative to this root unless absolute).
**Branch**: `git checkout dev && git checkout -b feat/spec-063-tail` (dev HEAD at scouting time: `3f9d1d69`).
**Naming correction**: spec-063 is **`specs/063-vol-ii-circulation/`** (Vol II Circulation + LODES OD), NOT "cross-scale integration" (that is spec-062). Spec-062's tasks.md has its *own* T042/T043 which are both `[X]` and unrelated. The two open tasks live at `specs/063-vol-ii-circulation/tasks.md:128` (T042) and `:129` (T043).

---

## 0. Verified current state (all claims checked against code 2026-07-08)

| Claim | Verdict | Anchor |
|---|---|---|
| `BorderCommuteSynthesisLoader` exists but never instantiated at session init | **CONFIRMED** | class at `src/babylon/economics/border_commute_synthesis.py:85`; `rg -n "BorderCommuteSynthesisLoader" src/` shows zero call sites outside its own module |
| Only a report field exists at `postgres_initialization.py:107` | **CONFIRMED exactly** | `src/babylon/persistence/postgres_initialization.py:106-107`: `# Spec 063 — Option B border-commute synthesis hydration counts.` / `border_synthesis_row_count: int = 0` — never written anywhere |
| `PairedCrossBorderEmissionEvaluator` does not exist | **CONFIRMED** | `rg -n "PairedCrossBorderEmissionEvaluator" src/ tests/` → 0 hits in code; only in `specs/063-vol-ii-circulation/{tasks.md:129,data-model.md,plan.md}` |
| ConservationAuditor registration mechanism | **CONFIRMED** | `ConservationAuditor.register_invariant(name, evaluator)` at `src/babylon/persistence/conservation_audit.py:309-317`; evaluator signature `(pre_state, post_state, context) -> Iterable[_InvariantResult]`; the ONLY production construction+registration site is `src/babylon/engine/headless_runner/runner.py:990-997` (phi evaluator registered at :995-997) |
| Canada boundary node (spec-062) | **CONFIRMED** | `INTERNATIONAL_NODES` includes `"canada"` first (`postgres_initialization.py:114-124`, R4 amendment); bootstrapped as `ExternalNode(kind=INTERNATIONAL)` at tick 0 via `_bootstrap_external_nodes` (`:522-598`); Φ attributed by bilateral-trade share, canada→bloc 7 North America (`_NODE_TO_BLOC`, `:371-379`) |

### Key mechanics a fresh engineer must know

- **Loader** (`border_commute_synthesis.py`): ctor (`:97-135`) takes keyword-only `bts_csv_path: Path|None, statcan_csv_path: Path|None, border_commute_share: float, detroit_port_codes: frozenset[str], tri_county_aggregate_hex: str, enabled: bool=False`. FR-036 fail-fast (`:121-126`) raises `FileNotFoundError` when `enabled=True` and BTS missing. Methods: `is_enabled()` (`:137`), `synthesize_year(year) -> tuple[BorderCommuteFlow, ...]` (`:141` — 52 weekly rows/direction; StatCan absent → `us_to_canada` only), `persist_to_postgres(*, runtime, session_id, years) -> int` (`:200-249`, INSERT into `immutable_reference_border_commute_synthesis`, `ON CONFLICT ... DO NOTHING`).
- **Config gate**: `GameDefines().economy.enable_border_commute_synthesis` (default False) at `src/babylon/config/defines/economy_basic.py:458-468`; `border_commute_share` (0.50, WWE-2017-cited) at `:446-457`. `EconomyDefines` is frozen (`:152`).
- **Postgres tables** (migrations already shipped, applied by both `runner._apply_migrations` `runner.py:260-274` and integration-test fixture `apply_062_migrations`): `immutable_reference_border_commute_synthesis` (`migrations/0017_border_commute_synthesis.sql`, PK `(session_id, year, week_of_year, direction)`) and `immutable_reference_lodes_od_matrix` (`0016_lodes_od_matrix.sql`, PK `(session_id, year, home_hex, workplace_dest)`, `s000_workers BIGINT`, `workplace_dest_kind IN ('hex','external')`).
- **T042 wiring point**: `initialize_session()` at `postgres_initialization.py:601-798`. The Spec-063 LODES hydration block is `:740-771` (gated on 4 `lodes_*` kwargs, `:743-748`); the FR-026 canada fail-fast guard is `:773-796`. **The synthesis block goes between them** (after `report.lodes_row_count` at `:771`, before the FR-026 check) so merged canada rows are visible to the guard.
- **`LODESCommuteMatrixLoader`** (`src/babylon/economics/lodes_commute_matrix.py:158`): `persist_to_postgres(runtime, session_id, year)` (`:284-321`), `load_year_from_postgres(runtime, session_id, year)` (`:323-366`) rebuilds a `LODESYearMatrix` from the Postgres rows. It **never reads the synthesis table** — merging must land canada rows in `immutable_reference_lodes_od_matrix` for read-back to work.
- **Emission + pairing** (what the T043 evaluator audits): `Vol2CirculationStep.step()` (`src/babylon/engine/systems/vol2_circulation.py:120-296`) records `COMMUTE_OUT` (hex→external, `:246-255`) immediately followed by the FR-030a paired `TRADE_EDGE` (external→hex, swapped endpoints, equal magnitude, `:257-266`). Rows buffer in `BoundaryFlowRegister` (`src/babylon/economics/boundary_flow_register.py:47-132`; frozen-Pydantic `BoundaryFlowRegisterRow` `:26-44`; enums `BoundaryEdgeKind.COMMUTE_OUT/TRADE_EDGE`, `NodeKind.HEX/EXTERNAL` from `src/babylon/economics/node_kinds.py:45-47`).
- **Audit plumbing**: the bridge flushes the register (`src/babylon/engine/headless_runner/bridge.py:490`), builds `audit_context = {"boundary_rows", "external_nodes_phi", "national_phi_reference", "weeks_per_year"}` (`:523-530`), calls `auditor.audit_end_of_tick(...)` (`:531-536`), and rides `audit_log_rows` + `boundary_register_rows` in the same `PerTickTransactionEnvelope` → `persist_tick_atomic` (FR-008a single transaction, `src/babylon/persistence/postgres_runtime/_spec_062.py:270-359`). **`boundary_rows` is already in the context** — the new evaluator needs zero bridge changes.
- **Audit row constraints** (shape the evaluator): `ConservationAuditRow.scale` max_length=32 (`src/babylon/persistence/audit_models.py:60`); DB CHECK admits only `('hex','county','state','national','global_phi','per_stage')` **or `scale LIKE 'external:%'`** (`migrations/0031_conservation_audit_external_scale.sql`); PK is `(session_id, tick, scale, invariant_name)` (`0014_conservation_audit_log.sql:22`) with `ON CONFLICT DO NOTHING` on insert. Severity: `grade_severity` (`conservation_audit.py:51-67`) — residual >1e-6 → ALARM.
- **Dormancy warning**: the engine invokes Vol2 only via `ImperialRentSystem._invoke_vol2_circulation_if_wired` (`src/babylon/engine/systems/economic.py:101,173-206`), gated on context keys `vol2_step`/`boundary_flow_register`/`session_id`/`simulated_year` — **nothing in `src/` ever sets `vol2_step`**, so an engine tick emits no COMMUTE_OUT today. Integration tests must invoke `Vol2CirculationStep.step()` directly (runtime activation is remediation Phase 5.2, NOT this branch).
- **Test infra**: `pg_pool` session fixture at `tests/conftest.py:322-340` (skips without Postgres; default DSN `dbname=babylon_test host=localhost port=5433 user=test password=test`; bring up via `mise run db:up`). Integration template: `tests/integration/test_two_phase_initialization.py` (module `apply_062_migrations` + `runtime` + `sqlite_path` fixtures; `DETROIT_TRI_COUNTY = ["26163","26125","26099"]`; `pytestmark = [pytest.mark.cross_scale, pytest.mark.integration]`; `pytest.importorskip("psycopg")`). Evaluator unit-test template: `tests/unit/persistence/test_phi_week_conservation.py`. Geometry/port constants: `tests/constants_063.py` (`DETROIT_PORT_CODES = {"3801","3802"}` `:34`, `DETROIT_TRI_COUNTY_AGGREGATE_HEX` `:86` — computes to `872ab2c58ffffff`, matching the literal at `tests/unit/economics/circulation/test_border_commute_synthesis.py:21`).
- **Operator data NOT acquired**: no `border_crossings/` dir exists under `/media/user/data/babylon-data/` (repo `data/` is a symlink farm into that trove; `data/lodes → /media/user/data/babylon-data/lodes` exists with `od/` + `us_xwalk.csv.gz`). All synthesis tests must use synthetic BTS CSVs (`_write_minimal_bts_csv` pattern, `test_border_commute_synthesis.py:25-40`); real-data paths stay skip-gated (T050 operator step outstanding).

---

## 1. T043 — `paired_cross_border_emission` evaluator (do FIRST; zero-dependency, pure)

### 1a. RED — new unit test `tests/unit/persistence/test_paired_cross_border_emission.py`

Model directly on `tests/unit/persistence/test_phi_week_conservation.py` (helpers `_commute_out(origin, dest, mag)` / `_trade_edge(dest, origin, mag)` building `BoundaryFlowRegisterRow`s). Cases:

1. `test_fully_paired_rows_yield_ok_result` — 2 COMMUTE_OUT (hex→canada, hex→rest_of_usa) each with swapped-equal TRADE_EDGE → one result per dest, `computed_value == 0.0`, `expected_value == 0.0`; through `ConservationAuditor` (`epsilon=1e-9, rng_seed=42`) + `register_invariant("paired_cross_border_emission", ...)` + `evaluate(...)` → all rows `AuditSeverity.OK`, `alarms == []`.
2. `test_missing_pair_yields_alarm` — COMMUTE_OUT to canada without TRADE_EDGE → result `scale == "external:canada"`, `computed_value == 1.0`, `expected_value == 0.0`; via auditor → 1 ALARM `ConservationAlarmEvent`.
3. `test_magnitude_mismatch_counts_as_missing` — pair exists but TRADE_EDGE magnitude differs by 0.5 → ALARM.
4. `test_two_missing_pairs_same_dest_aggregate_to_one_row` — 2 origins → canada, no pairs → **one** result, `computed_value == 2.0` (PK-safety property, see design note).
5. `test_multiple_rows_same_origin_dest_sum_before_compare` — two COMMUTE_OUT (o1→canada, 10.0 + 5.0) + two TRADE_EDGE (canada→o1, 10.0 + 5.0) → OK (magnitudes summed per `(origin,dest)` key before comparing).
6. `test_non_external_commute_and_none_context_ignored` — `dest_kind=HEX` COMMUTE_OUT ignored; `evaluator(None, None, None) == []`.
7. `test_no_commute_out_yields_no_results` — DRAIN_EDGE-only context → `[]` (evaluator is silent when Vol2 hasn't run — prevents false alarms on every current production tick where Vol2 is dormant).

`pytestmark = [pytest.mark.unit]`. Run: `poetry run pytest tests/unit/persistence/test_paired_cross_border_emission.py -v` → RED (ImportError).

### 1b. GREEN — implement in `src/babylon/persistence/conservation_audit.py`

Design note (deviation from tasks.md:129 wording, forced by schema): "one audit row per missing pair" is physically impossible — `conservation_audit_log` PK is `(session_id, tick, scale, invariant_name)` and `scale` is ≤32 chars with a CHECK admitting only `external:%` for boundary scales; per-pair rows for the same dest in one tick would silently vanish under `ON CONFLICT DO NOTHING`. Aggregate **one result per external dest node**, `computed_value = missing-pair count`, `expected_value = 0.0` → residual ≥1 > 1e-6 → ALARM per FR-030c ("MUST surface as an audit-log alarm in the per-tick conservation auditor" — satisfied). Document this in the docstring.

Spec chose a function (matching `phi_week_conservation_evaluator` house style) rather than a class — tasks.md names a class but the registry accepts any callable; keep the module's existing idiom. Insert after `phi_week_conservation_evaluator` (after line 234):

```python
def paired_cross_border_emission_evaluator(
    _pre_state: Any, _post_state: Any, context: Any
) -> list[_InvariantResult]:
    """Evaluate the FR-030c COMMUTE_OUT ↔ paired TRADE_EDGE contract (spec-063 T043).

    Registered on the :class:`ConservationAuditor` under the
    ``paired_cross_border_emission`` invariant. Reads the tick's flushed
    boundary rows from ``context["boundary_rows"]`` (the same key the
    bridge already populates for the phi-week evaluator).

    For every ``COMMUTE_OUT`` row with ``dest_kind=EXTERNAL``, FR-030a
    requires a paired ``TRADE_EDGE`` with swapped source/dest and equal
    magnitude in the SAME tick. Magnitudes are summed per
    ``(origin_hex, external_dest)`` key on both sides before comparison so
    classifier fan-in (two raw dests resolving to one node id) pairs cleanly.

    **Aggregation note (deliberate deviation from tasks.md T043 wording)**:
    results aggregate to ONE row per external dest node
    (``scale=external:<dest>``, ``computed_value=<missing-pair count>``,
    ``expected_value=0.0``) rather than one row per missing pair — the
    ``conservation_audit_log`` primary key ``(session_id, tick, scale,
    invariant_name)`` plus the 32-char ``external:%`` scale CHECK
    (migration 0031) cannot represent per-pair rows without silent
    ``ON CONFLICT DO NOTHING`` drops. Any missing pair still grades ALARM
    (residual >= 1 > 1e-6) in the same tick, per FR-030c.

    Ticks with no external ``COMMUTE_OUT`` yield no results (the Vol II
    sub-stage only runs when wired — emitting OK rows for dormant ticks
    would be noise).

    Args:
        _pre_state: Unused (signature parity with other evaluators).
        _post_state: Unused.
        context: Per-tick audit context carrying ``boundary_rows``.
            ``None`` yields no results.

    Returns:
        One ``_InvariantResult`` per external dest node that received at
        least one ``COMMUTE_OUT`` this tick; ``computed_value`` is the
        count of unpaired ``(origin, dest)`` keys for that dest.
    """
    import math

    from babylon.economics.node_kinds import BoundaryEdgeKind, NodeKind

    if context is None:
        return []
    boundary_rows = context.get("boundary_rows") or []

    out_by_pair: dict[tuple[str, str], float] = {}
    trade_by_pair: dict[tuple[str, str], float] = {}
    for row in boundary_rows:
        if (
            row.flow_type is BoundaryEdgeKind.COMMUTE_OUT
            and row.source_kind is NodeKind.HEX
            and row.dest_kind is NodeKind.EXTERNAL
        ):
            key = (row.source_node_id, row.dest_node_id)
            out_by_pair[key] = out_by_pair.get(key, 0.0) + row.magnitude
        elif (
            row.flow_type is BoundaryEdgeKind.TRADE_EDGE
            and row.source_kind is NodeKind.EXTERNAL
            and row.dest_kind is NodeKind.HEX
        ):
            # Stored swapped (external source, hex dest); re-key to the
            # COMMUTE_OUT orientation for pair lookup.
            key = (row.dest_node_id, row.source_node_id)
            trade_by_pair[key] = trade_by_pair.get(key, 0.0) + row.magnitude

    missing_by_dest: dict[str, int] = {}
    dests_seen: set[str] = set()
    for (origin, dest), out_sum in out_by_pair.items():
        dests_seen.add(dest)
        paired = trade_by_pair.get((origin, dest))
        if paired is None or not math.isclose(
            paired, out_sum, rel_tol=1e-9, abs_tol=1e-12
        ):
            missing_by_dest[dest] = missing_by_dest.get(dest, 0) + 1

    return [
        _InvariantResult(
            scale=f"external:{dest}"[:32],
            invariant_name="paired_cross_border_emission",
            computed_value=float(missing_by_dest.get(dest, 0)),
            expected_value=0.0,
        )
        for dest in sorted(dests_seen)
    ]
```

Add `"paired_cross_border_emission_evaluator"` to `__all__` (`conservation_audit.py:437-443`). **Do NOT touch `_DEFAULT_INVARIANTS`** (`:272-294`) — `tests/unit/persistence/test_conservation_auditor.py:163-166` pins the canonical 21-element audit_log.yaml enumeration; registration is via `register_invariant` only (same as the phi evaluator, which is also not in the default list).

### 1c. Registration at session init — `src/babylon/engine/headless_runner/runner.py`

Extend the import at `:931-935` and add after the phi registration (`:995-997`):

```python
        # Spec-063 T043 / FR-030c: every external COMMUTE_OUT must carry a
        # paired TRADE_EDGE (swapped endpoints, equal magnitude) in-tick.
        auditor.register_invariant(
            "paired_cross_border_emission", paired_cross_border_emission_evaluator
        )
```

No bridge change needed — `boundary_rows` is already in `audit_context` (`bridge.py:523`). No migration needed — invariant_name is unconstrained TEXT; scale reuses the `external:%` namespace from migration 0031.

**Commit 1**: `feat(spec-063): T043 paired_cross_border_emission conservation evaluator + runner registration`

---

## 2. T042 — wire `BorderCommuteSynthesisLoader` into `initialize_session`

### 2a. RED — extend `tests/unit/economics/circulation/test_border_commute_synthesis.py`

T040's `[X]` claimed `merge_into_year_matrix` per data-model §1.5b (`specs/063-vol-ii-circulation/data-model.md:176`) — **it does not exist** (loader has only `synthesize_year`/`persist_to_postgres`/`is_enabled`). Implement it now; it is the in-memory half of the T042 merge. New tests (reuse `_write_minimal_bts_csv` + `_TRI_COUNTY_AGGREGATE_HEX` already in the file):

1. `test_merge_disabled_returns_input_unchanged` — disabled loader + any `LODESYearMatrix` → same object returned (`is` identity).
2. `test_merge_adds_canada_column_with_mean_weekly_magnitude` — enabled loader (synthetic BTS, 10,000 vehicles/month) + a small 1-origin matrix → returned matrix has `"canada" in merged.dest_to_col`, `dest_kind_by_col[col] is NodeKind.EXTERNAL`, entry at `(tri_county_aggregate_hex row, canada col)` ≈ `round(10_000 * 0.5 / (52/12))` (mean of 52 equal weekly rows = the weekly value ≈ 1153.85 → 1154), and original matrix object is untouched (frozen model; assert original `dest_to_col` lacks canada).
3. `test_merge_creates_origin_row_when_aggregate_hex_absent` — matrix without the aggregate hex as an origin → merged matrix gains the row; `row_sums` consistent (`LODESYearMatrix` model_validator enforces `row_sums == matrix.sum(axis=1)` — build via the same pair-counts path).

### 2b. GREEN — `src/babylon/economics/border_commute_synthesis.py`

Add module-level production constants (currently test-only in `tests/constants_063.py` — production needs its own per Constitution III.1; do NOT modify the tests module):

```python
# BTS port-of-entry codes for the Detroit-Windsor crossings (research §7).
DETROIT_PORT_CODES: frozenset[str] = frozenset({"3801", "3802"})

# Default fixture locations per spec FR-032/FR-033 (repo `data/` symlink farm
# realizes the spec's `data-trove/`; operator acquisition steps = tasks T050).
DEFAULT_BTS_CSV_PATH = Path("data/border_crossings/bts_border_crossings.csv")
DEFAULT_STATCAN_CSV_PATH = Path("data/border_crossings/statcan_frontier_counts.csv")

# Detroit metro centroid (~Wayne County center); res-7 cell = 872ab2c58ffffff.
_DETROIT_CENTROID_LATLNG: tuple[float, float] = (42.331, -83.046)


def default_tri_county_aggregate_hex() -> str:
    """H3 res-7 cell at the Detroit metro centroid (synthesis aggregate origin)."""
    import h3

    return str(h3.latlng_to_cell(*_DETROIT_CENTROID_LATLNG, 7))
```

Add the missing method (mirrors `_build_csr_matrix` reconstruction; import `LODESYearMatrix` + `NodeKind` lazily/TYPE_CHECKING as the module already does for `RuntimePersistence`):

```python
    def merge_into_year_matrix(
        self, matrix: LODESYearMatrix, year: int
    ) -> LODESYearMatrix:
        """Return a NEW matrix with the synthesized canada entry added (FR-035).

        Only the ``us_to_canada`` direction merges — OD-matrix origins are
        in-area hexes by schema, so the ``canada_to_us`` counterpart stays in
        ``immutable_reference_border_commute_synthesis`` for future
        household-reproduction specs. The annual entry is the MEAN of the
        weekly ``magnitude_workers`` values (LODES S000 semantics: standing
        worker count, not a flow sum — summing 52 weekly standing estimates
        would inflate the commuter population ~52x), rounded to the nearest
        integer to match the BIGINT ``s000_workers`` column.

        When ``is_enabled()`` is False or no rows synthesize, returns the
        input matrix unchanged.
        """
```

Implementation: `rows = [r for r in self.synthesize_year(year) if r.direction == "us_to_canada"]`; if empty → return `matrix`; `annual = round(sum(r.magnitude_workers for r in rows) / len(rows))`; if `annual <= 0` → return `matrix`; rebuild pair-counts from the existing matrix (`matrix.matrix.tocoo()` + `origin_hex_to_row`/`dest_node_id_by_col` inversion, exactly the `persist_to_postgres` iteration pattern at `lodes_commute_matrix.py:298-305`), add `(self.tri_county_aggregate_hex, "canada") += annual` with `boundary_dest_kind["canada"] = NodeKind.EXTERNAL`, and rebuild via the same sorted-pair-counts CSR assembly (`_build_csr_matrix` logic — either import-and-call a small extracted helper or replicate the ~25-line assembly; DRY-preferred: add `LODESCommuteMatrixLoader.build_matrix_from_pairs(...)` staticmethod delegating to `_build_csr_matrix`'s body and call it from both — but `_build_csr_matrix` is an instance method using no state, so the surgical option is `LODESCommuteMatrixLoader._build_csr_matrix` extracted to a module-level function `build_year_matrix(pair_counts, boundary_dest_kind, year)` in `lodes_commute_matrix.py`, kept re-exported; choose this, update `__all__`).

Also add the Postgres-side merge so `load_year_from_postgres` reads back a merged matrix (T042's literal contract: "then LODESCommuteMatrixLoader reads back the merged matrix"):

```python
    def persist_merged_lodes_rows(
        self,
        *,
        runtime: RuntimePersistence,
        session_id: UUID,
        years: tuple[int, ...],
    ) -> int:
        """Insert the annual canada aggregate into immutable_reference_lodes_od_matrix.

        One row per year: ``(session_id, year, tri_county_aggregate_hex,
        'canada', 'external', <annual mean weekly commuters>)``. Idempotent via
        the table's composite-PK ``ON CONFLICT DO NOTHING``. Returns rows
        attempted (0 when disabled).
        """
```

(SQL mirrors `LODESCommuteMatrixLoader.persist_to_postgres` at `lodes_commute_matrix.py:308-321`, same `runtime._pool.connection()` + `# noqa: SLF001` house pattern.) Update `__all__` (`border_commute_synthesis.py:366-369`) with the new names.

**Commit 2**: `feat(spec-063): T040-completion merge_into_year_matrix + Postgres canada-row merge on BorderCommuteSynthesisLoader`

### 2c. `initialize_session` wiring — `src/babylon/persistence/postgres_initialization.py`

Extend the signature (`:601-616`) with keyword-only optionals, matching the existing `lodes_*` style:

```python
    border_bts_csv_path: Path | None = None,
    border_statcan_csv_path: Path | None = None,
    # Test-support seams per quickstart §5 (FR-026 / SC-006):
    external_node_overrides: frozenset[str] | None = None,
    synthetic_lodes_canadian_rows: bool = False,
```

**(i) FR-026 early preflight (makes T033's SC-006 `< 5.0s` satisfiable — the existing guard at `:777-796` runs AFTER ~30s of reference hydration).** Insert right after `_preflight_hickel_intensive_coverage` (`:657`), before any Postgres write:

```python
    # Spec-063 FR-026 / SC-006 early preflight: when the caller both removes
    # canada from the external-node registry AND requests synthetic Canadian
    # LODES rows, fail before any hydration work (fail-fast < 5s budget).
    effective_international: tuple[str, ...] = (
        tuple(sorted(external_node_overrides))
        if external_node_overrides is not None
        else INTERNATIONAL_NODES
    )
    if synthetic_lodes_canadian_rows and "canada" not in effective_international:
        raise InitializationError(
            "Spec 063 FR-026 fail-fast: canada destination present in LODES "
            "matrix but canada not present in external_node registry. Add "
            "canada to the external-node set or disable the Canadian-row "
            "injection that produced these rows."
        )
```

Then at `:697-700` replace the hardcoded set with `report.external_node_ids = set(effective_international) | {DOMESTIC_REST_NODE}` and thread `node_ids=effective_international` into `_bootstrap_external_nodes` (add a `node_ids: tuple[str, ...] = INTERNATIONAL_NODES` keyword param there, replacing the loop constant at `:558`). This also revives the currently-**dead** data-driven guard at `:777` (`"canada" not in report.external_node_ids` was always False because `:697` hardcoded all 9 nodes).

**(ii) Synthetic canada row injection** (T032/T033 test seam) — inside the LODES block or standalone after it, when `synthetic_lodes_canadian_rows` is True: one INSERT into `immutable_reference_lodes_od_matrix` `(session_id, start_year, default_tri_county_aggregate_hex(), 'canada', 'external', 100)` with `ON CONFLICT DO NOTHING`, via `runtime._pool.connection()` (house pattern with `# noqa: SLF001`).

**(iii) The T042 synthesis block** — insert after `report.lodes_row_count = rows_persisted` (`:771`), BEFORE the FR-026 data-driven check (`:773`), and OUTSIDE the `lodes_root` gate (synthesis is independently meaningful; guard the lodes-merge half on the loader path):

```python
    # Spec 063 T042 — Option B border-commute synthesis (FR-031..FR-036).
    # Gated on GameDefines; FR-036 fail-fast (missing BTS CSV) propagates
    # from the loader constructor as FileNotFoundError naming the path.
    if defines.economy.enable_border_commute_synthesis:
        from babylon.economics.border_commute_synthesis import (
            DEFAULT_BTS_CSV_PATH,
            DEFAULT_STATCAN_CSV_PATH,
            DETROIT_PORT_CODES,
            BorderCommuteSynthesisLoader,
            default_tri_county_aggregate_hex,
        )

        synthesizer = BorderCommuteSynthesisLoader(
            bts_csv_path=border_bts_csv_path or DEFAULT_BTS_CSV_PATH,
            statcan_csv_path=border_statcan_csv_path or DEFAULT_STATCAN_CSV_PATH,
            border_commute_share=defines.economy.border_commute_share,
            detroit_port_codes=DETROIT_PORT_CODES,
            tri_county_aggregate_hex=default_tri_county_aggregate_hex(),
            enabled=True,
        )
        synthesis_years = tuple(start_year + offset for offset in range(scenario_length))
        report.border_synthesis_row_count = synthesizer.persist_to_postgres(
            runtime=runtime, session_id=session_id, years=synthesis_years
        )
        # Merge the annual canada aggregate into the OD-matrix table so
        # LODESCommuteMatrixLoader.load_year_from_postgres reads back the
        # merged matrix (T042).
        synthesizer.persist_merged_lodes_rows(
            runtime=runtime, session_id=session_id, years=synthesis_years
        )
```

Note the FR-026 data-driven guard at `:773-796` now runs after the merge and after synthetic injection, so canada rows + default registry (canada present) pass, and canada rows + overrides-without-canada raise — both branches now reachable.

**Commit 3** (with the T036/T033 integration tests below, same unit of work): `feat(spec-063): T042 wire BorderCommuteSynthesisLoader into initialize_session + FR-026 revival`

---

## 3. The 5 missing integration tests (ledger adjudication)

The tasks ledger names **six** absent integration-test files: T032 `test_detroit_windsor_routing.py`, T033 `test_canada_required_invariant.py`, T035 `test_paired_cross_border_emission.py`, T036 `test_synthesis_enabled_disabled.py` (all four falsely annotated `[X]` as "landed at unit level"), plus unchecked T051 `test_circulation_perf_budget.py` and T052 `test_atomicity_inheritance.py`. **The five for this branch = T032 + T033 + T035 + T036 + T052.** Defer T051: the remediation plan runs perf LAST (Phase 6.6 / spec-106 owns budgets), and T051 depends on 50-tick multi-stage timing that belongs with the national profiling work — annotate the ledger accordingly.

All five files: `pytestmark = [pytest.mark.cross_scale, pytest.mark.integration]`, `pytest.importorskip("psycopg")` / `("psycopg_pool")`, module-scoped `apply_062_migrations` + `runtime` fixtures copied from `tests/integration/test_five_flow_types.py:32-45`, `sqlite_path` skip-fixture from `test_two_phase_initialization.py:43-47`, `DETROIT_TRI_COUNTY = ["26163", "26125", "26099"]`. The quickstart's `runtime.fetch_boundary_register(...)` API **does not exist** — query `boundary_flow_register` with raw SQL via `runtime._pool.connection()` (pattern: `tests/integration/test_external_node_flows.py:80-152`). Note `tests/integration/` suites share the `babylon_test` DB — always filter by `session_id`.

### T036 — `tests/integration/test_synthesis_enabled_disabled.py` (SC-011/SC-012, session level)
- Fixture `synthetic_bts_csv(tmp_path)` reusing the 12-month × 2-port writer pattern (`test_border_commute_synthesis.py:25-40`; per DRY either import the helper by moving it to `tests/_helpers/` or accept the small duplication with a cross-reference comment — moving is preferred).
- Enabled defines via the frozen-model rebuild pattern (`test_two_phase_initialization.py:102-110`): `GameDefines.model_validate({**GameDefines().model_dump(), "economy": {**GameDefines().economy.model_dump(), "enable_border_commute_synthesis": True}})`.
- Test 1 (enabled): `initialize_session(..., defines=defines_on, start_year=2010, scenario_length_years=1, counties=DETROIT_TRI_COUNTY, border_bts_csv_path=synthetic_bts_csv)` → `report.border_synthesis_row_count == 52`; SQL `SELECT COUNT(*) FROM immutable_reference_border_commute_synthesis WHERE session_id=%s` == 52; `SELECT s000_workers FROM immutable_reference_lodes_od_matrix WHERE session_id=%s AND workplace_dest='canada'` returns exactly 1 row ≈ `round(10_000*0.5/(52/12))`; and read-back: `LODESCommuteMatrixLoader` is not constructible without lodes files — assert merged read-back at SQL level plus (when `data/lodes` present, else skip that sub-assert) `load_year_from_postgres(runtime, session_id, 2010).dest_to_col` contains `"canada"`.
- Test 2 (disabled default): `report.border_synthesis_row_count == 0`; zero synthesis-table rows; zero canada OD rows.
- Test 3 (FR-036): enabled defines + `border_bts_csv_path=tmp_path/"missing.csv"` → `pytest.raises(FileNotFoundError, match="BTS Border Crossing CSV required")`.

### T033 — `tests/integration/test_canada_required_invariant.py` (FR-026 + SC-006)
```python
start = time.perf_counter()
with pytest.raises(InitializationError, match=r"canada.*not present"):
    initialize_session(
        session_id=uuid4(), sqlite_path=sqlite_path, runtime=runtime,
        defines=GameDefines(), start_year=2010, scenario_length_years=1,
        counties=DETROIT_TRI_COUNTY,
        external_node_overrides=frozenset(["china", "eu"]),
        synthetic_lodes_canadian_rows=True,
    )
assert time.perf_counter() - start < 5.0  # SC-006
```
Second test: same call WITH canada in overrides (or defaults) + `synthetic_lodes_canadian_rows=True` completes and the synthetic canada row is present in `immutable_reference_lodes_od_matrix`. (Note: the exception class is `InitializationError` — quickstart's `SessionInitializationError` never existed.)

### T032 — `tests/integration/test_detroit_windsor_routing.py`
Honest scope (engine tick cannot exercise Vol2 — dormant, see §0): initialize a session with `synthetic_lodes_canadian_rows=True`; rebuild the matrix via `LODESCommuteMatrixLoader.load_year_from_postgres`?? — no loader construction without disk files, so instead build the `LODESYearMatrix` directly from the session's persisted OD rows (SQL SELECT → `pair_counts`/`boundary_dest_kind` → the newly-extracted `build_year_matrix(...)` from §2b), construct `Vol2CirculationStep(od_loader=<stub returning it>, classifier=CrossBorderCommuteClassifier(study_area_hexes=frozenset([aggregate_hex]), study_area_states=frozenset(["26"]), domestic_states=US_DOMESTIC_FIPS_STATES from tests.constants_063))`, `BabylonGraph()` with the aggregate hex node (`_node_type="hex", v=1000.0`), fresh `BoundaryFlowRegister`; `step(...)`; assert exactly one `COMMUTE_OUT` row with `dest_node_id == "canada"` in `register.query(flow_type=BoundaryEdgeKind.COMMUTE_OUT)`; then persist via `PerTickTransactionEnvelope(session_id=..., tick=1, boundary_register_rows=register.flush(), determinism_hash="0"*64)` + `runtime.persist_tick_atomic(envelope)` and assert the row is in Postgres (`SELECT ... FROM boundary_flow_register WHERE session_id=%s AND flow_type='commute_out' AND dest_node_id='canada'`). Unit-model: `tests/unit/engine/systems/test_vol2_classifier_routing.py`.

### T035 — `tests/integration/test_paired_cross_border_emission.py`
Same harness as T032, then:
- FR-030a sweep (quickstart §6 logic): every COMMUTE_OUT `(source,dest)` has a TRADE_EDGE keyed `(dest,source)` with `abs(diff) < 1e-9` — assert against the Postgres rows post-persist.
- FR-030b observational-only: `v_after_step = np.array([graph payload v for each hex node])` captured right after `step()`; `register.flush()`; recapture; `numpy.array_equal(...)` (trivially true today, pins the contract).
- FR-030c through the auditor + DB: `ConservationAuditor(epsilon=1e-9, rng_seed=42)`; `register_invariant("paired_cross_border_emission", paired_cross_border_emission_evaluator)`; happy path — `audit_end_of_tick(session_id=..., tick=1, hex_rows=[], context={"boundary_rows": rows})` → zero ALARM; broken path — drop one TRADE_EDGE from the row list, re-evaluate at tick=2 → exactly one ALARM; persist the alarm tick's audit rows via an envelope and assert `SELECT severity FROM conservation_audit_log WHERE session_id=%s AND invariant_name='paired_cross_border_emission' AND tick=2` → `'alarm'` with `scale='external:canada'` (proves scale-CHECK compatibility end-to-end).

### T052 — `tests/integration/test_atomicity_inheritance.py` (FR-022/FR-008a)
- Part 1 (spec-literal): classifier stub whose `classify` raises `RuntimeError` on its 2nd call; matrix with two external dests from one origin; `pytest.raises(RuntimeError)` around `step(...)`; assert `register.buffered_count() > 0` (partial buffer) but `SELECT COUNT(*) FROM boundary_flow_register WHERE session_id=%s AND tick=1` == 0 (nothing reached Postgres — the register is memory-only until envelope commit).
- Part 2 (transaction rollback proper): build an envelope whose `boundary_register_rows` are valid but whose `audit_log_rows` contains a row violating the scale CHECK (e.g. `scale="bogus_scale"` — bypass Pydantic by building a valid `ConservationAuditRow` then... Pydantic allows any ≤32 string, DB CHECK rejects it) → `pytest.raises(Exception)` on `persist_tick_atomic(envelope)`; assert zero `boundary_flow_register` rows for that (session, tick) — proves the shared-transaction rollback covers spec-063's rows (inserts ordered boundary-before-audit at `_spec_062.py:309-318`).
- Part 3: subsequent clean envelope for tick 2 commits fine (retry-after-failure).

**Commit 4**: `test(spec-063): T032/T035/T052 integration coverage — routing, paired emission via auditor, atomicity inheritance`

---

## 4. Ledger + docs updates (final commit)

In `specs/063-vol-ii-circulation/tasks.md`:
- `:128` **T042 `[ ]`→`[X]`** — append annotation: *(landed 2026-07-XX — initialize_session synthesis block + border_synthesis_row_count wired; merge via persist_merged_lodes_rows into immutable_reference_lodes_od_matrix; FR-036 propagates from loader ctor)*
- `:129` **T043 `[ ]`→`[X]`** — *(landed as function-style `paired_cross_border_emission_evaluator` in conservation_audit.py per module idiom; aggregates one ALARM row per external dest — per-pair rows impossible under the (session,tick,scale,invariant) PK; registered in runner.py session init)*
- `:131` **T045 `[ ]`→`[X]`** once the US3 commits exist.
- `:142` **T047 `[ ]`→`[X]`** with `[record-reconciliation]`: already implemented at `vol2_circulation.py:81` (`wall_time_ms` field) + `:153-155,286` (perf_counter) — code predates this branch.
- `:115,:116,:118,:119` (T032/T033/T035/T036, already `[X]`): update annotations to note the real integration files now exist (this branch) superseding the "landed at unit level" downgrade.
- `:146` T051: leave `[ ]`, append *(deferred to spec-106 national-perf per REMEDIATION_PLAN Phase 6.6 — perf budgets ratified there)*.
- `:147` **T052 `[ ]`→`[X]`**.

Also fix the stale FR-026 annotation reality: T033's note claims the invariant was "already wired" — record that the guard was dead (unreachable) until this branch's `external_node_overrides` revival, in the T033 annotation.

Update `ai/state.yaml` spec-063 entry (T048 remains open for full polish, but per CLAUDE.md "update ai after significant work" adjust the 063 task count 39/58 → 46/58 or as counted after flips).

**Commit 5**: `docs(spec-063): ledger truth flips T042/T043/T045/T047/T052 + T051 deferral [record-reconciliation]`

---

## 5. Verification commands (exact)

```bash
# Unit TDD loop (fast, no Postgres):
poetry run pytest tests/unit/persistence/test_paired_cross_border_emission.py -v
poetry run pytest tests/unit/economics/circulation/test_border_commute_synthesis.py -v
poetry run pytest tests/unit/persistence/test_conservation_auditor.py tests/unit/persistence/test_phi_week_conservation.py -v   # regression: 21-invariant pin + phi evaluator untouched
mise run test:q -- tests/unit/economics/circulation tests/unit/persistence tests/unit/engine/systems

# Integration (Postgres 5433; skips cleanly if down):
mise run db:up
BABYLON_TEST_PG_DSN="dbname=babylon_test host=localhost port=5433 user=test password=test" \
  poetry run pytest tests/integration/test_synthesis_enabled_disabled.py \
                    tests/integration/test_canada_required_invariant.py \
                    tests/integration/test_detroit_windsor_routing.py \
                    tests/integration/test_paired_cross_border_emission.py \
                    tests/integration/test_atomicity_inheritance.py -v
# Regression on touched persistence surfaces:
BABYLON_TEST_PG_DSN="..." poetry run pytest tests/integration/test_two_phase_initialization.py tests/integration/test_five_flow_types.py tests/integration/test_external_node_boundary.py -v

# Strict gates (repo standard):
poetry run mypy src/babylon/economics/border_commute_synthesis.py src/babylon/economics/lodes_commute_matrix.py src/babylon/persistence/conservation_audit.py src/babylon/persistence/postgres_initialization.py src/babylon/engine/headless_runner/runner.py --strict
poetry run ruff check src/babylon/economics/ src/babylon/persistence/ tests/ --fix && poetry run ruff format .
mise run check
```

Watch-outs: (a) NEVER touch `_DEFAULT_INVARIANTS` — `test_default_invariant_names_enumerate_21` pins it; (b) `pyproject.toml` has `strict_markers = true` — only registered markers (`unit`, `integration`, `cross_scale` all registered at `pyproject.toml:152-174`); (c) integration DB is shared — always scope SQL by `session_id`; (d) `EconomyDefines` is frozen — use the `model_validate({**model_dump()})` rebuild pattern for flag-on defines; (e) hex hydration is NOT needed by these tests (avoid `hex_hydration_counties` to keep init <30s); (f) start_year=2010 stays inside the Hickel 'Intensive' [1980,2017] preflight window (`postgres_initialization.py:253-291`) — do not use start_year ≥2018 in integration tests or `PhiAttributionUnavailableError` fires.
