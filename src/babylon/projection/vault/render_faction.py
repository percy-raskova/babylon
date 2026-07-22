"""Sandboxed deterministic faction-page rendering (Constitution III.13).

Sibling of :mod:`babylon.projection.vault.render` (the county/sovereign
renderer) for :class:`~babylon.projection.view_models.FactionView` — T3 U4.
Reuses :func:`~babylon.projection.vault.render._build_environment` rather
than duplicating it: that module's own docstring declares itself "the only
place the environment is built" (ADR099, construction-is-code), so this
renderer imports the same factory instead of growing a second one (matching
``render_institution.py``'s precedent).

Follows the identical discipline ``render.py`` documents: a present-but-
``None`` field is different from a missing template name (Jinja's
``StrictUndefined`` only fires on the latter), so this module walks the view
once, resolving every scalar-identity field to a formatted statblock row,
every ``territory_influence`` entry to its own prose line (an INFLUENCES
reading names TWO subjects — faction and territory — which a single-subject
statblock row cannot express, matching ``render_field_state.py``'s ``edges``
precedent), and every absent field to a named ``{absence}`` block with
remedy text.
"""

from __future__ import annotations

from typing import Final

from babylon.projection.vault.render import _build_environment
from babylon.projection.view_models import FactionView

#: FactionView fields that are always present (identity/provenance) — every
#: other declared field is walked for statblock/absence resolution.
_IDENTITY_FIELDS: Final[frozenset[str]] = frozenset({"kind", "faction_id", "verified_tick"})

#: Remedy verb for each optional FactionView field, in the "Verb(Noun) to
#: <goal>" register the spike established for {absence} blocks (matches
#: ``render.py``'s ``_REMEDY_BY_FIELD``). Keyed by the exact FactionView
#: field name so a field added without a remedy entry fails loudly in
#: :func:`_absent_fields` rather than silently rendering no block.
_REMEDY_BY_FIELD: Final[dict[str, str]] = {
    "name": "Survey(Faction) to attribute a name",
    "ideology": "Classify(Faction) to attribute its ideological label",
    "colonial_stance": "Classify(Faction) to attribute its colonial stance",
    "is_settler_formation": "Investigate(Faction) to attribute settler-formation status",
    "extraction_modifier": "Audit(Faction) to attribute its extraction multiplier",
    "violence_modifier": "Audit(Faction) to attribute its violence multiplier",
    "class_reduction": "Assess(ClassStruggle) to attribute the faction's class-reduction effect",
    "metabolic_reduction": "Audit(Metabolism) to attribute the faction's metabolic effect",
    "color_hex": "Survey(Faction) to attribute a UI color",
    "founded_tick": "Investigate(Faction) to attribute the founding tick",
    "dissolved_tick": "Investigate(Faction) to attribute a dissolution tick",
    "territory_influence": "Observe(Influence) to attribute INFLUENCES-edge territory anchors",
}


def _optional_field_names() -> tuple[str, ...]:
    """Return FactionView's optional (non-identity) field names, in declared order.

    :returns: field names in :class:`~babylon.projection.view_models.FactionView`
        declaration order, excluding the always-present identity fields.
    """
    return tuple(name for name in FactionView.model_fields if name not in _IDENTITY_FIELDS)


