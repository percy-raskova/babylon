"""Unit tests for babylon.domain.economics.sigma.statistics (RED phase first)."""

from __future__ import annotations

import pytest

from babylon.domain.economics.sigma.statistics import compute_distribution_stats, z_score
from babylon.domain.economics.sigma.types import DistributionStats


class TestComputeDistributionStats:
    def test_computes_sample_mean_and_std_dev(self) -> None:
        stats = compute_distribution_stats([1.0, 2.0, 3.0])
        assert stats.mean == pytest.approx(2.0)
        assert stats.std_dev == pytest.approx(1.0)
        assert stats.n_observations == 3

    def test_known_values_match_hand_computed_sample_std(self) -> None:
        # ddof=1 sample std of [2, 4, 4, 4, 5, 5, 7, 9] is 2.13809...
        values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
        stats = compute_distribution_stats(values)
        assert stats.mean == pytest.approx(5.0)
        assert stats.std_dev == pytest.approx(2.138089935, rel=1e-6)

    def test_raises_on_fewer_than_two_observations(self) -> None:
        with pytest.raises(ValueError, match="at least 2"):
            compute_distribution_stats([1.0])

    def test_raises_on_empty_observations(self) -> None:
        with pytest.raises(ValueError, match="at least 2"):
            compute_distribution_stats([])

    def test_raises_on_degenerate_zero_spread(self) -> None:
        with pytest.raises(ValueError, match="zero spread"):
            compute_distribution_stats([3.0, 3.0, 3.0])


class TestZScore:
    def test_value_at_mean_is_zero(self) -> None:
        stats = DistributionStats(mean=10.0, std_dev=2.0, n_observations=5)
        assert z_score(10.0, stats) == pytest.approx(0.0)

    def test_value_one_std_above_mean_is_one(self) -> None:
        stats = DistributionStats(mean=10.0, std_dev=2.0, n_observations=5)
        assert z_score(12.0, stats) == pytest.approx(1.0)

    def test_value_below_mean_is_negative(self) -> None:
        stats = DistributionStats(mean=10.0, std_dev=2.0, n_observations=5)
        assert z_score(6.0, stats) == pytest.approx(-2.0)
