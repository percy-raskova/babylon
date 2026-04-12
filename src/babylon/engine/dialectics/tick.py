"""Pure tick function for the v2 dialectical engine.

The tick is a pure function::

    def tick(world, player_actions) -> (new_world, events)

Same inputs always produce same outputs. This matters for replay,
debugging, and the ability to test that "if I do X at tick N, the
engine produces Y at tick N+10."

Phase 1 implements a simplified single-pass. The full 8-phase nested
loop (V1 inner → V2 medium → V3 outer → class/political → player →
sublation → invariant → event) is deferred to Phase 2+.

See Also:
    :class:`babylon.engine.dialectics.world.World`: The world state.
    :class:`babylon.engine.dialectics.base.Dialectic`: The fundamental type.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from babylon.engine.dialectics.base import WorldView
from babylon.engine.dialectics.invariants_v2 import check_all_invariants
from babylon.engine.dialectics.world import World, WorldEvent


def tick(
    world: World,
    _player_actions: list[Any],
) -> tuple[World, list[WorldEvent]]:
    """Execute one simulation tick.

    Pure function — same inputs always produce same outputs.

    Phase 1 single-pass:
        1. Step all live dialectics (in insertion order; topological
           ordering via morphisms is Phase 2).
        2. Run sublation pass.
        3. Run invariant check.
        4. Collect events.
        5. Return new World + events.

    Args:
        world: Current world state (immutable).
        player_actions: List of player interventions (Phase 2).

    Returns:
        Tuple of (new World at tick+1, list of events generated).
    """
    new_tick = world.tick + 1
    events: list[WorldEvent] = []

    # ---------------------------------------------------------------
    # 1. Step all live dialectics
    # ---------------------------------------------------------------
    live = world.get_live_dialectics()
    new_dialectics: dict[UUID, Any] = dict(world.dialectics)  # preserve sublated

    world_view = WorldView(tick=new_tick, dialectics=world.dialectics)

    for d_id, d in live.items():
        inputs = world.get_inputs_for(d_id)
        new_d = d.step(inputs, world_view)
        new_dialectics[d_id] = new_d

    # ---------------------------------------------------------------
    # 2. Sublation pass
    # ---------------------------------------------------------------
    new_sublated: set[UUID] = set(world.sublated_ids)

    for d_id, d in list(new_dialectics.items()):
        if d_id in new_sublated:
            continue
        successor = d.sublate()
        if successor is not None:
            new_sublated.add(d_id)
            new_dialectics[successor.id] = successor
            events.append(
                WorldEvent(
                    event_type="sublation",
                    dialectic_id=d_id,
                    payload={
                        "predecessor_id": str(d_id),
                        "successor_id": str(successor.id),
                        "successor_type": successor.type_tag,
                    },
                )
            )

    # ---------------------------------------------------------------
    # 3. Invariant check
    # ---------------------------------------------------------------
    # Build a temporary world for invariant checking
    check_world = World(
        tick=new_tick,
        dialectics=new_dialectics,
        morphisms=world.morphisms,
        sublated_ids=frozenset(new_sublated),
    )
    violations = check_all_invariants(check_world)
    for v in violations:
        events.append(
            WorldEvent(
                event_type="invariant_violation",
                payload={"violation": v},
            )
        )

    # ---------------------------------------------------------------
    # 4. Build new world
    # ---------------------------------------------------------------
    new_world = World(
        tick=new_tick,
        dialectics=new_dialectics,
        morphisms=world.morphisms,
        events=events,
        sublated_ids=frozenset(new_sublated),
    )

    return new_world, events
