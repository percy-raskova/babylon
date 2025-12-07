"""Trigger model for event conditions.

A Trigger defines conditions that can cause events to occur.
Triggers are the connection between game state and event generation.

This replaces the old dataclass in data/models/trigger.py.

Design note: The old Trigger used a Callable for the condition,
which cannot be serialized. This version uses a declarative
condition specification that can be evaluated and serialized.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class TriggerCondition(BaseModel):
    """A single condition that can be evaluated against game state.

    Conditions specify what to check, how to compare, and what threshold
    to use. Multiple conditions can be combined in a Trigger.

    Attributes:
        path: Dot-notation path to the value in game state (e.g., "economy.gini_coefficient")
        operator: Comparison operator
        threshold: Value to compare against
        description: Human-readable explanation
    """

    path: str = Field(..., description="Dot-notation path to value in game state")
    operator: Literal[">=", "<=", ">", "<", "==", "!="] = Field(
        ..., description="Comparison operator"
    )
    threshold: float = Field(..., description="Value to compare against")
    description: str = Field(default="", description="Human-readable explanation")

    model_config = {"extra": "forbid"}

    def evaluate(self, game_state: dict[str, Any]) -> bool:
        """Evaluate this condition against the game state.

        Args:
            game_state: The current game state dictionary

        Returns:
            True if the condition is met, False otherwise
        """
        # Navigate the dot-notation path
        value = self._get_nested_value(game_state, self.path)
        if value is None:
            return False

        # Apply the comparison
        if self.operator == ">=":
            return value >= self.threshold
        elif self.operator == "<=":
            return value <= self.threshold
        elif self.operator == ">":
            return value > self.threshold
        elif self.operator == "<":
            return value < self.threshold
        elif self.operator == "==":
            return value == self.threshold
        elif self.operator == "!=":
            return value != self.threshold
        else:
            return False

    def _get_nested_value(self, data: dict[str, Any], path: str) -> float | None:
        """Get a value from nested dictionary using dot notation.

        Args:
            data: The dictionary to search
            path: Dot-notation path (e.g., "economy.gini_coefficient")

        Returns:
            The value at the path, or None if not found
        """
        keys = path.split(".")
        current: Any = data

        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            elif hasattr(current, key):
                current = getattr(current, key)
            else:
                return None

            if current is None:
                return None

        # Convert to float if possible
        if isinstance(current, (int, float)):
            return float(current)
        if isinstance(current, str):
            try:
                return float(current)
            except ValueError:
                return None
        return None


class Trigger(BaseModel):
    """A condition that can trigger game events.

    Triggers define when events should occur based on game state.
    They can have multiple conditions that must all be met (AND logic)
    or any one met (OR logic).

    Attributes:
        id: Unique identifier
        description: Human-readable description
        trigger_type: Category of trigger (economic, political, social, etc.)
        conditions: List of conditions to evaluate
        logic: How to combine conditions (all must pass or any must pass)
        parameters: Optional parameters for condition evaluation
        cooldown_turns: Minimum turns between activations (0 = no cooldown)
        last_triggered_turn: Turn when this was last triggered
    """

    id: str = Field(..., description="Unique identifier")
    description: str = Field(..., description="Human-readable description")
    trigger_type: str | None = Field(
        default=None, description="Category: economic, political, social, etc."
    )
    conditions: list[TriggerCondition] = Field(
        default_factory=list, description="Conditions to evaluate"
    )
    logic: Literal["all", "any"] = Field(
        default="all", description="Logic for combining conditions: all (AND) or any (OR)"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Optional parameters"
    )
    cooldown_turns: int = Field(
        default=0, ge=0, description="Minimum turns between activations"
    )
    last_triggered_turn: int | None = Field(
        default=None, description="Turn when last triggered"
    )

    model_config = {"extra": "forbid"}

    def evaluate(self, game_state: dict[str, Any], current_turn: int = 0) -> bool:
        """Evaluate if the trigger condition is met.

        Args:
            game_state: The current game state to evaluate against
            current_turn: The current turn number (for cooldown checking)

        Returns:
            True if the trigger condition is met, False otherwise
        """
        # Check cooldown
        if self.last_triggered_turn is not None:
            turns_since = current_turn - self.last_triggered_turn
            if turns_since < self.cooldown_turns:
                return False

        # No conditions = always triggers
        if not self.conditions:
            return True

        # Evaluate conditions based on logic
        if self.logic == "all":
            return all(cond.evaluate(game_state) for cond in self.conditions)
        else:  # any
            return any(cond.evaluate(game_state) for cond in self.conditions)

    def mark_triggered(self, current_turn: int) -> None:
        """Mark this trigger as having been triggered.

        Args:
            current_turn: The current turn number
        """
        self.last_triggered_turn = current_turn
