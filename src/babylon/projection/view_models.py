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
discriminated union keyed on the ``kind`` literal; it currently holds only
:class:`CountyView` and is written to grow (state and national dossiers join in
Program 24 P2) with no change to the hydrate helpers.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from babylon.models.enums import SocialRole
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


class SocialClassView(BaseModel):
    """A social-class dossier — the projected read-model for one class node.

    Every field beyond identity and provenance is ``Optional``: a
    ``class_id`` absent from the committed ``WorldState`` (see
    :func:`~babylon.projection.social_class.project_social_class`) projects
    as an all-``None`` dossier (honest absence, Constitution III.11), and
    ``county_class_composition`` is ``None`` whenever the class carries no
    county attribution or its county has no territory-level composition
    data yet.

    Extra keys are rejected (``extra="forbid"``): a payload carrying a field
    this model does not declare is a shape mismatch to surface loudly, not
    to swallow.

    :param kind: The discriminator literal ``"social_class"`` tagging this
        record in :data:`ProjectionRecord`.
    :param class_id: The graph node id — the class's identity (pattern
        ``^C[0-9]{3,}$``, matching ``SocialClass.id``).
    :param verified_tick: The committed tick this dossier was projected
        from, the staleness anchor for any materialization.
    :param role: This class's position in the world system (``SocialRole``),
        or ``None`` if the node does not exist.
    :param county_fips: The county this class is attributed to (spec-065
        ``SocialClass.county_fips``), or ``None`` if unattributed or the
        node does not exist; ``""`` is the source's own "explicitly
        unattributed" sentinel and hydrates through unchanged.
    :param population: This class's own block size (NOT a county-wide
        aggregate — contrast :attr:`CountyView.population`), or ``None``.
    :param wealth: This class's own wealth (money-form), or ``None``.
    :param organization: This class's collective cohesion in ``[0, 1]``, or
        ``None``.
    :param repression_faced: State violence directed at this class in
        ``[0, 1]``, or ``None``.
    :param p_acquiescence: This class's own P(S|A), or ``None`` — NOT the
        county's pop-weighted mean (contrast
        :attr:`CountyView.p_acquiescence`).
    :param p_revolution: This class's own P(S|R), or ``None``.
    :param consciousness: This class's own ``(r, l, f)`` consciousness
        simplex, mapped from its ``IdeologicalProfile`` via the spec-065
        bridge, or ``None``.
    :param county_class_composition: The containing county's five-class
        share breakdown (nesting context — the same producer
        :attr:`CountyView.class_composition` uses), resolved via this
        class's own ``county_fips``; ``None`` if unattributed or the county
        has no composition data yet.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["social_class"] = "social_class"
    class_id: str = Field(pattern=r"^C[0-9]{3,}$")
    verified_tick: int = Field(ge=0)

    role: SocialRole | None = None
    county_fips: str | None = Field(default=None, pattern=r"^\d{5}$|^$")
    population: int | None = Field(default=None, ge=0)
    wealth: Currency | None = None
    organization: Probability | None = None
    repression_faced: Probability | None = None
    p_acquiescence: Probability | None = None
    p_revolution: Probability | None = None
    consciousness: ConsciousnessSimplex | None = None
    county_class_composition: ClassComposition | None = None


#: A projected record of any scale, keyed on ``kind``. Program 24 P2 widens
#: it to a discriminated union (``CountyView | SocialClassView | ...``) as
#: state, national, and other-kind dossiers land — the hydrate helpers below
#: need no change beyond their own kind-specific adapter.
ProjectionRecord = Annotated[
    CountyView | SocialClassView,
    Field(discriminator="kind"),
]

_COUNTY_ADAPTER: TypeAdapter[CountyView] = TypeAdapter(CountyView)
_SOCIAL_CLASS_ADAPTER: TypeAdapter[SocialClassView] = TypeAdapter(SocialClassView)
_RECORD_ADAPTER: TypeAdapter[CountyView | SocialClassView] = TypeAdapter(ProjectionRecord)


def hydrate_county(data: Mapping[str, Any]) -> CountyView:
    """Validate an untyped mapping into a :class:`CountyView`.

    :param data: A mapping shaped like a ``CountyView`` — a recorded fixture,
        a JSON payload, or an assembled row dict. Missing optional keys become
        ``None``; unknown keys are rejected.
    :returns: The validated, frozen :class:`CountyView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _COUNTY_ADAPTER.validate_python(data)


def hydrate_social_class(data: Mapping[str, Any]) -> SocialClassView:
    """Validate an untyped mapping into a :class:`SocialClassView`.

    :param data: A mapping shaped like a ``SocialClassView`` — a recorded
        fixture, a JSON payload, or an assembled row dict. Missing optional
        keys become ``None``; unknown keys are rejected.
    :returns: The validated, frozen :class:`SocialClassView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _SOCIAL_CLASS_ADAPTER.validate_python(data)


def hydrate_record(data: Mapping[str, Any]) -> CountyView | SocialClassView:
    """Validate an untyped mapping into the correct :data:`ProjectionRecord`.

    Dispatch is by the ``kind`` discriminator, so this helper stays correct as
    new record types join the union.

    :param data: A mapping carrying a ``kind`` discriminator and the fields of
        the matching record type.
    :returns: The validated record (a :class:`CountyView` or
        :class:`SocialClassView` today).
    :raises pydantic.ValidationError: if ``kind`` is missing/unknown or the
        payload violates the matched record's shape.
    """
    return _RECORD_ADAPTER.validate_python(data)


__all__ = [
    "ClassComposition",
    "ConsciousnessSimplex",
    "CountyView",
    "ProjectionRecord",
    "SocialClassView",
    "hydrate_county",
    "hydrate_record",
    "hydrate_social_class",
]
