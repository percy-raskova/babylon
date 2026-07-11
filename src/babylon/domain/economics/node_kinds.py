"""Cross-scale node-kind and edge-kind enumerations.

Spec 062, data-model.md §2.3. The :class:`NodeKind` enum tells the
:class:`BoundaryFlowRegister` which ID space a dyadic flow lives in;
:class:`BoundaryEdgeKind` classifies the flow itself.

See Also:
    ``specs/062-cross-scale-integration/contracts/boundary_register.yaml``.
    :mod:`babylon.domain.economics.boundary_flow_register`.
"""

from __future__ import annotations

from enum import StrEnum


class NodeKind(StrEnum):
    """Identifier-space discriminator for boundary-register endpoints.

    HEX:      H3 res-7 index (15 chars).
    COUNTY:   5-digit FIPS county code.
    STATE:    2-digit FIPS state code.
    NATIONAL: "USA" (literal sentinel for the national aggregate).
    EXTERNAL: external_node.node_id (e.g., "canada", "china", "rest_of_usa").
    """

    HEX = "hex"
    COUNTY = "county"
    STATE = "state"
    NATIONAL = "national"
    EXTERNAL = "external"


class BoundaryEdgeKind(StrEnum):
    """Classification of a boundary flow's economic role.

    TRADE_EDGE:       Bidirectional value flow (FAF tons + Ricci $-value).
                      Positive magnitude = study-area export.
    DRAIN_EDGE:       Directional periphery → core Φ (Hickel drain).
    COMMUTE_OUT:      Vol II worker exit (study-area boundary).
    COMMUTE_IN:       Vol II worker entry (study-area boundary).
    PHYSICAL_EXCHANGE: FAF freight or USGS minerals.
    """

    TRADE_EDGE = "trade_edge"
    DRAIN_EDGE = "drain_edge"
    COMMUTE_OUT = "commute_out"
    COMMUTE_IN = "commute_in"
    PHYSICAL_EXCHANGE = "physical_exchange"


__all__ = ["NodeKind", "BoundaryEdgeKind"]
