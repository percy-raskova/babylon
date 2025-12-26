"""Unit tests for interview_persona.py tuning fork script.

TDD RED Phase: These tests verify the event construction, accumulation pattern,
and NarrativeDirector integration without requiring real LLM calls.

Tests use MockLLM to verify the full flow without external dependencies.
"""

from __future__ import annotations

from babylon.ai.director import NarrativeDirector
from babylon.ai.llm_provider import MockLLM
from babylon.ai.persona_loader import load_default_persona
from babylon.engine.factories import create_bourgeoisie, create_proletariat
from babylon.models.entities.relationship import Relationship
from babylon.models.enums import EdgeType, EventType
from babylon.models.events import CrisisEvent, ExtractionEvent, PhaseTransitionEvent
from babylon.models.world_state import WorldState


class TestEventConstruction:
    """Test that Hard Case events are constructed correctly."""

    def test_extraction_event_valid(self) -> None:
        """Verify ExtractionEvent with all required fields."""
        event = ExtractionEvent(
            tick=1,
            source_id="GlobalSouth",
            target_id="Empire_Core",
            amount=1000.0,
            mechanism="Debt Servicing",
        )

        assert event.tick == 1
        assert event.source_id == "GlobalSouth"
        assert event.target_id == "Empire_Core"
        assert event.amount == 1000.0
        assert event.mechanism == "Debt Servicing"
        assert event.event_type == EventType.SURPLUS_EXTRACTION

    def test_crisis_event_valid(self) -> None:
        """Verify CrisisEvent with all required fields."""
        event = CrisisEvent(
            tick=2,
            pool_ratio=0.12,
            aggregate_tension=0.95,
            decision="AUSTERITY",
            wage_delta=-0.25,
        )

        assert event.tick == 2
        assert event.pool_ratio == 0.12
        assert event.aggregate_tension == 0.95
        assert event.decision == "AUSTERITY"
        assert event.wage_delta == -0.25
        assert event.event_type == EventType.ECONOMIC_CRISIS

    def test_phase_transition_event_valid(self) -> None:
        """Verify PhaseTransitionEvent with all required fields."""
        event = PhaseTransitionEvent(
            tick=3,
            previous_state="liquid",
            new_state="solid",
            percolation_ratio=0.88,
            num_components=1,
            largest_component_size=150,
            cadre_density=0.75,
        )

        assert event.tick == 3
        assert event.previous_state == "liquid"
        assert event.new_state == "solid"
        assert event.percolation_ratio == 0.88
        assert event.num_components == 1
        assert event.largest_component_size == 150
        assert event.cadre_density == 0.75
        assert event.event_type == EventType.PHASE_TRANSITION


class TestEventAccumulationPattern:
    """Test the Event Accumulation Pattern: events grow each tick."""

    def test_event_accumulation_pattern(self) -> None:
        """Verify state.events grows: tick1 has 1, tick2 has 2, tick3 has 3."""
        # Create Hard Case events
        extraction_event = ExtractionEvent(
            tick=1,
            source_id="GlobalSouth",
            target_id="Empire_Core",
            amount=1000.0,
            mechanism="Debt Servicing",
        )

        crisis_event = CrisisEvent(
            tick=2,
            pool_ratio=0.12,
            aggregate_tension=0.95,
            decision="AUSTERITY",
            wage_delta=-0.25,
        )

        phase_event = PhaseTransitionEvent(
            tick=3,
            previous_state="liquid",
            new_state="solid",
            percolation_ratio=0.88,
            num_components=1,
            largest_component_size=150,
            cadre_density=0.75,
        )

        # Simulate accumulation pattern
        events_tick1 = [extraction_event]
        events_tick2 = events_tick1 + [crisis_event]
        events_tick3 = events_tick2 + [phase_event]

        # Verify accumulation
        assert len(events_tick1) == 1
        assert len(events_tick2) == 2
        assert len(events_tick3) == 3

        # Verify all events preserved
        assert events_tick3[0].event_type == EventType.SURPLUS_EXTRACTION
        assert events_tick3[1].event_type == EventType.ECONOMIC_CRISIS
        assert events_tick3[2].event_type == EventType.PHASE_TRANSITION


class TestMinimalWorldState:
    """Test minimal WorldState construction."""

    def test_minimal_worldstate_creation(self) -> None:
        """Verify minimal state can be created with 2 entities + 1 edge."""
        worker = create_proletariat()
        owner = create_bourgeoisie()

        exploitation = Relationship(
            source_id=worker.id,
            target_id=owner.id,
            edge_type=EdgeType.EXPLOITATION,
            value_flow=0.0,
            tension=0.0,
        )

        state = WorldState(
            tick=0,
            entities={worker.id: worker, owner.id: owner},
            relationships=[exploitation],
            event_log=[],
            events=[],
        )

        assert state.tick == 0
        assert len(state.entities) == 2
        assert len(state.relationships) == 1
        assert len(state.events) == 0

    def test_worldstate_with_events(self) -> None:
        """Verify WorldState can be created with events."""
        worker = create_proletariat()
        owner = create_bourgeoisie()

        extraction_event = ExtractionEvent(
            tick=1,
            source_id="GlobalSouth",
            target_id="Empire_Core",
            amount=1000.0,
            mechanism="Debt Servicing",
        )

        state = WorldState(
            tick=1,
            entities={worker.id: worker, owner.id: owner},
            relationships=[],
            event_log=[],
            events=[extraction_event],
        )

        assert len(state.events) == 1
        assert state.events[0].event_type == EventType.SURPLUS_EXTRACTION


