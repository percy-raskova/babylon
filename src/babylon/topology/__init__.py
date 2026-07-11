"""The Topology — the Embedded Trinity's second pillar, as its own package.

Fluid relational state over rustworkx (Amendment L): ``BabylonGraph`` /
``BabylonUGraph`` and their query/aggregation/subgraph adapters, plus the
pure graph algorithms. Extracted from ``babylon.engine`` in Program 14
Phase 1 so the layers below the engine (persistence hydration, formulas'
curvature math) can construct and traverse the substrate without importing
the engine backward.

Layering: ``topology`` sits above ``models`` (it stores ``GraphNode`` /
``GraphEdge`` payloads) and below ``persistence`` and ``engine``. The
*interface* lower layers type against is ``babylon.kernel.graph_protocol``;
this package is the implementation.
"""

from babylon.topology.graph import BabylonGraph, BabylonUGraph

__all__ = [
    "BabylonGraph",
    "BabylonUGraph",
]
