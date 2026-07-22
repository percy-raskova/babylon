"""The Dashboard domain view — the economy read-model.

Renders T3's :class:`~babylon.projection.view_models.EconomyView`: the Fundamental-Theorem
verdict off the ``wage`` opposition balance, the Φ tri-decomposition, the Vol III surplus
split, and the matter book. All values arrive as extensive ratio-of-sums from the projection
(design §C1) — this view only formats them. Honest-None discipline (III.11): an unwired feed
renders as a loud absence, never a fabricated zero.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from babylon.projection.endgame import EndgameStatus
from babylon.projection.view_models import EconomyView

_ABSENT = "— absent (feed unwired)"

_PANE_ABSENT: Final[str] = (
    "▌ dashboard: no EconomyView projected yet (feed wires in at Program 24 P2-P6)."
)
"""Program 24 P1 honest-absence fence: this pane has no live economy projection to render
until the host-side composition root (``babylon.game.session``) wires one in. Constitution
III.11 — never a fabricated number, never a bare placeholder word."""

_HUD_ABSENT: Final[str] = "▌ hud: no EndgameStatus projected yet (feed wires in at Program 24 P4)."
"""Program 24 P4 honest-absence fence: this HUD strip has no live endgame-progress projection
to render until the host-side composition root (``babylon.game.session``) wires one in.
Constitution III.11 — never a fabricated number, never a bare placeholder word."""

_AXIS_ORDER: Final[tuple[tuple[str, str], ...]] = (
    ("revolutionary_victory", "REVOLUTIONARY VICTORY"),
    ("ecological_collapse", "ECOLOGICAL COLLAPSE"),
    ("fascist_consolidation", "FASCIST CONSOLIDATION"),
    ("red_ogv", "RED OGV"),
    ("fragmented_collapse", "FRAGMENTED COLLAPSE"),
)
"""The five recognized patterns, spec-070 FR-033 priority order — the same order
:meth:`~babylon.engine.observers.endgame_detector.EndgameDetector.axis_progress` keys its
payload with, mirrored here only for DISPLAY order (this module never imports the engine;
``EndgameStatus.axes`` arrives as a plain ``dict`` with no ordering guarantee of its own)."""

_BAR_WIDTH: Final[int] = 10
_LABEL_WIDTH: Final[int] = 22


def _bar(value: float) -> str:
    """A ``_BAR_WIDTH``-glyph filled/empty bar for one axis's clamped progress.

    :param value: the axis's progress, expected in ``[0.0, 1.0]`` (clamped defensively —
        the fold in :func:`~babylon.projection.endgame.endgame_status` already clamps every
        gate ratio, but this renderer never trusts an upstream invariant it cannot itself
        verify).
    :returns: a string of exactly ``_BAR_WIDTH`` glyphs, ``█`` for the filled portion and
        ``░`` for the rest.
    """
    clamped = max(0.0, min(1.0, value))
    filled = round(clamped * _BAR_WIDTH)
    return "█" * filled + "░" * (_BAR_WIDTH - filled)


def _axis_value(axes: Mapping[str, Any], key: str) -> float:
    """Read one axis's progress off ``EndgameStatus.axes``, honestly ``0.0`` when unset.

    Mirrors :func:`babylon.projection.briefing._axis_progress`'s own missing/non-numeric
    fallback (the same ``axes`` payload, a different render target) rather than inventing a
    second convention for the same honest-zero reading.

    :param axes: the :attr:`~babylon.projection.endgame.EndgameStatus.axes` payload.
    :param key: the axis name to read.
    :returns: the axis's progress as a float, ``0.0`` if absent/non-numeric.
    """
    value = axes.get(key, 0.0)
    return float(value) if isinstance(value, (int, float)) else 0.0


def _fmt(value: float | None, *, prefix: str = "", digits: int = 4) -> str:
    if value is None:
        return _ABSENT
    return f"{prefix}{value:.{digits}g}"


def render_economy_text(view: EconomyView) -> str:
    """Format the economy read-model as glyph-floor text."""
    if view.wage_balance is None or view.labor_aristocracy_verdict is None:
        theorem = f"FUNDAMENTAL THEOREM: {_ABSENT}"
    else:
        verdict = (
            "revolution impossible (Wc>Vc)"
            if view.labor_aristocracy_verdict
            else "revolution not-impossible (Wc≤Vc)"
        )
        theorem = f"FUNDAMENTAL THEOREM: wage balance {view.wage_balance:+.2f} → {verdict}"
    phi = (
        f"IMPERIAL RENT Φ={_fmt(view.phi_decomposition_total)}"
        f"  (φ_UE={_fmt(view.phi_unequal_exchange)}"
        f" φ_repro={_fmt(view.phi_reproduction)}"
        f" φ_dom={_fmt(view.phi_domestic)})"
    )
    surplus = (
        f"SURPLUS s={_fmt(view.surplus_produced)}"
        f"  (p={_fmt(view.profit_of_enterprise)} i={_fmt(view.interest_burden)}"
        f" r={_fmt(view.ground_rent)} t={_fmt(view.taxes_on_surplus)})"
    )
    matter = (
        f"MATTER O={_fmt(view.overshoot_ratio)}"
        f"  (C={_fmt(view.total_consumption)} B={_fmt(view.total_biocapacity)}"
        f" M̄={_fmt(view.biocapacity_ceiling)})"
    )
    return "\n".join((theorem, phi, surplus, matter))


def render_hud_text(
    status: EndgameStatus,
    *,
    tick: int,
    driver_attached: bool,
    locked: bool = False,
    lock_reason: str | None = None,
    awaiting_ack: bool = False,
    busy: bool = False,
    pause_summary: str | None = None,
) -> str:
    """Format the live HUD strip: tick/horizon counter, five endgame axis progress
    bars, and the paced driver's lock/pause state (Program 24 P4).

    :param status: this tick's folded :class:`~babylon.projection.endgame.EndgameStatus`
        (``EndgameDetector.axis_progress()``/``recognized_pattern``/``pattern_since_tick``,
        folded host-side by :meth:`~babylon.game.session.GameSession.endgame_status`).
    :param tick: the campaign's current committed tick — ``CampaignHandle.tick``, not itself
        an ``EndgameStatus`` field (that model carries only the fixed ``horizon_tick``).
    :param driver_attached: whether a :class:`~babylon.tui.app.PacedDriverHandle` is wired at
        all; ``False`` renders the pacing line as its own honest absence rather than
        conflating "no driver wired" with a driver that happens to be unlocked and idle.
    :param locked: :attr:`~babylon.tui.app.PacedDriverHandle.locked` (ignored when
        ``driver_attached`` is ``False``).
    :param lock_reason: :attr:`~babylon.tui.app.PacedDriverHandle.lock_reason`.
    :param awaiting_ack: :attr:`~babylon.tui.app.PacedDriverHandle.awaiting_ack`.
    :param busy: :attr:`~babylon.tui.app.PacedDriverHandle.busy`.
    :param pause_summary: :attr:`~babylon.tui.app.PacedDriverHandle.pause_summary`.
    :returns: the HUD strip's glyph-floor body text.
    """
    counter = f"T+{tick}/{status.horizon_tick}"
    axis_lines = (
        f"{label:<{_LABEL_WIDTH}}[{_bar(_axis_value(status.axes, key))}] "
        f"{_axis_value(status.axes, key):.2f}"
        for key, label in _AXIS_ORDER
    )
    if not driver_attached:
        pacing = "PACING: no paced driver attached"
    elif locked:
        pacing = f"PACING: LOCKED — {lock_reason}"
    elif awaiting_ack:
        pacing = f"PACING: autopause pending ({pause_summary}) — press 'a' to acknowledge"
    elif busy:
        pacing = "PACING: a run is already in progress"
    else:
        pacing = "PACING: ready"
    return "\n".join((counter, *axis_lines, pacing))


class DashboardView(Widget):
    """Economic dashboard pane."""

    def compose(self) -> ComposeResult:
        yield Static(_HUD_ABSENT, id="dashboard-hud")
        yield Static(_PANE_ABSENT, id="dashboard-body")

    def render_economy(self, view: EconomyView) -> str:
        """Render ``view`` as the pane's glyph-floor body text, replacing the pane body."""
        text = render_economy_text(view)
        self.query_one("#dashboard-body", Static).update(text)
        return text

    def render_hud(
        self,
        status: EndgameStatus,
        *,
        tick: int,
        driver_attached: bool,
        locked: bool = False,
        lock_reason: str | None = None,
        awaiting_ack: bool = False,
        busy: bool = False,
        pause_summary: str | None = None,
    ) -> str:
        """Render the live HUD strip (Program 24 P4), replacing the pane's HUD region.

        See :func:`render_hud_text` for the parameters' meaning.
        """
        text = render_hud_text(
            status,
            tick=tick,
            driver_attached=driver_attached,
            locked=locked,
            lock_reason=lock_reason,
            awaiting_ack=awaiting_ack,
            busy=busy,
            pause_summary=pause_summary,
        )
        self.query_one("#dashboard-hud", Static).update(text)
        return text
