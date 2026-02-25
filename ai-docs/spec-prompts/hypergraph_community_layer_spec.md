# Hypergraph Community Layer: Spec-Kit Specification

**Spec ID**: `021-hypergraph-community-layer`
**Purpose**: Formalize community/identity relationships as hyperedges for solidarity computation and state repression modeling
**Created**: 2026-02-25
**Dependencies**: 019-crisis-devaluation, 020-primitive-accumulation-dispossession
**Revision**: Initial draft

---

## Theoretical Foundation Summary

The hypergraph community layer addresses a critical gap in the four-node model: **within-Core solidarity pathways that cross national, gender, sexuality, racial, and disability lines**. Standard graph edges model dyadic relationships (EXPLOITATION, SOLIDARITY, WAGES), but community membership is inherently *n-ary*—multiple agents share membership in a single community simultaneously.

**Key Insight**: Communities are not node attributes but **hyperedges**—first-class entities that connect arbitrary numbers of agents and can themselves be targeted by state action.

**Architectural Principle**: Babylon uses a **dual-graph architecture**:
- **NetworkX** for pairwise relationships where things *flow* (value, solidarity, repression)
- **XGI** for n-ary relationships where entities *share membership* (communities, identity categories)

This is not implementation convenience — it reflects a genuine ontological distinction. Flows are dyadic; membership is n-ary.

**Why Hyperedges, Not Bipartite Simulation**:
The FBI doesn't surveil individuals who happen to share attributes—it targets *communities as units*. COINTELPRO designated "Black Nationalist Hate Groups" as a category and surveilled everyone legible as belonging to it. A bipartite graph could simulate this, but hyperedges make the community-as-target semantics explicit.

---

## Architectural Delineation: NetworkX vs XGI

### The Fundamental Distinction

**NetworkX (pairwise edges):** Relationships where something *flows* between exactly two entities.

**XGI (hyperedges):** Relationships where multiple entities *share membership* in a collective structure.

This is not an implementation convenience — it reflects a genuine ontological difference in what's being modeled.

### Edge Type Classification

| Relationship | Representation | Rationale |
|--------------|----------------|-----------|
| EXPLOITATION | NetworkX DiEdge | Value flows A → B |
| WAGES | NetworkX DiEdge | Money flows employer → worker |
| SOLIDARITY | NetworkX Edge | Concrete relationship between two agents/orgs |
| TRIBUTE | NetworkX DiEdge | Rent/tax flows A → B |
| REPRESSION | NetworkX DiEdge | State violence flows state → target |
| Territory adjacency | NetworkX Edge | Geographic connection A ↔ B |
| Community membership | XGI Hyperedge | N agents share membership simultaneously |
| State designation | XGI Hyperedge attribute | State targets community as unit |

### Conceptual Basis

**Hyperedges are structure** — who shares what with whom. Relatively static. Changes slowly as identity/membership shifts (disability onset, documentation status change, coming out).

**Pairwise edges are dynamics** — what flows between whom. Changes every tick as value, solidarity, and repression propagate through the network.

### Temporal Dynamics

```
Hyperedges (XGI):     α-smoothed updates    (identity is stable)
Pairwise edges (NX):  per-tick updates      (flows are continuous)
Community state:      α-smoothed updates    (heat, cohesion drift slowly)
Membership strength:  α-smoothed updates    (roles shift over months/years)
```

### Causal Relationship

Hyperedge overlap creates *potential*. Pairwise edges realize *actuality*.

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  Hyperedge      │         │    Potential     │         │   Pairwise      │
│  Overlap        │ ──────► │    Function      │ ──────► │   Edge Forms    │
│  (XGI)          │         │    (computed)    │         │   (NetworkX)    │
└─────────────────┘         └──────────────────┘         └─────────────────┘

shared_communities(A,B) → solidarity_potential(A,B) → SOLIDARITY edge A↔B
```

Shared community membership ≠ solidarity. It creates *conditions* for solidarity.
The actual SOLIDARITY edge in NetworkX represents a concrete relationship that
may or may not form between agents who share communities.

```python
# Hyperedge overlap creates solidarity POTENTIAL
potential = solidarity_potential(A, B)  # uses XGI community overlap

