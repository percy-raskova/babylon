"""Unit tests for the web bridge's ``_seed_balkanization_layer`` delegate.

P25 U6 (ADR132): the seeding logic lives in
``babylon.engine.scenarios.balkanization_seed.apply_balkanization_seed``
(full behavioral contract:
``tests/unit/engine/scenarios/test_balkanization_seed.py``); the bridge keeps
a thin wrapper plus the wayne-specific ordering rule (county-FIPS stamp
BEFORE seeding, so wayne's 81 hex territories resolve the county-keyed seed
directly — the old hex-parent aggregation and the ``bridge_county_h3``
reference-DB read are retired, and the whole session build is DB-free).

These tests pin the BRIDGE-facing consequences: FR-040b claims coverage on
the wayne scenario, the stamped-wayne influence broadcast, and the county
scenario's direct resolution.
"""

from __future__ import annotations

import pytest

from babylon.engine.scenarios._legacy_wayne import create_wayne_county_scenario
from babylon.models.entities.territory import Territory
from babylon.models.enums import EdgeType, SectorType
from babylon.models.world_state import WorldState
from game.engine_bridge import (
    _build_initial_state_for_scenario,
    _seed_balkanization_layer,
    _seed_wayne_county_fips,
)

pytestmark = pytest.mark.unit

_WAYNE_FIPS = "26163"


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


def _wayne_seed_values() -> dict[str, tuple[float, str]]:
    """The committed seed's Wayne County rows — the independent oracle."""
    from babylon.data.game.balkanization import load_seed_influences

    return {
        str(e["faction_id"]): (float(e["influence_level"]), str(e["support_type"]))
        for e in load_seed_influences()
        if str(e["territory_id"]) == _WAYNE_FIPS
    }


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
        """Task R / ADR080: an UNSTAMPED wayne state (hex territories, no
        county_fips, no map) resolves nothing literally, so every territory
        falls to the FR-040b fallback — which routes to the domestic federal
        sovereign ``SOV_USA_FED``, never the provisional exterior-null
        sovereign."""
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
class TestWayneStampThenSeedOrdering:
    """P25 U6: the production ordering (FIPS stamp -> seed) makes wayne's
    hex territories resolve the county-keyed seed directly."""

    def test_unstamped_wayne_gets_no_influences(self) -> None:
        """Without the stamp (and without a hex_to_county map) the county-
        keyed seed has nothing to bind to — the retired hex-parent
        aggregation is really gone."""
        state = _build_state()

        seeded = _seed_balkanization_layer(state)

        influences = [r for r in seeded.relationships if r.edge_type == EdgeType.INFLUENCES]
        assert influences == []

    def test_stamped_wayne_broadcasts_the_county_values(self) -> None:
        """The production order (mirroring ``_build_initial_state_for_
        scenario``): every stamped wayne territory receives Wayne County's
        exact seed values — an intensive broadcast, verified against the
        raw seed file (independent oracle, never production's own loop)."""
        state = _seed_wayne_county_fips(_build_state())

        seeded = _seed_balkanization_layer(state)

        influences = [r for r in seeded.relationships if r.edge_type == EdgeType.INFLUENCES]
        assert influences, "stamped wayne territories must bind the county-keyed seed"
        assert {r.target_id for r in influences} == set(seeded.territories)

        expected = _wayne_seed_values()
        for rel in influences:
            level, support = expected[rel.source_id]
            assert rel.influence_level == pytest.approx(level)
            assert rel.support_type == support

    def test_build_initial_state_seeds_wayne_with_influences(self) -> None:
        """The real call boundary: a wayne_county session build carries the
        full political layer with per-territory influence — no reference-DB
        read anywhere on the path."""
        state = _build_initial_state_for_scenario("wayne_county")

        assert len(state.factions) == 4
        assert len(state.sovereigns) == 3
        influences = [r for r in state.relationships if r.edge_type == EdgeType.INFLUENCES]
        assert {r.target_id for r in influences} == set(state.territories)
        claims = [r for r in state.relationships if r.edge_type == EdgeType.CLAIMS]
        assert sorted(r.target_id for r in claims) == sorted(state.territories)


