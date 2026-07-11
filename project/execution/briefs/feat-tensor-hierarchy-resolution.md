# Implementation Brief — Phase 5.3 `feat/tensor-hierarchy-resolution`

**Ruling context** (`project/REMEDIATION_PLAN.md:22,147`): owner ruled 2026-07-07 to wire dormant tensor_hierarchy **LIVE** (own phase, R-PROOF proof.md per activation batch). If evidence suggests county_exposure supersedes it, present evidence to Percy **BEFORE** any retirement. This brief's verdict: **county_exposure does NOT supersede it** (§C) — default wire-live plan stands; §H is the evidence dossier for the owner.

All paths relative to `/home/user/projects/game/babylon` unless absolute. All line numbers verified against dev HEAD on 2026-07-08.

---

## A. Inventory — what spec-025/057 built (`src/babylon/economics/tensor_hierarchy/`, 3,790 raw lines / 14 py files)

| Module | Lines | What it computes | Status |
|---|---|---|---|
| `types.py` | 782 | Frozen Pydantic tensors: `InterIndustryFlow`, `LeontiefInverse` (:401), `ImperialRentField` (:463), `ShadowSubsidyTensor` (:522), `StationaryDistribution` (:564), `DecomposedFlow`, `ImportShareVector`, `PeripheryLaborCoefficients`, `ProductionChainRentResult`, `Department` enum (:63) | shared |
| `inter_industry.py` | 399 | `DefaultInterIndustryFlowSource` (:52, reads `fact_bea_io_coefficient` USE matrix over ALL 107 `dim_bea_industry` codes ordered `line_number, bea_code` :134-141; `get_industry_codes()` :166-185); `DefaultLeontiefComputer` (:216, L=(I−A)⁻¹); `DefaultDepartmentAggregator` (:292, 107→4 Marxian depts via TOML) | **WIREABLE** (flow source); LeontiefComputer + DeptAggregator have no consumer even post-wiring |
| `production_chain_rent.py` | 201 | `DBImportShareSource` (:38-79, **reads IMPORT_USE table type — absent from DB, see §D**); `ProductionChainDecomposer` (:95, A→A_d/A_m/L_d, raises ValueError on industry misalignment :108-110); `ProductionChainRentCalculator` (:145, Φ_j = Σ_i M[i,j]·(w_ratio_i−1)·y_j, clamp :181) | decomposer+calculator WIREABLE; **DBImportShareSource UNUSABLE as-is** |
| `leontief_rent/periphery_labor_coefficients.py` | 237 | `DefaultPeripheryLaborCoefficientsSource` (:103): Hickel ERDI from `fact_hickel_erdi_annual` broadcast across BEA industries; `scale_type="Intensive"` default (:130); AxiomViolationEvent on ERDI<1 (:210-212) | **WIREABLE** (data 1980-2017 only) |
| `leontief_rent/final_demand.py` | 103 | `DefaultFinalDemandSource` (:33): BEA `total_final_uses_millions` per industry, gap-fill 0.0 (:86-90), raises ValueError on missing year (:100-103). **Units: $ MILLIONS** | **WIREABLE** (needs $ scaling, §D3) |
| `leontief_rent/industry_to_county_allocator.py` | 302 | `DefaultIndustryToCountyAllocator` (:82): QCEW window read (:164-178) → NAICS→BEA via `bridge_naics_bea` → county share of national BEA employment → `phi_hour[fips] = county_rent/(total_emp×2080)` (:250); emits `QcewCarryForwardEvent`/`PhiHourOutlierEvent`. NOTE: `allocate()` bypasses its CachedSource cache (:109-127) | **WIREABLE** (perf + crosswalk caveats §E/§D5) |
| `visibility.py` | 134 | `DefaultVisibilitySource` (:43): wraps gamma calculator → `VisibilityMetric`/`ShadowSubsidyTensor` | wrapper; gamma fix = Phase 5.1; no consumer |
| `reproduction.py` | 170 | `DefaultReproductionSource` (:123) returns `NoDataSentinel` **by design** — "CEX loader pending constitutional amendment" (:27) | DATA-BLOCKED STUB |
| `class_transition.py` | 216 | `DefaultClassTransitionSource` (:176) returns `NoDataSentinel` **by design** — PSID loader deferred (:34); `DefaultClassTransitionComputer` (:37) eigenvector math is real | DATA-BLOCKED STUB |
| `geographic_flow.py` | 277 | `DefaultGeographicFlowSource` reads `fact_faf_commodity_flow` (**2,494,901 rows EXIST**) → `ImperialRentField` per CFS area | data present, but **no consumer seam anywhere** — wiring needs a new spec; OUT OF 5.3 SCOPE |
| `validation.py`, `protocols.py`, `mappings/` | 830 | Three-tier validation, 8 Protocols, typed BEA→dept TOML singleton | shared |

