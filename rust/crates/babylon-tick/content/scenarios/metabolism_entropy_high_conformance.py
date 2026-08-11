"""Conformance vector for `metabolism/biocapacity-update` at `entropy_factor`
AT its declared cap, from the frozen engine -- the other half of the
mutation-verification pair for the D-1 scaled-`Int` workaround. See
``metabolism_entropy_low_conformance.py``'s module docstring for the full
rationale; this script seeds the IDENTICAL territory (same
``biocapacity``/``max_biocapacity``/``extraction_intensity``/
``regeneration_rate``) with ``entropy_factor`` at ``3.0`` -- the declared
``le=3.0`` cap, inclusive -- instead of near the floor.

At this cap the ecological cost is high enough (``raw_extraction *
entropy_factor = 10 * 3.0 = 30``, against a regeneration of only ``2``) that
``current + delta`` goes negative and the ``max(0.0, ...)`` floor binds --
unlike the low-entropy companion script, where the same territory stays
comfortably positive. That swing, from a positive floor-inert result to an
exact ``0.0`` floor-bound result, driven by nothing but ``entropy_factor``,
is the clearest possible proof the scaled-``Int`` workaround is live.

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" uv run python \\
        rust/crates/babylon-tick/content/scenarios/metabolism_entropy_high_conformance.py
"""

from __future__ import annotations

from babylon.config.defines import MetabolismDefines
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.metabolism import MetabolismSystem
from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph

SUBJECT_ID = "high-entropy-county"
SEED = {
    "biocapacity": 10.0,
    "max_biocapacity": 100.0,
    "extraction_intensity": 1.0,
    "regeneration_rate": 0.02,
}
#: At the cap (3.0, inclusive) -- legal, ordinary construction.
ENTROPY_FACTOR = 3.0


def build_graph() -> BabylonGraph:
    """Build the one-territory world."""
    graph = BabylonGraph()
    graph.add_node(SUBJECT_ID, NodeType.TERRITORY, **SEED)
    return graph


def main() -> None:
    """Run one tick of the frozen MetabolismSystem with entropy_factor at its cap."""
    services = ServiceContainer.create()
    try:
        object.__setattr__(
            services.defines,
            "metabolism",
            MetabolismDefines(entropy_factor=ENTROPY_FACTOR),
        )

        graph = build_graph()
        MetabolismSystem().step(graph, services, TickContext(tick=1))

        node = graph.get_node(SUBJECT_ID)
        if node is None:
            raise SystemExit(f"node {SUBJECT_ID} vanished during the tick")
        a = node.attributes
        print(f"entropy_factor = {ENTROPY_FACTOR!r}")
        print("post-tick state:")
        print(
            f"  {SUBJECT_ID:<20} biocapacity={a['biocapacity']!r} "
            f"max_biocapacity={a['max_biocapacity']!r}"
        )
    finally:
        services.database.close()


if __name__ == "__main__":
    main()
