# Feature Specification: Community Hyperedge Layer Upgrade

**Feature Branch**: `029-community-hyperedge-upgrade`
**Created**: 2026-02-27
**Status**: Draft
**Prerequisite**: Feature 022 (Hypergraph Community Layer) — already implemented
**Required By**: Org-topology specs 030-035

## Overview

Upgrade the existing community hyperedge layer (Feature 022) with a three-category structural taxonomy, contradiction axis formalization, community-level consciousness modeling, and infiltration resistance mechanics. This provides the structural foundation that all downstream organizational topology specs (030-035) depend on.

**What already exists** (must be preserved):
- CommunityType enum with 13 members (SETTLER, PATRIARCHAL, NEW_AFRIKAN, FIRST_NATIONS, CHICANO, WOMEN, TRANS, DISABLED, QUEER, UNDOCUMENTED, INCARCERATED, YOUTH, ADULT, ELDER)
- CommunityState model (heat, legal_status, cohesion, infrastructure, visibility, reproduction_cost_modifier, rent_access_modifier)
- CommunityMembership model (agent_id, community_type, role, strength, visibility, overt, effective_visibility)
- LegalStatus enum (5-level escalation ratchet)
- MembershipRole enum (5 integration levels)
- build_community_hypergraph() function (XGI-based)
- CommunitySystem (pipeline position 6)

**What this upgrade adds**:
- Structural taxonomy: three qualitatively distinct community categories
- Contradiction axis formalization: extraction relationships between paired communities
- Community consciousness: ideological dimension tracking collective identity and political tendency
- Infiltration resistance: community-level counter-intelligence derived from consciousness and cohesion
- Cross-class bridge detection: identifying communities that span contradiction axes

## User Scenarios & Testing

### User Story 1 - Three-Category Taxonomy (Priority: P1)

As the simulation architect, I need every community hyperedge classified into exactly one of three structural categories (contradiction pair, institutional exclusion, lifecycle phase) so that downstream systems can differentiate extraction-based oppression from institutional exclusion and temporal lifecycle positioning.

**Why this priority**: Foundation for all other stories. Consciousness, infiltration resistance, and contradiction axes all depend on category assignment.

**Independent Test**: Category mapping can be tested by verifying every CommunityType maps to exactly one HyperedgeCategory, and that the mapping is exhaustive (no unmapped types).

**Acceptance Scenarios**:

1. **Given** the complete set of 14 CommunityType members, **When** the taxonomy mapping is queried, **Then** every type maps to exactly one HyperedgeCategory (CONTRADICTION_PAIR, INSTITUTIONAL_EXCLUSION, or LIFECYCLE_PHASE)
2. **Given** SETTLER and PATRIARCHAL community types, **When** their category is queried, **Then** both return CONTRADICTION_PAIR
3. **Given** DISABLED, QUEER, UNDOCUMENTED, and INCARCERATED community types, **When** their category is queried, **Then** all return INSTITUTIONAL_EXCLUSION
4. **Given** YOUTH, ADULT, and ELDER community types, **When** their category is queried, **Then** all return LIFECYCLE_PHASE
5. **Given** a new CommunityType member is added without updating the mapping, **When** the system initializes, **Then** a validation error is raised (exhaustiveness check)

______________________________________________________________________

### User Story 2 - Contradiction Axis Formalization (Priority: P2)

As the simulation architect, I need contradiction pairs formalized as named axes with hegemonic and marginalized sides so that the system can model extraction relationships, determine axis opposition, and support bifurcation analysis.

**Why this priority**: Axes define the extraction relationship that consciousness and infiltration resistance operate within. Required by bifurcation topology analysis (spec 033).

**Independent Test**: Axis queries can be tested by verifying get_contradiction_axis returns the correct axis for paired communities, None for unpaired ones, and get_opposing_communities returns the correct opposition set.

**Acceptance Scenarios**:

