"""EconomyMonitor observer for economic crisis detection (Sprint 3.1).

The EconomyMonitor is a SimulationObserver that detects sudden drops
in the imperial_rent_pool and logs [CRISIS_DETECTED] warnings. This
enables AI narrative generation to respond to economic instability.

Theoretical Context:
    The imperial_rent_pool represents the accumulated surplus extracted
    from the periphery. When it drops suddenly (>20%), it signals a
    crisis in the imperial extraction system - either from:
    - Successful peripheral resistance
    - Core over-consumption depleting reserves
    - Supply chain disruption

Detection Logic:
    percentage_change = (new_pool - prev_pool) / prev_pool
    if percentage_change <= CRISIS_THRESHOLD:
        log WARNING with [CRISIS_DETECTED] marker
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState


class EconomyMonitor:
    """Observer detecting economic crises via imperial_rent_pool drops.

    Implements SimulationObserver protocol to receive state change
    notifications and analyze economic state for crisis conditions.

    A crisis is detected when the imperial_rent_pool drops by 20% or more
    from the previous tick. The [CRISIS_DETECTED] log marker allows AI
    narrative systems to respond appropriately.

    Attributes:
        CRISIS_THRESHOLD: Class constant defining crisis trigger (-0.20 = 20% drop).
        name: Observer identifier ("EconomyMonitor").

    Example:
        >>> from babylon.engine.observers.economic import EconomyMonitor
        >>> monitor = EconomyMonitor()
        >>> monitor.name
        'EconomyMonitor'
    """

    CRISIS_THRESHOLD: float = -0.20
    """Percentage drop threshold that triggers crisis detection (-20%)."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        """Initialize EconomyMonitor.

        Args:
            logger: Logger instance for crisis warnings.
                Defaults to module-level logger if not provided.
        """
        self._logger: logging.Logger = logger or logging.getLogger(__name__)

    @property
    def name(self) -> str:
        """Return observer identifier.

        Returns:
            String "EconomyMonitor" for logging and debugging.
        """
        return "EconomyMonitor"

    def on_simulation_start(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Called when simulation begins.

        No-op for EconomyMonitor. Crisis detection only operates
        on state transitions, not initial state.

        Args:
            initial_state: WorldState at tick 0 (unused).
            config: SimulationConfig for this run (unused).
        """
        pass

    def on_tick(
        self,
        previous_state: WorldState,
        new_state: WorldState,
    ) -> None:
        """Called after each tick completes with both states for delta analysis.

        Compares imperial_rent_pool between states and logs a warning
        if the drop exceeds CRISIS_THRESHOLD (20%).

        Args:
            previous_state: WorldState before the tick.
            new_state: WorldState after the tick.
        """
        prev_pool = previous_state.economy.imperial_rent_pool
        new_pool = new_state.economy.imperial_rent_pool

        # Guard against division by zero
        if prev_pool <= 0.0:
            return

        percentage_change = (new_pool - prev_pool) / prev_pool

        if percentage_change <= self.CRISIS_THRESHOLD:
            drop_percent = abs(percentage_change * 100)
            self._logger.warning(
                "[CRISIS_DETECTED] Imperial rent pool dropped by %.1f%% (%.2f -> %.2f)",
                drop_percent,
                prev_pool,
                new_pool,
            )

    def on_simulation_end(self, final_state: WorldState) -> None:
        """Called when simulation ends.

        No-op for EconomyMonitor. No cleanup or summary needed.

        Args:
            final_state: Final WorldState when simulation ends (unused).
        """
        pass
