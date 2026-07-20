"""Unit tests for ``_seed_balkanization_layer`` CLAIMS-edge seeding.

Wave-1 item W1.5 (spine goal): the shipped ``seed_sovereigns.json``
initial_claims reference ExternalNode IDs ("canada" / "rest_of_usa"),
never real ``state.territories`` keys, so the literal ``territory_id in
state.territories`` join at ``_seed_balkanization_layer`` rejected every
claim in every scenario, unconditionally — CLAIMS edges never seeded and
``SOV_EXTERIOR_NULL`` (the documented FR-040b fallback sovereign, spec-070)
never claimed anything either.

These tests pin the FR-040b coverage invariant against production code
(the SC-017 integration test at
``tests/integration/balkanization/test_seed_coverage_invariant.py``
hand-fabricates the same shape but never exercises
``_seed_balkanization_layer`` itself).
"""

from __future__ import annotations

import pytest

from babylon.engine.scenarios._legacy_wayne import create_wayne_county_scenario
from babylon.models.entities.territory import Territory
from babylon.models.enums import EdgeType, SectorType
from babylon.models.world_state import WorldState
from game.engine_bridge import _seed_balkanization_layer

pytestmark = pytest.mark.unit


def _build_state():
    # wayne_county: a real, entirely domestic-interior H3 scenario (no
    # exterior nodes) — the shape the FR-040b domestic fallback assumes.
    state, _config, _defines = create_wayne_county_scenario()
    return state


def _county_territory(territory_id: str, county_fips: str) -> Territory:
    """A minimal county-grain (T4-shaped) Territory: opaque id, real fips,
    no h3_index — mirrors ``_create_us_territories``'s output shape."""
    return Territory(
        id=territory_id,
        county_fips=county_fips,
        h3_index=None,
        name=f"Test County {county_fips}",
        sector_type=SectorType.INDUSTRIAL,
    )


def _expected_hex_influences(
    hex_territories: dict[str, Territory],
) -> dict[tuple[str, str], tuple[float, str]]:
    """Independently recompute the hex-parent aggregation for assertions.

    Mirrors the hex path's own aggregation rule (mean ``influence_level``,
    lexicographic-max ``support_type`` tie-break — see
    ``_seed_balkanization_layer``'s docstring) via ``h3.cell_to_parent`` at
    the fixture's own resolution. Uses only the raw seed data and the h3
    library (never ``_seed_balkanization_layer`` or its internal loop), so
    this is an independent oracle, not a tautological re-assertion of
    production's own output (T5 review M1).
    """
    import h3

    from babylon.data.game.balkanization import load_seed_influences

    resolution = h3.get_resolution(next(iter(sorted(hex_territories))))
    buckets: dict[tuple[str, str], list[tuple[float, str]]] = {}
    for edge in load_seed_influences():
        try:
            parent = h3.cell_to_parent(str(edge["territory_id"]), resolution)
        except (ValueError, TypeError):
            continue
        if parent not in hex_territories:
            continue
        key = (str(edge["faction_id"]), parent)
        buckets.setdefault(key, []).append(
            (float(edge["influence_level"]), str(edge["support_type"]))
        )
    expected: dict[tuple[str, str], tuple[float, str]] = {}
    for key, children in buckets.items():
        level = round(sum(lvl for lvl, _ in children) / len(children), 6)
        support = max(children, key=lambda c: (c[0], c[1]))[1]
        expected[key] = (level, support)
    return expected


def _expected_county_influences(
    hex_to_county: dict[str, str],
    territory_by_fips: dict[str, str],
) -> dict[tuple[str, str], tuple[float, str]]:
    """Independently recompute the county-grain aggregation for assertions.

    Mirrors the hex path's own aggregation rule (mean ``influence_level``,
    lexicographic-max ``support_type`` tie-break — see
    ``_seed_balkanization_layer``'s docstring) applied to the county grain
    instead of the hex-parent grain.
    """
    from babylon.data.game.balkanization import load_seed_influences

    buckets: dict[tuple[str, str], list[tuple[float, str]]] = {}
    for edge in load_seed_influences():
        fips = hex_to_county.get(str(edge["territory_id"]))
        if fips is None:
            continue
        target = territory_by_fips.get(fips)
        if target is None:
            continue
        key = (str(edge["faction_id"]), target)
        buckets.setdefault(key, []).append(
            (float(edge["influence_level"]), str(edge["support_type"]))
        )
    expected: dict[tuple[str, str], tuple[float, str]] = {}
    for key, children in buckets.items():
        level = round(sum(lvl for lvl, _ in children) / len(children), 6)
        support = max(children, key=lambda c: (c[0], c[1]))[1]
        expected[key] = (level, support)
    return expected


