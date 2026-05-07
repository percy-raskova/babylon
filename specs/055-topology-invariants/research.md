# Phase 0 Research: Topological Invariants

**Feature**: 055-topology-invariants
**Date**: 2026-05-06
**Spec**: [spec.md](./spec.md)

## Purpose

Resolve open implementation patterns and surface findings that emerged from
reading the production code. The three `/speckit.clarify` decisions are
already in `spec.md`; this document records the *technical* decisions that
follow from them.

---

## §1. Edge-mode legal-arc set — single source of truth

**Decision**: Import `_VALID_TRANSITIONS` directly from
`src/babylon/engine/systems/edge_transition.py` into the test module. Do
NOT duplicate the arc set or re-derive it from `_TRANSITIONS`. The
production code already builds `_VALID_TRANSITIONS` as
`{(t.from_mode, t.to_mode) for t in _TRANSITIONS}` plus the explicit
`(ANTAGONISTIC, ANTAGONISTIC)` persistence transition.

**Rationale**: `edge_transition.py:458–462` defines

```python
_VALID_TRANSITIONS: set[tuple[EdgeMode, EdgeMode]] = {
    (t.from_mode, t.to_mode) for t in _TRANSITIONS
}
_VALID_TRANSITIONS.add((EdgeMode.ANTAGONISTIC, EdgeMode.ANTAGONISTIC))
```

