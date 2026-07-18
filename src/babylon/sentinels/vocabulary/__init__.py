"""Vocabulary sentinel: the graph node-type vocabulary stays closed.

Instance of the Sentinel pattern guarding ``_node_type`` AND node SHAPE.
Registry = the scan roots plus the dated production-closure/shape exemptions;
checks = three static AST rules (no invented strings anywhere; every
production query has a production producer; every stamped attribute on a
known node type is real shape). The vocabulary itself is read live from
:class:`~babylon.models.enums.topology.NodeType` — one source of truth, no
duplicate-and-sync; the shape rule reads model fields live from the Pydantic
entity models the same way.

Founding incident (2026-07-18, commit ``3b60dcfe``): a fixture hand-stamped
``_node_type="balkanization_faction"`` while production stamps ``"faction"``.
Three production call sites queried the invented string, matched zero nodes
forever, and silently disabled ``RED_SETTLER_TRAP_DETECTED``, secession
enumeration and ``FASCIST_RECRUITMENT``. Every test passed, because fixture and
query agreed on a convention production never emitted.

Rule (c) (2026-07-18, task #45 audit): the sibling bug, one level down --
a fixture stamping ``territory_ids`` on a ``social_class`` node (a field
``SocialClass`` does not have) gave six tests a green bar over four live
bugs. Same closed-loop shape, over attributes instead of the type itself.
"""

from babylon.sentinels.vocabulary.checks import (
    fabricated_node_attributes,
    invented_node_types,
    unstamped_queried_node_types,
)
from babylon.sentinels.vocabulary.registry import (
    ATTRIBUTE_EXEMPTIONS,
    EXTRA_STAMPABLE_ATTRIBUTES,
    MODEL_FIELDS_BY_NODE_TYPE,
    PRODUCTION_ROOTS,
    SCAN_ROOTS,
    UNSTAMPED_QUERY_ALLOWLIST,
)

__all__ = [
    "ATTRIBUTE_EXEMPTIONS",
    "EXTRA_STAMPABLE_ATTRIBUTES",
    "MODEL_FIELDS_BY_NODE_TYPE",
    "PRODUCTION_ROOTS",
    "SCAN_ROOTS",
    "UNSTAMPED_QUERY_ALLOWLIST",
    "fabricated_node_attributes",
    "invented_node_types",
    "unstamped_queried_node_types",
]
