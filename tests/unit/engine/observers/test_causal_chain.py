"""Tests for CausalChainObserver - The Shock Doctrine detector.

TDD Red Phase: These tests define the contract for detecting the
"Shock Doctrine" pattern (Crash -> Austerity -> Radicalization) and
outputting structured JSON NarrativeFrame.

The CausalChainObserver detects:
- Tick N: Pool drop > 20% (ECONOMIC_SHOCK)
- Tick N+1: Wage decrease (AUSTERITY_RESPONSE)
- Tick N+2: P(Revolution) increase (RADICALIZATION)

Design Decisions:
- Buffer size: 5 ticks (deque with maxlen)
- Output: JSON with [NARRATIVE_JSON] prefix at WARNING level
- Pattern: "Shock Doctrine" - the 2008 financial crisis pattern
"""

from __future__ import annotations

import json
import logging
from collections import deque

import pytest

from babylon.engine.observer import SimulationObserver
from babylon.models import SimulationConfig, WorldState
from babylon.models.entities.economy import GlobalEconomy
from babylon.models.entities.social_class import SocialClass
from babylon.models.enums import SocialRole

# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


def create_state(
    tick: int,
    pool: float = 100.0,
    wage: float = 0.20,
    p_rev: float = 0.30,
) -> WorldState:
    """Create minimal WorldState with specified economic metrics.

    Args:
        tick: The tick number for this state.
        pool: Imperial rent pool value (default 100.0).
        wage: Current super-wage rate (default 0.20).
        p_rev: P(Revolution) probability (default 0.30).

    Returns:
        WorldState with customized economy and one entity.
    """
    economy = GlobalEconomy(
        imperial_rent_pool=pool,
        current_super_wage_rate=wage,
    )
    # Create one entity with p_revolution set
    # ID must match pattern ^C[0-9]{3}$
    entity = SocialClass(
        id="C001",
        name="Proletariat",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        p_revolution=p_rev,
    )
    return WorldState(tick=tick, economy=economy, entities={"C001": entity})


# =============================================================================
# TEST PROTOCOL COMPLIANCE
# =============================================================================


@pytest.mark.unit
class TestCausalChainProtocol:
    """Tests for CausalChainObserver protocol compliance."""

    def test_implements_observer_protocol(self) -> None:
        """CausalChainObserver satisfies SimulationObserver protocol."""
        from babylon.engine.observers.causal import CausalChainObserver

        observer = CausalChainObserver()
        assert isinstance(observer, SimulationObserver)

    def test_name_property_returns_correct_name(self) -> None:
        """Name property returns 'CausalChainObserver'."""
        from babylon.engine.observers.causal import CausalChainObserver

        observer = CausalChainObserver()
        assert observer.name == "CausalChainObserver"


# =============================================================================
# TEST HISTORY BUFFER
# =============================================================================


@pytest.mark.unit
class TestHistoryBuffer:
    """Tests for history buffer management."""

    def test_history_buffer_uses_deque_with_maxlen_5(self) -> None:
        """History buffer is a deque with maxlen=5."""
        from babylon.engine.observers.causal import CausalChainObserver

        observer = CausalChainObserver()
        assert isinstance(observer._history, deque)
        assert observer._history.maxlen == 5

    def test_on_simulation_start_clears_buffer(self) -> None:
        """on_simulation_start clears buffer and records initial state."""
        from babylon.engine.observers.causal import CausalChainObserver, TickSnapshot

        observer = CausalChainObserver()
        # Add some history manually
        observer._history.append(TickSnapshot(0, 100.0, 0.2, 0.3))
        observer._history.append(TickSnapshot(1, 90.0, 0.2, 0.3))
        assert len(observer._history) == 2

        # on_simulation_start should clear and record initial
        state = create_state(tick=0)
        observer.on_simulation_start(state, SimulationConfig())
        # Should be cleared then have one entry (the initial state)
        assert len(observer._history) == 1


# =============================================================================
# TEST SHOCK DOCTRINE DETECTION
# =============================================================================


