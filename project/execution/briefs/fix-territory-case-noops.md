# Implementation Brief: fix/territory-case-noops

Two of the 26 default engine systems — `ReserveArmySystem` (position 5) and `DispossessionEventSystem` (position 10) — are silent no-ops in every production run because they filter for node type `"Territory"` (capitalized) while `WorldState.to_graph()` writes `_node_type="territory"` (lowercase) and the query filter is an exact string comparison. Their own tests pass because the fixtures hand-seed the wrong case. Additionally, fixing the case alone is NOT safe: both systems write attributes that are not `Territory` model fields into an `extra="forbid"` model, so the per-tick `from_graph()` round-trip would raise `ValidationError` the moment either system actually fires. This brief covers the case fix, the model-field/exclusion-set decisions, the fixture rebuild, RED-first tests, and baseline verification. All lines verified against `chore/test-infra-rearm` @ 9101dddf.

---

## 1. Verified seams (current code, exact lines)

### 1a. The wrong-case filters

`src/babylon/engine/systems/reserve_army.py:59`
```python
        for node in list(protocol.query_nodes(node_type="Territory")):
```

`src/babylon/engine/systems/dispossession_events.py:61`
```python
        for node in list(protocol.query_nodes(node_type="Territory")):
```

### 1b. What to_graph actually writes

`src/babylon/models/world_state.py:371-405` — all six node-type markers are lowercase snake_case:
```python
        # Add entity nodes with _node_type marker
        for entity_id, entity in self.entities.items():
            G.add_node(entity_id, _node_type="social_class", **entity.model_dump())

        # Add territory nodes with _node_type marker
        for territory_id, territory in self.territories.items():
            G.add_node(territory_id, _node_type="territory", **territory.model_dump())
```
(also `"organization"` :381, `"key_figure"` :389, `"institution"` :393, `"industry"` :405)

### 1c. The exact-match filter

`src/babylon/engine/adapters/query_mixin.py:50-56` (BabylonGraph inherits `QueryMixin` — `src/babylon/engine/graph.py:551` `class BabylonGraph(_GraphCore, AggregationMixin, QueryMixin):`):
```python
        for node_id in self._graph.nodes:
            data = dict(self._graph.nodes[node_id])
            n_type = data.pop("_node_type", "unknown")

            # Type filter
            if node_type and n_type != node_type:
                continue
```
`"Territory" != "territory"` → zero matches → both `step()` bodies never execute their loop.

### 1d. The per-tick round-trip that makes non-model writes fatal

Both production paths reconstruct `WorldState` from the graph EVERY tick:
- Facade: `src/babylon/engine/simulation_engine.py:698` (`G = state.to_graph()`) → `:718` (`_DEFAULT_ENGINE.run_tick(G, services, context)`) → `:752-757` (`return WorldState.from_graph(G, ...)`).
- Bridged headless runner: `src/babylon/engine/headless_runner/runner.py:377-378` (`engine.run_tick(graph, services, context)` then `world = WorldState.from_graph(graph, tick=tick)`) and `:1050` (`graph = world.to_graph()` per tick).

`from_graph` territory branch: `src/babylon/models/world_state.py:489-490` → `_reconstruct_territory` at `:153-162`:
```python
def _reconstruct_territory(node_data: dict[str, Any]) -> Territory:
    """Reconstruct a Territory from graph node data."""
    territory_data = {k: v for k, v in node_data.items() if k not in TERRITORY_EXCLUDED_FIELDS}
    ...
    return Territory(**territory_data)
```

`Territory` config, `src/babylon/models/entities/territory.py:50-54`:
```python
    model_config = ConfigDict(
        extra="forbid",  # Reject unknown fields
        frozen=True,  # Spec 056 / Constitution III.7 — immutable state
        str_strip_whitespace=True,  # Clean string inputs
    )
```

Both systems are registered in `_DEFAULT_SYSTEMS`: `src/babylon/engine/simulation_engine.py:331` (`ReserveArmySystem(),  # 5.`) and `:336` (`DispossessionEventSystem(),  # 10.`).

