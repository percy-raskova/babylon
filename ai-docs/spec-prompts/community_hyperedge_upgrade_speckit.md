# Community Hyperedge Layer Upgrade: Spec-Kit Prompt

**Purpose**: Upgrade the existing community hyperedge layer (022) with consciousness model, three-category taxonomy, hegemonic hyperedges, and infiltration resistance mechanics
**Usage**: Feed to `/speckit.specify` BEFORE running any org-topology-speckit-prompts-v4 specs
**Prerequisite**: Existing community hyperedge implementation with XGI, CommunityType enum, CommunityNode model, MembershipEdge, and build_community_hypergraph()
**Why this exists**: The org topology specs (030-035) assume community hyperedges have consciousness attributes, a three-category taxonomy, and hegemonic hyperedge members. This upgrade bridges the gap.

---

## Spec ID: `022b-community-hyperedge-upgrade`

### Prompt:

```
Upgrade the existing community hyperedge layer to support consciousness modeling,
three-category taxonomy, hegemonic community hyperedges, and community-level
infiltration resistance.

CONTEXT:
- Community hyperedges are ALREADY IMPLEMENTED via XGI with bipartite NetworkX fallback
- Existing models: CommunityType enum, CommunityNode (heat, cohesion, infrastructure,
  visibility, reproduction_cost_modifier, rent_access_modifier), MembershipEdge
  (role, strength, visibility), build_community_hypergraph()
- This spec UPGRADES the existing implementation, not replaces it
- All existing functionality must be preserved
- The downstream org-topology specs (030-035) depend on this upgrade

WHAT EXISTS (do not break):
- CommunityType enum with QUEER, TRANS, DISABLED, UNDOCUMENTED, NEW_AFRIKAN,
  FIRST_NATIONS, CHICANO
- CommunityNode with heat, cohesion, infrastructure, visibility,
  reproduction_cost_modifier, rent_access_modifier
- MembershipEdge with role, strength, visibility
- CommunityLegalStatus enum
- build_community_hypergraph(agents) -> xgi.Hypergraph
- XGI serialization to/from JSON
- SQLite persistence via existing Ledger

WHAT THIS UPGRADE ADDS:

=== 1. THREE-CATEGORY TAXONOMY ===

Community hyperedges are NOT all the same structural type. There are three
qualitatively distinct categories with different material bases, different
relationships to oppression, and different modeling requirements.

```python
class HyperedgeCategory(Enum):
    CONTRADICTION_PAIR = "contradiction_pair"
    # Both hegemonic and marginalized sides exist as real hyperedges
    # with members, institutions, extraction flows between them.
    # The relationship is EXTRACTIVE — value flows from marginalized to hegemonic.
    # Examples: SETTLER ↔ NEW_AFRIKAN, PATRIARCHAL ↔ WOMEN

    INSTITUTIONAL_EXCLUSION = "institutional_exclusion"
    # Only the marginalized side exists as a real hyperedge.
    # No paired oppressor community — oppression flows through institutional defaults.
    # The "oppressor" isn't a community, it's the structure itself.
    # Examples: DISABLED, QUEER, UNDOCUMENTED, INCARCERATED

    LIFECYCLE_PHASE = "lifecycle_phase"
    # Temporal positions in D-P-D' intergenerational lifecycle.
    # NOT identity communities — structural phases everyone traverses.
    # Universal, temporally permeable, defined by relationship to production.
    # Examples: YOUTH (D), ADULT (P), ELDER (D')
