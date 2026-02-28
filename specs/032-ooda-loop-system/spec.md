# Feature Specification: OODA Loop System

**Feature Branch**: `032-ooda-loop-system`
**Created**: 2026-02-28
**Status**: Draft
**Input**: OODA Loop System — organizational action resolution. Organizations are agents; OODA loops are their metabolism. Ticks represent ~1 week (52/year). Orgs act in layers per tick, with community hyperedges affecting action costs, eligibility, and consciousness effects.

## Clarifications

### Session 2026-02-28

- Q: What should happen with coordination_range and autonomy in the OODA ACT phase? They're specified in FR-005 but have no behavioral requirements. → A: Specify behavior now. coordination_range limits the number of distinct territories an org can target per tick. autonomy modifies the effectiveness-breadth tradeoff: high autonomy distributes actions across more targets with diluted effect; low autonomy concentrates actions with amplified effect.
- Q: Do organizational actions consume only action_points per tick, or also budget/monetary resources? → A: Actions are primarily constrained by action_points (OODA ACT phase capacity). The Action model MUST include resource cost fields (cadre_labor_cost, sympathizer_labor_cost, budget_cost) for forward compatibility with the Vanguard Economy (Epoch 3, see ai-docs/epochs/epoch3/vanguard-economy.yaml). In this feature, action_points is enforced; resource costs are defined but not enforced until the Vanguard Economy is integrated.
- Design correction: Initiative is dynamic, not fixed. The original spec assumed state always acts first (Layer 1 before Layer 2). Corrected to: initiative is a computed score combining OODA cycle time, institutional bonus, counter-intelligence, community embeddedness, and momentum. State starts with high institutional bonus but revolutionaries can seize the initiative. Layers 1/2 merged into a single Action Phase resolved by initiative score.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Layer-Ordered Turn Resolution (Priority: P1)

The simulation resolves one tick of organizational activity in three phases: Layer 0 (automatic economic metabolism), the Action Phase (all organizations resolved in initiative order), and Layer 3 (consequence propagation). Within the Action Phase, each organization's initiative score determines who acts first. The state begins the game with a large institutional initiative bonus, but this advantage can erode as revolutionary organizations build counter-intelligence, community embeddedness, momentum from successful actions, and superior OODA speed. Initiative is not a fixed privilege — it is a contested terrain.

**Why this priority**: Initiative ordering is the structural foundation. Without it, no organizational action can be meaningfully resolved. The dynamic initiative model encodes the material reality that state power is contingent, not absolute — the state starts with institutional advantage but revolutionary organizations can seize the initiative through organization, speed, and popular support.

**Independent Test**: Can be fully tested by creating a minimal tick with one StateApparatus, one PoliticalFaction, and one Business, verifying that Layer 0 runs automatically, the Action Phase resolves organizations by initiative score (state first in early game), and Layer 3 propagates consequences.

**Acceptance Scenarios**:

1. **Given** a tick at game start with a Business, an FBI StateApparatus, and a revolutionary PoliticalFaction, **When** the turn resolves, **Then** Layer 0 processes business surplus extraction automatically, the FBI acts before the faction in the Action Phase (institutional initiative bonus dominates early), and Layer 3 propagates consequences.
2. **Given** two PoliticalFactions in the Action Phase with different initiative scores, **When** the turn resolves, **Then** the organization with the higher initiative score acts first.
3. **Given** a revolutionary PoliticalFaction that has built strong counter-intelligence, community embeddedness, and momentum from recent successes, **When** its initiative score is computed against a local police StateApparatus, **Then** the faction's initiative score can exceed the police's, causing the faction to act first.
4. **Given** a tick with no organizations present, **When** the turn resolves, **Then** Layer 0 still processes automatic metabolism and no errors occur.
5. **Given** an FBI StateApparatus (national jurisdiction, high institutional bonus) vs the same revolutionary faction, **When** initiative scores are compared, **Then** the FBI's institutional bonus is harder to overcome than the local police's, reflecting the material reality that federal state power is more entrenched than local.

______________________________________________________________________

### User Story 2 - OODA Profile and Cycle Time (Priority: P2)

Each organization has an OODA profile describing its observe, orient, decide, and act capabilities. The profile contributes to a computed initiative score (along with institutional bonus, counter-intelligence, community embeddedness, and momentum) that governs action ordering in the Action Phase, and constrains the number and scope of actions the organization can take per tick.

