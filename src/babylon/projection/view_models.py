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
and :class:`StateView` (Program 24 P2 WO-16) and is written to grow further
(national and beyond) with no change to the hydrate helpers.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from babylon.models.enums import (
    ApparatusType,
    ClassCharacter,
    ClassInscription,
    ConsciousnessTendency,
    LegalStanding,
    OrgType,
    SocialFunction,
)
from babylon.models.types import Currency, Ideology, Probability, SignedLaborHours

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


class StateView(BaseModel):
    """A state dossier — the projected read-model for one US state.

    Rolled up from every county the state contains: Constitution II.11's
    spatial substrate is county/territory-grained, so ``state`` has no
    graph node of its own — it is a *projection-time* nesting tier, R7's
    Victoria-3 nesting made concrete (see
    :func:`~babylon.projection.state.project_state` for the exact
    per-field combination rule, Program 24 P2 WO-16). Every field beyond
    identity and provenance is ``Optional`` for the same reason as
    :class:`CountyView`'s: a state's value is either withheld by a
    fog/veil gate or simply not attributed in a given run, and the honest
    projection is ``None``, never a defaulted zero.

    Extra keys are rejected (``extra="forbid"``): a payload carrying a
    field this model does not declare is a shape mismatch to surface
    loudly, not to swallow.

    :param kind: The discriminator literal ``"state"`` tagging this record
        in :data:`ProjectionRecord`.
    :param state_fips: The two-digit state FIPS code — the state's
        identity (``Territory.county_fips``'s two-digit prefix); state is
        not a graph node type.
    :param verified_tick: The committed tick this dossier was projected
        from (``tick_commit``), the staleness anchor for any
        materialization.
    :param population: The sum of every attributed county's population in
        the state, or ``None`` if no county in the state is attributed.
    :param class_composition: The five-class shares, population-weighted
        across every territory in the state that carries a
        ``tick_class_distribution``, or ``None`` if none does.
    :param median_wage: Population-weighted mean of county median wage
        across the state, or ``None``.
    :param imperial_rent_phi: The SUM of every territory's per-tick Φ in
        the state, in labor-hours (an extensive flow — additive across
        scope, unlike the intensive fields above), or ``None`` if no
        territory in the state carries the attribute.
    :param consciousness: The population-weighted ``(r, l, f)``
        consciousness simplex across the state, or ``None``.
    :param legitimacy: Population-weighted mean legitimation index across
        the state, or ``None`` if unattributed.
    :param p_acquiescence: Population-weighted P(S|A) across the state, or
        ``None``.
    :param p_revolution: Population-weighted P(S|R) across the state, or
        ``None``.
    :param bifurcation_score: Population-weighted mean bifurcation axis
        across the state, or ``None``.
    :param sovereign_id: The id of the sovereign claiming *every*
        territory in the state via a CLAIMS edge, or ``None`` when any
        territory is unclaimed, contested, or claimed by a different
        sovereign than its peers — the state-level generalization of
        :class:`CountyView`'s own "zero or contested claims" rule.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["state"] = "state"
    state_fips: str = Field(pattern=r"^\d{2}$")
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


class NationalView(BaseModel):
    """A national dossier — the projected read-model for the whole country.

    County+Nesting frame (Program 24 P2 WO-17): the nation is the tier above
    state above county. Most fields are the same population-weighted rollups
    the county dossier tracks, aggregated one tier up over every attributed
    county in :class:`~babylon.models.world_state.WorldState`; the six
    value-composition fields (``c_sum`` … ``hex_count``) are a different kind
    of quantity entirely — the ``v_national_value_aggregate`` declared-view
    row (Constitution II.11), which sums ``dynamic_hex_state`` nationwide in
    Postgres and cannot be derived from the in-memory graph/world at all
    (spec-089: hex data is persisted, not graph-resident). Every field beyond
    identity/provenance is ``Optional`` for the same reason as
    :class:`CountyView`: withheld by a gate, simply unattributed this run, or
    (for the value-composition six) never injected by a caller with no
    Postgres session to read from — in every case the honest projection is
    ``None``, never a defaulted zero.

    Extra keys are rejected (``extra="forbid"``).

    :param kind: The discriminator literal ``"national"`` tagging this record
        in :data:`ProjectionRecord`.
    :param national_id: The nation's identity (``"USA"`` today, matching
        ``NationalValueAggregate.national_id``) — not a FIPS code, so no
        pattern constraint beyond non-empty.
    :param verified_tick: The committed tick this dossier was projected from.
    :param population: Σ population over every entity nationwide with an
        attributed ``county_fips`` and positive population, or ``None`` if
        no county anywhere is attributed.
    :param class_composition: The five-class shares, population-weighted
        across every territory's own ``tick_class_distribution``, or
        ``None`` if no territory carries one.
    :param median_wage: Population-weighted mean of every territory's
        ``tick_median_wage``, or ``None``.
    :param imperial_rent_pool: The nationwide accumulated imperial-rent
        stock (``WorldState.economy.imperial_rent_pool``, the "Gas Tank") —
        NOT a rollup of the per-county Φ (``CountyView.imperial_rent_phi``);
        it is a single nation-scale quantity the engine always materializes,
        so unlike every other statistic here it is never withheld.
    :param consciousness: The ``(r, l, f)`` consciousness simplex,
        population-weighted across every attributed county's own aggregate,
        or ``None``.
    :param legitimacy: Population-weighted mean of every territory's
        ``legitimation_index``, or ``None``.
    :param p_acquiescence: Population-weighted P(S|A) across every
        attributed county, or ``None``.
    :param p_revolution: Population-weighted P(S|R) across every attributed
        county, or ``None``.
    :param bifurcation_score: Population-weighted mean of every territory's
        ``tick_bifurcation_score``, or ``None``.
    :param sovereign_id: The id of the single sovereign holding a CLAIMS edge
        over every claimed territory nationwide, or ``None`` when unclaimed
        (no CLAIMS edges) or fragmented (more than one distinct claimant
        anywhere — a balkanized nation has no single sovereign).
    :param c_sum: Constant-capital value-substance sum, from the injected
        ``v_national_value_aggregate`` row, or ``None`` if none was injected.
    :param v_sum: Variable-capital (labor-power) value-substance sum, or
        ``None``.
    :param s_sum: Surplus-value substance sum, or ``None``.
    :param k_sum: Capital-stock substance sum, or ``None``.
    :param biocapacity_sum: Nationwide biocapacity stock sum, or ``None``.
    :param hex_count: Count of hexes folded into the aggregate, or ``None``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["national"] = "national"
    national_id: str = Field(min_length=1)
    verified_tick: int = Field(ge=0)

    population: int | None = Field(default=None, ge=0)
    class_composition: ClassComposition | None = None
    median_wage: Currency | None = None
    imperial_rent_pool: Currency
    consciousness: ConsciousnessSimplex | None = None
    legitimacy: Probability | None = None
    p_acquiescence: Probability | None = None
    p_revolution: Probability | None = None
    bifurcation_score: Ideology | None = None
    sovereign_id: str | None = None

    c_sum: float | None = Field(default=None, ge=0)
    v_sum: float | None = Field(default=None, ge=0)
    s_sum: float | None = Field(default=None, ge=0)
    k_sum: float | None = Field(default=None, ge=0)
    biocapacity_sum: float | None = Field(default=None, ge=0)
    hex_count: int | None = Field(default=None, ge=0)


