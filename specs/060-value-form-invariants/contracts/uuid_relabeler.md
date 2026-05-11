# Contract: UUID Relabeler

**Spec**: [../spec.md](../spec.md) — FR-013, US6(a)
**Inventory source**: [../research.md](../research.md) — R5
**Data model**: [../data-model.md](../data-model.md) — `UUIDRelabeler`
**Implementation**: `tests/_helpers/invariants/uuid_relabeler.py`

## Purpose

US6(a) / FR-013 require relabeling every entity ID in a `WorldState`
and asserting that numerical outputs are bit-identical (1e-15 relative
tolerance) after a tick. The relabeler is the operation that produces
the aliased world.

## Field inventory

### Top-level dict-key namespaces (canonical IDs)

The eight `WorldState` dicts that map `id → entity`:

```python
TOP_LEVEL_KEY_FIELDS = (
    "entities",          # SocialClass
    "territories",       # Territory
    "state_finances",    # StateFinance
    "contradiction_frames",
    "organizations",     # OrganizationType (Organization, Business, etc.)
    "key_figures",       # KeyFigure
    "institutions",      # Institution
    "industries",        # IndustryHyperedge
)
```

### Entity-internal ID fields

```python
# Each (entity_class, field_name) below is rewritten.
# Source: tests/_helpers/invariants/uuid_relabeler.py
ENTITY_ID_FIELDS: dict[type[BaseModel], tuple[str, ...]] = {
    Organization: ("id", "headquarters_id"),
    KeyFigure: ("id", "organization_id"),
    Territory: ("id", "host_id", "occupant_id"),
    SocialClass: ("id",),
    Contradiction: ("id",),
    Relationship: ("source_id", "target_id"),
    AttentionThread: ("thread_id", "target_id", "owning_apparatus_id"),
    StateApparatusAI: ("target_id", "framework_id", "creating_apparatus_id"),
    Community: ("agent_id",),
    Institution: ("id",),  # confirm in implementation
    IndustryHyperedge: ("id",),  # confirm in implementation
}
```

## Algorithm

1. **Collect canonical IDs**:
   ```python
   canonical_ids: set[str] = set()
   for field_name in TOP_LEVEL_KEY_FIELDS:
       canonical_ids.update(getattr(world, field_name).keys())
   ```

2. **Build the alias mapping**:
   ```python
   sorted_ids = sorted(canonical_ids)   # determinism
   mapping = {orig: alias_fn(i, orig) for i, orig in enumerate(sorted_ids)}
   assert len(set(mapping.values())) == len(mapping), "alias collision"
   ```

3. **Dump and rewrite**:
   ```python
   dump = world.model_dump()
   _rewrite_in_place(dump, mapping)  # recursive walk, replaces dict keys
                                     # and string values matching mapping
   ```

4. **Reconstitute**:
   ```python
   return WorldState.model_validate(dump), mapping
   ```

## Recursive rewriter

The recursive walker visits dicts and lists:

```python
def _rewrite_in_place(obj, mapping: dict[str, str]) -> None:
    if isinstance(obj, dict):
        # rewrite both keys (where key is an ID) and values (where value
        # is an ID or contains nested IDs)
        for key in list(obj.keys()):
            if key in mapping:
                obj[mapping[key]] = obj.pop(key)
        for key, val in obj.items():
            if isinstance(val, str) and val in mapping:
                obj[key] = mapping[val]
            elif isinstance(val, (dict, list)):
                _rewrite_in_place(val, mapping)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, str) and item in mapping:
                obj[i] = mapping[item]
            elif isinstance(item, (dict, list)):
                _rewrite_in_place(item, mapping)
```

## Invariants

| Invariant | Verification |
|---|---|
| Bijection | every `mapping[orig]` is unique |
| ID-only change | for any non-string field f: `relabeled.f == original.f` exactly |
| Numeric field invariance | for any numeric field f: `step(relabeled).f == step(original).f` within 1e-15 (this is what FR-013 asserts) |
| Round-trip | applying the inverse mapping restores the original world |

## Edge cases

| Case | Behavior |
|---|---|
| ID-shaped field references an entity NOT in the canonical set (e.g., a `framework_id` pointing to a framework not in any `WorldState` dict) | Leave unchanged. Emit warning. |
| Empty world (no entities) | Return identity (empty mapping). |
| Collision in user-supplied `alias_fn` | Raise `ValueError`. |
| Duplicate IDs in canonical set (shouldn't happen) | Raise `ValueError`. |

## Out of scope

- Relabeling Postgres-persisted state.
- Renaming enum values, edge mode types, or dialectic relation kinds —
  those are not IDs.
- Renaming filesystem paths or trace CSV file names.

## Anti-pattern

Tests MUST NOT relabel only the top-level dict keys without sweeping
nested references — that would break `Relationship.source_id` /
`target_id` integrity and produce an invalid `WorldState` that fails
Pydantic validation. The recursive walker handles this; tests must
rely on it.
