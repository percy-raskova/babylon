"""Tests for get_multiverse_scenarios() factory function.

RED Phase: These tests will fail initially until get_multiverse_scenarios() is implemented.
"""

from __future__ import annotations

import pytest

# Imports will fail in RED phase - this is expected
from babylon.engine.scenarios import get_multiverse_scenarios
from babylon.models.scenario import ScenarioConfig


class TestMultiverseFactory:
    """Test get_multiverse_scenarios() factory function."""

    @pytest.mark.unit
    def test_returns_list_of_scenario_configs(self) -> None:
        """Test that get_multiverse_scenarios returns a list of ScenarioConfig."""
        scenarios = get_multiverse_scenarios()

        assert isinstance(scenarios, list)
        for scenario in scenarios:
            assert isinstance(scenario, ScenarioConfig)

    @pytest.mark.unit
    def test_returns_exactly_eight_scenarios(self) -> None:
        """Test that get_multiverse_scenarios returns exactly 2^3 = 8 permutations."""
        scenarios = get_multiverse_scenarios()

        assert len(scenarios) == 8

    @pytest.mark.unit
    def test_all_names_unique(self) -> None:
        """Test that all scenario names are unique."""
        scenarios = get_multiverse_scenarios()
        names = [s.name for s in scenarios]

        assert len(names) == len(set(names)), "Scenario names must be unique"

    @pytest.mark.unit
    def test_superwage_multiplier_values(self) -> None:
        """Test that superwage_multiplier has exactly two values: 0.3 (Low) and 1.5 (High)."""
        scenarios = get_multiverse_scenarios()
        superwage_multipliers = {s.superwage_multiplier for s in scenarios}

        assert superwage_multipliers == {0.3, 1.5}

    @pytest.mark.unit
    def test_solidarity_index_values(self) -> None:
        """Test that solidarity_index has exactly two values: 0.2 (Low) and 0.8 (High)."""
        scenarios = get_multiverse_scenarios()
        solidarity_indices = {s.solidarity_index for s in scenarios}

        assert solidarity_indices == {0.2, 0.8}

    @pytest.mark.unit
    def test_repression_capacity_values(self) -> None:
        """Test that repression_capacity has exactly two values: 0.2 (Low) and 0.8 (High)."""
        scenarios = get_multiverse_scenarios()
        repression_capacities = {s.repression_capacity for s in scenarios}

        assert repression_capacities == {0.2, 0.8}

    @pytest.mark.unit
    def test_all_permutations_present(self) -> None:
        """Test that all 8 permutations of High/Low values are present."""
        scenarios = get_multiverse_scenarios()

        # Create set of (superwage, solidarity, repression) tuples
        combinations = {
            (s.superwage_multiplier, s.solidarity_index, s.repression_capacity) for s in scenarios
        }

        # Expected: all 8 combinations of {0.3, 1.5} x {0.2, 0.8} x {0.2, 0.8}
        expected = set()
        for sw in [0.3, 1.5]:
            for sol in [0.2, 0.8]:
                for rep in [0.2, 0.8]:
                    expected.add((sw, sol, rep))

        assert combinations == expected

    @pytest.mark.unit
    def test_naming_convention_high_sw(self) -> None:
        """Test that scenarios with superwage_multiplier=1.5 have 'HighSW' in name."""
        scenarios = get_multiverse_scenarios()
        high_sw = [s for s in scenarios if s.superwage_multiplier == 1.5]

        for scenario in high_sw:
            assert "HighSW" in scenario.name or "High" in scenario.name

    @pytest.mark.unit
    def test_naming_convention_low_sw(self) -> None:
        """Test that scenarios with superwage_multiplier=0.3 have 'LowSW' in name."""
        scenarios = get_multiverse_scenarios()
        low_sw = [s for s in scenarios if s.superwage_multiplier == 0.3]

        for scenario in low_sw:
            assert "LowSW" in scenario.name or "Low" in scenario.name

    @pytest.mark.unit
    def test_deterministic_output(self) -> None:
        """Test that get_multiverse_scenarios returns same results on repeated calls."""
        scenarios1 = get_multiverse_scenarios()
        scenarios2 = get_multiverse_scenarios()

        # Same length
        assert len(scenarios1) == len(scenarios2)

        # Same content (compare by model_dump for exact equality)
        for s1, s2 in zip(scenarios1, scenarios2, strict=True):
            assert s1.model_dump() == s2.model_dump()

    @pytest.mark.unit
    def test_extreme_scenarios_present(self) -> None:
        """Test that both extreme scenarios are present."""
        scenarios = get_multiverse_scenarios()

        # Find the "stable" scenario: High SW + Low Solidarity + High Repression
        stable = [
            s
            for s in scenarios
            if s.superwage_multiplier == 1.5
            and s.solidarity_index == 0.2
            and s.repression_capacity == 0.8
        ]
        assert len(stable) == 1, "Should have exactly one stable scenario"

        # Find the "collapse" scenario: Low SW + High Solidarity + Low Repression
        collapse = [
            s
            for s in scenarios
            if s.superwage_multiplier == 0.3
            and s.solidarity_index == 0.8
            and s.repression_capacity == 0.2
        ]
        assert len(collapse) == 1, "Should have exactly one collapse scenario"