**Why this priority**: The OODA profile is the data model that all action mechanics depend on. It encodes the fundamental tradeoff: small autocratic organizations cycle fast but coordinate poorly; large democratic organizations cycle slowly but achieve coherent strategy. Democratic centralism (fast decide + democratic orient + disciplined act) represents a specific and historically significant optimization. The initiative score integrates OODA speed with situational factors — a fast organization embedded in a supportive community with counter-intelligence capability can seize the initiative from the state.

**Independent Test**: Can be fully tested by constructing organizations with different OODA profiles and initiative factors, verifying that initiative scores produce the correct ordering, and that action_points constrain available actions per tick.

**Acceptance Scenarios**:

1. **Given** an organization with AUTOCRATIC decision mode and low bureaucratic depth, **When** its cycle time is computed, **Then** it is shorter than an identical organization with CONSENSUS decision mode.
2. **Given** an organization with DEMOCRATIC decision mode and high ideological coherence, **When** its cycle time is computed, **Then** the orient phase contributes less delay than an organization with low coherence (coherent organizations orient faster).
3. **Given** an organization with 3 action_points, **When** it submits 4 actions in a single tick, **Then** only the first 3 are executed and the 4th is rejected.
4. **Given** two organizations with identical profiles except sensor_latency (1 tick vs 3 ticks), **When** their cycle times are compared, **Then** the organization with lower latency has a shorter cycle time.
5. **Given** an organization with coordination_range of 1 and headquarters in territory A, **When** it attempts to target territory B (not adjacent), **Then** the action is rejected as out of range.
6. **Given** two identical organizations except autonomy (0.2 vs 0.8), both performing EDUCATE on the same community, **When** the consciousness effects are compared, **Then** the low-autonomy organization produces a larger per-action consciousness effect while the high-autonomy organization can spread actions across more targets.

______________________________________________________________________

### User Story 3 - Action Types with Consciousness Side-Effects (Priority: P3)

Organizations execute typed actions (EDUCATE, AGITATE, RECRUIT, REPRESS, PROVIDE_SERVICE, etc.) that produce both direct effects and consciousness side-effects on target communities. The consciousness effect depends on the interaction between the action type, the acting organization's consciousness tendency, and the organization's embeddedness in the target community.

**Why this priority**: Actions are the core gameplay mechanic. The consciousness side-effect system is what makes the simulation politically meaningful: the same action (PROVIDE_SERVICE) has different ideological consequences depending on whether a revolutionary mutual aid org or a liberal NGO performs it.

**Independent Test**: Can be fully tested by executing individual action types from organizations with different consciousness tendencies against a target community and measuring the resulting consciousness delta (collective_identity change, contestation change, tendency pressure).

**Acceptance Scenarios**:

1. **Given** a revolutionary PoliticalFaction performing EDUCATE in a community where it has high membership overlap, **When** the action resolves, **Then** the community's collective_identity increases and dominant_tendency shifts toward REVOLUTIONARY.
2. **Given** a liberal CivilSocietyOrg performing EDUCATE in the same community, **When** the action resolves, **Then** the community's collective_identity does not increase (neutral or slight decrease) and dominant_tendency shifts toward LIBERAL.
3. **Given** a StateApparatus performing ASSIMILATE against a marginalized community, **When** the action resolves, **Then** the community's collective_identity decreases (pushed toward 0).
4. **Given** any organization performing AGITATE in a community, **When** the action resolves, **Then** ideological_contestation increases in that community.
5. **Given** a revolutionary org performing PROVIDE_SERVICE, **When** compared to a liberal org performing the same service, **Then** the revolutionary org produces a small positive collective_identity effect while the liberal org produces a neutral or slightly negative effect.
6. **Given** an organization performing EDUCATE in a community where it has zero membership overlap, **When** the action resolves, **Then** the consciousness effect is severely reduced by a credibility penalty.

______________________________________________________________________

### User Story 4 - Community-Modified Action Costs (Priority: P4)

The cost of organizational actions varies based on the relationship between the acting organization and the target community. Actions within communities where the organization is embedded cost less; actions across contradiction pairs cost more; consciousness work in communities the organization is not part of incurs a credibility penalty.

**Why this priority**: Cost modification prevents organizations from cheaply projecting influence into communities they have no organic relationship with. This encodes the principle that you cannot raise consciousness in a community from outside it.

