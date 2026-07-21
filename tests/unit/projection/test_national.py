"""Contract tests for :func:`babylon.projection.national.project_national`.

The national read-model's behavioral contract: population-weighted rollups
one tier above the county dossier, honest ``None`` for every unattributed
quantity, an injected ``NationalValueAggregate`` row (never a Postgres
read of its own) for the six value-composition fields, deterministic
output. Fixture-fed — no engine tick, no database — per the keel's
fixture-first discipline; a plain in-memory ``NationalValueAggregate`` is
constructed directly where needed (a Pydantic model, not a DB read).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.enums import SocialRole
from babylon.models.enums.topology import EdgeType, NodeType
from babylon.models.world_state import WorldState
from babylon.persistence.county_aggregation import _ideology_to_ternary
from babylon.persistence.postgres_aggregation import NationalValueAggregate
from babylon.projection.fixtures.recorder import load_national_fixture, record_national_fixture
from babylon.projection.national import national_statblocks, project_national
from babylon.topology import BabylonGraph

WAYNE = "26163"
OAKLAND = "26125"
SESSION_ID = "b26163b2-0000-4000-8000-000000000001"

_WAYNE_DISTRIBUTION = {
    "bourgeoisie": 0.077,
    "petit_bourgeoisie": 0.191,
    "labor_aristocracy": 0.226,
    "proletariat": 0.382,
    "lumpenproletariat": 0.124,
}

_OAKLAND_DISTRIBUTION = {
    "bourgeoisie": 0.10,
    "petit_bourgeoisie": 0.20,
    "labor_aristocracy": 0.30,
    "proletariat": 0.30,
    "lumpenproletariat": 0.10,
}


def _make_entity(
    eid: str,
    *,
    county_fips: str | None,
    population: int = 100,
    p_acquiescence: float = 0.5,
    p_revolution: float = 0.3,
    class_consciousness: float = 0.5,
    national_identity: float = 0.5,
) -> SocialClass:
    """Build a SocialClass with the spec-065 attribution fields set."""
    return SocialClass(
        id=eid,
        name=f"Test {eid}",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=1.0,
        ideology=IdeologicalProfile(
            class_consciousness=class_consciousness,
            national_identity=national_identity,
        ),
        p_acquiescence=p_acquiescence,
        p_revolution=p_revolution,
        population=population,
        county_fips=county_fips,
    )


def _world(*entities: SocialClass) -> WorldState:
    """Wrap entities in a minimal WorldState."""
    return WorldState(entities={entity.id: entity for entity in entities})


def _two_county_graph() -> BabylonGraph:
    """A graph with Wayne and Oakland territories, both under one sovereign."""
    graph = BabylonGraph()
    graph.add_node(
        "T001",
        NodeType.TERRITORY,
        county_fips=WAYNE,
        tick_median_wage=19.85,
        tick_bifurcation_score=-0.32,
        tick_class_distribution=dict(_WAYNE_DISTRIBUTION),
        legitimation_index=0.71,
    )
    graph.add_node(
        "T002",
        NodeType.TERRITORY,
        county_fips=OAKLAND,
        tick_median_wage=25.00,
        tick_bifurcation_score=0.10,
        tick_class_distribution=dict(_OAKLAND_DISTRIBUTION),
        legitimation_index=0.55,
    )
    graph.add_node("SOV_USA", NodeType.SOVEREIGN, name="United States")
    graph.add_edge("SOV_USA", "T001", EdgeType.CLAIMS)
    graph.add_edge("SOV_USA", "T002", EdgeType.CLAIMS)
    return graph


class TestFullDossier:
    """Every field populated when every producer has attributed data."""

    def test_projects_every_field(self) -> None:
        """A fully-attributed two-county nation yields a dossier with no absences."""
        world = _world(
            _make_entity(
                "C001",
                county_fips=WAYNE,
                population=300,
                p_acquiescence=0.61,
                p_revolution=0.44,
                class_consciousness=0.8,
                national_identity=0.1,
            ),
            _make_entity(
                "C002",
                county_fips=OAKLAND,
                population=100,
                p_acquiescence=0.9,
                p_revolution=0.1,
                class_consciousness=0.2,
                national_identity=0.6,
            ),
        )
        view = project_national("USA", graph=_two_county_graph(), world=world, tick=847)

        assert view.national_id == "USA"
        assert view.verified_tick == 847
        assert view.population == 400
        assert view.median_wage == pytest.approx((19.85 * 300 + 25.00 * 100) / 400)
        assert view.bifurcation_score == pytest.approx((-0.32 * 300 + 0.10 * 100) / 400)
        assert view.legitimacy == pytest.approx((0.71 * 300 + 0.55 * 100) / 400)
        assert view.sovereign_id == "SOV_USA"
        assert view.class_composition is not None
        assert view.class_composition.proletariat == pytest.approx((0.382 * 300 + 0.30 * 100) / 400)
        assert view.imperial_rent_pool == pytest.approx(100.0)  # GlobalEconomy default

    def test_survival_means_are_population_weighted(self) -> None:
        """P(S|A)/P(S|R) match the pop-weighted combination across both counties."""
        world = _world(
            _make_entity(
                "C001", county_fips=WAYNE, population=300, p_acquiescence=0.6, p_revolution=0.4
            ),
            _make_entity(
                "C002", county_fips=OAKLAND, population=100, p_acquiescence=1.0, p_revolution=0.0
            ),
        )
        view = project_national("USA", graph=_two_county_graph(), world=world, tick=1)

        assert view.p_acquiescence == pytest.approx((0.6 * 300 + 1.0 * 100) / 400)
        assert view.p_revolution == pytest.approx((0.4 * 300 + 0.0 * 100) / 400)

    def test_consciousness_matches_pop_weighted_bridge_mapping(self) -> None:
        """The simplex equals the pop-weighted ideology bridge mapping across counties."""
        world = _world(
            _make_entity(
                "C001",
                county_fips=WAYNE,
                population=300,
                class_consciousness=0.8,
                national_identity=0.1,
            ),
            _make_entity(
                "C002",
                county_fips=OAKLAND,
                population=100,
                class_consciousness=0.2,
                national_identity=0.6,
            ),
        )
        view = project_national("USA", graph=_two_county_graph(), world=world, tick=1)
        r1, l1, f1 = _ideology_to_ternary(0.8, 0.1)
        r2, l2, f2 = _ideology_to_ternary(0.2, 0.6)

        assert view.consciousness is not None
        assert view.consciousness.revolutionary == pytest.approx((r1 * 300 + r2 * 100) / 400)
        assert view.consciousness.liberal == pytest.approx((l1 * 300 + l2 * 100) / 400)
        assert view.consciousness.fascist == pytest.approx((f1 * 300 + f2 * 100) / 400)

    def test_value_aggregate_fields_project_when_injected(self) -> None:
        """c_sum..hex_count hydrate from an explicitly-injected NationalValueAggregate."""
        aggregate = NationalValueAggregate(
            session_id=SESSION_ID,
            tick=1,
            national_id="USA",
            c_sum=1000.0,
            v_sum=500.0,
            s_sum=250.0,
            k_sum=2000.0,
            biocapacity_sum=750.0,
            hex_count=42,
        )
        view = project_national(
            "USA",
            graph=BabylonGraph(),
            world=_world(),
            tick=1,
            national_aggregate=aggregate,
        )

        assert view.c_sum == pytest.approx(1000.0)
        assert view.v_sum == pytest.approx(500.0)
        assert view.s_sum == pytest.approx(250.0)
        assert view.k_sum == pytest.approx(2000.0)
        assert view.biocapacity_sum == pytest.approx(750.0)
        assert view.hex_count == 42


class TestHonestAbsence:
    """Missing producers project as None — never a default (III.11)."""

    def test_bare_graph_yields_none_fields(self) -> None:
        """No territories, no entities: every rollup projects None."""
        view = project_national("USA", graph=BabylonGraph(), world=_world(), tick=5)

        assert view.population is None
        assert view.median_wage is None
        assert view.bifurcation_score is None
        assert view.legitimacy is None
        assert view.class_composition is None
        assert view.consciousness is None
        assert view.p_acquiescence is None
        assert view.p_revolution is None
        assert view.sovereign_id is None
        assert view.c_sum is None
        assert view.v_sum is None
        assert view.s_sum is None
        assert view.k_sum is None
        assert view.biocapacity_sum is None
        assert view.hex_count is None

    def test_imperial_rent_pool_is_never_absent(self) -> None:
        """The Gas Tank stock is always present, even with an otherwise-bare world."""
        view = project_national("USA", graph=BabylonGraph(), world=_world(), tick=5)

        assert view.imperial_rent_pool == pytest.approx(100.0)

    def test_no_claims_yields_no_sovereign(self) -> None:
        """Territories exist but nothing claims them: sovereign_id is None."""
        graph = BabylonGraph()
        graph.add_node("T001", NodeType.TERRITORY, county_fips=WAYNE)
        view = project_national("USA", graph=graph, world=_world(), tick=5)

        assert view.sovereign_id is None

    def test_balkanized_nation_has_no_single_sovereign(self) -> None:
        """Two distinct sovereigns claiming different territories: sovereign_id is None."""
        graph = BabylonGraph()
        graph.add_node("T001", NodeType.TERRITORY, county_fips=WAYNE)
        graph.add_node("T002", NodeType.TERRITORY, county_fips=OAKLAND)
        graph.add_node("SOV_USA", NodeType.SOVEREIGN, name="United States")
        graph.add_node("SOV_RED_OGV", NodeType.SOVEREIGN, name="Red OGV")
        graph.add_edge("SOV_USA", "T001", EdgeType.CLAIMS)
        graph.add_edge("SOV_RED_OGV", "T002", EdgeType.CLAIMS)
        view = project_national("USA", graph=graph, world=_world(), tick=5)

        assert view.sovereign_id is None

    def test_unattributed_territory_does_not_skew_the_rollup(self) -> None:
        """A territory whose county has no attributed entities contributes zero weight."""
        graph = _two_county_graph()
        graph.add_node(
            "T003",
            NodeType.TERRITORY,
            county_fips="26099",
            tick_median_wage=999.0,
        )
        world = _world(_make_entity("C001", county_fips=WAYNE, population=300))
        view = project_national("USA", graph=graph, world=world, tick=5)

        assert view.median_wage == pytest.approx(19.85)


class TestLoudFailure:
    """A present-but-wrong value raises; only a missing one is absence."""

    def test_malformed_class_distribution_raises(self) -> None:
        """A distribution dict with missing shares fails validation loudly."""
        graph = BabylonGraph()
        graph.add_node(
            "T001",
            NodeType.TERRITORY,
            county_fips=WAYNE,
            tick_class_distribution={"proletariat": 1.0},
        )
        world = _world(_make_entity("C001", county_fips=WAYNE, population=100))
        with pytest.raises(ValidationError):
            project_national("USA", graph=graph, world=world, tick=1)

    def test_mismatched_aggregate_national_id_raises(self) -> None:
        """An injected aggregate for a different nation is a caller bug, surfaced loud."""
        aggregate = NationalValueAggregate(
            session_id=SESSION_ID,
            tick=1,
            national_id="NOT_USA",
            c_sum=1.0,
            v_sum=1.0,
            s_sum=1.0,
            k_sum=1.0,
            biocapacity_sum=1.0,
            hex_count=1,
        )
        with pytest.raises(ValueError, match="national_id"):
            project_national(
                "USA", graph=BabylonGraph(), world=_world(), tick=1, national_aggregate=aggregate
            )

    def test_mismatched_aggregate_tick_raises(self) -> None:
        """An injected aggregate for a different tick is a caller bug, surfaced loud."""
        aggregate = NationalValueAggregate(
            session_id=SESSION_ID,
            tick=2,
            national_id="USA",
            c_sum=1.0,
            v_sum=1.0,
            s_sum=1.0,
            k_sum=1.0,
            biocapacity_sum=1.0,
            hex_count=1,
        )
        with pytest.raises(ValueError, match="tick"):
            project_national(
                "USA", graph=BabylonGraph(), world=_world(), tick=1, national_aggregate=aggregate
            )


class TestDeterminism:
    """Identical inputs yield identical frozen dossiers."""

    def test_double_projection_is_identical(self) -> None:
        """Two projections of the same state compare equal."""
        world = _world(_make_entity("C001", county_fips=WAYNE, population=100))
        graph = _two_county_graph()

        first = project_national("USA", graph=graph, world=world, tick=847)
        second = project_national("USA", graph=graph, world=world, tick=847)

        assert first == second
        assert first.model_dump() == second.model_dump()


class TestFixtureRoundTrip:
    """The recorder round-trips a NationalView byte-identically (mirrors CountyView's)."""

    def test_round_trips_to_an_equal_view(self, tmp_path: Path) -> None:
        world = _world(_make_entity("C001", county_fips=WAYNE, population=100))
        view = project_national("USA", graph=_two_county_graph(), world=world, tick=847)
        path = tmp_path / "national.json"

        record_national_fixture(view, path)
        loaded = load_national_fixture(path)

        assert loaded == view
        assert loaded.model_dump() == view.model_dump()

    def test_recording_twice_is_byte_identical(self, tmp_path: Path) -> None:
        world = _world(_make_entity("C001", county_fips=WAYNE, population=100))
        view = project_national("USA", graph=_two_county_graph(), world=world, tick=847)
        first_path = tmp_path / "first.json"
        second_path = tmp_path / "second.json"

        record_national_fixture(view, first_path)
        record_national_fixture(view, second_path)

        assert first_path.read_bytes() == second_path.read_bytes()

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_national_fixture(tmp_path / "does_not_exist.json")


class TestCommittedFixture:
    """The WO-17 harvester's committed fixture stays present and well-shaped."""

    _COMMITTED_FIXTURE = (
        Path(__file__).parent.parent.parent / "fixtures" / "projection" / "national_USA.json"
    )

    def test_committed_fixture_is_present_and_well_shaped(self) -> None:
        """The shipped fixture loads, names the right nation, and has a valid tick."""
        assert self._COMMITTED_FIXTURE.is_file(), (
            f"committed projection fixture missing: {self._COMMITTED_FIXTURE} — "
            "regenerate via `uv run python tools/record_national_fixture.py`"
        )

        view = load_national_fixture(self._COMMITTED_FIXTURE)

        assert view.national_id == "USA"
        assert view.verified_tick >= 0


class TestNationalStatblocks:
    """The live per-kind statblock provider (Wave-1 shared-file discipline)."""

    def test_known_subject_resolves_rows(self) -> None:
        world = _world(_make_entity("C001", county_fips=WAYNE, population=100))
        view = project_national("USA", graph=_two_county_graph(), world=world, tick=1)
        provider = national_statblocks({"national/USA": view})

        rows = provider("national/USA")

        assert rows is not None
        assert ("population", "100") in rows
        assert any(label == "sovereign_id" for label, _ in rows)

    def test_unknown_subject_is_honest_absence(self) -> None:
        provider = national_statblocks({})

        assert provider("national/does-not-exist") is None
