"""MetricsCollector observer for unified simulation metrics.

Implements SimulationObserver protocol to collect comprehensive metrics
during simulation runs. Supports two modes:

- "interactive": Rolling window of recent ticks (for dashboard)
- "batch": Accumulates all history (for parameter sweeps)

Sprint 4.1: Phase 4 Dashboard/Sweeper unification.
Sprint 4.1C: Add JSON export for DAG structure preservation.
"""

from __future__ import annotations

import json
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Literal

from babylon.models.enums import EdgeType
from babylon.models.metrics import EdgeMetrics, EntityMetrics, SweepSummary, TickMetrics

if TYPE_CHECKING:
    from babylon.config.defines import GameDefines
    from babylon.models.config import SimulationConfig
    from babylon.models.entities.social_class import SocialClass
    from babylon.models.world_state import WorldState

# Entity ID to slot mapping
ENTITY_SLOTS: Final[dict[str, str]] = {
    "C001": "p_w",  # Periphery Worker
    "C002": "p_c",  # Comprador
    "C003": "c_b",  # Core Bourgeoisie
    "C004": "c_w",  # Labor Aristocracy
}

# Death threshold for outcome determination
DEATH_THRESHOLD: Final[float] = 0.001


class MetricsCollector:
    """Observer that collects simulation metrics for analysis.

    Implements SimulationObserver protocol. Extracts entity and edge
    metrics at each tick, with optional rolling window for memory
    efficiency in interactive mode.
    """

    def __init__(
        self,
        mode: Literal["interactive", "batch"] = "interactive",
        rolling_window: int = 50,
    ) -> None:
        """Initialize the collector.

        Args:
            mode: "interactive" uses rolling window, "batch" keeps all history
            rolling_window: Maximum ticks to keep in interactive mode
        """
        self._mode: Literal["interactive", "batch"] = mode
        self._rolling_window = rolling_window
        self._history: deque[TickMetrics] | list[TickMetrics]
        if mode == "interactive":
            self._history = deque(maxlen=rolling_window)
        else:
            self._history = []

    @property
    def name(self) -> str:
        """Return observer identifier."""
        return "MetricsCollector"

    @property
    def latest(self) -> TickMetrics | None:
        """Return most recent tick metrics, or None if empty."""
        if not self._history:
            return None
        return self._history[-1]

    @property
    def history(self) -> list[TickMetrics]:
        """Return metrics history as a list."""
        return list(self._history)

    @property
    def summary(self) -> SweepSummary | None:
        """Return sweep summary, or None if no data collected."""
        if not self._history:
            return None
        return self._compute_summary()

    def on_simulation_start(
        self,
        initial_state: WorldState,
        config: SimulationConfig,  # noqa: ARG002 - Required by SimulationObserver protocol
    ) -> None:
        """Called when simulation begins. Clears history and records tick 0."""
        # Clear history
        if self._mode == "interactive":
            self._history = deque(maxlen=self._rolling_window)
        else:
            self._history = []

        # Record initial state
        snapshot = self._record_snapshot(initial_state)
        self._history.append(snapshot)

    def on_tick(
        self,
        previous_state: WorldState,  # noqa: ARG002 - Required by SimulationObserver protocol
        new_state: WorldState,
    ) -> None:
        """Called after each tick completes. Records new state."""
        snapshot = self._record_snapshot(new_state)
        self._history.append(snapshot)

    def on_simulation_end(self, final_state: WorldState) -> None:
        """Called when simulation ends. No-op for MetricsCollector."""
        pass

    def to_csv_rows(self) -> list[dict[str, Any]]:
        """Export metrics history as list of dicts for CSV output."""
        rows: list[dict[str, Any]] = []
        for tick_metrics in self._history:
            row: dict[str, Any] = {"tick": tick_metrics.tick}

            # Flatten p_w metrics
            if tick_metrics.p_w is not None:
                row["p_w_wealth"] = tick_metrics.p_w.wealth
                row["p_w_consciousness"] = tick_metrics.p_w.consciousness
                row["p_w_national_identity"] = tick_metrics.p_w.national_identity
                row["p_w_agitation"] = tick_metrics.p_w.agitation
                row["p_w_psa"] = tick_metrics.p_w.p_acquiescence
                row["p_w_psr"] = tick_metrics.p_w.p_revolution
                row["p_w_organization"] = tick_metrics.p_w.organization

            # Flatten p_c metrics (wealth only)
            if tick_metrics.p_c is not None:
                row["p_c_wealth"] = tick_metrics.p_c.wealth

            # Flatten c_b metrics (wealth only)
            if tick_metrics.c_b is not None:
                row["c_b_wealth"] = tick_metrics.c_b.wealth

            # Flatten c_w metrics
            if tick_metrics.c_w is not None:
                row["c_w_wealth"] = tick_metrics.c_w.wealth
                row["c_w_consciousness"] = tick_metrics.c_w.consciousness
                row["c_w_national_identity"] = tick_metrics.c_w.national_identity
                row["c_w_agitation"] = tick_metrics.c_w.agitation

            # Edge metrics
            row["exploitation_tension"] = tick_metrics.edges.exploitation_tension
            row["exploitation_rent"] = tick_metrics.edges.exploitation_rent
            row["tribute_flow"] = tick_metrics.edges.tribute_flow
            row["wages_paid"] = tick_metrics.edges.wages_paid
            row["solidarity_strength"] = tick_metrics.edges.solidarity_strength

            # Global metrics
            row["imperial_rent_pool"] = tick_metrics.imperial_rent_pool
            row["global_tension"] = tick_metrics.global_tension

            # Economy drivers (Phase 4.1B)
            row["current_super_wage_rate"] = tick_metrics.current_super_wage_rate
            row["current_repression_level"] = tick_metrics.current_repression_level
            row["pool_ratio"] = tick_metrics.pool_ratio

            # Derived differentials (Phase 4.1B)
            row["consciousness_gap"] = tick_metrics.consciousness_gap
            row["wealth_gap"] = tick_metrics.wealth_gap

            rows.append(row)

        return rows

    def to_json(
        self,
        defines: GameDefines,
        config: SimulationConfig,
        csv_path: Path | None = None,
    ) -> dict[str, Any]:
        """Export run metadata as structured JSON for reproducibility.

        Captures the causal DAG hierarchy:
        - Level 1 (Fundamental): GameDefines parameters
        - Level 2 (Config): SimulationConfig settings
        - Level 3 (Emergent): SweepSummary computed from simulation

        Args:
            defines: GameDefines with fundamental parameters
            config: SimulationConfig with run settings
            csv_path: Optional path to associated CSV time-series file

        Returns:
            Structured dict ready for JSON serialization
        """
        summary = self.summary
        return {
            "schema_version": "1.0",
            "generated_at": datetime.now(UTC).isoformat(),
            "causal_dag_levels": {
                "fundamental": "GameDefines - exogenous parameters",
                "config": "SimulationConfig - run settings",
                "emergent": "SweepSummary - observed outcomes",
            },
            "fundamentals": defines.model_dump(mode="json"),
            "config": config.model_dump(mode="json"),
            "summary": summary.model_dump(mode="json") if summary else None,
            "ticks_collected": len(self._history),
            "time_series_csv": str(csv_path) if csv_path else None,
        }

    def export_json(
        self,
        path: Path,
        defines: GameDefines,
        config: SimulationConfig,
        csv_path: Path | None = None,
    ) -> None:
        """Write JSON metadata to file.

        Args:
            path: Output path for JSON file
            defines: GameDefines with fundamental parameters
            config: SimulationConfig with run settings
            csv_path: Optional path to associated CSV time-series file
        """
        data = self.to_json(defines, config, csv_path)
        path.write_text(json.dumps(data, indent=2, default=str))

    def _record_snapshot(self, state: WorldState) -> TickMetrics:
        """Extract metrics from WorldState and create TickMetrics."""
        # Extract entity metrics
        entity_slots: dict[str, EntityMetrics | None] = {}
        for entity_id, slot_name in ENTITY_SLOTS.items():
            entity = state.entities.get(entity_id)
            if entity is not None:
                entity_slots[slot_name] = self._extract_entity_metrics(entity)
            else:
                entity_slots[slot_name] = None

        # Extract edge metrics
        edge_metrics = self._extract_edge_metrics(state)

        # Extract global metrics
        imperial_rent_pool = 0.0
        if state.economy is not None:
            imperial_rent_pool = float(state.economy.imperial_rent_pool)

        global_tension = self._compute_global_tension(state)

        # Extract economy drivers
        current_super_wage_rate = 0.20
        current_repression_level = 0.5
        pool_ratio = 1.0
        if state.economy is not None:
            current_super_wage_rate = float(state.economy.current_super_wage_rate)
            current_repression_level = float(state.economy.current_repression_level)
            pool_ratio = min(float(state.economy.imperial_rent_pool) / 100.0, 1.0)

        # Calculate differentials
        consciousness_gap = 0.0
        wealth_gap = 0.0
        p_w = entity_slots.get("p_w")
        c_w = entity_slots.get("c_w")
        c_b = entity_slots.get("c_b")
        if p_w is not None and c_w is not None:
            consciousness_gap = float(p_w.consciousness) - float(c_w.consciousness)
        if c_b is not None and p_w is not None:
            wealth_gap = float(c_b.wealth) - float(p_w.wealth)

        return TickMetrics(
            tick=state.tick,
            p_w=entity_slots.get("p_w"),
            p_c=entity_slots.get("p_c"),
            c_b=entity_slots.get("c_b"),
            c_w=entity_slots.get("c_w"),
            edges=edge_metrics,
            imperial_rent_pool=imperial_rent_pool,
            global_tension=global_tension,
            current_super_wage_rate=current_super_wage_rate,
            current_repression_level=current_repression_level,
            pool_ratio=pool_ratio,
            consciousness_gap=consciousness_gap,
            wealth_gap=wealth_gap,
        )

    def _extract_entity_metrics(self, entity: SocialClass) -> EntityMetrics:
        """Extract EntityMetrics from a SocialClass entity."""
        return EntityMetrics(
            wealth=float(entity.wealth),
            consciousness=float(entity.ideology.class_consciousness),
            national_identity=float(entity.ideology.national_identity),
            agitation=float(entity.ideology.agitation),
            p_acquiescence=float(entity.p_acquiescence),
            p_revolution=float(entity.p_revolution),
            organization=float(entity.organization),
        )

    def _extract_edge_metrics(self, state: WorldState) -> EdgeMetrics:
        """Extract EdgeMetrics from WorldState relationships with aggregation."""
        exploitation_tensions: list[float] = []
        exploitation_rents: list[float] = []
        tribute_flows: list[float] = []
        wages_paid_list: list[float] = []
        solidarity_strengths: list[float] = []

        for rel in state.relationships:
            if rel.edge_type == EdgeType.EXPLOITATION:
                exploitation_tensions.append(float(rel.tension))
                exploitation_rents.append(float(rel.value_flow))
            elif rel.edge_type == EdgeType.TRIBUTE:
                tribute_flows.append(float(rel.value_flow))
            elif rel.edge_type == EdgeType.WAGES:
                wages_paid_list.append(float(rel.value_flow))
            elif rel.edge_type == EdgeType.SOLIDARITY:
                solidarity_strengths.append(float(rel.solidarity_strength))

        return EdgeMetrics(
            exploitation_tension=max(exploitation_tensions, default=0.0),
            exploitation_rent=sum(exploitation_rents),
            tribute_flow=sum(tribute_flows),
            wages_paid=sum(wages_paid_list),
            solidarity_strength=max(solidarity_strengths, default=0.0),
        )

    def _compute_global_tension(self, state: WorldState) -> float:
        """Compute average tension across EXPLOITATION relationships only."""
        exploitation_rels = [
            rel for rel in state.relationships if rel.edge_type == EdgeType.EXPLOITATION
        ]
        if not exploitation_rels:
            return 0.0
        total_tension = sum(float(rel.tension) for rel in exploitation_rels)
        return total_tension / len(exploitation_rels)

    def _compute_summary(self) -> SweepSummary:
        """Compute SweepSummary from history."""
        history_list = list(self._history)
        if not history_list:
            return SweepSummary(
                ticks_survived=0,
                outcome="ERROR",
                final_p_w_wealth=0.0,
                final_p_c_wealth=0.0,
                final_c_b_wealth=0.0,
                final_c_w_wealth=0.0,
                max_tension=0.0,
                crossover_tick=None,
                cumulative_rent=0.0,
                peak_p_w_consciousness=0.0,
                peak_c_w_consciousness=0.0,
            )

        last_tick = history_list[-1]
        ticks_survived = len(history_list)

        # Determine outcome
        p_w_wealth = last_tick.p_w.wealth if last_tick.p_w is not None else 0.0
        outcome: Literal["SURVIVED", "DIED", "ERROR"] = (
            "DIED" if p_w_wealth <= DEATH_THRESHOLD else "SURVIVED"
        )

        # Final wealth values
        final_p_w_wealth = last_tick.p_w.wealth if last_tick.p_w is not None else 0.0
        final_p_c_wealth = last_tick.p_c.wealth if last_tick.p_c is not None else 0.0
        final_c_b_wealth = last_tick.c_b.wealth if last_tick.c_b is not None else 0.0
        final_c_w_wealth = last_tick.c_w.wealth if last_tick.c_w is not None else 0.0

        # Max tension
        max_tension = max(tick.edges.exploitation_tension for tick in history_list)

        # Crossover detection (first tick where P(S|R) > P(S|A))
        crossover_tick: int | None = None
        for tick in history_list:
            if tick.p_w is not None and tick.p_w.p_revolution > tick.p_w.p_acquiescence:
                crossover_tick = tick.tick
                break

        # Cumulative rent
        cumulative_rent = sum(tick.edges.exploitation_rent for tick in history_list)

        # Peak consciousness
        peak_p_w_consciousness = max(
            (tick.p_w.consciousness for tick in history_list if tick.p_w is not None),
            default=0.0,
        )
        peak_c_w_consciousness = max(
            (tick.c_w.consciousness for tick in history_list if tick.c_w is not None),
            default=0.0,
        )

        return SweepSummary(
            ticks_survived=ticks_survived,
            outcome=outcome,
            final_p_w_wealth=final_p_w_wealth,
            final_p_c_wealth=final_p_c_wealth,
            final_c_b_wealth=final_c_b_wealth,
            final_c_w_wealth=final_c_w_wealth,
            max_tension=max_tension,
            crossover_tick=crossover_tick,
            cumulative_rent=cumulative_rent,
            peak_p_w_consciousness=peak_p_w_consciousness,
            peak_c_w_consciousness=peak_c_w_consciousness,
        )
