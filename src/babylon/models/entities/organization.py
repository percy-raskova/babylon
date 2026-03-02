"""Organization entity models for the Babylon simulation (Feature 031).

Defines the Organization base class and four frozen Pydantic subtypes:
StateApparatus, Business, PoliticalFaction, CivilSocietyOrg. Also defines
IntelMethodology (supporting model) and KeyFigure (separate graph node).

The ``OrganizationType`` discriminated union dispatches on ``org_type``
for automatic subtype selection during deserialization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.models.enums import (
    ClassCharacter,
    ConsciousnessTendency,
    JurisdictionLevel,
    LegalStanding,
    OrgType,
    ServiceType,
    StateFaction,
)
from babylon.models.types import Coefficient, Currency, Probability

if TYPE_CHECKING:
    from babylon.config.defines import OrganizationDefines


class IntelMethodology(BaseModel):
    """Intelligence methodology capabilities (Sparrow-grounded).

    Defines which social network analysis techniques an intelligence
    agency can employ and the maximum fraction of true topology observable.

    Attributes:
        centrality_analysis: Can identify hub nodes and bridges.
        equivalence_analysis: Can find structurally equivalent positions.
        template_matching: Can match against known org templates.
        temporal_analysis: Can detect activation pattern changes over time.
        observation_ceiling: Max fraction of true topology observable [0, 1].
    """

    model_config = ConfigDict(frozen=True)

    centrality_analysis: bool = Field(
        default=False,
        description="Can identify hub nodes and bridges",
    )
    equivalence_analysis: bool = Field(
        default=False,
        description="Can find structurally equivalent positions (Sparrow 1993)",
    )
    template_matching: bool = Field(
        default=False,
        description="Can match against known org templates",
    )
    temporal_analysis: bool = Field(
        default=False,
        description="Can detect activation pattern changes over time",
    )
    observation_ceiling: Probability = Field(
        default=0.2,
        description="Max fraction of true topology observable [0, 1]",
    )

    @classmethod
    def local_pd(cls, defines: OrganizationDefines | None = None) -> IntelMethodology:
        """Local PD preset: centrality only, low ceiling.

        Args:
            defines: Optional OrganizationDefines for tunable ceiling value.
        """
        ceiling = defines.observation_ceiling_local_pd if defines is not None else 0.2
        return cls(
            centrality_analysis=True,
            observation_ceiling=ceiling,
        )

    @classmethod
    def fusion_center(cls, defines: OrganizationDefines | None = None) -> IntelMethodology:
        """Fusion Center preset: centrality + temporal, medium ceiling.

        Args:
            defines: Optional OrganizationDefines for tunable ceiling value.
        """
        ceiling = defines.observation_ceiling_fusion if defines is not None else 0.5
        return cls(
            centrality_analysis=True,
            temporal_analysis=True,
            observation_ceiling=ceiling,
        )

    @classmethod
    def fbi(cls, defines: OrganizationDefines | None = None) -> IntelMethodology:
        """FBI preset: all capabilities, FBI-level ceiling.

        Args:
            defines: Optional OrganizationDefines for tunable ceiling value.
        """
        ceiling = defines.observation_ceiling_fbi if defines is not None else 0.4
        return cls(
            centrality_analysis=True,
            equivalence_analysis=True,
            template_matching=True,
            temporal_analysis=True,
            observation_ceiling=ceiling,
        )


class Organization(BaseModel):
    """Base organization entity for the Babylon simulation.

    All four subtypes (StateApparatus, Business, PoliticalFaction,
    CivilSocietyOrg) inherit these 15 fields. Frozen and immutable.

    Attributes:
        id: Unique organization identifier.
        name: Human-readable name.
        org_type: Discriminator for subtype dispatch.
        class_character: Which class this org serves.
        cohesion: Internal unity and coordination [0, 1].
        cadre_level: Leadership quality [0, 1].
        budget: Available resources [0, inf).
        legal_standing: Legal status of the organization.
        consciousness_tendency: Ideological tendency pushed on communities.
        territory_ids: Territories where org operates.
        headquarters_id: Primary location (must be in territory_ids).
        heat: State attention level [0, 1].
        is_institution: Has crystallized into institution.
        institutional_persistence: Resistance to dissolution (institutions only).
        member_node_ids: Individual key figures and cadre.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        min_length=1,
        description="Unique organization identifier",
    )
    name: str = Field(
        min_length=1,
        description="Human-readable name",
    )
    org_type: OrgType = Field(
        description="Discriminator for subtype dispatch",
    )
    class_character: ClassCharacter = Field(
        description="Which class this org serves",
    )
    cohesion: Probability = Field(
        default=0.1,
        description="Internal unity and coordination [0=atomized, 1=unified]",
    )
    cadre_level: Probability = Field(
        default=0.0,
        description="Leadership quality [0=none, 1=elite]",
    )
    budget: Currency = Field(
        default=0.0,
        description="Available resources",
    )
    legal_standing: LegalStanding = Field(
        default=LegalStanding.REGISTERED,
        description="Legal status of the organization",
    )
    consciousness_tendency: ConsciousnessTendency = Field(
        default=ConsciousnessTendency.LIBERAL,
        description="Ideological tendency pushed on communities",
    )
    territory_ids: list[str] = Field(
        default_factory=list,
        description="Territories where org operates",
    )
    headquarters_id: str | None = Field(
        default=None,
        description="Primary location (must be in territory_ids if set)",
    )
    heat: Probability = Field(
        default=0.0,
        description="State attention level [0=invisible, 1=targeted]",
    )
    is_institution: bool = Field(
        default=False,
        description="Has crystallized into institution (I.16)",
    )
    institutional_persistence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Resistance to dissolution (institutions only) [0, 1]",
    )
    member_node_ids: list[str] = Field(
        default_factory=list,
        description="Individual key figures and cadre node IDs",
    )

    @model_validator(mode="after")
    def _validate_constraints(self) -> Organization:
        """Validate cross-field constraints."""
        if self.headquarters_id is not None and self.headquarters_id not in self.territory_ids:
            msg = "headquarters_id must be in territory_ids"
            raise ValueError(msg)
        if not self.is_institution and self.institutional_persistence is not None:
            msg = "institutional_persistence must be None when is_institution is False"
            raise ValueError(msg)
        return self


