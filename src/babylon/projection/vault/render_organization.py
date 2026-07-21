"""Sandboxed deterministic organization-page rendering (Constitution III.13).

Mirrors :mod:`babylon.projection.vault.render`'s county rendering exactly,
generalized to :class:`~babylon.projection.view_models.OrganizationView`.
Deliberately a SEPARATE module rather than an addition to ``render.py``
(unlike ``view_models.py``/``registry.py``/``tui/directives.py``,
``vault/render.py`` is not a declared append-only zipper file for parallel
Lane P work — see ``specs/24-archive/work-orders-p2-p4.md``'s WO-16 naming
hint, ``render_state`` "in ``vault/render.py`` (or ``vault/render_state.py``)")
so parallel per-kind page WOs never collide on the same file.

Reuses :func:`babylon.projection.vault.render._build_environment` — that
module's own docstring asserts it is "the *only* place the environment is
built"; importing it here (rather than constructing a second, independently
-drifting sandboxed environment) keeps that claim true rather than silently
falsifying it.
"""

from __future__ import annotations

from typing import Final

from babylon.projection.vault.render import _build_environment
from babylon.projection.view_models import OrganizationView

#: OrganizationView fields that are always present (identity/provenance) —
#: every other declared field is walked for statblock/absence resolution.
_IDENTITY_FIELDS: Final[frozenset[str]] = frozenset({"kind", "org_id", "verified_tick"})

#: Remedy verb for each optional OrganizationView field, in the "Verb(Noun)
#: to <goal>" register the county spike established for {absence} blocks.
#: Keyed by the exact OrganizationView field name so a field added without a
#: remedy entry fails loudly in :func:`_absent_fields` rather than silently
#: rendering no block.
_REMEDY_BY_FIELD: Final[dict[str, str]] = {
    "name": "Survey(Organization) to attribute a name",
    "org_type": "Survey(Organization) to attribute its type",
    "class_character": "Investigate(Organization) to attribute its class character",
    "legal_standing": "Survey(Organization) to attribute its legal standing",
    "budget": "Audit(Organization) to attribute its budget",
    "territory_ids": "Survey(Organization) to attribute its territorial presence",
    "headquarters_id": "Survey(Organization) to attribute its headquarters",
    "is_institution": "Survey(Organization) to attribute institutional status",
    "heat": "Investigate(Organization) to attribute state attention",
    "consciousness_tendency": "Investigate(Organization) to attribute its ideological tendency",
    "cohesion": "Investigate(Organization) to attribute internal cohesion",
    "cadre_level": "Investigate(Organization) to attribute cadre quality",
}


def _optional_field_names() -> tuple[str, ...]:
    """Return OrganizationView's optional (non-identity) field names, in declared order.

    :returns: field names in
        :class:`~babylon.projection.view_models.OrganizationView` declaration
        order, excluding the always-present identity fields.
    """
    return tuple(name for name in OrganizationView.model_fields if name not in _IDENTITY_FIELDS)


def _statblock_rows(view: OrganizationView) -> tuple[tuple[str, str], ...]:
    """Resolve every present field of ``view`` into a formatted statblock row.

    Scalars format floats to six decimal places for a stable, deterministic
    textual form; ``territory_ids`` (a tuple, possibly empty) joins as a
    comma-separated list, or the literal ``(none)`` when empty — an org with
    zero territories is a real fact, not an absence.

    :param view: the organization projection to walk.
    :returns: ``(label, value)`` pairs in OrganizationView declaration order.
    """
    rows: list[tuple[str, str]] = []
    if view.name is not None:
        rows.append(("name", view.name))
    if view.org_type is not None:
        rows.append(("org_type", str(view.org_type.value)))
    if view.class_character is not None:
        rows.append(("class_character", str(view.class_character.value)))
    if view.legal_standing is not None:
        rows.append(("legal_standing", str(view.legal_standing.value)))
    if view.budget is not None:
        rows.append(("budget", f"{view.budget:.6f}"))
    if view.territory_ids is not None:
        joined = ", ".join(view.territory_ids) if view.territory_ids else "(none)"
        rows.append(("territory_ids", joined))
    if view.headquarters_id is not None:
        rows.append(("headquarters_id", view.headquarters_id))
    if view.is_institution is not None:
        rows.append(("is_institution", str(view.is_institution)))
    if view.heat is not None:
        rows.append(("heat", f"{view.heat:.6f}"))
    if view.consciousness_tendency is not None:
        rows.append(("consciousness_tendency", str(view.consciousness_tendency.value)))
    if view.cohesion is not None:
        rows.append(("cohesion", f"{view.cohesion:.6f}"))
    if view.cadre_level is not None:
        rows.append(("cadre_level", f"{view.cadre_level:.6f}"))
    return tuple(rows)


def _absent_fields(view: OrganizationView) -> tuple[tuple[str, str], ...]:
    """Resolve every ``None`` field of ``view`` into a named remedy entry.

    :param view: the organization projection to walk.
    :returns: ``(field_name, remedy)`` pairs, one per absent optional field,
        in OrganizationView declaration order.
    :raises KeyError: if an absent field has no entry in
        :data:`_REMEDY_BY_FIELD` — an OrganizationView field added without a
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
            msg = f"no remedy text registered for absent OrganizationView field {field_name!r}"
            raise KeyError(msg) from exc
        entries.append((field_name, remedy))
    return tuple(entries)


def render_organization(view: OrganizationView, *, verified_tick: int) -> str:
    """Render an organization dossier page from a projection view-model.

    Pure function of ``(view, verified_tick)`` — no wall-clock, no
    randomness, no filesystem reads inside the template — so two calls with
    identical arguments yield byte-identical output (Constitution III.13's
    determinism contract).

    :param view: the organization projection to materialize.
    :param verified_tick: the tick stamped into the page's frontmatter as
        its staleness anchor. Passed explicitly rather than read from
        ``view.verified_tick`` so the caller (the materializer) declares
        the bake tick once and unambiguously.
    :returns: the rendered Markdown page text.
    :raises jinja2.exceptions.UndefinedError: if the template references a
        field this module does not resolve (a template/model shape drift).
    """
    environment = _build_environment()
    template = environment.get_template("organization.md.j2")
    return template.render(
        organization=view,
        verified_tick=verified_tick,
        statblock_rows=_statblock_rows(view),
        absent_fields=_absent_fields(view),
    )


__all__ = ["render_organization"]
