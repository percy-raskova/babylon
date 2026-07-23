"""Shared mass-work SOLIDARITY producer (Unit 6 write side, ADR087).

ADR085 retired an org-sourced ``SOLIDARITY`` amplification READ that had no
WRITE side — no verb or system ever created an organization-sourced
``SOLIDARITY`` edge, so the branch was dead weight fed only by a fabricated
test fixture. This module is that missing write side, ratified as Path 1
(owner ruling 2026-07-19): when an organization performs a **mass-work verb**
(``EDUCATE``, ``PROPAGANDIZE``, ``PROVIDE_SERVICE`` — the consciousness-
building verbs; ``PROTEST`` stays a solidarity *consumer* via
``mobilize.py``'s ``_count_solidarity_edges``, never a producer) targeting a
``social_class`` node, it creates-or-strengthens an org -> class
``SOLIDARITY`` edge, direct-graph-write style (the ``aid.py``/``mobilize.py``
pattern — a resolver writing graph state itself, not through the five-factor
consciousness-delta machinery).

**Theory grounding** (MIM(P) organizing loop, owner-ratified 2026-07-18/19):
organized mass work materially raises a class's effective solidarity, which
routes agitation toward revolution rather than fascism
(:func:`babylon.formulas.consciousness_routing.route_agitation_to_ternary`'s
``effective_solidarity`` term, read via
:class:`~babylon.engine.systems.ideology.ConsciousnessSystem`). Acquiring
doctrine amplifies this: an org with the ``MASS_LINK`` tag (``trade_unionism``
et al., :mod:`babylon.data.game.doctrine_tree_mvp`) does the SAME mass work
more effectively --

    gain = mass_work_solidarity_gain * (1 + mass_link_weight * mass_link)

-- a CONTINUOUS amplification, not a binary gate: an org with ``MASS_LINK ==
0`` still organizes (the base ``mass_work_solidarity_gain``), doctrine makes
it organize BETTER. ``solidarity_strength`` is capped at 1.0.

See Also:
    :mod:`babylon.engine.systems.doctrine`: the per-tick decay of org-sourced
        edges (``mass_work_solidarity_decay_rate``) -- a mass link not
        renewed by work withers.
    :mod:`babylon.engine.systems.ideology`: the read side -- an
        organization-sourced ``SOLIDARITY`` edge contributes
        ``solidarity_strength`` directly (gated on
        ``negligible_transmission``, not ``class_consciousness`` -- orgs have
        none).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.models.enums import EdgeType, NodeType
from babylon.models.enums.doctrine import DoctrineTag

if TYPE_CHECKING:
    from babylon.config.defines.doctrine import DoctrineDefines
    from babylon.topology.graph import BabylonGraph

__all__ = ["apply_mass_work_solidarity"]

#: Ceiling every org-sourced SOLIDARITY edge's solidarity_strength is capped
#: at (mirrors the ceiling class_consciousness/national_identity are already
#: clamped to elsewhere in the ideology pipeline).
_MAX_SOLIDARITY_STRENGTH = 1.0


def apply_mass_work_solidarity(
    graph: BabylonGraph,
    org_id: str,
    org_attrs: dict[str, Any],
    target_id: str,
    doctrine: DoctrineDefines,
    efficiency: float = 1.0,
) -> None:
    """Create-or-strengthen an org -> class SOLIDARITY edge from mass work.

    A no-op when the target is not a ``social_class`` node (mass work only
    organizes classes; a territory or another org is not a solidarity
    target here) or when the ``(org_id, target_id)`` pair already carries a
    DIFFERENT edge type -- the graph stores one edge per node pair
    (:meth:`~babylon.topology.graph.BabylonGraph.add_edge`'s NetworkX-style
    merge semantics), so blindly adding a SOLIDARITY edge over an existing
    MEMBERSHIP/TRANSACTIONAL/etc. edge would silently clobber it. Skipping is
    the honest failure mode; clobbering would be a silent data-corruption bug.

    :param graph: World graph (mutated: the org -> target SOLIDARITY edge is
        created or its ``solidarity_strength`` is strengthened).
    :param org_id: Acting organization's node id (the edge's source).
    :param org_attrs: Acting organization's node attributes (read for
        ``doctrine_tags``).
    :param target_id: The verb's target node id (the edge's target).
    :param doctrine: DoctrineDefines coefficients (``mass_work_solidarity_gain``,
        ``mass_link_weight``).
    :param efficiency: Multiplier on the computed gain. Defaults to ``1.0`` (the
        classic mass-work base). Campaign(Election, mode=RUN) passes
        ``politics.debs_solidarity_efficiency`` — a class-struggle ballot
        campaign IS recruitment, but converts labour to solidarity below the
        base rate of direct mass work (P25 U11, ADR137).
    """
    target_node = graph.nodes.get(target_id)
    if target_node is None or target_node.get("_node_type") != NodeType.SOCIAL_CLASS.value:
        return

    doctrine_tags = org_attrs.get("doctrine_tags") or {}
    mass_link = float(doctrine_tags.get(DoctrineTag.MASS_LINK, doctrine_tags.get("mass_link", 0.0)))
    gain = (
        doctrine.mass_work_solidarity_gain
        * (1.0 + doctrine.mass_link_weight * mass_link)
        * efficiency
    )

    existing = graph.get_edge(org_id, target_id, EdgeType.SOLIDARITY.value)
    if existing is not None:
        current = float(existing.attributes.get("solidarity_strength", 0.0))
        graph.update_edge(
            org_id,
            target_id,
            EdgeType.SOLIDARITY.value,
            solidarity_strength=min(_MAX_SOLIDARITY_STRENGTH, current + gain),
        )
    elif not graph.has_edge(org_id, target_id):
        graph.add_edge(
            org_id,
            target_id,
            edge_type=EdgeType.SOLIDARITY.value,
            solidarity_strength=min(_MAX_SOLIDARITY_STRENGTH, gain),
        )
    # else: (org_id, target_id) already holds a different edge type -- skip
    # rather than clobber it (see docstring).
