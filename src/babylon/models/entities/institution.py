"""Institution entity models for the Babylon simulation (Feature 040).

Defines the Institution base entity and supporting models:
- InternalBalanceOfForces: Factional weight distribution
- ReproductionMechanism: Self-perpetuation capacity
- SpawningBlueprint: Template for replacement Organizations
- InstitutionOrgRelation: Institution-Organization housing relationship
- Institution: Third-layer entity between substrate and agents
- FactionShiftEvent: Hegemonic fraction change event
- ReproductionEvent: Organization spawning event
- BonapartistModeEvent: Bonapartist threshold crossing event

All models are frozen (immutable) Pydantic BaseModels.

See Also:
    ``specs/040-institution-base-model/data-model.md``: Entity definitions.
    :mod:`babylon.models.enums`: ApparatusType, SocialFunction, etc.
"""

from __future__ import annotations

from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from babylon.models.enums import (
    ApparatusType,
    ClassCharacter,
    ClassInscription,
    LifecyclePhase,
    OrgType,
    RulingClassFraction,
    SocialFunction,
)

# =============================================================================
# InternalBalanceOfForces
# =============================================================================


class InternalBalanceOfForces(BaseModel):
    """Factional weight distribution within an institution (Feature 040).

    Three ruling-class fractions compete for hegemony within each
    institution. Weights always sum to 1.0 (tolerance +/- 0.01).
    The hegemonic fraction (highest weight) modulates housed
    Organization OODA orientation.

    Attributes:
        liberal_technocratic: Weight of consent-based rule faction [0, 1].
        revanchist_fascist: Weight of naked repression faction [0, 1].
        institutionalist_bonapartist: Weight of self-preservation faction [0, 1].
        internal_contestation: How actively factional warfare is occurring [0, 1].

    Reference: FR-005, FR-006.
    """

    model_config = ConfigDict(frozen=True)

    liberal_technocratic: float = Field(
        ge=0.0,
        le=1.0,
        description="Weight of Liberal-Technocratic faction [0, 1]",
    )
    revanchist_fascist: float = Field(
        ge=0.0,
        le=1.0,
        description="Weight of Revanchist-Fascist faction [0, 1]",
    )
    institutionalist_bonapartist: float = Field(
        ge=0.0,
        le=1.0,
        description="Weight of Institutionalist-Bonapartist faction [0, 1]",
    )
    internal_contestation: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How actively factional warfare is occurring [0=settled, 1=active]",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def hegemonic_fraction(self) -> RulingClassFraction:
        """Faction with highest weight."""
        weights = {
            RulingClassFraction.LIBERAL_TECHNOCRATIC: self.liberal_technocratic,
            RulingClassFraction.REVANCHIST_FASCIST: self.revanchist_fascist,
            RulingClassFraction.INSTITUTIONALIST_BONAPARTIST: self.institutionalist_bonapartist,
        }
        return max(weights, key=lambda k: weights[k])

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> Self:
        """Validate faction weights sum to 1.0."""
        total = (
            self.liberal_technocratic + self.revanchist_fascist + self.institutionalist_bonapartist
        )
        if not (0.99 <= total <= 1.01):
            msg = f"Faction weights must sum to 1.0, got {total}"
            raise ValueError(msg)
        return self


# =============================================================================
# ReproductionMechanism
# =============================================================================


