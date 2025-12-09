"""SocialClass entity model.

A SocialClass is the fundamental node type in the Babylon simulation.
It represents a social class in the world system, defined by:
1. Its relationship to the means of production (SocialRole)
2. Its material conditions (wealth, subsistence threshold)
3. Its ideological position (multi-dimensional consciousness model)
4. Its survival calculus outputs (P(S|A), P(S|R))

This is the Phase 1 node type from the four-phase blueprint.

Sprint 3.4.3 (George Jackson Refactor): Replaced scalar ideology with
multi-dimensional IdeologicalProfile containing:
- class_consciousness: Relationship to Capital [0=False, 1=Revolutionary]
- national_identity: Relationship to State/Tribe [0=Internationalist, 1=Fascist]
- agitation: Raw political energy from crisis (falling wages)
"""

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.models.enums import SocialRole
from babylon.models.types import Currency, Probability


class EconomicComponent(BaseModel):
    """Economic material conditions of a social class."""

    model_config = ConfigDict(frozen=True)

    wealth: Currency = Field(default=10.0, description="Economic resources")
    subsistence_threshold: Currency = Field(default=5.0, description="Minimum wealth for survival")


class IdeologicalProfile(BaseModel):
    """Multi-dimensional ideological state of a social class.

    Sprint 3.4.3 (George Jackson Refactor): This model replaces the scalar
    ideology field with a multi-dimensional consciousness model.

    The key insight: "Fascism is the defensive form of capitalism."
    - Agitation + Solidarity -> Class Consciousness (Revolutionary Path)
    - Agitation + No Solidarity -> National Identity (Fascist Path)

    Attributes:
        class_consciousness: Relationship to Capital [0.0=False, 1.0=Revolutionary]
            How clearly the class understands its position relative to capital.
        national_identity: Relationship to State/Tribe [0.0=Internationalist, 1.0=Fascist]
            How strongly the class identifies with nation/race over class.
        agitation: Raw political energy from crisis [0.0, inf)
            Accumulated energy from falling wages, crisis conditions.
            Routes to either axis based on solidarity_pressure.
    """

    model_config = ConfigDict(frozen=True)

    class_consciousness: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            description="Relationship to Capital: 0=False Consciousness, 1=Revolutionary",
        ),
    ] = 0.0

    national_identity: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            description="Relationship to State/Tribe: 0=Internationalist, 1=Nativist/Fascist",
        ),
    ] = 0.5

    agitation: Annotated[
        float,
        Field(
            ge=0.0,
            description="Raw political energy from crisis (falling wages)",
        ),
    ] = 0.0

    @classmethod
    def from_legacy_ideology(cls, ideology_value: float) -> "IdeologicalProfile":
        """Convert legacy scalar ideology [-1, 1] to IdeologicalProfile.

        Legacy mapping:
        - ideology=-1 (revolutionary) -> class_consciousness=1.0, national_identity=0.0
        - ideology=0 (neutral) -> class_consciousness=0.5, national_identity=0.5
        - ideology=+1 (reactionary) -> class_consciousness=0.0, national_identity=1.0

        Args:
            ideology_value: Legacy ideology scalar in range [-1.0, 1.0]

        Returns:
            IdeologicalProfile with mapped values
        """
        # Clamp to valid range
        ideology_value = max(-1.0, min(1.0, ideology_value))

        # Legacy consciousness formula: consciousness = (1 - ideology) / 2
        # So ideology=-1 gives consciousness=1, ideology=+1 gives consciousness=0
        class_consciousness = (1.0 - ideology_value) / 2.0

        # National identity inversely related to class consciousness in legacy model
        # ideology=-1 (revolutionary) -> internationalist (0.0)
        # ideology=+1 (reactionary) -> nativist (1.0)
        national_identity = (1.0 + ideology_value) / 2.0

        return cls(
            class_consciousness=class_consciousness,
            national_identity=national_identity,
            agitation=0.0,
        )

    def to_legacy_ideology(self) -> float:
        """Convert IdeologicalProfile back to legacy scalar ideology [-1, 1].

        This provides backward compatibility for systems still using the
        scalar ideology representation.

        Returns:
            Legacy ideology scalar in range [-1.0, 1.0]
        """
        # Reverse the legacy formula: ideology = 1 - 2 * consciousness
        return 1.0 - 2.0 * self.class_consciousness


