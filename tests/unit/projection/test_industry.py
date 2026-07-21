"""Contract tests for :func:`babylon.projection.industry.project_industry`.

The industry read-model's behavioral contract: one producer per field (the
graph node itself), honest ``None`` for a missing node, deterministic output.
Fixture-fed — no engine tick, no database — per the keel's fixture-first
discipline.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.enums.topology import NodeType
from babylon.models.world_state import WorldState
from babylon.projection.industry import industry_statblocks, project_industry
from babylon.topology import BabylonGraph

IND_MANUFACTURING = "ind_31-33"

_WEIGHTS = {
    "dept_I": 0.4,
    "dept_IIa": 0.3,
    "dept_IIb": 0.2,
    "dept_III": 0.1,
}


def _full_graph() -> BabylonGraph:
    """A graph with one fully-attributed industry node."""
    graph = BabylonGraph()
    graph.add_node(
        IND_MANUFACTURING,
        NodeType.INDUSTRY,
        naics_2digit="31-33",
        naics_label="Manufacturing",
        department_weights=dict(_WEIGHTS),
        member_business_ids=frozenset({"org_ford", "org_gm"}),
        member_worker_block_ids=frozenset({"class_uaw"}),
        county_fips=frozenset({"26163", "26125"}),
        total_employment=2000,
        total_wages=100000.0,
        profit_rate=1.0 / 3.0,
        occ=2.0,
    )
    return graph


def _empty_world() -> WorldState:
    """A minimal WorldState — industry data never comes from entities."""
    return WorldState()


class TestFullDossier:
    """Every field populated when the industry node carries every attribute."""

    def test_projects_every_field(self) -> None:
        """A fully-attributed industry yields a dossier with no absences."""
        view = project_industry(
            IND_MANUFACTURING, graph=_full_graph(), world=_empty_world(), tick=847
        )

        assert view.industry_id == IND_MANUFACTURING
        assert view.verified_tick == 847
        assert view.naics_2digit == "31-33"
        assert view.naics_label == "Manufacturing"
        assert view.total_employment == 2000
        assert view.total_wages == pytest.approx(100000.0)
        assert view.profit_rate == pytest.approx(1.0 / 3.0)
        assert view.occ == pytest.approx(2.0)
        assert view.member_business_count == 2
        assert view.member_worker_block_count == 1
        assert view.county_fips == ("26125", "26163")  # sorted, deterministic

    def test_department_weights_match_the_source_dict(self) -> None:
        """The DepartmentComposition sub-model mirrors the raw node attribute."""
        view = project_industry(
            IND_MANUFACTURING, graph=_full_graph(), world=_empty_world(), tick=1
        )

        assert view.department_weights is not None
        assert view.department_weights.dept_I == pytest.approx(0.4)
        assert view.department_weights.dept_IIa == pytest.approx(0.3)
        assert view.department_weights.dept_IIb == pytest.approx(0.2)
        assert view.department_weights.dept_III == pytest.approx(0.1)


class TestHonestAbsence:
    """A missing industry node projects as None — never a default (III.11)."""

    def test_no_industry_node_yields_all_none_fields(self) -> None:
        """A graph with no matching node projects every non-identity field None."""
        view = project_industry(
            IND_MANUFACTURING, graph=BabylonGraph(), world=_empty_world(), tick=5
        )

        assert view.industry_id == IND_MANUFACTURING
        assert view.verified_tick == 5
        assert view.naics_2digit is None
        assert view.naics_label is None
        assert view.total_employment is None
        assert view.total_wages is None
        assert view.profit_rate is None
        assert view.occ is None
        assert view.department_weights is None
        assert view.member_business_count is None
        assert view.member_worker_block_count is None
        assert view.county_fips is None

    def test_a_node_of_a_different_type_with_the_same_id_is_not_mistaken_for_an_industry(
        self,
    ) -> None:
        """A same-id node of a different ``_node_type`` is honest absence, not a mismatch."""
        graph = BabylonGraph()
        graph.add_node(IND_MANUFACTURING, NodeType.TERRITORY, county_fips="26163")

        view = project_industry(IND_MANUFACTURING, graph=graph, world=_empty_world(), tick=1)

        assert view.naics_2digit is None
        assert view.county_fips is None

    def test_empty_membership_frozensets_project_as_zero_not_none(self) -> None:
        """A present-but-empty roster is a real zero, not absence."""
        graph = BabylonGraph()
        graph.add_node(
            IND_MANUFACTURING,
            NodeType.INDUSTRY,
            naics_2digit="31-33",
            naics_label="Manufacturing",
            department_weights=dict(_WEIGHTS),
            member_business_ids=frozenset(),
            member_worker_block_ids=frozenset(),
        )
        view = project_industry(IND_MANUFACTURING, graph=graph, world=_empty_world(), tick=1)

        assert view.member_business_count == 0
        assert view.member_worker_block_count == 0


class TestLoudFailure:
    """A present-but-wrong value raises; only a missing node is absence."""

    def test_malformed_department_weights_raises(self) -> None:
        """A department_weights dict with missing shares fails validation loudly."""
        graph = BabylonGraph()
        graph.add_node(
            IND_MANUFACTURING,
            NodeType.INDUSTRY,
            naics_2digit="31-33",
            naics_label="Manufacturing",
            department_weights={"dept_I": 1.0},
        )
        with pytest.raises(ValidationError):
            project_industry(IND_MANUFACTURING, graph=graph, world=_empty_world(), tick=1)


class TestDeterminism:
    """Identical inputs yield identical frozen dossiers."""

    def test_double_projection_is_identical(self) -> None:
        """Two projections of the same state compare equal."""
        graph = _full_graph()
        world = _empty_world()

        first = project_industry(IND_MANUFACTURING, graph=graph, world=world, tick=847)
        second = project_industry(IND_MANUFACTURING, graph=graph, world=world, tick=847)

        assert first == second
        assert first.model_dump() == second.model_dump()


class TestIndustryStatblocks:
    """The Wave-1 per-kind statblock provider (registered by WO-45, not here)."""

    def test_known_subject_returns_hardcoded_rows(self) -> None:
        rows = industry_statblocks("industry/ind_31-33")
        assert rows is not None
        assert ("naics_2digit", "31-33") in rows

    def test_unknown_subject_returns_none(self) -> None:
        assert industry_statblocks("industry/ind_99") is None
        assert industry_statblocks("county/26163") is None
