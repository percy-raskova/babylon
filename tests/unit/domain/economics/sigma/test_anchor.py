"""Unit tests for babylon.domain.economics.sigma.anchor (RED phase first)."""

from __future__ import annotations

import pytest

from babylon.domain.economics.sigma.anchor import anchor_to_world_scale
from babylon.domain.economics.sigma.statistics import compute_distribution_stats
from babylon.domain.economics.sigma.types import DistributionStats


class TestAnchorToWorldScale:
    def test_us_composite_anchors_above_world_mean(self) -> None:
        # Owner Ruling 1 (program-10 §2): "US hexes occupy the upper band" —
        # a composite far above the world mean should anchor strongly positive.
        world_stats = DistributionStats(mean=0.0, std_dev=1.0, n_observations=9)
        us_raw_composite = 2.5
        assert anchor_to_world_scale(us_raw_composite, world_stats) == pytest.approx(2.5)

    def test_external_bloc_anchors_at_or_below_world_mean(self) -> None:
        world_stats = DistributionStats(mean=0.0, std_dev=1.0, n_observations=9)
        periphery_raw_composite = -1.2
        assert anchor_to_world_scale(periphery_raw_composite, world_stats) == pytest.approx(-1.2)

    def test_world_stats_computed_from_bloc_observations_and_consumed(self) -> None:
        # A realistic small "world" cross-section: 8 external blocs + rest_of_usa.
        bloc_raw_composites = [-1.8, -1.2, -0.9, -0.5, -0.2, 0.1, 0.4, 0.9, 3.2]
        world_stats = compute_distribution_stats(bloc_raw_composites)
        anchored = anchor_to_world_scale(3.2, world_stats)
        assert anchored > 0.0  # the US-like outlier sits above the world mean
