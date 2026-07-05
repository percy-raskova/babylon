"""Spec-095: bridge method contract tests (RED phase).

Tests for ``get_contradiction_snapshot``, ``get_endgame_state``, and
``get_journal_objectives`` — the three new EngineBridge methods that power the
Dialectic screen, chronicle end-screen, and Vic3-style objectives tracker.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID

import pytest

from game.engine_bridge import EngineBridge

pytestmark = pytest.mark.unit

_SESSION = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def _mock_graph_with_contradictions() -> MagicMock:
    """A mock BabylonGraph carrying contradiction_frames + dialectical_regime."""
    graph = MagicMock()
    graph.graph = {
        "tick": 5,
        "contradiction_frames": {
            "global": {
                "principal": {
                    "id": "capital_labor",
                    "type": "class",
                    "aspect_a": "Labor",
                    "aspect_b": "Capital",
                    "principal_aspect": "b",
                    "identity": 0.5,
                    "intensity": 0.71,
                    "aspect_balance": 0.03,
                    "form_of_struggle": "extractive",
                    "is_antagonistic": True,
                },
                "secondary": {
                    "id": "imperial",
                    "type": "imperial",
                    "aspect_a": "Core",
                    "aspect_b": "Periphery",
                    "principal_aspect": "a",
                    "identity": 0.5,
                    "intensity": 0.42,
                    "aspect_balance": -0.01,
                    "form_of_struggle": "extractive",
                    "is_antagonistic": True,
                },
            }
        },
        "dialectical_regime": "crisis",
    }
    # nodes() and edges() return empty — only graph-level attrs matter here.
    graph.nodes.return_value = iter([])
    graph.edges = MagicMock(return_value=iter([]))
    return graph


def _make_mock_persistence_with_contradictions() -> MagicMock:
    mock = MagicMock()
    mock.get_metadata.return_value = None
    mock.get_session.return_value = {"scenario": "default"}
    # hydrate_graph returns a graph with contradiction attributes
    mock.hydrate_graph.return_value = _mock_graph_with_contradictions()
    # _pool with a connection cursor returning contradiction_field rows
    mock._pool = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        {
            "tick": 5,
            "field_name": "capital_labor",
            "value": 0.71,
            "dt": 0.03,
        },
        {
            "tick": 5,
            "field_name": "imperial",
            "value": 0.42,
            "dt": -0.01,
        },
    ]
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    mock._pool.connection.return_value = conn
    return mock


# ---------------------------------------------------------------------- #
# get_contradiction_snapshot
# ---------------------------------------------------------------------- #


class TestGetContradictionSnapshot:
    """FR-095-01: get_contradiction_snapshot reads contradiction_field rows +
    graph attributes and returns a ContradictionSnapshot dict."""

    def test_returns_well_formed_snapshot(self) -> None:
        mock_persistence = _make_mock_persistence_with_contradictions()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_contradiction_snapshot(_SESSION)

        assert "tick" in result
        assert "regime" in result
        assert result["regime"] == "crisis"
        assert "oppositions" in result
        assert isinstance(result["oppositions"], list)
        assert len(result["oppositions"]) >= 1
        assert "principal_key" in result
        assert "frame" in result

    def test_oppositions_have_required_fields(self) -> None:
        mock_persistence = _make_mock_persistence_with_contradictions()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_contradiction_snapshot(_SESSION)
        for opp in result["oppositions"]:
            assert "key" in opp
            assert "gap" in opp
            assert "rate" in opp
            assert "is_principal" in opp

    def test_frame_has_principal_and_secondary(self) -> None:
        mock_persistence = _make_mock_persistence_with_contradictions()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_contradiction_snapshot(_SESSION)
        frame = result["frame"]
        assert "principal" in frame
        assert "secondary" in frame
        principal = frame["principal"]
        assert "aspect_a" in principal
        assert "aspect_b" in principal
        assert "intensity" in principal

    def test_degrades_gracefully_without_pool(self) -> None:
        """When the persistence layer has no _pool (SQLite), the snapshot
        still returns graph-level data with empty oppositions."""
        mock_persistence = MagicMock()
        mock_persistence.get_metadata.return_value = None
        mock_persistence.hydrate_graph.return_value = _mock_graph_with_contradictions()
        # No _pool attribute
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_contradiction_snapshot(_SESSION)

        assert "regime" in result
        assert result["regime"] == "crisis"
        # oppositions may be empty (no SQL read), but frame is from graph
        assert "frame" in result


# ---------------------------------------------------------------------- #
# get_endgame_state
# ---------------------------------------------------------------------- #


class TestGetEndgameState:
    """FR-095-02: get_endgame_state returns the terminal outcome + stat cards."""

    def test_returns_in_progress_when_no_endgame(self) -> None:
        mock_persistence = MagicMock()
        mock_persistence.get_metadata.return_value = None
        mock_persistence.hydrate_graph.return_value = _mock_graph_with_contradictions()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_endgame_state(_SESSION)

        assert "tick" in result
        assert "outcome" in result
        # No endgame event → outcome is None or "in_progress"
        assert result["outcome"] is None or result["outcome"] == "in_progress"

    def test_returns_outcome_when_endgame_fires(self) -> None:
        mock_persistence = MagicMock()
        mock_persistence.get_metadata.return_value = None
        graph = _mock_graph_with_contradictions()
        graph.graph["events"] = [
            {"event_type": "REVOLUTIONARY_VICTORY", "tick": 5, "data": {"summary": "Babylon falls"}}
        ]
        mock_persistence.hydrate_graph.return_value = graph
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_endgame_state(_SESSION)

        assert result["outcome"] == "revolutionary_victory"
        assert result["tick"] == 5
        assert "headline" in result
        assert "stats" in result

    def test_returns_stats_block(self) -> None:
        mock_persistence = MagicMock()
        mock_persistence.get_metadata.return_value = None
        mock_persistence.hydrate_graph.return_value = _mock_graph_with_contradictions()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_endgame_state(_SESSION)

        assert "stats" in result
        stats = result["stats"]
        assert "final_tick" in stats
        assert "consciousness" in stats
        assert "solidarity_edges" in stats
        assert "heat" in stats


# ---------------------------------------------------------------------- #
# get_journal_objectives
# ---------------------------------------------------------------------- #


class TestGetJournalObjectives:
    """FR-095-03: get_journal_objectives derives Vic3-style objectives."""

    def test_returns_well_formed_objectives(self) -> None:
        mock_persistence = MagicMock()
        mock_persistence.get_metadata.return_value = None
        mock_persistence.hydrate_graph.return_value = _mock_graph_with_contradictions()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_journal_objectives(_SESSION)

        assert "tick" in result
        assert "objectives" in result
        assert isinstance(result["objectives"], list)
        assert len(result["objectives"]) >= 1

    def test_objectives_have_required_fields(self) -> None:
        mock_persistence = MagicMock()
        mock_persistence.get_metadata.return_value = None
        mock_persistence.hydrate_graph.return_value = _mock_graph_with_contradictions()
        bridge = EngineBridge(mock_persistence)

        result = bridge.get_journal_objectives(_SESSION)
        for obj in result["objectives"]:
            assert "id" in obj
            assert "title" in obj
            assert "description" in obj
            assert "progress" in obj
            assert 0.0 <= obj["progress"] <= 1.0
            assert obj["status"] in ("active", "complete", "failed")
            assert obj["category"] in ("revolution", "collapse", "fascist", "red_ogv", "fragmented")