```

Every CommunityType must be assigned to exactly one HyperedgeCategory.
This assignment is FIXED (not runtime-configurable) because it's a
structural property of the community type, not a parameter.

=== 2. NEW COMMUNITY TYPES ===

Add hegemonic-side hyperedges for contradiction pairs and lifecycle phases:

```python
class CommunityType(Enum):
    # === CONTRADICTION PAIR: Colonial axis ===
    # Hegemonic side
    SETTLER = "settler"            # Material basis: land, imperial rent, property regimes
                                   # Has institutions: HOAs, police unions, school boards,
                                   # border militias, MAGA movement
                                   # Active political project defending extraction position

    # Marginalized side (existing — preserve these)
    NEW_AFRIKAN = "new_afrikan"
    FIRST_NATIONS = "first_nations"
    CHICANO = "chicano"

    # === CONTRADICTION PAIR: Patriarchal axis ===
    # Hegemonic side
    PATRIARCHAL = "patriarchal"    # Material basis: unwaged reproductive labor extraction
                                   # Has institutions: patriarchal family structure,
                                   # gendered wage system, religious hierarchies
                                   # Membership defined by material position in extraction,
                                   # NOT gender identity. Trans men do NOT occupy same
                                   # material position as cis men in patriarchy.

    # Marginalized side
    WOMEN = "women"                # NEW — was implicit, now explicit
    TRANS = "trans"                # Existing

    # === INSTITUTIONAL EXCLUSION (marginalized side only) ===
    DISABLED = "disabled"          # Existing
    QUEER = "queer"                # Existing
    UNDOCUMENTED = "undocumented"  # Existing
    INCARCERATED = "incarcerated"  # NEW — current or formerly incarcerated

    # === LIFECYCLE PHASES (D-P-D' circuit) ===
    YOUTH = "youth"                # D phase — pre-productive, receives socialization
    ADULT = "adult"                # P phase — productive, sells labor-power
    ELDER = "elder"                # D' phase — post-productive, legitimation bargain
```

=== 3. CONTRADICTION PAIR AXIS FORMALIZATION ===

Contradiction pairs are formalized as axes with hegemonic and marginalized sides.
This is not just a grouping convenience — the axis defines the EXTRACTION
RELATIONSHIP between paired hyperedges and determines what "crossing the line"
means in bifurcation analysis.

```python
class ContradictionAxis(BaseModel):
    """A structural axis of contradiction between hegemonic and marginalized communities.

    The axis defines an extraction relationship: value flows from
    marginalized to hegemonic through measurable mechanisms.
    """
    id: str
    name: str  # "colonial", "patriarchal"

    hegemonic: CommunityType          # SETTLER, PATRIARCHAL
    marginalized: list[CommunityType] # [NEW_AFRIKAN, FIRST_NATIONS, CHICANO], [WOMEN, TRANS]

    extraction_mechanism: str         # Human-readable description of how value flows
    # Colonial: "Land theft, imperial rent, carceral labor, property value regimes, wage theft"
    # Patriarchal: "Unwaged reproductive labor extraction, wage gap, care externalization"

    exclusive: bool
    # Colonial axis: mostly exclusive (socially assigned racial category)
    # Patriarchal axis: mostly exclusive (material position in extraction system)

    permeable: bool
    # Colonial: False (race is socially fixed in US context)
    # Patriarchal: low permeability (gender transition changes position, but slowly)
