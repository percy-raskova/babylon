"""Tests for babylon.projection.vault.render_key_figure: the honest-absence key-figure page.

StrictUndefined/sandbox behavior of the shared Jinja environment factory is
already proven once by ``test_render.py::TestSandboxedEnvironment`` against
``babylon.projection.vault.render._build_environment`` — this module imports
that same factory (see ``render_key_figure``'s module docstring for why) and
does not re-verify it here (ADR099: one factory, one proof).
"""

from __future__ import annotations

from babylon.projection.key_figure import DEAD_PRODUCER_REMEDY
from babylon.projection.vault.render_key_figure import render_key_figure
from babylon.projection.view_models import KeyFigureView


def _view(key_figure_id: str = "kf-001", tick: int = 500) -> KeyFigureView:
    return KeyFigureView(key_figure_id=key_figure_id, verified_tick=tick)


class TestRenderKeyFigure:
    """Content contract: frontmatter and the one honest-absence block."""

    def test_it_renders_frontmatter_with_the_stable_id_slug_and_verified_tick(self) -> None:
        page = render_key_figure(_view(), verified_tick=500)
        assert page.startswith("---\n")
        assert "id: key_figure/kf-001" in page
        assert "verified_tick: 500" in page

    def test_it_renders_exactly_one_absence_block_naming_the_dead_producer(self) -> None:
        page = render_key_figure(_view(), verified_tick=500)
        assert page.count("{absence}") == 1
        assert "{absence} key_figure —" in page
        assert "ADR084" in page
        assert DEAD_PRODUCER_REMEDY in page

    def test_it_emits_no_statblock_fence(self) -> None:
        """An empty {statblock} fence is the keel's LIVE-page signal (P1 WO-7b);
        this baked page is never live, so it emits none at all rather than an
        empty one that would invite that ambiguity (see the template's own
        comment)."""
        page = render_key_figure(_view(), verified_tick=500)
        assert "{statblock}" not in page

    def test_it_never_renders_a_bare_none(self) -> None:
        page = render_key_figure(_view(), verified_tick=500)
        assert "None" not in page

    def test_it_is_a_pure_function_of_its_inputs(self) -> None:
        first = render_key_figure(_view(), verified_tick=500)
        second = render_key_figure(_view(), verified_tick=500)
        assert first == second

    def test_different_ids_render_different_frontmatter_but_the_same_absence_text(self) -> None:
        """The dossier is identity-parameterized but data-identical for every id."""
        page_a = render_key_figure(_view("kf-001"), verified_tick=500)
        page_b = render_key_figure(_view("kf-002"), verified_tick=500)

        assert "id: key_figure/kf-001" in page_a
        assert "id: key_figure/kf-002" in page_b
        assert DEAD_PRODUCER_REMEDY in page_a
        assert DEAD_PRODUCER_REMEDY in page_b
