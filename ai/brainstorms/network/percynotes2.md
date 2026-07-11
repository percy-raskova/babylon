# Organization & Topology: Spec-Kit Prompts

**Purpose**: Prompts for Claude Code + spec-kit to generate specifications for the Organization system
**Usage**: Feed each prompt to `/speckit.specify` sequentially; each phase builds on the prior
**Context**: These assume existing codebase has SocialClass nodes, Territory nodes, EdgeMode enum, NetworkXAdapter, TopologyMonitor, and SimulationEngine with system execution order
**Key Insight**: In Babylon, Organizations ARE the agents. SocialClass and Territory are substrate.

---

## Architectural Foundation

The Organization system rests on four key insights from prior design work:

**1. Two-Layer Architecture: Substrate + Agents**
```
SUBSTRATE LAYER (no agency)
├── SocialClass blocks (demographic reservoirs with population, wealth, consciousness)
└── Territory (spatial grid, H3 hexagons, can be occupied/contested)

AGENT LAYER (has agency)
└── Organization (the ONLY agent type)
    ├── StateApparatus (FBI, police, military, courts)
    ├── Business (employer, extracts surplus value)
    ├── PoliticalFaction (player & NPC rivals)
    └── CivilSocietyOrg (church, NGO, union, school)
```

SocialClass blocks don't act — they're acted upon, recruited from, extracted from. Organizations are the entities that make decisions, take actions, have goals. This is orthodox Marxism: a class-in-itself is a statistical category; a class-for-itself requires organization.

**2. Organization vs Institution**
- **Organization**: Voluntary coordination for collective action. Has members, internal topology, can be destroyed.
- **Institution**: Crystallized social relations that reproduce themselves. Has legal standing, fixed assets, survives member turnover.
- Organizations can become Institutions (formalization). Institutions can house multiple Organizations.
- The FBI is an Organization housed within the DOJ Institution. A union local is an Organization housed within a labor federation Institution.

**3. OODA Loop as Organizational Metabolism**
Each Organization has an OODA profile determining how many actions it gets per turn and how fast it cycles through Observe → Orient → Decide → Act. This is the internal clock of organizational agency. Trade-offs: speed vs coherence, autonomy vs coordination, democracy vs reaction time.

**4. Organizations as Named Subgraphs**
An Organization is NOT a separate node type added to the graph. It is a VIEW over the main graph — a set of member nodes (drawn from SocialClass blocks) connected by SOLIDARITY or COMMAND edges, with institutional attributes (budget, legal standing, surveillance capacity) attached to the subgraph as a whole.

---

## Phase 1: Organization Base Model

### Spec ID: `020-organization-base-model`

### Prompt:

```
Create a specification for the Organization Base Model.

CONTEXT:
- Organizations are the ONLY agents in Babylon. Everything else is substrate.
- Existing codebase has: OrganizationComponent (cohesion, cadre_level),
  faction.schema.json, institution.schema.json, RevolutionaryFinance model
- These existing pieces need to be unified under a coherent Organization ABC
- Organizations are views over the NetworkX graph, not separate node types

THEORETICAL FOUNDATION:

**What Organizations DO** (minimum viable mechanics):
1. Contain members (drawn from SocialClass population blocks)
2. Have internal topology (star/hierarchy vs mesh/cell)
3. Control resources (budget, assets, legal authority)
4. Take collective action (recruit, repress, provide services, employ, organize)
5. Be infiltrated, disrupted, or allied with
6. Have class character (which class they ultimately serve — may differ from composition)

**Organization ABC**:
```python
class Organization(BaseModel):
    id: str
    name: str
    org_type: OrgType  # STATE_APPARATUS | BUSINESS | POLITICAL_FACTION | CIVIL_SOCIETY

    # Class analysis
    class_character: ClassCharacter  # BOURGEOIS | PROLETARIAN | CONTESTED
    # class_composition is computed from membership, not stored

    # Internal state
    internal_topology: TopologyType  # STAR | HIERARCHY | MESH | CELL
    cohesion: float  # [0,1] internal unity
    cadre_level: float  # [0,1] quality of leadership

    # Resources
    budget: float
    legal_standing: LegalStanding  # SOVEREIGN | CHARTERED | REGISTERED | INFORMAL | UNDERGROUND

    # Spatial
    territory_ids: list[str]  # Where this org operates (PRESENCE edges)
    headquarters_id: str | None  # Primary territory

    # State attention
    heat: float  # [0,1] surveillance pressure

    # Institutional attributes (nullable — not all orgs are institutions)
    is_institution: bool  # Has it formalized?
    institutional_persistence: float | None  # How well it survives member turnover
