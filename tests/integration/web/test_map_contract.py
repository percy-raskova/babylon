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

Spec-112 C5 — aggregated (non-hex) ``/map/`` features ship ``geometry: None``
(the frontend derives region polygons from H3 cells at render time, see
``@deck.gl/geo-layers``'s ``H3ClusterLayer``), so each aggregated feature now
carries ``properties.member_h3``: the sorted list of H3 indexes rolled into
that group. Also pins a pre-existing quirk: ``zoom="cz"`` has no backing
column on ``HexState`` and no ``group_key_map`` entry, so it silently falls
through to county grouping — documented here, not fixed (owner queue).

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


@pytest.mark.usefixtures("_django_configured")
class TestMemberH3Aggregation:
    """Spec-112 C5 gate: aggregated features carry ``properties.member_h3``
    (the sorted H3 indexes rolled into that group) so the frontend can build
    region polygons via ``H3ClusterLayer`` — the backend ships
    ``geometry: None`` for aggregated features and always has.

    Stub-row based (like :class:`TestMapMetricContract`) so grouping
    correctness across *multiple* county groups is directly controllable —
    the live ``wayne_county`` scenario used by
    :class:`TestCountyFramingSeededSession` seeds every hex with the same
    (empty) ``county_fips``, so it cannot exercise cross-group isolation.
    """

    def test_county_zoom_features_carry_sorted_member_h3_per_group(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [_hex_row_stub("872a3072cffffff"), _hex_row_stub("872a3072dffffff")]
        rows[1].county_fips = "26099"

        features = EngineBridge._aggregate_hex_features(rows, "county")

        by_key = {f["properties"]["group_key"]: f for f in features}
        assert by_key["26163"]["properties"]["member_h3"] == ["872a3072cffffff"]
        assert by_key["26099"]["properties"]["member_h3"] == ["872a3072dffffff"]

    def test_member_h3_is_sorted_within_a_group(self) -> None:
        from game.engine_bridge import EngineBridge

        # Deliberately out-of-lexical-order h3 indexes within one group.
        rows = [_hex_row_stub("872a3072dffffff"), _hex_row_stub("872a3072cffffff")]

        features = EngineBridge._aggregate_hex_features(rows, "county")

        assert len(features) == 1
        assert features[0]["properties"]["member_h3"] == sorted(
            ["872a3072dffffff", "872a3072cffffff"]
        )

    def test_member_h3_union_covers_every_input_hex_with_no_duplicates(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [
            _hex_row_stub("872a3072cffffff"),
            _hex_row_stub("872a3072dffffff"),
            _hex_row_stub("872a30728ffffff"),
        ]
        rows[2].county_fips = "26099"

        features = EngineBridge._aggregate_hex_features(rows, "county")

        all_members = [h for f in features for h in f["properties"]["member_h3"]]
        assert sorted(all_members) == sorted(r.h3_index for r in rows)
        assert len(all_members) == len(set(all_members)), "no duplicate h3 across groups"

    def test_hex_zoom_features_have_no_member_h3(self) -> None:
        """Hex-zoom features are already 1:1 with a single H3 cell (the
        feature's own ``id``) — ``member_h3`` is an aggregation-only concept
        and stays absent at native hex resolution (Constitution III.11: no
        redundant properties)."""
        from game.engine_bridge import _hex_feature_properties

        props = _hex_feature_properties(_hex_row_stub())
        assert "member_h3" not in props


@pytest.mark.usefixtures("_django_configured")
class TestZoomCzFallsThroughToCounty:
    """Pins current (pre-existing, NOT fixed here) behavior: ``HexState``
    has no commuting-zone column at all, and ``_aggregate_hex_features``'s
    ``group_key_map`` has no ``"cz"`` entry, so ``zoom="cz"`` silently falls
    through ``group_key_map.get(zoom, "county_fips")`` and groups by
    ``county_fips`` instead of a real CZ dimension. Flagged for the owner
    queue: fixing this needs a schema addition (a CZ column + loader), not
    just a ``group_key_map`` entry — out of scope for this lane.
    """

    def test_cz_zoom_groups_by_county_fips_not_a_cz_dimension(self) -> None:
        from game.engine_bridge import EngineBridge

        rows = [_hex_row_stub("872a3072cffffff"), _hex_row_stub("872a3072dffffff")]
        rows[1].county_fips = "26099"

        cz_features = EngineBridge._aggregate_hex_features(rows, "cz")
        county_features = EngineBridge._aggregate_hex_features(rows, "county")

        cz_keys = {f["properties"]["group_key"] for f in cz_features}
        county_keys = {f["properties"]["group_key"] for f in county_features}
        assert cz_keys == county_keys == {"26163", "26099"}
        # The only difference is the literal "zoom" property value echoed
        # back — the grouping dimension itself is identical to "county".
        assert {f["properties"]["zoom"] for f in cz_features} == {"cz"}


def _seeded_wayne_state_and_graph() -> tuple[Any, Any]:
    """Build the real ``wayne_county`` tick-0 ``WorldState``/graph via the
    exact scenario-seeding pipeline ``EngineBridge.create_game`` calls
    (``_build_initial_state_for_scenario`` — includes owner item 8's
    ``_seed_balkanization_layer`` and owner item 30's
    ``_seed_wayne_county_fips``), entirely in-memory.

    Deliberately does NOT go through ``bridge.create_game`` +
    ``get_map_snapshot``/``hex_latest``: both the write side
    (``_persist_hex_state_safe``) and the read side
    (``EngineBridge.get_map_snapshot``) go through Django's ORM
    (``game.models.HexState``/``GameSession``), which in this integration
    suite's ``testing`` settings module points ``DATABASES["default"]`` at
    an in-memory SQLite with no unmanaged-table DDL applied — not the
    database the raw-psycopg ``bridge`` fixture (``POSTGRES_HOST`` et al.)
    ever writes to. Concretely: a real ``bridge.create_game(...)`` call's
    ``_persist_hex_state_safe`` step silently swallows a ``RuntimeError:
    Database access not allowed`` (pytest-django's DB blocker; verified
    empirically while authoring this test), so a bridge-created session's
    ``hex_latest`` stays permanently empty in this harness — the same
    Django-ORM wall ``TestBalkanizationSeed``'s ``_balkanization()`` helper
    in ``test_balkanization_seed.py`` documents and routes around. (In
    production/dev this is a non-issue — see ``_persist_hex_state_safe``'s
    own docstring: Django's ``default`` alias IS the same Postgres the
    persistence pool points at there.) Flagged for the owner queue: no
    lane-owned file can fix this without touching shared `conftest.py`
    DB-routing.

    So this helper drives the same scenario-seeding functions
    ``create_game`` calls and skips the DB round-trip, returning genuine
    engine-derived state (81 real H3 cells, each stamped with the real
    Wayne County FIPS ``26163``).
    """
    from game.engine_bridge import _build_initial_state_for_scenario

    state = _build_initial_state_for_scenario("wayne_county")
    return state, state.to_graph()


def _seeded_hex_rows(state: Any, graph: Any) -> list[object]:
    """Project a seeded ``WorldState``'s territories into
    ``hex_latest``-row-shaped objects via the real
    ``_serialize_territory``/``_hex_state_row`` pipeline (same as
    :func:`_seeded_wayne_state_and_graph`, one level down).

    Columns ``_hex_state_row`` never sets (no live per-territory source —
    see its docstring) still exist on a real ``HexState`` row, defaulted to
    the model/DB default — same ``db_defaults`` fixture as
    ``TestHexRowBuilderRoundTrip`` above.
    """
    from game.engine_bridge import _hex_state_row, _serialize_territory

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
    rows: list[object] = []
    for territory in state.territories.values():
        row = _hex_state_row(uuid.uuid4(), state.tick, _serialize_territory(territory, graph=graph))
        if row is not None:
            rows.append(SimpleNamespace(**{**db_defaults, **row}))
    return rows


@pytest.mark.usefixtures("_django_configured")
class TestCountyFramingSeededSession:
    """Spec-112 C5 RED gate: ``_aggregate_hex_features``/``_hex_feature_properties``
    (the parts of ``get_map_snapshot`` reachable without a live database —
    see :func:`_seeded_wayne_state_and_graph`) against a real seeded
    ``wayne_county`` session's territories, rather than hand-built stubs.
    """

    def test_county_zoom_features_carry_member_h3_covering_the_full_hex_set(self) -> None:
        from game.engine_bridge import EngineBridge

        state, graph = _seeded_wayne_state_and_graph()
        rows = _seeded_hex_rows(state, graph)
        assert rows, "expected wayne_county to seed at least one hex"

        features = EngineBridge._aggregate_hex_features(rows, "county")
        assert features, "expected at least one county-aggregated feature"

        all_members: list[str] = []
        for feature in features:
            member_h3 = feature["properties"]["member_h3"]
            assert member_h3 == sorted(member_h3), "member_h3 must be sorted"
            all_members.extend(member_h3)

        assert len(all_members) == len(set(all_members)), "no duplicate h3 across groups"
        assert set(all_members) == {r.h3_index for r in rows}

    def test_hex_zoom_features_have_no_member_h3(self) -> None:
        from game.engine_bridge import _hex_feature_properties

        state, graph = _seeded_wayne_state_and_graph()
        rows = _seeded_hex_rows(state, graph)
        assert rows

        for row in rows:
            assert "member_h3" not in _hex_feature_properties(row)

    def test_balkanization_present_at_hex_zoom(self) -> None:
        """Same code path ``get_map_snapshot`` uses for ``metadata.balkanization``
        (hydrate the raw graph -> ``_build_balkanization_block``) — this part
        needs no Django ORM, so it's safe to call directly (see
        ``test_balkanization_seed.py``). Zoom-independent in the real
        endpoint (always attempted regardless of the zoom branch), pinned
        here specifically for the hex-zoom case this lane's RED gate covers.
        """
        from game.engine_bridge import _build_balkanization_block

        _state, graph = _seeded_wayne_state_and_graph()
        block = _build_balkanization_block(graph)

        assert block["factions"]
