"""The Dashboard domain view — the economy read-model.

Renders T3's :class:`~babylon.projection.view_models.EconomyView`: the Fundamental-Theorem
verdict off the ``wage`` opposition balance, the Φ tri-decomposition, the Vol III surplus
split, and the matter book. All values arrive as extensive ratio-of-sums from the projection
(design §C1) — this view only formats them. Honest-None discipline (III.11): an unwired feed
renders as a loud absence, never a fabricated zero.
"""

from __future__ import annotations

from textual.widget import Widget

from babylon.projection.view_models import EconomyView

_ABSENT = "— absent (feed unwired)"


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


class DashboardView(Widget):
    """Economic dashboard pane."""

    def render_economy(self, view: EconomyView) -> str:
        """Render ``view`` as the pane's glyph-floor body text."""
        return render_economy_text(view)