# Potential + material conditions → actual solidarity edge
if potential > threshold and organizing_opportunity_exists:
    G.add_edge(A, B, type=EdgeType.SOLIDARITY, strength=computed_strength)
```

### Mathematical Operations by Layer

| Operation | NetworkX | XGI |
|-----------|----------|-----|
| Path from A to B | Shortest path algorithms | N/A — not a flow structure |
| Flow magnitude A → B | Edge weight × flow rate | N/A |
| Who shares communities with A? | Requires bipartite workaround | `H.nodes.memberships(A)` (native) |
| Community centroid influence | N/A | Hypergraph Laplacian |
| Connected components | `nx.connected_components(G)` | `xgi.connected_components(H)` |
| Cycles / redundancy | β₁ of graph | β₁, β₂... of simplicial complex |
| Curvature | Ollivier-Ricci on edges | Hypergraph Ricci on overlaps |
| Percolation threshold | Giant component analysis | Hyperedge percolation |

### Invariants by Layer

**NetworkX invariants (flow topology):**
- β₀: Connected components of solidarity subgraph → fragmentation
- β₁: Cycles in solidarity subgraph → redundancy/resilience
- Percolation: Does giant component span class fractions?
- Ricci curvature: Where is value accumulating? (negative = pinching)

**XGI invariants (membership topology):**
- Hyperedge overlap distribution: How interconnected are communities?
- Hypergraph β₁: Cycles of overlapping communities
- Hypergraph curvature: Positive = cross-cutting structure, Negative = compartmentalization
- Intersection cardinality: Size of multi-community intersections

### The Two Graphs in Practice

```python
class WorldState(BaseModel):
    """Complete simulation state with both graph layers."""

    # === PAIRWISE LAYER (NetworkX) ===
    # Flows, exploitation, solidarity relationships
    flow_graph: nx.DiGraph  # EXPLOITATION, WAGES, TRIBUTE, REPRESSION edges
    solidarity_graph: nx.Graph  # SOLIDARITY edges (undirected)
    territory_graph: nx.Graph  # Geographic adjacency

    # === HYPEREDGE LAYER (XGI) ===
    # Community membership structure
    community_hypergraph: xgi.Hypergraph  # Agents as nodes, communities as hyperedges

    # === STATE ===
    agents: list[Agent]
    territories: list[Territory]
    organizations: list[Organization]
    community_states: dict[CommunityType, CommunityState]

    def rebuild_hypergraph(self) -> None:
        """Rebuild XGI hypergraph from agent community memberships."""
        self.community_hypergraph = build_community_hypergraph(
            self.agents, self.community_states
        )

    def compute_solidarity_potential(self, a: str, b: str) -> float:
        """Use hypergraph to compute potential, may create NetworkX edge."""
        shared = shared_communities(self.community_hypergraph, a, b)
        base = self.get_class_solidarity(a, b)
        community_bonus = 0.1 * len(shared)
        rent_penalty = 0.05 * abs(self.get_phi(a) - self.get_phi(b))
        return base + community_bonus - rent_penalty
