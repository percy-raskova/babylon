# Research: Community Hyperedge Layer Upgrade

**Feature**: 029-community-hyperedge-upgrade
**Date**: 2026-02-27
**Status**: Complete

## Key Finding: CommunityType Enum Already Complete

The user's original prompt assumed only 7 CommunityType members existed (QUEER, TRANS,
DISABLED, UNDOCUMENTED, NEW_AFRIKAN, FIRST_NATIONS, CHICANO). Investigation of the
actual codebase reveals **all 14 members already exist** in `src/babylon/models/enums.py`
(lines 426-469):

| Member | Category | Status |
|--------|----------|--------|
| SETTLER | Category 1 hegemonic | Already exists |
| PATRIARCHAL | Category 1 hegemonic | Already exists |
| NEW_AFRIKAN | Category 1 marginalized | Already exists |
| FIRST_NATIONS | Category 1 marginalized | Already exists |
| CHICANO | Category 1 marginalized | Already exists |
| WOMEN | Category 1 marginalized | Already exists |
| TRANS | Category 1 marginalized | Already exists |
| DISABLED | Category 2 exclusion | Already exists |
| QUEER | Category 2 exclusion | Already exists |
| UNDOCUMENTED | Category 2 exclusion | Already exists |
| INCARCERATED | Category 2 exclusion | Already exists |
| YOUTH | Category 3 lifecycle | Already exists |
| ADULT | Category 3 lifecycle | Already exists |
| ELDER | Category 3 lifecycle | Already exists |

The enum docstring already documents the three-category taxonomy per Constitution II.7.
This means the upgrade scope is **purely additive** — no enum modifications needed.

## Naming Corrections

The user's prompt used names from the original spec prompt, not the actual codebase:

| Prompt Name | Actual Codebase Name | Location |
|-------------|---------------------|----------|
| CommunityNode | CommunityState | `src/babylon/models/entities/community.py:46` |
| MembershipEdge | CommunityMembership | `src/babylon/models/entities/community.py:98` |
| CommunityLegalStatus | LegalStatus | `src/babylon/models/enums.py:472` |

All spec and plan artifacts use the **actual codebase names**.

## Existing Infrastructure Assessment

### Models (`src/babylon/models/entities/community.py`)

- **CommunityState**: Frozen Pydantic model with 7 fields (community_type, heat, legal_status,
  cohesion, infrastructure, visibility, reproduction_cost_modifier, rent_access_modifier).
  Uses constrained types: `Probability` for [0,1] fields, `Coefficient` for multipliers.
- **CommunityMembership**: Frozen Pydantic with 5 fields + 1 computed (effective_visibility).
- **Constants**: ROLE_STRENGTH_WEIGHTS, LEGAL_STATUS_MULTIPLIERS, LEGAL_STATUS_ORDER.

### System (`src/babylon/engine/systems/community.py`)

- **build_community_hypergraph**: Accepts `list[CommunityMembership]` and `dict[CommunityType, CommunityState]`,
  returns `xgi.Hypergraph`. Uses `idx=comm_type.value` for hyperedge IDs. Stores state fields as
  hyperedge attributes (heat, cohesion, infrastructure, visibility, legal_status, reproduction_cost_modifier,
  rent_access_modifier).
- **CommunitySystem**: Pipeline position 6. Performs solidarity amplification, threat scoring,
  infrastructure decay. Accesses graph via `GraphProtocol`.
- **Repression actions**: `legal_status_escalate`, `designate_community`, `infiltrate_community`,
  `disrupt_infrastructure`.

### Formulas (`src/babylon/formulas/community.py`)

- `calculate_solidarity_potential`: Base + overlap_bonus * shared_count - rent_penalty * |rent_diff|
- `calculate_threat_score`: Sum of heat * visibility * role_weight * legal_multiplier
- `calculate_infrastructure_decay`: current * (1-alpha) + maintenance * alpha
- `calculate_solidarity_amplification`: base * (1 + sum(infra * cohesion * str_a * str_b))
- `compute_community_cost_modifier`: Product of reproduction_cost_modifier across memberships

### Tests (43 existing tests across 3 files)

- `tests/unit/models/test_community_models.py`: 18 tests (state, membership, lookups, cost)
- `tests/unit/engine/systems/test_community_system.py`: 14 tests (builder, overlap, system step, repression)
- `tests/unit/formulas/test_community_formulas.py`: 18 tests (solidarity, threat, decay, amplification)

