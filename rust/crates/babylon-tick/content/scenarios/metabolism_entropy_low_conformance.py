"""Conformance vector for `metabolism/biocapacity-update` at `entropy_factor`
NEAR its declared floor, from the frozen engine -- one half of the
mutation-verification pair for the D-1 scaled-`Int` workaround (see
``metabolism.bsl``'s own D-1 and
``reports/metabolism-port-assessment-2026-08-11.md`` §3).

This script is the PROVENANCE of every number pinned in
``rust/crates/babylon-tick/tests/metabolism_entropy_low_conformance.rs``.
Its companion, ``metabolism_entropy_high_conformance.py``, seeds the
IDENTICAL territory with ``entropy_factor`` at its declared cap (``3.0``)
instead of near its floor (``1.01``) -- the two scripts together prove the
scaled-``Int`` `:const` (``metabolism/entropy-factor-x1e6``) actually
carries the coefficient's effect end to end: a bug in the ``/ 1000000``
descaling (an off-by-a-factor-of-ten, say) would make one or both of these
diverge from what the frozen engine actually computes.

``1.01`` is legal under ``MetabolismDefines.entropy_factor``'s own
``Field(gt=1.0, le=3.0)`` -- ordinary Pydantic construction, no
``model_construct`` bypass needed (unlike Dispossession's saturation/
negative-weight scripts, which push OUTSIDE their coefficients' declared
domains on purpose).

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" uv run python \\
        rust/crates/babylon-tick/content/scenarios/metabolism_entropy_low_conformance.py
"""

from __future__ import annotations

from babylon.config.defines import MetabolismDefines
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.metabolism import MetabolismSystem
from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph

SUBJECT_ID = "low-entropy-county"
SEED = {
    "biocapacity": 10.0,
    "max_biocapacity": 100.0,
    "extraction_intensity": 1.0,
    "regeneration_rate": 0.02,
}
#: Near the floor (1.0, exclusive) -- legal, ordinary construction.
ENTROPY_FACTOR = 1.01


def build_graph() -> BabylonGraph:
    """Build the one-territory world."""
    graph = BabylonGraph()
    graph.add_node(SUBJECT_ID, NodeType.TERRITORY, **SEED)
    return graph


def main() -> None:
    """Run one tick of the frozen MetabolismSystem with a low entropy_factor."""
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
