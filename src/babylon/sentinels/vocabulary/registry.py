"""Declared invariants of the graph node-type vocabulary.

The vocabulary sentinel's registry: which trees are scanned, and the one
narrow, dated exemption to the production-closure rule. The *vocabulary
itself* is deliberately NOT duplicated here — it is read live from
:class:`~babylon.models.enums.topology.NodeType`, so the enum stays the single
source of truth and registry drift is structurally impossible.

Layer 0.5: imports nothing above :mod:`babylon.models`.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "LITERAL_EXEMPTIONS",
    "PRODUCTION_ROOTS",
    "SCAN_ROOTS",
    "UNSTAMPED_QUERY_ALLOWLIST",
]

#: Every tree scanned by rule (a) — the "no invented strings" rule. ``tests``
#: is in scope *because* the bug this sentinel exists to prevent lived in a
#: fixture: a test that stamps a type production never emits is the whole
#: failure mode, so excluding tests would exclude the defect.
SCAN_ROOTS: Final[tuple[str, ...]] = ("src", "web", "tests")

#: The trees whose stamps and queries must CLOSE against each other — rule
#: (b). Test fixtures deliberately do not count as producers: a node type that
#: only a fixture ever stamps is exactly the "green test over a dead feature"
#: shape, so letting ``tests`` satisfy a production query would blind the
#: sentinel to its own founding bug.
PRODUCTION_ROOTS: Final[tuple[str, ...]] = ("src", "web")

#: Node types production QUERIES but never STAMPS. Every entry is a live
#: defect held open by an owner decision, not an approved pattern — a query
#: here iterates the empty set on every tick.
#:
#: Added 2026-07-18 (Task 1b). TODO(owner): scope the repair or delete the
#: dead queries; this list must only ever shrink.
#:
#: - ``hex``: production carries hex substrate state on TERRITORY nodes via
#:   ``domain/economics/substrate/hex_graph_bridge.py``; no code path stamps a
#:   ``hex`` node onto the engine graph. ``SubstrateSystem`` (MATERIAL_BASE
#:   @2.5), ``Vol2CirculationStep``, ``territory_diagnostics`` and the
#:   ``simulation_engine`` determinism-hash row collector therefore all iterate
#:   an empty set at runtime.
#: - ``community``: community membership lives in the XGI *hypergraph*
#:   (``engine/systems/community.py``), not the main graph. The last surviving
#:   query is ``domain/institution/queries.py::community_embeddedness``, which
#:   has no production caller. The same defect was already found and fixed once
#:   in the web bridge (see ``tests/unit/web/test_engine_bridge.py``,
#:   ``test_educate_targets_uses_social_class_not_community``).
UNSTAMPED_QUERY_ALLOWLIST: Final[frozenset[str]] = frozenset({"hex", "community"})

#: Exact ``(path, literal)`` pairs exempt from rule (a). Deliberately keyed on
#: BOTH file and string so an exemption cannot leak to another call site: the
#: point of the rule is that an invented type is invisible, and a broad
#: exemption would re-hide it.
#:
#: Added 2026-07-18 (Task 1b). This list must only ever shrink.
LITERAL_EXEMPTIONS: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        # The 3b60dcfe regression test asserts the WRONG string matches
        # NOTHING. Naming the bogus type is the whole point of the test, so
        # this exemption is permanent rather than debt.
        (
            "tests/unit/balkanization/test_faction_node_type_query.py",
            "balkanization_faction",
        ),
        # Legacy CamelCase persistence format. ``postgres_runtime/_legacy.py``
        # deliberately tolerates BOTH casings (see ``_extract_promoted_columns``,
        # which branches on ``node_type in ("SocialClass", "social_class")``),
        # and these tests cover the legacy branch by hydrating legacy rows.
        # NOT a live bug — but note a graph hydrated from CamelCase rows will
        # NOT answer ``query_nodes(NodeType.SOCIAL_CLASS)``.
        # TODO(owner): decide whether the legacy casing should be normalised on
        # hydration; until then the tolerance stays covered and visible here.
        ("tests/unit/persistence/test_postgres_runtime.py", "SocialClass"),
    }
)
