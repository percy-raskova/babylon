"""Contract tests for :func:`babylon.projection.faction.project_faction`.

The faction read-model's behavioral contract: one producer per field,
honest ``None`` for every unattributed or nonexistent quantity, deterministic
output. Fixture-fed — no engine tick, no database — per the keel's
fixture-first discipline. Mirrors ``tests/unit/projection/test_sovereign.py``
exactly (T3 U4 shares the same recipe as WO-20's ``project_sovereign``).

The HONEST-EMPTY case (``TestNoScenarioSeedsFactions``) pins down a real
production fact: no ``babylon.engine.scenarios`` builder ever constructs a
``BalkanizationFaction`` or populates ``WorldState.factions`` today — only
the legacy web bridge's ``_seed_balkanization_layer`` does (Bridge-layer
only). A graph with zero faction nodes is exactly what every real headless
campaign bakes, and ``project_faction`` must still return a valid,
all-absent dossier for it — never a crash.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.enums.topology import EdgeType, NodeType
from babylon.models.world_state import WorldState
from babylon.projection.faction import faction_statblocks, project_faction
from babylon.topology import BabylonGraph

FAC_RESTORATIONIST = "FAC_RESTORATIONIST"


def _full_graph() -> BabylonGraph:
    """A faction influencing two territories, at differing intensities."""
    graph = BabylonGraph()
    graph.add_node(
        FAC_RESTORATIONIST,
        NodeType.FACTION,
        name="Restorationist Coalition",
        ideology="settler-restorationism",
        colonial_stance="uphold",
        is_settler_formation=True,
        extraction_modifier=1.2,
        violence_modifier=1.1,
        class_reduction=0.3,
        metabolic_reduction=-0.2,
        color_hex="#AA0000",
        founded_tick=0,
    )
    graph.add_node("T001", NodeType.TERRITORY, county_fips="26163")
    graph.add_node("T002", NodeType.TERRITORY, county_fips="26125")
    graph.add_edge(
        FAC_RESTORATIONIST,
        "T001",
        EdgeType.INFLUENCES,
        influence_level=0.7,
        support_type="labor",
    )
    graph.add_edge(
        FAC_RESTORATIONIST,
        "T002",
        EdgeType.INFLUENCES,
        influence_level=0.4,
        support_type="ideological",
    )
    return graph


def _world() -> WorldState:
    """Faction fields are all graph-sourced; the world is never consulted."""
    return WorldState()


class TestFullDossier:
    """Every field populated when every producer has attributed data."""

    def test_projects_every_field(self) -> None:
        """A fully-attributed faction yields a dossier with no absences."""
        view = project_faction(FAC_RESTORATIONIST, graph=_full_graph(), world=_world(), tick=847)

        assert view.faction_id == FAC_RESTORATIONIST
        assert view.verified_tick == 847
        assert view.name == "Restorationist Coalition"
        assert view.ideology == "settler-restorationism"
        assert view.colonial_stance is not None
        assert view.colonial_stance.value == "uphold"
        assert view.is_settler_formation is True
        assert view.extraction_modifier == pytest.approx(1.2)
        assert view.violence_modifier == pytest.approx(1.1)
        assert view.class_reduction == pytest.approx(0.3)
        assert view.metabolic_reduction == pytest.approx(-0.2)
        assert view.color_hex == "#AA0000"
        assert view.founded_tick == 0
        assert view.dissolved_tick is None

    def test_territory_influence_is_sorted_by_level_descending(self) -> None:
        """INFLUENCES-derived rows come back highest-influence-first."""
        view = project_faction(FAC_RESTORATIONIST, graph=_full_graph(), world=_world(), tick=1)

        assert view.territory_influence is not None
        assert [row.territory_id for row in view.territory_influence] == ["T001", "T002"]
        assert view.territory_influence[0].influence_level == pytest.approx(0.7)
        assert view.territory_influence[0].county_fips == "26163"
        assert view.territory_influence[0].support_type == "labor"
        assert view.territory_influence[1].county_fips == "26125"
        assert view.territory_influence[1].support_type == "ideological"

    def test_territory_influence_ignores_other_factions_edges(self) -> None:
        """Only this faction's own INFLUENCES edges are counted."""
        graph = _full_graph()
        graph.add_node("FAC_RIVAL", NodeType.FACTION, name="Rival")
        graph.add_node("T003", NodeType.TERRITORY, county_fips="26099")
        graph.add_edge("FAC_RIVAL", "T003", EdgeType.INFLUENCES, influence_level=0.9)

        view = project_faction(FAC_RESTORATIONIST, graph=graph, world=_world(), tick=1)

        assert view.territory_influence is not None
        territory_ids = [row.territory_id for row in view.territory_influence]
        assert "T003" not in territory_ids
        assert territory_ids == ["T001", "T002"]


