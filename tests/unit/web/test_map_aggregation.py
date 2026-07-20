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

    @pytest.mark.parametrize("zoom", ["county", "state", "bea", "msa", "cz"])
    def test_all_aggregated_zooms_survive_decimal(self, zoom: str) -> None:
        bridge = EngineBridge(MagicMock())
        features = bridge._aggregate_hex_features([_hex()], zoom)
        assert features
        assert isinstance(features[0]["properties"]["imperial_rent"], float)


class TestCzZoomAggregation:
    """#39 T7: ``zoom="cz"`` groups by real commuting zone (T3's committed
    ``bridge_county_cz.csv`` crosswalk via ``_county_to_cz_lookup``), not the
    pre-T7 silent fallback to ``county_fips`` grouping. Fast tier — the
    committed CSV needs no DB, mirrored fixture approach to
    :class:`TestAggregateHexFeaturesDecimalSafety` above.
    """

    def test_cz_zoom_merges_counties_sharing_a_commuting_zone(self) -> None:
        """Michigan spot-check: Wayne/Oakland/Macomb (26163/26125/26099) all
        sit in commuting zone 11600 (Detroit) — three distinct counties
        collapse into one CZ group."""
        bridge = EngineBridge(MagicMock())
        rows = [
            _hex(h3_index="862ab2c8fffff01", county_fips="26163"),  # Wayne
            _hex(h3_index="862ab2c8fffff02", county_fips="26125"),  # Oakland
            _hex(h3_index="862ab2c8fffff03", county_fips="26099"),  # Macomb
        ]

        features = bridge._aggregate_hex_features(rows, "cz")

        assert len(features) == 1
        props = features[0]["properties"]
        assert props["group_key"] == "11600"
        assert props["zoom"] == "cz"
        assert sorted(props["member_h3"]) == sorted(r.h3_index for r in rows)

    def test_cz_zoom_keys_are_cz_ids_not_county_fips(self) -> None:
        """The silent fallback is dead: cz-zoom group keys must be real CZ
        ids, never the raw county_fips the pre-T7 bug silently grouped by."""
        bridge = EngineBridge(MagicMock())
        rows = [
            _hex(h3_index="862ab2c8fffff01", county_fips="26163"),
            _hex(h3_index="862ab2c8fffff02", county_fips="26099"),
        ]

        cz_features = bridge._aggregate_hex_features(rows, "cz")
        county_features = bridge._aggregate_hex_features(rows, "county")

        cz_keys = {f["properties"]["group_key"] for f in cz_features}
        county_keys = {f["properties"]["group_key"] for f in county_features}
        assert cz_keys == {"11600"}
        assert county_keys == {"26163", "26099"}
        assert cz_keys != county_keys

    def test_cz_less_county_falls_into_the_unknown_bucket(self) -> None:
        """One of the 19 AK/CT counties absent from the 1990 ERS crosswalk
        (09110, a 2022 Connecticut planning region — see
        ``cz_adjunction()``'s docstring) must NOT 500 or silently merge into
        a wrong CZ group. It follows the SAME "unknown" null-bucket every
        county already takes at the never-populated bea/msa zooms (the
        established partial-coverage precedent this mirrors) — read
        directly off ``_aggregate_hex_features``'s
        ``key = getattr(state, group_attr, None); if key is None: key =
        "unknown"`` handling."""
        bridge = EngineBridge(MagicMock())
        rows = [_hex(h3_index="862ab2c8fffff04", county_fips="09110")]

        features = bridge._aggregate_hex_features(rows, "cz")

        assert len(features) == 1
        assert features[0]["properties"]["group_key"] == "unknown"

    def test_vintage_bridged_county_lands_in_its_bridged_cz(self) -> None:
        """12086 (Miami-Dade, renamed from Dade County/12025 in 1997) has no
        row of its own in the 1990 crosswalk — T3's
        ``_FIPS_VINTAGE_BRIDGES`` binds it to 12025's CZ (07000)."""
        bridge = EngineBridge(MagicMock())
        rows = [_hex(h3_index="862ab2c8fffff05", county_fips="12086")]

        features = bridge._aggregate_hex_features(rows, "cz")

        assert len(features) == 1
        assert features[0]["properties"]["group_key"] == "07000"

    def test_unknown_zoom_value_still_falls_back_to_county(self) -> None:
        """Pre-existing behavior pinned: a zoom string with no
        ``group_key_map`` entry (typo, or a not-yet-supported level) still
        defaults to ``county_fips`` grouping — unaffected by the new "cz"
        entry."""
        bridge = EngineBridge(MagicMock())
        rows = [_hex(h3_index="862ab2c8fffff06", county_fips="26163")]

        features = bridge._aggregate_hex_features(rows, "galaxy")

        assert len(features) == 1
        assert features[0]["properties"]["group_key"] == "26163"
        assert features[0]["properties"]["zoom"] == "galaxy"
