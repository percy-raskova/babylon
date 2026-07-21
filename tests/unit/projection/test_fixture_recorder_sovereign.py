"""Contract tests for the sovereign half of :mod:`babylon.projection.fixtures.recorder`.

A separate file from ``test_fixture_recorder.py`` (county) — mirrors its
structure exactly for :class:`~babylon.projection.view_models.SovereignView`.
The harvester (``tools/record_sovereign_fixture.py``) that drives the real
engine is exercised separately, once; its committed output is verified by
:class:`TestCommittedFixture` below.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

from babylon.projection.fixtures.recorder import (
    load_sovereign_fixture,
    record_sovereign_fixture,
)
from babylon.projection.view_models import SovereignView, hydrate_record

#: The fixture tools/record_sovereign_fixture.py ships. A committed artifact,
#: not built here — see the module docstring's honest-absence finding.
_COMMITTED_FIXTURE: Path = (
    Path(__file__).parent.parent.parent / "fixtures" / "projection" / "sovereign_SOV_USA_FED.json"
)
_SHIPPED_ID: str = "SOV_USA_FED"


def _full_view(*, tick: int = 847) -> SovereignView:
    """A fully-populated SOV_USA_FED-shaped ``SovereignView`` — every field set."""
    return SovereignView(
        sovereign_id="SOV_USA_FED",
        verified_tick=tick,
        name="United States Federal Government",
        sovereignty_type="recognized_state",
        legitimacy=0.82,
        ruling_faction_id="FAC_RESTORATIONIST",
        extraction_policy="intensify",
        capital_territory_id="T_DC",
        capital_county_fips="11001",
        founded_tick=0,
        claimed_county_fips=("26125", "26163"),
    )


def _sparse_view(*, tick: int = 3) -> SovereignView:
    """An all-``None`` (beyond identity/provenance) ``SovereignView`` — a
    sovereign id nobody has minted yet."""
    return SovereignView(sovereign_id="SOV_UNMINTED", verified_tick=tick)


class TestRoundTrip:
    """Recording then loading a view yields an equal, byte-identical artifact."""

    @pytest.mark.parametrize("view_factory", [_full_view, _sparse_view])
    def test_round_trips_to_an_equal_view(
        self, tmp_path: Path, view_factory: Callable[[], SovereignView]
    ) -> None:
        """A recorded-then-loaded view compares equal to the original."""
        view = view_factory()
        path = tmp_path / "view.json"

        record_sovereign_fixture(view, path)
        loaded = load_sovereign_fixture(path)

        assert loaded == view
        assert loaded.model_dump() == view.model_dump()

    def test_recording_twice_is_byte_identical(self, tmp_path: Path) -> None:
        """Recording the same view twice writes identical bytes (determinism)."""
        view = _full_view()
        first_path = tmp_path / "first.json"
        second_path = tmp_path / "second.json"

        record_sovereign_fixture(view, first_path)
        record_sovereign_fixture(view, second_path)

        assert first_path.read_bytes() == second_path.read_bytes()

    def test_recorded_file_ends_with_a_trailing_newline(self, tmp_path: Path) -> None:
        """The recorded JSON is POSIX-friendly: exactly one trailing newline."""
        path = tmp_path / "view.json"
        record_sovereign_fixture(_sparse_view(), path)

        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n")
        assert not text.endswith("\n\n")


class TestHydrateRecordCompatibility:
    """The recorded file also hydrates through the discriminated-union helper."""

    def test_recorded_file_hydrates_through_hydrate_record(self, tmp_path: Path) -> None:
        """``hydrate_record`` (keyed on ``kind``) accepts a recorded sovereign fixture."""
        view = _full_view()
        path = tmp_path / "view.json"
        record_sovereign_fixture(view, path)

        data = json.loads(path.read_text(encoding="utf-8"))
        rehydrated = hydrate_record(data)

        assert rehydrated == view


class TestLoudFailure:
    """A missing or malformed fixture fails loud — never a silent default."""

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        """Loading a path with no file raises ``FileNotFoundError``."""
        with pytest.raises(FileNotFoundError):
            load_sovereign_fixture(tmp_path / "does_not_exist.json")

    def test_malformed_json_raises_value_error(self, tmp_path: Path) -> None:
        """Loading a file with invalid JSON syntax raises ``ValueError``."""
        path = tmp_path / "malformed.json"
        path.write_text("{not valid json", encoding="utf-8")

        with pytest.raises(ValueError):
            load_sovereign_fixture(path)

    def test_wrong_shaped_json_raises_validation_error(self, tmp_path: Path) -> None:
        """Valid JSON that doesn't hydrate to a ``SovereignView`` raises loudly."""
        path = tmp_path / "wrong_shape.json"
        path.write_text(json.dumps({"sovereign_id": "not-a-valid-id"}), encoding="utf-8")

        with pytest.raises(ValidationError):
            load_sovereign_fixture(path)


class TestCommittedFixture:
    """The WO-20 harvester's committed fixture stays present and well-shaped.

    Deliberately NOT a skip: if
    ``tests/fixtures/projection/sovereign_SOV_USA_FED.json`` goes missing or
    drifts out of ``SovereignView``'s schema, this test must fail loud
    (Constitution III.11).

    This fixture's ``claimed_county_fips`` (and every other optional field)
    is ``None`` by construction — see ``tools/record_sovereign_fixture.py``'s
    docstring: the ``single_county`` harvest scenario seeds no ``sovereign``
    node, so this is the honest-absence projection, not a stub.
    """

    def test_committed_fixture_is_present_and_well_shaped(self) -> None:
        """The shipped fixture loads, names the right id, and has a valid tick."""
        assert _COMMITTED_FIXTURE.is_file(), (
            f"committed projection fixture missing: {_COMMITTED_FIXTURE} — "
            "regenerate via `uv run python tools/record_sovereign_fixture.py`"
        )

        view = load_sovereign_fixture(_COMMITTED_FIXTURE)

        assert view.sovereign_id == _SHIPPED_ID
        assert view.verified_tick >= 0

    def test_committed_fixture_is_the_honest_absence_shape(self) -> None:
        """single_county seeds no sovereign — every optional field is None."""
        view = load_sovereign_fixture(_COMMITTED_FIXTURE)

        assert view.name is None
        assert view.claimed_county_fips is None