class ReproductionMechanism(BaseModel):
    """Self-perpetuation capacity of an institution (Feature 040).

    Tracks the formal mechanisms that allow an institution to reproduce
    itself: recruitment, training, succession, budget independence, and
    legal self-perpetuation. The computed reproduction_capacity score
    determines how effectively an institution replaces lost members.

    Attributes:
        recruitment_pipeline: Has formal member intake process.
        training_program: Has formal training/socialization.
        succession_protocol: Has leadership succession plan.
        budget_independence: Fraction of budget from own sources [0, 1].
        legal_self_perpetuation: Has legal mandate to exist.

    Reference: FR-012.
    """

    model_config = ConfigDict(frozen=True)

    recruitment_pipeline: bool = Field(
        default=False,
        description="Has formal member intake process",
    )
    training_program: bool = Field(
        default=False,
        description="Has formal training/socialization",
    )
    succession_protocol: bool = Field(
        default=False,
        description="Has leadership succession plan",
    )
    budget_independence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of budget from own sources [0, 1]",
    )
    legal_self_perpetuation: bool = Field(
        default=False,
        description="Has legal mandate to exist",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def reproduction_capacity(self) -> float:
        """Composite reproduction capacity score.

        Formula: (sum(bools) / 4) * 0.7 + budget_independence * 0.3

        The four boolean mechanisms contribute 70% of capacity,
        budget independence contributes 30%.
        """
        bool_count = sum(
            [
                self.recruitment_pipeline,
                self.training_program,
                self.succession_protocol,
                self.legal_self_perpetuation,
            ]
        )
        return (bool_count / 4) * 0.7 + self.budget_independence * 0.3


# =============================================================================
# SpawningBlueprint
# =============================================================================


class SpawningBlueprint(BaseModel):
    """Template for replacement Organization creation (Feature 040).

    Stored by institutions to define how replacement Organizations are
    created when housed ones are destroyed. Spawned orgs inherit from
    the blueprint, modified by the institution's current state.

    Attributes:
        org_type: Organization category to spawn.
        default_class_character: Initial class character for spawned org.
        base_attributes: Additional attributes for spawned org.

    Reference: FR-016.
    """

    model_config = ConfigDict(frozen=True)

    org_type: OrgType = Field(
        description="Organization category to spawn",
    )
    default_class_character: ClassCharacter = Field(
        description="Initial class character for spawned org",
    )
    base_attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional attributes for spawned org",
    )


# =============================================================================
# InstitutionOrgRelation
# =============================================================================


class InstitutionOrgRelation(BaseModel):
    """Relationship between institution and housed Organization (Feature 040).

    Tracks the material and political dimensions of how an institution
    houses and shapes an Organization.

    Attributes:
        institution_id: Parent institution ID.
        organization_id: Housed organization ID.
        resource_provision: Fraction of institution resources provided [0, 1].
        legal_cover: Whether institution provides legal protection.
        legitimacy_transfer: How much institutional legitimacy transfers [0, 1].
        action_oversight: How much institution constrains org actions [0, 1].
        factional_alignment: Which faction the org aligns with, if any.

    Reference: FR-011.
    """

    model_config = ConfigDict(frozen=True)

    institution_id: str = Field(
        min_length=1,
        description="Parent institution ID",
    )
    organization_id: str = Field(
        min_length=1,
        description="Housed organization ID",
    )
    resource_provision: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of institution resources provided [0, 1]",
    )
    legal_cover: bool = Field(
        default=False,
        description="Whether institution provides legal protection",
    )
    legitimacy_transfer: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How much institutional legitimacy transfers [0, 1]",
    )
    action_oversight: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How much institution constrains org actions [0, 1]",
    )
    factional_alignment: RulingClassFraction | None = Field(
        default=None,
        description="Which ruling-class faction the org aligns with",
    )


# =============================================================================
# Institution
# =============================================================================


