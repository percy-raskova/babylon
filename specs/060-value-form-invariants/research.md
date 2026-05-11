# Phase 0 Research: Marx Value-Form Invariants

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Date**: 2026-05-11

The plan identified six NEEDS CLARIFICATION items. Each is resolved below
against the codebase, with file:line citations. Where the answer is "the
engine already supports this", the implementation tests it directly. Where
the answer is "the engine does not yet support this", the spec's SKIP
convention applies.

---

## R1. H3 Disaggregation Rule (FR-016)

**Question**: Does the engine have a named, single-source-of-truth
disaggregation rule for spatial H3 round-trips? If yes, reuse it. If no,
declare one as the FR-011 exception.

**Decision**: Use **`h3.cell_to_parent(cell, parent_res)`** for roll-up
and a **`uniform_split`** rule (parent value divided equally among the 7
children at one finer resolution) as the canonical disaggregation rule for
FR-016. Declare it as a new module-level constant in
`src/babylon/config/h3_splitter.py` because no existing module names a
single rule — different parts of the codebase use different conventions.

**Rationale**:

- `src/babylon/infrastructure/r8_mesh.py:50` uses
  `h3.cell_to_children(r7_hex, 8)` for R7→R8 disaggregation (7 children
  per parent).
- `src/babylon/infrastructure/r8_types.py:152` uses
  `h3.cell_to_parent(self.h3_index, 7)` for R8→R7 roll-up with a strict
  validator that the parent_h3 field matches the computed parent.
- `src/babylon/economics/substrate/spatial.py:196` uses
  `h3.cell_to_parent(h3_id, 6)` and `cell_to_parent(h3_id, 5)` for
  multi-resolution aggregation up the H3 hierarchy.
- `src/babylon/economics/substrate/circulation.py:86` uses
  *"Equal weight within county (simplified disaggregation)"* as an
  inline comment — equal-weight splitting is the documented default
  convention in the substrate layer.

No module exports a single named rule. The uniform-split convention is
the de facto default; codifying it as `H3SplitterRule.UNIFORM` in a
shared config makes FR-016 testable and centralizes the convention so
future regional/area-weighted/population-weighted splits can be added as
additional enum members.

**Alternatives considered**:
- *Area-weighted split (Voronoi-style)*: H3 cells are hexagonal and
  uniform in area at any given resolution, so area-weighting and
  uniform-weighting are mathematically equivalent. Rejected as
  unnecessary complication.
- *Population-weighted split*: Would require population data per child
  cell; substrate doesn't carry this at all resolutions. Deferred to a
  future spec if/when needed.
- *No production change (just probe existing modules)*: Rejected because
  there is no single existing source of truth; tests would have to
  hardcode the convention themselves, duplicating it. The FR-011
  exception explicitly permits declaring this one constant.

**File to add**: `src/babylon/config/h3_splitter.py` (~50 LOC, single
`H3SplitterRule` `StrEnum` with one member `UNIFORM`, plus a small
`split_uniformly(parent_value, n_children) -> list[float]` helper).

---

## R2. Capital Migration Mechanism (FR-019)

**Question**: Is there an active capital-migration step in the engine that
US7(c) Volume III equalization tendency can run against?

**Decision**: **YES — use `DefaultHexEqualizationComputer` in
`src/babylon/economics/substrate/equalization.py`.**

**Rationale**:

- `src/babylon/economics/substrate/__init__.py:23`:
  `from babylon.economics.substrate.equalization import
  DefaultHexEqualizationComputer` (publicly exported).
- `src/babylon/economics/substrate/equalization.py:103`:
  `compute Volume III capital equalization via profit rate gradient`.
- The module's docstring (`equalization.py:1-22`) names the formula
  `delta_c[hex] = alpha * (r[hex] - r_avg) * c[hex]`, gives the
  conservation proof, and explicitly tags it Volume III (Marx Capital
  Vol. III, chapters 9-10).
