"""Shared helpers for the frozen-engine conformance provenance scripts beside
this file (``*_conformance.py``) — theme 6,
``docs/superpowers/plans/2026-08-18-bsl-refactor-program.md`` Task R2.2.

**Deadline, not urgency (plan R2.2).** This module exists ahead of the
Python-engine-freeze deletion ceremony (no date scheduled yet) — after that
ceremony these scripts become the surviving oracle, and extracting shared
helpers against a dead reference would be archaeology, not engineering.

**Scope (R2.2.2/R2.2.3): pure addition.** Two files
(``solidarity_conformance.py``, ``consciousness_ternary_conformance.py``)
hand-roll a standalone pipeline with no ``ServiceContainer``/``BabylonGraph``
at all and stay explicitly out of scope. Of the remaining 23, this module
extracts only the CONFIRMED-shared scaffold — ``ServiceContainer.create()``
plus its ``try``/``finally: services.database.close()`` wrapper, the
node-fetch-or-die idiom, and the per-subject "post-tick state:" print block —
verified genuinely identical (not carrying oracle-specific logic) by reading
``metabolism_extreme_damage_conformance.py`` and
``dispossession_conformance.py`` in full. Oracle-specific extras (a defines
dump before the tick, an events dump after) are NOT absorbed here — they stay
in whichever script needs them. Landing this module changes NOTHING about
the 25 existing scripts except the one migrated as proof-of-adoption
(``metabolism_extreme_damage_conformance.py``); sweeping the rest is a named,
explicitly deferred follow-up (same discipline as the Rust side's R2.1.3).
"""

from __future__ import annotations

from typing import Any

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph


def run_tick_and_print(
    system_cls: type,
    subjects: list[tuple[str, dict[str, Any]]],
    fields_to_print: list[str],
    *,
    node_type: NodeType = NodeType.TERRITORY,
    width: int = 16,
) -> None:
    """Build one graph from ``subjects``, run one tick of ``system_cls``,
    print each subject's post-tick state, and close services.

    The ``ServiceContainer.create()``/try-finally/print-header scaffold
    shared, verbatim, across the 23/25 ``*_conformance.py`` scripts that use
    ``ServiceContainer``/``BabylonGraph`` (confirmed by reading
    ``metabolism_extreme_damage_conformance.py`` and
    ``dispossession_conformance.py`` in full).

    ``subjects`` is ``[(node_id, seed_attrs), ...]``, in the same declaration
    order the frozen scenario used — every existing script's own
    ``SUBJECTS``/loop already carries this order, so this parameter changes
    nothing about it.

    ``fields_to_print`` names the attributes printed per subject, in order,
    formatted ``field=value!r`` exactly as every existing script's own
    f-string does (``repr()``, not ``str()`` — floats print with their full
    precision, matching the Rust side's own bit-exact provenance capture).
    Read with ``.get()`` (never a bare subscript): a field a guard skipped
    writing prints ``None`` rather than raising, matching
    ``dispossession_conformance.py``'s own computed-field read.

    Does NOT print oracle-specific extras (a defines dump before the tick,
    an events dump after) — those stay in the caller, which prints its own
    header/footer around this call. Kept out on purpose (R2.2.2): they are
    NOT confirmed-shared boilerplate, they are oracle-specific.
    """
    services = ServiceContainer.create()
    try:
        graph = BabylonGraph()
        for node_id, seed in subjects:
            graph.add_node(node_id, node_type, **seed)
        system_cls().step(graph, services, TickContext(tick=1))

        print("post-tick state:")
        for node_id, _seed in subjects:
            node = graph.get_node(node_id)
            if node is None:
                raise SystemExit(f"node {node_id} vanished during the tick")
            a = node.attributes
            fields = " ".join(f"{field}={a.get(field)!r}" for field in fields_to_print)
            print(f"  {node_id:<{width}} {fields}")
    finally:
        services.database.close()
