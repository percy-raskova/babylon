"""MetricsCollector observer for unified simulation metrics.

Implements SimulationObserver protocol to collect comprehensive metrics
during simulation runs. Supports two modes:

- "interactive": Rolling window of recent ticks (for dashboard)
- "batch": Accumulates all history (for parameter sweeps)

Sprint 4.1: Phase 4 Dashboard/Sweeper unification.

RED PHASE STUB: This module contains minimal stubs that raise
NotImplementedError. The GREEN phase will provide implementations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from babylon.models.config import SimulationConfig
    from babylon.models.metrics import SweepSummary, TickMetrics
    from babylon.models.world_state import WorldState


class MetricsCollector:
    """Observer that collects simulation metrics for analysis.

    Implements SimulationObserver protocol. Extracts entity and edge
    metrics at each tick, with optional rolling window for memory
    efficiency in interactive mode.

    RED PHASE: Stub that raises NotImplementedError on all operations.
    """

    def __init__(
        self,
        mode: str = "interactive",
        rolling_window: int = 50,
    ) -> None:
        """Stub: raises NotImplementedError."""
        raise NotImplementedError("MetricsCollector not yet implemented (RED phase)")

    @property
    def name(self) -> str:
        """Return observer identifier."""
        raise NotImplementedError("MetricsCollector.name not yet implemented (RED phase)")

    @property
    def latest(self) -> TickMetrics | None:
        """Return most recent tick metrics, or None if empty."""
        raise NotImplementedError("MetricsCollector.latest not yet implemented (RED phase)")

    @property
    def history(self) -> list[TickMetrics]:
        """Return metrics history as a list (respects rolling window in interactive mode)."""
        raise NotImplementedError("MetricsCollector.history not yet implemented (RED phase)")

    @property
    def summary(self) -> SweepSummary | None:
        """Return sweep summary, or None if no data collected."""
        raise NotImplementedError("MetricsCollector.summary not yet implemented (RED phase)")

    def on_simulation_start(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
    ) -> None:
        """Called when simulation begins."""
        raise NotImplementedError(
            "MetricsCollector.on_simulation_start not yet implemented (RED phase)"
        )

    def on_tick(
        self,
        previous_state: WorldState,
        new_state: WorldState,
    ) -> None:
        """Called after each tick completes."""
        raise NotImplementedError("MetricsCollector.on_tick not yet implemented (RED phase)")

    def on_simulation_end(self, final_state: WorldState) -> None:
        """Called when simulation ends."""
        raise NotImplementedError(
            "MetricsCollector.on_simulation_end not yet implemented (RED phase)"
        )

    def to_csv_rows(self) -> list[dict[str, Any]]:
        """Export metrics history as list of dicts for CSV output."""
        raise NotImplementedError("MetricsCollector.to_csv_rows not yet implemented (RED phase)")
