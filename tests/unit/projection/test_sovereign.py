"""Contract tests for :func:`babylon.projection.sovereign.project_sovereign`.

The sovereign read-model's behavioral contract: one producer per field,
honest ``None`` for every unattributed or nonexistent quantity, deterministic
output. Fixture-fed — no engine tick, no database — per the keel's
fixture-first discipline. Mirrors ``tests/unit/projection/test_county.py``
exactly (WO-20 shares the same recipe as WO-2's ``project_county``).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.enums.topology import EdgeType, NodeType
from babylon.models.world_state import WorldState
from babylon.projection.sovereign import project_sovereign, sovereign_statblocks
from babylon.topology import BabylonGraph

USA = "SOV_USA_FED"
FAC_RESTORATIONIST = "FAC_RESTORATIONIST"


def _full_graph() -> BabylonGraph:
    """A sovereign claiming two territories, with a capital in a third."""
    graph = BabylonGraph()
    graph.add_node(
        USA,
        NodeType.SOVEREIGN,
        name="United States Federal Government",
        sovereignty_type="recognized_state",
        legitimacy=0.82,
        ruling_faction_id=FAC_RESTORATIONIST,
        extraction_policy="intensify",
        capital_territory_id="T_DC",
        founded_tick=0,
    )
    graph.add_node("T001", NodeType.TERRITORY, county_fips="26163")
    graph.add_node("T002", NodeType.TERRITORY, county_fips="26125")
    graph.add_node("T_DC", NodeType.TERRITORY, county_fips="11001")
    graph.add_edge(USA, "T001", EdgeType.CLAIMS)
    graph.add_edge(USA, "T002", EdgeType.CLAIMS)
    return graph


def _world() -> WorldState:
    """Sovereign fields are all graph-sourced; the world is never consulted."""
    return WorldState()


class TestFullDossier:
    """Every field populated when every producer has attributed data."""

    def test_projects_every_field(self) -> None:
        """A fully-attributed sovereign yields a dossier with no absences."""
        view = project_sovereign(USA, graph=_full_graph(), world=_world(), tick=847)

        assert view.sovereign_id == USA
        assert view.verified_tick == 847
        assert view.name == "United States Federal Government"
        assert view.sovereignty_type is not None
        assert view.sovereignty_type.value == "recognized_state"
        assert view.legitimacy == pytest.approx(0.82)
        assert view.ruling_faction_id == FAC_RESTORATIONIST
        assert view.extraction_policy is not None
        assert view.extraction_policy.value == "intensify"
        assert view.capital_territory_id == "T_DC"
        assert view.capital_county_fips == "11001"
        assert view.founded_tick == 0
        assert view.dissolved_tick is None

    def test_claimed_county_fips_is_sorted_and_deduplicated(self) -> None:
        """CLAIMS-derived county FIPS come back sorted, regardless of edge order."""
        graph = _full_graph()
        # A duplicate CLAIMS edge to the same territory must not double the row.
        graph.add_edge(USA, "T001", EdgeType.CLAIMS)
        view = project_sovereign(USA, graph=graph, world=_world(), tick=1)

        assert view.claimed_county_fips == ("26125", "26163")

    def test_claimed_county_fips_ignores_other_sovereigns_claims(self) -> None:
        """Only this sovereign's own CLAIMS edges are counted."""
        graph = _full_graph()
        graph.add_node("SOV_RIVAL", NodeType.SOVEREIGN, name="Rival")
        graph.add_node("T003", NodeType.TERRITORY, county_fips="26099")
        graph.add_edge("SOV_RIVAL", "T003", EdgeType.CLAIMS)

        view = project_sovereign(USA, graph=graph, world=_world(), tick=1)

        assert view.claimed_county_fips == ("26125", "26163")
        assert "26099" not in (view.claimed_county_fips or ())


