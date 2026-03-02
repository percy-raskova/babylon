# Feature Specification: State Apparatus AI — Attention Threads, Enemy AI & Organization-Territory Integration

**Feature Branch**: `039-state-apparatus-ai`
**Created**: 2026-03-02
**Status**: Draft
**Depends On**: 022b-community-hyperedge-upgrade, 026-unified-class-system, 031-organization-base-model, 032-ooda-loop-system, 033-bifurcation-topology, 034-ternary-consciousness, 038-unified-class-system

---

## Executive Summary

This specification defines the state apparatus as a strategic adversary — not a unitary rational actor, but a factional coalition whose behavior shifts based on which faction dominates at any moment. It unifies three previously deferred subsystems (attention threads, NPC faction AI, organization-territory integration) with a state verb taxonomy, factional politics model, and state AI decision architecture into a single coherent feature.

The core design claim: the player's actions don't just provoke state *responses* — they shift *which version of the state* the player is fighting. The state is a coalition of Finance-Capital, Security-State, and Settler-Populist factions, each with distinct material bases and strategic preferences over a six-verb action space. The factional balance at any moment determines the state's objective function, its verb selection, and ultimately whether the system converges toward fascism or permits revolutionary opening.

This specification covers:

1. **Attention Thread System** (Sparrow-grounded intelligence allocation)
2. **State Verb Taxonomy** (six top-level verbs with ~24 sub-verbs)
3. **Factional Politics Model** (three-faction coalition with shifting balance)
4. **State AI Decision Architecture** (factional objective function, escalation logic)
5. **Organization-Territory Integration** (spatial dynamics, DEVELOP/WITHDRAW effects, consciousness geography)
6. **Extensions to existing specs** (031 org model, 032 OODA, 033 bifurcation)

---

## Clarifications

### Session 2026-03-02

- Q: How many actions does the state execute per tick? → A: One action per tick, but designed for easy extensibility to multi-action mechanics later (e.g., budget-constrained variable count or per-verb-category parallelism)
- Q: What can the player observe about state internals (faction balance, budget, threads)? → A: Indirect signals only (verb frequency shifts, narrative tone, public budget patterns), with player actions (COUNTER_INTEL, state apparatus infiltration) that can reveal internals. A "God Mode" debug toggle exposes all state internals (faction weights, budget, thread allocation) for testing and development.
- Q: How large is the attention thread pool and how does it scale? → A: Thread pool size is derived from apparatus capacity — each StateApparatus contributes threads based on its surveillance_capacity attribute. FUND and STAFF can grow the pool. Detroit 2010 baseline: ~5-8 total threads across all apparatus.
- Q: Should "measurably" in success criteria define minimum effect sizes? → A: Yes. Minimum effect sizes defined as tunable GameDefines parameters. Starting default floor: at least 0.02 faction weight shift per triggering event. Statistical validation: detectable by 2-sided t-test at p<0.05 over 100 seeded runs.
- Q: What is the lifecycle of LegalFramework entities created by LEGISLATE? → A: All legislation (including EMERGENCY_POWERS) persists until explicitly revoked by a LEGISLATE(REVOKE) action. No automatic expiry. Revocation carries its own legitimacy cost/gain depending on context.

---

## User Scenarios & Testing

### User Story 1 — State Responds to Player Organizing with Faction-Weighted Verbs (Priority: P1)

As a player building a revolutionary organization in Detroit, I want the state to respond to my actions through a legible escalation sequence (ideological warfare first, then surveillance, then repression) so that I can read the state's behavior and make strategic decisions about visibility, timing, and counter-measures.

**Why this priority**: Without a functioning state AI that selects from the verb taxonomy based on factional balance, there is no adversary. This is the minimum viable enemy.

**Independent Test**: Can be fully tested by running a 52-tick simulation where the player generates increasing Heat, and verifying that the state's verb selections shift from CO-OPT (PROPAGANDIZE, BRIBE) through REPRESS (SURVEIL, RAID) in a legible sequence. Delivers the core adversarial gameplay loop.

**Acceptance Scenarios**:

1. **Given** a world state with default Detroit 2010 faction balance (FC=0.45, SS=0.30, SP=0.25) and low player Heat, **When** the state AI selects actions for one tick, **Then** it prefers low-cost verbs (PROPAGANDIZE, SURVEIL) over high-cost verbs (RAID, LIQUIDATE)
2. **Given** a world state where the player has generated sustained Heat (>0.6) over 8 ticks, **When** the state AI selects actions, **Then** the security-state faction weight has increased and REPRESS sub-verbs appear more frequently than CO-OPT sub-verbs
3. **Given** a world state where the security-state faction weight exceeds 0.4, **When** the state AI allocates budget, **Then** REPRESS and ADMINISTER receive more budget share than DEVELOP or CO-OPT
4. **Given** a world state where the state budget is exhausted, **When** the state AI selects actions, **Then** it shifts to zero-cost or low-cost options (NEGLECT over INVEST, PROPAGANDIZE over BRIBE, SURVEIL over RAID)

______________________________________________________________________

### User Story 2 — Attention Threads Track and Analyze Player Organization (Priority: P2)

As a player running a clandestine organization, I want the state's intelligence apparatus to gradually discover my organization's topology through attention threads — accumulating partial intelligence over time, making mistakes based on the observation gap, and escalating analysis when my community's collective_identity rises — so that organizational security decisions (cell structure, counter-intel, operational profile) have meaningful gameplay consequences.

**Why this priority**: Attention threads are the mechanism by which the state "sees" the player. Without them, state actions have no intelligence basis and cannot target meaningfully.

