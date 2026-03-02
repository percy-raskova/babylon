# Contract: Territory Effects

**Spec**: FR-E01, FR-E02, FR-E03, FR-E04, FR-E06, FR-E08, FR-E09
**Module**: `src/babylon/engine/state_ai/territory_integration.py` (DEVELOP/WITHDRAW resolve functions)
**Pattern**: GraphProtocol mutation via `update_node()` / `remove_edge()`, frozen Pydantic models, all thresholds from `StateApparatusAIDefines`

## Behavioral Contracts

### BC-TE-001: INVEST Increases Territory Economic Value

**Given**: A territory node `T001` with `property_value_proxy` at baseline (e.g., 1.0) and a `StateAction` with `verb=DEVELOP`, `sub_verb=INVEST`, `parameters={"sector": "COMMERCIAL"}` targeting `T001`.

**When**: The INVEST action is resolved for 8 consecutive ticks against `T001`, each tick applying the configurable `StateApparatusAIDefines.invest_property_delta` increment.

**Then**:
- `property_value_proxy` on `T001` has increased by at least `8 * defines.invest_property_delta` from baseline
- `V_reproduction` for any `SocialClass` node connected to `T001` via `TENANCY` edge has increased (higher property values raise cost of living)
- A `TERRITORY_INVESTED` event is emitted via `EventBus` each tick the action resolves
- The territory's `rent_level` has increased proportionally to the `property_value_proxy` change

**Invariant**: `property_value_proxy` is monotonically non-decreasing while INVEST actions continue. INVEST never decreases economic value.

**Rationale** (FR-E08, SC-008): INVEST is the first stage of the gentrification circuit. Rising property values create displacement pressure. The economic pipeline reads `property_value_proxy` from territory nodes to compute `V_reproduction`, so the effect propagates automatically to survival calculus.

**Test Signature**:
```python
def test_invest_increases_property_value_proxy(self) -> None:
    """BC-TE-001: 8 ticks of INVEST raises property_value_proxy by at least 8 * delta."""
    ...
```

---

### BC-TE-002: NEGLECT Degrades Territory Infrastructure

**Given**: A territory node `T001` with `infrastructure_quality` at baseline 0.8 and no active INVEST or DEVELOP actions. A `StateAction` with `verb=DEVELOP`, `sub_verb=NEGLECT` targeting `T001`.

**When**: The NEGLECT action is applied for 12 consecutive ticks, each tick applying exponential decay: `infrastructure_quality *= (1.0 - defines.neglect_decay_rate)`.

**Then**:
- `infrastructure_quality` has decreased from 0.8 following the decay curve: `0.8 * (1.0 - defines.neglect_decay_rate) ** 12`
- `infrastructure_quality` does NOT fall below `defines.neglect_quality_floor` (the configurable floor prevents reaching zero)
- `property_value_proxy` has declined (degraded territory loses economic value)
- Territory services (education, healthcare, transit quality indicators) have degraded proportionally to infrastructure quality loss
- A `TERRITORY_NEGLECTED` event is emitted via `EventBus` each tick

**Invariant**: `infrastructure_quality >= defines.neglect_quality_floor` at all times. The floor is a hard lower bound that NEGLECT cannot breach.

**Worked Example**: With `neglect_decay_rate=0.05` and `neglect_quality_floor=0.1`:
- After 12 ticks: `0.8 * (0.95)^12 = 0.431` (infrastructure nearly halved)
- After 40 ticks: `0.8 * (0.95)^40 = 0.107` (approaches floor but does not breach it)

**Rationale** (FR-E08, SC-008): NEGLECT is low-visibility (minimal legitimacy cost) but cumulatively devastating. It models the systematic disinvestment pattern — Flint, Detroit's neighborhoods, the South Bronx. NEGLECT followed by INVEST creates the disinvestment-reinvestment gentrification cycle.

**Test Signature**:
```python
def test_neglect_degrades_infrastructure_with_floor(self) -> None:
    """BC-TE-002: 12 ticks of NEGLECT decays infrastructure but respects quality floor."""
    ...
```

---

### BC-TE-003: DISPLACE Removes Population and Severs TENANCY Edges

**Given**: A territory node `T001` with `population=1000` and 5 `TENANCY` edges connecting population blocks (SocialClass nodes) to `T001`. Community infrastructure exists in `T001` with `collective_identity=0.6` on the associated community hyperedge. A `StateAction` with `verb=DEVELOP`, `sub_verb=DISPLACE`, `parameters={"mechanism": "RENT_INCREASE"}` targeting `T001`.

**When**: The DISPLACE action resolves against `T001`.

