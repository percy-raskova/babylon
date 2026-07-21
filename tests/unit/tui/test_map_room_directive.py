"""Unit tests for the ``{maproom}`` directive + ``babylon.tui.map_room`` (WO-33).

Deliberately a *separate* test file from ``tests/unit/tui/test_directives.py``:
that file is not one of the WO-33 shared-file zipper points (only
``view_models.py``, ``registry.py``, and ``directives.py`` itself are), and
several Lane T work orders add their own directive simultaneously — keeping
each WO's directive tests in its own file avoids gratuitous merge collisions
in a file nobody declared shared.
"""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Label
from textual_image.widget import HalfcellImage, TGPImage

from babylon.projection.topology.choropleth import ChoroplethCell
from babylon.tui.directives import BabylonFence, parse_maproom_body
from babylon.tui.map_room import build_choropleth_image, render_map_room


class _FenceHost(App[None]):
    """Bare app hosting an arbitrary markdown fragment (mirrors test_directives.py)."""

    def __init__(self, markdown: str) -> None:
        super().__init__()
        self._markdown = markdown

    def compose(self) -> ComposeResult:
        from babylon.tui.app import BabylonMarkdown

        yield BabylonMarkdown(self._markdown, open_links=False)


class TestParseMaproomBody:
    def test_parses_tier_and_region_values(self) -> None:
        tier, cells = parse_maproom_body("tier: state\n26: 0.500000\n27: 1.250000\n")
        assert tier == "state"
        assert cells == (
            ChoroplethCell(region_id="26", exploitation_rate=0.5),
            ChoroplethCell(region_id="27", exploitation_rate=1.25),
        )

    def test_bare_region_line_is_honest_absence(self) -> None:
        _tier, cells = parse_maproom_body("tier: ea\n08:\n")
        assert cells == (ChoroplethCell(region_id="08", exploitation_rate=None),)

    def test_preserves_body_order_not_sorted(self) -> None:
        _tier, cells = parse_maproom_body("tier: county\n26163: 0.1\n26001: 0.2\n")
        assert [cell.region_id for cell in cells] == ["26163", "26001"]

    def test_rejects_missing_tier_line(self) -> None:
        with pytest.raises(ValueError, match="tier:"):
            parse_maproom_body("26: 0.5\n")

    def test_rejects_unknown_tier(self) -> None:
        with pytest.raises(ValueError, match="ea/state/county"):
            parse_maproom_body("tier: nation\n")

    def test_rejects_a_line_with_no_separator(self) -> None:
        with pytest.raises(ValueError, match="':'"):
            parse_maproom_body("tier: state\nbogus line\n")

    def test_rejects_a_non_numeric_value(self) -> None:
        with pytest.raises(ValueError, match="non-numeric"):
            parse_maproom_body("tier: state\n26: not-a-number\n")


class TestDirectiveMaproomDispatch:
    @pytest.mark.asyncio
    async def test_it_renders_the_cell_art_floor_for_a_well_formed_body(self) -> None:
        app = _FenceHost("```{maproom}\ntier: state\n26: 0.500000\n```")
        async with app.run_test():
            fence = app.query_one(BabylonFence)
            widgets = list(fence.query(HalfcellImage))
            assert len(widgets) == 1

    @pytest.mark.asyncio
    async def test_it_never_renders_tgp_raster_from_the_directive(self) -> None:
        """No capability flag reaches fenced-directive dispatch yet — always glyph."""
        app = _FenceHost("```{maproom}\ntier: county\n26163: 3.000000\n```")
        async with app.run_test():
            fence = app.query_one(BabylonFence)
            assert not list(fence.query(TGPImage))
            assert list(fence.query(HalfcellImage))

    @pytest.mark.asyncio
    async def test_it_refuses_a_malformed_body_loudly(self) -> None:
        app = _FenceHost("```{maproom}\nbogus\n```")
        async with app.run_test():
            fence = app.query_one(BabylonFence)
            labels = list(fence.query(Label))
            assert len(labels) == 1
            assert "ABSENT" in labels[0].content

    @pytest.mark.asyncio
    async def test_it_renders_absence_for_a_tier_with_no_cells(self) -> None:
        """The EA tier's real-world shape today: a tier line, zero data rows
        (babylon.projection.topology.choropleth.ea_choropleth_cells honest
        absence) — never a fabricated cell."""
        app = _FenceHost("```{maproom}\ntier: ea\n```")
        async with app.run_test():
            fence = app.query_one(BabylonFence)
            labels = list(fence.query(Label))
            assert len(labels) == 1
            assert "no choropleth cells" in labels[0].content
            assert "'ea'" in labels[0].content


class TestBuildChoroplethImage:
    def test_image_width_scales_with_cell_count(self) -> None:
        cells = (
            ChoroplethCell(region_id="a", exploitation_rate=0.1),
            ChoroplethCell(region_id="b", exploitation_rate=0.9),
        )
        image = build_choropleth_image(cells, cell_px=10)
        assert image.size == (20, 10)

    def test_empty_cells_still_yield_a_valid_nonzero_image(self) -> None:
        image = build_choropleth_image((), cell_px=10)
        assert image.size == (10, 10)

    def test_is_deterministic(self) -> None:
        cells = (ChoroplethCell(region_id="a", exploitation_rate=1.5),)
        first = build_choropleth_image(cells)
        second = build_choropleth_image(cells)
        assert first.tobytes() == second.tobytes()

    def test_absent_and_extreme_cells_get_different_colors(self) -> None:
        absent = build_choropleth_image(
            (ChoroplethCell(region_id="a", exploitation_rate=None),), cell_px=4
        )
        extreme = build_choropleth_image(
            (ChoroplethCell(region_id="a", exploitation_rate=float("inf")),), cell_px=4
        )
        assert absent.getpixel((0, 0)) != extreme.getpixel((0, 0))


class TestRenderMapRoom:
    """Structural coverage for the TGP/pixel path — deliberately NOT a
    snapshot golden (kitty-protocol bytes are non-deterministic across
    environments; the WO's own ruling reserves that for a manual, real-Kitty
    eyes-on check). This class asserts parity and widget-type selection
    only, never pixel/escape-sequence bytes."""

    def test_glyph_selects_halfcell_image(self) -> None:
        cells = (ChoroplethCell(region_id="26163", exploitation_rate=0.5),)
        widget = render_map_room(cells, render_tier="glyph")
        assert isinstance(widget, HalfcellImage)

    def test_pixel_selects_tgp_image(self) -> None:
        cells = (ChoroplethCell(region_id="26163", exploitation_rate=0.5),)
        widget = render_map_room(cells, render_tier="pixel")
        assert isinstance(widget, TGPImage)

    def test_both_tiers_render_the_identical_source_bitmap(self) -> None:
        """ADR097 D2 information parity, enforced structurally: both widgets
        wrap byte-identical image data for the same cells."""
        cells = (
            ChoroplethCell(region_id="26163", exploitation_rate=0.5),
            ChoroplethCell(region_id="26001", exploitation_rate=None),
        )
        glyph = render_map_room(cells, render_tier="glyph")
        pixel = render_map_room(cells, render_tier="pixel")
        assert glyph.image is not None
        assert pixel.image is not None
        assert glyph.image.tobytes() == pixel.image.tobytes()