```

### Update Frequencies

| Component | Update Frequency | Rationale |
|-----------|------------------|-----------|
| Flow edges (EXPLOITATION, WAGES) | Every tick | Value flows continuously |
| SOLIDARITY edges | Per tick (strength), rare (creation/destruction) | Relationships persist |
| REPRESSION edges | Event-driven | State action is discrete |
| Community membership | Rare events | Identity changes slowly |
| Community state (heat, cohesion) | α-smoothed per tick | Institutional inertia |
| Hypergraph rebuild | When membership changes | Expensive, cache otherwise |

### Why Not Bipartite for Everything?

A bipartite graph (agents ↔ communities) could simulate hyperedges. We use XGI because:

1. **Semantic clarity**: Hyperedge = community as first-class entity, not a node pretending to be a group
2. **Algorithm availability**: XGI provides hypergraph-specific algorithms (Laplacian, centrality, homology)
3. **State targeting**: The FBI targets communities, not membership edges — hyperedge attributes capture this
4. **Curvature**: Hypergraph Ricci curvature measures community interconnection, not agent-community ties

The bipartite representation is always available via `xgi.to_bipartite_graph(H)` if needed for specific NetworkX algorithms.

---

## Core Concepts

### 1. Community as Hyperedge

A **Community** is a hyperedge connecting all agents who belong to it:

```
Community(TRANS) = {agent_1, agent_3, agent_7, agent_12, ...}
Community(NEW_AFRIKAN) = {agent_2, agent_3, agent_5, ...}
```

Note that agent_3 belongs to both—this is the **overlap** that creates cross-cutting solidarity potential.

### 2. Community Types

Communities divide into two categories with different dynamics:

**Identity Communities** (ascribed or deeply integrated):
- NEW_AFRIKAN, FIRST_NATIONS, CHICANO (internal nations)
- QUEER, TRANS (sexuality/gender)
- DISABLED (disability)
- UNDOCUMENTED (documentation status)
- WOMEN (gender—relevant for reproductive labor allocation)

**Organizational Communities** (voluntary affiliation):
- Modeled separately via Organization nodes
- Community membership modulates which organizations agents can effectively join

### 3. Community State

Each community has state independent of its members:

| Attribute | Type | Description |
|-----------|------|-------------|
| `heat` | float [0,1] | State attention/surveillance intensity |
| `legal_status` | enum | LEGAL, SURVEILLED, DESIGNATED_EXTREMIST, DESIGNATED_TERRORIST, CRIMINALIZED |
| `cohesion` | float [0,1] | Internal trust and mutual aid effectiveness |
| `infrastructure` | float [0,1] | Meeting spaces, comms, mutual aid networks |
| `visibility` | float [0,1] | Legibility to state surveillance |
| `reproduction_cost_modifier` | float | Multiplier on V_reproduction for members |
| `rent_access_modifier` | float | Multiplier on Φ received by members |

### 4. Membership Strength

Membership is not binary—agents have varying degrees of integration:

| Role | Weight | Description |
|------|--------|-------------|
| CORE_ORGANIZER | 1.0 | Infrastructure maintainers, visible leaders |
| ACTIVE | 0.7 | Regular participants, known within community |
| PARTICIPANT | 0.4 | Occasional engagement |
| PERIPHERAL | 0.2 | Marginal connection |
| SYMPATHIZER | 0.1 | External ally, not legible as member |

---

## Theoretical Mechanisms

### Solidarity Transmission via Shared Community

Solidarity potential between agents increases with shared community membership:

```
solidarity_potential(A, B) = base_class_solidarity
                           + community_bonus × |communities(A) ∩ communities(B)|
                           - rent_differential_penalty × |Φ_A - Φ_B|
