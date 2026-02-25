"""Community membership models for the hypergraph layer (Feature 022).

Communities are n-ary membership structures represented as XGI hyperedges.
This module defines the data models for community state and agent membership.

See Also:
    :mod:`babylon.engine.systems.community`: CommunitySystem that operates on these models.
    Constitution II.7: Edges vs Hyperedges (NetworkX + XGI).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, computed_field

from babylon.models.enums import CommunityType, LegalStatus, MembershipRole
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
