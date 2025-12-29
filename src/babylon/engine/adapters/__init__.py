"""Graph adapters for the Babylon simulation engine.

Slice 1.7: The Graph Bridge

This package contains adapters that implement GraphProtocol for different
graph backends:

    NetworkXAdapter: Reference implementation using NetworkX (Epoch 1-2)
    ColumnarAdapter: DuckDB + DuckPGQ implementation (Epoch 3, planned)

All Systems interact with the graph through GraphProtocol, never directly
with the backend. This enables backend swapping without changing System code.
"""

from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter
from babylon.engine.adapters.subgraph_view import SubgraphView

__all__ = [
    "NetworkXAdapter",
    "SubgraphView",
]
