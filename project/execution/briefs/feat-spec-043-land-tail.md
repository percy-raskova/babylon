# Implementation Brief — feat/spec-043-land-tail (Phase 6.3)

**Scope authority**: `project/REMEDIATION_PLAN.md:155` — "4 remaining transitions (inheritance/eminent-domain/speculation/gentrification); ValueTensor4x3 intersection; retire static `equity_factor` (`wealth_proxy.py`, `economy_class.py`)". Spec source: `specs/043-land-ownership-substrate/spec.md` (127 lines, Status: Draft at `:6` — single-file spec, no tasks.md; the transitions table at `:88-96`, tensor integration at `:78-80`, constitutional constraints at `:100-106`, falsifiability at `:110-115`). Branch does not exist yet — create from `dev` (per babylon/CLAUDE.md governance).

All paths below are relative to `/home/user/projects/game/babylon` unless absolute.

---

## A. Verified current state

### A1. Live transition machinery — pattern to mirror

**No registry, no engine System.** The three live transitions are **stateless pure functions** in `src/babylon/economics/substrate/transitions.py` (237 lines), signature shape `(state: HexEconomicState, fraction: float, ...) -> HexEconomicState`:

- `apply_foreclosure` `:25-66` — clamps `min(tenure.residential_owner_occupied, max(0.0, fraction_lost))` (`:51`), early-returns `state` unchanged if `not state.tenure_composition` (`:46-47`) or `actual <= 0` (`:53-54`), builds an `updates` dict, `tenure.model_copy(update=updates)` then `state.model_copy(update={"tenure_composition": new_tenure})` (`:65-66`). Boolean routing arg `to_rental` selects sink share (`:60-63`).
- `apply_purchase` `:69-99` — rental → owner_occupied, clamped on rental.
- `apply_abandonment` `:102-145` — proportional split across owner+rental (`:132-136`), sink = vacant_abandoned.
- `evaluate_class_shares(tenure, equity_threshold_met) -> dict[SocialRole, float]` `:148-192` — property→class map (owner→LA if equity met else INTERNAL_PROLETARIAT; rental→INTERNAL_PROLETARIAT; commercial+industrial→CORE_BOURGEOISIE; vacant→LUMPENPROLETARIAT; public/trust excluded).
- `check_equity_threshold(state, defines: ClassSystemDefines | None) -> bool` `:195-237` — `equity_ratio = s/(c+v+s)` (`:236`) vs `defines.equity_factor` (`:237`); lazy-default defines via local import (`:227-230`). This IS the dynamic replacement for the static scaler.

Data model: `HexTenureComposition` at `src/babylon/economics/substrate/types.py:88-125` — 7 frozen `ge=0.0` float shares, `@model_validator(mode="after")` enforcing sum==1.0 within `CONSERVATION_TOLERANCE = 1e-10` (`:40`, validator `:110-125`). Attached as `HexEconomicState.tenure_composition: HexTenureComposition | None = None` (`:183-185`).

Ground-rent circuit: `src/babylon/economics/substrate/ground_rent.py` — `GroundRentResult` frozen model `:36-53` (absolute/differential/total + `rent_from_v`/`rent_from_s` split), `compute_ground_rent(state, r_avg, defines: RentCircuitDefines | None)` `:65-152`. Integrated into `DefaultHexEqualizationComputer.equalize_capital` at `src/babylon/economics/substrate/equalization.py:117-242` (rent phase `:156-195`: deducts `rent_from_v` from v and `rent_from_s` from s pre-migration, gated on `rent_defines is not None`).

**Export gap**: `src/babylon/economics/substrate/__init__.py` exports ground_rent (`:24`, `__all__:62-64`) but **never imports `transitions`** — `apply_*`, `evaluate_class_shares`, `check_equity_threshold` are absent from the package `__all__`. Fix in this branch (CLAUDE.md "Maintain `__all__` Exports").

