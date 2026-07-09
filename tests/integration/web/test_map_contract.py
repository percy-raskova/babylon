"""Spec-109 A3+A5: one map-metric contract; no fabricated org consciousness.

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

Requires a running PostgreSQL instance. Skip with:
``pytest -m "not requires_postgres"``.
"""

from __future__ import annotations

import os

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


def _hex_row_stub(h3_index: str = "872a3072cffffff") -> object:
    """A ``hex_latest``-row-shaped object carrying every column the map
    feature builders read (matches ``game.models.HexState`` attribute names)."""
    from types import SimpleNamespace

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