@pytest.mark.unit
class TestShockDoctrineDetection:
    """Tests for detecting the Shock Doctrine pattern."""

    def test_detects_shock_doctrine_pattern(self, caplog: pytest.LogCaptureFixture) -> None:
        """The 2008 Crash scenario - detect Crash -> Austerity -> Radicalization.

        Pattern:
        - Tick 10: Pre-crash (stable baseline)
        - Tick 11: Crash (pool drops 30%)
        - Tick 12: Austerity (wage cut) + Radicalization (p_rev increase)
        """
        from babylon.engine.observers.causal import CausalChainObserver

        observer = CausalChainObserver()

        # Tick 10: Pre-crash (stable)
        state_10 = create_state(tick=10, pool=100.0, wage=0.20, p_rev=0.30)
        # Tick 11: Crash (pool drops 30%)
        state_11 = create_state(tick=11, pool=70.0, wage=0.20, p_rev=0.30)
        # Tick 12: Austerity + Radicalization
        state_12 = create_state(tick=12, pool=70.0, wage=0.15, p_rev=0.45)

        observer.on_simulation_start(state_10, SimulationConfig())
        observer.on_tick(state_10, state_11)

        with caplog.at_level(logging.WARNING):
            observer.on_tick(state_11, state_12)

        assert "[NARRATIVE_JSON]" in caplog.text

    def test_no_detection_without_pool_crash(self, caplog: pytest.LogCaptureFixture) -> None:
        """No pattern if pool doesn't crash (only 10% drop).

        A 10% drop is below the 20% threshold and should NOT trigger.
        """
        from babylon.engine.observers.causal import CausalChainObserver

        observer = CausalChainObserver()

        state_0 = create_state(tick=0, pool=100.0, wage=0.20, p_rev=0.30)
        state_1 = create_state(tick=1, pool=90.0, wage=0.20, p_rev=0.30)  # Only 10% drop
        state_2 = create_state(tick=2, pool=90.0, wage=0.15, p_rev=0.45)

        observer.on_simulation_start(state_0, SimulationConfig())
        observer.on_tick(state_0, state_1)

        with caplog.at_level(logging.WARNING):
            observer.on_tick(state_1, state_2)

        assert "[NARRATIVE_JSON]" not in caplog.text

    def test_no_detection_without_wage_cut(self, caplog: pytest.LogCaptureFixture) -> None:
        """No pattern if wages don't decrease.

        Austerity requires wage decrease. Wage increase disqualifies pattern.
        """
        from babylon.engine.observers.causal import CausalChainObserver

        observer = CausalChainObserver()

        state_0 = create_state(tick=0, pool=100.0, wage=0.20, p_rev=0.30)
        state_1 = create_state(tick=1, pool=70.0, wage=0.20, p_rev=0.30)  # Pool crash
        state_2 = create_state(tick=2, pool=70.0, wage=0.25, p_rev=0.45)  # Wage UP

        observer.on_simulation_start(state_0, SimulationConfig())
        observer.on_tick(state_0, state_1)

        with caplog.at_level(logging.WARNING):
            observer.on_tick(state_1, state_2)

        assert "[NARRATIVE_JSON]" not in caplog.text

    def test_no_detection_without_radicalization(self, caplog: pytest.LogCaptureFixture) -> None:
        """No pattern if p_revolution doesn't increase.

        Radicalization requires p_rev increase. Decrease disqualifies pattern.
        """
        from babylon.engine.observers.causal import CausalChainObserver

        observer = CausalChainObserver()

        state_0 = create_state(tick=0, pool=100.0, wage=0.20, p_rev=0.30)
        state_1 = create_state(tick=1, pool=70.0, wage=0.20, p_rev=0.30)  # Pool crash
        state_2 = create_state(tick=2, pool=70.0, wage=0.15, p_rev=0.25)  # p_rev DOWN

        observer.on_simulation_start(state_0, SimulationConfig())
        observer.on_tick(state_0, state_1)

        with caplog.at_level(logging.WARNING):
            observer.on_tick(state_1, state_2)

        assert "[NARRATIVE_JSON]" not in caplog.text


# =============================================================================
# TEST JSON FRAME STRUCTURE
# =============================================================================