## B. Callers — verified

- **Zero production imports** of `tensor_hierarchy` outside itself: only refs in src are Sphinx docstrings (`config/defines/economy_basic.py:498`, `reference/schema.py:2554`, `dialectics/instances/scale.py:39`, `melt/gamma_hydration.py:68`, `substrate/{__init__,protocols,types,validation}.py` See-Alsos). Review claim CONFIRMED for imports.
- **BUT the review understates the seam**: a complete, duck-typed production execution path already exists and runs every year boundary:
  - `simulation_engine._DEFAULT_SYSTEMS` → `TickDynamicsSystem.step` (position 4) gates `tick % 52 == 0` (`economics/tick/system/__init__.py:132`) and `services.melt_calculator is not None` (:136-138 — melt IS wired since E101, so the gate passes in canonical runs)
  - Step 4 → `_compute_imperial_rent` (:181, body :573-600) → `economics/tick/system/imperial_rent.py:45 compute()`
  - `compute()` stage 1 (`imperial_rent.py:86-88, 158-169`) checks 5 ServiceContainer slots — `periphery_labor_source`, `final_demand_source`, `industry_county_allocator`, `production_chain_calculator`, `bea_industries` (`engine/services.py:131-140`; `create()` kwargs :179-183) — **all None in every entry point**, so every year-boundary tick emits the wildcard `QcewCarryForwardEvent(county_fips="*")` unwired sentinel and passes county states through.
- Entry points and their wiring: canonical headless runner wires only `gamma_calculator`+`melt_calculator` (`engine/headless_runner/runner.py:869-917 _build_economics_overrides`, call site :1031-1043); `tools/tick_probe.py:100` wires nothing; web bridge uses `simulation_engine.step()` (`web/game/engine_bridge.py:21`) with no `calculator_overrides`.
- **Downstream consumers of `phi_hour`** (what wiring makes live): frozen at bootstrap `0.0` today (`tick/system/__init__.py:467,509`; `tick/initializer.py:203`):
  1. `TickSummary.Phi_aggregate = Σ phi_hour×employment×2080` (`tick/derived_rates.py:106-110`) → graph attr → persisted → **observable surface for R-PROOF even before 5.2**
  2. Graph round-trip `tick_phi_hour` (`tick/graph_bridge.py:95` write, :247 read)
  3. Class-transition savings adjustment `min(phi_hour×2080/wage, cap)` (`economics/dynamics/savings_schedule.py:76-94`) via `EconomicConditions.phi_hour` (`tick/system/__init__.py:1529`, `dynamics/transition_engine.py:135`) — **gated on `services.transition_engine` (:1491), which Phase 5.2 wires**. 5.3 lands the producer; 5.2 lands the semantic consumer.
  4. Legacy Simulation facade trace (`engine/simulation/_legacy.py:707`).
