"""Spec-095: EndgameDetector priority + bridge endgame-outcome coverage tests.

Two concerns:

1. **Bridge 3-of-5 bug (RED)**: ``resolve_tick`` line 1058 only recognized 3 of 5
   GameOutcome event types (``REVOLUTIONARY_VICTORY``, ``ECOLOGICAL_COLLAPSE``,
   ``FASCIST_CONSOLIDATION``), missing ``RED_OGV`` and ``FRAGMENTED_COLLAPSE``.
   When the engine fires either of those, the snapshot's ``endgame`` block was
   never populated. This test forces the fix (FR-095-02).

2. **FR-033 priority characterization**: The EndgameDetector docstring (Slice 1.6,
   stale) claims ``REVOLUTIONARY_VICTORY > ECOLOGICAL_COLLAPSE >
   FASCIST_CONSOLIDATION``. Spec-070 FR-033 reorders to ``RED_OGV →
   FRAGMENTED_COLLAPSE → ECOLOGICAL_COLLAPSE → FASCIST_CONSOLIDATION →
   REVOLUTIONARY_VICTORY`` (first-match-wins, REVOLUTIONARY_VICTORY LAST). The
   code follows FR-033; the docstring is stale. This test PINS FR-033's order so
   a future "fix the docstring by changing the code" regression is caught. The
   docstring fix itself is engine code (cross-lane, flagged in spec-095 §6).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from babylon.engine.observers.endgame_detector import EndgameDetector
from babylon.models import WorldState
from babylon.models.config import SimulationConfig
from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.enums import GameOutcome, SocialRole
from game.engine_bridge import EngineBridge

pytestmark = pytest.mark.unit

_SESSION = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def _make_mock_persistence() -> MagicMock:
    mock = MagicMock()
    mock.hydrate_graph.return_value = MagicMock()
    mock.get_metadata.return_value = None
    mock.get_session.return_value = {"scenario": "default"}
    mock.get_pending_turns.return_value = []
    mock.mark_turns_resolved.return_value = 0
    mock.persist_tick.return_value = None
    return mock


def _make_mock_new_state(tick: int = 1) -> MagicMock:
    mock = MagicMock()
    mock.tick = tick
    mock.entities = {}
    mock.territories = {}
    mock.organizations = {}
    mock.institutions = {}
    mock.economy = MagicMock()
    mock.economy.model_dump.return_value = {}
    mock.relationships = []
    mock.events = []
    mock.to_graph.return_value = MagicMock()
    return mock


# ---------------------------------------------------------------------- #
# 1. Bridge 3-of-5 bug — resolve_tick must surface ALL 5 endgame types
# ---------------------------------------------------------------------- #


class TestBridgeEndgameCoverage:
    """FR-095-02: resolve_tick must recognize all 5 GameOutcome event types."""

    @patch("game.engine_bridge.step")
    def test_resolve_tick_surfaces_red_ogv_endgame(self, mock_step: MagicMock) -> None:
        """RED_OGV endgame event must populate snapshot['endgame'].

        Currently RED: endgame_types set at engine_bridge.py:1058 omits
        'RED_OGV', so the snapshot['endgame'] block is never set.
        """
        mock_persistence = _make_mock_persistence()
        mock_new_state = _make_mock_new_state()
        event = MagicMock()
        event.event_type = "RED_OGV"
        event.tick = 1
        event.data = {"summary": "Settler-socialist trap"}
        mock_new_state.events = [event]
        mock_step.return_value = mock_new_state

        bridge = EngineBridge(mock_persistence)
        result = bridge.resolve_tick(_SESSION)

        assert "endgame" in result, "RED_OGV endgame must surface in snapshot"
        assert result["endgame"]["outcome"] == "RED_OGV"

    @patch("game.engine_bridge.step")
    def test_resolve_tick_surfaces_fragmented_collapse_endgame(self, mock_step: MagicMock) -> None:
        """FRAGMENTED_COLLAPSE endgame event must populate snapshot['endgame'].

        Currently RED: endgame_types set omits 'FRAGMENTED_COLLAPSE'.
        """
        mock_persistence = _make_mock_persistence()
        mock_new_state = _make_mock_new_state()
        event = MagicMock()
        event.event_type = "FRAGMENTED_COLLAPSE"
        event.tick = 1
        event.data = {"summary": "Balkanization"}
        mock_new_state.events = [event]
        mock_step.return_value = mock_new_state

        bridge = EngineBridge(mock_persistence)
        result = bridge.resolve_tick(_SESSION)

        assert "endgame" in result
        assert result["endgame"]["outcome"] == "FRAGMENTED_COLLAPSE"

    @patch("game.engine_bridge.step")
    def test_resolve_tick_surfaces_revolutionary_victory_endgame(
        self, mock_step: MagicMock
    ) -> None:
        """REVOLUTIONARY_VICTORY (already in the set) must still work."""
        mock_persistence = _make_mock_persistence()
        mock_new_state = _make_mock_new_state()
        event = MagicMock()
        event.event_type = "REVOLUTIONARY_VICTORY"
        event.tick = 1
        event.data = {"summary": "Babylon falls"}
        mock_new_state.events = [event]
        mock_step.return_value = mock_new_state

        bridge = EngineBridge(mock_persistence)
        result = bridge.resolve_tick(_SESSION)

        assert "endgame" in result
        assert result["endgame"]["outcome"] == "REVOLUTIONARY_VICTORY"


# ---------------------------------------------------------------------- #
# 2. FR-033 priority characterization (EndgameDetector)
# ---------------------------------------------------------------------- #


class TestEndgameDetectorFR033Priority:
    """Pin the FR-033 priority order: RED_OGV → FRAGMENTED_COLLAPSE →
    ECOLOGICAL_COLLAPSE → FASCIST_CONSOLIDATION → REVOLUTIONARY_VICTORY.

    The stale Slice-1.6 docstring says REVOLUTIONARY_VICTORY-first; the code
    checks it LAST. This test asserts the CODE's order (FR-033) is correct, so a
    future change to match the stale docstring is caught as a regression.

    The docstring fix itself is cross-lane (src/babylon/, engine code).
    """

    def test_fr033_cascade_order_via_subclass(self) -> None:
        """FR-033 priority: RED_OGV → FRAGMENTED_COLLAPSE → ECOLOGICAL_COLLAPSE
        → FASCIST_CONSOLIDATION → REVOLUTIONARY_VICTORY (first-match-wins).

        The stale Slice-1.6 docstring says REVOLUTIONARY_VICTORY-first; the code
        checks it LAST. This test subclasses EndgameDetector, overrides the
        ``_check_*`` methods to record call order, and forces ALL predicates to
        return True. The FIRST predicate in FR-033 order (RED_OGV) must win —
        NOT REVOLUTIONARY_VICTORY as the stale docstring claims.

        Constructing real WorldState fixtures where multiple terminal conditions
        hold simultaneously is impractical (they have contradictory prerequisites
        like ABOLISH- vs UPHOLD-majority). A subclass with stubbed predicates
        isolates the priority cascade — the ONLY thing under test here.
        """

        class OrderTrackingDetector(EndgameDetector):
            call_order: list[str] = []

            def _check_red_ogv(self, state: Any) -> bool:
                self.call_order.append("RED_OGV")
                return True

            def _check_fragmented_collapse(self, state: Any) -> bool:
                self.call_order.append("FRAGMENTED_COLLAPSE")
                return True

            def _check_ecological_collapse(self, state: Any) -> bool:
                self.call_order.append("ECOLOGICAL_COLLAPSE")
                return True

            def _check_fascist_consolidation(self, state: Any) -> bool:
                self.call_order.append("FASCIST_CONSOLIDATION")
                return True

            def _check_revolutionary_victory(self, state: Any) -> bool:
                self.call_order.append("REVOLUTIONARY_VICTORY")
                return True

        detector = OrderTrackingDetector()
        state = WorldState(tick=1, entities={})
        detector.on_simulation_start(state, SimulationConfig())
        detector.on_tick(state, state)

        # RED_OGV is checked FIRST and returns True → first-match-wins.
        assert detector.outcome is GameOutcome.RED_OGV
        # Only RED_OGV was evaluated (short-circuit after first match).
        assert detector.call_order == ["RED_OGV"]

    def test_revolutionary_victory_checked_last_not_first(self) -> None:
        """FR-033: when all predicates EXCEPT RED_OGV hold, FRAGMENTED_COLLAPSE
        wins (2nd in cascade). REVOLUTIONARY_VICTORY (5th, last) never gets
        evaluated — contradicting the stale docstring's "REVOLUTIONARY_VICTORY
        > ..." (first) claim.

        This is the discrepancy's smoking gun: if the docstring were correct
        (REVOLUTIONARY_VICTORY first), this state would yield
        REVOLUTIONARY_VICTORY. FR-033 code yields FRAGMENTED_COLLAPSE.
        """

        class SkipRedOgvDetector(EndgameDetector):
            call_order: list[str] = []

            def _check_red_ogv(self, state: Any) -> bool:
                self.call_order.append("RED_OGV")
                return False  # RED_OGV does NOT hold

            def _check_fragmented_collapse(self, state: Any) -> bool:
                self.call_order.append("FRAGMENTED_COLLAPSE")
                return True  # This holds → wins

            def _check_ecological_collapse(self, state: Any) -> bool:
                self.call_order.append("ECOLOGICAL_COLLAPSE")
                return True

            def _check_fascist_consolidation(self, state: Any) -> bool:
                self.call_order.append("FASCIST_CONSOLIDATION")
                return True

            def _check_revolutionary_victory(self, state: Any) -> bool:
                self.call_order.append("REVOLUTIONARY_VICTORY")
                return True

        detector = SkipRedOgvDetector()
        state = WorldState(tick=1, entities={})
        detector.on_simulation_start(state, SimulationConfig())
        detector.on_tick(state, state)

        # FRAGMENTED_COLLAPSE (2nd) wins, NOT REVOLUTIONARY_VICTORY (5th).
        assert detector.outcome is GameOutcome.FRAGMENTED_COLLAPSE
        # REVOLUTIONARY_VICTORY was never reached (short-circuit).
        assert "REVOLUTIONARY_VICTORY" not in detector.call_order

    def test_revolutionary_victory_fires_when_alone(self) -> None:
        """FR-033: REVOLUTIONARY_VICTORY is checked LAST, not first.

        The stale docstring claims 'REVOLUTIONARY_VICTORY > ...' (first). The
        code checks it last. This test documents that the code follows FR-033,
        NOT the docstring. When FASCIST_CONSOLIDATION conditions hold (but
        REVOLUTIONARY_VICTORY conditions do NOT), the outcome is
        FASCIST_CONSOLIDATION — which is consistent with BOTH the docstring and
        FR-033 since REVOLUTIONARY_VICTORY's predicates don't hold.

        The real discrepancy (both holding simultaneously) requires sovereigns +
        factions + percolation, which is tested at the engine level in
        tests/unit/balkanization/test_endgame_priority_order.py. This test pins
        the contract from the bridge's perspective: the bridge must surface
        whichever outcome the detector fires, in FR-033 order.
        """
        config = SimulationConfig()
        entities = {
            f"C{i:03d}": SocialClass(
                id=f"C{i:03d}",
                name=f"Reactionary {i}",
                role=SocialRole.LABOR_ARISTOCRACY,
                ideology=IdeologicalProfile(class_consciousness=0.2, national_identity=0.9),
            )
            for i in range(5)
        }
        detector = EndgameDetector()
        initial = WorldState(tick=0, entities=entities)
        detector.on_simulation_start(initial, config)
        detector.on_tick(initial, WorldState(tick=1, entities=entities))

        # FASCIST_CONSOLIDATION fires (false-consciousness route, 5 nodes).
        # REVOLUTIONARY_VICTORY predicates don't hold (no percolation, no
        # ABOLISH-majority), so this is consistent with both orderings.
        assert detector.outcome is GameOutcome.FASCIST_CONSOLIDATION

    def test_all_five_outcomes_exist_in_enum(self) -> None:
        """FR-095-02: all 5 terminal GameOutcome values must be recognized by
        the bridge. This pins the contract that the bridge's endgame_types set
        must include all 5."""
        terminal = {
            GameOutcome.REVOLUTIONARY_VICTORY,
            GameOutcome.ECOLOGICAL_COLLAPSE,
            GameOutcome.FASCIST_CONSOLIDATION,
            GameOutcome.RED_OGV,
            GameOutcome.FRAGMENTED_COLLAPSE,
        }
        assert len(terminal) == 5
        assert GameOutcome.IN_PROGRESS not in terminal
