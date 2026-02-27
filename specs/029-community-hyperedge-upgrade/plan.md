# Implementation Plan: Community Hyperedge Layer Upgrade

**Branch**: `029-community-hyperedge-upgrade` | **Date**: 2026-02-27 | **Spec**: `specs/029-community-hyperedge-upgrade/spec.md`
**Input**: Feature specification from `/specs/029-community-hyperedge-upgrade/spec.md`

## Summary

Upgrade the existing community hyperedge layer (Feature 022) with a three-category structural taxonomy, contradiction axis formalization, community-level consciousness modeling, and infiltration resistance mechanics. The upgrade is **purely additive** — all 14 CommunityType enum members already exist, all existing models/tests are preserved. New additions: 2 enums, 2 models, 6 constants, 7 functions, 2 computed fields on CommunityState, and updates to build_community_hypergraph to include consciousness in hyperedge attributes.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: Pydantic 2.x (frozen models, validation), XGI 0.10 (hypergraph), NetworkX 3.x (graph protocol)
**Storage**: In-memory via XGI Hypergraph + GraphProtocol. CommunityConsciousness serialized to JSON via Pydantic. No new database tables.
**Testing**: pytest (unit + integration, 43 existing community tests must pass)
**Target Platform**: Linux (simulation engine)
**Project Type**: Single project (existing codebase extension)
**Performance Goals**: No performance-critical paths — taxonomy/axis queries are O(1) lookups, infiltration resistance is O(1) computed field
**Constraints**: Backward compatible — existing callers must not require modification. Frozen Pydantic models. XGI remains optional dependency.
**Scale/Scope**: 14 community types, 2 contradiction axes, 14 consciousness defaults. ~300 lines of new code, ~50 lines of modified code.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I.1 Settler-Colonial Frame | PASS | Colonial axis is the primary contradiction axis |
| I.7 Quantitative → Qualitative | PASS | CI is float (quantity), tendency is enum (quality) — correct separation |
| I.12 Catastrophe Surface | PASS | Consciousness values are control parameters (continuous), tendency shifts are discrete |
| I.18 Material-Ideological Distinction | PASS | **This IS the feature** — two dimensions on every hyperedge |
| II.7 Edges vs Hyperedges | PASS | Three categories implemented per constitution text |
| III.1 No Magic Constants | PASS | All defaults flagged SYNTHETIC, coefficients named |
| III.4 Data Source Traceability | PASS | No new data sources — defaults are theoretical/synthetic |
| VIII.9 Community as Pairwise Edge | PASS | Using XGI hyperedges, not pairwise |
| VIII.10 Oppressor Hyperedge | PASS | Category 2 has NO hegemonic side — only Category 1 has both sides |

No violations. Gate passes.

## Project Structure

### Documentation (this feature)

```text
specs/029-community-hyperedge-upgrade/
├── plan.md              # This file
├── research.md          # Phase 0: codebase investigation, naming corrections
├── data-model.md        # Phase 1: entity definitions, relationships
├── quickstart.md        # Phase 1: integration scenarios
├── contracts/
│   ├── taxonomy-api.md  # FR-001, FR-002, FR-010 contracts
│   └── consciousness-api.md  # FR-003, FR-004, FR-005, FR-006, FR-009 contracts
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/babylon/models/
├── enums.py                           # ADD: HyperedgeCategory, ConsciousnessTendency enums
└── entities/
    └── community.py                   # EXTEND: CommunityConsciousness model,
                                       #   ContradictionAxis model, constants,
                                       #   CommunityState new fields + computed fields,
                                       #   pure query functions

src/babylon/engine/systems/
└── community.py                       # EXTEND: build_community_hypergraph (consciousness attrs),
                                       #   communities_spanning_axis, effective_infiltration_ceiling

tests/unit/models/
└── test_community_models.py           # EXTEND: taxonomy, consciousness, resistance tests

tests/unit/engine/systems/
└── test_community_system.py           # EXTEND: bridge detection, consciousness in hypergraph

tests/unit/formulas/
└── test_community_formulas.py         # No changes expected (existing formulas unchanged)
```

**Structure Decision**: Single project, extending existing community layer modules. No new files — all additions go into existing `community.py` files in models and engine/systems. New test cases added to existing test files.

## Key Implementation Details

### Backward Compatibility Strategy

CommunityState gains two new fields:

1. **`category: HyperedgeCategory`** — Auto-assigned via `@model_validator(mode="after")` that looks up `self.community_type` in `COMMUNITY_CATEGORY_MAP`. Since CommunityState is frozen, the validator uses `object.__setattr__` during validation. Existing callers that don't pass `category` get it auto-populated.

2. **`consciousness: CommunityConsciousness`** — Defaults via `Field(default_factory=CommunityConsciousness)`. Existing callers get the generic default (CI=0.3, liberal, contestation=0.2).

The two `@computed_field` additions (`infiltration_resistance`, `is_cross_class_bridge`) are not constructor arguments and cannot break existing callers.

### Infiltration Resistance Formula

```
resistance = CI * 0.6 + cohesion * 0.3 + CI * cohesion * 0.1
```

Coefficients stored as module-level named constants:
- `INFILTRATION_CI_WEIGHT = 0.6`
- `INFILTRATION_COHESION_WEIGHT = 0.3`
- `INFILTRATION_INTERACTION_WEIGHT = 0.1`

### Effective Ceiling Formula

```
effective_ceiling = base_ceiling * (1.0 - max_resistance * 0.7)
```

Module-level constant: `INFILTRATION_CEILING_FACTOR = 0.7`

### build_community_hypergraph Update

Add consciousness attributes to hyperedge attributes alongside existing ones:
```python
H.add_edge(
    members, idx=comm_type.value,
    # ... existing attributes ...
    consciousness_ci=float(state.consciousness.collective_identity),
    consciousness_tendency=state.consciousness.dominant_tendency.value,
    consciousness_contestation=float(state.consciousness.ideological_contestation),
    category=state.category.value,
)
```

### Exhaustiveness Validation

Module-level assertion at import time:
```python
_missing = set(CommunityType) - set(COMMUNITY_CATEGORY_MAP.keys())
if _missing:
    raise RuntimeError(f"COMMUNITY_CATEGORY_MAP missing types: {_missing}")
```

Same pattern for CONSCIOUSNESS_DEFAULTS.

## Existing Code to Reuse

| Component | Location | Reuse |
|-----------|----------|-------|
| CommunityState model | `models/entities/community.py:46` | Extend with new fields |
| CommunityType enum | `models/enums.py:426` | Use as-is (all 14 members exist) |
| Probability type | `models/types.py` | Constrain CI and contestation |
| Coefficient type | `models/types.py` | N/A (no new coefficients) |
| build_community_hypergraph | `engine/systems/community.py:33` | Extend with consciousness attrs |
| shared_communities | `engine/systems/community.py:84` | Use as-is |
| ROLE_STRENGTH_WEIGHTS | `models/entities/community.py:19` | Pattern for new constants |
| ConfigDict(frozen=True) | Throughout | Pattern for new models |

## Verification

After implementation:

```bash
# All existing community tests pass (FR-008)
poetry run pytest tests/unit/models/test_community_models.py -v
poetry run pytest tests/unit/engine/systems/test_community_system.py -v
poetry run pytest tests/unit/formulas/test_community_formulas.py -v

# Full unit suite
mise run test:unit

# Lint + format + typecheck
mise run check
```

## Complexity Tracking

No constitution violations to justify. All additions are straightforward extensions of existing patterns.
