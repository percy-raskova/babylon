"""CausalChainObserver for detecting the "Shock Doctrine" pattern (Sprint 3.2).

The CausalChainObserver is a SimulationObserver that detects causal chains
in simulation state changes and outputs structured JSON NarrativeFrame.

Theoretical Context (Naomi Klein's "Shock Doctrine"):
    The Shock Doctrine pattern describes how economic crises (shocks) are
    exploited to impose austerity measures while populations are disoriented.
    This leads to radicalization as material conditions worsen:

    1. ECONOMIC_SHOCK: Pool drops > 20% (crisis hits)
    2. AUSTERITY_RESPONSE: Wages decrease (bourgeoisie cuts costs)
    3. RADICALIZATION: P(Revolution) increases (class consciousness rises)

Detection Logic:
    - Maintain rolling 5-tick history buffer
    - Check for sequential pattern: Crash(N) -> Austerity(N+1) -> Radicalization(N+2)
    - Output JSON NarrativeFrame with causal graph structure

Output Format:
    [NARRATIVE_JSON] {"causal_graph": {"nodes": [...], "edges": [...]}}
"""

from __future__ import annotations

import json
import logging
from collections import deque
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState


class TickSnapshot(NamedTuple):
    """Immutable snapshot of economic metrics at a single tick.

    Attributes:
        tick: The tick number.
        pool: Imperial rent pool value (Currency).
        wage: Current super-wage rate (Coefficient).
        p_rev: Maximum P(Revolution) across all entities.
    """

    tick: int
    pool: float
    wage: float
    p_rev: float