- `src/babylon/economics/substrate/types.py:300`: `equalization_alpha:
  float` is a tunable parameter on `HexGrid` defines.
- `src/babylon/economics/substrate/protocols.py:252`:
  `Protocol for computing Volume III capital equalization at hex level`
  formalizes the protocol contract.

The mechanism is operative whenever `equalization_alpha > 0` and the
scenario hydrates hex-level economic state. US7(c) runs the engine for
N ticks with `equalization_alpha > 0` and reads the inter-sectoral
profit-rate variance trajectory.

**SKIP condition**: If a scenario sets `equalization_alpha == 0` (or
disables the substrate equalization step), the test SKIPs with reason
"Capital migration disabled (`equalization_alpha == 0`) — Volume III
equalization tendency cannot be tested" and points to this spec.

**Alternatives considered**:
- *Synthesize a separate migration mechanism for the test*: Rejected.
  Reusing the engine's actual mechanism is the only way the test
  protects against regressions in the production code path.

**No production-side change**: The mechanism already exists with a
documented conservation proof.

---

## R3. TransformationDialectic State Probe (FR-008, FR-021)

**Question**: How does the test detect whether the engine is in
"proportional-prices" mode vs. "full-transformation" mode, so that US3
(redistribution arm), US4, US5 SKIP cleanly when transformation is
inactive?

**Decision**: Probe the `weight` field of the `TransformationDialectic`
instance on the world. Mode classification:

- `weight ≤ 0`: proportional-prices mode. SKIP the transformation-gated
  tests.
- `weight > 0`: redistribution-active mode. RUN the transformation-gated
  tests.

**Rationale**:

- `src/babylon/engine/dialectics/transformation.py:45`: class
  `TransformationDialectic(Dialectic[TransformationPole, EmptyPole])`.
- `transformation.py:54-55`: docstring explicitly defines the weight
  convention: *"weight < 0 → values dominate prices (low
  equalization). weight > 0 → prices of production fully equalized."*
- `transformation.py:95`: `new_weight = max(-1.0, min(1.0, new_rate * 2.0 - 0.5))`
  — the weight is computed and bounded each tick from the average
  profit rate, so a single read at tick boundary T+1 gives the
  authoritative state.

The probe is one line:
```python
def probe_transformation_mode(world: WorldState) -> TransformationMode:
    dial = world.dialectics["transformation"]
    return (
        TransformationMode.REDISTRIBUTION_ACTIVE
        if dial.weight > 0
        else TransformationMode.PROPORTIONAL_PRICES
    )
```

Per FR-021, this is the single source of truth for the four
transformation-gated tests (FR-005-redistribution-arm, FR-006, FR-007,
FR-019). Each test imports `probe_transformation_mode` and SKIPs based
on its return value.

**Alternatives considered**:
- *Read `equalization_alpha` from defines*: Rejected. `equalization_alpha`
  controls the hex-level capital migration speed (R2), not the price-form
  redistribution that US3/US4/US5 depend on. These are two different
  Volume III mechanisms; conflating them would produce wrong SKIP
  behavior.
- *Compare prices vs. values numerically and infer mode*: Rejected.
  Tautological — the test would be probing the very property it wants
  to assert.

---

## R4. WorldState Equality Semantics (FR-014)

**Question**: How is `WorldState` equality defined? FR-014 requires the
post-serialization round-trip to equal the original.

**Decision**: Use **Pydantic's default `__eq__`** on `WorldState`
(structural equality over all model fields) for the round-trip identity
check. `WorldState` is `frozen=True` and `model_config =
ConfigDict(frozen=True)` (per `src/babylon/models/world_state.py:206`),
making it hashable and comparable by structural equality. No custom
`__eq__` is needed.

**Rationale**:

- `src/babylon/models/world_state.py:183`: `class WorldState(BaseModel)`
  with `model_config = ConfigDict(frozen=True)` at line 206.
- Frozen Pydantic v2 models compare via structural equality (all fields)
  by default.
