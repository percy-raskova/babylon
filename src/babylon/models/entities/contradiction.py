"""Contradiction models for dialectical simulation.

Contradictions are structural tensions between opposing forces.
This module implements a dynamic Maoist framework where
principal and secondary contradictions operate at various zoom levels.
"""

from typing import Literal

from pydantic import BaseModel, Field

from babylon.models.enums import ContradictionType, EdgeMode
from babylon.models.types import Intensity


class Contradiction(BaseModel):
    """A structural contradiction at a specific scale.

    Instead of hardcoding the fractal, this uses a dynamic aspect mapping.
    """

    id: str = Field(..., description="Unique identifier for this contradiction")
    type: ContradictionType = Field(
        ..., description="The axis of contradiction (e.g., NATIONAL, CLASS)"
    )
    aspect_a: str = Field(..., description="One side of the contradiction")
    aspect_b: str = Field(..., description="The other side of the contradiction")

    principal_aspect: Literal["a", "b"] = Field(
        ..., description="Which aspect is currently principal (dominant)"
    )

    identity: Intensity = Field(
        default=0.0,
        description="Mutual presupposition strength of the two aspects",
    )

    intensity: Intensity = Field(
        default=0.0,
        description="Current tension level of the contradiction (0 = dormant, 1 = maximum crisis)",
    )
    aspect_balance: float = Field(
        default=0.0,
        description="Rate of change / capacity accumulation of the subordinate aspect relative to the dominant one. Derivative of intensity.",
    )

    form_of_struggle: EdgeMode = Field(
        ..., description="Qualitative mode of the contradiction on an edge"
    )

    is_antagonistic: bool = Field(
        default=False,
        description="Whether this contradiction is irreconcilable within the current mode of production",
    )

    model_config = {"extra": "forbid"}


class ContradictionFrame(BaseModel):
    """The 2x2 contradiction matrix at a given scale and moment.

    Models the principal and secondary contradictions for a specific scope.
    """

    principal: Contradiction = Field(
        ..., description="The principal contradiction defining the character of the system"
    )
    secondary: Contradiction = Field(
        ..., description="The secondary contradiction operating in the background"
    )

    model_config = {"extra": "forbid"}
