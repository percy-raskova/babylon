"""Spec-109 A3+A5+A2: one map-metric contract; no fabricated org consciousness;
habitability joins the contract from the live graph.

A3 — the ``/map/`` metric contract had three divergent copies:
``VALID_MAP_LAYERS`` (api.py) advertised 11 layers, the snapshot's
``metadata.available_metrics`` advertised 6, and the emitted feature
properties defined the truth. Requesting a lens for a never-emitted metric
(consciousness/wealth/rent/biocapacity) produced features with no value key
— a silently blank overlay (Constitution III.11). One source of truth now
lives in ``web/game/map_contract.py``; every advertised metric must be
emitted at every zoom.

A5 — ``_serialize_organization`` fabricated a ``{0.33, 0.33, 0.34}``
consciousness simplex for every org. The engine computes no org-level
distribution, so the honest value is ``None`` (loud empty in the UI), never
plausible thirds.

A2 — the web bridge persisted only ~9 of ~30 ``hex_latest`` columns.
``habitability`` (MetabolismSystem's Sovereign-driven metabolic impact,
Spec-070 FR-043) is graph-only — excluded from the Territory pydantic model
— so it is threaded through via the live graph and carried in
``hex_latest``'s JSONB ``attributes`` column, flattened to a top-level
``habitability`` property at both zooms.

Requires a running PostgreSQL instance. Skip with:
``pytest -m "not requires_postgres"``.
"""

from __future__ import annotations

import os
import uuid
from types import SimpleNamespace
from typing import Any

import pytest

pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(
        not os.environ.get("POSTGRES_HOST"),
        reason="PostgreSQL not configured (set POSTGRES_HOST)",
    ),
]


@pytest.fixture
def _django_configured() -> None:
    """Configure Django so ``game.*`` modules import (no DB access needed)."""
    import django
    from django.conf import settings

    if not settings.configured:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "babylon_web.settings.development")
        django.setup()


def _hex_row_stub(
    h3_index: str = "872a3072cffffff", *, habitability: float | None = 0.55
) -> object:
    """A ``hex_latest``-row-shaped object carrying every column the map
    feature builders read (matches ``game.models.HexState`` attribute names).

    ``habitability`` lives in the JSONB ``attributes`` column (spec-109
    A2) — omitted (``None``) when the graph never wrote it for this hex,
    matching real hex_latest rows for territories with no Sovereign
    metabolic_impact entry.
    """
    return SimpleNamespace(
        h3_index=h3_index,
        county_fips="26163",
        county_name="Wayne",
        state_fips="26",
        bea_ea_code=None,
        msa_code=None,
        profit_rate=0.12,
        exploitation_rate=0.4,
        occ=2.1,
        imperial_rent=3.5,
        heat=0.6,
        org_count=2,
        dominant_class="proletariat",
        pop_total=1000,
        attributes={"habitability": habitability} if habitability is not None else {},
    )


@pytest.mark.usefixtures("_django_configured")
class TestMapMetricContract:
    """A3 gate: API layers == the contract == emitted properties, both zooms."""

    def test_api_layer_allowlist_derives_from_the_contract(self) -> None:
        """VALID_MAP_LAYERS and MAP_METRIC_PROPERTIES are one set."""
        from game.api import VALID_MAP_LAYERS
        from game.map_contract import MAP_METRIC_PROPERTIES

        assert set(VALID_MAP_LAYERS) == set(MAP_METRIC_PROPERTIES)

    def test_every_contract_metric_is_emitted_at_hex_zoom(self) -> None:
        """Hex-zoom feature properties carry every contract metric."""
        from game.engine_bridge import _hex_feature_properties
        from game.map_contract import MAP_METRIC_PROPERTIES

        props = _hex_feature_properties(_hex_row_stub())
        missing = [m for m in MAP_METRIC_PROPERTIES if m not in props]
        assert not missing, f"contract metrics missing at hex zoom: {missing}"

    def test_every_contract_metric_survives_county_aggregation(self) -> None:
        """County-zoom aggregated properties carry every contract metric."""
        from game.engine_bridge import EngineBridge
        from game.map_contract import MAP_METRIC_PROPERTIES

        rows = [_hex_row_stub(), _hex_row_stub("872a3072dffffff")]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features, "expected at least one aggregated feature"
        for feature in features:
            props = feature["properties"]
            missing = [m for m in MAP_METRIC_PROPERTIES if m not in props]
            assert not missing, f"contract metrics lost in aggregation: {missing}"


class TestOrgConsciousnessHonesty:
    """A5 gate: no fabricated simplex — None until the engine computes one."""

    def test_org_consciousness_is_null_not_fabricated_thirds(self, bridge: object) -> None:
        """Serialized orgs carry consciousness=None, not invented thirds."""
        session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)
        snapshot = bridge.get_snapshot(session_id)

        assert snapshot["organizations"], "wayne_county seeds at least one org"
        for org in snapshot["organizations"]:
            assert org["consciousness"] is None