All 43 tests must pass without modification after the upgrade (FR-008).

## Technology Decisions

### Decision 1: New Enums and Models Location

**Decision**: Add new enums (HyperedgeCategory, ConsciousnessTendency) to `src/babylon/models/enums.py`
alongside existing CommunityType. Add new models (CommunityConsciousness, ContradictionAxis) to
`src/babylon/models/entities/community.py` alongside existing CommunityState.

**Rationale**: Keeps all community-related types co-located. Follows existing pattern where
CommunityType, LegalStatus, and MembershipRole are all in enums.py.

**Alternatives considered**: Separate `community_taxonomy.py` module — rejected because it fragments
the community layer across multiple files without reducing complexity.

### Decision 2: Constants Location

**Decision**: Add taxonomy constants (COMMUNITY_CATEGORY_MAP, HEGEMONIC_COMMUNITIES, etc.),
contradiction axis constants (COLONIAL_AXIS, PATRIARCHAL_AXIS), and consciousness defaults
(CONSCIOUSNESS_DEFAULTS) to `src/babylon/models/entities/community.py`.

**Rationale**: Constants are tightly coupled to the models they reference. Same pattern as
ROLE_STRENGTH_WEIGHTS and LEGAL_STATUS_MULTIPLIERS already in community.py.

**Alternatives considered**: Separate `community_constants.py` — rejected; creates unnecessary
import indirection for tightly coupled data.

### Decision 3: Helper Functions Location

**Decision**: Add axis query functions (get_contradiction_axis, is_hegemonic, is_marginalized,
get_opposing_communities, shared_marginalized_communities) to `src/babylon/models/entities/community.py`.
Add hypergraph-dependent functions (communities_spanning_axis, effective_infiltration_ceiling) to
`src/babylon/engine/systems/community.py`.

**Rationale**: Pure data queries belong with the models. Functions requiring XGI hypergraph
access belong with the system that builds and queries hypergraphs.

### Decision 4: CommunityState Extension Strategy

**Decision**: Add new fields directly to existing CommunityState model: `category` (HyperedgeCategory),
`consciousness` (CommunityConsciousness with default_factory). Add `infiltration_resistance` as
a `@computed_field`. Add `is_cross_class_bridge` as a `@computed_field`.

**Rationale**: Direct extension preserves backward compatibility since all new fields have defaults.
Existing callers constructing `CommunityState(community_type=X)` continue to work because:
- `category` gets auto-assigned from COMMUNITY_CATEGORY_MAP via a model_validator
- `consciousness` defaults via `default_factory=CommunityConsciousness`
- `infiltration_resistance` and `is_cross_class_bridge` are computed fields (not constructor args)

**Alternatives considered**: Subclassing CommunityState as CommunityStateV2 — rejected because
it requires updating all callers to use the new class, defeating backward compatibility.

### Decision 5: Category Auto-Assignment

**Decision**: Use a Pydantic `@model_validator(mode="after")` on CommunityState that looks up
the category from COMMUNITY_CATEGORY_MAP if not explicitly provided. This ensures category
is always set correctly based on community_type.

**Rationale**: Ensures category is never inconsistent with community_type. Backward-compatible
because existing callers don't pass category — it gets auto-assigned.

**Note**: Since CommunityState is frozen, the validator must use `object.__setattr__` during
validation (Pydantic allows this in validators even for frozen models).

### Decision 6: XGI Dependency for Bridge Detection

**Decision**: `communities_spanning_axis` requires XGI Hypergraph. Keep XGI as optional
dependency. The function returns empty list if XGI is not available.

**Rationale**: Matches existing pattern where build_community_hypergraph already requires XGI.
Bridge detection is a secondary feature that won't block simulation without XGI.

### Decision 7: Infiltration Resistance Coefficients

**Decision**: Use coefficients from spec: 0.6 (CI weight), 0.3 (cohesion weight), 0.1 (interaction term).
Store as module-level named constants for discoverability by the tuning infrastructure.

**Rationale**: Named constants can be discovered by `get_tunable_parameters()` and included
in sensitivity analysis. Matches project pattern of making calibration constants visible.

**Note**: These are calibration constants (Tier C per Feature 028 taxonomy) that may be
adjusted through playtesting. Eventually should migrate to GameDefines.