**Dormancy fact (baseline-relevant)**: nothing in the canonical runner reaches this code. `hydrate_hex_grid` (`substrate/hydrator.py:66-159`) never sets `tenure_composition`; `equalize_capital` has exactly one non-test caller, `tools/demo_substrate.py:170`, and it passes **no** `rent_defines`; `ServiceContainer.hex_grid` defaults `None` (`src/babylon/engine/services.py:104`) and is never assigned a `HexGrid` in production, so `TickDynamicsSystem._write_hex_substrate` no-ops (`src/babylon/economics/tick/system/__init__.py:255-257`).

### A2. Spec text for the 4 missing transitions (`specs/043-land-ownership-substrate/spec.md:88-96`)

| Transition | Spec mechanism (verbatim) | Class effect |
|---|---|---|
| Inheritance | "D-P-D' Lifecycle Circuit: intergenerational property transmission." | Sustains LA Reproduction |
| Eminent Domain | "State `DEVELOP` or `ADMINISTER` action confiscating land." | Displacement; LA → Proletariat |
| Speculation | "Exchange-value of land drastically decouples from use-value." | Pricing pressure; setup for gentrification |
| Gentrification | "Coordinated capital infusion shifting hex composition (rental → commercial / owner_occupied)." | Proletariat displacement |

One line each — share sources/sinks are design decisions; this brief fixes them (section B). Existing machinery to anchor each:

- **Inheritance**: `src/babylon/economics/lifecycle/inheritance.py` — `_CLASS_INHERITANCE_SCALE` `:92-98` (LA=0.5, PROLETARIAT=0.05, LUMPEN=0.0), `compute_class_aware_inheritance` `:142-186` with **foreclosure severing** `:166-173` (net_inheritance=0 when foreclosed). Engine emission point: `src/babylon/engine/systems/lifecycle.py:161-180` publishes `EventType.INHERITANCE_TRANSFER` (`models/enums/events.py:113`) when D' deaths > 0. Circuit split: `lifecycle/dual_circuit.py` `compute_dispossession_effects` (home-equity fraction → inheritance impact).
- **Eminent domain**: `OrgAction.ADMINISTER`/`DEVELOP` exist at `src/babylon/models/enums/organizations.py:83-84` (OODA verbs). Tension-driven trigger sibling: `engine/systems/dispossession_events.py` reads `foreclosure_rate`/`eviction_rate`/`displacement_rate` node attrs (`:66-71`).
- **Speculation**: exchange/use-value decoupling signal **already exists**: `HousingValueDecomposition` at `src/babylon/economics/rent/types.py:78-121` with `speculative_premium` (`:102`) and computed `fictitious_fraction` (`:110-121`); `DefaultHousingDecompositionCalculator.decompose_housing_value(fips, year)` at `economics/rent/calculator.py:156+` (spec-024 FR-008/009). Use `fictitious_fraction` as the caller-side trigger; the transition itself only mutates tenure.
- **Gentrification**: spec names source and sinks explicitly: rental → commercial / owner_occupied.

### A3. ValueTensor4x3 intersection — what exists / what's missing

Spec `:78-80`: residential rent intersects **v** (worker reproduction fund); commercial/industrial rent intersects **s** (splits surplus into profit-of-enterprise vs ground rent).

Exists (hex-scalar level): `GroundRentResult.rent_from_v`/`rent_from_s` (`ground_rent.py:132-144`) + deduction in equalization (`equalization.py:171-195`). **Missing**: any function touching `ValueTensor4x3` — `ground_rent.py` and `transitions.py` never import `economics/tensor.py`. The 4-department decomposition (`ValueTensor4x3` at `tensor.py:211-296`: `dept_I/IIa/IIb/III: DepartmentRow` `:261-268`; `DepartmentRow(c,v,s)` `:133-204`; computed `total_v` `:325-336`, `total_s` `:338-346`) is where the intersection must land. Type constraint: `c/v/s` are `LaborHours` = `Annotated[float, Field(ge=0.0), SnapToGrid]` quantized to **1e-6** (`src/babylon/models/types.py:213-235`) — conservation assertions in tests must use `abs=1e-6`, NOT the substrate's 1e-10.

