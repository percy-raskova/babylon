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

from babylon.models.enums import CommunityType
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


class CommunityOverlap(BaseModel):
    """One other community sharing at least one roster member with the queried one.

    :param community_id: The other :class:`~babylon.models.enums.CommunityType`
        this dossier's roster overlaps with.
    :param shared_member_count: How many of the queried community's roster
        members also belong to ``community_id``. Always ``>= 1`` — a pair
        sharing zero members is simply absent from
        :attr:`CommunityView.overlaps`, never a listed zero (mirrors the
        ``CountyView`` honest-absence discipline: a fact that isn't true
        isn't recorded as a false zero).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    community_id: CommunityType
    shared_member_count: int = Field(ge=1)


class CommunityView(BaseModel):
    """A community/hyperedge dossier — the projected read-model for one
    :class:`~babylon.models.enums.CommunityType`.

    Community is **never a graph node** (Constitution II.7; MEMORY
    hex/community Lawverian disposition, ``NoCommunityFanOut`` INV-010) — a
    community is an XGI hyperedge whose members are ``SocialClass`` nodes
    carrying a ``community_memberships`` entry, so this dossier is projected
    from that entity-level data, never from a node lookup. **Amendment D
    (read-only):** hyperedge *rendering* is presentation-only and safe while
    II.7 is ``[TRANSITION STATE]`` for hyperedge *mutation* — this view (and
    its vault page) carries no mutation affordance, roster/formation-tick/
    overlaps are display fields only.

    As of Program 24 P2 (WO-24), no scenario populates
    ``SocialClass.community_memberships`` in any real game
    (``CommunitySystem.step`` is a structural no-op —
    ``src/babylon/sentinels/seam/registry.py`` marks the payload
    ``STRUCTURALLY_IMPOSSIBLE``), so :attr:`roster` and :attr:`overlaps`
    honestly hydrate to ``None`` today; the projection code exists to light
    up the moment a producer lands, not to fabricate activity.

    Extra keys are rejected (``extra="forbid"``): a payload carrying a field
    this model does not declare is a shape mismatch to surface loudly.

    :param kind: The discriminator literal ``"community"`` tagging this
        record in :data:`ProjectionRecord`.
    :param community_id: The community this dossier describes — one of the
        14 fixed :class:`~babylon.models.enums.CommunityType` members, NOT a
        free-form id. An unrecognized string is a caller error (loud
        ``ValidationError``), never an absence — absence is the *fields*
        being empty, not the identity being unrecognized.
    :param verified_tick: The committed tick this dossier was projected from,
        the staleness anchor for any materialization.
    :param roster: The sorted tuple of member ``SocialClass`` ids currently
        attributed to this community, or ``None`` if nobody is (honest
        absence — never an empty tuple for "nobody"; an empty tuple is
        reserved for a *different*, currently-unreachable case, see
        :attr:`overlaps`). Renders as read-only ``[[social_class/<id>]]``
        wikilinks — incidence-via-backlinks (design-canon S9).
    :param formation_tick: The tick this hyperedge was first instantiated —
        **always ``None`` today, and not merely per-run absent**: neither
        ``CommunityState`` nor ``CommunityMembership``
        (``babylon.models.entities.community``) carries any timestamp field,
        because a ``CommunityType`` is a fixed 14-member taxonomy assigned at
        import time (``COMMUNITY_CATEGORY_MAP``), not a hyperedge
        dynamically instantiated at some tick. Declared ``Optional`` so a
        future spec adding hyperedge lifecycle tracking can populate it
        without a schema break, not because this run simply lacks the data.
    :param overlaps: Every *other* community sharing at least one roster
        member with this one, sorted by ``community_id``, or ``None`` when
        :attr:`roster` itself is ``None`` (overlap cannot be computed without
        a roster). A roster that IS attributed but shares zero members with
        any other community projects :attr:`overlaps` as an empty tuple, not
        ``None`` — "computed and found none" is a different fact from "not
        computed."
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["community"] = "community"
    community_id: CommunityType
    verified_tick: int = Field(ge=0)

    roster: tuple[str, ...] | None = None
    formation_tick: int | None = None
    overlaps: tuple[CommunityOverlap, ...] | None = None


#: A projected record of any scale, keyed on ``kind``. Program 24 P2 widens
#: this union as further dossier kinds land (state, national, ... — the
#: hydrate helpers below need no change per kind added).
ProjectionRecord = Annotated[
    CountyView | CommunityView,
    Field(discriminator="kind"),
]

_COUNTY_ADAPTER: TypeAdapter[CountyView] = TypeAdapter(CountyView)
_COMMUNITY_ADAPTER: TypeAdapter[CommunityView] = TypeAdapter(CommunityView)
_RECORD_ADAPTER: TypeAdapter[CountyView | CommunityView] = TypeAdapter(ProjectionRecord)


def hydrate_county(data: Mapping[str, Any]) -> CountyView:
    """Validate an untyped mapping into a :class:`CountyView`.

    :param data: A mapping shaped like a ``CountyView`` — a recorded fixture,
        a JSON payload, or an assembled row dict. Missing optional keys become
        ``None``; unknown keys are rejected.
    :returns: The validated, frozen :class:`CountyView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _COUNTY_ADAPTER.validate_python(data)


def hydrate_community(data: Mapping[str, Any]) -> CommunityView:
    """Validate an untyped mapping into a :class:`CommunityView`.

    :param data: A mapping shaped like a ``CommunityView`` — a recorded
        fixture, a JSON payload, or an assembled row dict. Missing optional
        keys become ``None``; unknown keys are rejected.
    :returns: The validated, frozen :class:`CommunityView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _COMMUNITY_ADAPTER.validate_python(data)


def hydrate_record(data: Mapping[str, Any]) -> CountyView | CommunityView:
    """Validate an untyped mapping into the correct :data:`ProjectionRecord`.

    Dispatch is by the ``kind`` discriminator, so this helper stays correct as
    new record types join the union.

    :param data: A mapping carrying a ``kind`` discriminator and the fields of
        the matching record type.
    :returns: The validated record, typed to the member :data:`ProjectionRecord`
        matches (a :class:`CountyView` or :class:`CommunityView` today).
    :raises pydantic.ValidationError: if ``kind`` is missing/unknown or the
        payload violates the matched record's shape.
    """
    return _RECORD_ADAPTER.validate_python(data)


__all__ = [
    "ClassComposition",
    "CommunityOverlap",
    "CommunityView",
    "ConsciousnessSimplex",
    "CountyView",
    "ProjectionRecord",
    "hydrate_community",
    "hydrate_county",
    "hydrate_record",
]
