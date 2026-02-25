# Organization & Topology: Spec-Kit Prompts (v2)

**Purpose**: Prompts for Claude Code + spec-kit to generate specifications for the Organization system
**Usage**: Feed each prompt to `/speckit.specify` sequentially; each phase builds on the prior
**Context**: These assume existing codebase has SocialClass nodes, Territory nodes, EdgeMode enum, NetworkXAdapter, TopologyMonitor, and SimulationEngine with system execution order
**Key Insight**: In Babylon, Organizations ARE the agents. SocialClass and Territory are substrate.
**Revision**: Incorporates Malcolm K. Sparrow's network vulnerability analysis (1991, 1993) and hypergraph/community layer via XGI

---

## Architectural Foundation

The Organization system rests on six key insights from prior design work:

**1. Two-Layer Architecture: Substrate + Agents**
```
SUBSTRATE LAYER (no agency)
├── SocialClass blocks (demographic reservoirs with population, wealth, consciousness)
├── Territory (spatial grid, H3 hexagons, can be occupied/contested)
└── Community (hyperedge connecting multiple agents via shared identity/condition)

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

**5. Sparrow's Network Vulnerability Framework**
Malcolm K. Sparrow (1991, 1993) formalized how law enforcement operationalizes graph theory for network disruption. His framework is mathematically symmetric: the same algorithms serve both attacker (state targeting) and defender (movement hardening). Babylon implements BOTH sides:

- **State side**: AttentionThread system uses Sparrow's targeting methodology
  - Six centrality types mapped to operational significance
  - Automorphic equivalence classes identify irreplaceable vs fungible roles
  - Minimal cutset analysis finds structural vulnerabilities
  - Template matching (Big Floyd) identifies organizational patterns

- **Movement side**: Sword of Damocles test runs Sparrow's algorithms defensively
  - "Run Big Floyd against ourselves" — identify what the state would target
  - Equivalence class size determines replaceability (large classes = fungible = resilient)
  - β₁ cycles provide routing redundancy that defeats centrality-based targeting
  - AVLF graph (Adelson-Velskii et al. 1969) proves analysis-resistant topology is mathematically possible

- **The observation gap**: G_observed ≠ G_actual
  - State sees: phone metadata, financial transactions, social media, location data
  - State misses: face-to-face trust, dormant strong ties, consciousness/commitment, cash economies
  - Systematic distortions: edge type conflation, temporal flattening, denominator explosion, informant incentive distortion
  - This gap is where operational security lives

**6. Communities as Hyperedges**
Communities (DISABLED, QUEER, NEW_AFRIKAN, UNDOCUMENTED, etc.) are NOT pairwise relationships — they're n-ary relations connecting all agents who share that membership. This is a hyperedge from hypergraph theory, implemented via XGI library with bipartite NetworkX as fallback.

Communities serve as:
- Solidarity potential modifiers (shared community membership raises solidarity ceiling)
- Reproduction cost modifiers (community infrastructure offsets higher costs)
- Repression targets (state can attack community infrastructure, raising costs for all members)
- Cross-class bridges (a DISABLED community hyperedge may span bourgeois and proletarian members)

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
- intel_methodology: IntelMethodology  # What Sparrow-style analysis they can perform
  (See Sparrow integration notes below)

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

**Sparrow Integration (StateApparatus-specific)**:

StateApparatus organizations have IntelMethodology determining what network analysis
they can perform on targets. This is grounded in Sparrow 1991's mapping of graph
concepts to operational law enforcement objectives:

```python
class IntelMethodology(BaseModel):
    """What network analysis a StateApparatus can perform.

    Based on Sparrow 1991 taxonomy. Capabilities are NOT binary —
    they depend on resources, training, and technical infrastructure.
    """
    # Can compute target centralities? (Palantir: yes. Small-town PD: no)
    centrality_analysis: bool
    # Can identify structurally equivalent roles? (Sparrow 1993 algorithm)
    equivalence_analysis: bool
    # Can perform template matching? (Big Floyd: subgraph pattern recognition)
    template_matching: bool
    # Can do temporal pattern analysis? (Pattern of life monitoring)
    temporal_analysis: bool
    # What % of target graph is observable? (bounded by data sources)
    observation_ceiling: float  # [0,1] — even Palantir can't see everything