**Independent Test**: Can be fully tested by creating an FBI attention thread targeting a player organization, advancing 12 ticks, and verifying that intel_completeness grows, observed_subgraph expands, Sparrow analysis identifies singletons (if any exist), and the observation gap produces distortions. Delivers intelligence-driven targeting as gameplay.

**Acceptance Scenarios**:

1. **Given** an FBI attention thread targeting a star-topology organization, **When** 8 ticks elapse with SIGNALS surveillance, **Then** intel_completeness has increased from 0.0 and the hub node has been identified as a singleton in equivalence class analysis
2. **Given** an FBI attention thread targeting a cell-topology organization, **When** 8 ticks elapse with SIGNALS surveillance, **Then** intel_completeness is lower than for the equivalent star topology (compartmentalization limits observation ceiling)
3. **Given** rising collective_identity (>0.5) in a community where the player operates, **When** the state performs meta-OODA thread allocation, **Then** more threads are allocated to organizations within that community than to organizations in low-CI communities
4. **Given** an attention thread with intel_completeness > 0.6, **When** the state performs Sparrow analysis, **Then** it identifies centrality rankings, equivalence classes, and potential cutsets on G_observed (which may differ from G_actual)

______________________________________________________________________

### User Story 3 — Factional Balance Shifts Based on Player Actions and Material Conditions (Priority: P3)

As a player, I want to see that my strategic choices (generating Heat, disrupting extraction, building legitimacy, accepting or rejecting co-optation offers) measurably shift which faction dominates the state apparatus — so that the game presents genuine strategic dilemmas rather than a fixed escalation script.

**Why this priority**: Factional dynamics are what make the state strategically interesting rather than a simple difficulty ratchet. This transforms the state from "enemy that gets harder" to "enemy that changes character."

**Independent Test**: Can be fully tested by running two parallel 26-tick simulations with identical starting conditions but different player strategies (one generating high Heat, one building legitimacy quietly), and verifying that the resulting faction balances diverge measurably. Delivers strategic depth.

**Acceptance Scenarios**:

1. **Given** a player generating sustained Heat through visible organizing, **When** 12 ticks elapse, **Then** security-state faction weight has increased relative to starting conditions
2. **Given** a player building legitimacy through mutual aid without generating Heat, **When** 12 ticks elapse, **Then** finance-capital faction weight has increased (CO-OPT pressure) while security-state weight has NOT increased
3. **Given** a player that successfully survives state repression (org persists after RAID), **When** the next faction balance update occurs, **Then** security-state credibility decreases (their methods failed)
4. **Given** conditions matching the fascist convergence threshold (SS>0.4, settler CI>0.6, FC<0.25), **When** the state AI selects actions, **Then** behavior shifts qualitatively: CO-OPT budget redirects to REPRESS, DEVELOP becomes displacement-oriented, LEGISLATE shifts toward EMERGENCY_POWERS

______________________________________________________________________

### User Story 4 — DEVELOP and WITHDRAW Reshape Territory (Priority: P4)

As a player organizing in a specific neighborhood, I want state DEVELOP actions (INVEST, REZONE, DISPLACE, NEGLECT) to change the material conditions of the territory I operate in — raising costs, displacing residents, severing community infrastructure — so that "the ground shifting beneath me" is a strategic challenge distinct from direct repression.

**Why this priority**: DEVELOP is the asymmetric verb the player cannot mirror. It creates strategic dilemmas (do I fight displacement or relocate?) that are qualitatively different from the REPRESS response.

**Independent Test**: Can be fully tested by applying INVEST to a territory over 8 ticks and verifying that property value proxy rises, V_reproduction increases for existing residents, and class composition begins to shift. Delivers the gentrification-as-weapon mechanic.

**Acceptance Scenarios**:

1. **Given** a territory with stable economic indicators, **When** the state applies INVEST (COMMERCIAL) for 8 ticks, **Then** property value proxy rises and V_reproduction increases for existing residents
2. **Given** a territory with rising property values from prior INVEST, **When** the state applies DISPLACE (RENT_INCREASE), **Then** population is removed from territory, TENANCY edges are severed, and community infrastructure degrades
3. **Given** a territory where the state performs STRATEGIC_WITHDRAWAL with asset_extraction=True, **When** the withdrawal completes, **Then** state apparatus PRESENCE edges are removed, infrastructure quality degrades, and V_reproduction rises for remaining population
4. **Given** a territory where the state performs NEGLECT over 12 ticks, **When** territory indicators are measured, **Then** infrastructure quality has degraded, property values have declined, and services have reduced

______________________________________________________________________

### User Story 5 — Organization-Territory Spatial Dynamics (Priority: P5)

As a player, I want organizations to occupy specific territories through PRESENCE edges, generating Heat based on operational profile, with recruitment requiring territorial presence and community infrastructure bound to specific locations — so that spatial strategy matters and displacement has concrete organizational consequences.

**Why this priority**: Without spatial grounding, organizations float in abstract space. Territory integration makes displacement meaningful, consciousness geography possible, and heat mechanics functional.

**Independent Test**: Can be fully tested by placing two organizations in the same territory with different operational profiles (HIGH_PROFILE vs LOW_PROFILE), advancing 8 ticks, and verifying differential heat accumulation and recruitment eligibility. Delivers spatial strategy.

**Acceptance Scenarios**:

