"""Tests for MetricsCollector non-singleton behavior.

RED Phase: These tests define the contract that MetricsCollector
is no longer a singleton after Infrastructure Hardening (Spec 008).

Test Intent:
- T012: MetricsCollector() creates independent instances, not singletons
- Each instance has isolated state (counters, gauges, etc.)
- No shared class-level _instance variable
"""

from __future__ import annotations


class TestMetricsCollectorNotSingleton:
    """Test that MetricsCollector is no longer a singleton."""

    def test_two_instances_are_different_objects(self) -> None:
        """T012: MetricsCollector() returns different instances each time.

        SC-002 (implementation): After removing the singleton pattern,
        creating two MetricsCollector instances should return different
        objects, not the same instance.
        """
        from babylon.metrics.collector import MetricsCollector

        collector1 = MetricsCollector()
        collector2 = MetricsCollector()

        # They should be different objects (not the same singleton)
        assert collector1 is not collector2

    def test_instances_have_independent_state(self) -> None:
        """T012b: Two MetricsCollector instances have independent state.

        Verifies that counters recorded to one instance don't appear
        in another instance's summary.
        """
        from babylon.metrics.collector import MetricsCollector

        collector1 = MetricsCollector()
        collector2 = MetricsCollector()

        # Record to collector1 only
        collector1.increment("test_counter", 10)
        collector1.gauge("test_gauge", 42.0)

        # collector2 should have empty state
        summary1 = collector1.summary()
        summary2 = collector2.summary()

        assert summary1["counters"].get("test_counter", 0) == 10
        assert summary1["gauges"].get("test_gauge") == 42.0

        # collector2 should be independent
        assert summary2["counters"].get("test_counter", 0) == 0
        assert summary2["gauges"].get("test_gauge") is None

    def test_no_class_level_instance_variable(self) -> None:
        """T012c: MetricsCollector has no _instance class variable.

        After singleton removal, the _instance class variable should
        not exist or should be removed.
        """
        from babylon.metrics.collector import MetricsCollector

        # The _instance class variable should not exist after refactoring
        # This test will fail while singleton pattern exists
        assert not hasattr(MetricsCollector, "_instance") or MetricsCollector._instance is None

    def test_clear_only_affects_own_instance(self) -> None:
        """T012d: clear() only affects the instance it's called on.

        Verifies that clearing one collector doesn't affect another.
        """
        from babylon.metrics.collector import MetricsCollector

        collector1 = MetricsCollector()
        collector2 = MetricsCollector()

        # Record to both
        collector1.increment("counter", 5)
        collector2.increment("counter", 3)

        # Clear only collector1
        collector1.clear()

        # collector1 should be empty, collector2 should still have data
        assert collector1.summary()["counters"].get("counter", 0) == 0
        assert collector2.summary()["counters"].get("counter", 0) == 3