```

FBI field office: all True, observation_ceiling ~0.4
Local PD: centrality only, observation_ceiling ~0.2
Fusion center: centrality + temporal, observation_ceiling ~0.5 (data integration advantage)

REQUIRED OUTPUTS:

**Models (Pydantic)**:
- Organization ABC with frozen=True
- Four subtypes: StateApparatus, Business, PoliticalFaction, CivilSocietyOrg
- OrgType, ClassCharacter, TopologyType, LegalStanding enums
- IntelMethodology model for StateApparatus
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
- Sparrow's equivalence class analysis: key figures in SINGLETON equivalence classes
  are irreplaceable; those in large classes are fungible (their role can be filled)

CONSTRAINTS:
- Must integrate with existing NetworkXAdapter and GraphProtocol
- Must work with existing SimulationEngine system execution order
- Organization state is frozen Pydantic; mutations create new instances
- All parameters must trace to data or derive from primitives (no magic constants)

VALIDATION CRITERIA:
- Can instantiate all four subtypes for Detroit test case
- Detroit FBI field office as StateApparatus with correct jurisdiction and intel methodology
- Ford/GM as Business with QCEW-derived employment
- At least one PoliticalFaction (player) and one CivilSocietyOrg (church/mutual aid)
- Organization.to_subgraph() returns valid NetworkX subgraph view
- class_composition computed from actual member node class positions
- IntelMethodology correctly limits what StateApparatus can observe about targets

DEPENDENCIES:
- Requires: SocialClass node model (exists), Territory node model (exists),
  EdgeMode enum (exists), NetworkXAdapter (exists)
- Deprecates: OrganizationComponent (migrate cohesion/cadre_level into Organization)

WHAT THIS DOES NOT INCLUDE:
- OODA loop mechanics (Phase 2)
- Community/hyperedge layer (Phase 3)
- Attention thread / state repression AI (Phase 4)
- Bifurcation topology analysis (Phase 5)
- NPC faction AI decision-making (Phase 6)
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
  - Community hyperedge effects propagate (Phase 3)

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

    # Intelligence (grounded in Sparrow 1991 methodology)
    SURVEIL = "surveil"            # StateApparatus: observe target org topology
    INFILTRATE = "infiltrate"     # Insert corrupted node into target org
    COUNTER_INTEL = "counter_intel"  # Detect/remove infiltrators
    MAP_NETWORK = "map_network"    # Sparrow-style: compute centralities, equivalences on known topology

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
- MAP_NETWORK action computes Sparrow-style analysis on known portion of target graph
- Resource costs prevent unlimited action (budget/labor constrains)
- Detroit test: model one tick with FBI + player org + one business + one church

CONSTRAINTS:
- Must respect existing system execution order (material base first)
- Layer 0 is NOT OODA-driven — it's automatic economic metabolism
- Player org actions come from player input, not AI
- NPC org actions from AI (defer AI implementation to Phase 6, use random/rule-based stub)
- No magic constants — action costs derive from labor hour requirements

WHAT THIS DOES NOT INCLUDE:
- NPC faction AI decision logic (Phase 6 — stub with random/heuristic)
- Player UI for action selection (defer to GUI spec)
- Detailed infiltration/counter-intel mechanics (defer)
- Coalition formation rules (defer)
- Organization → Institution transition (defer)
```

---

## Phase 3: Community Hyperedge Layer

### Spec ID: `022-community-hyperedge-layer`

### Prompt:

```
Create a specification for the Community Hyperedge Layer — identity-based groupings
that cross organizational and class boundaries.

CONTEXT:
- Communities (DISABLED, QUEER, NEW_AFRIKAN, UNDOCUMENTED, etc.) are n-ary
  relations connecting all agents who share a condition/identity
- In hypergraph theory, these are HYPEREDGES — one edge connecting multiple nodes
- Computational layer: XGI library, with bipartite NetworkX as fallback
- Communities are SUBSTRATE (like SocialClass and Territory), not agents
- Requires: 020-organization-base-model

THEORETICAL FOUNDATION:

**Why Communities Are Not Organizations**:
You don't "join" the DISABLED community — material conditions place you there.
Communities are pre-political groupings that organizations recruit FROM and
organize WITHIN. A community has no OODA loop, no budget, no leadership.
But it does have:
- Infrastructure (mutual aid networks, support services, gathering spaces)
- Shared reproduction costs (higher for marginalized communities)
- Solidarity potential (shared experience creates basis for solidarity)
- Vulnerability to collective repression (state targets communities, not just individuals)

**Community as Hyperedge**:
A standard graph edge connects two nodes. A hyperedge connects N nodes simultaneously.
"DISABLED" isn't a pairwise relationship — it's a set containing all agents with that
condition. Modeling it as a hyperedge means "these agents are all connected by virtue
of shared disability status" without needing N² pairwise edges.

```python
# XGI implementation
import xgi

H = xgi.Hypergraph()
H.add_nodes_from(["agent_1", "agent_2", "agent_3", "agent_4"])

# Communities as hyperedges
H.add_edge(["agent_1", "agent_2", "agent_3"], id="TRANS")
H.add_edge(["agent_1", "agent_4"], id="DISABLED")
H.add_edge(["agent_2", "agent_3", "agent_4"], id="NEW_AFRIKAN")

# Query shared communities
shared = H.nodes.memberships("agent_1") & H.nodes.memberships("agent_2")
# → {"TRANS"} — they share TRANS community
```

**CommunityType Enum**:
```python
class CommunityType(Enum):
    # Identity communities (material conditions of existence)
    NEW_AFRIKAN = "new_afrikan"
    FIRST_NATIONS = "first_nations"
    CHICANO = "chicano"
    QUEER = "queer"
    TRANS = "trans"
    DISABLED = "disabled"
    UNDOCUMENTED = "undocumented"
    ELDER = "elder"
    YOUTH = "youth"

    # Occupational communities (shared labor conditions)
    INCARCERATED = "incarcerated"         # Current or formerly incarcerated
    SERVICE_WORKER = "service_worker"
    CARE_WORKER = "care_worker"
    SEX_WORKER = "sex_worker"

    # Geographic communities (neighborhood/place-based)
    # These are Territory-bound; implemented via PRESENCE + Territory
