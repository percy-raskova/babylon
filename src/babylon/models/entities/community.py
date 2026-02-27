"""Community membership models for the hypergraph layer (Feature 022).

Communities are n-ary membership structures represented as XGI hyperedges.
This module defines the data models for community state and agent membership.

See Also:
    :mod:`babylon.engine.systems.community`: CommunitySystem that operates on these models.
    Constitution II.7: Edges vs Hyperedges (NetworkX + XGI).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from babylon.models.enums import (
    CommunityType,
    ConsciousnessTendency,
    HyperedgeCategory,
    LegalStatus,
    MembershipRole,
)
from babylon.models.types import Coefficient, Probability

# Membership role strength weights (Feature 022, FR-004)
ROLE_STRENGTH_WEIGHTS: dict[MembershipRole, float] = {
    MembershipRole.CORE_ORGANIZER: 1.0,
    MembershipRole.ACTIVE: 0.7,
    MembershipRole.PARTICIPANT: 0.4,
    MembershipRole.PERIPHERAL: 0.2,
    MembershipRole.SYMPATHIZER: 0.1,
}

# Legal status threat multipliers (Feature 022, FR-015)
LEGAL_STATUS_MULTIPLIERS: dict[LegalStatus, float] = {
    LegalStatus.LEGAL: 0.1,
    LegalStatus.SURVEILLED: 0.5,
    LegalStatus.DESIGNATED_EXTREMIST: 1.0,
    LegalStatus.DESIGNATED_TERRORIST: 2.0,
    LegalStatus.CRIMINALIZED: 3.0,
}

# Legal status escalation order (one-way ratchet, Feature 022 clarification)
LEGAL_STATUS_ORDER: list[LegalStatus] = [
    LegalStatus.LEGAL,
    LegalStatus.SURVEILLED,
    LegalStatus.DESIGNATED_EXTREMIST,
    LegalStatus.DESIGNATED_TERRORIST,
    LegalStatus.CRIMINALIZED,
]


# === Feature 029: Three-Category Taxonomy ===

# Maps every CommunityType to exactly one HyperedgeCategory.
# This assignment is FIXED (structural property, not runtime-configurable).
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

# Import-time exhaustiveness validation (FR-001)
_missing_category = set(CommunityType) - set(COMMUNITY_CATEGORY_MAP.keys())
if _missing_category:
    raise RuntimeError(f"COMMUNITY_CATEGORY_MAP missing types: {_missing_category}")

# Which side of a contradiction axis a community is on
HEGEMONIC_COMMUNITIES: frozenset[CommunityType] = frozenset(
    {CommunityType.SETTLER, CommunityType.PATRIARCHAL}
)

MARGINALIZED_COMMUNITIES: frozenset[CommunityType] = frozenset(
    {
        CommunityType.NEW_AFRIKAN,
        CommunityType.FIRST_NATIONS,
        CommunityType.CHICANO,
        CommunityType.WOMEN,
        CommunityType.TRANS,
        CommunityType.DISABLED,
        CommunityType.QUEER,
        CommunityType.UNDOCUMENTED,
        CommunityType.INCARCERATED,
    }
)

LIFECYCLE_COMMUNITIES: frozenset[CommunityType] = frozenset(
    {CommunityType.YOUTH, CommunityType.ADULT, CommunityType.ELDER}
)


class ContradictionAxis(BaseModel):
    """A structural axis of contradiction with hegemonic and marginalized sides.

    Args:
        id: Short identifier for the axis.
        name: Human-readable axis name.
        hegemonic: The hegemonic community type on this axis.
        marginalized: List of marginalized community types on this axis.
        extraction_mechanism: Description of the material extraction.
        exclusive: Whether membership is mutually exclusive.
        permeable: Whether agents can cross the axis boundary.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    hegemonic: CommunityType
    marginalized: list[CommunityType]
    extraction_mechanism: str
    exclusive: bool
    permeable: bool


# === Feature 029: Contradiction Axes (US2) ===

COLONIAL_AXIS = ContradictionAxis(
    id="colonial",
    name="Colonial",
    hegemonic=CommunityType.SETTLER,
    marginalized=[
        CommunityType.NEW_AFRIKAN,
        CommunityType.FIRST_NATIONS,
        CommunityType.CHICANO,
    ],
    extraction_mechanism="Land, imperial rent, carceral labor, property value regimes",
    exclusive=True,
    permeable=False,
)

