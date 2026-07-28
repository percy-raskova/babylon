"""The ``[render]`` config contract (ADR097 D4).

``babylon doctor`` persists the probed tier here; runtime only ever reads it.
Writes are read-modify-write via tomlkit so ADR096's ``babylon doctor
--provision`` tables (and any hand-added config) survive untouched.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from pathlib import Path

import tomlkit
from pydantic import BaseModel, ConfigDict

from babylon.intelligence.providers import _config_dir
from babylon.render.capability import CapabilityReport
from babylon.render.tiers import PaletteTier, RenderTier


class RenderConfig(BaseModel):
    """The runtime-visible slice of ``[render]``.

    Task 35 (contract §7): the pixel facts round-trip so
    ``render_config_json`` can carry them to the Rust client without any
    runtime re-probe (ADR097 D4). ``None`` is honest absence — the persisted
    sentinels are ``""`` for the protocol and ``0`` for the cell dimensions
    (TOML has no null).
    """

    model_config = ConfigDict(frozen=True)

    tier: RenderTier = RenderTier.GLYPH
    palette: PaletteTier = PaletteTier.DEGRADED_256
    pixel_protocol: str | None = None
    cell_width: int | None = None
    cell_height: int | None = None
    in_tmux: bool = False


def render_config_path(env: Mapping[str, str]) -> Path:
    """``config.toml`` under the shared config dir (providers precedence)."""
    return _config_dir(env) / "config.toml"


def read_render_config(config_path: Path) -> RenderConfig:
    """Read the persisted tier, falling back to glyph/256 defaults."""
    try:
        with config_path.open("rb") as handle:
            data = tomllib.load(handle)
    except FileNotFoundError:
        return RenderConfig()
    render = data.get("render", {})
    tier_raw = render.get("tier", RenderTier.GLYPH.value)
    palette_raw = render.get("palette", PaletteTier.DEGRADED_256.value)
    cell_width = int(render.get("cell_width", 0)) or None
    cell_height = int(render.get("cell_height", 0)) or None
    return RenderConfig(
        tier=RenderTier(tier_raw),
        palette=PaletteTier(palette_raw),
        pixel_protocol=str(render.get("pixel_protocol", "")) or None,
        cell_width=cell_width,
        cell_height=cell_height,
        in_tmux=bool(render.get("in_tmux", False)),
    )


def write_render_section(
    config_path: Path,
    report: CapabilityReport,
    tier: RenderTier,
    palette: PaletteTier,
) -> None:
    """Read-modify-write only the ``[render]`` table; preserve every other table."""
    if config_path.exists():
        document = tomlkit.parse(config_path.read_text(encoding="utf-8"))
    else:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        document = tomlkit.document()

    render = tomlkit.table()
    render["tier"] = tier.value
    render["palette"] = palette.value
    render["probed_term"] = report.term
    render["truecolor"] = report.truecolor
    render["pixel_protocol"] = report.pixel_protocol or ""
    render["in_tmux"] = report.in_tmux
    render["cell_width"] = report.cell_width or 0
    render["cell_height"] = report.cell_height or 0
    document["render"] = render

    config_path.write_text(tomlkit.dumps(document), encoding="utf-8")


def resolve_active_tier(override: RenderTier | None, cfg: RenderConfig) -> RenderTier:
    """A ``--render`` override wins for the session; else the persisted tier."""
    return override if override is not None else cfg.tier
