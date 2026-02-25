# Feature Specification: Hypergraph Community Layer

**Feature Branch**: `022-hypergraph-community-layer`
**Created**: 2026-02-25
**Status**: Draft
**Input**: Formalize community/identity relationships as hyperedges for solidarity computation and state repression modeling
**Dependencies**: 017-simulation-tick-dynamics, 018-crisis-devaluation-mechanics

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Community Membership as Hyperedge Structure (Priority: P1)

The simulation represents communities (racial, gender, sexuality, disability, documentation status) as first-class collective structures that agents belong to, rather than as attributes on individual agents or as pairwise relationships between agents. A community of 50 members is one structure containing all 50, not 1,225 pairwise edges. This enables the system to reason about communities as units — who belongs, who overlaps, and what the community's collective state is — independent of the dyadic flow relationships in the existing NetworkX graph.

**Why this priority**: Without the community hyperedge data structure, none of the downstream mechanics (solidarity potential, state repression, reproduction cost modification) can function. This is the foundational layer.

**Independent Test**: Can be fully tested by creating agents with community memberships, building the hypergraph, and verifying membership queries return correct results — independent of any simulation tick logic.

**Acceptance Scenarios**:

1. **Given** agents with assigned community memberships (e.g., agent_3 belongs to both TRANS and NEW_AFRIKAN communities), **When** the community hypergraph is built, **Then** querying shared communities between agent_3 and another NEW_AFRIKAN member returns the correct intersection.
1. **Given** a community with zero members, **When** the hypergraph is built, **Then** that community is not represented as a hyperedge (empty communities are excluded).
1. **Given** agents with varying membership roles (CORE_ORGANIZER, ACTIVE, PARTICIPANT, PERIPHERAL, SYMPATHIZER), **When** the hypergraph is queried, **Then** each agent's role and membership strength are accessible as attributes.
1. **Given** a complete agent population, **When** the community overlap matrix is computed, **Then** the diagonal entry for each agent equals their total community count, and off-diagonal entries equal the number of shared communities between each pair.

______________________________________________________________________

### User Story 2 - Solidarity Potential from Community Overlap (Priority: P2)

When two agents share community memberships, this creates conditions — but not certainty — for solidarity formation. The system computes a solidarity potential score based on how many communities two agents share, penalized by the imperial rent differential between them (material divergence impedes solidarity even with shared identity). This potential feeds into the existing solidarity system: high potential + organizing opportunity may produce an actual SOLIDARITY edge in the NetworkX graph.

**Why this priority**: This is the primary causal mechanism connecting the hypergraph layer to the existing simulation. Without it, community membership has no gameplay effect.

**Independent Test**: Can be tested by constructing agents with known community overlaps and rent differentials, computing solidarity potential, and verifying the formula produces expected values — independent of full simulation ticks.

**Acceptance Scenarios**:

1. **Given** two agents sharing 3 community memberships with zero rent differential, **When** solidarity potential is computed, **Then** the result is higher than for two agents sharing 0 communities.
1. **Given** two agents sharing 2 communities but with a large imperial rent differential (one receives full Φ, the other receives none), **When** solidarity potential is computed, **Then** the rent penalty reduces the score below what community overlap alone would produce.
1. **Given** two agents in shared communities with high infrastructure and cohesion values, **When** solidarity transmission occurs along an existing SOLIDARITY edge, **Then** the transmission rate is amplified by the community infrastructure multiplier.

______________________________________________________________________

### User Story 3 - State Repression Targeting Communities (Priority: P3)

The state targets communities as collective units, not just individual agents. Designating a community as extremist, infiltrating it, disrupting its infrastructure, or arresting its organizers are actions that affect all members simultaneously. Each agent accumulates a threat score based on the heat, visibility, and legal status of all communities they belong to. State repression of a community degrades its infrastructure, which in turn increases the reproduction costs of all members (they lose mutual aid, healthcare access, social support).

**Why this priority**: This is the adversary mechanic that makes community membership strategically consequential. Without it, communities are analytically interesting but have no antagonist pressure.

**Independent Test**: Can be tested by designating a community as extremist and verifying that all visible members' threat scores increase, and that infrastructure disruption raises reproduction costs for all members.

**Acceptance Scenarios**:

1. **Given** a community with legal status LEGAL, **When** the state designates it as DESIGNATED_EXTREMIST, **Then** the community's heat increases and all members with non-zero visibility experience increased threat scores.
1. **Given** a community with infrastructure at 0.8, **When** the state disrupts its infrastructure, **Then** infrastructure decreases and all members' effective reproduction costs increase (they lose mutual aid support).
1. **Given** a community with cohesion at 0.7, **When** the state infiltrates it, **Then** cohesion decreases, which reduces solidarity transmission effectiveness for edges between community members.
1. **Given** an agent belonging to two high-heat communities (both DESIGNATED_EXTREMIST), **When** the agent's threat score is computed, **Then** the score reflects cumulative heat from both memberships, weighted by the agent's visibility and role in each.

