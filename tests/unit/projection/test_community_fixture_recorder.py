"""Contract tests for the community half of :mod:`babylon.projection.fixtures.recorder`.

Trimmed mirror of ``test_fixture_recorder.py`` scoped to
``record_community_fixture``/``load_community_fixture`` — the county file
already exercises the shared JSON/loud-failure mechanics in full; this file
adds the committed-fixture-presence check for WO-24's own artifact and the
round-trip/determinism cases specific to :class:`CommunityView`'s tri-state
(``None`` / empty-tuple / populated) fields.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.projection.fixtures.recorder import (
    load_community_fixture,
    record_community_fixture,
)
from babylon.projection.view_models import CommunityOverlap, CommunityView, hydrate_record

_COMMITTED_FIXTURE: Path = (
    Path(__file__).parent.parent.parent / "fixtures" / "projection" / "community_settler.json"
)


def _full_view() -> CommunityView:
    return CommunityView(
        community_id="settler",
        verified_tick=847,
        roster=("C001", "C002"),
        overlaps=(CommunityOverlap(community_id="patriarchal", shared_member_count=2),),
    )


def _absent_view() -> CommunityView:
    return CommunityView(community_id="settler", verified_tick=3)


class TestRoundTrip:
    @pytest.mark.parametrize("view_factory", [_full_view, _absent_view])
    def test_round_trips_to_an_equal_view(self, tmp_path: Path, view_factory) -> None:  # type: ignore[no-untyped-def]
        view = view_factory()
        path = tmp_path / "view.json"

        record_community_fixture(view, path)
        loaded = load_community_fixture(path)

        assert loaded == view
        assert loaded.model_dump() == view.model_dump()

    def test_recording_twice_is_byte_identical(self, tmp_path: Path) -> None:
        view = _full_view()
        first_path = tmp_path / "first.json"
        second_path = tmp_path / "second.json"

        record_community_fixture(view, first_path)
        record_community_fixture(view, second_path)

        assert first_path.read_bytes() == second_path.read_bytes()

    def test_recorded_file_hydrates_through_hydrate_record(self, tmp_path: Path) -> None:
        """``hydrate_record`` (keyed on ``kind``) accepts a recorded fixture."""
        import json

        view = _full_view()
        path = tmp_path / "view.json"
        record_community_fixture(view, path)

        data = json.loads(path.read_text(encoding="utf-8"))
        rehydrated = hydrate_record(data)

        assert rehydrated == view


class TestLoudFailure:
    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_community_fixture(tmp_path / "does_not_exist.json")


class TestCommittedFixture:
    """The WO-24 harvester's committed fixture stays present and well-shaped.

    Deliberately NOT a skip: if this fixture goes missing or drifts out of
    ``CommunityView``'s schema, this test must fail loud (Constitution
    III.11).
    """

    def test_committed_fixture_is_present_and_well_shaped(self) -> None:
        assert _COMMITTED_FIXTURE.is_file(), (
            f"committed projection fixture missing: {_COMMITTED_FIXTURE} — "
            "regenerate via `mise run archive:record-fixtures-community`"
        )

        view = load_community_fixture(_COMMITTED_FIXTURE)

        assert view.community_id == "settler"
        assert view.verified_tick >= 0

    def test_committed_fixture_is_honestly_all_absent(self) -> None:
        """No scenario wires a community_memberships producer today (see the
        babylon.projection.community module docstring) — this pins that the
        shipped fixture says so honestly rather than fabricating a roster."""
        view = load_community_fixture(_COMMITTED_FIXTURE)

        assert view.roster is None
        assert view.formation_tick is None
        assert view.overlaps is None
