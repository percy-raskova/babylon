# Organization & Topology: Spec-Kit Prompts (v4 — Final)

**Purpose**: Prompts for Claude Code + spec-kit to generate specifications for the Organization system
**Usage**: Feed each prompt to `/speckit.specify` sequentially; each phase builds on the prior
**Prerequisite**: Community hyperedge layer (022) is ALREADY IMPLEMENTED via XGI
**Context**: Existing codebase has SocialClass nodes, Territory nodes, EdgeMode enum, NetworkXAdapter, TopologyMonitor, SimulationEngine, and working community hyperedge infrastructure
**Key Insight**: In Babylon, Organizations ARE the agents. SocialClass, Territory, and Community are substrate.
**Revision v4**: Incorporates community consciousness (material basis + ideological dimension), the assimilation/revolution dialectic, and consciousness-weighted bifurcation analysis

---

## Architectural Foundation

### Two-Layer Architecture: Substrate + Agents

```
SUBSTRATE LAYER (no agency)
├── SocialClass blocks (demographic reservoirs with population, wealth, consciousness)
├── Territory (spatial grid, H3 hexagons, can be occupied/contested)
└── Community hyperedges (IMPLEMENTED — three structural categories + consciousness)

AGENT LAYER (has agency)
└── Organization (the ONLY agent type)
    ├── StateApparatus (FBI, police, military, courts)
    ├── Business (employer, extracts surplus value)
    ├── PoliticalFaction (player & NPC rivals)
    └── CivilSocietyOrg (church, NGO, union, school)
```

### Community Hyperedge Taxonomy (Implemented)

Three structurally distinct categories. NOT a spectrum — qualitatively different
groupings with different material bases, different relationships to oppression,
and different modeling requirements.

**Category 1: Contradiction Pairs**
Both hegemonic and marginalized sides are real hyperedges with members,
institutions, political projects, and material extraction flows between them.

| Hegemonic Hyperedge | Marginalized Hyperedge(s) | Material Basis of Extraction |
|---------------------|---------------------------|------------------------------|
| SETTLER | NEW_AFRIKAN, FIRST_NATIONS, CHICANO | Land, imperial rent, carceral labor, property value regimes |
| PATRIARCHAL | WOMEN, TRANS | Unwaged reproductive labor (Dept III), wage gap, care externalization |

SETTLER has institutions (HOAs, police unions, suburban school boards, border militias),
material infrastructure (property value regimes, redlining legacies), and active political
projects. It recruits, organizes, defends its extraction position.

PATRIARCHAL has institutions (patriarchal family structure, gendered wage systems,
religious hierarchies) and extracts reproductive labor (Federici). Trans men don't
occupy the same material position in patriarchy as cis men — PATRIARCHAL membership
defined by material position in extraction, not gender identity.

**Category 2: Institutional Exclusion**
Only the marginalized side exists as a real hyperedge. No paired oppressor community.
Oppression flows through institutional defaults and resource allocation.

| Hyperedge | Material Basis | Why No Paired Oppressor |
|-----------|---------------|------------------------|
| DISABLED | Built environment assumes able-bodiedness; higher reproduction costs | ABLED is absence of disability, not a political community |
| QUEER | Institutional heteronormativity; exclusion from protections | HETEROSEXUAL is unmarked default |
| UNDOCUMENTED | Legal exclusion from labor protections, healthcare, housing | CITIZEN is legal status, not solidarity community |
| INCARCERATED | Carceral system; sub-minimum labor extraction; civil death | FREE is absence of incarceration |

**Category 3: Lifecycle Phases (D-P-D' Circuit)**
Temporal positions in the intergenerational lifecycle. NOT identity communities —
structural phases with distinct material conditions.

| Hyperedge | D-P-D' Phase | Material Position |
|-----------|-------------|-------------------|
| YOUTH | D (Dependent) | Pre-productive. Cannot sell labor-power. Receives care, socialization, ideological transmission. |
| ADULT | P (Productive) | Sells labor-power. Where C-M-C and M-C-M' operate. |
| ELDER | D' (Dependent') | Post-productive. The D' promise (Social Security, pensions) is the legitimation bargain. |