```

**Community State** (attributes on the hyperedge):
```python
class CommunityState(BaseModel):
    community_type: CommunityType

    # Infrastructure
    infrastructure: float  # [0,1] mutual aid capacity, support networks
    gathering_spaces: int  # physical locations (territory-bound)

    # Material effects
    reproduction_cost_modifier: float  # >1.0 means higher costs (e.g., disability)
    infrastructure_offset: float  # infrastructure reduces effective cost

    # Visibility and vulnerability
    heat: float  # [0,1] state attention on this community as a whole
    visibility: float  # [0,1] how legible this community is to surveillance

    # Solidarity mechanics
    internal_solidarity_floor: float  # Minimum solidarity between members
    cross_class_bridge: bool  # Does this community span the colonial divide?
```

**How Communities Modify Simulation Dynamics**:

1. Solidarity potential between agents:
   shared_communities = len(agent_a.communities & agent_b.communities)
   solidarity_ceiling += community_bonus * shared_communities
   (Shared experience creates basis for organizing, doesn't guarantee it)

2. Reproduction costs:
   For each community an agent belongs to, apply reproduction_cost_modifier.
   Community infrastructure offsets this (mutual aid reduces individual burden).
   When state attacks community infrastructure, costs rise for ALL members.

3. Cross-class bridging:
   Some communities span the colonial divide (DISABLED includes both LA and lumpen).
   These communities create POTENTIAL for cross-line solidarity that pure class
   analysis would miss. Organizations can exploit these bridges.

4. State targeting:
   State can target a community's INFRASTRUCTURE rather than individual members.
   This is cheaper than node-by-node targeting and affects everyone in the hyperedge.
   Example: defunding trans healthcare = attacking TRANS community infrastructure.

**Bipartite Fallback** (if XGI adds unwanted complexity):
Model communities as nodes in main NetworkX graph with MEMBERSHIP edges:

```
Agent nodes ←—MEMBERSHIP—→ Community nodes
A1 ——→ DISABLED
A1 ——→ QUEER
A2 ——→ DISABLED
A3 ——→ QUEER
A3 ——→ UNDOCUMENTED
```

Same semantics, no new dependency. XGI adds algorithmic power (hypergraph
centrality, higher-order clustering) but bipartite gives you the data model.

REQUIRED OUTPUTS:

**Models**:
- CommunityType enum
- CommunityState (frozen Pydantic)
- CommunityIndex: reverse lookup from community → member agent IDs (O(1) queries)

**Hypergraph Integration**:
- build_community_hypergraph(agents) -> xgi.Hypergraph
- Conversion functions: worldstate_to_xgi() / xgi_to_worldstate()
- Fallback: bipartite representation in main NetworkX graph

**Mechanics**:
- solidarity_potential_modifier(agent_a, agent_b) -> float (based on shared communities)
- effective_reproduction_cost(agent, communities) -> float (modified by infrastructure)
- community_infrastructure_attack(community_type, damage) -> list of affected agents
- cross_class_bridges(H: xgi.Hypergraph) -> list[CommunityType] (which communities span divide)

**Persistence**:
- Community membership stored in existing SQLite schema (membership table)
- CommunityState stored as JSON in communities table
- XGI hypergraph rebuilt from SQLite on simulation start (same pattern as NetworkX)

VALIDATION CRITERIA:
- Agent with DISABLED + QUEER membership has higher solidarity potential with
  another DISABLED + QUEER agent than with an agent sharing zero communities
- Attacking TRANS infrastructure raises reproduction costs for all TRANS agents
- DISABLED community identified as cross_class_bridge (spans LA and lumpen members)
- Community membership survives serialization roundtrip (SQLite → XGI → SQLite)
- Detroit test: model at least 3 community types across Wayne/Oakland class blocks

CONSTRAINTS:
- XGI is optional dependency — bipartite fallback must work without it
- Communities are substrate, NOT agents — no OODA, no actions, no decisions
- Community membership is MATERIAL (you don't choose to be disabled), not voluntary
  (exception: some communities like religious affiliation have voluntary component)
- No magic constants for reproduction cost modifiers — derive from literature or
  flag as SYNTHETIC with documented rationale

WHAT THIS DOES NOT INCLUDE:
- Inter-community alliance dynamics (defer)
- Community-based organizations as distinct from community-as-substrate (those are
  CivilSocietyOrg subtypes, covered in Phase 1)
- Nation vs community distinction (defer — treat nations as CommunityType for now)
- Historical community formation/dissolution (defer)
```

---

## Phase 4: State Attention Thread System (Sparrow-Grounded)

### Spec ID: `023-attention-thread-system`

### Prompt:

```
Create a specification for the State Attention Thread System, grounded in
Malcolm K. Sparrow's network vulnerability analysis framework.

CONTEXT:
- The state's scarce resource is ATTENTION, not violence capacity
- Sparrow (1991) formalized how law enforcement maps graph concepts to
  operational disruption objectives. This spec operationalizes his framework.
- Sparrow (1993) provides a linear-time algorithm for computing automorphic
  equivalence classes — determining which nodes are structurally interchangeable
- Attention Threads are parallel OODA loops run by StateApparatus organizations
- Requires: 020-organization-base-model, 021-ooda-loop-system
- Validated against: state-repression-research.md (COINTELPRO, Palantir, fusion centers)

THEORETICAL FOUNDATION:

**Sparrow's Operational Graph Analysis** (1991):

Sparrow maps six centrality measures to law enforcement objectives:

| Centrality Type | Operational Meaning | Babylon Use |
|----------------|---------------------|-------------|
| Degree | "Who is most connected?" | Find recruitment hubs |
| Betweenness | "Who bridges subgroups?" | Target coalition-builders (Hampton) |
| Closeness | "Who can reach everyone fastest?" | Identify information propagators |
| Eigenvector | "Who is connected to important people?" | Find power brokers |
| Flow betweenness | "Who controls resource flows?" | Target logistics/finance |
| Information centrality | "Who holds irreplaceable knowledge?" | Target cadre |

And three equivalence notions:

| Equivalence | Meaning | Targeting Implication |
|------------|---------|---------------------|
| Structural | Identical connections | Truly interchangeable — targeting one is pointless |
| Automorphic | Same neighborhood structure | Functionally interchangeable — target all or none |
| Regular | Same role pattern | Same function, different connections — target the role |

**Sparrow's Key Insight**: Equivalence class SIZE determines targeting value.
- Singleton class = irreplaceable role → high-value target
- Large class = fungible role → targeting individuals is futile

**The Numerical Signatures Algorithm** (Sparrow 1993):
Computes automorphic equivalence in O(edges) time:
1. Each node broadcasts its degree
2. Nodes combine incoming signals: S = ∏(π + incoming)
3. Retransmit combined signature
4. Iterate — identical signatures = identical structural position

The π-based multiplication exploits transcendentality: identical signatures
can ONLY arise from identical incoming signal sets.

SPAN refinement tracks which nodes contributed to a signature (reachable neighborhoods).
Directed graph extension handles asymmetric edges (EXPLOITATION is directional).
Multiplex extension handles multiple edge types.

**The Observation Gap** (G_observed ≠ G_actual):

The state NEVER sees the complete graph. What it observes depends on:
- Data sources: phone metadata, financial records, social media, location data,
  informant reports, public records
- Each source reveals SOME edges but not others
- Systematic distortions:
  - Edge type conflation (can't distinguish solidarity from incidental contact)
  - Temporal flattening (old dead ties look like current ties)
  - Denominator explosion (too many connections to act on)
  - Informant incentive distortion (paid sources exaggerate)
  - Cash economy invisibility (informal transactions untracked)
  - Face-to-face blindness (in-person meetings leave no metadata)

```python
class ObservationModel(BaseModel):
    """What portion of the actual graph a StateApparatus can see.

    G_observed is always a SUBSET of G_actual, and a DISTORTED one.
    """
    # What edges are visible by data source?
    phone_metadata: bool      # Reveals communication edges
    financial_records: bool   # Reveals economic edges
    social_media: bool        # Reveals public association edges
    location_data: bool       # Reveals co-location (noisy)
    informant_reports: bool   # Reveals internal edges (distorted by incentives)
    public_records: bool      # Reveals institutional affiliations

    # Derived observation ceiling
    @computed_field
    def observation_ceiling(self) -> float:
        """Maximum fraction of actual graph observable.

        Even with ALL sources, ceiling < 1.0 because face-to-face,
        cash transactions, and pre-digital ties are invisible.
        """
        sources = [self.phone_metadata, self.financial_records,
                   self.social_media, self.location_data,
                   self.informant_reports, self.public_records]
        # Each source adds diminishing visibility
        base = sum(0.15 if s else 0 for s in sources[:3])  # Major sources
        minor = sum(0.08 if s else 0 for s in sources[3:])  # Minor sources
        return min(base + minor, 0.65)  # Hard ceiling — face-to-face is invisible
```

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

    # Intelligence state — what has this thread learned?
    observed_subgraph: set[str]  # Node IDs visible to this thread
    observed_edges: set[tuple[str,str]]  # Edge pairs visible
    intel_completeness: float  # [0,1] = |observed| / |actual| for target org

    # Sparrow analysis results (computed when intel_completeness > threshold)
    known_centralities: dict[str, float] | None  # Betweenness of observed nodes
    known_equivalence_classes: list[set[str]] | None  # Sparrow 1993 algorithm output
    identified_singletons: list[str] | None  # Irreplaceable roles (high-value targets)
    known_cutsets: list[set[str]] | None  # Minimal node sets whose removal fragments

    # OODA for this specific thread
    ooda_state: OODAPhase

    # Stickiness — threads resist reallocation
    stickiness: float  # [0,1] institutional inertia
    ticks_active: int
```

**Meta-OODA vs Thread-Level OODA**:
The state runs TWO levels of OODA simultaneously:

Meta-OODA (strategic): Which threats to allocate threads to?
  - OBSERVE: What organizations exist? What's their heat level?
  - ORIENT: Which pose systemic risk? (not just which are loudest)
  - DECIDE: Allocate/reallocate threads across targets
  - ACT: Assign resources, open/close investigations