**Doc drift note**: both system docstrings claim stale positions — `reserve_army.py:33` says "Position: #17" and `dispossession_events.py:33` says "Position: #18". Actual positions are 5 and 10 (also stated in the modules' own line-1 docstrings, which are equally stale: "System #17"/"System #18"). Fix these docstrings in passing since you are editing both files anyway.

---

## 2. Attribute inventory: every non-model attr the two systems touch, with the decision

Current `Territory` model fields (`territory.py:57-146`): `id`, `h3_index`, `name`, `sector_type`, `territory_type`, `host_id`, `occupant_id`, `profile`, `heat`, `rent_level`, `population`, `under_eviction`, `biocapacity`, `max_biocapacity`, `regeneration_rate`, `extraction_intensity`. Nothing else. (`SocialClass` DOES have `wealth: Currency = Field(default=10.0, ...)` at `social_class.py:57`/`:308` — territory `wealth` is a NEW concept.)

Current `TERRITORY_EXCLUDED_FIELDS` (`world_state.py:73-87`):
```python
TERRITORY_EXCLUDED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "p_acquiescence",
        "p_revolution",
        "dpd_state",
        "dependency_ratio",
        "legitimation_index",
        "legitimation_crisis",
        "legitimation_state",
        "mobility_params",
        "adjusted_p_to_d_prime",
        "transmitted_ideology",
        "differential_p_to_d_prime",
    }
)
```

### ReserveArmySystem (`reserve_army.py`)
| Attr | Access | Lines | Decision | Rationale |
|---|---|---|---|---|
| `reserve_ratio` | read + re-written | :63, :80 | **model field** | Loader/scenario input; must survive the per-tick round-trip or the system permanently re-no-ops from tick 2 |
| `median_wage` | read + written | :82-84 | **model field** | Mutated multiplicatively; the integration test `test_multi_tick_wage_suppression_compounds` requires cross-tick compounding, which only model fields survive |
| `wage_pressure` | written | :79 | **exclusion set** | Per-tick computed output, recomputed every tick — exact analog of the existing `p_acquiescence`/`p_revolution` exclusions |

### DispossessionEventSystem (`dispossession_events.py`)
| Attr | Access | Lines | Decision | Rationale |
|---|---|---|---|---|
| `wealth` | read + written | :90, :97 | **model field** (`Currency`, default 0.0) | Mutated persistent state (`wealth=territory_wealth - transfer_amount`); must persist |
| `dispossession_intensity` | written | :114 | **exclusion set** | Per-tick computed output |
| `foreclosure_rate` | read only | :66 | **model field** (float [0,1], default 0.0) | Input; must survive round-trip to drive the system |
| `eviction_rate` | read only | :67 | **model field** | same |
| `displacement_rate` | read only | :68 | **model field** | same |
| `concentrated_ownership` | read only | :83 | **model field** | same |
| `absentee_landlord_share` | read only | :84 | **model field** | same |
| `fips_code` | read only, fallback `"00000"` | :78 | **leave as `.get()` fallback** | Only feeds `TerritoryDispossessionState` provenance; never written by the system; `Territory` already carries `h3_index`, and `county_fips` lives on `SocialClass` (`social_class.py:403`). Don't seed it in fixtures. |
| `year` | read only, fallback `2010` | :79 | **leave as `.get()` fallback** | same |

Why zero defaults are safe: with `reserve_ratio=0.0` the system hits `if reserve_ratio <= 0.0: continue` (`reserve_army.py:68-69`); with all three rates 0.0 it hits `if foreclosure_rate <= 0.0 and eviction_rate <= 0.0 and displacement_rate <= 0.0: continue` (`dispossession_events.py:71`). So existing scenarios (which set none of these) produce byte-identical behavior — the systems become *activatable*, not *active*.

Note: nothing in production currently seeds these inputs onto graph nodes. `hydrate_class_shares` (`src/babylon/engine/hydration/reference.py:222`) computes `median_wage` etc. but has NO callers outside its own `__init__.py` export; `TickDynamicsSystem` wage-pressure math runs on `CountyEconomicState` objects, not graph territory nodes (`src/babylon/economics/tick/system/__init__.py:891-899`). Wiring a data source is out of scope for this branch (that is the "wire the dormant sim" phase); this branch makes the systems correct and activatable.

---

## 3. Conservation gate (INV-001) — no change needed

`DispossessionEventSystem.creates_value: ClassVar[bool] = True` (`dispossession_events.py:39`) and it is already in the four-system opt-out set asserted by `tests/property/invariants/test_value_conservation.py:255-262` (`ImperialRentSystem, StruggleSystem, DispossessionEventSystem, DecompositionSystem`). `ReserveArmySystem.creates_value = False` (`reserve_army.py:37`) and it touches no hex `c+v+s`. Un-no-oping trips no conservation sentinel. Do not touch the markers.

---

## 4. Systems sweep result: no other case bug

Every other `query_nodes(node_type=...)` call in `src/babylon/engine/systems/` uses lowercase and matches a real writer: `"territory"` (faction_influence.py:90, lifecycle.py:72, production.py:248, sovereignty.py:83, territory.py:115/225/324, metabolism.py:89/111), `"social_class"` (field_derivative, community, control_ratio, contradiction_field, struggle, production, vitality, reactionary, ideology, decomposition, economic, metabolism), `"hex"` (substrate.py:71, territory_diagnostics.py:70, vol2_circulation.py:163), `"sovereign"` (collapse_transition.py:68/270, faction_influence.py:202), `"organization"` (community.py:393), `"balkanization_faction"` (faction_influence.py:164/200, reactionary.py:215). The two claimed systems are the ONLY offenders.

Not bugs (do not touch):
- `tests/unit/engine/test_system_order.py:56/:100` — `"Territory"` there is the SYSTEM name (`TerritorySystem.name == "Territory"`, asserted at `tests/unit/engine/systems/test_territory_system.py:37`), not a node type.
- `tests/unit/persistence/test_postgres_runtime.py:162/:175/:1138` — `"Territory"` is a freeform `"type"` label in a persistence-payload test using a private `_build_graph` helper; the persistence layer is type-agnostic.
- `src/babylon/engine/event_evaluator.py:318-336` — `NodeFilter.matches()` consumes `_node_type` from data dicts; filter values come from event-template data, and no capitalized usage was found.

---

## 5. Test fixtures that mask the bug (must be rebuilt via to_graph)

1. `tests/unit/engine/systems/test_reserve_army_system.py:19` — `attrs.setdefault("_node_type", "Territory")` in `_make_territory_graph`; also `:104` seeds `_node_type="SocialClass"` (also wrong case — to_graph writes `"social_class"`). 201 lines, 10 tests.
2. `tests/unit/engine/systems/test_dispossession_event_system.py:20` — same `setdefault("_node_type", "Territory")` plus `fips_code`/`year` seeding at :21-22; `:179` seeds `_node_type="SocialClass"`. 247 lines, 9 tests.
3. `tests/integration/test_volume_i_integration.py:30/:46/:62` — `_node_type="Territory"` in `_make_detroit_graph` (wayne/oakland/macomb, 263 lines; classes `TestReserveArmyWageFeedback`, `TestDispossessionValueTransfer`, `TestCombinedFeedbackLoop` all use the graph fixture; `TestExploitationModeVisibility` is graph-free — leave it alone).

**There are NO skipped/xfailed tests to un-skip** — `rg -i 'skip.*(reserve|disposs)'` over tests/ returns nothing. The masking is entirely via wrong-case fixtures, so the remediation is fixture rebuild, not un-skipping.

Fixture rebuild constraint: `Territory.id` must match `^(T[0-9]{3,}|[0-9a-f]{15})$` (`territory.py:59`), so the current node ids `"wayne"`/`"oakland"`/`"macomb"` are ILLEGAL as Territory ids. Rename to `T001`/`T002`/`T003` with `name="Wayne County"` etc., and update every `graph.nodes["wayne"]` assertion. `SocialClass.id` must match `^C[0-9]{3}$` (use `"C001"`). The established to_graph-fixture style to copy is `tests/unit/engine/systems/test_reactionary_crisis.py:40`: `graph = WorldState(tick=0, entities={"C001": la}).to_graph()`.

Rebuilt helper sketch (both unit files + integration file, matching surrounding style):
```python
from babylon.models import SocialClass, Territory, WorldState
from babylon.models.enums import SectorType, SocialRole


def _make_territory_graph(
    territories: dict[str, dict[str, float]],
) -> BabylonGraph:
    """Build a to_graph-shaped test graph with territory nodes.

    Nodes carry the exact ``_node_type="territory"`` marker production
    writes (world_state.py to_graph) — hand-seeded markers previously
    masked the Feature-021 case bug.
    """
    state = WorldState(
        tick=0,
        territories={
            node_id: Territory(
                id=node_id,
                name=f"County {node_id}",
                sector_type=SectorType.RESIDENTIAL,
                **attrs,
            )
            for node_id, attrs in territories.items()
        },
    )
    return state.to_graph()
```
Call sites become e.g. `_make_territory_graph({"T001": {"reserve_ratio": 0.15, "median_wage": 1000.0}})`. Drop the `import networkx as nx` / `-> nx.DiGraph[str]` return annotations while rewriting the helpers (annotate `-> BabylonGraph`); ruff will flag the now-unused nx import (your change created the orphan — remove it). In the dispossession file, DROP the `fips_code`/`year` seeding (the system's `.get()` fallbacks cover them and no test asserts them). `test_skips_non_territory_nodes` in both files: build via `WorldState(tick=0, entities={"C001": SocialClass(id="C001", name="Worker", role=SocialRole.WORKER, wealth=500.0)}).to_graph()` then seed the decoy attrs with `graph.update_node("C001", reserve_ratio=0.15, median_wage=500.0)` (`update_node` merges attrs — `graph.py:656-665`; social_class nodes tolerate extras because `SOCIAL_CLASS_COMPUTED_FIELDS` filtering plus these tests never call from_graph — but keep the seeding minimal). For `_make_detroit_graph` in the integration file, construct three `Territory` models carrying the new model fields (reserve_ratio/median_wage/wealth/foreclosure_rate/eviction_rate/displacement_rate/concentrated_ownership/absentee_landlord_share) with the same values currently at lines 28-73, minus fips_code/year.

---

## 6. Implementation steps (TDD order)

### Step 1 — RED: new test module `tests/unit/engine/systems/test_feature021_territory_roundtrip.py`

Write these five tests first; run them; ALL must fail on current code (mark `@pytest.mark.red_phase` per project convention, remove the marker at GREEN):

```python
"""Feature 021 territory-case fix: systems act on to_graph-shaped graphs.

RED-first tests for the node_type case bug (reserve_army.py:59,
dispossession_events.py:61 queried "Territory"; to_graph writes
"territory") and the extra="forbid" round-trip latch.
"""

from __future__ import annotations

from babylon.engine.services import ServiceContainer
from babylon.engine.systems.dispossession_events import DispossessionEventSystem
from babylon.engine.systems.reserve_army import ReserveArmySystem
from babylon.models import Territory, WorldState
from babylon.models.enums import SectorType


def _wayne_state() -> WorldState:
    """WorldState whose to_graph output carries Feature-021 inputs."""
    return WorldState(
        tick=0,
        territories={
            "T001": Territory(
                id="T001",
                name="Wayne County",
                sector_type=SectorType.RESIDENTIAL,
                reserve_ratio=0.18,
                median_wage=45000.0,
                wealth=500_000_000.0,
                foreclosure_rate=0.08,
                eviction_rate=0.05,
                displacement_rate=0.03,
            ),
        },
    )


class TestTerritoryFeature021Fields:
    def test_territory_accepts_feature021_inputs(self) -> None:
        """Territory model carries the Feature-021 input fields."""
        t = _wayne_state().territories["T001"]
        assert t.reserve_ratio == 0.18
        assert t.median_wage == 45000.0


class TestReserveArmyOnProductionGraph:
    def test_mutates_to_graph_shaped_territory(self) -> None:
        """The system matches lowercase _node_type='territory' nodes."""
        graph = _wayne_state().to_graph()
        ReserveArmySystem().step(graph, ServiceContainer.create(), {"tick": 1})

        assert graph.nodes["T001"]["median_wage"] < 45000.0
        assert graph.nodes["T001"]["wage_pressure"] > 0.0

    def test_round_trip_survives_and_persists_wage(self) -> None:
        """from_graph neither crashes nor loses the mutated wage."""
        graph = _wayne_state().to_graph()
        ReserveArmySystem().step(graph, ServiceContainer.create(), {"tick": 1})

        state = WorldState.from_graph(graph, tick=1)  # must NOT raise
        assert state.territories["T001"].median_wage < 45000.0
        # computed output is per-tick: dropped on reconstruction
        assert not hasattr(state.territories["T001"], "wage_pressure")


class TestDispossessionOnProductionGraph:
    def test_mutates_to_graph_shaped_territory(self) -> None:
        graph = _wayne_state().to_graph()
        DispossessionEventSystem().step(graph, ServiceContainer.create(), {"tick": 1})

        assert graph.nodes["T001"]["wealth"] < 500_000_000.0
        assert graph.nodes["T001"]["dispossession_intensity"] > 0.0

    def test_round_trip_survives_and_persists_wealth(self) -> None:
        graph = _wayne_state().to_graph()
        DispossessionEventSystem().step(graph, ServiceContainer.create(), {"tick": 1})

        state = WorldState.from_graph(graph, tick=1)  # must NOT raise
        assert state.territories["T001"].wealth < 500_000_000.0
```

Also add one full-loop compounding test (the real production seam — `step()` round-trips every tick):
```python
class TestFullTickLoop:
    def test_wage_suppression_compounds_across_step_round_trips(self) -> None:
        """simulation_engine.step to_graph→systems→from_graph preserves compounding."""
        from babylon.engine.simulation_engine import step
        from babylon.models import SimulationConfig

        state = _wayne_state()
        config = SimulationConfig()
        wages = [state.territories["T001"].median_wage]
        for _ in range(3):
            state = step(state, config)
            wages.append(state.territories["T001"].median_wage)
        assert wages[0] > wages[1] > wages[2] > wages[3] > 0.0
```
(Check `SimulationConfig()` constructs bare in other engine tests before copying; if it needs args, mirror whatever `tests/unit/engine/` already does. `step()` will run all 26 systems, which is the point — this proves no OTHER system chokes on the new territory attrs.)

Expected RED failures on current code: the `Territory(...)` construction itself raises `ValidationError` (extra="forbid" rejects `reserve_ratio` etc.) — that is the correct first RED signal; after Step 3 adds fields but before Step 2 fixes the case, the mutation assertions fail with unchanged values, isolating the filter bug. Land Steps 2+3+4 together as one GREEN.

### Step 2 — GREEN: the one-word fixes

`src/babylon/engine/systems/reserve_army.py:59`:
```python
        for node in list(protocol.query_nodes(node_type="territory")):
```
`src/babylon/engine/systems/dispossession_events.py:61`: identical change. Also correct the stale "Position: #17"/"#18" docstrings (both files, module docstring line 1 and class docstring ~line 33) to positions 5 and 10.

### Step 3 — GREEN: Territory model fields

`src/babylon/models/entities/territory.py` — append after `extraction_intensity` (line 146), matching the local `float Field(ge/le)` style used by `regeneration_rate`/`extraction_intensity` and the `Currency` style used by `biocapacity`:
```python
    # Feature 021 (Capital Volume I) — labor-market and dispossession state.
    # Inputs are scenario/loader-seeded; ReserveArmySystem (#5) and
    # DispossessionEventSystem (#10) read and mutate them each tick. Zero
    # defaults keep both systems inert unless a scenario seeds them.
    median_wage: Currency = Field(
        default=0.0,
        description="Median wage paid in this territory (reserve-army pressure target)",
    )
    reserve_ratio: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of labor force in the reserve army [0, 1]",
    )
    wealth: Currency = Field(
        default=0.0,
        description="Aggregate territory wealth (dispossession value-transfer source)",
    )
    foreclosure_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Foreclosure rate feeding dispossession intensity [0, 1]",
    )
    eviction_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Eviction rate feeding dispossession intensity [0, 1]",
    )
    displacement_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Displacement rate feeding dispossession intensity [0, 1]",
    )
    concentrated_ownership: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Ownership concentration index [0, 1]",
    )
    absentee_landlord_share: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Absentee landlord share of rental stock [0, 1]",
    )
```
Also extend the class docstring `Attributes:` block (Sphinx-compatible RST is mandatory).

### Step 4 — GREEN: exclusion-set additions

`src/babylon/models/world_state.py:73-87` — add to `TERRITORY_EXCLUDED_FIELDS`:
```python
        # Feature 021 per-tick computed outputs (ReserveArmySystem #5,
        # DispossessionEventSystem #10) — recomputed every tick, never
        # Territory model fields (extra="forbid" would reject them).
        "wage_pressure",
        "dispossession_intensity",
```
The Spec-055 round-trip property test reads this set from production at runtime (`tests/property/invariants/test_round_trip_identity.py:36-56` `_build_exclude_paths_from_production`), so it self-updates — no edit needed there.

### Step 5 — Fixture rebuild (section 5 above)
Rewrite `_make_territory_graph` in both unit files and `_make_detroit_graph` in the integration file via `WorldState(...).to_graph()`. All 19 graph-based tests in those files must stay green with only id renames (`wayne`→`T001` etc.) and the fips/year removal. Values (0.15/0.20/0.05/0.99 ratios, 1000.0 wages, wealth figures) are inline per the tests/constants.py doctrine — they are scenario-local, keep them inline.

### Step 6 — Optional but recommended: extend the Hypothesis territory strategy
`tests/property/strategies/primitives.py:83-109` (`territory_strategy` uses `st.builds(Territory, ...)` with explicit kwargs). Add the 8 new fields so round-trip identity actually exercises them:
```python
        median_wage=_currency(),
        reserve_ratio=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        wealth=_currency(),
        foreclosure_rate=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        eviction_rate=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        displacement_rate=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        concentrated_ownership=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        absentee_landlord_share=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
```

### Step 7 — ai-docs update
Per repo CLAUDE.md: note in `ai-docs/state.yaml` that the two Feature-021 systems are live-able (case bug fixed, from_graph latch defused); the CLAUDE.md engine table needs no change (positions 5/10 already correct there).

---

## 7. Baseline impact and how qa:regression works

Baselines in `tests/baselines/`: `two_node.json`, `imperial_circuit.json`, `starvation.json`, `glut.json`, `fascist_bifurcation.json`, `mutation_baseline.json` (consumed by `mise run qa:regression` → `poetry run python tools/regression_test.py compare`, `.mise.toml:562-564`), plus `detroit-tri-county-5t.json` + `michigan-e2e.json` (`qa:e2e-regression` → `regression_test.py compare-bundle`, compares `summary.json` aggregates: `counties_alive` exact, `total_v` ±1% — `tools/regression_test.py:515-556`) and `storage-budget-5t.json` (rows/tick, `qa:storage-budget`).

**Expected drift: ZERO.** Reasons, all verified:
- The `regression_test.py` scenarios (`create_imperial_circuit_scenario`, `create_two_node_scenario` + parameter-injected variants) contain NO territories (`rg territor src/babylon/engine/scenarios/imperial_circuit.py two_node.py` → empty), so the two systems iterate nothing either way.
- Where territories DO exist (bridged runner), the new fields default to 0.0 → both systems early-`continue` (`reserve_army.py:68-69`, `dispossession_events.py:71`) → no writes, no events.
- The determinism hash is `sha256(f"{session_id}:{tick}:{config.random_seed}")` (`runner.py:1313-1315`) — node attributes are not hashed, so the enlarged `model_dump()` surface cannot drift it.

Therefore: do NOT run `qa:regression-generate`. Run `mise run qa:regression` and require PASS with the existing baselines — a failure means a real behavior change and you must stop and investigate, not regenerate (baseline regen is reserved for the separate coordinated Phase 2.R).

---

## 8. Verification commands (in order)

```bash
# RED (before any src change) — all new tests must fail
poetry run pytest tests/unit/engine/systems/test_feature021_territory_roundtrip.py -vv

# GREEN — the fix + fixtures
poetry run pytest tests/unit/engine/systems/test_feature021_territory_roundtrip.py \
  tests/unit/engine/systems/test_reserve_army_system.py \
  tests/unit/engine/systems/test_dispossession_event_system.py -vv
poetry run pytest tests/integration/test_volume_i_integration.py -vv

# Round-trip + conservation property gates (exclusion-set and creates_value sentinels)
poetry run pytest tests/property/invariants/test_round_trip_identity.py -vv
poetry run pytest tests/property/invariants/test_value_conservation.py -vv

# Strict typing on every touched file
poetry run mypy src/babylon/engine/systems/reserve_army.py \
  src/babylon/engine/systems/dispossession_events.py \
  src/babylon/models/entities/territory.py \
  src/babylon/models/world_state.py --strict

# Zero-drift proof + fast gate
mise run qa:regression
mise run check

# Commit (hook-safe)
mise run commit -- "fix(engine): lowercase territory node-type filter un-no-ops ReserveArmy + DispossessionEvents (Feature 021)"
```
(Or `mise run test:q -- <path>` for the scoped runs — it keeps the cache so `mise run test:failed` re-runs only failures.)

Known unrelated RED at dev HEAD (do not chase): `tests/integration/economics/` has ~34 NoDataSentinel data-availability failures, and the pre-rearm unit suite had a 0027/0028 migration conflict (being fixed on this very `chore/test-infra-rearm` base). Scope your green-gate to the commands above plus `mise run check`.
