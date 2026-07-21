"""Frozen view-models — the shapes a client hydrates from a projection.

Where :mod:`babylon.projection.registry` describes the *views* a client may
read, this module describes the *records* it gets back. The keystone is
:class:`CountyView`, the county dossier assembled from several declared
sources (value aggregate, per-county Φ, survival calculus, consciousness
simplex, legitimacy). Unlike a single SQL-view row model, a ``CountyView``
composes fields drawn from multiple subsystems, so every field a fog or veil
gate can withhold — and every field a given run may simply not attribute — is
``Optional`` with **honest ``None`` semantics**: ``None`` means *absent*, never
a silently-defaulted zero (the ``from_graph`` fallback trap the constitution's
Loud Failure clause, III.11, exists to forbid).

Records are validated through :class:`~pydantic.TypeAdapter` helpers rather
than direct construction so a client can hydrate an untyped dict — recorded
fixture, JSON payload, or view row — in one call. :data:`ProjectionRecord` is a
discriminated union keyed on the ``kind`` literal; it grows by one member per
Program 24 P2 Lane P work order with no change to the hydrate helpers — it now
also holds :class:`KeyFigureView` (WO-21).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from babylon.models.types import (
    Currency,
    Ideology,
    Probability,
    SignedLaborHours,
)

#: Tolerance for the simplex/share sum invariants — matches the engine-side
#: ``ClassDistribution`` and ternary-consciousness tolerance so a record that
#: round-trips a live value is never rejected for float drift.
_SUM_TOLERANCE: float = 1e-3


class ClassComposition(BaseModel):
    """The five-class population shares of a county, summing to one.

    Mirrors the engine's ``ClassDistribution`` (five shares over the MLM-TW
    class schema). Shares are populations *normalized* to fractions, not head
    counts; use :attr:`CountyView.population` for the absolute count.

    :param bourgeoisie: Share owning capital and buying labor-power.
    :param petit_bourgeoisie: Share of small proprietors and self-employed.
    :param labor_aristocracy: Share of super-waged core labor (the Φ recipients
        of the Fundamental Theorem).
    :param proletariat: Share selling labor-power at or below value.
    :param lumpenproletariat: Share outside stable wage relations.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    bourgeoisie: Probability
    petit_bourgeoisie: Probability
    labor_aristocracy: Probability
    proletariat: Probability
    lumpenproletariat: Probability

    @model_validator(mode="after")
    def _validate_sum(self) -> ClassComposition:
        """Require the five shares to sum to one within :data:`_SUM_TOLERANCE`.

        :raises ValueError: if the shares do not sum to one — a malformed
            composition is a bug, not a silently-normalized input.
        :returns: The validated model (unchanged).
        """
        total = (
            self.bourgeoisie
            + self.petit_bourgeoisie
            + self.labor_aristocracy
            + self.proletariat
            + self.lumpenproletariat
        )
        if abs(total - 1.0) > _SUM_TOLERANCE:
            msg = f"class shares must sum to 1.0 (got {total:.6f})"
            raise ValueError(msg)
        return self


class ConsciousnessSimplex(BaseModel):
    """The ternary revolutionary/liberal/fascist consciousness of a county.

    The live, per-county consciousness signal is the ``(r, l, f)`` ternary
    simplex written to ``dynamic_consciousness_state`` (``ideology_r/l/f``),
    aggregated pop-weighted across a county's classes. This is deliberately
    *not* the scalar ``SocialClass.class_consciousness``, which is an
    owner-gated always-default engine field and must not be projected as
    meaningful.

    :param revolutionary: Share of consciousness oriented to rupture (the
        ``r`` pole).
    :param liberal: Share oriented to reform within the existing order (the
        ``l`` pole).
    :param fascist: Share oriented to reactionary consolidation (the ``f``
        pole).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    revolutionary: Probability
    liberal: Probability
    fascist: Probability

    @model_validator(mode="after")
    def _validate_sum(self) -> ConsciousnessSimplex:
        """Require the three poles to sum to one within :data:`_SUM_TOLERANCE`.

        :raises ValueError: if the poles do not sum to one.
        :returns: The validated model (unchanged).
        """
        total = self.revolutionary + self.liberal + self.fascist
        if abs(total - 1.0) > _SUM_TOLERANCE:
            msg = f"consciousness poles must sum to 1.0 (got {total:.6f})"
            raise ValueError(msg)
        return self


class CountyView(BaseModel):
    """A county dossier — the projected read-model for one county.

    Every field beyond identity and provenance is ``Optional`` because a
    county's value is either withheld by a fog/veil gate or simply not
    attributed in a given run; in both cases the honest projection is ``None``,
    never a defaulted zero. A missing key in the source dict hydrates to
    ``None`` for the same reason.

    Extra keys are rejected (``extra="forbid"``): a payload carrying a field
    this model does not declare is a shape mismatch to surface loudly, not to
    swallow.

    :param kind: The discriminator literal ``"county"`` tagging this record in
        :data:`ProjectionRecord`.
    :param county_fips: The five-digit county FIPS code — the county's identity
        (``Territory.county_fips``); county is not a graph node type.
    :param verified_tick: The committed tick this dossier was projected from
        (``tick_commit``), the staleness anchor for any materialization.
    :param population: Absolute county population, or ``None`` if unattributed.
    :param class_composition: The five-class shares, or ``None`` if absent.
    :param median_wage: County median hourly wage (money-form), or ``None``.
    :param imperial_rent_phi: Per-county imperial rent Φ in labor-hours, signed
        (positive = rent recipient, negative = periphery donor); a value-axis
        quantity a veil gate withholds below tier 1, hydrating to ``None``.
    :param consciousness: The ``(r, l, f)`` consciousness simplex, or ``None``.
    :param legitimacy: The territory legitimation index in ``[0, 1]``, or
        ``None`` if unattributed.
    :param p_acquiescence: Pop-weighted P(S|A), survival-through-acquiescence,
        or ``None``.
    :param p_revolution: Pop-weighted P(S|R), survival-through-revolution, or
        ``None``.
    :param bifurcation_score: The county bifurcation axis in ``[-1, +1]``
        (revolutionary at ``-1``, fascist at ``+1``), or ``None``.
    :param sovereign_id: The id of the sovereign claiming this county via a
        CLAIMS edge, or ``None`` when unclaimed (no CLAIMS edge projected).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["county"] = "county"
    county_fips: str = Field(pattern=r"^\d{5}$")
    verified_tick: int = Field(ge=0)

    population: int | None = Field(default=None, ge=0)
    class_composition: ClassComposition | None = None
    median_wage: Currency | None = None
    imperial_rent_phi: SignedLaborHours | None = None
    consciousness: ConsciousnessSimplex | None = None
    legitimacy: Probability | None = None
    p_acquiescence: Probability | None = None
    p_revolution: Probability | None = None
    bifurcation_score: Ideology | None = None
    sovereign_id: str | None = None


