"""``peek()`` — the Archive's single stat-plate renderer (design canon S7).

S7 (``ai/_inbox/tui/20260719archiveinterfacedesign.md``): *"A single
``peek(entity, depth)`` renderer producing a compact stat plate implements, at
different sizes: Vic3 nested tooltips, Obsidian hover preview, page
transclusion, and watchlist rows. Keyboard peek is first-class; mouse hover
works but is never load-bearing."* This module is that one renderer.

**Live-query, not baked** (contrast S3): :func:`peek` consumes a projection
view-model directly — never a rendered vault page — so it can be called on
demand from any surface (a hover, a focus move, a watchlist refresh) without
a materialization round-trip. This is the deliberate seam vault pages don't
have: pages are pre-rendered Markdown pinned to a ``verified_tick``; peek
plates are live snapshots of whatever view-model the caller currently holds.

**Depth is a size selector, not a query parameter.** ``depth`` picks one of
four fixed verbosity tiers, matching S7's four named contexts one-to-one:

.. list-table:: Depth → size mapping
   :header-rows: 1

   * - ``depth``
     - Context
     - Stat rows shown
   * - ``0``
     - watchlist row (a pinned list, many rows at once — must be terse)
     - at most 1
   * - ``1``
     - Obsidian-style hover preview (a small popup on a wikilink)
     - at most 3
   * - ``2``
     - Vic3-style nested tooltip (a drill-down, one level richer)
     - at most 6
   * - ``3``
     - page transclusion (embeds the *whole* dossier inline)
     - every present field

``MAX_DEPTH`` (``3``) is a **hard, statically-provable bound** (Power-of-10
rule 2): :func:`peek` range-checks ``depth`` with a single comparison, no
loop, so any future caller that recurses into :func:`peek` again (e.g. a
Vic3-style tooltip nested inside another tooltip, for an entity referenced by
id in the first one's fields) is bounded to at most four levels simply by
threading ``depth + 1`` through — the bound is enforced here once, not
re-derived at every call site. No such recursive resolver is wired yet (that
needs an id → view-model lookup this module deliberately does not own); the
bound is adopted now so it is never retrofitted under time pressure later.

**Dispatch on ``.kind`` is structural, not a lookup table.** Every
:data:`~babylon.projection.view_models.ProjectionRecord` kind is a frozen
Pydantic model carrying a ``kind`` discriminator and (by the keel convention
:class:`~babylon.projection.county.project_county`'s ``CountyView``
establishes) a ``verified_tick`` staleness stamp plus its own identity field
named ``f"{kind}_fips"`` or ``f"{kind}_id"``. :func:`peek` reads those
conventions off ``type(entity_view).model_fields`` at call time — there is no
``if kind == "county": ...`` branch and no per-kind registry to maintain, so
a new Lane P kind (state, organization, sovereign, ...) landing in
``ProjectionRecord`` via the additive zipper on ``view_models.py`` needs
**zero changes here**. A kind whose identity field doesn't match the
convention still renders — the header degrades to the bare kind name rather
than guessing or raising, and every field is still walked and shown; this is
a graceful degrade, not a silent fabrication (Constitution III.11: the
identity is honestly incomplete, not wrong).

**Absence renders loud, never blank** (III.11): a view-model with no
populated optional field (an unattributed entity) does not produce an empty
plate — it produces a single explicit "no attributed data" marker line, the
same ``▌`` convention :mod:`babylon.tui.directives` uses for absence blocks.

**Keyboard-first; mouse hover supported, never load-bearing** (S7): this
module has no widget or event-binding code by design — :func:`peek` is a
pure ``(view, depth) -> RenderableType`` function. Whether a caller invokes
it from a keyboard focus-move (the primary path) or a mouse ``Enter`` event
(secondary, optional) is entirely the caller's concern; the renderer itself
is transport-neutral with respect to *why* it was called, exactly as it is
transport-neutral with respect to *which* kind it was called for.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel
from rich import box
from rich.console import RenderableType
from rich.panel import Panel
from rich.text import Text

from babylon.projection.view_models import ProjectionRecord
from babylon.tui.theme import BONE, CRIMSON, DIM, GOLD

__all__ = ["MAX_DEPTH", "peek"]

MAX_DEPTH: Final[int] = 3
"""The hard upper bound on ``depth`` — see the module docstring's depth table."""