@pytest.mark.usefixtures("_django_configured")
class TestHabitabilityMapMetric:
    """A2 gate (2a): habitability is present + numeric at both zooms and is
    a first-class member of the contract, not a silent extra."""

    def test_habitability_is_in_the_contract(self) -> None:
        from game.map_contract import MAP_METRIC_PROPERTIES

        assert "habitability" in MAP_METRIC_PROPERTIES

    def test_habitability_numeric_at_hex_zoom(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(habitability=0.72))

        assert isinstance(props["habitability"], float)
        assert props["habitability"] == pytest.approx(0.72)

    def test_habitability_none_when_never_written(self) -> None:
        """A hex the graph never touched (no Sovereign metabolic_impact entry)
        reports None, not a fabricated 0.0 or biocapacity proxy."""
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub(habitability=None))

        assert props["habitability"] is None

    def test_habitability_population_weighted_mean_at_county_zoom(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub("872a3072cffffff", habitability=0.4),
            _hex_row_stub("872a3072dffffff", habitability=0.8),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert len(features) == 1
        # Both stub rows share pop_total=1000 -> equal weight -> simple mean.
        assert features[0]["properties"]["habitability"] == pytest.approx(0.6)

    def test_habitability_county_mean_is_none_when_no_hex_has_data(self) -> None:
        """A county whose hexes never got a habitability write must not read
        as a silent 0.0 (Constitution III.11) — coverage must be explicit."""
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub("872a3072cffffff", habitability=None),
            _hex_row_stub("872a3072dffffff", habitability=None),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["habitability"] is None

    def test_habitability_county_mean_ignores_hexes_without_coverage(self) -> None:
        """A partial-coverage county's mean is over the covered hexes only,
        never silently diluted by treating missing data as 0.0."""
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub("872a3072cffffff", habitability=0.9),
            _hex_row_stub("872a3072dffffff", habitability=None),
        ]
        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert features[0]["properties"]["habitability"] == pytest.approx(0.9)


class TestHexRowBuilderRoundTrip:
    """A2 gate (2b): every hex_latest column the row-builder writes non-null
    for a real territory survives to the /map/ feature properties (modulo
    the documented rename/aggregation-only/geometry/bookkeeping exclusions).
    """

    # hex_latest columns _hex_state_row can write non-null that are
    # deliberately NOT on the /map/ hex-zoom property surface — one reason
    # each (Constitution III.11 asks for an honest inventory, not a blanket
    # exemption).
    _EXCLUDED_FROM_MAP_SURFACE = frozenset(
        {
            "game_id",  # session bookkeeping, not a displayed metric
            "tick",  # row-selection bookkeeping, not a property
            "center_lat",  # geometry internal — the feature boundary is built
            "center_lng",  # from h3.cell_to_boundary(h3_index), not these columns
            "state_fips",  # only a grouping key for zoom="state" aggregation
            "heat_delta",  # per-hex history/inspector surface, not the map contract
            "attributes",  # raw JSONB carrier — its keys are flattened individually
        }
    )

    # hex_latest column name -> /map/ property name, where they differ.
    _RENAMES = {"org_count": "org_presence", "pop_total": "population"}

    def test_non_null_row_columns_survive_to_hex_zoom_properties(self) -> None:
        from game.engine_bridge import _hex_feature_properties, _hex_state_row

        territory: dict[str, Any] = {
            "id": "T001",
            "h3_index": "872a3072cffffff",
            "county_fips": "26163",
            "name": "Test County",
            "heat": 0.6,
            "population": 1000,
            "habitability": 0.55,
        }
        row = _hex_state_row(uuid.uuid4(), 3, territory, org_count=2, heat_delta=0.1)
        assert row is not None

        # Columns the row-builder does NOT set for this territory (e.g. no
        # profit_rate source) still exist on a real persisted row, defaulted
        # to the model's own None/'26' — fill those in so the stub matches a
        # real ``HexState`` instance's attribute surface.
        db_defaults: dict[str, Any] = {
            "bea_ea_code": None,
            "msa_code": None,
            "state_fips": "26",
            "profit_rate": None,
            "exploitation_rate": None,
            "occ": None,
            "imperial_rent": None,
            "dominant_class": None,
        }
        stub = SimpleNamespace(**{**db_defaults, **row})

        props = _hex_feature_properties(stub)

        checked = 0
        for column, value in row.items():
            if value is None or column in self._EXCLUDED_FROM_MAP_SURFACE:
                continue
            prop_key = self._RENAMES.get(column, column)
            assert prop_key in props, (
                f"hex_latest column {column!r} written non-null but "
                f"{prop_key!r} is missing from /map/ feature properties"
            )
            assert props[prop_key] == value
            checked += 1

        assert checked > 0, "expected at least one non-excluded non-null column"
        assert props["habitability"] == pytest.approx(0.55)