```

Define exactly two axes for initial implementation:

COLONIAL_AXIS = ContradictionAxis(
    id="colonial", name="Colonial",
    hegemonic=CommunityType.SETTLER,
    marginalized=[CommunityType.NEW_AFRIKAN, CommunityType.FIRST_NATIONS, CommunityType.CHICANO],
    extraction_mechanism="Land, imperial rent, carceral labor, property value regimes",
    exclusive=True, permeable=False
)

PATRIARCHAL_AXIS = ContradictionAxis(
    id="patriarchal", name="Patriarchal",
    hegemonic=CommunityType.PATRIARCHAL,
    marginalized=[CommunityType.WOMEN, CommunityType.TRANS],
    extraction_mechanism="Unwaged reproductive labor, wage gap, care externalization",
    exclusive=True, permeable=False
)

Store these as module-level constants, not database records. They're theoretical
structure, not runtime state.

=== 4. COMMUNITY CONSCIOUSNESS MODEL ===

Every community hyperedge has two dimensions: material basis (objective, already
modeled via infrastructure, reproduction_cost_modifier, etc.) and ideological
dimension (subjective, NEW in this upgrade).

The GAP between material basis and ideological self-understanding is the
terrain of political struggle. This is class-in-itself vs class-for-itself
generalized across all contradiction axes.

```python
class ConsciousnessTendency(Enum):
    ASSIMILATIONIST_LIBERAL = "assimilationist_liberal"
    # "Expand the definition, let us in."
    # Gay marriage, Black CEOs, women in combat roles.
    # Seeks inclusion in existing institutions without transforming them.
    # Works for SOME members (closest to hegemonic side on other axes).
    # Leaves structural extraction intact.
    # Organizational vehicle: liberal CivilSocietyOrgs, Democratic Party.

    ASSIMILATIONIST_FASCIST = "assimilationist_fascist"
    # "We're the good ones, exclude the others."
    # Respectability politics taken to extreme.
    # Collaboration with hegemonic order for individual escape.
    # Strategy: shrink the marginalized definition, exclude the most marginal.
    # Organizational vehicle: conservative wings within marginalized communities.

    REVOLUTIONARY = "revolutionary"
    # "Our interests are structurally opposed. Integration is impossible."
    # The contradiction is material, not a misunderstanding.
    # No amount of representation resolves structural extraction.
    # Strategy: oppositional collective identity, independent power.
    # Organizational vehicle: revolutionary PoliticalFactions.


class CommunityConsciousness(BaseModel):
    """The ideological dimension of a community hyperedge.

    Tracks the gap between material basis (objective position in
    extraction/exclusion/lifecycle) and collective self-understanding
    (whether members recognize separate material interests).

    This is class-in-itself vs class-for-itself, generalized.
    """
    collective_identity: float = Field(default=0.3, ge=0.0, le=1.0)
    # What fraction of members identify as having separate material interests
    # from the hegemonic order?
    # 0.0 = fully assimilated ("we're all Americans")
    # 1.0 = full oppositional consciousness ("our interests are structurally opposed")
    #
    # NOTE: Hegemonic hyperedges (SETTLER, PATRIARCHAL) also have this field,
    # but it means something different: it measures how consciously the hegemonic
    # group defends its extraction position. High collective_identity on SETTLER
    # = active white nationalist consciousness. Low = passive beneficiary.

    dominant_tendency: ConsciousnessTendency = ConsciousnessTendency.ASSIMILATIONIST_LIBERAL
    # What is the prevailing ideological tendency within this community?
    # This is the DEFAULT direction members drift without active organizing.
    # The state works to keep this at ASSIMILATIONIST_LIBERAL for marginalized
    # communities and at ASSIMILATIONIST_FASCIST for hegemonic communities.

    ideological_contestation: float = Field(default=0.2, ge=0.0, le=1.0)
    # How actively contested is the ideological terrain?
    # Low = consensus (everyone agrees on direction, whichever it is)
    # High = active struggle between tendencies within the community
    # Agitation RAISES this (exposes contradictions, provokes debate).
    # Education can LOWER this by winning the argument (building consensus
    # around one tendency).