class TestHonestAbsence:
    """Missing producers project as None — never a default (III.11)."""

    def test_unknown_sovereign_id_yields_all_none(self) -> None:
        """A sovereign id with no matching graph node projects every field None."""
        graph = _full_graph()
        view = project_sovereign("SOV_NOPE", graph=graph, world=_world(), tick=5)

        assert view.name is None
        assert view.sovereignty_type is None
        assert view.legitimacy is None
        assert view.ruling_faction_id is None
        assert view.extraction_policy is None
        assert view.capital_territory_id is None
        assert view.capital_county_fips is None
        assert view.founded_tick is None
        assert view.dissolved_tick is None
        # claimed_county_fips is None here — "this sovereign doesn't exist" —
        # never confused with the empty-tuple "exists but claims nothing".
        assert view.claimed_county_fips is None

    def test_empty_graph_yields_all_none(self) -> None:
        """No territory node at all still projects a valid, all-absent dossier."""
        view = project_sovereign(USA, graph=BabylonGraph(), world=_world(), tick=9)

        assert view.sovereign_id == USA
        assert view.name is None
        assert view.claimed_county_fips is None

    def test_sovereign_with_no_claims_has_empty_but_present_claimed_county_fips(self) -> None:
        """A real sovereign that currently claims nothing gets () — not None."""
        graph = BabylonGraph()
        graph.add_node(USA, NodeType.SOVEREIGN, name="United States Federal Government")

        view = project_sovereign(USA, graph=graph, world=_world(), tick=5)

        assert view.name == "United States Federal Government"
        assert view.claimed_county_fips == ()
        assert view.claimed_county_fips is not None

    def test_missing_capital_territory_node_projects_none_county(self) -> None:
        """A capital_territory_id naming a nonexistent territory yields None, not a crash."""
        graph = BabylonGraph()
        graph.add_node(USA, NodeType.SOVEREIGN, capital_territory_id="T_GHOST")

        view = project_sovereign(USA, graph=graph, world=_world(), tick=5)

        assert view.capital_territory_id == "T_GHOST"
        assert view.capital_county_fips is None

    def test_capital_territory_with_no_county_fips_projects_none_county(self) -> None:
        """A capital territory that carries no county_fips yields None, not KeyError."""
        graph = BabylonGraph()
        graph.add_node(USA, NodeType.SOVEREIGN, capital_territory_id="T_BARE")
        graph.add_node("T_BARE", NodeType.TERRITORY)

        view = project_sovereign(USA, graph=graph, world=_world(), tick=5)

        assert view.capital_territory_id == "T_BARE"
        assert view.capital_county_fips is None

    def test_no_capital_territory_id_projects_none_for_both(self) -> None:
        """A sovereign that names no capital at all projects both fields None."""
        graph = BabylonGraph()
        graph.add_node(USA, NodeType.SOVEREIGN, name="United States Federal Government")

        view = project_sovereign(USA, graph=graph, world=_world(), tick=5)

        assert view.capital_territory_id is None
        assert view.capital_county_fips is None

    def test_a_node_id_collision_with_a_non_sovereign_type_projects_absence(self) -> None:
        """An id that resolves to a node of a different type is not this sovereign."""
        graph = BabylonGraph()
        graph.add_node(USA, NodeType.TERRITORY, county_fips="26163")

        view = project_sovereign(USA, graph=graph, world=_world(), tick=5)

        assert view.name is None
        assert view.claimed_county_fips is None


class TestLoudFailure:
    """A present-but-wrong value raises; only a missing one is absence."""

    def test_malformed_sovereignty_type_raises(self) -> None:
        """An unrecognized sovereignty_type string fails validation loudly."""
        graph = BabylonGraph()
        graph.add_node(USA, NodeType.SOVEREIGN, sovereignty_type="not_a_real_type")

        with pytest.raises(ValidationError):
            project_sovereign(USA, graph=graph, world=_world(), tick=1)

    def test_legitimacy_out_of_probability_range_raises(self) -> None:
        """A legitimacy outside [0, 1] fails validation loudly."""
        graph = BabylonGraph()
        graph.add_node(USA, NodeType.SOVEREIGN, legitimacy=1.5)

        with pytest.raises(ValidationError):
            project_sovereign(USA, graph=graph, world=_world(), tick=1)

    def test_malformed_ruling_faction_id_raises(self) -> None:
        """A ruling_faction_id not matching the FAC_* pattern fails loudly."""
        graph = BabylonGraph()
        graph.add_node(USA, NodeType.SOVEREIGN, ruling_faction_id="not-a-faction-id")

        with pytest.raises(ValidationError):
            project_sovereign(USA, graph=graph, world=_world(), tick=1)


class TestDeterminism:
    """Identical inputs yield identical frozen dossiers."""

    def test_double_projection_is_identical(self) -> None:
        """Two projections of the same state compare equal."""
        graph = _full_graph()

        first = project_sovereign(USA, graph=graph, world=_world(), tick=847)
        second = project_sovereign(USA, graph=graph, world=_world(), tick=847)

        assert first == second
        assert first.model_dump() == second.model_dump()


class TestSovereignStatblocks:
    """The WO-45 composition seam: a live, per-kind statblock provider."""

    def test_it_resolves_a_known_sovereign_subject_to_rows(self) -> None:
        provider = sovereign_statblocks(graph=_full_graph(), world=_world(), tick=5)

        rows = provider("sovereign/SOV_USA_FED")

        assert rows is not None
        assert ("name", "United States Federal Government") in rows

    def test_it_returns_none_for_an_unknown_sovereign_id(self) -> None:
        provider = sovereign_statblocks(graph=_full_graph(), world=_world(), tick=5)

        assert provider("sovereign/SOV_NOPE") is None

    def test_it_returns_none_for_a_non_sovereign_subject(self) -> None:
        """A ``county/*`` (or any other kind's) subject is not this provider's concern."""
        provider = sovereign_statblocks(graph=_full_graph(), world=_world(), tick=5)

        assert provider("county/26163") is None

    def test_rows_match_the_baked_render_pathway(self) -> None:
        """The live provider and render_sovereign never disagree on row content."""
        from babylon.projection.vault.render import sovereign_statblock_rows

        graph = _full_graph()
        provider = sovereign_statblocks(graph=graph, world=_world(), tick=5)
        view = project_sovereign(USA, graph=graph, world=_world(), tick=5)

        assert provider("sovereign/SOV_USA_FED") == list(sovereign_statblock_rows(view))