_FIELD_CAP_BY_DEPTH: Final[tuple[int | None, ...]] = (1, 3, 6, None)
"""Stat rows shown at each depth ``0..MAX_DEPTH``; ``None`` means uncapped.
Indexed directly by ``depth`` — its length is :data:`MAX_DEPTH` ``+ 1``."""

_IDENTITY_SUFFIXES: Final[tuple[str, ...]] = ("_fips", "_id")
"""Suffixes tried, in order, against the view's own ``kind`` to find its
identity field — mirrors ``CountyView.county_fips`` (``"county" + "_fips"``)."""

_UNIVERSAL_FIELDS: Final[frozenset[str]] = frozenset({"kind", "verified_tick"})
"""Fields every ``ProjectionRecord`` kind carries by the keel convention
(mirrors ``CountyView``) and that :func:`peek` folds into the header instead
of walking as stat rows."""


def _identity_field_name(view: BaseModel) -> str | None:
    """Find ``view``'s own identity field by the ``{kind}_fips``/``{kind}_id`` convention.

    :param view: any projection view-model carrying a ``kind`` field.
    :returns: the matching field name declared on ``type(view)``, or ``None``
        if ``view`` has no ``kind`` field or no field matches either
        convention — a graceful "no known identity field" answer, never a
        guess.
    """
    kind = getattr(view, "kind", None)
    if not isinstance(kind, str):
        return None
    fields = type(view).model_fields
    for suffix in _IDENTITY_SUFFIXES:
        candidate = f"{kind}{suffix}"
        if candidate in fields:
            return candidate
    return None


def _header(view: BaseModel) -> str:
    """Build the plate header: ``"{kind}/{identity} @ T{tick:04d}"``.

    Degrades field-by-field when a piece is missing: no matching identity
    field yields ``"{kind} @ T{tick:04d}"``; no ``verified_tick`` yields just
    the identity part. Never raises — a header is always producible from a
    ``kind``-bearing model, even one this module has never seen before.

    :param view: any projection view-model carrying a ``kind`` field.
    :returns: the header string.
    """
    kind = getattr(view, "kind", None)
    label = kind if isinstance(kind, str) else type(view).__name__

    identity_name = _identity_field_name(view)
    if identity_name is not None:
        identity_value = getattr(view, identity_name, None)
        if identity_value is not None:
            label = f"{label}/{identity_value}"

    tick = getattr(view, "verified_tick", None)
    if isinstance(tick, int):
        return f"{label} @ T{tick:04d}"
    return label


def _format_scalar(value: object) -> str:
    """Format one leaf value for display: floats to six decimals, else ``str``.

    Mirrors :func:`babylon.projection.vault.render._statblock_rows`'s
    formatting so a peek row and a baked statblock row read identically for
    the same underlying value.

    :param value: the field value to format (never ``None`` — callers only
        pass present values).
    :returns: the formatted string.
    """
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _format_field(name: str, value: object) -> list[tuple[str, str]]:
    """Resolve one field into zero, one, or several ``(label, value)`` rows.

    A ``None`` value contributes nothing (absence is handled once, at the
    plate level, not per field). A nested :class:`~pydantic.BaseModel`
    (``ClassComposition``, ``ConsciousnessSimplex``, and any future composite
    field of the same shape) flattens into one dotted row per present
    sub-field, generically over ``type(value).model_fields`` — no per-model
    branch. Anything else is one scalar row.

    :param name: the field's declared name on the parent view.
    :param value: the field's current value.
    :returns: zero or more ``(label, formatted_value)`` pairs.
    """
    if value is None:
        return []
    if isinstance(value, BaseModel):
        return [
            (f"{name}.{sub_name}", _format_scalar(sub_value))
            for sub_name in type(value).model_fields
            if (sub_value := getattr(value, sub_name, None)) is not None
        ]
    return [(name, _format_scalar(value))]


