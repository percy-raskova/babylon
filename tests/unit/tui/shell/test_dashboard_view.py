"""Behavioral contract for the DashboardView economy read-model renderer (Task 6).

Binds to T3's REAL ``babylon.projection.view_models.EconomyView`` (landed with the
overnight cascade) — not the plan's pre-merge ``EconomyViewLike`` placeholder contract.

Program 24 P4 adds the HUD strip's own render tests below: ``render_hud_text`` formats
``babylon.projection.endgame.EndgameStatus`` (the SAME fold ``GameSession.endgame_status``
uses live) plus the paced driver's plain-scalar lock/pause state.
"""

from babylon.config.defines import GameDefines
from babylon.models.enums.events import GameOutcome
from babylon.projection.endgame import endgame_status
from babylon.projection.view_models import EconomyView
from babylon.tui.shell.views.dashboard_view import render_economy_text, render_hud_text


def _view(**overrides) -> EconomyView:
    base = {"economy_id": "USA", "verified_tick": 12}
    base.update(overrides)
    return EconomyView(**base)


def test_theorem_verdict_reads_off_wage_balance():
    view = _view(wage_balance=0.25, labor_aristocracy_verdict=True)
    out = render_economy_text(view)
    # Positive balance = wage exceeds value produced = the imperial bribe holds.
    assert "+0.25" in out
    assert "revolution impossible" in out.lower()


def test_phi_tri_decomposition_total_is_shown():
    view = _view(
        phi_unequal_exchange=10.0,
        phi_reproduction=5.0,
        phi_domestic=3.0,
        phi_decomposition_total=18.0,
    )
    out = render_economy_text(view)
    assert "Φ=18" in out


def test_absent_values_render_as_loud_absence_not_zero():
    out = render_economy_text(_view())
    # Honest-None discipline: an unwired feed is an absence block, never a fabricated 0.
    assert "0.0" not in out
    assert "absent" in out.lower() or "unwired" in out.lower()


def test_overshoot_ratio_renders_when_present():
    out = render_economy_text(_view(overshoot_ratio=1.4))
    assert "O=1.4" in out


# --------------------------------------------------------------------------- #
# render_hud_text — the live HUD strip (Program 24 P4): tick/horizon counter,  #
# five endgame axis progress bars, and the paced driver's lock/pause state.    #
# --------------------------------------------------------------------------- #


def _status(axes: dict[str, float]):
    """A real, freshly-folded ``EndgameStatus`` — the same fold ``GameSession.
    endgame_status`` uses live, over the default ``GameDefines`` and no recognized
    pattern (unless a test overrides ``axes`` to imply one via ``pattern=`` below)."""
    return endgame_status(tick=10, pattern=None, since_tick=None, defines=GameDefines(), axes=axes)


def test_counter_shows_the_current_tick_over_the_defines_derived_horizon():
    status = endgame_status(tick=142, pattern=None, since_tick=None, defines=GameDefines())
    out = render_hud_text(status, tick=142, driver_attached=False)
    assert f"T+142/{status.horizon_tick}" in out


def test_all_five_axes_render_with_their_real_progress_value():
    axes = {
        "revolutionary_victory": 0.3,
        "ecological_collapse": 0.0,
        "fascist_consolidation": 0.6,
        "red_ogv": 0.0,
        "fragmented_collapse": 1.0,
    }
    out = render_hud_text(_status(axes), tick=10, driver_attached=False)
    assert "REVOLUTIONARY VICTORY" in out
    assert "0.30" in out
    assert "FASCIST CONSOLIDATION" in out
    assert "0.60" in out
    assert "FRAGMENTED COLLAPSE" in out
    assert "1.00" in out
    # A fully-progressed axis renders a fully-filled bar; a zero axis, fully empty.
    assert "██████████" in out
    assert "░░░░░░░░░░" in out


def test_a_missing_axis_key_reads_honestly_as_zero_not_a_crash():
    out = render_hud_text(_status({}), tick=0, driver_attached=False)
    assert "RED OGV" in out
    assert "0.00" in out


def test_no_driver_attached_renders_its_own_honest_absence():
    out = render_hud_text(_status({}), tick=0, driver_attached=False)
    assert "no paced driver attached" in out


def test_locked_driver_shows_the_lock_reason():
    out = render_hud_text(
        _status({}),
        tick=0,
        driver_attached=True,
        locked=True,
        lock_reason=GameOutcome.FASCIST_CONSOLIDATION,
    )
    assert "LOCKED" in out
    assert "fascist_consolidation" in out


def test_awaiting_ack_shows_the_pause_summary():
    out = render_hud_text(
        _status({}),
        tick=0,
        driver_attached=True,
        awaiting_ack=True,
        pause_summary="tick 5: some critical event",
    )
    assert "autopause pending" in out
    assert "tick 5: some critical event" in out


def test_busy_driver_shows_a_run_in_progress():
    out = render_hud_text(_status({}), tick=0, driver_attached=True, busy=True)
    assert "run" in out.lower()


def test_idle_unlocked_driver_shows_ready():
    out = render_hud_text(_status({}), tick=0, driver_attached=True)
    assert "PACING: ready" in out
