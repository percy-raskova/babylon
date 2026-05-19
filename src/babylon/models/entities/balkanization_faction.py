"""Spec-070 BalkanizationFaction entity (FR-005 -- FR-008 + FR-045).

A political coalition that contests sovereignty over Territory through
INFLUENCES edges. Disambiguated from:

- :class:`babylon.models.entities.organization.PoliticalFaction`
  (spec-031, Organization-base subclass with OODA hooks).
- :class:`babylon.models.entities.state_apparatus_ai.FactionBalance`
  and :class:`babylon.models.enums.organizations.StateFaction`
  (spec-039, state-internal ruling-class factionalism).

This module is the *political-topology coalition* concept: a frozen
Pydantic record carrying a ``colonial_stance`` axis and a 4-tuple of
mechanical multipliers. It does not implement OODA loops or
organizational hierarchy — those concerns are deferred to spec-072.

Cross-references:

- I.1 Settler-Colonial Frame: ``colonial_stance`` is the principal axis.
- I.16 Organization vs Institution: Faction is organization-side
  (voluntary, dissolvable).
- I.20 Political Claims as Overlay: INFLUENCES edges are overlays on the
  immutable spatial substrate.
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.models.enums import ColonialStance
from babylon.models.types import Probability


class BalkanizationFaction(BaseModel):
    """Political coalition contesting sovereignty (spec-070).

    Attributes:
        id: Stable ID matching ``^FAC_[A-Z][A-Z0-9_]*$``.
        name: Display name.
        ideology: Free-text ideological label (e.g.,
            ``"settler-restorationism"``).
        colonial_stance: Principal political axis (UPHOLD / IGNORE / ABOLISH).
        is_settler_formation: Whether the faction is composed primarily
            of settler-formation classes.
        extraction_modifier: Mechanical multiplier on extraction
            (default by stance from
            :class:`~babylon.config.defines.balkanization.BalkanizationDefines`).
        violence_modifier: Mechanical multiplier on state violence.
        class_reduction: Faction's effect on class contradiction
            (``[0, 1]``).
        metabolic_reduction: Faction's effect on metabolic impact
            (``[-1, +1]``).
        color_hex: UI color in ``#RRGGBB`` form.
        founded_tick: Tick the faction was instantiated.
        dissolved_tick: Optional dissolution tick.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^FAC_[A-Z][A-Z0-9_]*$")
    name: str = Field(min_length=1, max_length=128)
    ideology: str = Field(min_length=1, max_length=64)

    colonial_stance: ColonialStance
    is_settler_formation: bool

    extraction_modifier: float = Field(ge=0.0)
    violence_modifier: float = Field(ge=0.0)
    class_reduction: Probability = Field(default=0.0)
    metabolic_reduction: float = Field(ge=-1.0, le=1.0)

    color_hex: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")

    founded_tick: int = Field(ge=0)
    dissolved_tick: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _validate_dissolution_after_founding(self) -> Self:
        if self.dissolved_tick is not None and self.dissolved_tick < self.founded_tick:
            raise ValueError(
                f"dissolved_tick ({self.dissolved_tick}) must be ≥ "
                f"founded_tick ({self.founded_tick})"
            )
        return self