- Tests-only coverage today: 201 unit tests (`tests/unit/economics/tensor_hierarchy/` 177 + `leontief_rent/` 24) + 8 defines tests + `tests/integration/economics/tick/{test_imperial_rent_pipeline,test_facade_behavioral_fence,test_imperial_rent_perf,test_imperial_rent_calibration}.py`. The SC-004 OOM calibration assertion is explicitly DEFERRED "until Wayne County baseline is wired" (`test_imperial_rent_calibration.py:7-11`) — **this branch owes it**.

## C. county_exposure (spec-100/101) comparison — does it supersede?

| Dimension | spec-100/101 `county_exposure.py` + `engine/systems/phi_distribution.py` | spec-057 tensor_hierarchy pipeline |
|---|---|---|
| Output quantity | Weekly Φ **flow** ($/week) per county, per external bloc | `phi_hour` **rate** ($/labor-hour) per county |
| Φ magnitude source | Hickel national drain (raw, `postgres_initialization.py` `national_phi_reference` :89,109,698; Hickel preflight :247-286) — 2015 anchor **$9.75T** | Structurally derived: Leontief chain × import content × ERDI wage differential × final demand — 2015 prototype **$931B** (§H) |
| Consumer | `BoundaryFlowRegister` DRAIN_EDGE rows → ConservationAuditor Σ≡Φ_week identity (spec-101 FR-101-5, `runner.py:994-997`) | Class-transition savings calculus (Vol-I/016 dynamics) + Phi_aggregate |
| Temporal behavior | **Static**: one start-year map loaded once (`runner.py:1058-1067`), bloc-invariant broadcast | Recomputed **every sim-year** with year-scoped ERDI/IO/QCEW |
| Industry resolution | Pre-collapsed to one county weight | 107 BEA industries end-to-end |
| Compute location | Offline (`mise run data:exposure`, `src/babylon_data/exposure/`) → `fact_county_exposure_by_external` (2010-2024, 8 blocs) | Runtime, per year boundary |
| Shared DNA | Both use the SAME noncomparable-imports proxy (spec-100 verified IMPORT_USE absent 2026-07-04, `babylon_data/exposure/compute.py:20-34`) and QCEW county shares | — |

**Verdict: complementary, not superseding.** They overlap only in the "distribute by import-exposure × QCEW shares" concept. spec-101 answers conservation/money-flow; spec-057 answers the per-hour imperial-rent rate that the survival/class-transition calculus consumes. Retiring tensor_hierarchy would leave `phi_hour` permanently 0 and the Vol-I savings adjustment permanently inert. The holistic review's "superseded" framing (HOLISTIC_REVIEW:472, 524) conflates the two quantities. **No retirement; owner sees §H anyway per ruling.**

## D. Blockers found (NEW — in no review) and their resolutions