```

**Consciousness on hegemonic vs marginalized hyperedges**:

For MARGINALIZED communities:
- collective_identity measures oppositional consciousness
- High CI = "we have separate interests from the hegemonic order"
- Revolutionary orgs try to raise it; state tries to lower it

For HEGEMONIC communities (SETTLER, PATRIARCHAL):
- collective_identity measures defensive consciousness
- High CI = active defense of extraction position (white nationalism, patriarchal reaction)
- Low CI = passive beneficiary ("I don't see color", "I'm not sexist")
- Fascist orgs try to raise it (activate lateral antagonism)
- Liberal state tries to keep it moderate (enough to maintain extraction,
  not so much that it destabilizes — fascism is useful but dangerous)

For LIFECYCLE phases:
- collective_identity is less relevant (everyone passes through)
- BUT: ideological_contestation matters for D-phase (what gets taught to youth)
- AND: dominant_tendency matters for D'-phase (do elders support or resist
  the legitimation bargain?)

=== 5. INFILTRATION RESISTANCE ===

A community's collective_identity directly affects the state's ability to
infiltrate organizations embedded within that community. This is not a metaphor —
a community where "don't talk to cops" is survival knowledge learned from birth
has organic counter-intelligence that no formal COUNTER_INTEL process can match.

```python
class CommunityState(BaseModel):
    """Full state of a community hyperedge.

    EXTENDS existing CommunityNode — preserve all existing fields,
    add consciousness and infiltration resistance.
    """
    # === EXISTING FIELDS (preserve) ===
    id: str
    community_type: CommunityType
    heat: float = Field(default=0.0, ge=0.0, le=1.0)
    legal_status: CommunityLegalStatus = CommunityLegalStatus.LEGAL
    cohesion: float = Field(default=0.5, ge=0.0, le=1.0)
    infrastructure: float = Field(default=0.5, ge=0.0, le=1.0)
    visibility: float = Field(default=0.5, ge=0.0, le=1.0)
    reproduction_cost_modifier: float = Field(default=1.0)
    rent_access_modifier: float = Field(default=1.0)

    # === NEW: Taxonomy ===
    category: HyperedgeCategory
    # Assigned from CommunityType mapping, not user-configurable

    # === NEW: Consciousness ===
    consciousness: CommunityConsciousness = Field(default_factory=CommunityConsciousness)

    # === NEW: Infiltration resistance ===
    @computed_field
    def infiltration_resistance(self) -> float:
        """How resistant this community is to state infiltration.

        High collective_identity → community treats state as adversary →
        informants face social death → fewer willing informants →
        state's infiltration success drops.

        This modifies the observation_ceiling of any AttentionThread
        targeting organizations embedded in this community.
        """
        # Base resistance from collective identity
        ci_factor = self.consciousness.collective_identity

        # Social closure (cohesion) amplifies resistance
        # Tight community where everyone knows everyone = organic vetting
        closure_factor = self.cohesion

        # Combined: both consciousness AND social density needed
        # High CI + low cohesion = people hate cops but don't know each other
        #   (infiltrator blends in because nobody checks)
        # Low CI + high cohesion = tight community but cooperates with state
        #   (infiltrator is noticed but nobody cares)
        # High CI + high cohesion = maximum resistance
        #   (infiltrator is noticed AND reported/excluded)
        return ci_factor * 0.6 + closure_factor * 0.3 + ci_factor * closure_factor * 0.1

    # === NEW: Cross-class bridge detection ===
    @computed_field
    def is_cross_class_bridge(self) -> bool:
        """Does this community span a contradiction axis?

        Only meaningful for INSTITUTIONAL_EXCLUSION communities.
        DISABLED includes both SETTLER and colonized members.
        INCARCERATED spans the patriarchal axis.

        Contradiction pairs are the AXIS, not the bridge.
        Lifecycle phases bridge by default (everyone goes through them).
        """
        return self.category == HyperedgeCategory.INSTITUTIONAL_EXCLUSION
        # Refined at runtime by checking actual member composition
