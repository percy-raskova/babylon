"""The render half of ``babylon doctor`` (ADR097 D4): probe once, persist, report."""

from __future__ import annotations

import tomllib
from pathlib import Path

from babylon.render.capability import TerminalQuerier
from babylon.render.doctor import run_render_probe


class _Q:
    def __init__(self, *, is_tty: bool, protocol: str | None) -> None:
        self._is_tty = is_tty
        self._protocol = protocol

    def is_a_tty(self) -> bool:
        return self._is_tty

    def detect_pixel_protocol(self) -> str | None:
        return self._protocol


def test_run_render_probe_persists_and_reports(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    queries: TerminalQuerier = _Q(is_tty=True, protocol="kitty")
    lines = run_render_probe({"TERM": "xterm-kitty", "COLORTERM": "truecolor"}, queries, path)
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    assert data["render"]["tier"] == "pixel"
    assert data["render"]["palette"] == "truecolor"
    assert any("render tier: pixel" in line for line in lines)


def test_run_render_probe_declares_glyph_degradation(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    queries: TerminalQuerier = _Q(is_tty=False, protocol=None)
    lines = run_render_probe({"TERM": "dumb"}, queries, path)
    joined = "\n".join(lines)
    assert "render tier: glyph" in joined
    assert "degraded" in joined.lower()
