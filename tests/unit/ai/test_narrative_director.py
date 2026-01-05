"""Tests for NarrativeDirector AI observer implementation.

TDD Red Phase: These tests define the contract for the NarrativeDirector
that observes simulation state changes and generates narrative.

The NarrativeDirector sits in the Ideological Superstructure - it observes
the Material Base (simulation mechanics) but cannot modify it.

Sprint 4.1: Updated to use typed SimulationEvent objects from state.events
instead of string-based event_log.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass

from babylon.models import (
    EdgeType,
    Relationship,
    SimulationConfig,
    SocialClass,
    SocialRole,
    WorldState,
)
from babylon.models.events import ExtractionEvent, TransmissionEvent

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def worker() -> SocialClass:
    """Create a periphery worker social class."""
    return SocialClass(
        id="C001",
        name="Worker",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=0.5,
        ideology=0.0,
        organization=0.1,
        repression_faced=0.5,
        subsistence_threshold=0.3,
    )


@pytest.fixture
def owner() -> SocialClass:
    """Create a core owner social class."""
    return SocialClass(
        id="C002",
        name="Owner",
        role=SocialRole.CORE_BOURGEOISIE,
        wealth=10.0,
        ideology=0.5,
        organization=0.7,
        repression_faced=0.1,
        subsistence_threshold=0.1,
    )


@pytest.fixture
def exploitation_edge() -> Relationship:
    """Create an exploitation relationship from worker to owner."""
    return Relationship(
        source_id="C001",
        target_id="C002",
        edge_type=EdgeType.EXPLOITATION,
        value_flow=0.0,
        tension=0.0,
    )


@pytest.fixture
def initial_state(
    worker: SocialClass,
    owner: SocialClass,
    exploitation_edge: Relationship,
) -> WorldState:
    """Create initial WorldState with two nodes and one edge."""
    return WorldState(
        tick=0,
        entities={"C001": worker, "C002": owner},
        relationships=[exploitation_edge],
    )


@pytest.fixture
def config() -> SimulationConfig:
    """Create default simulation config."""
    return SimulationConfig()


# =============================================================================
# TEST PROTOCOL COMPLIANCE
# =============================================================================


@pytest.mark.unit
class TestNarrativeDirectorProtocol:
    """Tests for NarrativeDirector SimulationObserver compliance."""

    def test_narrative_director_satisfies_observer_protocol(self) -> None:
        """NarrativeDirector satisfies SimulationObserver protocol."""
        from babylon.ai.director import NarrativeDirector
        from babylon.engine.observer import SimulationObserver

        director = NarrativeDirector()
        assert isinstance(director, SimulationObserver)

    def test_narrative_director_has_name_property(self) -> None:
        """NarrativeDirector has name property for identification."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector()
        assert director.name == "NarrativeDirector"


# =============================================================================
# TEST CONFIGURATION
# =============================================================================


@pytest.mark.unit
class TestNarrativeDirectorConfig:
    """Tests for NarrativeDirector configuration."""

    def test_narrative_director_init_default_no_llm(self) -> None:
        """NarrativeDirector defaults to no LLM usage."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector()
        assert director.use_llm is False

    def test_narrative_director_init_with_use_llm_flag(self) -> None:
        """NarrativeDirector accepts use_llm flag."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(use_llm=True)
        assert director.use_llm is True


# =============================================================================
# TEST EVENT PROCESSING
# =============================================================================


@pytest.mark.unit
class TestNarrativeDirectorEvents:
    """Tests for NarrativeDirector event processing."""

    def test_on_tick_detects_new_events(
        self,
        initial_state: WorldState,
    ) -> None:
        """on_tick detects new events added during tick.

        Sprint 4.1: Updated to use typed events.
        """
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector()

        # Initial state with no events
        previous_state = initial_state

        # Create typed events (Sprint 4.1)
        event_a = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )
        event_b = TransmissionEvent(
            tick=1,
            target_id="C001",
            source_id="C002",
            delta=0.05,
            solidarity_strength=0.5,
        )

        # New state with events added
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [event_a, event_b],
            }
        )

        # Should not raise
        director.on_tick(previous_state, new_state)

    def test_on_tick_logs_new_events(
        self,
        initial_state: WorldState,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """on_tick logs new events.

        Sprint 4.1: Updated to use typed ExtractionEvent and check
        for formatted event text in logs.
        """
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector()

        # Create typed event (Sprint 4.1)
        extraction_event = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [extraction_event],
            }
        )

        with caplog.at_level(logging.INFO):
            director.on_tick(previous_state, new_state)

        # Check that the formatted event is logged
        assert "SURPLUS_EXTRACTION" in caplog.text

    def test_on_tick_handles_no_new_events(
        self,
        initial_state: WorldState,
    ) -> None:
        """on_tick handles case with no new events gracefully.

        Sprint 4.1: Updated to use typed events.
        """
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector()

        # Create a typed event
        old_event = ExtractionEvent(
            tick=0,
            source_id="C001",
            target_id="C002",
            amount=5.0,
        )

        # Both states have same events
        previous_state = initial_state.model_copy(update={"events": [old_event]})
        new_state = initial_state.model_copy(update={"tick": 1, "events": [old_event]})

        # Should not raise
        director.on_tick(previous_state, new_state)


