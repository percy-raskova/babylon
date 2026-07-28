"""Probe-once capability contract (ADR097 D4).

Pure env-dict cases with an injected querier: no real terminal is touched. The
probe never re-runs mid-session; these tests pin what a single probe concludes.
"""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from babylon.render.capability import (
    CapabilityReport,
    TerminalQuerier,
    derive_tiers,
    probe,
    verdict_lines,
)
from babylon.render.tiers import PaletteTier, RenderTier


class FakeQuerier:
    """Stand-in for a real terminal: fully caller-controlled."""

    def __init__(
        self,
        *,
        is_tty: bool,
        protocol: str | None,
        cell_size: tuple[int, int] | None = None,
    ) -> None:
        self._is_tty = is_tty
        self._protocol = protocol
        self._cell_size = cell_size

    def is_a_tty(self) -> bool:
        return self._is_tty

    def detect_pixel_protocol(self) -> str | None:
        return self._protocol

    def detect_cell_size(self) -> tuple[int, int] | None:
        return self._cell_size


def _probe(
    env: Mapping[str, str],
    *,
    is_tty: bool,
    protocol: str | None,
    cell_size: tuple[int, int] | None = None,
) -> CapabilityReport:
    querier: TerminalQuerier = FakeQuerier(is_tty=is_tty, protocol=protocol, cell_size=cell_size)
    return probe(env, querier)


def test_kitty_truecolor_tty_with_cell_size_is_pixel_truecolor() -> None:
    report = _probe(
        {"TERM": "xterm-kitty", "COLORTERM": "truecolor"},
        is_tty=True,
        protocol="kitty",
        cell_size=(9, 18),
    )
    assert report.truecolor is True
    assert report.pixel_protocol == "kitty"
    assert (report.cell_width, report.cell_height) == (9, 18)
    assert derive_tiers(report) == (RenderTier.PIXEL, PaletteTier.TRUECOLOR)


def test_kitty_without_cell_size_demotes_to_glyph_and_declares_it() -> None:
    # Contract §7 (Task 35): the pixel tier's FontSize prerequisite — kitty
    # with unknown cell pixel dimensions cannot construct a StatefulProtocol
    # without re-probing, so the VERDICT is glyph, declared aloud.
    report = _probe(
        {"TERM": "xterm-kitty", "COLORTERM": "truecolor"},
        is_tty=True,
        protocol="kitty",
        cell_size=None,
    )
    assert report.pixel_protocol == "kitty"
    assert report.cell_width is None
    tier, palette = derive_tiers(report)
    assert tier is RenderTier.GLYPH
    joined = "\n".join(verdict_lines(report, tier, palette))
    assert "cell pixel size" in joined
    assert "degraded" in joined.lower()


def test_sixel_demotes_to_glyph_with_declared_note() -> None:
    # ADR099: sixel is not a target — recorded as evidence, never a pixel tier.
    report = _probe(
        {"TERM": "foot", "COLORTERM": "truecolor"},
        is_tty=True,
        protocol="sixel",
        cell_size=(8, 16),
    )
    assert report.pixel_protocol == "sixel"
    tier, palette = derive_tiers(report)
    assert tier is RenderTier.GLYPH
    joined = "\n".join(verdict_lines(report, tier, palette))
    assert "sixel" in joined
    assert "not a target" in joined


def test_cell_size_not_consulted_off_tty_or_inside_tmux() -> None:
    non_tty = _probe({"TERM": "xterm-kitty"}, is_tty=False, protocol=None, cell_size=(9, 18))
    assert (non_tty.cell_width, non_tty.cell_height) == (None, None)
    tmuxed = _probe(
        {"TERM": "tmux-256color", "TMUX": "/tmp/tmux-1000/default,1,0"},
        is_tty=True,
        protocol="kitty",
        cell_size=(9, 18),
    )
    assert (tmuxed.cell_width, tmuxed.cell_height) == (None, None)


def test_gnome_vte_256_no_pixel_is_glyph_truecolor() -> None:
    # VTE reports truecolor via COLORTERM but has no pixel protocol.
    report = _probe(
        {"TERM": "xterm-256color", "COLORTERM": "truecolor"}, is_tty=True, protocol=None
    )
    assert report.has_256 is True
    assert report.pixel_protocol is None
    assert derive_tiers(report) == (RenderTier.GLYPH, PaletteTier.TRUECOLOR)


def test_tmux_forces_glyph_even_if_querier_claims_pixel() -> None:
    # Inside tmux, passthrough is not assumed: honest glyph, protocol suppressed.
    report = _probe(
        {"TERM": "tmux-256color", "TMUX": "/tmp/tmux-1000/default,1,0"},
        is_tty=True,
        protocol="kitty",
    )
    assert report.in_tmux is True
    assert report.pixel_protocol is None
    assert derive_tiers(report)[0] is RenderTier.GLYPH


def test_dumb_terminal_is_glyph_degraded() -> None:
    report = _probe({"TERM": "dumb"}, is_tty=True, protocol=None)
    assert report.truecolor is False
    assert report.has_256 is False
    assert derive_tiers(report) == (RenderTier.GLYPH, PaletteTier.DEGRADED_256)


def test_non_tty_ci_never_reports_pixel() -> None:
    # CI / piped output: no TTY, so the pixel query is not even consulted.
    report = _probe(
        {"TERM": "xterm-256color", "COLORTERM": "truecolor", "CI": "true"},
        is_tty=False,
        protocol="sixel",
    )
    assert report.is_tty is False
    assert report.pixel_protocol is None
    assert derive_tiers(report)[0] is RenderTier.GLYPH


def test_report_is_frozen() -> None:
    report = _probe({"TERM": "dumb"}, is_tty=False, protocol=None)
    with pytest.raises(Exception):  # noqa: B017 - pydantic frozen raises ValidationError
        report.truecolor = True  # type: ignore[misc]


def test_verdict_lines_declare_degradation() -> None:
    report = _probe({"TERM": "xterm-256color"}, is_tty=True, protocol=None)
    tier, palette = derive_tiers(report)
    lines = verdict_lines(report, tier, palette)
    joined = "\n".join(lines)
    assert "render tier: glyph" in joined
    assert "palette: 256" in joined
    assert "degraded" in joined.lower()