```

=== 6. COMMUNITY TYPE → CATEGORY MAPPING ===

```python
COMMUNITY_CATEGORY_MAP: dict[CommunityType, HyperedgeCategory] = {
    # Contradiction pairs — hegemonic side
    CommunityType.SETTLER: HyperedgeCategory.CONTRADICTION_PAIR,
    CommunityType.PATRIARCHAL: HyperedgeCategory.CONTRADICTION_PAIR,

    # Contradiction pairs — marginalized side
    CommunityType.NEW_AFRIKAN: HyperedgeCategory.CONTRADICTION_PAIR,
    CommunityType.FIRST_NATIONS: HyperedgeCategory.CONTRADICTION_PAIR,
    CommunityType.CHICANO: HyperedgeCategory.CONTRADICTION_PAIR,
    CommunityType.WOMEN: HyperedgeCategory.CONTRADICTION_PAIR,
    CommunityType.TRANS: HyperedgeCategory.CONTRADICTION_PAIR,

    # Institutional exclusion
    CommunityType.DISABLED: HyperedgeCategory.INSTITUTIONAL_EXCLUSION,
    CommunityType.QUEER: HyperedgeCategory.INSTITUTIONAL_EXCLUSION,
    CommunityType.UNDOCUMENTED: HyperedgeCategory.INSTITUTIONAL_EXCLUSION,
    CommunityType.INCARCERATED: HyperedgeCategory.INSTITUTIONAL_EXCLUSION,

    # Lifecycle phases
    CommunityType.YOUTH: HyperedgeCategory.LIFECYCLE_PHASE,
    CommunityType.ADULT: HyperedgeCategory.LIFECYCLE_PHASE,
    CommunityType.ELDER: HyperedgeCategory.LIFECYCLE_PHASE,
}
```

Which side of a contradiction axis a community is on:

```python
HEGEMONIC_COMMUNITIES = {CommunityType.SETTLER, CommunityType.PATRIARCHAL}
MARGINALIZED_COMMUNITIES = {
    CommunityType.NEW_AFRIKAN, CommunityType.FIRST_NATIONS, CommunityType.CHICANO,
    CommunityType.WOMEN, CommunityType.TRANS,
    CommunityType.DISABLED, CommunityType.QUEER,
    CommunityType.UNDOCUMENTED, CommunityType.INCARCERATED,
}
LIFECYCLE_COMMUNITIES = {CommunityType.YOUTH, CommunityType.ADULT, CommunityType.ELDER}
```

=== 7. CONSCIOUSNESS DEFAULTS BY COMMUNITY TYPE ===

Initial consciousness values for Detroit test case. These are STARTING
conditions reflecting the ideological terrain as of simulation start (2010).
They will change over the course of the simulation through org actions.

```python
CONSCIOUSNESS_DEFAULTS: dict[CommunityType, CommunityConsciousness] = {
    # Hegemonic — moderate defensive consciousness, low contestation
    CommunityType.SETTLER: CommunityConsciousness(
        collective_identity=0.4,  # Passive beneficiary, some active defense
        dominant_tendency=ConsciousnessTendency.ASSIMILATIONIST_LIBERAL,
        ideological_contestation=0.3,  # Some tension between liberal and fascist
    ),
    CommunityType.PATRIARCHAL: CommunityConsciousness(
        collective_identity=0.3,  # Mostly passive, naturalized
        dominant_tendency=ConsciousnessTendency.ASSIMILATIONIST_LIBERAL,
        ideological_contestation=0.2,
    ),

    # Colonial axis — marginalized side
    CommunityType.NEW_AFRIKAN: CommunityConsciousness(
        collective_identity=0.5,  # Significant historical consciousness in Detroit
        dominant_tendency=ConsciousnessTendency.ASSIMILATIONIST_LIBERAL,
        ideological_contestation=0.4,  # Active debate between liberal/revolutionary
    ),
    CommunityType.FIRST_NATIONS: CommunityConsciousness(
        collective_identity=0.6,  # Strong sovereign identity
        dominant_tendency=ConsciousnessTendency.REVOLUTIONARY,  # Sovereignty framing
        ideological_contestation=0.3,
    ),
    CommunityType.CHICANO: CommunityConsciousness(
        collective_identity=0.4,
        dominant_tendency=ConsciousnessTendency.ASSIMILATIONIST_LIBERAL,
        ideological_contestation=0.3,
    ),

    # Patriarchal axis — marginalized side
    CommunityType.WOMEN: CommunityConsciousness(
        collective_identity=0.3,
        dominant_tendency=ConsciousnessTendency.ASSIMILATIONIST_LIBERAL,
        ideological_contestation=0.3,
    ),
    CommunityType.TRANS: CommunityConsciousness(
        collective_identity=0.5,  # Rising oppositional consciousness
        dominant_tendency=ConsciousnessTendency.ASSIMILATIONIST_LIBERAL,  # Still mostly "let us in"
        ideological_contestation=0.5,  # Very actively contested 2010s-2020s
    ),

    # Institutional exclusion
    CommunityType.DISABLED: CommunityConsciousness(
        collective_identity=0.3,
        dominant_tendency=ConsciousnessTendency.ASSIMILATIONIST_LIBERAL,
        ideological_contestation=0.2,
    ),
    CommunityType.QUEER: CommunityConsciousness(
        collective_identity=0.4,
        dominant_tendency=ConsciousnessTendency.ASSIMILATIONIST_LIBERAL,
        ideological_contestation=0.4,
    ),
    CommunityType.UNDOCUMENTED: CommunityConsciousness(
        collective_identity=0.4,
        dominant_tendency=ConsciousnessTendency.ASSIMILATIONIST_LIBERAL,
        ideological_contestation=0.2,  # Fear suppresses public debate
    ),
    CommunityType.INCARCERATED: CommunityConsciousness(
        collective_identity=0.6,  # Strong oppositional consciousness (George Jackson tradition)
        dominant_tendency=ConsciousnessTendency.REVOLUTIONARY,
        ideological_contestation=0.3,
    ),

    # Lifecycle — consciousness is less about identity, more about position
    CommunityType.YOUTH: CommunityConsciousness(
        collective_identity=0.2,  # Youth don't yet have strong collective political identity
        dominant_tendency=ConsciousnessTendency.ASSIMILATIONIST_LIBERAL,
        ideological_contestation=0.5,  # But highly contestable (D-phase socialization)
    ),
    CommunityType.ADULT: CommunityConsciousness(
        collective_identity=0.1,  # "Adult" is unmarked default in productive phase
        dominant_tendency=ConsciousnessTendency.ASSIMILATIONIST_LIBERAL,
        ideological_contestation=0.1,
    ),
    CommunityType.ELDER: CommunityConsciousness(
        collective_identity=0.3,  # Some consciousness around D' promise (Social Security)
        dominant_tendency=ConsciousnessTendency.ASSIMILATIONIST_LIBERAL,
        ideological_contestation=0.3,  # Tension over whether system can still provide
    ),
}
```

These defaults are SYNTHETIC — derived from political analysis, not empirical
measurement. Flag them as such in code comments. They serve as starting
conditions for the Detroit test case and WILL be adjusted through playtesting
and validation.

=== 8. HELPER FUNCTIONS ===

Add to existing community hyperedge infrastructure:

```python
def get_contradiction_axis(community: CommunityType) -> ContradictionAxis | None:
    """Which contradiction axis does this community belong to, if any?"""
    for axis in [COLONIAL_AXIS, PATRIARCHAL_AXIS]:
        if community == axis.hegemonic or community in axis.marginalized:
            return axis
    return None