def faction_statblock_rows(view: FactionView) -> tuple[tuple[str, str], ...]:
    """Resolve every present scalar field of ``view`` into a statblock row.

    ``territory_influence`` is deliberately excluded — it renders as its own
    prose section via :func:`_influence_rows`, matching
    ``render_field_state.py``'s ``edges`` precedent. Public (unlike
    ``render_institution.py``'s private ``_statblock_rows``) because
    :func:`babylon.projection.faction.faction_statblocks`'s live provider
    reuses it — one row-format definition serving both the baked template
    path and the live ``{statblock}`` directive path, so they can never
    drift apart.

    :param view: the faction projection to walk.
    :returns: ``(label, value)`` pairs in FactionView declaration order.
    """
    rows: list[tuple[str, str]] = []
    if view.name is not None:
        rows.append(("name", view.name))
    if view.ideology is not None:
        rows.append(("ideology", view.ideology))
    if view.colonial_stance is not None:
        rows.append(("colonial_stance", view.colonial_stance.value))
    if view.is_settler_formation is not None:
        rows.append(("is_settler_formation", str(view.is_settler_formation)))
    if view.extraction_modifier is not None:
        rows.append(("extraction_modifier", f"{view.extraction_modifier:.6f}"))
    if view.violence_modifier is not None:
        rows.append(("violence_modifier", f"{view.violence_modifier:.6f}"))
    if view.class_reduction is not None:
        rows.append(("class_reduction", f"{view.class_reduction:.6f}"))
    if view.metabolic_reduction is not None:
        rows.append(("metabolic_reduction", f"{view.metabolic_reduction:.6f}"))
    if view.color_hex is not None:
        rows.append(("color_hex", view.color_hex))
    if view.founded_tick is not None:
        rows.append(("founded_tick", str(view.founded_tick)))
    if view.dissolved_tick is not None:
        rows.append(("dissolved_tick", str(view.dissolved_tick)))
    return tuple(rows)


def _influence_rows(view: FactionView) -> tuple[str, ...]:
    """Format each ``territory_influence`` entry as its own line.

    :param view: the faction projection to walk.
    :returns: one formatted line per entry in ``territory_influence``, or
        empty when it is ``None`` or an attributed-but-empty tuple. An
        unresolved ``county_fips`` renders as the deliberate literal
        ``"n/a"`` (matching ``render_field_state.py``'s ``_edge_rows``
        convention), never the bare text ``"None"``.
    """
    if not view.territory_influence:
        return ()
    lines: list[str] = []
    for entry in view.territory_influence:
        county_fips = "n/a" if entry.county_fips is None else entry.county_fips
        lines.append(
            f"{entry.territory_id} county={county_fips} "
            f"influence_level={entry.influence_level:.6f} support_type={entry.support_type}"
        )
    return tuple(lines)


def _absent_fields(view: FactionView) -> tuple[tuple[str, str], ...]:
    """Resolve every ``None`` field of ``view`` into a named remedy entry.

    :param view: the faction projection to walk.
    :returns: ``(field_name, remedy)`` pairs, one per absent optional field,
        in FactionView declaration order.
    :raises KeyError: if an absent field has no entry in
        :data:`_REMEDY_BY_FIELD` — a FactionView field added without a
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
            msg = f"no remedy text registered for absent FactionView field {field_name!r}"
            raise KeyError(msg) from exc
        entries.append((field_name, remedy))
    return tuple(entries)


def render_faction(view: FactionView, *, verified_tick: int) -> str:
    """Render a faction dossier page from a projection view-model.

    Pure function of ``(view, verified_tick)`` — no wall-clock, no
    randomness, no filesystem reads inside the template — so two calls with
    identical arguments yield byte-identical output (Constitution III.13's
    determinism contract).

    :param view: the faction projection to materialize.
    :param verified_tick: the tick stamped into the page's frontmatter as
        its staleness anchor. Passed explicitly rather than read from
        ``view.verified_tick`` so the caller (the materializer) declares the
        bake tick once and unambiguously.
    :returns: the rendered Markdown page text.
    :raises jinja2.exceptions.UndefinedError: if the template references a
        field this module does not resolve (a template/model shape drift).
    """
    environment = _build_environment()
    template = environment.get_template("faction.md.j2")
    return template.render(
        faction=view,
        verified_tick=verified_tick,
        statblock_rows=faction_statblock_rows(view),
        influence_rows=_influence_rows(view),
        absent_fields=_absent_fields(view),
    )


__all__ = ["render_faction", "faction_statblock_rows"]
