# Data Model: Dialectical Field Topology

**Date**: 2026-02-25
**Feature**: 002-dialectical-field-topology

## Entities

### ContradictionField

A named scalar field computed at every social-class node per tick.

| Attribute | Type | Description |
|-----------|------|-------------|
| name | str (enum-like) | Field identifier: "exploitation", "immiseration", "imperial_rent", "displacement" (extensible) |
| value | float [0.0, 10.0] | Normalized field value at this node/tick |
| raw_value | float | Pre-normalization value from economic calculator |

**Identity**: (node_id, field_name, tick) — unique per node per field per tick.
**Lifecycle**: Created at tick 0 for all nodes and fields. Updated each tick. Never deleted during a run.
**Storage**: Node attribute `contradiction_fields: dict[str, float]` (current tick values).

### FieldDerivatives

Computed spatial and temporal derivatives for each field at each node/edge.

| Attribute | Type | Description |
|-----------|------|-------------|
| gradient | dict[tuple[str,str], float] | Per-edge: grad_f(i,j) = f(j) - f(i) |
| laplacian | float | Per-node: Lf(i) = sum_neighbors(f(j) - f(i)) |
| df_dt | float or None | First temporal derivative (None if < 2 ticks history) |
| d2f_dt2 | float or None | Second temporal derivative (None if < 3 ticks history) |

**Identity**: (node_id or edge_key, field_name, tick).
**Lifecycle**: Computed each tick after field values. Spatial derivatives require at least 1 tick. Temporal derivatives require 2+ ticks.
**Storage**: Node attribute `field_derivatives: dict[str, dict]` mapping field name to `{"laplacian": float, "df_dt": float|None, "d2f_dt2": float|None}`. Edge gradients stored as edge attribute `field_gradients: dict[str, float]`.

### ContradictionHistory

Tick-keyed history of field values for temporal derivative computation.

| Attribute | Type | Description |
|-----------|------|-------------|
| values | dict[str, dict[str, list[float]]] | node_id -> field_name -> [value_at_t-2, value_at_t-1, value_at_t] |

**Storage**: `persistent_data["contradiction_history"]` — survives across ticks via TickContext.
**Retention**: Rolling window of 3 most recent ticks per node per field (sufficient for d2f/dt2).

### EdgeMode

Qualitative category of a social relationship (distinct from EdgeType).

| Value | Description |
|-------|-------------|
| EXTRACTIVE | Unidirectional value flow from exploited to exploiter |
| TRANSACTIONAL | Bidirectional symmetric market exchange |
| SOLIDARISTIC | Bidirectional mutual aid, shared risk |
| ANTAGONISTIC | Oppositional, open conflict |
| CO_OPTIVE | Bidirectional asymmetric, concessions for quiescence |

**Identity**: Per-edge attribute.
**Storage**: Edge attribute `edge_mode: str` (EdgeMode enum value).
**State machine**: Governed by FR-010 transition topology with compound predicates.

### CompoundPredicate

Declarative conjunction of threshold conditions governing state transitions.

| Attribute | Type | Description |
|-----------|------|-------------|
| name | str | Human-readable identifier |
| conditions | list[PredicateCondition] | All must be True for predicate to fire |

### PredicateCondition

A single threshold comparison within a compound predicate.

| Attribute | Type | Description |
|-----------|------|-------------|
| field | str | Contradiction field name |
| metric | str | One of: "value", "df_dt", "d2f_dt2", "laplacian", "curvature", "edge_mode" |
| operator | str | One of: ">", ">=", "<", "<=", "==", "!=" |
| threshold | float or str | Numeric threshold or enum value for edge_mode comparisons |
| scope | str | "source", "target", or "edge" — which end of the edge to evaluate |

### EdgeModeTransition

A permissible transition in the edge mode state machine.

| Attribute | Type | Description |
|-----------|------|-------------|
| from_mode | EdgeMode | Source mode |
| to_mode | EdgeMode | Target mode |
| predicate | CompoundPredicate | Condition that triggers this transition |
| priority | int | Resolution order when multiple transitions eligible (lower = higher priority) |
| description | str | Human-readable transition name |

### PrincipalContradiction

Per-tick identification of the dominant contradiction field.

| Attribute | Type | Description |
|-----------|------|-------------|
| field_name | str | Name of the principal contradiction |
| max_abs_df_dt | float | The largest |df/dt| that determined selection |
| changed | bool | Whether principal contradiction changed from previous tick |

**Storage**: Graph-level attribute `principal_contradiction: dict`.

### ContinuityResidual

Per-node, per-tick accounting of contradiction flow balance.

| Attribute | Type | Description |
|-----------|------|-------------|
| node_id | str | Node identifier |
| field_name | str | Contradiction field |
| delta_f | float | Change in field value this tick |
| net_flow | float | Sum of gradients along adjacent edges |
| residual | float | delta_f - net_flow |
| mechanism | str or None | Named mechanism if residual is accounted for (e.g., "wage_increase", "co_optive_suppression") |

**Storage**: Node attribute `continuity_residuals: dict[str, dict]` and/or `persistent_data` for historical diagnostics.

### OllivierRicciCurvature

Structural property of each edge, cached between topology changes.

| Attribute | Type | Description |
|-----------|------|-------------|
| curvature | float | Ollivier-Ricci curvature value |
| computed_at_tick | int | Tick when last computed |

**Storage**: Edge attribute `ricci_curvature: float` and `ricci_computed_tick: int`.
**Invalidation**: Recomputed when graph topology changes (node/edge added/removed).

### LatentContradiction (CO-OPTIVE specific)

Suppressed contradiction accumulated during co-optation.

| Attribute | Type | Description |
|-----------|------|-------------|
| node_id | str | Co-opted node |
| field_name | str | Suppressed contradiction field |
| accumulated | float | Total suppressed df/dt over co-optation duration |
| source_edge | tuple[str, str] | The CO-OPTIVE edge responsible |

**Storage**: `persistent_data["latent_contradictions"]` keyed by (node_id, field_name, source_edge).
**Release**: When CO-OPTIVE edge transitions away, accumulated latent contradiction produces df/dt spike.

## Relationships

```
ContradictionField ──computed_at──► Node (social_class)
FieldDerivatives ──derived_from──► ContradictionField
FieldDerivatives.gradient ──along──► Edge
CompoundPredicate ──governs──► EdgeModeTransition
EdgeModeTransition ──applied_to──► Edge (via edge_mode attribute)
PrincipalContradiction ──selected_from──► ContradictionField (max |df/dt|)
ContinuityResidual ──accounts_for──► ContradictionField (per node)
OllivierRicciCurvature ──cached_on──► Edge
LatentContradiction ──suppressed_by──► CO-OPTIVE Edge
```

## Validation Rules

1. Field values MUST be in [0.0, 10.0] after normalization (EC-007: clamp and log if exceeded).
2. Temporal derivatives MUST be None (not 0.0) when insufficient history exists (EC-001).
3. Laplacian at isolated nodes (degree 0) MUST be 0.0 with a warning (EC-002).
4. EdgeMode transitions MUST follow the state machine in FR-010. Prohibited transitions raise errors.
5. CO-OPTIVE edges MUST declare which fields they suppress (per-edge configurable, FR-014).
6. CO-OPTIVE edges with zero material flow are invalid and MUST transition (EC-010).
7. Curvature values MUST only be recomputed when topology changes, not per-tick (FR-005).