PATRIARCHAL_AXIS = ContradictionAxis(
    id="patriarchal",
    name="Patriarchal",
    hegemonic=CommunityType.PATRIARCHAL,
    marginalized=[CommunityType.WOMEN, CommunityType.TRANS],
    extraction_mechanism="Unwaged reproductive labor, wage gap, care externalization",
    exclusive=True,
    permeable=False,
)

CONTRADICTION_AXES: list[ContradictionAxis] = [COLONIAL_AXIS, PATRIARCHAL_AXIS]


def get_contradiction_axis(community: CommunityType) -> ContradictionAxis | None:
    """Return the contradiction axis a community belongs to, or None.

    Args:
        community: A CommunityType member.

    Returns:
        The ContradictionAxis if the community is part of a contradiction pair,
        None if it is institutional exclusion or lifecycle phase.
    """
    for axis in CONTRADICTION_AXES:
        if community == axis.hegemonic or community in axis.marginalized:
            return axis
    return None


def is_hegemonic(community: CommunityType) -> bool:
    """Return True if the community is on the hegemonic side of any axis.

    Args:
        community: A CommunityType member.

    Returns:
        True if hegemonic, False otherwise.
    """
    return community in HEGEMONIC_COMMUNITIES


def is_marginalized(community: CommunityType) -> bool:
    """Return True if the community is marginalized (including institutional exclusion).

    Args:
        community: A CommunityType member.

    Returns:
        True if marginalized, False otherwise.
    """
    return community in MARGINALIZED_COMMUNITIES


def get_opposing_communities(community: CommunityType) -> list[CommunityType]:
    """Return the communities on the opposite side of the contradiction axis.

    Args:
        community: A CommunityType member.

    Returns:
        List of opposing community types. Empty if not part of a contradiction axis.
    """
    axis = get_contradiction_axis(community)
    if axis is None:
        return []
    if community == axis.hegemonic:
        return list(axis.marginalized)
    return [axis.hegemonic]


def shared_marginalized_communities(
    agent_a_communities: set[CommunityType],
    agent_b_communities: set[CommunityType],
) -> set[CommunityType]:
    """Return marginalized communities shared by two agents.

    Args:
        agent_a_communities: Set of community types agent A belongs to.
        agent_b_communities: Set of community types agent B belongs to.

    Returns:
        Set of CommunityType that are in both agents' sets AND are marginalized.
    """
    shared = agent_a_communities & agent_b_communities
    return shared & MARGINALIZED_COMMUNITIES


# === Feature 029: Community Consciousness Model (US3) ===


class CommunityConsciousness(BaseModel):
    """The ideological dimension of a community hyperedge.

    Args:
        collective_identity: Oppositional consciousness [0, 1].
        dominant_tendency: Prevailing ideological direction.
        ideological_contestation: Active debate between tendencies [0, 1].
    """

    model_config = ConfigDict(frozen=True)

    collective_identity: Probability = Field(
        default=Probability(0.3),
        description="Oppositional consciousness [0, 1]",
    )
    dominant_tendency: ConsciousnessTendency = Field(
        default=ConsciousnessTendency.LIBERAL,
        description="Prevailing ideological direction",
    )
    ideological_contestation: Probability = Field(
        default=Probability(0.2),
        description="Active debate between tendencies [0, 1]",
    )


