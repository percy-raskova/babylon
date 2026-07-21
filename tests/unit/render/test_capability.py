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

    def __init__(self, *, is_tty: bool, protocol: str | None) -> None:
        self._is_tty = is_tty
        self._protocol = protocol

    def is_a_tty(self) -> bool:
        return self._is_tty

    def detect_pixel_protocol(self) -> str | None:
        return self._protocol


def _probe(env: Mapping[str, str], *, is_tty: bool, protocol: str | None) -> CapabilityReport:
    querier: TerminalQuerier = FakeQuerier(is_tty=is_tty, protocol=protocol)
    return probe(env, querier)


def test_kitty_truecolor_tty_is_pixel_truecolor() -> None:
    report = _probe(
        {"TERM": "xterm-kitty", "COLORTERM": "truecolor"}, is_tty=True, protocol="kitty"
    )
    assert report.truecolor is True
    assert report.pixel_protocol == "kitty"
    assert derive_tiers(report) == (RenderTier.PIXEL, PaletteTier.TRUECOLOR)


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