1. **Given** the COLONIAL axis, **When** queried, **Then** SETTLER is identified as hegemonic and [NEW_AFRIKAN, FIRST_NATIONS, CHICANO] as marginalized
2. **Given** the PATRIARCHAL axis, **When** queried, **Then** PATRIARCHAL is identified as hegemonic and [WOMEN, TRANS] as marginalized
3. **Given** SETTLER community type, **When** get_opposing_communities is called, **Then** [NEW_AFRIKAN, FIRST_NATIONS, CHICANO] is returned
4. **Given** NEW_AFRIKAN community type, **When** get_opposing_communities is called, **Then** [SETTLER] is returned
5. **Given** DISABLED community type (institutional exclusion), **When** get_contradiction_axis is called, **Then** None is returned
6. **Given** YOUTH community type (lifecycle phase), **When** get_contradiction_axis is called, **Then** None is returned
7. **Given** the is_hegemonic predicate, **When** applied to SETTLER, **Then** True; **When** applied to NEW_AFRIKAN, **Then** False
8. **Given** the is_marginalized predicate, **When** applied to DISABLED, **Then** True (institutional exclusion counts as marginalized); **When** applied to SETTLER, **Then** False

______________________________________________________________________

### User Story 3 - Community Consciousness Model (Priority: P3)

As the simulation architect, I need every community hyperedge to carry an ideological dimension (collective identity, dominant tendency, and ideological contestation) so that the gap between material basis and collective self-understanding can drive political struggle dynamics.

**Why this priority**: Consciousness is the terrain of political organizing. Org-topology Phases 1-2 (specs 030-031) require consciousness attributes to model EDUCATE, AGITATE, and ASSIMILATE actions.

**Independent Test**: Consciousness can be tested by verifying all 14 community types have default consciousness values, values survive serialization roundtrip, and the semantic meaning differs between hegemonic and marginalized communities.

**Acceptance Scenarios**:

1. **Given** the 14 community types, **When** consciousness defaults are loaded, **Then** every type has a valid CommunityConsciousness with collective_identity in [0, 1], a dominant_tendency, and ideological_contestation in [0, 1]
2. **Given** INCARCERATED community, **When** consciousness defaults are loaded, **Then** dominant_tendency is REVOLUTIONARY (George Jackson tradition)
3. **Given** SETTLER community, **When** consciousness defaults are loaded, **Then** dominant_tendency is ASSIMILATIONIST_LIBERAL (passive beneficiary default)
4. **Given** FIRST_NATIONS community, **When** consciousness defaults are loaded, **Then** dominant_tendency is REVOLUTIONARY (sovereignty framing) and collective_identity is 0.6
5. **Given** a CommunityState with consciousness, **When** serialized to JSON and deserialized, **Then** all consciousness fields are preserved exactly
6. **Given** YOUTH community (lifecycle phase), **When** consciousness defaults are loaded, **Then** ideological_contestation is high (0.5 — D-phase socialization is highly contestable) despite low collective_identity (0.2)

______________________________________________________________________

### User Story 4 - Infiltration Resistance (Priority: P4)

As the simulation architect, I need community-level infiltration resistance derived from collective identity and social cohesion so that the state's ability to infiltrate organizations embedded in high-consciousness, tight-knit communities is mechanically reduced.

**Why this priority**: Required by attention thread system (spec 032) to modify observation ceiling for surveillance targeting organizations in resistant communities.

**Independent Test**: Infiltration resistance can be tested by computing resistance for communities with known consciousness and cohesion values and verifying the effective_infiltration_ceiling formula reduces base ceiling proportionally.

**Acceptance Scenarios**:

1. **Given** a community with collective_identity=0.9 and cohesion=0.8, **When** infiltration_resistance is computed, **Then** the result is high (approximately 0.85 or above)
2. **Given** a community with collective_identity=0.1 and cohesion=0.2, **When** infiltration_resistance is computed, **Then** the result is low (approximately 0.12 or below)
3. **Given** a community with high collective_identity but low cohesion, **When** infiltration_resistance is computed, **Then** resistance is moderate (consciousness without social density provides incomplete protection)
4. **Given** a community with low collective_identity but high cohesion, **When** infiltration_resistance is computed, **Then** resistance is moderate (social density without consciousness means the community cooperates with the state)
5. **Given** a base observation ceiling of 0.8 and a target community with high infiltration_resistance, **When** effective_infiltration_ceiling is computed, **Then** the ceiling is significantly reduced (approximately 40-60% of base)
6. **Given** no target communities (empty list), **When** effective_infiltration_ceiling is computed, **Then** the base ceiling is returned unchanged

______________________________________________________________________

