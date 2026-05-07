# Quickstart: Topological Invariants — Property-Based Tests

**Feature**: 055-topology-invariants
**Audience**: Maintainers running, debugging, or extending the
topology-invariant test suite.

## Run the suite

```bash
# Default profile (fast — runs in mise run test:unit)
poetry run pytest tests/property/invariants/test_edge_mode_trajectory.py \
                  tests/property/invariants/test_community_membership_lint.py \
                  tests/property/invariants/test_frozen_discipline.py \
                  tests/property/invariants/test_round_trip_identity.py -v

# Or via mise (combined with Spec 053 + 054 invariants)
mise run test:unit

# Slow profile (5x more examples — for nightly / pre-release)
HYPOTHESIS_PROFILE=slow poetry run pytest tests/property/invariants/ -v
```

**Expected default-profile timing**: ≤ 60 s for the four new test files
combined. The combined `tests/property/` suite (Spec 053 + 054 + 055) is
budgeted to ≤ 3 min on default — Spec 053 + 054 baseline is 83 s, leaving
~97 s of headroom for Spec 055 within the 3-min cap.

**Measured at implementation time (2026-05-07)**:

- Spec 055 alone (4 test files): **6.33 s** (well under 60 s cap)
- Combined Spec 053 + 054 + 055: **87.83 s** (under 180 s cap)
- 112 passed, 19 skipped (frozen-discipline pre-existing debt — see
  `_PRE_EXISTING_NON_FROZEN_DEBT` in `test_frozen_discipline.py`)

## What each test catches

| Test file | Catches | Failure mode |
|-----------|---------|--------------|
| `test_edge_mode_trajectory.py` | Illegal arcs in the EdgeTransitionSystem state machine | Hypothesis-shrunk minimal trajectory printed to stdout, naming the offending `(prev_mode -> cur_mode)` arc and the events that produced it |
| `test_community_membership_lint.py` | `EdgeType.MEMBERSHIP` edges with community sources (Anti-Pattern VIII.9) | Failure msg names `(source_id, target_id)` and the `_node_type` value of the source |
| `test_frozen_discipline.py` (Layer 1) | A state-bearing model class with `frozen=True` removed | Per-class assertion at collection time names the offending class |
| `test_frozen_discipline.py` (Layer 2) | In-place mutation of an entity during a tick (id() match + field difference) | Failure msg names entity ID, class, and the field-level diff |
| `test_round_trip_identity.py` | `WorldState.from_graph(state.to_graph())` lossy on some `WorldState` shape | Failure msg shows the diff between pre and post `model_dump()` |

## Interpret a failure

### EdgeMode trajectory failure

```text
FAILED tests/property/invariants/test_edge_mode_trajectory.py::test_synthesized_trajectory_is_legal
AssertionError: Illegal arc at step 4: (EdgeMode.EXTRACTIVE -> EdgeMode.SOLIDARISTIC).
Trajectory: [EXTRACTIVE, EXTRACTIVE, ANTAGONISTIC, EXTRACTIVE, EXTRACTIVE, SOLIDARISTIC]
Events: [{field: "exploitation", metric: "value", value: 0.85, scope: "source"}, ...]

Falsifying example: trajectory_input=(EdgeMode.EXTRACTIVE, [
    {"field": "exploitation", "metric": "value", "value": 0.85, "scope": "source"},
    ...
])
```

**Diagnosis**: `EdgeTransitionSystem` produced a direct
`EXTRACTIVE -> SOLIDARISTIC` arc that is not in `_VALID_TRANSITIONS`.
Either:
1. The dialectical model genuinely allows this leap — add the arc to
   `_TRANSITIONS` in `edge_transition.py`. The test imports
   `_VALID_TRANSITIONS` so no test edit is needed.
2. The leap is a bug — find the predicate in `_TRANSITIONS` that fired
   incorrectly and fix the predicate condition.

### Community fan-out failure

```text
FAILED tests/property/invariants/test_community_membership_lint.py::test_no_community_fan_out_post_pipeline
AssertionError: Community fan-out edge detected: (COMM_001 -> C002, MEMBERSHIP) —
source node _node_type='community'. Membership MUST live in the XGI hyperedge layer
(Anti-Pattern VIII.9).

Falsifying example: state=WorldState(entities={...}, ...)
```