1. **No IMPORT_USE data**: `dim_bea_io_table_type` contains only `USE` + `TOTAL_REQ` (verified read-only query). `DBImportShareSource` (production_chain_rent.py:38-79) would return industries present-in-facts ordered `bea_code` (~71) which ≠ the 107-code flow list → `ProductionChainDecomposer.decompose` raises ValueError (:108-110) → **uncaught in `compute()` stage 4 (imperial_rent.py:126-127) → engine tick CRASH**. Even if aligned, IMPORT_USE absence ⇒ m_j≡0 ⇒ Φ≡0. **Resolution**: new `NoncomparableImportShareSource` using the spec-100 proxy — m_j = A[import_row, j] / Σ_i A[i, j] where import_row = `dim_bea_industry` name LIKE 'Noncomparable imports%' (id=107, bea_code='Other'; precedent `babylon_data/exposure/compute.py:57,110-118`). Measured 2015: m_j mean 0.0067, max 0.139, 66 nonzero — understates comparable imports (documented spec-100 limitation, same words).
2. **Uncaught stage-4 ValueError**: add a `try/except ValueError` guard around `get_import_shares` in `compute()` mirroring the final_demand pattern (imperial_rent.py:101-105) so a bad year degrades loudly instead of crashing (behavioral fence preserved: same return class, same exception classes).
3. **Unit mismatch ($M vs $)**: `total_final_uses_millions` ⇒ phi_vector in $M ⇒ `phi_hour = county_rent/(emp×2080)` lands at ~3.4e-6 instead of ~$3.45/hr (the savings_schedule doc example is `phi_hour=3.50` dollars, `savings_schedule.py:53`; allocator comment :246-248 admits units are caller-defined). **Resolution**: `DollarsFinalDemandSource` wrapper ×1e6. Sanity: $931.4B ÷ (137.5M QCEW jobs × 2080h) ≈ $3.26/hr national mean — inside outlier thresholds ±1000 (`economy_basic.py:503-520`).
4. **Hickel 'Intensive' ends 2017** (`fact_hickel_erdi_annual`: Extensive 1960-79, Intensive 1980-2017, Intensive_China_Inflection 2005 only; ERDI 2015 = 8.25). A 2010-start 520-tick run touches years 2010-2019 (`_determine_year` base 2010, `tick/system/__init__.py:272-284`): **2018-2019 degrade to pass-through** (prior phi_hour preserved, wildcard sentinel emitted). Same shape as the dead-gamma trap the review flagged — MUST appear in proof.md + the C.8 wiring manifest when it lands (2.R).
5. **Crosswalk coverage 12.8%**: `bridge_naics_bea` (462 rows, 66 BEA codes; NAICS lengths 2-6) matches only 154 of 1,382 six-digit codes, and `fact_qcew_annual` stores 6-digit leaf rows only (verified Wayne 2015: 931 rows, all len-6, Σemp=699,235 — no hierarchy double-count). Measured: covered employment = 12.9% (Wayne) / 12.8% (national). Effect: phi_hour deflated (denominator uses full total_emp, numerator routes through covered industries only); conservation holds only over crosswalk-reachable industries. **Not a blocker** — mechanics correct, magnitudes attenuated; flag for data-program (086/097/098 family) crosswalk densification. Include measured number in proof.md.
6. **Data present and sufficient otherwise**: `fact_bea_io_coefficient` USE 2010-2024 (~3.85k/yr); `fact_bea_final_demand_annual` 1997-2024 (73 codes/yr); `fact_qcew_annual` 2010-2024 (~0.97-1.0M rows/yr, 3,220 counties); `dim_bea_industry` 107 rows (7 NULL line_number sort first — deterministic with bea_code tiebreak).

## E. Cost estimate (measured on this machine, read-only sqlite3)

Pipeline frequency: **year boundaries only** (tick % 52 == 0) → 10 invocations in a 520-tick run.
- Allocator step-2 QCEW window read `[year−5, year]`: **5,826,100 rows in 73.5s** + Python dict aggregation (est. +20-40s, ~1.5-2 GB transient RAM). Dominant cost. Runs on the FULL national table regardless of scope (national denominators are semantic — do not scope-filter).
- Flow-source USE load: 0.7s/yr. 107×107 `np.linalg.inv`: 1.1ms. Periphery/final-demand: 1-73 rows, negligible.
- **Total: ~95-115s per year boundary ⇒ ~16-19 min added to a 520-tick canonical run; amortized ~2s/tick.** Acceptable for wire-live; record actuals in proof.md. Follow-up optimization (separate commit, optional): SQL-side `GROUP BY` + max-year selection to avoid shipping 5.8M rows into Python (est. 5-10× reduction). Note: `allocate()` never uses its cache (:109-127) — harmless at 1 call/boundary.
- Event volume: carry-forward events emitted per county with stale data; QCEW is complete 2010-2024 for run years ⇒ near-zero expected. Outliers: none at $3.26/hr scale.

## F. Implementation steps (TDD red→green; commit per unit via `mise run commit`)

**Step 0** — branch `feat/tensor-hierarchy-resolution` from `dev`.

