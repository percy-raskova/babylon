"""GeographicFlow tensor source, ImperialRent computation, and aggregation.

Feature: 025-tensor-hierarchy
Date: 2026-02-26

Implements:
- DefaultGeographicFlowSource: Reads BTS FAF flows from SQLite.
- DefaultImperialRentComputer: Computes phi = inflow - outflow per CFS area.
- DefaultGeographicAggregator: Aggregates CFS Area flows to state level.

See Also:
    :mod:`babylon.economics.tensor_hierarchy.types`: GeographicFlow, ImperialRentField.
    :mod:`babylon.data.bts.faf_loader`: FAFLoader for ingesting FAF5 CSV data.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from babylon.economics.tensor import NoDataSentinel
from babylon.economics.tensor_hierarchy.types import (
    GeographicFlow,
    ImperialRentField,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# =============================================================================
# DEFAULT GEOGRAPHIC FLOW SOURCE
# =============================================================================


class DefaultGeographicFlowSource:
    """Reads BTS FAF commodity flows from SQLite.

    Reads from ``fact_faf_commodity_flow`` populated by FAFLoader.
    Returns GeographicFlow with the O-D flow matrix for a given year.

    Args:
        session_factory: Callable returning a SQLAlchemy Session context manager.

    Example:
        >>> source = DefaultGeographicFlowSource(session_factory)
        >>> flow = source.get_flow(2017)
        >>> print(f"Areas: {flow.n_areas}")
    """

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        """Initialize with session factory.

        Args:
            session_factory: Returns a Session context manager.
        """
        self._session_factory = session_factory
        self._available_years_cache: frozenset[int] | None = None

    def get_flow(self, year: int) -> GeographicFlow | NoDataSentinel:
        """Load O-D commodity flow matrix for a given year.

        Args:
            year: Calendar year (FAF5 data from 2012).

        Returns:
            GeographicFlow with CFS areas and flow matrix, or NoDataSentinel
            if no flow records exist for that year.
        """
        from babylon.data.reference.schema import DimCFSArea, FactFAFCommodityFlow

        with self._session_factory() as session:
            flows = (
                session.query(FactFAFCommodityFlow).filter(FactFAFCommodityFlow.year == year).all()
            )

            if not flows:
                return NoDataSentinel("national", year, f"No FAF commodity flows for year {year}")

            areas = session.query(DimCFSArea).order_by(DimCFSArea.cfs_code).all()
            code_list = [a.cfs_code for a in areas]
            code_to_idx: dict[str, int] = {c: i for i, c in enumerate(code_list)}
            id_to_code: dict[int, str] = {a.cfs_area_id: a.cfs_code for a in areas}

            n = len(code_list)
            matrix = np.zeros((n, n), dtype=np.float64)

            for flow in flows:
                orig_code = id_to_code.get(flow.origin_cfs_area_id)
                dest_code = id_to_code.get(flow.dest_cfs_area_id)
                if orig_code is None or dest_code is None:
                    continue
                orig_idx = code_to_idx.get(orig_code)
                dest_idx = code_to_idx.get(dest_code)
                if orig_idx is None or dest_idx is None:
                    continue
                value = float(flow.value_millions) if flow.value_millions is not None else 0.0
                matrix[orig_idx, dest_idx] += value

        return GeographicFlow(year=year, areas=code_list, flow_matrix=matrix)

    def available_years(self) -> frozenset[int]:
        """Return set of years with flow data available.

        Returns:
            Frozenset of years with loaded FAF flow records.
        """
        if self._available_years_cache is not None:
            return self._available_years_cache

        from babylon.data.reference.schema import FactFAFCommodityFlow

        with self._session_factory() as session:
            rows = session.query(FactFAFCommodityFlow.year).distinct().all()
            self._available_years_cache = frozenset(row[0] for row in rows)

        return self._available_years_cache


# =============================================================================
# DEFAULT IMPERIAL RENT COMPUTER
# =============================================================================


class DefaultImperialRentComputer:
    """Computes ImperialRentField from GeographicFlow.

    The imperial rent (phi) for each CFS area is:

    .. math::

        \\phi[a] = \\text{inflow}[a] - \\text{outflow}[a]

    where inflow[a] = sum of column a (all origins sending to dest a)
    and outflow[a] = sum of row a (all destinations receiving from origin a).

    For a closed system, sum(phi) = 0 exactly (value conservation).

    Positive phi: Area extracts value (core/accumulation zone).
    Negative phi: Area loses value (periphery/extraction zone).

    Example:
        >>> computer = DefaultImperialRentComputer()
        >>> rent = computer.compute_rent(flow)
        >>> assert abs(rent.phi.sum()) < 1e-9
    """

    def compute_rent(self, flow: GeographicFlow) -> ImperialRentField:
        """Compute net value extraction per CFS area.

        Args:
            flow: GeographicFlow with O-D matrix (F[orig, dest] = value).

        Returns:
            ImperialRentField with phi[a] = inflow[a] - outflow[a].
        """
        inflows = flow.flow_matrix.sum(axis=0)  # column sums = total received
        outflows = flow.flow_matrix.sum(axis=1)  # row sums = total sent
        phi = inflows - outflows

        return ImperialRentField(
            year=flow.year,
            areas=flow.areas,
            phi=phi,
        )

    def symmetric_component(self, flow: GeographicFlow) -> np.ndarray:
        """Extract the symmetric part of the flow matrix.

        S = (F + F^T) / 2 represents bilateral flows (bidirectional exchange).

        Args:
            flow: GeographicFlow with O-D matrix.

        Returns:
            Symmetric matrix S = (F + F^T) / 2, shape (n, n).
        """
        f = flow.flow_matrix
        result: np.ndarray = (f + f.T) / 2.0
        return result

    def antisymmetric_component(self, flow: GeographicFlow) -> np.ndarray:
        """Extract the antisymmetric part of the flow matrix.

        A = (F - F^T) / 2 represents net directional flows.
        A[i,j] > 0 means net flow from i to j.

        Args:
            flow: GeographicFlow with O-D matrix.

        Returns:
            Antisymmetric matrix A = (F - F^T) / 2, shape (n, n).
        """
        f = flow.flow_matrix
        result: np.ndarray = (f - f.T) / 2.0
        return result


# =============================================================================
# DEFAULT GEOGRAPHIC AGGREGATOR
# =============================================================================


class DefaultGeographicAggregator:
    """Aggregates CFS Area flows to state (or other geographic) level.

    Maps each CFS Area code to a target identifier (e.g., state abbreviation)
    via a user-provided mapping dictionary, then sums flows within and
    between target groups.

    Example:
        >>> aggregator = DefaultGeographicAggregator()
        >>> mapping = {"11": "MA", "12": "NY", "119": "NY"}
        >>> state_flow = aggregator.aggregate(flow, mapping)
        >>> state_flow.n_areas  # 2: MA, NY
        2
    """

    def aggregate(
        self,
        flow: GeographicFlow,
        mapping: dict[str, str],
    ) -> GeographicFlow:
        """Produce a target-level flow matrix by summing CFS area flows.

        Areas not present in mapping are excluded from the aggregated output.
        Total flow magnitude is preserved (sum of aggregated matrix ==
        sum of original matrix for mapped areas).

        Args:
            flow: GeographicFlow with CFS-area-level data.
            mapping: Dict mapping CFS code -> target identifier (e.g., state code).

        Returns:
            GeographicFlow with target identifiers as areas.
        """
        targets = sorted(set(mapping.values()))
        target_to_idx: dict[str, int] = {t: i for i, t in enumerate(targets)}
        n_targets = len(targets)

        area_to_target: dict[int, int] = {}
        for area_idx, area_code in enumerate(flow.areas):
            target = mapping.get(area_code)
            if target is not None and target in target_to_idx:
                area_to_target[area_idx] = target_to_idx[target]

        agg_matrix = np.zeros((n_targets, n_targets), dtype=np.float64)
        n = flow.n_areas

        for orig_idx in range(n):
            orig_target = area_to_target.get(orig_idx)
            if orig_target is None:
                continue
            for dest_idx in range(n):
                dest_target = area_to_target.get(dest_idx)
                if dest_target is None:
                    continue
                agg_matrix[orig_target, dest_target] += flow.flow_matrix[orig_idx, dest_idx]

        return GeographicFlow(
            year=flow.year,
            areas=targets,
            flow_matrix=agg_matrix,
        )


__all__ = [
    "DefaultGeographicAggregator",
    "DefaultGeographicFlowSource",
    "DefaultImperialRentComputer",
]
