"""Volume II wage circulation via LODES commute flows.

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26

Redistributes variable capital (wages) from production hexes to
residence hexes using LODES origin-destination commute data.
Two-stage disaggregation: county-to-county flows from ``fact_lodes``
are distributed to hex-to-hex using tract employment weights.

Conservation: sum(v) preserved via explicit rescaling. The sparse matrix
multiply ``od_matrix.T @ v_vec`` with ~1000+ hexes accumulates ~1e-9
floating-point error, so circulation conservation uses a wider tolerance
(1e-8) than other operations (1e-10). See ``DefaultConservationChecker``.

See Also:
    :mod:`babylon.economics.substrate.types`: HexGrid, BoundaryFlowRegister.
    :mod:`babylon.economics.substrate.protocols`: CommuterFlowSource.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from babylon.economics.substrate.protocols import CommuterFlowSource
    from babylon.economics.substrate.types import BoundaryFlowRegister, HexEconomicState, HexGrid

logger = logging.getLogger(__name__)


class DefaultHexCirculationComputer:
    """Redistribute wages from production to residence hexes.

    Builds a sparse OD matrix from county-level LODES flows,
    disaggregated to hex-to-hex using tract employment weights.
    """

    # Spec 053 INV-001: substrate computer; conservation-preserving by
    # construction. Opt-out marker (default-deny per FR-004a).
    creates_value: ClassVar[bool] = False

    def build_od_matrix(
        self,
        grid: HexGrid,
        commuter_source: CommuterFlowSource,
        year: int,
    ) -> sparse.csr_matrix:
        """Build hex-to-hex OD sparse matrix from county flows.

        Args:
            grid: HexGrid with hex-to-county assignments.
            commuter_source: Source of county-level commuter flow data.
            year: LODES vintage year.

        Returns:
            Sparse CSR matrix (N_hexes x N_hexes), row-normalized.
        """
        hex_ids = sorted(grid.hexes.keys())
        n = len(hex_ids)
        hex_to_idx = {h: i for i, h in enumerate(hex_ids)}

        # Get county OD flows
        county_fips_list = list(grid.county_hex_ids.keys())
        od_flows = commuter_source.get_county_od_flows(county_fips_list, year)

        # Build sparse matrix
        rows: list[int] = []
        cols: list[int] = []
        data: list[float] = []

        for (home_county, work_county), flow in od_flows.items():
            if flow <= 0:
                continue

            home_hexes = list(grid.county_hex_ids.get(home_county, frozenset()))
            work_hexes = list(grid.county_hex_ids.get(work_county, frozenset()))

            if not home_hexes or not work_hexes:
                continue

            # Equal weight within county (simplified disaggregation)
            home_weight = 1.0 / len(home_hexes)
            work_weight = 1.0 / len(work_hexes)

            for w_hex in work_hexes:
                if w_hex not in hex_to_idx:
                    continue
                w_idx = hex_to_idx[w_hex]
                for h_hex in home_hexes:
                    if h_hex not in hex_to_idx:
                        continue
                    h_idx = hex_to_idx[h_hex]
                    flow_val = float(flow) * work_weight * home_weight
                    rows.append(w_idx)
                    cols.append(h_idx)
                    data.append(flow_val)

        if not rows:
            return sparse.csr_matrix((n, n), dtype=np.float64)

        od_matrix = sparse.coo_matrix((data, (rows, cols)), shape=(n, n), dtype=np.float64).tocsr()

        # Row-normalize: each row sums to 1.0
        row_sums = np.array(od_matrix.sum(axis=1)).flatten()
        row_sums[row_sums == 0] = 1.0  # Avoid division by zero
        inv_sums = sparse.diags(1.0 / row_sums)
        od_matrix = inv_sums @ od_matrix

        return od_matrix

    def circulate_wages(
        self,
        grid: HexGrid,
        od_matrix: sparse.csr_matrix,
    ) -> tuple[HexGrid, BoundaryFlowRegister]:
        """Redistribute variable capital from production to residence hexes.

        Args:
            grid: HexGrid with production-phase variable capital.
            od_matrix: Sparse OD matrix from :meth:`build_od_matrix`.

        Returns:
            Tuple of (updated HexGrid, BoundaryFlowRegister).
        """
        from babylon.economics.substrate.types import (
            BoundaryFlowRegister as BFR,
        )
        from babylon.economics.substrate.types import (
            HexGrid as HexGridType,
        )

        hex_ids = sorted(grid.hexes.keys())
        n = len(hex_ids)

        # Build v vector
        v_vec = np.array(
            [grid.hexes[h].variable_capital for h in hex_ids],
            dtype=np.float64,
        )

        pre_total_v = float(v_vec.sum())

        # Redistribute: v_residence = od_matrix.T @ v_production.
        #
        # Domain note: a row of zeros in the OD matrix means "this hex has
        # no commute outflow." The correct semantics is that those workers
        # stay home, so the hex's v stays in place. Without this treatment
        # the matrix multiply silently drops v[k] for any zero-row k,
        # violating the spec-053 INV-003 conservation invariant.
        if od_matrix.shape[0] == n and od_matrix.shape[1] == n:
            row_sums = np.asarray(od_matrix.sum(axis=1)).flatten()
            zero_row_mask = row_sums == 0.0
            if zero_row_mask.any():
                # Patch zero rows with an identity row so v[k] flows to k.
                identity_patch = sparse.diags(zero_row_mask.astype(np.float64))
                od_effective = od_matrix + identity_patch
            else:
                od_effective = od_matrix
            v_new = od_effective.T @ v_vec
        else:
            v_new = v_vec.copy()

        post_total_v = float(v_new.sum())

        # Rescale to conserve variable capital. The identity-patch above
        # eliminates the only systematic mass-loss source; the remaining
        # drift here is purely sparse-multiply round-off (~ULP per element).
        if post_total_v > 0 and abs(pre_total_v - post_total_v) > 1e-15:
            scale = pre_total_v / post_total_v
            v_new *= scale

        # Build updated hexes
        updated_hexes: dict[str, HexEconomicState] = {}
        for i, h3_id in enumerate(hex_ids):
            hex_state = grid.hexes[h3_id]
            new_v = float(v_new[i])

            # Recompute rates
            total_cv = hex_state.constant_capital + new_v
            profit_rate = hex_state.surplus_value / total_cv if total_cv > 0 else 0.0
            exploitation_rate = hex_state.surplus_value / new_v if new_v > 0 else 0.0

            updated_hexes[h3_id] = hex_state.model_copy(
                update={
                    "variable_capital": new_v,
                    "profit_rate": profit_rate,
                    "exploitation_rate": exploitation_rate,
                }
            )

        new_grid = HexGridType(
            hexes=updated_hexes,
            county_hex_ids=grid.county_hex_ids,
            res6_parents=grid.res6_parents,
            res5_parents=grid.res5_parents,
            res6_children=grid.res6_children,
            res5_children=grid.res5_children,
        )

        boundary = BFR(
            external_outflow_v=0.0,
            external_inflow_v=0.0,
            net_flow=0.0,
        )

        return new_grid, boundary


__all__ = [
    "DefaultHexCirculationComputer",
]