**Step 1 — defines gate** (`src/babylon/config/defines/economy_basic.py`, inside `LeontiefRentDefines` :483-521, after `qcew_carry_forward_max_years`):
```python
    enabled: bool = Field(
        default=True,
        description=(
            "Master gate for wiring the Spec 057 Leontief imperial-rent "
            "pipeline into the headless runner (remediation Phase 5.3, "
            "owner ruling 2026-07-07: wire dormant tensor_hierarchy LIVE). "
            "False restores graceful-degradation stub behavior "
            "(phi_hour frozen at bootstrap values)."
        ),
    )
```
RED first: extend `tests/unit/config/test_leontief_rent_defines.py` (8 tests exist) — `enabled` defaults True, frozen. Note: field addition changes `_defines_hash` (runner.py:850-858) in run manifests — call out in proof.md. Default True implements the ruling; the OFF leg for A/B proof uses a temporary `src/babylon/data/defines.yaml` override (`GameDefines.load_default()` picks it up; none exists at HEAD).

**Step 2 — import-share source**, NEW `src/babylon/economics/tensor_hierarchy/leontief_rent/import_shares.py` (~120 lines, style of siblings — `CachedSource`, RST docstrings, mypy strict):
```python
class NoncomparableImportShareSource(CachedSource[ImportShareVector]):
    """Noncomparable-imports proxy for per-industry import shares (Phase 5.3).

    The reference DB carries no BEA IMPORT_USE matrix (verified 2026-07-04,
    spec-100; re-verified 2026-07-08): the only import-content measure is the
    USE-table row of dim_bea_industry "Noncomparable imports and rest-of-the-
    world adjustment". m_j = A[import_row, j] / sum_i A[i, j] — the fraction
    of industry j's intermediate inputs that are noncomparable imports. This
    UNDERSTATES total import content (comparable imports are commingled into
    domestic commodity rows); same limitation as spec-100 county exposure.
    """
    cache_negative_results: bool = True

    def __init__(self, *, db_session: Session, bea_industries: list[str]) -> None:
        super().__init__()
        self._db = db_session
        self._industries = list(bea_industries)

    def get_import_shares(self, year: int) -> ImportShareVector:
        result = self._resolve(year, lambda: self._fetch(year))
        if isinstance(result, NoDataSentinel):
            raise ValueError(f"No USE coefficients for year {year}; cannot derive import shares")
        return result

    def _fetch(self, year: int) -> ImportShareVector | NoDataSentinel:
        # 1) resolve import-source bea_industry_id via industry_name LIKE
        #    'Noncomparable imports%' (mirror babylon_data/exposure/compute.py:110-118)
        # 2) load USE coefficients for year (same ORM joins as
        #    DefaultInterIndustryFlowSource.get_direct_requirements, inter_industry.py:86-157)
        # 3) build shares np.ndarray in self._industries order:
        #    m_j = coeff(import_row -> j) / colsum_j, 0.0 where colsum_j == 0
        # 4) return ImportShareVector(year=year, industries=self._industries, shares=...)
```
Alignment invariant: `industries == bea_industries` exactly (order+length) so `decompose()` :108-110 never raises. RED tests: NEW `tests/unit/economics/tensor_hierarchy/leontief_rent/test_import_shares.py` using the `reference_sqlite_session_factory` fixture pattern (see `test_industry_to_county_allocator.py:46-60` — in-memory `NormalizedBase` schema, seed `DimTime`/`DimBEAIndustry`/`DimBEAIOTableType`/`FactBEAIOCoefficient`): (a) alignment to configured list incl. codes with no facts (share 0.0); (b) m_j = coeff/colsum on a synthetic 3-industry fixture with one import row; (c) zero-colsum → 0.0; (d) missing year → ValueError; (e) determinism (two calls identical).

