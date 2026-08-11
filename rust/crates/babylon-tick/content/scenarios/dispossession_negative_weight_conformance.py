"""Conformance vectors for `dispossession/territory-transfer`'s D-3
total-sum FLOOR clamp, from the frozen engine — closes the LAST gap in the
per-clamp mutation table (F3 of the 2026-08-11 adversarial review round on
PR #498).

This script is the PROVENANCE of every number pinned in
``rust/crates/babylon-tick/tests/dispossession_negative_weight_conformance.rs``.

The ten per-input floor/ceiling clamps
(``dispossession_negative_input_conformance.py`` +
``dispossession_ceiling_matrix_conformance.py``) guarantee every rate/
structural term feeding the weighted sum is in ``[0, 1]``, which makes D-3's
total-sum FLOOR clamp mutation-dead against any RATE mutation alone: five
non-negative terms cannot sum negative. But `DispossessionDefines`' WEIGHTS
are the exact same unguarded ``:const`` surface F1 found for
``transfer_scale``/``deadweight_loss_fraction`` — nothing stops
``weight_foreclosure`` from being authored negative and unsuffixed, and a
negative weight times an in-domain positive rate is a genuinely negative
term the per-input (rate-side only) clamps cannot catch.

``weight_foreclosure=-1.0`` needs the same `DispossessionDefines.
model_construct` bypass the saturation/negative-input scripts use, since
weights ARE `GameDefines`-sourced and Pydantic-gated at construction
(``Field(ge=0.0, le=1.0)``) — see those scripts' headers for why the bypass
is legitimate provenance rather than a hack.

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" uv run python \\
        rust/crates/babylon-tick/content/scenarios/dispossession_negative_weight_conformance.py
"""

from __future__ import annotations

from babylon.config.defines import DispossessionDefines
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.dispossession_events import DispossessionEventSystem
from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph

#: Only `weight_foreclosure` is out of domain; every other coefficient is
#: shipped/in-domain so the ONE clamp under test (D-3's floor) is isolated.
BYPASS_DEFINES = DispossessionDefines.model_construct(
    weight_foreclosure=-1.0,
    weight_eviction=0.0,
    weight_displacement=0.0,
    weight_tax_sale=0.0,
    weight_eminent_domain=0.0,
    deadweight_loss_fraction=0.05,
    transfer_scale=0.01,
)


def main() -> None:
    """Run one tick of the frozen DispossessionEventSystem, defines bypassed."""
    services = ServiceContainer.create()
    try:
        object.__setattr__(services.defines, "dispossession", BYPASS_DEFINES)

        graph = BabylonGraph()
        graph.add_node(
            "negative-weight-county",
            NodeType.TERRITORY,
            foreclosure_rate=1.0,
            eviction_rate=0.0,
            displacement_rate=0.0,
            concentrated_ownership=0.0,
            absentee_landlord_share=0.0,
            wealth=1_000_000.0,
        )
        DispossessionEventSystem().step(graph, services, TickContext(tick=1))
        events = services.event_bus.get_history()

        node = graph.get_node("negative-weight-county")
        if node is None:
            raise SystemExit("negative-weight-county vanished during the tick")
        a = node.attributes
        print("post-tick state:")
        print(
            f"  negative-weight-county  wealth={a['wealth']!r} "
            f"dispossession_intensity={a.get('dispossession_intensity')!r}"
        )
        print()

        print("events:")
        for event in events:
            print(f"  {event.type} {event.payload!r}")
        if not events:
            print("  (none)")
    finally:
        services.database.close()


if __name__ == "__main__":
    main()