1. **Given** an organization with HIGH_PROFILE presence in a territory, **When** 4 ticks elapse, **Then** heat in that territory has increased faster than for a LOW_PROFILE organization
2. **Given** an organization with NO presence in a territory, **When** it attempts RECRUIT targeting population in that territory, **Then** the action fails or has severely reduced effectiveness
3. **Given** a community with collective_identity=0.7 concentrated in Territory A and collective_identity=0.2 in Territory B, **When** the state measures consciousness by territory, **Then** Territory A shows higher threat priority than Territory B
4. **Given** a territory where an eviction cascade displaces organized residents, **When** the displacement resolves, **Then** local collective_identity decreases as the organized community is scattered and community infrastructure in that territory degrades

______________________________________________________________________

### User Story 6 — State CO-OPT Actions Target Consciousness and Leadership (Priority: P6)

As a player building revolutionary consciousness, I want the state to deploy CO-OPT verbs (PROPAGANDIZE, BRIBE, INCORPORATE, DIVIDE) that attack the ideological terrain — lowering collective_identity, absorbing leaders, manufacturing antagonism between allied organizations — so that the ideological struggle has a material adversary, not just inertia.

**Why this priority**: CO-OPT is the state's preferred first-line defense. Without it, the state only has repression, which is less realistic and less strategically interesting.

**Independent Test**: Can be fully tested by applying PROPAGANDIZE (WE_ARE_ALL_AMERICANS) to a community for 8 ticks and verifying that collective_identity decreases measurably. Delivers ideological warfare as gameplay.

**Acceptance Scenarios**:

1. **Given** a community with collective_identity=0.5, **When** the state applies PROPAGANDIZE (WE_ARE_ALL_AMERICANS, intensity=0.8) for 4 ticks, **Then** collective_identity has decreased
2. **Given** a high-CL KeyFigure in a player organization with moderate org Coherence, **When** the state applies INCORPORATE (NONPROFIT_STATUS, resources=high), **Then** there is a nonzero acceptance probability and if accepted, the KeyFigure is removed from the player organization
3. **Given** a SOLIDARISTIC edge between two player-aligned organizations, **When** the state applies DIVIDE (IDENTITY_WEDGE) for 4 ticks, **Then** the edge degrades toward TRANSACTIONAL
4. **Given** a SocialClass block targeted by BRIBE (WAGE_CONCESSION), **When** the bribe is applied, **Then** material position increases and a TRANSACTIONAL edge is created between the state and target

______________________________________________________________________

### Edge Cases

- What happens when the state budget reaches zero mid-tick? (State must shift to zero-cost actions for remaining sub-verbs; budget constraint is checked per action, not per tick)
- What happens when all attention threads are allocated and a new high-priority target emerges? (Meta-OODA must deallocate lowest-priority thread; stickiness parameter resists rapid reallocation)
- What happens when a territory has no remaining population after DISPLACE? (Territory enters ABANDONED state; no further DEVELOP actions possible; available for SCORCHED_EARTH or recolonization)
- What happens when fascist convergence threshold is reached and then conditions revert? (Fascism is a near-absorbing state — reversion requires external intervention or catastrophic state failure, modeled as very high reversion resistance)
- What happens when the player infiltrates a state apparatus? (Counter-action to AUDIT: player INFILTRATE into StateApparatus degrades its OODA, reveals attention thread targets, provides early warning of REPRESS actions)
- What happens when LEGISLATE (EMERGENCY_POWERS) is revoked? (LEGISLATE(REVOKE) removes the LegalFramework entity; capabilities granted by emergency powers are revoked; thread capacity returns to baseline; LIQUIDATE becomes unavailable in core territories again. Revocation carries legitimacy implications — revoking may restore legitimacy but signals weakness)

---

## Requirements

### Functional Requirements

#### Subsystem A: Attention Thread System

- **FR-A01**: System MUST model state intelligence as a finite set of attention threads, each tracking a specific target (organization, territory, or community) with accumulated intelligence that grows over time. Thread pool size MUST be derived from the sum of surveillance_capacity across all StateApparatus nodes; FUND and STAFF actions that increase surveillance_capacity grow the pool. Detroit 2010 baseline: ~5-8 total threads
- **FR-A02**: System MUST implement the observation gap — state analysis operates on G_observed (always incomplete, always distorted) not G_actual, with distortions including edge type conflation, temporal flattening, informant incentive distortion, cash invisibility, and face-to-face blindness
- **FR-A03**: System MUST implement Sparrow's network analysis algorithms on G_observed: centrality computation (degree, betweenness, closeness, eigenvector), equivalence class computation via numerical signatures, singleton identification, and minimal cutset detection
- **FR-A04**: System MUST implement meta-OODA for thread allocation — deciding which targets get threads based on heat level, collective_identity of communities the target operates in, organization size, and recent player actions
- **FR-A05**: System MUST implement thread-level OODA — each thread progresses through OBSERVE (expand observed_subgraph), ORIENT (Sparrow analysis), DECIDE (choose targeting strategy), ACT (execute)
- **FR-A06**: System MUST model five surveillance methods (SIGNALS, FINANCIAL, SOCIAL_MEDIA, INFORMANT, PHYSICAL) with different intelligence yields: SIGNALS reveals communication patterns, FINANCIAL reveals resource flows, SOCIAL_MEDIA reveals public-facing topology, INFORMANT reveals internal state with distortion, PHYSICAL reveals face-to-face meetings
- **FR-A07**: System MUST enforce observation ceiling per apparatus — FBI ceiling ~0.4, local PD ~0.2, fusion center ~0.5 — with cell topology reducing effective ceiling further
- **FR-A08**: System MUST model thread phases (DORMANT, MONITORING, ACTIVE_INVESTIGATION, DISRUPTION) with escalation driven by intelligence accumulation and threat assessment