This is the canonical state machine. Any future addition or removal of an
arc is automatically reflected in the test the moment `_TRANSITIONS` is
edited — exactly what FR-002 demands ("no hand-maintained arc list is
permitted in the test module").

**Module-private symbol caveat**: `_VALID_TRANSITIONS` carries a single
underscore prefix indicating module-private. The test module imports it
explicitly as a deliberate cross-module coupling that *is* the contract:
the production code's arc set IS the test's expected set, by reference,
not by copy. A docstring on the import in the test module records this
intent so a future reader does not "fix" the apparent encapsulation
violation.

**Trivial-transition handling**: A tick where no predicate fires leaves
`edge_mode` unchanged, producing the trivial pair `(m, m)` for some
`m ≠ ANTAGONISTIC`. This is *not* an arc in `_VALID_TRANSITIONS` for any
mode other than `ANTAGONISTIC`. The trajectory test treats trivial
no-transition pairs as legal-by-definition (no transition occurred) and
counts them separately from the explicit `(ANTAGONISTIC, ANTAGONISTIC)`
persistence arc, per FR-012. Implementation: filter trivial pairs out of
the legality check; report their count in the test's stdout for
trajectory-coverage statistics.

**Alternatives considered**:

- **Hardcode the 17 arcs in the test**: explicitly forbidden by FR-002
  ("no hand-maintained arc list").
- **Re-derive from `_TRANSITIONS` in the test**: works but requires
  duplicating the persistence-arc rule, splitting the source of truth.

---

## §2. Synthesized evidence-event generation pattern

**Decision**: For US1's synthesized branch (Q3 hybrid clarification), the
evidence-event strategy generates `(field_name, metric, value)` triples
that are written directly into graph node attributes between
`EdgeTransitionSystem.step` calls. Specifically:

```python
@composite
def evidence_event(draw) -> dict[str, Any]:
    """Draw a single evidence event — a node-attribute write payload."""
    field = draw(st.sampled_from(["exploitation", "imperial_rent", "immiseration"]))
    metric = draw(st.sampled_from(["value", "df_dt", "d2f_dt2", "laplacian"]))
    value = draw(st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False))
    return {"field": field, "metric": metric, "value": value}
```

The synthesized branch then builds a 2-node graph (one source, one
target), seeds each with `contradiction_fields` and `field_derivatives`
dicts, applies the evidence event by writing into those dicts, and runs
`EdgeTransitionSystem.step` once per event. The trajectory is the sequence
of `edge_mode` values observed after each step.

**Rationale**: The state machine's predicates are defined over
`contradiction_fields[…]` and `field_derivatives[…][…]` (per
`_evaluate_condition` at `edge_transition.py:470`). Writing to these
dicts directly is exactly the contract the System reads — synthesized
events exercise the predicate space without the cost of running an
upstream System.

**Coverage strategy for predicates**: The 3 fields × 4 metrics × random
value range covers the entire predicate condition space declared in
`_TRANSITIONS`. Hypothesis's shrinker will narrow failures to the smallest
event sequence that produces the violation.

**Observed branch (Q3 hybrid clarification, second half)**: The observed
branch runs at least one full `SimulationEngine.run_tick` trajectory of
length ≥ 5 ticks against a random `WorldState`, captures the resulting
`edge_mode` for every edge that carries a mode, and asserts the same
legality property. Implementation pattern:

```python
@given(state=worldstate_strategy(min_entities=2, max_relationships=4))
def test_observed_trajectory_is_legal(state, services_fixture, ctx_fixture):
    pre_modes = _capture_edge_modes(state.to_graph())
    for tick in range(5):
        graph = state.to_graph()
        engine.run_tick(graph, services_fixture, ctx_fixture)
        state = WorldState.from_graph(graph, tick=state.tick + 1)
        post_modes = _capture_edge_modes(graph)
        for edge_id, (prev, cur) in pairwise(pre_modes, post_modes):
            assert (prev, cur) in _VALID_TRANSITIONS or prev == cur, ...
        pre_modes = post_modes
```

**Alternatives considered**:

- **State-machine driver via `RuleBasedStateMachine`** (Hypothesis's
  stateful testing): more powerful but heavier — requires modeling
  evidence events as Hypothesis rules and serves the same purpose as the
  composite strategy. Rejected as over-engineered for this slice.
- **Random `EdgeTransitionSystem.step` invocations without explicit
  evidence events**: relies on whatever attributes happen to be on the
  graph; produces poor predicate coverage. Rejected.

---

## §3. Community-node detector — `_node_type == "community"`

**Decision (resolved by Q1 clarification)**: Single helper
`is_community_node(graph, node_id) -> bool` that returns
`True` iff `graph.nodes[node_id].get("_node_type") == "community"`. The
helper lives in `tests/property/harness/topology_harness.py` (alongside
the `TopologyInvariantHarness` runner) and is the single source of truth
for US2's linter.

**Rationale**: This matches the codebase's established `_node_type`
convention used by `WorldState.to_graph` / `from_graph`, the
`NodeFilter.matches()` pattern (`MEMORY.md`: "_node_type must be
reconstructed for `NodeFilter.matches()`"), and Spec 054's
`_iter_worldstate_collections` helper which already discriminates entity
types this way. Single attribute lookup, fast, no XGI coupling.

**Implementation**:

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import networkx as nx

def is_community_node(graph: "nx.DiGraph[str]", node_id: str) -> bool:
    """True iff the node is marked as a community node via _node_type.

    Single source of truth for US2's hyperedges-not-pairwise linter.
    Encoded as a function (not a constant) so the rule is testable and
    extensible if the codebase convention shifts.
    """
    if node_id not in graph.nodes:
        return False
    return graph.nodes[node_id].get("_node_type") == "community"
```

**Alternatives considered** (already discussed in `/speckit.clarify`):

- **XGI hypergraph node-set membership** (option B): semantically purest
  but couples the harness to XGI; rejected.
- **CommunityType StrEnum membership** (option C): fragile string
  matching; rejected.
- **Hybrid** (option D): doubles maintenance; rejected.

---

## §4. State-bearing Pydantic model class registry (US3 structural audit)

**Decision**: Walk every Pydantic model class under
`babylon.models.entities` and `babylon.models.world_state` (and the
top-level `WorldState` class itself). For each discovered class, assert
`cls.model_config.get("frozen") is True`. The walker lives in
`tests/property/harness/model_class_registry.py`.

**Rationale**: The set of state-bearing Pydantic models is exactly the
set whose instances populate the collections enumerated by Spec 054's
`_iter_worldstate_collections` helper, plus any nested model types those
top-level models hold (e.g., `TernaryConsciousness` inside
`SocialClass.consciousness`). The discovery walker is a closure of
`pkgutil.iter_modules` over `babylon.models.entities` plus introspection
of `WorldState.model_fields` to surface the contained types.

**Implementation sketch**:

```python
import pkgutil
import importlib
import inspect
from pydantic import BaseModel
from babylon.models import entities, world_state

def discover_state_bearing_models() -> list[type[BaseModel]]:
    """Yield every Pydantic model class in babylon.models.entities + world_state."""
    seen: set[type[BaseModel]] = {world_state.WorldState}
    for finder, name, ispkg in pkgutil.walk_packages(entities.__path__, entities.__name__ + "."):
        module = importlib.import_module(name)
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, BaseModel) and cls.__module__ == name:
                seen.add(cls)
    return sorted(seen, key=lambda c: c.__qualname__)
```

**Static check**:

```python
def assert_frozen_at_collection_time() -> None:
    for cls in discover_state_bearing_models():
        # Pydantic v2 may store the config as a class-attribute dict OR via ConfigDict;
        # both shapes resolve through model_config which is always present on BaseModel subclasses.
        cfg = getattr(cls, "model_config", None)
        if cfg is None:
            continue  # skip non-state classes (no model_config means it's a wrapper)
        if cfg.get("frozen") is not True:
            raise AssertionError(
                f"State-bearing model {cls.__qualname__} is not frozen "
                f"(model_config['frozen']={cfg.get('frozen')!r}). "
                f"All state-bearing Pydantic models MUST set frozen=True."
            )
```

This runs once at test collection time (parametrized over the discovered
class list, one assert per class), so the per-class result appears in the
test report and a single class regression is isolable.

**Bypass marker support**: A model class MAY carry
`bypasses_topology_invariant: ClassVar[dict[str, str]] = {"frozen_discipline": "<reason>"}`
to opt out — same shape as the System-side marker — for the rare model
that legitimately needs a mutable field (e.g., a value-object cache that
isn't part of game state). The harness skips frozen-asserting any class
whose `bypasses_topology_invariant` dict contains the
`"frozen_discipline"` key, and machine-asserts the justification is
non-empty per FR-011 / SC-006.

**Out of scope — runtime mutation through frozen models**: A frozen
Pydantic model can still hold a mutable container (`list`, `dict`, `set`)
that downstream code can mutate. US3 does NOT target this — it asserts
identity, not transitive immutability. Catching mutable-container leaks
is a follow-up that would benefit from `pydantic-extra-types` or a
custom pydantic validator; tracked as a future invariant if empirical
evidence shows it's needed.

**Alternatives considered**:

- **Walk the full `babylon.models` namespace**: includes utility types
  (`Probability`, `Currency`) that aren't classes but type aliases;
  filter complexity outweighs benefit. Rejected.
- **Hardcode a model class list**: explicitly forbidden by the same
  no-hand-maintenance principle as Spec 054. Rejected.

---

## §5. US3 identity-discipline check — ID matching strategy

**Decision**: Match pre-state and post-state entities by their `id`
string field (the simulation entity ID), NOT by Python `id()` identity.
For each ID-matched pair, then compare Python `id()` to detect in-place
mutation:

```python
pre_collections = dict(_iter_worldstate_collections(pre_state))
post_collections = dict(_iter_worldstate_collections(post_state))

for entity_id in pre_collections.keys() & post_collections.keys():
    pre_entity = pre_collections[entity_id]
    post_entity = post_collections[entity_id]
    fields_equal = pre_entity.model_dump() == post_entity.model_dump()
    same_python_id = id(pre_entity) is id(post_entity)
    # Legal: (equal AND same id) OR (different AND different id)
    # Illegal: same id AND fields differ → in-place mutation
    if same_python_id and not fields_equal:
        raise AssertionError(
            f"In-place mutation detected on entity {entity_id} "
            f"(class {type(pre_entity).__name__}); fields changed "
            f"without producing a new instance."
        )
```

**Rationale**: The simulation entity ID (e.g., `"C001"` for a
`SocialClass`) is the stable cross-tick identity. Python `id()` is the
secondary signal that distinguishes "engine left it alone" (same Python
id) from "engine produced a fresh instance via `model_copy`" (different
Python id). A bug where `id()` matches but fields differ is the
in-place mutation US3 targets.

**Helper reuse**: The walker reuses Spec 054's
`_iter_worldstate_collections` exactly — a future addition to `WorldState`
extends both Spec 054's bound check and Spec 055's identity check via a
single edit, per FR-005.

**Edge case — the `relationships` list**: `WorldState.relationships` is a
list, not a dict, so there's no key-based matching. The harness keys
relationships by the `(source_id, target_id, edge_type)` tuple, which is
unique per `Relationship` instance per the model's invariants. If a
relationship is added or removed across the tick, it doesn't appear in
both collections and the identity check skips it (legitimate).

**Edge case — Python id() recycling**: Python may recycle an `id()` value
after garbage-collecting the original object. The harness pins the
pre-state collection (held in a local variable for the duration of the
test) so the ids cannot be recycled while the post-state is being
evaluated. This is how Spec 054's pre/post invariants already work.

---

## §6. Aleksandrov Test alignment (Constitutional III.8)

Each invariant traces to a material relation. This is the
provenance-chain documentation required by P0 principle III.8.

| Invariant | Material Relation | Why the Bound is Real |
|-----------|-------------------|------------------------|
| **Edge-mode trajectory legality** | The 17-arc state machine (Constitution I.15) encodes the dialectical-field topology — qualitative modes (`EXTRACTIVE`, `TRANSACTIONAL`, `SOLIDARISTIC`, `ANTAGONISTIC`, `CO_OPTIVE`) are the discrete state space of contradiction modes. The arcs encode which dialectical transformations are materially possible (e.g., extraction can be contested into antagonism, but cannot leap straight to mutual aid without an intermediate broken-extraction or co-optive phase). | The bound *is* the materialist commitment that revolutionary transformations cannot skip steps — the dialectic moves through quantity-into-quality jumps along permissible paths. Skipping a mode is unrepresentable in the dialectical model. |
| **Hyperedges-not-pairwise (community → member)** | Constitution II.7 distinguishes dyadic flows (morphism graph) from N-ary memberships (XGI hypergraph). A community is structurally an N-ary collective — it cannot be reduced to its pairwise edges to members without losing the constitutive collectivity (Anti-Pattern VIII.9). | The bound *is* the structural distinction between dyadic dialectical relations and collective hyperedge memberships. Collapsing the latter into the former discards the polylogical category that the framework requires. |
| **Frozen Pydantic discipline** | Constitution III.7 declares the engine is `step(WorldState) → WorldState`, a pure transformation. Any in-place state mutation breaks replayability, breaks deterministic hashing (a pre-state hash computed before the in-place write no longer matches the post-state), and breaks the State/Engine separation that Constitution II.6 establishes. | The bound *is* the operational test of III.7 — purity is not enforceable by inspection; only by per-tick identity audit. |
| **Round-trip identity** | Constitution II.6: "State is Data, Engine is Transformation." Round-trip identity is the operational definition of "State is Data" — the data IS its serialized form (modulo the explicit `tick` parameter), and the graph representation is a lossless intermediary between in-memory state and the persisted ledger. | The bound *is* the State/Data identity. Any field that fails round-trip is a hidden side-channel of the engine, not data. |

This table is referenced from the Constitution Check post-design re-eval
in `plan.md`.

---

## §7. WorldState scale defaults

**Decision**: Reuse Spec 054's defaults — `max_entities=4` (small),
`max_relationships=4` for US1 / US2 / US3 (per-tick checks); for US4
(round-trip), allow up to `max_entities=8` and `max_relationships=8`
since the round-trip is `O(N)` and serialization cost is well within
budget.

**Rationale**: Topology invariants are about graph *structure* not
*scale* — a 4-entity graph is sufficient to express every legal arc, the
community-node detection rule, the per-entity identity check, and the
round-trip property. Bumping N doesn't add falsification surface area;
it does add runtime cost. SC-005's 60s budget over 4 test files (15s
each) allows comfortable margin at small N.

The slow profile (`HYPOTHESIS_PROFILE=slow`) increases `max_examples` but
keeps the small-N strategy parameters; the marginal coverage benefit of
larger N at higher example counts is empirically nil for structural
invariants.

**Alternatives considered**:

- **Match Spec 053's `max_hexes=25_000`**: 4-orders-of-magnitude entity
  count for tests where the bug surface is `O(1)` per edge / per
  entity. Rejected as wasteful.
- **Per-test customization**: defer until empirical CI timing data shows
  it's needed.

---

## §8. Round-trip exclude rules — read from production

**Decision**: The US4 round-trip property test reads its `exclude` set
from production code (`src/babylon/models/world_state.py`) at test
collection time:

```python
from babylon.models.world_state import (
    _SOCIAL_CLASS_COMPUTED_FIELDS as SOCIAL_CLASS_COMPUTED,
    _TERRITORY_EXCLUDED_FIELDS as TERRITORY_EXCLUDED,
)

# At test time:
exclude_for_dump = {"tick"} | _build_field_path_set(SOCIAL_CLASS_COMPUTED, TERRITORY_EXCLUDED)
assert restored.model_dump(exclude=exclude_for_dump) == state.model_dump(exclude=exclude_for_dump)
```

If the production code does not currently expose these as named
constants, the implementation phase MUST refactor `from_graph` to read
from named module-level constants (same pattern as `_VALID_TRANSITIONS`
in `edge_transition.py`). This single-source-of-truth refactor is part
of US4's task list.

**Rationale**: FR-010 explicitly forbids hardcoding the exclude-set in
the test. If the production code adds a new computed field tomorrow, the
test must pick it up automatically — same drift-safety principle as
`_VALID_TRANSITIONS`.

**Alternatives considered**:

- **Hardcode `exclude={"tick", "consumption_needs", ...}` in the test**:
  forbidden by FR-010.
- **Compute exclude dynamically by diffing pre/post `model_dump()`**:
  fragile (would mask real differences as legitimately-excluded).

---

## §9. Patterns reused from Spec 053 / Spec 054

| Spec 053 / 054 artifact | Spec 055 use |
|-------------------------|--------------|
| Profile registration in `tests/conftest.py` (`default`, `slow`) | Reuse as-is — no changes |
| Profile registration in `tests/property/conftest.py` (`dev`, `ci`, `nightly`) | Reuse as-is — no changes |
| `tol(n, magnitude)` helper in `tests/property/harness/__init__.py` | Not used by Spec 055 (structural invariants don't need magnitude-aware tolerance) |
| `system_registry.all_systems()` from Spec 054 | Reused for US1 observed branch and US2 full-pipeline runs |
| `_iter_worldstate_collections` from Spec 054 `engine/invariants.py` | Reused as the canonical entity walker for US3 identity check (FR-005) |
| `BoundInvariantHarness` shape from Spec 054 | New `TopologyInvariantHarness` mirrors the same shape (constructor, `run` method, opt-out marker reading) |
| `bypasses_bound_invariant: ClassVar[dict[str, str]]` opt-out marker | Sister marker `bypasses_topology_invariant: ClassVar[dict[str, str]]` per FR-011 — same shape exactly, different key namespace |
| `@composite` strategies in `tests/property/strategies/` | New strategies in same directory — `edge_mode_evidence.py`, plus extension to `worldstate.py` |

---

## Open Questions Carried to Phase 1

None. All technical decisions resolved; spec FR-002 / FR-003 will be
implemented per §1 / §2 (synthesized + observed hybrid); spec FR-004 per
§3 (`_node_type == "community"` helper); spec FR-005 / FR-006 per §4 / §5
(reuse `_iter_worldstate_collections`, static class audit + per-tick
identity check); spec FR-010 per §8 (read exclude-set from production).

These refinements do not invalidate the spec — they sharpen the
implementation contract. They are recorded here rather than rewritten
into the spec because they arise from production-code investigation that
post-dates the spec write-up; they belong in research, not in
requirements.