class OrganizationView(BaseModel):
    """An organization dossier — the projected read-model for one organization
    (Program 24 P2 WO-18).

    Every field beyond identity and provenance is ``Optional``: ``None`` means
    ``org_id`` names no known organization this run (see
    :func:`~babylon.projection.organization.project_organization`'s absence
    discipline), never a fabricated default. Extra keys are rejected
    (``extra="forbid"``).

    Fields split into two fog tiers (Track 1 / Task 5 §B; NOT wired to
    :func:`~babylon.projection.fog.filter.apply_fog` by this WO — see
    :mod:`babylon.projection.organization`'s module docstring): ``name``
    through ``is_institution`` are MATERIAL (existence, public activity,
    territorial presence — never gated); ``heat`` through ``cadre_level`` are
    POLITICAL (an org's internal state, gated for every non-player org).

    :param kind: The discriminator literal ``"organization"`` tagging this
        record in :data:`ProjectionRecord`.
    :param org_id: The organization's node/entity id — organization IS a
        graph node type (unlike county), so this is the literal node id.
    :param verified_tick: The committed tick this dossier was projected from.
    :param name: Human-readable name, or ``None`` if absent.
    :param org_type: The subtype discriminator (state apparatus / business /
        political faction / civil society), or ``None`` if absent.
    :param class_character: Which class this org objectively serves, or
        ``None`` if absent.
    :param legal_standing: Legal status, or ``None`` if absent.
    :param budget: Available resources, or ``None`` if absent.
    :param territory_ids: Territories where the org operates — an empty
        tuple is a real fact (zero territories), distinct from ``None``
        (unattributed).
    :param headquarters_id: Primary location, or ``None`` (no headquarters
        set, or unattributed).
    :param is_institution: Whether the org has crystallized into an
        institution, or ``None`` if absent.
    :param heat: State attention level, or ``None`` if absent/gated.
    :param consciousness_tendency: Ideological tendency pushed on
        communities, or ``None`` if absent/gated.
    :param cohesion: Internal unity and coordination, or ``None`` if
        absent/gated.
    :param cadre_level: Leadership quality, or ``None`` if absent/gated.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["organization"] = "organization"
    org_id: str = Field(min_length=1)
    verified_tick: int = Field(ge=0)

    name: str | None = None
    org_type: OrgType | None = None
    class_character: ClassCharacter | None = None
    legal_standing: LegalStanding | None = None
    budget: Currency | None = None
    territory_ids: tuple[str, ...] | None = None
    headquarters_id: str | None = None
    is_institution: bool | None = None

    heat: Probability | None = None
    consciousness_tendency: ConsciousnessTendency | None = None
    cohesion: Probability | None = None
    cadre_level: Probability | None = None


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


#: A projected record of any scale, keyed on ``kind``. Widened by
#: Program 24 P2 as each entity-kind page lands; the hydrate helpers
#: below need no change as the union grows.
ProjectionRecord = Annotated[
    CountyView | InstitutionView | NationalView | OrganizationView | StateView,
    Field(discriminator="kind"),
]

_COUNTY_ADAPTER: TypeAdapter[CountyView] = TypeAdapter(CountyView)
_STATE_ADAPTER: TypeAdapter[StateView] = TypeAdapter(StateView)
_NATIONAL_ADAPTER: TypeAdapter[NationalView] = TypeAdapter(NationalView)
_ORGANIZATION_ADAPTER: TypeAdapter[OrganizationView] = TypeAdapter(OrganizationView)
_INSTITUTION_ADAPTER: TypeAdapter[InstitutionView] = TypeAdapter(InstitutionView)
_RECORD_ADAPTER: TypeAdapter[CountyView | NationalView | OrganizationView | StateView] = (
    TypeAdapter(ProjectionRecord)
)


def hydrate_county(data: Mapping[str, Any]) -> CountyView:
    """Validate an untyped mapping into a :class:`CountyView`.

    :param data: A mapping shaped like a ``CountyView`` — a recorded fixture,
        a JSON payload, or an assembled row dict. Missing optional keys become
        ``None``; unknown keys are rejected.
    :returns: The validated, frozen :class:`CountyView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _COUNTY_ADAPTER.validate_python(data)


def hydrate_state(data: Mapping[str, Any]) -> StateView:
    """Validate an untyped mapping into a :class:`StateView`.

    :param data: A mapping shaped like a ``StateView`` — a recorded fixture,
        a JSON payload, or an assembled row dict. Missing optional keys become
        ``None``; unknown keys are rejected.
    :returns: The validated, frozen :class:`StateView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _STATE_ADAPTER.validate_python(data)