**Step 3 — unit adapter + bundle + builder**, NEW `src/babylon/economics/tensor_hierarchy/leontief_rent/wiring.py`:
```python
@dataclass(frozen=True)
class ProductionChainService:
    """Attribute bundle matching imperial_rent.compute's access pattern
    (services.production_chain_calculator.{flow_source,import_shares_source,
    decomposer,calculator} — imperial_rent.py:107,126-133)."""
    flow_source: DefaultInterIndustryFlowSource
    import_shares_source: NoncomparableImportShareSource
    decomposer: ProductionChainDecomposer
    calculator: ProductionChainRentCalculator


class DollarsFinalDemandSource:
    """Unit adapter: DefaultFinalDemandSource returns $ MILLIONS
    (total_final_uses_millions); phi_hour consumers expect DOLLARS/hour
    (savings_schedule.py:53 example: 3.50). Scale by 1e6 here so
    phi_vector, county_rent, and phi_hour are all in dollars."""
    _MILLIONS_TO_DOLLARS = 1_000_000.0

    def __init__(self, base: DefaultFinalDemandSource) -> None:
        self._base = base

    def get_final_demand(self, year: int) -> np.ndarray:
        return self._base.get_final_demand(year) * self._MILLIONS_TO_DOLLARS


def build_leontief_rent_services(
    *,
    session_factory: Callable[[], Session],
    db_session: Session,
    event_bus: EventBus,
    defines: LeontiefRentDefines,
) -> dict[str, Any]:
    """The 5 ServiceContainer kwargs (services.py:179-183) for spec-057."""
    flow_source = DefaultInterIndustryFlowSource(session_factory)
    bea_industries = flow_source.get_industry_codes()  # all 107, FR-006 baseline
    return {
        "periphery_labor_source": DefaultPeripheryLaborCoefficientsSource(
            db_session=db_session, event_bus=event_bus, bea_industries=bea_industries
        ),
        "final_demand_source": DollarsFinalDemandSource(
            DefaultFinalDemandSource(db_session=db_session, bea_industries=bea_industries)
        ),
        "industry_county_allocator": DefaultIndustryToCountyAllocator(
            db_session=db_session, event_bus=event_bus, defines=defines
        ),
        "production_chain_calculator": ProductionChainService(
            flow_source=flow_source,
            import_shares_source=NoncomparableImportShareSource(
                db_session=db_session, bea_industries=bea_industries
            ),
            decomposer=ProductionChainDecomposer(),
            calculator=ProductionChainRentCalculator(),
        ),
        "bea_industries": bea_industries,
    }
```
Export from `leontief_rent/__init__.py` (update `__all__` per CI hygiene). RED tests: NEW `tests/unit/economics/tensor_hierarchy/leontief_rent/test_wiring.py` — builder returns exactly the 5 keys; `bea_industries` == `flow_source.get_industry_codes()`; bundle attrs match compute()'s access pattern; DollarsFinalDemandSource scales ×1e6.

**Step 4 — stage-4 crash guard**, `src/babylon/economics/tick/system/imperial_rent.py:126` — replace the bare call:
```python
    try:
        shares = services.production_chain_calculator.import_shares_source.get_import_shares(year)
    except ValueError:
        _publish_no_data_signal(services, year=year, source_name="import_shares_source")
        return _stub_zero_pass_through(county_states)
```
(Mirrors :101-105; behavioral fence intact — same return class, same exception classes, unchanged event ordering.) RED test: add to `tests/integration/economics/tick/test_imperial_rent_pipeline.py` a `MockImportSharesSource(raise_value=ValueError(...))` case asserting pass-through + one wildcard sentinel with `source_name == "import_shares_source"`.