- Round-trip via `WorldState.model_dump_json()` →
  `WorldState.model_validate_json(json_str)` exercises every serializer/
  deserializer for every nested model.
- Known gotcha from project CLAUDE.md ("Graph Round-Trip Can Lose
  Mutations"): `from_graph()` excludes computed fields and uses model
  defaults for missing fields. FR-014 is a **JSON** round-trip, not a
  graph round-trip — the JSON path includes all fields, so this gotcha
  does not apply. But we add a sibling test (in
  `test_serialization_roundtrip.py`) that asserts JSON-round-trip
  semantic equality.

**Comparison helper**: For diagnostic output, use
`pydantic_core.to_jsonable_python` on both sides plus DeepDiff (already
in dev deps) for a human-readable field-level diff when the assertion
fails. This drives FR-010's diagnostic requirement.

**Alternatives considered**:
- *Custom equality dropping non-deterministic fields*: Rejected. There
  are no documented non-deterministic fields on `WorldState`. If a
  future field carries a timestamp, the test will fail until a custom
  exclusion is added — which is the right behavior (the test surfaces
  the new non-determinism).
- *Graph round-trip instead of JSON round-trip*: Rejected per the
  CLAUDE.md gotcha. Graph round-trip is a different invariant (used
  by `to_graph`/`from_graph` for cross-system mutation flow) and is
  already covered by existing tests.

---

## R5. UUID-Typed Fields Inventory (FR-013)

**Question**: Which fields on `WorldState` and nested models carry
opaque string IDs that FR-013 must relabel?

**Decision**: Build the relabeler from the following inventory. All
fields are typed as `str` (no `UUID` type is used; per
project convention IDs are strings, often UUID-shaped but also
sometimes domain-meaningful like `"WAYNE_COUNTY_PROLETARIAT"`). The
relabeler relabels **all** of these consistently across both keys
and value-side references.

**Top-level `WorldState` dict keys** (each dict maps `id → entity`):

| Field | Location | Type |
|---|---|---|
| `entities` | `world_state.py:214` | `dict[str, SocialClass]` |
| `territories` | `world_state.py:219` | `dict[str, Territory]` |
| `state_finances` | `world_state.py:244` | `dict[str, StateFinance]` |
| `contradiction_frames` | `world_state.py:249` | `dict[str, ContradictionFrame]` |
| `organizations` | `world_state.py:255` | `dict[str, OrganizationType]` |
| `key_figures` | `world_state.py:259` | `dict[str, KeyFigure]` |
| `institutions` | `world_state.py:265` | `dict[str, Institution]` |
| `industries` | `world_state.py:275` | `dict[str, IndustryHyperedge]` |

**Entity-internal ID fields** (each entity has an `id` plus may reference
other entities):

| Field | Location | Note |
|---|---|---|
| `Organization.id` | `entities/organization.py:140` | str |
| `Organization.headquarters_id` | `entities/organization.py:178` | str \| None, must be in `territory_ids` |
| `KeyFigure.id` | `entities/organization.py:393` | str |
| `KeyFigure.organization_id` | `entities/organization.py:401` | str — back-ref |
| `Territory.id` | `entities/territory.py:57` | str |
| `Territory.host_id` | `entities/territory.py:84` | str \| None |
| `Territory.occupant_id` | `entities/territory.py:88` | str \| None |
| `SocialClass.id` | `entities/social_class.py:271` | str |
| `Contradiction.id` | `entities/contradiction.py:22` | str |
| `Relationship.source_id` | `entities/relationship.py:76` | str |
| `Relationship.target_id` | `entities/relationship.py:81` | str |
| `AttentionThread.thread_id` | `entities/attention_thread.py:60` | str |
| `AttentionThread.target_id` | `entities/attention_thread.py:62` | str |
| `AttentionThread.owning_apparatus_id` | `entities/attention_thread.py:84` | str |
| `StateApparatusAI.target_id` | `entities/state_apparatus_ai.py:270` | str \| None |
| `StateApparatusAI.framework_id` | `entities/state_apparatus_ai.py:338` | str |
| `StateApparatusAI.creating_apparatus_id` | `entities/state_apparatus_ai.py:358` | str |
| `Community.agent_id` | `entities/community.py:388` | str |

**Relabeling algorithm**:

1. Collect all canonical IDs by iterating top-level dict keys.
2. Generate aliases via a deterministic function:
   `alias(i, original_id) = f"alias_{i:06d}"` where `i` is the index
   in canonical order (sorted by original ID).
3. Build a `dict[str, str]` mapping original → alias.
4. Walk `WorldState` via Pydantic's `model_dump()`, rewrite every
   string field whose name ends in `_id` or equals `id` and whose value
   is in the mapping.
5. Rewrite top-level dict keys using the same mapping.
6. Reconstitute via `WorldState.model_validate(dump)`.

**Edge cases**:
- IDs **not** in the mapping (e.g., `framework_id` referring to a
  framework not in `WorldState`): leave unchanged. Diagnostic test
  warns if any such orphan IDs are found.
- `Relationship.source_id` / `target_id` MUST point to a known entity
  (validated by Pydantic). The relabeling preserves these references
  by walking *all* `_id`-suffixed fields, not just the canonical keys.

**Alternatives considered**:
- *Walk the model with Pydantic's `model_validate` round-trip*: same
  thing but more verbose. Direct dump-rewrite-reconstitute is the
  cleanest expression.

---

## R6. Scenario Builders (US1–US7 fixtures)

**Question**: Confirm the entry points for the two-county and Wayne
County scenarios.

**Decision**: Use these entry points:

- **Two-county**: `babylon.engine.scenarios.two_node.TwoNodeScenario.build()`
  → `(WorldState, SimulationConfig, GameDefines)`
- **Wayne County**: `babylon.engine.scenarios.wayne_county.WayneCountyScenario.build()`
  → `(WorldState, SimulationConfig, GameDefines)`
- **Legacy back-compat shim** (still works, deprecated):
  `babylon.engine.scenarios_wayne_county.create_wayne_county_scenario()`
  exists per `src/babylon/engine/scenarios_wayne_county.py:6` and
  delegates to the new class-based scenario per ADR-006.1 / Spec 059
  US4.

**Rationale**:

- `src/babylon/engine/scenarios/__init__.py`, `scenarios/base.py`
  define `Scenario` ABC with `__init_subclass__` registry (Spec 059
  Phase 4 / US4 deliverable).
- `src/babylon/engine/scenarios/two_node.py:20`: `class TwoNodeScenario(Scenario)`.
- `src/babylon/engine/scenarios/wayne_county.py:20`: `class WayneCountyScenario(Scenario)`.

Both return the canonical tuple `(WorldState, SimulationConfig,
GameDefines)`. Tests use the class-based form to avoid the legacy
shim's deprecation warning.

**Alternatives considered**:
- Use the legacy function form for simplicity. Rejected: the class
  form is the post-Spec-059 canonical entry point; tests on a new
  spec should use the new convention.

---

## Summary

All six NEEDS CLARIFICATION items resolved. Phase 1 design can proceed
with full confidence in:

1. The H3 splitter rule we will declare (`UNIFORM`, one-line config).
2. The capital-migration mechanism we will exercise (`DefaultHex-
   EqualizationComputer`).
3. The transformation-mode probe (one-line read of
   `world.dialectics["transformation"].weight`).
4. The WorldState equality semantics (Pydantic default structural
   equality on the frozen model).
5. The UUID-typed field inventory (17 ID-shaped fields plus 8
   top-level dict-key namespaces, all string-typed).
6. The scenario builders (class-based `Scenario.build()` per ADR-006.1).

No new third-party dependencies are required. The only production-side
change permitted by FR-011 is the `H3SplitterRule` constant declaration
(R1). All other work is test-only under `tests/`.
