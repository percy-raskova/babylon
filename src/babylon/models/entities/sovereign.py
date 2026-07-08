"""Spec-070 Sovereign entity (FR-001 -- FR-004 + FR-040 / FR-040b).

A Sovereign is an institution-side authority that CLAIMS Territories
and applies a per-tick ``metabolic_impact`` along its CLAIMS edges.
Crystallizes the ruling-Faction's :class:`ColonialStance` into an
:class:`ExtractionPolicy` which drives the Territory habitability
trajectory.

Cross-references:

- I.16 Organization vs Institution: Sovereign is institution-side
  (crystallized authority that survives ruling-faction change).
- I.20 Political Claims as Overlay: CLAIMS edges are overlays on the
  immutable spatial substrate.
- II.9 Morphism Dyadic: CLAIMS / ADMINISTERS edges are dyadic.

FR-040b special case: ``SOV_EXTERIOR_NULL`` is a PROVISIONAL exterior
fallback Sovereign with ``ruling_faction_id=None`` and
``extraction_policy=CONTINUE``. The Pydantic validator must permit
this exact combination while rejecting any other ``None``-ruling /
non-CONTINUE pairing.
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from babylon.models.enums import ExtractionPolicy, SovereigntyType
from babylon.models.types import Probability


class Sovereign(BaseModel):
    """Authority that claims Territory (spec-070).

    Attributes:
        id: Stable ID matching ``^SOV_[A-Z][A-Z0-9_]*$``.
        name: Display name.
        sovereignty_type: Classification (recognized_state, provisional,
            insurgent, occupation, secessionist, emergency).
        legitimacy: Current legitimacy ∈ ``[0, 1]``. ``<= 0.0`` triggers
            ``SOVEREIGN_COLLAPSE`` per FR-023.
        color_hex: UI color in ``#RRGGBB`` form.
        capital_territory_id: Optional capital territory ID.
        ruling_faction_id: ID of the
            :class:`~babylon.models.entities.balkanization_faction.BalkanizationFaction`
            currently in power. ``None`` only for SOV_EXTERIOR_NULL
            per FR-040b.
        extraction_policy: Derived deterministically from the ruling
            faction's ``colonial_stance``. Must be ``CONTINUE`` when
            ``ruling_faction_id`` is ``None``.
        founded_tick: Tick the Sovereign was instantiated.
        dissolved_tick: Optional dissolution tick.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^SOV_[A-Z][A-Z0-9_]*$")
    name: str = Field(min_length=1, max_length=128)
    sovereignty_type: SovereigntyType

    legitimacy: Probability = Field(default=1.0)
    color_hex: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    capital_territory_id: str | None = None

    ruling_faction_id: str | None = Field(
        default=None,
        pattern=r"^FAC_[A-Z][A-Z0-9_]*$",
    )
    extraction_policy: ExtractionPolicy

    founded_tick: int = Field(ge=0)
    dissolved_tick: int | None = Field(default=None, ge=0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def metabolic_impact(self) -> float:
        """Per-tick habitability change applied along outgoing CLAIMS
        edges (FR-004).

        Uses :class:`BalkanizationDefines` canonical defaults; override
        path is to construct a custom Sovereign + custom defines in
        higher-level code, not via this property.
        """
        # Runtime-local import: models MUST NOT import formulas at module
        # level — formulas.balkanization imports babylon.models.enums back,
        # so a module-level import here deadlocks any process whose first
        # babylon import is formulas.balkanization (doctest, tooling).
        from babylon.formulas.balkanization import calculate_metabolic_impact

        return calculate_metabolic_impact(self.extraction_policy)

    @model_validator(mode="after")
    def _validate_null_ruling_only_with_continue(self) -> Self:
        """FR-040b: ``ruling_faction_id=None`` is permitted only when
        ``extraction_policy=CONTINUE`` (the SOV_EXTERIOR_NULL fallback).
        """

        if (
            self.ruling_faction_id is None
            and self.extraction_policy is not ExtractionPolicy.CONTINUE
        ):
            raise ValueError(
                "Sovereign with NULL ruling_faction_id must have "
                "extraction_policy=CONTINUE (FR-040b SOV_EXTERIOR_NULL "
                f"convention); got {self.extraction_policy!r}"
            )
        return self

    @model_validator(mode="after")
    def _validate_dissolution_after_founding(self) -> Self:
        if self.dissolved_tick is not None and self.dissolved_tick < self.founded_tick:
            raise ValueError(
                f"dissolved_tick ({self.dissolved_tick}) must be ≥ "
                f"founded_tick ({self.founded_tick})"
            )
        return self