______________________________________________________________________

### User Story 4 - Reproduction Cost Modification by Community Membership (Priority: P4)

Community membership modifies the material conditions of agents. Disabled agents face higher reproduction costs (healthcare, accessibility). Trans agents face higher costs (healthcare, legal, discrimination). Undocumented agents may face lower base costs (excluded from state services) but have reduced access to imperial rent. These modifiers are multiplicative — an agent who is both disabled and undocumented faces the compound effect.

**Why this priority**: This connects community membership to the economic substrate of the simulation, making identity materially consequential rather than merely social.

**Independent Test**: Can be tested by creating agents with various community memberships and verifying their effective reproduction costs match expected multiplicative modifiers.

**Acceptance Scenarios**:

1. **Given** an agent with no community memberships, **When** reproduction cost is computed, **Then** the result equals the base reproduction cost.
1. **Given** an agent belonging to DISABLED (modifier 1.2) and TRANS (modifier 1.1) communities, **When** reproduction cost is computed, **Then** the result equals base cost x 1.2 x 1.1 (multiplicative compounding).
1. **Given** an agent belonging to UNDOCUMENTED community, **When** imperial rent access is computed, **Then** the agent's rent access is reduced by the community's rent_access_modifier.

______________________________________________________________________

### Edge Cases

- What happens when an agent's last community membership is removed? Agent remains a node in the hypergraph with zero memberships — they still exist in the flow graph.
- How does the system handle a community where all CORE_ORGANIZER members are arrested? Cohesion drops sharply; infrastructure degrades without maintainers. The community persists but becomes dysfunctional.
- What happens when community membership changes mid-tick (e.g., disability onset)? Membership changes are rare events processed between ticks, not during tick execution.
- How does the system handle agents belonging to 5+ communities? Reproduction cost modifiers compound multiplicatively; threat score sums across all memberships. No upper limit on community count.
- What happens when two communities have 100% member overlap? They remain distinct hyperedges with independent state. Overlap creates high solidarity potential but communities retain separate heat, cohesion, infrastructure values.
- What happens when a community's infrastructure reaches 0? The community still exists but provides no solidarity transmission amplification and no mutual aid reduction to reproduction costs. Members bear full individual costs.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST represent communities as n-ary membership structures where each community connects all its members simultaneously, not as pairwise relationships.
- **FR-002**: System MUST maintain community membership separate from the existing dyadic flow graph — two distinct data structures for two ontologically different relationship types (Constitution II.7).
- **FR-003**: System MUST support the following community types at minimum: NEW_AFRIKAN, FIRST_NATIONS, CHICANO, WHITE, QUEER, HETEROSEXUAL, TRANS, CISGENDER, DISABLED, ABLED, UNDOCUMENTED, WOMEN. Hegemonic communities (WHITE, HETEROSEXUAL, CISGENDER, ABLED) are the structural counterparts to oppressed communities — they receive full rent access, zero state heat, and reduced reproduction costs.
- **FR-004**: System MUST assign each community member a role (CORE_ORGANIZER, ACTIVE, PARTICIPANT, PERIPHERAL, SYMPATHIZER) with corresponding membership strength weights (1.0, 0.7, 0.4, 0.2, 0.1).
- **FR-005**: System MUST track independent state for each community: heat, legal_status, cohesion, infrastructure, visibility, reproduction_cost_modifier, rent_access_modifier.
- **FR-006**: System MUST compute solidarity potential between any two agents based on: base class solidarity + community overlap bonus - imperial rent differential penalty.
- **FR-007**: System MUST amplify solidarity transmission between agents who share communities, scaled by community infrastructure and cohesion.
- **FR-008**: System MUST support community-level state repression actions: designate (change legal status), infiltrate (reduce cohesion), disrupt infrastructure, arrest organizers (remove CORE_ORGANIZER members).
- **FR-009**: System MUST compute per-agent threat scores as the sum across all community memberships of: heat x effective_visibility x role_weight x legal_status_multiplier. Effective visibility equals 1.0 if the membership's overt flag is true, otherwise the membership's base visibility value.
- **FR-010**: System MUST modify each agent's reproduction cost multiplicatively based on the reproduction_cost_modifier of all communities they belong to.
- **FR-011**: System MUST modify each agent's imperial rent access based on the rent_access_modifier of their communities.
- **FR-012**: Community state (heat, cohesion, infrastructure) MUST update via alpha-smoothing (slow drift), not per-tick recalculation. Infrastructure decays naturally toward zero without active maintenance — CORE_ORGANIZER presence and player Aid verb counteract decay. Heat and cohesion also drift: heat decays toward zero (state attention fades without new provocation), cohesion decays without organizing work.
- **FR-013**: Membership changes (joining or leaving a community) MUST be processed as rare discrete events between ticks, not during tick execution.
- **FR-014**: System MUST support querying shared communities between any two agents and computing a pairwise community overlap matrix for the full population.
- **FR-015**: System MUST support legal status escalation: LEGAL → SURVEILLED → DESIGNATED_EXTREMIST → DESIGNATED_TERRORIST → CRIMINALIZED, with increasing threat multipliers (0.1, 0.5, 1.0, 2.0, 3.0). Escalation is one-way for state action — only player political struggle can reverse legal status. The state ratchets up; it does not voluntarily de-escalate.

