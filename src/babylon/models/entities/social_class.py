"""SocialClass entity model.

A SocialClass is the fundamental node type in the Babylon simulation.
It represents a social class in the world system, defined by:
1. Its relationship to the means of production (SocialRole)
2. Its material conditions (wealth, subsistence threshold)
3. Its ideological position (revolutionary to reactionary)
4. Its survival calculus outputs (P(S|A), P(S|R))

This is the Phase 1 node type from the four-phase blueprint.
"""

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.enums import SocialRole
from babylon.models.types import Currency, Ideology, Probability


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