#### Subsystem B: State Verb Taxonomy

- **FR-B01**: System MUST implement six top-level state verbs: ADMINISTER, DEVELOP, RESEARCH, CO_OPT, REPRESS, WITHDRAW
- **FR-B02**: System MUST implement ADMINISTER sub-verbs: FUND (allocate budget to apparatus), STAFF (hire/train personnel), LEGISLATE (create legal frameworks), AUDIT (internal review)
- **FR-B03**: System MUST implement DEVELOP sub-verbs: INVEST (capital investment in territory), REZONE (change land use), DISPLACE (active population removal), NEGLECT (deliberate disinvestment)
- **FR-B04**: System MUST implement RESEARCH sub-verbs: PURSUE_TECH (advance technology tree), DEPLOY_TECH (activate technology in apparatus or territory)
- **FR-B05**: System MUST implement CO_OPT sub-verbs: BRIBE (material transfer for compliance), PROPAGANDIZE (narrative control), INCORPORATE (absorb opposition leadership), DIVIDE (manufacture antagonistic edges)
- **FR-B06**: System MUST implement REPRESS sub-verbs: SURVEIL (passive intelligence), INFILTRATE (insert corrupted node), RAID (kinetic action), PROSECUTE (legal warfare), LIQUIDATE (assassination/disappearance)
- **FR-B07**: System MUST implement WITHDRAW sub-verbs: STRATEGIC_WITHDRAWAL (concede territory with hollowing), TACTICAL_RETREAT (temporary repositioning), SCORCHED_EARTH (active destruction)
- **FR-B08**: System MUST enforce asymmetry — the player cannot execute any state verb; the state cannot execute player-specific verbs (Political Education generating CL, Mutual Aid creating SOLIDARITY edges from scratch)
- **FR-B09**: System MUST implement LEGISLATE effects that modify game rules: SURVEILLANCE_AUTH increases observation ceiling, ANTI_PROTEST raises Heat generation for PROTEST actions, EMERGENCY_POWERS doubles thread capacity at severe legitimacy cost, ZONING enables DEVELOP in target territory. All legislation persists until explicitly revoked via LEGISLATE(REVOKE); there is no automatic expiry. System MUST implement REVOKE as a LEGISLATE sub-action that removes an active LegalFramework entity
- **FR-B10**: System MUST implement LIQUIDATE availability constraints: requires EMERGENCY_POWERS OR low international visibility territory OR prior terrorist designation; in core territories with high media presence, LIQUIDATE carries extreme legitimacy cost
- **FR-B11**: System MUST implement NEGOTIATE as a resolution mechanic within WITHDRAW and CO_OPT — not a standalone verb but a negotiation phase when the state has decided to concede or bribe

#### Subsystem C: Factional Politics Model

- **FR-C01**: System MUST model three state factions: Finance-Capital (material base in extraction efficiency), Security-State (material base in repressive apparatus), Settler-Populist (material base in imperial rent distribution to settler nation)
- **FR-C02**: System MUST represent faction balance as a weight vector summing to 1.0, with computed dominant faction (highest weight) and stability metric
- **FR-C03**: System MUST implement faction verb preferences — each faction has a preference weighting over the six verbs (e.g., Security-State: REPRESS=0.35, ADMINISTER=0.25; Finance-Capital: DEVELOP=0.30, CO_OPT=0.25)
- **FR-C04**: System MUST shift faction balance based on player actions: generating Heat increases Security-State weight; disrupting extraction increases Finance-Capital panic; building legitimacy increases CO_OPT pressure from Finance-Capital; surviving repression decreases Security-State credibility
- **FR-C05**: System MUST shift faction balance based on material conditions: profit rate decline increases Finance-Capital influence; imperial rent contraction increases Settler-Populist panic; legitimacy crisis increases Security-State weight
- **FR-C06**: System MUST implement fascist convergence detection: when Security-State weight > 0.4 AND settler collective_identity > 0.6 with ASSIMILATIONIST_FASCIST tendency AND Finance-Capital weight < 0.25, the state transitions to fascist mode
- **FR-C07**: System MUST model fascist mode as a near-absorbing state: CO_OPT budget redirects to REPRESS, DEVELOP becomes displacement-oriented, WITHDRAW becomes scorched earth in contested territories, LEGISLATE shifts to EMERGENCY_POWERS
- **FR-C08**: System MUST assign factional alignment to each StateApparatus (e.g., FBI=Security-State, Commerce Department=Finance-Capital, Border Patrol=Settler-Populist) as an organizational attribute, not an AI decision

#### Subsystem D: State AI Decision Architecture