def is_hegemonic(community: CommunityType) -> bool:
    """Is this community on the hegemonic side of a contradiction pair?"""
    return community in HEGEMONIC_COMMUNITIES

def is_marginalized(community: CommunityType) -> bool:
    """Is this community on the marginalized side (contradiction or exclusion)?"""
    return community in MARGINALIZED_COMMUNITIES

def get_opposing_communities(community: CommunityType) -> list[CommunityType]:
    """Get the communities on the other side of this community's contradiction axis."""
    axis = get_contradiction_axis(community)
    if axis is None:
        return []
    if community == axis.hegemonic:
        return axis.marginalized
    else:
        return [axis.hegemonic]

def shared_marginalized_communities(
    agent_a_communities: set[CommunityType],
    agent_b_communities: set[CommunityType]
) -> set[CommunityType]:
    """Marginalized communities shared by two agents.
    Used for solidarity potential calculation."""
    shared = agent_a_communities & agent_b_communities
    return shared & MARGINALIZED_COMMUNITIES

def communities_spanning_axis(
    H: xgi.Hypergraph,
    axis: ContradictionAxis
) -> list[CommunityType]:
    """Which institutional exclusion communities have members on BOTH sides
    of this contradiction axis? These are potential cross-class bridges."""
    bridges = []
    for comm_type in MARGINALIZED_COMMUNITIES:
        if COMMUNITY_CATEGORY_MAP[comm_type] != HyperedgeCategory.INSTITUTIONAL_EXCLUSION:
            continue
        members = H.edges.members(comm_type.value)
        member_communities = set()
        for member in members:
            member_communities.update(H.nodes.memberships(member))
        has_hegemonic = axis.hegemonic.value in member_communities
        has_marginalized = any(m.value in member_communities for m in axis.marginalized)
        if has_hegemonic and has_marginalized:
            bridges.append(comm_type)
    return bridges

