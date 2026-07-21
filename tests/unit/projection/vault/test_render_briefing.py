"""Tests for babylon.projection.vault.render_briefing (WO-35).

Golden-content contract for the briefing dossier page: the codename regex,
the five pattern sections, the win badge, and the "100 years" horizon
framing all match ``lobby-briefing.spec.ts``'s acceptance (spec-116
FR-116-3) — the e2e behavior this WO ports into a projection contract test.
"""

from __future__ import annotations

import re
from uuid import UUID

from babylon.config.defines import GameDefines
from babylon.projection.briefing import project_briefing
from babylon.projection.vault.render_briefing import render_briefing

_SESSION = UUID("12345678-1234-5678-1234-567812345678")


def _view(**overrides: object):
    kwargs: dict[str, object] = {"tick": 0, "defines": GameDefines()}
    kwargs.update(overrides)
    return project_briefing(_SESSION, **kwargs)  # type: ignore[arg-type]


class TestRenderBriefing:
    """Content contract: frontmatter, codename, five patterns, horizon."""

    def test_it_renders_frontmatter_with_the_stable_id_slug_and_verified_tick(self) -> None:
        page = render_briefing(_view())
        assert page.startswith("---\n")
        assert f"id: briefing/{_SESSION}" in page
        assert "verified_tick: 0" in page

    def test_it_renders_the_operation_codename_matching_the_e2e_acceptance(self) -> None:
        page = render_briefing(_view())
        match = re.search(r"OPERATION [A-Z]+ [A-Z]+", page)
        assert match is not None, page

    def test_it_renders_a_statblock_carrying_the_briefing_numbers(self) -> None:
        view = _view()
        page = render_briefing(view)
        assert f"{{statblock}} briefing/{_SESSION}" in page
        assert f"codename: {view.codename}" in page
        assert "horizon_years: 100" in page
        assert "horizon_ticks: 5200" in page
        assert "win_objective_id: revolution" in page

    def test_it_renders_exactly_five_pattern_sections(self) -> None:
        view = _view()
        page = render_briefing(view)
        for objective in view.objectives:
            assert f"### {objective.title}" in page
            assert objective.description in page
        assert page.count("- id: `") == 5

    def test_it_renders_the_win_badge_on_exactly_the_revolution_pattern(self) -> None:
        page = render_briefing(_view())
        assert page.count("THE WIN CONDITION") == 1
        assert "### Revolutionary Victory — THE WIN CONDITION" in page

    def test_it_renders_the_fixed_horizon_framing(self) -> None:
        page = render_briefing(_view())
        assert "100 years" in page
        assert "5200 weekly turns" in page

    def test_it_is_a_pure_function_of_its_input(self) -> None:
        view = _view()
        first = render_briefing(view)
        second = render_briefing(view)
        assert first == second

    def test_two_independently_projected_views_render_byte_identical(self) -> None:
        """Two independent project_briefing calls with the same inputs yield
        byte-identical pages — the determinism double-bake DoD leans on."""
        first = render_briefing(project_briefing(_SESSION, tick=0, defines=GameDefines()))
        second = render_briefing(project_briefing(_SESSION, tick=0, defines=GameDefines()))
        assert first == second
