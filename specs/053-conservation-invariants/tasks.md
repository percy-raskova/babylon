---
description: "Tasks for Property-Based Tests for Conservation Invariants"
---

# Tasks: Property-Based Tests for Conservation Invariants

**Input**: Design documents from `/specs/053-conservation-invariants/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: This feature *is* a test-engineering feature. Every task that produces test code IS the deliverable; there are no separate "implementation tasks" with their own test tasks. The `creates_value` markers on production code are non-test deliverables and are explicitly called out.

**Terminology**: This document uses "non-opt-out system" exclusively when referring to the marker mechanism (i.e., a class without `creates_value=True`). The spec's narrative term "non-creating system" is a synonym for the same concept. The two state containers are distinct: **engine systems** (implement `babylon.engine.systems.protocol.System`, mutate a `nx.DiGraph[str]`, only carry `wealth` attributes — not `c+v+s`) and **substrate computers** (live under `babylon.economics.substrate.*`, follow the protocols in `substrate/protocols.py`, operate on `HexGrid` where the explicit `c+v+s` fields live). The c+v+s conservation invariant therefore tests substrate computers directly; engine systems are tested via a weaker "no hex-state mutation" assertion at the full-pipeline level (since they should not touch hex c+v+s at all).

**Organization**: Tasks are grouped by user story to enable independent implementation and validation of each invariant.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- File paths are absolute under `/home/user/projects/game/babylon/`

## Path Conventions

- New tests: `tests/property/invariants/test_<name>.py`
- New strategies: `tests/property/strategies/<name>.py`
- Production marker only: `src/babylon/engine/systems/<system>.py` (one-line `creates_value: ClassVar[bool]` addition)
- Existing reused infra: `tests/property/conftest.py`, `tests/property/strategies/{primitives,worldstate}.py`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Configure the Hypothesis profiles and verify the property-test harness is intact before any invariant work begins.

- [ ] T001 Verify `tests/property/` exists and contains `conftest.py`, `strategies/`, `invariants/`, `systems/` subdirectories — abort and surface guidance if missing
- [ ] T002 [P] Configure Hypothesis profiles in `tests/property/conftest.py`: register `default` (max_examples=100 — satisfies SC-001 baseline, derandomize=True — satisfies FR-014, deadline=None) and `slow` (max_examples=500, derandomize=False, deadline=None); load `default` by default; load `slow` if `HYPOTHESIS_PROFILE=slow` env var is set (per research.md R7)
- [ ] T003 [P] Add `.hypothesis/` to `.gitignore` if not already present, and confirm `cache_dir` setting in `[tool.pytest.ini_options]` accommodates the example DB
- [ ] T004 [P] Verify `hypothesis` and `scipy` are importable in the project venv (`poetry run python -c "import hypothesis, scipy.sparse, h3"`)

**Checkpoint**: Hypothesis runs deterministically with the `default` profile; `tests/property/` infrastructure intact; example DB has a writable home.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Two foundational deliverables that MUST be complete before any invariant test can be written or parametrized.

**⚠️ CRITICAL**: No user story phase may begin until both T005-block and T006-block complete.

### T005-block — `creates_value` class marker on every engine system AND substrate computer

> **Note (resolves I1)**: Two distinct "Production" classes exist. `src/babylon/engine/systems/production.py:ProductionSystem` is the *engine-side* class that implements the `System` Protocol. `src/babylon/economics/substrate/production.py:DefaultHexProductionComputer` is the *substrate-side* computer that owns the c+v+s computation. Both must carry the marker; tasks below disambiguate explicitly.

- [ ] T005 [P] Add `creates_value: ClassVar[bool] = True` to `ImperialRentSystem` in `src/babylon/engine/systems/economic.py` (audited as wealth-mutating per research.md R1/R2)
- [ ] T006 [P] Add `creates_value: ClassVar[bool] = True` to `StruggleSystem` in `src/babylon/engine/systems/struggle.py` (uprising destruction)
- [ ] T007 [P] Add `creates_value: ClassVar[bool] = True` to `DispossessionEvents` in `src/babylon/engine/systems/dispossession_events.py` (default-deny while audit pending; flip to False when conservation proven)
- [ ] T008 [P] Add `creates_value: ClassVar[bool] = True` to `DecompositionSystem` in `src/babylon/engine/systems/decomposition.py` (default-deny while audit pending)
- [ ] T009 [P] For every remaining concrete `System` class in `src/babylon/engine/systems/*.py` not covered by T005–T008, add `creates_value: ClassVar[bool] = False`. Use `git grep -l "class.*System" src/babylon/engine/systems/` to enumerate at task-start time so newly-added systems are not missed. Reference list (verified 2026-05-05): `solidarity.SolidaritySystem`, `ideology.ConsciousnessSystem`, `survival.SurvivalSystem`, `contradiction.ContradictionSystem`, `territory.TerritorySystem`, `production.ProductionSystem` (engine-side), `lifecycle.LifecycleSystem`, `metabolism.MetabolismSystem`, `reserve_army.ReserveArmySystem`, `community.CommunitySystem`, `ooda.OODASystem`, `edge_transition.EdgeTransitionSystem`, `field_derivative.FieldDerivativeSystem`, `event_template.EventTemplateSystem`, `contradiction_field.ContradictionFieldSystem`, `control_ratio.ControlRatioSystem`, `vitality.VitalitySystem`.
- [ ] T009a [P] Add `creates_value: ClassVar[bool] = False` to substrate computer classes in `src/babylon/economics/substrate/`: `production.DefaultHexProductionComputer`, `circulation.DefaultHexCirculationComputer`, `aggregation.DefaultResolutionAggregator`, `equalization.DefaultHexEqualizationComputer`, `ground_rent.*` (use `git grep -l "class Default.*Computer\|class Default.*Aggregator" src/babylon/economics/substrate/` to enumerate). These are the classes that actually own c+v+s mutations; default `False` because they are designed to be conservation-preserving by construction. **Resolves C1**: substrate computers are now in scope for the per-system test (T017a).
- [ ] T010 Run `poetry run mypy src/babylon/engine/systems/ src/babylon/economics/substrate/` to confirm the markers type-check; fix any `ClassVar` import issues

### T006-block — Hypothesis strategies needed by US1–US5

- [ ] T011 [P] Create `tests/property/strategies/hex_grid.py` with `hex_grid_strategy(min_hexes=1, max_hexes=25_000, seed_cells=MICHIGAN_RES7_SEED_CELLS)` per data-model.md §3.1. Uses real `h3.cell_to_parent` to derive consistent res-6/res-5 parent maps. Populates `MICHIGAN_RES7_SEED_CELLS` at module-import time via `h3.polygon_to_cells(MICHIGAN_BOUNDARY, res=7)` (Michigan boundary from Natural Earth SQLite per spec 036). Falls back to `WAYNE_OAKLAND_MACOMB_SEED_CELLS` if Natural Earth is unavailable. Hypothesis size-biased shrinking will favor small grids by default; the upper bound matches the Article IV statewide scale (~50 k res-7 cells in Michigan).
- [ ] T012 [P] Create `tests/property/strategies/od_matrix.py` with `od_matrix_strategy(n, density, flavor)` per data-model.md §3.2; supports `flavor ∈ {"identity", "empty_rows", "dense", "random"}` and produces row-stochastic CSR matrices. At large `n` (e.g., toward the 25 000 upper bound matching `hex_grid_strategy`), default `density` to ≤0.01 to match empirical LODES sparsity and keep matrix construction tractable.
- [ ] T013 [P] Create `tests/property/strategies/dpd_state.py` with `dpd_state_grid_strategy(min_hexes=1, max_hexes=25_000)` per data-model.md §3.3; produces `Mapping[hex_id, DPDState]` with non-negative integer cohort counts. Uses the same `MICHIGAN_RES7_SEED_CELLS` pool from T011 for consistency across strategies.
- [ ] T014 [P] Create `tests/property/strategies/capital_stock.py` with `capital_stock_triple_strategy()` per data-model.md §3.4; produces `(K_t ∈ [0, 1e9], δ ∈ [0, 1], I_t ∈ [0, 1e9])` triples with finite, non-NaN floats
- [ ] T014a [P] **Resolves U1**: Add `worldstate_with_hexes_strategy(min_hexes=1, max_hexes=25_000)` to `tests/property/strategies/worldstate.py` (extending the existing spec-040 file). This composite strategy draws a `WorldState` via the existing `worldstate_strategy()` AND a `HexGrid` via `hex_grid_strategy()`, and returns a `tuple[WorldState, HexGrid]` so per-system tests can pass each container to whichever class consumes it (engine systems take the graph derived from `WorldState.to_graph()`; substrate computers take the `HexGrid` directly). Document in the strategy's docstring that the WorldState and HexGrid share no node IDs and are independent state containers.
- [ ] T014b [P] Add `tick_context_fixture()` and `service_container_fixture()` factories to `tests/property/conftest.py` for use by full-pipeline tests. The service container provides `defines`, `formulas`, `event_bus`, and `database` stubs sufficient for a single tick. The tick context is a minimal `TickContext(tick=0)` (or dict equivalent). **Resolves U2** for downstream tasks.
- [ ] T015 Run `poetry run pytest tests/property/strategies/ -v` to confirm new strategies are at least importable and round-trip a single example each

**Checkpoint**: All engine systems carry an explicit `creates_value` marker; all four new strategy modules exist and produce valid examples. Phase 3+ tests can now be parametrized over discovered systems and can compose generators.

---

## Phase 3: User Story 1 — c+v+s Value Conservation Across Systems (Priority: P1) 🎯 MVP

**Goal**: Detect any silent c+v+s drift in any non-opt-out engine system, both in isolation (per-system) and end-to-end (full pipeline).

**Independent Test**: `poetry run pytest tests/property/invariants/test_value_conservation.py` exercises every system with `creates_value=False` against ≥100 generated `WorldState` instances; any drift beyond `max(1e-10, 1e-11 * N)` produces a shrunk counterexample identifying the violating system.

### Implementation for User Story 1

- [ ] T016 [P] [US1] Create `tests/property/invariants/test_value_conservation.py` skeleton with module docstring referencing `contracts/value_conservation.md` (INV-001) and stating the scaled tolerance `max(1e-10, 1e-11 * N)` and its derivation from sparse-multiply error proportionality (per FR-012). Import `hex_grid_strategy`, `worldstate_with_hexes_strategy`, the system Protocol, and the substrate-computer protocols.
- [ ] T017 [US1] Implement engine-system discovery helper `_discover_non_opt_out_engine_systems()` in `tests/property/invariants/test_value_conservation.py`: imports each module under `babylon.engine.systems`, finds classes implementing `System`, filters by `getattr(cls, "creates_value", False) is False`, returns the list (used by `pytest.parametrize`).
- [ ] T017a [US1] **Resolves C1**: Implement substrate-computer discovery helper `_discover_non_opt_out_substrate_computers()` in the same file: walks `babylon.economics.substrate.{production,circulation,aggregation,equalization,ground_rent}`, finds concrete classes whose name matches `^Default.*Computer$` or `^Default.*Aggregator$`, filters by `getattr(cls, "creates_value", False) is False`, returns the list. These are the classes that own c+v+s mutations and must be tested per-class.
- [ ] T018 [US1] Implement `_sum_cvs(grid: HexGrid) -> float` and `_tol(n: int) -> float` helpers in the same file (`tol(n) = max(1e-10, 1e-11 * n)`). Each helper carries a docstring noting the FR-006/FR-004 source and the sparse-multiply derivation (per FR-012).
- [ ] T019 [US1] Implement per-substrate-computer test `test_per_computer_cvs_conservation` parametrized over `_discover_non_opt_out_substrate_computers()`: `@given(hex_grid_strategy())`, invokes the computer's primary method (e.g., `compute_production(grid)`, `aggregate(grid, target_resolution=…)`), asserts `|sum_cvs(post) - sum_cvs(pre)| < tol(N)`. Failure message format: `f"INV-001: substrate computer {Cls.__name__} mutated sum(c+v+s) by {drift} > tol={tol(N)}; pre={pre}, post={post}"` (resolves C2). Test docstring documents tolerance choice and derivation (FR-012). Implements User Story 1 acceptance scenarios 1, 3, 4 for the substrate side.
- [ ] T019a [US1] Implement per-engine-system test `test_per_engine_system_no_hex_mutation` parametrized over `_discover_non_opt_out_engine_systems()`: `@given(worldstate_with_hexes_strategy())`, builds the engine graph via `WorldState.to_graph()`, invokes `system.step(graph, services_fixture, tick_context_fixture)`, asserts that the HexGrid is unchanged (engine systems should not touch substrate state at all). Failure message: `f"INV-001: engine system {Cls.__name__} mutated hex c+v+s — engine systems must not touch substrate state"`. Test docstring documents the design rule per FR-012.
- [ ] T020 [US1] Implement full-pipeline test `test_full_pipeline_cvs_conservation`: `@given(worldstate_with_hexes_strategy())`, builds `(graph, services, context)` from the conftest fixtures (resolves U2), constructs a `SimulationEngine(systems=[...])` with the canonical pipeline, calls `engine.run_tick(graph, services, context)` (in-place mutation), then asserts `|sum_cvs(post_hex) - sum_cvs(pre_hex)| < tol(N)` net of recorded extractions from `creates_value=True` systems (read from `services.event_bus` history). Failure message format: `f"INV-001: full-pipeline drift {drift} > tol={tol(N)}; per-system pre/post: {breakdown}"` (resolves C2). Implements User Story 1 acceptance scenarios 2, 5.
- [ ] T021 [US1] Decorate the per-substrate-computer test (T019), the per-engine-system test (T019a), and the full-pipeline test (T020) with `@example` cases for the documented edge inputs: empty hexes (c=v=s=0), single-hex grid, concentration-on-one-hex (User Story 1 Edge Cases). One `@example(...)` decorator per case per test function.
- [ ] T022 [US1] Run `poetry run pytest tests/property/invariants/test_value_conservation.py -v` and confirm all generated examples pass on a clean `dev` checkout; commit example DB seed if any pre-existing regression surfaces (it shouldn't on dev)

**Checkpoint**: Per-system test parametrizes over the auto-discovered non-opt-out systems and asserts conservation on each. Full-pipeline test catches inter-system interaction bugs. The MVP for the broader feature is complete: c+v+s conservation is now under active falsification machinery.

---

## Phase 4: User Story 2 — H3 Hierarchical Sum Conservation (Priority: P1)

**Goal**: Detect any drift in the res-7 → res-6 → res-5 sheaf gluing condition for any generated grid, before AND after a tick.

**Independent Test**: `poetry run pytest tests/property/invariants/test_h3_hierarchical.py` runs ≥100 generated grids and asserts that for every res-6 and res-5 parent, the sum of children equals the parent aggregate within `1e-10`.

### Implementation for User Story 2

- [ ] T023 [P] [US2] Create `tests/property/invariants/test_h3_hierarchical.py` skeleton referencing `contracts/h3_hierarchical.md` (INV-002). Module docstring states the fixed `1e-10` tolerance and notes that this is exact-arithmetic aggregation (no sparse multiply, hence no N-scaling) per FR-012. Import `hex_grid_strategy`, `worldstate_with_hexes_strategy`, and `DefaultResolutionAggregator`.
- [ ] T024 [US2] Implement pre-step tests `test_sheaf_gluing_at_res6` and `test_sheaf_gluing_at_res5`: `@given(hex_grid_strategy())`, runs `DefaultResolutionAggregator.aggregate(grid, target_resolution=r)`, asserts for every parent that `|sum_children(c+v+s) - parent_aggregate| < 1e-10`. Failure message: `f"INV-002: sheaf gluing violated at res-{r}, parent={parent_id}, drift={drift}"`. Implements User Story 2 acceptance scenarios 1, 2, 4.
- [ ] T025 [US2] Implement cross-resolution global test `test_sheaf_global_consistency`: `@given(hex_grid_strategy())`, asserts `|sum(r6_totals) - sum(r5_totals)| < 1e-10` and both equal the per-hex sum within `1e-10`. Failure message includes `INV-002` prefix.
- [ ] T026 [US2] Implement post-step test `test_sheaf_gluing_post_tick`: `@given(worldstate_with_hexes_strategy())`, builds `(graph, services, context)` via the conftest fixtures (T014b), runs `engine.run_tick(graph, services, context)` (in-place), then asserts the gluing condition still holds on the (unchanged, by FR for engine systems) HexGrid at both res-6 and res-5. Failure message includes `INV-002` prefix. Implements User Story 2 acceptance scenario 3.
- [ ] T027 [US2] Decorate the four res tests (T024 ×2 + T025 + T026) with `@example` cases for empty grid and single-hex grid (User Story 2 edge cases).
- [ ] T028 [US2] Run `poetry run pytest tests/property/invariants/test_h3_hierarchical.py -v` and confirm pass

**Checkpoint**: Sheaf gluing is enforced on any generated grid at any tick boundary. Cross-resolution coherence is preserved.

---

## Phase 5: User Story 3 — Variable Capital Conservation Under LODES Circulation (Priority: P1)

**Goal**: Detect any drift in `sum(v)` under `circulate_wages` for any sparse OD matrix and any starting hex state, including edge cases (identity, empty rows).

**Independent Test**: `poetry run pytest tests/property/invariants/test_circulation_v.py` runs ≥100 (grid, OD) pairs and asserts `sum(v)` conservation within `tol(N)` and `sum(c)` / `sum(s)` exactness.

### Implementation for User Story 3

- [ ] T029 [P] [US3] Create `tests/property/invariants/test_circulation_v.py` skeleton referencing `contracts/circulation_v.md` (INV-003). Module docstring states tolerance `tol(N) = max(1e-10, 1e-11 * N)` with derivation: "sparse OD matrix multiply `od_matrix.T @ v_vec` accumulates floating-point error proportional to hex count" (per FR-012). Import `hex_grid_strategy`, `od_matrix_strategy`, and `DefaultHexCirculationComputer`.
- [ ] T030 [US3] Implement `_sum_v`, `_sum_c`, `_sum_s` helpers and `_tol(n)` in the same file. Helper docstrings cite the contract section and the test's tolerance derivation.
- [ ] T031 [US3] Implement random-OD test `test_circulation_v_conserved_random`: `@given(hex_grid_strategy(), od_matrix_strategy(flavor="random"))`, calls `circulate_wages`, asserts `|sum(v)_post - sum(v)_pre| < tol(N)` AND `sum(c)_post == sum(c)_pre` exactly AND `sum(s)_post == sum(s)_pre` exactly. Failure message: `f"INV-003: circulation drifted sum(v) by {drift} > tol={tol(N)}"` (or for c/s: `f"INV-003: circulation mutated sum({field}) by {drift} (must be exactly 0)"`). Implements User Story 3 acceptance scenarios 1, 4.
- [ ] T032 [US3] Implement identity-OD test `test_circulation_v_identity`: `@given(hex_grid_strategy())` with `flavor="identity"`, asserts per-hex `v` unchanged within `tol(N)` (no spurious redistribution). Failure message includes `INV-003` prefix. Implements User Story 3 acceptance scenario 2.
- [ ] T033 [US3] Implement empty-row OD test `test_circulation_v_empty_rows`: `@given(hex_grid_strategy(), od_matrix_strategy(flavor="empty_rows"))`, asserts `sum(v)` still conserved within `tol(N)`. Failure message includes `INV-003` prefix. Implements User Story 3 acceptance scenario 3.
- [ ] T034 [US3] Run `poetry run pytest tests/property/invariants/test_circulation_v.py -v` and confirm pass

**Checkpoint**: LODES circulation is now property-tested across the full sparse-OD input space. Existing example-based test in `tests/unit/economics/substrate/test_circulation.py` remains as named regression.

---

## Phase 6: User Story 4 — Population Conservation Modulo Births and Deaths (Priority: P2)

**Goal**: Detect any silent off-by-one in D-P-D′ cohort transitions; assert `pop_{t+1} == pop_t + births_t - deaths_t` exactly.

**Independent Test**: `poetry run pytest tests/property/invariants/test_population.py` runs ≥100 generated `DPDState` distributions and asserts integer-exact accounting equation per tick and across multi-tick sequences.

### Implementation for User Story 4

- [ ] T035 [P] [US4] Create `tests/property/invariants/test_population.py` skeleton referencing `contracts/population_lifecycle.md` (INV-004). Module docstring states tolerance `0` (integer-valued; exact equality required) per FR-012. Import `dpd_state_grid_strategy`, `WorldState`, `SimulationEngine`, the `EventType` enum (for BIRTH/DEATH filtering), and the conftest fixtures from T014b.
- [ ] T036 [US4] Implement `_sum_population(world_or_dpd_map) -> int`, `_count_births(events) -> int`, `_count_deaths(events) -> int` helpers. Note in docstrings that `events` is read from the per-tick `WorldState.events` list, never accumulated by the engine itself (per CLAUDE.md gotcha).
- [ ] T037 [US4] Implement single-tick test `test_population_accounting_single_tick`: `@given(dpd_state_grid_strategy())`, builds a `WorldState` with the generated DPD distribution, builds `(graph, services, context)` from the conftest fixtures (T014b), captures `pre_pop`, calls `engine.run_tick(graph, services, context)`, captures `post_pop`, reads `births` and `deaths` from `services.event_bus.history` (or equivalent per-tick event source), asserts `post_pop == pre_pop + births - deaths` exactly. Failure message: `f"INV-004: population accounting violated — pre={pre_pop}, post={post_pop}, births={births}, deaths={deaths}, expected={pre_pop + births - deaths}"`. Implements User Story 4 acceptance scenarios 1, 2, 3.
- [ ] T038 [US4] Implement multi-tick test `test_population_accounting_multi_tick`: `@given(dpd_state_grid_strategy(), integers(min_value=1, max_value=10))`. Loop N ticks: at the start of each iteration, capture `pop_t` from the current graph; call `engine.run_tick(graph, services, context_t)`; **read births/deaths from the current tick's events ONLY** (do not trust any accumulated field — per CLAUDE.md "WorldState.events is per-tick, NOT cumulative"); store the per-tick births/deaths in test-local lists; advance `context_t.tick += 1`. After the loop, assert `pop_T == pop_0 + sum(births_per_tick) - sum(deaths_per_tick)`. Failure message includes `INV-004` prefix and the failing tick index. Implements User Story 4 acceptance scenario 4.
- [ ] T039 [US4] Decorate the two tests (T037, T038) with `@example` cases for zero-population grid and single-hex single-cohort grid (User Story 4 edge cases).
- [ ] T040 [US4] Run `poetry run pytest tests/property/invariants/test_population.py -v` and confirm pass

**Checkpoint**: D-P-D′ cohort accounting equation is now an enforced invariant; silent off-by-ones in lifecycle transitions or vitality mortality will produce a counterexample.

---

## Phase 7: User Story 5 — Capital Stock Perpetual-Inventory Recurrence (Priority: P2)

**Goal**: Assert `K_{t+1} = (1-δ)K_t + I_t` holds for the `CapitalStockCalculator` over the full physical input space.

**Independent Test**: `poetry run pytest tests/property/invariants/test_capital_recurrence.py` runs ≥100 generated `(K, δ, I)` triples and asserts the recurrence within `1e-10`, plus three explicit boundary checks.

### Implementation for User Story 5

- [ ] T041 [P] [US5] **Resolves U3**: Create `tests/property/invariants/test_capital_recurrence.py` skeleton referencing `contracts/capital_recurrence.md` (INV-005). Module docstring states tolerance `1e-10` (closed-form arithmetic; no accumulating error) per FR-012, AND notes the verified API: `CapitalStockCalculator` does NOT expose a `step(K, δ, I)` method. The recurrence is implemented by `DepreciationConfig.next_K(K_prev: float, c: float) -> float` — see `src/babylon/economics/capital_stock.py:263` and `src/babylon/economics/depreciation.py`. The "investment" term `I_t` corresponds to the `c` argument (constant capital flow). Import `capital_stock_triple_strategy` and `DepreciationConfig`.
- [ ] T042 [US5] Implement general recurrence test `test_recurrence_general`: `@given(capital_stock_triple_strategy())` produces `(K_t, δ, I_t)`. For each example, construct `cfg = DepreciationConfig(rate=δ, ...)` (audit `DepreciationConfig.__init__` signature at task-start time and supply any other required fields with sensible defaults), call `K_t1 = cfg.next_K(K_t, I_t)`, compute `expected = (1 − δ) * K_t + I_t`, assert `|K_t1 − expected| < 1e-10`. Failure message: `f"INV-005: recurrence violated — K_t={K_t}, δ={δ}, I_t={I_t}, K_t1={K_t1}, expected={expected}, drift={K_t1 - expected}"`. Implements User Story 5 acceptance scenario 1.
- [ ] T043 [US5] Implement boundary tests `test_recurrence_no_depreciation` (δ=0 ⇒ `K_t1 == K_t + I_t`), `test_recurrence_full_depreciation` (δ=1 ⇒ `K_t1 == I_t`), `test_recurrence_no_investment` (I_t=0 ⇒ `K_t1 == (1-δ) * K_t`). Each uses `DepreciationConfig.next_K`. Failure messages include `INV-005` prefix and the boundary case name. Implements User Story 5 acceptance scenarios 2, 3, 4.
- [ ] T044 [US5] Implement monotonicity test `test_recurrence_monotone_in_delta`: `@given(K=floats(0, 1e9), δ_low=floats(0, 1), δ_high=floats(0, 1))` with `assume(δ_high > δ_low)` and `I_t = 0`, asserts `cfg(δ_high).next_K(K, 0) <= cfg(δ_low).next_K(K, 0)` (monotonically non-increasing in δ when I_t = 0). Failure message includes `INV-005` prefix. Implements User Story 5 acceptance scenario 4 monotonicity clause.
- [ ] T045 [US5] Run `poetry run pytest tests/property/invariants/test_capital_recurrence.py -v` and confirm pass

**Checkpoint**: All five conservation invariants now have property tests. The falsification harness is complete.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Validate the full suite end-to-end, integrate with the unit gate, and update documentation.

- [ ] T046 [P] Run `poetry run pytest tests/property/invariants/ -v` end-to-end; confirm total wall-clock under 60 s on the default Hypothesis profile (per SC-002). If the budget is exceeded because Hypothesis is drawing too many large grids, tune `hex_grid_strategy`'s default size bias (or add a `target=` to bias toward the small end) rather than reducing `max_hexes` from the 25 000 upper bound — the upper bound is the Article IV statewide-Michigan scale and SHOULD remain reachable on the slow profile.
- [ ] T046a [P] **Resolves G1**: Configure CI cache for the Hypothesis example database. Identify the active CI provider (Woodpecker per X.5; check `.woodpecker.yml`/`.woodpecker/` or `.github/workflows/`) and add a cache step that restores `.hypothesis/` before the test job and saves it after. Cache key SHOULD include the Python version and a hash of `pyproject.toml` so unrelated dependency bumps don't invalidate the example DB. If no CI is configured for this repo yet, add a placeholder `.hypothesis-cache.md` under `ai-docs/` documenting the requirement so it lands when CI is wired up. **Satisfies SC-004** (DB accumulates across runs).
- [ ] T047 [P] Run `mise run test:unit` and confirm the new tests are picked up (they should be, since they live under `tests/property/` which is part of the unit gate)
- [ ] T048 Run `poetry run mypy src/babylon/engine/systems/ tests/property/` and resolve any type errors introduced by the `creates_value` markers or the new strategies
- [ ] T049 Run `poetry run ruff check tests/property/invariants/ tests/property/strategies/ --fix` and `poetry run ruff format tests/property/invariants/ tests/property/strategies/`
- [ ] T050 [P] Run a deliberate-violation smoke test: temporarily mutate `ImperialRentSystem.step()` to add `+1` to a wealth field (do NOT commit), run `pytest tests/property/invariants/test_value_conservation.py`, confirm a counterexample is produced within one invocation, then revert. (Validates SC-003.)
- [ ] T051 [P] Run with `HYPOTHESIS_PROFILE=slow poetry run pytest tests/property/invariants/` and confirm 500 examples per test pass with `derandomize=False`
- [ ] T052 Update `ai-docs/state.yaml` to record completion of feature 053: increment property-test count, add `053_conservation_invariants` to completed sprints
- [ ] T053 Add an ADR entry to `ai-docs/decisions.yaml`: `ADR_053_conservation_invariants` documenting the default-deny `creates_value` marker policy, the scaled-tolerance `max(1e-10, 1e-11 * N)` rationale, and the spec-040 strategy reuse
- [ ] T054 Run `poetry run pytest tests/unit/economics/substrate/test_{conservation,aggregation,circulation}.py -v` to confirm the existing example-based tests still pass (FR-009)
- [ ] T055 Walk through `quickstart.md` end-to-end on a clean checkout: run each commanded `pytest` invocation and confirm the documented behaviour matches reality
- [ ] T056 Commit per the conventional-commit format in CLAUDE.md, one commit per checkpoint reached (Phase 1, Phase 2 markers, Phase 2 strategies, each US, polish)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** — no dependencies; can start immediately
- **Foundational (Phase 2)** — depends on Setup completion; BLOCKS all user stories
  - T005-block (`creates_value` markers) and T006-block (strategies) can run in parallel within Phase 2
- **User Stories (Phase 3+)** — all depend on Foundational
  - US1, US2, US3 (P1) can run in parallel
  - US4, US5 (P2) can run in parallel after Foundational
- **Polish (Phase 8)** — depends on all user stories complete

### User Story Dependencies

| Story | Depends on | Why |
|-------|-----------|-----|
| US1 | T005–T009a (markers, both engine + substrate), T011 (hex_grid), T014a (worldstate_with_hexes), T014b (services + context fixtures) | Needs `creates_value` markers on engine systems AND substrate computers; needs both state-container generators; needs run_tick fixtures |
| US2 | T011 (hex_grid), T014a + T014b (for post-step test only) | Pre-step tests need `hex_grid_strategy`; post-step test additionally needs the WorldState strategy and run_tick fixtures |
| US3 | T011 (hex_grid), T012 (od_matrix) | Needs `hex_grid_strategy` + `od_matrix_strategy` |
| US4 | T013 (dpd_state), T014b (services + context fixtures) | Needs `dpd_state_grid_strategy` and run_tick fixtures |
| US5 | T014 (capital_stock) | Needs `capital_stock_triple_strategy` only |

**No cross-story dependencies among US1–US5.** Each invariant is an independent test file; they only share the strategy infrastructure built in Phase 2.

### Within Each User Story

- Strategy module must exist (Phase 2) before test file is written
- Test skeleton (helpers + imports) before parametrized tests
- Pre-step tests before post-step tests (post-step depends on the engine running cleanly)

### Parallel Opportunities

- All Phase 1 setup tasks marked [P] (T002, T003, T004) can run in parallel
- All Phase 2 marker tasks (T005–T009 + T009a) can run in parallel — different files
- All Phase 2 strategy tasks (T011–T014 + T014a + T014b) can run in parallel — different files (T014a edits the existing `worldstate.py` so it serializes against any other edit to that file; T014b edits `conftest.py` similarly)
- All five user-story phases can run in parallel once Phase 2 completes (one developer per invariant)
- Within a user story, the skeleton task (T016, T023, T029, T035, T041) is the only serial-blocking task; the test-implementation tasks within a phase mostly add `@given`-decorated functions to that one file, so they are serial

---

## Parallel Example: Phase 2 Strategies

```bash
# Launch all four new strategy modules in parallel:
Task: "Create tests/property/strategies/hex_grid.py with hex_grid_strategy(...)"
Task: "Create tests/property/strategies/od_matrix.py with od_matrix_strategy(...)"
Task: "Create tests/property/strategies/dpd_state.py with dpd_state_grid_strategy(...)"
Task: "Create tests/property/strategies/capital_stock.py with capital_stock_triple_strategy(...)"
```

## Parallel Example: User Stories (after Foundational)

```bash
# With three developers, each takes a P1 story:
Developer A: Phase 3 — User Story 1 (test_value_conservation.py)
Developer B: Phase 4 — User Story 2 (test_h3_hierarchical.py)
Developer C: Phase 5 — User Story 3 (test_circulation_v.py)
# Then sequentially or in parallel for P2:
Developer A: Phase 6 — User Story 4 (test_population.py)
Developer B: Phase 7 — User Story 5 (test_capital_recurrence.py)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 2: Foundational (T005–T015) — this is the largest single chunk; gates everything
3. Complete Phase 3: User Story 1 (T016–T022) — the c+v+s invariant is the most load-bearing one; once it lands, the broader feature has demonstrated value
4. **STOP and VALIDATE**: Run the deliberate-violation smoke test from T050; confirm a counterexample is produced
5. The MVP is now usable: a maintainer changing any system gets immediate feedback on c+v+s drift

### Incremental Delivery

1. Setup + Foundational → harness ready
2. Add US1 (c+v+s) → test independently → MVP shipped
3. Add US2 (sheaf gluing) → test independently → spatial-substrate guard online
4. Add US3 (circulation v) → test independently → LODES guard online
5. Add US4 (population) → test independently → cohort accounting guard online
6. Add US5 (capital recurrence) → test independently → perpetual-inventory guard online
7. Polish: SC-002 wall-clock check, slow profile validation, docs sync

### Parallel Team Strategy

With 3+ developers:

1. Pair on Setup + Foundational (one developer on markers, one on strategies, one on conftest profiles)
2. Once T015 checkpoint reached:
   - Developer A: US1 (highest impact, most parametrize complexity)
   - Developer B: US2 (sheaf gluing, h3-library reasoning)
   - Developer C: US3 (sparse-matrix generators, edge-case discipline)
3. Then any developer:
   - US4 (event accumulation across ticks — touches WorldState gotchas)
   - US5 (recurrence — smallest test, can be done quickly)
4. Pair on Phase 8 polish

---

## Notes

- **Tests ARE the deliverable** — there is no separate "test the tests" phase; the property tests' pass/fail on the dev branch is the validation
- **`creates_value` markers are the only production-code change** — and they are additive class-level constants with `ClassVar[bool]`, no semantic effect
- **No new domain entities, no new persistence** — purely test-side infrastructure
- **Commit after each phase checkpoint** per CLAUDE.md "commit early, commit often"
- **Verify the existing example-based tests still pass** at T054 — FR-009 requires preservation, not replacement
- **Smoke-test deliberate violation** at T050 — this is the SC-003 acceptance criterion, validating that the harness actually catches regressions
