# Implementation Brief — Phase 5.2 `feat/vol2-vol3-service-wiring`

Wire the dormant Capital Vol I/II/III TickDynamics service stack into the canonical headless runner, defines-gated, with a proof window per activation batch. All anchors verified against dev HEAD `3293833d` (2026-07-08).

---

## 0. STOP-SHIP DISCOVERY (read first — affects Phase 2.R too)

**At dev HEAD, the canonical bridged 520-tick run crashes at tick 52.** Empirically reproduced in-process:

```
TickDynamicsSystem.step(graph, services, {"tick": 52}) on a bridged-shape graph
→ ValidationError: ClassDistribution.fips 'T001' string_too_short (min_length=5)
```

Causal chain (every link verified):
1. Spec-E101 wired `melt_calculator` into the runner (`runner.py:903-915`), so TickDynamicsSystem passes its `services.melt_calculator is None` early-return gate (`src/babylon/economics/tick/system/__init__.py:136`). Real `get_melt(2011)` returns `57.478…` (verified against the reference DB), so Step 2 succeeds.
2. The bridge builds territories with IDs `T001…T083`, NOT FIPS (`src/babylon/engine/headless_runner/bridge.py:788-795`; `Territory.id` is model-constrained to `^T[0-9]{3}$`, `models/entities/territory.py:57`). The county FIPS only appears in `Territory.name` ("County 26163") and on SocialClass nodes (`county_fips` field, `bridge.py:758-767`).
3. At the first year boundary (tick 52), `_bootstrap_county_states` finds no `tick_capital_stock` attrs → `{}` (`tick/system/__init__.py:303-352`), so `_get_territory_fips` returns the raw territory node IDs `["T001",…]` (`:288-301`).
4. `_compute_county_states` builds `ClassDistribution(fips="T001", …)` (`:486-494`) → `fips: str = Field(..., min_length=5, max_length=5)` (`economics/tick/types.py:259`, `economics/dynamics/types.py` ClassDistribution) → raises. `SimulationEngine.run_tick` does NOT isolate system exceptions (`engine/simulation_engine.py:213-219` is try/**finally** for timing only) → run dies.

No post-E101 520-tick canonical has been run (the plan itself defers the cc4a5303 R-PROOF regen to 2.R), which is why this has never fired. The last completed bundles (`reports/sim-runs/2026-07-02T*`) predate the melt wiring. **Phase 2.R's regen run will hit this crash.** Coordinate: land Step 1 below (the FIPS identity fix) before or with 2.R.

---

## 1. Inventory (verified)

### (a) TickDynamicsSystem service slots — `src/babylon/economics/tick/system/__init__.py` (1,680 LOC, system #4 in `_DEFAULT_SYSTEMS`; runs only on `tick % 52 == 0`, `:132`)

| # | Slot | Read at | Gate/fallback when `None` |
|---|------|---------|---------------------------|
| 1 | `melt_calculator` | `:136` (required gate), `:371` | whole system no-ops — **WIRED (E101)** |
| 2 | `gamma_calculator` | `:387-390` | gamma_III = 0.33 (`:386`) — **WIRED but data-inert (Phase 5.1's problem)** |
| 3 | `basket_calculator` | `:380-383` | gamma_basket = 0.68, `estimated=True` (`:378-379`) |
| 4 | `capital_calculator` | `:446-449` | K = prev or **0.0** (`:445`) |
| 5 | `throughput_calculator` | `:454-458` | pi=1.0, depth=2.0 (`:452-453`) |
| 6 | `tensor_registry` | getattr `:166,:699,:1303,:1328,:1355` | crisis profit_rate=None → detector no-op (`crisis_detector.py:124-125`); financial surplus=None |
| 7 | `reserve_army_data_source` | `:854` (gates Vol I layer), `:893` | whole Vol-I wage-pressure layer skipped |
| 8 | `dispossession_data_source` | `:1511-1521` | `DEFAULT_FORECLOSURE/BANKRUPTCY/EVICTION` = 0.006/0.006/0.063 (`:83-85`) |
| 9 | `turnover_profile_source` | `:921` (gates Vol II layer), `:1019-1022` | whole circulation layer skipped |
| 10 | `inventory_data_source` | `:965,:974-977` | days_inventory 30.0 (`:1048-1049`), inventory 0.0 |
| 11 | `depreciation_data_source` | `:966,:979-981` | depr `max(…,1.0)` (`:1056`) |
| 12 | `interest_calculator` | `:1119` (gates Vol III layer), `:1157-1160` | whole financial layer skipped; national rate would be 0.0 |
| 13 | `fictitious_capital_calculator` | `:1163-1166` | fictitious=None |
| 14 | `distribution_calculator` | `:1199-1220` | no surplus_distribution/debt |
| 15 | `rent_calculator` | `:1223-1226` | no rent_extraction |
| 16 | `housing_calculator` | `:1229-1232` | no housing_decomposition |
| 17 | `financial_crisis_assessor` | `:1235-1246,:1271` | no crisis assessment (also requires #14's output) |
| 18 | `transition_engine` | `:1491` (gates Step 6), `:1549` | class distributions frozen forever |

Non-calculator reads: `defines`, `event_bus`, `hex_grid` (`:255`, out of scope). **Spec-057 Leontief slots** (`periphery_labor_source`, `final_demand_source`, `industry_county_allocator`, `production_chain_calculator`, `bea_industries` — read in `tick/system/imperial_rent.py:90-138`) are **Phase 5.3's branch, NOT this one**.

**Passenger slots** (exist on ServiceContainer + returned by factories, but have ZERO readers anywhere in src/: verified by rg): `productivity_data_source`, `credit_cycle_detector`, `counter_tendency_calculator`, `value_basis_converter`, `z1_source`, `housing_data_source`. Wire them anyway (they arrive free inside the factory dicts) so the C.8 audit table shows them, and document their zero-reader status in proof.md. So the plan's "~13" is really **16 dormant read-slots + 6 passengers**.

### (b) Runner ServiceContainer construction — `src/babylon/engine/headless_runner/runner.py`

- `_build_economics_overrides(session_factory)` `:869-917` — builds ONLY `gamma_calculator` (MVPUnpaidCareHoursSource + QCEWCareAdapter) and `melt_calculator` (SQLiteBEANationalGDPSource + SQLiteQCEWNationalEmploymentSource).
- Call site `:1031-1043`: `calc_session_factory = get_normalized_session_factory()` → `services = ServiceContainer.create(defines=defines, **economics_overrides)` → post-create attribute assignment of `event_bus`/`boundary_register`/`auditor` (`:1041-1043`, ServiceContainer is a mutable dataclass, `engine/services.py:27`).
- `defines = GameDefines.load_default()` at `:956`. Graph built once at `:1050` (`world.to_graph()`), persistent across ticks; ticks run `range(1, config.ticks)` (`:1298`) → year boundaries at 52,104,…,468 → **9 TickDynamics activations in a 520-tick run, years 2011–2019** (`_determine_year` = 2010 + tick//52, `:283-286`; `base_year` graph attr is never set by the bridged runner — 2010 default only coincidentally matches canonical `start_year`).
- `ServiceContainer.create()` (`engine/services.py:142-268`) already accepts **every** key the factories emit; all fields are `Any = field(default=None)` (`:82-129`). Zero container changes needed.

### (c) Dormant service constructors — `src/babylon/economics/factory.py` (690 LOC)

| Factory | Lines | Returns (keys) | Data needs (verified in reference DB, read-only) |
|---|---|---|---|
| `create_economics_services(session_factory, tensor_registry)` | `:93-149` | 7: melt, basket, gamma, capital, throughput, transition_engine, tensor_registry | basket: `fact_bilateral_trade_annual` (2010-2024 ✓), `fact_bea_final_demand_annual` (1997-2024 ✓), `fact_hickel_erdi_annual` (**ends 2017** — gamma_import degrades to MVP after); capital: hydrated TensorRegistry; throughput: `FactBEACountyGDP` (1.99M rows ✓) + `fact_qcew_annual` (14.67M rows, 2010-2024 ✓, spec-086 complete) |
| `load_fred_series_from_db` | `:152-231` | Vol-III FRED cache (10 series) | ALL present: FEDFUNDS/DGS10/BAA10Y/TCMDO/NCBEILQ027S/B230RC0Q173SBEA/A054RC1Q027SBEA 1990-2024; CPIAUCSL/GDPDEF/GFDEBTN 2010-2024 ✓ |
| `create_financial_services(fred_series_cache)` | `:234-376` | 11: distribution, interest, credit_cycle, fictitious, rent, housing, counter_tendency, value_basis, crisis_assessor, z1, housing_data | FRED cache above; Z1Loader/CensusHousingLoader use hardcoded defaults; `DefaultRentCalculator` gets a stub all-None adapter (`:346-358`) → rent_extraction will be sentinel-skipped — document, don't "fix" |
| `load_circulation_series_from_db` | `:379-440` | ISRATIO (1992-2024 ✓, months→days ×30.4), GPDI (1990-2024 ✓) | — |
| `create_circulation_services(circ_cache, fred_cache)` | `:443-507` | 3: turnover_profile_source, inventory_data_source, depreciation_data_source | — |
| `load_vol1_series_from_db` | `:510-555` | OPHNFB/HOANBS (1990-2024 ✓), NROU (1990-2024 ✓), UNRATE (2010-2024 ✓) | — |
| `create_vol1_services(vol1_cache, fred_cache)` | `:558-679` | 3: reserve_army, productivity, dispossession (hardcoded ≤2020 + UNRATE proxy 2021+) | — |

**Legacy wiring precedent** (the exact order to reuse): `src/babylon/engine/simulation/_legacy.py:269-309` — economics → financial → circulation → vol1, each `overrides.update(...)`. TensorRegistry hydration precedent at `:216-236`: `MarxianHydrator(SQLiteQCEWSource(session), StubBEASource(), DepartmentMapper.from_yaml(economics_path))` under `get_reference_session()`, then `tensor_registry.hydrate_counties(hydrator, fips_codes, years)` (`economics/tensor_registry.py:555`; per-county-year failures become NoDataSentinel entries, non-fatal). YAML path: `src/babylon/economics/data/naics_to_dept.yaml` (`_legacy.py:223-225`). Year set: reuse `derive_year_set(start_year, total_ticks)` from `engine/headless_runner/reference_data_cache.py` (michigan = 83 counties × 11 years = 913 hydrations, startup-only).

### (d) Defines-gating pattern

Sole precedent: `enable_border_commute_synthesis: bool = Field(default=False, description="Spec 063, FR-031 — opt-in flag …")` at `src/babylon/config/defines/economy_basic.py:458` (consumed in `economics/border_commute_synthesis.py`). GameDefines is frozen (`_assembler.py:124`); submodels registered as `Field(default_factory=…)` (`:125-170`) AND must be added to `_from_yaml_dict` (`:264-303`) or YAML loading silently drops the section.

**Overlay mechanism is DEAD at HEAD**: `--defines` (argparse_cli.py:93-98, help says "TOML overlay") → `SimulationRunConfig.defines_overlay_path` (models.py:117, set at runner.py:225) → **never read again**; `run()` unconditionally calls `GameDefines.load_default()` (runner.py:956). This branch must implement overlay application — it IS the per-batch proof-window mechanism.

### (e) What each activation changes in tick outputs

**Coupling facts (all verified):** no engine system, no persistence path, and no web code reads any `tick_*` territory attribute (rg sweep — only `graph_metadata` schema mentions `tick_dynamics`, and `persist_graph_metadata` has no bridged-runner caller). Outputs live in (i) the `tick_dynamics` graph attr (`tick/graph_bridge.py:58-68` — holds live Pydantic objects; round-trips fine because the bridged graph is persistent and never re-serialized), (ii) territory node `tick_*` attrs (`:80-183` — **silently skipped in the bridged runner** because `graph.get_node(real_fips)` misses T-nodes), and (iii) **events**: `CRISIS_PHASE_TRANSITION`, `ECONOMIC_CRISIS` (`:748-774`), `DISPOSSESSION_CASCADE` (`:818-831`), `BIFURCATION_THRESHOLD` (`:1455-1469`) — captured by EventCapture (subscribed to all EventTypes) → `summary.json["events"]`.

Therefore: **trace.csv is byte-identical under every batch** (its 24 columns come from social-class/hex state, `manifest.py:38-215`); `summary.json` changes only via `events` and `performance`; the 5-tick `qa:e2e-regression` / `qa:storage-budget` baselines never reach tick 52 and are immune. Per-batch effect:

- **Batch A (economics core):** real per-county K (perpetual inventory, `capital_stock.py:137`), pi/supply-chain depth, data-driven gamma_basket (smoothed, `:392-405`), annual class transitions (Step 6 live), live crisis detection (tensor profit_rate feeds `MultiPeriodCrisisDetector`; DEEP quarters compress `median_wage`, `:643-658`) → first possible crisis/bifurcation/cascade events.
- **Batch B (Vol I):** `median_wage *= (1 - wage_pressure(reserve_ratio))` per boundary (`:893-899`, UNRATE−NROU decomposition); real dispossession rates flow into `EconomicConditions` (`:1508-1532`, only matters with A's transition_engine).
- **Batch C (Vol II):** `circulation_state` populated per county (circuit/inventory/depreciation + crisis assessment `:1029-1094`); **requires A** — early-returns per county while `capital_stock <= 0` (`:1013-1015`).
- **Batch D (Vol III):** real national interest rate (FEDFUNDS, decimal, replaces 0.0 at `:1160`), fictitious capital stock, surplus distribution s=p+i+r+t + debt accumulation (needs A's tensor `total_s`, `:1199-1220`), housing decomposition (hardcoded Census defaults), financial crisis signals. rent_extraction stays sentinel-skipped (stub adapter).

---

## 2. Implementation steps (dependency-safe order; commit after each; `mise run commit`)

### Step 1 — County identity fix (the tick-52 crash) — LAND FIRST, coordinate with 2.R

1. Add optional field to Territory (`src/babylon/models/entities/territory.py`, after `name` `:67`), matching surrounding style:

```python
    county_fips: str | None = Field(
        default=None,
        min_length=5,
        max_length=5,
        description=(
            "5-digit county FIPS this territory represents, when hydrated "
            "per-county by the bridged runner (ADR044). None for abstract "
            "MVP territories. Territory.id stays ^T[0-9]{3}$ — this field "
            "is the economic-pipeline join key (TickDynamicsSystem)."
        ),
    )
```
Model field ⇒ automatically survives `to_graph`/`from_graph` (graph-write contract satisfied; no exclusion-set change).

2. Set it in the bridge (`engine/headless_runner/bridge.py:791-795`):

```python
            territories[territory_id] = Territory(
                id=territory_id,
                name=f"County {county_fips}",
                sector_type=SectorType.INDUSTRIAL,
                county_fips=county_fips,
            )
```

3. Make `_get_territory_fips` prefer it and **fail loud, not crash** (`tick/system/__init__.py:288-301`):

```python
    def _get_territory_fips(self, graph: GraphProtocol) -> list[str]:
        fips_list: list[str] = []
        for node in graph.query_nodes():
            if node.node_type != "territory":
                continue
            fips = str(node.attributes.get("county_fips") or node.id)
            if len(fips) == 5:
                fips_list.append(fips)
            else:
                logger.warning(
                    "TickDynamics: territory %s has no 5-digit county_fips "
                    "(got %r) — excluded from county pipeline",
                    node.id,
                    fips,
                )
        return fips_list
```
Fallback to `node.id` preserves every existing unit fixture (they key territory nodes by bare FIPS strings). Territory node `tick_*` projection stays skipped (`graph_bridge.py:82-84` `get_node(fips)` → None) — deliberately: projecting onto T-nodes would trip `Territory extra="forbid"` in the per-tick `from_graph` (`world_state.py:153-162`, `models/entities/territory.py:50-51`). Defer projection until a consumer exists (would need a `tick_` prefix exclusion in `_reconstruct_territory` + C.1 roundtrip coverage).

### Step 2 — `ServiceWiringDefines` + overlay application (the gates)

New `src/babylon/config/defines/service_wiring.py` (mirror `economy_basic.py` style):

```python
class ServiceWiringDefines(BaseModel):
    """Activation gates for the TickDynamics Vol I/II/III service stack.

    Phase 5.2 (remediation plan): each flag wires one factory batch into the
    headless runner's ServiceContainer. Defaults flip to True only after the
    batch's R-PROOF window (proof.md + regenerated baselines).
    """

    model_config = ConfigDict(frozen=True)

    wire_economics_core: bool = Field(
        default=False,
        description=(
            "Batch A — basket/capital/throughput/transition_engine + hydrated "
            "TensorRegistry (specs 011-017 via create_economics_services)."
        ),
    )
    wire_vol1_production: bool = Field(default=False, description="Batch B — reserve-army wage pressure, productivity, dispossession sources (spec 021).")
    wire_vol2_circulation: bool = Field(default=False, description="Batch C — turnover/inventory/depreciation circulation layer (spec 023). Requires Batch A for county capital_stock > 0.")
    wire_vol3_financial: bool = Field(default=False, description="Batch D — interest/fictitious/distribution/rent/housing/crisis-assessor stack (spec 024). Distribution/crisis need Batch A's TensorRegistry.")
```

Register in `_assembler.py`: import; field `service_wiring: ServiceWiringDefines = Field(default_factory=ServiceWiringDefines)` (after `class_system`, `:170` region); add `service_wiring=ServiceWiringDefines(**data.get("service_wiring", {}))` to `_from_yaml_dict` (`:264-303`). **Both places or YAML runs silently lose the section.**

Overlay application in `run()` (runner.py:956):

```python
        defines = GameDefines.load_default()
        if config.defines_overlay_path is not None:
            defines = _apply_defines_overlay(defines, config.defines_overlay_path)
```

```python
def _apply_defines_overlay(defines: GameDefines, overlay_path: Path) -> GameDefines:
    """Deep-merge a partial YAML overlay onto ``defines`` and re-validate.

    Loud by design: missing file raises FileNotFoundError; unknown keys
    raise pydantic.ValidationError (extra='forbid' on every submodel).
    """
    with overlay_path.open("r", encoding="utf-8") as fh:
        overlay = yaml.safe_load(fh) or {}
    merged = _deep_merge(defines.model_dump(mode="python"), overlay)
    return GameDefines._from_yaml_dict(merged)
```
(`_deep_merge`: ~8-line dict-recursive helper; fixed recursion depth = defines nesting depth, satisfies the bounded-loop rule.) Fix the `--defines` help text (argparse_cli.py:97) TOML→YAML in the same commit. Note: `_defines_hash(defines)` at runner.py:1491 already hashes the post-overlay instance once this lands, so manifests distinguish proof-window runs for free.

### Step 3 — Extend `_build_economics_overrides` (runner.py:869-917)

Keep the existing gamma+melt body; append flag-gated batches following the `_legacy.py:269-309` order. Keep each function under 100 lines — factor the tensor hydration into its own helper:

```python
def _hydrate_tensor_registry(
    scope_fips: frozenset[str],
    years: Sequence[int],
) -> Any:
    """Hydrate a TensorRegistry for the run scope (Batch A prerequisite).

    Mirrors Simulation.from_sqlite (engine/simulation/_legacy.py:216-236).
    Per-county-year failures degrade to NoDataSentinel entries (logged by
    TensorRegistry.hydrate_counties) — hydration never raises on data gaps.
    """
    from babylon.economics.adapters import SQLiteQCEWSource
    from babylon.economics.department_mapper import DepartmentMapper
    from babylon.economics.hydrator import MarxianHydrator
    from babylon.economics.tensor_registry import TensorRegistry
    from babylon.engine.hydration.reference import StubBEASource
    from babylon.reference.database import get_reference_session

    registry = TensorRegistry()
    dept_yaml = Path(babylon.economics.__file__).parent / "data" / "naics_to_dept.yaml"
    with get_reference_session() as session:
        hydrator = MarxianHydrator(
            SQLiteQCEWSource(session), StubBEASource(), DepartmentMapper.from_yaml(dept_yaml)
        )
        registry.hydrate_counties(hydrator, sorted(scope_fips), list(years))
    return registry
```

```python
def _build_wired_service_batches(
    session_factory: Any,
    wiring: ServiceWiringDefines,
    scope_fips: frozenset[str],
    years: Sequence[int],
) -> dict[str, Any]:
    """Flag-gated Vol I/II/III factory batches (Phase 5.2).

    Order mirrors engine/simulation/_legacy.py:269-309. The FRED cache is
    loaded at most once and shared across batches.
    """
    from babylon.economics import factory as econ_factory

    overrides: dict[str, Any] = {}
    fred_cache: dict[str, dict[int, float]] | None = None
    if wiring.wire_economics_core:
        registry = _hydrate_tensor_registry(scope_fips, years)
        overrides.update(econ_factory.create_economics_services(session_factory, registry))
    if wiring.wire_vol1_production:
        fred_cache = fred_cache or econ_factory.load_fred_series_from_db(session_factory)
        vol1 = econ_factory.load_vol1_series_from_db(session_factory)
        overrides.update(econ_factory.create_vol1_services(vol1, fred_cache))
    if wiring.wire_vol2_circulation:
        fred_cache = fred_cache or econ_factory.load_fred_series_from_db(session_factory)
        circ = econ_factory.load_circulation_series_from_db(session_factory)
        overrides.update(econ_factory.create_circulation_services(circ, fred_cache))
    if wiring.wire_vol3_financial:
        fred_cache = fred_cache or econ_factory.load_fred_series_from_db(session_factory)
        overrides.update(econ_factory.create_financial_services(fred_series_cache=fred_cache))
    return overrides
```

Call-site change (runner.py:1034-1040): compute `years = sorted(derive_year_set(config.start_year, config.ticks))` (import from `.reference_data_cache`), then

```python
        economics_overrides = _build_economics_overrides(
            session_factory=calc_session_factory,
        )
        economics_overrides.update(
            _build_wired_service_batches(
                calc_session_factory, defines.service_wiring, config.scope_fips, years
            )
        )
```

**Ordering subtlety:** `create_economics_services` also returns `melt_calculator`/`gamma_calculator` (identical construction today), and Batch-A's dict-update runs AFTER the E101 base — so when Phase 5.1 lands its ATUS-backed gamma in `_build_economics_overrides`, re-apply the base gamma last (`overrides["gamma_calculator"] = base_overrides["gamma_calculator"]`) or merge in the opposite order so 5.1's adapter always wins. Leave an explicit comment; this is the one 5.1↔5.2 interaction.

### Step 4 — C.8-lite wiring audit (loud machine)

C.8 has NOT landed at HEAD (planned for 2.R). Add a minimal version here regardless — it is this branch's acceptance evidence:

```python
_TICK_SERVICE_SLOTS: Final[tuple[str, ...]] = (
    "melt_calculator", "basket_calculator", "gamma_calculator",
    "capital_calculator", "throughput_calculator", "tensor_registry",
    "transition_engine", "reserve_army_data_source", "dispossession_data_source",
    "productivity_data_source", "turnover_profile_source", "inventory_data_source",
    "depreciation_data_source", "interest_calculator", "fictitious_capital_calculator",
    "distribution_calculator", "rent_calculator", "housing_calculator",
    "financial_crisis_assessor", "credit_cycle_detector", "counter_tendency_calculator",
    "value_basis_converter", "z1_source", "housing_data_source",
)


def _service_wiring_table(services: ServiceContainer) -> dict[str, bool]:
    """C.8 wiring audit: which TickDynamics slots are live vs None."""
    return {name: getattr(services, name) is not None for name in _TICK_SERVICE_SLOTS}
```

Log it right after container construction (one line per slot, `WIRED`/`None`) and thread the dict into `build_manifest`'s free-form `data_versions` (`manifest.py:228,:245-246` — "Free-form; all entries land in deterministic_inputs") as `data_versions["service_wiring"]`. No manifest schema change needed.

### Step 5 — Per-batch activation + proof windows (four commits)

For each batch N in **A → B → C → D** (A first — C hard-depends on A's `capital_stock > 0`, D's distribution/crisis need A's tensor registry; B is independent but its dispossession rates only matter after A):
1. TDD unit tests green (below).
2. Proof-window run with overlay (defaults still False):
   `overlays/wiring-batch-a.yaml` → `service_wiring: {wire_economics_core: true}` (cumulative for later batches).
   `poetry run python -m babylon.engine.headless_runner --scope detroit-tri-county --ticks 105 --defines overlays/wiring-batch-a.yaml` (105 ticks ⇒ boundaries at 52+104) and a 520-tick michigan run for the batch you're proving.
3. Write `specs/…/proof.md` (follow `specs/101-trade-activation/proof.md` / `specs/102-gamma-shocks/proof.md` R-PROOF style): assert **trace.csv byte-identical** to the no-flag run of the same seed (strong claim, justified by the zero-consumer verification above), diff `summary.json["events"]`, quote the manifest `service_wiring` table, note wallclock delta (tensor hydration = 913 county-year queries at startup for michigan — measure, don't guess).
4. **Final commit of the branch** (owner ruling: wire LIVE): flip the four defaults to `True`, regenerate `tests/baselines/michigan-e2e.json` via `mise run sim:e2e-bg` (watch `mise run sim:status`), commit baseline + consolidated proof.md in the same PR. `detroit-tri-county-5t.json` needs no regen (5 ticks < 52 — TickDynamics never fires; verify `mise run qa:e2e-regression` stays green untouched).

---

## 3. TDD plan (RED first, per batch)

Existing coverage to build on:
- `tests/unit/engine/headless_runner/test_gamma_wiring.py` — the exact monkeypatch harness for run()-level container assertions (`:53-152`: stubs Postgres/bridge, captures `ServiceContainer.create` kwargs via `_StopAfterCreate` sentinel). Extend, don't reinvent.
- `tests/unit/economics/test_factory.py` — `create_economics_services` contract (`:81` asserts **exactly seven keys** — don't touch the factory's return shape).
- `tests/unit/economics/tick/test_system.py` + `conftest.py` (`:283` `mock_melt_calculator`, `:313` `mock_transition_engine`) — system-behavior mocks; `test_financial_integration.py` covers the Vol-III layer with mocks.
- `tests/integration/economics/test_detroit_wiring.py` — legacy full-stack wiring integration.

New tests:

1. **`tests/unit/economics/tick/test_bridged_fips_identity.py`** (Step 1, RED reproduces the crash):
```python
def test_step_survives_bridged_territory_ids() -> None:
    """RED at HEAD: ValidationError ClassDistribution fips='T001' (tick 52)."""
    territories = {
        f"T{i:03d}": Territory(
            id=f"T{i:03d}", name=f"County 2616{i}",
            sector_type=SectorType.INDUSTRIAL, county_fips=f"2616{i}",
        )
        for i in range(1, 4)
    }
    graph = WorldState(territories=territories).to_graph()
    services = ServiceContainer.create(melt_calculator=_StubMelt(27.5))
    TickDynamicsSystem().step(graph, services, {"tick": 52})  # must not raise
    td = graph.get_graph_attr("tick_dynamics", None)
    assert set(td["county_states"]) == {"26161", "26162", "26163"}
```
   Plus: territory WITHOUT `county_fips` and 4-char id → excluded with a `caplog` warning, no raise; existing FIPS-keyed fixture graphs still resolve via the `node.id` fallback (regression guard for the whole tick unit suite).
2. **`tests/unit/config/test_service_wiring_defines.py`**: four flags exist, all default `False`, model frozen, `GameDefines().service_wiring` present, YAML section round-trips through `load_from_yaml` (write temp YAML with `service_wiring: {wire_vol1_production: true}`).
3. **`tests/unit/engine/headless_runner/test_defines_overlay.py`** (RED: overlay ignored at HEAD): `_apply_defines_overlay` flips exactly the overlay keys and preserves everything else; unknown key → ValidationError; run()-harness variant asserting the container's defines reflect the overlay.
4. **`tests/unit/engine/headless_runner/test_vol_wiring.py`** (per batch, gamma_wiring-style): `_build_wired_service_batches(sf, wiring_all_off, …) == {}`; each flag alone yields exactly its factory's keys, all non-None (skip-guard on `SQLITE_REF.exists()` like `test_gamma_wiring.py:26,:41-42`); run()-harness test that flags-on ⇒ `captured["interest_calculator"] is not None` etc.
5. **`tests/unit/engine/headless_runner/test_wiring_audit.py`**: `_service_wiring_table` covers all 24 slots; manifest `deterministic_inputs["data_versions"]["service_wiring"]` present.
6. **Batch-effect unit tests** (mocks, in `tests/unit/economics/tick/`): B — wage pressure shrinks `median_wage`; C — with turnover wired but K=0, `circulation_state` untouched (documents the A-dependency); D — real interest source ⇒ `national_rate > 0` and distribution gated on tensor surplus.

Scoped commands:
```bash
mise run test:q -- tests/unit/economics/tick/ tests/unit/engine/headless_runner/ tests/unit/config/
poetry run pytest tests/unit/engine/headless_runner/test_gamma_wiring.py tests/unit/economics/test_factory.py -q   # regression fences
mise run check                                            # merge gate: ruff + format + mypy strict + test:unit
mise run qa:e2e-regression                                # must stay green untouched (5t < first boundary)
```

## 4. Verification via short headless run

```bash
# Proof window (defaults OFF, overlay ON) — 2 year boundaries, ~3 counties
poetry run python -m babylon.engine.headless_runner --scope detroit-tri-county --ticks 105 \
  --defines overlays/wiring-batch-a.yaml
# assert: exit_reason=completed; startup log shows the WIRED/None table;
# manifest.json deterministic_inputs.data_versions.service_wiring matches the overlay;
# summary.json events may now include crisis_phase_transition entries.

# A/B trace neutrality (same seed, flag off vs on): diff the two bundles' trace.csv → byte-identical.

# Final (defaults ON): mise run sim:e2e-bg ; mise run sim:status   # 520t michigan regen for baseline+proof
```

## 5. Constraints & gotchas checklist

- Pydantic frozen models throughout; mypy strict (container slots are `Any`, so no typing friction; type the new helpers fully); ruff (`B905` zip strict, import order); functions ≤100 lines (hence the split helpers).
- Do NOT touch `create_economics_services`' 7-key contract (`test_factory.py:81`), the spec-057 Leontief slots (Phase 5.3), or the `fips[:2]`-as-NAICS quirk (`tick/system/__init__.py:1020` — see drift alert; document in proof.md).
- MELT returns NoDataSentinel for 2024 → Step-2 warn+skip for that year (`:372-374`); canonical 520t tops out at 2019 — non-issue, but note in proof.md for longer runs.
- `hydrate_counties` is startup-only; if michigan hydration is slow, measure before optimizing (spec-106 territory).
- Commit sequence: Step 1 → Step 2 → Step 3+4 → Batch A → B → C → D → defaults-flip+baseline+proof. Each is independently revertable; branch from `dev`, PR to `dev`.