@pytest.mark.unit
class TestSeedBalkanizationLayerClaims:
    """FR-040b: CLAIMS edges must actually seed."""

    def test_claims_edges_are_seeded(self) -> None:
        state = _build_state()

        seeded = _seed_balkanization_layer(state)

        claims = [r for r in seeded.relationships if r.edge_type == EdgeType.CLAIMS]
        assert len(claims) > 0

    def test_every_territory_is_claimed_by_exactly_one_sovereign(self) -> None:
        state = _build_state()

        seeded = _seed_balkanization_layer(state)

        claims = [r for r in seeded.relationships if r.edge_type == EdgeType.CLAIMS]
        claimants_by_territory: dict[str, list[str]] = {}
        for claim in claims:
            claimants_by_territory.setdefault(claim.target_id, []).append(claim.source_id)

        for territory_id in seeded.territories:
            claimants = claimants_by_territory.get(territory_id, [])
            assert len(claimants) == 1, (
                f"territory {territory_id!r} claimed by {len(claimants)} "
                f"sovereigns (expected exactly 1): {claimants}"
            )

    def test_otherwise_unclaimed_territories_go_to_sov_usa_fed(self) -> None:
        """Task R / ADR080: neither ``canada`` nor ``rest_of_usa`` (the seed
        file's literal initial_claims territory_ids) are real territory
        keys in this scenario, so every territory falls to the FR-040b
        fallback — which now routes to the domestic federal sovereign
        ``SOV_USA_FED`` (every Territory in ``state.territories`` is a
        domestic interior H3 cell), never the provisional exterior-null
        sovereign. Zero CLAIMS may source from SOV_EXTERIOR_NULL, and
        SOV_USA_FED must hold a CLAIMS majority (in this all-fallback
        scenario, all of it) of the interior Territories."""
        state = _build_state()

        seeded = _seed_balkanization_layer(state)

        claims = [r for r in seeded.relationships if r.edge_type == EdgeType.CLAIMS]
        null_claims = [r for r in claims if r.source_id == "SOV_EXTERIOR_NULL"]
        assert null_claims == [], (
            f"SOV_EXTERIOR_NULL must not claim domestic interior Territories: {null_claims}"
        )

        usa_fed_claims = [r for r in claims if r.source_id == "SOV_USA_FED"]
        assert len(usa_fed_claims) / len(seeded.territories) >= 0.5


@pytest.mark.unit
class TestSeedBalkanizationLayerHexPathUnchanged:
    """#39 T5: the hex aggregation path must stay byte-identical.

    Pre-existing tests in this file only ever asserted on CLAIMS edges;
    the INFLUENCES/hex-parent aggregation pass was never pinned at all.
    This test closes that gap so a future edit to the county path cannot
    silently regress Wayne's hex path.
    """

    def test_wayne_hex_scenario_still_gets_influences(self) -> None:
        state = _build_state()

        seeded = _seed_balkanization_layer(state)

        influences = [r for r in seeded.relationships if r.edge_type == EdgeType.INFLUENCES]
        assert influences, "hex-parent aggregation must still produce INFLUENCES edges"
        # Every aggregated edge must target a real scenario territory (the
        # h3.cell_to_parent join), never a raw hex id absent from the scenario.
        assert {r.target_id for r in influences} <= set(seeded.territories)

        # T5 review M1: pin the actual influence_level/support_type VALUES,
        # not just edge existence + target subset — an independent oracle
        # (never the production aggregation) computed from the fixture's own
        # seed data.
        hex_territories = {
            tid: t for tid, t in state.territories.items() if getattr(t, "h3_index", None)
        }
        expected = _expected_hex_influences(hex_territories)
        actual = {
            (r.source_id, r.target_id): (r.influence_level, r.support_type) for r in influences
        }
        assert actual == expected


