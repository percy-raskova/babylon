"""Protocol definitions for the State Apparatus AI (Feature 039).

Defines the NPCDecisionStrategy protocol for pluggable state AI implementations.
The default implementation is RuleBasedStateAI (decision.py).

See Also:
    :mod:`babylon.ooda.state_ai.decision`: Default implementation.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from babylon.config.defines import StateApparatusAIDefines
from babylon.models.entities.state_apparatus_ai import StateAction


@runtime_checkable
class NPCDecisionStrategy(Protocol):
    """Protocol for state apparatus AI decision strategies.

    Implementations must select one or more StateActions given the current
    game state. The decision function must be deterministic given identical
    inputs and RNG seed.

    Reference: FR-D01, FR-D08.
    """

    def select_action(
        self,
        org_id: str,
        org_attrs: dict[str, Any],
        graph: Any,
        context: dict[str, Any],
        defines: StateApparatusAIDefines,
    ) -> list[StateAction]:
        """Select state actions for this tick.

        Args:
            org_id: StateApparatus organization node ID.
            org_attrs: Organization node attributes dict.
            graph: Graph protocol instance (read-only for decision).
            context: Simulation context with persistent_data.
            defines: State AI configuration coefficients.

        Returns:
            List of StateAction instances (may be empty if no budget).
        """
        ...