### Key Entities

- **Community**: A collective structure that agents belong to. Has independent state (heat, cohesion, infrastructure, legal_status, visibility). Represented as a hyperedge connecting all member agents. Types include identity communities (NEW_AFRIKAN, TRANS, DISABLED, etc.) and are extensible.
- **Community Membership**: The relationship between an agent and a community. Has role (CORE_ORGANIZER through SYMPATHIZER), strength (0.1-1.0), visibility (legibility to state), and overt flag (publicly identified — when true, overrides visibility to 1.0).
- **Community State**: Per-community attributes tracking state attention (heat), internal trust (cohesion), organizational capacity (infrastructure), legal designation (legal_status), and material modifiers (reproduction_cost_modifier, rent_access_modifier).
- **Threat Score**: Per-agent computed value aggregating heat exposure across all community memberships, weighted by role and legal status. Determines targeting priority for state repression.
- **Solidarity Potential**: Per-pair computed value representing the conditions for solidarity formation based on shared community membership, penalized by material divergence (rent differential).

## Clarifications

### Session 2026-02-25

- Q: Can community legal status de-escalate (e.g., CRIMINALIZED back to SURVEILLED)? → A: No. Legal status escalation is strictly one-way for state action. De-escalation is only achievable through political struggle (player action), not state concession. The state ratchets up; only revolution reverses it.
- Q: Does community infrastructure recover naturally or require active maintenance? → A: Infrastructure decays naturally without maintenance. Only CORE_ORGANIZER activity and player Aid verb sustain or rebuild it. Communities are not self-sustaining — they require organizing work.
- Q: Does the `overt` flag on community membership have mechanical effect? → A: Yes. Overt sets membership visibility to 1.0 (fully legible to state), overriding the base visibility value. Publicly identified members are maximally visible.

## Assumptions

- Community types are predefined in an enum. Adding new community types requires a code change, not runtime configuration. This is acceptable because community categories reflect structural analysis, not user input.
- Default calibration values for community modifiers (reproduction_cost_modifier, rent_access_modifier) are estimated from academic literature and will be refined during Detroit test case validation.
- Organization-community relationships (organizations recruit from communities) are out of scope for this feature and deferred to a future extension.
- Community formation dynamics (how new communities emerge) are out of scope. This feature models existing communities.
- Geographic clustering of community membership (communities concentrated in specific territories) is out of scope but expected as a future extension relevant to the Detroit test case.
- Media/narrative effects on community visibility are out of scope.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Community membership queries (shared communities between two agents) complete using native n-ary membership operations, not pairwise edge traversal.
- **SC-002**: Agents sharing 2+ communities have measurably higher solidarity potential than agents sharing 0 communities, all else equal.
- **SC-003**: Imperial rent differential between two agents reduces solidarity potential proportionally, even when community overlap is high — formalizing that material divergence impedes solidarity.
- **SC-004**: State repression of a community (infrastructure disruption) produces a measurable increase in reproduction costs for all members of that community.
- **SC-005**: Agent threat scores correctly aggregate across multiple community memberships — an agent in two DESIGNATED_EXTREMIST communities has a higher threat score than an agent in one.
- **SC-006**: Community state updates (heat, cohesion, infrastructure) are alpha-smoothed, not instantaneous — reflecting institutional inertia.
- **SC-007**: All structural validation tests pass: round-trip membership integrity, correct overlap matrix computation, empty community exclusion, correct role weight lookups.
- **SC-008**: In the Detroit test case, NEW_AFRIKAN community membership is concentrated in Wayne County (>70% of members), and community overlap creates measurable solidarity paths between Wayne and Oakland counties.
- **SC-009**: George Jackson bifurcation outcomes in the Detroit test case are affected by cross-community solidarity topology — presence or absence of cross-cutting community memberships changes the bifurcation result.