@pytest.mark.unit
class TestSeedBalkanizationLayerCountyInfluences:
    """#39 T5: county-grain influence aggregation via an injected hex→county map.

    The mapping is injected (DI, no runtime discovery) so this logic is
    testable without the reference DB — the real ``bridge_county_h3`` read
    lives at the call boundary (``_load_seed_hex_to_county_bridge``,
    called from ``_build_initial_state_for_scenario``), never inside
    ``_seed_balkanization_layer`` itself.
    """

    def test_county_keyed_scenario_gets_influences_from_injected_mapping(self) -> None:
        from babylon.data.game.balkanization import load_seed_influences

        seed_hex_ids = sorted({str(e["territory_id"]) for e in load_seed_influences()})
        hex_a, hex_b = seed_hex_ids[0], seed_hex_ids[1]

        state = WorldState(
            territories={
                "T0001": _county_territory("T0001", "26163"),
                "T0002": _county_territory("T0002", "06037"),
            }
        )
        hex_to_county = {hex_a: "26163", hex_b: "06037"}

        seeded = _seed_balkanization_layer(state, hex_to_county=hex_to_county)

        influences = [r for r in seeded.relationships if r.edge_type == EdgeType.INFLUENCES]
        assert influences, "expected a non-empty county-grain influence layer"

        expected = _expected_county_influences(hex_to_county, {"26163": "T0001", "06037": "T0002"})
        actual = {
            (r.source_id, r.target_id): (r.influence_level, r.support_type) for r in influences
        }
        assert actual == expected

    def test_territory_with_neither_key_is_skipped(self) -> None:
        from babylon.data.game.balkanization import load_seed_influences

        seed_hex_ids = sorted({str(e["territory_id"]) for e in load_seed_influences()})
        hex_a = seed_hex_ids[0]

        abstract_territory = Territory(
            id="T9999",
            name="Abstract (no county_fips, no h3_index)",
            sector_type=SectorType.INDUSTRIAL,
        )
        state = WorldState(
            territories={
                "T0001": _county_territory("T0001", "26163"),
                "T9999": abstract_territory,
            }
        )
        hex_to_county = {hex_a: "26163"}

        seeded = _seed_balkanization_layer(state, hex_to_county=hex_to_county)

        influences = [r for r in seeded.relationships if r.edge_type == EdgeType.INFLUENCES]
        assert influences, "the county-keyed territory must still get influences"
        assert all(r.target_id != "T9999" for r in influences), (
            "a territory with neither h3_index nor county_fips must never be an INFLUENCES target"
        )

    def test_seed_hex_whose_county_is_absent_from_scenario_is_dropped(self) -> None:
        """Mirrors the hex path's own unmatched-parent behavior: a seed edge
        whose resolved parent/county isn't a scenario territory is silently
        skipped (``if parent not in hex_territories: continue`` in the hex
        branch) — never a loud error, never a fabricated territory."""
        from babylon.data.game.balkanization import load_seed_influences

        seed_hex_ids = sorted({str(e["territory_id"]) for e in load_seed_influences()})
        hex_a, hex_unmatched = seed_hex_ids[0], seed_hex_ids[2]

        state = WorldState(territories={"T0001": _county_territory("T0001", "26163")})
        # hex_unmatched resolves to a real-shaped FIPS that simply has no
        # matching territory in this (deliberately narrow) scenario.
        hex_to_county = {hex_a: "26163", hex_unmatched: "51999"}

        seeded = _seed_balkanization_layer(state, hex_to_county=hex_to_county)

        influences = [r for r in seeded.relationships if r.edge_type == EdgeType.INFLUENCES]
        assert influences
        assert {r.target_id for r in influences} == {"T0001"}

    def test_scenario_with_neither_h3_nor_county_territories_is_a_noop(self) -> None:
        abstract_territory = Territory(
            id="T0001",
            name="Abstract",
            sector_type=SectorType.INDUSTRIAL,
        )
        state = WorldState(territories={"T0001": abstract_territory})

        seeded = _seed_balkanization_layer(state, hex_to_county={"deadbeefcafe123": "26163"})

        influences = [r for r in seeded.relationships if r.edge_type == EdgeType.INFLUENCES]
        assert influences == []

    def test_determinism_two_runs_identical(self) -> None:
        from babylon.data.game.balkanization import load_seed_influences

        seed_hex_ids = sorted({str(e["territory_id"]) for e in load_seed_influences()})
        hex_a, hex_b = seed_hex_ids[0], seed_hex_ids[1]
        state = WorldState(
            territories={
                "T0001": _county_territory("T0001", "26163"),
                "T0002": _county_territory("T0002", "06037"),
            }
        )
        hex_to_county = {hex_a: "26163", hex_b: "06037"}

        first = _seed_balkanization_layer(state, hex_to_county=hex_to_county)
        second = _seed_balkanization_layer(state, hex_to_county=hex_to_county)

        first_influences = [r for r in first.relationships if r.edge_type == EdgeType.INFLUENCES]
        second_influences = [r for r in second.relationships if r.edge_type == EdgeType.INFLUENCES]
        assert first_influences == second_influences