**Independent Test**: Can be fully tested by computing action costs for the same action type across different org-community relationships (embedded, non-embedded, across contradiction axis) and verifying the cost differentials.

**Acceptance Scenarios**:

1. **Given** an organization recruiting within a community where it shares membership, **When** the RECRUIT cost is computed, **Then** it costs fewer action points than recruiting in a community with no shared members.
2. **Given** an organization recruiting across a contradiction pair (e.g., a SETTLER-dominated org targeting a NEW_AFRIKAN community), **When** the RECRUIT cost is computed, **Then** it costs significantly more than recruiting within a shared community.
3. **Given** an organization performing EDUCATE in a community where it has members, **When** the cost is computed, **Then** the cost is at the base rate.
4. **Given** an organization performing EDUCATE in a community where it has no members, **When** the cost is computed, **Then** the cost is higher and the action's effectiveness is reduced by a credibility multiplier.
5. **Given** BUILD_INFRASTRUCTURE targeting a community hyperedge, **When** the action resolves, **Then** all members of that community benefit from the infrastructure improvement.

______________________________________________________________________

### User Story 5 - Lifecycle-Modified Action Capacity (Priority: P5)

An organization's action capacity is modified by the lifecycle composition of its membership. Youth (D-phase) members cannot act but receive ideological socialization. Adult (P-phase) members have full action capacity. Elder (D'-phase) members have reduced action points but provide legitimacy bonuses and institutional memory.

**Why this priority**: Lifecycle integration grounds organizational capacity in demographic reality. Organizations controlling youth institutions (schools) gain disproportionate ideological influence over the next generation, which is a critical strategic dynamic.

**Independent Test**: Can be fully tested by constructing organizations with different lifecycle compositions and verifying that effective action capacity reflects the weighted contribution of each lifecycle phase.

**Acceptance Scenarios**:

1. **Given** an organization with 50% youth membership, **When** its effective action capacity is calculated, **Then** it is lower than an identical organization with 50% adult membership (youth contribute zero action capacity).
2. **Given** an organization with significant elder membership, **When** its effective action capacity is calculated, **Then** elders contribute reduced action points (scaled by elder capacity factor) but the organization receives a legitimacy bonus on consciousness-related actions.
3. **Given** an organization controlling a youth institution (school), **When** it performs EDUCATE targeting youth, **Then** the action shapes the ideological socialization of D-phase members without requiring those members to "act."
4. **Given** a youth-only membership pool, **When** the organization attempts any non-EDUCATE action, **Then** the action fails due to insufficient action capacity.

______________________________________________________________________

### User Story 6 - Layer 3 Consequence Propagation (Priority: P6)

After Layer 0 and the Action Phase complete, Layer 3 propagates consequences: heat changes on communities targeted by state action, edge transformations (TRANSACTIONAL to SOLIDARISTIC from ORGANIZE actions), community consciousness shifts (aggregate collective_identity and dominant_tendency updates), infrastructure effects, and legitimation index updates.

**Why this priority**: Consequence propagation is what connects organizational actions to the broader simulation. Without it, actions are isolated events with no systemic impact.

**Independent Test**: Can be fully tested by executing a set of actions across Layer 0 and the Action Phase, then running Layer 3 propagation and verifying that community states, edge modes, heat levels, and legitimation indices update correctly.

**Acceptance Scenarios**:

1. **Given** a StateApparatus that performed SURVEIL on a community in the Action Phase, **When** Layer 3 propagates, **Then** that community's heat increases.
2. **Given** a PoliticalFaction that performed ORGANIZE in the Action Phase, **When** Layer 3 propagates, **Then** affected edges shift from TRANSACTIONAL toward SOLIDARISTIC mode.
3. **Given** multiple organizations that targeted the same community with consciousness-affecting actions, **When** Layer 3 propagates, **Then** the aggregate consciousness effect is computed (summing deltas, dominant tendency by weight) and the community's collective_identity and dominant_tendency update accordingly.
4. **Given** ATTACK_INFRASTRUCTURE against a community, **When** Layer 3 propagates, **Then** the community's infrastructure decreases and reproduction costs increase for members.
5. **Given** a tick's worth of D-P-D' transitions in Layer 0, **When** Layer 3 propagates, **Then** the legitimation index updates based on population reproduction dynamics.

______________________________________________________________________