```

**Subtypes** (inherit Organization, add specific attributes):

StateApparatus:
- jurisdiction: national | state | county | municipal
- violence_capacity: float (monopoly on violence share)
- surveillance_capacity: float
- legal_authority: list[Authority]  # ARREST, SEARCH, WIRETAP, etc.

Business:
- sector: NAICSSector
- employment_count: int (drawn from SocialClass blocks)
- surplus_extraction_rate: float (s/v for this firm)
- revenue: float

PoliticalFaction:
- ideology: IdeologicalProfile
- is_player: bool  # The one the player controls
- relationship_to_player: RelationType  # if NPC

CivilSocietyOrg:
- service_type: ServiceType  # MUTUAL_AID | EDUCATION | RELIGIOUS | HEALTHCARE | LEGAL
- legitimacy: float  # public trust [0,1]

REQUIRED OUTPUTS:

**Models (Pydantic)**:
- Organization ABC with frozen=True
- Four subtypes: StateApparatus, Business, PoliticalFaction, CivilSocietyOrg
- OrgType, ClassCharacter, TopologyType, LegalStanding enums
- Deprecation path from existing OrganizationComponent, faction.schema.json

**Graph Integration**:
- Organization.member_node_ids: list[str] — references to SocialClass nodes
- Organization.to_subgraph(G: nx.Graph) -> nx.subgraph_view — returns the org's view
- Organization.class_composition(G: nx.Graph) -> dict[ClassPosition, float] — computed
- New edge types: RECRUITMENT (Org → SocialClass), EMPLOYMENT (Business → SocialClass),
  PRESENCE (Org → Territory), COMMAND (internal hierarchy), MEMBERSHIP (SocialClass → Org)

**Key Figures**:
- KeyFigure model: individual nodes with name, role, org_id, betweenness significance
- Key figures exist WITHIN organizational topology as high-centrality nodes
- Removal of key figure has topological consequences (component splitting, centrality shift)

CONSTRAINTS:
- Must integrate with existing NetworkXAdapter and GraphProtocol
- Must work with existing SimulationEngine system execution order
- Organization state is frozen Pydantic; mutations create new instances
- All parameters must trace to data or derive from primitives (no magic constants)

VALIDATION CRITERIA:
- Can instantiate all four subtypes for Detroit test case
- Detroit FBI field office as StateApparatus with correct jurisdiction
- Ford/GM as Business with QCEW-derived employment
- At least one PoliticalFaction (player) and one CivilSocietyOrg (church/mutual aid)
- Organization.to_subgraph() returns valid NetworkX subgraph view
- class_composition computed from actual member node class positions

DEPENDENCIES:
- Requires: SocialClass node model (exists), Territory node model (exists),
  EdgeMode enum (exists), NetworkXAdapter (exists)
- Deprecates: OrganizationComponent (migrate cohesion/cadre_level into Organization)

WHAT THIS DOES NOT INCLUDE:
- OODA loop mechanics (Phase 2)
- Attention thread / state repression AI (Phase 3)
- Bifurcation topology analysis (Phase 4)
- NPC faction AI decision-making (Phase 5)
- Player faction control interface / GUI (defer)
- Organization → Institution transition mechanics (defer)
- Coalition/united front formation (defer)
```

---

## Phase 2: OODA Loop System

### Spec ID: `021-ooda-loop-system`

### Prompt:

