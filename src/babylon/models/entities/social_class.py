"""SocialClass entity model.

A SocialClass is the fundamental node type in the Babylon simulation.
It represents a social class in the world system, defined by:
1. Its relationship to the means of production (SocialRole)
2. Its material conditions (wealth, subsistence threshold)
3. Its ideological position (revolutionary to reactionary)
4. Its survival calculus outputs (P(S|A), P(S|R))

This is the Phase 1 node type from the four-phase blueprint.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.models.enums import SocialRole
from babylon.models.types import Currency, Ideology, Probability


class EconomicComponent(BaseModel):
    """Economic material conditions of a social class."""

    model_config = ConfigDict(frozen=True)

    wealth: Currency = Field(default=10.0, description="Economic resources")
    subsistence_threshold: Currency = Field(default=5.0, description="Minimum wealth for survival")


class IdeologicalComponent(BaseModel):
    """Ideological state of a social class."""

    model_config = ConfigDict(frozen=True)

    ideology: Ideology = Field(
        default=0.0, description="Position: -1=revolutionary, +1=reactionary"
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
    - Ideology: [-1, 1] for ideological position
    - Probability: [0, 1] for survival probabilities and organization/repression

    Attributes:
        id: Unique identifier matching pattern ^C[0-9]{3}$
        name: Human-readable name for the class
        role: Position in the world system (SocialRole enum)
        description: Optional detailed description
        wealth: Economic resources (Currency, default 10.0)
        ideology: Position on revolutionary-reactionary spectrum (Ideology, default 0.0)
        p_acquiescence: P(S|A) - survival probability through acquiescence (Probability)
        p_revolution: P(S|R) - survival probability through revolution (Probability)
        subsistence_threshold: Minimum wealth for survival (Currency, default 5.0)
        organization: Collective cohesion/class consciousness (Probability, default 0.1)
        repression_faced: State violence directed at this class (Probability, default 0.5)
    """

    model_config = ConfigDict(
        extra="forbid",  # Reject unknown fields
        validate_assignment=True,  # Validate on attribute mutation
        str_strip_whitespace=True,  # Clean string inputs
    )

    @model_validator(mode="before")
    @classmethod
    def unpack_components(cls, data: Any) -> Any:
        """Unpack component objects into flat fields if provided."""
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
            data.setdefault("ideology", ideological.get("ideology", 0.0))
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
    ideology: Ideology = Field(
        default=0.0,
        description="Position: -1=revolutionary, +1=reactionary",
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