# SYNTHETIC starting values for all 14 community types.
# Detroit test case, circa 2010. Values are placeholders for calibration.
CONSCIOUSNESS_DEFAULTS: dict[CommunityType, CommunityConsciousness] = {
    # Contradiction pairs — hegemonic
    CommunityType.SETTLER: CommunityConsciousness(
        collective_identity=Probability(0.4),
        dominant_tendency=ConsciousnessTendency.LIBERAL,
        ideological_contestation=Probability(0.3),
    ),
    CommunityType.PATRIARCHAL: CommunityConsciousness(
        collective_identity=Probability(0.3),
        dominant_tendency=ConsciousnessTendency.LIBERAL,
        ideological_contestation=Probability(0.2),
    ),
    # Contradiction pairs — marginalized
    CommunityType.NEW_AFRIKAN: CommunityConsciousness(
        collective_identity=Probability(0.5),
        dominant_tendency=ConsciousnessTendency.LIBERAL,
        ideological_contestation=Probability(0.4),
    ),
    CommunityType.FIRST_NATIONS: CommunityConsciousness(
        collective_identity=Probability(0.6),
        dominant_tendency=ConsciousnessTendency.REVOLUTIONARY,
        ideological_contestation=Probability(0.3),
    ),
    CommunityType.CHICANO: CommunityConsciousness(
        collective_identity=Probability(0.4),
        dominant_tendency=ConsciousnessTendency.LIBERAL,
        ideological_contestation=Probability(0.3),
    ),
    CommunityType.WOMEN: CommunityConsciousness(
        collective_identity=Probability(0.3),
        dominant_tendency=ConsciousnessTendency.LIBERAL,
        ideological_contestation=Probability(0.3),
    ),
    CommunityType.TRANS: CommunityConsciousness(
        collective_identity=Probability(0.5),
        dominant_tendency=ConsciousnessTendency.LIBERAL,
        ideological_contestation=Probability(0.4),
    ),
    # Institutional exclusion
    CommunityType.DISABLED: CommunityConsciousness(
        collective_identity=Probability(0.3),
        dominant_tendency=ConsciousnessTendency.LIBERAL,
        ideological_contestation=Probability(0.2),
    ),
    CommunityType.QUEER: CommunityConsciousness(
        collective_identity=Probability(0.4),
        dominant_tendency=ConsciousnessTendency.LIBERAL,
        ideological_contestation=Probability(0.4),
    ),
    CommunityType.UNDOCUMENTED: CommunityConsciousness(
        collective_identity=Probability(0.5),
        dominant_tendency=ConsciousnessTendency.LIBERAL,
        ideological_contestation=Probability(0.3),
    ),
    CommunityType.INCARCERATED: CommunityConsciousness(
        collective_identity=Probability(0.6),
        dominant_tendency=ConsciousnessTendency.REVOLUTIONARY,
        ideological_contestation=Probability(0.3),
    ),
    # Lifecycle phases
    CommunityType.YOUTH: CommunityConsciousness(
        collective_identity=Probability(0.2),
        dominant_tendency=ConsciousnessTendency.LIBERAL,
        ideological_contestation=Probability(0.5),
    ),
    CommunityType.ADULT: CommunityConsciousness(
        collective_identity=Probability(0.1),
        dominant_tendency=ConsciousnessTendency.LIBERAL,
        ideological_contestation=Probability(0.1),
    ),
    CommunityType.ELDER: CommunityConsciousness(
        collective_identity=Probability(0.3),
        dominant_tendency=ConsciousnessTendency.LIBERAL,
        ideological_contestation=Probability(0.2),
    ),
}

# Import-time exhaustiveness validation (FR-004)
_missing_consciousness = set(CommunityType) - set(CONSCIOUSNESS_DEFAULTS.keys())
if _missing_consciousness:
    raise RuntimeError(f"CONSCIOUSNESS_DEFAULTS missing types: {_missing_consciousness}")

# Named constants for infiltration resistance formula (Feature 029, US4)
INFILTRATION_CI_WEIGHT: float = 0.6
INFILTRATION_COHESION_WEIGHT: float = 0.3
INFILTRATION_INTERACTION_WEIGHT: float = 0.1
INFILTRATION_CEILING_FACTOR: float = 0.7


