"""The verb plate — the nine Article V verbs, one projection (WO-26).

S6 (``ai/_inbox/tui/20260719archiveinterfacedesign.md``): *"Select a target
(node, edge, page) -> a newt-style plate renders which of the nine Article V
verbs are legal for that target type, gated by the org's OODA capacity this
tick, costs shown, everything derived from the verb registry + GameDefines.
Confirmation shows a deterministic consequence preview where computable
(VII.8 feedforward). Investigate's three sub-verbs surface faithfully."*
This module is that rendering.

**Fixture-fed here; live-wired at WO-38.** :func:`render_verb_plate` takes a
:class:`~babylon.projection.verbs.view_models.VerbPlateView` — however it was
built. The live provider is
:func:`babylon.projection.verbs.plate.build_verb_plate` (already landed);
this widget never imports the graph, the engine, or a database, matching
:mod:`babylon.tui.peek`'s live-query-surface pattern: a pure
``(view) -> RenderableType`` function, no Textual widget class, no App
composition owned here.

**Eligibility gates the row; affordability never hides one.** Per the
plate-provider's own contract (``build_verb_plate``'s docstring): "the UI
disables on ``eligible`` only, never on ``can_afford``." An ineligible verb
renders its player-facing reason inline — *never* omitted or greyed into
silence (Constitution III.11 / spec-116 FR-4.8); an eligible-but-unaffordable
verb still renders as legal, with the affordability note riding along
honestly.

**Investigate's three sub-verbs surface faithfully, not collapsed.**
Constitution Article V: *"Investigate has three target types, each a
distinct sub-verb preserving atomicity: Investigate(Territory) ...
Investigate(Org) ... Investigate(Edge) ... Each sub-verb is atomic. The
player selects the target type; the engine resolves the appropriate
sub-verb."* The plate renders all three named affordances under INVESTIGATE
rather than one generic button. The view-model does not yet carry
independent eligibility/cost/preview *per sub-verb* — Lane E's INVESTIGATE
wiring (WO-40) landed the territory/org write+read side of intel; no
edge-investigate resolver exists yet (``babylon.engine.actions.investigate``
reveals node attributes by node type, not edge attributes). Until a
per-sub-verb split lands, every sub-verb line here inherits the parent
INVESTIGATE row's one eligibility/cost/preview signal — an honest
description of what is computed today, never a fabricated three-way split
(Constitution III.11).

**Structured verbs only — no free text, no direct graph mutation (R4).**
This module renders exactly the nine canonical verbs (plus Investigate's
three named sub-verbs) the plate provider enumerates; it has no free-text
input surface and performs no graph write of any kind — selection and
submission are a caller's concern (:mod:`babylon.projection.verbs.submit`),
kept entirely out of this rendering layer.
"""

from __future__ import annotations

from typing import Final

from rich import box
from rich.console import RenderableType
from rich.panel import Panel
from rich.text import Text

from babylon.projection.verbs.preview import VERB_TO_ACTION_TYPE
from babylon.projection.verbs.view_models import VerbPlateView, VerbRow
from babylon.tui.theme import BONE, CRIMSON, DIM, GOLD

__all__ = ["INVESTIGATE_SUB_VERBS", "render_verb_plate"]

INVESTIGATE_SUB_VERBS: Final[tuple[str, ...]] = ("Territory", "Org", "Edge")
"""Investigate's three sub-verbs, in Constitution Article V's own order.
Each renders as its own named line (``"Investigate(Territory)"`` etc.) —
never collapsed into a single generic ``"Investigate"`` row (S6)."""

_LABEL_WIDTH: Final[int] = 24
"""Column width for the verb/sub-verb label — wide enough for the longest
label, ``"Investigate(Territory)"`` (22 chars), plus a one-space margin."""


