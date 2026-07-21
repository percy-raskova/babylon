"""Sandboxed deterministic social-class-page rendering (Constitution III.13).

Mirrors :mod:`babylon.projection.vault.render`'s statblock/absence-resolution
discipline for :class:`~babylon.projection.view_models.SocialClassView`, kept
in its own module rather than appended to ``render.py`` (Program 24 P2 Lane P
WO-23) — this keeps the WO collision-free against sibling Lane P work orders
that also add a ``render_<kind>`` function. The sandboxed-environment
construction itself is NOT duplicated: :func:`~babylon.projection.vault.
render._build_environment` builds one generic ``ImmutableSandboxedEnvironment``
pointed at the shared ``vault/templates/`` package directory (every kind's
template lives there), so there is exactly one environment factory for the
whole vault (ADR099: construction is code, never data) and this module
reuses it rather than re-declaring it.

See :mod:`babylon.projection.vault.render` for the absence-vs-``None``
rendering discipline this module follows identically: a present-but-``None``
field is a different case from a genuinely-missing template name, so this
module walks the view once and hands the template only precomputed,
already-``str`` statblock rows and absence entries.
"""

from __future__ import annotations

from typing import Final

from babylon.projection.vault.render import _build_environment
from babylon.projection.view_models import ClassComposition, ConsciousnessSimplex, SocialClassView

#: SocialClassView fields that are always present (identity/provenance) —
#: every other declared field is walked for statblock/absence resolution.
_IDENTITY_FIELDS: Final[frozenset[str]] = frozenset({"kind", "class_id", "verified_tick"})

#: Remedy verb for each optional SocialClassView field, in the "Verb(Noun)
#: to <goal>" register the spike established for {absence} blocks (see
#: ``render.py``'s ``_REMEDY_BY_FIELD``). Keyed by the exact SocialClassView
#: field name so a field added without a remedy entry fails loudly in
#: :func:`_absent_fields` rather than silently rendering no block.
_REMEDY_BY_FIELD: Final[dict[str, str]] = {
    "role": "Survey(SocialClass) to attribute a role",
    "county_fips": "Attribute(SocialClass) to a county",
    "population": "Survey(SocialClass) to attribute block size",
    "wealth": "Assess(LaborMarket) to attribute wealth",
    "organization": "Assess(Organization) to attribute cohesion",
    "repression_faced": "Observe(Repression) to attribute state violence",
    "p_acquiescence": "Assess(SurvivalCalculus) to attribute P(S|A)",
    "p_revolution": "Assess(SurvivalCalculus) to attribute P(S|R)",
    "consciousness": "Poll(Consciousness) to attribute the ternary simplex",
    "county_class_composition": "Census(Territory) to attribute the county's class shares",
}


def _optional_field_names() -> tuple[str, ...]:
    """Return SocialClassView's optional (non-identity) field names, in declared order.

    :returns: field names in :class:`~babylon.projection.view_models.
        SocialClassView` declaration order, excluding the always-present
        identity fields.
    """
    return tuple(name for name in SocialClassView.model_fields if name not in _IDENTITY_FIELDS)


def _statblock_rows(view: SocialClassView) -> tuple[tuple[str, str], ...]:
    """Resolve every present field of ``view`` into a formatted statblock row.

    Composite fields (:class:`ConsciousnessSimplex`, :class:`ClassComposition`)
    flatten into one dotted row per sub-field; scalars format floats to six
    decimal places for a stable, deterministic textual form.

    :param view: the social-class projection to walk.
    :returns: ``(label, value)`` pairs in SocialClassView declaration order.
    """
    rows: list[tuple[str, str]] = []
    if view.role is not None:
        rows.append(("role", view.role.value))
    if view.county_fips is not None:
        rows.append(("county_fips", view.county_fips))
    if view.population is not None:
        rows.append(("population", str(view.population)))
    if view.wealth is not None:
        rows.append(("wealth", f"{view.wealth:.6f}"))
    if view.organization is not None:
        rows.append(("organization", f"{view.organization:.6f}"))
    if view.repression_faced is not None:
        rows.append(("repression_faced", f"{view.repression_faced:.6f}"))
    if view.p_acquiescence is not None:
        rows.append(("p_acquiescence", f"{view.p_acquiescence:.6f}"))
    if view.p_revolution is not None:
        rows.append(("p_revolution", f"{view.p_revolution:.6f}"))
    if view.consciousness is not None:
        for field_name in ConsciousnessSimplex.model_fields:
            value = getattr(view.consciousness, field_name)
            rows.append((f"consciousness.{field_name}", f"{value:.6f}"))
    if view.county_class_composition is not None:
        for field_name in ClassComposition.model_fields:
            value = getattr(view.county_class_composition, field_name)
            rows.append((f"county_class_composition.{field_name}", f"{value:.6f}"))
    return tuple(rows)


def _absent_fields(view: SocialClassView) -> tuple[tuple[str, str], ...]:
    """Resolve every ``None`` field of ``view`` into a named remedy entry.

    :param view: the social-class projection to walk.
    :returns: ``(field_name, remedy)`` pairs, one per absent optional field,
        in SocialClassView declaration order.
    :raises KeyError: if an absent field has no entry in
        :data:`_REMEDY_BY_FIELD` — a SocialClassView field added without a
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
            msg = f"no remedy text registered for absent SocialClassView field {field_name!r}"
            raise KeyError(msg) from exc
        entries.append((field_name, remedy))
    return tuple(entries)


def render_social_class(view: SocialClassView, *, verified_tick: int) -> str:
    """Render a social-class dossier page from a projection view-model.

    Pure function of ``(view, verified_tick)`` — no wall-clock, no
    randomness, no filesystem reads inside the template — so two calls with
    identical arguments yield byte-identical output (Constitution III.13's
    determinism contract).

    :param view: the social-class projection to materialize.
    :param verified_tick: the tick stamped into the page's frontmatter as
        its staleness anchor. Passed explicitly rather than read from
        ``view.verified_tick`` so the caller (the materializer) declares
        the bake tick once and unambiguously.
    :returns: the rendered Markdown page text.
    :raises jinja2.exceptions.UndefinedError: if the template references a
        field this module does not resolve (a template/model shape drift).
    """
    environment = _build_environment()
    template = environment.get_template("social_class.md.j2")
    return template.render(
        social_class=view,
        verified_tick=verified_tick,
        statblock_rows=_statblock_rows(view),
        absent_fields=_absent_fields(view),
    )


__all__ = ["render_social_class"]