class IdeologicalComponent(BaseModel):
    """Ideological state of a social class (legacy component view)."""

    model_config = ConfigDict(frozen=True)

    ideology: "IdeologicalProfile" = Field(
        default_factory=IdeologicalProfile,
        description="Multi-dimensional ideological profile",
    )
    organization: Probability = Field(default=0.1, description="Collective cohesion (0.1 = 10%)")


class SurvivalComponent(BaseModel):
    """Survival calculus outputs for a social class."""

    model_config = ConfigDict(frozen=True)

    p_acquiescence: Probability = Field(default=0.0, description="P(S|A)")
    p_revolution: Probability = Field(default=0.0, description="P(S|R)")


class MaterialConditionsComponent(BaseModel):
    """Material conditions affecting a social class."""

    model_config = ConfigDict(frozen=True)

    repression_faced: Probability = Field(default=0.5, description="State violence level")


class SocialClass(BaseModel):
    """A social class in the world system.

    The fundamental unit of the simulation. Classes are defined by their
    relationship to production and their position in the imperial hierarchy.

    This model uses Sprint 1 constrained types for automatic validation:
    - Currency: [0, inf) for wealth, subsistence_threshold
    - IdeologicalProfile: Multi-dimensional consciousness model (Sprint 3.4.3)
    - Probability: [0, 1] for survival probabilities and organization/repression

    Attributes:
        id: Unique identifier matching pattern ^C[0-9]{3}$
        name: Human-readable name for the class
        role: Position in the world system (SocialRole enum)
        description: Optional detailed description
        wealth: Economic resources (Currency, default 10.0)
        ideology: Multi-dimensional ideological profile (IdeologicalProfile)
        p_acquiescence: P(S|A) - survival probability through acquiescence (Probability)
        p_revolution: P(S|R) - survival probability through revolution (Probability)
        subsistence_threshold: Minimum wealth for survival (Currency, default 5.0)
        organization: Collective cohesion/class consciousness (Probability, default 0.1)
        repression_faced: State violence directed at this class (Probability, default 0.5)

    Legacy Compatibility:
        If a float value is passed for ideology, it will be automatically converted
        to an IdeologicalProfile using from_legacy_ideology().
    """

    model_config = ConfigDict(
        extra="forbid",  # Reject unknown fields
        validate_assignment=True,  # Validate on attribute mutation
        str_strip_whitespace=True,  # Clean string inputs
    )

    @model_validator(mode="before")
    @classmethod
    def unpack_components_and_convert_legacy(cls, data: Any) -> Any:
        """Unpack component objects and convert legacy ideology to IdeologicalProfile."""
        if not isinstance(data, dict):
            return data

        if "economic" in data:
            economic = data.pop("economic")
            if isinstance(economic, EconomicComponent):
                economic = economic.model_dump()
            elif not isinstance(economic, dict):
                raise ValueError("economic must be EconomicComponent or dict")
            data.setdefault("wealth", economic.get("wealth", 10.0))
            data.setdefault("subsistence_threshold", economic.get("subsistence_threshold", 5.0))

        if "ideological" in data:
            ideological = data.pop("ideological")
            if isinstance(ideological, IdeologicalComponent):
                ideological = ideological.model_dump()
            elif not isinstance(ideological, dict):
                raise ValueError("ideological must be IdeologicalComponent or dict")
            # Get ideology from component - could be float or IdeologicalProfile
            ideology_val = ideological.get("ideology")
            if ideology_val is not None:
                data.setdefault("ideology", ideology_val)
            data.setdefault("organization", ideological.get("organization", 0.1))

        if "survival" in data:
            survival = data.pop("survival")
            if isinstance(survival, SurvivalComponent):
                survival = survival.model_dump()
            elif not isinstance(survival, dict):
                raise ValueError("survival must be SurvivalComponent or dict")
            data.setdefault("p_acquiescence", survival.get("p_acquiescence", 0.0))
            data.setdefault("p_revolution", survival.get("p_revolution", 0.0))

        if "material_conditions" in data:
            material = data.pop("material_conditions")
            if isinstance(material, MaterialConditionsComponent):
                material = material.model_dump()
            elif not isinstance(material, dict):
                raise ValueError("material_conditions must be MaterialConditionsComponent or dict")
            data.setdefault("repression_faced", material.get("repression_faced", 0.5))

        # LEGACY COMPATIBILITY: Convert float ideology to IdeologicalProfile
        ideology_value = data.get("ideology")
        if ideology_value is not None:
            if isinstance(ideology_value, int | float) and not isinstance(ideology_value, bool):
                # Convert legacy scalar ideology to IdeologicalProfile
                data["ideology"] = IdeologicalProfile.from_legacy_ideology(float(ideology_value))
            elif isinstance(ideology_value, dict):
                # Dict representation - convert to IdeologicalProfile
                data["ideology"] = IdeologicalProfile(**ideology_value)
            # If already IdeologicalProfile, leave as-is

        return data

    # Required fields
    id: str = Field(
        ...,
        pattern=r"^C[0-9]{3}$",
        description="Unique identifier matching ^C[0-9]{3}$",
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Human-readable name for the class",
    )
    role: SocialRole = Field(
        ...,
        description="Position in the world system",
    )

    # Optional metadata
    description: str = Field(
        default="",
        description="Detailed description of the class",
    )

    # Manifold coordinates (material and ideological state)
    wealth: Currency = Field(
        default=10.0,
        description="Economic resources",
    )
    ideology: IdeologicalProfile = Field(
        default_factory=IdeologicalProfile,
        description="Multi-dimensional ideological profile (Sprint 3.4.3). Float input auto-converts via model_validator.",
    )

    # Survival calculus outputs (computed, can be updated)
    p_acquiescence: Probability = Field(
        default=0.0,
        description="P(S|A) - survival probability through acquiescence",
    )
    p_revolution: Probability = Field(
        default=0.0,
        description="P(S|R) - survival probability through revolution",
    )

    # Material conditions (inputs to survival calculus)
    subsistence_threshold: Currency = Field(
        default=5.0,
        description="Minimum wealth required for survival",
    )
    organization: Probability = Field(
        default=0.1,
        description="Collective cohesion / class consciousness (0.1 = 10%)",
    )
    repression_faced: Probability = Field(
        default=0.5,
        description="State violence directed at this class (0.5 = moderate)",
    )

    @property
    def economic(self) -> EconomicComponent:
        """Return economic component view (computed, not live)."""
        return EconomicComponent(
            wealth=self.wealth,
            subsistence_threshold=self.subsistence_threshold,
        )

    @property
    def ideological(self) -> IdeologicalComponent:
        """Return ideological component view (computed, not live)."""
        return IdeologicalComponent(
            ideology=self.ideology,
            organization=self.organization,
        )

    @property
    def survival(self) -> SurvivalComponent:
        """Return survival component view (computed, not live)."""
        return SurvivalComponent(
            p_acquiescence=self.p_acquiescence,
            p_revolution=self.p_revolution,
        )

    @property
    def material_conditions(self) -> MaterialConditionsComponent:
        """Return material conditions component view (computed, not live)."""
        return MaterialConditionsComponent(
            repression_faced=self.repression_faced,
        )