### A4. Static equity_factor sites to retire

1. **`src/babylon/economics/melt/wealth_proxy.py`** (519 lines):
   - `EQUITY_FACTOR = 0.6` class constant `:159`.
   - `__init__` param `equity_factor: float | None = None` `:242` + priority chain `:265-271` (`explicit > class_system_defines.equity_factor > EQUITY_FACTOR`).
   - Scaler math `return effective * self._equity_factor` at `:334` inside `estimate_la_share` `:293-334` — **already emits `DeprecationWarning`** (`:317-326`) pointing to `check_equity_threshold` + `evaluate_class_shares`. Docstring `.. deprecated::` block `:296-301`.
   - Internal consumer: `get_class_distribution_estimate` calls `self.estimate_la_share(fips, year)` at `:486`.
   - Module docstring calibration story `:23-27` ("EQUITY_FACTOR = 0.6 calibrated from Fed SCF").
2. **`src/babylon/config/defines/economy_class.py`**:
   - `ClassSystemDefines.equity_factor` field `:221-229` — description ALREADY re-purposed: "Feature 043: Absolute threshold test on equity required for LA classification. Formerly a population-level numeric scaler." **DO NOT DELETE THE FIELD** — `check_equity_threshold` consumes it (`transitions.py:237`), and `GameDefines` assembles it (`config/defines/_assembler.py:170`, yaml load `:298`; no `src/babylon/data/defines.yaml` exists, so dataclass defaults apply).
   - **Stale scaler language remains** in the class-level Args docstring `:194-195`: "equity_factor: Fraction of homeowners with meaningful equity. Calibrated: 65% ownership * 0.6 = 39% ~ 40% LA share." — rewrite to threshold semantics.
3. Production blast radius is minimal: only registration `self.register(WealthProxyCalculator, DefaultWealthProxyCalculator)` at `src/babylon/core/protocol_kit.py:256`; zero runtime callers of `estimate_la_share` outside the module. Test blast radius: `tests/unit/economics/melt/test_wealth_proxy.py` (510 lines; scaler-math tests `:214-246`, `T018` defines-priority tests `:420-471`), `tests/unit/economics/melt/test_county_classification.py:319-320` (asserts Oakland LA > Wayne LA), `tests/unit/economics/melt/test_class_position.py:687-768` (lumpen + `get_class_distribution_estimate` distribution tests — executor MUST read `:729-768` assertions before changing semantics).

**What replaces the scaler (the dynamic value)**: per-hex — `evaluate_class_shares(tenure, check_equity_threshold(state, GameDefines().class_system))`; county-level — owner-occupancy share × the **boolean** threshold test on the county equity ratio `s/(c+v+s)` (Constitution VIII.1: discrete switch, not a 0.6 multiplier). County c/v/s available via `MarxianHydrator.hydrate(fips, year)` tensor (`substrate/hydrator.py:182-187` shows the access pattern).

### A5. Existing test coverage to mirror

- `tests/unit/economics/substrate/test_transitions.py` (136 lines) — module-level `base_state` fixture `:15-36` (tenure 0.4/0.2/0.1/0.1/0.1/0.0/0.1 on Wayne hex `"872830828ffffff"`, c=500/v=200/s=100), `@pytest.mark.unit class TestDiscreteTransitions` `:39-136`. Per-transition coverage: happy path, clamp (`:61-68`), no-op on `tenure_composition=None` asserting **identity** `res1 is empty_state` (`:102-110`), class-share integration (`:112-136`). Assertions via `abs(x - y) < 1e-9`.
- `tests/unit/economics/substrate/test_equity_threshold.py` (162 lines) — `_make_tenure(**kwargs)` / `_make_hex_state()` helper pattern `:24-57`; threshold boundary tests + foreclosure-demotes-LA integration `:126-149`.
- `tests/unit/economics/substrate/test_ground_rent.py` (264 lines) + `test_equalization_rent.py` (197 lines) — rent formula and pipeline-integration patterns; hex IDs from `tests/unit/economics/substrate/conftest.py` (`WAYNE_HEX_IDS:26`, `OAKLAND_HEX_IDS:33`).