```
Create a specification for the OODA Loop System — organizational action resolution.

CONTEXT:
- Organizations are agents; OODA loops are their metabolism
- The simulation runs in ticks (~1 week each, 52 ticks/year)
- Within each tick, Organizations act in LAYERS based on OODA cycle time
- Faster OODA = more actions per tick, but trade-offs against coherence
- Requires: 020-organization-base-model

THEORETICAL FOUNDATION:

**OODA as Organizational Metabolism**:
Each Organization has an OODAProfile with four phases:

OBSERVE: How well do you see?
- intelligence: float [0,1] — fog of war penetration
- sensor_latency: int — ticks before info is actionable

ORIENT: How do you interpret what you see?
- ideological_coherence: float [0,1] — unified worldview
- analytical_capacity: float — ability to process complexity

DECIDE: How do you choose action?
- decision_mode: AUTOCRATIC | DELEGATE | DEMOCRATIC | CONSENSUS
- bureaucratic_depth: int — approval layers required

ACT: How do you execute?
- action_points: int — discrete actions per turn
- coordination_range: float — how far subunits synchronize
- autonomy: float [0,1] — subunit freedom

**The Trade-off Space**:
| Fast OODA | Slow OODA |
|-----------|-----------|
| Small cell, autonomous | Large bureaucracy |
| Autocratic command | Democratic deliberation |
| Loose ideology | Rigid ideology |
| Low coherence (might do wrong thing fast) | High coherence (does right thing slowly) |
| Local optimization | Global coordination |

Democratic centralism (Leninist model) is an OODA optimization: centralized decision (fast DECIDE phase) with democratic input (better ORIENT phase), disciplined execution (reliable ACT phase).

**Turn Resolution Layers**:
Within each tick, actions resolve in layers:

Layer 0 (Material base): Resource extraction, wage payment, surplus allocation
  - All Businesses act (no OODA needed — this is economic metabolism)

Layer 1 (State action): StateApparatus organizations with fastest OODA
  - Surveillance updates, repression actions, legal harassment
  - State acts FIRST because it has institutional advantage

Layer 2 (Organizational action): PoliticalFactions and CivilSocietyOrgs
  - Recruitment, organizing, service provision, actions
  - Resolved in OODA speed order (fastest first)

Layer 3 (Reaction): Consequences propagate
  - Heat changes, edge transformations, consciousness shifts

**Action Types** (what Organizations can DO):
```python
class ActionType(Enum):
    # Recruitment & organizing
    RECRUIT = "recruit"            # Draw members from SocialClass blocks
    ORGANIZE = "organize"          # Build solidarity edges (TRANSACTIONAL → SOLIDARISTIC)
    EDUCATE = "educate"            # Political education, raise consciousness

    # Resource operations
    FUNDRAISE = "fundraise"        # Increase budget
    PROVIDE_SERVICE = "provide_service"  # Mutual aid, builds legitimacy
    EMPLOY = "employ"              # Business: hire from SocialClass pools

    # Conflict
    REPRESS = "repress"            # StateApparatus: target nodes/edges
    PROTEST = "protest"            # Raise consciousness, raise heat
    STRIKE = "strike"              # Withdraw labor, damage Business surplus
    EXPROPRIATE = "expropriate"    # Direct action, high heat

    # Intelligence
    SURVEIL = "surveil"            # StateApparatus: observe org topology
    INFILTRATE = "infiltrate"     # Insert corrupted node
    COUNTER_INTEL = "counter_intel"  # Detect/remove infiltrators

    # Diplomacy
    PROPOSE_ALLIANCE = "propose_alliance"  # United front formation
    DENOUNCE = "denounce"          # Public break, edge → ANTAGONISTIC
```

**Resource Costs**:
Every action costs cadre_labor_hours (skilled organizer time) and/or
spontaneous_labor_hours (general member time), plus budget where applicable.
Cadre labor is the scarce resource — this is why leadership development matters.

REQUIRED OUTPUTS:

**Models**:
- OODAProfile (frozen Pydantic) with computed cycle_time property
- ActionType enum
- Action model: (org_id, action_type, target, resource_cost, ooda_phase)
- TurnResolution: orchestrates layer-by-layer execution within a tick

**System**:
- OODASystem that integrates with SimulationEngine.run_tick()
- Layer-by-layer resolution with correct ordering
- Resource deduction from Organization budget / labor pools
- Action effect application (modifies graph state)

**Computed Properties**:
- cycle_time: ticks to complete one full OODA loop
- actions_per_tick: floor(1 / cycle_time) — how many actions this org gets
- coherence_penalty: penalty for fast OODA (lower quality decisions)

VALIDATION CRITERIA:
- FBI field office gets Layer 1 priority (state acts first)
- Democratic org with CONSENSUS decision_mode has slower cycle_time than
  autocratic org with AUTOCRATIC decision_mode
- RECRUIT action draws from SocialClass population and creates MEMBERSHIP edge
- ORGANIZE action transforms TRANSACTIONAL → SOLIDARISTIC edge
- REPRESS action removes nodes or degrades edges
- Resource costs prevent unlimited action (budget/labor constrains)
- Detroit test: model one tick with FBI + player org + one business + one church

CONSTRAINTS:
- Must respect existing system execution order (material base first)
- Layer 0 is NOT OODA-driven — it's automatic economic metabolism
- Player org actions come from player input, not AI
- NPC org actions from AI (defer AI implementation to Phase 5, use random/rule-based stub)
- No magic constants — action costs derive from labor hour requirements

WHAT THIS DOES NOT INCLUDE:
- NPC faction AI decision logic (Phase 5 — stub with random/heuristic)
- Player UI for action selection (defer to GUI spec)
- Detailed infiltration/counter-intel mechanics (defer)
- Coalition formation rules (defer)
- Organization → Institution transition (defer)
```