### User Story 5 - Cross-Class Bridge Detection and Integration (Priority: P5)

As the simulation architect, I need to detect which institutional exclusion communities have members spanning a contradiction axis (e.g., DISABLED community with both SETTLER and NEW_AFRIKAN members) so that cross-class solidarity potential can be identified, and I need all existing functionality preserved with the new attributes integrated into the hypergraph.

**Why this priority**: Bridge detection is needed for bifurcation analysis (spec 033). Integration ensures no regressions.

**Independent Test**: Bridge detection can be tested with a synthetic hypergraph where DISABLED has members from both sides of the colonial axis. Integration verified by running all existing community tests.

**Acceptance Scenarios**:

1. **Given** a hypergraph where DISABLED community has members who also belong to SETTLER and NEW_AFRIKAN communities, **When** communities_spanning_axis is called for the COLONIAL axis, **Then** DISABLED is identified as a cross-class bridge
2. **Given** a hypergraph where QUEER community has members only on the marginalized side, **When** communities_spanning_axis is called, **Then** QUEER is NOT identified as a bridge
3. **Given** SETTLER community (contradiction pair, not institutional exclusion), **When** is_cross_class_bridge is queried, **Then** False (contradiction pairs are the axis itself, not bridges)
4. **Given** two agents sharing marginalized community memberships, **When** shared_marginalized_communities is computed, **Then** only marginalized communities appear in the result (hegemonic and lifecycle communities excluded)
5. **Given** the upgraded CommunityState with consciousness attributes, **When** build_community_hypergraph is called, **Then** hyperedge attributes include consciousness state alongside existing attributes (heat, cohesion, infrastructure, etc.)
6. **Given** all existing community tests, **When** the test suite is run after the upgrade, **Then** all pre-existing tests pass without modification

______________________________________________________________________

### Edge Cases

- What happens when a CommunityType is added to the enum but not to COMMUNITY_CATEGORY_MAP? Validation must catch the inconsistency at initialization time.
- What happens when consciousness defaults are missing for a CommunityType? The system must fail loudly rather than silently using generic defaults.
- What happens when effective_infiltration_ceiling receives communities with zero infiltration_resistance? Base ceiling passes through unchanged.
- What happens when communities_spanning_axis is called on an empty hypergraph? Returns an empty list.
- How does infiltration_resistance behave at boundary values (all zeros, all ones)? At CI=0.0/cohesion=0.0, resistance is 0.0. At CI=1.0/cohesion=1.0, resistance is 1.0.
- What happens if an agent belongs to communities on BOTH sides of a contradiction axis (e.g., a member of both SETTLER and NEW_AFRIKAN)? The data model permits this but it represents an error condition for the colonial axis (exclusive=True). Validation should warn but not crash.

## Requirements

### Functional Requirements

- **FR-001 (Exhaustive Category Mapping)**: System MUST assign every CommunityType to exactly one HyperedgeCategory. The mapping MUST be validated at initialization to prevent unmapped types.
- **FR-002 (Contradiction Axis Structure)**: System MUST define exactly two contradiction axes (Colonial and Patriarchal) as immutable structural constants (not database records). Each axis MUST identify one hegemonic community type and one or more marginalized community types.
- **FR-003 (Consciousness State)**: Every community hyperedge MUST carry a CommunityConsciousness with three fields: collective_identity [0, 1], dominant_tendency (one of three tendency values), and ideological_contestation [0, 1].
- **FR-004 (Consciousness Defaults)**: System MUST provide SYNTHETIC consciousness starting values for all 14 community types calibrated for the Detroit test case (simulation start circa 2010). These values MUST be explicitly flagged as synthetic (not empirically derived).
- **FR-005 (Infiltration Resistance)**: System MUST compute per-community infiltration resistance as a derived property combining collective_identity and cohesion. The formula MUST produce maximum resistance only when BOTH consciousness and social density are high.
- **FR-006 (Effective Infiltration Ceiling)**: System MUST provide a function to modify a base observation ceiling by the maximum infiltration resistance of target communities. No target communities means no modification.
- **FR-007 (Cross-Class Bridge Detection)**: System MUST identify institutional exclusion communities whose members span a contradiction axis. Contradiction pair communities and lifecycle communities MUST NOT be reported as bridges.
- **FR-008 (Backward Compatibility)**: All existing community layer functionality (CommunityState fields, CommunityMembership, build_community_hypergraph, CommunitySystem step, solidarity amplification, threat scoring) MUST continue to work without modification to existing callers.
- **FR-009 (Serialization Roundtrip)**: CommunityConsciousness MUST survive serialization to JSON and deserialization without data loss.
- **FR-010 (Axis Query Functions)**: System MUST provide pure functions to query contradiction axis membership, hegemonic/marginalized status, and opposing communities for any CommunityType.