@pytest.mark.unit
class TestCountyGrainDirectResolution:
    """County-grain (T4-shaped) territories resolve the seed directly by
    their ``county_fips`` attribute — no map, no DB."""

    def test_county_keyed_territory_gets_the_seed_rows(self) -> None:
        state = WorldState(
            territories={
                "T0001": _county_territory("T0001", _WAYNE_FIPS),
                "T0002": _county_territory("T0002", "06037"),  # not in the tri-county seed
            }
        )

        seeded = _seed_balkanization_layer(state)

        influences = [r for r in seeded.relationships if r.edge_type == EdgeType.INFLUENCES]
        expected = _wayne_seed_values()
        actual = {
            (r.source_id, r.target_id): (r.influence_level, r.support_type) for r in influences
        }
        assert actual == {(faction, "T0001"): values for faction, values in expected.items()}

    def test_territory_with_neither_key_is_skipped(self) -> None:
        abstract_territory = Territory(
            id="T9999",
            name="Abstract (no county_fips, no h3_index)",
            sector_type=SectorType.INDUSTRIAL,
        )
        state = WorldState(
            territories={
                "T0001": _county_territory("T0001", _WAYNE_FIPS),
                "T9999": abstract_territory,
            }
        )

        seeded = _seed_balkanization_layer(state)

        influences = [r for r in seeded.relationships if r.edge_type == EdgeType.INFLUENCES]
        assert influences, "the county-keyed territory must still get influences"
        assert all(r.target_id != "T9999" for r in influences), (
            "a territory with neither h3_index nor county_fips must never be an INFLUENCES target"
        )
        # ...but SC-017 still holds: the abstract territory is claimed.
        claims = [r for r in seeded.relationships if r.edge_type == EdgeType.CLAIMS]
        assert {r.target_id for r in claims} == {"T0001", "T9999"}

    def test_seed_county_absent_from_scenario_is_dropped(self) -> None:
        """A seed county (Oakland/Macomb) with no matching scenario
        territory is silently skipped — never a loud error, never a
        fabricated territory."""
        state = WorldState(territories={"T0001": _county_territory("T0001", _WAYNE_FIPS)})

        seeded = _seed_balkanization_layer(state)

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
        state = WorldState(
            territories={
                "T0001": _county_territory("T0001", _WAYNE_FIPS),
                "T0002": _county_territory("T0002", "26125"),
            }
        )

        first = _seed_balkanization_layer(state)
        second = _seed_balkanization_layer(state)

        first_influences = [r for r in first.relationships if r.edge_type == EdgeType.INFLUENCES]
        second_influences = [r for r in second.relationships if r.edge_type == EdgeType.INFLUENCES]
        assert first_influences == second_influences


@pytest.mark.unit
class TestUSScenarioDirectResolution:
    """The national county-grain scenario binds the tri-county seed without
    any reference-DB read (the retired #39 T5 bridge read is gone — this
    used to be a ``requires_reference_db`` test)."""

    def test_us_scenario_tri_county_territories_get_real_influences(self) -> None:
        from babylon.engine.scenarios._legacy import create_us_scenario

        state, _config, _defines = create_us_scenario()

        seeded = _seed_balkanization_layer(state)

        influences = [r for r in seeded.relationships if r.edge_type == EdgeType.INFLUENCES]
        assert len(influences) == 12, "3 tri-county territories x 4 factions"
        assert {r.target_id for r in influences} <= set(seeded.territories)
        fips_by_territory = {
            tid: t.county_fips for tid, t in seeded.territories.items() if t.county_fips
        }
        assert {fips_by_territory[r.target_id] for r in influences} == {
            "26163",
            "26125",
            "26099",
        }
