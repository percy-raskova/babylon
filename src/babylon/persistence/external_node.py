"""Pydantic model for the dynamic_external_node_state Postgres row.

Spec 062, data-model.md §2.2. Each external node carries country-aggregate
state but no internal hex structure (FR-038). Eight international nodes
(Canada + 7 world regions per R4 amendment) plus one ``rest_of_usa``
domestic node form the boundary set.

See Also:
    ``specs/062-cross-scale-integration/contracts/persistence.yaml``.
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExternalNodeKind(StrEnum):
    """Discriminator between international and domestic external nodes.

    INTERNATIONAL: Canada, China, EU, India, Sub-Saharan Africa,
                   Latin America, Russia/CSI, Southeast Asia.
    DOMESTIC_REST: ``rest_of_usa`` (single sink for non-international,
                   non-study-area US flows).
    """

    INTERNATIONAL = "international"
    DOMESTIC_REST = "domestic_rest"


class ExternalNode(BaseModel):
    """One row of the ``dynamic_external_node_state`` table.

    The fixed external-node enumeration is locked to nine values to enforce
    FR-036/FR-037: ``canada``, ``china``, ``eu``, ``india``,
    ``sub_saharan_africa``, ``latin_america``, ``russia_csi``,
    ``southeast_asia`` (kind=international), plus ``rest_of_usa``
    (kind=domestic_rest).

    Per FR-038 the model has NO internal hex structure: no ``hexes``,
    ``hex_count``, ``h3_index``, ``internal_hexes`` field of any name.
    Enforced structurally by :mod:`test_external_node_no_hex_structure`.
    """

    model_config = ConfigDict(frozen=True)

    session_id: UUID
    tick: int = Field(ge=0)
    node_id: str = Field(min_length=1, max_length=64)
    kind: ExternalNodeKind

    phi_year_inflow: float = Field(ge=0)
    bilateral_trade_value: float = Field(ge=0)
    bilateral_trade_tons: float = Field(ge=0)
    erdi_ratio: float = Field(gt=0)


__all__ = ["ExternalNode", "ExternalNodeKind"]
