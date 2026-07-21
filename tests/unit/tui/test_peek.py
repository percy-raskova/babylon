"""Contract tests for :func:`babylon.tui.peek.peek` (Program 24 P2 WO-25).

Pins the WO's three named behaviors: the depth→size mapping, generic
dispatch on ``.kind`` (proven against kinds this module has never seen,
not just ``CountyView``), and honest-absence rendering. Fixture-fed only —
no engine, no graph, no vault — ``peek()`` is a live-query surface over
already-projected view-models.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel
from rich.panel import Panel
from rich.text import Text

from babylon.projection.view_models import ClassComposition, ConsciousnessSimplex, CountyView
from babylon.tui.peek import MAX_DEPTH, peek

WAYNE = CountyView(
    county_fips="26163",
    verified_tick=847,
    population=1_749_343,
    class_composition=ClassComposition(
        bourgeoisie=0.01,
        petit_bourgeoisie=0.09,
        labor_aristocracy=0.4,
        proletariat=0.35,
        lumpenproletariat=0.15,
    ),
    median_wage=19.85,
    imperial_rent_phi=412.7,
    consciousness=ConsciousnessSimplex(
        revolutionary=0.148785,
        liberal=0.4375,
        fascist=0.413715,
    ),
    legitimacy=0.71,
    p_acquiescence=0.61,
    p_revolution=0.44,
    bifurcation_score=-0.32,
    sovereign_id="SOV_USA",
)
"""Wayne County (FIPS 26163) @ T0847, wages 19.85 — the WO-25 fixture persona."""

BARE = CountyView(county_fips="00000", verified_tick=3)
"""A county with no attributed producer at all — every optional field None."""

_TOTAL_ROWS_WHEN_FULLY_ATTRIBUTED = 16
"""population(1) + class_composition(5) + median_wage(1) + imperial_rent_phi(1)
+ consciousness(3) + legitimacy(1) + p_acquiescence(1) + p_revolution(1)
+ bifurcation_score(1) + sovereign_id(1) — WAYNE's declaration-order walk."""


def _rows_of(result: object) -> list[str]:
    """Extract the plain body lines from a peek() result, panel or bare text."""
    if isinstance(result, Panel):
        assert isinstance(result.renderable, Text)
        return result.renderable.plain.splitlines()
    assert isinstance(result, Text)
    return result.plain.splitlines()


class _FakeOrganizationView(BaseModel):
    """Stands in for the not-yet-landed ``OrganizationView`` (Lane P WO-18).

    Proves :func:`peek` dispatches on ``.kind`` structurally: this type is
    not a member of :data:`~babylon.projection.view_models.ProjectionRecord`
    and peek.py has no code naming ``"organization"`` anywhere, yet the
    identity-field convention (``f"{kind}_id"``) resolves correctly.
    """

    kind: str = "organization"
    organization_id: str = "uaw-9999"
    cadre_level: float = 0.8
    verified_tick: int = 12


class _FakeUnconventionalView(BaseModel):
    """A kind-bearing view whose identity field matches no known convention.

    Proves the header degrades gracefully (bare kind, no crash) rather than
    guessing at an identity field peek.py cannot recognize.
    """

    kind: str = "widget"
    callsign: str = "ALPHA"
    verified_tick: int = 1


class TestDepthValidation:
    """The hard depth<=3 bound: a single range check, statically provable."""

    def test_the_hard_bound_constant_is_three(self) -> None:
        assert MAX_DEPTH == 3

    def test_it_rejects_a_negative_depth(self) -> None:
        with pytest.raises(ValueError, match="depth"):
            peek(WAYNE, -1)

    def test_it_rejects_a_depth_past_the_hard_bound(self) -> None:
        with pytest.raises(ValueError, match="depth"):
            peek(WAYNE, MAX_DEPTH + 1)

    @pytest.mark.parametrize("depth", [0, 1, 2, 3])
    def test_every_depth_in_bounds_is_accepted(self, depth: int) -> None:
        peek(WAYNE, depth)  # must not raise


