"""Doctrine-capability gate for parameterised verb sub-modes (P25 U11, ADR137).

The reformist fork (``ai/_inbox/P25-U11-DOCTRINE-FORK-DESIGN.md`` §3.2) does not
give every organization every electoral tactic. A stance node in the Doctrine
Tree carries a :class:`~babylon.models.entities.doctrine.DoctrineCapability`
declaring which verb sub-modes it unlocks (``verb_modes``) and which edge types
it may mint (``edge_types``). A resolver asked for a sub-mode the acting org has
not *acquired* refuses **loudly** (Constitution III.11) rather than silently
falling back to the classic path — a silent fallback would let an org that never
took a line still run a ballot campaign, which is exactly the "green test over a
dead feature" failure this codebase gates against.

The gate is deliberately data-driven: nothing here enumerates stance ids. Adding
a stance to ``doctrine_tree_mvp.json`` with a ``capabilities`` block is the only
step needed to grant a tactic.

See Also:
    :func:`babylon.engine.actions.campaign.resolve_campaign`: Campaign(Election).
    :func:`babylon.engine.actions.negotiate.resolve_negotiate`: Negotiate(Coalition).
    :func:`babylon.engine.actions.mobilize.resolve_mobilize`: Mobilize(Canvass).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from babylon.models.entities.doctrine import DoctrineCapability


def acquired_capabilities(org_attrs: dict[str, Any]) -> tuple[DoctrineCapability, ...]:
    """Return the capability blocks of every doctrine node the org has acquired.

    :param org_attrs: Acting organization's node attributes (read for
        ``acquired_doctrine_ids``).
    :returns: Capability blocks in acquisition order; empty when the org has
        acquired nothing (or nothing it acquired declares capabilities).
    """
    acquired = tuple(org_attrs.get("acquired_doctrine_ids", ()))
    if not acquired:
        return ()

    # Lazy import: only capability-gated sub-verbs pay the tree load, matching
    # the EDUCATE(Doctrine) precedent and keeping the resolver import graph flat.
    from babylon.domain.doctrine import load_doctrine_tree

    tree = load_doctrine_tree()
    # Bounded by the acquired list, which is itself bounded by the tree's node
    # count -- a finite, data-declared collection (Power-of-10 rule 2).
    blocks = [tree.nodes[node_id].capabilities for node_id in acquired if node_id in tree.nodes]
    return tuple(blocks)


def grants_verb_mode(org_attrs: dict[str, Any], mode: str) -> bool:
    """Whether any acquired stance unlocks ``mode`` (e.g. ``campaign:election:run``).

    :param org_attrs: Acting organization's node attributes.
    :param mode: Fully-qualified sub-mode key as declared in the tree.
    :returns: ``True`` when at least one acquired stance lists ``mode``.
    """
    return any(mode in block.verb_modes for block in acquired_capabilities(org_attrs))


def grants_edge_type(org_attrs: dict[str, Any], edge_type: str) -> bool:
    """Whether any acquired stance authorises minting ``edge_type``.

    :param org_attrs: Acting organization's node attributes.
    :param edge_type: Edge-type value (e.g. ``membership``).
    :returns: ``True`` when at least one acquired stance lists ``edge_type``.
    """
    return any(edge_type in block.edge_types for block in acquired_capabilities(org_attrs))


def decouples_cadre_valve(org_attrs: dict[str, Any]) -> bool:
    """Whether an acquired stance decouples cadre from officeholding.

    Principled abstention (``abstention_boycott``) is the only stance that sets
    this today: an org that refuses to seat its cadre in a bourgeois assembly
    cannot be captured by the office it does not hold. It is the counterweight
    to that stance's sect-isolation cost.

    :param org_attrs: Acting organization's node attributes.
    :returns: ``True`` when officeholder capture must not accrue.
    """
    return any(block.cadre_valve_decouple for block in acquired_capabilities(org_attrs))


__all__ = [
    "acquired_capabilities",
    "decouples_cadre_valve",
    "grants_edge_type",
    "grants_verb_mode",
]
