"""DoctrineSystem — the party's ideological development over the Doctrine Tree.

Owner-ratified 2026-07-15 (the six DT rulings). Each tick, per ORGANIZATION node,
this system runs the deterministic doctrine loop built from the pure mechanics in
:mod:`babylon.domain.doctrine.mechanics`:

1. **Decay** — every accumulated tag strength erodes by ``tag_decay_rate``
   (Ruling 3, 0.55%/tick): unexercised theory fades.
2. **Accrue theoretical labour** — ``study_allocation × cadre_level`` (Ruling 4).
   ``cadre_level`` is the MVP surplus proxy: theoretical labour is intellectual
   work, so a party's *cadre quality* (not its material budget) is the apt
   capacity measure. ``study_allocation`` is the midpoint of the ratified band.
3. **Bootstrap the root** — the free ``class_consciousness`` root is acquired
   once TL is non-negative, seeding starting tag strength.
4. **Greedy auto-acquire** — the cheapest affordable, unlocked, non-trap node is
   acquired (deterministic: min ``cost_tl``, id tie-break); its ``tag_deltas``
   add to the accumulator and its ``cost_tl`` is spent. This is the AI party's
   OODA-driven study; the player's ``study`` verb (Unit 7) targets a specific node.
5. **Trap firing** — any *reachable* trap (all parents held) whose
   ``trap_condition`` holds against the current tags is fallen into (acquired
   involuntarily, its deltas applied), and a ``DOCTRINE_TRAP_SPRUNG`` event fires.

Determinism: no RNG (Constitution III.7) — every step is a pure function of the
node's prior state. Byte-safe on the qa:regression goldens by construction: those
five scenarios carry no organization nodes, so this system is a no-op there.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from babylon.domain.doctrine import evaluate_trap_condition, load_doctrine_tree
from babylon.domain.doctrine.mechanics import (
    accrue_theoretical_labor,
    acquire,
    can_acquire,
    decay_tags,
)
from babylon.models.enums.doctrine import DoctrineTag

if TYPE_CHECKING:
    from babylon.config.defines.doctrine import DoctrineDefines
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol
    from babylon.models.entities.doctrine import DoctrineNode, DoctrineTree

from babylon.kernel.system_base import SystemBase
from babylon.kernel.system_protocol import ContextType


def _apply_deltas(tags: dict[DoctrineTag, float], deltas: object) -> dict[DoctrineTag, float]:
    """Add a node's ``tag_deltas`` (signed ints) onto the float accumulator."""
    result = dict(tags)
    if isinstance(deltas, dict):
        for tag, delta in deltas.items():
            key = tag if isinstance(tag, DoctrineTag) else DoctrineTag(tag)
            result[key] = result.get(key, 0.0) + float(delta)
    return result


def _cheapest_acquirable(tree: DoctrineTree, acquired: tuple[str, ...], tl: float) -> str | None:
    """The deterministically-chosen next node to auto-acquire, or ``None``.

    Cheapest affordable, unlocked, non-trap node; ties broken by node id so the
    choice is reproducible.
    """
    candidates = [node_id for node_id in tree.nodes if can_acquire(tree, acquired, node_id, tl)]
    if not candidates:
        return None
    return min(candidates, key=lambda nid: (tree.nodes[nid].cost_tl, nid))


def _reachable_traps(tree: DoctrineTree, acquired: tuple[str, ...]) -> list[DoctrineNode]:
    """Trap nodes whose every parent is already held (id-sorted for determinism)."""
    held = set(acquired)
    traps = [
        node
        for node in tree.nodes.values()
        if node.is_trap
        and node.id not in held
        and node.trap_condition is not None
        and all(parent in held for parent in node.parents)
    ]
    return sorted(traps, key=lambda n: n.id)


