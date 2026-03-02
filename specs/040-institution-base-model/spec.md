# Feature Specification: Institution Base Model

**Feature Branch**: `040-institution-base-model`
**Created**: 2026-03-02
**Status**: Draft
**Input**: Institution Base Model - Third layer entity between substrate and agents. Institutions are a distinct layer between substrate (SocialClass, Territory, Community hyperedges) and agents (Organizations). They are agent-generating substrate that crystallizes past class struggles into self-reproducing social relations. They persist through member turnover, generate and constrain Organizations, have internal balance-of-forces between ruling-class fractions, and serve as sites of class struggle.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Instantiate RSA Institutions (Priority: P1)

The simulation must be able to create and maintain Repressive State Apparatus institutions (police departments, courts, military bases, prisons) that house Organizations like the FBI or local police. These institutions persist independently of their personnel — destroying all current FBI agents degrades but does not destroy the DOJ institution that houses them. The DOJ can spawn a replacement Organization when a housed Organization is destroyed.

**Why this priority**: RSA institutions are the primary antagonist infrastructure the player encounters. Without them, the state has no persistent repressive capacity and the core gameplay loop (player vs. state) cannot function.

**Independent Test**: Can be fully tested by instantiating a DOJ institution as RSA_JUDICIAL with the FBI as a housed StateApparatus Organization, verifying that destroying the FBI Organization degrades but does not destroy the DOJ, and confirming the DOJ can spawn a replacement Organization.

**Acceptance Scenarios**:

1. **Given** an RSA_JUDICIAL institution (DOJ) with FBI as a housed Organization, **When** the FBI Organization is destroyed, **Then** the DOJ institution persists with degraded capacity but retains its social function (ADJUDICATION) and can spawn a replacement Organization.
2. **Given** an RSA_POLICE institution (Detroit PD) with personnel_capacity=500, **When** 80% of personnel are removed, **Then** the institution persists with reduced operational capacity but its legal authorities and fixed assets remain intact.
3. **Given** an RSA_MILITARY institution with jurisdiction over specific territories, **When** queried for its territory footprint, **Then** it returns the correct set of Territory IDs where its infrastructure exists.

______________________________________________________________________

### User Story 2 - Instantiate ISA Institutions (Priority: P1)

The simulation must create Ideological State Apparatus institutions (schools, churches, media organizations, cultural bodies) that function predominantly by ideology rather than violence. These institutions have structural selectivity — they make certain actions cheaper and others more expensive for housed Organizations. A university makes EDUCATE cheap but REPRESS expensive.