- **FR-D01**: System MUST implement a factional objective function where the state AI maximizes a weighted sum of faction-specific objectives, with weights determined by current FactionBalance
- **FR-D02**: Finance-Capital objective MUST maximize: extraction efficiency, profit rate, stability; minimize: market disruption, uncertainty
- **FR-D03**: Security-State objective MUST maximize: threat suppression, apparatus size, surveillance coverage; minimize: percolation ratio, maximum collective_identity
- **FR-D04**: Settler-Populist objective MUST maximize: settler property values, cultural homogeneity, imperial rent to base; minimize: cross-line solidarity, demographic change in settler territories
- **FR-D05**: System MUST implement the state OODA decision flow per tick: OBSERVE (read world state within intelligence limits), ORIENT (apply factional lens), DECIDE (score candidate actions against factional objective), ACT (execute exactly one action in Layer 1). The action-per-tick count MUST be a configurable parameter (default: 1) to allow future expansion to multi-action mechanics without architectural changes
- **FR-D06**: System MUST implement escalation logic — state prefers cheap, low-visibility actions and escalates only when cheaper options fail: PROPAGANDIZE before BRIBE before SURVEIL before RAID before PROSECUTE before LIQUIDATE
- **FR-D07**: System MUST implement de-escalation logic — when player pressure subsides, state prefers cheaper verbs; when CO-OPT succeeds, state de-escalates; budget pressure forces cheaper options
- **FR-D08**: System MUST be deterministic given world state and RNG seed; no external AI service for state decisions in stub implementation
- **FR-D09**: System MUST implement the NPCDecisionStrategy protocol (hot-swappable) allowing future replacement of rule-based AI with LLM-backed decision function
- **FR-D10**: System MUST implement per-org-type AI: StateApparatus (verb taxonomy), Business (employ/lobby), CivilSocietyOrg (varies by consciousness_tendency), PoliticalFaction (varies by consciousness_strategy)
- **FR-D11**: System MUST surface state behavior to the player only through indirect signals: observable verb selections, media narrative shifts, public budget records, and territory-level effects. Player actions (COUNTER_INTEL, infiltrating state apparatus) MUST be able to reveal deeper internals (faction weights, thread targets) proportional to intelligence success
- **FR-D12**: System MUST implement a God Mode debug toggle that, when enabled, exposes all state internals to the player (faction weights, budget allocation, attention thread targets and intel_completeness, AI decision scoring) for testing and development purposes

#### Subsystem E: Organization-Territory Integration

- **FR-E01**: System MUST model organizational territorial presence through PRESENCE edges with operational profile (HIGH_PROFILE or LOW_PROFILE)
- **FR-E02**: System MUST implement heat mechanics: HIGH_PROFILE presence increases heat; thread allocation increases heat; heat decays without activity; heat threshold triggers state response
- **FR-E03**: System MUST bind community infrastructure to specific territories — gathering spaces, mutual aid, healthcare exist in SPECIFIC territories and displacement severs members from infrastructure
- **FR-E04**: System MUST implement consciousness geography — collective_identity varies spatially; EDUCATE actions produce local consciousness shifts before community-wide effects
- **FR-E05**: System MUST implement D-P-D' infrastructure as territory-bound: schools (D-phase ideological transmission), workplaces (P-phase), elder care (D'-phase); organization controlling a school shapes YOUTH consciousness via its consciousness_strategy
- **FR-E06**: System MUST implement eviction as consciousness disruption — displacement scatters organized communities, lowers local collective_identity, severs community infrastructure, and shifts territory demographic composition
- **FR-E07**: System MUST require territorial PRESENCE for recruitment — organizations cannot RECRUIT in territories where they have no presence
- **FR-E08**: System MUST implement DEVELOP verb effects on territory: INVEST changes economic indicators, REZONE enables new development, DISPLACE removes population and severs edges, NEGLECT degrades infrastructure over time
- **FR-E09**: System MUST implement WITHDRAW verb effects on territory: STRATEGIC_WITHDRAWAL hollows territory (removes state apparatus, extracts assets), TACTICAL_RETREAT temporarily reduces state attention, SCORCHED_EARTH destroys infrastructure

#### Subsystem F: Extensions to Existing Specs

- **FR-F01**: System MUST extend 031 (Organization Base Model) with: StateFaction enum, FactionBalance model, factional_alignment field on StateApparatus, StateBudget model
- **FR-F02**: System MUST extend 032 (OODA Loop System) with: StateActionType enum (six top-level verbs and all sub-verbs), state action resolution in Layer 1, faction balance shift as Layer 3 consequence, budget consumption per state action, StateAction model parallel to Action
- **FR-F03**: System MUST extend 033 (Bifurcation Topology) with: fascist convergence detection function, faction balance as input to bifurcation analysis

### Key Entities

