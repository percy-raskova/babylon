"""ProductionDialectic — LaborProcess ↔ Valorization (V1 Ch7§2, Ch8, Ch9).

Ch7§2: "The production of surplus-value is the differentia specifica
of capitalist production." The labor process (creating use-values)
is subordinated to the valorization process (creating surplus-value).

See Also:
    :mod:`babylon.economics.tensor`: DepartmentRow pole model.
    :class:`babylon.engine.dialectics.base.Dialectic`: Generic base class.
"""

from __future__ import annotations

from typing import Any

from babylon.economics.tensor import DepartmentRow
from babylon.engine.dialectics.base import Dialectic, EmptyPole, TickInputs, WorldView


class ProductionDialectic(Dialectic[DepartmentRow, EmptyPole]):
    """The labor process ↔ valorization process contradiction (V1 Ch7§2).

    Ch7§2: "The production of surplus-value is the differentia specifica
    of capitalist production." The labor process (creating use-values)
    is subordinated to the valorization process (creating surplus-value).

    Weight semantics:
        weight < 0 → labor process dominant (A): production for use.
        weight > 0 → valorization dominant (B): production for profit.

    observe() returns the **value tensor** [l, c, v, s, r]:
        l = v + s (living labor / new value added)
        c = constant capital transferred
        v = variable capital (value of labor-power)
        s = surplus-value
        r = s/v (rate of exploitation)
    """

    type_tag: str = "ProductionDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> ProductionDialectic:
        """Motion law T for the production contradiction.

        Higher exploitation rates push weight positive (toward valorization).
        Uses upstream input if available, otherwise falls back to internal state.

        Args:
            inputs: Upstream outputs. Looks for ``rate_of_exploitation``.
            world: Read-only world context.

        Returns:
            New ProductionDialectic with updated weight and tick.
        """
        delta = 0.0
        e = self.pole_a.exploitation_rate

        # Check for upstream input (from LaborProcessDialectic)
        own_input = inputs.upstream.get(self.id)
        if own_input is not None:
            e = float(own_input.get("rate_of_exploitation", e))

        # Exploitation above 1.0 pushes toward valorization dominance
        if e > 0:
            delta = (e - 1.0) * 0.05

        new_weight = max(-1.0, min(1.0, self.weight + delta))
        return self.model_copy(update={"weight": new_weight, "tick_updated": world.tick})

    def observe(self) -> dict[str, Any]:
        """Project the value tensor [l, c, v, s, r] + labor pool.

        Ch8: Total value = c + v + s = c + l, where l = v + s.

        Returns:
            Value tensor components, OCC, and labor pool contribution.
        """
        c = float(self.pole_a.c)
        v = float(self.pole_a.v)
        s = float(self.pole_a.s)
        e = self.pole_a.exploitation_rate

        obs = super().observe()
        obs.update(
            {
                "c": c,
                "v": v,
                "s": s,
                "l": v + s,  # Living labor = new value
                "r": e,  # Rate of exploitation alias
                "rate_of_exploitation": e,
                "occ": self.pole_a.organic_composition,
            }
        )
        return obs

    def invariants(self) -> list[str]:
        """Production-specific invariants.

        Checks:
            - Surplus value ≥ 0.

        Returns:
            List of violation descriptions.
        """
        violations = super().invariants()
        if self.pole_a.s < 0:
            violations.append(f"ProductionDialectic {self.id}: s is negative")
        return violations


__all__ = [
    "ProductionDialectic",
]