class Institution(BaseModel):
    """Third-layer entity representing crystallized social relations (Feature 040).

    Institutions are the layer between substrate (SocialClass, Territory,
    Community) and agents (Organizations). They persist through member
    turnover, generate and constrain Organizations, maintain internal
    balance of forces, and serve as sites of class struggle.

    Graph node type: ``_node_type="institution"``

    Attributes:
        id: Unique institution identifier.
        name: Human-readable name.
        apparatus_type: Althusserian classification.
        social_function: Population need served.
        class_inscription: Which class the institution serves.
        internal_balance: Factional weight distribution.
        action_modifiers: Override structural selectivity modifiers.
        budget: Available resources.
        fixed_asset_territory_ids: Territories with fixed infrastructure.
        legal_authorities: Legal powers held.
        personnel_capacity: Maximum personnel count.
        formalization_level: Degree of bureaucratic formalization [0, 1].
        institutional_inertia: Resistance to rapid change [0, 1].
        legitimacy: Public perceived legitimacy [0, 1].
        housed_org_ids: Organizations housed within.
        territory_ids: Territories where institution operates.
        jurisdiction: Jurisdiction scope (RSA types only).
        lifecycle_function: D-P-D' phase assignment.
        reproduction: Self-perpetuation mechanisms.
        spawning_blueprints: Templates for replacement orgs.

    Reference: FR-001 through FR-016.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        min_length=1,
        description="Unique institution identifier",
    )
    name: str = Field(
        min_length=1,
        description="Human-readable name",
    )
    apparatus_type: ApparatusType = Field(
        description="Althusserian apparatus type classification",
    )
    social_function: SocialFunction = Field(
        description="Population need served by this institution",
    )
    class_inscription: ClassInscription = Field(
        default=ClassInscription.BOURGEOIS,
        description="Which class the institution serves",
    )
    internal_balance: InternalBalanceOfForces = Field(
        description="Factional weight distribution",
    )
    action_modifiers: dict[str, float] = Field(
        default_factory=dict,
        description="Override structural selectivity modifiers (ActionType -> multiplier)",
    )
    budget: float = Field(
        default=0.0,
        ge=0.0,
        description="Available resources",
    )
    fixed_asset_territory_ids: list[str] = Field(
        default_factory=list,
        description="Territories with fixed infrastructure",
    )
    legal_authorities: frozenset[str] = Field(
        default_factory=frozenset,
        description="Legal powers held by this institution",
    )
    personnel_capacity: int = Field(
        default=0,
        ge=0,
        description="Maximum personnel count",
    )
    formalization_level: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Degree of bureaucratic formalization [0, 1]",
    )
    institutional_inertia: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Resistance to rapid change [0, 1]",
    )
    legitimacy: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Public perceived legitimacy [0, 1]",
    )
    housed_org_ids: list[str] = Field(
        default_factory=list,
        description="Organization IDs housed within this institution",
    )
    territory_ids: list[str] = Field(
        default_factory=list,
        description="Territories where institution operates",
    )
    jurisdiction: frozenset[str] | None = Field(
        default=None,
        description="Jurisdiction scope (RSA types only)",
    )
    lifecycle_function: LifecyclePhase | None = Field(
        default=None,
        description="D-P-D' lifecycle phase assignment",
    )
    reproduction: ReproductionMechanism = Field(
        description="Self-perpetuation mechanisms",
    )
    spawning_blueprints: list[SpawningBlueprint] = Field(
        default_factory=list,
        description="Templates for replacement Organizations",
    )

    @model_validator(mode="after")
    def _validate_constraints(self) -> Self:
        """Validate cross-field constraints.

        - jurisdiction should only be set for RSA_ apparatus types
        - action_modifiers values must be > 0.0
        """
        if self.jurisdiction is not None and not self.apparatus_type.value.startswith("rsa_"):
            msg = "jurisdiction should only be set for RSA_ apparatus types"
            raise ValueError(msg)

        max_modifiers = len(self.action_modifiers)
        for checked, (key, val) in enumerate(self.action_modifiers.items()):
            if checked >= max_modifiers:
                break  # pragma: no cover — bounded loop guard
            if val <= 0.0:
                msg = f"action_modifiers['{key}'] must be > 0.0, got {val}"
                raise ValueError(msg)

        return self


# =============================================================================
# Event Types (FR-019)
# =============================================================================


class FactionShiftEvent(BaseModel):
    """Returned when update_internal_balance changes the hegemonic fraction.

    Reference: FR-019, EventType.INSTITUTION_FACTION_SHIFT.
    """

    model_config = ConfigDict(frozen=True)

    institution_id: str = Field(
        min_length=1,
        description="Institution whose hegemonic fraction changed",
    )
    old_fraction: RulingClassFraction = Field(
        description="Previous hegemonic fraction",
    )
    new_fraction: RulingClassFraction = Field(
        description="New hegemonic fraction",
    )
    weights: dict[str, float] = Field(
        description="Updated faction weights",
    )


class ReproductionEvent(BaseModel):
    """Returned when an institution spawns a replacement Organization.

    Reference: FR-019, EventType.INSTITUTION_REPRODUCTION.
    """

    model_config = ConfigDict(frozen=True)

    institution_id: str = Field(
        min_length=1,
        description="Institution that spawned the org",
    )
    spawned_org_type: OrgType = Field(
        description="Type of organization spawned",
    )
    blueprint: SpawningBlueprint = Field(
        description="Blueprint used for spawning",
    )


class BonapartistModeEvent(BaseModel):
    """Returned when BONAPARTIST weight crosses the Bonapartist threshold.

    Reference: FR-019, EventType.INSTITUTION_BONAPARTIST_MODE.
    """

    model_config = ConfigDict(frozen=True)

    institution_id: str = Field(
        min_length=1,
        description="Institution entering Bonapartist mode",
    )
    bonapartist_weight: float = Field(
        ge=0.0,
        le=1.0,
        description="Current BONAPARTIST faction weight",
    )
