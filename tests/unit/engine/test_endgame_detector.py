"""Tests for EndgameDetector observer and GameOutcome enum (Slice 1.6).

Covers the EndgameDetector as a SimulationObserver:
- GameOutcome enum values
- SimulationObserver protocol compliance
- Initial state (IN_PROGRESS, is_game_over False)
- ENDGAME_REACHED event emission mechanics (emitted once, via get_pending_events())
- Lifecycle hooks (on_simulation_start reset, on_simulation_end)

Outcome-adjudication doctrine (which conditions trigger which GameOutcome) is
out of scope here per owner ruling 2026-07-16 — the game runs a fixed century
horizon and endgame behavior is emergent; outcomes are used only as fixture
vehicles to trigger detector machinery.

NOTE: red_phase markers retired 2026-07-08 — the suite runs green.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

# These imports will fail until implementation exists - that's the RED phase
from babylon.engine.observer import SimulationObserver
from babylon.engine.observers.endgame_detector import EndgameDetector
from babylon.models.enums import EventType, GameOutcome

# TDD GREEN phase - tests now pass with implementation

if TYPE_CHECKING:
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def config() -> SimulationConfig:
    """Create default simulation config."""
    from babylon.models import SimulationConfig

    return SimulationConfig()


def create_minimal_state(tick: int = 0) -> WorldState:
    """Create minimal WorldState for testing.

    Args:
        tick: The simulation tick number.

    Returns:
        A minimal WorldState suitable for testing.
    """
    from babylon.models import WorldState

    return WorldState(tick=tick)


# =============================================================================
# TEST GAME OUTCOME ENUM
# =============================================================================


@pytest.mark.unit
class TestGameOutcomeEnum:
    """Test GameOutcome enum definition and values."""

    def test_game_outcome_enum_has_in_progress(self) -> None:
        """GameOutcome must have IN_PROGRESS value.

        The game starts in IN_PROGRESS state and remains there until
        one of the endgame conditions is met.
        """
        assert hasattr(GameOutcome, "IN_PROGRESS")
        assert GameOutcome.IN_PROGRESS.value == "in_progress"

    def test_game_outcome_enum_has_revolutionary_victory(self) -> None:
        """GameOutcome must have REVOLUTIONARY_VICTORY value.

        Represents successful proletarian revolution when:
        - percolation >= 0.7 (mass organization)
        - class_consciousness > 0.8 (ideological clarity)
        """
        assert hasattr(GameOutcome, "REVOLUTIONARY_VICTORY")
        assert GameOutcome.REVOLUTIONARY_VICTORY.value == "revolutionary_victory"

    def test_game_outcome_enum_has_ecological_collapse(self) -> None:
        """GameOutcome must have ECOLOGICAL_COLLAPSE value.

        Represents irreversible ecological collapse when:
        - overshoot_ratio > 2.0 for 5 consecutive ticks
        """
        assert hasattr(GameOutcome, "ECOLOGICAL_COLLAPSE")
        assert GameOutcome.ECOLOGICAL_COLLAPSE.value == "ecological_collapse"

    def test_game_outcome_enum_has_fascist_consolidation(self) -> None:
        """GameOutcome must have FASCIST_CONSOLIDATION value.

        Represents fascist victory when:
        - national_identity > class_consciousness for 3+ nodes
        """
        assert hasattr(GameOutcome, "FASCIST_CONSOLIDATION")
        assert GameOutcome.FASCIST_CONSOLIDATION.value == "fascist_consolidation"


# =============================================================================
# TEST ENDGAME DETECTOR PROTOCOL COMPLIANCE
# =============================================================================


@pytest.mark.unit
class TestEndgameDetectorProtocol:
    """Test EndgameDetector protocol compliance."""

    def test_endgame_detector_implements_simulation_observer(self) -> None:
        """EndgameDetector must implement SimulationObserver protocol.

        As an observer, it receives state change notifications and
        monitors for endgame conditions without modifying simulation state.
        """
        detector = EndgameDetector()
        assert isinstance(detector, SimulationObserver)

    def test_endgame_detector_has_name_property(self) -> None:
        """EndgameDetector.name returns 'EndgameDetector'."""
        detector = EndgameDetector()
        assert detector.name == "EndgameDetector"


# =============================================================================
# TEST ENDGAME DETECTOR INITIAL STATE
# =============================================================================


@pytest.mark.unit
class TestEndgameDetectorInitialState:
    """Test EndgameDetector initial state."""

    def test_endgame_detector_starts_in_progress(self) -> None:
        """EndgameDetector starts with outcome = IN_PROGRESS.

        Before any state is analyzed, the game is assumed to be ongoing.
        """
        detector = EndgameDetector()
        assert detector.outcome == GameOutcome.IN_PROGRESS

    def test_endgame_detector_is_game_over_false_initially(self) -> None:
        """EndgameDetector.is_game_over is False initially.

        Convenience property to check if game has ended.
        """
        detector = EndgameDetector()
        assert detector.is_game_over is False


# =============================================================================
# TEST EVENT EMISSION
# =============================================================================


@pytest.mark.unit
class TestEndgameEventEmission:
    """Test that EndgameDetector emits ENDGAME_REACHED event."""

    def test_endgame_detector_emits_endgame_reached_event(
        self,
        config: SimulationConfig,
    ) -> None:
        """EndgameDetector emits ENDGAME_REACHED event when game ends.

        The event should be retrievable via get_pending_events() similar
        to TopologyMonitor's PHASE_TRANSITION events.
        """
        from babylon.models import WorldState
        from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
        from babylon.models.enums import SocialRole

        # Trigger fascist consolidation (quickest to set up)
        entities = {
            f"C{i:03d}": SocialClass(
                id=f"C{i:03d}",
                name=f"Fascist {i}",
                role=SocialRole.LABOR_ARISTOCRACY,
                ideology=IdeologicalProfile(
                    national_identity=0.9,
                    class_consciousness=0.1,
                ),
            )
            for i in range(5)
        }

        prev_state = WorldState(tick=0, entities=entities)
        new_state = WorldState(tick=1, entities=entities)

        detector = EndgameDetector()
        detector.on_simulation_start(prev_state, config)
        detector.on_tick(prev_state, new_state)

        # Get pending events
        events = detector.get_pending_events()

        # Should have exactly one ENDGAME_REACHED event
        assert len(events) == 1
        event = events[0]
        assert event.event_type == EventType.ENDGAME_REACHED
        assert event.outcome == GameOutcome.FASCIST_CONSOLIDATION

    def test_no_event_when_game_continues(
        self,
        config: SimulationConfig,
    ) -> None:
        """No ENDGAME_REACHED event when game is still IN_PROGRESS."""
        from babylon.models import WorldState

        prev_state = WorldState(tick=0)
        new_state = WorldState(tick=1)

        detector = EndgameDetector()
        detector.on_simulation_start(prev_state, config)
        detector.on_tick(prev_state, new_state)

        events = detector.get_pending_events()
        assert len(events) == 0

    def test_event_only_emitted_once(
        self,
        config: SimulationConfig,
    ) -> None:
        """ENDGAME_REACHED event is emitted only once when game ends.

        Subsequent ticks should not emit additional events.
        """
        from babylon.models import WorldState
        from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
        from babylon.models.enums import SocialRole

        entities = {
            f"C{i:03d}": SocialClass(
                id=f"C{i:03d}",
                name=f"Fascist {i}",
                role=SocialRole.LABOR_ARISTOCRACY,
                ideology=IdeologicalProfile(
                    national_identity=0.9,
                    class_consciousness=0.1,
                ),
            )
            for i in range(5)
        }

        detector = EndgameDetector()
        initial_state = WorldState(tick=0, entities=entities)
        detector.on_simulation_start(initial_state, config)

        # First tick - should emit event
        detector.on_tick(
            WorldState(tick=0, entities=entities),
            WorldState(tick=1, entities=entities),
        )
        events1 = detector.get_pending_events()
        assert len(events1) == 1

        # Second tick - should NOT emit again
        detector.on_tick(
            WorldState(tick=1, entities=entities),
            WorldState(tick=2, entities=entities),
        )
        events2 = detector.get_pending_events()
        assert len(events2) == 0


# =============================================================================
# TEST LIFECYCLE HOOKS
# =============================================================================


@pytest.mark.unit
class TestEndgameDetectorLifecycle:
    """Test EndgameDetector lifecycle hooks."""

    def test_on_simulation_start_resets_state(
        self,
        config: SimulationConfig,
    ) -> None:
        """on_simulation_start resets detector to initial state.

        Allows reuse of detector across multiple simulation runs.
        """
        from babylon.models import WorldState
        from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
        from babylon.models.enums import SocialRole

        entities = {
            f"C{i:03d}": SocialClass(
                id=f"C{i:03d}",
                name=f"Fascist {i}",
                role=SocialRole.LABOR_ARISTOCRACY,
                ideology=IdeologicalProfile(
                    national_identity=0.9,
                    class_consciousness=0.1,
                ),
            )
            for i in range(5)
        }

        detector = EndgameDetector()

        # First run - ends in fascism
        detector.on_simulation_start(WorldState(tick=0, entities=entities), config)
        detector.on_tick(
            WorldState(tick=0, entities=entities),
            WorldState(tick=1, entities=entities),
        )
        assert detector.outcome == GameOutcome.FASCIST_CONSOLIDATION

        # Reset with new simulation start
        detector.on_simulation_start(WorldState(tick=0), config)

        # Should be back to IN_PROGRESS
        assert detector.outcome == GameOutcome.IN_PROGRESS
        assert detector.is_game_over is False

    def test_on_simulation_end_no_crash(
        self,
        config: SimulationConfig,
    ) -> None:
        """on_simulation_end does not crash."""
        detector = EndgameDetector()
        final_state = create_minimal_state(tick=100)

        # Should not raise
        detector.on_simulation_end(final_state)
