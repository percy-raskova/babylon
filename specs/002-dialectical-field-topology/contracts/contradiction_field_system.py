"""Contract: ContradictionFieldSystem (System #14).

Computes named contradiction fields at every social-class node per tick
from existing economic calculator outputs.

Reference: FR-001 (extensible field computation)
Reference: FR-002 (tick-keyed history persistence)
Reference: FR-011 (reads from economic outputs, no duplication)
Reference: R-003 (storage architecture)
Reference: R-006 (system ordering — position 14)

System Protocol: step(graph, services, context) -> None
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from babylon.engine.graph_protocol import GraphProtocol
    from babylon.engine.services import ServiceContainer
    from babylon.engine.systems.protocol import ContextType


class ContradictionFieldSystemContract:
    """Contract for ContradictionFieldSystem.

    Execution Order: 14 (after all 13 existing economic systems)

    Inputs (read from graph nodes):
        - exploitation_rate (float): s/v from economic calculator
        - wages (float): current wage level
        - previous_wages (float): prior tick wage level (from persistent_data)
        - imperial_rent_share (float): node's share of imperial rent
        - population (float): current population
        - previous_population (float): prior tick population

    Outputs (written to graph nodes):
        - contradiction_fields: dict[str, float]
            Mapping of field_name -> normalized value [0.0, 10.0]
            e.g., {"exploitation": 7.2, "immiseration": 3.1, ...}

    Cross-tick state (persistent_data):
        - contradiction_history: dict[str, dict[str, list[float]]]
            node_id -> field_name -> [value_t-2, value_t-1, value_t]
            Rolling window of 3 most recent ticks per node per field.

    Invariants:
        - All field values in [0.0, 10.0] after normalization (EC-007)
        - History window never exceeds 3 entries per node per field
        - Field computation is field-name-agnostic (iterates registry)
        - No economic calculation is duplicated — reads outputs only
    """

    @property
    def name(self) -> str:
        """System identifier."""
        return "contradiction_field"

    def step(
        self,
        graph: GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Compute contradiction fields for all social-class nodes.

        Algorithm:
            1. Auto-wrap graph if not GraphProtocol
            2. Get field registry from services
            3. For each social-class node:
                a. For each registered field:
                    - Compute raw value from node attributes
                    - Normalize to [0.0, 10.0]
                    - Clamp and log if exceeded (EC-007)
                b. Write contradiction_fields dict to node
            4. Update contradiction_history in persistent_data
               (rolling window of 3 ticks)
        """
        ...