---

## B. Implementation plan (TDD, one commit per unit)

Use `mise run commit -- "..."` for hook-safe commits. All new code: frozen Pydantic, explicit return types, RST docstrings (Args/Returns + `See Also` cross-refs), mypy strict, ruff clean.

### Commit 1 — `feat(substrate): four remaining spec-043 tenure transitions`

**RED**: extend `tests/unit/economics/substrate/test_transitions.py` with four `@pytest.mark.unit` classes reusing the existing `base_state` fixture. Minimum matrix per transition (mirrors live coverage): happy path with exact-arithmetic assertions; clamp when fraction exceeds source share; no-op identity when `tenure_composition is None`; no-op when clamped amount ≤ 0; shares still a valid composition (the model validator raises on construction, but assert sum explicitly like the live tests assert per-field). Suggested cases:

```python
@pytest.mark.unit
class TestInheritance:
    def test_full_retention_is_noop(self, base_state: HexEconomicState) -> None:
        """retention_rate=1.0 sustains LA reproduction: tenure unchanged."""
        new_state = apply_inheritance(base_state, 0.2, retention_rate=1.0)
        t = new_state.tenure_composition
        assert t is not None
        assert abs(t.residential_owner_occupied - 0.4) < 1e-9

    def test_failed_transmission_to_rental(self, base_state: HexEconomicState) -> None:
        """retention 0.5 on 0.2 transferred: 0.1 estate-sold to landlords."""
        new_state = apply_inheritance(base_state, 0.2, retention_rate=0.5, to_rental=True)
        t = new_state.tenure_composition
        assert t is not None
        assert abs(t.residential_owner_occupied - 0.3) < 1e-9
        assert abs(t.residential_rental - 0.3) < 1e-9

    def test_severed_inheritance_to_vacant(self, base_state: HexEconomicState) -> None:
        """retention 0.0, to_rental=False: Detroit tax-forfeiture signature."""
        new_state = apply_inheritance(base_state, 0.2, retention_rate=0.0, to_rental=False)
        t = new_state.tenure_composition
        assert t is not None
        assert abs(t.residential_owner_occupied - 0.2) < 1e-9
        assert abs(t.vacant_abandoned - 0.3) < 1e-9
```
Plus clamp (`fraction_transferred=0.5` → clamp to 0.4), and None-tenure identity. For eminent domain: proportional take across owner(0.4)/rental(0.2)/vacant(0.1) pool=0.7 with `fraction_taken=0.35` → owner −0.2, rental −0.1, vacant −0.05, public 0.1→0.45; plus `include_vacant=False` variant (pool=0.6); plus clamp to full pool. For speculation: `apply_speculation(base_state, 0.1)` → owner 0.3, rental 0.3 (inverse of purchase); clamp at 0.4. For gentrification: `fraction_converted=0.2, commercial_ratio=0.5` → rental 0.2→0.0, commercial 0.1→0.2, owner 0.4→0.5; ratio 1.0 and 0.0 variants; clamp on rental.

**GREEN**: append to `src/babylon/economics/substrate/transitions.py`, exactly in the live style (clamp → early return → `updates` dict → double `model_copy`). Sketches (surrounding style, ~40 lines each incl. docstring — well under the 100-line rule):