def _stat_rows(view: BaseModel) -> tuple[tuple[str, str], ...]:
    """Walk every non-identity field of ``view`` into ordered stat rows.

    Field order follows ``type(view).model_fields`` declaration order, so the
    same view always yields the same row sequence (determinism, matching
    :func:`babylon.projection.vault.render._statblock_rows`'s contract).

    :param view: any projection view-model carrying a ``kind`` field.
    :returns: ``(label, value)`` pairs for every present, non-identity field.
    """
    identity_name = _identity_field_name(view)
    skip = _UNIVERSAL_FIELDS | ({identity_name} if identity_name is not None else set())
    rows: list[tuple[str, str]] = []
    for name in type(view).model_fields:
        if name in skip:
            continue
        rows.extend(_format_field(name, getattr(view, name, None)))
    return tuple(rows)


def _absence_text(header: str) -> Text:
    """The honest-absence marker shown when a view has no populated field.

    :param header: the plate's header string, so the absence line still
        names what was looked up (never a bare, unattributable "nothing").
    :returns: a styled single-line :class:`~rich.text.Text`.
    """
    return Text(f"▌ {header} — no attributed data", style=f"bold {CRIMSON}")


def _watchlist_row(header: str, rows: tuple[tuple[str, str], ...]) -> RenderableType:
    """Build the depth-0 plate: one unadorned line, no border (S7 watchlist row).

    :param header: the plate header.
    :param rows: the (already depth-capped) stat rows; only the first is used.
    :returns: a single-line :class:`~rich.text.Text`.
    """
    if not rows:
        return _absence_text(header)
    label, value = rows[0]
    return Text(f"{header}  {label}={value}", style=BONE)


def _plate(header: str, rows: tuple[tuple[str, str], ...]) -> RenderableType:
    """Build the depth 1–3 plate: a bordered panel (§9b newt-plate chrome).

    Crimson border, square corners, gold title — the plate anatomy DESIGN_BIBLE
    §9b specifies for chrome, applied here at Rich-renderable granularity
    rather than Textual CSS (this function's output has no widget/App context
    to resolve ``$theme`` variables against).

    :param header: the plate header, rendered as the panel title.
    :param rows: the (already depth-capped) stat rows.
    :returns: a bordered :class:`~rich.panel.Panel`.
    """
    body: RenderableType
    if not rows:
        body = _absence_text(header)
    else:
        body = Text()
        for index, (label, value) in enumerate(rows):
            if index:
                body.append("\n")
            body.append(f"{label:<24}", style=DIM)
            body.append(value, style=BONE)
    return Panel(
        body,
        title=Text(header, style=f"bold {GOLD}"),
        border_style=CRIMSON,
        box=box.SQUARE,
        padding=(0, 1),
    )


def peek(entity_view: ProjectionRecord, depth: int) -> RenderableType:
    """Render a compact stat plate for ``entity_view`` at the given ``depth``.

    The single mechanism S7 calls for: the same function, called with a
    different ``depth``, produces a watchlist row, a hover preview, a nested
    tooltip, or a page-transclusion-sized plate — see the module docstring's
    depth table.

    :param entity_view: any projection view-model carrying a ``kind``
        discriminator (today, any member of
        :data:`~babylon.projection.view_models.ProjectionRecord`).
    :param depth: the size tier, ``0`` (most compact) through
        :data:`MAX_DEPTH` (most detailed).
    :raises ValueError: if ``depth`` is outside ``[0, MAX_DEPTH]`` — a single
        range check, not a loop, so the bound is trivially statically
        provable (Power-of-10 rule 2).
    :returns: a Rich renderable: a bare :class:`~rich.text.Text` line at
        ``depth == 0``, a bordered :class:`~rich.panel.Panel` otherwise.
    """
    if not 0 <= depth <= MAX_DEPTH:
        msg = f"peek() depth must be within [0, {MAX_DEPTH}], got {depth}"
        raise ValueError(msg)

    header = _header(entity_view)
    rows = _stat_rows(entity_view)
    cap = _FIELD_CAP_BY_DEPTH[depth]
    if cap is not None:
        rows = rows[:cap]

    if depth == 0:
        return _watchlist_row(header, rows)
    return _plate(header, rows)
