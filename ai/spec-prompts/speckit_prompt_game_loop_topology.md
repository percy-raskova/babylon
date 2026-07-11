# Spec-Kit Prompt: Game Loop Topology

## Spec ID: `020-game-loop-topology`

```
Create a specification for the Game Loop Topology — the NetworkX graph
schema required to support one complete play cycle with nine player verbs.

CONTEXT:
- Babylon has a working 12-system simulation engine operating on a NetworkX DiGraph
- The graph currently has two node types (social_class, territory) and six edge
  types (EXPLOITATION, SOLIDARITY, TRIBUTE, WAGES, TENANCY, ADJACENCY)
- The engine runs ticks, produces events, the economics layer computes real values
- MISSING: the player has no representation in the graph, organizations don't exist
  as agents, and the nine player verbs have no graph operations to execute against
- This spec adds the MINIMUM topology needed for one playable turn cycle

WHAT ALREADY EXISTS (NOT IN SCOPE TO BUILD):

**Graph infrastructure** (all functional):
- GraphProtocol: 16-method backend-agnostic interface (graph_protocol.py)
- NetworkX adapter implementing GraphProtocol
- SocialRole enum: 8 class positions (CORE_BOURGEOISIE through CARCERAL_ENFORCER)
- EdgeType enum: 6 edge types (EXPLOITATION, SOLIDARITY, TRIBUTE, WAGES, TENANCY, ADJACENCY)
- Node attributes: wealth, consciousness, is_alive, population, territory references
- Territory nodes with FIPS codes, biocapacity, hex assignments
- 12-system engine executing in materialist causality order
- Scenario creation functions (create_imperial_circuit_scenario, etc.)
- Entity registry with canonical IDs

**Theoretical design** (documented but not implemented):
- EdgeMode categorical framework (EXTRACTIVE/TRANSACTIONAL/SOLIDARISTIC/ANTAGONISTIC)
  from solidarity_edge_formalization.md — NOT in production code
- Organization-as-subgraph-view architecture from prior design conversations
- OODA loop formalization for organizational agency
- Attention Thread model for state repression
- Contradiction primitive spec

**The current graph is an economic substrate. This spec adds the political layer.**

THEORETICAL FOUNDATION:

**1. Organizations Are the Only Agents**
Everything else — class nodes, territories, economic flows — is substrate.
Organizations observe the substrate, make decisions, and act on the graph.
The player controls one Organization. NPCs control others (state, businesses,
rival factions, civil society).

**2. Organizations Are Named Subgraph Views, Not New Node Types**
An Organization is a set of member node IDs + institutional attributes.
Organization.to_subgraph(G) returns an nx.subgraph_view.
This means organizations OVERLAP — a worker can be a union member AND
a church member AND a party member simultaneously. Multiple edges.

**3. EdgeMode Replaces EdgeType for Inter-Group Relations**
The four categorical modes (EXTRACTIVE, TRANSACTIONAL, SOLIDARISTIC, ANTAGONISTIC)
from solidarity_edge_formalization.md are the qualitative relationship types.
Organizing work TRANSFORMS edge modes — this is the core mechanic.
EdgeMode transitions follow degradation/upgrade paths:
  SOLIDARISTIC ↔ TRANSACTIONAL ↔ EXTRACTIVE → ANTAGONISTIC
  (ANTAGONISTIC can resolve to any mode depending on outcome)

**4. The Nine Player Verbs as Graph Operations**
Each verb is a function: (Organization, TargetNode(s), Graph) → MutatedGraph.
Every verb costs organizational resources (cadre time, material).
Every verb has observable consequences on the graph.

THE NINE VERBS AND THEIR GRAPH OPERATIONS:

1. EDUCATE (target: population nodes connected to org)
   - Reads: org membership edges, target consciousness, target class position
   - Writes: target consciousness, may upgrade edge resilience
   - Query: "which population nodes am I connected to, and what's their
     current consciousness level?"
   - Requires: MEMBERSHIP edges between org and social_class nodes

2. AID (target: population nodes in territory)
   - Reads: org resources, target V_reproduction, territory conditions
   - Writes: target V_reproduction (reduces cost of living), may create new
     MEMBERSHIP edges (people join orgs that help them)
   - Query: "what territories am I present in, who lives there, what do
     they need?"
   - Requires: PRESENCE edges between org and territory nodes

3. ATTACK (target: other organization or state apparatus nodes)
   - Reads: org military capacity, target defense, graph distance
   - Writes: target org capacity reduction, may sever edges, may trigger
     state attention thread allocation, may transform edge modes
   - Query: "what are the enemy's key nodes, what's the topology between
     us and them?"
   - Requires: ANTAGONISTIC edges or ability to create them

4. MOBILIZE (target: population nodes for mass action)
   - Reads: org membership count, consciousness levels, solidarity density,
     current crisis conditions
   - Writes: temporarily projects power (strike disrupts production,
     demonstration shifts legitimacy), may create new solidarity edges
   - Query: "how many people can I turn out, what's the solidarity network
     density, are crisis conditions favorable?"
   - Requires: MEMBERSHIP edges with sufficient consciousness threshold

5. CAMPAIGN (target: electoral/institutional nodes)
   - Reads: org legitimacy, population support in territory, legal standing
   - Writes: may capture institutional positions, shifts policy parameters,
     may co-opt org (institutional capture risk)
   - Query: "what institutions exist in this territory, what's our
     support level?"
   - Requires: org legal_standing, territory-level support aggregation

6. MOVE (target: org's own resources and cadre)
   - Reads: org resource inventory, cadre assignments, territory access
   - Writes: redistributes cadre across territories, acquires resources
     (fundraise/expropriate), establishes supply lines
   - Query: "where are my people, where do I need them, what resources
     do I have?"
   - Requires: PRESENCE edges (which territories), MEMBERSHIP edges
     (which cadre), resource attributes on org

7. INVESTIGATE (target: territory, organization, or conditions)
   - Reads: org intelligence capacity, target observability,
     counter-surveillance
   - Writes: increases org's information about target (reveals hidden
     attributes, maps enemy topology, assesses conditions)
   - Query: "what do I know vs what exists, what's the gap?"
   - Requires: concept of information asymmetry — org.known_topology
     vs actual topology

8. REPRODUCE (target: org's own membership and capabilities)
   - Reads: org recruitment pipeline, sympathizer pool, training capacity
   - Writes: converts sympathizer → member → cadre (upgrades MEMBERSHIP
     edge attributes), improves org capability attributes
   - Query: "who's sympathetic but not yet a member, who's a member but
     not yet trained?"
   - Requires: MEMBERSHIP edges with tier attribute
     (SYMPATHIZER/MEMBER/CADRE)

9. NEGOTIATE (target: other organizations)
   - Reads: org diplomatic standing, target org goals/ideology, shared
     enemies, prior relationship
   - Writes: creates/transforms inter-org edges (ALLIANCE, CEASEFIRE,
     UNITED_FRONT), may merge resource pools, coordinate actions
   - Query: "which orgs share my enemies, what's our relationship history?"
   - Requires: ORG_RELATION edges between organization entities

REQUIRED NODE SCHEMA:

**social_class** (EXISTS — extend with):
  - consciousness: float [0,1] — exists, keep
  - membership_orgs: list[str] — org IDs this population block belongs to
  - sympathy_orgs: list[str] — org IDs with sympathizer-level connection
  - information_state: dict — what this node "knows" (for fog of war)

**territory** (EXISTS — extend with):
  - controlling_org: str | None — which org has dominant presence
  - org_presence: dict[str, float] — org_id → presence strength
  - institutional_slots: list[str] — which institutions exist here

**organization** (NEW node type):
  - org_id: str
  - org_type: OrgType (STATE_APPARATUS | BUSINESS | POLITICAL_FACTION |
    CIVIL_SOCIETY)
  - is_player: bool
  - class_character: ClassCharacter (BOURGEOIS | PETIT_BOURGEOIS |
    PROLETARIAN | LUMPEN)
  - legal_standing: LegalStanding (LEGAL | GREY | UNDERGROUND | BANNED)

  # Resources
  - cadre_count: int — trained operatives
  - member_count: int — general membership
  - budget: float — material resources
  - military_capacity: float — armed capability [0,1]

  # OODA profile (simplified for MVP)
  - actions_per_turn: int — how many verbs per tick (default 1-3)
  - cycle_speed: float — OODA speed modifier

  # State apparatus specific
  - attention_thread_max: int | None — only for STATE_APPARATUS
  - surveillance_capacity: float | None
  - violence_capacity: float | None

REQUIRED EDGE SCHEMA:

**MEMBERSHIP** (NEW: organization ↔ social_class):
  - tier: SYMPATHIZER | MEMBER | CADRE
  - since_tick: int
  - Undirected semantically but stored as org → social_class

**PRESENCE** (NEW: organization → territory):
  - strength: float [0,1]
  - visible: bool — can state detect this presence?
  - since_tick: int

**ORG_RELATION** (NEW: organization ↔ organization):
  - mode: EdgeMode (EXTRACTIVE | TRANSACTIONAL | SOLIDARISTIC | ANTAGONISTIC)
  - resilience: float [0,1]
  - formal_agreement: ALLIANCE | CEASEFIRE | UNITED_FRONT | NONE
  - intel_level: float [0,1] — how much each knows about the other

**ATTENTION_THREAD** (NEW: state_apparatus → target organization):
  - intensity: float [0,1]
  - intel_gathered: float [0,1]
  - phase: DORMANT | MONITORING | ACTIVE | DISRUPTION
  - ticks_active: int
  - stickiness: float [0,1] — institutional inertia

**Existing edges** (KEEP as substrate):
  - EXPLOITATION, SOLIDARITY, TRIBUTE, WAGES: economic substrate
  - TENANCY, ADJACENCY: spatial substrate
  - These continue to be managed by the 12-system engine
  - Player verbs READ these but mostly don't WRITE them directly
  - Exception: MOBILIZE (strike) can temporarily sever EXPLOITATION edges

EDGEMODE MIGRATION:
- Current EdgeType enum stays for backward compatibility with engine systems
- New EdgeMode enum added for inter-org and political edges
- EdgeMode transition rules from solidarity_edge_formalization.md:
  Under pressure: SOLIDARISTIC → TRANSACTIONAL → ANTAGONISTIC
  Through organizing: TRANSACTIONAL → SOLIDARISTIC (the core player mechanic)
  EXTRACTIVE → ANTAGONISTIC (rebellion) requires consciousness + org threshold
  ANTAGONISTIC resolution depends on outcome of conflict

TURN STRUCTURE:

Each tick, organizations act in speed order (fastest OODA first):
1. Economic substrate updates (existing 12-system engine)
2. State apparatus meta-OODA: allocate/reallocate attention threads
3. NPC organizations execute their OODA cycle (AI-driven verb selection)
4. Player organization selects and executes verbs (limited by actions_per_turn)
5. Consequences resolve: edge mode transitions, state responses, resource changes

For MVP, steps 2-3 can be stub implementations that do nothing. The critical
path is: player selects verb → verb executes as graph operation → graph state
changes → player can observe result.

SCOPE BOUNDARIES:
- DO NOT implement full OODA AI for NPC organizations (stub it)
- DO NOT implement full attention thread lifecycle (stub it)
- DO NOT implement fog of war / information asymmetry (all-visible MVP)
- DO NOT implement the Contradiction primitive
- DO NOT change the 12-system economic engine
- DO NOT build UI for verb selection (CLI/test harness is fine)
- DO implement all nine verbs as graph operation functions
- DO implement Organization node type with required attributes
- DO implement the four new edge types (MEMBERSHIP, PRESENCE, ORG_RELATION,
  ATTENTION_THREAD)
- DO implement EdgeMode enum with transition rules
- DO implement a Detroit scenario creator that instantiates:
  - 1 player PoliticalFaction
  - 1 StateApparatus (FBI Detroit field office)
  - 1-2 Businesses (auto industry)
  - 1-2 CivilSociety orgs (church, community org)
  - Connected to existing Wayne/Oakland social_class and territory nodes

VALIDATION CRITERIA:
- All nine verbs execute without error on Detroit test scenario
- EDUCATE on a connected population node increases consciousness
- AID on a territory reduces V_reproduction for residents
- ATTACK on a target org reduces its capacity
- MOBILIZE with sufficient support produces observable effect
- CAMPAIGN against an institution modifies policy parameters
- MOVE reallocates cadre between territories
- INVESTIGATE increases known information about target
- REPRODUCE converts sympathizer → member with MEMBERSHIP tier change
- NEGOTIATE between two orgs creates ORG_RELATION edge with agreed mode
- State attention thread activates when player org becomes visible enough
- Edge mode transitions follow documented rules (no SOLIDARISTIC → EXTRACTIVE
  without intermediate steps)

WHAT SUCCESS LOOKS LIKE:
After this spec is implemented, I can instantiate a Detroit scenario with
organizations, execute a sequence of player verbs from a test harness, and
watch the graph state change in response. Each verb has legible consequences.
The economic substrate (existing engine) continues running underneath. The
political layer (new) reads from the economic layer and acts on the social
layer. The state responds (even if minimally in MVP). This is the minimum
viable play cycle — ugly, CLI-driven, but interactive and responsive.

DEPENDENCIES:
- Requires: 019-detroit-vertical-slice (real data flowing through engine)
- Requires: Existing GraphProtocol and NetworkX adapter
- Requires: Existing social_class and territory node schemas
- Informs: Future UI spec for verb selection interface
- Informs: Future NPC AI spec for organizational decision-making
- Informs: Future attention thread spec for full state repression model

RELATIONSHIP TO PRIOR SPECS:
- Specs 020-025 from the org-topology conversation (organization base model,
  OODA system, attention threads, bifurcation, territory integration, NPC stub)
  are SUBSUMED by this spec. This is the integrated version that builds what
  the play cycle actually needs rather than building each subsystem in isolation.
- The full OODA formalization, attention thread lifecycle, and bifurcation
  analysis from those specs become FUTURE enhancements after the basic loop works.
```
