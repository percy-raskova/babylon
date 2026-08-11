"""Conformance vector for `metabolism/biocapacity-update`'s ceiling clamp,
from the frozen engine — the DISCRIMINATING scenario for the
``min(new_max, current + delta)`` half of the frozen formula's double clamp.

This script is the PROVENANCE of every number pinned in
``rust/crates/babylon-tick/tests/metabolism_ceiling_conformance.rs``.

**Why this needs its own scenario, and why extraction is zero here.**
``metabolism-conformance.bscn`` uses the production-default
``regeneration_rate=0.02``. That default does NOT make the ceiling clamp
unreachable in general -- a ``current`` close enough to ``max_biocapacity``
(e.g. ``current=99``, ``max_biocapacity=100``: ``regen = 0.02*100 = 2``,
``current + delta = 101 > 100`` at ``extraction_intensity=0``) already
exceeds it, by a margin of roughly ``regeneration_rate`` itself. What the
default rules out is a DRAMATIC, unambiguous margin from an ORDINARY,
mid-range stock level: this scenario boosts ``regeneration_rate`` to
``0.9`` (legal per ``Territory.regeneration_rate``'s own
``Field(ge=0.0, le=1.0)`` -- no Pydantic bypass needed) precisely so the
clamp fires from ``current_biocapacity=50`` -- nowhere near the ceiling --
rather than needing a seed sitting within a hair of it. With
``extraction_intensity=0`` (so the ecological cost is exactly zero and the
ceiling is approached PURELY through regeneration): ``regeneration_rate *
max_biocapacity = 90``, against ``current_biocapacity=50`` --
``current + delta = 140``, comfortably past ``max_biocapacity = 100``, and
the frozen formula's ``max(0.0, min(new_max, current + delta))`` must clamp
it back to exactly ``100.0``.

**Why this is NOT also a "ratcheted ceiling" vector.** With
``extraction_intensity=0``, ``raw_extraction = extraction_intensity *
current_biocapacity`` is exactly zero, so
``calculate_hysteresis_damage`` returns exactly ``0.0`` and
``new_max = max(0.0, max_biocapacity - 0.0) = max_biocapacity`` unchanged --
the clamp here binds against the ORIGINAL ceiling, not a ratcheted one. **An
earlier revision of this docstring claimed the combination (damage > 0 AND
the ceiling clamp binding against the RATCHETED value) was "provably
unreachable with int-seeded fields" -- that argument fixed
``entropy_factor``/``hysteresis_rate`` at their PRODUCTION DEFAULTS while
reasoning about reachability, missing that both are ALSO per-scenario
``MetabolismDefines`` coefficients, exactly like ``regeneration_rate``.
FALSE, disproved by execution: see
``metabolism_ratcheted_ceiling_conformance.py``
(``regeneration_rate=1.0``, ``entropy_factor=1.005``,
``hysteresis_rate=0.01``, all legal at their declared extremes) for a
territory that hits both conditions at once.** This scenario stays useful
in its own right -- it isolates the UNRATCHETED ceiling clamp with no
hysteresis interaction at all, which the ratcheted-ceiling scenario does
not (there the two clamps interact).

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" uv run python \\
        rust/crates/babylon-tick/content/scenarios/metabolism_ceiling_conformance.py
"""

from __future__ import annotations

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.metabolism import MetabolismSystem
from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph

SUBJECT_ID = "ceiling-county"
SEED = {
    "biocapacity": 50.0,
    "max_biocapacity": 100.0,
    "extraction_intensity": 0.0,
    # Boosted from the 0.02 production default -- see the module docstring.
    # Legal per Territory.regeneration_rate's own Field(ge=0.0, le=1.0).
    "regeneration_rate": 0.9,
}


def build_graph() -> BabylonGraph:
    """Build the one-territory world."""
    graph = BabylonGraph()
    graph.add_node(SUBJECT_ID, NodeType.TERRITORY, **SEED)
    return graph


def main() -> None:
    """Run one tick of the frozen MetabolismSystem and print the vectors."""
    services = ServiceContainer.create()
    try:
        graph = build_graph()
        MetabolismSystem().step(graph, services, TickContext(tick=1))

        node = graph.get_node(SUBJECT_ID)
        if node is None:
            raise SystemExit(f"node {SUBJECT_ID} vanished during the tick")
        a = node.attributes
        print("post-tick state:")
        print(
            f"  {SUBJECT_ID:<14} biocapacity={a['biocapacity']!r} "
            f"max_biocapacity={a['max_biocapacity']!r} "
            f"(seed biocapacity={SEED['biocapacity']!r} "
            f"seed max_biocapacity={SEED['max_biocapacity']!r})"
        )
    finally:
        services.database.close()


if __name__ == "__main__":
    main()