- **AttentionThread**: A state intelligence resource tracking a specific target. Key attributes: target (org/territory/community), phase, intensity, observed_subgraph, intel_completeness, Sparrow analysis results, OODA state, stickiness, ticks_active
- **StateFaction**: Enumeration of ruling-class factions (FINANCE_CAPITAL, SECURITY_STATE, SETTLER_POPULIST) with distinct material bases and verb preferences
- **FactionBalance**: Weight vector over factions summing to 1.0, with stability and legitimacy metrics. Shifts based on player actions and material conditions
- **StateAction**: A state verb execution instance. Key attributes: verb, sub-verb, target, budget cost, thread cost, legitimacy cost, faction alignment. Parallel to player Action but with different resource profile
- **StateBudget**: Tracks state revenue (tax + federal transfers + imperial rent pool), allocation across verb categories, and factional claims on budget. Finite — the binding constraint on state omnipotence
- **ObservationModel**: What intelligence sources a StateApparatus has access to (phone metadata, financial records, social media, location data, informant reports, public records). Determines observation ceiling
- **SparrowAnalysis**: Results of network analysis on G_observed — centrality rankings, equivalence classes, identified singletons, known cutsets. Always partial, always potentially wrong
- **TerritoryPresence**: An organization's footprint in a territory — operational profile (HIGH_PROFILE/LOW_PROFILE), infrastructure controlled, community infrastructure bound to location
- **LegalFramework**: Active legislation affecting game rules in a jurisdiction — surveillance authorizations, anti-protest laws, emergency powers, zoning changes. Created by LEGISLATE, consumed by other verbs

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: All six top-level state verbs and all sub-verbs are executable by the state AI in a 52-tick test run; no verb category goes unused for 52 consecutive ticks
- **SC-002**: Changing FactionBalance weights produces different state verb selections over a 52-tick run (detectable at p<0.05 over 100 seeded runs) — Security-State dominance increases REPRESS frequency by at least 2x compared to Finance-Capital dominance
- **SC-003**: Given rising player Heat and collective_identity, the state AI escalates from PROPAGANDIZE through SURVEIL through RAID in a legible, observable sequence within 20 ticks; given declining Heat, de-escalation occurs within 8 ticks
- **SC-004**: When fascist convergence conditions are met, the state AI transitions to qualitatively different behavior within 4 ticks — REPRESS budget share exceeds 50%, DEVELOP shifts to displacement-oriented sub-verbs
- **SC-005**: The state AI respects budget limits — when budget reaches zero, all remaining actions in that tick are zero-cost or deferred; no budget violations occur across 52 ticks
- **SC-006**: Attention thread intel_completeness grows monotonically per thread (absent counter-intel); after 12 ticks, a MONITORING thread on a star-topology org identifies the hub as a singleton with probability > 0.8
- **SC-007**: Cell topology organizations have intel_completeness at least 30% lower than equivalent star topology organizations after 12 ticks of surveillance, validating compartmentalization as a defensive mechanic
- **SC-008**: INVEST in a territory measurably changes economic indicators within 8 ticks; NEGLECT measurably degrades territory within 12 ticks; DISPLACE removes at least 50% of target population from territory
- **SC-009**: PROPAGANDIZE (WE_ARE_ALL_AMERICANS) decreases collective_identity in target community by at least the minimum effect floor (default: 0.02 per application, tunable via GameDefines) within 4 ticks; INCORPORATE removes targeted KeyFigure with probability inversely proportional to org Coherence and community collective_identity
- **SC-010**: Player-generated Heat increases Security-State faction weight by at least the minimum effect floor (default: 0.02 per event, tunable via GameDefines) within 4 ticks; player disruption of extraction shifts Finance-Capital response by at least the minimum effect floor within 8 ticks; player legitimacy wins increase Settler-Populist reaction by at least the minimum effect floor within 8 ticks. All effects detectable by 2-sided t-test at p<0.05 over 100 seeded runs

---

## Theoretical Foundation

### State-Player Asymmetry

The player's verb taxonomy (BUILD, MOBILIZE, STRIKE) reflects the strategic position of an insurgent force: building capacity from nothing. The state occupies the inverse position: it already controls the material base, the legal framework, the ideological apparatus, and the means of violence. Its strategic problem is *maintenance*, not construction.

| State Verb | Target Layer | Strategic Mode | Player Equivalent |
|-----------|-------------|----------------|-------------------|
| ADMINISTER | State apparatus (self) | Internal capacity reproduction | BUILD |
| DEVELOP | Territory / material base | Reshape the ground | *None* (asymmetric) |
| RESEARCH | Technology / capability space | Expand action space | *None* (asymmetric) |
| CO_OPT | Civil society / opposition | Absorb or neutralize | MOBILIZE (inverse) |
| REPRESS | Organizations / topology | Destroy or degrade | STRIKE (inverse) |
| WITHDRAW | Territory / commitment | Concede or reposition | *None* (asymmetric) |

Three verbs (ADMINISTER, CO_OPT, REPRESS) are rough mirrors of the player's three categories. Three verbs (DEVELOP, RESEARCH, WITHDRAW) are asymmetric — the player has no equivalent because these require state-level control over the material base, the legal framework, or sovereign territory.

### The State as Factional Coalition

The state's objective function is not fixed. It is the *resultant* of competing factional interests within the ruling class:

- **Finance-Capital**: Prefers stability. Favors CO_OPT and DEVELOP. Tolerates organizing unless it threatens accumulation. Cannot tolerate profit rate decline.
- **Security-State**: Budget and power grow with threat levels. Favors REPRESS and ADMINISTER. Institutional incentive to maintain threat perception. Repression generates conditions for its own escalation.
- **Settler-Populist**: Material base in imperial rent distribution. Favors DEVELOP (displacement), CO_OPT (bribe the base), WITHDRAW (abandon "undesirable" zones). Provides mass base for fascism when imperial rent contracts.

### Fascism as Factional Convergence

Fascism is what happens when: (1) Security-State achieves internal dominance, (2) Settler-Populist provides mass base via lateral antagonism, (3) Finance-Capital acquiesces because co-optation has failed. The player can read this convergence in shifting verb preferences.

### Sparrow's Network Vulnerability Framework

Malcolm K. Sparrow (1991, 1993) formalized how law enforcement operationalizes graph theory. The state operates on G_observed (always incomplete, always distorted). The observation gap (G_observed != G_actual) is the core strategic game mechanic. The state sees metadata; misses face-to-face, cash, consciousness, commitment.

### Consciousness as Threat Trigger

Rising collective_identity within a community is the signal that triggers state escalation. The state monitors consciousness and escalates when assimilation is failing. This creates the dialectic: revolutionary education leads to state escalation, which either crushes or radicalizes, depending on the ideological terrain at the moment of impact.

---

## State Verb Taxonomy (Detailed)

### ADMINISTER — Internal Capacity Management

**FUND**: Allocate budget to a specific apparatus. Increases capacity attributes (violence_capacity, surveillance_capacity, service_capacity). Budget cost: direct. Faction-dependent targeting.

**STAFF**: Hire and train personnel. Draws from ADULT population. Creates KeyFigure nodes within apparatus. Expands OODA capacity. Cost: budget + training time + labor pool draw.