```

**The Rent Differential Penalty**: Even with shared identity, if one group receives full imperial rent and the other receives none, solidarity formation is structurally impeded. This formalizes MIM(Prisons) insight that consciousness follows material conditions.

### Reproduction Cost Modification

Community membership modifies V_reproduction:

```
V_reproduction(agent) = V_base × Π(community.reproduction_cost_modifier for community in agent.communities)
```

Examples:
- DISABLED: +1.2× (healthcare, accessibility costs)
- TRANS: +1.1× (healthcare, documentation, discrimination costs)
- UNDOCUMENTED: +0.9× (excluded from state services) but ×0.7 rent_access

### Community Infrastructure Multiplier

When computing solidarity transmission, community infrastructure amplifies the effect:

```
transmission_multiplier = 1 + Σ(
    community.infrastructure × community.cohesion ×
    source_membership.strength × target_membership.strength
    for community in shared_communities(source, target)
)
```

### State Repression Dynamics

**Agent Threat Score** (how much heat an agent draws):

```
threat_score(agent) = Σ(
    community.heat ×
    membership.visibility ×
    role_weight[membership.role] ×
    legal_status_multiplier[community.legal_status]
    for membership in agent.memberships
)
```

Legal status multipliers:
- LEGAL: 0.1
- SURVEILLED: 0.5
- DESIGNATED_EXTREMIST: 1.0
- DESIGNATED_TERRORIST: 2.0
- CRIMINALIZED: 3.0

**Community-Level Repression Actions**:

| Action | Effect |
|--------|--------|
| `designate_extremist(community)` | legal_status → DESIGNATED_EXTREMIST, heat += 0.3 |
| `infiltrate(community)` | cohesion -= 0.2, creates paranoia |
| `disrupt_infrastructure(community)` | infrastructure -= 0.4, affects all members' V_reproduction |
| `arrest_organizers(community)` | Remove CORE_ORGANIZER members, cohesion -= 0.3 |

**Repression → Material Immiseration**:
When state disrupts community infrastructure, every member's effective reproduction cost increases—they lose mutual aid, healthcare access, social support. Repression creates material harm, not just psychological fear.

---

## Required Data Structures

### CommunityType Enum

```python
class CommunityType(Enum):
    # Internal nations
    NEW_AFRIKAN = auto()
    FIRST_NATIONS = auto()
    CHICANO = auto()

    # Identity categories
    QUEER = auto()
    TRANS = auto()
    DISABLED = auto()
    UNDOCUMENTED = auto()
    WOMEN = auto()

    # Can extend for specific use cases
```

### CommunityState Model

```python
class CommunityState(BaseModel):
    community_type: CommunityType
    heat: float = Field(default=0.0, ge=0.0, le=1.0)
    legal_status: LegalStatus = LegalStatus.LEGAL
    cohesion: float = Field(default=0.5, ge=0.0, le=1.0)
    infrastructure: float = Field(default=0.3, ge=0.0, le=1.0)
    visibility: float = Field(default=0.5, ge=0.0, le=1.0)
    reproduction_cost_modifier: float = Field(default=1.0, ge=0.0)
    rent_access_modifier: float = Field(default=1.0, ge=0.0, le=1.0)
```

### Membership Model

```python
class CommunityMembership(BaseModel):
    agent_id: str
    community_type: CommunityType
    role: MembershipRole = MembershipRole.PARTICIPANT
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    visibility: float = Field(default=0.5, ge=0.0, le=1.0)  # Known to state?
    overt: bool = False  # Publicly identified?
```

### XGI Integration

```python
import xgi
from collections import defaultdict

def build_community_hypergraph(
    agents: list[Agent],
    community_states: dict[CommunityType, CommunityState]
) -> xgi.Hypergraph:
    """Build XGI hypergraph where communities are hyperedges."""
    H = xgi.Hypergraph()

    # Collect members per community
    community_members: dict[CommunityType, list[str]] = defaultdict(list)
    for agent in agents:
        H.add_node(agent.id, **agent.dict(exclude={"communities"}))
        for membership in agent.community_memberships:
            community_members[membership.community_type].append(agent.id)

    # Communities become hyperedges with state attributes
    for comm_type, members in community_members.items():
        if len(members) > 0:
            state = community_states.get(comm_type, CommunityState(community_type=comm_type))
            H.add_edge(members, id=comm_type.value, **state.dict())

    return H

def shared_communities(H: xgi.Hypergraph, agent_a: str, agent_b: str) -> set[str]:
    """Return community IDs shared by both agents."""
    return H.nodes.memberships(agent_a) & H.nodes.memberships(agent_b)

def community_overlap_matrix(H: xgi.Hypergraph) -> np.ndarray:
    """Compute pairwise community overlap for all agents."""
    # XGI provides this via incidence matrix operations
    I = xgi.incidence_matrix(H, sparse=True)
    overlap = I @ I.T  # Agents × Agents, entry = # shared communities
    return overlap.toarray()