---

## Phase 3: State Attention Thread System

### Spec ID: `022-attention-thread-system`

### Prompt:

```
Create a specification for the State Attention Thread System.

CONTEXT:
- The state's scarce resource is ATTENTION, not violence capacity
- State repression is modeled as a constrained optimization: where to allocate
  limited investigative bandwidth
- Attention Threads are parallel OODA loops run by StateApparatus organizations
- Requires: 020-organization-base-model, 021-ooda-loop-system
- Validated against: state-repression-research.md (COINTELPRO, Palantir, fusion centers)

THEORETICAL FOUNDATION:

**Attention as Scarce Resource**:
The FBI has ~35,000 employees. They cannot surveil everyone. The state must
ALLOCATE attention — this allocation IS the repression strategy. An FBI field
office might have 3-5 active investigations (threads) plus passive monitoring.

**AttentionThread Model**:
```python
class AttentionThread(BaseModel):
    id: str
    owner_org_id: str  # Which StateApparatus owns this thread
    target_org_id: str | None  # Which org is being investigated
    target_territory_id: str | None  # Or which territory is being monitored

    # Thread state
    phase: ThreadPhase  # DORMANT | MONITORING | ACTIVE_INVESTIGATION | DISRUPTION
    intensity: float  # [0,1] resources committed
    intel_gathered: float  # [0,1] topology knowledge of target

    # OODA for this specific thread
    ooda_state: OODAPhase  # Which phase this thread is currently in

    # Stickiness — threads resist reallocation
    stickiness: float  # [0,1] institutional inertia keeping thread on target

    # Lifecycle
    ticks_active: int
    last_action_tick: int
