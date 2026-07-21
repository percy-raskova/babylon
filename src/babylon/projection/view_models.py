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

from babylon.models.types import (
    Coefficient,
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


class DepartmentComposition(BaseModel):
    """The Volume II department shares of an industry's output, summing to one.

    Mirrors ``babylon.domain.economics.department_mapper.DepartmentAllocation``
    (the Marx Vol II department schema, extended to four departments: means of
    production, necessary consumption, luxury consumption, social
    reproduction) — projected here, not imported, per the projection layer's
    no-engine-no-domain-import discipline (Constitution's layering; WO-22).

    :param dept_I: Share allocated to Department I (means of production).
    :param dept_IIa: Share allocated to Department IIa (necessary consumption).
    :param dept_IIb: Share allocated to Department IIb (luxury consumption).
    :param dept_III: Share allocated to Department III (social reproduction).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    dept_I: Coefficient
    dept_IIa: Coefficient
    dept_IIb: Coefficient
    dept_III: Coefficient

    @model_validator(mode="after")
    def _validate_sum(self) -> DepartmentComposition:
        """Require the four department shares to sum to one within tolerance.

        :raises ValueError: if the shares do not sum to one — a malformed
            allocation is a bug, not a silently-normalized input.
        :returns: The validated model (unchanged).
        """
        total = self.dept_I + self.dept_IIa + self.dept_IIb + self.dept_III
        if abs(total - 1.0) > _SUM_TOLERANCE:
            msg = f"department shares must sum to 1.0 (got {total:.6f})"
            raise ValueError(msg)
        return self


class IndustryView(BaseModel):
    """An industry dossier — the projected read-model for one NAICS-sector hyperedge.

    Unlike :class:`CountyView`, which composes several independent
    subsystem-sourced quantities, an industry has exactly one producer for
    every field: the ``INDUSTRY``-typed graph node itself
    (``babylon.models.entities.industry.IndustryHyperedge``, hydrated by
    ``babylon.engine.hydration.reference.hydrate_industry_hyperedges`` from
    the reference QCEW/BEA tables and stamped onto the graph by
    ``WorldState.to_graph()``). So presence/absence is a single binary gate —
    a graph carrying no node for ``industry_id`` projects every non-identity
    field as ``None``, never a defaulted zero (Constitution III.11).

    .. list-table:: Field-producer rulings
       :header-rows: 1

       * - Field
         - Producer
       * - ``naics_2digit`` / ``naics_label``
         - ``IndustryHyperedge.naics_2digit`` / ``naics_label`` node
           attributes — the reference ``DimIndustry`` sector identity.
       * - ``total_employment`` / ``total_wages``
         - ``IndustryHyperedge.total_employment`` / ``total_wages`` — the
           QCEW ``FactQcewAnnual`` employment/wages sum for the sector
           (variable capital *v* in money-form).
       * - ``profit_rate`` / ``occ``
         - ``IndustryHyperedge.profit_rate`` / ``occ`` — the Leontief/Marx
           Vol III derived quantities (``sv_ratio / (cv_ratio + 1)`` and the
           sector c/v ratio) computed by
           ``babylon.domain.economics.department_mapper.DepartmentMapper``
           at hydration time and stamped onto the graph node; projected here
           by reading the node's attributes only, never by importing
           ``domain.economics`` (WO-22: "read it via the graph").
       * - ``department_weights``
         - ``IndustryHyperedge.department_weights`` — the Vol II department
           allocation (``DepartmentMapper.get_allocation(...).to_dict()``).
       * - ``member_business_count`` / ``member_worker_block_count``
         - Cardinality of ``IndustryHyperedge.member_business_ids`` /
           ``member_worker_block_ids``. No live hydrator populates
           membership today (only a unit test constructs it, for XGI
           topology) — a present-but-empty roster projects as ``0``, a
           genuinely absent node projects both counts as ``None``.
       * - ``county_fips``
         - ``IndustryHyperedge.county_fips`` — the counties this sector's
           QCEW aggregate spans, sorted for deterministic ordering (the
           source ``frozenset`` carries none, Constitution III.13).

    Extra keys are rejected (``extra="forbid"``): a payload carrying a field
    this model does not declare is a shape mismatch to surface loudly, not to
    swallow.

    :param kind: The discriminator literal ``"industry"`` tagging this record
        in :data:`ProjectionRecord`.
    :param industry_id: The graph node id (e.g. ``"ind_31-33"``) — the
        industry's identity; industry is not FIPS-keyed like county.
    :param verified_tick: The committed tick this dossier was projected from,
        the staleness anchor for any materialization.
    :param naics_2digit: The 2-digit NAICS sector code, or ``None`` if absent.
    :param naics_label: The human-readable sector title, or ``None``.
    :param total_employment: Sector employment count, or ``None``.
    :param total_wages: Sector total wages (variable capital *v*), or
        ``None``.
    :param profit_rate: The BEA/QCEW-derived sector profit rate, or ``None``.
    :param occ: The sector Organic Composition of Capital (c/v), or ``None``.
    :param department_weights: The Vol II department allocation, or ``None``.
    :param member_business_count: Count of member business ids, or ``None``.
    :param member_worker_block_count: Count of member worker-block ids, or
        ``None``.
    :param county_fips: The sorted tuple of counties this sector spans, or
        ``None``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["industry"] = "industry"
    industry_id: str = Field(min_length=1)
    verified_tick: int = Field(ge=0)

    naics_2digit: str | None = None
    naics_label: str | None = None
    total_employment: int | None = Field(default=None, ge=0)
    total_wages: Currency | None = None
    profit_rate: float | None = Field(default=None, ge=0.0)
    occ: float | None = Field(default=None, ge=0.0)
    department_weights: DepartmentComposition | None = None
    member_business_count: int | None = Field(default=None, ge=0)
    member_worker_block_count: int | None = Field(default=None, ge=0)
    county_fips: tuple[str, ...] | None = None


#: A projected record of any scale, keyed on ``kind``. Program 24 P2 widens
#: this union as each new dossier lands (state/national/organization/... join
#: :class:`CountyView` and :class:`IndustryView` here) — the hydrate helpers
#: below need no change.
ProjectionRecord = Annotated[
    CountyView | IndustryView,
    Field(discriminator="kind"),
]

_COUNTY_ADAPTER: TypeAdapter[CountyView] = TypeAdapter(CountyView)
_INDUSTRY_ADAPTER: TypeAdapter[IndustryView] = TypeAdapter(IndustryView)
_RECORD_ADAPTER: TypeAdapter[ProjectionRecord] = TypeAdapter(ProjectionRecord)


def hydrate_county(data: Mapping[str, Any]) -> CountyView:
    """Validate an untyped mapping into a :class:`CountyView`.

    :param data: A mapping shaped like a ``CountyView`` — a recorded fixture,
        a JSON payload, or an assembled row dict. Missing optional keys become
        ``None``; unknown keys are rejected.
    :returns: The validated, frozen :class:`CountyView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _COUNTY_ADAPTER.validate_python(data)


def hydrate_industry(data: Mapping[str, Any]) -> IndustryView:
    """Validate an untyped mapping into an :class:`IndustryView`.

    :param data: A mapping shaped like an ``IndustryView`` — a recorded
        fixture, a JSON payload, or an assembled row dict. Missing optional
        keys become ``None``; unknown keys are rejected.
    :returns: The validated, frozen :class:`IndustryView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _INDUSTRY_ADAPTER.validate_python(data)


def hydrate_record(data: Mapping[str, Any]) -> CountyView | IndustryView:
    """Validate an untyped mapping into the correct :data:`ProjectionRecord`.

    Dispatch is by the ``kind`` discriminator, so this helper stays correct as
    new record types join the union.

    :param data: A mapping carrying a ``kind`` discriminator and the fields of
        the matching record type.
    :returns: The validated record (a :class:`CountyView` or
        :class:`IndustryView` today).
    :raises pydantic.ValidationError: if ``kind`` is missing/unknown or the
        payload violates the matched record's shape.
    """
    return _RECORD_ADAPTER.validate_python(data)


__all__ = [
    "ClassComposition",
    "ConsciousnessSimplex",
    "CountyView",
    "DepartmentComposition",
    "IndustryView",
    "ProjectionRecord",
    "hydrate_county",
    "hydrate_industry",
    "hydrate_record",
]