class KeyFigureView(BaseModel):
    """A key-figure dossier — the permanent honest-absence page (ADR084, WO-21).

    Unlike :class:`CountyView`, where individual fields go absent per-run
    while the *kind* itself is real, this kind has **no live producer at
    all**: the backing ``KeyFigure`` model and ``WorldState.key_figures``
    were formally retired under Constitution III.10
    (``ai/decisions/ADR084_retire_dead_models.yaml``, 2026-07-18) as a dead
    speculative construct — no scenario, seed, OODA system, or bridge in
    this engine version ever populated either one.
    ``models.enums.topology.NodeType.KEY_FIGURE`` was reclassified by the
    same ADR from production-stamped to "declared but not
    production-stamped" and dropped from the vocabulary sentinel's
    ``MODEL_FIELDS_BY_NODE_TYPE``: it now exists purely to type
    ``classify_topology()``'s COMMAND-edge test fixtures
    (``tests/unit/.../test_topology_classifier.py``). There is therefore no
    field beyond identity/provenance this model could honestly declare — a
    ``name``, ``organization_id``, or similar attribute would have no
    producer to cite in a field-producer table and would be exactly the
    fabricated-plausible-default Constitution III.11 forbids. See
    :func:`babylon.projection.key_figure.project_key_figure` for the
    projector and :data:`babylon.projection.key_figure.DEAD_PRODUCER_REMEDY`
    for the dossier's sole absence remedy text.

    Extra keys are rejected (``extra="forbid"``).

    :param kind: The discriminator literal ``"key_figure"`` tagging this
        record in :data:`ProjectionRecord`.
    :param key_figure_id: The graph node id naming the key figure. Always
        caller-supplied, never resolved from a real graph node — production
        never stamps one.
    :param verified_tick: The committed tick this dossier was projected
        from — kept for shape parity with every other Lane P view, even
        though this kind's (absent) data never changes across ticks.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["key_figure"] = "key_figure"
    key_figure_id: str = Field(min_length=1)
    verified_tick: int = Field(ge=0)


#: A projected record of any scale, keyed on ``kind``. Grows by one union
#: member per Program 24 P2 Lane P work order (WO-21 added
#: :class:`KeyFigureView`) — the hydrate helpers below need no change.
ProjectionRecord = Annotated[
    CountyView | KeyFigureView,
    Field(discriminator="kind"),
]

_COUNTY_ADAPTER: TypeAdapter[CountyView] = TypeAdapter(CountyView)
_KEY_FIGURE_ADAPTER: TypeAdapter[KeyFigureView] = TypeAdapter(KeyFigureView)
_RECORD_ADAPTER: TypeAdapter[CountyView | KeyFigureView] = TypeAdapter(ProjectionRecord)


def hydrate_county(data: Mapping[str, Any]) -> CountyView:
    """Validate an untyped mapping into a :class:`CountyView`.

    :param data: A mapping shaped like a ``CountyView`` — a recorded fixture,
        a JSON payload, or an assembled row dict. Missing optional keys become
        ``None``; unknown keys are rejected.
    :returns: The validated, frozen :class:`CountyView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _COUNTY_ADAPTER.validate_python(data)


def hydrate_key_figure(data: Mapping[str, Any]) -> KeyFigureView:
    """Validate an untyped mapping into a :class:`KeyFigureView`.

    :param data: A mapping shaped like a ``KeyFigureView`` — a recorded
        fixture, a JSON payload, or an assembled row dict. Unknown keys are
        rejected.
    :returns: The validated, frozen :class:`KeyFigureView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _KEY_FIGURE_ADAPTER.validate_python(data)


def hydrate_record(data: Mapping[str, Any]) -> CountyView | KeyFigureView:
    """Validate an untyped mapping into the correct :data:`ProjectionRecord`.

    Dispatch is by the ``kind`` discriminator, so this helper stays correct as
    new record types join the union.

    :param data: A mapping carrying a ``kind`` discriminator and the fields of
        the matching record type.
    :returns: The validated record (a :class:`CountyView` today).
    :raises pydantic.ValidationError: if ``kind`` is missing/unknown or the
        payload violates the matched record's shape.
    """
    return _RECORD_ADAPTER.validate_python(data)


__all__ = [
    "ClassComposition",
    "ConsciousnessSimplex",
    "CountyView",
    "KeyFigureView",
    "ProjectionRecord",
    "hydrate_county",
    "hydrate_key_figure",
    "hydrate_record",
]