### User Story 7 - Detroit Integration Test (Priority: P7)

A single tick resolves with four organizations operating in Detroit: the FBI (StateApparatus), a revolutionary faction (PoliticalFaction), a liberal church (CivilSocietyOrg), and an auto manufacturer (Business). Each organization acts according to its layer, OODA profile, and relationship to Detroit's communities. The tick produces observable changes to community consciousness, heat, and organizational resources.

**Why this priority**: This is the integration test that validates all components working together. Detroit is the canonical test territory because it sits at the intersection of colonial, class, and lifecycle contradictions.

**Independent Test**: Can be fully tested by constructing a Detroit scenario with four organizations, running one tick, and verifying that initiative ordering is correct, consciousness effects reflect organizational tendencies, and the state's institutional bonus gives it early-game priority.

**Acceptance Scenarios**:

1. **Given** the FBI performing SURVEIL on a NEW_AFRIKAN community at game start, **When** the tick completes, **Then** the FBI acted before the revolutionary faction (institutional initiative bonus) and that community's heat has increased and visibility has risen.
2. **Given** the revolutionary faction performing EDUCATE in a community where it has members, **When** the tick completes, **Then** collective_identity in that community has increased (small per-tick amount).
3. **Given** the liberal church performing PROVIDE_SERVICE to the same community, **When** the tick completes, **Then** collective_identity has not increased from the church's action (neutral/slightly negative consciousness effect despite material benefit).
4. **Given** the auto manufacturer in Layer 0, **When** the tick completes, **Then** surplus extraction and wage payments processed automatically without OODA involvement.
5. **Given** all four organizations acted, **When** Layer 3 propagates, **Then** the aggregate consciousness effect on each targeted community reflects the net of all acting organizations' tendencies.
6. **Given** the same Detroit scenario but 20 ticks later, with the revolutionary faction having built strong counter-intelligence and community embeddedness, **When** initiative scores are computed, **Then** the faction's initiative score has risen relative to the local police (though the FBI's federal bonus remains harder to overcome).

______________________________________________________________________

### Edge Cases

- What happens when an organization has zero action points (fully elder/youth composition)?
- What happens when two organizations in the Action Phase have identical initiative scores? (Resolution: deterministic tiebreaker by organization ID)
- What happens when a community's collective_identity would exceed 1.0 or drop below 0.0 from aggregate effects? (Clamped to [0, 1])
- What happens when an organization targets a community that no longer exists (dissolved between ticks)? (Action fails gracefully, action points not consumed)
- What happens when a StateApparatus with EXTRALEGAL standing attempts REPRESS? (Allowed but generates higher heat on the org itself)
- What happens when AGITATE is performed in a community with ideological_contestation already at 1.0? (No additional contestation increase; contestation is clamped)
- What happens when an organization attempts an action it is not eligible for (e.g., a Business attempting REPRESS)? (Action rejected; action points not consumed)
- What happens when Layer 0 economic metabolism produces negative surplus for a Business? (Business operates at a loss; no surplus extraction, but wage obligations remain)
- What happens when a revolutionary org's initiative score exactly equals a StateApparatus's score? (Tiebreaker by organization ID, same as any other tie — no inherent state advantage in ties)

## Requirements *(mandatory)*

### Functional Requirements

**Turn Resolution**