class StateApparatus(Organization):
    """State apparatus organization (Feature 031).

    Wields state violence and surveillance. Default legal standing is SOVEREIGN.

    Attributes:
        jurisdiction: Scope of authority.
        violence_capacity: Capacity for coercive force [0, 1].
        surveillance_capacity: Capacity for surveillance [0, 1].
        legal_authority: Specific authorities wielded.
        intel_methodology: Intelligence capabilities (Sparrow-grounded).
    """

    org_type: Literal[OrgType.STATE_APPARATUS] = OrgType.STATE_APPARATUS
    legal_standing: LegalStanding = Field(
        default=LegalStanding.SOVEREIGN,
        description="Legal status (SOVEREIGN for state apparatus)",
    )
    jurisdiction: JurisdictionLevel = Field(
        description="Scope of authority",
    )
    violence_capacity: Probability = Field(
        default=0.0,
        description="Capacity for coercive force [0, 1]",
    )
    surveillance_capacity: Probability = Field(
        default=0.0,
        description="Capacity for surveillance [0, 1]",
    )
    legal_authority: list[str] = Field(
        default_factory=list,
        description="Specific authorities wielded",
    )
    intel_methodology: IntelMethodology = Field(
        default_factory=IntelMethodology,
        description="Intelligence capabilities (Sparrow-grounded)",
    )
    # State Apparatus AI (Feature 039)
    factional_alignment: StateFaction = Field(
        default=StateFaction.SECURITY_STATE,
        description="Dominant faction alignment of this apparatus (Feature 039)",
    )


class Business(Organization):
    """Business organization (Feature 031).

    Accumulates capital and employs labor.

    Attributes:
        sector: NAICS sector description.
        employment_count: Number of employees.
        surplus_extraction_rate: Rate of surplus value extraction [0, 1].
        revenue: Annual revenue [0, inf).
    """

    org_type: Literal[OrgType.BUSINESS] = OrgType.BUSINESS
    sector: str = Field(
        min_length=1,
        description="NAICS sector description",
    )
    employment_count: int = Field(
        default=0,
        ge=0,
        description="Number of employees",
    )
    surplus_extraction_rate: Coefficient = Field(
        default=0.0,
        description="Rate of surplus value extraction [0, 1]",
    )
    revenue: Currency = Field(
        default=0.0,
        description="Annual revenue",
    )


class PoliticalFaction(Organization):
    """Political faction organization (Feature 031).

    Contests political power. The player's faction is marked with ``is_player``.

    Attributes:
        ideology: Ideological label (e.g., "Marxism-Leninism").
        is_player: Whether this is the player's faction.
        relationship_to_player: Relationship state.
    """

    org_type: Literal[OrgType.POLITICAL_FACTION] = OrgType.POLITICAL_FACTION
    ideology: str = Field(
        min_length=1,
        description="Ideological label",
    )
    is_player: bool = Field(
        default=False,
        description="Is this the player's faction?",
    )
    relationship_to_player: str = Field(
        default="neutral",
        description="Relationship state",
    )


class CivilSocietyOrg(Organization):
    """Civil society organization (Feature 031).

    Non-state, non-business collective providing community services.
    ``legitimacy`` doubles as the credibility factor in the consciousness
    effect formula.

    Attributes:
        service_type: Domain of service provision.
        legitimacy: Community trust/credibility [0, 1].
    """

    org_type: Literal[OrgType.CIVIL_SOCIETY] = OrgType.CIVIL_SOCIETY
    service_type: ServiceType = Field(
        description="Domain of service provision",
    )
    legitimacy: Probability = Field(
        default=0.5,
        description="Community trust/credibility [0, 1]",
    )


# Discriminated union for automatic subtype dispatch
OrganizationType = Annotated[
    StateApparatus | Business | PoliticalFaction | CivilSocietyOrg,
    Field(discriminator="org_type"),
]
"""Discriminated union dispatching on ``org_type`` to the correct subtype."""


class KeyFigure(BaseModel):
    """Individual node within organizational topology (Feature 031).

    Stored as a separate graph node (``_node_type="key_figure"``).
    COMMAND edges connect KeyFigure nodes within the same organization.

    Attributes:
        id: Unique key figure identifier.
        name: Name.
        organization_id: Parent organization.
        role: Position title/function.
        structural_importance: Topological criticality [0, 1].
        is_singleton: No structural equivalent (Sparrow).
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        min_length=1,
        description="Unique key figure identifier",
    )
    name: str = Field(
        min_length=1,
        description="Name",
    )
    organization_id: str = Field(
        min_length=1,
        description="Parent organization ID",
    )
    role: str = Field(
        min_length=1,
        description="Position title/function",
    )
    structural_importance: Probability = Field(
        default=0.5,
        description="Topological criticality [0, 1]",
    )
    is_singleton: bool = Field(
        default=False,
        description="No structural equivalent (Sparrow)",
    )
