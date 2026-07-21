"""Contract tests for record_key_figure_fixture/load_key_figure_fixture (WO-21).

Fixture-fed — no engine, no database. These tests build
:class:`~babylon.projection.view_models.KeyFigureView` instances in-test and
round-trip them through the recorder; the harvester
(``tools/record_key_figure_fixture.py``) that drives the real engine (only to
empirically confirm the honest-absence premise — see its module docstring)
is exercised separately, once, and its output is the committed fixture the
last test class in this module verifies.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from babylon.projection.fixtures.recorder import (
    load_key_figure_fixture,
    record_key_figure_fixture,
)
from babylon.projection.view_models import KeyFigureView, hydrate_record

_COMMITTED_FIXTURE: Path = (
    Path(__file__).parent.parent.parent / "fixtures" / "projection" / "key_figure_kf-001.json"
)
_SHIPPED_ID: str = "kf-001"


def _view(*, key_figure_id: str = "kf-001", tick: int = 5) -> KeyFigureView:
    return KeyFigureView(key_figure_id=key_figure_id, verified_tick=tick)


class TestRoundTrip:
    """Recording then loading a view yields an equal, byte-identical artifact."""

    def test_round_trips_to_an_equal_view(self, tmp_path: Path) -> None:
        view = _view()
        path = tmp_path / "view.json"

        record_key_figure_fixture(view, path)
        loaded = load_key_figure_fixture(path)

        assert loaded == view
        assert loaded.model_dump() == view.model_dump()

    def test_recording_twice_is_byte_identical(self, tmp_path: Path) -> None:
        view = _view()
        first_path = tmp_path / "first.json"
        second_path = tmp_path / "second.json"

        record_key_figure_fixture(view, first_path)
        record_key_figure_fixture(view, second_path)

        assert first_path.read_bytes() == second_path.read_bytes()

    def test_recorded_file_ends_with_a_trailing_newline(self, tmp_path: Path) -> None:
        path = tmp_path / "view.json"
        record_key_figure_fixture(_view(), path)

        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n")
        assert not text.endswith("\n\n")


class TestHydrateRecordCompatibility:
    """The recorded file also hydrates through the discriminated-union helper."""

    def test_recorded_file_hydrates_through_hydrate_record(self, tmp_path: Path) -> None:
        view = _view()
        path = tmp_path / "view.json"
        record_key_figure_fixture(view, path)

        data = json.loads(path.read_text(encoding="utf-8"))
        rehydrated = hydrate_record(data)

        assert rehydrated == view


class TestLoudFailure:
    """A missing or malformed fixture fails loud — never a silent default."""

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_key_figure_fixture(tmp_path / "does_not_exist.json")

    def test_malformed_json_raises_value_error(self, tmp_path: Path) -> None:
        path = tmp_path / "malformed.json"
        path.write_text("{not valid json", encoding="utf-8")

        with pytest.raises(ValueError):
            load_key_figure_fixture(path)

    def test_wrong_shaped_json_raises_validation_error(self, tmp_path: Path) -> None:
        path = tmp_path / "wrong_shape.json"
        path.write_text(json.dumps({"key_figure_id": ""}), encoding="utf-8")

        with pytest.raises(ValidationError):
            load_key_figure_fixture(path)

    def test_invented_field_is_rejected(self, tmp_path: Path) -> None:
        """extra='forbid': a payload claiming a data field this kind never
        carries fails loud rather than being silently dropped."""
        path = tmp_path / "invented_field.json"
        path.write_text(
            json.dumps({"key_figure_id": "kf-001", "verified_tick": 5, "name": "Someone"}),
            encoding="utf-8",
        )

        with pytest.raises(ValidationError):
            load_key_figure_fixture(path)


class TestCommittedFixture:
    """The WO-21 harvester's committed fixture stays present and well-shaped.

    Deliberately NOT a skip: if
    ``tests/fixtures/projection/key_figure_kf-001.json`` goes missing or
    drifts out of ``KeyFigureView``'s schema, this test must fail loud
    (Constitution III.11).
    """

    def test_committed_fixture_is_present_and_well_shaped(self) -> None:
        assert _COMMITTED_FIXTURE.is_file(), (
            f"committed projection fixture missing: {_COMMITTED_FIXTURE} — "
            "regenerate via `uv run python tools/record_key_figure_fixture.py`"
        )

        view = load_key_figure_fixture(_COMMITTED_FIXTURE)

        assert view.key_figure_id == _SHIPPED_ID
        assert view.verified_tick >= 0
