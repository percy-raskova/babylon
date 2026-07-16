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

Every ``congress_interval_ticks`` the **Party Congress** convenes first (Unit 5,
Ruling 5 / DT-5, :mod:`babylon.domain.doctrine.congress`): one purge attempt
against the first held trap, resolved by a weighted draw from the
seed-deterministic tick RNG (:func:`~babylon.kernel.system_base.resolve_rng`,
Constitution III.7 — same seed, same history), with tag deltas since the last
congress biasing the odds inside a clamped contingency band.

Determinism: the per-tick loop is RNG-free; the congress consumes the seeded
tick RNG only when a purge is actually attempted (an org holds a trap AND can
afford ``trap_escape_tl``). Byte-safe on the qa:regression goldens by
construction: those five scenarios carry no organization nodes, so this system
is a no-op — and draws nothing — there.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from babylon.domain.doctrine import evaluate_trap_condition, load_doctrine_tree
from babylon.domain.doctrine.congress import held_sprung_traps, run_congress
from babylon.domain.doctrine.mechanics import (
    accrue_theoretical_labor,
    acquire,
    can_acquire,
    decay_tags,
)
from babylon.kernel.event_bus import Event
from babylon.models.enums import EventType
from babylon.models.enums.doctrine import DoctrineTag

if TYPE_CHECKING:
    import random

    from babylon.config.defines.doctrine import DoctrineDefines
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol
    from babylon.models.entities.doctrine import DoctrineNode, DoctrineTree

from babylon.kernel.system_base import SystemBase, resolve_rng
from babylon.kernel.system_protocol import ContextType

#: ``compute_doctrine``'s triple ``kind`` string -> the EventType it publishes
#: as (ADR073 Unit 6a). Every kind ``compute_doctrine`` can return MUST have an
#: entry here — a missing kind would silently drop an event (Constitution
#: III.11), so ``DoctrineSystem.step`` indexes this dict directly (no
#: ``.get()`` fallback) and a bad kind raises loudly instead.
_KIND_TO_EVENT_TYPE: dict[str, EventType] = {
    "sprung": EventType.DOCTRINE_TRAP_SPRUNG,
    "escaped": EventType.DOCTRINE_TRAP_ESCAPED,
    "purge_failed": EventType.DOCTRINE_PURGE_FAILED,
}


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
) -> tuple[tuple[str, ...], float, dict[DoctrineTag, float], list[str], str | None]:
    """Advance one organization's doctrine state by one tick (pure).

    A standing ``study_target_id`` (the player's Educate(Doctrine) order,
    Unit 7b) redirects acquisition: while the target is UNLOCKED (parents
    held) but unaffordable, the org SAVES its theoretical labor — greedy
    auto-acquire is suspended (directed study is wallet discipline); once
    affordable it is acquired and the order clears. While the target is
    still LOCKED, greedy continues (building the tree toward it). An
    invalid, trap, or already-held target clears the order.

    :param attrs: The org node's current attribute mapping.
    :returns: ``(acquired_ids, theoretical_labor, doctrine_tags,
        sprung_trap_ids, study_target_id)``.
    """
    acquired: tuple[str, ...] = tuple(attrs.get("acquired_doctrine_ids", ()))
    tl = float(attrs.get("theoretical_labor", 0.0))
    tags = _read_tags(attrs.get("doctrine_tags"))
    cadre = float(attrs.get("cadre_level", 0.0))
    raw_target = attrs.get("study_target_id")
    study_target: str | None = str(raw_target) if raw_target else None

    tags = decay_tags(tags, defines.tag_decay_rate)
    study_allocation = (defines.study_allocation_min + defines.study_allocation_max) / 2.0
    tl += accrue_theoretical_labor(cadre, study_allocation)

    if tree.root_id not in acquired and can_acquire(tree, acquired, tree.root_id, tl):
        acquired = acquire(acquired, tree.root_id)
        tags = _apply_deltas(tags, tree.nodes[tree.root_id].tag_deltas)

    target_node = tree.nodes.get(study_target) if study_target is not None else None
    if study_target is not None and (
        target_node is None or target_node.is_trap or study_target in acquired
    ):
        study_target = None
        target_node = None

    if target_node is not None and all(p in set(acquired) for p in target_node.parents):
        # Directed study: acquire when affordable, otherwise save — no greedy.
        if tl >= target_node.cost_tl:
            tl -= target_node.cost_tl
            acquired = acquire(acquired, target_node.id)
            tags = _apply_deltas(tags, target_node.tag_deltas)
            study_target = None
    else:
        candidate = _cheapest_acquirable(tree, acquired, tl)
        if candidate is not None:
            tl -= tree.nodes[candidate].cost_tl
            acquired = acquire(acquired, candidate)
            tags = _apply_deltas(tags, tree.nodes[candidate].tag_deltas)
            if study_target == candidate:
                study_target = None

    sprung: list[str] = []
    for trap in _reachable_traps(tree, acquired):
        if evaluate_trap_condition(trap.trap_condition or "", tags):
            acquired = acquire(acquired, trap.id)
            tags = _apply_deltas(tags, trap.tag_deltas)
            sprung.append(trap.id)

    return acquired, tl, tags, sprung, study_target


