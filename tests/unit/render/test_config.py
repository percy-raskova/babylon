"""Render config contract (ADR097 D4).

Runtime reads the persisted tier; doctor writes it. The writer must be a
read-modify-write that preserves 096's tables (both are ``babylon doctor``
extensions and must never clobber each other).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from babylon.render.capability import CapabilityReport
from babylon.render.config import (
    RenderConfig,
    read_render_config,
    render_config_path,
    resolve_active_tier,
    write_render_section,
)
from babylon.render.tiers import PaletteTier, RenderTier


def _report(**kw: object) -> CapabilityReport:
    base: dict[str, object] = {
        "term": "xterm-256color",
        "colorterm": "",
        "truecolor": False,
        "has_256": True,
        "in_tmux": False,
        "is_tty": True,
        "pixel_protocol": None,
    }
    base.update(kw)
    return CapabilityReport(**base)  # type: ignore[arg-type]


def test_read_missing_config_returns_defaults(tmp_path: Path) -> None:
    cfg = read_render_config(tmp_path / "config.toml")
    assert cfg.tier is RenderTier.GLYPH
    assert cfg.palette is PaletteTier.DEGRADED_256


def test_round_trip_write_then_read(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    write_render_section(path, _report(truecolor=True), RenderTier.PIXEL, PaletteTier.TRUECOLOR)
    cfg = read_render_config(path)
    assert cfg.tier is RenderTier.PIXEL
    assert cfg.palette is PaletteTier.TRUECOLOR


def test_write_preserves_foreign_tables(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        '[intelligence]\nmode = "auto"\ntimeout_s = 30.0\n\n[provision]\nmodel = "qwen"\n',
        encoding="utf-8",
    )
    write_render_section(path, _report(), RenderTier.GLYPH, PaletteTier.DEGRADED_256)
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    # 096's tables survive untouched.
    assert data["intelligence"] == {"mode": "auto", "timeout_s": 30.0}
    assert data["provision"] == {"model": "qwen"}
    # Ours landed with evidence fields.
    assert data["render"]["tier"] == "glyph"
    assert data["render"]["palette"] == "256"
    assert data["render"]["probed_term"] == "xterm-256color"


def test_rewrite_updates_render_only(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    write_render_section(path, _report(), RenderTier.GLYPH, PaletteTier.DEGRADED_256)
    write_render_section(path, _report(truecolor=True), RenderTier.PIXEL, PaletteTier.TRUECOLOR)
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    assert data["render"]["tier"] == "pixel"
    assert data["render"]["palette"] == "truecolor"


def test_render_config_path_honors_override(tmp_path: Path) -> None:
    path = render_config_path({"BABYLON_CONFIG_DIR": str(tmp_path)})
    assert path == tmp_path / "config.toml"


def test_resolve_active_tier_prefers_override() -> None:
    cfg = RenderConfig(tier=RenderTier.GLYPH, palette=PaletteTier.DEGRADED_256)
    assert resolve_active_tier(RenderTier.PIXEL, cfg) is RenderTier.PIXEL
    assert resolve_active_tier(None, cfg) is RenderTier.GLYPH