def _status_text(row: VerbRow) -> Text:
    """The eligibility/affordability fragment for one verb row.

    :param row: the verb's plate row.
    :returns: ``"[bold red]x reason"`` when ineligible (the reason always
        shown, never hidden — spec-116 FR-4.8); otherwise ``"[gold]legal"``,
        with an affordability note appended when the org cannot currently
        pay (still rendered as legal — eligibility alone gates the row).
    """
    if not row.eligible:
        return Text(f"✗ {row.reason}", style=CRIMSON)
    text = Text("✓ legal", style=GOLD)
    if not row.can_afford:
        text.append(f"  · {row.afford_note}", style=DIM)
    return text


def _preview_text(row: VerbRow) -> Text | None:
    """The deterministic consequence-preview line (VII.8 feedforward).

    :param row: the verb's plate row.
    :returns: ``None`` when the row carries no preview (an honest absence,
        never fabricated); otherwise a dim line naming the estimated
        consciousness delta, heat delta, success probability, AP cost, and
        any player-facing warnings.
    """
    preview = row.preview
    if preview is None:
        return None
    text = Text(
        f"CI{preview.estimated_consciousness_delta:+.4f}  "
        f"heat{preview.estimated_heat_delta:+.4f}  "
        f"p={preview.success_probability:.2f}  "
        f"cost={preview.action_point_cost:g} AP",
        style=DIM,
    )
    if preview.warnings:
        text.append("  " + "; ".join(preview.warnings), style=CRIMSON)
    return text


def _verb_line(label: str, row: VerbRow) -> Text:
    """One row's full display: the label, its status, and its preview.

    :param label: the display label (a canonical verb's capitalized name, or
        one of the three ``"Investigate(...)"`` sub-verb labels).
    :param row: the verb's plate row (shared across all of INVESTIGATE's
        sub-verb lines — see the module docstring's honesty note).
    :returns: a two-line :class:`~rich.text.Text` (one, if the row carries
        no preview): the label + status, then the indented preview.
    """
    line = Text(f"{label:<{_LABEL_WIDTH}}", style=BONE if row.eligible else DIM)
    line.append_text(_status_text(row))
    preview = _preview_text(row)
    if preview is not None:
        line.append("\n    ")
        line.append_text(preview)
    return line


def _missing_verb_line(verb: str) -> Text:
    """Loud refusal for a canonical verb absent from the plate view.

    Article V: all nine verbs are "always available" — a missing row is a
    caller bug (a malformed or truncated view-model), never silently
    dropped (Constitution III.11).

    :param verb: the canonical verb name absent from ``view.verbs``.
    :returns: a bold-crimson absence marker naming the missing verb.
    """
    return Text(f"▌ {verb} — missing from plate view", style=f"bold {CRIMSON}")


def render_verb_plate(view: VerbPlateView) -> RenderableType:
    """Render the nine-verb plate, Investigate expanded to its three sub-verbs.

    :param view: the plate view-model — fixture-fed here (WO-26); the live
        provider is :func:`babylon.projection.verbs.plate.build_verb_plate`
        (WO-38).
    :returns: a bordered Rich panel (§9b newt-plate chrome: crimson border,
        gold title, square corners) with one line per canonical verb, three
        for INVESTIGATE, in Article V's canonical order.
    """
    by_verb = {row.verb: row for row in view.verbs}
    body = Text()
    first = True
    for verb in VERB_TO_ACTION_TYPE:
        row = by_verb.get(verb)
        if verb == "investigate" and row is not None:
            entries: list[tuple[str, VerbRow | None]] = [
                (f"Investigate({sub})", row) for sub in INVESTIGATE_SUB_VERBS
            ]
        else:
            entries = [(verb.capitalize(), row)]
        for label, entry_row in entries:
            if not first:
                body.append("\n")
            first = False
            if entry_row is None:
                body.append_text(_missing_verb_line(verb))
            else:
                body.append_text(_verb_line(label, entry_row))
    header = f"{view.org_id} — verb plate @ T{view.tick:04d}"
    return Panel(
        body,
        title=Text(header, style=f"bold {GOLD}"),
        border_style=CRIMSON,
        box=box.SQUARE,
        padding=(0, 1),
    )
