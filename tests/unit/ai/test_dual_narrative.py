"""Tests for Dual Narrative System - The Gramscian Wire.

TDD Red Phase: These tests define the contract for dual-perspective
narrative generation. The NarrativeDirector will generate two views
of the same simulation events:

1. CORPORATE: Hegemonic perspective that frames events to maintain status quo
2. LIBERATED: Revolutionary perspective that reveals material conditions

This implements the ideological component of the simulation - demonstrating
how the same material reality can be framed in contradictory ways.

Sprint 4.3: Dual Narrative feature implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    pass

from babylon.models import (
    EdgeType,
    Relationship,
    SocialClass,
    SocialRole,
    WorldState,
)
from babylon.models.events import UprisingEvent

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
def uprising_event() -> UprisingEvent:
    """Create an uprising event for testing dual narratives."""
    return UprisingEvent(
        tick=1,
        node_id="C001",
        trigger="spark",
        agitation=0.9,
        repression=0.7,
    )


# =============================================================================
# TEST SYSTEM PROMPTS EXIST
# =============================================================================


@pytest.mark.unit
class TestDualNarrativeConstants:
    """Tests for dual narrative system prompt constants."""

    def test_corporate_system_prompt_exists(self) -> None:
        """CORPORATE_SYSTEM_PROMPT constant exists in director module."""
        from babylon.ai.director import CORPORATE_SYSTEM_PROMPT

        assert isinstance(CORPORATE_SYSTEM_PROMPT, str)
        assert len(CORPORATE_SYSTEM_PROMPT) > 0

    def test_corporate_system_prompt_contains_stability(self) -> None:
        """CORPORATE_SYSTEM_PROMPT emphasizes stability (hegemonic frame)."""
        from babylon.ai.director import CORPORATE_SYSTEM_PROMPT

        # The corporate voice should emphasize maintaining order
        assert "stability" in CORPORATE_SYSTEM_PROMPT.lower()

    def test_corporate_system_prompt_contains_passive_voice(self) -> None:
        """CORPORATE_SYSTEM_PROMPT directs use of passive voice."""
        from babylon.ai.director import CORPORATE_SYSTEM_PROMPT

        # Corporate media uses passive voice to obscure agency
        assert "passive voice" in CORPORATE_SYSTEM_PROMPT.lower()

    def test_corporate_system_prompt_contains_downplays(self) -> None:
        """CORPORATE_SYSTEM_PROMPT downplays systemic issues."""
        from babylon.ai.director import CORPORATE_SYSTEM_PROMPT

        # Hegemonic narrative minimizes structural analysis
        assert "downplays" in CORPORATE_SYSTEM_PROMPT.lower()

    def test_liberated_system_prompt_exists(self) -> None:
        """LIBERATED_SYSTEM_PROMPT constant exists in director module."""
        from babylon.ai.director import LIBERATED_SYSTEM_PROMPT

        assert isinstance(LIBERATED_SYSTEM_PROMPT, str)
        assert len(LIBERATED_SYSTEM_PROMPT) > 0

    def test_liberated_system_prompt_contains_revolutionary(self) -> None:
        """LIBERATED_SYSTEM_PROMPT contains revolutionary framing."""
        from babylon.ai.director import LIBERATED_SYSTEM_PROMPT

        # The liberated voice should embrace revolutionary analysis
        assert "revolutionary" in LIBERATED_SYSTEM_PROMPT.lower()

    def test_liberated_system_prompt_contains_solidarity(self) -> None:
        """LIBERATED_SYSTEM_PROMPT emphasizes solidarity."""
        from babylon.ai.director import LIBERATED_SYSTEM_PROMPT

        # Revolutionary perspective centers collective action
        assert "solidarity" in LIBERATED_SYSTEM_PROMPT.lower()

    def test_liberated_system_prompt_contains_active_voice(self) -> None:
        """LIBERATED_SYSTEM_PROMPT directs use of active voice."""
        from babylon.ai.director import LIBERATED_SYSTEM_PROMPT

        # Revolutionary narrative uses active voice to highlight agency
        assert "active voice" in LIBERATED_SYSTEM_PROMPT.lower()


# =============================================================================
# TEST _generate_perspective() METHOD
# =============================================================================


@pytest.mark.unit
class TestGeneratePerspective:
    """Tests for _generate_perspective() method."""

    def test_generate_perspective_method_exists(
        self,
        uprising_event: UprisingEvent,
    ) -> None:
        """NarrativeDirector has _generate_perspective() method."""
        from babylon.ai.director import NarrativeDirector
        from babylon.ai.llm_provider import MockLLM

        mock_llm = MockLLM(default_response="Test narrative")
        director = NarrativeDirector(use_llm=True, llm=mock_llm)

        # Method should exist and be callable
        assert hasattr(director, "_generate_perspective")
        assert callable(director._generate_perspective)

    def test_generate_perspective_returns_string(
        self,
        uprising_event: UprisingEvent,
    ) -> None:
        """_generate_perspective() returns a string."""
        from babylon.ai.director import NarrativeDirector
        from babylon.ai.llm_provider import MockLLM

        mock_llm = MockLLM(default_response="Test narrative")
        director = NarrativeDirector(use_llm=True, llm=mock_llm)

        result = director._generate_perspective(uprising_event, "CORPORATE")

        assert isinstance(result, str)

    def test_generate_perspective_corporate_uses_corporate_prompt(
        self,
        uprising_event: UprisingEvent,
    ) -> None:
        """_generate_perspective with CORPORATE uses CORPORATE_SYSTEM_PROMPT."""
        from babylon.ai.director import NarrativeDirector
        from babylon.ai.llm_provider import MockLLM

        mock_llm = MockLLM(default_response="Corporate narrative")
        director = NarrativeDirector(use_llm=True, llm=mock_llm)

        director._generate_perspective(uprising_event, "CORPORATE")

        # Verify the system prompt passed to LLM contains corporate framing
        assert mock_llm.call_count == 1
        call = mock_llm.call_history[0]
        assert call["system_prompt"] is not None
        assert "stability" in call["system_prompt"].lower()

    def test_generate_perspective_liberated_uses_liberated_prompt(
        self,
        uprising_event: UprisingEvent,
    ) -> None:
        """_generate_perspective with LIBERATED uses LIBERATED_SYSTEM_PROMPT."""
        from babylon.ai.director import NarrativeDirector
        from babylon.ai.llm_provider import MockLLM

        mock_llm = MockLLM(default_response="Liberated narrative")
        director = NarrativeDirector(use_llm=True, llm=mock_llm)

        director._generate_perspective(uprising_event, "LIBERATED")

        # Verify the system prompt passed to LLM contains revolutionary framing
        assert mock_llm.call_count == 1
        call = mock_llm.call_history[0]
        assert call["system_prompt"] is not None
        assert "revolutionary" in call["system_prompt"].lower()

    def test_generate_perspective_includes_event_in_prompt(
        self,
        uprising_event: UprisingEvent,
    ) -> None:
        """_generate_perspective includes event data in the user prompt."""
        from babylon.ai.director import NarrativeDirector
        from babylon.ai.llm_provider import MockLLM

        mock_llm = MockLLM(default_response="Test narrative")
        director = NarrativeDirector(use_llm=True, llm=mock_llm)

        director._generate_perspective(uprising_event, "CORPORATE")

        # The prompt should reference the event
        assert mock_llm.call_count == 1
        call = mock_llm.call_history[0]
        # Event type or key details should appear in prompt
        assert "uprising" in call["prompt"].lower() or "C001" in call["prompt"]


# =============================================================================
# TEST dual_narratives PROPERTY
# =============================================================================


@pytest.mark.unit
class TestDualNarrativesProperty:
    """Tests for dual_narratives property."""

    def test_dual_narratives_property_exists(self) -> None:
        """NarrativeDirector has dual_narratives property."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector()

        assert hasattr(director, "dual_narratives")

    def test_dual_narratives_returns_dict(self) -> None:
        """dual_narratives returns a dictionary."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector()
        result = director.dual_narratives

        assert isinstance(result, dict)

    def test_dual_narratives_initially_empty(self) -> None:
        """dual_narratives is initially empty."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector()
        result = director.dual_narratives

        assert len(result) == 0

    def test_dual_narratives_type_annotation(self) -> None:
        """dual_narratives has correct type annotation: dict[int, dict[str, Any]]."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector()
        result: dict[int, dict[str, Any]] = director.dual_narratives

        # Type annotation should be satisfied
        assert isinstance(result, dict)


# =============================================================================
# TEST on_tick() POPULATES DUAL NARRATIVES
# =============================================================================


@pytest.mark.unit
class TestOnTickPopulatesDualNarratives:
    """Tests for on_tick() populating _dual_narratives for significant events."""

    def test_on_tick_populates_dual_narratives_for_uprising(
        self,
        initial_state: WorldState,
        uprising_event: UprisingEvent,
    ) -> None:
        """on_tick populates dual_narratives for UprisingEvent."""
        from babylon.ai.director import NarrativeDirector
        from babylon.ai.llm_provider import MockLLM

        mock_llm = MockLLM(responses=["Corporate view of uprising", "Liberated view of uprising"])
        director = NarrativeDirector(use_llm=True, llm=mock_llm)

        # Initial state with no events
        previous_state = initial_state

        # New state with uprising event
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [uprising_event],
            }
        )

        director.on_tick(previous_state, new_state)

        # Dual narratives should have an entry for tick 1
        assert 1 in director.dual_narratives

    def test_on_tick_dual_narrative_entry_has_required_keys(
        self,
        initial_state: WorldState,
        uprising_event: UprisingEvent,
    ) -> None:
        """Dual narrative entry has 'event', 'corporate', 'liberated' keys."""
        from babylon.ai.director import NarrativeDirector
        from babylon.ai.llm_provider import MockLLM

        mock_llm = MockLLM(responses=["Corporate narrative", "Liberated narrative"])
        director = NarrativeDirector(use_llm=True, llm=mock_llm)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [uprising_event],
            }
        )

        director.on_tick(previous_state, new_state)

        entry = director.dual_narratives[1]
        assert "event" in entry
        assert "corporate" in entry
        assert "liberated" in entry

    def test_on_tick_dual_narrative_contains_event_reference(
        self,
        initial_state: WorldState,
        uprising_event: UprisingEvent,
    ) -> None:
        """Dual narrative entry 'event' contains the triggering event."""
        from babylon.ai.director import NarrativeDirector
        from babylon.ai.llm_provider import MockLLM

        mock_llm = MockLLM(responses=["Corporate narrative", "Liberated narrative"])
        director = NarrativeDirector(use_llm=True, llm=mock_llm)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [uprising_event],
            }
        )

        director.on_tick(previous_state, new_state)

        entry = director.dual_narratives[1]
        # The event key should reference the actual event
        assert entry["event"] == uprising_event

    def test_on_tick_dual_narrative_contains_generated_narratives(
        self,
        initial_state: WorldState,
        uprising_event: UprisingEvent,
    ) -> None:
        """Dual narrative entry contains LLM-generated narratives."""
        from babylon.ai.director import NarrativeDirector
        from babylon.ai.llm_provider import MockLLM

        corporate_text = "Order was restored after disturbances subsided."
        liberated_text = "The people rose up against oppression!"

        mock_llm = MockLLM(responses=[corporate_text, liberated_text])
        director = NarrativeDirector(use_llm=True, llm=mock_llm)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [uprising_event],
            }
        )

        director.on_tick(previous_state, new_state)

        entry = director.dual_narratives[1]
        assert entry["corporate"] == corporate_text
        assert entry["liberated"] == liberated_text

    def test_on_tick_calls_llm_twice_for_significant_event(
        self,
        initial_state: WorldState,
        uprising_event: UprisingEvent,
    ) -> None:
        """on_tick calls LLM twice for significant event (corporate + liberated)."""
        from babylon.ai.director import NarrativeDirector
        from babylon.ai.llm_provider import MockLLM

        mock_llm = MockLLM(responses=["Corporate narrative", "Liberated narrative"])
        director = NarrativeDirector(use_llm=True, llm=mock_llm)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [uprising_event],
            }
        )

        director.on_tick(previous_state, new_state)

        # Should have called generate() twice - once per perspective
        assert mock_llm.call_count == 2

    def test_on_tick_no_dual_narrative_without_llm(
        self,
        initial_state: WorldState,
        uprising_event: UprisingEvent,
    ) -> None:
        """on_tick does not populate dual_narratives when use_llm=False."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(use_llm=False)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [uprising_event],
            }
        )

        director.on_tick(previous_state, new_state)

        # No dual narratives without LLM enabled
        assert len(director.dual_narratives) == 0

    def test_on_tick_no_dual_narrative_for_non_significant_event(
        self,
        initial_state: WorldState,
    ) -> None:
        """on_tick does not populate dual_narratives for non-significant events."""
        from babylon.ai.director import NarrativeDirector
        from babylon.ai.llm_provider import MockLLM
        from babylon.models.events import TransmissionEvent

        # TransmissionEvent is not in SIGNIFICANT_EVENT_TYPES
        non_significant_event = TransmissionEvent(
            tick=1,
            target_id="C001",
            source_id="C002",
            delta=0.05,
            solidarity_strength=0.5,
        )

        mock_llm = MockLLM(default_response="Should not be called")
        director = NarrativeDirector(use_llm=True, llm=mock_llm)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [non_significant_event],
            }
        )

        director.on_tick(previous_state, new_state)

        # No dual narrative for non-significant events
        assert 1 not in director.dual_narratives