```

**Meta-OODA vs Thread-Level OODA**:
The state runs TWO levels of OODA simultaneously:

Meta-OODA (strategic): Which threats to allocate threads to?
  - OBSERVE: What organizations exist? What's their topology?
  - ORIENT: Which pose systemic risk? (not just which are loudest)
  - DECIDE: Allocate/reallocate threads across targets
  - ACT: Assign resources, open/close investigations

Thread-Level OODA (tactical): How to handle this specific target?
  - OBSERVE: Surveillance, infiltration, informant reports
  - ORIENT: Map target org's internal topology
  - DECIDE: What disruptive action to take?
  - ACT: Arrest, raid, legal harassment, edge poisoning

**Five Revolutionary Strategies Against Threads** (from design conversations):
1. OVERWHELM: Generate so many targets the state can't cover them all
2. DECOY: Create high-visibility low-value targets to absorb threads
3. COMPARTMENTALIZE: Cell structure limits intel_gathered ceiling
4. COUNTER-INTEL: Detect and remove infiltrators / corrupted nodes
5. LEGITIMACY SHIELD: Build enough public support that repression is politically costly

**Thread Lifecycle**:
DORMANT → (trigger event) → MONITORING → (threshold) → ACTIVE_INVESTIGATION →
(sufficient intel) → DISRUPTION → (target neutralized OR resources exhausted) →
DORMANT or REALLOCATED

**Heat Integration**:
Organization.heat and Territory.heat feed INTO thread allocation decisions:
- High heat → more likely to attract a thread
- Thread activity → increases target's heat further (positive feedback)
- But: threads cost resources, so state can't escalate everywhere

REQUIRED OUTPUTS:

**Models**:
- AttentionThread (frozen Pydantic)
- ThreadPhase enum: DORMANT, MONITORING, ACTIVE_INVESTIGATION, DISRUPTION
- ThreadAllocationStrategy: how the state distributes threads
- IntelReport: what a thread has learned about a target org's topology

**System**:
- AttentionSystem that runs during Layer 1 (state action phase)
- Thread allocation logic (meta-OODA)
- Thread-level action execution
- Integration with heat mechanics on Organizations and Territories

**Key Mechanics**:
- max_threads per StateApparatus (finite, ~3-5 for a field office)
- Thread stickiness (institutional inertia — once watching you, hard to stop)
- Intel accumulation (each tick of MONITORING reveals more of target topology)
- Disruption actions: node removal, edge degradation, legal harassment (capacity drain)

**Topology Awareness** (the state understands networks):
- Thread gathers intel_gathered ∈ [0,1] representing % of target org topology known
- At intel_gathered > threshold, state can identify high-centrality nodes
- State targets cycle-closers (β₁ reduction) and bridges (component splitting)
- This is explicitly what COINTELPRO did and what Palantir automates

VALIDATION CRITERIA:
- FBI field office with max_threads=5 cannot monitor more than 5 targets
- Thread on player org accumulates intel over time
- At sufficient intel, state identifies and targets highest-centrality member
- Thread reallocation happens when new higher-priority target emerges
- Cell topology (high β₁) limits intel_gathered ceiling vs star topology
- Detroit test: FBI allocates threads between player org, rival faction, and protest movement

CONSTRAINTS:
- State is not omniscient — intel_gathered starts at 0 and builds over time
- State is not monolithic — different agencies may have different threads on same target
  (but inter-agency coordination is imperfect — model as coordination_failure probability)
- Thread allocation should be EMERGENT from threat assessment, not scripted
- No magic constants — thread counts derived from staffing data, intel rates from
  documented investigation timelines

WHAT THIS DOES NOT INCLUDE:
- Full informant/corrupted node mechanics (defer — noted as Gap 1 in state-repression-research.md)
- Inter-agency rivalry and coordination failure details (defer)
- Judicial system as separate entity (defer)
- Player notification of surveillance (defer to GUI)
- Media/public opinion feedback on repression (defer)

REFERENCES:
- state-repression-research.md — full validation against COINTELPRO and modern capabilities
- Hoover memo 1968: topology-aware strategy is explicitly documented
- Palantir Gotham: automated link analysis with centrality highlighting
```

---

## Phase 4: Bifurcation Topology Analysis

### Spec ID: `023-bifurcation-topology`

### Prompt:

```
Create a specification for Bifurcation Topology Analysis — the George Jackson model.

CONTEXT:
- The central prediction of the simulation: does crisis produce fascism or revolution?
- Answer depends on SOLIDARITY TOPOLOGY at moment of crisis, not consciousness levels
- Named for George Jackson's insight: agitation without organization produces fascism
- Requires: 020-organization-base-model (for org topology), EdgeMode enum (exists)
- Builds on: TopologyMonitor (exists, has Sword of Damocles test)

THEORETICAL FOUNDATION:

**The George Jackson Bifurcation**:
When crisis hits (profit rate collapse, legitimacy crisis, material deprivation):
- If cross-line SOLIDARISTIC edges exist → class consciousness route → revolutionary potential
- If only within-group SOLIDARISTIC edges exist → national/racial consciousness route → fascist potential
- "Cross-line" means across the colonial divide (Core ↔ Periphery solidarity)

**The Colonial Divide**:
```python
CORE_CLASSES = {ClassPosition.BOURGEOISIE, ClassPosition.PETIT_BOURGEOISIE,
                ClassPosition.LABOR_ARISTOCRACY}
PERIPHERY_CLASSES = {ClassPosition.PROLETARIAT, ClassPosition.LUMPENPROLETARIAT}

def crosses_colonial_divide(edge, G) -> bool:
    """Does this edge connect nodes on opposite sides of the colonial divide?"""
    source_class = G.nodes[edge.source]['class_position']
    target_class = G.nodes[edge.target]['class_position']
    return (source_class in CORE_CLASSES) != (target_class in CORE_CLASSES)
