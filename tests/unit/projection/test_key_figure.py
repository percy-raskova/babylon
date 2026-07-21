"""Contract tests for :func:`babylon.projection.key_figure.project_key_figure`.

The key-figure read-model's behavioral contract: unlike ``project_county``,
there is no per-field absence to pin here — the whole *kind* has no live
producer (ADR084), so every dossier is the honest-absence page,
unconditionally. Fixture-fed — no engine tick, no database — per the keel's
fixture-first discipline.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.enums.topology import NodeType
from babylon.models.world_state import WorldState
from babylon.projection.key_figure import (
    DEAD_PRODUCER_REMEDY,
    key_figure_statblocks,
    project_key_figure,
)
from babylon.projection.view_models import KeyFigureView
from babylon.topology import BabylonGraph

KF_001 = "kf-001"


def _empty_world() -> WorldState:
    """A ``WorldState`` with no entities — ``project_key_figure`` never reads it."""
    return WorldState(entities={})


class TestHonestAbsence:
    """Every projected dossier is identity-only — there is no field to attribute."""

    def test_projects_identity_and_tick_only(self) -> None:
        """The view carries exactly the caller-supplied id/tick, nothing more."""
        view = project_key_figure(KF_001, graph=BabylonGraph(), world=_empty_world(), tick=847)

        assert view.kind == "key_figure"
        assert view.key_figure_id == KF_001
        assert view.verified_tick == 847

    def test_indifferent_to_graph_contents(self) -> None:
        """A hand-stamped key_figure node in the graph changes nothing.

        Even a test/fixture graph that stamps a ``NodeType.KEY_FIGURE`` node
        (the only place this vocabulary is legal per ADR084 — it types
        ``classify_topology()``'s COMMAND-edge fixtures) carries no declared
        attribute schema for this projector to read — see the module
        docstring for why it does not query the graph at all.
        """
        bare_graph = BabylonGraph()
        stamped_graph = BabylonGraph()
        stamped_graph.add_node(KF_001, NodeType.KEY_FIGURE, name="Someone")
        world = _empty_world()

        bare_view = project_key_figure(KF_001, graph=bare_graph, world=world, tick=1)
        stamped_view = project_key_figure(KF_001, graph=stamped_graph, world=world, tick=1)

        assert bare_view == stamped_view

    def test_indifferent_to_world_contents(self) -> None:
        """A populated ``WorldState`` changes nothing — there is no world-side source."""
        graph = BabylonGraph()
        empty_view = project_key_figure(KF_001, graph=graph, world=_empty_world(), tick=1)
        populated_view = project_key_figure(
            KF_001, graph=graph, world=WorldState(entities={}), tick=1
        )

        assert empty_view == populated_view


class TestNoDataFieldsDeclared:
    """``KeyFigureView`` declares no field beyond identity/provenance (ADR084).

    A structural contract test, not a behavioral one: it locks in the
    "permanently honest-absence" design decision so a future change that
    adds a data field to ``KeyFigureView`` must consciously update this test
    (and, presumably, cite a live producer when it does).
    """

    def test_only_identity_fields_declared(self) -> None:
        assert set(KeyFigureView.model_fields) == {"kind", "key_figure_id", "verified_tick"}


class TestKeyFigureStatblocks:
    """The per-kind statblock-row builder (Lane P convention; WO-45 consumes it)."""

    def test_always_returns_an_empty_tuple(self) -> None:
        view = project_key_figure(KF_001, graph=BabylonGraph(), world=_empty_world(), tick=1)
        assert key_figure_statblocks(view) == ()

    def test_empty_regardless_of_which_view_is_passed(self) -> None:
        view_a = project_key_figure("kf-001", graph=BabylonGraph(), world=_empty_world(), tick=1)
        view_b = project_key_figure("kf-002", graph=BabylonGraph(), world=_empty_world(), tick=99)
        assert key_figure_statblocks(view_a) == key_figure_statblocks(view_b) == ()


class TestDeadProducerRemedy:
    """The dossier's sole absence remedy names the ADR that killed the producer."""

    def test_remedy_cites_adr084(self) -> None:
        assert "ADR084" in DEAD_PRODUCER_REMEDY

    def test_remedy_is_single_line_ascii(self) -> None:
        """No em dash / newline — the remedy is spliced into a Jinja fence info string."""
        assert "\n" not in DEAD_PRODUCER_REMEDY
        DEAD_PRODUCER_REMEDY.encode("ascii")  # raises UnicodeEncodeError if not


class TestLoudFailure:
    """A malformed *identity* fails loud — a missing producer is absence, not this."""

    def test_empty_key_figure_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            project_key_figure("", graph=BabylonGraph(), world=_empty_world(), tick=1)

    def test_negative_tick_raises(self) -> None:
        with pytest.raises(ValidationError):
            project_key_figure(KF_001, graph=BabylonGraph(), world=_empty_world(), tick=-1)


class TestDeterminism:
    """Identical inputs yield identical frozen dossiers."""

    def test_double_projection_is_identical(self) -> None:
        graph = BabylonGraph()
        world = _empty_world()

        first = project_key_figure(KF_001, graph=graph, world=world, tick=847)
        second = project_key_figure(KF_001, graph=graph, world=world, tick=847)

        assert first == second
        assert first.model_dump() == second.model_dump()