class TestHonestAbsence:
    """Missing producers project as None — never a default (III.11)."""

    def test_unknown_faction_id_yields_all_none(self) -> None:
        """A faction id with no matching graph node projects every field None."""
        graph = _full_graph()
        view = project_faction("FAC_NOPE", graph=graph, world=_world(), tick=5)

        assert view.name is None
        assert view.ideology is None
        assert view.colonial_stance is None
        assert view.is_settler_formation is None
        assert view.extraction_modifier is None
        assert view.violence_modifier is None
        assert view.class_reduction is None
        assert view.metabolic_reduction is None
        assert view.color_hex is None
        assert view.founded_tick is None
        assert view.dissolved_tick is None
        # territory_influence is None here -- "this faction doesn't exist" --
        # never confused with the empty-tuple "exists but influences nothing".
        assert view.territory_influence is None

    def test_empty_graph_yields_all_none(self) -> None:
        """No territory node at all still projects a valid, all-absent dossier."""
        view = project_faction(FAC_RESTORATIONIST, graph=BabylonGraph(), world=_world(), tick=9)

        assert view.faction_id == FAC_RESTORATIONIST
        assert view.name is None
        assert view.territory_influence is None

    def test_faction_with_no_influence_has_empty_but_present_tuple(self) -> None:
        """A real faction that currently influences nothing gets () -- not None."""
        graph = BabylonGraph()
        graph.add_node(FAC_RESTORATIONIST, NodeType.FACTION, name="Restorationist Coalition")

        view = project_faction(FAC_RESTORATIONIST, graph=graph, world=_world(), tick=5)

        assert view.name == "Restorationist Coalition"
        assert view.territory_influence == ()
        assert view.territory_influence is not None

    def test_influenced_territory_with_no_county_fips_projects_none_county(self) -> None:
        """An influenced territory carrying no county_fips yields None, not KeyError."""
        graph = BabylonGraph()
        graph.add_node(FAC_RESTORATIONIST, NodeType.FACTION)
        graph.add_node("T_BARE", NodeType.TERRITORY)
        graph.add_edge(FAC_RESTORATIONIST, "T_BARE", EdgeType.INFLUENCES, influence_level=0.5)

        view = project_faction(FAC_RESTORATIONIST, graph=graph, world=_world(), tick=5)

        assert view.territory_influence is not None
        assert view.territory_influence[0].territory_id == "T_BARE"
        assert view.territory_influence[0].county_fips is None

    def test_a_node_id_collision_with_a_non_faction_type_projects_absence(self) -> None:
        """An id that resolves to a node of a different type is not this faction."""
        graph = BabylonGraph()
        graph.add_node(FAC_RESTORATIONIST, NodeType.TERRITORY, county_fips="26163")

        view = project_faction(FAC_RESTORATIONIST, graph=graph, world=_world(), tick=5)

        assert view.name is None
        assert view.territory_influence is None