### Key Entities

- **HyperedgeCategory**: Three-valued enum classifying community structural types (contradiction pair, institutional exclusion, lifecycle phase)
- **ConsciousnessTendency**: Three-valued enum representing ideological directions (assimilationist liberal, assimilationist fascist, revolutionary)
- **CommunityConsciousness**: Frozen model representing the ideological dimension of a community (collective identity, dominant tendency, ideological contestation)
- **ContradictionAxis**: Frozen model representing a structural axis of contradiction with hegemonic and marginalized sides, extraction mechanism description, and permeability properties
- **CommunityState** (extended): Existing community state model upgraded with consciousness, category, infiltration_resistance, and is_cross_class_bridge

## Success Criteria

### Measurable Outcomes

- **SC-001**: All 14 community types are classified into exactly one of three categories with zero unmapped types
- **SC-002**: Contradiction axis queries return correct results for all 14 community types (7 paired, 4 institutional, 3 lifecycle)
- **SC-003**: Consciousness defaults are defined for all 14 community types with all fields in valid ranges
- **SC-004**: Infiltration resistance produces expected values across the full input range (monotonically increasing with both collective_identity and cohesion)
- **SC-005**: All pre-existing community layer tests pass without modification after the upgrade
- **SC-006**: Consciousness survives JSON serialization roundtrip with zero data loss for all 14 default configurations
- **SC-007**: Cross-class bridge detection correctly identifies institutional exclusion communities spanning contradiction axes in a synthetic test hypergraph

## Assumptions

- The three-category taxonomy (contradiction pair, institutional exclusion, lifecycle phase) is a fixed structural property of community types, not a runtime-configurable parameter
- Contradiction axes are theoretical structure stored as module-level constants, not database records that change at runtime
- All consciousness default values are SYNTHETIC (derived from political analysis for the Detroit test case, not empirically measured) and flagged as such
- Consciousness DYNAMICS (how values change over time through organizational actions) are NOT part of this spec — they are deferred to org-topology Phase 2 (spec 031)
- XGI remains an optional dependency; bipartite NetworkX fallback must continue to work
- The existing CommunityState model name is preserved (the user's prompt referenced "CommunityNode" but the actual codebase uses "CommunityState")
- The existing CommunityMembership model name is preserved (the user's prompt referenced "MembershipEdge" but the actual codebase uses "CommunityMembership")
- Infiltration resistance coefficients in the derived formula (0.6 CI weight, 0.3 cohesion weight, 0.1 interaction term) are calibration constants that may be adjusted through playtesting

## Boundary / Out of Scope

- Consciousness dynamics (how CI, tendency, and contestation change over time) — deferred to org-topology Phase 2
- Organization interaction with consciousness (EDUCATE, AGITATE, ASSIMILATE actions) — deferred to org-topology Phases 1-2
- Bifurcation analysis using consciousness weighting — deferred to org-topology Phase 4
- State targeting using infiltration resistance — deferred to org-topology Phase 3
- Territory-level consciousness geography — deferred to org-topology Phase 6
- Legibility dimension (nonprofit vs LLC observation profiles) — deferred
- Historical consciousness trajectories — deferred
- Nation vs community distinction — deferred, nations treated as CommunityType for now
- Adding new data sources not already in the existing infrastructure
- Modifying the existing SQLite schema

## Dependencies

- **Requires**: Feature 022 (Hypergraph Community Layer) — already implemented
- **Requires**: SocialClass nodes in the simulation graph (for class position of community members)
- **Required By**: All org-topology specs (030-035)
- **Required By**: Bifurcation topology analysis (spec 033) — needs consciousness weighting
- **Required By**: Attention thread system (spec 032) — needs infiltration resistance