@pytest.mark.unit
@pytest.mark.requires_reference_db
class TestSeedBalkanizationLayerCountyInfluencesRealDB:
    """#39 T5: the real ``bridge_county_h3`` end-to-end path.

    Excluded from CI (``requires_reference_db``); runs locally where
    ``data/sqlite/marxist-data-3NF.sqlite`` exists.
    """

    def test_us_scenario_county_territories_get_real_influences(self) -> None:
        from babylon.engine.scenarios._legacy import create_us_scenario
        from game.engine_bridge import _load_seed_hex_to_county_bridge

        state, _config, _defines = create_us_scenario()
        hex_to_county = _load_seed_hex_to_county_bridge()
        assert hex_to_county, "real bridge_county_h3 read returned nothing"

        seeded = _seed_balkanization_layer(state, hex_to_county=hex_to_county)

        influences = [r for r in seeded.relationships if r.edge_type == EdgeType.INFLUENCES]
        assert influences, "USScenario county territories must get a non-empty influence layer"
        assert {r.target_id for r in influences} <= set(seeded.territories)


@pytest.mark.unit
class TestLoadSeedHexToCountyBridgeDegradesGracefully:
    """#39 T5 blocker found during implementation: the reference SQLite is
    ABSENT (not just thin) on the dev CI tier by design (pyproject.toml's
    ``requires_reference_db`` marker doc), but ``_build_initial_state_for_scenario
    ("default"/"us")`` — county-grain since #39 T4 — is exercised by dozens
    of plain ``unit``-marked tests across the suite that never expected a DB
    dependency. Reproduced locally by pointing ``BABYLON_NORMALIZED_DB_PATH``
    at a nonexistent file: every one of those tests raised
    ``sqlite3.OperationalError: no such table: bridge_county_h3`` before this
    guard existed. ``_load_seed_hex_to_county_bridge`` must degrade to ``{}``
    (the pre-existing county-influence no-op), loudly logged, never let a DB
    hiccup take an entire session build down with it.

    T5 review I1: that degradation is legitimate ONLY when the reference DB
    file is genuinely absent (the CI/unit-tier case above). A file that
    EXISTS but is broken (corrupt, locked, missing the table) is a real
    production fault and must propagate loud (Constitution III.11), never
    collapse into the same silent no-op — the two tests below pin both
    halves of that boundary.
    """

    def test_missing_db_file_degrades_to_empty_mapping(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        import logging

        import babylon.reference.database as database_module
        from game.engine_bridge import _load_seed_hex_to_county_bridge

        missing_path = tmp_path / "does_not_exist.sqlite"
        monkeypatch.setattr(database_module, "NORMALIZED_DB_PATH", missing_path)

        with caplog.at_level(logging.WARNING):
            result = _load_seed_hex_to_county_bridge()

        assert result == {}
        assert any("reference DB file absent" in record.message for record in caplog.records), (
            f"expected a loud WARNING naming the absent DB file, got: {caplog.records}"
        )

    def test_present_but_broken_db_raises(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A DB file that EXISTS but lacks ``bridge_county_h3``/``dim_county``
        (e.g. a fresh, empty SQLite file) is the "present but broken" case
        I1 distinguishes from "absent" — it must raise, never degrade to
        the no-op, because the file genuinely being there but unusable is
        exactly the production fault (corruption/locks/schema drift) the
        old blanket ``except OperationalError`` used to mute."""
        import sqlite3

        from sqlalchemy.exc import OperationalError

        import babylon.reference.database as database_module
        from game.engine_bridge import _load_seed_hex_to_county_bridge

        broken_path = tmp_path / "empty_no_table.sqlite"
        # A genuinely valid, connectable SQLite file that simply has none
        # of the normalized schema's tables.
        sqlite3.connect(str(broken_path)).close()

        monkeypatch.setattr(database_module, "NORMALIZED_DB_PATH", broken_path)
        monkeypatch.setattr(database_module, "NORMALIZED_DATABASE_URL", f"sqlite:///{broken_path}")
        # normalized_engine()/get_normalized_session_factory() memoize into
        # these module globals on first use anywhere in the test process;
        # reset them so this test's engine is actually bound to broken_path
        # instead of reusing whatever the reference DB already resolved to.
        # monkeypatch restores both to their prior value on teardown.
        monkeypatch.setattr(database_module, "_normalized_engine", None)
        monkeypatch.setattr(database_module, "_NormalizedSessionLocal", None)

        # SQLAlchemy wraps the raw sqlite3.OperationalError ("no such
        # table: bridge_county_h3") in its own exception type; the original
        # driver exception is chained on .orig.
        with pytest.raises(OperationalError):
            _load_seed_hex_to_county_bridge()