**Why this priority**: ISA institutions are the terrain where hegemony is manufactured and contested (Gramsci's war of position). They are the primary sites of class struggle for the player and are essential to the consciousness mechanics.

**Independent Test**: Can be fully tested by instantiating Detroit Public Schools as ISA_EDUCATIONAL with lifecycle_function=D (youth/dependent phase), verifying structural selectivity makes EDUCATE actions cheaper and REPRESS actions more expensive for housed Organizations.

**Acceptance Scenarios**:

1. **Given** an ISA_EDUCATIONAL institution (Detroit Public Schools) with lifecycle_function=D, **When** a housed Organization attempts an EDUCATE action, **Then** the structural selectivity modifier reduces the action cost (modifier < 1.0).
2. **Given** an ISA_EDUCATIONAL institution, **When** a housed Organization attempts a REPRESS action, **Then** the structural selectivity modifier increases the action cost (modifier > 1.0).
3. **Given** an ISA_RELIGIOUS institution (Catholic Church) with community embeddedness, **When** queried for community embeddedness, **Then** it returns the set of community hyperedges (by CommunityType) in which the institution is embedded.

______________________________________________________________________

### User Story 3 - Internal Balance of Forces (Priority: P1)

Each institution maintains an internal balance of forces between three ruling-class fractions: Liberal-Technocratic, Revanchist-Fascist, and Institutionalist-Bonapartist. The hegemonic fraction (whichever has the highest weight) modulates the OODA orientation of housed Organizations. This balance shifts slowly (coefficient-level, alpha-smoothed) in response to crisis intensity, legitimacy erosion, and external threats.

**Why this priority**: The internal factional balance is what makes institutions dynamic rather than static. It determines whether the state responds with assimilation or repression, and creates the contradictions the player can exploit. Without it, institutions are inert containers.

**Independent Test**: Can be fully tested by creating an FBI-equivalent institution with initial balance {LIBERAL: 0.5, REVANCHIST: 0.3, BONAPARTIST: 0.2}, verifying the hegemonic fraction is LIBERAL, then applying crisis conditions to shift the balance toward REVANCHIST and confirming the hegemonic fraction changes.

**Acceptance Scenarios**:

1. **Given** an institution with faction_weights {LIBERAL: 0.5, REVANCHIST: 0.3, BONAPARTIST: 0.2}, **When** the hegemonic fraction is computed, **Then** it returns LIBERAL_TECHNOCRATIC.
2. **Given** the same institution under rising crisis (crisis_intensity=0.8, legitimacy=0.3), **When** the balance update is applied, **Then** the REVANCHIST weight increases and LIBERAL weight decreases (alpha-smoothed, slow coefficient-level change).
3. **Given** an institution where BONAPARTIST weight > 0.4 and no other fraction > 0.35, **When** the Bonapartist threshold is evaluated, **Then** the institution is flagged as entering Bonapartist mode (independent of civilian oversight).

______________________________________________________________________

### User Story 4 - Economic Institutions (Priority: P2)

The simulation must support economic institutions (firms, banks, resource extraction companies) that house Business Organizations. These institutions have class_inscription, structural selectivity, and material infrastructure (budget, fixed assets, legal authorities) that shape what Business Organizations can do within them.

**Why this priority**: Economic institutions are where surplus extraction occurs. They are necessary for the full D-P-D' lifecycle circuit but are not the primary antagonist infrastructure — they augment the political simulation rather than drive it.

**Independent Test**: Can be fully tested by instantiating Ford Motor Company as ECONOMIC_PRODUCTIVE housing a Business Organization, verifying budget allocation, fixed asset tracking, and structural selectivity for economic actions.

**Acceptance Scenarios**:

1. **Given** an ECONOMIC_PRODUCTIVE institution (Ford) housing a Business Organization, **When** the Business Organization's available actions are queried, **Then** the institution's permitted_org_types includes Business and its action_modifiers favor production-related actions.
2. **Given** an ECONOMIC_FINANCIAL institution (a bank) with budget_independence=0.9, **When** its reproduction capacity is computed, **Then** it reflects high self-funding capacity in the overall reproduction score.

______________________________________________________________________

### User Story 5 - Institutional Reproduction (Priority: P2)

Institutions self-reproduce through formal mechanisms: recruitment pipelines, training programs, succession protocols, budget independence, and legal self-perpetuation. The reproduction capacity determines how effectively an institution replaces lost members. An institution with high reproduction capacity (police academy, university tenure system) is far harder to destroy than one with low reproduction capacity.

**Why this priority**: Reproduction is what distinguishes institutions from organizations. Without it, institutions would be vulnerable to the same targeted disruption (COINTELPRO-style) that destroys organizations, collapsing the three-layer architecture.

**Independent Test**: Can be fully tested by creating two institutions — one with full reproduction mechanisms (recruitment_pipeline=True, training_program=True, succession_protocol=True, budget_independence=0.8, legal_self_perpetuation=True) and one with minimal — then verifying that destroying personnel in the first results in much less capacity degradation than the second.

**Acceptance Scenarios**:

1. **Given** an institution with all reproduction mechanisms active (recruitment, training, succession, legal mandate) and budget_independence=0.8, **When** reproduction_capacity is computed, **Then** it returns a value > 0.8.
2. **Given** an institution with no reproduction mechanisms and budget_independence=0.1, **When** reproduction_capacity is computed, **Then** it returns a value < 0.2.
3. **Given** an institution with succession_protocol=True, **When** the housed Organization's leader is removed, **Then** the institution triggers a replacement through its succession mechanism rather than dissolving.

______________________________________________________________________

### User Story 6 - Institutional Persistence and Social Function (Priority: P2)

Each institution carries a social function (EMPLOYMENT, EDUCATION, POLICING, HEALTHCARE, CARE, ADJUDICATION, etc.) that represents a population need. An institution persists until an alternative institution with the same social function reaches sufficient legitimacy to absorb its constituency. Destroying an institution without replacing its social function creates a crisis of reproduction.

**Why this priority**: The social function / replacement principle is the core strategic constraint — it prevents naive "just destroy the police" strategies and forces the player to build alternative institutions before attempting institutional destruction.

**Independent Test**: Can be fully tested by creating an RSA_POLICE institution with social_function=POLICING serving specific territories, verifying it cannot be destroyed while no alternative institution serves that function, and confirming that an unmet social function generates crisis signals.

**Acceptance Scenarios**:

1. **Given** an institution with social_function=POLICING and legitimacy=0.6 serving territories T1-T5, **When** its legitimacy drops below the destruction threshold, **Then** it persists as long as no alternative institution covers the POLICING function for those territories.
2. **Given** an institution that is destroyed without a replacement, **When** the social function becomes UNMET in affected territories, **Then** a crisis_of_reproduction signal is generated for the affected SocialClass blocks.

______________________________________________________________________

### Edge Cases

- What happens when all housed Organizations within an institution are destroyed simultaneously? The institution persists in degraded state with zero operational capacity but intact infrastructure, awaiting reproduction.
- How does the system handle an institution with faction_weights that don't sum to 1.0? Weights must be normalized; the system rejects or corrects invalid weight distributions.
- What happens when an institution's legitimacy reaches exactly 0.0? The institution enters a terminal degradation state but is not immediately destroyed — destruction requires replacement of its social function.
- How does an institution with zero budget maintain itself? budget_independence=0.0 means the institution relies entirely on external funding; loss of funding erodes reproduction_capacity over time but does not cause instant destruction.
- What happens when the same Organization is housed in multiple institutions? This is valid (e.g., a political faction operating within both a university and a media organization) — each institution-org relationship is tracked independently with separate resource provision and oversight values.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST represent institutions as a distinct entity layer between substrate (SocialClass, Territory, Community hyperedges) and agents (Organizations), with no OODA loop agency.
- **FR-002**: System MUST classify institutions by Althusserian apparatus type: RSA subtypes (Executive, Military, Police, Judicial, Carceral), ISA subtypes (Educational, Religious, Family, Legal, Political, Communications, Cultural), and Economic subtypes (Productive, Financial, Extractive).
- **FR-003**: System MUST assign each institution a social function from a defined set (EMPLOYMENT, EDUCATION, WORSHIP, POLICING, HEALTHCARE, CARE, ADJUDICATION, COMMUNICATION, LEGISLATION, INCARCERATION, MILITARY_DEFENSE, FINANCIAL_INTERMEDIATION).
- **FR-004**: System MUST track class inscription (BOURGEOIS, PROLETARIAN, CONTESTED) separately from Organization class_character, with inscription changing only through sustained struggle on coefficient timescale (alpha-smoothed).
- **FR-005**: System MUST maintain internal balance of forces between three ruling-class fractions (Liberal-Technocratic, Revanchist-Fascist, Institutionalist-Bonapartist) with weights summing to 1.0 and a computed hegemonic fraction.
- **FR-006**: System MUST compute internal_contestation as a measure of how actively factional warfare is occurring within the institution (high = active warfare, low = settled hegemony).
- **FR-007**: System MUST define structural selectivity as action cost modifiers for Organizations housed within the institution (e.g., university: EDUCATE=0.7 cheaper, REPRESS=2.0 more expensive).
- **FR-008**: System MUST track material infrastructure: budget, fixed assets (Territory IDs), legal authorities, and personnel capacity.
- **FR-009**: System MUST track institutional persistence attributes: formalization_level, succession_protocol, institutional_inertia, and legitimacy.
- **FR-010**: System MUST support housing multiple Organizations within a single institution, including Organizations with conflicting factional alignments.
- **FR-011**: System MUST model institution-organization relationships including resource provision, legal cover, legitimacy transfer, action oversight, and factional alignment.
- **FR-012**: System MUST model reproduction mechanisms (recruitment pipeline, training program, succession protocol, budget independence, legal self-perpetuation) with a computed reproduction_capacity score.
- **FR-013**: System MUST support querying an institution's housed Organizations, territory footprint, and community embeddedness (which community hyperedges the institution participates in).
- **FR-014**: System MUST compute how the hegemonic fraction modulates housed Organizations' OODA profiles (Liberal favors ASSIMILATE, Revanchist favors REPRESS, Bonapartist favors self-preservation).
- **FR-015**: System MUST support an optional D-P-D' lifecycle phase assignment (D=youth/dependent, P=productive/adult, D'=elder/dependent) or None for non-phase-specific institutions.
- **FR-016**: System MUST ensure that destroying all housed Organizations degrades but does not destroy the institution — the institution persists and can spawn replacement Organizations via reproduction mechanisms.
- **FR-017**: System MUST deprecate and replace the existing institution.schema.json with the new Institution model.
- **FR-018**: System MUST deprecate Organization.is_institution field (from Feature 030) in favor of separate Institution entities.

