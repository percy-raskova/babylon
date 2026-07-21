"""Incidence/adjacency matrix cell-art grid renderer (WO-32, Lane T).

Renders the two frozen Pydantic grids from
:mod:`babylon.projection.topology.incidence` as monospace markup text — the
cell-art idiom :func:`~babylon.tui.directives.render_paoh` already
established for PAOH (a fixed-width grid of glyphs, not a Rich/Textual
``Table`` or a force-directed layout; S9: "needs an ordering, not a layout").
Design canon S9 + Constitution I.21: the grid exists to make **centrality**
(a row/column with many marks — a hub), **singletons** (a row/column with
none), and **cutsets** (a hyperedge column whose removal would fragment the
adjacency graph) visible to a human eye. This module computes none of those
three classifications — it draws the raw grid, faithfully, and leaves the
seeing to the reader (the WO's own "READ-ONLY, no targeting mechanics"
ruling).

Pure functions of their input matrix — no wall-clock, no randomness, no I/O
— so two calls on the same matrix produce byte-identical text (the same
determinism discipline :func:`~babylon.tui.directives.render_paoh` and
:func:`~babylon.projection.vault.render.render_county` already hold).
"""

from __future__ import annotations

from textual.markup import escape

from babylon.projection.topology.incidence import AdjacencyMatrix, IncidenceMatrix

__all__ = ["render_incidence_matrix", "render_adjacency_matrix"]

_PRESENT = "●"
_ABSENT = "·"
_DIAGONAL = "—"


def _column_width(labels: tuple[str, ...]) -> int:
    """The fixed cell width every column shares: the longest label, +1 gap.

    :param labels: The column header labels.
    :returns: ``1`` for an empty ``labels`` (a matrix with zero columns still
        needs a defined, if unused, width) — otherwise ``max(len) + 1``.
    """
    if not labels:
        return 1
    return max(len(label) for label in labels) + 1


def _header_row(row_label_width: int, col_labels: tuple[str, ...], col_width: int) -> str:
    """Build the column-header line, labels escaped (III.11-adjacent hygiene:
    dynamic ids can carry bracket characters that would otherwise parse as
    stray Textual markup — see ``directives.py``'s own statblock-escaping
    note)."""
    header = " " * (row_label_width + 1)
    header += "".join(f"[$foreground]{escape(label):<{col_width}}[/]" for label in col_labels)
    return header


def render_incidence_matrix(matrix: IncidenceMatrix) -> str:
    """Render a node x hyperedge incidence grid as cell-art markup text.

    :param matrix: The incidence grid (:mod:`babylon.projection.topology.
        incidence`'s deterministic ordering provider, or the identical shape
        parsed straight from a baked ``{matrix}`` fence body).
    :returns: Markup text for a Textual ``Label(markup=True)`` — a header row
        of hyperedge names, then one row per node with a filled dot
        (``●``) where the node is a member of that column's hyperedge, a
        hollow dot (``·``) otherwise. Renders as a single header line
        followed by ``"no incidence data"`` when :attr:`~babylon.projection.
        topology.incidence.IncidenceMatrix.nodes` is empty (an honest empty
        grid, not fabricated cells) — callers typically prefer the
        directive's own absence block for that case, but this function stays
        total over its input.
    """
    col_labels = tuple(str(edge) for edge in matrix.hyperedges)
    col_width = _column_width(col_labels)
    row_label_width = max((len(node) for node in matrix.nodes), default=1)
    lines = [_header_row(row_label_width, col_labels, col_width)]
    if not matrix.nodes:
        lines.append("[$text-muted]no incidence data[/]")
        return "\n".join(lines)
    for node, row in zip(matrix.nodes, matrix.cells, strict=True):
        line = f"[$foreground]{escape(node):<{row_label_width}}[/] "
        for present in row:
            glyph = _PRESENT if present else _ABSENT
            style = "b $accent" if present else "$panel"
            line += f"[{style}]{glyph:<{col_width}}[/]"
        lines.append(line)
    return "\n".join(lines)


def render_adjacency_matrix(matrix: AdjacencyMatrix) -> str:
    """Render a node x node co-membership adjacency grid as cell-art markup text.

    :param matrix: The adjacency grid (:mod:`babylon.projection.topology.
        incidence`'s ordering provider, or the identical shape parsed from a
        baked ``{matrix}`` fence body).
    :returns: Markup text: a header row of node names, then one row per node
        — a filled dot for an adjacent pair, a hollow dot for a non-adjacent
        pair, and an em-dash (``—``) on the diagonal (self-adjacency is not
        a meaningful quantity, distinct from "not adjacent" — never rendered
        as a false ``·``). ``"no adjacency data"`` when :attr:`~babylon.
        projection.topology.incidence.AdjacencyMatrix.nodes` is empty.
    """
    col_labels = matrix.nodes
    col_width = _column_width(col_labels)
    row_label_width = max((len(node) for node in matrix.nodes), default=1)
    lines = [_header_row(row_label_width, col_labels, col_width)]
    if not matrix.nodes:
        lines.append("[$text-muted]no adjacency data[/]")
        return "\n".join(lines)
    for row_index, (node, row) in enumerate(zip(matrix.nodes, matrix.cells, strict=True)):
        line = f"[$foreground]{escape(node):<{row_label_width}}[/] "
        for col_index, adjacent in enumerate(row):
            if row_index == col_index:
                glyph, style = _DIAGONAL, "$text-muted"
            elif adjacent:
                glyph, style = _PRESENT, "b $accent"
            else:
                glyph, style = _ABSENT, "$panel"
            line += f"[{style}]{glyph:<{col_width}}[/]"
        lines.append(line)
    return "\n".join(lines)
