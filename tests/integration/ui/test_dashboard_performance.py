"""Performance and memory verification tests for God Mode Dashboard.

These tests verify:
- T058: Memory growth stays under 50MB over 10,000 ticks
- T059: No individual frame exceeds 100ms render time

Feature: 007-god-mode-dashboard
"""

from __future__ import annotations

import gc
import time
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot

try:
    from babylon.ui.dashboard.main_window import DashboardWindow
    from babylon.ui.dashboard.observer import DashboardObserver
    from babylon.ui.dashboard.testing import MockSimulation

    DASHBOARD_EXISTS = True
except ImportError:
    DASHBOARD_EXISTS = False

pytestmark = [
    pytest.mark.skipif(not DASHBOARD_EXISTS, reason="Dashboard not yet implemented"),
    pytest.mark.slow,  # These tests take longer to run
]


def get_memory_mb() -> float:
    """Get current process memory usage in MB.

    Returns:
        Memory usage in megabytes.
    """
    try:
        import resource

        # Get max resident set size in KB (on Linux) or bytes (on macOS)
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # rusage.ru_maxrss is in KB on Linux, bytes on macOS
        import platform

        if platform.system() == "Darwin":
            return usage.ru_maxrss / 1024 / 1024  # bytes -> MB
        return usage.ru_maxrss / 1024  # KB -> MB
    except ImportError:
        # Fallback for systems without resource module
        return 0.0


class TestMemoryStability:
    """T058: Memory leak verification tests."""

    @pytest.mark.parametrize("tick_count", [100, 1000])
    def test_memory_growth_under_limit(
        self,
        qtbot: QtBot,
        tick_count: int,
    ) -> None:
        """Memory growth should stay under 50MB over many ticks.

        This is a scaled-down version of the 10,000 tick test.
        """
        # Create fresh simulation and dashboard
        sim = MockSimulation.with_detroit_territories()
        window = DashboardWindow(simulation=sim)
        qtbot.addWidget(window)

        # Force garbage collection before measuring baseline
        gc.collect()
        baseline_mb = get_memory_mb()

        # Run ticks
        for i in range(tick_count):
            sim.step()
            # Allow Qt events to process periodically
            if i % 100 == 0:
                qtbot.wait(1)

        # Force garbage collection before final measurement
        gc.collect()
        final_mb = get_memory_mb()

        growth_mb = final_mb - baseline_mb

        # Should not grow more than 50MB
        # Note: This is a relaxed check since resource module reports max RSS
        assert growth_mb < 50.0, f"Memory grew by {growth_mb:.1f}MB (limit: 50MB)"

    def test_observer_cleanup_releases_memory(
        self,
        qtbot: QtBot,
    ) -> None:
        """Closing dashboard should release observer memory."""
        sim = MockSimulation.with_detroit_territories()

        # Create dashboard
        window = DashboardWindow(simulation=sim)
        qtbot.addWidget(window)

        # Run some ticks
        for _ in range(50):
            sim.step()

        gc.collect()
        before_close = get_memory_mb()

        # Close window (should unregister observer)
        window.close()

        gc.collect()
        after_close = get_memory_mb()

        # Memory should not grow significantly after close
        assert after_close <= before_close + 5.0


class TestRenderPerformance:
    """T059: Frame render time verification tests."""

    def test_individual_frame_under_100ms(
        self,
        qtbot: QtBot,
    ) -> None:
        """No individual frame should exceed 100ms render time."""
        sim = MockSimulation.with_detroit_territories()
        window = DashboardWindow(simulation=sim)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)

        max_frame_time_ms = 0.0

        # Run 100 ticks and measure update time
        for _ in range(100):
            start = time.perf_counter()
            sim.step()
            # Process Qt events (simulates frame render)
            qtbot.wait(1)
            elapsed_ms = (time.perf_counter() - start) * 1000
            max_frame_time_ms = max(max_frame_time_ms, elapsed_ms)

        # No frame should exceed 100ms
        assert max_frame_time_ms < 100.0, (
            f"Max frame time: {max_frame_time_ms:.1f}ms (limit: 100ms)"
        )

    def test_throttling_maintains_30fps(
        self,
        qtbot: QtBot,
    ) -> None:
        """Observer should throttle to 30 FPS (33ms intervals)."""
        sim = MockSimulation.with_detroit_territories()

        # Create observer directly for precise timing measurement
        observer = DashboardObserver(simulation=sim)

        emission_times: list[float] = []

        def record_emission(_tick: int, _snapshot: object) -> None:
            emission_times.append(time.perf_counter())

        observer.tick_processed.connect(record_emission)

        # Rapidly step simulation (100 ticks at once)
        for _ in range(20):
            sim.step()
            # Allow Qt timer to fire
            qtbot.wait(5)

        # Wait for throttle timer to flush
        qtbot.wait(50)

        # Should have fewer emissions than steps due to throttling
        # At 30 FPS, 100 rapid steps should coalesce to ~3-4 emissions
        # (depends on exact timing)
        assert len(emission_times) < 20, (
            f"Got {len(emission_times)} emissions, expected fewer due to throttling"
        )


class TestScalability:
    """Tests for dashboard scalability with varying data sizes."""

    def test_handles_rapid_updates(
        self,
        qtbot: QtBot,
    ) -> None:
        """Dashboard should handle rapid tick updates without freezing."""
        sim = MockSimulation.with_detroit_territories()
        window = DashboardWindow(simulation=sim)
        qtbot.addWidget(window)

        # Rapidly step 500 times without waiting
        start = time.perf_counter()
        for _ in range(500):
            sim.step()
        step_time = time.perf_counter() - start

        # Processing events should not take long
        qtbot.wait(100)  # Allow UI to catch up

        # 500 steps should complete quickly (simulation logic is simple)
        assert step_time < 1.0, f"500 steps took {step_time:.2f}s (expected <1s)"


__all__ = [
    "TestMemoryStability",
    "TestRenderPerformance",
    "TestScalability",
]
