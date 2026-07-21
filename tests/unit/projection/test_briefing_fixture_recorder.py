"""Contract tests for the briefing half of :mod:`babylon.projection.fixtures.recorder` (WO-35).

Mirrors ``test_fixture_recorder.py``'s county round-trip contract for
:class:`~babylon.projection.briefing.BriefingView`. No committed golden
fixture ships here (unlike county's harvested Wayne-tick-847 artifact):
:func:`~babylon.projection.briefing.project_briefing` is a pure function of
plain values with no engine/database step to harvest, so there is nothing a
harvester tool would produce that this round-trip doesn't already prove.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from babylon.config.defines import GameDefines
from babylon.projection.briefing import BriefingView, project_briefing
from babylon.projection.fixtures.recorder import (
    load_briefing_fixture,
    record_briefing_fixture,
)

_SESSION = UUID("12345678-1234-5678-1234-567812345678")


def _fresh_view() -> BriefingView:
    """A tick-0 briefing dossier for a fresh campaign — honest zero progress."""
    return project_briefing(_SESSION, tick=0, defines=GameDefines())


def _held_pattern_view() -> BriefingView:
    """A briefing dossier with a held outcome and nonzero axis progress."""
    from babylon.models.enums.events import GameOutcome

    return project_briefing(
        _SESSION,
        tick=520,
        defines=GameDefines(),
        axes={"revolutionary_victory": 0.71, "ecological_collapse": 0.2},
        outcome=GameOutcome.REVOLUTIONARY_VICTORY,
    )


class TestRoundTrip:
    """Recording then loading a view yields an equal, byte-identical artifact."""

    @pytest.mark.parametrize("view_factory", [_fresh_view, _held_pattern_view])
    def test_round_trips_to_an_equal_view(
        self, tmp_path: Path, view_factory: Callable[[], BriefingView]
    ) -> None:
        view = view_factory()
        path = tmp_path / "view.json"

        record_briefing_fixture(view, path)
        loaded = load_briefing_fixture(path)

        assert loaded == view
        assert loaded.model_dump() == view.model_dump()

    def test_recording_twice_is_byte_identical(self, tmp_path: Path) -> None:
        view = _fresh_view()
        first_path = tmp_path / "first.json"
        second_path = tmp_path / "second.json"

        record_briefing_fixture(view, first_path)
        record_briefing_fixture(view, second_path)

        assert first_path.read_bytes() == second_path.read_bytes()

    def test_recorded_file_ends_with_a_trailing_newline(self, tmp_path: Path) -> None:
        path = tmp_path / "view.json"
        record_briefing_fixture(_fresh_view(), path)

        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n")
        assert not text.endswith("\n\n")


class TestLoudFailure:
    """A missing or malformed fixture fails loud — never a silent default."""

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_briefing_fixture(tmp_path / "does_not_exist.json")

    def test_malformed_json_raises_value_error(self, tmp_path: Path) -> None:
        path = tmp_path / "malformed.json"
        path.write_text("{not valid json", encoding="utf-8")

        with pytest.raises(ValueError):
            load_briefing_fixture(path)

    def test_wrong_shaped_json_raises_validation_error(self, tmp_path: Path) -> None:
        path = tmp_path / "wrong_shape.json"
        path.write_text(json.dumps({"session_id": str(_SESSION)}), encoding="utf-8")

        with pytest.raises(ValidationError):
            load_briefing_fixture(path)
