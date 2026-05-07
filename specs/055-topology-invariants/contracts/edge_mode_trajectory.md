# Contract: Edge Mode Trajectory Legality (US1 — INV-009)

**Predicate ID**: INV-009
**User Story**: US1 (P1)
**Source**: [spec.md §US1](../spec.md#user-story-1--edge-mode-trajectory-legality-across-n-evidence-events-priority-p1)
**Tests**: `tests/property/invariants/test_edge_mode_trajectory.py`
**Invariant class**: `babylon.engine.invariants.EdgeModeTrajectoryLegal`

## Predicate

For every edge that carries an `edge_mode` attribute, observed across a
sequence of evidence events:

```text
∀ i ∈ [0, N), ∀ edge in graph at tick i:
    (edge.mode_at_tick_{i}, edge.mode_at_tick_{i+1}) ∈ _VALID_TRANSITIONS
    OR edge.mode_at_tick_{i} == edge.mode_at_tick_{i+1}  # trivial no-transition

∀ edge in final post-graph:
    edge.edge_mode ∈ EdgeMode  # final mode is a legal enum value
```

**Tolerance**: Exact set membership; the legal-arc set
`_VALID_TRANSITIONS` is imported by reference from
`babylon.engine.systems.edge_transition`.

**Trivial transitions**: A pair `(m, m)` for any mode `m ≠ ANTAGONISTIC`
is implicitly legal (no transition occurred — no predicate fired). The
only `(m, m)` pair that is also explicitly in `_VALID_TRANSITIONS` is
`(ANTAGONISTIC, ANTAGONISTIC)` (persistence). The test counts trivial
no-transitions and explicit persistence transitions separately for
trajectory-coverage statistics per FR-012.

## Inputs (Hypothesis strategies)

| Strategy | Source | Branch |
|----------|--------|--------|
| `edge_mode_trajectory_strategy()` | `tests/property/strategies/edge_mode_evidence.py` | Synthesized (a) |
| `worldstate_strategy(min_entities=2, max_relationships=4)` | `tests/property/strategies/worldstate.py` | Observed (b) |

The synthesized strategy generates `(starting_mode, events)` tuples
where `events` is a list of ≥ 10 evidence-event dicts each containing
`{field, metric, value, scope}`. The observed strategy generates a full
`WorldState` for end-to-end pipeline runs.

## Test predicates

### Predicate A — Synthesized trajectory legality (US1 branch a)

```python
@given(trajectory_input=edge_mode_trajectory_strategy())
@settings(max_examples=100, derandomize=True)
def test_synthesized_trajectory_is_legal(trajectory_input, services_fixture, ctx_fixture):
    starting_mode, events = trajectory_input
    graph = _build_two_node_graph(starting_mode)
    system = EdgeTransitionSystem()
    modes_observed = [starting_mode]

    for event in events:
        _apply_event_to_graph(graph, event)
        system.step(graph, services_fixture, ctx_fixture)
        new_mode = _read_edge_mode(graph)
        modes_observed.append(new_mode)

    # Pairwise legality check
    for i, (prev, cur) in enumerate(zip(modes_observed[:-1], modes_observed[1:])):
        if prev == cur:
            continue  # trivial no-transition tick — legal by definition
        assert (prev, cur) in _VALID_TRANSITIONS, (
            f"Illegal arc at step {i}: ({prev} -> {cur}). "
            f"Trajectory: {modes_observed}"
        )

    # Final mode must be a legal enum value
    assert modes_observed[-1] in EdgeMode
```

### Predicate B — Observed end-to-end trajectory legality (US1 branch b)

```python
@given(state=worldstate_strategy(min_entities=2, max_relationships=4))
@settings(max_examples=20, derandomize=True)  # smaller — full pipeline cost
def test_observed_trajectory_is_legal(state, services_fixture, ctx_fixture):
    pre_modes = _capture_edge_modes(state.to_graph())  # {edge_id: EdgeMode}
    systems = [cls() for cls in all_systems()]
    engine = SimulationEngine(systems=systems)

    for tick in range(5):
        graph = state.to_graph()
        engine.run_tick(graph, services_fixture, ctx_fixture)
        state = WorldState.from_graph(graph, tick=state.tick + 1)
        post_modes = _capture_edge_modes(graph)

        # Check legality for every edge present in both pre and post
        for edge_id in pre_modes.keys() & post_modes.keys():
            prev = pre_modes[edge_id]
            cur = post_modes[edge_id]
            if prev == cur:
                continue
            assert (prev, cur) in _VALID_TRANSITIONS, (
                f"Tick {tick} edge {edge_id}: illegal arc ({prev} -> {cur})"
            )
        pre_modes = post_modes
```

### Predicate C — Final mode is always a legal `EdgeMode` value

Combined into Predicate A's final assertion (`modes_observed[-1] in
EdgeMode`); also asserted in Predicate B's per-tick `_capture_edge_modes`
helper which constructs `EdgeMode(value)` and propagates `ValueError` if
the value is malformed.

## Failure modes

| Cause | Symptom | Remediation |
|-------|---------|-------------|
| A new transition is added to `_TRANSITIONS` but the predicate is wrong | Predicate A fails on a synthesized event sequence; trajectory shows the illegal arc | Fix the predicate or the arc declaration in `edge_transition.py`; the test imports `_VALID_TRANSITIONS` so no test edit is needed |
| `EdgeTransitionSystem` writes a stale string instead of a fresh `EdgeMode` | Predicate B fails when `EdgeMode(value)` raises | Find the writer; ensure all writes go through `EdgeMode(...)` constructor |
| `EXTRACTIVE → SOLIDARISTIC` arc is silently added | Predicate A fails: the offending arc is not in `_VALID_TRANSITIONS` | Either add `(EXTRACTIVE, SOLIDARISTIC)` to `_VALID_TRANSITIONS` (intentional dialectical-model change) OR remove the predicate that produced the leap (bug fix) |

## Out of scope

- Predicate firing logic itself (already covered by per-transition
  example tests in `tests/unit/engine/systems/test_edge_transition.py`).
- Aspect reversal logic (separate System-level concern).
- CO-OPTIVE suppression accumulator (separate System-level concern).
