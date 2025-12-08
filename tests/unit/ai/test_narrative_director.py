"""Tests for NarrativeDirector AI observer implementation.

TDD Red Phase: These tests define the contract for the NarrativeDirector
that observes simulation state changes and generates narrative.

The NarrativeDirector sits in the Ideological Superstructure - it observes
the Material Base (simulation mechanics) but cannot modify it.
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
        """on_tick detects new events added during tick."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector()

        # Initial state with no events
        previous_state = initial_state

        # New state with events added
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["Event A happened", "Event B happened"],
            }
        )

        # Should not raise
        director.on_tick(previous_state, new_state)

    def test_on_tick_logs_new_events(
        self,
        initial_state: WorldState,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """on_tick logs new events."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector()

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["Revolution brewing in the periphery"],
            }
        )

        with caplog.at_level(logging.INFO):
            director.on_tick(previous_state, new_state)

        assert "Revolution brewing" in caplog.text

    def test_on_tick_handles_no_new_events(
        self,
        initial_state: WorldState,
    ) -> None:
        """on_tick handles case with no new events gracefully."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector()

        # Both states have same event log
        previous_state = initial_state.model_copy(update={"event_log": ["Old event"]})
        new_state = initial_state.model_copy(update={"tick": 1, "event_log": ["Old event"]})

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