def hydrate_national(data: Mapping[str, Any]) -> NationalView:
    """Validate an untyped mapping into a :class:`NationalView`.

    :param data: A mapping shaped like a ``NationalView`` — a recorded
        fixture, a JSON payload, or an assembled row dict. Missing optional
        keys become ``None``; unknown keys are rejected.
    :returns: The validated, frozen :class:`NationalView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _NATIONAL_ADAPTER.validate_python(data)


def hydrate_organization(data: Mapping[str, Any]) -> OrganizationView:
    """Validate an untyped mapping into an :class:`OrganizationView`.

    :param data: A mapping shaped like an ``OrganizationView`` — a recorded
        fixture, a JSON payload, or an assembled row dict. Missing optional
        keys become ``None``; unknown keys are rejected.
    :returns: The validated, frozen :class:`OrganizationView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _ORGANIZATION_ADAPTER.validate_python(data)


def hydrate_institution(data: Mapping[str, Any]) -> InstitutionView:
    """Validate an untyped mapping into an :class:`InstitutionView`.

    :param data: A mapping shaped like an ``InstitutionView`` — a recorded
        fixture, a JSON payload, or an assembled row dict. Missing optional
        keys become ``None``; unknown keys are rejected.
    :returns: The validated, frozen :class:`InstitutionView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _INSTITUTION_ADAPTER.validate_python(data)


def hydrate_record(
    data: Mapping[str, Any],
) -> CountyView | NationalView | OrganizationView | StateView:
    """Validate an untyped mapping into the correct :data:`ProjectionRecord`.

    Dispatch is by the ``kind`` discriminator, so this helper stays correct as
    new record types join the union.

    :param data: A mapping carrying a ``kind`` discriminator and the fields of
        the matching record type.
    :returns: The validated record (one of the union's view types).
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
    "NationalView",
    "OrganizationView",
    "ProjectionRecord",
    "StateView",
    "hydrate_county",
    "hydrate_institution",
    "hydrate_national",
    "hydrate_organization",
    "hydrate_record",
    "hydrate_state",
]
