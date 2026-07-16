"""Organization entity models for the Babylon simulation (Feature 031).

Defines the Organization base class and four frozen Pydantic subtypes:
StateApparatus, Business, PoliticalFaction, CivilSocietyOrg. Also defines
IntelMethodology (supporting model) and KeyFigure (separate graph node).

The ``OrganizationType`` discriminated union dispatches on ``org_type``
for automatic subtype selection during deserialization.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.models.entities.state_apparatus_ai import FactionBalance
from babylon.models.enums import (
    ClassCharacter,
    ConsciousnessTendency,
    JurisdictionLevel,
    LegalStanding,
    OrgType,
    ServiceType,
    StateFaction,
)
from babylon.models.enums.doctrine import DoctrineTag
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
    # Doctrine Tree state (DoctrineSystem, owner-ratified 2026-07-15). Empty for
    # orgs that never study; the DoctrineSystem accumulates these across ticks.
    # Stored on the model (not graph-only) so acquisitions + theoretical labour
    # survive snapshots and WorldState round-trips — accumulated state, unlike
    # the per-tick-recomputed shadow attrs of P19/EH.
    acquired_doctrine_ids: tuple[str, ...] = Field(
        default=(),
        description="Doctrine node ids this organization has acquired, in acquisition order",
    )
    theoretical_labor: float = Field(
        default=0.0,
        ge=0.0,
        description="Accumulated theoretical labour available to acquire doctrine nodes",
    )
    doctrine_tags: dict[DoctrineTag, float] = Field(
        default_factory=dict,
        description="Decaying per-tag doctrine strength accumulator (Ruling 3: 0.55%/tick decay)",
    )
    congress_tag_snapshot: dict[DoctrineTag, float] = Field(
        default_factory=dict,
        description="Tag state at the last Party Congress — the delta baseline for the next congress's purge odds (Ruling 5 / DT-5)",
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
        if self.is_institution:
            warnings.warn(
                "Organization.is_institution is deprecated. "
                "Use Institution entity (Feature 040) instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        if self.institutional_persistence is not None:
            warnings.warn(
                "Organization.institutional_persistence is deprecated. "
                "Use Institution.formalization_level and "
                "Institution.institutional_inertia (Feature 040) instead.",
                DeprecationWarning,
                stacklevel=2,
            )
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
        faction_balance: Ruling-class factional weight vector (Feature 039).
            ``None`` means the org runs the legacy static priority queue
            (``babylon.ooda.npc_stub._NPC_PRIORITIES``); setting this is the
            sole gate that activates ``RuleBasedStateAI`` dispatch in
            ``babylon.ooda.npc_stub._try_state_ai_dispatch``.
        rng_seed: Deterministic seed for ``RuleBasedStateAI``'s per-candidate
            tiebreaker draw (Constitution III.7). Read by
            ``_try_state_ai_dispatch``; required whenever ``faction_balance``
            is set, or the tiebreaker falls back to OS-entropy-seeded
            ``random.Random(None)`` — a real non-determinism bug.
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
    faction_balance: FactionBalance | None = Field(
        default=None,
        description=(
            "Ruling-class factional weight vector gating RuleBasedStateAI "
            "dispatch (Feature 039). None = legacy static priority queue."
        ),
    )
    rng_seed: int | None = Field(
        default=None,
        description=(
            "Deterministic seed for RuleBasedStateAI's tiebreaker draw "
            "(Constitution III.7). Should be set whenever faction_balance is."
        ),
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
    naics_2digit: str | None = Field(
        default=None,
        description="The 2-digit NAICS code for ECONOMIC_SECTOR hyperedge linking",
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
    constant_capital: Currency = Field(
        default=0.0,
        description="Constant capital (c)",
    )
    variable_capital: Currency = Field(
        default=0.0,
        description="Variable capital (v) - wages",
    )
    surplus_value: Currency = Field(
        default=0.0,
        description="Surplus value (s)",
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
