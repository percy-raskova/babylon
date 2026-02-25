# Research: Dialectical Field Topology

**Date**: 2026-02-25
**Feature**: 002-dialectical-field-topology

## R-001: GraphProtocol Integration Pattern

**Decision**: New systems (ContradictionFieldSystem, etc.) use the existing GraphProtocol with auto-wrap guard pattern.

**Rationale**: All 13 existing systems follow this pattern. The protocol provides `query_nodes()`, `query_edges()`, `update_node()`, `update_edge()`, `get_graph_attr()`, `set_graph_attr()` — sufficient for all field operations.

**Key patterns**:
- Auto-wrap: `if not isinstance(graph, GraphProtocol): graph = NetworkXAdapter.wrap(graph)`
- Node iteration: `graph.query_nodes(node_type="social_class")` returns `Iterator[GraphNode]`
- Node write: `graph.update_node(node_id, field=value)` — shallow merge at top level
- Nested dict write: read full dict, rebuild, write entire key back
- Cross-tick state: `context.persistent_data[KEY]` dict survives between ticks

**Alternatives considered**: Direct NetworkX access — rejected because it bypasses the protocol abstraction.

## R-002: Edge Mode vs Edge Type Architectural Gap

**Decision**: Introduce an `edge_mode` attribute on edges as a separate concept from `EdgeType`.

**Rationale**: The codebase has a two-layer edge system:
- **EdgeType** (9 values): Mechanical relationship types — EXPLOITATION, SOLIDARITY, WAGES, TRIBUTE, etc. Used by all 13 systems for specific operations.
- **Edge modes** (constitution I.6): Qualitative categories — EXTRACTIVE, TRANSACTIONAL, SOLIDARISTIC, ANTAGONISTIC. Exist only in documentation and the snapshot layer.

These are different abstraction levels. Multiple EdgeTypes map to one mode (EXPLOITATION, TRIBUTE, WAGES are all aspects of EXTRACTIVE relationships). The modes are qualitative state; the types are mechanical function.

**Implementation**: Add `EdgeMode` enum (5 values including CO-OPTIVE) to `enums.py`. Add `edge_mode` as an attribute on edges via `update_edge()`. Systems that need modal logic query `edge.attributes.get("edge_mode")`. The existing `EdgeType` system remains unchanged.

**Alternatives considered**:
- Replace EdgeType with EdgeMode — rejected: breaks all 13 existing systems.
- Map EdgeType to EdgeMode dynamically — rejected: mapping is not 1-to-1 (SOLIDARITY type can exist in TRANSACTIONAL or SOLIDARISTIC mode contexts).

## R-003: Contradiction Field Storage Architecture

**Decision**: Store contradiction field values as a nested dict on each node, with historical values in `persistent_data`.

**Rationale**: Follows the existing pattern used by ConsciousnessSystem for `previous_wages` / `previous_wealth`. Field values live on nodes via `update_node(node_id, contradiction_fields={"exploitation": 3.2, "immiseration": 1.7, ...})`. History is stored in `persistent_data["contradiction_history"]` keyed by `(node_id, field_name, tick)`.

**Key design**: The field registry is open — a dict of field names to computation functions. Adding a new field requires only registering a new name + computation callable.

**Alternatives considered**: Store fields as separate top-level node attributes (e.g., `contradiction_exploitation=3.2`) — rejected: proliferates attributes and makes field-name-agnostic iteration harder.

## R-004: Ollivier-Ricci Curvature Implementation

**Decision**: Implement custom Wasserstein-1 solver using scipy, not external `pot` library.

**Rationale**:
- `babylon_ricci_final.csv` is trade flow data, NOT pre-computed curvature values. No existing curvature code exists.
- NetworkX has Laplacian support but NOT Ollivier-Ricci.
- The `pot` (Python Optimal Transport) library is not in dependencies.
- For graphs with small node neighborhoods (typical degree < 10 in Detroit metro), Wasserstein-1 reduces to a linear program solvable with `scipy.optimize.linprog()`.
- Adding `pot` as a dependency for one function is disproportionate.

**Algorithm**: For each edge (u, v):
1. Construct probability distributions mu_u, mu_v over neighborhoods (with alpha=0.5 self-loop)
2. Compute Wasserstein-1 distance W(mu_u, mu_v) via `scipy.optimize.linprog()`
3. Curvature kappa(u,v) = 1 - W(mu_u, mu_v) / d(u,v) where d(u,v) = 1 (unweighted)

**Alternatives considered**: `pot` library — rejected as over-dependency. Custom EMD via `scipy.stats.wasserstein_distance` — rejected: that's 1D only, not for graph distributions.

## R-005: Compound Predicate System Design

**Decision**: Data-driven predicate evaluation using a list of condition dicts, not a DSL or expression parser.

**Rationale**: The predicates are conjunctions of threshold comparisons over a fixed vocabulary (field value, df/dt, d2f/dt2, Laplacian, curvature, edge mode). A list of `{"field": "exploitation", "derivative": 0, "operator": ">", "threshold": 0.7}` dicts is sufficient, testable, and serializable. No need for a full expression parser.

**Evaluation**: Each conjunct is checked. If any conjunct references an undefined derivative (insufficient history), that conjunct evaluates to False. The predicate fires only when ALL conjuncts are True.

**Alternatives considered**: Expression string parser (e.g., `"f > 0.7 AND df/dt > 0"`) — rejected: harder to test, serialize, and validate. Lambda/callable predicates — rejected: not serializable to data files.

## R-006: System Ordering

**Decision**: The new systems slot into the existing 13-system order as follows:

```
Existing:                          New:
1. VitalitySystem
2. TerritorySystem
3. ProductionSystem
4. TickDynamicsSystem
5. SolidaritySystem
6. ImperialRentSystem
7. DecompositionSystem
8. ControlRatioSystem
9. MetabolismSystem
10. SurvivalSystem
11. StruggleSystem
12. ConsciousnessSystem
13. ContradictionSystem
14. ContradictionFieldSystem (NEW) — computes field values from economic outputs
15. FieldDerivativeSystem (NEW)    — computes spatial/temporal derivatives
16. EdgeTransitionSystem (NEW)     — evaluates compound predicates, fires transitions
```

**Rationale**: Contradiction fields must be computed AFTER all economic systems have run (systems 1-13 produce the values fields read). Derivatives must follow field computation. Transitions must follow derivatives (predicates reference derivatives).

**Alternatives considered**: Single monolithic system — rejected: violates single-responsibility. Inserting between existing systems — rejected: fields depend on ALL economic outputs.

## R-007: Normalization Scheme

**Decision**: Domain-specific normalization using empirically-grounded bounds per field.

**Rationale**: Min-max normalization is unstable (bounds shift with data). Z-score requires population statistics. Domain-specific bounds (e.g., exploitation rate e=s/v has a natural range based on QCEW data) provide stable, interpretable values. Each field defines its own `[raw_min, raw_max]` mapping to `[0.0, 10.0]`.

**Implementation**: Each registered field provides a normalization function alongside its computation function.

## R-008: Constitution Amendment Required

**Decision**: The constitution (I.6 and I.15) needs amendment to add CO-OPTIVE as the 5th edge mode.

**Rationale**: I.6 defines 4 modes. I.15 defines the transition state machine with 4 modes. The edge-mode-completeness-analysis.md provides the MLM theoretical justification for CO-OPTIVE. This is a constitutional extension, not a violation — new theoretical commitment derived from systematic literature review (Mao, Lenin, Dimitrov, Jackson).

**Action**: Constitution sync should add CO-OPTIVE to I.6 table and extend I.15 transition topology. Version bump to 1.6.0.