- **FR-001**: System MUST resolve each tick's organizational actions in three phases: Layer 0 (automatic economic metabolism), Action Phase (all organizations resolved in descending initiative score order), and Layer 3 (consequence propagation).
- **FR-002**: System MUST compute an initiative score for each organization each tick. The initiative score MUST be a function of: OODA cycle time (faster = higher initiative), institutional initiative bonus (state apparatus starts high, non-state starts low), counter-intelligence capability, community embeddedness, and momentum from recent successful actions.
- **FR-003**: System MUST resolve Action Phase organizations in descending initiative score order (highest first). Organizations with identical initiative scores MUST be resolved in deterministic order (by organization ID).
- **FR-004**: Layer 0 MUST NOT involve OODA processing; economic metabolism (surplus extraction, wage payment, D-P-D' population transitions) runs automatically each tick.
- **FR-042**: StateApparatus organizations MUST receive an institutional initiative bonus that is high at game start, reflecting entrenched state power. This bonus MUST be configurable in GameDefines and MUST vary by jurisdiction level (federal > state > local).
- **FR-043**: Non-state organizations MUST be able to increase their initiative score through: faster OODA cycle times, successful counter-intelligence (COUNTER_INTEL actions), deep community embeddedness (high membership overlap in target communities), and momentum (accumulated from recent successful actions).
- **FR-044**: Initiative advantage MUST be contestable: a revolutionary organization with superior OODA speed, strong community roots, and successful counter-intelligence MUST be able to exceed a local police StateApparatus's initiative score. Federal-level state apparatus (FBI) MUST have a higher institutional bonus that is harder but not impossible to overcome.

**OODA Profile**

- **FR-005**: Each organization MUST have an OODAProfile with four phases: OBSERVE (intelligence, sensor_latency), ORIENT (ideological_coherence, analytical_capacity), DECIDE (decision_mode, bureaucratic_depth), and ACT (action_points, coordination_range, autonomy).
- **FR-006**: System MUST compute cycle_time from the OODAProfile such that AUTOCRATIC decision mode produces shorter cycle times than DELEGATE, which is shorter than DEMOCRATIC, which is shorter than CONSENSUS. Faster cycle_time MUST contribute to a higher initiative score.
- **FR-007**: System MUST constrain the number of actions per tick to the organization's action_points. Actions beyond this limit MUST be rejected.
- **FR-008**: sensor_latency MUST represent the delay (in ticks) before observed information becomes available to the orient phase. In this feature, sensor_latency is used as a cycle time weight in the OBSERVE phase computation (higher latency → slower cycle time). Delayed-observation semantics (observing state from N ticks ago) are deferred to a future enhancement.
- **FR-040**: coordination_range MUST limit the number of distinct territories an organization can target with actions in a single tick. An organization can only act within territories reachable from its headquarters or territory_ids within its coordination_range. StateApparatus organizations with national jurisdiction MUST have coordination_range covering all territories in their jurisdiction.
- **FR-041**: autonomy MUST modify the effectiveness-breadth tradeoff of organizational actions. High autonomy (close to 1.0) allows distributing actions across more targets per tick but reduces per-action consciousness effect magnitude. Low autonomy (close to 0.0) concentrates actions on fewer targets but amplifies per-action consciousness effect. "Disciplined ACT" (democratic centralism pattern) corresponds to low autonomy with high coordination.

**Action Types**

- **FR-009**: System MUST support the following action types: RECRUIT, ORGANIZE, EDUCATE, AGITATE, PROPAGANDIZE, FUNDRAISE, PROVIDE_SERVICE, EMPLOY, REPRESS, PROTEST, STRIKE, EXPROPRIATE, SURVEIL, INFILTRATE, COUNTER_INTEL, MAP_NETWORK, PROPOSE_ALLIANCE, DENOUNCE, BUILD_INFRASTRUCTURE, ATTACK_INFRASTRUCTURE, ASSIMILATE.
- **FR-010**: Each action type MUST have a base action point cost, an eligibility set (which organization types can perform it), a consciousness effect profile, and resource cost fields (cadre_labor_cost, sympathizer_labor_cost, budget_cost) for forward compatibility with the Vanguard Economy. In this feature, only action_points are enforced; resource costs are defined but deferred.
- **FR-011**: REPRESS and SURVEIL MUST be restricted to StateApparatus organizations (and organizations with violence_capacity or surveillance_capacity respectively).
- **FR-012**: ASSIMILATE MUST be available to StateApparatus and organizations with LIBERAL consciousness tendency that have institutional backing.
- **FR-013**: EMPLOY MUST be restricted to Business organizations.

**Consciousness Effects**

- **FR-014**: Every action performed within or targeting a community MUST produce a consciousness side-effect determined by the combination of action type, the acting organization's consciousness_tendency, and the organization's embeddedness (membership overlap) in the target community.
- **FR-015**: EDUCATE by a REVOLUTIONARY organization MUST increase collective_identity and shift dominant_tendency toward REVOLUTIONARY. EDUCATE by a LIBERAL organization MUST produce neutral or negative collective_identity change.
- **FR-016**: AGITATE MUST increase ideological_contestation in the target community regardless of the acting organization's tendency. AGITATE serves as a precondition for EDUCATE effectiveness: EDUCATE in a community with low contestation MUST produce diminished consciousness effects.
- **FR-017**: ASSIMILATE MUST decrease collective_identity (push toward 0) in the target community.
- **FR-018**: PROVIDE_SERVICE by a REVOLUTIONARY organization MUST produce a small positive collective_identity effect. PROVIDE_SERVICE by a LIBERAL organization MUST produce neutral or slightly negative collective_identity effect.
- **FR-019**: Consciousness effects MUST be small per tick (no single action should shift collective_identity by more than a configurable maximum delta per tick) but compound over multiple ticks.
- **FR-020**: Credibility MUST scale the consciousness effect: an organization's membership overlap with the target community determines its credibility. Zero overlap MUST result in near-zero consciousness effect.

**Community-Modified Costs**

- **FR-021**: RECRUIT within a community where the organization shares membership MUST cost fewer action points than the base cost.
- **FR-022**: RECRUIT across a contradiction pair (hegemonic org targeting marginalized community or vice versa) MUST cost significantly more than the base cost.
- **FR-023**: EDUCATE in a community where the organization has no membership MUST cost more and suffer a credibility penalty that reduces effectiveness.
- **FR-024**: BUILD_INFRASTRUCTURE MUST benefit all members of the targeted community hyperedge.
- **FR-025**: ATTACK_INFRASTRUCTURE MUST reduce the targeted community's infrastructure level and increase reproduction_cost_modifier for its members.

**Lifecycle Constraints**

- **FR-026**: Youth (D-phase) members MUST NOT contribute action capacity. They receive EDUCATE (ideological socialization) but cannot execute other actions.
- **FR-027**: Adult (P-phase) members MUST contribute full action capacity.
- **FR-028**: Elder (D'-phase) members MUST contribute reduced action capacity (scaled by the configurable elder_capacity_factor) and MUST provide a legitimacy bonus on consciousness-related actions.
- **FR-029**: Organizations controlling D-phase institutions (schools, youth programs) MUST be able to perform EDUCATE targeting youth, shaping their ideological orientation.

**Layer 3 Propagation**

- **FR-030**: Layer 3 MUST aggregate all consciousness deltas targeting each community and apply them as a single update to collective_identity and dominant_tendency, using the existing aggregation formula (sum deltas, clamp to [0, 1], dominant tendency by weight).
- **FR-031**: Layer 3 MUST update community heat based on state surveillance and repression actions from the Action Phase.
- **FR-032**: Layer 3 MUST process edge transformations triggered by ORGANIZE actions (TRANSACTIONAL to SOLIDARISTIC mode transitions).
- **FR-033**: Layer 3 MUST update community infrastructure levels based on BUILD_INFRASTRUCTURE and ATTACK_INFRASTRUCTURE actions.
- **FR-034**: All configurable coefficients (action costs, consciousness effect magnitudes, cost modifiers, cycle time weights) MUST be centralized in GameDefines, not hardcoded.

**Integration**

- **FR-035**: The OODA system MUST integrate with the existing SimulationEngine tick pipeline as a system that participates in the ordered system execution.
- **FR-036**: The OODA system MUST use the existing GraphProtocol for all graph operations (querying organizations, updating community state, reading edges).
- **FR-037**: The OODA system MUST publish events via the existing EventBus for significant actions (state repression, protests, consciousness shifts exceeding a threshold).
- **FR-038**: NPC action selection MUST be handled by a stub that selects actions based on simple priority rules (not full AI). Full NPC AI is deferred to a future phase.
- **FR-039**: Player action input MUST be accepted as a pre-formed list of actions for the player's organization. Player UI is deferred to a future phase.

### Key Entities

- **OODAProfile**: Four-phase organizational capability profile (observe, orient, decide, act) with a computed cycle_time. Determines action ordering and capacity per tick.
- **ActionType**: Enumeration of all organizational actions (21 types across 7 categories: recruitment, consciousness work, resources, conflict, intelligence, diplomacy, infrastructure).
- **Action**: A single organizational action for a tick, specifying the acting organization, action type, target (community, organization, or territory), action point cost, and forward-compatible resource costs (cadre_labor_cost, sympathizer_labor_cost, budget_cost) for Vanguard Economy integration.
- **ActionResult**: The outcome of executing an action, including direct effects, consciousness delta, resource expenditure, and any events generated.
- **ConsciousnessDelta**: The consciousness side-effect of an action on a target community (collective_identity change, contestation change, tendency pressure). Extends the existing Feature 031 model.
- **TurnResolution**: The complete processing of one tick across all three phases (Layer 0, Action Phase, Layer 3), collecting all action results and propagating consequences.
- **ActionCostModifier**: The computed cost adjustment for an action based on org-community relationship (shared membership, contradiction axis, embeddedness).
- **InitiativeScore**: The computed per-tick ordering value for each organization, combining OODA cycle time, institutional bonus, counter-intelligence, community embeddedness, and momentum. Determines who acts first in the Action Phase.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A single tick with four organizations (StateApparatus, PoliticalFaction, CivilSocietyOrg, Business) resolves within the existing tick pipeline, producing correct initiative ordering (state first at game start due to institutional bonus; non-state organizations can seize initiative as conditions change).
- **SC-002**: CONSENSUS organizations consistently produce longer cycle times than AUTOCRATIC organizations across all valid parameter combinations.
- **SC-003**: RECRUIT within a shared community costs measurably fewer action points than RECRUIT across a contradiction pair.
- **SC-004**: EDUCATE by a REVOLUTIONARY organization produces a positive collective_identity delta, while EDUCATE by a LIBERAL organization produces a zero or negative delta, for the same target community.
- **SC-005**: ASSIMILATE produces a negative collective_identity delta on the target community.
- **SC-006**: EDUCATE in a community where the organization has zero membership overlap produces near-zero consciousness effect (credibility penalty).
- **SC-007**: PROVIDE_SERVICE by a REVOLUTIONARY organization produces a measurably different consciousness effect than the same service by a LIBERAL organization.
- **SC-008**: AGITATE increases ideological_contestation in the target community, and EDUCATE following AGITATE produces a larger consciousness effect than EDUCATE without prior agitation.
- **SC-009**: Youth (D-phase) members receive EDUCATE effects but contribute zero action capacity; elder (D'-phase) members contribute reduced action capacity with a legitimacy bonus.
- **SC-010**: Per-tick consciousness changes remain below the configurable maximum delta, but compound across 52 ticks to produce meaningful ideological shifts.
- **SC-011**: All action costs, effect magnitudes, and cycle time weights trace to named coefficients in GameDefines with no hardcoded numeric literals in system logic.

## Assumptions

- **A-001**: Feature 031 (Organization Base Model) is fully implemented, providing organization subtypes, consciousness effects, composition queries, and key figure topology.
- **A-002**: Community hyperedge infrastructure (Features 022, 029) is fully implemented, providing CommunityConsciousness, CommunityState, CommunityType, membership queries, and contradiction axes.
- **A-003**: The D-P-D' lifecycle circuit (Feature 030) is implemented, providing lifecycle phase classification and population transitions.
- **A-004**: One tick represents approximately one week of real time (52 ticks per simulation year).
- **A-005**: Player actions are provided as pre-formed action lists (no interactive UI in this feature). NPC actions come from a simple priority-based stub.
- **A-006**: Consciousness changes are intentionally slow per tick (ideological change is gradual) but compound over many ticks to produce meaningful shifts over simulated months/years.

## Scope Exclusions

- **NPC AI Logic**: Full autonomous decision-making for NPC organizations is deferred. This feature provides only a stub that selects highest-priority available actions.
- **Player UI**: Interactive action selection interface is deferred. Player actions are accepted as pre-formed lists.
- **Detailed Infiltration Mechanics**: Deep infiltration simulation (agent placement, cover maintenance, extraction) is deferred. INFILTRATE action exists but has simplified resolution.
- **Coalition Formation**: Inter-organizational alliance negotiation and coalition governance is deferred. PROPOSE_ALLIANCE and DENOUNCE exist as actions but resolve as simple relationship changes.
- **Multi-Tick Action Planning**: Sustained campaigns, escalation ladders, and strategic planning across multiple ticks are deferred.
- **Attention Threads**: Organization-level attention allocation across multiple simultaneous concerns is deferred.

## Dependencies

- **Requires**: Feature 031 (Organization Base Model) — org subtypes, consciousness effects, composition
- **Requires**: Feature 029 (Community Hyperedge Upgrade) — community consciousness, contradiction axes, membership
- **Requires**: Feature 030 (D-P-D' Lifecycle Circuit) — lifecycle phases, population transitions
- **Integrates with**: SimulationEngine tick pipeline, GraphProtocol, EventBus, GameDefines
- **Required By**: Future NPC AI system, future player UI, future coalition system