class TestDepthSizeMapping:
    """Pins the depth→size mapping exactly, by row count and renderable shape."""

    def test_depth_zero_returns_bare_text_not_a_panel(self) -> None:
        assert isinstance(peek(WAYNE, 0), Text)

    @pytest.mark.parametrize("depth", [1, 2, 3])
    def test_depth_one_through_three_return_a_bordered_panel(self, depth: int) -> None:
        assert isinstance(peek(WAYNE, depth), Panel)

    def test_depth_zero_shows_only_the_first_declared_field(self) -> None:
        text = peek(WAYNE, 0)
        assert isinstance(text, Text)
        assert "population" in text.plain
        assert "median_wage" not in text.plain

    def test_depth_one_caps_at_three_rows(self) -> None:
        rows = _rows_of(peek(WAYNE, 1))
        assert len(rows) == 3
        joined = "\n".join(rows)
        assert "population" in joined
        assert "class_composition.bourgeoisie" in joined
        assert "class_composition.petit_bourgeoisie" in joined
        assert "median_wage" not in joined

    def test_depth_two_caps_at_six_rows(self) -> None:
        rows = _rows_of(peek(WAYNE, 2))
        assert len(rows) == 6
        joined = "\n".join(rows)
        assert "population" in joined
        assert "class_composition.lumpenproletariat" in joined
        assert "median_wage" not in joined

    def test_depth_three_shows_every_populated_field(self) -> None:
        rows = _rows_of(peek(WAYNE, 3))
        assert len(rows) == _TOTAL_ROWS_WHEN_FULLY_ATTRIBUTED
        joined = "\n".join(rows)
        assert "sovereign_id" in joined
        assert "consciousness.fascist" in joined

    def test_row_counts_never_decrease_as_depth_increases(self) -> None:
        counts = [len(_rows_of(peek(WAYNE, depth))) for depth in range(4)]
        assert counts == sorted(counts)
        assert counts[0] < counts[3]

    def test_the_header_names_the_entity_and_the_tick(self) -> None:
        result = peek(WAYNE, 2)
        assert isinstance(result, Panel)
        assert isinstance(result.title, Text)
        assert result.title.plain == "county/26163 @ T0847"


class TestDispatchOnKind:
    """Dispatch is structural over ``.kind`` — no per-kind branch in peek.py."""

    def test_it_renders_a_kind_never_named_in_peek_py_without_new_code(self) -> None:
        fake = _FakeOrganizationView()
        rows = _rows_of(peek(fake, 3))  # type: ignore[arg-type]
        joined = "\n".join(rows)
        assert "organization_id" not in joined  # folded into the header, not a row
        assert "cadre_level" in joined

    def test_the_header_uses_the_kind_specific_identity_field_convention(self) -> None:
        fake = _FakeOrganizationView()
        result = peek(fake, 1)  # type: ignore[arg-type]
        assert isinstance(result, Panel)
        assert isinstance(result.title, Text)
        assert result.title.plain == "organization/uaw-9999 @ T0012"

    def test_an_unconventional_identity_field_degrades_to_the_bare_kind(self) -> None:
        fake = _FakeUnconventionalView()
        result = peek(fake, 1)  # type: ignore[arg-type]
        assert isinstance(result, Panel)
        assert isinstance(result.title, Text)
        assert result.title.plain == "widget @ T0001"
        rows = _rows_of(result)
        assert any("callsign" in row for row in rows)


class TestAbsenceRendering:
    """A fully-unattributed view renders one honest marker, never an empty plate."""

    @pytest.mark.parametrize("depth", [0, 1, 2, 3])
    def test_a_fully_unattributed_view_renders_a_named_absence_marker(self, depth: int) -> None:
        rows = _rows_of(peek(BARE, depth))
        assert len(rows) == 1
        assert "▌" in rows[0]
        assert "no attributed data" in rows[0]
        assert "county/00000" in rows[0]


class TestDeterminism:
    """Identical inputs render identical output — no wall-clock, no randomness."""

    def test_two_calls_with_the_same_view_and_depth_are_equal(self) -> None:
        first = peek(WAYNE, 2)
        second = peek(WAYNE, 2)
        assert _rows_of(first) == _rows_of(second)
