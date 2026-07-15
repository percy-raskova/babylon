"""Unit tests for the partition sentinel (Program 19 Phase 1, ADR070).

The sixth sentinel: a declared crosswalk from derived class cells to the
seeded ``SocialRole`` vocabulary, plus a pure analyzer that turns a run's
per-tick ``pole_readings`` stashes into a :class:`PartitionReport` —
agreement rate, divergent nodes, unpositioned counts, multi-occupancy, and
side-flip counts. ADVISORY tier only in Phase 1: the DATA is the
deliverable, never a gate. The analyzer is engine-free (layer 0.5); the
engine-running harness lives in ``tools/partition_probe.py``.
"""

from __future__ import annotations

import pytest

from babylon.models.enums.social import SocialRole
from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.partition.checks import PartitionReport, analyze_partition
from babylon.sentinels.partition.registry import (
    CELL_AXIS_NAMES,
    CELL_TO_SEEDED_ROLES,
    KNOWN_CELLS,
    PRINCIPAL_AXES,
    cell_name,
)

pytestmark = pytest.mark.unit


def _stash(
    capital_labor: dict[str, str],
    wage: dict[str, str],
) -> dict[str, dict[str, dict[str, object]]]:
    """One tick's ``pole_readings`` dump: axis -> node -> reading dict."""
    return {
        "capital_labor": {
            node: {
                "opposition_key": "capital_labor",
                "entity_id": node,
                "side": side,
                "sigma": -0.5 if side == "a" else 0.5,
            }
            for node, side in capital_labor.items()
        },
        "wage": {
            node: {
                "opposition_key": "wage",
                "entity_id": node,
                "side": side,
                "sigma": -0.8 if side == "a" else 0.8,
            }
            for node, side in wage.items()
        },
    }


class TestRegistry:
    def test_known_cells_are_the_axis_product(self) -> None:
        assert (
            frozenset({"labor:exploited", "labor:bribed", "capital:exploited", "capital:bribed"})
            == KNOWN_CELLS
        )

    def test_crosswalk_covers_exactly_the_known_cells(self) -> None:
        assert frozenset(CELL_TO_SEEDED_ROLES) == KNOWN_CELLS

    def test_crosswalk_roles_are_valid_social_roles(self) -> None:
        valid = {role.value for role in SocialRole}
        for cell, roles in CELL_TO_SEEDED_ROLES.items():
            assert roles <= valid, f"{cell} names a non-SocialRole value"

    def test_cell_name_composes_both_axes(self) -> None:
        assert cell_name({"capital_labor": "a", "wage": "a"}) == "labor:exploited"
        assert cell_name({"capital_labor": "a", "wage": "b"}) == "labor:bribed"
        assert cell_name({"capital_labor": "b", "wage": "a"}) == "capital:exploited"
        assert cell_name({"capital_labor": "b", "wage": "b"}) == "capital:bribed"

    def test_cell_name_is_none_without_both_axes(self) -> None:
        assert cell_name({"capital_labor": "a"}) is None
        assert cell_name({"wage": "b"}) is None
        assert cell_name({}) is None

    def test_principal_axes_key_the_vocabulary(self) -> None:
        assert PRINCIPAL_AXES == ("capital_labor", "wage")
        assert frozenset(CELL_AXIS_NAMES) == frozenset(PRINCIPAL_AXES)


