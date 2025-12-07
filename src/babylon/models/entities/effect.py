"""Effect model for state modifications.

An Effect represents an atomic change to the game state.
Effects are the fundamental unit of state mutation in the simulation.

This replaces the old dataclass in data/models/contradiction.py.
"""

from typing import Literal

from pydantic import BaseModel, Field


class Effect(BaseModel):
    """A modification to game state.

    Effects are the atoms of change - they modify single attributes
    on single targets by specific amounts. Every state change in the
    simulation should be expressible as one or more Effects.

    Attributes:
        target_id: ID of the entity to modify
        attribute: Name of the attribute to change
        operation: How to modify the value
        magnitude: Amount of change (interpretation depends on operation)
        description: Human-readable explanation of why this effect occurs
    """

    target_id: str = Field(..., description="Entity ID to modify")
    attribute: str = Field(..., description="Attribute name to change")
    operation: Literal["increase", "decrease", "set", "multiply"] = Field(
        ...,
        description="Operation to perform: increase/decrease add/subtract, set replaces, multiply scales",
    )
    magnitude: float = Field(..., description="Amount of change")
    description: str = Field(default="", description="Why this effect occurs")

    model_config = {"extra": "forbid"}

    def apply_to(self, current_value: float) -> float:
        """Calculate the new value after applying this effect.

        Args:
            current_value: The current value of the attribute

        Returns:
            The new value after the effect is applied
        """
        if self.operation == "increase":
            return current_value + self.magnitude
        elif self.operation == "decrease":
            return current_value - self.magnitude
        elif self.operation == "set":
            return self.magnitude
        elif self.operation == "multiply":
            return current_value * self.magnitude
        else:
            # Should be unreachable due to Literal type
            raise ValueError(f"Unknown operation: {self.operation}")