class TestNoScenarioSeedsFactions:
    """The HONEST-EMPTY case: no engine scenario seeds FACTION nodes today.

    Only the legacy web bridge's ``_seed_balkanization_layer`` does
    (Bridge-layer only, owner item 8) -- a real headless campaign's graph
    has zero faction nodes, and this projector must handle that gracefully
    rather than assume at least one faction always exists.
    """

    def test_empty_graph_with_no_faction_nodes_at_all(self) -> None:
        """A graph with no faction node whatsoever still yields a valid dossier."""
        graph = BabylonGraph()
        graph.add_node("T001", NodeType.TERRITORY, county_fips="26163")

        view = project_faction("FAC_ANY", graph=graph, world=_world(), tick=520)

        assert view.faction_id == "FAC_ANY"
        assert view.verified_tick == 520
        assert view.name is None
        assert view.territory_influence is None


class TestLoudFailure:
    """A present-but-wrong value raises; only a missing one is absence."""

    def test_malformed_colonial_stance_raises(self) -> None:
        """An unrecognized colonial_stance string fails validation loudly."""
        graph = BabylonGraph()
        graph.add_node(FAC_RESTORATIONIST, NodeType.FACTION, colonial_stance="not_a_real_stance")

        with pytest.raises(ValidationError):
            project_faction(FAC_RESTORATIONIST, graph=graph, world=_world(), tick=1)

    def test_class_reduction_out_of_probability_range_raises(self) -> None:
        """A class_reduction outside [0, 1] fails validation loudly."""
        graph = BabylonGraph()
        graph.add_node(FAC_RESTORATIONIST, NodeType.FACTION, class_reduction=1.5)

        with pytest.raises(ValidationError):
            project_faction(FAC_RESTORATIONIST, graph=graph, world=_world(), tick=1)

    def test_malformed_color_hex_raises(self) -> None:
        """A color_hex not matching #RRGGBB fails validation loudly."""
        graph = BabylonGraph()
        graph.add_node(FAC_RESTORATIONIST, NodeType.FACTION, color_hex="not-a-color")

        with pytest.raises(ValidationError):
            project_faction(FAC_RESTORATIONIST, graph=graph, world=_world(), tick=1)


class TestDeterminism:
    """Identical inputs yield identical frozen dossiers."""

    def test_double_projection_is_identical(self) -> None:
        """Two projections of the same state compare equal."""
        graph = _full_graph()

        first = project_faction(FAC_RESTORATIONIST, graph=graph, world=_world(), tick=847)
        second = project_faction(FAC_RESTORATIONIST, graph=graph, world=_world(), tick=847)

        assert first == second
        assert first.model_dump() == second.model_dump()


class TestFactionStatblocks:
    """The WO-45 composition seam: a live, per-kind statblock provider."""

    def test_it_resolves_a_known_faction_subject_to_rows(self) -> None:
        provider = faction_statblocks(graph=_full_graph(), world=_world(), tick=5)

        rows = provider("faction/FAC_RESTORATIONIST")

        assert rows is not None
        assert ("name", "Restorationist Coalition") in rows

    def test_it_returns_none_for_an_unknown_faction_id(self) -> None:
        provider = faction_statblocks(graph=_full_graph(), world=_world(), tick=5)

        assert provider("faction/FAC_NOPE") is None

    def test_it_returns_none_for_a_non_faction_subject(self) -> None:
        """A ``sovereign/*`` (or any other kind's) subject is not this provider's concern."""
        provider = faction_statblocks(graph=_full_graph(), world=_world(), tick=5)

        assert provider("sovereign/SOV_USA_FED") is None

    def test_rows_match_the_baked_render_pathway(self) -> None:
        """The live provider and render_faction never disagree on row content."""
        from babylon.projection.vault.render_faction import faction_statblock_rows

        graph = _full_graph()
        provider = faction_statblocks(graph=graph, world=_world(), tick=5)
        view = project_faction(FAC_RESTORATIONIST, graph=graph, world=_world(), tick=5)

        assert provider("faction/FAC_RESTORATIONIST") == list(faction_statblock_rows(view))