```python
def apply_inheritance(
    state: HexEconomicState,
    fraction_transferred: float,
    retention_rate: float,
    to_rental: bool = True,
) -> HexEconomicState:
    """Apply an intergenerational inheritance event to a hex.

    D-P-D' Lifecycle Circuit (Feature 030): owner-occupied property of the
    dying D' cohort either transmits to heirs (sustaining LA reproduction —
    tenure unchanged) or fails to transmit. Failed transmission is an
    estate sale to landlords (``residential_rental``) or tax-delinquent
    forfeiture (``vacant_abandoned``). Foreclosure severing (spec 038
    FR-008) is expressed as ``retention_rate=0.0``.

    Args:
        state: Current hex economic state.
        fraction_transferred: Fraction of total hex area in owner-occupied
            estates whose owners died this tick.
        retention_rate: Fraction of transferred property retained by heirs,
            in [0, 1]. Callers derive this from
            :meth:`~babylon.economics.lifecycle.inheritance.DefaultInheritanceCalculator.compute_class_aware_inheritance`.
        to_rental: If True, non-retained property is bought by landlords;
            if False it becomes vacant/abandoned.

    Returns:
        Updated HexEconomicState.
    """
    if not state.tenure_composition:
        return state

    tenure = state.tenure_composition
    actual_transferred = min(tenure.residential_owner_occupied, max(0.0, fraction_transferred))
    lost = actual_transferred * (1.0 - min(1.0, max(0.0, retention_rate)))
    if lost <= 0.0:
        return state

    updates = {"residential_owner_occupied": tenure.residential_owner_occupied - lost}
    if to_rental:
        updates["residential_rental"] = tenure.residential_rental + lost
    else:
        updates["vacant_abandoned"] = tenure.vacant_abandoned + lost

    new_tenure = tenure.model_copy(update=updates)
    return state.model_copy(update={"tenure_composition": new_tenure})


def apply_eminent_domain(
    state: HexEconomicState,
    fraction_taken: float,
    include_vacant: bool = True,
) -> HexEconomicState:
    """Apply a state confiscation (eminent domain) event to a hex.

    State ``DEVELOP`` / ``ADMINISTER`` actions (spec 032/039 OrgAction verbs)
    confiscate private land into ``public`` tenure. Displacement follows via
    :func:`evaluate_class_shares`: the owner-occupied share drop demotes
    LA households to Proletariat.
    """
    if not state.tenure_composition:
        return state

    tenure = state.tenure_composition
    pool = tenure.residential_owner_occupied + tenure.residential_rental
    if include_vacant:
        pool += tenure.vacant_abandoned
    if pool <= 0.0:
        return state

    actual_taken = min(pool, max(0.0, fraction_taken))
    if actual_taken <= 0.0:
        return state

    updates = {
        "residential_owner_occupied": tenure.residential_owner_occupied
        - actual_taken * (tenure.residential_owner_occupied / pool),
        "residential_rental": tenure.residential_rental
        - actual_taken * (tenure.residential_rental / pool),
        "public": tenure.public + actual_taken,
    }
    if include_vacant:
        updates["vacant_abandoned"] = tenure.vacant_abandoned - actual_taken * (
            tenure.vacant_abandoned / pool
        )

    new_tenure = tenure.model_copy(update=updates)
    return state.model_copy(update={"tenure_composition": new_tenure})


def apply_speculation(state: HexEconomicState, fraction_speculated: float) -> HexEconomicState:
    """Apply a speculative buy-out event to a hex.

    Exchange-value decouples from use-value: speculative capital prices
    households out of ownership, converting owner-occupied stock to
    landlord-held rental (the inverse of :func:`apply_purchase`). This is
    the setup phase for :func:`apply_gentrification`. Callers gate on
    :attr:`~babylon.economics.rent.types.HousingValueDecomposition.fictitious_fraction`
    exceeding a threshold (spec 024 FR-008/009).
    """
    if not state.tenure_composition:
        return state

    tenure = state.tenure_composition
    actual = min(tenure.residential_owner_occupied, max(0.0, fraction_speculated))
    if actual <= 0.0:
        return state

    new_tenure = tenure.model_copy(
        update={
            "residential_owner_occupied": tenure.residential_owner_occupied - actual,
            "residential_rental": tenure.residential_rental + actual,
        }
    )
    return state.model_copy(update={"tenure_composition": new_tenure})


def apply_gentrification(
    state: HexEconomicState,
    fraction_converted: float,
    commercial_ratio: float = 0.5,
) -> HexEconomicState:
    """Apply a gentrification event to a hex.

    Coordinated capital infusion converts rental stock into commercial
    property and owner-occupied housing (spec 043 transition table:
    rental -> commercial / owner_occupied). Tenants are displaced; the
    Proletariat land share shrinks via :func:`evaluate_class_shares`.
    """
    if not state.tenure_composition:
        return state

    tenure = state.tenure_composition
    actual = min(tenure.residential_rental, max(0.0, fraction_converted))
    if actual <= 0.0:
        return state

    ratio = min(1.0, max(0.0, commercial_ratio))
    new_tenure = tenure.model_copy(
        update={
            "residential_rental": tenure.residential_rental - actual,
            "commercial": tenure.commercial + actual * ratio,
            "residential_owner_occupied": tenure.residential_owner_occupied
            + actual * (1.0 - ratio),
        }
    )
    return state.model_copy(update={"tenure_composition": new_tenure})
```