# =============================================================================
# TEST LIFECYCLE
# =============================================================================


@pytest.mark.unit
class TestNarrativeDirectorLifecycle:
    """Tests for NarrativeDirector lifecycle hooks."""

    def test_on_simulation_start_initializes_context(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """on_simulation_start logs initialization."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector()

        with caplog.at_level(logging.INFO):
            director.on_simulation_start(initial_state, config)

        assert "Simulation started" in caplog.text
        assert "tick 0" in caplog.text

    def test_on_simulation_end_produces_summary(
        self,
        initial_state: WorldState,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """on_simulation_end logs summary."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector()

        final_state = initial_state.model_copy(
            update={
                "tick": 100,
                "event_log": ["Event 1", "Event 2", "Event 3"],
            }
        )

        with caplog.at_level(logging.INFO):
            director.on_simulation_end(final_state)

        assert "Simulation ended" in caplog.text
        assert "tick 100" in caplog.text
        assert "3 total events" in caplog.text


# =============================================================================
# TEST ERROR HANDLING
# =============================================================================


@pytest.mark.unit
class TestNarrativeDirectorErrorHandling:
    """Tests for NarrativeDirector error handling."""

    def test_on_tick_error_returns_gracefully(
        self,
        initial_state: WorldState,
    ) -> None:
        """on_tick handles internal errors gracefully (no exception propagation)."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector()

        # Even with unusual input, should not crash
        previous_state = initial_state
        new_state = initial_state.model_copy(update={"tick": 1})

        # Should not raise
        director.on_tick(previous_state, new_state)


# =============================================================================
# TEST INTEGRATION WITH SIMULATION
# =============================================================================


@pytest.mark.unit
class TestNarrativeDirectorIntegration:
    """Tests for NarrativeDirector integration with Simulation."""

    def test_narrative_director_receives_all_lifecycle_events(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """NarrativeDirector integrated with Simulation receives all events."""
        from babylon.ai.director import NarrativeDirector
        from babylon.engine.simulation import Simulation

        director = NarrativeDirector()
        sim = Simulation(initial_state, config, observers=[director])

        with caplog.at_level(logging.INFO):
            sim.step()
            sim.step()
            sim.end()

        # Should see start, ticks, and end
        assert "Simulation started" in caplog.text
        assert "Simulation ended" in caplog.text


# =============================================================================
# TEST PER-TICK EVENT SEMANTICS (REGRESSION TESTS)
# =============================================================================


@pytest.mark.unit
class TestNarrativeDirectorPerTickEvents:
    """Tests for per-tick event semantics (regression for bug fix).

    Bug: Code assumed events accumulated across ticks, but WorldState.events
    is replaced each tick with only that tick's events.

    Original broken code (director.py:273-279):
        num_new_events = len(new_state.events) - len(previous_state.events)
        if num_new_events == 0:
            return
        new_events = list(new_state.events[-num_new_events:])

    When prev=1 event and new=0 events, this gave num_new_events=-1,
    causing incorrect slicing behavior.

    Fix: Changed to recognize all events in new_state are new:
        new_events = list(new_state.events)
    """

    def test_events_are_per_tick_not_cumulative(
        self,
        initial_state: WorldState,
    ) -> None:
        """Events in new_state are from current tick only, not accumulated.

        Regression test: Verifies the fix for negative event count bug.
        Previous code gave negative count when prev had more events than new.
        """
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector()

        # Tick 1: has 1 event
        event_tick1 = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )
        state_tick1 = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [event_tick1],
            }
        )

        # Tick 2: has 0 events (events are per-tick, not cumulative)
        state_tick2 = initial_state.model_copy(
            update={
                "tick": 2,
                "events": [],  # Empty! Events don't accumulate
            }
        )

        # Should NOT crash (was crashing with negative slice before fix)
        director.on_tick(state_tick1, state_tick2)

    def test_all_new_state_events_are_processed(
        self,
        initial_state: WorldState,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """All events in new_state should be processed as new events."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector()

        # Previous tick: no events
        prev_state = initial_state.model_copy(update={"tick": 0, "events": []})

        # New tick: 3 events (all new since events are per-tick)
        events = [
            ExtractionEvent(tick=1, source_id="C001", target_id="C002", amount=1.0),
            ExtractionEvent(tick=1, source_id="C002", target_id="C001", amount=2.0),
            TransmissionEvent(
                tick=1,
                source_id="C001",
                target_id="C002",
                delta=0.05,
                solidarity_strength=0.5,
            ),
        ]
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "events": events,
            }
        )

        # Should process all 3 events without error
        with caplog.at_level(logging.INFO):
            director.on_tick(prev_state, new_state)

        # All 3 events should be logged (2 SURPLUS_EXTRACTION, 1 CONSCIOUSNESS_TRANSMISSION)
        assert caplog.text.count("SURPLUS_EXTRACTION") == 2
        assert "CONSCIOUSNESS_TRANSMISSION" in caplog.text

    def test_decreasing_event_count_between_ticks_handled(
        self,
        initial_state: WorldState,
    ) -> None:
        """Handle case where previous tick had more events than current tick.

        This is the exact scenario that triggered the original bug:
        prev_state.events had length 3, new_state.events had length 1.
        Old code: 1 - 3 = -2, then sliced [-(-2):] = last 2 events.
        """
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector()

        # Previous tick had 3 events
        prev_events = [
            ExtractionEvent(tick=1, source_id="C001", target_id="C002", amount=1.0),
            ExtractionEvent(tick=1, source_id="C002", target_id="C001", amount=2.0),
            ExtractionEvent(tick=1, source_id="C001", target_id="C002", amount=3.0),
        ]
        prev_state = initial_state.model_copy(update={"tick": 1, "events": prev_events})

        # New tick has only 1 event (events don't carry over)
        new_events = [
            TransmissionEvent(
                tick=2,
                source_id="C001",
                target_id="C002",
                delta=0.05,
                solidarity_strength=0.5,
            ),
        ]
        new_state = initial_state.model_copy(update={"tick": 2, "events": new_events})

        # Should NOT crash and should process the 1 new event correctly
        director.on_tick(prev_state, new_state)


