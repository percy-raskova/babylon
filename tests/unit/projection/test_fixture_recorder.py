"""Contract tests for :mod:`babylon.projection.fixtures.recorder`.

Fixture-fed — no engine, no database. These tests build
:class:`~babylon.projection.view_models.CountyView` instances in-test and
round-trip them through the recorder; the harvester
(``tools/record_projection_fixtures.py``) that drives the real engine to
produce a ``CountyView`` in the first place is exercised separately, once,
and its output is the committed fixture the last test class in this module
verifies.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

from babylon.projection.fixtures.recorder import (
    load_county_fixture,
    load_industry_fixture,
    record_county_fixture,
    record_industry_fixture,
)
from babylon.projection.view_models import (
    ClassComposition,
    ConsciousnessSimplex,
    CountyView,
    IndustryView,
    hydrate_record,
)

#: The fixture the WO-6 harvester ships. A committed artifact, not built here.
_COMMITTED_FIXTURE: Path = (
    Path(__file__).parent.parent.parent / "fixtures" / "projection" / "county_26163.json"
)
_SHIPPED_FIPS: str = "26163"

#: The fixture the WO-22 harvester ships (honest-absence — see
#: ``tools/record_industry_fixture.py``'s docstring for why).
_COMMITTED_INDUSTRY_FIXTURE: Path = (
    Path(__file__).parent.parent.parent / "fixtures" / "projection" / "industry_ind_31-33.json"
)
_SHIPPED_INDUSTRY_ID: str = "ind_31-33"


def _full_view(*, tick: int = 847) -> CountyView:
    """A fully-populated Wayne-shaped ``CountyView`` — every field set."""
    return CountyView(
        county_fips="26163",
        verified_tick=tick,
        population=400,
        class_composition=ClassComposition(
            bourgeoisie=0.077,
            petit_bourgeoisie=0.191,
            labor_aristocracy=0.226,
            proletariat=0.382,
            lumpenproletariat=0.124,
        ),
        median_wage=19.85,
        imperial_rent_phi=412.7,
        consciousness=ConsciousnessSimplex(revolutionary=0.3, liberal=0.6, fascist=0.1),
        legitimacy=0.71,
        p_acquiescence=0.61,
        p_revolution=0.44,
        bifurcation_score=-0.32,
        sovereign_id="SOV_USA",
    )


def _sparse_view(*, tick: int = 3) -> CountyView:
    """An all-``None`` (beyond identity/provenance) ``CountyView`` — a county
    nobody has attributed yet."""
    return CountyView(county_fips="26125", verified_tick=tick)


def _full_industry_view(*, tick: int = 500) -> IndustryView:
    """A fully-populated Manufacturing-shaped ``IndustryView`` — every field set."""
    return IndustryView(
        industry_id="ind_31-33",
        verified_tick=tick,
        naics_2digit="31-33",
        naics_label="Manufacturing",
        total_employment=2000,
        total_wages=100000.0,
        profit_rate=1.0 / 3.0,
        occ=2.0,
        member_business_count=2,
        member_worker_block_count=1,
        county_fips=("26125", "26163"),
    )


def _sparse_industry_view(*, tick: int = 5) -> IndustryView:
    """An all-``None`` (beyond identity/provenance) ``IndustryView`` — the
    honest-absence shape ``tools/record_industry_fixture.py`` actually ships."""
    return IndustryView(industry_id="ind_31-33", verified_tick=tick)


class TestRoundTrip:
    """Recording then loading a view yields an equal, byte-identical artifact."""

    @pytest.mark.parametrize("view_factory", [_full_view, _sparse_view])
    def test_round_trips_to_an_equal_view(
        self, tmp_path: Path, view_factory: Callable[[], CountyView]
    ) -> None:
        """A recorded-then-loaded view compares equal to the original."""
        view = view_factory()
        path = tmp_path / "view.json"

        record_county_fixture(view, path)
        loaded = load_county_fixture(path)

        assert loaded == view
        assert loaded.model_dump() == view.model_dump()

    def test_recording_twice_is_byte_identical(self, tmp_path: Path) -> None:
        """Recording the same view twice writes identical bytes (determinism)."""
        view = _full_view()
        first_path = tmp_path / "first.json"
        second_path = tmp_path / "second.json"

        record_county_fixture(view, first_path)
        record_county_fixture(view, second_path)

        assert first_path.read_bytes() == second_path.read_bytes()

    def test_recorded_file_ends_with_a_trailing_newline(self, tmp_path: Path) -> None:
        """The recorded JSON is POSIX-friendly: exactly one trailing newline."""
        path = tmp_path / "view.json"
        record_county_fixture(_sparse_view(), path)

        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n")
        assert not text.endswith("\n\n")


class TestHydrateRecordCompatibility:
    """The recorded file also hydrates through the discriminated-union helper."""

    def test_recorded_file_hydrates_through_hydrate_record(self, tmp_path: Path) -> None:
        """``hydrate_record`` (keyed on ``kind``) accepts a recorded fixture."""
        view = _full_view()
        path = tmp_path / "view.json"
        record_county_fixture(view, path)

        data = json.loads(path.read_text(encoding="utf-8"))
        rehydrated = hydrate_record(data)

        assert rehydrated == view


class TestLoudFailure:
    """A missing or malformed fixture fails loud — never a silent default."""

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        """Loading a path with no file raises ``FileNotFoundError``."""
        with pytest.raises(FileNotFoundError):
            load_county_fixture(tmp_path / "does_not_exist.json")

    def test_malformed_json_raises_value_error(self, tmp_path: Path) -> None:
        """Loading a file with invalid JSON syntax raises ``ValueError``."""
        path = tmp_path / "malformed.json"
        path.write_text("{not valid json", encoding="utf-8")

        with pytest.raises(ValueError):
            load_county_fixture(path)

    def test_wrong_shaped_json_raises_validation_error(self, tmp_path: Path) -> None:
        """Valid JSON that doesn't hydrate to a ``CountyView`` raises loudly."""
        path = tmp_path / "wrong_shape.json"
        path.write_text(json.dumps({"county_fips": "not-five-digits"}), encoding="utf-8")

        with pytest.raises(ValidationError):
            load_county_fixture(path)


