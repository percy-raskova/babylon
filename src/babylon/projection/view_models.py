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
discriminated union keyed on the ``kind`` literal; it holds :class:`CountyView`
and :class:`InstitutionView` (Program 24 P2 WO-19) today and is written to grow
further as more Lane P kinds join, with no change to the hydrate helpers.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from babylon.models.enums import (
    ApparatusType,
    ClassInscription,
    SocialFunction,
)
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


class FactionalComposition(BaseModel):
    """The three ruling-class-fraction weights within an institution.

    Mirrors the legacy ``InstitutionSerializer.factional_composition``
    contract (``web/game/serializers.py``) and the engine's
    ``InternalBalanceOfForces`` (``babylon.models.entities.institution``) —
    but projects only the three named fraction weights. ``internal_
    contestation`` and the computed ``hegemonic_fraction`` are deliberately
    NOT projected here: the former has no legacy-parity contract to mirror,
    and the latter is an enum member the plain-float weight contract below
    does not carry (matching ``_institution_factional_control`` in
    ``web/game/engine_bridge.py``, which extracts the same three keys for the
    same reason — a raw passthrough of ``internal_balance`` would also trip
    this model's own ``extra="forbid"``).

    :param liberal_technocratic: Weight of the consent-based-rule faction.
    :param revanchist_fascist: Weight of the naked-repression faction.
    :param institutionalist_bonapartist: Weight of the self-preservation
        faction.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    liberal_technocratic: Probability
    revanchist_fascist: Probability
    institutionalist_bonapartist: Probability

    @model_validator(mode="after")
    def _validate_sum(self) -> FactionalComposition:
        """Require the three weights to sum to one within the engine's own tolerance.

        Uses the wider ``[0.99, 1.01]`` band ``InternalBalanceOfForces``
        itself validates against — not the tighter :data:`_SUM_TOLERANCE`
        :class:`ClassComposition`/:class:`ConsciousnessSimplex` use — so a
        record round-tripping a live engine value is never rejected for float
        drift the engine's own validator already tolerates.

        :raises ValueError: if the three weights do not sum to one within
            tolerance — a malformed composition is a bug, not a silently
            re-normalized input.
        :returns: The validated model (unchanged).
        """
        total = (
            self.liberal_technocratic + self.revanchist_fascist + self.institutionalist_bonapartist
        )
        if not (0.99 <= total <= 1.01):
            msg = f"factional composition weights must sum to 1.0 (got {total:.6f})"
            raise ValueError(msg)
        return self


class InstitutionView(BaseModel):
    """An institution dossier — the projected read-model for one institution.

    Unlike :class:`CountyView` (assembled from several declared sources),
    every field here has exactly one producer: the institution's own graph
    node, stamped whole-cloth by ``WorldState.to_graph()`` from the
    ``Institution`` Pydantic model (Feature 040) — no cross-entity
    aggregation is needed. The only absence case is therefore "no institution
    node carries this id" (every field ``None`` but identity/provenance);
    once a node exists, every field it declares is present, because
    ``Institution`` stamps them whole-cloth. A present-but-malformed node
    (e.g. an ``internal_balance`` dict missing a named weight) is a shape bug
    that fails loud via :class:`FactionalComposition`'s own validation, never
    a silently-substituted default.

    Extra keys are rejected (``extra="forbid"``): a payload carrying a field
    this model does not declare is a shape mismatch to surface loudly, not to
    swallow.

    :param kind: The discriminator literal ``"institution"`` tagging this
        record in :data:`ProjectionRecord`.
    :param institution_id: The institution's graph node id — its identity
        (mirrors the legacy ``InstitutionSerializer.id``).
    :param verified_tick: The committed tick this dossier was projected from,
        the staleness anchor for any materialization.
    :param name: Human-readable institution name, or ``None`` if no
        institution carries ``institution_id``.
    :param apparatus_type: The Althusserian apparatus classification, or
        ``None``.
    :param social_function: The population need this institution serves, or
        ``None``.
    :param class_inscription: Which class the institution serves, or
        ``None``.
    :param legitimacy: Public perceived legitimacy in ``[0, 1]``, or
        ``None``.
    :param budget: Available resources (money-form, non-negative), or
        ``None``.
    :param housed_org_ids: Organization ids housed within this institution —
        an empty tuple is a real "houses nothing" value, distinct from
        ``None`` (the institution itself is unattributed).
    :param territory_ids: Territories where this institution operates, same
        empty-vs-``None`` distinction as :attr:`housed_org_ids`.
    :param factional_composition: The three ruling-class-fraction weights, or
        ``None``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["institution"] = "institution"
    institution_id: str = Field(min_length=1)
    verified_tick: int = Field(ge=0)

    name: str | None = Field(default=None, min_length=1)
    apparatus_type: ApparatusType | None = None
    social_function: SocialFunction | None = None
    class_inscription: ClassInscription | None = None
    legitimacy: Probability | None = None
    budget: Currency | None = None
    housed_org_ids: tuple[str, ...] | None = None
    territory_ids: tuple[str, ...] | None = None
    factional_composition: FactionalComposition | None = None


#: A projected record of any scale, keyed on ``kind``. Holds
#: :class:`CountyView` and :class:`InstitutionView` (Program 24 P2 WO-19);
#: further Lane P kinds join the union the same way, with no change to the
#: hydrate helpers below.
ProjectionRecord = Annotated[
    CountyView | InstitutionView,
    Field(discriminator="kind"),
]

_COUNTY_ADAPTER: TypeAdapter[CountyView] = TypeAdapter(CountyView)
_INSTITUTION_ADAPTER: TypeAdapter[InstitutionView] = TypeAdapter(InstitutionView)
_RECORD_ADAPTER: TypeAdapter[CountyView | InstitutionView] = TypeAdapter(ProjectionRecord)


def hydrate_county(data: Mapping[str, Any]) -> CountyView:
    """Validate an untyped mapping into a :class:`CountyView`.

    :param data: A mapping shaped like a ``CountyView`` — a recorded fixture,
        a JSON payload, or an assembled row dict. Missing optional keys become
        ``None``; unknown keys are rejected.
    :returns: The validated, frozen :class:`CountyView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _COUNTY_ADAPTER.validate_python(data)


def hydrate_institution(data: Mapping[str, Any]) -> InstitutionView:
    """Validate an untyped mapping into an :class:`InstitutionView`.

    :param data: A mapping shaped like an ``InstitutionView`` — a recorded
        fixture, a JSON payload, or an assembled row dict. Missing optional
        keys become ``None``; unknown keys are rejected.
    :returns: The validated, frozen :class:`InstitutionView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _INSTITUTION_ADAPTER.validate_python(data)


def hydrate_record(data: Mapping[str, Any]) -> CountyView | InstitutionView:
    """Validate an untyped mapping into the correct :data:`ProjectionRecord`.

    Dispatch is by the ``kind`` discriminator, so this helper stays correct as
    new record types join the union.

    :param data: A mapping carrying a ``kind`` discriminator and the fields of
        the matching record type.
    :returns: The validated record (:class:`CountyView` or
        :class:`InstitutionView` today).
    :raises pydantic.ValidationError: if ``kind`` is missing/unknown or the
        payload violates the matched record's shape.
    """
    return _RECORD_ADAPTER.validate_python(data)


__all__ = [
    "ClassComposition",
    "ConsciousnessSimplex",
    "CountyView",
    "FactionalComposition",
    "InstitutionView",
    "ProjectionRecord",
    "hydrate_county",
    "hydrate_institution",
    "hydrate_record",
]