**Then**:
- At least `floor(1000 * defines.displace_population_fraction)` population is removed from `T001` (default fraction: 0.5, so at least 500 displaced)
- TENANCY edges between displaced population blocks and `T001` are severed via `graph.remove_edge()`
- `community_infrastructure_quality` in the territory decreases (displacement scatters the organized community)
- `collective_identity` on the affected community hyperedge decreases (FR-E06: eviction as consciousness disruption)
- Displaced population blocks are relocated to adjacent territories (determined by ADJACENCY edges, affordability via `rent_level`, and existing community presence). If no affordable adjacent territory exists, population enters a DISPLACED state
- A `TERRITORY_DISPLACED` event is emitted via `EventBus` with metadata including the count of displaced population and the displacement mechanism

**Edge Case (EC-003)**: If `T001` has `population=0` (empty territory), DISPLACE produces no displacement. However, any economic effects from the displacement mechanism (e.g., RENT_INCREASE still raises `rent_level`) still apply.

**Rationale** (FR-E03, FR-E06, FR-E08): DISPLACE is the kinetic component of the gentrification circuit. It severs community infrastructure, scatters organized populations, and disrupts collective identity. It makes DISPLACE a strategic weapon against organizational growth distinct from direct REPRESS actions.

**Test Signature**:
```python
def test_displace_severs_tenancy_edges_and_reduces_population(self) -> None:
    """BC-TE-003: DISPLACE removes population, severs TENANCY, degrades community."""
    ...
```

---

### BC-TE-004: STRATEGIC_WITHDRAWAL Removes PRESENCE Edges and Hollows Territory

**Given**: A territory node `T001` with:
- 2 `PRESENCE` edges connecting `StateApparatus` organization nodes to `T001`
- `infrastructure_quality=0.7`
- `state_investment > 0` (active state investment in the territory)
- Population blocks connected via `TENANCY` edges

A `StateAction` with `verb=WITHDRAW`, `sub_verb=STRATEGIC_WITHDRAWAL`, `parameters={"asset_extraction": true}` targeting `T001`.

**When**: The STRATEGIC_WITHDRAWAL action resolves against `T001`.

**Then**:
- All `PRESENCE` edges between `StateApparatus` nodes and `T001` are removed via `graph.remove_edge()` (non-state organization PRESENCE edges are NOT affected)
- `infrastructure_quality` degrades by an accelerated NEGLECT factor (faster than standard NEGLECT decay)
- `state_investment` is set to `0.0` for `T001` (no further state resource allocation)
- `V_reproduction` increases for remaining population (loss of state services raises the cost of self-provision)
- When `asset_extraction=true`, the state recovers a fraction of its prior investment as budget (the withdrawal is partially self-funding)
- Non-state `PRESENCE` edges remain intact (player organizations keep their territorial footprint)

**Invariant**: STRATEGIC_WITHDRAWAL only removes `PRESENCE` edges where the source node has `_node_type="organization"` and `org_type="state_apparatus"`. Player and civil society organization PRESENCE edges are never touched.

**Rationale** (FR-E09, FR-B07): The state does not simply leave. It defunds, extracts assets, and lets infrastructure decay BEFORE withdrawing. The player inherits a husk: a territory with no state services, degraded infrastructure, and rising reproduction costs. This is a strategic trap: the player may overextend by trying to govern a hollowed territory.

**Test Signature**:
```python
def test_strategic_withdrawal_removes_state_presence_only(self) -> None:
    """BC-TE-004: STRATEGIC_WITHDRAWAL removes state PRESENCE edges, hollows territory."""
    ...
```

---

### BC-TE-005: SCORCHED_EARTH Destroys Infrastructure

**Given**: A territory node `T001` with `infrastructure_quality=0.7` and `territory_type=PERIPHERY` (low international visibility). Population blocks connected via `TENANCY` edges. A `StateAction` with `verb=WITHDRAW`, `sub_verb=SCORCHED_EARTH` targeting `T001`.

**When**: The SCORCHED_EARTH action resolves against `T001`.

**Then**:
- `infrastructure_quality` is set to `defines.neglect_quality_floor` or below (immediate destruction, not gradual decay)
- `legitimacy_cost` on the `StateAction` is proportional to territory visibility:
  - `territory_type=CORE`: extreme legitimacy cost (high media presence)
  - `territory_type=PERIPHERY`: minimal legitimacy cost (low international visibility)
- `V_reproduction` spikes immediately for remaining population (services destroyed)
- All community infrastructure in the territory is destroyed (infrastructure list cleared)
- All state `PRESENCE` edges are removed (same as STRATEGIC_WITHDRAWAL)

**Distinction from STRATEGIC_WITHDRAWAL**: STRATEGIC_WITHDRAWAL hollows over time (gradual); SCORCHED_EARTH destroys immediately. STRATEGIC_WITHDRAWAL extracts assets (budget recovery); SCORCHED_EARTH spends budget to destroy. Both remove state presence, but SCORCHED_EARTH is the kinetic option with higher legitimacy cost and immediate effect.

