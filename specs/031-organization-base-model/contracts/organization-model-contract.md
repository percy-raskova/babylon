# Contract: Organization Model

**Feature**: 031-organization-base-model
**Date**: 2026-02-27

## Purpose

Defines how Organization entities (base + 4 subtypes) are created, validated, serialized to/from the graph, and mutated. This is the data contract — all callers of the Organization model must respect these rules.

## Contract: Organization Creation

### Preconditions

1. `id` is a non-empty, unique string (no other node with this ID exists in the graph).
2. `name` is a non-empty string.
3. `org_type` is a valid `OrgType` enum value matching the subtype being created.
4. `class_character` is a valid `ClassCharacter` enum value (BOURGEOIS, PETTY_BOURGEOIS, LABOR_ARISTOCRATIC, PROLETARIAN, LUMPEN, or CONTESTED).
5. All `Probability`-typed fields are in `[0, 1]`.
7. All `Currency`-typed fields are in `[0, inf)`.
8. `territory_ids` contains only IDs of existing Territory nodes.
9. `headquarters_id`, if set, is contained in `territory_ids`.
10. `institutional_persistence` is `None` if `is_institution` is `False`.
11. `member_node_ids` contains only IDs of existing KeyFigure or cadre nodes.

### Postconditions

1. A frozen Pydantic model is returned; all fields are immutable.
2. `model_config = ConfigDict(frozen=True)` is enforced.
3. The `org_type` field matches the subtype's `Literal` declaration.
4. All default values are applied for omitted optional fields.
5. There is NO `internal_topology` field — topology is computed from COMMAND edges via `classify_topology()`.

### Error Conditions

| Condition | Error Type | Message Pattern |
|-----------|-----------|-----------------|
| Missing required field | `ValidationError` | `Field required` |
| Probability out of bounds | `ValidationError` | `Input should be >= 0 and <= 1` |
| Currency negative | `ValidationError` | `Input should be >= 0` |
| Empty `id` or `name` | `ValidationError` | `String should have at least 1 character` |
| Invalid enum value | `ValidationError` | `Input should be 'VALUE1', 'VALUE2', ...` |
| `institutional_persistence` set when `is_institution=False` | `ValidationError` | `institutional_persistence must be None when is_institution is False` |
| `headquarters_id` not in `territory_ids` | `ValidationError` | `headquarters_id must be in territory_ids` |

## Contract: Subtype Dispatch (Discriminated Union)

### Mechanism

```
Annotated[
    Union[StateApparatus, Business, PoliticalFaction, CivilSocietyOrg],
    Field(discriminator="org_type")
]
```

### Dispatch Rules

| `org_type` Value | Subtype Created |
|-----------------|----------------|
| `OrgType.STATE_APPARATUS` | `StateApparatus` |
| `OrgType.BUSINESS` | `Business` |
| `OrgType.POLITICAL_FACTION` | `PoliticalFaction` |
| `OrgType.CIVIL_SOCIETY` | `CivilSocietyOrg` |

### Subtype-Specific Preconditions

**StateApparatus**:
- `jurisdiction` is a valid `JurisdictionLevel`.
- `violence_capacity` and `surveillance_capacity` are `Probability` [0, 1].
- `intel_methodology` is an `IntelMethodology` instance (default factory if omitted).
- `legal_standing` defaults to `SOVEREIGN` (soft warning if set to non-SOVEREIGN).

**Business**:
- `sector` is a non-empty string.
- `employment_count` is a non-negative integer.
- `surplus_extraction_rate` is a `Coefficient` [0, 1].
- `revenue` is `Currency` [0, inf).

**PoliticalFaction**:
- `ideology` is a non-empty string.
- `is_player` is a boolean.
- `relationship_to_player` is a string (default: `"neutral"`).

**CivilSocietyOrg**:
- `service_type` is a valid `ServiceType`.
- `legitimacy` is `Probability` [0, 1] (default: 0.5).

## Contract: Graph Serialization (to_graph)

### Preconditions

1. Organization instance is valid (passes all creation preconditions).
2. Target graph implements `GraphProtocol`.

### Algorithm

```
1. Call org.model_dump() to get all fields as a dict.
2. Add node to graph: G.add_node(org.id, _node_type="organization", **dumped_fields)
3. For each territory_id in org.territory_ids:
     Add edge: (org.id, territory_id, EdgeType.PRESENCE)
4. For each member_node_id in org.member_node_ids:
     Verify node exists in graph (KeyFigure or cadre).
```

### Postconditions

1. Graph contains a node with `_node_type="organization"` and the org's ID.
2. All org fields are stored as node attributes.
3. PRESENCE edges exist for all territory_ids.

## Contract: Graph Deserialization (from_graph)

### Preconditions

1. Graph node has `_node_type="organization"`.
2. Node attributes contain at minimum: `id`, `name`, `org_type`.

### Algorithm

```
1. Extract node data (all attributes except _node_type).
2. Filter out excluded fields: organization_excluded = {"effective_capacity", "composition_cache"}
3. Dispatch on org_type to reconstruct correct subtype.
4. Return frozen Organization instance.
```

### Postconditions

1. Returned instance is the correct subtype matching `org_type`.
2. All stored fields are restored.
3. Computed/excluded fields are NOT in the reconstructed instance.

### Error Conditions

| Condition | Error Type | Description |
|-----------|-----------|-------------|
| Missing `org_type` | `KeyError` | Cannot dispatch without discriminator |
| Unknown `org_type` value | `ValueError` | No subtype matches |
| Invalid field values | `ValidationError` | Pydantic re-validates on construction |

## Contract: Mutation via model_copy

### Preconditions

1. Source organization is a valid frozen instance.
2. `update` dict contains only valid field names with valid values.

### Algorithm

```
new_org = org.model_copy(update={"field": new_value})
```

### Postconditions

1. Returns a NEW frozen instance.
2. Original instance is unchanged.
3. Only specified fields differ; all others are identical.
4. New instance passes all validation rules.

### Invariants

- Organization instances are NEVER mutated in place.
- Every state change produces a new instance.
- The original and new instance can coexist simultaneously.

## Contract: KeyFigure

### Creation Preconditions

1. `id` is unique, non-empty.
2. `name` is non-empty.
3. `organization_id` references an existing Organization node.
4. `role` is non-empty.
5. `structural_importance` is `Probability` [0, 1] (default: 0.5).

### Graph Representation

- Stored as graph node with `_node_type="key_figure"`.
- COMMAND edges connect KeyFigure → KeyFigure within the same organization.
- Parent organization references KeyFigure via `member_node_ids`.

### Invariants

- KeyFigure removal triggers cohesion recalculation on parent Organization.
- Cohesion loss = `cohesion_loss_per_key_figure` per removed figure (from OrganizationDefines).
- Cohesion floor = `min_cohesion_threshold` (never reaches exactly 0).

## Contract: IntelMethodology

### Creation

- All boolean fields default to `False`.
- `observation_ceiling` is `Probability` [0, 1] (default: 0.2).
- Frozen: `ConfigDict(frozen=True)`.

### Preset Configurations

| Preset | centrality | equivalence | template | temporal | ceiling |
|--------|-----------|-------------|----------|----------|---------|
| Local PD | True | False | False | False | 0.2 |
| Fusion Center | True | False | False | True | 0.5 |
| FBI | True | True | True | True | 0.4 |

### Semantics

- `observation_ceiling` = max fraction of true topology edges visible.
- Which edges are visible depends on capability mix (centrality sees high-degree first; temporal sees recently-active first).
- Ceiling values are tunable via `OrganizationDefines`.
