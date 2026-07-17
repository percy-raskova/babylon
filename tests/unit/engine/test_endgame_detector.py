"""Tests for EndgameDetector observer and GameOutcome enum (Slice 1.6 / spec-116).

Covers the EndgameDetector as a SimulationObserver and pattern recognizer
(spec-116 FR-116-1):
- GameOutcome enum values
- SimulationObserver protocol compliance
- Initial state (no recognized pattern)
- Lifecycle hooks (on_simulation_start reset, on_simulation_end)
- Pattern recognition: recognized_pattern / pattern_since_tick / axis_progress()

Outcome-adjudication doctrine (which conditions trigger which GameOutcome) is
out of scope here per owner ruling 2026-07-16 — the game runs a fixed century
horizon and endgame behavior is emergent; outcomes are used only as fixture
vehicles to trigger detector machinery (ADR074).

Spec-116 FR-116-1 (owner ruling 2026-07-17): EndgameDetector is a pattern
RECOGNIZER, not an adjudicator. ``is_game_over``/``outcome`` are gone;
``on_tick`` re-evaluates every axis every tick and patterns can dissolve.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from babylon.engine.observer import SimulationObserver
from babylon.engine.observers.endgame_detector import EndgameDetector
from babylon.models.enums import GameOutcome

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


def _fascist_entities(count: int = 5, fascist_count: int | None = None) -> dict[str, object]:
    """Build a dict of SocialClass entities, ``fascist_count`` of which have
    national_identity > class_consciousness (defaults to all of them)."""
    from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
    from babylon.models.enums import SocialRole

    if fascist_count is None:
        fascist_count = count
    entities: dict[str, object] = {}
    for i in range(count):
        if i < fascist_count:
            ideology = IdeologicalProfile(national_identity=0.9, class_consciousness=0.1)
        else:
            ideology = IdeologicalProfile(national_identity=0.1, class_consciousness=0.9)
        entities[f"C{i:03d}"] = SocialClass(
            id=f"C{i:03d}",
            name=f"Node {i}",
            role=SocialRole.LABOR_ARISTOCRACY,
            ideology=ideology,
        )
    return entities


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

        Represents fascist victory when the fraction of ideology-bearing
        nodes with national_identity > class_consciousness reaches
        fascist_majority_fraction.
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
    """Test EndgameDetector initial state (spec-116: recognizer, not adjudicator)."""

    def test_endgame_detector_starts_with_no_recognized_pattern(self) -> None:
        """EndgameDetector starts with recognized_pattern None.

        Before any state is analyzed, no pattern is recognized.
        """
        detector = EndgameDetector()
        assert detector.recognized_pattern is None

    def test_endgame_detector_starts_with_no_pattern_since_tick(self) -> None:
        """EndgameDetector.pattern_since_tick is None initially."""
        detector = EndgameDetector()
        assert detector.pattern_since_tick is None


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

        entities = _fascist_entities(count=5)

        detector = EndgameDetector()

        # First run - recognizes fascist consolidation.
        detector.on_simulation_start(WorldState(tick=0, entities=entities), config)
        detector.on_tick(
            WorldState(tick=0, entities=entities),
            WorldState(tick=1, entities=entities),
        )
        assert detector.recognized_pattern is GameOutcome.FASCIST_CONSOLIDATION

        # Reset with new simulation start.
        detector.on_simulation_start(WorldState(tick=0), config)

        # Should be back to no recognized pattern.
        assert detector.recognized_pattern is None
        assert detector.pattern_since_tick is None

    def test_on_simulation_end_no_crash(
        self,
        config: SimulationConfig,  # noqa: ARG002
    ) -> None:
        """on_simulation_end does not crash."""
        detector = EndgameDetector()
        final_state = create_minimal_state(tick=100)

        # Should not raise
        detector.on_simulation_end(final_state)


# =============================================================================
# TEST PATTERN RECOGNITION (spec-116 FR-116-1)
# =============================================================================


@pytest.mark.unit
class TestPatternRecognition:
    """Normative spec-116 FR-116-1 recognizer tests."""

    def test_recognition_sets_pattern_and_since_tick(self) -> None:
        """Fixture drives the fascist axis to matched at tick N; recognized_pattern
        and pattern_since_tick both reflect the transition tick."""
        from babylon.models import WorldState

        entities = _fascist_entities(count=5)
        detector = EndgameDetector()

        detector.on_tick(
            WorldState(tick=0, entities=entities),
            WorldState(tick=1, entities=entities),
        )

        assert detector.recognized_pattern is GameOutcome.FASCIST_CONSOLIDATION
        assert detector.pattern_since_tick == 1

    def test_pattern_dissolves_when_conditions_recede(self) -> None:
        """Same fixture, then consciousness recovers below the fraction —
        recognized_pattern and pattern_since_tick both revert to None."""
        from babylon.models import WorldState

        fascist_entities = _fascist_entities(count=5)
        detector = EndgameDetector()

        detector.on_tick(
            WorldState(tick=0, entities=fascist_entities),
            WorldState(tick=1, entities=fascist_entities),
        )
        assert detector.recognized_pattern is GameOutcome.FASCIST_CONSOLIDATION

        # Consciousness recovers: 0 of 5 nodes fascist now.
        recovered_entities = _fascist_entities(count=5, fascist_count=0)
        detector.on_tick(
            WorldState(tick=1, entities=fascist_entities),
            WorldState(tick=2, entities=recovered_entities),
        )

        assert detector.recognized_pattern is None
        assert detector.pattern_since_tick is None

    def test_fascist_axis_uses_fraction_not_count(self) -> None:
        """6 ideology-bearing nodes, 4 fascist (0.667) => NOT matched; flip a
        5th (0.833) => still NOT matched at the spec-116-calibrated fraction
        0.9 (Task 6 pacing calibration: a single archetypal entity's ideology
        flip must not cause an early FASCIST_CONSOLIDATION lock — see
        ``EndgameDefines.fascist_majority_fraction``'s docstring); flip the
        6th (1.0) => matched."""
        from babylon.models import WorldState

        detector = EndgameDetector()

        four_of_six = _fascist_entities(count=6, fascist_count=4)
        detector.on_tick(
            WorldState(tick=0, entities=four_of_six),
            WorldState(tick=1, entities=four_of_six),
        )
        assert detector.recognized_pattern is not GameOutcome.FASCIST_CONSOLIDATION
        assert detector.axis_progress()["fascist_consolidation"] < 1.0

        five_of_six = _fascist_entities(count=6, fascist_count=5)
        detector.on_tick(
            WorldState(tick=1, entities=four_of_six),
            WorldState(tick=2, entities=five_of_six),
        )
        assert detector.recognized_pattern is not GameOutcome.FASCIST_CONSOLIDATION
        assert detector.axis_progress()["fascist_consolidation"] < 1.0

        six_of_six = _fascist_entities(count=6, fascist_count=6)
        detector.on_tick(
            WorldState(tick=2, entities=five_of_six),
            WorldState(tick=3, entities=six_of_six),
        )
        assert detector.recognized_pattern is GameOutcome.FASCIST_CONSOLIDATION
        assert detector.axis_progress()["fascist_consolidation"] == pytest.approx(1.0)

    def test_axis_progress_keys_and_bounds(self) -> None:
        """axis_progress() returns exactly the 5 canonical keys, each in [0, 1]."""
        detector = EndgameDetector()
        progress = detector.axis_progress()

        assert set(progress) == {
            "revolutionary_victory",
            "ecological_collapse",
            "fascist_consolidation",
            "red_ogv",
            "fragmented_collapse",
        }
        assert all(0.0 <= v <= 1.0 for v in progress.values())

    def test_matched_iff_progress_saturates(self) -> None:
        """Whenever recognized_pattern == P, axis_progress()[P.value] == 1.0."""
        from babylon.models import WorldState

        entities = _fascist_entities(count=5)
        detector = EndgameDetector()

        detector.on_tick(
            WorldState(tick=0, entities=entities),
            WorldState(tick=1, entities=entities),
        )

        pattern = detector.recognized_pattern
        assert pattern is not None
        assert detector.axis_progress()[pattern.value] == pytest.approx(1.0)

    def test_on_tick_serializes_graph_once(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """on_tick must build exactly ONE graph and thread it through all
        five axis evaluators (not re-serialize per axis)."""
        from babylon.models import WorldState
        from babylon.models.world_state import WorldState as WorldStateClass

        call_count = {"n": 0}
        original_to_graph = WorldStateClass.to_graph

        def counting_to_graph(self: WorldStateClass) -> object:
            call_count["n"] += 1
            return original_to_graph(self)

        monkeypatch.setattr(WorldStateClass, "to_graph", counting_to_graph)

        entities = _fascist_entities(count=5)
        detector = EndgameDetector()
        detector.on_tick(
            WorldState(tick=0, entities=entities),
            WorldState(tick=1, entities=entities),
        )

        assert call_count["n"] == 1