Thread-Level OODA (tactical, per-target):
  - OBSERVE: Surveillance → expand observed_subgraph
  - ORIENT: Run Sparrow analysis on observed portion
    - Compute centralities on G_observed
    - Compute equivalence classes (Sparrow 1993 algorithm)
    - Identify singletons (irreplaceable) and cutsets (structural vulnerabilities)
  - DECIDE: Choose disruption strategy based on analysis
    - If singleton identified → target for removal (arrest, assassination, legal harassment)
    - If cutset found → sever those edges (manufacture internal conflict, isolate)
    - If all classes large → shift to capacity degradation (attrition, not surgery)
  - ACT: Execute disruption action

**The Five Revolutionary Counter-Strategies Against Threads**:
1. OVERWHELM: Generate so many targets threads can't cover them all
2. DECOY: Create high-visibility low-value targets to absorb threads
3. COMPARTMENTALIZE: Cell structure limits observation ceiling per thread
4. COUNTER-INTEL: Detect and remove infiltrators / corrupted nodes
5. LEGITIMACY SHIELD: Build enough public support that repression is politically costly

**AVLF-Inspired Network Hardening** (Adelson-Velskii et al. 1969):
The AVLF graph proves analysis-resistant topology exists: 26 nodes, each degree 10,
where every node's local neighborhood looks identical — yet there ARE two distinct
structural roles that local algorithms cannot distinguish.

While real solidarity networks won't be AVLF graphs, the principles inform
defensive topology design:
- Maximize equivalence class sizes (make roles fungible)
- Distribute centrality (no hubs)
- Build redundant cycles (β₁ > 0)
- Maintain high local density within cells

REQUIRED OUTPUTS:

**Models**:
- AttentionThread (frozen Pydantic)
- ThreadPhase enum: DORMANT, MONITORING, ACTIVE_INVESTIGATION, DISRUPTION
- ObservationModel (what data sources available)
- SparrowAnalysis: results of running network vulnerability analysis on observed graph
- ThreadAllocationStrategy: how the state distributes threads

**Systems**:
- AttentionSystem that runs during Layer 1 (state action phase)
- Thread allocation logic (meta-OODA)
- Per-thread intelligence gathering (expand observed_subgraph each tick)
- Per-thread Sparrow analysis (run when intel_completeness crosses thresholds)
- Per-thread disruption action selection and execution

**Sparrow Algorithm Implementation**:
- compute_numerical_signatures(G, iterations) -> dict[node, signature]
  (Sparrow 1993 π-product algorithm, O(edges) per iteration)
- compute_equivalence_classes(signatures) -> list[set[node]]
- find_singletons(classes) -> list[node]  # Irreplaceable roles
- find_minimal_cutsets(G, max_size) -> list[set[node]]  # Structural vulnerabilities
- resilience_report(G) -> ResilienceReport  # "Run Big Floyd against ourselves"

**Sword of Damocles Integration**:
The existing TopologyMonitor's Sword of Damocles test should use Sparrow's
actual algorithms:

```python
def sword_of_damocles(G: nx.Graph) -> ResilienceReport:
    """Run the state's own analysis against ourselves."""
    betweenness = nx.betweenness_centrality(G)
    high_value = [n for n, b in betweenness.items() if b > threshold]

    equiv_classes = compute_equivalence_classes(
        compute_numerical_signatures(G, iterations=3)
    )
    irreplaceable = [c for c in equiv_classes if len(c) == 1]

    cutsets = find_minimal_cutsets(G, max_size=3)

    # Simulate targeted removal and measure fragmentation
    fragmentation_curve = []
    for strategy in [betweenness_targeting, singleton_targeting, cutset_targeting]:
        G_damaged = G.copy()
        targets = strategy(G_damaged)
        G_damaged.remove_nodes_from(targets)
        frag = 1 - len(max(nx.connected_components(G_damaged))) / len(G)
        fragmentation_curve.append((strategy.__name__, frag))

    return ResilienceReport(
        high_centrality_nodes=high_value,
        irreplaceable_roles=irreplaceable,
        critical_cutsets=cutsets,
        fragmentation_curves=fragmentation_curve,
        equivalence_class_distribution=class_size_histogram
    )
```

VALIDATION CRITERIA:
- FBI field office with max_threads=5 cannot monitor more than 5 targets
- Thread on player org accumulates observed_subgraph over time
- At sufficient intel_completeness, Sparrow analysis correctly identifies highest-centrality member
- Sparrow equivalence analysis on star topology: hub is singleton, spokes are one class
- Sparrow equivalence analysis on mesh topology: larger classes, fewer singletons
- Cell topology limits observation_ceiling (compartmentalization works)
- Thread reallocation happens when new higher-priority target emerges
- Detroit test: FBI allocates threads between player org, rival faction, and protest movement

CONSTRAINTS:
- State is not omniscient — intel_completeness starts at 0 and builds over time
- Sparrow analysis runs on G_observed, NOT G_actual — the state can be wrong
- State analysis is distorted by observation gap (edge type conflation, temporal flattening)
- Different agencies have different ObservationModels (FBI has phone, PD has location)
- Thread allocation should be EMERGENT from threat assessment, not scripted
- No magic constants — thread counts from staffing data, intel rates from investigation timelines

