"""Graph adapter machinery for the Babylon simulation engine.

Slice 1.7 introduced this package as "The Graph Bridge" with
NetworkXAdapter as the GraphProtocol reference implementation. Amendment L
(constitution v2.7.0) replaced that adapter with the rustworkx-backed
:class:`babylon.engine.graph.BabylonGraph`, which implements the protocol
directly; the adapter was deleted once nothing constructed it.

What remains here is the shared machinery BabylonGraph composes:

    QueryMixin / AggregationMixin: protocol query/aggregate implementations
    SubgraphView, SubgraphFilterBuilder: filtered read-only graph views
    CompatGraph: the structural Protocol those mixins are typed against

All Systems interact with the graph through GraphProtocol, never directly
with the backend.
"""

from babylon.engine.adapters.subgraph_view import SubgraphView

__all__ = [
    "SubgraphView",
]
