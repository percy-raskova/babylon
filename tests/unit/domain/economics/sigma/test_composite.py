"""Unit tests for babylon.domain.economics.sigma.composite (RED phase first)."""

from __future__ import annotations

import pytest

from babylon.domain.economics.sigma.composite import compose_sigma, standardize_components
from babylon.domain.economics.sigma.types import (
    ComponentDistributionStats,
    ComponentWeights,
    DistributionStats,
    SigmaComponents,
    StandardizedComponents,
)


@pytest.fixture
def stats() -> ComponentDistributionStats:
    return ComponentDistributionStats(
        organic_composition=DistributionStats(mean=3.0, std_dev=1.0, n_observations=10),
        capital_intensity=DistributionStats(mean=100_000.0, std_dev=50_000.0, n_observations=10),
        labor_content=DistributionStats(mean=0.02, std_dev=0.01, n_observations=10),
    )


class TestStandardizeComponents:
    def test_standardizes_each_component_against_its_own_distribution(
        self, stats: ComponentDistributionStats
    ) -> None:
        components = SigmaComponents(
            node_id="BEA-334",
            year=2020,
            organic_composition=4.0,  # 1 std above mean
            capital_intensity=150_000.0,  # 1 std above mean
            labor_content=0.03,  # 1 std above mean
        )
        standardized = standardize_components(components, stats)
        assert standardized.node_id == "BEA-334"
        assert standardized.year == 2020
        assert standardized.organic_composition_z == pytest.approx(1.0)
        assert standardized.capital_intensity_z == pytest.approx(1.0)
        assert standardized.labor_content_z == pytest.approx(1.0)

    def test_value_at_mean_standardizes_to_zero(self, stats: ComponentDistributionStats) -> None:
        components = SigmaComponents(
            node_id="BEA-221",
            year=2020,
            organic_composition=3.0,
            capital_intensity=100_000.0,
            labor_content=0.02,
        )
        standardized = standardize_components(components, stats)
        assert standardized.organic_composition_z == pytest.approx(0.0)
        assert standardized.capital_intensity_z == pytest.approx(0.0)
        assert standardized.labor_content_z == pytest.approx(0.0)


class TestComposeSigma:
    def test_equal_weights_average_the_standardized_components(self) -> None:
        standardized = StandardizedComponents(
            node_id="BEA-334",
            year=2020,
            organic_composition_z=1.0,
            capital_intensity_z=1.0,
            labor_content_z=1.0,
        )
        weights = ComponentWeights(
            weight_occ=1 / 3, weight_capital_intensity=1 / 3, weight_labor_content=1 / 3
        )
        # rel=1e-4: each weight is independently SnapToGrid-quantized to 1e-5,
        # so three repeating-decimal 1/3 weights sum to 0.999999, not 1.0 exactly.
        assert compose_sigma(standardized, weights) == pytest.approx(1.0, rel=1e-4)

    def test_zero_weight_on_a_component_excludes_it(self) -> None:
        standardized = StandardizedComponents(
            node_id="BEA-334",
            year=2020,
            organic_composition_z=2.0,
            capital_intensity_z=0.0,
            labor_content_z=0.0,
        )
        weights = ComponentWeights(
            weight_occ=1.0, weight_capital_intensity=0.0, weight_labor_content=0.0
        )
        assert compose_sigma(standardized, weights) == pytest.approx(2.0)

    def test_asymmetric_weights_produce_weighted_sum(self) -> None:
        standardized = StandardizedComponents(
            node_id="BEA-334",
            year=2020,
            organic_composition_z=2.0,
            capital_intensity_z=-1.0,
            labor_content_z=0.5,
        )
        weights = ComponentWeights(
            weight_occ=0.5, weight_capital_intensity=0.3, weight_labor_content=0.2
        )
        expected = 2.0 * 0.5 + (-1.0) * 0.3 + 0.5 * 0.2
        assert compose_sigma(standardized, weights) == pytest.approx(expected)
