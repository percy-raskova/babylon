"""Tests for EconomyMonitor observer (Sprint 3.1: The Economic Seismograph).

TDD Red Phase: These tests define the contract for detecting economic crises
by monitoring sudden drops in the imperial_rent_pool.

The EconomyMonitor detects sudden drops (>20%) in imperial_rent_pool and
logs [CRISIS_DETECTED] warnings to enable AI narrative generation.

Design Decisions:
- Threshold: -20% (CRISIS_THRESHOLD = -0.20)
- Boundary: Exactly -20% triggers crisis (>= comparison)
- Division by zero: Zero previous pool = no crisis (avoid NaN/Inf)
- Log format: [CRISIS_DETECTED] with percentage drop
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from babylon.models import SimulationConfig, WorldState
from babylon.models.entities.economy import GlobalEconomy

if TYPE_CHECKING:
    pass


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def config() -> SimulationConfig:
    """Create default simulation config."""
    return SimulationConfig()


def create_state_with_pool(pool: float, tick: int = 0) -> WorldState:
    """Create a minimal WorldState with specified imperial_rent_pool.

    Args:
        pool: The imperial_rent_pool value.
        tick: The tick number (default 0).

    Returns:
        WorldState with customized economy.imperial_rent_pool.
    """
    economy = GlobalEconomy(imperial_rent_pool=pool)
    return WorldState(tick=tick, economy=economy)


# =============================================================================
# TEST PROTOCOL COMPLIANCE
# =============================================================================


@pytest.mark.unit
class TestEconomyMonitorProtocol:
    """Tests for EconomyMonitor protocol compliance."""

    def test_implements_observer_protocol(self) -> None:
        """EconomyMonitor satisfies SimulationObserver protocol."""
        from babylon.engine.observer import SimulationObserver
        from babylon.engine.observers.economic import EconomyMonitor

        monitor = EconomyMonitor()
        assert isinstance(monitor, SimulationObserver)

    def test_name_property_returns_economy_monitor(self) -> None:
        """Name property returns 'EconomyMonitor'."""
        from babylon.engine.observers.economic import EconomyMonitor

        monitor = EconomyMonitor()
        assert monitor.name == "EconomyMonitor"


# =============================================================================
# TEST CRISIS DETECTION
# =============================================================================


@pytest.mark.unit
class TestCrisisDetection:
    """Tests for economic crisis detection logic."""

    def test_detects_crisis_on_exact_20_percent_drop(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """100 -> 80 = -20% triggers crisis (boundary condition).

        The threshold is >= -0.20, so exactly -20% should trigger.
        """
        from babylon.engine.observers.economic import EconomyMonitor

        monitor = EconomyMonitor()
        prev_state = create_state_with_pool(100.0, tick=0)
        new_state = create_state_with_pool(80.0, tick=1)

        with caplog.at_level(logging.WARNING):
            monitor.on_tick(prev_state, new_state)

        assert "[CRISIS_DETECTED]" in caplog.text

    def test_detects_crisis_on_50_percent_drop(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """100 -> 50 = -50% triggers crisis (severe drop).

        A 50% drop is well past the threshold and should definitely trigger.
        """
        from babylon.engine.observers.economic import EconomyMonitor

        monitor = EconomyMonitor()
        prev_state = create_state_with_pool(100.0, tick=0)
        new_state = create_state_with_pool(50.0, tick=1)

        with caplog.at_level(logging.WARNING):
            monitor.on_tick(prev_state, new_state)

        assert "[CRISIS_DETECTED]" in caplog.text

    def test_no_crisis_on_19_percent_drop(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """100 -> 81 = -19% does NOT trigger crisis.

        A 19% drop is below the threshold and should NOT trigger.
        """
        from babylon.engine.observers.economic import EconomyMonitor

        monitor = EconomyMonitor()
        prev_state = create_state_with_pool(100.0, tick=0)
        new_state = create_state_with_pool(81.0, tick=1)

        with caplog.at_level(logging.WARNING):
            monitor.on_tick(prev_state, new_state)

        assert "[CRISIS_DETECTED]" not in caplog.text

    def test_no_crisis_on_pool_increase(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """100 -> 150 = +50% does NOT trigger crisis.

        An increase in the pool should never trigger a crisis.
        """
        from babylon.engine.observers.economic import EconomyMonitor

        monitor = EconomyMonitor()
        prev_state = create_state_with_pool(100.0, tick=0)
        new_state = create_state_with_pool(150.0, tick=1)

        with caplog.at_level(logging.WARNING):
            monitor.on_tick(prev_state, new_state)

        assert "[CRISIS_DETECTED]" not in caplog.text

    def test_no_crisis_on_stable_pool(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """100 -> 100 = 0% does NOT trigger crisis.

        No change in the pool should not trigger a crisis.
        """
        from babylon.engine.observers.economic import EconomyMonitor

        monitor = EconomyMonitor()
        prev_state = create_state_with_pool(100.0, tick=0)
        new_state = create_state_with_pool(100.0, tick=1)

        with caplog.at_level(logging.WARNING):
            monitor.on_tick(prev_state, new_state)

        assert "[CRISIS_DETECTED]" not in caplog.text

    def test_crisis_log_contains_percentage(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Log message includes percentage drop.

        The crisis message should contain the actual percentage drop
        so AI can understand the severity.
        """
        from babylon.engine.observers.economic import EconomyMonitor

        monitor = EconomyMonitor()
        prev_state = create_state_with_pool(100.0, tick=0)
        new_state = create_state_with_pool(70.0, tick=1)  # -30% drop

        with caplog.at_level(logging.WARNING):
            monitor.on_tick(prev_state, new_state)

        # Should contain percentage (30% or -30%)
        assert "30" in caplog.text

    def test_handles_zero_previous_pool(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Avoid division by zero when prev_pool is 0.

        When the previous pool is zero, we cannot calculate percentage change.
        This should NOT trigger a crisis and should NOT crash.
        """
        from babylon.engine.observers.economic import EconomyMonitor

        monitor = EconomyMonitor()
        prev_state = create_state_with_pool(0.0, tick=0)
        new_state = create_state_with_pool(50.0, tick=1)

        # Should not raise and should not trigger crisis
        with caplog.at_level(logging.WARNING):
            monitor.on_tick(prev_state, new_state)

        assert "[CRISIS_DETECTED]" not in caplog.text

    def test_handles_zero_to_zero_transition(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Handle 0 -> 0 transition gracefully.

        Both previous and new pool at zero should not crash or trigger.
        """
        from babylon.engine.observers.economic import EconomyMonitor

        monitor = EconomyMonitor()
        prev_state = create_state_with_pool(0.0, tick=0)
        new_state = create_state_with_pool(0.0, tick=1)

        # Should not raise and should not trigger crisis
        with caplog.at_level(logging.WARNING):
            monitor.on_tick(prev_state, new_state)

        assert "[CRISIS_DETECTED]" not in caplog.text

    def test_small_pool_values_detect_crisis(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Crisis detection works with small pool values.

        10 -> 5 = -50% should trigger crisis even with small absolute values.
        """
        from babylon.engine.observers.economic import EconomyMonitor

        monitor = EconomyMonitor()
        prev_state = create_state_with_pool(10.0, tick=0)
        new_state = create_state_with_pool(5.0, tick=1)

        with caplog.at_level(logging.WARNING):
            monitor.on_tick(prev_state, new_state)

        assert "[CRISIS_DETECTED]" in caplog.text


# =============================================================================
# TEST LIFECYCLE HOOKS
# =============================================================================


@pytest.mark.unit
class TestLifecycleHooks:
    """Tests for observer lifecycle hooks (no-ops)."""

    def test_on_simulation_start_is_noop(self, config: SimulationConfig) -> None:
        """on_simulation_start doesn't raise.

        The EconomyMonitor does not need to do anything on simulation start.
        """
        from babylon.engine.observers.economic import EconomyMonitor

        monitor = EconomyMonitor()
        initial_state = create_state_with_pool(100.0)

        # Should not raise
        monitor.on_simulation_start(initial_state, config)

    def test_on_simulation_end_is_noop(self) -> None:
        """on_simulation_end doesn't raise.

        The EconomyMonitor does not need to do anything on simulation end.
        """
        from babylon.engine.observers.economic import EconomyMonitor

        monitor = EconomyMonitor()
        final_state = create_state_with_pool(100.0, tick=10)

        # Should not raise
        monitor.on_simulation_end(final_state)


# =============================================================================
# TEST CUSTOM LOGGER
# =============================================================================


@pytest.mark.unit
class TestCustomLogger:
    """Tests for custom logger injection."""

    def test_accepts_custom_logger(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """EconomyMonitor accepts custom logger in constructor.

        This allows testing isolation and custom log routing.
        """
        from babylon.engine.observers.economic import EconomyMonitor

        custom_logger = logging.getLogger("custom.test.logger")
        monitor = EconomyMonitor(logger=custom_logger)

        prev_state = create_state_with_pool(100.0, tick=0)
        new_state = create_state_with_pool(50.0, tick=1)

        with caplog.at_level(logging.WARNING, logger="custom.test.logger"):
            monitor.on_tick(prev_state, new_state)

        # Should use custom logger
        assert "[CRISIS_DETECTED]" in caplog.text


# =============================================================================
# TEST THRESHOLD CONSTANT
# =============================================================================


@pytest.mark.unit
class TestThresholdConstant:
    """Tests for crisis threshold constant."""

    def test_crisis_threshold_is_negative_20_percent(self) -> None:
        """CRISIS_THRESHOLD is -0.20 (20% drop)."""
        from babylon.engine.observers.economic import EconomyMonitor

        assert EconomyMonitor.CRISIS_THRESHOLD == -0.20