def _read_tags(raw: object) -> dict[DoctrineTag, float]:
    """Coerce a graph node's ``doctrine_tags`` attr to a float accumulator dict."""
    if not isinstance(raw, dict):
        return {}
    out: dict[DoctrineTag, float] = {}
    for tag, value in raw.items():
        key = tag if isinstance(tag, DoctrineTag) else DoctrineTag(tag)
        out[key] = float(value)
    return out


def step_organization(
    attrs: dict[str, Any],
    tree: DoctrineTree,
    defines: DoctrineDefines,
) -> tuple[tuple[str, ...], float, dict[DoctrineTag, float], list[str]]:
    """Advance one organization's doctrine state by one tick (pure).

    :param attrs: The org node's current attribute mapping.
    :returns: ``(acquired_ids, theoretical_labor, doctrine_tags, sprung_trap_ids)``.
    """
    acquired: tuple[str, ...] = tuple(attrs.get("acquired_doctrine_ids", ()))
    tl = float(attrs.get("theoretical_labor", 0.0))
    tags = _read_tags(attrs.get("doctrine_tags"))
    cadre = float(attrs.get("cadre_level", 0.0))

    tags = decay_tags(tags, defines.tag_decay_rate)
    study_allocation = (defines.study_allocation_min + defines.study_allocation_max) / 2.0
    tl += accrue_theoretical_labor(cadre, study_allocation)

    if tree.root_id not in acquired and can_acquire(tree, acquired, tree.root_id, tl):
        acquired = acquire(acquired, tree.root_id)
        tags = _apply_deltas(tags, tree.nodes[tree.root_id].tag_deltas)

    candidate = _cheapest_acquirable(tree, acquired, tl)
    if candidate is not None:
        tl -= tree.nodes[candidate].cost_tl
        acquired = acquire(acquired, candidate)
        tags = _apply_deltas(tags, tree.nodes[candidate].tag_deltas)

    sprung: list[str] = []
    for trap in _reachable_traps(tree, acquired):
        if evaluate_trap_condition(trap.trap_condition or "", tags):
            acquired = acquire(acquired, trap.id)
            tags = _apply_deltas(tags, trap.tag_deltas)
            sprung.append(trap.id)

    return acquired, tl, tags, sprung


def compute_doctrine(
    graph: GraphProtocol, defines: DoctrineDefines, tree: DoctrineTree
) -> list[tuple[str, str]]:
    """Run the doctrine loop over every organization node; write state back.

    :returns: ``(org_id, trap_id)`` pairs for every trap sprung this tick (for a
        later phase to emit as events; Unit 4 computes state only).
    """
    sprung_events: list[tuple[str, str]] = []
    for node in graph.query_nodes(node_type="organization"):
        attrs = dict(node.attributes)
        org_id = str(attrs.get("id", node.id))
        acquired, tl, tags, sprung = step_organization(attrs, tree, defines)
        graph.update_node(
            org_id,
            acquired_doctrine_ids=acquired,
            theoretical_labor=tl,
            doctrine_tags=tags,
        )
        sprung_events.extend((org_id, trap_id) for trap_id in sprung)
    return sprung_events


class DoctrineSystem(SystemBase):
    """Advances every organization's Doctrine Tree state each tick.

    See the module docstring for the five-step per-org loop. Purely deterministic
    (no RNG); byte-safe on the org-less qa:regression scenarios.
    """

    name: ClassVar[str] = "Doctrine"
    creates_value: ClassVar[bool] = False

    def __init__(self) -> None:
        super().__init__()
        self._tree: DoctrineTree | None = None

    def step(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
    ) -> None:
        """Run the doctrine loop over all organizations, writing per-org state.

        Trap-sprung events are computed but not yet published — event emission +
        the bridge whitelist are wired in Unit 6, alongside the behavioural
        feedback into bifurcation/consciousness.
        """
        del context
        if self._tree is None:
            self._tree = load_doctrine_tree()
        compute_doctrine(graph, services.defines.doctrine, self._tree)