**Step 5 — runner wiring**, `src/babylon/engine/headless_runner/runner.py`:
- Extend `_build_economics_overrides` (:869-917) signature: `(session_factory: Any = None, *, leontief_session: Any = None, event_bus: Any = None, defines: Any = None)`. After the melt block (:905-915), add:
```python
    if (
        leontief_session is not None
        and event_bus is not None
        and defines is not None
        and defines.economy.leontief_rent.enabled
    ):
        from babylon.economics.tensor_hierarchy.leontief_rent.wiring import (
            build_leontief_rent_services,
        )

        overrides.update(
            build_leontief_rent_services(
                session_factory=session_factory,
                db_session=leontief_session,
                event_bus=event_bus,
                defines=defines.economy.leontief_rent,
            )
        )
```
- Call site (:1031-1043): after `calc_session_factory = get_normalized_session_factory()` add `leontief_session = calc_session_factory()` and pass `leontief_session=leontief_session, event_bus=event_bus, defines=defines` (event_bus exists since :988; `defines` since :956). Initialize `leontief_session: Any = None` with the other pre-try locals (:947-951) and close it in the `finally:` block (:1237-1243) alongside `runtime.close()`/`pool.close()`. Update the function's Spec-E101 docstring to mention 5.3. (Sources hold one run-lifetime read-only SQLite session — same DB the melt session factory targets; runner is single-threaded.)
- Optional parity: `tools/tick_probe.py:100` may get the same overrides in a follow-up commit (not required for R-PROOF).

RED tests: NEW `tests/unit/engine/headless_runner/test_leontief_wiring.py`, cloning the proven patterns in `tests/unit/engine/headless_runner/test_gamma_wiring.py`:
- `test_build_overrides_wires_spec057_when_enabled` (real ref-DB session via `get_normalized_session_factory`, real `EventBus`, `GameDefines()`): all 5 keys present and non-None; `len(overrides["bea_industries"]) == 107`.
- `test_build_overrides_omits_spec057_when_disabled`: `GameDefines` with `economy.leontief_rent.enabled=False` (`model_copy(update=...)` through the frozen chain, or construct `EconomyDefines(leontief_rent=LeontiefRentDefines(enabled=False))`) → none of the 5 keys present.
- `test_run_passes_spec057_services_to_service_container`: monkeypatch harness copied from `test_gamma_wiring.py:53-152` (`_StopAfterCreate` sentinel), assert `captured["production_chain_calculator"] is not None` etc.

**Step 6 — real-data integration proof tests**, NEW `tests/integration/economics/tick/test_leontief_live_wiring.py` (`@pytest.mark.integration`, skip when `data/sqlite/marxist-data-3NF.sqlite` missing):
- `test_phi_hour_nonzero_and_plausible_2015`: build services via `build_leontief_rent_services` + `SimpleNamespace` (pattern `test_imperial_rent_pipeline.py:178-196`) with 2-3 Michigan county fixtures (`_county` helper :38-65), `NationalTickParameters(year=2015, ...)` → `compute()` → `0.0 < phi_hour < 100.0` for counties present, in DOLLARS/hour scale.
- `test_determinism`: two identical calls produce byte-equal `{fips: phi_hour}` (Constitution III.7).
- `test_2019_degrades_loud`: year=2019 (no Hickel) → states pass through unchanged, exactly one wildcard sentinel with `source_name == "periphery_labor_source"`.
- `test_sc004_hickel_oom`: complete the deferred gate in `test_imperial_rent_calibration.py` — compute national `total_phi` (sum of `rent_result.phi_vector`) for 2015, ratio vs Hickel CSV `annual_drain_usd_billions` (=9750.0). **Expected ratio ≈ 0.0955 — marginally BELOW the [0.1, 10] window** (§H). Assert `0.05 <= ratio <= 10.0` with a loud comment citing the IMPORT_USE gap, and flag the window choice for Percy in proof.md. Do NOT silently widen without the flag.

