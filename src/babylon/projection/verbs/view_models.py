"""Frozen view-models for the verb read-side (WO-38).

Live-query surfaces (contrast the vault's baked ``ProjectionRecord`` kinds):
the plate and previews are recomputed per render from the current graph, so
these models live here rather than widening the vault union in
:mod:`babylon.projection.view_models`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class VerbPreview(BaseModel):
    """Estimated, read-only consequences of one proposed verb.

    Mirrors the legacy bridge's ``preview_action`` payload field-for-field;
    the consciousness estimate is resolver-parity (preview == resolution)
    for the consciousness verbs and a documented heuristic for the rest.

    :ivar estimated_consciousness_delta: Collective-identity delta estimate,
        rounded to 4 places; ``0.0`` when the verb has no consciousness
        effect on the resolved target.
    :ivar estimated_heat_delta: Heat estimate, rounded to 4 places.
    :ivar action_point_cost: AP cost of the verb.
    :ivar success_probability: Rounded success estimate; ``0.0`` for a dead
        preview (acting org absent from the graph).
    :ivar affected_territory_ids: The acting org's territories plus the
        explicit target, in that order.
    :ivar warnings: Player-facing caveats (budget, heat, eviction, missing
        nodes) — honest, never suppressed.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    estimated_consciousness_delta: float
    estimated_heat_delta: float
    action_point_cost: float
    success_probability: float
    affected_territory_ids: tuple[str, ...]
    warnings: tuple[str, ...]


class VerbRow(BaseModel):
    """One verb's row on the plate.

    :ivar verb: Canonical verb name.
    :ivar eligible: Target-existence predicate result — the UI disables on
        this alone, never on affordability.
    :ivar reason: Player-facing reason when ineligible, else ``None``.
    :ivar remedy: Player-facing remedy when ineligible, else ``None``.
    :ivar can_afford: Affordability via the same check that gates
        submission, so the plate can never disagree with a rejection.
    :ivar afford_note: The affordability failure note, else ``None``.
    :ivar preview: Target-less preview (the acting org as resolved target);
        target-specific estimates land once a target is chosen.
    :ivar candidate_target_ids: The verb's own honest candidate target ids —
        the SAME entity domain :attr:`eligible`'s predicate tests, computed
        from :func:`~babylon.projection.verbs.plate.build_verb_plate`'s one
        bounded pass over the graph (never a fabricated id beyond what that
        pass actually found). Empty for a self-targeting verb (``reproduce``
        always targets the acting org itself, never an explicit id — see
        that verb's own eligibility-row comment in ``plate.py``). A picker
        widget reads this to enumerate real targets without touching the
        graph itself (unit "verb-targeting", shell-interconnect).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    verb: str
    eligible: bool
    reason: str | None
    remedy: str | None
    can_afford: bool
    afford_note: str | None
    preview: VerbPreview | None
    candidate_target_ids: tuple[str, ...]


class VerbPlateView(BaseModel):
    """The full nine-verb plate for one acting org at one tick.

    :ivar kind: Discriminator literal.
    :ivar org_id: The acting organization.
    :ivar tick: The tick the plate was computed against.
    :ivar verbs: One row per canonical verb, in canonical order.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str = "verb_plate"
    org_id: str
    tick: int
    verbs: tuple[VerbRow, ...]