class CausalChainObserver:
    """Observer detecting the Shock Doctrine causal chain pattern.

    Implements SimulationObserver protocol to receive state change
    notifications and analyze for the Crash -> Austerity -> Radicalization
    pattern that emerges from economic crises.

    The pattern is detected when:
    - Tick N: Pool drops >= 20% (ECONOMIC_SHOCK)
    - Tick N+1 or later: Wage decreases (AUSTERITY_RESPONSE)
    - Tick N+2 or later: P(Revolution) increases (RADICALIZATION)

    When detected, outputs a JSON NarrativeFrame with [NARRATIVE_JSON] prefix
    at WARNING level for AI narrative generation.

    Attributes:
        CRASH_THRESHOLD: Class constant defining crash trigger (-0.20 = 20% drop).
        BUFFER_SIZE: Size of the rolling history buffer (5 ticks).
        name: Observer identifier ("CausalChainObserver").

    Example:
        >>> from babylon.engine.observers.causal import CausalChainObserver
        >>> observer = CausalChainObserver()
        >>> observer.name
        'CausalChainObserver'
    """

    CRASH_THRESHOLD: float = -0.20
    """Percentage drop threshold that triggers economic shock detection (-20%)."""

    BUFFER_SIZE: int = 5
    """Size of the rolling history buffer for pattern detection."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        """Initialize CausalChainObserver.

        Args:
            logger: Logger instance for narrative JSON output.
                Defaults to module-level logger if not provided.
        """
        self._logger: logging.Logger = logger or logging.getLogger(__name__)
        self._history: deque[TickSnapshot] = deque(maxlen=self.BUFFER_SIZE)
        # Spec-116 FR-4.1: frames captured by the MOST RECENT on_tick call
        # (rebound, not mutated, each tick — a previously returned tuple
        # stays valid), plus the emitted-window dedup set. The rolling
        # buffer re-matches the same 3-tick window for up to BUFFER_SIZE-3
        # further ticks; keying emissions by the window's crash tick (one
        # snapshot per tick => a window is fully identified by it) stops
        # cross-tick re-emission.
        self._tick_frames: list[dict[str, object]] = []
        self._emitted_crash_ticks: set[int] = set()

    @property
    def name(self) -> str:
        """Return observer identifier.

        Returns:
            String "CausalChainObserver" for logging and debugging.
        """
        return "CausalChainObserver"

    @property
    def latest_frames(self) -> tuple[dict[str, object], ...]:
        """Frames captured during the most recent ``on_tick`` call.

        One ``TICK_PULSE`` delta frame per tick (from the second recorded
        snapshot onward — the spec-116 §6 heartbeat), plus a
        ``SHOCK_DOCTRINE`` frame on the tick a new pattern window is
        detected. Empty before the first tick and immediately after
        ``on_simulation_start``.

        Returns:
            Immutable snapshot of this tick's frames (possibly empty).
        """
        return tuple(self._tick_frames)

    def on_simulation_start(
        self,
        initial_state: WorldState,
        config: SimulationConfig,  # noqa: ARG002
    ) -> None:
        """Called when simulation begins.

        Clears the history buffer, the captured frames, and the
        emitted-window dedup set, then records the initial state as baseline.

        Args:
            initial_state: WorldState at tick 0.
            config: SimulationConfig for this run (unused).
        """
        self._history.clear()
        self._tick_frames = []
        self._emitted_crash_ticks.clear()
        self._record_snapshot(initial_state)

    def on_tick(
        self,
        previous_state: WorldState,  # noqa: ARG002
        new_state: WorldState,
    ) -> None:
        """Called after each tick completes with both states for delta analysis.

        Records the new state, captures this tick's pulse frame, and checks
        for the Shock Doctrine pattern. Detected frames are appended to
        ``latest_frames`` (and the shock frame is still logged with the
        ``[NARRATIVE_JSON]`` prefix for backward compatibility).

        Args:
            previous_state: WorldState before the tick (unused, history is internal).
            new_state: WorldState after the tick.
        """
        self._tick_frames = []
        self._record_snapshot(new_state)
        self._capture_pulse_frame()
        self._detect_shock_doctrine()
        self._prune_emitted_windows()

    def _capture_pulse_frame(self) -> None:
        """Append the per-tick TICK_PULSE delta frame (needs >= 2 snapshots)."""
        if len(self._history) < 2:
            return
        self._tick_frames.append(self._build_pulse_frame(self._history[-2], self._history[-1]))

    def _build_pulse_frame(self, prev: TickSnapshot, cur: TickSnapshot) -> dict[str, object]:
        """Build the TICK_PULSE frame from two consecutive snapshots.

        Args:
            prev: The prior tick's snapshot.
            cur: This tick's snapshot.

        Returns:
            ``{"pattern": "TICK_PULSE", "tick": int, "deltas": {...}}`` with
            before/after pairs for pool, wage, and peak p_revolution.
        """
        return {
            "pattern": "TICK_PULSE",
            "tick": cur.tick,
            "deltas": {
                "pool": {"before": prev.pool, "after": cur.pool},
                "wage": {"before": prev.wage, "after": cur.wage},
                "p_rev": {"before": prev.p_rev, "after": cur.p_rev},
            },
        }

    def on_simulation_end(self, final_state: WorldState) -> None:
        """Called when simulation ends.

        No-op for CausalChainObserver. No cleanup or summary needed.

        Args:
            final_state: Final WorldState when simulation ends (unused).
        """
        pass

    def _extract_max_p_rev(self, state: WorldState) -> float:
        """Extract maximum P(Revolution) from all entities in state.

        Args:
            state: WorldState to analyze.

        Returns:
            Maximum p_revolution value across all entities, or 0.0 if no entities.
        """
        if not state.entities:
            return 0.0
        return max(entity.p_revolution for entity in state.entities.values())

    def _record_snapshot(self, state: WorldState) -> None:
        """Record a snapshot of the current state into history buffer.

        Args:
            state: WorldState to snapshot.
        """
        snapshot = TickSnapshot(
            tick=state.tick,
            pool=float(state.economy.imperial_rent_pool),
            wage=float(state.economy.current_super_wage_rate),
            p_rev=self._extract_max_p_rev(state),
        )
        self._history.append(snapshot)

    def _detect_shock_doctrine(self) -> None:
        """Check history for Shock Doctrine pattern and emit if found.

        Pattern requirements (sequential):
        1. ECONOMIC_SHOCK: Pool drops >= 20% between ticks
        2. AUSTERITY_RESPONSE: Wage decreases in subsequent tick
        3. RADICALIZATION: P(Revolution) increases in subsequent tick

        A detected frame is logged at WARNING level (``[NARRATIVE_JSON]``,
        backward compat) AND appended to ``latest_frames``. Each 3-tick
        window emits at most once across its lifetime in the rolling buffer
        (dedup keyed by crash tick).
        """
        # Need at least 3 snapshots to detect the pattern
        if len(self._history) < 3:
            return

        history_list = list(self._history)

        # Check all possible 3-tick windows in the buffer
        max_window_size = len(history_list)
        for i in range(max_window_size - 2):
            snapshot_n = history_list[i]
            snapshot_n1 = history_list[i + 1]
            snapshot_n2 = history_list[i + 2]

            if snapshot_n.tick in self._emitted_crash_ticks:
                continue  # this window already emitted on an earlier tick

            # Check for pattern
            if self._is_shock_doctrine_pattern(snapshot_n, snapshot_n1, snapshot_n2):
                frame = self._build_frame(snapshot_n, snapshot_n1, snapshot_n2)
                self._logger.warning("[NARRATIVE_JSON] %s", json.dumps(frame))
                self._tick_frames.append(frame)
                self._emitted_crash_ticks.add(snapshot_n.tick)
                return  # Only emit once per detection

    def _prune_emitted_windows(self) -> None:
        """Drop dedup keys older than the buffer window (bounded memory).

        Once a crash tick has scrolled out of the rolling buffer it can
        never re-match, so its key is dead weight — over a 5200-tick
        campaign the set would otherwise grow without bound.
        """
        if not self._history:
            return
        oldest = self._history[0].tick
        self._emitted_crash_ticks = {t for t in self._emitted_crash_ticks if t >= oldest}

    def _is_shock_doctrine_pattern(
        self,
        crash_snap: TickSnapshot,
        austerity_snap: TickSnapshot,
        radical_snap: TickSnapshot,
    ) -> bool:
        """Check if three snapshots form the Shock Doctrine pattern.

        Args:
            crash_snap: Snapshot at the crash tick (baseline).
            austerity_snap: Snapshot at the austerity tick (after crash).
            radical_snap: Snapshot at the radicalization tick.

        Returns:
            True if pattern matches, False otherwise.
        """
        # Guard against division by zero
        if crash_snap.pool <= 0.0:
            return False

        # Check 1: Pool crash >= 20%
        pool_change = (austerity_snap.pool - crash_snap.pool) / crash_snap.pool
        if pool_change > self.CRASH_THRESHOLD:  # Not a significant crash
            return False

        # Check 2: Wage decrease (austerity)
        if radical_snap.wage >= austerity_snap.wage:  # Wages didn't decrease
            return False

        # Check 3: P(Revolution) increase (radicalization)
        return radical_snap.p_rev > austerity_snap.p_rev

    def _build_frame(
        self,
        crash: TickSnapshot,
        austerity: TickSnapshot,
        radical: TickSnapshot,
    ) -> dict[str, object]:
        """Build a NarrativeFrame JSON structure for the Shock Doctrine pattern.

        Args:
            crash: Snapshot at the economic shock tick.
            austerity: Snapshot at the austerity response tick.
            radical: Snapshot at the radicalization tick.

        Returns:
            Dictionary representing the causal graph JSON structure.
        """
        return {
            "pattern": "SHOCK_DOCTRINE",
            "causal_graph": {
                "nodes": [
                    {
                        "id": f"shock_t{crash.tick}",
                        "type": "ECONOMIC_SHOCK",
                        "tick": crash.tick,
                        "data": {
                            "pool_before": crash.pool,
                            "pool_after": austerity.pool,
                            "drop_percent": round(
                                (austerity.pool - crash.pool) / crash.pool * 100, 1
                            ),
                        },
                    },
                    {
                        "id": f"austerity_t{austerity.tick}",
                        "type": "AUSTERITY_RESPONSE",
                        "tick": austerity.tick,
                        "data": {
                            "wage_before": austerity.wage,
                            "wage_after": radical.wage,
                        },
                    },
                    {
                        "id": f"radical_t{radical.tick}",
                        "type": "RADICALIZATION",
                        "tick": radical.tick,
                        "data": {
                            "p_rev_before": austerity.p_rev,
                            "p_rev_after": radical.p_rev,
                        },
                    },
                ],
                "edges": [
                    {
                        "source": f"shock_t{crash.tick}",
                        "target": f"austerity_t{austerity.tick}",
                        "relation": "TRIGGERS_REACTION",
                    },
                    {
                        "source": f"austerity_t{austerity.tick}",
                        "target": f"radical_t{radical.tick}",
                        "relation": "CAUSES_RADICALIZATION",
                    },
                ],
            },
        }