def effective_infiltration_ceiling(
    base_ceiling: float,
    target_community_states: list[CommunityState]
) -> float:
    """Modify observation ceiling by community infiltration resistance.

    An AttentionThread targeting an org embedded in high-CI communities
    faces reduced infiltration success.
    """
    if not target_community_states:
        return base_ceiling
    max_resistance = max(c.infiltration_resistance for c in target_community_states)
    return base_ceiling * (1.0 - max_resistance * 0.7)
    # At max resistance (~0.85), ceiling drops to ~40% of base
    # At zero resistance, ceiling unchanged
```

REQUIRED OUTPUTS:

**New Models (Pydantic, frozen=True)**:
- HyperedgeCategory enum
- ConsciousnessTendency enum
- CommunityConsciousness model
- ContradictionAxis model
- CommunityState (EXTENDS existing CommunityNode — add consciousness,
  category, infiltration_resistance, is_cross_class_bridge)

**Updated Models**:
- CommunityType enum (add SETTLER, PATRIARCHAL, WOMEN, INCARCERATED,
  YOUTH, ADULT, ELDER)

**Constants**:
- COMMUNITY_CATEGORY_MAP
- HEGEMONIC_COMMUNITIES, MARGINALIZED_COMMUNITIES, LIFECYCLE_COMMUNITIES
- COLONIAL_AXIS, PATRIARCHAL_AXIS
- CONSCIOUSNESS_DEFAULTS

**Functions**:
- get_contradiction_axis(community) -> ContradictionAxis | None
- is_hegemonic(community) -> bool
- is_marginalized(community) -> bool
- get_opposing_communities(community) -> list[CommunityType]
- shared_marginalized_communities(a, b) -> set[CommunityType]
- communities_spanning_axis(H, axis) -> list[CommunityType]
- effective_infiltration_ceiling(base, communities) -> float

**Updated build_community_hypergraph**:
- Must handle new community types including hegemonic hyperedges
- Hyperedge attributes must include consciousness state
- Must support querying by HyperedgeCategory

**Persistence**:
- CommunityConsciousness serializable to SQLite JSON column
- ContradictionAxis stored as module constants (not database)
- Consciousness defaults loaded on simulation init, persist per-tick changes

VALIDATION CRITERIA:

**Taxonomy**:
- Every CommunityType maps to exactly one HyperedgeCategory
- SETTLER and PATRIARCHAL are CONTRADICTION_PAIR category
- DISABLED and QUEER are INSTITUTIONAL_EXCLUSION category
- YOUTH, ADULT, ELDER are LIFECYCLE_PHASE category
- get_contradiction_axis(SETTLER) returns COLONIAL_AXIS
- get_contradiction_axis(DISABLED) returns None
- get_opposing_communities(SETTLER) returns [NEW_AFRIKAN, FIRST_NATIONS, CHICANO]
- get_opposing_communities(NEW_AFRIKAN) returns [SETTLER]

**Consciousness**:
- All community types have consciousness defaults
- collective_identity is float [0,1]
- INCARCERATED starts with REVOLUTIONARY dominant_tendency
- SETTLER starts with ASSIMILATIONIST_LIBERAL dominant_tendency
- Consciousness survives serialization roundtrip

**Infiltration resistance**:
- Community with CI=0.9, cohesion=0.8 has high infiltration_resistance (~0.8+)
- Community with CI=0.1, cohesion=0.2 has low infiltration_resistance (~0.1)
- effective_infiltration_ceiling with high-resistance community is significantly
  lower than base ceiling
- effective_infiltration_ceiling with no communities returns base unchanged

**Cross-class bridges**:
- communities_spanning_axis correctly identifies INSTITUTIONAL_EXCLUSION communities
  whose members belong to both sides of a contradiction axis
- DISABLED spans colonial axis if it has both SETTLER and NEW_AFRIKAN members
- Contradiction pair communities are NOT bridges (they're the axis itself)

**Integration**:
- build_community_hypergraph handles all new community types
- XGI hypergraph includes hegemonic hyperedges with correct attributes
- Existing CommunityNode fields (heat, infrastructure, etc.) preserved
- Existing MembershipEdge preserved
- Existing serialization still works

**Detroit test case**:
- Wayne County population mapped to appropriate community memberships
  including SETTLER (white population) and NEW_AFRIKAN (Black population)
- PATRIARCHAL hyperedge exists with membership based on material position
- YOUTH/ADULT/ELDER mapped from Census age cohorts
- At least one INSTITUTIONAL_EXCLUSION community (DISABLED) with members
  spanning the colonial axis
- Consciousness defaults loaded correctly for all community types

CONSTRAINTS:
- EXTENDS existing models, does not replace them
- All existing tests must continue to pass
- Frozen Pydantic models; mutations create new instances
- No magic constants — consciousness defaults are SYNTHETIC and flagged as such
- ContradictionAxis instances are module-level constants, not database records
- XGI remains optional dependency (bipartite fallback must work)
- HyperedgeCategory assignment is from fixed mapping, not runtime-configurable
- Consciousness values change through simulation actions (org-topology Phase 2),
  not through this spec — this spec provides the STRUCTURE, not the dynamics

DEPENDENCIES:
- Requires: existing community hyperedge implementation (022)
- Requires: SocialClass nodes (for class position of community members)
- Required BY: all org-topology specs (030-035)
- Required BY: bifurcation topology analysis (033) — needs consciousness weighting
- Required BY: attention thread system (032) — needs infiltration resistance

WHAT THIS DOES NOT INCLUDE:
- Consciousness DYNAMICS (how CI changes over time) — that's org-topology Phase 2
- Organization interaction with consciousness — that's org-topology Phase 1-2
- Bifurcation analysis using consciousness — that's org-topology Phase 4
- State targeting using infiltration resistance — that's org-topology Phase 3
- Territory-level consciousness geography — that's org-topology Phase 6
- Legibility dimension (nonprofit vs LLC observation profiles) — defer
- Historical consciousness trajectories (how did Detroit CI change 2010-2025) — defer
- Nation vs community distinction — deferred, nations treated as CommunityType
```

