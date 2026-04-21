"""ClassDialectic — In-Itself ↔ For-Itself (Lukacs, Marx).

A class exists in-itself as an objective economic position (material
grievance, exploitation, immiseration). It becomes for-itself when
it achieves collective self-consciousness and organization sufficient
to act as a historical agent.

When the for-itself weight crosses the sublation threshold AND
organization is sufficiently high, the class sublates into a
PartyDialectic — the vanguard organizational form that governs
the class's subsequent motion.

After sublation, the class continues to evolve (Aufhebung: preserved
+ negated + raised). But its step() now reads the party's observe()
output via ``world.find_successor()``, meaning the party governs the
class's motion — not raw material conditions.

See Also:
    :class:`babylon.engine.dialectics.party.PartyDialectic`
    :class:`babylon.engine.dialectics.sublation.SublationRule`
    :class:`babylon.engine.dialectics.base.Dialectic`: Generic base class.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from babylon.engine.dialectics.base import Dialectic, TickInputs, WorldView
from babylon.engine.dialectics.sublation import SublationRule


class InItself(BaseModel):
    """Class-in-itself: objective material position.

    Attributes:
        material_grievance: Intensity of material deprivation ∈ [0, 1].
    """

    model_config = ConfigDict(frozen=True)

    material_grievance: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Intensity of material deprivation.",
    )


class ForItself(BaseModel):
    """Class-for-itself: collective self-consciousness and organization.

    Attributes:
        organization_level: Degree of class organization ∈ [0, 1].
    """

    model_config = ConfigDict(frozen=True)

    organization_level: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Degree of class organization.",
    )


# Sublation threshold: weight must be >= this for sublation to occur
_SUBLATION_WEIGHT_THRESHOLD = 0.7


def _make_party_sublation_rule() -> SublationRule:
    """Construct the class→party sublation rule.

    Deferred to a function to avoid circular imports (party.py
    imports are only needed when the factory fires).
    """
    return SublationRule(
        name="class_to_party",
        threshold=lambda d: d.weight >= _SUBLATION_WEIGHT_THRESHOLD,
        successor_type="PartyDialectic",
        successor_factory=_create_party,
    )


def _create_party(d: Dialectic[Any, Any]) -> Dialectic[Any, Any]:
    """Factory: create a PartyDialectic from a sublating ClassDialectic."""
    from babylon.engine.dialectics.party import MassLine, PartyDialectic, Vanguard

    return PartyDialectic(
        pole_a=Vanguard(discipline=d.pole_b.organization_level),
        pole_b=MassLine(support=d.pole_a.material_grievance),
        weight=0.5,
        parent_id=d.id,
        tick_created=d.tick_updated,
        tick_updated=d.tick_updated,
    )


class ClassDialectic(Dialectic[InItself, ForItself]):
    """In-Itself ↔ For-Itself class consciousness contradiction.

    Weight semantics:
        weight < 0 → in-itself dominant (fragmented, passive).
        weight > 0 → for-itself dominant (organized, active).

    Motion law:
        Material grievances push weight positive. Organization
        level amplifies the shift. When a successor (PartyDialectic)
        exists, motion is governed by the party's directive.

    Sublation:
        Uses ``SublationRule`` — when weight >= 0.7, sublates to
        PartyDialectic.
    """

    type_tag: str = "ClassDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> ClassDialectic:
        """Motion law T for class dialectic.

        If a successor (PartyDialectic) exists in the world view,
        the class's evolution is governed by the party's directive.
        Otherwise, evolution follows raw material conditions.

        Args:
            inputs: Upstream outputs.
            world: Read-only world context.

        Returns:
            New ClassDialectic with updated weight and tick.
        """
        # Check if a successor (PartyDialectic) exists and governs us
        successor = world.find_successor(self.id)
        _ = inputs  # Upstream inputs not yet consumed; reserved for future use

        if successor is not None:
            # Governed by the party: party directive shapes class weight
            directive = successor.observe().get("current_directive", 0.0)
            # Party discipline moderates class spontaneity
            delta = float(directive) * 0.1
        else:
            # Governed by material conditions
            delta = self.pole_a.material_grievance * 0.05

        new_weight = max(-1.0, min(1.0, self.weight + delta))

        return self.model_copy(
            update={
                "weight": new_weight,
                "tick_updated": world.tick,
            }
        )

    def sublate(self) -> Dialectic[Any, Any] | None:
        """Sublate to PartyDialectic when weight >= threshold.

        Delegates to the ``SublationRule`` abstraction. The class
        produces the party. From that point on, the party governs
        the class.

        Returns:
            PartyDialectic if threshold crossed, else None.
        """
        rule = _make_party_sublation_rule()
        if rule.threshold_met(self):
            return rule.create_successor(self)
        return None

    def observe(self) -> dict[str, Any]:
        """Project class state for downstream consumption.

        Returns:
            Base observation extended with class-specific metrics.
        """
        obs = super().observe()
        obs.update(
            {
                "material_grievance": self.pole_a.material_grievance,
                "organization_level": self.pole_b.organization_level,
            }
        )
        return obs


__all__ = [
    "ClassDialectic",
    "ForItself",
    "InItself",
]
