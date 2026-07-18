"""Vocabulary sentinel: the graph node-type vocabulary stays closed.

Instance of the Sentinel pattern guarding ``_node_type``. Registry = the scan
roots plus the dated production-closure exemption; checks = two static AST
rules (no invented strings anywhere; every production query has a production
producer). The vocabulary itself is read live from
:class:`~babylon.models.enums.topology.NodeType` — one source of truth, no
duplicate-and-sync.

Founding incident (2026-07-18, commit ``3b60dcfe``): a fixture hand-stamped
``_node_type="balkanization_faction"`` while production stamps ``"faction"``.
Three production call sites queried the invented string, matched zero nodes
forever, and silently disabled ``RED_SETTLER_TRAP_DETECTED``, secession
enumeration and ``FASCIST_RECRUITMENT``. Every test passed, because fixture and
query agreed on a convention production never emitted.
"""

from babylon.sentinels.vocabulary.checks import (
    invented_node_types,
    unstamped_queried_node_types,
)
from babylon.sentinels.vocabulary.registry import (
    PRODUCTION_ROOTS,
    SCAN_ROOTS,
    UNSTAMPED_QUERY_ALLOWLIST,
)

__all__ = [
    "PRODUCTION_ROOTS",
    "SCAN_ROOTS",
    "UNSTAMPED_QUERY_ALLOWLIST",
    "invented_node_types",
    "unstamped_queried_node_types",
]
