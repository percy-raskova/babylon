"""Fenced-directive dispatch: one ``MarkdownFence`` subclass, four directives.

Textual's token walker asserts ``issubclass(fence_class, MarkdownFence)`` and
routes every fence through ``BLOCKS["fence"]``/``BLOCKS["code_block"]``, so
dispatch happens on the fence info string (``token.info``) — never via
paired container tokens, which break the 8.2.8 walker's generic close-pop
(ADR099). ``{statblock}``, ``{absence}``, ``{narrative}`` and ``{paoh}``
render as styled blocks; any other ``{directive}`` refuses to render
silently (Constitution III.11 — loud failure over a plausible default).
Ordinary fences (no ``{...}`` info string) fall through to normal syntax
highlighting.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from typing import Final, Protocol, runtime_checkable

from textual import events
from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import Label
from textual.widgets._markdown import MarkdownFence

from babylon.projection.topology.choropleth import ChoroplethCell, MapTier

DIRECTIVE_RE: Final = re.compile(r"^\{(\w+)\}\s*(.*)$")

StatblockRow = tuple[str, str]
StatblockProvider = Callable[[str], Sequence[StatblockRow] | None]
"""Looks up statblock rows for a subject id. ``None`` means "no projection
for this subject" and renders as an absence block — never a fabricated
plausible-looking default (Constitution III.11)."""


def no_statblocks(_subject: str) -> Sequence[StatblockRow] | None:
    """Default provider when the host ``Markdown`` widget wires none.

    :param _subject: the statblock subject id (unused).
    :returns: ``None``, always — callers inject a real projection-backed
        provider (see ``babylon.tui.app.BabylonMarkdown``).
    """
    return None


@runtime_checkable
class _StatblockHost(Protocol):
    """Structural type for a ``Markdown`` widget that carries a provider."""

    statblocks: StatblockProvider


class DirectiveHover(Message):
    """Posted on mouse Enter/Leave over a directive plate.

    :ivar subject: ``"{name}:{arg}"`` identifying the hovered directive.
    :ivar entered: ``True`` on Enter, ``False`` on Leave.
    """

    def __init__(self, subject: str, entered: bool) -> None:
        self.subject = subject
        self.entered = entered
        super().__init__()


def parse_paoh_body(
    body: str,
) -> tuple[tuple[str, ...], tuple[tuple[int, frozenset[str]], ...]]:
    """Parse a ``{paoh}`` fence body into nodes and tick-ordered hyperedges.

    Line-oriented body format, no external fixture required::

        nodes: uaw-600, tenants-un, mutaid-dx
        3: uaw-600, tenants-un
        9: tenants-un, mutaid-dx

    :param body: the raw fenced code block content.
    :raises ValueError: if there is no ``nodes:`` line, an edge line's tick
        is not an integer, or an edge names a node absent from ``nodes``.
    :returns: ``(nodes, edges)`` — nodes in declared order, edges sorted by
        tick ascending.
    """
    nodes: tuple[str, ...] | None = None
    edges: list[tuple[int, frozenset[str]]] = []
    for line in (raw.strip() for raw in body.splitlines()):
        if not line:
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        if key == "nodes":
            nodes = tuple(part.strip() for part in rest.split(",") if part.strip())
            continue
        try:
            tick = int(key)
        except ValueError as exc:
            raise ValueError(f"{{paoh}} line has neither 'nodes:' nor a tick: {line!r}") from exc
        members = frozenset(part.strip() for part in rest.split(",") if part.strip())
        edges.append((tick, members))
    if nodes is None:
        raise ValueError("{paoh} body must declare a 'nodes: ...' line")
    unknown = {member for _, members in edges for member in members} - set(nodes)
    if unknown:
        raise ValueError(f"{{paoh}} edge(s) reference undeclared node(s): {sorted(unknown)}")
    edges.sort(key=lambda pair: pair[0])
    return nodes, tuple(edges)


def render_paoh(nodes: Sequence[str], edges: Sequence[tuple[int, frozenset[str]]]) -> str:
    """Render a PAOH matrix: nodes as rows, hyperedges as tick-ordered columns.

    Membership dots joined by vertical connector segments spanning each
    hyperedge's row range — an ordering, not a layout; deterministic in
    node/edge order.

    :param nodes: node labels in row order.
    :param edges: ``(tick, member_names)`` pairs, already tick-sorted.
    :returns: markup text for a Textual ``Label`` (``markup=True``).
    """
    row_of = {name: row for row, name in enumerate(nodes)}
    header = " " * 11 + " ".join(f"[$foreground]t{tick:<3}[/]" for tick, _ in edges)
    spans = [
        (min(row_of[m] for m in members), max(row_of[m] for m in members)) for _, members in edges
    ]
    lines = [header]
    for row, node in enumerate(nodes):
        cells = []
        for (_, members), (lo, hi) in zip(edges, spans, strict=True):
            if node in members:
                cells.append("[b $accent]●[/]   ")
            elif lo < row < hi:
                cells.append("[$primary]│[/]   ")
            else:
                cells.append("[$panel]·[/]   ")
        lines.append(f"[$foreground]{node:<10}[/] " + "".join(cells))
    return "\n".join(lines)


def parse_maproom_body(body: str) -> tuple[MapTier, tuple[ChoroplethCell, ...]]:
    """Parse a ``{maproom}`` fence body into a tier and its choropleth cells.

    Line-oriented body format, no external fixture required (mirrors
    :func:`parse_paoh_body`)::

        tier: state
        26: 0.500000
        08:

    A bare ``<region_id>:`` line with nothing after the colon is an honest
    absence for that region (Constitution III.11) — never a fabricated 0.0.

    :param body: the raw fenced code block content.
    :raises ValueError: if there is no ``tier:`` line, the tier is not one of
        ``ea``/``state``/``county``, a line has no ``:`` separator, or a
        region line's value is present but not a valid float.
    :returns: ``(tier, cells)`` — cells in body order (a baked page's own
        order is its deterministic order, per III.13; this parser does not
        re-sort).
    """
    tier: MapTier | None = None
    cells: list[ChoroplethCell] = []
    for line in (raw.strip() for raw in body.splitlines()):
        if not line:
            continue
        key, sep, rest = line.partition(":")
        key = key.strip()
        if not sep:
            raise ValueError(f"{{maproom}} line has no ':' separator: {line!r}")
        if key == "tier":
            candidate = rest.strip()
            if candidate == "ea":
                tier = "ea"
            elif candidate == "state":
                tier = "state"
            elif candidate == "county":
                tier = "county"
            else:
                raise ValueError(f"{{maproom}} tier must be ea/state/county, got {candidate!r}")
            continue
        value_text = rest.strip()
        if not value_text:
            cells.append(ChoroplethCell(region_id=key))
            continue
        try:
            value = float(value_text)
        except ValueError as exc:
            raise ValueError(
                f"{{maproom}} region {key!r} has a non-numeric value: {value_text!r}"
            ) from exc
        cells.append(ChoroplethCell(region_id=key, exploitation_rate=value))
    if tier is None:
        raise ValueError("{maproom} body must declare a 'tier: ...' line")
    return tier, tuple(cells)


class BabylonFence(MarkdownFence):
    """Dispatch on the fence info string: ``'{name} args'`` -> a directive;
    anything else still syntax-highlights as an ordinary code fence."""

    def _directive(self) -> tuple[str, str] | None:
        match = DIRECTIVE_RE.match((self.lexer or "").strip())
        if match is None:
            return None
        return match.group(1), match.group(2).strip()

    def compose(self) -> ComposeResult:
        directive = self._directive()
        if directive is None:
            yield from super().compose()  # ordinary fences still highlight
            return
        name, arg = directive
        method = getattr(self, f"_directive_{name}", None)
        if method is None:
            # Loud failure, never a plausible default (Constitution III.11).
            yield Label(
                f"▌ UNKNOWN DIRECTIVE {{{name}}} — refusing to render silently",
                classes="absence",
            )
            return
        yield from method(arg)

    def _directive_statblock(self, arg: str) -> ComposeResult:
        rows: Sequence[StatblockRow] | None
        body = self.code.strip()
        if body:
            # A BAKED page carries its numbers in the fence body (III.13: a
            # materialized view renders from its own bytes, never a live
            # provider). Body lines are machine-written ``key: value`` pairs;
            # anything else means a corrupt page — refuse loudly.
            parsed: list[StatblockRow] = []
            for line in body.splitlines():
                key, sep, value = line.partition(":")
                if not sep or not key.strip():
                    yield Label(
                        f"▌ MALFORMED STATBLOCK BODY in {arg} — refusing to render",
                        classes="absence",
                    )
                    return
                parsed.append((key.strip(), value.strip()))
            rows = parsed
        else:
            # A LIVE page's empty statblock defers to the host's projection
            # provider by subject id.
            host = self._markdown
            provider = host.statblocks if isinstance(host, _StatblockHost) else no_statblocks
            rows = provider(arg)
        if rows is None:
            yield Label(f"▌ no statblock projection for {arg}", classes="absence")
            return
        lines = [f"[b $accent]{arg}[/]"]
        lines += [f"[$text-muted]{key:<20}[/] [$foreground]{val}[/]" for key, val in rows]
        yield Label("\n".join(lines), classes="statblock", markup=True)

    def _directive_absence(self, arg: str) -> ComposeResult:
        body = self.code.strip() or arg
        yield Label(f"▌ ABSENT — {body}", classes="absence", markup=False)

    def _directive_narrative(self, arg: str) -> ComposeResult:
        body = self.code.strip()
        yield Label(
            f"[i $foreground]{body}[/]\n[$text-muted]— the Narrator ({arg})[/]",
            classes="narrative",
            markup=True,
        )

    def _directive_paoh(self, _arg: str) -> ComposeResult:
        try:
            nodes, edges = parse_paoh_body(self.code)
        except ValueError as exc:
            yield Label(f"▌ ABSENT — {{paoh}} {exc}", classes="absence")
            return
        yield Label(render_paoh(nodes, edges), classes="paoh", markup=True)

    def _directive_maproom(self, _arg: str) -> ComposeResult:
        try:
            tier, cells = parse_maproom_body(self.code)
        except ValueError as exc:
            yield Label(f"▌ ABSENT — {{maproom}} {exc}", classes="absence")
            return
        if not cells:
            yield Label(f"▌ no choropleth cells for tier {tier!r}", classes="absence")
            return
        # Always the cell-art floor (ADR097 Tier 0, the design target, never
        # a fallback): no capability flag reaches the fenced-directive
        # dispatch yet — ADR097 D4's babylon-doctor probe/config plumbing is
        # separate, future work (babylon.tui.map_room.render_map_room takes
        # render_tier explicitly for the caller that eventually wires it).
        from babylon.tui.map_room import render_map_room

        yield render_map_room(cells, render_tier="glyph")

    # Public naming-convention handlers, not the underscore form: Textual
    # reserves `_on_<event>` for its own base-class interception (dispatch
    # checks `_{name}` before `{name}` per class in the MRO), and no base
    # defines `_on_enter`/`_on_leave` at the 8.2.8 pin — the public name is
    # the sanctioned user override point and stays collision-free if a
    # future Textual adds its own private hover bookkeeping.
    def on_enter(self, _event: events.Enter) -> None:
        directive = self._directive()
        if directive is not None:
            self.post_message(DirectiveHover(f"{directive[0]}:{directive[1]}", True))

    def on_leave(self, _event: events.Leave) -> None:
        directive = self._directive()
        if directive is not None:
            self.post_message(DirectiveHover(f"{directive[0]}:{directive[1]}", False))


__all__ = [
    "DIRECTIVE_RE",
    "StatblockRow",
    "StatblockProvider",
    "no_statblocks",
    "DirectiveHover",
    "parse_paoh_body",
    "render_paoh",
    "parse_maproom_body",
    "BabylonFence",
]
