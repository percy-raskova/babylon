"""Conformance vector for `metabolism/biocapacity-update`'s ceiling clamp,
from the frozen engine — the DISCRIMINATING scenario for the
``min(new_max, current + delta)`` half of the frozen formula's double clamp.

This script is the PROVENANCE of every number pinned in
``rust/crates/babylon-tick/tests/metabolism_ceiling_conformance.rs``.

**Why this needs its own scenario, and why extraction is zero here.**
``metabolism-conformance.bscn`` uses the production-default
``regeneration_rate=0.02``, which can never push ``current + delta`` above
``max_biocapacity`` for any legal ``extraction_intensity`` in ``{0, 1}`` --
the only two values `int`-declared field seeding can carry (slice 1's
scenario loader accepts only integer literals for node attributes,
``bsl-language.rst``/``scenario.rs::attribute_value``). This scenario
deliberately boosts ``regeneration_rate`` to ``0.9`` (legal per
``Territory.regeneration_rate``'s own ``Field(ge=0.0, le=1.0)`` -- no
Pydantic bypass needed) with ``extraction_intensity=0`` so the ceiling is
approached purely through regeneration: ``regeneration_rate * max_biocapacity
= 90``, against a ``current_biocapacity`` of ``50`` -- ``current + delta =
140``, comfortably past ``max_biocapacity = 100``, and the frozen formula's
``max(0.0, min(new_max, current + delta))`` must clamp it back to exactly
``100.0``.

**Why this is NOT also a "ratcheted ceiling" vector, and why that
combination is provably unreachable with int-seeded fields.** With
``extraction_intensity=0``, ``raw_extraction = extraction_intensity *
current_biocapacity`` is exactly zero, so
``calculate_hysteresis_damage`` returns exactly ``0.0`` and
``new_max = max(0.0, max_biocapacity - 0.0) = max_biocapacity`` unchanged --
the clamp here binds against the ORIGINAL ceiling, not a ratcheted one. For
``extraction_intensity=1`` (the only other int-seedable value),
algebraically ``current + delta = current * (1 - entropy_factor) +
regeneration_rate * max_biocapacity``, which is DECREASING in
``current_biocapacity`` since ``entropy_factor > 1`` always (declared domain
``(1.0, 3.0]``) -- and ``regeneration_rate * max_biocapacity <=
max_biocapacity`` (``regeneration_rate <= 1.0``), so ``current + delta``
can approach but never EXCEED ``max_biocapacity`` at ``extraction_intensity
= 1``, for any current/max_biocapacity/regeneration_rate combination. A
node with BOTH a strictly-ratcheted ceiling (``damage > 0``, needing
``extraction_intensity > 0``) AND a binding ceiling clamp
(``current + delta`` exceeding that ceiling) needs a FRACTIONAL
``extraction_intensity`` strictly between ``0`` and roughly ``1 /
entropy_factor`` -- unreachable through slice 1's int-only field seeding.
The hysteresis ratchet itself (``new_max`` strictly below its seed) is
proven separately, by ``zero-floor-county`` in ``metabolism_conformance.py``,
whose ``max_biocapacity`` ends the tick at ``99.5`` against a ``100.0``
seed.

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