**LEGISLATE**: Create legal frameworks. Modifies game rules within jurisdiction scope. Legitimacy cost proportional to severity. Sub-actions: SURVEILLANCE_AUTH, ANTI_PROTEST, EMERGENCY_POWERS, ZONING, TAX_INCENTIVE, LABOR_REGULATION, REVOKE. All legislation persists until explicitly revoked via LEGISLATE(REVOKE); revocation carries its own legitimacy cost/gain.

**AUDIT**: Internal apparatus review. Detects inefficiency, corruption, infiltration. Three depths: ROUTINE (1 tick, gross issues), THOROUGH (4 ticks, moderate infiltration), DEEP (12 ticks, sophisticated infiltration, temporarily reduces operational capacity).

### DEVELOP — Reshape the Material Base

**INVEST**: Capital investment in territory. Raises property values, changes economic character, increases V_reproduction. Precondition for displacement cascade.

**REZONE**: Change legal land use categories. Requires prior LEGISLATE (ZONING). Enables new investment types. Begins displacement countdown if displacement_expected.

**DISPLACE**: Active population removal. Mechanisms: EMINENT_DOMAIN, CODE_ENFORCEMENT, RENT_INCREASE, DEMOLITION, TAX_FORECLOSURE. Severs TENANCY edges, destroys community infrastructure. Generates Heat and consciousness agitation.

**NEGLECT**: Deliberate disinvestment. Low visibility, cumulative devastating effects. Creates conditions for future DISPLACE or INVEST cycle (the gentrification circuit).

### RESEARCH — Expand Capability Space

**PURSUE_TECH**: Advance technology tree. Classification: PUBLIC (visible), CLASSIFIED (restricted), BLACK (invisible without infiltration). Player appropriation mechanic: technology becomes available to player via seizure/replication, not research.

**DEPLOY_TECH**: Activate researched technology. Applies effects from technology tree. Ongoing operational costs (compute, personnel, maintenance).

### CO_OPT — Absorb, Neutralize, Divide

**BRIBE**: Material transfer for compliance. Types: GRANT, TAX_BREAK, CONTRACT, WAGE_CONCESSION, PATRONAGE. Creates TRANSACTIONAL edges. Shifts consciousness toward ASSIMILATIONIST_LIBERAL.

**PROPAGANDIZE**: Narrative control. Narratives: WE_ARE_ALL_AMERICANS (attacks collective_identity), THREAT_NARRATIVE (raises settler CI), REFORM_IS_WORKING (reinforces liberal tendency), DELEGITIMIZE_OPPOSITION (reduces org REP).

**INCORPORATE**: Absorb opposition leadership. Offers: ELECTORAL_CANDIDACY, NONPROFIT_STATUS, ADVISORY_POSITION, ACADEMIC_APPOINTMENT, MEDIA_PLATFORM. Acceptance probability inversely proportional to collective_identity and org Coherence.

**DIVIDE**: Manufacture antagonistic edges between opposition groups. Methods: RUMOR, SELECTIVE_LEAK, PROVOCATEUR, FUND_RIVAL, IDENTITY_WEDGE. Targets edges, not nodes. Requires prior SURVEIL intelligence.

### REPRESS — Direct State Violence

**SURVEIL**: Passive intelligence gathering via attention thread. Low cost, thread-consuming. Foundation for all other REPRESS and for DIVIDE.

**INFILTRATE**: Insert corrupted node. Agent types: INFORMANT (passive reporting), PROVOCATEUR (active degradation), MOLE (leadership infiltration). Success modified by target topology, Coherence, community infiltration_resistance, observation ceiling.

**RAID**: Kinetic action. Scales: TARGETED (specific KeyFigures), SWEEP (territory-wide), MASS (crackdown). Force levels: POLICE, SWAT, MILITARY. Legal basis affects legitimacy cost.

**PROSECUTE**: Legal warfare. Charges: CONSPIRACY, RACKETEERING, TAX, CIVIL_RIGHTS_VIOLATION, TERRORISM. Drains resources, ties up leadership, chilling effect on nearby organizations.

**LIQUIDATE**: Assassination, disappearance, rendition. Methods: ASSASSINATION, DISAPPEARANCE, RENDITION, PRISON_KILLING. Availability constrained by EMERGENCY_POWERS or territory visibility. Colonial asymmetry: nearly free in peripheral territories, extremely costly in core.

### WITHDRAW — Concede, Reposition, Scorch

**STRATEGIC_WITHDRAWAL**: Concede territory. Hollows first — defunds, extracts assets, lets infrastructure decay. Player inherits a husk.

**TACTICAL_RETREAT**: Temporary repositioning. Threads redirected elsewhere. Window of opportunity for player — but may be a honeypot.

**SCORCHED_EARTH**: Active destruction. Infrastructure destroyed. Population action: IGNORE, EVACUATE, BLOCKADE. Massive legitimacy cost in core territories, nearly free in peripheral.

---

## Factional Dynamics (Detailed)

### Faction Verb Preferences (Starting Weights)

| Verb | Finance-Capital | Security-State | Settler-Populist |
|------|----------------|---------------|-----------------|
| ADMINISTER | 0.15 | 0.25 | 0.10 |
| DEVELOP | 0.30 | 0.05 | 0.25 |
| RESEARCH | 0.15 | 0.20 | 0.05 |
| CO_OPT | 0.25 | 0.10 | 0.20 |
| REPRESS | 0.05 | 0.35 | 0.20 |
| WITHDRAW | 0.10 | 0.05 | 0.20 |

### Player Actions That Shift Faction Balance