```

---

## Validation Criteria

### Structural Validation

- **V-001**: Community hypergraph correctly reflects agent membership (round-trip test)
- **V-002**: shared_communities(A, B) returns correct intersection
- **V-003**: community_overlap_matrix diagonal equals agent community count
- **V-004**: Empty communities (no members) are not added as hyperedges

### Solidarity Computation Validation

- **V-005**: Agents with 2+ shared communities have higher solidarity_potential than those with 0
- **V-006**: Rent differential penalty reduces solidarity_potential for high-Φ / low-Φ pairs
- **V-007**: Community infrastructure multiplier increases transmission for well-organized communities

### Repression Dynamics Validation

- **V-008**: designate_extremist() increases heat for all visible members
- **V-009**: disrupt_infrastructure() increases V_reproduction for all members
- **V-010**: infiltrate() reduces cohesion, which reduces solidarity transmission
- **V-011**: Agents with multiple high-heat memberships have higher threat_score

### Detroit Test Case Validation

- **V-012**: NEW_AFRIKAN community concentrated in Wayne County (>70% of members)
- **V-013**: Community overlap creates solidarity paths between Wayne and Oakland
- **V-014**: State repression of NEW_AFRIKAN community increases V_reproduction for Wayne residents
- **V-015**: George Jackson bifurcation outcome affected by cross-community solidarity topology

---

## Data Requirements

### Calibration Sources

| Data Need | Source | Status |
|-----------|--------|--------|
| Community population estimates | Census ACS, specialized surveys | AVAILABLE |
| reproduction_cost_modifier | Healthcare expenditure surveys, academic literature | ESTIMATED |
| rent_access_modifier | Wage gap studies, immigration economics | ESTIMATED |
| Historical heat levels | COINTELPRO documents, FBI reports | QUALITATIVE |
| Infrastructure estimates | NGO/mutual aid org data | SYNTHETIC |

### Default Calibration Values

```python
COMMUNITY_DEFAULTS = {
    CommunityType.NEW_AFRIKAN: CommunityState(
        community_type=CommunityType.NEW_AFRIKAN,
        heat=0.4,  # Historical targeting
        legal_status=LegalStatus.SURVEILLED,  # Post-Ferguson
        cohesion=0.6,
        infrastructure=0.5,
        visibility=0.8,  # Highly legible
        reproduction_cost_modifier=1.15,  # Healthcare disparities
        rent_access_modifier=0.85,  # Wage gap
    ),
    CommunityType.TRANS: CommunityState(
        community_type=CommunityType.TRANS,
        heat=0.3,  # Rising targeting
        legal_status=LegalStatus.SURVEILLED,
        cohesion=0.7,  # Strong mutual aid
        infrastructure=0.4,
        visibility=0.6,  # Variable
        reproduction_cost_modifier=1.25,  # Healthcare, legal
        rent_access_modifier=0.75,  # Employment discrimination
    ),
    # ... etc
}
```

---

## Dependencies

### Required Prior Specs

- **017-class-dynamics-engine**: Class position determination
- **019-crisis-devaluation**: Crisis triggers that affect community dynamics
- **020-primitive-accumulation-dispossession**: Dispossession events that target communities

### Required Libraries

- **xgi**: Hypergraph data structure and algorithms (`pip install xgi`)
- **networkx**: For non-hyperedge relationships (existing dependency)

### Integration Points

| Component | Integration |
|-----------|-------------|
| WorldState | Add `community_states: dict[CommunityType, CommunityState]` |
| Agent | Add `community_memberships: list[CommunityMembership]` |
| SolidarityCalculator | Modify to use community_overlap_matrix |
| StateRepressionSystem | New system consuming community state |
| V_reproduction calculator | Integrate reproduction_cost_modifier |

---

## Scope

### In Scope

- Community as hyperedge data structure
- XGI integration for hypergraph operations
- Community state (heat, cohesion, infrastructure, legal_status)
- Membership roles and strength
- Solidarity potential computation with community bonus
- State repression mechanics (designate, infiltrate, disrupt)
- V_reproduction modification by community membership

### Out of Scope (Future Extensions)

- **FE-001**: Organization-community relationships (organizations recruit from communities)
- **FE-002**: Community formation dynamics (how new communities emerge)
- **FE-003**: Inter-community coalition modeling
- **FE-004**: Geographic clustering of community membership
- **FE-005**: Temporal dynamics of community cohesion
- **FE-006**: Media/narrative effects on community visibility

---

## Implementation Phases

### Phase 1: Data Structures (MVP)

1. Define CommunityType enum
2. Define CommunityState and CommunityMembership models
3. Add to WorldState schema
4. Implement build_community_hypergraph()
5. Write structural validation tests (V-001 through V-004)

### Phase 2: Solidarity Integration

1. Implement shared_communities() and community_overlap_matrix()
2. Modify solidarity_potential() to include community bonus
3. Implement infrastructure_multiplier for transmission
4. Write solidarity validation tests (V-005 through V-007)

### Phase 3: State Repression

1. Implement StateRepressionSystem with community-level actions
2. Implement threat_score() computation
3. Connect infrastructure degradation to V_reproduction
4. Write repression validation tests (V-008 through V-011)

### Phase 4: Detroit Calibration

1. Calibrate community defaults for Detroit test case
2. Initialize community membership from Census/ACS data
3. Run Detroit scenario and validate (V-012 through V-015)

---

## Usage Notes

1. **XGI is a computational view, not persistence**: Rebuild hypergraph from Pydantic state each tick or cache with incremental updates
2. **Communities are slow-changing**: heat, cohesion, infrastructure update via α-smoothing, not per-tick
3. **Membership can change**: Agents can gain/lose community membership (e.g., disability onset, documentation status change)
4. **Keep NetworkX for dyadic edges**: Use XGI specifically for n-ary community relationships
5. **Flows go in NetworkX, structure goes in XGI**: If something transfers between two entities, it's a NetworkX edge. If multiple entities share membership in something, it's an XGI hyperedge.
6. **Hyperedges create potential, edges realize it**: Community overlap → solidarity_potential() → maybe SOLIDARITY edge forms

---

## 10. Summary: The Dual-Graph Architecture

### Two Graphs, Two Purposes

| Graph | Library | Contains | Updates | Purpose |
|-------|---------|----------|---------|---------|
| Flow/Solidarity Graph | NetworkX | Pairwise edges (EXPLOITATION, SOLIDARITY, WAGES, REPRESSION) | Per tick | Model what flows between entities |
| Community Hypergraph | XGI | N-ary hyperedges (community memberships) | On membership change | Model what entities share |

### The Causal Chain

```
Community Overlap (XGI)
        ↓