WHAT THIS DOES NOT INCLUDE:
- Full informant/corrupted node mechanics (defer — Gap 1 in state-repression-research.md)
- Inter-agency rivalry and coordination failure details (defer)
- Judicial system as separate entity (defer)
- Player notification of surveillance (defer to GUI)
- Media/public opinion feedback on repression (defer)
- Persistent homology for deeper topological analysis (defer to Phase 5)

REFERENCES:
- Sparrow 1991: "The application of network analysis to criminal intelligence"
- Sparrow 1993: "A linear algorithm for computing automorphic equivalence classes"
- state-repression-research.md — full validation against COINTELPRO and modern capabilities
- Hoover memo 1968: topology-aware strategy explicitly documented
- Palantir Gotham: automated link analysis with centrality highlighting
- FBI Big Floyd: template matching as subgraph isomorphism
```

---

## Phase 5: Bifurcation Topology Analysis

### Spec ID: `024-bifurcation-topology`

### Prompt:

```
Create a specification for Bifurcation Topology Analysis — the George Jackson model.

CONTEXT:
- The central prediction of the simulation: does crisis produce fascism or revolution?
- Answer depends on SOLIDARITY TOPOLOGY at moment of crisis, not consciousness levels
- Named for George Jackson's insight: agitation without organization produces fascism
- Requires: 020-organization-base-model (for org topology), EdgeMode enum (exists),
  022-community-hyperedge-layer (communities as cross-class bridges)
- Builds on: TopologyMonitor (exists, has Sword of Damocles test)
- Extends with: Sparrow analysis from Phase 4 (equivalence classes, cutsets)

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
    source_class = G.nodes[edge.source]['class_position']
    target_class = G.nodes[edge.target]['class_position']
    return (source_class in CORE_CLASSES) != (target_class in CORE_CLASSES)
```

**Community Hyperedges as Cross-Class Bridges**:
Some communities span the colonial divide (DISABLED includes both LA and lumpen members).
These hyperedges create POTENTIAL paths for cross-line solidarity that pure class
analysis would miss. The bifurcation analysis must account for:
- Which communities span the divide? (cross_class_bridge from Phase 3)
- Is there organizational presence within those communities building solidarity?
- Or is the state successfully isolating community members by class position?

**Bifurcation Tendency**:
Compute from topology of SOLIDARISTIC edges:
- Count cross-line solidaristic edges vs within-line solidaristic edges
- Count cross-line ANTAGONISTIC edges (hostility across divide)
- Weight by community bridges (shared community membership raises potential)
- Ratio determines bifurcation tendency

```python
def bifurcation_tendency(G, H_communities) -> BifurcationResult:
    solidarity_edges = [(u,v) for u,v,d in G.edges(data=True)
                        if d['mode'] == EdgeMode.SOLIDARISTIC]
    cross_line = [e for e in solidarity_edges if crosses_colonial_divide(e, G)]
    within_line = [e for e in solidarity_edges if not crosses_colonial_divide(e, G)]

    # Community bridge bonus: shared communities that span divide
    bridge_communities = cross_class_bridges(H_communities)
    bridge_potential = len(bridge_communities) * community_bridge_weight

    effective_cross = len(cross_line) + bridge_potential

    if effective_cross > len(within_line) * threshold:
        return BifurcationResult(tendency="revolutionary", ...)
    else:
        return BifurcationResult(tendency="fascist", ...)
```

**Material Constraints on Solidarity**:
- wage_gap_ratio > 10 → solidarity_ceiling = 0.3 (very hard to build)
- wage_gap_ratio < 2 → solidarity_ceiling = 0.9 (material similarity enables)
- geographic_proximity required (PRESENCE in same territory)
- shared_exploitation_source raises ceiling +0.2 (common enemy)
- shared_community_membership raises ceiling (Phase 3 modifier)
These are CEILINGS, not determinants. Organizing effort is still required.

**Betti Number Analysis**:
- β₀: Connected components in solidarity subgraph (fragmentation)
- β₁: Independent cycles (routing redundancy — resilience)
  - Compute via nx.cycle_basis() or β₁ = E - V + β₀
  - Low β₁ = fragile (tree-like), high β₁ = resilient (mesh-like)
- β₂: 2D voids in clique complex (hollow shells — organizations that coordinate
       at boundaries but lack full interpenetration)

Ideal revolutionary topology: P(t) = 1 + kt (high β₁, zero β₂)
- Many redundant paths (mesh, not star)
- No hollow shells (genuine interpenetration, not just elite coordination)

**Sparrow Equivalence Integration**:
From Phase 4, equivalence class analysis adds:
- Large equivalence classes = resilient to targeted removal = good for revolution
- Singleton classes = irreplaceable roles = vulnerability
- The bifurcation surface should include equivalence class distribution as input

**Antagonism Direction**:
```python
def antagonism_direction(edge, G) -> str:
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
- bifurcation_tendency(G, H_communities) -> BifurcationResult
- solidarity_ceiling(node_a, node_b, G, H_communities) -> float
- cross_class_bridges(H_communities) -> list[CommunityType]

