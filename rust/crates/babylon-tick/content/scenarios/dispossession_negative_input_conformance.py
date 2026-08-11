"""Conformance vectors for `dispossession/territory-transfer`'s PER-INPUT
floor AND ceiling clamps, from the frozen engine — the ADVERSARIAL-REVIEW
follow-up scenario (F2 of the 2026-08-11 review round on PR #498).

This script is the PROVENANCE of every number pinned in
``rust/crates/babylon-tick/tests/dispossession_negative_input_conformance.rs``.

``foreclosure_rate``/``eviction_rate`` are read straight off a raw graph
node dict (``_get_float``, `dispossession_events.py:70-72`) — NOT through a
Pydantic-validated ``Territory`` model, so nothing in the real engine stops
an out-of-domain value (past either the floor OR the ceiling) from reaching
them; this half needs no bypass at all, only a raw
``BabylonGraph.add_node(**attrs)`` call (which accepts any value —
`**attributes: Any`, no validation). ``deadweight_loss_fraction`` IS
`GameDefines`-sourced and Pydantic-gated at construction, so reaching a
negative value there uses the same ``DispossessionDefines.model_construct``
bypass as the saturation scenario's script — see that script's header for
why the bypass is legitimate provenance rather than a hack: it reaches
exactly the configuration BSL's unsuffixed ``:const`` reaches structurally.

``foreclosure_rate=5.0`` (past its ceiling) is deliberate, not incidental:
ceiling-clamped to `1.0` it lands on the SAME intensity a seed of `1.0`
would — proving the per-input CEILING clamp does real work, which a fixture
that never exceeds `1.0` cannot (`min(1.0, 1.0)` is a no-op whether or not
the clamp exists at all). It also anchors the `(when …)` gate open, since
`eviction_rate`/`displacement_rate`/`concentrated_ownership`/
`absentee_landlord_share` are ALL deliberately negative here — every other
per-input floor, exercised in the same vector (`dispossession-ceiling-
matrix-conformance.py` completes the CEILING half for the four fields this
script does not push past their own ceiling).

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" uv run python \\
        rust/crates/babylon-tick/content/scenarios/dispossession_negative_input_conformance.py
"""

from __future__ import annotations

from babylon.config.defines import DispossessionDefines
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.dispossession_events import DispossessionEventSystem
from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph

#: Weights unchanged from `defines.yaml`; `deadweight_loss_fraction` pushed
#: negative (past its own `Field(ge=0.0)` floor) to exercise
#: `compute_value_transfer`'s floor half — `transfer_scale` stays in-domain
#: so this scenario tests floors ONLY, not the ceiling scenario already
#: covered by `dispossession_saturation_conformance.py`.
BYPASS_DEFINES = DispossessionDefines.model_construct(
    weight_foreclosure=0.4,
    weight_eviction=0.3,
    weight_displacement=0.15,
    weight_tax_sale=0.05,
    weight_eminent_domain=0.02,
    deadweight_loss_fraction=-1.0,
    transfer_scale=0.01,
)


def main() -> None:
    """Run one tick of the frozen DispossessionEventSystem, defines bypassed."""
    services = ServiceContainer.create()
    try:
        object.__setattr__(services.defines, "dispossession", BYPASS_DEFINES)

        graph = BabylonGraph()
        # foreclosure_rate=5 (past the ceiling, and the gate anchor);
        # eviction/displacement/concentrated_ownership/absentee_landlord_share
        # all past the floor — every one a raw graph dict read, no Pydantic
        # gate on any of them.
        graph.add_node(
            "negative-input-county",
            NodeType.TERRITORY,
            foreclosure_rate=5.0,
            eviction_rate=-3.0,
            displacement_rate=-8.0,
            concentrated_ownership=-2.0,
            absentee_landlord_share=-9.0,
            wealth=1_000_000.0,
        )
        DispossessionEventSystem().step(graph, services, TickContext(tick=1))
        events = services.event_bus.get_history()

        node = graph.get_node("negative-input-county")
        if node is None:
            raise SystemExit("negative-input-county vanished during the tick")
        a = node.attributes
        print("post-tick state:")
        print(
            f"  negative-input-county  wealth={a['wealth']!r} "
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