```

**Bifurcation Tendency**:
Compute from topology of SOLIDARISTIC edges:
- Count cross-line solidaristic edges vs within-line solidaristic edges
- Count cross-line ANTAGONISTIC edges (hostility across divide)
- Ratio determines bifurcation tendency

```python
def bifurcation_tendency(G) -> str:
    solidarity_edges = [(u,v) for u,v,d in G.edges(data=True)
                        if d['mode'] == EdgeMode.SOLIDARISTIC]
    cross_line = [e for e in solidarity_edges if crosses_colonial_divide(e, G)]
    within_line = [e for e in solidarity_edges if not crosses_colonial_divide(e, G)]

    if len(cross_line) > len(within_line) * threshold:
        return "revolutionary"
    else:
        return "fascist"
```

**Material Constraints on Solidarity**:
Solidarity formation is constrained by material conditions:
- wage_gap_ratio > 10 → solidarity_ceiling = 0.3 (very hard to build cross-line solidarity)
- wage_gap_ratio < 2 → solidarity_ceiling = 0.9 (material similarity enables solidarity)
- geographic_proximity required (can't build solidarity with people you never encounter)
- shared_exploitation_source raises ceiling +0.2 (common enemy helps)

These are CEILINGS, not determinants. Organizing effort is still required.

**Betti Number Analysis**:
- β₀: Connected components in solidarity subgraph (fragmentation)
- β₁: Independent cycles (routing redundancy — resilience)
- β₂: 2D voids in clique complex (hollow shells — organizations that coordinate
       at boundaries but lack full interpenetration)

Ideal revolutionary topology: P(t) = 1 + kt (high β₁, zero β₂)
- Many redundant paths (mesh, not star)
- No hollow shells (genuine interpenetration, not just elite coordination)

**Sword of Damocles Extension**:
Existing TopologyMonitor has the 20% purge test. Extend with:
- Targeted purge: remove highest-betweenness nodes (not random)
- What's the minimum % of targeted removals that fragments the network?
- Star topology: ~5% (remove hub). Mesh: ~40-60%. Cell: varies by compartmentalization.

**Antagonism Direction**:
```python
def antagonism_direction(edge, G) -> str:
    """Where is the anger directed?"""
    source_class = G.nodes[edge.source]['class_position']
    target_class = G.nodes[edge.target]['class_position']

    if crosses_colonial_divide(edge, G):
        if source_class in PERIPHERY_CLASSES:
            return "upward"      # Revolutionary direction
        else:
            return "downward"    # Repressive direction
    else:
        return "lateral"         # Scapegoating / horizontal hostility
```

Fascist tendency = lateral antagonism dominates (blame immigrants, not capital)
Revolutionary tendency = upward antagonism + cross-line solidarity

REQUIRED OUTPUTS:

**Analysis Functions**:
- crosses_colonial_divide(edge, G) -> bool
- antagonism_direction(edge, G) -> str
- bifurcation_tendency(G) -> BifurcationResult
- solidarity_ceiling(node_a, node_b, G) -> float

**Topology Metrics**:
- betti_0(G, subgraph_filter) -> int  # Connected components
- betti_1(G, subgraph_filter) -> int  # Independent cycles (via nx.cycle_basis or E-V+β₀)
- resilience_score(G, purge_strategy) -> float  # Survival under targeted purge

**BifurcationResult Model**:
```python
class BifurcationResult(BaseModel):
    tendency: Literal["revolutionary", "fascist", "indeterminate"]
    cross_line_solidarity_count: int
    within_line_solidarity_count: int
    lateral_antagonism_count: int
    upward_antagonism_count: int
    beta_0: int  # Components
    beta_1: int  # Cycles
    resilience_under_targeted_purge: float
    critical_nodes: list[str]  # Highest-betweenness nodes whose removal matters most
