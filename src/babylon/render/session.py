"""Per-session render override (ADR097 D4).

``babylon --render=glyph|pixel`` sets a process-wide override; runtime resolves
the active tier as override-else-persisted. The override never re-probes and is
never written back to config (it is a session-only decision).
"""

from __future__ import annotations

from collections.abc import Mapping

from babylon.render.config import read_render_config, render_config_path, resolve_active_tier
from babylon.render.tiers import RenderTier

_SESSION_OVERRIDE: RenderTier | None = None


def set_render_override(tier: RenderTier | None) -> None:
    """Record the ``--render`` choice for this process (None clears it)."""
    global _SESSION_OVERRIDE
    _SESSION_OVERRIDE = tier


def get_render_override() -> RenderTier | None:
    return _SESSION_OVERRIDE


def active_render_tier(override: RenderTier | None, env: Mapping[str, str]) -> RenderTier:
    """Resolve the tier a session should render at: override else persisted config."""
    cfg = read_render_config(render_config_path(env))
    return resolve_active_tier(override, cfg)
