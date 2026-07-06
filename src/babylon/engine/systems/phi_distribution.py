"""Imperial-rent Φ distribution to counties (Spec 062 T058 / FR-034 / FR-035).

For each external node carrying ``phi_year_inflow``, the weekly slice is
``phi_year_inflow / 52``. That slice is distributed across US counties
weighted by the county's exposure to that external node's trading sector
(BEA I-O imports × QCEW industry shares). For the MVP the exposure weights
are passed in by the caller; downstream specs will compute them from the
hydrated `immutable_reference_bea_io` and `immutable_reference_qcew_employment`
tables.

Every transfer is recorded as a `DRAIN_EDGE` boundary register row from
the external node to the receiving county (Constitution II.9 dyadic
morphism + R2 hex-pair schema).

See Also:
    ``specs/062-cross-scale-integration/spec.md`` FR-034 / FR-035.
    :mod:`babylon.economics.boundary_flow_register`:
        :class:`BoundaryFlowRegister`.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from uuid import UUID

from babylon.economics.boundary_flow_register import (
    BoundaryEdgeKind,
    BoundaryFlowRegister,
    NodeKind,
)

logger = logging.getLogger(__name__)


def distribute_phi_week_to_counties(
    *,
    session_id: UUID,
    tick: int,
    external_node_id: str,
    phi_year_inflow: float,
    county_exposure: Mapping[str, float],
    register: BoundaryFlowRegister,
    weeks_per_year: float = 52.0,
) -> dict[str, float]:
    """Distribute one external node's weekly Φ across US counties.

    The weekly Φ slice is ``phi_year_inflow / weeks_per_year`` per FR-035.
    Each county receives a share equal to its exposure weight (the weights
    MUST sum to 1.0; a non-unit sum is treated as a calling-side bug per
    Constitution III.1 — no silent renormalization).

    Args:
        session_id: Owning session UUID for the boundary register rows.
        tick: Simulation tick (>=0).
        external_node_id: The source external node (e.g., "canada").
        phi_year_inflow: Annual Φ inflow from this external node.
        county_exposure: ``{county_fips: weight}`` map; weights MUST sum to 1.
        register: BoundaryFlowRegister buffer to receive DRAIN_EDGE rows.
        weeks_per_year: Ticks per simulation year (default 52, matching
            ``GameDefines.timescale.weeks_per_year`` — spec-101 review minor:
            sourced from a single caller-supplied value rather than an
            independently-hardcoded literal in each consuming module).

    Returns:
        ``{county_fips: phi_amount}`` showing the per-county weekly Φ.

    Raises:
        ValueError: If ``phi_year_inflow`` is negative, or if the exposure
            weights do not sum to 1 within 1e-9.

    Example (Detroit-Windsor placeholder):
        Canada has ``phi_year_inflow = 100_000_000`` for 2010. Weekly
        slice is ``1_923_076.92``. Wayne County (26163) has exposure 0.6;
        Oakland (26125) has exposure 0.4. The auditor sums all three
        weekly slices on year-boundary tick 51 and asserts the total
        equals the annual figure to within ε.
    """
    if phi_year_inflow < 0:
        raise ValueError(f"phi_year_inflow must be non-negative; got {phi_year_inflow!r}")
    if not county_exposure:
        return {}

    weight_sum = sum(county_exposure.values())
    if abs(weight_sum - 1.0) > 1e-9:
        raise ValueError(
            f"county_exposure weights must sum to 1.0 (got {weight_sum!r}); "
            f"non-unit sums signal a caller bug — no silent renormalization."
        )

    phi_week = phi_year_inflow / weeks_per_year
    transfers: dict[str, float] = {}
    for county_fips, weight in county_exposure.items():
        amount = phi_week * weight
        transfers[county_fips] = amount
        register.record(
            session_id=session_id,
            tick=tick,
            source_node_id=external_node_id,
            source_kind=NodeKind.EXTERNAL,
            dest_node_id=county_fips,
            dest_kind=NodeKind.COUNTY,
            flow_type=BoundaryEdgeKind.DRAIN_EDGE,
            magnitude=amount,
        )
    return transfers


__all__ = ["distribute_phi_week_to_counties"]