Design rationale (document in the commit body): shares sum is conserved by construction in every branch; each transition is expressible purely in the frozen 7-share schema (spec forbids schema growth — the data model at `spec.md:40-64` is fixed); speculation = owner→rental because a distinct "speculative_hold" share does not exist in the schema and vacancy is semantically abandonment; retention/foreclosure coupling reuses `_CLASS_INHERITANCE_SCALE` semantics from `lifecycle/inheritance.py:92-98` at the CALLER, keeping the transition pure. `model_copy(update=...)` on frozen models skips re-validation (same as the 3 live transitions) — conservation holds arithmetically; tests assert it.

Also in this commit: export the whole transitions surface from `src/babylon/economics/substrate/__init__.py` — add `from babylon.economics.substrate.transitions import (apply_abandonment, apply_eminent_domain, apply_foreclosure, apply_gentrification, apply_inheritance, apply_purchase, apply_speculation, check_equity_threshold, evaluate_class_shares)` + a `# Tenure transitions (Feature 043)` group in `__all__`.

### Commit 2 — `feat(substrate): ground-rent x ValueTensor4x3 intersection`

**RED**: new `tests/unit/economics/substrate/test_tensor_intersection.py`. Build tensors with the `tensor.py:229-238` docstring example values. Cases: (1) v-deduction allocated proportionally to each department's v share (all depts v=100 → equal quarters); (2) s-deduction proportional to s shares; (3) conservation `adjusted.total_v == pytest.approx(total_v - deducted_from_v, abs=1e-6)` (**1e-6, LaborHours SnapToGrid quantization — NOT 1e-10**); (4) rent exceeding available v clamps: `deducted_from_v == total_v`, all dept v == 0; (5) `total_v == 0` tensor → `deducted_from_v == 0`, no NaN; (6) zero-rent identity (`_ZERO_RENT` from ground_rent.py:56-62 → adjusted equals input per-field); (7) result model frozen; (8) `fips_code`/`year`/`naics_granularity`/`excluded_wages`/`visibility_g33` pass through unchanged.

**GREEN**: extend `src/babylon/economics/substrate/ground_rent.py` (cohesion: the spec places this inside the Ground Rent Circuit section):

