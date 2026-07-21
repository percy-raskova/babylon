"""Sandboxed deterministic institution-page rendering (Constitution III.13).

Sibling of :mod:`babylon.projection.vault.render` (the county renderer) for
:class:`~babylon.projection.view_models.InstitutionView` — Program 24 P2
WO-19. Reuses :func:`~babylon.projection.vault.render._build_environment`
rather than duplicating it: that module's own docstring declares itself
"the only place the environment is built" (ADR099, construction-is-code),
so every per-kind renderer imports the same factory instead of growing a
second one.

Follows the identical discipline ``render.py`` documents: a present-but-
``None`` field is different from a missing template name (Jinja's
``StrictUndefined`` only fires on the latter), so this module walks the view
once, resolving every present field to a formatted statblock row and every
absent field to a named ``{absence}`` block with remedy text, handing the
template only those precomputed, already-``str`` structures.
"""

from __future__ import annotations

from typing import Final

from babylon.projection.vault.render import _build_environment
from babylon.projection.view_models import FactionalComposition, InstitutionView

#: InstitutionView fields that are always present (identity/provenance) —
#: every other declared field is walked for statblock/absence resolution.
_IDENTITY_FIELDS: Final[frozenset[str]] = frozenset({"kind", "institution_id", "verified_tick"})

#: Remedy verb for each optional InstitutionView field, in the "Verb(Noun) to
#: <goal>" register the spike established for {absence} blocks (matches
#: ``render.py``'s ``_REMEDY_BY_FIELD``). Keyed by the exact InstitutionView
#: field name so a field added without a remedy entry fails loudly in
#: :func:`_absent_fields` rather than silently rendering no block.
_REMEDY_BY_FIELD: Final[dict[str, str]] = {
    "name": "Survey(Institution) to attribute a name",
    "apparatus_type": "Classify(Institution) to attribute its apparatus type",
    "social_function": "Classify(Institution) to attribute its social function",
    "class_inscription": "Assess(ClassStruggle) to attribute its class inscription",
    "legitimacy": "Survey(Legitimation) to attribute the legitimacy index",
    "budget": "Audit(Institution) to attribute its budget",
    "housed_org_ids": "Investigate(Institution) to attribute housed organizations",
    "territory_ids": "Investigate(Institution) to attribute its territories",
    "factional_composition": "Poll(InternalBalance) to attribute the factional weights",
}


def _optional_field_names() -> tuple[str, ...]:
    """Return InstitutionView's optional (non-identity) field names, in declared order.

    :returns: field names in :class:`~babylon.projection.view_models.
        InstitutionView` declaration order, excluding the always-present
        identity fields.
    """
    return tuple(name for name in InstitutionView.model_fields if name not in _IDENTITY_FIELDS)


def _format_id_list(ids: tuple[str, ...]) -> str:
    """Format an id tuple for a statblock row: comma-joined, or an honest "(none)".

    :param ids: The id tuple to format (already known non-``None`` — a real,
        present value, possibly empty).
    :returns: A comma-joined listing, or the literal ``"(none)"`` for an
        empty tuple — a real "houses/operates in nothing" value, never
        confusable with the absent-field case (which never reaches this
        function).
    """
    return ", ".join(ids) if ids else "(none)"


def _statblock_rows(view: InstitutionView) -> tuple[tuple[str, str], ...]:
    """Resolve every present field of ``view`` into a formatted statblock row.

    The composite :class:`~babylon.projection.view_models.FactionalComposition`
    field flattens into one dotted row per weight; scalars format floats to
    six decimal places for a stable, deterministic textual form.

    :param view: the institution projection to walk.
    :returns: ``(label, value)`` pairs in InstitutionView declaration order.
    """
    rows: list[tuple[str, str]] = []
    if view.name is not None:
        rows.append(("name", view.name))
    if view.apparatus_type is not None:
        rows.append(("apparatus_type", view.apparatus_type.value))
    if view.social_function is not None:
        rows.append(("social_function", view.social_function.value))
    if view.class_inscription is not None:
        rows.append(("class_inscription", view.class_inscription.value))
    if view.legitimacy is not None:
        rows.append(("legitimacy", f"{view.legitimacy:.6f}"))
    if view.budget is not None:
        rows.append(("budget", f"{view.budget:.6f}"))
    if view.housed_org_ids is not None:
        rows.append(("housed_org_ids", _format_id_list(view.housed_org_ids)))
    if view.territory_ids is not None:
        rows.append(("territory_ids", _format_id_list(view.territory_ids)))
    if view.factional_composition is not None:
        for field_name in FactionalComposition.model_fields:
            value = getattr(view.factional_composition, field_name)
            rows.append((f"factional_composition.{field_name}", f"{value:.6f}"))
    return tuple(rows)


def _absent_fields(view: InstitutionView) -> tuple[tuple[str, str], ...]:
    """Resolve every ``None`` field of ``view`` into a named remedy entry.

    :param view: the institution projection to walk.
    :returns: ``(field_name, remedy)`` pairs, one per absent optional field,
        in InstitutionView declaration order.
    :raises KeyError: if an absent field has no entry in
        :data:`_REMEDY_BY_FIELD` — an InstitutionView field added without a
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
            msg = f"no remedy text registered for absent InstitutionView field {field_name!r}"
            raise KeyError(msg) from exc
        entries.append((field_name, remedy))
    return tuple(entries)


def render_institution(view: InstitutionView, *, verified_tick: int) -> str:
    """Render an institution dossier page from a projection view-model.

    Pure function of ``(view, verified_tick)`` — no wall-clock, no
    randomness, no filesystem reads inside the template — so two calls with
    identical arguments yield byte-identical output (Constitution III.13's
    determinism contract).

    :param view: the institution projection to materialize.
    :param verified_tick: the tick stamped into the page's frontmatter as
        its staleness anchor. Passed explicitly rather than read from
        ``view.verified_tick`` so the caller (the materializer) declares the
        bake tick once and unambiguously.
    :returns: the rendered Markdown page text.
    :raises jinja2.exceptions.UndefinedError: if the template references a
        field this module does not resolve (a template/model shape drift).
    """
    environment = _build_environment()
    template = environment.get_template("institution.md.j2")
    return template.render(
        institution=view,
        verified_tick=verified_tick,
        statblock_rows=_statblock_rows(view),
        absent_fields=_absent_fields(view),
    )


__all__ = ["render_institution"]