```

**Integration**:
- BifurcationSystem that runs after all organizational actions resolve
- Computes BifurcationResult each tick
- Stores in simulation history for time series analysis
- This is the OUTCOME VARIABLE of the simulation — the thing we're predicting

VALIDATION CRITERIA:
- Pure within-group solidarity → tendency = "fascist"
- Cross-line solidarity exceeding threshold → tendency = "revolutionary"
- Star topology yields low resilience; mesh yields high resilience
- Removing highest-betweenness node from star topology fragments network
- Removing highest-betweenness node from mesh topology does NOT fragment
- β₁ = 0 for tree/star topologies; β₁ > 0 for mesh topologies
- Detroit test: Wayne County (periphery) ↔ Oakland County (core) edge
  should predict bifurcation tendency based on solidarity vs antagonism

CONSTRAINTS:
- Must work with existing EdgeMode enum (EXTRACTIVE/TRANSACTIONAL/SOLIDARISTIC/ANTAGONISTIC)
- β₂ computation requires clique complex — use giotto-tda or ripser as optional dependency
  (core spec uses β₀ and β₁ only, computable with pure NetworkX)
- No magic threshold for bifurcation — derive from historical cases or make configurable
  with documented rationale
- Colonial divide definition must match wealth-based class position from spec 014

WHAT THIS DOES NOT INCLUDE:
- Persistent homology (Phase 2 of topology analysis — defer)
- Crisis trigger mechanics (when does bifurcation actually fire?)
- Post-bifurcation dynamics (what happens after fascist/revolutionary outcome?)
- Spatial dimension of bifurcation (which territories tip which way?)
- GUI visualization of bifurcation surface (defer to GUI spec)

REFERENCES:
- solidarity_edge_formalization.md — EdgeMode theory and degradation mechanics
- state-repression-research.md — Sword of Damocles validation
- George Jackson, "Blood in My Eye" — the theoretical source
```

---

## Phase 5: Organization-Territory Integration

### Spec ID: `024-org-territory-integration`

### Prompt:

```
Create a specification for Organization-Territory Integration — spatial dynamics of organizational action.

CONTEXT:
- Organizations operate IN territories (PRESENCE edges)
- Territory has H3 hex grid, sector type, heat level, occupant stack
- Organizations conducting HIGH_PROFILE operations raise territory heat
- Heat attracts state attention threads
- The visibility/recruitment trade-off: you can't organize in the dark, but
  daylight brings repression
- Requires: 020-organization-base-model, 021-ooda-loop-system, 022-attention-thread-system

THEORETICAL FOUNDATION:

**Organizations Occupy Territories**:
Every Organization has presence in one or more territories:
- PRESENCE edge: Org → Territory (where they operate)
- headquarters_id: primary territory
- Operational profile per territory: HIGH_PROFILE (visible, recruits) vs LOW_PROFILE (safe, slow)

**Heat Mechanics**:
Territory heat accumulates from organizational activity:
- HIGH_PROFILE actions in a territory raise heat
- State attention threads monitoring a territory raise heat further
- Heat decays over time without new activity (people forget)
- Heat above threshold triggers state response (raids, arrests, increased surveillance)

**Eviction Pipeline**:
When territory heat exceeds threshold:
- Occupants displaced to adjacent territories (if available)
- Organizations disrupted spatially (lose PRESENCE edges)
- Carceral geography routes: reservation → penal colony → concentration camp
  (based on displacement_priority_mode: EXTRACTION | CONTAINMENT | ELIMINATION)

**Fractal Scale**:
Organizations operate at different spatial scales:
- Tenant association: block level
- Union local: industrial district
- Party chapter: city level
- Federal agency: national with local field offices

Territory nesting (subLocations) means the same mechanics compute at appropriate scale.

**Recruitment Geography**:
RECRUIT action requires PRESENCE in a territory that contains the target SocialClass population.
Can't recruit people you have no spatial access to.

REQUIRED OUTPUTS:

**Models**:
- PresenceEdge: (org_id, territory_id, operational_profile, duration)
- TerritoryHeatEvent: records what caused heat change
- EvictionEvent: records displacement

**Mechanics**:
- heat_accumulation(territory, actions_this_tick) -> float
- heat_decay(territory, ticks_since_last_activity) -> float
- eviction_check(territory) -> list[EvictionEvent] | None
- recruitment_eligibility(org, territory, target_class) -> bool

**Integration with Attention Threads**:
- High territory heat → higher probability of thread allocation
- Thread MONITORING a territory → heat increases for all orgs present
- Thread DISRUPTION action in territory → eviction cascade

VALIDATION CRITERIA:
- Org with HIGH_PROFILE presence accumulates heat faster than LOW_PROFILE
- Heat above threshold triggers eviction check
- Org cannot RECRUIT in territory where it has no PRESENCE
- FBI thread monitoring a territory increases heat for all present orgs
- Adjacent territory absorbs displaced orgs (ADJACENCY edges in H3 grid)
- Detroit test: organizing in Wayne County (high heat area) vs Oakland County (lower heat)

CONSTRAINTS:
- H3 resolution for Detroit: use resolution 7 (~5km hex) for initial implementation
- Heat is a float [0,1] not a counter (normalized)
- Eviction is deterministic given heat threshold, not probabilistic
- Territory adjacency from H3 k-ring, not arbitrary

WHAT THIS DOES NOT INCLUDE:
- Gentrification mechanics (territory transformation over time — defer)
- Infrastructure targeting (power plants, water systems — defer)
- Climate displacement effects (defer)
- Full carceral geography pipeline (defer — just model displacement for now)
- Territory control/contestation (defer)
```