class CommunityState(BaseModel):
    """State of a community, independent of its members.

    Each community has collective attributes tracking state attention,
    internal cohesion, organizational infrastructure, and material
    modifiers applied to all members.

    Args:
        community_type: Identity of this community.
        heat: State attention/surveillance intensity [0, 1].
        legal_status: Current legal designation (one-way escalation).
        cohesion: Internal trust and mutual aid effectiveness [0, 1].
        infrastructure: Organizational capacity (meeting spaces, comms) [0, 1].
        visibility: Community legibility to state surveillance [0, 1].
        reproduction_cost_modifier: Multiplier on V_reproduction for members.
        rent_access_modifier: Multiplier on imperial rent received by members.
    """

    model_config = ConfigDict(frozen=True)

    community_type: CommunityType
    category: HyperedgeCategory = Field(
        default=HyperedgeCategory.CONTRADICTION_PAIR,
        description="Structural category, auto-assigned from community_type",
    )
    heat: Probability = Field(
        default=Probability(0.0),
        description="State attention/surveillance intensity",
    )
    legal_status: LegalStatus = Field(
        default=LegalStatus.LEGAL,
        description="Current legal designation (one-way escalation)",
    )
    cohesion: Probability = Field(
        default=Probability(0.5),
        description="Internal trust and mutual aid effectiveness",
    )
    infrastructure: Probability = Field(
        default=Probability(0.3),
        description="Meeting spaces, comms, mutual aid networks",
    )
    visibility: Probability = Field(
        default=Probability(0.5),
        description="Legibility to state surveillance",
    )
    reproduction_cost_modifier: float = Field(
        default=1.0,
        ge=0.0,
        description="Multiplier on V_reproduction for members",
    )
    rent_access_modifier: Coefficient = Field(
        default=Coefficient(1.0),
        description="Multiplier on imperial rent received by members",
    )
    consciousness: CommunityConsciousness = Field(
        default_factory=CommunityConsciousness,
        description="Ideological dimension of the community",
    )

    @model_validator(mode="after")
    def _assign_category(self) -> CommunityState:
        """Auto-assign category from community_type via COMMUNITY_CATEGORY_MAP."""
        object.__setattr__(self, "category", COMMUNITY_CATEGORY_MAP[self.community_type])
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def infiltration_resistance(self) -> float:
        """Community resistance to state infiltration.

        Formula: CI * 0.6 + cohesion * 0.3 + CI * cohesion * 0.1

        Returns:
            Resistance score in [0.0, 1.0].
        """
        ci = float(self.consciousness.collective_identity)
        coh = float(self.cohesion)
        return (
            ci * INFILTRATION_CI_WEIGHT
            + coh * INFILTRATION_COHESION_WEIGHT
            + ci * coh * INFILTRATION_INTERACTION_WEIGHT
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_cross_class_bridge(self) -> bool:
        """Whether this community can span contradiction axes.

        Only INSTITUTIONAL_EXCLUSION communities bridge across axes because
        their members can come from both hegemonic and marginalized sides.

        Returns:
            True if the community is an institutional exclusion type.
        """
        return self.category == HyperedgeCategory.INSTITUTIONAL_EXCLUSION


def effective_infiltration_ceiling(
    base_ceiling: float,
    target_community_states: list[CommunityState],
) -> float:
    """Compute effective infiltration ceiling reduced by community resistance.

    Args:
        base_ceiling: Base infiltration ceiling [0, 1].
        target_community_states: Communities the target belongs to.

    Returns:
        Reduced ceiling. At max resistance (~1.0), drops to ~30% of base.
    """
    if not target_community_states:
        return base_ceiling
    max_resistance = max(cs.infiltration_resistance for cs in target_community_states)
    return base_ceiling * (1.0 - max_resistance * INFILTRATION_CEILING_FACTOR)


class CommunityMembership(BaseModel):
    """An agent's membership in a community.

    Represents the relationship between an individual agent and a
    community hyperedge. Each membership has a role determining
    integration level and a visibility determining legibility to state.

    Args:
        agent_id: Identifier of the member agent.
        community_type: Which community this membership is in.
        role: Integration level within the community.
        strength: Membership weight [0, 1], derived from role default.
        visibility: Base legibility to state [0, 1].
        overt: Publicly identified — overrides visibility to 1.0.
    """

    model_config = ConfigDict(frozen=True)

    agent_id: str
    community_type: CommunityType
    role: MembershipRole = Field(
        default=MembershipRole.PARTICIPANT,
        description="Integration level within community",
    )
    strength: Coefficient = Field(
        default=Coefficient(0.4),
        description="Membership weight, derived from role default",
    )
    visibility: Probability = Field(
        default=Probability(0.5),
        description="Base legibility to state",
    )
    overt: bool = Field(
        default=False,
        description="Publicly identified — overrides visibility to 1.0",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def effective_visibility(self) -> float:
        """Effective visibility accounting for overt flag.

        Returns:
            1.0 if overt, otherwise the base visibility value.
        """
        if self.overt:
            return 1.0
        return float(self.visibility)
