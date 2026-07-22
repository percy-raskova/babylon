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
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from babylon.models.enums import (
    ApparatusType,
    ClassCharacter,
    ClassInscription,
    ColonialStance,
    CommunityType,
    ConsciousnessTendency,
    ExtractionPolicy,
    LegalStanding,
    OrgType,
    SocialFunction,
    SocialRole,
    SovereigntyType,
)
from babylon.models.types import (
    Coefficient,
    Currency,
    Ideology,
    Intensity,
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
    :param habitability: Territory ecological viability in ``[0, 1]``
        (MetabolismSystem's biocapacity/Sovereign-metabolic-impact index), or
        ``None`` before MetabolismSystem has ever run this session (tick 0)
        or when no territory carries this county's FIPS — never a fabricated
        ``0.0`` or the ``1.0`` some aggregators default an unattributed
        reading to.
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
    habitability: Probability | None = None
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


class SovereignView(BaseModel):
    """A sovereign dossier — the projected read-model for one sovereign authority.

    Program 24 P2 WO-20: sovereign is the CLAIMS-edge claimant
    :func:`~babylon.projection.county.project_county`'s ``_single_claimant``
    already resolves for a county's ``sovereign_id`` field; this view is what
    a county page's ``[[sovereign/<id>]]`` wikilink resolves to.

    Every field beyond identity and provenance is ``Optional`` because the
    sovereign either doesn't exist in this run (a stale/unminted id) or one
    of its attributes genuinely isn't attributed; in both cases the honest
    projection is ``None``, never a defaulted value. ``claimed_county_fips``
    is the one field where an *empty* value (``()``) and ``None`` mean
    different things — see :attr:`claimed_county_fips`.

    Extra keys are rejected (``extra="forbid"``): a payload carrying a field
    this model does not declare is a shape mismatch to surface loudly, not to
    swallow.

    :param kind: The discriminator literal ``"sovereign"`` tagging this
        record in :data:`ProjectionRecord`.
    :param sovereign_id: The sovereign's stable node id (``SOV_*``,
        spec-070) — the sovereign's identity; sovereign IS a graph node
        (unlike county, which addresses a territory by ``county_fips``).
    :param verified_tick: The committed tick this dossier was projected from
        (``tick_commit``), the staleness anchor for any materialization.
    :param name: Display name, or ``None`` if the sovereign node doesn't
        exist / carries none.
    :param sovereignty_type: The sovereign's classification (recognized
        state, provisional, insurgent, occupation, secessionist, emergency),
        or ``None``.
    :param legitimacy: Current legitimacy in ``[0, 1]`` — the same attribute
        ``CollapseTransitionSystem`` reads for the FR-023
        ``SOVEREIGN_COLLAPSE`` trigger — or ``None``.
    :param ruling_faction_id: The ruling
        :class:`~babylon.models.entities.balkanization_faction.BalkanizationFaction`'s
        id, or ``None`` (legitimately ``None`` for the FR-040b
        ``SOV_EXTERIOR_NULL`` fallback, or absence).
    :param extraction_policy: The sovereign's per-tick extractive relationship
        (intensify/continue/cease), or ``None``.
    :param capital_territory_id: The raw capital territory node id, or
        ``None`` if the sovereign names no capital / doesn't exist.
    :param capital_county_fips: The capital territory's ``county_fips``,
        derived from :attr:`capital_territory_id`, or ``None`` when there is
        no capital, the named territory doesn't exist, or it carries no
        ``county_fips``.
    :param founded_tick: The tick the sovereign was instantiated, or ``None``.
    :param dissolved_tick: The tick the sovereign dissolved, or ``None`` (the
        common case for a still-active sovereign, not necessarily an
        attribution gap).
    :param claimed_county_fips: The sorted, de-duplicated ``county_fips`` of
        every territory this sovereign CLAIMS — the reverse of
        ``project_county``'s ``sovereign_id``. ``None`` when the sovereign
        node itself doesn't exist; an empty tuple is a real, present value
        ("this sovereign currently claims nothing"), never conflated with
        absence.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["sovereign"] = "sovereign"
    sovereign_id: str = Field(pattern=r"^SOV_[A-Z][A-Z0-9_]*$")
    verified_tick: int = Field(ge=0)

    name: str | None = None
    sovereignty_type: SovereigntyType | None = None
    legitimacy: Probability | None = None
    ruling_faction_id: str | None = Field(default=None, pattern=r"^FAC_[A-Z][A-Z0-9_]*$")
    extraction_policy: ExtractionPolicy | None = None
    capital_territory_id: str | None = None
    capital_county_fips: str | None = Field(default=None, pattern=r"^\d{5}$")
    founded_tick: int | None = Field(default=None, ge=0)
    dissolved_tick: int | None = Field(default=None, ge=0)
    claimed_county_fips: tuple[str, ...] | None = None


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


class ClassPhiReadingView(BaseModel):
    """One class/county's Fundamental Theorem reading (Vol I U2).

    Projection-side mirror of
    :class:`~babylon.domain.dialectics.instances.value_form.ClassPhiReading`
    — the projection layer declares its own wire shape rather than importing
    the domain model (WO-22's no-engine-no-domain-import discipline, the
    same choice :class:`DepartmentComposition` makes for
    ``DepartmentMapper.DepartmentAllocation``). Hydrated verbatim from the
    ``fundamental_theorem`` graph-attribute dump
    (``ContradictionSystem._stash_fundamental_theorem``), never recomputed.

    :param entity_id: The class/county graph node id this reading is for.
    :param w_paid: W_c — total wages paid this tick.
    :param v_produced: V_c — productivity value captured this tick.
    :param phi_absolute: Phi = W_c − V_c in dollars. Always defined.
    :param phi_relative: ``(W_c − V_c)/V_c``, or ``None`` when ``v_produced
        <= 0`` (a class that produced nothing has no defined ratio).
    :param labor_aristocracy_ratio: ``W_c / V_c``, or ``None`` under the
        same guard.
    :param is_labor_aristocracy: ``W_c > V_c`` (strict), or ``None`` under
        the same guard.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    entity_id: str = Field(min_length=1)
    w_paid: float
    v_produced: float
    phi_absolute: float
    phi_relative: float | None = None
    labor_aristocracy_ratio: float | None = None
    is_labor_aristocracy: bool | None = None


class EconomyView(BaseModel):
    """The economy dossier — the singleton national Φ/surplus/matter read-model.

    T3 spine-C prescription (``ai/_inbox/PROGRAM_v1_0_0_playable_archive.md``
    §C): (1) the Fundamental Theorem verdict read off the SAME
    ``opposition_states["wage"].balance`` the engine's own contradiction
    registry adjudicates — never a parallel Φ; (2) the per-class/county Φ
    readings the ``fundamental_theorem`` graph stash carries (Vol I U2);
    (3) Φ's tri-decomposition (unequal exchange + reproduction + domestic,
    excluding the report-only Φ_III term from the total); (4) the Volume
    III surplus split ``s = p + i + r + t``, aggregated RATIO-OF-SUMS across
    territories, never mean-of-ratios; (5) the metabolic "matter-book"
    (overshoot ``O = C/B``, the monotone ceiling ``M̄``); (6) the energy
    vertex β_J, an UNPOSITIONED honest absence (genuinely absent tree-wide —
    no EROI/joule accounting anywhere in the engine). Money and matter are
    never rendered as interconvertible — see
    :func:`~babylon.projection.economy.project_economy` for the full
    field-by-field producer ruling.

    Extra keys are rejected (``extra="forbid"``): a payload carrying a field
    this model does not declare is a shape mismatch to surface loudly, not
    to swallow.

    :param kind: The discriminator literal ``"economy"`` tagging this record
        in :data:`ProjectionRecord`.
    :param economy_id: The economy's identity (``"USA"`` today, matching
        :attr:`NationalView.national_id`'s singleton convention) — not a
        FIPS code.
    :param verified_tick: The committed tick this dossier was projected from.
    :param wage_balance: The ``wage`` opposition's signed Balance
        ``(W_c − V_c)/(W_c + V_c)`` read verbatim off ``opposition_states``
        — positive means the wage exceeds value produced (the imperial
        bribe). ``None`` when the opposition registry is unwired or the
        ``wage`` key is not registered this run.
    :param labor_aristocracy_verdict: ``wage_balance > 0``, the Fundamental
        Theorem verdict BY CONSTRUCTION (never recomputed from a parallel
        feed). ``None`` under the same guard as :attr:`wage_balance`.
    :param class_phi_readings: Every class/county's
        :class:`ClassPhiReadingView`, sorted by ``entity_id`` for
        deterministic ordering, or ``None`` when the ``fundamental_theorem``
        graph attribute itself is absent (the opposition registry never
        ran). An attributed-but-empty tuple means the registry ran but no
        node carried both ``w_paid``/``v_produced`` this tick — a real,
        different fact from "never computed".
    :param phi_unequal_exchange: Emmanuel/Amin international transfer
        (``(1 − γ_basket)·Consumption``), or ``None`` — genuinely absent
        tree-wide: no engine producer publishes ``γ_basket`` or aggregate
        consumption to the graph today.
    :param phi_reproduction: Meillassoux externalized reproduction
        (``max(0, P_g2 − wage)``), or ``None`` — genuinely absent tree-wide.
    :param phi_domestic: Fortunati domestic shadow labor (``τ · L_unpaid``),
        or ``None`` — genuinely absent tree-wide (unpaid/reproductive
        labor-hours have no producer, even though national MELT τ is itself
        live elsewhere).
    :param phi_iii_report: The kernel's narrower invisible-fraction Φ_III
        (report only, excluded from any total), or ``None`` — same absence.
    :param phi_decomposition_total: The sum of :attr:`phi_unequal_exchange`
        + :attr:`phi_reproduction` + :attr:`phi_domestic` (excluding
        :attr:`phi_iii_report` by design — the domain model's own ``total``
        computed-field rule), or ``None`` unless all three conservation
        components are present.
    :param surplus_produced: Σ ``tick_total_surplus`` (s) across territories
        this tick, or ``None`` when no territory carries the attribute.
    :param profit_of_enterprise: Σ ``tick_profit_of_enterprise`` (p) —
        signed; may be negative in a debt spiral.
    :param interest_burden: Σ ``tick_interest_burden`` (i).
    :param ground_rent: Σ ``tick_ground_rent`` (r).
    :param taxes_on_surplus: Σ ``tick_taxes_on_surplus`` (t).
    :param rentier_share: The national ``Σr / Σs`` — a genuine RATIO OF
        SUMS, never a mean of the per-territory ``tick_rentier_share``
        readings (the intensive-aggregation error class). ``None`` when
        Σs is not positive.
    :param financialization_share: The national ``Σi / Σs``, same
        ratio-of-sums discipline.
    :param total_consumption: Σ ``consumption_needs`` nationwide (C, the
        ``WorldState.total_consumption`` extensive sum), or ``None`` when
        the world carries no territory.
    :param total_biocapacity: Σ ``Territory.biocapacity`` nationwide (B),
        or ``None`` under the same guard.
    :param overshoot_ratio: ``C / B``, or ``None`` when B is not positive —
        never the ``WorldState.overshoot_ratio`` computed-field's own
        fabricated ``999.0`` sentinel (Constitution III.11 forbids a
        substituted default standing in for absence).
    :param biocapacity_ceiling: Σ ``Territory.max_biocapacity`` nationwide
        (the monotone ceiling M̄), or ``None`` when the world carries no
        territory.
    :param energy_beta_j: The energy vertex β_J — always ``None``.
        Genuinely absent tree-wide (verified: no EROI, fossil,
        power-density, or joule accounting anywhere in the engine); an
        UNPOSITIONED {absence} fence naming the energy-split prerequisite.
        Never derived from the money-form quantities above — money and
        matter are not interconvertible.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["economy"] = "economy"
    economy_id: str = Field(min_length=1)
    verified_tick: int = Field(ge=0)

    wage_balance: Ideology | None = None
    labor_aristocracy_verdict: bool | None = None
    class_phi_readings: tuple[ClassPhiReadingView, ...] | None = None

    phi_unequal_exchange: float | None = None
    phi_reproduction: float | None = None
    phi_domestic: float | None = None
    phi_iii_report: float | None = None
    phi_decomposition_total: float | None = None

    surplus_produced: Currency | None = None
    profit_of_enterprise: float | None = None
    interest_burden: Currency | None = None
    ground_rent: Currency | None = None
    taxes_on_surplus: Currency | None = None
    rentier_share: float | None = None
    financialization_share: float | None = None

    total_consumption: Currency | None = None
    total_biocapacity: Currency | None = None
    overshoot_ratio: float | None = Field(default=None, ge=0.0)
    biocapacity_ceiling: Currency | None = None

    energy_beta_j: float | None = None


class NationalTrendView(BaseModel):
    """One row of ``v_national_trend`` — the declared trend read-model (T5 Unit U2).

    Constitution II.11's declared cross-subsystem read interface over
    ``tick_summary`` (spec-037; extended by migrations 0033-0035): per-tick
    ``LAG``-window deltas for the series a real Archive campaign now
    actually writes (:func:`~babylon.projection.tick_summary.
    build_tick_summary_kwargs`, wired at :class:`~babylon.game.session.
    GameSession`'s commit boundary, T5 Unit U2) — Φ (``imperial_rent``, the
    Fundamental Theorem's Imperial Rent gap) and the Program 23 Market
    Scissors price⟷value axis (``price_log``/``fictitious_log``,
    ADR077/078), plus the correction-snap ledger's own foreshadowed
    increment read (``market_corrections``, a cumulative counter —
    migration ``0034_market_corrections.sql``'s own docstring: "the
    cockpit derives the snap ticks from increments"). ``tick_summary``'s
    remaining columns (``year``/``total_c``/``total_v``/``total_s``/
    ``exploitation_rate``/``profit_rate``/``co_optive_edge_count``/
    ``conservation_check``) carry no computed value from any engine system
    yet (see :func:`~babylon.projection.tick_summary.
    build_tick_summary_kwargs`'s own docstring) — a trend of a permanently
    ``NULL`` column is not a signal, so this view does not window them.

    Every ``*_delta`` is ``NULL`` at a session's first committed tick (no
    prior row for ``LAG`` to read) and whenever either endpoint of the pair
    is itself ``NULL`` (the axis was absent one side of the step) — honest
    absence (Constitution III.11), never a fabricated zero.

    :param session_id: The campaign session this row belongs to.
    :param tick: The committed tick this row summarizes.
    :param imperial_rent: ``GlobalEconomy.imperial_rent_pool`` this tick.
    :param imperial_rent_delta: ``imperial_rent - LAG(imperial_rent)``.
    :param price_log: The Market Scissors price-index log this tick.
    :param price_log_delta: ``price_log - LAG(price_log)``.
    :param fictitious_log: The Market Scissors fictitious-capitalization log.
    :param fictitious_log_delta: ``fictitious_log - LAG(fictitious_log)``.
    :param market_corrections: Cumulative correction-snap count as of this
        tick.
    :param market_corrections_delta: New correction snaps since the prior
        tick — a positive value marks a snap tick this tick.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: UUID
    tick: int = Field(ge=0)
    imperial_rent: float | None = None
    imperial_rent_delta: float | None = None
    price_log: float | None = None
    price_log_delta: float | None = None
    fictitious_log: float | None = None
    fictitious_log_delta: float | None = None
    market_corrections: int | None = None
    market_corrections_delta: int | None = None


class FieldStateNodeView(BaseModel):
    """One social-class node's Systems #19/#20 field-stack reading (T3 U3).

    Projection-side mirror of the shape
    ``web/game/engine_bridge.py::_build_field_state_nodes`` serializes —
    ContradictionFieldSystem @19's ``contradiction_fields`` (per-field
    value), FieldDerivativeSystem @20's ``field_derivatives`` (only its
    ``laplacian``/``df_dt`` sub-keys — ``d2f_dt2`` is deliberately out of
    this dossier's declared contract, matching the ported endpoint), and
    FascistFactionSystem's ``fascist_alignment``. A node contributes only
    the keys it actually carries this tick — never a fabricated zero for a
    field the engine did not compute.

    :param node_id: The social_class graph node id.
    :param name: The node's ``name`` attribute, or ``node_id`` itself when
        unattributed (matches the ported helper's own fallback).
    :param fields: ``{field_name: value}`` from ``contradiction_fields``, or
        ``None`` when the node carries none this tick.
    :param laplacian: ``{field_name: value}``, the ``laplacian`` sub-key of
        every field in ``field_derivatives`` that has one, or ``None``.
    :param df_dt: ``{field_name: value}``, the ``df_dt`` sub-key of every
        field in ``field_derivatives`` that has one (``None`` df_dt entries
        — fewer than 2 ticks of history — are excluded, not zero-filled), or
        ``None`` when no field has one yet.
    :param fascist_alignment: The node's ``fascist_alignment`` (a required
        ``Intensity`` ``SocialClass`` field, default 0.0 — so this is
        ``None`` only when the node itself carries no such attribute at
        all, never when the true value happens to be zero).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    fields: dict[str, float] | None = None
    laplacian: dict[str, float] | None = None
    df_dt: dict[str, float] | None = None
    fascist_alignment: Intensity | None = None


class FieldStateEdgeView(BaseModel):
    """One field-gradient edge entry (T3 U3), one per ``(edge, field)`` pair.

    Projection-side mirror of
    ``web/game/engine_bridge.py::_build_field_state_edges`` — an edge
    carrying gradients for N fields contributes N entries, one per field
    name, sorted. Territory anchoring reuses the TENANCY membership the
    engine's own ``ProductionSystem._find_tenancy_target`` establishes
    (Occupant -> Territory); an endpoint with no resolvable territory keeps
    its entry with that key present but ``None`` — never omitted or
    fabricated (the same keep-key-use-null convention the ported helper's
    own docstring documents).

    :param source: The edge's source social_class node id.
    :param target: The edge's target social_class node id.
    :param source_territory: The territory ``source`` holds a TENANCY edge
        into, or ``None`` when unresolved.
    :param target_territory: The territory ``target`` holds a TENANCY edge
        into, or ``None`` when unresolved.
    :param field: The field name this gradient reading is for.
    :param gradient: ``f(target) - f(source)`` for :attr:`field`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    source_territory: str | None = None
    target_territory: str | None = None
    field: str = Field(min_length=1)
    gradient: float


class PrincipalFieldView(BaseModel):
    """FieldDerivativeSystem @20's principal-FIELD identification (T3 U3).

    Deliberately distinct from ContradictionSystem @18's Maoist principal
    OPPOSITION (E0 rename) — this is the field-stack's fastest-developing
    contradiction FIELD (max ``|df/dt|`` across every node), never the
    opposition-layer's own principal.

    :param field_name: The identified principal field's name, or ``None``
        when no field has yet shown any nonzero ``df/dt`` (legitimately
        null under 2 ticks of history — never a fabricated first field).
    :param max_abs_df_dt: The winning field's max ``|df/dt|`` across every
        node (``0.0`` when :attr:`field_name` is ``None``).
    :param changed: Whether the principal field differs from the previous
        tick's.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    field_name: str | None = None
    max_abs_df_dt: float = Field(ge=0.0)
    changed: bool


class DialecticalRegimeView(BaseModel):
    """ContradictionSystem @18's fixed-point regime classification (T3 U3).

    Classifies the capital_labor opposition (falling back to whichever
    opposition is principal) into one of three regimes from its trajectory
    — reproduction (converged or contained), crisis (rising, no Aufhebung),
    or sublation (rising, level transition available).

    :param regime: ``"reproduction"``, ``"crisis"``, or ``"sublation"``.
    :param opposition: The classified opposition's key (``"capital_labor"``
        today, or its principal fallback).
    :param rate: The classified opposition's own rate this tick.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    regime: Literal["reproduction", "crisis", "sublation"]
    opposition: str = Field(min_length=1)
    rate: float


class FieldStateView(BaseModel):
    """The field-state dossier — the Weather Layer, Systems #19/#20's field stack (T3 U3).

    Port of ``web/game/engine_bridge.py::EngineBridge.get_field_state`` (the
    ``{tick, nodes, edges, principal_field, dialectical_regime}`` shape) into
    a pure projection read-model — same read logic, no redesign. Transport-
    neutral by construction — no Django, no engine imports, no database
    connection; the caller hands in the LIVE post-tick graph it already
    holds (never a ``WorldState.from_graph()`` round trip, which drops the
    graph-level ``principal_field``/``dialectical_regime`` attrs and every
    node/edge attr this dossier reads outside its own ``field_stack`` carrier
    — see :func:`~babylon.projection.field_state.project_field_state`).

    **One producer per field:**

    .. list-table:: Field-producer rulings
       :header-rows: 1

       * - Field
         - Producer
       * - ``nodes``
         - :class:`FieldStateNodeView` per social_class node carrying
           ``contradiction_fields`` (ContradictionFieldSystem @19),
           ``field_derivatives`` (FieldDerivativeSystem @20 — ``laplacian``/
           ``df_dt`` sub-keys only), or ``fascist_alignment``
           (FascistFactionSystem), sorted by ``node_id``. ``None`` when no
           social_class node carries any of the three this tick (the field
           stack never ran).
       * - ``edges``
         - :class:`FieldStateEdgeView` per ``(edge, field)`` pair carrying a
           ``field_gradients`` entry (FieldDerivativeSystem @20), territory-
           anchored via the live TENANCY edges, sorted by ``(source, target,
           field)``. ``None`` when no edge carries a gradient this tick.
       * - ``principal_field``
         - The ``principal_field`` graph attribute
           (``FieldDerivativeSystem._identify_principal_contradiction``),
           hydrated verbatim. ``None`` when the attribute itself is absent
           (the field stack never ran this tick — it is otherwise always
           written once ``FieldDerivativeSystem`` runs with a nonempty field
           registry).
       * - ``dialectical_regime``
         - The ``dialectical_regime`` graph attribute
           (``ContradictionSystem._classify_regime`` @18), hydrated
           verbatim. ``None`` when no ``capital_labor``/principal
           ``OppositionState`` existed yet this tick — the classifier
           returns without writing the attribute in that case.

    Absence discipline (Constitution III.11): a fresh graph with neither
    system having run yet (tick 0) projects every field ``None`` — an
    honest "the weather has not formed" reading, never a fabricated calm.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["field_state"] = "field_state"
    field_state_id: str = Field(min_length=1)
    verified_tick: int = Field(ge=0)

    nodes: tuple[FieldStateNodeView, ...] | None = None
    edges: tuple[FieldStateEdgeView, ...] | None = None
    principal_field: PrincipalFieldView | None = None
    dialectical_regime: DialecticalRegimeView | None = None


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


class FactionTerritoryInfluence(BaseModel):
    """One INFLUENCES edge from a faction into a territory (spec-070 FR-014).

    The reverse-direction sibling of :class:`FieldStateEdgeView`'s territory
    anchoring: a faction's influence is inherently relational (a faction, a
    territory, and how strongly/by what channel), so it gets its own
    per-entry composite rather than collapsing to a bare id the way
    :attr:`SovereignView.claimed_county_fips` does for weight-free CLAIMS.

    :param territory_id: The raw territory node id the faction influences
        (the INFLUENCES edge's target).
    :param county_fips: The territory's ``county_fips`` attribute, resolved
        the same way :func:`babylon.projection.sovereign._county_fips_of`
        resolves a sovereign's capital/claims, or ``None`` when the
        territory node doesn't exist or carries no ``county_fips``.
    :param influence_level: The edge's influence intensity in ``[0, 1]``.
    :param support_type: The edge's support channel (e.g.
        labor/ideological/material).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    territory_id: str = Field(min_length=1)
    county_fips: str | None = Field(default=None, pattern=r"^\d{5}$")
    influence_level: Probability
    support_type: str = Field(min_length=1)


class FactionView(BaseModel):
    """A balkanization-faction dossier — the projected read-model for one
    political coalition (T3 U4).

    Mirrors :func:`~babylon.projection.sovereign.project_sovereign`'s recipe:
    faction IS a graph node (spec-070's ``BalkanizationFaction``, stamped
    whole-cloth by ``WorldState.to_graph()``), so every identity field beyond
    provenance is that node's own attribute. ``territory_influence`` is the
    reverse of :attr:`SovereignView.claimed_county_fips` — carrying the
    INFLUENCES edge's weight/channel, not just the anchored id, per FR-014.

    Every field beyond identity and provenance is ``Optional`` because the
    faction either doesn't exist in this run (a stale/unminted id) or one of
    its attributes genuinely isn't attributed; in both cases the honest
    projection is ``None``, never a defaulted value. ``territory_influence``
    is the one field where an *empty* tuple ("influences nothing right now")
    and ``None`` ("this faction doesn't exist") are deliberately distinct.

    Extra keys are rejected (``extra="forbid"``): a payload carrying a field
    this model does not declare is a shape mismatch to surface loudly, not to
    swallow.

    :param kind: The discriminator literal ``"faction"`` tagging this record
        in :data:`ProjectionRecord`.
    :param faction_id: The faction's stable node id (``FAC_*``, spec-070).
    :param verified_tick: The committed tick this dossier was projected from
        (``tick_commit``), the staleness anchor for any materialization.
    :param name: Display name, or ``None`` if the faction node doesn't exist
        / carries none.
    :param ideology: Free-text ideological label, or ``None``.
    :param colonial_stance: The principal political axis (UPHOLD / IGNORE /
        ABOLISH), or ``None``.
    :param is_settler_formation: Whether the faction is a settler-formation
        coalition, or ``None``.
    :param extraction_modifier: Mechanical multiplier on extraction, or
        ``None``.
    :param violence_modifier: Mechanical multiplier on state violence, or
        ``None``.
    :param class_reduction: The faction's effect on class contradiction in
        ``[0, 1]``, or ``None``.
    :param metabolic_reduction: The faction's effect on metabolic impact in
        ``[-1, +1]``, or ``None``.
    :param color_hex: UI color in ``#RRGGBB`` form, or ``None``.
    :param founded_tick: The tick the faction was instantiated, or ``None``.
    :param dissolved_tick: The tick the faction dissolved, or ``None`` (the
        common case for a still-active faction, not necessarily an
        attribution gap).
    :param territory_influence: Every INFLUENCES edge this faction casts,
        sorted by influence level descending then territory id ascending
        (matching ``GraphProtocol.query_faction_influence_by_territory``'s
        own ordering). ``None`` when the faction node itself doesn't exist;
        an empty tuple is a real, present value ("this faction currently
        influences nothing"), never conflated with absence.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["faction"] = "faction"
    faction_id: str = Field(pattern=r"^FAC_[A-Z][A-Z0-9_]*$")
    verified_tick: int = Field(ge=0)

    name: str | None = None
    ideology: str | None = Field(default=None, min_length=1, max_length=64)
    colonial_stance: ColonialStance | None = None
    is_settler_formation: bool | None = None
    extraction_modifier: float | None = Field(default=None, ge=0.0)
    violence_modifier: float | None = Field(default=None, ge=0.0)
    class_reduction: Probability | None = None
    metabolic_reduction: float | None = Field(default=None, ge=-1.0, le=1.0)
    color_hex: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    founded_tick: int | None = Field(default=None, ge=0)
    dissolved_tick: int | None = Field(default=None, ge=0)
    territory_influence: tuple[FactionTerritoryInfluence, ...] | None = None


#: A projected record of any scale, keyed on ``kind``. Widened by
#: Program 24 P2 as each entity-kind page lands; the hydrate helpers
#: below need no change as the union grows.
ProjectionRecord = Annotated[
    CountyView
    | CommunityView
    | EconomyView
    | FactionView
    | FieldStateView
    | IndustryView
    | InstitutionView
    | KeyFigureView
    | NationalView
    | OrganizationView
    | SocialClassView
    | SovereignView
    | StateView,
    Field(discriminator="kind"),
]

_COUNTY_ADAPTER: TypeAdapter[CountyView] = TypeAdapter(CountyView)
_STATE_ADAPTER: TypeAdapter[StateView] = TypeAdapter(StateView)
_NATIONAL_ADAPTER: TypeAdapter[NationalView] = TypeAdapter(NationalView)
_ORGANIZATION_ADAPTER: TypeAdapter[OrganizationView] = TypeAdapter(OrganizationView)
_INSTITUTION_ADAPTER: TypeAdapter[InstitutionView] = TypeAdapter(InstitutionView)
_SOVEREIGN_ADAPTER: TypeAdapter[SovereignView] = TypeAdapter(SovereignView)
_FACTION_ADAPTER: TypeAdapter[FactionView] = TypeAdapter(FactionView)
_KEY_FIGURE_ADAPTER: TypeAdapter[KeyFigureView] = TypeAdapter(KeyFigureView)
_INDUSTRY_ADAPTER: TypeAdapter[IndustryView] = TypeAdapter(IndustryView)
_SOCIAL_CLASS_ADAPTER: TypeAdapter[SocialClassView] = TypeAdapter(SocialClassView)
_COMMUNITY_ADAPTER: TypeAdapter[CommunityView] = TypeAdapter(CommunityView)
_ECONOMY_ADAPTER: TypeAdapter[EconomyView] = TypeAdapter(EconomyView)
_FIELD_STATE_ADAPTER: TypeAdapter[FieldStateView] = TypeAdapter(FieldStateView)
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


def hydrate_economy(data: Mapping[str, Any]) -> EconomyView:
    """Validate an untyped mapping into an :class:`EconomyView`.

    :param data: A mapping shaped like an ``EconomyView`` — a recorded
        fixture, a JSON payload, or an assembled row dict. Missing optional
        keys become ``None``; unknown keys are rejected.
    :returns: The validated, frozen :class:`EconomyView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _ECONOMY_ADAPTER.validate_python(data)


def hydrate_field_state(data: Mapping[str, Any]) -> FieldStateView:
    """Validate an untyped mapping into a :class:`FieldStateView`.

    :param data: A mapping shaped like a ``FieldStateView`` — a recorded
        fixture, a JSON payload, or an assembled row dict. Missing optional
        keys become ``None``; unknown keys are rejected.
    :returns: The validated, frozen :class:`FieldStateView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _FIELD_STATE_ADAPTER.validate_python(data)


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


def hydrate_sovereign(data: Mapping[str, Any]) -> SovereignView:
    """Validate an untyped mapping into a :class:`SovereignView`.

    :param data: A mapping shaped like a ``SovereignView`` — a recorded
        fixture, a JSON payload, or an assembled row dict. Missing optional
        keys become ``None``; unknown keys are rejected.
    :returns: The validated, frozen :class:`SovereignView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _SOVEREIGN_ADAPTER.validate_python(data)


def hydrate_faction(data: Mapping[str, Any]) -> FactionView:
    """Validate an untyped mapping into a :class:`FactionView`.

    :param data: A mapping shaped like a ``FactionView`` — a recorded
        fixture, a JSON payload, or an assembled row dict. Missing optional
        keys become ``None``; unknown keys are rejected.
    :returns: The validated, frozen :class:`FactionView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _FACTION_ADAPTER.validate_python(data)


def hydrate_key_figure(data: Mapping[str, Any]) -> KeyFigureView:
    """Validate an untyped mapping into a :class:`KeyFigureView`.

    :param data: A mapping shaped like a ``KeyFigureView`` — a recorded
        fixture, a JSON payload, or an assembled row dict. Unknown keys are
        rejected.
    :returns: The validated, frozen :class:`KeyFigureView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _KEY_FIGURE_ADAPTER.validate_python(data)


def hydrate_industry(data: Mapping[str, Any]) -> IndustryView:
    """Validate an untyped mapping into an :class:`IndustryView`.

    :param data: A mapping shaped like an ``IndustryView`` — a recorded
        fixture, a JSON payload, or an assembled row dict. Missing optional
        keys become ``None``; unknown keys are rejected.
    :returns: The validated, frozen :class:`IndustryView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _INDUSTRY_ADAPTER.validate_python(data)


def hydrate_social_class(data: Mapping[str, Any]) -> SocialClassView:
    """Validate an untyped mapping into a :class:`SocialClassView`.

    :param data: A mapping shaped like a ``SocialClassView`` — a recorded
        fixture, a JSON payload, or an assembled row dict. Missing optional
        keys become ``None``; unknown keys are rejected.
    :returns: The validated, frozen :class:`SocialClassView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _SOCIAL_CLASS_ADAPTER.validate_python(data)


def hydrate_community(data: Mapping[str, Any]) -> CommunityView:
    """Validate an untyped mapping into a :class:`CommunityView`.

    :param data: A mapping shaped like a ``CommunityView`` — a recorded
        fixture, a JSON payload, or an assembled row dict. Missing optional
        keys become ``None``; unknown keys are rejected.
    :returns: The validated, frozen :class:`CommunityView`.
    :raises pydantic.ValidationError: on a shape or constraint violation.
    """
    return _COMMUNITY_ADAPTER.validate_python(data)


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
    "ClassPhiReadingView",
    "CommunityOverlap",
    "CommunityView",
    "ConsciousnessSimplex",
    "CountyView",
    "DepartmentComposition",
    "DialecticalRegimeView",
    "EconomyView",
    "FactionalComposition",
    "FactionTerritoryInfluence",
    "FactionView",
    "FieldStateEdgeView",
    "FieldStateNodeView",
    "FieldStateView",
    "IndustryView",
    "InstitutionView",
    "KeyFigureView",
    "NationalTrendView",
    "NationalView",
    "OrganizationView",
    "PrincipalFieldView",
    "ProjectionRecord",
    "SocialClassView",
    "SovereignView",
    "StateView",
    "hydrate_community",
    "hydrate_county",
    "hydrate_economy",
    "hydrate_faction",
    "hydrate_field_state",
    "hydrate_industry",
    "hydrate_institution",
    "hydrate_key_figure",
    "hydrate_national",
    "hydrate_organization",
    "hydrate_record",
    "hydrate_social_class",
    "hydrate_sovereign",
    "hydrate_state",
]
