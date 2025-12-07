"""Contradiction Analysis System for Babylon.

This system implements the dialectical logic of the simulation.
Contradictions are not bugs - they are the engine of history.

The mathematics of contradiction:
- Thesis + Antithesis -> Synthesis
- Quantity -> Quality (phase transitions)
- Negation of the Negation (revolutionary spirals)

Models are imported from babylon.models.entities for consistency.
"""

from __future__ import annotations

import logging
from typing import Any

from babylon.models.entities import ContradictionState, ResolutionOutcome
from babylon.models.enums import ResolutionType

logger = logging.getLogger(__name__)

# Re-export for backwards compatibility
__all__ = ["ContradictionState", "ResolutionOutcome", "ContradictionAnalysis"]


class ContradictionAnalysis:
    """Analyzes and evolves the dialectical contradictions in the simulation.

    This is the engine of historical change. Contradictions accumulate
    tension until they either resolve through synthesis or rupture.

    The class tracks:
    - Active contradictions and their states
    - The principal contradiction of the current period
    - Contradiction interdependencies (one affects another)
    """

    def __init__(self) -> None:
        """Initialize the contradiction analysis system."""
        self._contradictions: dict[str, ContradictionState] = {}
        self._dependencies: dict[str, list[str]] = {}  # source -> affected
        self._propagation_stack: set[str] = set()  # Prevent infinite recursion
        logger.debug("ContradictionAnalysis system initialized")

    def register_contradiction(self, state: ContradictionState) -> None:
        """Register a new contradiction in the system.

        Args:
            state: The contradiction state to register
        """
        self._contradictions[state.id] = state
        logger.info("Registered contradiction: %s", state.name)

    def get_contradiction(self, contradiction_id: str) -> ContradictionState | None:
        """Get a contradiction by ID.

        Args:
            contradiction_id: The contradiction identifier

        Returns:
            The ContradictionState or None if not found
        """
        return self._contradictions.get(contradiction_id)

    def get_principal_contradiction(self) -> ContradictionState | None:
        """Get the principal contradiction of the current period.

        The principal contradiction is the one that determines
        the character of the epoch. All other contradictions
        are secondary and influenced by it.

        Returns:
            The principal ContradictionState or None
        """
        for contradiction in self._contradictions.values():
            if contradiction.is_principal and not contradiction.resolved:
                return contradiction
        return None

    def update_tension(
        self,
        contradiction_id: str,
        delta: float,
        source: str | None = None,
    ) -> ResolutionOutcome | None:
        """Update the tension level of a contradiction.

        Args:
            contradiction_id: The contradiction to update
            delta: Change in tension (-1.0 to 1.0)
            source: Optional description of what caused the change

        Returns:
            ResolutionOutcome if the contradiction resolved, else None
        """
        contradiction = self._contradictions.get(contradiction_id)
        if contradiction is None or contradiction.resolved:
            return None

        # Apply tension change
        old_tension = contradiction.tension
        new_tension = max(0.0, min(1.0, contradiction.tension + delta))
        contradiction.tension = new_tension

        # Update momentum
        contradiction.momentum = delta

        logger.debug(
            "Contradiction %s tension: %.2f -> %.2f (source: %s)",
            contradiction_id,
            old_tension,
            new_tension,
            source or "unknown",
        )

        # Check for phase transitions
        if new_tension >= 1.0:
            return self._resolve_contradiction(contradiction_id, ResolutionType.RUPTURE)
        elif new_tension <= 0.0 and old_tension > 0.0:
            return self._resolve_contradiction(contradiction_id, ResolutionType.SYNTHESIS)

        # Propagate effects to dependent contradictions
        self._propagate_effects(contradiction_id, delta * 0.5)

        return None

    def _resolve_contradiction(
        self,
        contradiction_id: str,
        resolution_type: ResolutionType,
    ) -> ResolutionOutcome:
        """Resolve a contradiction and generate outcomes.

        Args:
            contradiction_id: The contradiction being resolved
            resolution_type: How it was resolved

        Returns:
            The resolution outcome
        """
        contradiction = self._contradictions[contradiction_id]
        contradiction.resolved = True

        logger.info(
            "Contradiction RESOLVED: %s via %s",
            contradiction.name,
            resolution_type,
        )

        # Generate outcome (in full implementation, this would spawn new contradictions)
        outcome = ResolutionOutcome(
            contradiction_id=contradiction_id,
            resolution_type=resolution_type,
            new_contradictions=[],
            system_changes={},
        )

        return outcome

    def _propagate_effects(self, source_id: str, effect_magnitude: float) -> None:
        """Propagate tension changes to dependent contradictions.

        Contradictions are interconnected. A change in one
        ripples through the system.

        Uses a propagation stack to prevent infinite recursion in
        bidirectional dependency graphs (dialectical feedback loops).
        """
        # Prevent infinite recursion in cycles
        if source_id in self._propagation_stack:
            return

        self._propagation_stack.add(source_id)

        try:
            affected_ids = self._dependencies.get(source_id, [])
            for affected_id in affected_ids:
                if affected_id not in self._propagation_stack:
                    self.update_tension(
                        affected_id,
                        effect_magnitude,
                        source=f"propagation from {source_id}",
                    )
        finally:
            self._propagation_stack.discard(source_id)

    def add_dependency(self, source_id: str, target_id: str) -> None:
        """Register that one contradiction affects another.

        Args:
            source_id: The contradiction that causes effects
            target_id: The contradiction that receives effects
        """
        if source_id not in self._dependencies:
            self._dependencies[source_id] = []
        if target_id not in self._dependencies[source_id]:
            self._dependencies[source_id].append(target_id)

    def get_all_active(self) -> list[ContradictionState]:
        """Get all active (unresolved) contradictions.

        Returns:
            List of active contradictions, sorted by tension (highest first)
        """
        active = [c for c in self._contradictions.values() if not c.resolved]
        return sorted(active, key=lambda c: c.tension, reverse=True)

    def summary(self) -> dict[str, Any]:
        """Get a summary of the contradiction system state.

        Returns:
            Dict with counts and key metrics
        """
        active = self.get_all_active()
        principal = self.get_principal_contradiction()

        return {
            "total_contradictions": len(self._contradictions),
            "active_contradictions": len(active),
            "resolved_contradictions": len(self._contradictions) - len(active),
            "principal_contradiction": principal.name if principal else None,
            "highest_tension": active[0].tension if active else 0.0,
            "avg_tension": (sum(c.tension for c in active) / len(active) if active else 0.0),
        }