# =============================================================================
# TEST DUAL NARRATIVE GENERATION (GRAMSCIAN WIRE MVP)
# =============================================================================


@pytest.mark.unit
class TestNarrativeDirectorDualNarratives:
    """Tests for dual narrative generation (Gramscian Wire MVP).

    The dual narrative system generates contrasting perspectives:
    - Corporate: establishment/hegemonic framing
    - Liberated: revolutionary/counter-hegemonic framing

    Only SIGNIFICANT_EVENT_TYPES trigger dual narrative generation.
    """

    def test_dual_narratives_generated_for_significant_events(
        self,
        initial_state: WorldState,
    ) -> None:
        """Significant events trigger dual narrative generation."""
        from babylon.ai import MockLLM, NarrativeDirector
        from babylon.models.events import SparkEvent

        llm = MockLLM(responses=["Corporate view", "Liberated view"])
        director = NarrativeDirector(use_llm=True, llm=llm)

        # EXCESSIVE_FORCE (SparkEvent) is a SIGNIFICANT_EVENT_TYPE
        spark_event = SparkEvent(
            tick=1,
            node_id="C001",
            repression=0.7,
            spark_probability=0.35,
        )
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [spark_event],
            }
        )

        director.on_tick(initial_state, new_state)

        assert len(director.dual_narratives) == 1
        assert 1 in director.dual_narratives
        assert "corporate" in director.dual_narratives[1]
        assert "liberated" in director.dual_narratives[1]
        assert "event" in director.dual_narratives[1]

    def test_non_significant_events_skip_dual_narratives(
        self,
        initial_state: WorldState,
    ) -> None:
        """Non-significant events don't trigger LLM calls for dual narratives."""
        from babylon.ai import MockLLM, NarrativeDirector

        llm = MockLLM(responses=["Should not be called"])
        director = NarrativeDirector(use_llm=True, llm=llm)

        # TransmissionEvent (CONSCIOUSNESS_TRANSMISSION) is NOT in SIGNIFICANT_EVENT_TYPES
        event = TransmissionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            delta=0.05,
            solidarity_strength=0.5,
        )
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [event],
            }
        )

        director.on_tick(initial_state, new_state)

        # No dual narratives generated for transmission events
        assert len(director.dual_narratives) == 0

    def test_significant_event_types_constant(self) -> None:
        """SIGNIFICANT_EVENT_TYPES contains expected event types."""
        from babylon.ai.director import NarrativeDirector
        from babylon.models.enums import EventType

        expected = frozenset(
            {
                EventType.SURPLUS_EXTRACTION,
                EventType.ECONOMIC_CRISIS,
                EventType.PHASE_TRANSITION,
                EventType.UPRISING,
                EventType.EXCESSIVE_FORCE,
                EventType.RUPTURE,
                EventType.MASS_AWAKENING,
                EventType.SUPERWAGE_CRISIS,
                EventType.TERMINAL_DECISION,
                EventType.ENDGAME_REACHED,  # Epoch 1 Gap 2: Endgame narrative support
            }
        )

        assert expected == NarrativeDirector.SIGNIFICANT_EVENT_TYPES

    def test_semantic_map_contains_endgame_reached(self) -> None:
        """SEMANTIC_MAP has query string for ENDGAME_REACHED events.

        The SEMANTIC_MAP translates event types into theoretical query strings
        for RAG retrieval. ENDGAME_REACHED needs a mapping to enable historical
        context retrieval for endgame narratives.
        """
        from babylon.ai.director import NarrativeDirector
        from babylon.models.enums import EventType

        assert EventType.ENDGAME_REACHED in NarrativeDirector.SEMANTIC_MAP
        query = NarrativeDirector.SEMANTIC_MAP[EventType.ENDGAME_REACHED]
        # Query should contain relevant theoretical keywords
        assert "historical materialism" in query.lower() or "revolutionary" in query.lower()

    def test_dual_narratives_contain_both_perspectives(
        self,
        initial_state: WorldState,
    ) -> None:
        """Dual narratives contain both corporate and liberated text."""
        from babylon.ai import MockLLM, NarrativeDirector
        from babylon.models.events import UprisingEvent

        llm = MockLLM(
            responses=[
                "Authorities maintained order during civil unrest.",
                ">>> TRANSMISSION <<< Workers rose against oppression!",
            ]
        )
        director = NarrativeDirector(use_llm=True, llm=llm)

        uprising = UprisingEvent(
            tick=5,
            node_id="C001",
            trigger="spark",
            agitation=0.8,
            repression=0.6,
        )
        new_state = initial_state.model_copy(
            update={
                "tick": 5,
                "events": [uprising],
            }
        )

        director.on_tick(initial_state, new_state)

        narratives = director.dual_narratives[5]
        assert "Authorities" in narratives["corporate"]
        assert "TRANSMISSION" in narratives["liberated"]

    def test_endgame_event_triggers_dual_narratives(
        self,
        initial_state: WorldState,
    ) -> None:
        """ENDGAME_REACHED events trigger dual narrative generation.

        EndgameEvent is a significant event type that should produce both
        corporate (status quo) and liberated (revolutionary) perspectives
        for the game's conclusion.
        """
        from babylon.ai import MockLLM, NarrativeDirector
        from babylon.models.enums import GameOutcome
        from babylon.models.events import EndgameEvent

        llm = MockLLM(
            responses=[
                "Order has been restored after a period of instability.",
                ">>> TRANSMISSION <<< The workers have seized the means!",
            ]
        )
        director = NarrativeDirector(use_llm=True, llm=llm)

        endgame_event = EndgameEvent(
            tick=100,
            outcome=GameOutcome.REVOLUTIONARY_VICTORY,
        )
        new_state = initial_state.model_copy(update={"tick": 100, "events": [endgame_event]})

        director.on_tick(initial_state, new_state)

        # Dual narratives should be generated for significant events
        assert len(director.dual_narratives) == 1
        assert 100 in director.dual_narratives
        assert "corporate" in director.dual_narratives[100]
        assert "liberated" in director.dual_narratives[100]
        assert "event" in director.dual_narratives[100]

    def test_dual_narratives_skipped_without_llm(
        self,
        initial_state: WorldState,
    ) -> None:
        """Without LLM, dual narratives are not generated.

        The dual narrative system requires an LLM to generate meaningful
        contrasting perspectives. When no LLM is provided, the system
        correctly skips dual narrative generation entirely.
        """
        from babylon.ai.director import NarrativeDirector
        from babylon.models.events import RuptureEvent

        # No LLM provided, use_llm=True but _llm=None
        director = NarrativeDirector(use_llm=True, llm=None)

        rupture = RuptureEvent(tick=1, edge="C001->C002")
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [rupture],
            }
        )

        director.on_tick(initial_state, new_state)

        # No dual narratives generated without LLM
        assert len(director.dual_narratives) == 0

    def test_significant_event_types_includes_terminal_crisis_events(self) -> None:
        """SIGNIFICANT_EVENT_TYPES includes terminal crisis event types.

        Phase 2 Dashboard: SUPERWAGE_CRISIS and TERMINAL_DECISION events
        should trigger narrative generation for the narrative feed.
        """
        from babylon.ai.director import NarrativeDirector
        from babylon.models.enums import EventType

        # Terminal Crisis events should be significant
        assert EventType.SUPERWAGE_CRISIS in NarrativeDirector.SIGNIFICANT_EVENT_TYPES
        assert EventType.TERMINAL_DECISION in NarrativeDirector.SIGNIFICANT_EVENT_TYPES
