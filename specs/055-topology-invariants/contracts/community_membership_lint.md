# Contract: Hyperedges-not-pairwise Lint (US2 — INV-010)

**Predicate ID**: INV-010
**User Story**: US2 (P1)
**Source**: [spec.md §US2](../spec.md#user-story-2--hyperedges-not-pairwise-structural-linter-priority-p1)
**Tests**: `tests/property/invariants/test_community_membership_lint.py`
**Invariant class**: `babylon.engine.invariants.NoCommunityFanOut`
**Constitution**: II.7 (Edges vs Hyperedges), Anti-Pattern VIII.9

## Predicate

For every `EdgeType.MEMBERSHIP` edge in the post-graph:

```text
∀ edge ∈ post.graph.edges where edge.type == EdgeType.MEMBERSHIP:
    is_community_node(graph, edge.source_id) is False
```

Where `is_community_node(graph, node_id)` returns `True` iff
`graph.nodes[node_id].get("_node_type") == "community"` (resolved by Q1
clarification).

## Inputs (Hypothesis strategies)

| Strategy | Source |
|----------|--------|
| `worldstate_with_community_node_strategy()` | `tests/property/strategies/worldstate.py` (NEW per FR-004) |

The strategy returns a tuple `(WorldState, frozenset[str])` where the
second element is the set of node IDs to mark as community nodes (per
`data-model.md §3.3`). Tests unpack the tuple, call `state.to_graph()`,
inject the markers via `_inject_community_markers(graph,
community_node_ids)` from `tests/property/harness/topology_harness.py`,
then run their assertions. Relationships sample uniformly from `EdgeType`
so MEMBERSHIP edges are exercised; tests assert that no MEMBERSHIP edge
has a community source in any post-state.

## Test predicates

### Predicate A — Linter on full-pipeline post-state

```python
@given(strategy_output=worldstate_with_community_node_strategy())
@settings(max_examples=100, derandomize=True)
def test_no_community_fan_out_post_pipeline(strategy_output, services_fixture, ctx_fixture):
    state, community_node_ids = strategy_output
    systems = [cls() for cls in all_systems()]
    engine = SimulationEngine(systems=systems)
    graph = state.to_graph()
    _inject_community_markers(graph, community_node_ids)
    engine.run_tick(graph, services_fixture, ctx_fixture)
    post_state = WorldState.from_graph(graph, tick=state.tick + 1)

    invariant = NoCommunityFanOut()
    result = invariant.check(state, post_state)
    assert result.ok, result.msg
```

### Predicate B — MEMBERSHIP edge count delta is non-negative for legitimate sources

```python
@given(strategy_output=worldstate_with_community_node_strategy())
@settings(max_examples=50, derandomize=True)
def test_membership_count_delta_is_legitimate_only(strategy_output, services_fixture, ctx_fixture):
    state, community_node_ids = strategy_output
    graph = state.to_graph()
    _inject_community_markers(graph, community_node_ids)
    engine = SimulationEngine(systems=[cls() for cls in all_systems()])
    engine.run_tick(graph, services_fixture, ctx_fixture)

    post_membership_count = _count_membership_edges(graph, exclude_community_sources=False)
    post_legitimate_count = _count_membership_edges(graph, exclude_community_sources=True)

    # Count of community-fan-out edges (illegitimate) MUST be 0 in post
    illegitimate_post = post_membership_count - post_legitimate_count
    assert illegitimate_post == 0, (
        f"Found {illegitimate_post} community-fan-out MEMBERSHIP edges in post-graph"
    )
```

### Predicate C — Seeded violation is caught

```python
def test_seeded_community_fan_out_is_detected(services_fixture, ctx_fixture):
    """Negative test — seed a deliberate violation and confirm the linter catches it."""
    state = _build_minimal_state(entity_ids=["COMM_001", "C001"])
    graph = state.to_graph()
    _inject_community_markers(graph, frozenset(["COMM_001"]))
    # Deliberately seed a community-fan-out edge directly on the graph
    graph.add_edge("COMM_001", "C001", edge_type=EdgeType.MEMBERSHIP)
    post_state = WorldState.from_graph(graph, tick=state.tick + 1)

    invariant = NoCommunityFanOut()
    result = invariant.check(state, post_state)
    assert not result.ok
    assert "COMM_001" in result.msg
    assert "MEMBERSHIP" in result.msg
```

## Failure modes

| Cause | Symptom | Remediation |
|-------|---------|-------------|
| A System wires up `MEMBERSHIP` from a community node to its members | Predicate A fails; failure msg names the offending `(community_id, member_id)` triple | Refactor the System to use the XGI hypergraph layer for community memberships, NOT pairwise MEMBERSHIP edges |
| The codebase convention shifts (e.g., `_node_type` is renamed) | Predicates A/B/C all fail with `is_community_node` returning `False` everywhere; seeded violation in C is no longer caught | Update `is_community_node()` in one place to match the new convention; tests resume working |
| A legitimate organization → SocialClass MEMBERSHIP edge happens to share an ID with a community node | Predicate A fails on a false positive | Confirm the source node IDs really are non-overlapping (community IDs and organization IDs MUST be disjoint at the schema level); if they're not, that's a separate schema bug |

## Out of scope

- The XGI hyperedge layer's own integrity (separate spec when Amendment D
  ratifies).
- Other illegitimate edge fan-out patterns (e.g., institution fan-outs)
  — only community→member is in scope per VIII.9.
- Source-side audits for non-MEMBERSHIP edges (RECRUITMENT, EMPLOYMENT,
  COMMAND, PRESENCE) — these are legitimately pairwise per their
  `EdgeType` docstrings.