```python
class TensorRentIntersection(BaseModel):
    """Result of intersecting ground rent with a county value tensor.

    Implements the spec-043 ``ValueTensor4x3`` integration: residential
    rent intersects variable capital (the worker reproduction fund);
    commercial/industrial rent intersects surplus value (splitting it
    into profit of enterprise and ground rent).

    Args:
        adjusted: Rent-adjusted county tensor.
        deducted_from_v: Rent actually deducted from variable capital.
        deducted_from_s: Rent actually deducted from surplus value.
    """

    model_config = ConfigDict(frozen=True)

    adjusted: ValueTensor4x3
    deducted_from_v: float = Field(ge=0.0, description="Rent taken from v")
    deducted_from_s: float = Field(ge=0.0, description="Rent taken from s")


def intersect_rent_with_tensor(
    tensor: ValueTensor4x3,
    rent: GroundRentResult,
) -> TensorRentIntersection:
    """Intersect a ground rent extraction with a county 4x3 value tensor.

    ``rent_from_v`` is allocated across the four departments proportionally
    to each department's share of ``total_v``; ``rent_from_s`` proportionally
    to ``total_s``. Deductions clamp to available value (LaborHours >= 0).

    Args:
        tensor: County-year value tensor (spec 011 primitive).
        rent: Hex or county ground rent decomposition (FR-010).

    Returns:
        TensorRentIntersection with the adjusted tensor and the amounts
        actually deducted.
    """
    total_v = float(tensor.total_v)
    total_s = float(tensor.total_s)
    take_v = min(rent.rent_from_v, total_v)
    take_s = min(rent.rent_from_s, total_s)

    def _adjust(row: DepartmentRow) -> DepartmentRow:
        v_frac = row.v / total_v if total_v > 0.0 else 0.0
        s_frac = row.s / total_s if total_s > 0.0 else 0.0
        return DepartmentRow(
            c=row.c,
            v=max(0.0, row.v - take_v * v_frac),
            s=max(0.0, row.s - take_s * s_frac),
        )

    adjusted = tensor.model_copy(
        update={
            "dept_I": _adjust(tensor.dept_I),
            "dept_IIa": _adjust(tensor.dept_IIa),
            "dept_IIb": _adjust(tensor.dept_IIb),
            "dept_III": _adjust(tensor.dept_III),
        }
    )
    return TensorRentIntersection(adjusted=adjusted, deducted_from_v=take_v, deducted_from_s=take_s)
```

Imports to add: `from babylon.economics.tensor import DepartmentRow, ValueTensor4x3` (top-level is safe — `tensor.py` has no substrate imports; no cycle). Export both symbols from `ground_rent.py.__all__` and `substrate/__init__.py`. Note for executor: `DepartmentRow` construction re-validates (fresh model), so ge-0 and quantization are enforced; `tensor.model_copy` skips validation but every replaced field is a validated model — matches the live transitions' pattern.

### Commit 3 — `refactor(economics): retire static equity_factor scaler (spec-043)`

Surgical steps:

