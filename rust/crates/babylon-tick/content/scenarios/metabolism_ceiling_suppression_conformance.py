"""Conformance vector for `metabolism/biocapacity-update`'s
regeneration-suppression-AT-THE-CEILING boundary (F3 fix round, adversarial
review of PR #501: mutating `metabolism.bsl`'s `(>= current max-cap)` guard
to `(> current max-cap)` left all 16 prior tests green, because
`zero-floor-county`'s discriminating case floors BOTH branches' results to
the identical `0.0` -- the mutation was hidden by the downstream `max(0.0,
...)` clamp, not caught by it).

This script is the PROVENANCE of every number pinned in
``rust/crates/babylon-tick/tests/metabolism_ceiling_suppression_conformance.rs``.

The frozen formula's own guard, verbatim (`metabolic_rift.py:42-44`):

.. code-block:: python

    regeneration = regeneration_rate * max_biocapacity
    if current_biocapacity >= max_biocapacity:
        regeneration = 0.0

At ``current_biocapacity == max_biocapacity`` EXACTLY, this suppresses
regeneration (the ``>=`` fires). A rule using ``>`` instead would WRONGLY
let regeneration fire at this exact boundary. To make that difference
survive to the FINAL clamped output (not get floored away like
``zero-floor-county``'s vector), this territory is chosen so the CORRECT
branch (`regeneration` suppressed) lands JUST BELOW zero (and floors to
`0.0`) while the WRONG branch (`regeneration` firing) lands comfortably
ABOVE zero (and survives the floor untouched) -- ``entropy_factor`` near its
declared floor (`1.005`, so the ecological cost barely exceeds the stock
itself) and a boosted ``regeneration_rate`` (`0.5`) make the gap between
the two branches large and unambiguous.

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" uv run python \\
        rust/crates/babylon-tick/content/scenarios/metabolism_ceiling_suppression_conformance.py
"""

from __future__ import annotations

from babylon.config.defines import MetabolismDefines
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.metabolism import MetabolismSystem
from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph

SUBJECT_ID = "at-ceiling-county"
SEED = {
    "biocapacity": 10.0,
    "max_biocapacity": 10.0,
    "extraction_intensity": 1.0,
    # Boosted -- legal per Territory.regeneration_rate's own
    # Field(ge=0.0, le=1.0).
    "regeneration_rate": 0.5,
}
#: Barely above the declared floor -- legal, ordinary construction.
ENTROPY_FACTOR = 1.005
#: Legal maximum (MetabolismDefines.hysteresis_rate: Field(ge=0.001, le=0.01)).
HYSTERESIS_RATE = 0.01


def build_graph() -> BabylonGraph:
    """Build the one-territory world, seeded EXACTLY at its own ceiling."""
    graph = BabylonGraph()
    graph.add_node(SUBJECT_ID, NodeType.TERRITORY, **SEED)
    return graph


def main() -> None:
    """Run one tick of the frozen MetabolismSystem at the current==max_biocapacity boundary."""
    services = ServiceContainer.create()
    try:
        object.__setattr__(
            services.defines,
            "metabolism",
            MetabolismDefines(entropy_factor=ENTROPY_FACTOR, hysteresis_rate=HYSTERESIS_RATE),
        )

        graph = build_graph()
        MetabolismSystem().step(graph, services, TickContext(tick=1))

        node = graph.get_node(SUBJECT_ID)
        if node is None:
            raise SystemExit(f"node {SUBJECT_ID} vanished during the tick")
        a = node.attributes
        print(f"entropy_factor = {ENTROPY_FACTOR!r}, hysteresis_rate = {HYSTERESIS_RATE!r}")
        print("post-tick state:")
        print(
            f"  {SUBJECT_ID:<20} biocapacity={a['biocapacity']!r} "
            f"max_biocapacity={a['max_biocapacity']!r}"
        )
    finally:
        services.database.close()


if __name__ == "__main__":
    main()
