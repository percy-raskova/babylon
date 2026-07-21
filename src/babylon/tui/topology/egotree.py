"""The Levi/bipartite ego-tree renderer: fence-body parsing + text art (WO-31).

Mirrors :mod:`babylon.tui.directives`'s ``parse_paoh_body``/``render_paoh``
and ``parse_maproom_body``/``render_map_room`` split exactly: a baked vault
page carries its ego-tree in the fence body as machine-written ``key: value``
lines (III.13 — a materialized view renders from its own bytes, never a live
provider call at render time), :func:`parse_egotree_body` reads that body
back into the same :class:`~babylon.projection.topology.levi.LeviEgoTree`
shape :func:`~babylon.projection.topology.levi.levi_ego_tree` produces at
bake time, and :func:`render_egotree` turns it into deterministic
box-drawing text art (S9: an ordering, never a force-directed layout).

Body format, line-oriented, no external fixture required::

    root: settler
    side: community
    C001: patriarchal, women
    C002:

``root``/``side`` declare the tree's root and which Levi node class it sits
on; every other line is one depth-1 child (``child_id: comma,separated,
grandchildren`` — an empty right-hand side is a child with zero depth-2
fan-out, mirrored from :func:`parse_maproom_body`'s bare-region-line
convention). Children render in body order, never re-sorted here — the
baked page's own order (already sorted by the ordering provider) IS its
deterministic order (III.13), the same discipline :func:`parse_maproom_body`
documents.
"""

from __future__ import annotations

from textual.markup import escape

from babylon.projection.topology.levi import LeviEgoTree, LeviNode, LeviSide

__all__ = ["parse_egotree_body", "render_egotree"]

_VALID_SIDES: frozenset[str] = frozenset({"member", "community"})


def parse_egotree_body(body: str) -> LeviEgoTree:
    """Parse an ``{egotree}`` fence body into a :class:`LeviEgoTree`.

    :param body: the raw fenced code block content.
    :raises ValueError: if there is no ``root:`` line, no ``side:`` line, the
        side value is not ``member``/``community``, a line has no ``:``
        separator, or the parsed root/side/children fail
        :class:`~babylon.projection.topology.levi.LeviEgoTree`'s own
        validation (e.g. an empty ``root:`` value) — surfaced as a
        ``ValueError`` (``pydantic.ValidationError`` is one) so callers need
        only catch one exception type, mirroring :func:`parse_paoh_body`.
    :returns: the parsed ego-tree, children in body order.
    """
    root: str | None = None
    side: LeviSide | None = None
    children: list[LeviNode] = []
    for line in (raw.strip() for raw in body.splitlines()):
        if not line:
            continue
        key, sep, rest = line.partition(":")
        key = key.strip()
        if not sep:
            raise ValueError(f"{{egotree}} line has no ':' separator: {line!r}")
        if key == "root":
            root = rest.strip()
            continue
        if key == "side":
            candidate = rest.strip()
            if candidate not in _VALID_SIDES:
                raise ValueError(
                    f"{{egotree}} side must be 'member' or 'community', got {candidate!r}"
                )
            side = candidate  # type: ignore[assignment]
            continue
        neighbors = tuple(part.strip() for part in rest.split(",") if part.strip())
        children.append(LeviNode(node_id=key, neighbors=neighbors))
    if root is None:
        raise ValueError("{egotree} body must declare a 'root: ...' line")
    if side is None:
        raise ValueError("{egotree} body must declare a 'side: ...' line")
    return LeviEgoTree(root_id=root, root_side=side, children=tuple(children))


def render_egotree(tree: LeviEgoTree) -> str:
    """Render a depth-2 ego-tree as deterministic box-drawing text art.

    Root on its own line, each depth-1 child on a branch line, each
    depth-2 grandchild indented one further level — a fixed, statically
    bounded two-level walk (Power-of-10 rule 2: the Levi graph's own
    bipartite shape caps depth at 2, not a counter that could be raised).

    :param tree: the ego-tree to render (see
        :func:`~babylon.projection.topology.levi.levi_ego_tree` or
        :func:`parse_egotree_body`).
    :returns: markup text for a Textual ``Label`` (``markup=True``).
    """
    lines = [f"[b $accent]{escape(tree.root_id)}[/] [$text-muted]({tree.root_side})[/]"]
    total_children = len(tree.children)
    for index, child in enumerate(tree.children):
        is_last_child = index == total_children - 1
        branch = "└── " if is_last_child else "├── "
        lines.append(f"[$primary]{branch}[/][$foreground]{escape(child.node_id)}[/]")
        prefix = "    " if is_last_child else "│   "
        total_neighbors = len(child.neighbors)
        for n_index, neighbor in enumerate(child.neighbors):
            is_last_neighbor = n_index == total_neighbors - 1
            sub_branch = "└── " if is_last_neighbor else "├── "
            lines.append(f"[$panel]{prefix}{sub_branch}[/][$text-muted]{escape(neighbor)}[/]")
    return "\n".join(lines)
