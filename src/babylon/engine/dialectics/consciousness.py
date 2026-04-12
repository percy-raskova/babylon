"""Class Consciousness Dialectics (Lukacs, MIM(P)).

This module contains the `ClassConsciousnessDialectic`, linking the spontaneous,
reified material conditions (Pole A) to the imputed, revolutionary consciousness
(Pole B) orchestrated by a vanguard.

Weight semantics:
    -1.0 <= weight < 0: Reified/Trade-Union consciousness dominates. The population
        is anchored to its immediate material conditions (capitalist hegemony). For
        the labor aristocracy, this represents the bribed consciousness.
    weight > 0: Imputed/Revolutionary consciousness dominates. The population
        has achieved the subject-object of history status.

See Also:
    :class:`babylon.engine.dialectics.base.Dialectic`: Generic base class.
"""

from __future__ import annotations

from typing import Any

from babylon.engine.dialectics.base import Dialectic, TickInputs, WorldView
from babylon.formulas.consciousness_routing import normalize_to_simplex, route_agitation_to_ternary
from babylon.models.components.material_conditions import MaterialConditionsBuffer
from babylon.models.entities.consciousness import TernaryConsciousness


class ClassConsciousnessDialectic(Dialectic[MaterialConditionsBuffer, TernaryConsciousness]):
    """The reified/spontaneous ↔ imputed/revolutionary contradiction.

    Weight reflects whether consciousness is dominated by immediate, reified
    material conditions (wage struggles, imperial bribery) (``weight < 0``, A dominant)
    or by imputed, revolutionary consciousness organized by a vanguard (``weight > 0``, B dominant).

    Motion law:
        - **Crises/Cracks in Hegemony**: Inputs from economic dialectics generate
          `agitation`, which acts to push consciousness out of equilibrium.
        - **Vanguard Intervention**: Education and solidarity route raw agitation
          into (Δr, Δl, Δf) TernaryConsciousness shifts.
        - Weight tracks the relative dominance of the ternary simplex over the base
          reification buffer.

    Invariants:
        - r + l + f ≈ 1.0 (simplex constraint)
    """

    type_tag: str = "ClassConsciousnessDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> ClassConsciousnessDialectic:
        """Motion law T for class consciousness.

        Calculates inputs from upstream economic crises, routes agitation
        into the ternary simplex, and evaluates the new weight of the dialectic.

        Args:
            inputs: Upstream outputs. Looks for own id's entry with
                    ``added_agitation``, ``solidarity``, ``education_pressure``.
            world: Read-only world context.

        Returns:
            New ClassConsciousnessDialectic with updated weight, poles, and tick.
        """
        old_mc = self.pole_a
        old_tc = self.pole_b

        added_agitation = 0.0
        solidarity = 0.0
        edu_pressure = 0.0

        own_input = inputs.upstream.get(self.id)
        if own_input is not None:
            added_agitation = float(own_input.get("added_agitation", 0.0))
            solidarity = float(own_input.get("solidarity", 0.0))
            edu_pressure = float(own_input.get("education_pressure", 0.0))

        new_agitation = old_mc.agitation + added_agitation

        delta_r, delta_l, delta_f = route_agitation_to_ternary(
            agitation=new_agitation,
            solidarity_factor=solidarity,
            education_pressure=edu_pressure,
        )

        new_r, new_l, new_f = normalize_to_simplex(
            old_tc.r + delta_r,
            old_tc.l + delta_l,
            old_tc.f + delta_f,
        )

        # Simple hardcoded consumption rate for now
        consumption_rate = 0.1
        remaining_agitation = max(0.0, new_agitation * (1.0 - consumption_rate))

        new_mc = old_mc.model_copy(update={"agitation": remaining_agitation})

        new_tc = TernaryConsciousness(
            r=new_r,
            l=new_l,
            f=new_f,
        )

        # Active consciousness vs reification
        active_consciousness = new_r + new_f
        weight_shift = (active_consciousness * 0.5) - (new_mc.reification_buffer * 0.5)
        new_weight = max(-1.0, min(1.0, self.weight + weight_shift))

        return self.model_copy(
            update={
                "pole_a": new_mc,
                "pole_b": new_tc,
                "weight": new_weight,
                "tick_updated": world.tick,
            }
        )

    def observe(self) -> dict[str, Any]:
        """Project class consciousness state for frontend rendering.

        Returns:
            Observation dict with consciousness metrics.
        """
        obs = super().observe()
        obs.update(
            {
                "agitation": self.pole_a.agitation,
                "reification_buffer": self.pole_a.reification_buffer,
                "r": float(self.pole_b.r),
                "l": float(self.pole_b.l),
                "f": float(self.pole_b.f),
            }
        )
        return obs

    def invariants(self) -> list[str]:
        """Consciousness-specific invariants.

        Checks:
            - r + l + f ≈ 1.0

        Returns:
            List of violation descriptions.
        """
        violations = super().invariants()
        total = float(self.pole_b.r) + float(self.pole_b.l) + float(self.pole_b.f)
        if abs(total - 1.0) > 1e-4:
            violations.append(
                f"ClassConsciousnessDialectic {self.id}: simplex sum is not 1.0 (sum={total})"
            )
        return violations
