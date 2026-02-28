# Feature Specification: Organization Base Model

**Feature Branch**: `031-organization-base-model`
**Created**: 2026-02-27
**Status**: Draft
**Input**: User description: "Organization Base Model — unified agent model for all organizations in Babylon"

## Clarifications

### Session 2026-02-27

- Q: How does the simulation track who belongs to an organization — individual member IDs, weighted edges to population blocks, or hybrid? → A: Hybrid — population-block edges for rank-and-file membership, individual nodes for Key Figures and cadre. Composition queries computed from both sources.
- Q: When multiple organizations act on the same community in the same tick, how do their consciousness effects combine? → A: Weighted by organization strength — effects weighted by (cadre_level * cohesion) before summing. Stronger orgs have more influence.
- Q: What is the default elder (D'-phase) capacity reduction factor? → A: Grounded in BLS labor force participation rate for 65+ (~19-23%). Default approximately 0.2, exposed as a tunable simulation parameter with BLS provenance. Design note: a single scalar is a Phase 1 placeholder. Elders have reduced action capacity but elevated legitimacy and institutional memory — the reduction should eventually be action-type-specific in Phase 2 (low for STRIKE, high for EDUCATE), mirroring the consciousness formula's action_base[action_type] pattern.
- Q: Do Business and StateApparatus organizations have consciousness effects? → A: Yes — all four org types carry consciousness tendency. StateApparatus defaults to LIBERAL, configurable per instance, shifts toward FASCIST at high heat. Business tendency is sector-dependent: high-tech, complex supply chains, international trade trends LIBERAL; low-tech, extractive, raw labor power, tariff-dependent trends FASCIST. Configurable per instance.
- Q: What determines the base magnitude of a consciousness effect before weighting? → A: Five-factor product: `action_base[action_type] * tendency_modifier[consciousness_tendency] * cadre_level * cohesion * credibility`. Phase 1 defines tunable tendency_modifier parameters per consciousness tendency (REVOLUTIONARY, LIBERAL, FASCIST) with action_base defaulting to 1.0. Phase 2 OODA introduces action-type-specific coefficients as a second multiplicative factor. Design note: tendency_modifier should eventually encode not just magnitude ("how hard does this hit") but also durability ("how long does the result persist"). Phase 1 treats it as scalar magnitude; durability dimension deferred.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Instantiate All Organization Types (Priority: P1)

A simulation designer creates organizations of all four types for a Detroit scenario: a state apparatus (Detroit Police Department), a business (Ford Motor Company), a political faction (revolutionary organization), and a civil society organization (mainstream church). Each organization has shared base properties (name, type, class character, internal topology, cohesion, cadre level, budget, legal standing, territories, headquarters, heat, institutional persistence) plus type-specific attributes.

**Why this priority**: Organizations are the ONLY agents in Babylon. Everything else is substrate. Without the ability to create and configure organizations, no agent behavior exists. This is the absolute foundation.

**Independent Test**: Can be fully tested by creating one instance of each organization type with Detroit-specific parameters and verifying all properties are correctly stored, queryable, and immutable.

**Acceptance Scenarios**:

1. **Given** a Detroit scenario, **When** a state apparatus "Detroit Police Department" is created with jurisdiction "municipal", violence capacity 0.7, surveillance capacity 0.3, and centrality-only intelligence methodology with observation ceiling 0.2, **Then** the organization exists with all base and state-apparatus-specific properties correctly set.
2. **Given** a Detroit scenario, **When** a business "Ford Motor Company" is created with sector "manufacturing", employment count from public data, surplus extraction rate, and revenue, **Then** the organization exists as a business with all economic attributes intact.
3. **Given** a Detroit scenario, **When** a political faction with consciousness strategy REVOLUTIONARY is created, **Then** the faction's strategy correctly indicates it pushes revolutionary consciousness within communities it acts upon.
4. **Given** a Detroit scenario, **When** a civil society org (mainstream church) is created with consciousness tendency LIBERAL and legitimacy 0.6, **Then** the organization's tendency correctly indicates its ideological effect on communities.
5. **Given** any organization, **When** an attempt is made to modify its properties in place, **Then** the modification is rejected. All changes produce new instances (immutability).

______________________________________________________________________

### User Story 2 — Analyze Organization Composition (Priority: P2)

The simulation queries an organization's membership composition along three axes:
- **Class composition**: What proportion of members belong to each class position (proletarian, labor aristocracy, lumpenproletariat, etc.)?
- **Community composition**: What community hyperedges do members belong to (New Afrikan, settler, incarcerated, etc.)?
- **Lifecycle composition**: What proportion of members are in D-phase (youth), P-phase (adult), or D'-phase (elder)?

This determines whether an organization's declared class character matches its actual membership, and constrains its effective capacity based on demographics.

**Why this priority**: Composition analysis bridges organizations (agents) to the substrate (social classes, communities, lifecycle). Without this, organizations are disconnected from the material conditions they exist within.

**Independent Test**: Can be tested by creating an organization with known member distribution and verifying all three composition queries return correct proportional breakdowns.

**Acceptance Scenarios**:

1. **Given** a political faction with members: 60% proletarian, 30% labor aristocracy, 10% lumpenproletariat, **When** class composition is queried, **Then** the result is a proportional breakdown summing to 1.0 (within 1% error).
2. **Given** an organization whose members belong to multiple community hyperedges (NEW_AFRIKAN, INCARCERATED, ADULT), **When** community composition is queried, **Then** the result reflects per-community membership proportions. Because members can belong to multiple communities simultaneously, proportions may sum to greater than 1.0.
3. **Given** an organization with 10% youth (D-phase), 70% adult (P-phase), 20% elder (D'-phase), **When** lifecycle composition is queried, **Then** proportions sum to 1.0, and the effective labor pool is determined by the adult proportion (only P-phase members can take direct action).

______________________________________________________________________

### User Story 3 — Consciousness Effect on Communities (Priority: P3)

When an organization acts within a community hyperedge (education, service provision, recruitment, organizing), the organization's consciousness strategy or tendency determines the ideological effect on that community's collective identity and dominant tendency. This is the primary mechanism of ideological struggle in the simulation.

- A **revolutionary** faction educating within a New Afrikan community raises oppositional consciousness (collective_identity increases, tendency moves toward REVOLUTIONARY).
- A **liberal** civil society org providing services reinforces assimilationist-liberal consciousness (collective_identity maintained or lowered, tendency stays LIBERAL).
- A **fascist** faction organizing within a settler community raises lateral antagonism (tendency moves toward FASCIST).
- A **patriarchal institution** (traditional family org) acting within a PATRIARCHAL hyperedge reinforces extraction while pushing assimilationist consciousness.

**Why this priority**: This is the core game mechanic linking organizations to the ideological dimension of class conflict. The player's ability to shift community consciousness through organizational action is central to Babylon's gameplay.

**Independent Test**: Can be tested by measuring the consciousness delta to a target community after an organization with a known strategy/tendency acts within it, across all three consciousness directions.

**Acceptance Scenarios**:

1. **Given** a revolutionary faction acts within a community with collective_identity 0.3 and dominant_tendency LIBERAL, **When** the consciousness effect is calculated, **Then** collective_identity increases (positive delta) and tendency pressure moves toward REVOLUTIONARY.
2. **Given** a liberal civil society org provides services within a community, **When** the consciousness effect is calculated, **Then** collective_identity is maintained or decreases, and tendency pressure reinforces LIBERAL.
3. **Given** a fascist faction organizes within a SETTLER community, **When** the consciousness effect is calculated, **Then** lateral antagonism increases and tendency pressure moves toward FASCIST.
4. **Given** a civil society org with LIBERAL tendency provides services in a community with collective_identity 0.7 and tendency REVOLUTIONARY, **When** the effect is calculated, **Then** the effect dampens revolutionary consciousness (negative delta to collective_identity).

______________________________________________________________________

### User Story 4 — State Intelligence Methodology (Priority: P4)

State apparatus organizations have intelligence methodologies grounded in network analysis theory (Sparrow 1991/1993) that determine what they can perceive about other organizations' networks. Different agencies have different capabilities:

- **FBI-equivalent**: All four analysis types (centrality, structural equivalence, template matching, temporal), observation ceiling ~0.4
- **Local police**: Centrality analysis only, observation ceiling ~0.2
- **Fusion center**: Centrality + temporal analysis, observation ceiling ~0.5

The observation ceiling represents a fundamental limit: the state never sees the network as it actually is. The observed network is always a lossy, distorted view of reality.

**Why this priority**: Differential intelligence capabilities create strategic depth. Operating under variable state observation is a core gameplay tension — the player must consider which state actors can see which aspects of their network.

**Independent Test**: Can be tested by creating three state apparatus organizations with different intelligence configurations and verifying their capabilities differ as specified.

**Acceptance Scenarios**:

1. **Given** an FBI-equivalent state apparatus, **When** its intelligence methodology is queried, **Then** all four analysis capabilities are enabled with observation ceiling approximately 0.4.
2. **Given** a local police department, **When** its intelligence methodology is queried, **Then** only centrality analysis is enabled with observation ceiling approximately 0.2.
3. **Given** a fusion center, **When** its intelligence methodology is queried, **Then** centrality and temporal analysis are enabled with observation ceiling approximately 0.5.

______________________________________________________________________

### User Story 5 — Key Figure Identification and Vulnerability (Priority: P5)

Organizations contain key figures — individuals occupying structurally critical positions within the internal topology. A key figure is "irreplaceable" in the Sparrow equivalence sense: their removal would disconnect or severely degrade the organization's network. This creates asymmetric vulnerability:

- **STAR/HIERARCHY** topologies: The central leader is a singleton. Removal fragments the organization.
- **MESH** topologies: Most members are equivalent. Few key figures exist.
- **CELL** topologies: Only inter-cell cutouts are key figures. Individual cell members are replaceable.

**Why this priority**: Key figure mechanics create the fundamental strategic tension between organizational efficiency (centralized) and resilience (distributed). This is essential for both player strategy and state counter-organization gameplay.

**Independent Test**: Can be tested by identifying key figures in organizations with known topologies and verifying their removal causes expected topological degradation.

**Acceptance Scenarios**:

1. **Given** an organization with STAR topology centered on one leader, **When** key figures are identified, **Then** the central node is flagged as irreplaceable, and its removal would fragment the organization.
2. **Given** an organization with CELL topology, **When** key figures are identified, **Then** only inter-cell connectors (cutouts) are flagged. Removing any single cell member does not fragment the network.
3. **Given** a key figure is removed from an organization, **When** cohesion is recalculated, **Then** cohesion decreases proportionally to the figure's structural importance within the topology.

______________________________________________________________________

### User Story 6 — D-P-D' Lifecycle Capacity Constraints (Priority: P6)

Organization membership reflects the D-P-D' lifecycle circuit. Youth members (D-phase) are politically educable through the organization's activities but cannot take direct action. Adult members (P-phase) form the active base. Elder members (D'-phase) carry institutional memory but have reduced action capacity. The dependency ratio (non-active to active members) constrains effective capacity.

Organizations controlling D-phase infrastructure (schools, youth programs) can influence ideological transmission during the socialization period, determining what consciousness youth carry into adulthood.

**Why this priority**: Without lifecycle integration, organizations are ageless abstractions disconnected from the population dynamics. Linking to D-P-D' creates realistic demographic constraints on organizational capacity.

**Independent Test**: Can be tested by creating organizations with known lifecycle distributions and verifying capacity calculations reflect phase-based constraints.

**Acceptance Scenarios**:

1. **Given** an organization with 70% adult, 20% elder, 10% youth, **When** effective capacity is calculated, **Then** adults contribute full capacity, elders contribute reduced capacity, and youth contribute zero action capacity.
2. **Given** an organization controlling D-phase infrastructure (a school), **When** it acts on youth members within its territory, **Then** it can influence the ideological transmission these youth receive during D-phase socialization.
3. **Given** an organization whose membership ages without youth recruitment over multiple ticks, **When** lifecycle composition is recalculated, **Then** the dependency ratio increases and effective capacity decreases each tick.

______________________________________________________________________

### User Story 7 — Legacy Model Unification (Priority: P7)

The simulation currently has three separate representations: a component model (cohesion + cadre level only), a faction schema (ideology, class composition, military, influence), and an institution schema (type, functions, controlled-by). These must be unified into a single coherent model that can represent everything the legacy models could represent.

**Why this priority**: Technical debt from three competing representations blocks all downstream features. Unification is a prerequisite, but ranked P7 because the new model itself (US1) supersedes legacy data — migration is a cleanup concern.

**Independent Test**: Can be tested by round-trip migration: every entity in existing faction and institution data files can be expressed as a unified organization subtype, and the migrated data retains all meaningful information.

**Acceptance Scenarios**:

1. **Given** existing faction data (e.g. "National Revival Movement" with ideology, class composition, military units), **When** migrated to the unified model, **Then** it becomes a PoliticalFaction with equivalent properties and no information loss.
2. **Given** existing institution data (e.g. "Policing" as a state institution, "Labor Unions" as an economic institution), **When** migrated, **Then** state institutions become StateApparatus organizations and economic/social institutions become CivilSocietyOrg or Business as appropriate.
3. **Given** the existing component model (cohesion + cadre_level), **When** migrated, **Then** these fields are preserved as base Organization properties, and the component model is deprecated.

______________________________________________________________________

### Edge Cases

- **Zero members**: Composition queries return empty distributions. Effective capacity is zero. Organization still exists as a legal/institutional shell.
- **All key figures removed**: Cohesion drops to minimum threshold (does not reach zero). Organization becomes non-functional but persists until explicitly dissolved.
- **Zero budget**: Organization continues to exist but cannot take resource-requiring actions. Volunteer labor (unpaid cadre) can still act.
- **Sovereign state apparatus loses legitimacy**: Legal standing (SOVEREIGN) does not change — sovereignty is structural. But the D-P-D' legitimation index declines, feeding bifurcation risk.
- **Member in multiple organizations**: Explicitly permitted. Each organization independently counts shared members in its composition.
- **Consciousness strategy contradicts class character** (e.g. bourgeois org with REVOLUTIONARY strategy): Permitted. Models co-optation, false consciousness, and entryism. Simulation mechanics expose contradictions through gameplay rather than preventing them at creation.
- **Organization with only D-phase (youth) members**: Effective action capacity is zero. Organization can receive ideological transmission but cannot take collective action.
- **State apparatus observes itself**: Observation ceiling applies even to self-observation — no organization has perfect self-knowledge.
- **Opposing organizations act on same community**: A revolutionary faction (cadre 0.8, cohesion 0.7, credibility 0.6) and a liberal church (cadre 0.3, cohesion 0.5, credibility 0.8) both act on the same community. Each produces a delta via the five-factor formula, then deltas are summed and clamped. The revolutionary org's higher cadre*cohesion may be offset by the church's higher credibility — the net effect depends on tendency_modifier magnitudes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support four distinct organization types sharing a common base of properties (identifier, name, type, class character, internal topology, cohesion, cadre level, budget, legal standing, territory footprint, headquarters, state attention/heat, institutional persistence) with type-specific extensions for each.
- **FR-002**: System MUST enforce immutability on all organization instances. Any property change produces a new instance; direct mutation is rejected with an error.
- **FR-003**: System MUST calculate class composition as proportional membership across all class positions, with proportions summing to 1.0 (within 1% tolerance). Empty membership returns an empty distribution.
- **FR-004**: System MUST calculate community composition as proportional membership across all 14 community hyperedge types. Because members participate in multiple communities, proportions may sum to greater than 1.0.
- **FR-005**: System MUST calculate lifecycle composition as proportional membership across D-phase (youth), P-phase (adult), and D'-phase (elder), summing to 1.0. This directly feeds effective capacity calculation.
- **FR-006**: System MUST compute a consciousness effect when an organization acts within a community. ALL four organization types carry a consciousness tendency and produce consciousness effects. The consciousness delta is a five-factor product: `action_base[action_type] * tendency_modifier[consciousness_tendency] * cadre_level * cohesion * credibility`. In Phase 1, action_base defaults to 1.0 (Phase 2 OODA introduces action-type-specific coefficients). The tendency_modifier is a tunable simulation parameter per consciousness tendency: REVOLUTIONARY (positive, raises collective_identity), LIBERAL (negative or zero, maintains/lowers collective_identity), FASCIST (shifts dominant_tendency toward fascist). Design note: tendency_modifier encodes both magnitude and (in future phases) durability of the consciousness shift — Phase 1 treats it as scalar magnitude only. Credibility represents the organization's perceived authority within the target community. Consciousness tendency defaults: PoliticalFaction and CivilSocietyOrg declare tendency explicitly; StateApparatus defaults to LIBERAL (shifts toward FASCIST at high heat, configurable per instance); Business tendency is sector-dependent (high-tech/international-trade capital trends LIBERAL, extractive/autarkic/raw-labor capital trends FASCIST, configurable per instance). When multiple organizations act on the same community in the same tick, their weighted deltas are summed and the combined result is clamped to valid bounds.
- **FR-007**: State apparatus organizations MUST have configurable intelligence methodology with four boolean analysis capabilities (centrality, structural equivalence, template matching, temporal) and an observation ceiling in [0, 1] bounding the fraction of true network topology perceivable.
- **FR-008**: System MUST identify key figures as structurally critical nodes within an organization's internal topology. STAR and HIERARCHY topologies produce singletons (irreplaceable leaders); CELL topologies produce key figures only at inter-cell connections; MESH topologies produce few or no key figures.
- **FR-009**: Organizations MUST support five relationship types to the simulation graph: MEMBERSHIP (org contains member), RECRUITMENT (org recruiting from population), EMPLOYMENT (business employs workers), COMMAND (hierarchy within org), and PRESENCE (org operates in territory).
- **FR-010**: System MUST provide a deprecation path from three legacy representations (component model, faction schema, institution schema) to the unified organization model with zero information loss.
- **FR-011**: All bounded numeric properties MUST enforce bounds at creation: cohesion, cadre_level, heat, observation_ceiling, violence_capacity, surveillance_capacity, legitimacy in [0, 1]; budget, revenue, employment_count in [0, infinity).
- **FR-012**: Effective organizational capacity MUST reflect lifecycle composition: P-phase (adult) members contribute full capacity (1.0), D'-phase (elder) members contribute reduced capacity (default factor ~0.2, grounded in BLS labor force participation rate for 65+, exposed as tunable parameter), and D-phase (youth) members contribute zero action capacity (0.0). Phase 1 uses a single scalar for elder capacity; Phase 2 OODA replaces this with a per-action-type capacity matrix (elders have low capacity for physical actions like strikes but high capacity for knowledge/legitimacy actions like education).
- **FR-013**: Organizations controlling D-phase infrastructure MUST be able to influence ideological transmission during the youth socialization period, with the effect magnitude determined by the organization's consciousness strategy/tendency and its control over the relevant territory.
- **FR-014**: An organization's class character (BOURGEOIS, PROLETARIAN, or CONTESTED) represents which class the organization *serves*, which MAY differ from its actual class composition. The system MUST NOT enforce consistency between class character and composition — contradictions are legitimate game states.
- **FR-015**: System MUST support five internal topology types (STAR, HIERARCHY, MESH, CELL) that determine organizational efficiency, key figure vulnerability, and resilience to targeted disruption.
- **FR-016**: System MUST support five legal standing levels (SOVEREIGN, CHARTERED, REGISTERED, INFORMAL, UNDERGROUND) that constrain what actions an organization can take and how visible it is to state apparatus observation.
- **FR-017**: Organization membership MUST use a hybrid representation: rank-and-file members tracked as weighted edges to population group nodes, Key Figures and cadre tracked as individually-identified nodes within the organizational subgraph. Composition queries (class, community, lifecycle) MUST aggregate both population-block weights and individual member attributes into a unified proportional result.

### Key Entities

- **Organization (Base)**: The foundational agent entity representing any collective actor — from the FBI to a neighborhood mutual aid group. Core attributes: identity, type classification, class character (which class it serves), internal topology (how it's structured), organizational health (cohesion, cadre level), resources (budget), legal standing, spatial footprint (territories, headquarters), state attention (heat), and institutional durability. Organizations are views over the simulation graph, not separate node types. Membership is hybrid: rank-and-file members are tracked as weighted edges to population group nodes (SocialClass blocks), while Key Figures and cadre are individually-tracked nodes within the organizational subgraph. Composition queries aggregate both sources.
- **State Apparatus**: State violence and surveillance wielders. Distinguished by jurisdiction level (national/state/county/municipal), violence capacity, surveillance capacity, legal authorities, and intelligence methodology. Consciousness tendency defaults to LIBERAL (state legitimates existing order) but shifts toward FASCIST at high heat; configurable per instance. Models everything from municipal police to federal agencies.
- **Business**: Capital-accumulating organizations. Distinguished by economic sector, employment count, surplus extraction rate, and revenue. Consciousness tendency is sector-dependent: high-tech, complex-supply-chain, international-trade capital trends LIBERAL; low-tech, extractive, raw-labor, tariff-dependent capital trends FASCIST. Configurable per instance. Models the employing class across scales.
- **Political Faction**: Organizations contesting for political power. Distinguished by ideology, player relationship, and consciousness strategy (what ideological tendency they push within communities). The primary vehicle for player agency and NPC political action.
- **Civil Society Organization**: Non-state, non-business collective formations. Distinguished by service type, legitimacy, and consciousness tendency. Models churches, unions, mutual aid networks, cultural organizations — the terrain of ideological struggle.
- **Intelligence Methodology**: Analytic capabilities of a state apparatus grounded in network analysis theory (Sparrow 1991/1993). Four capability dimensions plus an observation ceiling representing fundamental intelligence limits. Models the real-world gap between FBI, local PD, and fusion center capabilities.
- **Key Figure**: An individual occupying a structurally critical position within an organization's internal network. Importance defined topologically — removal degrades connectivity proportionally to structural centrality. Singletons (nodes with no structural equivalent) are irreplaceable high-value targets.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All four organization subtypes instantiable for a Detroit scenario with historically-grounded parameters (Detroit PD as state apparatus, Ford as business, a revolutionary faction, a mainstream church as civil society) within the same simulation context.
- **SC-002**: Class composition, community composition, and lifecycle composition queries each return correct proportional breakdowns matching known membership distributions, with less than 1% numerical error on each axis.
- **SC-003**: Consciousness effect calculations produce directionally correct results for all three tendency_modifier values (REVOLUTIONARY positive, LIBERAL negative/zero, FASCIST shifts tendency toward fascist), with magnitude proportional to the five-factor product (action_base * tendency_modifier * cadre_level * cohesion * credibility). Verified against all 14 community types. A high-cadre high-cohesion organization produces measurably larger deltas than a low-cadre low-cohesion one.
- **SC-004**: Three tiers of state intelligence capability (local PD, fusion center, FBI) produce observably different views of the organizational network, with higher-tier agencies perceiving more of the true topology but never exceeding their observation ceiling.
- **SC-005**: Key figure identification correctly distinguishes centralized topologies (STAR/HIERARCHY produce singletons) from distributed topologies (MESH/CELL produce few or no key figures), with measured cohesion loss upon key figure removal.
- **SC-006**: Every entity in existing faction and institution data files representable as a unified organization subtype with zero information loss, verified by round-trip migration.
- **SC-007**: All organization instances provably immutable — mutation attempts raise errors; all state changes produce new instances.
- **SC-008**: Effective capacity correctly reflects lifecycle composition: organization with 100% youth has zero capacity; 100% adult has maximum capacity (1.0); 100% elder has capacity ~0.2 (BLS-grounded default); mixed compositions scale linearly (e.g., 70% adult + 20% elder + 10% youth = 0.7 * 1.0 + 0.2 * 0.2 + 0.1 * 0.0 = 0.74).

## Assumptions

- The existing community hyperedge layer (14 types, 3 categories, CommunityConsciousness with collective_identity/dominant_tendency/ideological_contestation) is stable and will not change during this feature's implementation.
- The D-P-D' lifecycle circuit (Feature 030) provides the lifecycle phase data needed for US6. If Feature 030 is not yet integrated, lifecycle composition returns a default distribution (100% adult).
- "Consciousness strategy" (PoliticalFaction) and "consciousness tendency" (CivilSocietyOrg) are the same underlying concept (a ConsciousnessTendency value) with different field names reflecting the distinction between deliberate strategic choice (factions) and emergent institutional character (civil society). Both produce the same type of consciousness effect.
- Intelligence methodology observation ceilings (0.2, 0.4, 0.5) are initial calibration values that will be exposed as tunable simulation parameters, not hardcoded constants.
- The four internal topology types (STAR, HIERARCHY, MESH, CELL) are sufficient for Phase 1. More nuanced topology modeling (e.g., hybrid structures, dynamic topology evolution) is deferred to later phases.
- Key figure identification requires only structural analysis (degree centrality, articulation points) — no behavioral or intelligence-based identification in this phase.
- Business employment counts and economic data align with existing QCEW data integration patterns from the economics module.

## Scope Exclusions

The following are explicitly **not** part of this feature:

- **OODA loop mechanics** (Phase 2): Organizations do not yet take autonomous actions or make decisions.
- **Attention threads** (Phase 3): No attention/priority system for organization decision-making.
- **Bifurcation analysis** (Phase 4): Organizations do not yet feed into bifurcation calculations.
- **NPC AI** (Phase 5): Non-player organizations do not yet have autonomous behavior.
- **Org-Territory integration** (Phase 6): Deep territory-organization mechanics deferred.
- **Organization-to-Institution transition**: The process by which organizations crystallize into institutions is deferred.
- **Coalition/united front formation**: Inter-organization alliances and coalitions are deferred.