@pytest.mark.unit
class TestJsonFrameStructure:
    """Tests for JSON NarrativeFrame output structure."""

    def test_frame_is_valid_json(self, caplog: pytest.LogCaptureFixture) -> None:
        """Output can be parsed as valid JSON."""
        from babylon.engine.observers.causal import CausalChainObserver

        observer = CausalChainObserver()

        state_0 = create_state(tick=0, pool=100.0, wage=0.20, p_rev=0.30)
        state_1 = create_state(tick=1, pool=70.0, wage=0.20, p_rev=0.30)
        state_2 = create_state(tick=2, pool=70.0, wage=0.15, p_rev=0.45)

        observer.on_simulation_start(state_0, SimulationConfig())
        observer.on_tick(state_0, state_1)

        with caplog.at_level(logging.WARNING):
            observer.on_tick(state_1, state_2)

        # Extract and parse JSON
        json_str = caplog.text.split("[NARRATIVE_JSON]")[1].strip()
        frame = json.loads(json_str)  # Should not raise
        assert isinstance(frame, dict)

    def test_first_node_type_is_economic_shock(self, caplog: pytest.LogCaptureFixture) -> None:
        """First node in causal graph has type ECONOMIC_SHOCK."""
        from babylon.engine.observers.causal import CausalChainObserver

        observer = CausalChainObserver()

        state_0 = create_state(tick=0, pool=100.0, wage=0.20, p_rev=0.30)
        state_1 = create_state(tick=1, pool=70.0, wage=0.20, p_rev=0.30)
        state_2 = create_state(tick=2, pool=70.0, wage=0.15, p_rev=0.45)

        observer.on_simulation_start(state_0, SimulationConfig())
        observer.on_tick(state_0, state_1)

        with caplog.at_level(logging.WARNING):
            observer.on_tick(state_1, state_2)

        json_str = caplog.text.split("[NARRATIVE_JSON]")[1].strip()
        frame = json.loads(json_str)

        assert frame["causal_graph"]["nodes"][0]["type"] == "ECONOMIC_SHOCK"

    def test_first_edge_relation_is_triggers_reaction(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """First edge has relation TRIGGERS_REACTION."""
        from babylon.engine.observers.causal import CausalChainObserver

        observer = CausalChainObserver()

        state_0 = create_state(tick=0, pool=100.0, wage=0.20, p_rev=0.30)
        state_1 = create_state(tick=1, pool=70.0, wage=0.20, p_rev=0.30)
        state_2 = create_state(tick=2, pool=70.0, wage=0.15, p_rev=0.45)

        observer.on_simulation_start(state_0, SimulationConfig())
        observer.on_tick(state_0, state_1)

        with caplog.at_level(logging.WARNING):
            observer.on_tick(state_1, state_2)

        json_str = caplog.text.split("[NARRATIVE_JSON]")[1].strip()
        frame = json.loads(json_str)

        assert frame["causal_graph"]["edges"][0]["relation"] == "TRIGGERS_REACTION"


# =============================================================================
# TEST BUILD FRAME HELPER
# =============================================================================


@pytest.mark.unit
class TestBuildFrameHelper:
    """Tests for _build_frame internal helper."""

    def test_build_frame_returns_dict(self) -> None:
        """_build_frame returns a dictionary."""
        from babylon.engine.observers.causal import CausalChainObserver, TickSnapshot

        observer = CausalChainObserver()
        crash = TickSnapshot(tick=0, pool=100.0, wage=0.20, p_rev=0.30)
        austerity = TickSnapshot(tick=1, pool=70.0, wage=0.20, p_rev=0.30)
        radical = TickSnapshot(tick=2, pool=70.0, wage=0.15, p_rev=0.45)

        frame = observer._build_frame(crash, austerity, radical)
        assert isinstance(frame, dict)

    def test_build_frame_has_three_nodes(self) -> None:
        """Frame has exactly 3 nodes."""
        from babylon.engine.observers.causal import CausalChainObserver, TickSnapshot

        observer = CausalChainObserver()
        crash = TickSnapshot(tick=0, pool=100.0, wage=0.20, p_rev=0.30)
        austerity = TickSnapshot(tick=1, pool=70.0, wage=0.20, p_rev=0.30)
        radical = TickSnapshot(tick=2, pool=70.0, wage=0.15, p_rev=0.45)

        frame = observer._build_frame(crash, austerity, radical)
        assert len(frame["causal_graph"]["nodes"]) == 3

    def test_build_frame_has_two_edges(self) -> None:
        """Frame has exactly 2 edges."""
        from babylon.engine.observers.causal import CausalChainObserver, TickSnapshot

        observer = CausalChainObserver()
        crash = TickSnapshot(tick=0, pool=100.0, wage=0.20, p_rev=0.30)
        austerity = TickSnapshot(tick=1, pool=70.0, wage=0.20, p_rev=0.30)
        radical = TickSnapshot(tick=2, pool=70.0, wage=0.15, p_rev=0.45)

        frame = observer._build_frame(crash, austerity, radical)
        assert len(frame["causal_graph"]["edges"]) == 2


# =============================================================================
# TEST LIFECYCLE HOOKS
# =============================================================================


@pytest.mark.unit
class TestLifecycleHooks:
    """Tests for observer lifecycle hooks."""

    def test_on_simulation_end_is_noop(self) -> None:
        """on_simulation_end doesn't raise."""
        from babylon.engine.observers.causal import CausalChainObserver

        observer = CausalChainObserver()
        state = create_state(tick=10)
        observer.on_simulation_end(state)  # Should not raise


# =============================================================================
# TEST THRESHOLD CONSTANTS
# =============================================================================


@pytest.mark.unit
class TestThresholdConstants:
    """Tests for threshold constants."""

    def test_crash_threshold_is_negative_20_percent(self) -> None:
        """CRASH_THRESHOLD is -0.20 (20% drop)."""
        from babylon.engine.observers.causal import CausalChainObserver

        assert CausalChainObserver.CRASH_THRESHOLD == -0.20

    def test_buffer_size_is_5(self) -> None:
        """BUFFER_SIZE is 5."""
        from babylon.engine.observers.causal import CausalChainObserver

        assert CausalChainObserver.BUFFER_SIZE == 5


# =============================================================================
# TEST JSON SCHEMA VALIDATION
# =============================================================================


@pytest.mark.unit
class TestJsonSchemaValidation:
    """Tests for NarrativeFrame JSON schema compliance."""

    def test_shock_doctrine_output_validates_against_schema(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """CausalChainObserver output validates against NarrativeFrame schema."""
        from babylon.engine.observers.causal import CausalChainObserver
        from babylon.engine.observers.schema_validator import validate_narrative_frame

        observer = CausalChainObserver()

        state_0 = create_state(tick=0, pool=100.0, wage=0.20, p_rev=0.30)
        state_1 = create_state(tick=1, pool=70.0, wage=0.20, p_rev=0.30)
        state_2 = create_state(tick=2, pool=70.0, wage=0.15, p_rev=0.45)

        observer.on_simulation_start(state_0, SimulationConfig())
        observer.on_tick(state_0, state_1)

        with caplog.at_level(logging.WARNING):
            observer.on_tick(state_1, state_2)

        # Extract and validate against schema
        json_str = caplog.text.split("[NARRATIVE_JSON]")[1].strip()
        frame = json.loads(json_str)

        errors = validate_narrative_frame(frame)
        assert errors == [], f"Schema validation errors: {errors}"

    def test_build_frame_output_validates_against_schema(self) -> None:
        """_build_frame output validates against NarrativeFrame schema."""
        from babylon.engine.observers.causal import CausalChainObserver, TickSnapshot
        from babylon.engine.observers.schema_validator import (
            is_valid_narrative_frame,
            validate_narrative_frame,
        )

        observer = CausalChainObserver()
        crash = TickSnapshot(tick=0, pool=100.0, wage=0.20, p_rev=0.30)
        austerity = TickSnapshot(tick=1, pool=70.0, wage=0.20, p_rev=0.30)
        radical = TickSnapshot(tick=2, pool=70.0, wage=0.15, p_rev=0.45)

        frame = observer._build_frame(crash, austerity, radical)

        # Use both validation methods
        assert is_valid_narrative_frame(frame) is True
        errors = validate_narrative_frame(frame)
        assert errors == [], f"Schema validation errors: {errors}"
