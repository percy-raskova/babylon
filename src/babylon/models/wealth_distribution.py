"""National wealth-distribution state — the 4-bracket axis (Program 21 Phase 1).

The wealth partition is **national and 4-class** (top-1% / p90-99 / p50-90 /
bottom-50, the FRED-DFA / WID quantile structure pinned by
``tests/unit/config/test_wealth_distribution_invariants.py``), distinct from
the per-county 5-class **population** partition the tick engine carries. This
model is the graph-metadata carrier for that axis: ``WorldState`` holds it as
an optional field and round-trips it via ``G.graph["wealth_distribution"]``
(the ``economy``/``state_finances`` metadata pattern), written only when set
so axis-less graphs stay byte-identical (the EH ruling-6 precedent).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

#: Conservation tolerance: shares are renormalized by the writer, so any
#: drift beyond this is a bug upstream, not float noise.
_SUM_TOLERANCE = 1e-6


class WealthDistribution(BaseModel):
    """The national 4-bracket wealth-share vector and its ODE velocities.

    :ivar shares: ``(w1, w2, w3, w4)`` — wealth held by top-1% / p90-99 /
        p50-90 / bottom-50. Must sum to 1 (conservation of the whole).
    :ivar velocities: ``(dw1..dw4)/dt`` — the second-order ODE momentum state
        (``formulas.class_dynamics``), quarterly units.
    :ivar tick: the tick this vector was computed at.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    shares: tuple[float, float, float, float]
    velocities: tuple[float, float, float, float]
    tick: int

    @model_validator(mode="after")
    def _validate_conservation(self) -> WealthDistribution:
        """Reject a non-conserving vector loudly (Constitution III.11).

        :returns: ``self`` when the shares sum to 1 within tolerance.
        :raises ValueError: if any share is outside ``[0, 1]`` or the vector
            does not sum to 1.
        """
        for share in self.shares:
            if not 0.0 <= share <= 1.0:
                raise ValueError(f"wealth share {share!r} outside [0, 1]")
        total = sum(self.shares)
        if abs(total - 1.0) > _SUM_TOLERANCE:
            raise ValueError(f"wealth shares must sum to 1.0, got {total!r}")
        return self