**Topology Metrics**:
- betti_0(G, subgraph_filter) -> int
- betti_1(G, subgraph_filter) -> int
- resilience_score(G, purge_strategy) -> float
- equivalence_class_distribution(G) -> dict[int, int]  # class_size → count

**BifurcationResult Model**:
```python
class BifurcationResult(BaseModel):
    tendency: Literal["revolutionary", "fascist", "indeterminate"]
    cross_line_solidarity_count: int
    within_line_solidarity_count: int
    community_bridge_count: int
    lateral_antagonism_count: int
    upward_antagonism_count: int
    beta_0: int
    beta_1: int
    resilience_under_targeted_purge: float
    equivalence_class_distribution: dict[int, int]
    critical_singletons: list[str]  # Sparrow: irreplaceable roles
    critical_cutsets: list[set[str]]  # Sparrow: structural vulnerabilities
```

**Integration**:
- BifurcationSystem that runs after all organizational actions resolve
- Computes BifurcationResult each tick
- This is the OUTCOME VARIABLE — the thing the simulation predicts

VALIDATION CRITERIA:
- Pure within-group solidarity → tendency = "fascist"
- Cross-line solidarity exceeding threshold → tendency = "revolutionary"
- Adding DISABLED community bridge (spanning divide) shifts tendency toward revolutionary
- Star topology yields low resilience; mesh yields high resilience
- Removing highest-betweenness node from star fragments network
- Removing highest-betweenness node from mesh does NOT fragment
- β₁ = 0 for trees; β₁ > 0 for mesh
- Large equivalence classes → higher resilience score
- Detroit test: Wayne ↔ Oakland edge predicts bifurcation from solidarity vs antagonism

CONSTRAINTS:
- Must work with EdgeMode enum (EXTRACTIVE/TRANSACTIONAL/SOLIDARISTIC/ANTAGONISTIC)
- β₂ computation requires clique complex — optional dependency (giotto-tda or ripser)
- Core spec uses β₀ and β₁ only (pure NetworkX)
- Colonial divide definition matches wealth-based class from spec 014
- Community bridge analysis requires Phase 3 (XGI or bipartite fallback)

WHAT THIS DOES NOT INCLUDE:
- Persistent homology (optional Phase 2 of topology)
- Crisis trigger mechanics (when does bifurcation actually fire?)
- Post-bifurcation dynamics (what happens after outcome?)
- Spatial dimension (which territories tip which way?)
- GUI visualization of bifurcation surface (defer)
```

---

## Phase 6: Organization-Territory Integration

### Spec ID: `025-org-territory-integration`

### Prompt:

```
Create a specification for Organization-Territory Integration — spatial dynamics
of organizational action.

CONTEXT:
- Organizations operate IN territories (PRESENCE edges)
- Territory has H3 hex grid, sector type, heat level, occupant stack
- Organizations conducting HIGH_PROFILE operations raise territory heat
- Heat attracts state attention threads (Phase 4)
- Community hyperedges (Phase 3) have territory-bound infrastructure
- Requires: 020 through 024

THEORETICAL FOUNDATION:

**Organizations Occupy Territories**:
Every Organization has presence in one or more territories:
- PRESENCE edge: Org → Territory
- headquarters_id: primary territory
- Operational profile per territory: HIGH_PROFILE (visible, recruits) vs LOW_PROFILE (safe, slow)

**Heat Mechanics**:
Territory heat accumulates from organizational activity:
- HIGH_PROFILE actions raise heat
- State attention threads monitoring a territory raise heat further
- Heat decays over time without activity
- Heat above threshold triggers state response

**Community Infrastructure Is Territory-Bound**:
Community gathering spaces, mutual aid networks, healthcare providers — these exist
in SPECIFIC territories. When the state raises heat in a territory, community
infrastructure there is at risk. Displacement severs community infrastructure
from its members.

**Recruitment Geography**:
RECRUIT action requires PRESENCE in a territory containing the target SocialClass population.
Community membership provides an additional recruitment channel:
shared community → easier recruitment even across class lines.

**Eviction Pipeline**:
When territory heat exceeds threshold:
- Occupants displaced to adjacent territories (H3 k-ring adjacency)
- Organizations lose PRESENCE edges
- Community infrastructure damaged or destroyed
- Carceral routing: reservation → penal colony → concentration camp

REQUIRED OUTPUTS:

**Models**:
- PresenceEdge: (org_id, territory_id, operational_profile, duration)
- TerritoryHeatEvent: records what caused heat change

**Mechanics**:
- heat_accumulation(territory, actions_this_tick) -> float
- heat_decay(territory, ticks_since_last_activity) -> float
- eviction_check(territory) -> list[EvictionEvent] | None
- recruitment_eligibility(org, territory, target_class, shared_communities) -> bool

**Integration**:
- Attention threads (Phase 4) read territory heat for thread allocation
- Community infrastructure (Phase 3) damage on eviction
- OODA actions (Phase 2) require territorial PRESENCE

VALIDATION CRITERIA:
- HIGH_PROFILE presence accumulates heat faster than LOW_PROFILE
- Heat above threshold triggers eviction
- Cannot RECRUIT without PRESENCE
- Community infrastructure damaged when territory evicted
- Detroit test: organizing in Wayne County vs Oakland County heat dynamics

