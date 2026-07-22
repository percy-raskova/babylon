"""Sandboxed deterministic county-page rendering (Constitution III.13).

Environment construction is code, never data (ADR099): the
:class:`~jinja2.sandbox.ImmutableSandboxedEnvironment` below carries no
custom filters, globals, or finalizers, and templates are loaded from this
package's own ``templates/`` directory via a :class:`~jinja2.PackageLoader`,
which cannot be pointed outside the package (no filesystem-escape surface).
:class:`~jinja2.StrictUndefined` means a template referencing a field that
genuinely does not exist raises loudly rather than rendering silence —
Constitution III.11 extended to the vault.

A present-but-``None`` :class:`~babylon.projection.view_models.CountyView`
field is a *different* case from a missing name: Jinja renders a defined
attribute whose value is ``None`` as the literal text ``"None"`` rather than
raising, so the template never dereferences an ``Optional`` field directly.
Instead this module walks the view once, resolving every present field to a
formatted statblock row and every absent field to a named ``{absence}``
block with remedy text, and hands the template only those precomputed,
already-``str`` structures.

jinja2 is imported lazily (function-local) so importing this module — and
transitively ``babylon.projection.vault`` — never pulls jinja2 into
``sys.modules`` merely by being on the import path (package-``__init__``
contract).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from babylon.projection.view_models import (
    ClassComposition,
    ConsciousnessSimplex,
    CountyView,
    SovereignView,
)

if TYPE_CHECKING:
    from jinja2.sandbox import ImmutableSandboxedEnvironment

#: CountyView fields that are always present (identity/provenance) — every
#: other declared field is walked for statblock/absence resolution.
_IDENTITY_FIELDS: Final[frozenset[str]] = frozenset({"kind", "county_fips", "verified_tick"})

#: Remedy verb for each optional CountyView field, in the "Verb(Noun) to
#: <goal>" register the spike established for {absence} blocks. Keyed by the
#: exact CountyView field name so a field added without a remedy entry fails
#: loudly in :func:`_absent_fields` rather than silently rendering no block.
_REMEDY_BY_FIELD: Final[dict[str, str]] = {
    "population": "Survey(Territory) to attribute population",
    "class_composition": "Census(Territory) to attribute class shares",
    "median_wage": "Assess(LaborMarket) to attribute median wage",
    "imperial_rent_phi": "Audit(ImperialRent) to attribute Φ",
    "consciousness": "Poll(Consciousness) to attribute the ternary simplex",
    "legitimacy": "Survey(Legitimation) to attribute the legitimacy index",
    "p_acquiescence": "Assess(SurvivalCalculus) to attribute P(S|A)",
    "p_revolution": "Assess(SurvivalCalculus) to attribute P(S|R)",
    "bifurcation_score": "Observe(Bifurcation) to attribute the axis",
    "habitability": "Assess(Metabolism) to attribute the habitability index",
    "sovereign_id": "Claim(Sovereignty) to attribute a CLAIMS edge",
}


def _optional_field_names() -> tuple[str, ...]:
    """Return CountyView's optional (non-identity) field names, in declared order.

    :returns: field names in :class:`~babylon.projection.view_models.CountyView`
        declaration order, excluding the always-present identity fields.
    """
    return tuple(name for name in CountyView.model_fields if name not in _IDENTITY_FIELDS)


def _statblock_rows(view: CountyView) -> tuple[tuple[str, str], ...]:
    """Resolve every present field of ``view`` into a formatted statblock row.

    Composite fields (:class:`ClassComposition`, :class:`ConsciousnessSimplex`)
    flatten into one dotted row per sub-field; scalars format floats to six
    decimal places for a stable, deterministic textual form.

    :param view: the county projection to walk.
    :returns: ``(label, value)`` pairs in CountyView declaration order.
    """
    rows: list[tuple[str, str]] = []
    if view.population is not None:
        rows.append(("population", str(view.population)))
    if view.class_composition is not None:
        for field_name in ClassComposition.model_fields:
            value = getattr(view.class_composition, field_name)
            rows.append((f"class_composition.{field_name}", f"{value:.6f}"))
    if view.median_wage is not None:
        rows.append(("median_wage", f"{view.median_wage:.6f}"))
    if view.imperial_rent_phi is not None:
        rows.append(("imperial_rent_phi", f"{view.imperial_rent_phi:.6f}"))
    if view.consciousness is not None:
        for field_name in ConsciousnessSimplex.model_fields:
            value = getattr(view.consciousness, field_name)
            rows.append((f"consciousness.{field_name}", f"{value:.6f}"))
    if view.legitimacy is not None:
        rows.append(("legitimacy", f"{view.legitimacy:.6f}"))
    if view.p_acquiescence is not None:
        rows.append(("p_acquiescence", f"{view.p_acquiescence:.6f}"))
    if view.p_revolution is not None:
        rows.append(("p_revolution", f"{view.p_revolution:.6f}"))
    if view.bifurcation_score is not None:
        rows.append(("bifurcation_score", f"{view.bifurcation_score:.6f}"))
    if view.habitability is not None:
        rows.append(("habitability", f"{view.habitability:.6f}"))
    if view.sovereign_id is not None:
        rows.append(("sovereign_id", view.sovereign_id))
    return tuple(rows)


def _absent_fields(view: CountyView) -> tuple[tuple[str, str], ...]:
    """Resolve every ``None`` field of ``view`` into a named remedy entry.

    :param view: the county projection to walk.
    :returns: ``(field_name, remedy)`` pairs, one per absent optional field,
        in CountyView declaration order.
    :raises KeyError: if an absent field has no entry in
        :data:`_REMEDY_BY_FIELD` — a CountyView field added without a
        registered remedy is a loud failure, never a silently-skipped
        absence block.
    """
    entries: list[tuple[str, str]] = []
    for field_name in _optional_field_names():
        if getattr(view, field_name) is not None:
            continue
        try:
            remedy = _REMEDY_BY_FIELD[field_name]
        except KeyError as exc:
            msg = f"no remedy text registered for absent CountyView field {field_name!r}"
            raise KeyError(msg) from exc
        entries.append((field_name, remedy))
    return tuple(entries)


#: SovereignView fields that are always present (identity/provenance) — every
#: other declared field is walked for statblock/absence resolution.
_SOVEREIGN_IDENTITY_FIELDS: Final[frozenset[str]] = frozenset(
    {"kind", "sovereign_id", "verified_tick"}
)

#: Remedy verb for each optional SovereignView field, in the same
#: "Verb(Noun) to <goal>" register _REMEDY_BY_FIELD established for county.
#: Keyed by the exact SovereignView field name so a field added without a
#: remedy entry fails loudly in :func:`sovereign_absent_fields`.
_SOVEREIGN_REMEDY_BY_FIELD: Final[dict[str, str]] = {
    "name": "Identify(Sovereign) to attribute a name",
    "sovereignty_type": "Classify(Sovereign) to attribute its sovereignty type",
    "legitimacy": "Assess(Legitimacy) to attribute the sovereign's legitimacy",
    "ruling_faction_id": "Investigate(Faction) to attribute the ruling faction",
    "extraction_policy": "Audit(ExtractionPolicy) to attribute the policy",
    "capital_territory_id": "Survey(Territory) to attribute a capital",
    "capital_county_fips": "Survey(Territory) to attribute the capital's county",
    "founded_tick": "Investigate(Sovereign) to attribute the founding tick",
    "dissolved_tick": "Investigate(Sovereign) to attribute a dissolution tick",
    "claimed_county_fips": "Claim(Sovereignty) to attribute the sovereign's claims",
}


def _sovereign_optional_field_names() -> tuple[str, ...]:
    """Return SovereignView's optional (non-identity) field names, in declared order.

    :returns: field names in :class:`~babylon.projection.view_models.SovereignView`
        declaration order, excluding the always-present identity fields.
    """
    return tuple(
        name for name in SovereignView.model_fields if name not in _SOVEREIGN_IDENTITY_FIELDS
    )


def sovereign_statblock_rows(view: SovereignView) -> tuple[tuple[str, str], ...]:
    """Resolve every present field of ``view`` into a formatted statblock row.

    Public (unlike county's ``_statblock_rows``) because
    :func:`babylon.projection.sovereign.sovereign_statblocks`'s live provider
    reuses it — one row-format definition serving both the baked template
    path and the live ``{statblock}`` directive path, so they can never drift
    apart.

    :param view: the sovereign projection to walk.
    :returns: ``(label, value)`` pairs in SovereignView declaration order.
        ``claimed_county_fips`` renders as one comma-joined row (empty string
        when the sovereign claims nothing — a real, present value).
    """
    rows: list[tuple[str, str]] = []
    if view.name is not None:
        rows.append(("name", view.name))
    if view.sovereignty_type is not None:
        rows.append(("sovereignty_type", view.sovereignty_type.value))
    if view.legitimacy is not None:
        rows.append(("legitimacy", f"{view.legitimacy:.6f}"))
    if view.ruling_faction_id is not None:
        rows.append(("ruling_faction_id", view.ruling_faction_id))
    if view.extraction_policy is not None:
        rows.append(("extraction_policy", view.extraction_policy.value))
    if view.capital_territory_id is not None:
        rows.append(("capital_territory_id", view.capital_territory_id))
    if view.capital_county_fips is not None:
        rows.append(("capital_county_fips", view.capital_county_fips))
    if view.founded_tick is not None:
        rows.append(("founded_tick", str(view.founded_tick)))
    if view.dissolved_tick is not None:
        rows.append(("dissolved_tick", str(view.dissolved_tick)))
    if view.claimed_county_fips is not None:
        rows.append(("claimed_county_fips", ", ".join(view.claimed_county_fips)))
    return tuple(rows)


def sovereign_absent_fields(view: SovereignView) -> tuple[tuple[str, str], ...]:
    """Resolve every ``None`` field of ``view`` into a named remedy entry.

    :param view: the sovereign projection to walk.
    :returns: ``(field_name, remedy)`` pairs, one per absent optional field,
        in SovereignView declaration order.
    :raises KeyError: if an absent field has no entry in
        :data:`_SOVEREIGN_REMEDY_BY_FIELD` — a SovereignView field added
        without a registered remedy is a loud failure, never a
        silently-skipped absence block.
    """
    entries: list[tuple[str, str]] = []
    for field_name in _sovereign_optional_field_names():
        if getattr(view, field_name) is not None:
            continue
        try:
            remedy = _SOVEREIGN_REMEDY_BY_FIELD[field_name]
        except KeyError as exc:
            msg = f"no remedy text registered for absent SovereignView field {field_name!r}"
            raise KeyError(msg) from exc
        entries.append((field_name, remedy))
    return tuple(entries)


def _build_environment() -> ImmutableSandboxedEnvironment:
    """Construct the vault's Jinja2 environment.

    Construction is code, never data (ADR099): no custom finalize, filters,
    or globals are registered here, and this is the *only* place the
    environment is built — tests exercising StrictUndefined/sandbox
    behavior use this same factory rather than a bespoke one.

    :returns: a sandboxed environment with StrictUndefined, autoescape off
        (the output is Markdown, not HTML), and templates resolved from this
        package's ``templates/`` directory only.
    """
    from jinja2 import PackageLoader, StrictUndefined
    from jinja2.sandbox import ImmutableSandboxedEnvironment

    return ImmutableSandboxedEnvironment(
        loader=PackageLoader("babylon.projection.vault", "templates"),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )


def render_county(view: CountyView, *, verified_tick: int) -> str:
    """Render a county dossier page from a projection view-model.

    Pure function of ``(view, verified_tick)`` — no wall-clock, no
    randomness, no filesystem reads inside the template — so two calls with
    identical arguments yield byte-identical output (Constitution III.13's
    determinism contract).

    :param view: the county projection to materialize.
    :param verified_tick: the tick stamped into the page's frontmatter as
        its staleness anchor. Passed explicitly rather than read from
        ``view.verified_tick`` so the caller (the materializer) declares
        the bake tick once and unambiguously.
    :returns: the rendered Markdown page text.
    :raises jinja2.exceptions.UndefinedError: if the template references a
        field this module does not resolve (a template/model shape drift).
    """
    environment = _build_environment()
    template = environment.get_template("county.md.j2")
    return template.render(
        county=view,
        verified_tick=verified_tick,
        statblock_rows=_statblock_rows(view),
        absent_fields=_absent_fields(view),
    )


def render_sovereign(view: SovereignView, *, verified_tick: int) -> str:
    """Render a sovereign dossier page from a projection view-model.

    Pure function of ``(view, verified_tick)`` — no wall-clock, no
    randomness, no filesystem reads inside the template — so two calls with
    identical arguments yield byte-identical output (Constitution III.13's
    determinism contract).

    :param view: the sovereign projection to materialize.
    :param verified_tick: the tick stamped into the page's frontmatter as
        its staleness anchor. Passed explicitly rather than read from
        ``view.verified_tick`` so the caller (the materializer) declares
        the bake tick once and unambiguously.
    :returns: the rendered Markdown page text.
    :raises jinja2.exceptions.UndefinedError: if the template references a
        field this module does not resolve (a template/model shape drift).
    """
    environment = _build_environment()
    template = environment.get_template("sovereign.md.j2")
    return template.render(
        sovereign=view,
        verified_tick=verified_tick,
        statblock_rows=sovereign_statblock_rows(view),
        absent_fields=sovereign_absent_fields(view),
    )


__all__ = ["render_county", "render_sovereign"]