### Key Entities

- **Institution**: Third-layer entity representing crystallized social relations. Key attributes: apparatus_type, social_function, class_inscription, internal_balance_of_forces, structural_selectivity (action modifiers), material infrastructure (budget, fixed_assets, legal_authorities, personnel_capacity), persistence attributes (formalization_level, institutional_inertia, legitimacy), housed_org_ids, territory_ids, jurisdiction, lifecycle_function.
- **InternalBalanceOfForces**: Factional weight distribution across three ruling-class fractions with a computed hegemonic fraction and internal contestation measure. Weights always sum to 1.0.
- **RulingClassFraction**: Three-value classification: Liberal-Technocratic (consent-based rule, slow escalation), Revanchist-Fascist (naked repression, fast escalation), Institutionalist-Bonapartist (self-preservation, institutional independence).
- **ApparatusType**: Althusserian classification of institutional function — RSA types (Executive, Military, Police, Judicial, Carceral), ISA types (Educational, Religious, Family, Legal, Political, Communications, Cultural), Economic types (Productive, Financial, Extractive).
- **SocialFunction**: The population need served by the institution (Employment, Education, Worship, Policing, Healthcare, Care, Adjudication, Communication, Legislation, Incarceration, Military Defense, Financial Intermediation).
- **ClassInscription**: More resistant to change than Organization.class_character. Three values: Bourgeois, Proletarian, Contested. Changes only through sustained class struggle on coefficient timescale.
- **InstitutionOrgRelation**: Relationship between institution and housed Organization, tracking resource provision, legal cover, legitimacy transfer, action oversight, and factional alignment of the Organization within the institution.
- **ReproductionMechanism**: The self-perpetuation capacity of an institution — what makes it an institution rather than an organization. Tracks recruitment pipeline, training program, succession protocol, budget independence, and legal self-perpetuation.
- **StructuralSelectivity**: Action cost modifiers that shape what Organizations can do within the institution. Maps action types to float multipliers (< 1.0 = cheaper/easier, > 1.0 = more expensive/harder).
- **LifecyclePhase**: Optional D-P-D' assignment. D = controls ideological transmission (schools, childcare), P = where surplus extraction occurs (workplaces, unions), D' = the legitimation bargain (elder care, pensions).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A DOJ institution can be instantiated as RSA_JUDICIAL housing an FBI StateApparatus Organization, and destroying the FBI degrades but does not destroy the DOJ.
- **SC-002**: Detroit Public Schools can be instantiated as ISA_EDUCATIONAL with lifecycle_function=D, and its structural selectivity makes EDUCATE cheaper and REPRESS more expensive for housed Organizations.
- **SC-003**: Ford Motor Company can be instantiated as ECONOMIC_PRODUCTIVE housing a Business Organization with appropriate action modifiers.
- **SC-004**: The Catholic Church can be instantiated as ISA_RELIGIOUS and queried for community embeddedness across community hyperedges.
- **SC-005**: An institution's internal_balance shifts when crisis_intensity changes — rising crisis increases REVANCHIST weight, falling legitimacy weakens LIBERAL weight, and high external threat activates BONAPARTIST weight.
- **SC-006**: Multiple conflicting Organizations (e.g., FBI Civil Rights Division aligned LIBERAL vs. FBI Counterintelligence aligned REVANCHIST) can be housed in the same institution with independent factional alignments.
- **SC-007**: A university's structural selectivity makes EDUCATE cheap (modifier < 1.0) and REPRESS expensive (modifier > 1.0), directly affecting housed Organization action costs.
- **SC-008**: An institution with full reproduction mechanisms (all True, high budget_independence) computes reproduction_capacity > 0.8, while one with no mechanisms computes < 0.2.
- **SC-009**: Hegemonic fraction modulates housed Organization OODA: LIBERAL hegemony produces ASSIMILATE preference, REVANCHIST produces REPRESS preference, BONAPARTIST produces self-preservation behavior.
- **SC-010**: All existing Organization tests continue to pass after the Institution layer is introduced — the new layer augments, does not break, existing functionality.

