"""Archive-side endgame status — the century-horizon fold (WO-39).

Relocated from the legacy web bridge so the TUI determines game-over
independently of it. Doctrine (owner ruling 2026-07-17, spec-116): the
five patterns are RECOGNIZED, never adjudicated — recognizing a pattern
does not end the game; the game ends only at the fixed campaign horizon,
with :data:`GameOutcome.UNRESOLVED` when no pattern is held at that tick.

Pure fold over detector OUTPUTS (pattern, since-tick, axes): the
``EndgameDetector`` itself is an engine observer and stays engine-side —
projection never imports the engine (import-linter contract). The runner
threads the detector's state across this seam as plain data.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from babylon.config.defines import GameDefines
from babylon.models.enums.events import GameOutcome


def campaign_horizon_tick(defines: GameDefines) -> int:
    """The fixed game-over tick: campaign years times weeks per year.

    :param defines: The coefficient source.
    :returns: The horizon tick (inclusive — the game ends AT this tick).
    """
    return defines.endgame.campaign_horizon_years * defines.timescale.weeks_per_year


class EndgameStatus(BaseModel):
    """The recognized-pattern status at one tick.

    :ivar pattern: The currently recognized pattern, or ``None``.
    :ivar outcome: The outcome as of now — the held pattern, else
        :data:`GameOutcome.UNRESOLVED`.
    :ivar game_over: Whether the campaign has ended (horizon reached or
        explicitly forced).
    :ivar horizon_tick: The fixed campaign horizon.
    :ivar since_tick: The tick the current pattern was first recognized.
    :ivar locked: Whether the pattern has been held for at least the
        lock window (inclusive: ``tick - since + 1``).
    :ivar axes: The detector's per-axis progress payload, verbatim.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    pattern: GameOutcome | None
    outcome: GameOutcome
    game_over: bool
    horizon_tick: int
    since_tick: int | None
    locked: bool
    axes: dict[str, Any]


def endgame_status(
    *,
    tick: int,
    pattern: GameOutcome | None,
    since_tick: int | None,
    defines: GameDefines,
    axes: dict[str, Any] | None = None,
    force_game_over: bool = False,
) -> EndgameStatus:
    """Fold detector outputs into the Archive's endgame status.

    Verbatim relocation of the legacy bridge's recognition block (minus its
    web-session detector cache — the caller owns detector lifetime).

    :param tick: The current tick.
    :param pattern: The detector's currently recognized pattern.
    :param since_tick: When that pattern was first recognized.
    :param defines: The coefficient source.
    :param axes: The detector's ``axis_progress()`` payload.
    :param force_game_over: Test/e2e hook parity — ends the campaign now.
    :returns: The frozen status.
    """
    horizon = campaign_horizon_tick(defines)
    return EndgameStatus(
        pattern=pattern,
        outcome=pattern or GameOutcome.UNRESOLVED,
        game_over=tick >= horizon or force_game_over,
        horizon_tick=horizon,
        since_tick=since_tick,
        locked=(
            pattern is not None
            and since_tick is not None
            and (tick - since_tick + 1) >= defines.endgame.pattern_lock_ticks
        ),
        axes=dict(axes) if axes else {},
    )