Universal traversal, temporal permeability. Dependency ratio = (Pop_D + Pop_D') / Pop_P.

### The Material-Ideological Distinction on Community Hyperedges

**Every hyperedge has two dimensions:**

1. **Material basis** (objective): The concrete extraction, exclusion, or structural
   position that defines the hyperedge. This exists regardless of whether members
   recognize it. A Black person in Detroit has a material position within the
   SETTLER ↔ NEW_AFRIKAN contradiction pair whether or not they identify as
   having separate material interests from the settler nation.

2. **Ideological dimension** (subjective): Whether members of the hyperedge
   conceive of themselves as having collective interests that are structurally
   opposed to the hegemonic order. A trans person has to conceive of themselves
   not only as transgender, but as having material interests not served by
   integration into patriarchy.

The GAP between these two dimensions is the terrain of political struggle.
This is class-in-itself vs class-for-itself, generalized across all contradiction axes.

**Three Ideological Tendencies** (the assimilation/revolution dialectic):

```python
class ConsciousnessTendency(Enum):
    ASSIMILATIONIST_LIBERAL = "assimilationist_liberal"
    # "Expand the definition, let us in."
    # Gay marriage, Black CEOs, women in combat roles.
    # Works for SOME members (closest to hegemonic side on other axes).
    # Leaves structural extraction intact.
    # Strategy: reform existing institutions to be more inclusive.
    # Organizational vehicle: liberal CivilSocietyOrgs, Democratic Party.

    ASSIMILATIONIST_FASCIST = "assimilationist_fascist"
    # "We're the good ones, exclude the others."
    # Respectability politics taken to extreme.
    # Collaboration with hegemonic order in exchange for individual escape.
    # "I'm not like THOSE people."
    # Strategy: shrink the marginalized definition, exclude the most marginal.
    # Organizational vehicle: conservative wings within marginalized communities.

    REVOLUTIONARY = "revolutionary"
    # "Our interests are structurally opposed. Integration is impossible long-term."
    # The contradiction is material, not a misunderstanding to be resolved.
    # No amount of representation within existing institutions resolves extraction.
    # Strategy: build oppositional collective identity and independent power.
    # Organizational vehicle: revolutionary PoliticalFactions.
```

**The ruling class ideological strategy** is to suppress collective_identity:
"White or Black, gay or straight, we're all Americans." This asserts that the
material basis of the hyperedge doesn't exist or doesn't matter. The material
basis is still there (wage gap, carceral system, inaccessible built environment)
but the ideological overlay denies its significance.

**Liberalism and fascism are BOTH assimilationist** — two strategies for the same goal
(preventing revolutionary consciousness). Liberalism expands the definition
("anyone can be American"). Fascism shrinks it ("only REAL Americans"). Both
prevent the formation of oppositional collective identity.

**The revolutionary task** in the ideological realm: use agitation, propaganda, and
political education to get oppressed and marginalized hyperedge-groups to form
a collective self-identity that sees itself in opposition to hegemony and
understands it has no chance of long-term survival through integration.

```python
class CommunityConsciousness(BaseModel):
    """The ideological dimension of a community hyperedge.

    Tracks the gap between material basis (objective) and
    collective self-understanding (subjective).
    """
    # What fraction of members identify as having separate material interests
    # from the hegemonic order? [0 = fully assimilated, 1 = full oppositional]
    collective_identity: float  # [0,1]

    # Dominant ideological tendency within this community
    dominant_tendency: ConsciousnessTendency

    # How contested is the ideological terrain? (high = active struggle over direction)
    ideological_contestation: float  # [0,1]
```

### Sparrow's Network Vulnerability Framework

Malcolm K. Sparrow (1991, 1993) formalized how law enforcement operationalizes graph
theory. Mathematically symmetric — same algorithms serve attacker and defender.

**State side**: Six centrality types, equivalence class analysis, cutset identification,
template matching (Big Floyd). Operates on G_observed (always incomplete, distorted).

**Movement side**: Sword of Damocles — run the state's algorithms defensively.
Equivalence class size = replaceability. β₁ cycles = routing redundancy.
AVLF graph proves analysis-resistant topology is mathematically possible.

**Observation gap** (G_observed ≠ G_actual): The core strategic game mechanic.
State sees metadata; misses face-to-face, cash, consciousness, commitment.

### Organization vs Institution

Organization = voluntary coordination, can be destroyed.
Institution = crystallized social relations, survives member turnover.
Organizations become Institutions through formalization.

### OODA Loop as Organizational Metabolism

OODA profile determines action capacity per turn.
Speed vs coherence, autonomy vs coordination, democracy vs reaction time.

---

## Phase 1: Organization Base Model

### Spec ID: `030-organization-base-model`

### Prompt:

```
Create a specification for the Organization Base Model.

CONTEXT:
- Organizations are the ONLY agents in Babylon. Everything else is substrate.
- Community hyperedge layer is ALREADY IMPLEMENTED (XGI, three categories,
  with CommunityConsciousness tracking ideological dimension)
- Existing codebase: OrganizationComponent, faction.schema.json,
  institution.schema.json, RevolutionaryFinance model — all need unification
- Organizations are views over the NetworkX graph, not separate node types

THEORETICAL FOUNDATION:

**What Organizations DO**:
1. Contain members (drawn from SocialClass population blocks)
2. Have internal topology (star/hierarchy vs mesh/cell)
3. Control resources (budget, assets, legal authority)
4. Take collective action (recruit, repress, provide services, employ, organize)
5. Be infiltrated, disrupted, or allied with
6. Have class character (which class they serve — may differ from composition)
7. Interact with community hyperedges:
   - Recruit along community lines
   - Attack or build community infrastructure
   - Engage in ideological struggle over community consciousness
     (push collective_identity toward or away from revolutionary tendency)

**Organization ABC**:
```python
class Organization(BaseModel):
    id: str
    name: str
    org_type: OrgType  # STATE_APPARATUS | BUSINESS | POLITICAL_FACTION | CIVIL_SOCIETY

    # Class analysis
    class_character: ClassCharacter  # BOURGEOIS | PROLETARIAN | CONTESTED

    # Internal state
    internal_topology: TopologyType  # STAR | HIERARCHY | MESH | CELL
    cohesion: float  # [0,1]
    cadre_level: float  # [0,1]

    # Resources
    budget: float
    legal_standing: LegalStanding  # SOVEREIGN | CHARTERED | REGISTERED | INFORMAL | UNDERGROUND

    # Spatial
    territory_ids: list[str]
    headquarters_id: str | None

    # State attention
    heat: float  # [0,1]

    # Institutional attributes
    is_institution: bool
    institutional_persistence: float | None
```

**Subtypes**:

StateApparatus:
- jurisdiction: national | state | county | municipal
- violence_capacity: float
- surveillance_capacity: float
- legal_authority: list[Authority]
- intel_methodology: IntelMethodology (Sparrow-grounded)

Business:
- sector: NAICSSector
- employment_count: int
- surplus_extraction_rate: float
- revenue: float

PoliticalFaction:
- ideology: IdeologicalProfile
- is_player: bool
- relationship_to_player: RelationType
- consciousness_strategy: ConsciousnessTendency
  # What ideological tendency does this faction push within communities?
  # Revolutionary faction pushes REVOLUTIONARY consciousness
  # Liberal faction pushes ASSIMILATIONIST_LIBERAL
  # Fascist faction pushes ASSIMILATIONIST_FASCIST

CivilSocietyOrg:
- service_type: ServiceType
- legitimacy: float
- consciousness_tendency: ConsciousnessTendency
  # Churches often push ASSIMILATIONIST_LIBERAL or FASCIST
  # Mutual aid orgs may push REVOLUTIONARY
  # This determines their effect on community consciousness when they act

**Sparrow Integration (StateApparatus)**:
```python
class IntelMethodology(BaseModel):
    """What network analysis a StateApparatus can perform.
    Grounded in Sparrow 1991."""
    centrality_analysis: bool
    equivalence_analysis: bool  # Sparrow 1993 algorithm
    template_matching: bool     # Big Floyd
    temporal_analysis: bool
    observation_ceiling: float  # [0,1]
```

FBI: all True, ceiling ~0.4. Local PD: centrality only, ceiling ~0.2.
Fusion center: centrality + temporal, ceiling ~0.5.

**Community Interaction**:
Organizations interact with EXISTING hyperedge layer:
- consciousness_strategy determines what happens when org acts within a community:
  EDUCATE action by a REVOLUTIONARY faction raises collective_identity
  PROVIDE_SERVICE by a liberal CivilSocietyOrg reinforces ASSIMILATIONIST_LIBERAL
  Fascist org actions within SETTLER hyperedge raise lateral antagonism
- SETTLER hyperedge is where StateApparatus and fascist factions recruit base
- PATRIARCHAL institutions (patriarchal churches, trad family orgs) are CivilSocietyOrgs
  reinforcing extraction along that axis while pushing ASSIMILATIONIST ideology

**D-P-D' Integration**:
- YOUTH members: politically educable (D-phase socialization) but can't act
- ADULT members: active base (P-phase)
- ELDER members: institutional memory, reduced action capacity
- Dependency ratio affects org's effective labor pool
- Orgs controlling D-phase infrastructure (schools) control ideological transmission

**Key Figures**:
- Individual nodes within organizational topology
- Sparrow equivalence: singletons = irreplaceable = high-value targets
- Removal has topological consequences

REQUIRED OUTPUTS:

**Models (Pydantic)**:
- Organization ABC (frozen=True)
- Four subtypes with consciousness_strategy/tendency where applicable
- OrgType, ClassCharacter, TopologyType, LegalStanding enums
- IntelMethodology
- KeyFigure model
- Deprecation path from OrganizationComponent, faction.schema.json

**Graph Integration**:
- Organization.member_node_ids: list[str]
- Organization.to_subgraph(G) -> nx.subgraph_view
- Organization.class_composition(G) -> dict[ClassPosition, float]
- Organization.community_composition(H) -> dict[CommunityType, float]
- Organization.lifecycle_composition() -> dict[LifecyclePhase, float]
- Organization.consciousness_effect(target_community) -> ConsciousnessDelta
  (what happens to that community's collective_identity when this org acts?)
- Edge types: RECRUITMENT, EMPLOYMENT, PRESENCE, COMMAND, MEMBERSHIP

VALIDATION CRITERIA:
- All four subtypes instantiable for Detroit
- FBI with correct IntelMethodology
- Ford/GM as Business with QCEW employment
- Revolutionary PoliticalFaction has consciousness_strategy=REVOLUTIONARY
- Liberal CivilSocietyOrg (mainstream church) has tendency=ASSIMILATIONIST_LIBERAL
- consciousness_effect: revolutionary org raises collective_identity,
  liberal org maintains/lowers it, fascist org pushes ASSIMILATIONIST_FASCIST
- community_composition reflects member hyperedge memberships from XGI
- lifecycle_composition reflects D/P/D' distribution

CONSTRAINTS:
- Integrates with existing NetworkXAdapter, GraphProtocol, community hyperedge layer
- Frozen Pydantic; mutations create new instances
- No magic constants

DEPENDENCIES:
- Requires: SocialClass (exists), Territory (exists), EdgeMode (exists),
  NetworkXAdapter (exists), Community hyperedge layer (IMPLEMENTED)
- Deprecates: OrganizationComponent

WHAT THIS DOES NOT INCLUDE:
- OODA loop mechanics (Phase 2)
- Attention threads (Phase 3)
- Bifurcation analysis (Phase 4)
- NPC AI (Phase 5)
- Org-Territory integration (Phase 6)
- Organization → Institution transition (defer)
- Coalition/united front formation (defer)
```

---

## Phase 2: OODA Loop System

### Spec ID: `031-ooda-loop-system`

### Prompt:

```
Create a specification for the OODA Loop System — organizational action resolution.

CONTEXT:
- Organizations are agents; OODA loops are their metabolism
- Ticks = ~1 week, 52/year. Orgs act in LAYERS per tick.
- Community hyperedges (IMPLEMENTED) affect action costs, eligibility,
  and consciousness effects
- Requires: 030-organization-base-model

THEORETICAL FOUNDATION:

**OODAProfile** (four phases):

OBSERVE: intelligence [0,1], sensor_latency (ticks)
ORIENT: ideological_coherence [0,1], analytical_capacity
DECIDE: decision_mode (AUTOCRATIC|DELEGATE|DEMOCRATIC|CONSENSUS), bureaucratic_depth
ACT: action_points, coordination_range, autonomy [0,1]

**Trade-off space**:
Fast OODA: small, autocratic, loose ideology, low coherence, local optimization
Slow OODA: large, democratic, rigid ideology, high coherence, global coordination
Democratic centralism = fast DECIDE + democratic ORIENT + disciplined ACT

**Turn Resolution Layers**:

Layer 0 (Material base): Automatic economic metabolism
  - Business surplus extraction, wage payment
  - D-P-D' transitions (aging, birth, death at population level)

Layer 1 (State action): StateApparatus orgs
  - Surveillance, repression, legal harassment
  - Community infrastructure attacks
  - Ideological operations ("we're all Americans" messaging)
  - State acts FIRST (institutional advantage)

Layer 2 (Organizational action): PoliticalFactions, CivilSocietyOrgs
  - Resolved in OODA speed order (fastest first)
  - Actions include consciousness work within communities

Layer 3 (Reaction): Consequences propagate
  - Heat changes, edge transformations
  - Community consciousness shifts (collective_identity changes)
  - Community infrastructure effects
  - Legitimation index updates (D-P-D')

**Action Types**:
```python
class ActionType(Enum):
    # Recruitment & organizing
    RECRUIT = "recruit"
    ORGANIZE = "organize"          # TRANSACTIONAL → SOLIDARISTIC edge transformation

    # Consciousness work (the ideological dimension)
    EDUCATE = "educate"            # Political education within a community
                                   # Effect on collective_identity depends on
                                   # org's consciousness_strategy:
                                   # REVOLUTIONARY → raises collective_identity
                                   # LIBERAL → maintains/lowers (inclusion framing)
                                   # FASCIST → redirects toward lateral antagonism
    AGITATE = "agitate"            # Raise awareness of material conditions
                                   # Differs from EDUCATE: agitation exposes the
                                   # contradiction, education provides the framework
    PROPAGANDIZE = "propagandize"  # Mass messaging to shift dominant_tendency
                                   # within a community. Cheaper than EDUCATE
                                   # but less effective per-member.

    # Resource operations
    FUNDRAISE = "fundraise"
    PROVIDE_SERVICE = "provide_service"  # Mutual aid — builds legitimacy AND
                                         # demonstrates alternative to hegemonic
                                         # institutions (consciousness effect)
    EMPLOY = "employ"

    # Conflict
    REPRESS = "repress"
    PROTEST = "protest"
    STRIKE = "strike"
    EXPROPRIATE = "expropriate"

    # Intelligence (Sparrow-grounded)
    SURVEIL = "surveil"
    INFILTRATE = "infiltrate"
    COUNTER_INTEL = "counter_intel"
    MAP_NETWORK = "map_network"

    # Diplomacy
    PROPOSE_ALLIANCE = "propose_alliance"
    DENOUNCE = "denounce"

    # Community infrastructure
    BUILD_INFRASTRUCTURE = "build_infrastructure"
    ATTACK_INFRASTRUCTURE = "attack_infrastructure"

    # Ideological operations (hegemonic)
    ASSIMILATE = "assimilate"      # Push "we're all Americans" narrative
                                   # Directly attacks collective_identity of
                                   # marginalized communities
                                   # Available to: StateApparatus, liberal orgs,
                                   # hegemonic community institutions
```

**Consciousness Mechanics in Actions**:

Every org action within a community has a consciousness side-effect determined
by the org's consciousness_strategy:

PROVIDE_SERVICE by revolutionary org: builds legitimacy AND demonstrates that
  the community can meet its own needs without hegemonic institutions.
  Raises collective_identity slightly.

PROVIDE_SERVICE by liberal org: meets material needs but reinforces dependency
  on institutions within the existing order. Neutral or slightly lowers
  collective_identity.

EDUCATE by revolutionary org: the core consciousness-raising action. Targets
  specific community, moves collective_identity toward 1.0, shifts
  dominant_tendency toward REVOLUTIONARY. Requires cadre_labor_hours (scarce).

AGITATE by any org: exposes material contradictions. Raises awareness of the
  gap between material basis and ideological overlay. Prerequisite for
  EDUCATE — you can't educate people who don't yet see the problem.
  Raises ideological_contestation within the community.

ASSIMILATE by hegemonic-aligned org: "we're all Americans" messaging. Directly
  targets collective_identity, pushing it toward 0. Cheaper than EDUCATE
  because it has institutional backing (media, schools, state messaging).

**Community-Modified Action Costs**:
- RECRUIT within shared community: reduced cost
- RECRUIT across contradiction pair: much higher cost
- EDUCATE within community you're embedded in: normal cost
- EDUCATE in community you're NOT part of: higher cost + credibility penalty
  (you can't raise consciousness in a community from outside it)
- BUILD_INFRASTRUCTURE: benefits all members in hyperedge
- ATTACK_INFRASTRUCTURE: damages community resources, raises reproduction costs

**Lifecycle-Modified Action Capacity**:
- YOUTH (D): receive EDUCATE (ideological socialization), cannot act otherwise
  Orgs controlling D-phase institutions (schools) shape the next generation
- ADULT (P): full action capacity
- ELDER (D'): reduced action_points, legitimacy bonus, institutional memory

REQUIRED OUTPUTS:

**Models**:
- OODAProfile with computed cycle_time
- ActionType enum (including consciousness actions: EDUCATE, AGITATE, PROPAGANDIZE, ASSIMILATE)
- Action model with consciousness_delta field
- TurnResolution with Layer 3 consciousness propagation

**System**:
- OODASystem integrated with SimulationEngine.run_tick()
- Community-modified action costs
- Consciousness side-effects computed per action
- Lifecycle-modified action capacity
- Layer 3 propagation: collective_identity and dominant_tendency updates

**Consciousness Effect Computation**:
```python
def compute_consciousness_effect(
    action: Action,
    org: Organization,
    target_community: CommunityType,
    community_state: CommunityConsciousness
) -> ConsciousnessDelta:
    """What happens to community consciousness when this org acts?"""

    base_effect = ACTION_CONSCIOUSNESS_MAP[action.action_type]
    strategy_modifier = org.consciousness_strategy  # REVOLUTIONARY amplifies, LIBERAL dampens

    # Credibility: is this org embedded in the community?
    org_community_overlap = org.community_composition(H).get(target_community, 0)
    credibility = org_community_overlap  # Can't raise consciousness from outside

    # Contestation: highly contested communities are harder to shift
    resistance = community_state.ideological_contestation

    return ConsciousnessDelta(
        collective_identity_change=base_effect * strategy_modifier * credibility,
        contestation_change=...,
        tendency_pressure=org.consciousness_strategy
    )
```

VALIDATION CRITERIA:
- FBI gets Layer 1 priority
- CONSENSUS org slower cycle_time than AUTOCRATIC
- RECRUIT within shared community costs less
- EDUCATE by revolutionary org raises collective_identity
- EDUCATE by liberal org has neutral/negative effect on collective_identity
- ASSIMILATE action lowers collective_identity
- EDUCATE in a community you're not part of has credibility penalty
- PROVIDE_SERVICE by revolutionary org has different consciousness effect than same
  service by liberal org
- AGITATE raises ideological_contestation (precondition for EDUCATE effectiveness)
- YOUTH receive EDUCATE but can't act
- Detroit test: one tick with FBI + revolutionary faction + liberal church + business

CONSTRAINTS:
- Layer 0 automatic, not OODA
- Player actions from input, NPC from AI stub (Phase 5)
- No magic constants
- Must integrate with EXISTING community hyperedge infrastructure
- Consciousness effects must be SMALL per tick (ideological change is slow)
  but compounding over many ticks

DEPENDENCIES:
- Requires: 030-organization-base-model
- Integrates with: Community hyperedge layer (IMPLEMENTED), CommunityConsciousness

WHAT THIS DOES NOT INCLUDE:
- NPC AI logic (Phase 5)
- Player UI (defer)
- Detailed infiltration (defer)
- Coalition formation (defer)
```

---

## Phase 3: State Attention Thread System (Sparrow-Grounded)

### Spec ID: `032-attention-thread-system`

### Prompt:

```
Create a specification for the State Attention Thread System, grounded in
Malcolm K. Sparrow's network vulnerability analysis.

CONTEXT:
- State's scarce resource is ATTENTION
- Sparrow (1991): graph concepts → operational disruption objectives
- Sparrow (1993): linear-time automorphic equivalence algorithm
- Community hyperedges (IMPLEMENTED) are targetable — infrastructure attacks
- Community consciousness is targetable — ASSIMILATE actions
- Requires: 030, 031

THEORETICAL FOUNDATION:

**Sparrow's Operational Graph Analysis** (1991):

| Centrality | Operational Question |
|------------|---------------------|
| Degree | Who is most connected? |
| Betweenness | Who bridges subgroups? (Hampton was killed for this) |
| Closeness | Who reaches everyone fastest? |
| Eigenvector | Who connects to important people? |
| Flow betweenness | Who controls resource flows? |
| Information | Who holds irreplaceable knowledge? |

| Equivalence | Targeting Implication |
|-------------|---------------------|
| Structural | Truly interchangeable — targeting pointless |
| Automorphic | Functionally interchangeable — target all or none |
| Regular | Same role, different connections — target the role |

Equivalence class SIZE = targeting value. Singleton = irreplaceable. Large = fungible.

**Numerical Signatures Algorithm** (Sparrow 1993):
O(edges) per iteration. π-product exploits transcendentality.
SPAN refinement, directed graph extension, multiplex extension.

**The Observation Gap** (G_observed ≠ G_actual):

```python
class ObservationModel(BaseModel):
    phone_metadata: bool
    financial_records: bool
    social_media: bool
    location_data: bool
    informant_reports: bool
    public_records: bool

    @computed_field
    def observation_ceiling(self) -> float:
        sources = [self.phone_metadata, self.financial_records,
                   self.social_media, self.location_data,
                   self.informant_reports, self.public_records]
        base = sum(0.15 if s else 0 for s in sources[:3])
        minor = sum(0.08 if s else 0 for s in sources[3:])
        return min(base + minor, 0.65)
```

Distortions: edge type conflation, temporal flattening, denominator explosion,
informant incentive distortion, cash invisibility, face-to-face blindness.

**Three State Targeting Strategies** (not mutually exclusive):

1. **Network surgery** (Sparrow-classic): Target high-centrality nodes,
   sever cutsets, fragment solidarity network. Expensive, requires intel.

2. **Community infrastructure attack**: Target community-level resources
   (defund healthcare, ICE raids, close gathering spaces). Cheaper than
   node-by-node targeting. Raises reproduction costs for entire hyperedge.

3. **Ideological warfare**: ASSIMILATE actions that attack collective_identity.
   "We're all Americans" messaging. Fund assimilationist organizations within
   marginalized communities. Cheapest strategy, prevents revolutionary
   consciousness from forming. The state's PREFERRED strategy when it works.

The state escalates: ideological warfare → infrastructure attack → network surgery.
If ASSIMILATE keeps collective_identity low, the state doesn't NEED to do
expensive surveillance and targeted disruption. Revolutionary consciousness
is the trigger that forces the state to escalate.

**Community-Level Targeting**:
```python
class AttentionThread(BaseModel):
    id: str
    owner_org_id: str
    target_org_id: str | None
    target_territory_id: str | None
    target_community: CommunityType | None  # Can target a community

    phase: ThreadPhase  # DORMANT | MONITORING | ACTIVE_INVESTIGATION | DISRUPTION
    intensity: float
    observed_subgraph: set[str]
    observed_edges: set[tuple[str, str]]
    intel_completeness: float

    # Sparrow analysis (computed when intel sufficient)
    known_centralities: dict[str, float] | None
    known_equivalence_classes: list[set[str]] | None
    identified_singletons: list[str] | None
    known_cutsets: list[set[str]] | None

    ooda_state: OODAPhase
    stickiness: float
    ticks_active: int
```

**Meta-OODA**: Which threats get threads?
  Decision factors: heat level, collective_identity of communities org operates in
  (high collective_identity = higher threat priority), org size, recent actions.

**Thread-Level OODA**:
  OBSERVE → expand observed_subgraph
  ORIENT → Sparrow analysis on observed portion
  DECIDE → choose: network surgery, infrastructure attack, or ideological warfare
  ACT → execute

**Five Revolutionary Counter-Strategies**:
1. OVERWHELM: Generate too many targets
2. DECOY: High-visibility low-value targets absorb threads
3. COMPARTMENTALIZE: Cell structure limits observation ceiling
4. COUNTER-INTEL: Detect/remove infiltrators
5. LEGITIMACY SHIELD: Public support makes repression costly

**Consciousness as Threat Trigger**:
Rising collective_identity within a community is the signal that triggers state
escalation. The state monitors consciousness (through informants, social media
analysis, public statements) and escalates when assimilation is failing.
This creates the dialectic: revolutionary education → state escalation →
repression either crushes or radicalizes → consciousness either retreats or advances.

REQUIRED OUTPUTS:

**Models**:
- AttentionThread (frozen Pydantic) with target_community option
- ObservationModel
- SparrowAnalysis
- ThreadAllocationStrategy (factors in community consciousness levels)

**Systems**:
- AttentionSystem (Layer 1)
- Thread allocation sensitive to collective_identity levels
- Three targeting strategies: network surgery, infrastructure, ideological
- Escalation logic: ideological → infrastructure → surgery

**Sparrow Algorithms**:
- compute_numerical_signatures(G, iterations)
- compute_equivalence_classes(signatures)
- find_singletons(classes)
- find_minimal_cutsets(G, max_size)
- resilience_report(G) (Sword of Damocles)

VALIDATION CRITERIA:
- FBI max_threads=5 enforced
- Thread intel accumulates over time
- Star hub identified as singleton; mesh has larger classes
- Cell topology limits intel_completeness
- State escalates to network surgery ONLY when collective_identity is high
- Low collective_identity → state prefers ASSIMILATE (cheaper)
- High collective_identity → state escalates to infrastructure attacks and surveillance
- State can target community infrastructure, not just org nodes
- State makes mistakes (G_observed ≠ G_actual)
- Detroit test: FBI thread allocation across orgs and communities

CONSTRAINTS:
- State not omniscient
- Sparrow on G_observed, not G_actual
- Different agencies, different ObservationModels
- Escalation logic emergent, not scripted
- No magic constants

REFERENCES:
- Sparrow 1991, 1993
- state-repression-research.md
- Hoover memo 1968, Palantir, Big Floyd
```

---

## Phase 4: Bifurcation Topology Analysis

### Spec ID: `033-bifurcation-topology`

### Prompt:

```
Create a specification for Bifurcation Topology Analysis — the George Jackson model,
extended with community consciousness weighting.

CONTEXT:
- Central prediction: does crisis produce fascism or revolution?
- Depends on solidarity topology AND community consciousness at crisis moment
- Community hyperedges (IMPLEMENTED) provide both cross-class bridges AND
  axes of lateral antagonism (contradiction pairs)
- CommunityConsciousness (IMPLEMENTED) determines whether solidarity edges
  carry revolutionary or assimilationist content
- Requires: 030, community hyperedge layer (IMPLEMENTED)

THEORETICAL FOUNDATION:

**The George Jackson Bifurcation**:
Crisis → two attractors determined by topology + consciousness:
- Cross-line solidarity with revolutionary consciousness → revolution
- Within-group solidarity OR assimilationist consciousness → fascism

**Critical extension: consciousness-weighted solidarity**:

Cross-line solidarity between communities with high collective_identity is
qualitatively different from cross-line solidarity between assimilated communities.

- A SOLIDARISTIC edge between a NEW_AFRIKAN worker (collective_identity=0.8)
  and a white worker (who recognizes settler privilege) carries revolutionary
  potential — it's solidarity built on acknowledged structural opposition.

- A SOLIDARISTIC edge between a NEW_AFRIKAN worker (collective_identity=0.1,
  assimilated, "we're all Americans") and a white worker carries NO
  revolutionary potential — it's solidarity that denies the contradiction.
  Under crisis, this edge is the first to break.

The second type of solidarity is what the Democratic Party produces.
It looks like cross-line solidarity in the graph but has no revolutionary content.

```python
def consciousness_weighted_solidarity(edge, G, H) -> float:
    """Weight a solidarity edge by the consciousness of the communities involved."""
    source_communities = get_community_memberships(edge.source, H)
    target_communities = get_community_memberships(edge.target, H)

    # Average collective_identity of members' marginalized communities
    source_ci = mean(community_consciousness[c].collective_identity
                     for c in source_communities if c.is_marginalized)
    target_ci = mean(community_consciousness[c].collective_identity
                     for c in target_communities if c.is_marginalized)

    # Solidarity with revolutionary consciousness = revolutionary potential
    # Solidarity with assimilationist consciousness = fragile, breaks under crisis
    return edge.resilience * min(source_ci, target_ci)
```

**Multiple Axes of Contradiction**:
Not one colonial divide — multiple axes from contradiction pairs:
- SETTLER ↔ {colonized nations}: primary colonial axis
- PATRIARCHAL ↔ {WOMEN, TRANS}: reproductive labor axis

Each axis where lateral antagonism dominates → one more dimension toward fascism.
State activates multiple axes simultaneously (racial + gender + immigration panic).

**Community Bridges**:
Hyperedges spanning contradiction pairs = intersectionality emerging from graph:
- DISABLED spans colonial divide → potential bridge
- INCARCERATED spans patriarchal axis
- A Black trans person in both colonial AND patriarchal contradiction pairs
  does double bridge-building duty

BUT: bridge potential only activates if collective_identity is high enough.
A DISABLED community with collective_identity=0.1 (fully assimilated, "we're
all just people") provides no bridge. The same community at 0.8 (oppositional
consciousness, disability justice framework) bridges actively.

**Bifurcation Computation**:
```python
def bifurcation_tendency(G, H, consciousness) -> BifurcationResult:
    # Per contradiction axis
    for axis in contradiction_pairs:
        cross = consciousness_weighted_solidarity_edges_crossing(axis, G, H, consciousness)
        lateral = antagonistic_edges_along(axis, G)
        axis_tendency[axis] = cross / (lateral + epsilon)

    # Community bridges (weighted by collective_identity)
    bridges = communities_spanning_axes(H)
    bridge_potential = sum(
        bridge.infrastructure * consciousness[bridge.type].collective_identity
        for bridge in bridges
    )

    # Legitimation crisis amplifier (D-P-D')
    legitimation = compute_legitimation_index(G, H)
    crisis_intensity = base_crisis * (1 / (legitimation + epsilon))

    # Sparrow resilience
    equiv_classes = compute_equivalence_classes(solidarity_subgraph)
    resilience = mean_class_size(equiv_classes)

    return BifurcationResult(...)
```

**Material Constraints on Solidarity**:
- wage_gap_ratio > 10 → ceiling 0.3
- wage_gap_ratio < 2 → ceiling 0.9
- geographic_proximity required
- shared_exploitation_source +0.2
- shared_community_membership raises ceiling
- BUT: ceiling only applies to FORMING new solidarity edges
  Consciousness determines whether existing edges carry revolutionary content

**Betti Numbers**:
- β₀: components (fragmentation)
- β₁: cycles (redundancy = resilience)
Ideal: P(t) = 1 + kt (high β₁, zero β₂)

**The Assimilation Trap in Bifurcation**:
A graph can have high cross-line solidarity density AND still produce fascism
if that solidarity is assimilationist. The Democratic Party coalition is
exactly this: high cross-line edge density, near-zero collective_identity.
Under crisis, these edges break because they deny the contradiction that
the crisis exposes. The simulation must capture this.

REQUIRED OUTPUTS:

**Analysis Functions**:
- crosses_contradiction_axis(edge, G, axis) -> bool
- antagonism_direction(edge, G) -> str
- consciousness_weighted_solidarity(edge, G, H, consciousness) -> float
- bifurcation_tendency(G, H, consciousness) -> BifurcationResult
- solidarity_ceiling(node_a, node_b, G, H) -> float
- communities_spanning_axes(H, consciousness) -> list with weights
- compute_legitimation_index(G, H) -> float

**BifurcationResult Model**:
```python
class BifurcationResult(BaseModel):
    overall_tendency: Literal["revolutionary", "fascist", "indeterminate"]
    per_axis_tendency: dict[str, float]

    # Raw counts
    cross_line_solidarity_count: int
    within_line_solidarity_count: int
    lateral_antagonism_count: int
    upward_antagonism_count: int

    # Consciousness-weighted
    consciousness_weighted_cross_solidarity: float
    mean_collective_identity_marginalized: float
    dominant_tendency_distribution: dict[ConsciousnessTendency, float]

    # Community bridges
    community_bridge_count: int
    bridge_potential_weighted: float  # weighted by collective_identity

    # D-P-D'
    legitimation_index: float

    # Topology
    beta_0: int
    beta_1: int
    resilience_under_targeted_purge: float
    equivalence_class_distribution: dict[int, int]
    critical_singletons: list[str]
    critical_cutsets: list[set[str]]
```

VALIDATION CRITERIA:
- Pure within-group solidarity → fascist
- Cross-line solidarity with high collective_identity → revolutionary
- Cross-line solidarity with LOW collective_identity → STILL FASCIST
  (the assimilation trap — this is the critical test)
- DISABLED community with high collective_identity bridges divide
- DISABLED community with low collective_identity does NOT bridge
- Multiple axes of lateral antagonism reinforces fascism
- Low legitimation amplifies crisis
- Star: low resilience. Mesh: high.
- Large equivalence classes → higher resilience
- Detroit: Wayne ↔ Oakland solidarity weighted by consciousness

CONSTRAINTS:
- β₂ optional (giotto-tda)
- Core uses β₀, β₁ (pure NetworkX)
- Must integrate with EXISTING EdgeMode and community hyperedge layer
- Consciousness weighting must NOT collapse to a simple scalar multiplication —
  it's a qualitative filter (assimilated solidarity breaks under crisis stress)
```

---

## Phase 5: NPC Faction AI (Stub)

### Spec ID: `034-npc-faction-ai-stub`

### Prompt:

```
Create a specification for NPC Faction AI — stub implementation with
consciousness-aware behavior.

CONTEXT:
- Player controls one PoliticalFaction. All others need AI.
- STUB: rule-based heuristics
- Each org type has a consciousness_strategy that determines how it affects
  community consciousness through its actions
- Requires: 030 through 033

**StateApparatus AI**:
1. Meta-OODA: Allocate threads based on heat AND collective_identity
   (rising consciousness = rising threat)
2. PREFER ideological warfare (ASSIMILATE) when collective_identity is low
   — cheaper than surveillance
3. ESCALATE to infrastructure attacks when ASSIMILATE fails
4. ESCALATE to network surgery (Sparrow analysis) when collective_identity
   crosses threshold despite infrastructure attacks
5. Can fund/support assimilationist organizations within marginalized communities
   (liberal civil society orgs that lower collective_identity)
6. Activate lateral antagonism along contradiction pair axes (anti-trans panic,
   anti-immigrant rhetoric via media/policy)

**Business AI**:
1. EMPLOY from cheapest pool, prefer ADULT (P-phase)
2. Resist organizing. When strike threatened, lobby StateApparatus for support.
3. Consciousness effect: employment reinforces "we're all just workers" framing
   (implicitly assimilationist — identity is irrelevant in the workplace)

**CivilSocietyOrg AI** (varies by consciousness_tendency):
- Liberal (consciousness_tendency=ASSIMILATIONIST_LIBERAL):
  1. PROVIDE_SERVICE — meet needs within existing system
  2. EDUCATE with inclusion framing ("diversity is our strength")
  3. Avoids confrontation with state. Shifts LOW_PROFILE when heat rises.
  4. Net effect: lowers collective_identity by providing material relief
     without structural analysis

- Conservative/reactionary (tendency=ASSIMILATIONIST_FASCIST):
  1. PROVIDE_SERVICE to in-group only
  2. EDUCATE with exclusionary framing
  3. Reinforces hegemonic community (SETTLER, PATRIARCHAL) cohesion
  4. Net effect: raises lateral antagonism along contradiction axes

- Radical (tendency=REVOLUTIONARY):
  1. PROVIDE_SERVICE as demonstration of alternative (mutual aid)
  2. BUILD_INFRASTRUCTURE for marginalized communities
  3. Net effect: raises collective_identity, builds community capacity

**Rival PoliticalFaction AI** (varies by consciousness_strategy):
- Revolutionary rival:
  1. RECRUIT along community lines, prioritize shared hyperedge
  2. EDUCATE to raise collective_identity
  3. Compete with player for revolutionary base
  4. May PROPOSE_ALLIANCE against state (united front)

- Liberal rival:
  1. RECRUIT broadly, "big tent" approach
  2. Push ASSIMILATIONIST_LIBERAL consciousness
  3. May compete for same base while depoliticizing it

- Fascist rival:
  1. RECRUIT within SETTLER and PATRIARCHAL hyperedges
  2. AGITATE along contradiction pair axes (activate lateral antagonism)
  3. Fundamentally ANTAGONISTIC to player if player is revolutionary

REQUIRED OUTPUTS:
- NPCDecisionSystem with per-type, per-tendency decision functions
- StateAI with escalation logic: ideological → infrastructure → surgery
- CivilSocietyAI branching on consciousness_tendency
- FactionAI branching on consciousness_strategy
- NPCDecisionStrategy protocol (hot-swap)

VALIDATION CRITERIA:
- 52-tick run without crash
- State prefers ASSIMILATE when collective_identity low
- State escalates to surveillance when collective_identity rises
- Liberal church lowers collective_identity through services
- Revolutionary mutual aid org raises it
- Fascist org activates lateral antagonism in SETTLER hyperedge
- Business prefers ADULT workers
- Rival revolutionary faction competes for same community base

CONSTRAINTS:
- STUB quality
- Deterministic given RNG seed
- No external AI
- Strategy pattern for replacement
```

---

## Phase 6: Organization-Territory Integration

### Spec ID: `035-org-territory-integration`

### Prompt:

```
Create a specification for Organization-Territory Integration.

CONTEXT:
- Organizations operate IN territories (PRESENCE edges)
- Community infrastructure (IMPLEMENTED) is territory-bound
- D-P-D' infrastructure (schools, workplaces, elder care) is spatial
- Consciousness dynamics have a spatial dimension (some territories
  have higher collective_identity than others)
- Requires: 030 through 034

THEORETICAL FOUNDATION:

**Organizations Occupy Territories**:
PRESENCE edge with operational profile: HIGH_PROFILE | LOW_PROFILE

**Heat Mechanics**:
HIGH_PROFILE → heat rises. Threads → more heat. Decay without activity.
Threshold → state response.

**Community Infrastructure Is Territory-Bound**:
Gathering spaces, mutual aid, healthcare exist in SPECIFIC territories.
Displacement severs members from infrastructure.

**Consciousness Geography**:
collective_identity varies spatially. Some neighborhoods have higher
oppositional consciousness than others (historical organizing, institutional
presence, community density). Organizations EDUCATE in specific territories,
so consciousness shifts are local before they're community-wide.

**D-P-D' Infrastructure**:
- Schools (D-phase) in specific territories — control these, control
  ideological transmission to next generation
- Workplaces (P-phase) in specific territories
- Elder care (D'-phase) in specific territories
- Org controlling a school: EDUCATE action on YOUTH members in that territory.
  Consciousness_strategy of the controlling org determines what gets taught.

**Eviction as Consciousness Disruption**:
Displacement doesn't just sever community infrastructure — it disrupts
consciousness by scattering an organized community. Gentrification is
precisely this: displace a community with high collective_identity,
replace with settlers who have low collective_identity. The territory
"flips" ideologically as well as demographically.

REQUIRED OUTPUTS:
- PresenceEdge, TerritoryHeatEvent
- heat_accumulation/decay
- eviction_check
- recruitment_eligibility(org, territory, class, communities)
- Community infrastructure damage on eviction
- Consciousness geography (collective_identity varies by territory)
- D-P-D' infrastructure spatial mapping
- Eviction as consciousness disruption mechanic

VALIDATION CRITERIA:
- HIGH_PROFILE → faster heat
- Cannot RECRUIT without PRESENCE
- Community infrastructure damaged on eviction
- Eviction scatters organized community, lowering local collective_identity
- School control → shapes YOUTH consciousness
- Detroit: Wayne vs Oakland heat + consciousness dynamics

CONSTRAINTS:
- H3 resolution 7 for Detroit
- Heat float [0,1]
- H3 k-ring adjacency
```

---

## Dependency Graph

```
Community Hyperedge Layer + CommunityConsciousness (IMPLEMENTED) ──────┐
                                                                       │
030-organization-base-model (consciousness_strategy on orgs) ──────────┤
    │                                                                  │
    ├── 031-ooda-loop-system (EDUCATE/AGITATE/ASSIMILATE actions) ─────┤
    │       │                                                          │
    │       ├── 032-attention-thread-system (consciousness as threat)   │
    │       │       └── 035-org-territory-integration                   │
    │       │                                                          │
    │       └── 034-npc-faction-ai-stub (consciousness-aware behavior) │
    │                                                                  │
    └── 033-bifurcation-topology (consciousness-weighted edges) ←──────┘
```

Recommended order: 030 → 031 → 033 → 032 → 034 → 035

- 033 (bifurcation) is the OUTCOME VARIABLE — validate early
- 032 (attention threads) most complex, benefits from stable foundation
- 034 + 035 tie everything together for end-to-end testing

---

## Cross-Cutting Concerns

### The Material-Ideological Distinction

Every community hyperedge has:
- Material basis (objective): extraction, exclusion, or structural position
- Ideological dimension (CommunityConsciousness): whether members recognize
  separate material interests

This distinction appears in every spec:
| Spec | Material Dimension | Ideological Dimension |
|------|-------------------|----------------------|
| 030 | Org class_character | Org consciousness_strategy |
| 031 | Action resource costs | Action consciousness side-effects |
| 032 | State targeting (nodes, infrastructure) | State ideological warfare (ASSIMILATE) |
| 033 | Solidarity edge topology | Consciousness-weighted solidarity |
| 034 | NPC class-interest behavior | NPC consciousness_tendency drives messaging |
| 035 | Territory material conditions | Consciousness geography, eviction as ideological disruption |

### The Assimilation/Revolution Dialectic

Three tendencies, present in every spec:

**ASSIMILATIONIST_LIBERAL**: "Expand the definition." Democratic Party coalition.
Produces cross-line solidarity that LOOKS revolutionary in the graph but breaks
under crisis because it denies the structural contradiction.

**ASSIMILATIONIST_FASCIST**: "Shrink the definition." MAGA. Activates lateral
antagonism along contradiction pair axes. Recruits from SETTLER and PATRIARCHAL
hegemonic hyperedges.

**REVOLUTIONARY**: "The contradiction is structural." Builds oppositional
collective identity. Produces solidarity that HOLDS under crisis because it's
built on acknowledged material opposition.

The simulation's central prediction (bifurcation) depends on which tendency
dominates at the moment of crisis. This is what the player is fighting over.

### Sparrow Thread

| Phase | Role |
|-------|------|
| 030 | IntelMethodology (what state CAN do) |
| 032 | SparrowAnalysis (what state COMPUTES on G_observed) |
| 032 | Escalation trigger (consciousness levels determine state strategy) |
| 033 | Defensive analysis (singletons, cutsets in BifurcationResult) |
| 034 | StateAI decision-making |

### The Observation Gap As Game Mechanic

G_actual vs G_observed is the strategic space. BUT: consciousness adds another
dimension. The state can observe topology (partially, with distortions) but
consciousness is HARDER to observe — you can see that people are meeting,
but you can't see whether they're developing revolutionary consciousness or
just having a book club. The state infers consciousness from public actions
(protests, statements, publications) which is why HIGH_PROFILE actions
reveal consciousness as well as topology.

### Hyperedge Taxonomy Thread

| Category | Material | Ideological | Where Appears |
|----------|----------|-------------|---------------|
| **Contradiction pairs** | Extraction flows | collective_identity of marginalized side; solidarity/antagonism of hegemonic side | Bifurcation axes (033), state lateral antagonism (032, 034), org recruitment (030, 031) |
| **Institutional exclusion** | Reproduction cost | collective_identity determines whether excluded group sees itself as having separate interests | Infrastructure targeting (032), cross-class bridges (033), action costs (031) |
| **Lifecycle phases** | D-P-D' structural position | Ideological transmission in D-phase; legitimation bargain in D'-phase | Action capacity (031), legitimation index (033), spatial infrastructure (035) |
