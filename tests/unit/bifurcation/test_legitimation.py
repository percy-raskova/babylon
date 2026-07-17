"""Tests for the legitimation crisis amplifier (US7, Feature 033).

The legitimation amplifier scales crisis intensity inversely with
population-weighted mean legitimation across territories. At full
legitimation (1.0), the amplifier is 1.0 (no amplification). At zero
legitimation, the amplifier equals ``legitimation_amplifier_scale`` (default 2.0).

Formula:
    amplifier = 1.0 + (1.0 - mean_legitimation) * (scale - 1.0)

Where:
    mean_legitimation = pop-weighted mean of territory legitimation_index
    scale = BifurcationDefines.legitimation_amplifier_scale

See Also:
    :mod:`babylon.domain.bifurcation.legitimation`: Implementation.
    ``specs/033-bifurcation-topology/spec.md``: US7 specification.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import BifurcationDefines
from babylon.domain.bifurcation.legitimation import compute_legitimation_amplifier
from babylon.topology.graph import BabylonGraph


@pytest.mark.unit
class TestLegitimationAmplifierBasic:
    """Basic amplifier calculations with single territories."""

    def test_high_legitimation_near_unity(self, bifurcation_defines: BifurcationDefines) -> None:
        """High legitimation (0.8) yields amplifier close to 1.0.

        amplifier = 1.0 + (1.0 - 0.8) * (2.0 - 1.0) = 1.0 + 0.2 = 1.2
        """
        G: BabylonGraph = BabylonGraph()
        G.add_node(
            "T001",
            _node_type="territory",
            legitimation_index=0.8,
            population=1000,
        )

        result = compute_legitimation_amplifier(G, bifurcation_defines)

        assert result == pytest.approx(1.2)

    def test_low_legitimation_amplifies(self, bifurcation_defines: BifurcationDefines) -> None:
        """Low legitimation (0.2) yields amplifier significantly above 1.0.

        amplifier = 1.0 + (1.0 - 0.2) * (2.0 - 1.0) = 1.0 + 0.8 = 1.8
        """
        G: BabylonGraph = BabylonGraph()
        G.add_node(
            "T001",
            _node_type="territory",
            legitimation_index=0.2,
            population=1000,
        )

        result = compute_legitimation_amplifier(G, bifurcation_defines)

        assert result == pytest.approx(1.8)

    def test_zero_legitimation_gives_max_scale(
        self, bifurcation_defines: BifurcationDefines
    ) -> None:
        """Zero legitimation yields amplifier = legitimation_amplifier_scale.

        amplifier = 1.0 + (1.0 - 0.0) * (2.0 - 1.0) = 1.0 + 1.0 = 2.0
        """
        G: BabylonGraph = BabylonGraph()
        G.add_node(
            "T001",
            _node_type="territory",
            legitimation_index=0.0,
            population=500,
        )

        result = compute_legitimation_amplifier(G, bifurcation_defines)

        assert result == pytest.approx(2.0)
        assert result == pytest.approx(bifurcation_defines.legitimation_amplifier_scale)

    def test_full_legitimation_no_amplification(
        self, bifurcation_defines: BifurcationDefines
    ) -> None:
        """Full legitimation (1.0) yields amplifier = 1.0 (no amplification).

        amplifier = 1.0 + (1.0 - 1.0) * (2.0 - 1.0) = 1.0 + 0.0 = 1.0
        """
        G: BabylonGraph = BabylonGraph()
        G.add_node(
            "T001",
            _node_type="territory",
            legitimation_index=1.0,
            population=1000,
        )

        result = compute_legitimation_amplifier(G, bifurcation_defines)

        assert result == pytest.approx(1.0)


@pytest.mark.unit
class TestLegitimationAmplifierPopulationWeighted:
    """Population-weighted mean across multiple territories."""

    def test_population_weighted_mean(self, bifurcation_defines: BifurcationDefines) -> None:
        """Population-weighted mean with unequal populations.

        T001: pop=100, legitimation=0.8 -> contribution = 100 * 0.8 = 80
        T002: pop=300, legitimation=0.2 -> contribution = 300 * 0.2 = 60
        weighted_mean = (80 + 60) / (100 + 300) = 140 / 400 = 0.35
        amplifier = 1.0 + (1.0 - 0.35) * (2.0 - 1.0) = 1.0 + 0.65 = 1.65
        """
        G: BabylonGraph = BabylonGraph()
        G.add_node(
            "T001",
            _node_type="territory",
            legitimation_index=0.8,
            population=100,
        )
        G.add_node(
            "T002",
            _node_type="territory",
            legitimation_index=0.2,
            population=300,
        )

        result = compute_legitimation_amplifier(G, bifurcation_defines)

        # Verify weighted mean
        expected_mean = (100 * 0.8 + 300 * 0.2) / (100 + 300)
        assert expected_mean == pytest.approx(0.35)
        expected_amplifier = 1.0 + (1.0 - expected_mean) * (
            bifurcation_defines.legitimation_amplifier_scale - 1.0
        )
        assert result == pytest.approx(expected_amplifier)
        assert result == pytest.approx(1.65)

    def test_equal_population_equal_weights(self, bifurcation_defines: BifurcationDefines) -> None:
        """Equal populations produce simple arithmetic mean.

        T001: pop=500, legitimation=0.6
        T002: pop=500, legitimation=0.4
        weighted_mean = (500*0.6 + 500*0.4) / (500+500) = 500 / 1000 = 0.5
        amplifier = 1.0 + (1.0 - 0.5) * 1.0 = 1.5
        """
        G: BabylonGraph = BabylonGraph()
        G.add_node(
            "T001",
            _node_type="territory",
            legitimation_index=0.6,
            population=500,
        )
        G.add_node(
            "T002",
            _node_type="territory",
            legitimation_index=0.4,
            population=500,
        )

        result = compute_legitimation_amplifier(G, bifurcation_defines)

        assert result == pytest.approx(1.5)


@pytest.mark.unit
class TestLegitimationAmplifierEdgeCases:
    """Edge cases and graceful degradation."""

    def test_no_territories_returns_unity(self, bifurcation_defines: BifurcationDefines) -> None:
        """Empty graph returns amplifier = 1.0 (graceful degradation)."""
        G: BabylonGraph = BabylonGraph()

        result = compute_legitimation_amplifier(G, bifurcation_defines)

        assert result == pytest.approx(1.0)

    def test_only_social_class_nodes_returns_unity(
        self, bifurcation_defines: BifurcationDefines
    ) -> None:
        """Graph with only social_class nodes (no territories) returns 1.0."""
        G: BabylonGraph = BabylonGraph()
        G.add_node("C001", _node_type="social_class", wealth=50.0)
        G.add_node("C002", _node_type="social_class", wealth=20.0)

        result = compute_legitimation_amplifier(G, bifurcation_defines)

        assert result == pytest.approx(1.0)

    def test_missing_legitimation_uses_default(
        self, bifurcation_defines: BifurcationDefines
    ) -> None:
        """Territory missing legitimation_index uses default 0.5.

        amplifier = 1.0 + (1.0 - 0.5) * (2.0 - 1.0) = 1.5
        """
        G: BabylonGraph = BabylonGraph()
        G.add_node("T001", _node_type="territory", population=1000)

        result = compute_legitimation_amplifier(G, bifurcation_defines)

        assert result == pytest.approx(1.5)

    def test_missing_population_uses_default(self, bifurcation_defines: BifurcationDefines) -> None:
        """Territory missing population uses default 1.

        Single territory with default pop=1 and legitimation=0.6:
        amplifier = 1.0 + (1.0 - 0.6) * (2.0 - 1.0) = 1.4
        """
        G: BabylonGraph = BabylonGraph()
        G.add_node("T001", _node_type="territory", legitimation_index=0.6)

        result = compute_legitimation_amplifier(G, bifurcation_defines)

        assert result == pytest.approx(1.4)

    def test_amplifier_always_at_least_one(self, bifurcation_defines: BifurcationDefines) -> None:
        """Amplifier is always >= 1.0, even at maximum legitimation."""
        G: BabylonGraph = BabylonGraph()
        G.add_node(
            "T001",
            _node_type="territory",
            legitimation_index=1.0,
            population=1000,
        )

        result = compute_legitimation_amplifier(G, bifurcation_defines)

        assert result >= 1.0


@pytest.mark.unit
class TestLegitimationAmplifierCustomScale:
    """Tests with non-default legitimation_amplifier_scale."""

    def test_custom_scale_zero_legitimation(self) -> None:
        """Custom scale (5.0) at zero legitimation.

        amplifier = 1.0 + (1.0 - 0.0) * (5.0 - 1.0) = 1.0 + 4.0 = 5.0
        """
        defines = BifurcationDefines(legitimation_amplifier_scale=5.0)
        G: BabylonGraph = BabylonGraph()
        G.add_node(
            "T001",
            _node_type="territory",
            legitimation_index=0.0,
            population=1000,
        )

        result = compute_legitimation_amplifier(G, defines)

        assert result == pytest.approx(5.0)

    def test_custom_scale_mid_legitimation(self) -> None:
        """Custom scale (3.0) at mid legitimation (0.5).

        amplifier = 1.0 + (1.0 - 0.5) * (3.0 - 1.0) = 1.0 + 1.0 = 2.0
        """
        defines = BifurcationDefines(legitimation_amplifier_scale=3.0)
        G: BabylonGraph = BabylonGraph()
        G.add_node(
            "T001",
            _node_type="territory",
            legitimation_index=0.5,
            population=1000,
        )

        result = compute_legitimation_amplifier(G, defines)

        assert result == pytest.approx(2.0)

    def test_scale_one_always_unity(self) -> None:
        """When scale = 1.0, amplifier is always 1.0 regardless of legitimation.

        amplifier = 1.0 + (1.0 - 0.2) * (1.0 - 1.0) = 1.0 + 0.0 = 1.0
        """
        defines = BifurcationDefines(legitimation_amplifier_scale=1.0)
        G: BabylonGraph = BabylonGraph()
        G.add_node(
            "T001",
            _node_type="territory",
            legitimation_index=0.2,
            population=1000,
        )

        result = compute_legitimation_amplifier(G, defines)

        assert result == pytest.approx(1.0)
