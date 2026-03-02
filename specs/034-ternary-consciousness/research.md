# Research: 034-ternary-consciousness

**Date**: 2026-03-01
**Status**: Complete

## R1: Existing CommunityConsciousness Model

**Decision**: Replace internal representation of `CommunityConsciousness` with ternary (r, l, f) coordinates while preserving the external interface via computed properties.

**Findings**:
- `CommunityConsciousness` is at `src/babylon/models/entities/community.py:236-258`
- Frozen Pydantic model with 3 fields: `collective_identity` (Probability, default 0.3), `dominant_tendency` (ConsciousnessTendency, default LIBERAL), `ideological_contestation` (Probability, default 0.2)
- No computed fields or properties on `CommunityConsciousness` itself
- Embedded in `CommunityState` as `consciousness` field (line 406)
- `CommunityState` has 2 computed fields that read consciousness:
  - `infiltration_resistance`: `CI * 0.6 + cohesion * 0.3 + CI * cohesion * 0.1`
  - `is_cross_class_bridge`: returns True for INSTITUTIONAL_EXCLUSION category (does NOT read consciousness)
- `CONSCIOUSNESS_DEFAULTS` dict at lines 263-338 maps all 14 `CommunityType` values to pre-built instances
- Import-time exhaustiveness check at lines 341-343 ensures all types have defaults

**Rationale**: The ternary model replaces the 3 stored fields with 3 new stored fields (r, l, f) and provides the old 3 as computed properties. This is the minimum-disruption migration path.

**Alternatives Considered**:
- Subclass CommunityConsciousness: Rejected — frozen Pydantic models don't compose well via inheritance for field replacement
- Parallel model alongside existing: Rejected — two sources of truth

## R2: Organization Model and Membership

**Decision**: Use `budget` (Currency) instead of `resource_base` (which does not exist), and derive per-community membership from MEMBERSHIP edge weights.

**Findings**:
- Organization model at `src/babylon/models/entities/organization.py:112-208`
- **Critical spec correction**: The spec references `resource_base` field — this does NOT exist. The financial resource field is `budget: Currency`
- `consciousness_tendency: ConsciousnessTendency` field exists at line 168 (default LIBERAL)
- Membership is NOT stored per-community on the Organization model
- Membership is tracked via MEMBERSHIP edge weights in the graph: org → social_class edges
- `composition.py:19-26` computes total members by summing MEMBERSHIP edge weights
- Org-community overlap computed at runtime via `action_costs.py:85-120`: intersection of org MEMBERSHIP targets with community member_node_ids
- Organization subtypes: StateApparatus, Business, PoliticalFaction, CivilSocietyOrg (discriminated union)
- `cadre_level` (Probability) and `cohesion` (Probability) are the capacity multipliers used in consciousness delta formulas
- CivilSocietyOrg has `legitimacy` (Probability) used as credibility

**Rationale**: The ternary computation needs per-community membership density. This requires querying MEMBERSHIP edges filtered by community members, which is already implemented in `action_costs.py:85-120` and `action_effects.py:249-296`. Reuse this pattern.

## R3: Two Consciousness Representations

**Decision**: The ternary computation unifies the two existing representations by computing from organizational landscape (replacing both the Pydantic model storage and the raw graph node dict storage).

**Findings**:
- **Representation 1 (Pydantic)**: `CommunityState.consciousness: CommunityConsciousness` — used by CommunitySystem, bifurcation analysis, organizations modules. Access pattern: `state.consciousness.collective_identity`
- **Representation 2 (Graph dict)**: `graph.nodes[community_id]["collective_identity"]` — used by OODA layer3.py and action_effects.py. These are plain floats stored as node attributes
- `build_community_hypergraph()` (community.py:82-84) bridges Pydantic → XGI hyperedge attributes (a third representation: `consciousness_ci`, `consciousness_tendency`, `consciousness_contestation`)
- The OODA layer MUTATES consciousness via raw graph dict writes (layer3.py:89-91, 263-264). This is the primary mutation path
- Organizations/consciousness.py computes `ConsciousnessDelta` per org: `delta = tendency_modifier * cadre_level * cohesion * credibility`
- `aggregate_consciousness_effects()` sums deltas and determines dominant tendency

**Impact**: The ternary model replaces the OODA consciousness mutation path. Instead of computing deltas and writing CI back to graph nodes, the system recomputes ternary coordinates from the organizational landscape each tick. The OODA actions that currently modify consciousness (EDUCATE, AGITATE, ORGANIZE) instead modify the organizational landscape (membership, edge type, etc.) and consciousness follows automatically.

## R4: Bifurcation Topology Integration

**Decision**: The `consciousness_weighted_solidarity` function's consumption of `collective_identity` maps directly to the ternary `r` component with no formula changes needed.

**Findings**:
- `consciousness_weighted_solidarity()` at `src/babylon/bifurcation/consciousness.py:107-151`
- Reads `state.consciousness.collective_identity` via `_agent_mean_marginalized_ci()` (lines 64-104)
- Filters to MARGINALIZED_COMMUNITIES only (9 of 14 types)
- Takes weakest-link: `effective_ci = min(source_ci, target_ci)`
- Applies sigmoid: `1 / (1 + exp(-steepness * (ci - midpoint)))`
- Returns: `solidarity_strength * sigmoid_weight`
- BifurcationMonitor is standalone — not yet wired into SimulationEngine tick execution
- `BifurcationResult` carries `mean_collective_identity_marginalized` and `dominant_tendency_distribution`

**Rationale**: Since `collective_identity` maps to `r` in the ternary model, the bifurcation formulas need no modification. The `assimilation_ratio` and crisis-fragility markers are NEW capabilities layered on top.

## R5: Postgres Schema Impact

**Decision**: The postgres schema already stores `collective_identity`, `dominant_tendency`, `ideological_contestation` as flat columns. These become computed from (r, l, f) which are the new stored columns.

**Findings**:
- `postgres_schema.py:149-151`: Three columns in `community_state` table
- `postgres_runtime.py:317-318, 329-331`: INSERT and UPDATE reference these columns
- Values read as raw dict: `state.get("collective_identity", 0.0)` etc.

**Impact**: Schema migration adds `r FLOAT`, `l FLOAT`, `f FLOAT` columns. The old three columns become derived (or removed, pending backward-compat window).

## R6: Spec Correction — resource_base → budget

**Decision**: The spec references `resource_base` as a field on Organization. This field does not exist. The correct field is `budget: Currency`. The implementation plan MUST use `budget` in the consciousness computation formula.

**Finding**: Searched all Organization model code and all 4 subtypes. No field named `resource_base` exists anywhere. The closest is `budget: Currency` (default 0.0) on the base Organization class.

**Impact**: Acceptance scenario 1 references "resource base 1.0" — implementation should use `float(org.budget)` or a normalized budget metric as the capacity multiplier.