**Rationale** (FR-E09, FR-B07): SCORCHED_EARTH models the colonial asymmetry. Destruction of peripheral territory infrastructure is historically cheap in legitimacy terms (Gaza, Fallujah, Pine Ridge). Destruction of core territory infrastructure is politically catastrophic. This asymmetry is encoded in the legitimacy cost calculation, not in action availability.

**Test Signature**:
```python
def test_scorched_earth_destroys_infrastructure_with_visibility_cost(self) -> None:
    """BC-TE-005: SCORCHED_EARTH sets infrastructure to floor, legitimacy scales by visibility."""
    ...
```

---

### BC-TE-006: PRESENCE Edge with OperationalProfile Drives Heat Accumulation

**Given**: A territory node `T001` with `heat=0.0` and two organization nodes:
- Organization A: `PRESENCE` edge to `T001` with `operational_profile=HIGH_PROFILE`
- Organization B: `PRESENCE` edge to `T001` with `operational_profile=LOW_PROFILE`

**When**: 4 ticks elapse with both organizations maintaining their PRESENCE edges and operational profiles unchanged.

**Then**:
- `heat` on `T001` has increased from `0.0`
- The heat contribution from Organization A (HIGH_PROFILE) exceeds the heat contribution from Organization B (LOW_PROFILE) by a measurable margin
- Heat accumulation per tick is proportional to the operational profile weight: `HIGH_PROFILE` generates heat at `defines.high_profile_heat_rate` per tick; `LOW_PROFILE` generates heat at `defines.low_profile_heat_rate` per tick (where `high_profile_heat_rate > low_profile_heat_rate`)
- If both organizations go dormant (PRESENCE edges removed), heat decays toward `0.0` over subsequent ticks
- When `heat >= defines.heat_escalation_threshold` (default 0.6), the territory becomes a priority target for state attention thread allocation

**Invariant**: `heat` is bounded within `[0.0, 1.0]` (enforced by `Intensity` type on Territory model). Heat never exceeds 1.0 regardless of the number of HIGH_PROFILE organizations present.

**Rationale** (FR-E01, FR-E02): The visibility-security tradeoff is the core spatial dilemma. HIGH_PROFILE presence enables faster recruitment (via `clarity_bonus`) and stronger community ties, but attracts state attention that triggers surveillance and repression. This creates meaningful player decisions about organizational posture in each territory.

**Test Signature**:
```python
def test_high_profile_generates_more_heat_than_low_profile(self) -> None:
    """BC-TE-006: HIGH_PROFILE presence accumulates heat faster than LOW_PROFILE."""
    ...
```

---

### BC-TE-007: Territory Consciousness Geography Affects PROPAGANDIZE Effectiveness

**Given**: Two territory nodes:
- Territory A (`T001`): hosts a community with `collective_identity=0.7` (high consciousness)
- Territory B (`T002`): hosts a community with `collective_identity=0.2` (low consciousness)

A `StateAction` with `verb=CO_OPT`, `sub_verb=PROPAGANDIZE`, `parameters={"narrative": "WE_ARE_ALL_AMERICANS", "intensity": 0.8}` applied to each territory.

**When**: PROPAGANDIZE resolves against both territories with identical parameters and intensity.

**Then**:
- The absolute `collective_identity` decrease in Territory B (low CI) is greater than in Territory A (high CI)
- High-consciousness territories resist PROPAGANDIZE more effectively because existing collective identity provides a counter-narrative framework
- The effectiveness reduction follows: `effective_delta = base_delta * (1.0 - collective_identity * defines.consciousness_resistance_factor)`
- In Territory A (CI=0.7): PROPAGANDIZE has reduced effectiveness (high consciousness resists assimilation narratives)
- In Territory B (CI=0.2): PROPAGANDIZE has near-full effectiveness (low consciousness offers little resistance)
- PROPAGANDIZE effectiveness is spatially local: applying PROPAGANDIZE to Territory A does NOT affect collective_identity in Territory B (consciousness geography is territory-bound per FR-E04)

**Invariant**: `collective_identity` remains bounded within `[0.0, 1.0]`. PROPAGANDIZE cannot reduce `collective_identity` below `0.0`.

**Rationale** (FR-E04, FR-F03): Consciousness varies spatially. A neighborhood with strong organized community (high CI) resists ideological attack better than an atomized neighborhood (low CI). This makes territorial consciousness-building a defensive strategy against CO_OPT, and makes PROPAGANDIZE more effective in territories where the player has NOT yet organized. The state must decide whether to attack strong consciousness (expensive, may fail) or reinforce weakness (cheap, prevents future organizing).

**Test Signature**:
```python
def test_propagandize_less_effective_in_high_consciousness_territory(self) -> None:
    """BC-TE-007: PROPAGANDIZE effect inversely proportional to territory collective_identity."""
    ...
```
