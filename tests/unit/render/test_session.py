"""Session override resolution (ADR097 D4): --render wins over persisted config."""

from __future__ import annotations

from pathlib import Path

from babylon.render.session import active_render_tier
from babylon.render.tiers import RenderTier


def test_override_wins_over_config(tmp_path: Path) -> None:
    (tmp_path / "config.toml").write_text(
        '[render]\ntier = "glyph"\npalette = "256"\n', encoding="utf-8"
    )
    env = {"BABYLON_CONFIG_DIR": str(tmp_path)}
    assert active_render_tier(RenderTier.PIXEL, env) is RenderTier.PIXEL


def test_no_override_uses_persisted_tier(tmp_path: Path) -> None:
    (tmp_path / "config.toml").write_text(
        '[render]\ntier = "pixel"\npalette = "truecolor"\n', encoding="utf-8"
    )
    env = {"BABYLON_CONFIG_DIR": str(tmp_path)}
    assert active_render_tier(None, env) is RenderTier.PIXEL


def test_no_override_no_config_defaults_glyph(tmp_path: Path) -> None:
    env = {"BABYLON_CONFIG_DIR": str(tmp_path)}
    assert active_render_tier(None, env) is RenderTier.GLYPH