def compute_doctrine(
    graph: GraphProtocol,
    defines: DoctrineDefines,
    tree: DoctrineTree,
    *,
    tick: int = 0,
    rng: random.Random | None = None,
) -> list[tuple[str, str, str]]:
    """Run the doctrine loop over every organization node; write state back.

    On a congress tick (``tick > 0`` and ``tick % congress_interval_ticks == 0``,
    ``rng`` provided) the Party Congress convenes FIRST — it sums up the period
    the org just lived through — then the ordinary per-tick step runs. The RNG
    is drawn only when a purge is actually attempted, so org-less graphs (the
    qa:regression goldens) never touch the stream.

    :returns: ``(org_id, node_id, kind)`` triples — ``kind`` is ``"sprung"``
        (trap fallen into), ``"escaped"`` (congress purge succeeded), or
        ``"purge_failed"`` — consumed by :meth:`DoctrineSystem.step` to
        publish as ``DoctrineEvent`` instances (Unit 6a, ADR073).
    """
    events: list[tuple[str, str, str]] = []
    is_congress = tick > 0 and rng is not None and tick % defines.congress_interval_ticks == 0
    for node in graph.query_nodes(node_type="organization"):
        attrs = dict(node.attributes)
        org_id = str(attrs.get("id", node.id))

        if is_congress and rng is not None:
            acquired0 = tuple(attrs.get("acquired_doctrine_ids", ()))
            tl0 = float(attrs.get("theoretical_labor", 0.0))
            tags0 = _read_tags(attrs.get("doctrine_tags"))
            snapshot0 = _read_tags(attrs.get("congress_tag_snapshot"))
            # Same trap+affordability gate run_congress applies — the roll is
            # drawn only when an attempt will actually consume it.
            needs_roll = bool(held_sprung_traps(tree, acquired0)) and tl0 >= float(
                defines.trap_escape_tl
            )
            roll = rng.random() if needs_roll else 0.0
            outcome = run_congress(
                acquired=acquired0,
                theoretical_labor=tl0,
                tags=tags0,
                snapshot=snapshot0,
                tree=tree,
                defines=defines,
                roll=roll,
            )
            attrs["acquired_doctrine_ids"] = outcome.acquired
            attrs["theoretical_labor"] = outcome.theoretical_labor
            attrs["doctrine_tags"] = outcome.doctrine_tags
            attrs["congress_tag_snapshot"] = outcome.snapshot
            if outcome.attempted_trap_id is not None:
                kind = "escaped" if outcome.escaped else "purge_failed"
                events.append((org_id, outcome.attempted_trap_id, kind))

        acquired, tl, tags, sprung, study_target = step_organization(attrs, tree, defines)
        updates: dict[str, Any] = {
            "acquired_doctrine_ids": acquired,
            "theoretical_labor": tl,
            "doctrine_tags": tags,
            "study_target_id": study_target,
        }
        if is_congress:
            updates["congress_tag_snapshot"] = attrs["congress_tag_snapshot"]
        graph.update_node(org_id, **updates)
        events.extend((org_id, trap_id, "sprung") for trap_id in sprung)
    return events


class DoctrineSystem(SystemBase):
    """Advances every organization's Doctrine Tree state each tick.

    See the module docstring for the five-step per-org loop and the Party
    Congress (Unit 5). Seed-deterministic: the only stochastic element is the
    congress purge roll, drawn from :func:`resolve_rng` (Constitution III.7).
    Byte-safe on the org-less qa:regression scenarios (no orgs, no writes,
    no draws).
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

        Doctrine events (trap sprung / congress escape / purge failed) are
        published onto ``services.event_bus`` the same way StruggleSystem
        publishes UPRISING (Unit 6a, ADR073): each ``(org_id, node_id, kind)``
        triple from :func:`compute_doctrine` becomes one ``Event`` with the
        matching :data:`_KIND_TO_EVENT_TYPE` EventType and a
        ``{"org_id", "node_id"}`` payload. The behavioural feedback into
        bifurcation/consciousness is Unit 6b, not this method.
        """
        tick = _extract_tick(context)
        if self._tree is None:
            self._tree = load_doctrine_tree()
        triples = compute_doctrine(
            graph,
            services.defines.doctrine,
            self._tree,
            tick=tick,
            rng=resolve_rng(services, tick),
        )
        for org_id, node_id, kind in triples:
            services.event_bus.publish(
                Event(
                    type=_KIND_TO_EVENT_TYPE[kind],
                    tick=tick,
                    payload={"org_id": org_id, "node_id": node_id},
                )
            )


def _extract_tick(context: ContextType) -> int:
    """Current tick from the step context (same idiom as FactionInfluence)."""
    if isinstance(context, dict):
        return int(context.get("tick", 0))
    return int(getattr(context, "tick", 0))
