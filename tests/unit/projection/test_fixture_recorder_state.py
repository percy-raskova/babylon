"""Contract tests for the state half of :mod:`babylon.projection.fixtures.recorder`.

Mirrors ``tests/unit/projection/test_fixture_recorder.py`` exactly, for
:class:`~babylon.projection.view_models.StateView` (Program 24 P2 WO-16). A
dedicated file rather than an append to that shared test module — keeps this
Lane-P work order collision-free against sibling Lane-P work orders adding
their own fixture round-trip coverage in parallel.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

from babylon.projection.fixtures.recorder import (
    load_state_fixture,
    record_state_fixture,
)
from babylon.projection.view_models import StateView, hydrate_record

#: The fixture the WO-16 harvester ships. A committed artifact, not built here.
_COMMITTED_FIXTURE: Path = (
    Path(__file__).parent.parent.parent / "fixtures" / "projection" / "state_26.json"
)
_SHIPPED_STATE_FIPS: str = "26"


def _full_view(*, tick: int = 847) -> StateView:
    """A fully-populated Michigan-shaped ``StateView`` — every field set."""
    return StateView(
        state_fips="26",
        verified_tick=tick,
        population=400,
        median_wage=22.5,
        imperial_rent_phi=150.0,
        legitimacy=0.65,
        p_acquiescence=0.7,
        p_revolution=0.3,
        bifurcation_score=-0.05,
        sovereign_id="SOV_USA",
    )


def _sparse_view(*, tick: int = 3) -> StateView:
    """An all-``None`` (beyond identity/provenance) ``StateView`` — a state
    nobody has attributed yet."""
    return StateView(state_fips="48", verified_tick=tick)


class TestRoundTrip:
    """Recording then loading a view yields an equal, byte-identical artifact."""

    @pytest.mark.parametrize("view_factory", [_full_view, _sparse_view])
    def test_round_trips_to_an_equal_view(
        self, tmp_path: Path, view_factory: Callable[[], StateView]
    ) -> None:
        """A recorded-then-loaded view compares equal to the original."""
        view = view_factory()
        path = tmp_path / "view.json"

        record_state_fixture(view, path)
        loaded = load_state_fixture(path)

        assert loaded == view
        assert loaded.model_dump() == view.model_dump()

    def test_recording_twice_is_byte_identical(self, tmp_path: Path) -> None:
        """Recording the same view twice writes identical bytes (determinism)."""
        view = _full_view()
        first_path = tmp_path / "first.json"
        second_path = tmp_path / "second.json"

        record_state_fixture(view, first_path)
        record_state_fixture(view, second_path)

        assert first_path.read_bytes() == second_path.read_bytes()

    def test_recorded_file_ends_with_a_trailing_newline(self, tmp_path: Path) -> None:
        """The recorded JSON is POSIX-friendly: exactly one trailing newline."""
        path = tmp_path / "view.json"
        record_state_fixture(_sparse_view(), path)

        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n")
        assert not text.endswith("\n\n")


class TestHydrateRecordCompatibility:
    """The recorded file also hydrates through the discriminated-union helper."""

    def test_recorded_file_hydrates_through_hydrate_record(self, tmp_path: Path) -> None:
        """``hydrate_record`` (keyed on ``kind``) accepts a recorded fixture."""
        view = _full_view()
        path = tmp_path / "view.json"
        record_state_fixture(view, path)

        data = json.loads(path.read_text(encoding="utf-8"))
        rehydrated = hydrate_record(data)

        assert rehydrated == view


class TestLoudFailure:
    """A missing or malformed fixture fails loud — never a silent default."""

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        """Loading a path with no file raises ``FileNotFoundError``."""
        with pytest.raises(FileNotFoundError):
            load_state_fixture(tmp_path / "does_not_exist.json")

    def test_malformed_json_raises_value_error(self, tmp_path: Path) -> None:
        """Loading a file with invalid JSON syntax raises ``ValueError``."""
        path = tmp_path / "malformed.json"
        path.write_text("{not valid json", encoding="utf-8")

        with pytest.raises(ValueError):
            load_state_fixture(path)

    def test_wrong_shaped_json_raises_validation_error(self, tmp_path: Path) -> None:
        """Valid JSON that doesn't hydrate to a ``StateView`` raises loudly."""
        path = tmp_path / "wrong_shape.json"
        path.write_text(json.dumps({"state_fips": "not-two-digits"}), encoding="utf-8")

        with pytest.raises(ValidationError):
            load_state_fixture(path)


class TestCommittedFixture:
    """The WO-16 harvester's committed fixture stays present and well-shaped.

    Deliberately NOT a skip: if ``tests/fixtures/projection/state_26.json``
    goes missing or drifts out of ``StateView``'s schema, this test must fail
    loud (Constitution III.11).
    """

    def test_committed_fixture_is_present_and_well_shaped(self) -> None:
        """The shipped fixture loads, names the right FIPS, and has a valid tick."""
        assert _COMMITTED_FIXTURE.is_file(), (
            f"committed projection fixture missing: {_COMMITTED_FIXTURE} — "
            "regenerate via `uv run python tools/record_state_fixture.py`"
        )

        view = load_state_fixture(_COMMITTED_FIXTURE)

        assert view.state_fips == _SHIPPED_STATE_FIPS
        assert view.verified_tick >= 0
