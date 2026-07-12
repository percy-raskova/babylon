"""Regression: the map-snapshot aggregator must handle Decimal NUMERIC columns.

Program 17 item 1a lit ``imperial_rent`` (a Postgres ``NUMERIC`` column →
psycopg returns ``Decimal``). ``_aggregate_hex_features`` seeded its
accumulators as ``float`` and did ``acc[...] += state.imperial_rent``, so
``float += Decimal`` raised ``TypeError`` on the DEFAULT (``county``) map zoom —
an uncaught HTTP 500 the instant Φ became non-zero. The Wave-1 live-verify caught
it. Two fixes are pinned here:

1. the five ``NUMERIC`` metric columns are cast to ``float`` at the read boundary
   (``profit_rate``/``exploitation_rate``/``occ``/``imperial_rent``/``heat``);
2. ``imperial_rent`` is rounded to 6dp (was 2dp) so a ~1e-5 Leontief structural
   rent does not collapse to ``0.00`` and read as a blank default lens.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from game.engine_bridge import EngineBridge

_PHI = 0.0000335406867629077  # a real wayne_county tick-1 imperial_rent value


def _hex(**overrides: Any) -> SimpleNamespace:
    """Build a minimal hex_latest-row stand-in for the aggregator."""
    base: dict[str, Any] = {
        "county_fips": "26163",
        "state_fips": "26",
        "bea_ea_code": "EA1",
        "msa_code": "MSA1",
        "pop_total": 100,
        "profit_rate": None,
        "exploitation_rate": None,
        "occ": None,
        "imperial_rent": Decimal(str(_PHI)),
        "heat": Decimal("0.4"),
        "org_count": 1,
        "h3_index": "862ab2c8fffffff",
        "attributes": {},
        "dominant_class": None,
        "county_name": "Wayne",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class TestAggregateHexFeaturesDecimalSafety:
    """The aggregator must not crash on Decimal columns and must keep Φ visible."""

    def test_county_zoom_does_not_crash_on_decimal_imperial_rent(self) -> None:
        bridge = EngineBridge(MagicMock())
        features = bridge._aggregate_hex_features(
            [_hex(), _hex(h3_index="862ab2c8fffff01")], "county"
        )
        assert len(features) == 1
        props = features[0]["properties"]
        assert isinstance(props["imperial_rent"], float)
        # two hexes summed at 6dp — must be strictly > 0 (the 2dp bug → 0.0)
        assert props["imperial_rent"] == pytest.approx(round(2 * _PHI, 6))
        assert props["imperial_rent"] > 0.0

    def test_decimal_profit_occ_exploitation_are_float_safe(self) -> None:
        # the deferred capital/tensor_registry leg will make these Decimal too;
        # they must not reintroduce the float += Decimal crash.
        bridge = EngineBridge(MagicMock())
        features = bridge._aggregate_hex_features(
            [
                _hex(
                    profit_rate=Decimal("0.2"),
                    exploitation_rate=Decimal("1.5"),
                    occ=Decimal("3.0"),
                )
            ],
            "county",
        )
        props = features[0]["properties"]
        assert isinstance(props["profit_rate"], float)
        assert props["profit_rate"] == pytest.approx(0.2)

    @pytest.mark.parametrize("zoom", ["county", "state", "bea", "msa"])
    def test_all_aggregated_zooms_survive_decimal(self, zoom: str) -> None:
        bridge = EngineBridge(MagicMock())
        features = bridge._aggregate_hex_features([_hex()], zoom)
        assert features
        assert isinstance(features[0]["properties"]["imperial_rent"], float)
