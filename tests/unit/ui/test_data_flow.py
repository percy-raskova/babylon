"""Tests for refresh_ui() data propagation to UI components.

These subcutaneous tests verify that refresh_ui() correctly pushes data
from the simulation state to all Synopticon dashboard components:

1. ControlDeck - tick counter
2. NarrativeTerminal - narrative entries from NarrativeDirector
3. TrendPlotter - Imperial Rent and Global Tension metrics
4. StateInspector - C001 entity JSON
5. SystemLog - simulation events with log levels

The tests use mock components to verify method calls without browser rendering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from babylon.models.entities.economy import GlobalEconomy
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import SocialClass
from babylon.models.enums import EdgeType, SocialRole
from babylon.models.events import CrisisEvent, ExtractionEvent, SparkEvent
from babylon.models.world_state import WorldState

if TYPE_CHECKING:
    pass


# =============================================================================
# TEST CONTROL DECK UPDATES
# =============================================================================


class TestRefreshUIControlDeck:
    """Tests for refresh_ui() updating ControlDeck tick counter."""

    def test_refresh_ui_updates_control_deck_tick(
        self,
        reset_main_module_state: None,
        mock_simulation: Mock,
        mock_control_deck: Mock,
    ) -> None:
        """refresh_ui() calls control_deck.update_tick() with current tick."""
        import babylon.ui.main as main

        main._state.simulation = mock_simulation
        main._state.control_deck = mock_control_deck
        mock_simulation.current_state = WorldState(tick=42)

        main.refresh_ui()

        mock_control_deck.update_tick.assert_called_once_with(42)

    def test_refresh_ui_handles_none_control_deck(
        self,
        reset_main_module_state: None,
        mock_simulation: Mock,
    ) -> None:
        """refresh_ui() handles None control_deck gracefully."""
        import babylon.ui.main as main

        main._state.simulation = mock_simulation
        main._state.control_deck = None

        # Should not raise
        main.refresh_ui()


# =============================================================================
# TEST TREND PLOTTER UPDATES
# =============================================================================


class TestRefreshUITrendPlotter:
    """Tests for refresh_ui() pushing metrics to TrendPlotter."""

    def test_refresh_ui_pushes_rent_to_trend_plotter(
        self,
        reset_main_module_state: None,
        mock_simulation: Mock,
        mock_trend_plotter: Mock,
    ) -> None:
        """refresh_ui() pushes imperial_rent_pool to TrendPlotter."""
        import babylon.ui.main as main

        main._state.simulation = mock_simulation
        main._state.trend_plotter = mock_trend_plotter

        # Set up state with known rent value (use custom economy since frozen)
        economy = GlobalEconomy(imperial_rent_pool=150.0)
        state = WorldState(tick=5, economy=economy)
        mock_simulation.current_state = state

        main.refresh_ui()

        # Should call push_data with tick, rent, and tension
        mock_trend_plotter.push_data.assert_called_once()
        call_args = mock_trend_plotter.push_data.call_args[0]
        assert call_args[0] == 5  # tick
        assert call_args[1] == pytest.approx(150.0)  # rent

    def test_refresh_ui_pushes_tension_to_trend_plotter(
        self,
        reset_main_module_state: None,
        mock_simulation: Mock,
        mock_trend_plotter: Mock,
    ) -> None:
        """refresh_ui() calculates and pushes global tension to TrendPlotter."""
        import babylon.ui.main as main

        main._state.simulation = mock_simulation
        main._state.trend_plotter = mock_trend_plotter

        # Create entities
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=50.0,
        )
        owner = SocialClass(
            id="C002",
            name="Owner",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=500.0,
        )

        # Create relationships with known tensions (avg = 0.5)
        rel1 = Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.EXPLOITATION,
            tension=0.4,
        )
        rel2 = Relationship(
            source_id="C002",
            target_id="C001",
            edge_type=EdgeType.REPRESSION,
            tension=0.6,
        )

        state = WorldState(
            tick=10,
            entities={"C001": worker, "C002": owner},
            relationships=[rel1, rel2],
        )
        mock_simulation.current_state = state

        main.refresh_ui()

        # Verify tension is average of 0.4 and 0.6 = 0.5
        call_args = mock_trend_plotter.push_data.call_args[0]
        assert call_args[2] == pytest.approx(0.5)  # tension

    def test_refresh_ui_handles_empty_relationships(
        self,
        reset_main_module_state: None,
        mock_simulation: Mock,
        mock_trend_plotter: Mock,
    ) -> None:
        """refresh_ui() returns 0.0 tension when no relationships exist."""
        import babylon.ui.main as main

        main._state.simulation = mock_simulation
        main._state.trend_plotter = mock_trend_plotter

        state = WorldState(tick=1, relationships=[])
        mock_simulation.current_state = state

        main.refresh_ui()

        call_args = mock_trend_plotter.push_data.call_args[0]
        assert call_args[2] == 0.0  # tension = 0.0

    def test_refresh_ui_handles_none_trend_plotter(
        self,
        reset_main_module_state: None,
        mock_simulation: Mock,
    ) -> None:
        """refresh_ui() handles None trend_plotter gracefully."""
        import babylon.ui.main as main

        main._state.simulation = mock_simulation
        main._state.trend_plotter = None

        # Should not raise
        main.refresh_ui()


# =============================================================================
# TEST STATE INSPECTOR UPDATES
# =============================================================================


class TestRefreshUIStateInspector:
    """Tests for refresh_ui() updating StateInspector with C001 entity."""

    def test_refresh_ui_updates_state_inspector_with_c001(
        self,
        reset_main_module_state: None,
        mock_simulation: Mock,
        mock_state_inspector: Mock,
    ) -> None:
        """refresh_ui() calls state_inspector.refresh() with C001 entity data."""
        import babylon.ui.main as main

        main._state.simulation = mock_simulation
        main._state.state_inspector = mock_state_inspector

        # Create C001 entity
        worker = SocialClass(
            id="C001",
            name="Periphery Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=75.0,
        )

        state = WorldState(tick=3, entities={"C001": worker})
        mock_simulation.current_state = state

        main.refresh_ui()

        # Verify refresh called with entity data dict
        mock_state_inspector.refresh.assert_called_once()
        call_args = mock_state_inspector.refresh.call_args[0][0]
        assert call_args["id"] == "C001"
        assert call_args["name"] == "Periphery Worker"
        assert call_args["wealth"] == 75.0

    def test_refresh_ui_handles_missing_c001_entity(
        self,
        reset_main_module_state: None,
        mock_simulation: Mock,
        mock_state_inspector: Mock,
    ) -> None:
        """refresh_ui() handles missing C001 entity gracefully."""
        import babylon.ui.main as main

        main._state.simulation = mock_simulation
        main._state.state_inspector = mock_state_inspector

        # State with no C001
        state = WorldState(tick=1, entities={})
        mock_simulation.current_state = state

        main.refresh_ui()

        # Should not call refresh when C001 missing
        mock_state_inspector.refresh.assert_not_called()

    def test_refresh_ui_handles_none_state_inspector(
        self,
        reset_main_module_state: None,
        mock_simulation: Mock,
    ) -> None:
        """refresh_ui() handles None state_inspector gracefully."""
        import babylon.ui.main as main

        main._state.simulation = mock_simulation
        main._state.state_inspector = None

        # Should not raise
        main.refresh_ui()


# =============================================================================
# TEST SYSTEM LOG UPDATES
# =============================================================================


class TestRefreshUISystemLog:
    """Tests for refresh_ui() logging events to SystemLog."""

    def test_refresh_ui_logs_events_to_system_log(
        self,
        reset_main_module_state: None,
        mock_simulation: Mock,
        mock_system_log: Mock,
    ) -> None:
        """refresh_ui() logs new events to system_log."""
        import babylon.ui.main as main

        main._state.simulation = mock_simulation
        main._state.system_log = mock_system_log
        main._state.last_event_index = 0

        # Create extraction event
        event = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )

        state = WorldState(tick=1, events=[event])
        mock_simulation.current_state = state

        main.refresh_ui()

        # Verify log called
        mock_system_log.log.assert_called_once()
        call_args = mock_system_log.log.call_args
        assert "surplus_extraction" in call_args[0][0]  # Event type is lowercase
        assert call_args[0][1] == "INFO"  # Normal event = INFO

    def test_refresh_ui_incremental_event_logging(
        self,
        reset_main_module_state: None,
        mock_simulation: Mock,
        mock_system_log: Mock,
    ) -> None:
        """refresh_ui() only logs NEW events (index tracking)."""
        import babylon.ui.main as main

        main._state.simulation = mock_simulation
        main._state.system_log = mock_system_log
        main._state.last_event_index = 2  # Already processed 2 events

        # Create 3 events, but only event 3 is new
        event1 = ExtractionEvent(tick=1, source_id="C001", target_id="C002", amount=10.0)
        event2 = ExtractionEvent(tick=2, source_id="C001", target_id="C002", amount=15.0)
        event3 = ExtractionEvent(tick=3, source_id="C001", target_id="C002", amount=20.0)

        state = WorldState(tick=3, events=[event1, event2, event3])
        mock_simulation.current_state = state

        main.refresh_ui()

        # Only event3 should be logged (index 2 onwards)
        mock_system_log.log.assert_called_once()
        assert main._state.last_event_index == 3

    def test_refresh_ui_maps_crisis_to_error_level(
        self,
        reset_main_module_state: None,
        mock_simulation: Mock,
        mock_system_log: Mock,
    ) -> None:
        """refresh_ui() maps ECONOMIC_CRISIS events to ERROR log level."""
        import babylon.ui.main as main

        main._state.simulation = mock_simulation
        main._state.system_log = mock_system_log
        main._state.last_event_index = 0

        crisis_event = CrisisEvent(
            tick=10,
            pool_ratio=0.15,
            aggregate_tension=0.7,
            decision="CRISIS",
            wage_delta=-0.05,
        )

        state = WorldState(tick=10, events=[crisis_event])
        mock_simulation.current_state = state

        main.refresh_ui()

        call_args = mock_system_log.log.call_args
        assert call_args[0][1] == "ERROR"  # Crisis = ERROR level

    def test_refresh_ui_maps_excessive_force_to_warn_level(
        self,
        reset_main_module_state: None,
        mock_simulation: Mock,
        mock_system_log: Mock,
    ) -> None:
        """refresh_ui() maps EXCESSIVE_FORCE events to WARN log level."""
        import babylon.ui.main as main

        main._state.simulation = mock_simulation
        main._state.system_log = mock_system_log
        main._state.last_event_index = 0

        spark_event = SparkEvent(
            tick=5,
            node_id="C001",
            repression=0.8,
            spark_probability=0.4,
        )

        state = WorldState(tick=5, events=[spark_event])
        mock_simulation.current_state = state

        main.refresh_ui()

        call_args = mock_system_log.log.call_args
        assert call_args[0][1] == "WARN"  # Excessive force = WARN level

    def test_refresh_ui_handles_none_system_log(
        self,
        reset_main_module_state: None,
        mock_simulation: Mock,
    ) -> None:
        """refresh_ui() handles None system_log gracefully."""
        import babylon.ui.main as main

        main._state.simulation = mock_simulation
        main._state.system_log = None

        event = ExtractionEvent(tick=1, source_id="C001", target_id="C002", amount=10.0)
        state = WorldState(tick=1, events=[event])
        mock_simulation.current_state = state

        # Should not raise
        main.refresh_ui()


# =============================================================================
# TEST FULL REFRESH CYCLE
# =============================================================================


class TestRefreshUIFullCycle:
    """Tests for complete refresh_ui() cycles with all components."""

    def test_refresh_ui_updates_all_components(
        self,
        reset_main_module_state: None,
        mock_simulation: Mock,
        mock_control_deck: Mock,
        mock_trend_plotter: Mock,
        mock_state_inspector: Mock,
        mock_system_log: Mock,
    ) -> None:
        """refresh_ui() updates all Synopticon panels in single call."""
        import babylon.ui.main as main

        main._state.simulation = mock_simulation
        main._state.control_deck = mock_control_deck
        main._state.trend_plotter = mock_trend_plotter
        main._state.state_inspector = mock_state_inspector
        main._state.system_log = mock_system_log
        main._state.last_event_index = 0

        # Create comprehensive state (use custom economy since frozen)
        worker = SocialClass(
            id="C001",
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=100.0,
        )
        event = ExtractionEvent(tick=5, source_id="C001", target_id="C002", amount=10.0)
        economy = GlobalEconomy(imperial_rent_pool=200.0)

        state = WorldState(tick=5, entities={"C001": worker}, events=[event], economy=economy)
        mock_simulation.current_state = state

        main.refresh_ui()

        # All components should be updated
        mock_control_deck.update_tick.assert_called_once()
        mock_trend_plotter.push_data.assert_called_once()
        mock_state_inspector.refresh.assert_called_once()
        mock_system_log.log.assert_called_once()

    def test_refresh_ui_handles_none_simulation(
        self,
        reset_main_module_state: None,
    ) -> None:
        """refresh_ui() returns early when simulation is None."""
        import babylon.ui.main as main

        main._state.simulation = None

        # Should not raise
        main.refresh_ui()
