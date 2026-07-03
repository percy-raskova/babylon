"""SubstrateSystem: physical-stock tick at pipeline slot 2.5 (Spec 062, US7).

Implements the System protocol. Runs after :class:`TerritorySystem` (slot 2)
and before :class:`ProductionSystem` (slot 3), so production consumes the
just-computed substrate values within the same tick.

Per FR-050/FR-051, the substrate system tracks physical stocks (raw
materials, energy, biocapacity) that flow into Vol I production. For the
MVP, the system is a pure pass-through that records substrate snapshots
into the per-tick context so the auditor can observe them. Concrete
stock-depletion / regeneration logic lands with the downstream economics
spec that owns physical-substrate dynamics.

See Also:
    ``specs/062-cross-scale-integration/spec.md`` FR-050/FR-051/FR-052.
    :mod:`babylon.engine.systems.protocol`: System Protocol.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar

from babylon.engine.systems.base import SystemBase

if TYPE_CHECKING:
    from babylon.engine.graph_protocol import GraphProtocol
    from babylon.engine.services import ServiceContainer
    from babylon.engine.systems.protocol import ContextType

logger = logging.getLogger(__name__)

_STOCK_KEYS = ("raw_material_stock", "energy_stock", "biocapacity_stock")


class SubstrateSystem(SystemBase):
    """Pipeline slot 2.5: substrate stock update before Production.

    The system reads each hex's pre-tick substrate stocks
    (``raw_material_stock``, ``energy_stock``, ``biocapacity_stock``) from
    the graph, applies any depletion/regeneration this tick, and writes
    the post-tick values back to the graph node attributes. The values
    are then visible to :class:`ProductionSystem` in the same tick.

    Production hex-locality: this system does NOT cross hex boundaries.
    All depletion/regeneration is in-place per hex.
    """

    name: ClassVar[str] = "substrate"

    def step(
        self,
        graph: GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Update substrate stocks for every hex node.

        For the MVP, the stocks are passed through unchanged. The system
        slot itself is the load-bearing contribution: by occupying
        position 2.5, it guarantees Production reads post-Substrate
        values rather than pre-Substrate snapshots (US7 acceptance test).
        """
        _ = services  # Reserved for future depletion/regeneration coefficients.
        _ = context  # Tick/year metadata available via ``context["tick"]``.

        protocol = self._wrap_graph(graph)

        # Visit every hex node. We do NOT touch external nodes.
        hex_count = 0
        for node in list(protocol.query_nodes(node_type="hex")):
            hex_count += 1
            # Seed missing stocks with 0.0 (setdefault semantics). Concrete
            # dynamics (depletion rate × consumption, regeneration rate ×
            # biocapacity) land with the downstream physical-substrate spec.
            missing = {key: 0.0 for key in _STOCK_KEYS if key not in node.attributes}
            if missing:
                protocol.update_node(node.id, **missing)

        logger.debug("SubstrateSystem touched %d hex nodes", hex_count)


__all__ = ["SubstrateSystem"]