**Step 7 — R-PROOF (`proof.md` in the same PR)**: A/B 20-tick Michigan-scope headless runs — OFF leg via temporary `src/babylon/data/defines.yaml` (`economy: {leontief_rent: {enabled: false}}`), ON leg default. Document: `Phi_aggregate` per boundary; per-county `tick_phi_hour` sample; count of wildcard sentinels (expect: 0 unwired sentinels ON-leg for 2010-2017 years, per-year periphery sentinel for 2018+); wall-clock delta per boundary (§E predicted ~95-115s); `_defines_hash` change; the 0.0955 OOM ratio + crosswalk-coverage 12.8% findings; baseline regen if the michigan-e2e baseline shifts (it will — `Phi_aggregate` enters summary) with `write_baseline_to` + proof, per standing rules. Coordination: 2.R owns the coordinated regen — if 5.3 lands after 2.R, do its own regen; sequence with Phase-2 owner.

**Step 8 — docs**: update `ai/state.yaml` (tensor_hierarchy status DORMANT→LIVE-gated), add ADR to `ai/decisions.yaml` (noncomparable-imports proxy decision + unit-scaling decision), note Hickel-2017 coverage cliff next to the gamma-coverage note.

## G. Verification commands
```bash
poetry run pytest tests/unit/config/test_leontief_rent_defines.py -vv
poetry run pytest tests/unit/economics/tensor_hierarchy/ -vv                      # 201 existing must stay green
poetry run pytest tests/unit/economics/tensor_hierarchy/leontief_rent/test_import_shares.py \
                  tests/unit/economics/tensor_hierarchy/leontief_rent/test_wiring.py -vv
poetry run pytest tests/unit/engine/headless_runner/test_leontief_wiring.py \
                  tests/unit/engine/headless_runner/test_gamma_wiring.py -vv
poetry run pytest tests/integration/economics/tick/ -m integration -vv           # fence + pipeline + perf + calibration + NEW live wiring
poetry run mypy src/babylon/economics/tensor_hierarchy/ src/babylon/engine/headless_runner/ --strict
mise run check
mise run sim:probe -- --county 26163 --ticks 3    # smoke (probe unwired — expected unchanged)
```

## H. Evidence dossier for the owner (consult BEFORE any retirement / window change)

1. **Supersession**: NOT supported — §C table. county_exposure distributes the raw Hickel drain as conservation flows; tensor_hierarchy derives the structural $/hr rate feeding class transitions. Different quantities, consumers, temporal behavior. Recommendation: wire live (done by this branch), no retirement.
2. **Magnitude gap**: real-data prototype (2026-07-08, read-only): 2015 total structural Φ = **$931.4B** vs Hickel anchor **$9,750B** → OOM ratio **0.0955**, just under SC-004's [0.1, 10]. Root cause is the data gap (no IMPORT_USE ⇒ noncomparable-imports proxy, m_j mean 0.67%), not the code. Options: (a) accept widened [0.05, 10] gate with documented rationale (this brief's default); (b) commission an IMPORT_USE loader spec (data program) — would raise m_j and likely bring the ratio inside [0.1,10]; (c) rescale via a defines calibration factor (NOT recommended — violates III.8 material grounding).
3. **Crosswalk debt**: bridge_naics_bea reaches 12.8% of QCEW employment (6-digit leaf mismatch) — phi_hour attenuated; candidate for the 086/097/098 data program.
4. **Coverage cliff**: Hickel Intensive ends 2017; 2018+ sim-years freeze phi_hour at last computed values (loud sentinel). Extending the ERDI series is a data task, not a code task.

## I. Existing behavior contracts NOT to break
- `imperial_rent.compute` behavioral fence (Spec 058 FR-007): return class, ValueError for FR-006 misalignment, sorted-FIPS event ordering (imperial_rent.py:14-17).
- `_stub_zero_pass_through` prior-value semantics (:221-230) — counties absent from allocation keep prior phi_hour (never zeroed).
- `CountyEconomicState.phi_hour: Field(ge=0)` (`tick/types.py:318`) — negative rent impossible by three-layer clamp.
- Function-length rule (≤100 lines), frozen Pydantic, mypy strict, ruff (incl. B905 zip strict), RST docstrings, conventional commits via `mise run commit`.
