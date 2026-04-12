"""PartyDialectic — Vanguard ↔ Mass Line (MLM theory).

The party is the organizational form produced by sublation of the
ClassDialectic. It holds the class that generated it (via parent_id)
and governs that class's subsequent motion through directives.

The Vanguard pole represents organizational discipline, cadre quality,
and theoretical clarity. The Mass Line pole represents the party's
connection to and support from the masses.

When the vanguard loses contact with the masses (weight → -1),
the party degenerates into bureaucracy. When the mass line dominates
(weight → +1), the party dissolves into spontaneism.

See Also:
    :class:`babylon.engine.dialectics.class_struggle.ClassDialectic`
    :class:`babylon.engine.dialectics.base.Dialectic`: Generic base class.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from babylon.engine.dialectics.base import Dialectic, TickInputs, WorldView


class Vanguard(BaseModel):
    """Vanguard pole: organizational discipline and theoretical clarity.

    Attributes:
        discipline: Party discipline level ∈ [0, 1].
    """

    model_config = ConfigDict(frozen=True)

    discipline: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Party discipline level.",
    )


class MassLine(BaseModel):
    """Mass Line pole: connection to and support from the masses.

    Attributes:
        support: Popular support level ∈ [0, 1].
    """

    model_config = ConfigDict(frozen=True)

    support: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Popular support level.",
    )


class PartyDialectic(Dialectic[Vanguard, MassLine]):
    """Vanguard ↔ Mass Line party contradiction.

    Weight semantics:
        weight < 0 → vanguard dominant (risk of bureaucratic degeneration).
        weight > 0 → mass line dominant (risk of spontaneism).
        weight ≈ 0 → healthy dialectical balance.

    Motion law:
        Reads the sublated class's state to calibrate the directive.
        Discipline decays without class struggle input; mass support
        grows with material grievance.

    observe() emits:
        - ``current_directive``: float ∈ [-1, 1], a governance signal
          that the sublated ClassDialectic reads via find_successor().
        - ``discipline``: vanguard discipline level.
        - ``mass_support``: mass line support level.
    """

    type_tag: str = "PartyDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> PartyDialectic:
        """Motion law T for the party dialectic.

        Args:
            inputs: Upstream outputs.
            world: Read-only world context.

        Returns:
            New PartyDialectic with updated weight and tick.
        """
        # Party's weight drifts based on discipline vs mass support
        _ = inputs  # Upstream inputs not yet consumed; reserved for future use
        delta = (self.pole_b.support - self.pole_a.discipline) * 0.05
        new_weight = max(-1.0, min(1.0, self.weight + delta))

        return self.model_copy(
            update={
                "weight": new_weight,
                "tick_updated": world.tick,
            }
        )

    def observe(self) -> dict[str, Any]:
        """Project party state for downstream governance.

        Emits ``current_directive`` — the governance signal that the
        sublated ClassDialectic reads in its step().

        Returns:
            Base observation extended with party-specific metrics.
        """
        obs = super().observe()

        # The directive is a function of the party's internal balance.
        # Positive discipline → positive directive (organize, centralize).
        # Positive mass support → moderating directive (mass line corrections).
        directive = self.pole_a.discipline - self.pole_b.support

        obs.update(
            {
                "current_directive": directive,
                "discipline": self.pole_a.discipline,
                "mass_support": self.pole_b.support,
            }
        )
        return obs


__all__ = [
    "MassLine",
    "PartyDialectic",
    "Vanguard",
]