class TestCommittedFixture:
    """The WO-6 harvester's committed fixture stays present and well-shaped.

    Deliberately NOT a skip: if ``tests/fixtures/projection/county_26163.json``
    goes missing or drifts out of ``CountyView``'s schema, this test must fail
    loud (Constitution III.11) — the whole point of item 5 is that downstream
    view-consumer tasks can depend on this file existing and being valid.
    """

    def test_committed_fixture_is_present_and_well_shaped(self) -> None:
        """The shipped fixture loads, names the right FIPS, and has a valid tick."""
        assert _COMMITTED_FIXTURE.is_file(), (
            f"committed projection fixture missing: {_COMMITTED_FIXTURE} — "
            "regenerate via `mise run archive:record-fixtures`"
        )

        view = load_county_fixture(_COMMITTED_FIXTURE)

        assert view.county_fips == _SHIPPED_FIPS
        assert view.verified_tick >= 0


class TestIndustryRoundTrip:
    """Recording then loading an industry view yields an equal artifact."""

    @pytest.mark.parametrize("view_factory", [_full_industry_view, _sparse_industry_view])
    def test_round_trips_to_an_equal_view(
        self, tmp_path: Path, view_factory: Callable[[], IndustryView]
    ) -> None:
        """A recorded-then-loaded view compares equal to the original."""
        view = view_factory()
        path = tmp_path / "view.json"

        record_industry_fixture(view, path)
        loaded = load_industry_fixture(path)

        assert loaded == view
        assert loaded.model_dump() == view.model_dump()

    def test_recording_twice_is_byte_identical(self, tmp_path: Path) -> None:
        """Recording the same view twice writes identical bytes (determinism)."""
        view = _full_industry_view()
        first_path = tmp_path / "first.json"
        second_path = tmp_path / "second.json"

        record_industry_fixture(view, first_path)
        record_industry_fixture(view, second_path)

        assert first_path.read_bytes() == second_path.read_bytes()


class TestIndustryLoudFailure:
    """A missing or malformed industry fixture fails loud — never a silent default."""

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        """Loading a path with no file raises ``FileNotFoundError``."""
        with pytest.raises(FileNotFoundError):
            load_industry_fixture(tmp_path / "does_not_exist.json")

    def test_malformed_json_raises_value_error(self, tmp_path: Path) -> None:
        """Loading a file with invalid JSON syntax raises ``ValueError``."""
        path = tmp_path / "malformed.json"
        path.write_text("{not valid json", encoding="utf-8")

        with pytest.raises(ValueError):
            load_industry_fixture(path)


class TestCommittedIndustryFixture:
    """The WO-22 harvester's committed fixture stays present and well-shaped.

    Deliberately NOT a skip: if
    ``tests/fixtures/projection/industry_ind_31-33.json`` goes missing or
    drifts out of ``IndustryView``'s schema, this test must fail loud
    (Constitution III.11).
    """

    def test_committed_fixture_is_present_and_well_shaped(self) -> None:
        """The shipped fixture loads, names the right id, and has a valid tick."""
        assert _COMMITTED_INDUSTRY_FIXTURE.is_file(), (
            f"committed projection fixture missing: {_COMMITTED_INDUSTRY_FIXTURE} — "
            "regenerate via `uv run python tools/record_industry_fixture.py`"
        )

        view = load_industry_fixture(_COMMITTED_INDUSTRY_FIXTURE)

        assert view.industry_id == _SHIPPED_INDUSTRY_ID
        assert view.verified_tick >= 0
