# Contract: Ternary Simplex Pipeline (US3 — INV-008)

**Predicate ID**: INV-008
**User Story**: US3 (P2)
**Source**: [spec.md §US3](../spec.md#user-story-3--ternary-consciousness-simplex-preserved-across-the-pipeline-priority-p2)
**Tests**: `tests/property/invariants/test_simplex_pipeline.py`
**Invariant class**: `babylon.engine.invariants.SimplexPreserved`

## Predicate

For every entity in the post-state with a
`consciousness: TernaryConsciousness` field:

```text
∀ entity ∈ post.entities where entity.consciousness is not None:
    abs(c.r + c.l + c.f - 1.0) <= tol(N, |c.r+c.l+c.f|)
    -tol <= c.r <= 1.0 + tol
    -tol <= c.l <= 1.0 + tol
    -tol <= c.f <= 1.0 + tol
```

where `c = entity.consciousness` and `tol(N, mag)` is the magnitude-aware
helper from `harness/__init__.py:_tol` (extracted from Spec 053 per
research §9).

**Default `tol`**: `1e-4` per spec acceptance scenario US3.1. The
multi-tick variant (US3.2) uses the same `tol` — drift across 5 ticks is
expected to be O(5 × per-tick float64 round-off) which is well under
`1e-4`.

## Inputs (Hypothesis strategies)

| Strategy | Source |
|----------|--------|
| `worldstate_with_simplex_consciousness_strategy()` | `tests/property/strategies/worldstate.py` |
| `simplex_points()` | re-exported from `tests/test_simplex_invariants.py` via `tests/property/strategies/consciousness_simplex.py` |

## Test predicates

### Predicate A — Single-tick preservation (US3.1)

```python
@given(state=worldstate_with_simplex_consciousness_strategy())
@settings()
def test_simplex_preserved_single_tick(state, service_container_fixture, tick_context_fixture):
    post = SimulationEngine.run_tick(state.to_graph(), service_container_fixture, tick_context_fixture)
    post_state = WorldState.from_graph(post)
    invariant = SimplexPreserved(tolerance=1e-4)
    result = invariant.check(state, post_state)
    assert result.ok, result.msg
```

### Predicate B — Multi-tick stability (US3.2)

```python
@given(state=worldstate_with_simplex_consciousness_strategy())
@settings()
def test_simplex_preserved_five_ticks(state, service_container_fixture):
    invariant = SimplexPreserved(tolerance=1e-4)
    current = state
    for tick_idx in range(5):
        ctx = TickContext(tick=tick_idx)
        post_graph = SimulationEngine.run_tick(current.to_graph(), service_container_fixture, ctx)
        post = WorldState.from_graph(post_graph)
        result = invariant.check(current, post)
        assert result.ok, f"Tick {tick_idx}: {result.msg}"
        current = post
```

### Predicate C — Routing-layer simplex (US3.3)

```python
@given(
    agitation=st.floats(min_value=0.1, max_value=10.0, allow_nan=False),
    solidarity=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    edu_pressure=st.floats(min_value=0.0, max_value=0.8, allow_nan=False),
    starting_point=simplex_points(),
)
@settings()
def test_route_agitation_preserves_simplex(agitation, solidarity, edu_pressure, starting_point):
    r0, l0, f0 = starting_point
    defines = ConsciousnessDefines()
    dr, dl, df = route_agitation_to_ternary(agitation, solidarity, edu_pressure, defines)
    r1, l1, f1 = r0 + dr, l0 + dl, f0 + df
    assert abs(r1 + l1 + f1 - 1.0) <= 1e-4
    assert all(-1e-4 <= comp <= 1.0 + 1e-4 for comp in (r1, l1, f1))
```

## Failure modes

| Cause | Symptom | Remediation |
|-------|---------|-------------|
| A System writes raw `(r, l, f)` to graph node data without renormalizing | Predicate A fails after one tick | Apply `normalize_to_simplex(r, l, f)` before write |
| Cumulative float64 drift over many ticks | Predicate B fails after N ticks | Insert a periodic renormalization (e.g., every 10 ticks); update `_tol` if drift is unavoidable |
| `route_agitation_to_ternary` violates the simplex | Predicate C fails | Fix the routing math; this is in `formulas/consciousness_routing.py` |
| Formula legitimately produces a non-simplex intermediate that is renormalized in the System | Predicate C fails on the formula | Add `bypasses_bound_invariant = {"simplex_preserved": "<reason>"}` to the formula's module |

## Out of scope

- Existing `tests/test_simplex_invariants.py` covers per-construction
  simplex preservation. This spec adds the per-pipeline coverage.
- Substrate-floor enforcement (`SUBSTRATE_FLOOR_DEFAULTS` in
  `models/entities/consciousness.py`) — already tested by
  `test_substrate_floor_respected_in_constructor`.
- Shannon entropy bounds — already tested by
  `test_shannon_entropy_bounds`.