---

## Implementation Notes

### Migration Path from Existing CommunityNode

The cleanest approach is to rename CommunityNode → CommunityState and add
the new fields. If that breaks imports, create CommunityState as a new model
that inherits from or wraps CommunityNode.

### Hegemonic Hyperedge Membership

Assigning agents to SETTLER and PATRIARCHAL hyperedges requires mapping from
existing demographic data:
- SETTLER: Map from Census race data (white, non-Hispanic population)
- PATRIARCHAL: Map from Census sex data (cis male population, approximated
  as male population minus estimated trans population)

These are APPROXIMATIONS. The Census doesn't ask "are you a settler?" but
the material position tracks closely enough with racial category for
simulation purposes. Flag as SYNTHETIC.

### D-P-D' Lifecycle Membership

Map from Census age cohorts:
- YOUTH: 0-17
- ADULT: 18-64
- ELDER: 65+

Agents have EXACTLY ONE lifecycle phase membership at any given time.
Transition rates computed from demographic data. This is the only hyperedge
category where membership changes predictably and universally.

### Consciousness as Tick-Level State

CommunityConsciousness changes each tick based on organizational actions
(EDUCATE, AGITATE, ASSIMILATE, etc.). The consciousness model defined here
provides the STATE that those actions modify. The DYNAMICS are specified in
org-topology Phase 2 (OODA system).

Between this spec and Phase 2, consciousness values remain at their defaults.
This is fine for testing taxonomy, infiltration resistance, and bridge detection.
