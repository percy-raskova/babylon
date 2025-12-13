"""Context models for simulation tick execution.

This module provides typed context objects that replace raw ``dict[str, Any]``
for passing tick-level information between Systems during simulation.

The :class:`TickContext` maintains backward compatibility with dict-style access
while providing type safety for known keys.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.enums import DisplacementPriorityMode


class TickContext(BaseModel):
    """Typed context for a single simulation tick.

    Provides type-safe access to tick-level information while maintaining
    backward compatibility with dict-style access via ``__getitem__``.

    Attributes:
        tick: Current simulation tick number.
        persistent_data: Data that persists across ticks (e.g., previous_wages
            for the bifurcation mechanic in ConsciousnessSystem).
        displacement_mode: Optional override for territory displacement routing
            in TerritorySystem.

    Example::

        >>> ctx = TickContext(tick=5)
        >>> ctx.tick
        5
        >>> ctx["tick"]  # Backward compatible dict access
        5
        >>> ctx.get("tick", 0)  # Dict-style get with default
        5
        >>> ctx.persistent_data["previous_wages"] = {"worker": 100.0}
        >>> "previous_wages" in ctx
        True
    """

    model_config = ConfigDict(extra="allow")

    tick: int = 0
    persistent_data: dict[str, Any] = Field(default_factory=dict)
    displacement_mode: DisplacementPriorityMode | None = None

    def __getitem__(self, key: str) -> Any:
        """Enable dict-style read access for backward compatibility.

        Args:
            key: Attribute name to access.

        Returns:
            Attribute value, or value from persistent_data if not a direct
            attribute.

        Raises:
            KeyError: If key not found in attributes or persistent_data.
        """
        if key == "tick":
            return self.tick
        if key == "displacement_mode":
            return self.displacement_mode
        if key in self.persistent_data:
            return self.persistent_data[key]
        raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Enable dict-style write access for backward compatibility.

        Args:
            key: Attribute name to set.
            value: Value to assign.
        """
        if key == "tick":
            object.__setattr__(self, "tick", value)
        elif key == "displacement_mode":
            object.__setattr__(self, "displacement_mode", value)
        else:
            self.persistent_data[key] = value

    def __contains__(self, key: object) -> bool:
        """Check if key exists in context.

        Args:
            key: Key to check for existence.

        Returns:
            True if key is a known attribute or in persistent_data.
        """
        if key in ("tick", "displacement_mode"):
            return True
        return key in self.persistent_data

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-compatible get method with default value.

        Args:
            key: Key to look up.
            default: Value to return if key not found.

        Returns:
            Value for key, or default if not found.
        """
        try:
            return self[key]
        except KeyError:
            return default