## Scope

### In Scope

- Institution base model with all fields described above
- ApparatusType, SocialFunction, ClassInscription, LifecyclePhase enums
- InternalBalanceOfForces with RulingClassFraction
- InstitutionOrgRelation model
- ReproductionMechanism model
- StructuralSelectivity (action modifiers)
- Graph integration: housed_orgs(), territory_footprint(), community_embeddedness()
- Hegemonic fraction effect on OODA profiles
- Deprecation of institution.schema.json and Organization.is_institution

### Out of Scope

- Institutional capture mechanics (Phase 2)
- Organization-to-Institution transition / formalization (Phase 3)
- Full intra-institutional factional dynamics system with inter-institutional conflict (Phase 4)
- Institutional destruction and replacement mechanics (Phase 5)
- Institution-bifurcation integration (Phase 6)

## Assumptions

- The existing Organization ABC (Features 030/031) and its four subtypes (StateApparatus, Business, PoliticalFaction, CivilSocietyOrg) are stable and available for integration.
- Community hyperedge infrastructure (Features 022/029) with CommunityConsciousness is implemented and available via XGI.
- The OODA loop system (Feature 032) provides the OODAModifier protocol for hegemonic fraction effects.
- GraphProtocol is the standard interface for entity storage and retrieval.
- Frozen Pydantic models (model_config = ConfigDict(frozen=True)) are the project standard for all data types.
- Faction weights are initialized from empirical calibration data, not magic constants.
- Alpha-smoothing rate for class inscription changes is on the order of 0.05 (coefficient-level, slow) — same timescale used in Feature 039 for faction balance updates.

## Dependencies

- **Requires**: Feature 030 (Organization Base Model), Feature 031 (Organization subtypes and class_character), Feature 032 (OODA Loop System)
- **Integrates with**: Features 022/029 (Community Hyperedge Layer, CommunityConsciousness), Feature 033 (Bifurcation Topology), GraphProtocol
- **Deprecates**: institution.schema.json, Organization.is_institution field