Solidarity Potential (computed)
        ↓
SOLIDARITY Edge (NetworkX) ←── requires organizing opportunity
        ↓
Solidarity Transmission (per tick)
        ↓
Consciousness Drift (Morse dynamics)
        ↓
Bifurcation Outcome (George Jackson)
```

### Key Formulas

```
# Solidarity potential with community bonus
solidarity_potential(A, B) = base_class_solidarity
                           + 0.1 × |communities(A) ∩ communities(B)|
                           - 0.05 × |Φ_A - Φ_B|

# Reproduction cost modification
V_reproduction(agent) = V_base × Π(c.reproduction_cost_modifier for c in communities(agent))

# Solidarity transmission with community infrastructure
transmission(source, target) = base_transmission × (
    1 + Σ(c.infrastructure × c.cohesion × strength_source × strength_target
        for c in shared_communities)
)

# Agent threat score
threat_score(agent) = Σ(
    c.heat × m.visibility × role_weight[m.role] × status_mult[c.legal_status]
    for m in memberships(agent), c = community(m)
)

# Repression effect on reproduction
V_reproduction_post_repression = V_reproduction × (1 + 0.2 × Σ(1 - c.infrastructure for c in communities))
```

---

## Theoretical References

- **MIM(Prisons)**: Lumpen as revolutionary subject, national oppression framework
- **George Jackson**: Solidarity topology determines fascism vs revolution
- **Silvia Federici**: Reproductive labor and community as site of resistance
- **COINTELPRO documentation**: Historical model for state repression mechanics
- **Ward Churchill**: COINTELPRO analysis for targeting patterns