class TestNarrativeDirectorIntegration:
    """Test NarrativeDirector integration with MockLLM."""

    def test_director_processes_significant_events(self) -> None:
        """Verify director calls LLM for significant events."""
        mock_llm = MockLLM(
            responses=["The empire extracts its tribute, comrade."],
        )
        persona = load_default_persona()
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            persona=persona,
        )

        worker = create_proletariat()
        owner = create_bourgeoisie()

        # State before event
        previous_state = WorldState(
            tick=0,
            entities={worker.id: worker, owner.id: owner},
            relationships=[],
            event_log=[],
            events=[],
        )

        # State with significant event (SURPLUS_EXTRACTION is significant)
        extraction_event = ExtractionEvent(
            tick=1,
            source_id="GlobalSouth",
            target_id="Empire_Core",
            amount=1000.0,
            mechanism="Debt Servicing",
        )

        new_state = WorldState(
            tick=1,
            entities={worker.id: worker, owner.id: owner},
            relationships=[],
            event_log=[],
            events=[extraction_event],
        )

        director.on_tick(previous_state, new_state)

        # Verify LLM was called
        assert mock_llm.call_count == 1
        assert len(director.narrative_log) == 1
        assert "tribute" in director.narrative_log[0]

    def test_director_uses_persona_system_prompt(self) -> None:
        """Verify persona.render_system_prompt() is used."""
        mock_llm = MockLLM(responses=["Dialectical analysis complete."])
        persona = load_default_persona()
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            persona=persona,
        )

        worker = create_proletariat()
        owner = create_bourgeoisie()

        previous_state = WorldState(
            tick=0,
            entities={worker.id: worker, owner.id: owner},
            relationships=[],
            event_log=[],
            events=[],
        )

        extraction_event = ExtractionEvent(
            tick=1,
            source_id="GlobalSouth",
            target_id="Empire_Core",
            amount=1000.0,
            mechanism="Debt Servicing",
        )

        new_state = WorldState(
            tick=1,
            entities={worker.id: worker, owner.id: owner},
            relationships=[],
            event_log=[],
            events=[extraction_event],
        )

        director.on_tick(previous_state, new_state)

        # Verify system prompt contains persona elements
        assert mock_llm.call_count == 1
        call = mock_llm.call_history[0]
        system_prompt = call["system_prompt"]

        # Verify persona elements are in system prompt
        assert "Persephone" in system_prompt
        assert "Architect" in system_prompt  # address_user_as
        assert "Sardonic" in system_prompt or "Prophetic" in system_prompt  # tone


class TestHardCaseScenario:
    """Test the complete Hard Case scenario with all 3 ticks."""

    def test_hard_case_full_scenario_with_mock_llm(self) -> None:
        """Verify all 3 Hard Case events generate narrative."""
        mock_llm = MockLLM(
            responses=[
                "The Squeeze: Debt servicing drains the periphery.",
                "The Crash: Austerity is capital's desperation.",
                "The Reaction: Solidarity crystallizes into organization.",
            ],
        )
        persona = load_default_persona()
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            persona=persona,
        )

        worker = create_proletariat()
        owner = create_bourgeoisie()

        # Tick 0: Initial state
        state_0 = WorldState(
            tick=0,
            entities={worker.id: worker, owner.id: owner},
            relationships=[],
            event_log=[],
            events=[],
        )

        # Tick 1: The Squeeze
        extraction_event = ExtractionEvent(
            tick=1,
            source_id="GlobalSouth",
            target_id="Empire_Core",
            amount=1000.0,
            mechanism="Debt Servicing",
        )
        state_1 = WorldState(
            tick=1,
            entities={worker.id: worker, owner.id: owner},
            relationships=[],
            event_log=[],
            events=[extraction_event],
        )

        director.on_tick(state_0, state_1)
        assert mock_llm.call_count == 1

        # Tick 2: The Crash (accumulate previous events)
        crisis_event = CrisisEvent(
            tick=2,
            pool_ratio=0.12,
            aggregate_tension=0.95,
            decision="AUSTERITY",
            wage_delta=-0.25,
        )
        state_2 = WorldState(
            tick=2,
            entities={worker.id: worker, owner.id: owner},
            relationships=[],
            event_log=[],
            events=list(state_1.events) + [crisis_event],
        )

        director.on_tick(state_1, state_2)
        assert mock_llm.call_count == 2

        # Tick 3: The Reaction (accumulate all events)
        phase_event = PhaseTransitionEvent(
            tick=3,
            previous_state="liquid",
            new_state="solid",
            percolation_ratio=0.88,
            num_components=1,
            largest_component_size=150,
            cadre_density=0.75,
        )
        state_3 = WorldState(
            tick=3,
            entities={worker.id: worker, owner.id: owner},
            relationships=[],
            event_log=[],
            events=list(state_2.events) + [phase_event],
        )

        director.on_tick(state_2, state_3)
        assert mock_llm.call_count == 3

        # Verify all narratives generated
        assert len(director.narrative_log) == 3
        assert "Squeeze" in director.narrative_log[0]
        assert "Crash" in director.narrative_log[1]
        assert "Reaction" in director.narrative_log[2]