---

## Phase 6: NPC Faction AI (Stub)

### Spec ID: `025-npc-faction-ai-stub`

### Prompt:

```
Create a specification for NPC Faction AI — stub implementation for non-player organizations.

CONTEXT:
- Player controls one PoliticalFaction. All other organizations need AI.
- This is a STUB — rule-based heuristics, not sophisticated AI
- Purpose: make the simulation runnable end-to-end with all org types acting
- Requires: 020 through 024

THEORETICAL FOUNDATION:

NPC organizations follow class interest as default behavior:
- StateApparatus: protect existing order, allocate attention threads to threats
- Business: maximize surplus extraction, resist labor organizing
- CivilSocietyOrg: provide services, maintain legitimacy, avoid heat
- Rival PoliticalFaction: recruit, organize, compete with player for base

**Decision Heuristic per Type**:

StateApparatus:
1. Allocate threads to highest-heat organizations
2. If thread intel_gathered > 0.7 on any target, initiate DISRUPTION
3. If no active threats, MONITOR territories with recent activity

Business:
1. EMPLOY from cheapest available SocialClass pool
2. If strike active, attempt to break it (REPRESS via legal channels)
3. Otherwise maintain operations (automatic surplus extraction in Layer 0)

CivilSocietyOrg:
1. PROVIDE_SERVICE in territories where they have PRESENCE
2. If heat > 0.5 in their territory, shift to LOW_PROFILE
3. RECRUIT when below capacity

Rival PoliticalFaction:
1. RECRUIT in territories where player is weak
2. ORGANIZE existing members (build solidarity edges)
3. If player proposes alliance and ideological overlap > threshold, consider accepting
4. If threatened by state, prioritize COUNTER_INTEL

REQUIRED OUTPUTS:

**System**:
- NPCDecisionSystem that runs during OODA resolution phases
- Per-org-type decision function returning list[Action]
- Simple priority queue: most urgent action first, constrained by action_points

**Interface**:
- NPCDecisionStrategy protocol (for future replacement with better AI)
- Concrete implementations: StateAI, BusinessAI, CivilSocietyAI, RivalFactionAI

VALIDATION CRITERIA:
- Simulation runs for 52 ticks (1 year) without crashing
- FBI allocates threads to player org when player heat > threshold
- Business extracts surplus each tick
- Church provides services in its territory
- Rival faction recruits and grows over time
- All action costs properly deducted from budgets

CONSTRAINTS:
- STUB quality — optimize for "runs correctly" not "plays well"
- Deterministic given same RNG seed (for reproducibility)
- No external AI calls (no LLM in the loop for NPC decisions)
- Strategy pattern allows hot-swapping AI implementations later

WHAT THIS DOES NOT INCLUDE:
- Sophisticated threat assessment (just use heat as proxy)
- Coalition negotiation logic (always accept/reject based on simple threshold)
- Learning from past actions
- Adaptation to player strategy
- Personality/doctrine differences between same-type NPCs
```

---

## Dependency Graph

```
020-organization-base-model
    ├── 021-ooda-loop-system
    │   ├── 022-attention-thread-system
    │   │   └── 024-org-territory-integration
    │   └── 025-npc-faction-ai-stub
    └── 023-bifurcation-topology
```

Recommended implementation order: 020 → 021 → 023 → 022 → 024 → 025

Rationale: 023 (bifurcation) is the OUTCOME VARIABLE — you want to validate
the topology analysis early, even before the full action system exists.
022 and 024 are the most complex and benefit from having the simpler pieces stable.
025 is last because it's a stub that ties everything together for end-to-end testing.
