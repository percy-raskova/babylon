# GraphProtocol Extensions: Balkanization

The existing `GraphProtocol` (in `src/babylon/engine/graph_protocol.py`)
provides core node/edge operations. Spec-070 requires additional
query methods that are sufficiently common across the three new
Systems to warrant first-class GraphProtocol methods rather than
ad-hoc filter-then-iterate patterns.

These extensions are ADDITIONS — the existing protocol surface is
unchanged. The default `NetworkXAdapter` and the planned
`PostgresAdapter` (per spec-037 follow-up) MUST both implement
the new methods.

## New Query Methods

### `query_faction_influence_by_territory(territory_id: str) → list[(faction_id, influence_level, support_type)]`

Returns all INFLUENCES edges pointing at the given Territory,
sorted by `influence_level` descending. Used by
`FactionInfluenceSystem` for per-Territory winning-Faction
resolution (FR-021).

**Default impl** (`NetworkXAdapter`): filter
`in_edges(territory_id, data=True)` by `edge_type=INFLUENCES`,
extract attributes, sort.

**Postgres impl**: SQL query
`SELECT faction_id, influence_level, support_type FROM
runtime_influences_edges WHERE territory_id = $1 ORDER BY
influence_level DESC`.

### `query_sovereign_claims(sovereign_id: str) → list[(territory_id, control_level, legal_status)]`

Returns all CLAIMS edges originating from the given Sovereign,
sorted by `control_level` descending. Used by
`SovereigntySystem` and `CollapseTransitionSystem` for
per-Sovereign Territory enumeration.

**Default impl**: filter `out_edges(sovereign_id, data=True)` by
`edge_type=CLAIMS`, extract attributes, sort.

### `query_territory_claims(territory_id: str) → list[(sovereign_id, control_level, legal_status)]`

Returns all CLAIMS edges pointing at the given Territory, sorted
by `control_level` descending. Used by `SovereigntySystem` for
dual-power detection (FR-035) and effective-controller resolution
(FR-020).

### `query_adjacent_territories(territory_id: str) → set[str]`

Returns the set of Territory IDs adjacent to the given Territory
via `EdgeType.ADJACENCY`. Used by `FactionInfluenceSystem` for
contiguity BFS during active-secession detection (FR-029b).

**Default impl**: filter `all_edges(territory_id)` by
`edge_type=ADJACENCY`, return the set of "other" endpoints.

**Note**: `EdgeType.ADJACENCY` edges are bidirectional in the
existing graph (per spec-001 Sprint 3.5.1 semantics); this method
abstracts the direction handling.

### `bulk_partition_claims(from_sovereign_id: str, to_sovereign_id: str, territories: set[str]) → int`

Atomically rewires CLAIMS edges from one Sovereign to another for
the given Territory set. Used by `CollapseTransitionSystem` for
the fracture operation (FR-027).

**Performance requirement (FR-018)**: This operation MUST be
implementable in O(K) where K is the size of the moving territory
set — NOT O(N) where N is the size of the unaffected territory
set. The signature explicitly takes the moving set as input
rather than computing it from the full claim set, enabling
adapters to implement true O(K) rewiring.

**Default impl** (`NetworkXAdapter`): for each `t in territories`,
delete `(from_sovereign_id, t)` edge and create `(to_sovereign_id,
t)` edge. K operations.

**Returns**: count of edges rewired.

### `query_contiguous_component_under_predicate(territory_seed: str, predicate: Callable[[str], bool]) → set[str]`

BFS from `territory_seed`, traversing `EdgeType.ADJACENCY`,
collecting all Territories that satisfy `predicate(territory_id)`.
Used by `FactionInfluenceSystem` for contiguity check (FR-029b)
where `predicate = lambda t: faction_influence_in(t) > 0.5`.

**Performance**: Bounded by the size of the contiguous predicate-
satisfying region (NOT the global graph size), per FR-018's O(1)-in-
unchanged-territory-count requirement.

**Default impl** (`NetworkXAdapter`): standard BFS using
`networkx.bfs_edges` filtered by predicate. For the N=1000
benchmark per SC-004, this MUST not exceed O(K) where K is the
contiguous-region size.

## Determinism Notes

All new methods MUST produce results in deterministic order:

- `query_faction_influence_by_territory` and `query_sovereign_claims`
  and `query_territory_claims`: SORT by the primary numeric attribute
  descending; break ties by lexicographic ID of the "other" endpoint.
- `query_adjacent_territories`: return as a sorted list (caller
  receives a set conceptually, but materialised iteration order is
  deterministic).
- `query_contiguous_component_under_predicate`: BFS visit order is
  by lexicographic Territory ID at each frontier level.

These determinism guarantees are part of the contract, not
implementation-defined behavior.

## Adapter Verification

Both `NetworkXAdapter` and the future `PostgresAdapter` MUST pass
a shared contract test suite (`tests/unit/balkanization/test_graph_protocol_extensions.py`)
that verifies:

1. All six new methods are implemented.
2. Each method returns the documented type signature.
3. Each method honors the determinism guarantees.
4. `bulk_partition_claims` does NOT scale with unchanged-territory
   count (Hypothesis property test at N ∈ {10, 100, 1000}).
5. `query_contiguous_component_under_predicate` does NOT scale
   with global graph size (Hypothesis property test).