| Player Action | Faction Effect |
|---------------|---------------|
| Generate Heat (visible organizing) | +Security-State weight |
| Disrupt extraction (strike, sabotage) | +Security-State initially, +Finance-Capital panic if sustained |
| Build legitimacy (mutual aid, services) | +CO_OPT pressure from Finance-Capital |
| Win narrative victories | +Settler-Populist reaction |
| Survive repression | -Security-State credibility |
| Accept CO-OPT offers | +Finance-Capital ("system works") |
| Reject CO-OPT offers | +Security-State ("force is necessary") |

### Material Conditions That Shift Faction Balance

| Condition | Faction Effect |
|-----------|---------------|
| Profit rate decline | +Finance-Capital influence |
| Imperial rent contraction | +Settler-Populist panic |
| Legitimacy crisis | +Security-State (force as substitute) |
| Successful CO-OPT | +Finance-Capital |
| Failed repression | -Security-State, +Finance-Capital |

### Detroit 2010 Initialization

- FINANCE_CAPITAL: 0.45 (post-crisis, asserting control over recovery)
- SECURITY_STATE: 0.30 (heightened post-9/11, budget-constrained)
- SETTLER_POPULIST: 0.25 (Tea Party rising, not yet dominant)

SYNTHETIC defaults derived from political analysis. Validate by: does simulated state behavior 2010-2015 qualitatively match actual Detroit policy (emergency management, austerity, selective reinvestment)?

---

## State AI Decision Flow

### Per-Tick Decision Architecture

```
1. OBSERVE: Read world state within intelligence limits
   - AttentionThread reports (incomplete, distorted)
   - Economic indicators (profit rate, imperial rent pool, budget)
   - Community consciousness levels (inferred from public actions)
   - Player-generated Heat across territories

2. ORIENT: Apply factional lens
   - Current FactionBalance determines threat prioritization
   - Finance-Capital: extraction threats
   - Security-State: organizational threats
   - Settler-Populist: cultural/demographic threats

3. DECIDE: Select verb and sub-verb
   - Generate candidate actions across all six verb categories
   - Score each against factional objective function
   - Apply resource constraints (budget, threads, legal authority)
   - Select highest-scoring feasible action

4. ACT: Execute in Layer 1
   - Consume resources (budget, thread allocation)
   - Apply effects to targets

5. CONSEQUENCES (Layer 3):
   - Legitimacy changes
   - Faction balance shifts
   - Community consciousness effects
   - Player response opportunities
```

### Escalation Ladder

Preferred order (low to high cost/visibility):

```
PROPAGANDIZE -> BRIBE -> INCORPORATE -> SURVEIL -> DIVIDE
    -> INFILTRATE -> INVEST/REZONE -> FUND(security) -> LEGISLATE
        -> RAID -> PROSECUTE -> DISPLACE -> STRATEGIC_WITHDRAWAL
            -> EMERGENCY_POWERS -> MASS_RAID -> LIQUIDATE -> SCORCHED_EARTH
```

---

## Data Requirements

### State Budget Model

State budget derives from:
- Tax revenue (proportional to economic activity in jurisdiction, QCEW-derived)
- Federal transfers (for sub-federal state apparatuses)
- Imperial rent pool (for state discretionary capacity)

Budget is allocated across verb categories each tick, influenced by faction balance. Budget is finite — the fundamental constraint making state behavior strategic rather than omnipotent.

### Technology Tree Integration

The RESEARCH verb interfaces with the existing technologies.json. Technologies have faction preferences (Security-State pursues Predictive Repression; Finance-Capital pursues efficiency tech; all factions fund LLMs). Player appropriation mechanic: PUBLIC research is appropriable if player has skilled cadre; CLASSIFIED requires intelligence; BLACK requires infiltration.

---

## Assumptions

- **A-001**: Three factions are sufficient to model US state behavior at the resolution relevant to Detroit. More granular models (separating industrial from finance capital, or local from federal security apparatus) introduce scope beyond what is testable with current data.
- **A-002**: Faction balance as a weight vector summing to 1.0 assumes factions compete for influence over a shared apparatus rather than controlling separate parallel apparatuses. Both are true in reality; the simplification is acceptable for MVP.
- **A-003**: The state AI decision function is deterministic given world state and RNG seed. No external AI service in stub implementation. Strategy pattern allows hot-swap to LLM-backed decisions later.
- **A-004**: Budget is the binding constraint for non-REPRESS verbs; attention threads for REPRESS verbs. May need revisiting if playtesting reveals unrealistic behavior.
- **A-005**: LIQUIDATE in core territories requires EMERGENCY_POWERS. This is a game design constraint for legible escalation, not a claim about reality.
- **A-006**: Fascist convergence threshold (SS>0.4, settler CI>0.6, FC<0.25) is a game design parameter. Calibrate through playtesting.
- **A-007**: H3 resolution 7 for Detroit territory grid. Heat represented as float [0,1]. H3 k-ring for adjacency calculations.
- **A-008**: Sparrow numerical signatures algorithm converges in O(edges) per iteration. Sufficient for real-time computation at Detroit metro scale.

---

## What This Spec Does NOT Include

- International state relations (other states, international pressure, sanctions)
- Intra-apparatus politics (factions within the FBI, progressive prosecutors vs. law-and-order DAs)
- Electoral mechanics (how elections change faction balance — LEGISLATE and FactionBalance provide hooks)
- Climate change effects on state capacity
- Player-controlled state apparatus (post-revolution governance — endgame)
- LLM-backed decision function for state AI (stub is rule-based; strategy pattern enables future hot-swap)
- Detailed implementation of each sub-verb's effect calculations (those belong in implementation-phase contracts)
- Organization-to-institution transition mechanics (deferred)
- Coalition/united front formation mechanics (deferred)