1. `src/babylon/config/defines/economy_class.py:194-195` — rewrite the Args docstring line to: "equity_factor: Absolute threshold test on the hex/county equity ratio ``s / (c + v + s)`` required for LA classification (Feature 043). Formerly a population-level numeric scaler." Keep field `:221-229` untouched (it is the live threshold consumed at `transitions.py:237`).
2. `src/babylon/economics/melt/wealth_proxy.py`:
   - Delete `EQUITY_FACTOR = 0.6` (`:159`) and the `equity_factor: float | None` `__init__` param (`:242`, docstring `:251-253`) and priority chain (`:265-271`). Keep `class_system_defines` (still supplies `trust_land_discount` AND now the threshold).
   - Add a per-FIPS equity-ratio reference dict alongside `_HOMEOWNERSHIP_BY_FIPS` (`:172-181`), same mock-data pattern with the same "In production, this would come from data loaders" caveat, e.g. `_EQUITY_RATIO_BY_FIPS: dict[str, float] = {"26163": 0.12, "26125": 0.68, ...}` (Wayne below the 0.6 default threshold, Oakland above — encodes the spec's Detroit falsifiability case `spec.md:113`), plus an `equity_ratio_data: dict[str, float] | None = None` constructor override.
   - Re-implement `estimate_la_share` body (keep the `DeprecationWarning` `:317-326` and the `.. deprecated::` block — hex-resolution work should use substrate transitions):
     ```python
     homeownership = self.get_homeownership_rate(fips, year)
     if homeownership is None:
         return self.NATIONAL_LA_SHARE
     effective = self._effective_homeownership(fips, homeownership)
     equity_ratio = self._equity_ratio.get(fips)
     if equity_ratio is None:
         return self.NATIONAL_LA_SHARE
     if equity_ratio >= self._class_defines.equity_factor:
         return effective
     return 0.0
     ```
     This is the VIII.1-compliant discrete switch: full owner share constitutes LA when the threshold is met; nominal title without equity constitutes none.
   - Update module docstring `:15-33` (drop the "homeownership_rate * equity_factor" formula and the "EQUITY_FACTOR = 0.6 calibrated" block; describe the threshold test) and the class docstring examples `:144-156` (values change: e.g. Oakland → 0.78, Wayne → 0.0 under the reference ratios).
   - `get_class_distribution_estimate` (`:450-515`) needs no code change (inherits new semantics through `:486`) but its docstring's "LA = estimated from homeownership proxy" line should say "threshold-gated homeownership share".
3. Tests (read each before editing — expectations, not code under test):
   - `tests/unit/economics/melt/test_wealth_proxy.py:214-246` (scaler math) → rewrite as threshold tests: above-threshold returns owner share; below-threshold returns 0.0; missing equity data returns `NATIONAL_LA_SHARE`.
   - `:420-471` (T018 defines-priority) → now: `ClassSystemDefines(equity_factor=X)` moves the cut-line (construct two calculators around a fixed equity ratio, assert flip); the "explicit equity_factor overrides defines" test (`:436-449`) is deleted with the parameter.
   - `tests/unit/economics/melt/test_county_classification.py:319-320` — Oakland (0.78) > Wayne (0.0) still holds; verify surrounding assertions.
   - `tests/unit/economics/melt/test_class_position.py:729-768` — `get_class_distribution_estimate` distribution tests; re-check sums-to-1 invariants survive LA=0.0 for Wayne (bottom_share absorbs; code path `:488-507` already handles it).

### Optional wiring note (NOT in this branch without owner sign-off)

Real tenure hydration exists in the reference DB: `fact_census_housing` (`src/babylon/reference/schema.py:1094-1113`) has 1,351,380 rows; tri-county owner/renter/total × 2010–2023 verified present (e.g. 26163/2023 owner=1,189,638, renter=585,628). **Join via `dim_county.fips` (5-digit), NOT `dim_county.county_fips` (3-digit)** — a query against `county_fips IN ('26163',...)` silently returns 0 rows. ACS gives only the owner/renter residential split; commercial/industrial/public/trust/vacant have no reference source — hydration would need an allocation rule (design decision). Wiring tenure into `hydrate_hex_grid` + passing `rent_defines` into `equalize_capital` callers would change sim outputs and therefore requires an R-PROOF regen per the remediation plan's rules; the 6.3 scope as written does not require it.

---

## C. Verification

```bash
# per-commit red/green
poetry run pytest tests/unit/economics/substrate/test_transitions.py -vv
poetry run pytest tests/unit/economics/substrate/test_tensor_intersection.py -vv
poetry run pytest tests/unit/economics/substrate/ -m "not ai"          # whole substrate suite (13 files)
poetry run pytest tests/unit/economics/melt/test_wealth_proxy.py tests/unit/economics/melt/test_class_position.py tests/unit/economics/melt/test_county_classification.py -vv
# or the agent loop with cached --lf:
mise run test:q -- tests/unit/economics/substrate/
mise run test:failed
# strict gates
poetry run mypy src/babylon/economics/substrate/ src/babylon/economics/melt/wealth_proxy.py --strict
mise run check                       # lint + format + typecheck + test:unit
mise run qa:regression               # must be UNCHANGED (see baseline note)
```

**Baseline-impact note**: this branch is baseline-neutral by construction. The substrate transition/rent path never executes in canonical runs (`services.hex_grid` never injected — `services.py:104`; `equalize_capital`'s only production caller is `tools/demo_substrate.py:170` without `rent_defines`; `hydrate_hex_grid` never sets tenure), and `estimate_la_share` has no runtime caller beyond the DI registration at `protocol_kit.py:256`. `mise run qa:regression` and the 520-tick trace should be byte-identical; no 2.R-style regen or proof.md is required. If the optional tenure-hydration wiring is added, that flips: R-PROOF becomes mandatory.

Known unrelated red at HEAD (do not chase): `mise run test:doctest` broken repo-wide (models→formulas.balkanization circular import); unit suite had a 0027/0028 migration conflict on Postgres-touching tests per MEMORY.md — substrate/melt tests are pure in-memory and unaffected.