class TestAnalyzePartition:
    def test_full_agreement(self) -> None:
        stash = _stash(
            capital_labor={"W": "a", "O": "b"},
            wage={"W": "a", "O": "b"},
        )
        report = analyze_partition(
            scenario="synthetic",
            seeded_roles={
                "W": SocialRole.PERIPHERY_PROLETARIAT.value,  # labor:exploited ✓
                "O": SocialRole.CORE_BOURGEOISIE.value,  # capital:bribed ✓
            },
            tick_stashes=[stash],
        )
        assert isinstance(report, PartitionReport)
        assert report.agreement_rate == pytest.approx(1.0)
        assert report.divergent_nodes == ()
        assert report.class_node_count == 2

    def test_divergence_is_named(self) -> None:
        stash = _stash(capital_labor={"W": "a"}, wage={"W": "a"})
        report = analyze_partition(
            scenario="synthetic",
            seeded_roles={"W": SocialRole.LABOR_ARISTOCRACY.value},  # says bribed
            tick_stashes=[stash],
        )
        assert report.agreement_rate == pytest.approx(0.0)
        assert report.divergent_nodes == (
            ("W", SocialRole.LABOR_ARISTOCRACY.value, "labor:exploited"),
        )

    def test_agreement_rate_is_none_when_no_cell_bearing_nodes(self) -> None:
        # A node positioned on one axis only never forms a cell — the rate
        # must be None (no denominator), never a fabricated 0.0 or 1.0.
        stash = _stash(capital_labor={"W": "a"}, wage={})
        report = analyze_partition(
            scenario="synthetic",
            seeded_roles={"W": SocialRole.PERIPHERY_PROLETARIAT.value},
            tick_stashes=[stash],
        )
        assert report.agreement_rate is None

    def test_unpositioned_counts_per_axis(self) -> None:
        stash = _stash(capital_labor={"W": "a"}, wage={"W": "a", "X": "b"})
        report = analyze_partition(
            scenario="synthetic",
            seeded_roles={
                "W": SocialRole.PERIPHERY_PROLETARIAT.value,
                "X": SocialRole.LABOR_ARISTOCRACY.value,
                "Y": SocialRole.LUMPENPROLETARIAT.value,  # on neither axis
            },
            tick_stashes=[stash],
        )
        assert dict(report.unpositioned) == {"capital_labor": 2, "wage": 1}

    def test_multi_occupancy_counts_cells(self) -> None:
        stash = _stash(
            capital_labor={"W1": "a", "W2": "a", "O": "b"},
            wage={"W1": "a", "W2": "a", "O": "b"},
        )
        report = analyze_partition(
            scenario="synthetic",
            seeded_roles={
                "W1": SocialRole.PERIPHERY_PROLETARIAT.value,
                "W2": SocialRole.INTERNAL_PROLETARIAT.value,
                "O": SocialRole.CORE_BOURGEOISIE.value,
            },
            tick_stashes=[stash],
        )
        assert dict(report.multi_occupancy) == {"labor:exploited": 2, "capital:bribed": 1}

    def test_side_flips_counted_over_consecutive_ticks(self) -> None:
        ticks = [
            _stash(capital_labor={"W": "a"}, wage={}),
            _stash(capital_labor={"W": "b"}, wage={}),  # flip 1
            _stash(capital_labor={"W": "a"}, wage={}),  # flip 2
            _stash(capital_labor={"W": "a"}, wage={}),  # stable
        ]
        report = analyze_partition(
            scenario="synthetic",
            seeded_roles={"W": SocialRole.PERIPHERY_PROLETARIAT.value},
            tick_stashes=ticks,
        )
        assert dict_of_flips(report) == {("capital_labor", "W"): 2}

    def test_absence_gap_is_not_a_flip(self) -> None:
        ticks = [
            _stash(capital_labor={"W": "a"}, wage={}),
            _stash(capital_labor={}, wage={}),  # W unpositioned this tick
            _stash(capital_labor={"W": "b"}, wage={}),  # reappears flipped
        ]
        report = analyze_partition(
            scenario="synthetic",
            seeded_roles={"W": SocialRole.PERIPHERY_PROLETARIAT.value},
            tick_stashes=ticks,
        )
        # A gap breaks adjacency: a->(absent)->b is not a witnessed flip.
        assert dict_of_flips(report) == {}

    def test_empty_run_is_an_infrastructure_failure(self) -> None:
        with pytest.raises(SentinelCheckError):
            analyze_partition(scenario="synthetic", seeded_roles={}, tick_stashes=[])


def dict_of_flips(report: PartitionReport) -> dict[tuple[str, str], int]:
    return {(axis, node): count for axis, node, count in report.side_flips}


class TestEngineVocabularyIsShared:
    """The engine's cell writer and the sentinel share ONE vocabulary object."""

    def test_contradiction_system_cell_matches_registry_reconstruction(self) -> None:
        # Run the real system on a tiny graph, then reconstruct the cell from
        # the stash sides with the registry's own cell_name — byte-identical
        # by construction (single source of truth), no drift possible.
        from babylon.engine.services import ServiceContainer
        from babylon.engine.systems.contradiction import ContradictionSystem
        from babylon.models.enums import EdgeType
        from babylon.topology.graph import BabylonGraph

        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0, w_paid=2.0, v_produced=18.0)
        graph.add_node("owner", wealth=30.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)
        ContradictionSystem().step(graph, ServiceContainer.create(), {"tick": 1})

        stash = graph.graph["pole_readings"]
        sides = {
            axis: stash[axis]["worker"]["side"]
            for axis in PRINCIPAL_AXES
            if "worker" in stash.get(axis, {})
        }
        assert graph.nodes["worker"]["derived_class_cell"] == cell_name(sides)
