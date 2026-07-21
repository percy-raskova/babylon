"""Sandboxed deterministic community-page rendering (Constitution III.13).

Mirrors :mod:`babylon.projection.vault.render`'s county pipeline exactly —
same :class:`~jinja2.sandbox.ImmutableSandboxedEnvironment` construction (no
custom filters/globals/finalizers, templates loaded only from this package's
own ``templates/`` directory, :class:`~jinja2.StrictUndefined`), same
precompute-then-hand-to-template discipline for
:class:`~babylon.projection.view_models.CommunityView`'s ``Optional`` fields
(Jinja renders a defined-but-``None`` attribute as the literal text
``"None"`` rather than raising, so the template never dereferences an
``Optional`` field directly).

Lives in its own module rather than appending to ``render.py``: that
module's helper names (``_IDENTITY_FIELDS``, ``_REMEDY_BY_FIELD``,
``_optional_field_names``, ``_statblock_rows``, ``_absent_fields``,
``_build_environment``) are all County-shaped, and Program 24 P2 runs nine
Lane P WOs in parallel, each adding one entity kind — cramming every one of
them into the same file would make it a synchronization point the
shared-file-discipline table does not list, for no benefit. A dedicated
module per kind is the sanctioned alternative (WO-16 offers it explicitly:
"``render_state`` in ``vault/render.py`` (or ``vault/render_state.py``)")
and keeps this WO's diff entirely collision-free new files.

jinja2 is imported lazily (function-local), matching ``render.py``, so
importing this module never pulls jinja2 into ``sys.modules`` merely by
being on the import path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from babylon.projection.view_models import CommunityView

if TYPE_CHECKING:
    from jinja2.sandbox import ImmutableSandboxedEnvironment

#: CommunityView fields that are always present (identity/provenance) —
#: every other declared field is walked for statblock/absence resolution.
_IDENTITY_FIELDS: Final[frozenset[str]] = frozenset({"kind", "community_id", "verified_tick"})

#: Remedy text for each optional CommunityView field, in the "Verb(Noun) to
#: <goal>" register the county spike established for {absence} blocks.
#: ``formation_tick`` deliberately breaks that register — see its own
#: entry — because no verb can ever resolve it (there is no producer to
#: invoke, not merely one this run didn't attribute). Keyed by the exact
#: CommunityView field name so a field added without a remedy entry fails
#: loudly in :func:`_absent_fields` rather than silently rendering no block.
_REMEDY_BY_FIELD: Final[dict[str, str]] = {
    "roster": "Investigate(Community) to attribute a roster",
    "formation_tick": (
        "no producer exists — CommunityType is a fixed 14-member taxonomy, "
        "not a dynamically instantiated hyperedge (see CommunityView docstring)"
    ),
    "overlaps": "Investigate(Community) to attribute overlaps",
}


def _optional_field_names() -> tuple[str, ...]:
    """Return CommunityView's optional (non-identity) field names, in declared order.

    :returns: field names in :class:`~babylon.projection.view_models.CommunityView`
        declaration order, excluding the always-present identity fields.
    """
    return tuple(name for name in CommunityView.model_fields if name not in _IDENTITY_FIELDS)


def _statblock_rows(view: CommunityView) -> tuple[tuple[str, str], ...]:
    """Resolve the only scalar-shaped field a community dossier carries.

    ``roster``/``overlaps`` are collections rendered as their own wikilink
    sections in the template (design-canon S9 "backlinks = incidence"),
    never flattened into statblock rows the way ``CountyView``'s composite
    fields are — a roster of ``[[social_class/<id>]]`` links is exactly the
    thing a statblock row (plain ``key: value`` text) cannot express.

    :param view: the community projection to walk.
    :returns: a single ``("formation_tick", value)`` row when present, else
        empty — ``formation_tick`` has no producer today (see the module
        docstring), so this is empty in every real dossier currently, and
        that is a faithful, not a broken, statblock.
    """
    rows: list[tuple[str, str]] = []
    if view.formation_tick is not None:
        rows.append(("formation_tick", str(view.formation_tick)))
    return tuple(rows)


def _absent_fields(view: CommunityView) -> tuple[tuple[str, str], ...]:
    """Resolve every ``None`` field of ``view`` into a named remedy entry.

    An attributed-but-empty ``overlaps`` (``()``, not ``None``) is NOT
    absent — "computed and found none" renders via the template's own
    Overlaps section, never as a generic ``{absence}`` block.

    :param view: the community projection to walk.
    :returns: ``(field_name, remedy)`` pairs, one per ``None`` optional
        field, in CommunityView declaration order.
    :raises KeyError: if an absent field has no entry in
        :data:`_REMEDY_BY_FIELD` — a CommunityView field added without a
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
            msg = f"no remedy text registered for absent CommunityView field {field_name!r}"
            raise KeyError(msg) from exc
        entries.append((field_name, remedy))
    return tuple(entries)


def _build_environment() -> ImmutableSandboxedEnvironment:
    """Construct the vault's Jinja2 environment.

    Identical construction to :func:`babylon.projection.vault.render._build_environment`
    (ADR099: construction is code, never data) — duplicated rather than
    imported so this module has zero dependency on ``render.py``'s
    County-shaped internals; the two environments are behaviorally
    interchangeable by inspection, not by shared code.

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


def render_community(view: CommunityView, *, verified_tick: int) -> str:
    """Render a community dossier page from a projection view-model.

    Pure function of ``(view, verified_tick)`` — no wall-clock, no
    randomness, no filesystem reads inside the template — so two calls with
    identical arguments yield byte-identical output (Constitution III.13's
    determinism contract).

    :param view: the community projection to materialize.
    :param verified_tick: the tick stamped into the page's frontmatter as
        its staleness anchor. Passed explicitly rather than read from
        ``view.verified_tick`` so the caller (the materializer) declares
        the bake tick once and unambiguously.
    :returns: the rendered Markdown page text.
    :raises jinja2.exceptions.UndefinedError: if the template references a
        field this module does not resolve (a template/model shape drift).
    """
    environment = _build_environment()
    template = environment.get_template("community.md.j2")
    return template.render(
        community=view,
        verified_tick=verified_tick,
        statblock_rows=_statblock_rows(view),
        absent_fields=_absent_fields(view),
    )


__all__ = ["render_community"]
