"""Conformance vector proving `metabolism/biocapacity-update`'s ceiling
clamp binds against the RATCHETED ceiling (`new_max`), not the original
`max_biocapacity` seed (F2 fix round, adversarial review of PR #501).

This script is the PROVENANCE of every number pinned in
``rust/crates/babylon-tick/tests/metabolism_ratcheted_ceiling_conformance.rs``.

See ``metabolism-ratcheted-ceiling-conformance.bscn`` for the full
derivation of why ``regeneration_rate=1.0``/``entropy_factor=1.005``/
``hysteresis_rate=0.01`` (all pushed to their declared legal extremes,
still ordinary ``MetabolismDefines``/``Territory`` construction, no
Pydantic bypass needed) makes BOTH the hysteresis ratchet AND the ceiling
clamp fire simultaneously for one territory -- the combination
``metabolism_ceiling_conformance.py``'s earlier module docstring wrongly
claimed was unreachable (it fixed ``entropy_factor``/``hysteresis_rate`` at
their production defaults while reasoning about reachability, missing that
both are ALSO per-scenario coefficients).

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" uv run python \\
        rust/crates/babylon-tick/content/scenarios/metabolism_ratcheted_ceiling_conformance.py
"""

from __future__ import annotations

from babylon.config.defines import MetabolismDefines
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.metabolism import MetabolismSystem
from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph

SUBJECT_ID = "ratcheted-ceiling-county"
SEED = {
    "biocapacity": 50.0,
    "max_biocapacity": 100.0,
    "extraction_intensity": 1.0,
    # Legal maximum (Territory.regeneration_rate: Field(ge=0.0, le=1.0)).
    "regeneration_rate": 1.0,
}
#: Barely above the declared floor (MetabolismDefines.entropy_factor:
#: Field(gt=1.0, le=3.0)) -- legal, ordinary construction.
ENTROPY_FACTOR = 1.005
#: Legal maximum (MetabolismDefines.hysteresis_rate: Field(ge=0.001, le=0.01)).
HYSTERESIS_RATE = 0.01


def build_graph() -> BabylonGraph:
    """Build the one-territory world."""
    graph = BabylonGraph()
    graph.add_node(SUBJECT_ID, NodeType.TERRITORY, **SEED)
    return graph


def main() -> None:
    """Run one tick of the frozen MetabolismSystem with boosted coefficients."""
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
            f"  {SUBJECT_ID:<24} biocapacity={a['biocapacity']!r} "
            f"max_biocapacity={a['max_biocapacity']!r}"
        )
    finally:
        services.database.close()


if __name__ == "__main__":
    main()