**Diagnosis**: A System wrote a `MEMBERSHIP` edge from a community node
to an entity. Find the System (search for `EdgeType.MEMBERSHIP` writes
in `src/babylon/engine/systems/`); refactor to use the XGI hypergraph
layer for community memberships.

### Frozen discipline failure

```text
FAILED tests/property/invariants/test_frozen_discipline.py::test_state_bearing_model_is_frozen[SocialClass]
AssertionError: State-bearing model SocialClass must declare
model_config = ConfigDict(frozen=True). Got model_config['frozen']=False
```

OR

```text
FAILED tests/property/invariants/test_frozen_discipline.py::test_no_in_place_mutation_per_tick
AssertionError: In-place mutation detected on entity C001 (class SocialClass):
same id() but field-different. diff: {'wealth': (10.0, 999.0)}

Falsifying example: pre_state=WorldState(...)
```

**Diagnosis**: For Layer 1, restore `model_config = ConfigDict(frozen=True)`.
For Layer 2, find the System whose `step` writes through
`entity.__dict__[...]` or otherwise sidesteps Pydantic; refactor to use
`model_copy(update={...})`.

### Round-trip failure

```text
FAILED tests/property/invariants/test_round_trip_identity.py::test_round_trip_preserves_model_dump
AssertionError: assert {'entities': {'C001': {'wealth': 10.0}}} ==
                {'entities': {'C001': {'wealth': 10.0, 'new_field': 0.5}}}
```

**Diagnosis**: A new field exists on a model class but `to_graph` /
`from_graph` does not yet serialize it. Update both serializer and
deserializer; if the field is computed, add it to the production
`_SOCIAL_CLASS_COMPUTED_FIELDS` (or equivalent) constant so the test's
exclude-set picks it up automatically.

## Reproduce a failing example exactly

Hypothesis records every failing example in `.hypothesis/examples/`. To
reproduce locally:

```bash
poetry run pytest tests/property/invariants/test_<predicate>.py -v --hypothesis-seed=<seed>
```

The seed is printed in the failure output. Default profile uses
`derandomize=True`, so the same seed reproduces deterministically across
runs and machines.

## Add a new bypass marker (rare)

If implementation discovers a System or model class that legitimately
violates a topology invariant, add the opt-out marker:

```python
# On a System:
class MySystem:
    name = "my_system"
    bypasses_topology_invariant: ClassVar[dict[str, str]] = {
        "edge_mode_trajectory_legal": "Performs initialization-only reset of edge_mode at tick 0",
    }

# On a state-bearing model:
class MyValueCacheModel(BaseModel):
    bypasses_topology_invariant: ClassVar[dict[str, str]] = {
        "frozen_discipline": "Internal cache; not part of game state, mutations are local",
    }
    model_config = ConfigDict()  # NOT frozen=True (justified above)
```

The harness will skip the named predicate for that System / class. Empty
justifications fail CI per FR-011 / SC-006.

## Extending the suite

- **New `Invariant` implementation**: add to
  `src/babylon/engine/invariants.py`; instantiate in the appropriate
  test file; update the `data-model.md` §1 entry.
- **New community-node convention**: edit `is_community_node()` in
  `tests/property/harness/topology_harness.py` — single source of truth.
- **New `EdgeMode` value**: add to the enum in `babylon.models.enums`;
  add the legal arcs to `_TRANSITIONS` in `edge_transition.py`. The
  trajectory test picks up both automatically (no test edit needed).
- **New state-bearing model class**: place in `babylon.models.entities/`
  with `model_config = ConfigDict(frozen=True)`. The static frozen
  audit picks it up automatically via `pkgutil.walk_packages`.

## Reference paths

- Spec: `specs/055-topology-invariants/spec.md`
- Plan: `specs/055-topology-invariants/plan.md`
- Research: `specs/055-topology-invariants/research.md`
- Data model: `specs/055-topology-invariants/data-model.md`
- Contracts: `specs/055-topology-invariants/contracts/*.md`
- Production invariants: `src/babylon/engine/invariants.py`
- Edge state machine: `src/babylon/engine/systems/edge_transition.py`
- WorldState: `src/babylon/models/world_state.py`
- Existing harness: `tests/property/harness/`
- Existing strategies: `tests/property/strategies/`
- Existing example round-trip tests: `tests/unit/models/test_graph_roundtrip.py`
