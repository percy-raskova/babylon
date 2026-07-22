"""Behavioral contract for the DashboardView economy read-model renderer (Task 6).

Binds to T3's REAL ``babylon.projection.view_models.EconomyView`` (landed with the
overnight cascade) — not the plan's pre-merge ``EconomyViewLike`` placeholder contract.
"""

from babylon.projection.view_models import EconomyView
from babylon.tui.shell.views.dashboard_view import render_economy_text


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