CONSTRAINTS:
- H3 resolution 7 (~5km hex) for Detroit
- Heat is float [0,1], not counter
- Territory adjacency from H3 k-ring
- Eviction deterministic given threshold

WHAT THIS DOES NOT INCLUDE:
- Gentrification (territory transformation) — defer
- Infrastructure targeting (power, water) — defer
- Climate displacement — defer
- Full carceral geography pipeline — defer
- Territory contestation — defer
```

---

## Phase 7: NPC Faction AI (Stub)

### Spec ID: `026-npc-faction-ai-stub`

### Prompt:

```
Create a specification for NPC Faction AI — stub implementation using
Sparrow-grounded heuristics for state actors and class-interest heuristics
for non-state actors.

CONTEXT:
- Player controls one PoliticalFaction. All other organizations need AI.
- This is a STUB — rule-based heuristics, not sophisticated AI
- StateApparatus AI uses simplified Sparrow methodology (Phase 4)
- Purpose: make the simulation runnable end-to-end
- Requires: 020 through 025

THEORETICAL FOUNDATION:

NPC organizations follow class interest as default behavior, with
intelligence constraints (they can't see what they can't see).

**StateApparatus AI** (Sparrow-grounded):
1. Meta-OODA: Allocate threads to highest-heat organizations
2. Per-thread:
   a. MONITORING phase: Expand observed_subgraph each tick
   b. When intel_completeness > 0.5: Run Sparrow analysis
   c. If singletons found: Target highest-betweenness singleton
   d. If cutsets found: Attempt edge severing
   e. If no clear targets: Continue monitoring or reallocate thread
3. The state makes MISTAKES because it operates on G_observed, not G_actual
   - It may target someone who looks central in G_observed but isn't in G_actual
   - It may miss the real leadership if they maintain low observational profile

**Business AI**:
1. EMPLOY from cheapest available SocialClass pool
2. If strike active, attempt to break it
3. Otherwise maintain operations (automatic Layer 0)

**CivilSocietyOrg AI**:
1. PROVIDE_SERVICE in territories with PRESENCE
2. If heat > 0.5, shift to LOW_PROFILE
3. RECRUIT when below capacity

**Rival PoliticalFaction AI**:
1. RECRUIT in territories where player is weak
2. ORGANIZE existing members
3. Use community bridges for cross-class recruitment when possible

REQUIRED OUTPUTS:

**System**:
- NPCDecisionSystem with per-type decision functions
- StateAI explicitly uses Sparrow analysis results from attention threads
- NPCDecisionStrategy protocol for future hot-swapping

VALIDATION CRITERIA:
- 52-tick simulation runs without crashing
- FBI targets player org based on Sparrow analysis of observed topology
- FBI makes targeting mistakes based on observation gap
- Business extracts surplus each tick
- Rival faction grows over time

CONSTRAINTS:
- STUB quality — "runs correctly" not "plays well"
- Deterministic given same RNG seed
- No external AI calls
- Strategy pattern for future replacement
```

---

## Dependency Graph

```
020-organization-base-model
    ├── 021-ooda-loop-system
    │   ├── 023-attention-thread-system (Sparrow-grounded)
    │   │   └── 025-org-territory-integration
    │   └── 026-npc-faction-ai-stub
    ├── 022-community-hyperedge-layer
    │   └── 024-bifurcation-topology
    └── 024-bifurcation-topology (also depends on 022)
```

Recommended implementation order: 020 → 021 → 022 → 024 → 023 → 025 → 026

Rationale:
- 022 (communities) is lightweight and provides the hyperedge substrate
  that bifurcation analysis (024) needs for cross-class bridge detection
- 024 (bifurcation) is the OUTCOME VARIABLE — validate topology analysis
  early, even before the full action/attention system exists
- 023 (attention threads) is the most complex single spec and benefits
  from having simpler pieces stable first
- 025 (territory) wires spatial dynamics to attention threads
- 026 (NPC AI) is last because it ties everything together for end-to-end testing

## Key Cross-Cutting Concerns

**Sparrow Thread Through All Specs**:
Sparrow's framework appears in three places:
1. Phase 1: StateApparatus.IntelMethodology (what analysis they CAN do)
2. Phase 4: AttentionThread.SparrowAnalysis (what they ACTUALLY compute on observed graph)
3. Phase 5: BifurcationResult.critical_singletons/cutsets (defensive analysis — "what would they find?")

The same algorithms serve both sides. The asymmetry is in the observation gap.

**Hypergraph Thread Through All Specs**:
Community hyperedges appear in:
1. Phase 3: Core community model (XGI or bipartite fallback)
2. Phase 5: Bifurcation analysis (cross-class bridges shift tendency)
3. Phase 6: Territory integration (community infrastructure is territory-bound)
4. Phase 2: OODA Layer 3 (community effects propagate in reaction phase)

**The Observation Gap As Game Mechanic**:
The gap between G_actual and G_observed is the core strategic space:
- Player builds topology that is strong in G_actual but looks weak in G_observed
- State tries to close the gap through surveillance and infiltration
- Cell topology, operational security, and low-profile operations widen the gap
- High-profile actions close it (visibility = recruitment AND targeting)
