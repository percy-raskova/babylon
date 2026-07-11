"""Production Chain Imperial Rent Calculator.

Calculates $Φ_j$ using the Leontief inverse and import shares.
"""

from __future__ import annotations

import logging
from typing import Protocol

import numpy as np

from babylon.domain.economics.tensor_hierarchy.types import (
    DecomposedFlow,
    Department,  # noqa: F401
    ImportShareVector,
    InterIndustryFlow,
    PeripheryLaborCoefficients,
    ProductionChainRentResult,
)

logger = logging.getLogger(__name__)


# =============================================================================
# PROTOCOLS
# =============================================================================


class ImportShareSource(Protocol):
    """Protocol for fetching Import Share fractions."""

    def get_import_shares(self, year: int) -> ImportShareVector:
        """Fetch import shares for a given year."""
        ...


class DBImportShareSource:
    """Calculates import shares m_j directly from the USE and IMPORT_USE tables in the DB."""

    def __init__(self, session_factory) -> None:  # type: ignore
        self.session_factory = session_factory

    def get_import_shares(self, year: int) -> ImportShareVector:
        """Calculate m_j = (sum of imports into j) / (sum of all intermediate inputs into j)."""
        from sqlalchemy import text

        # In actual practice, we might use ORM, but for raw speed we use text.
        # This assumes the table exists and data is loaded.
        query = text("""
            SELECT
                target.bea_code as industry_code,
                SUM(CASE WHEN tt.table_type = 'IMPORT_USE' THEN c.coefficient ELSE 0 END) as import_sum,
                SUM(CASE WHEN tt.table_type = 'USE' THEN c.coefficient ELSE 0 END) as total_sum
            FROM fact_bea_io_coefficient c
            JOIN dim_time t ON c.time_id = t.time_id
            JOIN dim_bea_io_table_type tt ON c.table_type_id = tt.id
            JOIN dim_bea_industry target ON c.target_industry_id = target.bea_industry_id
            WHERE t.year = :year
            GROUP BY target.bea_code
            ORDER BY target.bea_code
        """)

        with self.session_factory() as session:
            rows = session.execute(query, {"year": year}).mappings().all()

        industries = []
        shares = []
        for row in rows:
            industries.append(row["industry_code"])
            total = float(row["total_sum"])
            imports = float(row["import_sum"])
            # Fallback to 0.0 if there are no intermediate inputs
            m_j = imports / total if total > 0.0 else 0.0
            shares.append(m_j)

        return ImportShareVector(
            year=year, industries=industries, shares=np.array(shares, dtype=np.float64)
        )


class FinalDemandSource(Protocol):
    """Protocol for fetching Final Demand directly, or derived."""

    def get_final_demand(self, year: int) -> np.ndarray:
        """Fetch or derive final demand."""
        ...


# =============================================================================
# DECOMPOSER
# =============================================================================


class ProductionChainDecomposer:
    """Decomposes the generic BEA Direct Requirements matrix."""

    def decompose(self, flow: InterIndustryFlow, shares: ImportShareVector) -> DecomposedFlow:
        """Decompose A into A_d (domestic) and A_m (imports), and calculate L_d.

        Args:
            flow: The source InterIndustryFlow matrix A
            shares: The ImportShareVector m_j

        Returns:
            DecomposedFlow encapsulating A_d, A_m, and L_d
        """
        if flow.industries != shares.industries:
            msg = "Flow and Shares industry vectors must align perfectly."
            raise ValueError(msg)

        n = flow.n_industries
        m_j = shares.shares

        # A_m[i,j] = A[i,j] * m_j
        # A_d[i,j] = A[i,j] * (1 - m_j)
        # Assuming m_j is the fraction of total intermediate inputs in j that uses imported M

        # We broadcast m_j across rows (i.e. to multiply each column by m_j)
        A_m = flow.coefficients * m_j
        A_d = flow.coefficients * (1.0 - m_j)

        # L_d = (I - A_d)^-1
        identity = np.eye(n, dtype=np.float64)
        L_d = np.linalg.inv(identity - A_d)

        return DecomposedFlow(
            year=flow.year,
            industries=flow.industries,
            A_d=A_d,
            A_m=A_m,
            L_d=L_d,
        )

    def import_content_matrix(self, decomposed: DecomposedFlow) -> np.ndarray:
        """Compute the Import Content Matrix M = A_m @ L_d."""
        return decomposed.A_m @ decomposed.L_d  # type: ignore[no-any-return]


# =============================================================================
# CALCULATOR
# =============================================================================


class ProductionChainRentCalculator:
    """Calculates Leontief production-chain imperial rent."""

    def __init__(self) -> None:
        self.decomposer = ProductionChainDecomposer()

    def calculate(
        self,
        decomposed: DecomposedFlow,
        labor_coeffs: PeripheryLaborCoefficients,
        final_demand: np.ndarray,
        dept_mapping: dict[str, str] | None = None,
    ) -> ProductionChainRentResult:
        """Calculate the total and per-industry imperial rent extracted.

        Args:
            decomposed: The A_d, A_m and L_d components
            labor_coeffs: w_core / w_periphery ratio per industry
            final_demand: The y vector (derived as y = x - Ax)
            dept_mapping: Optional dict of industry_code -> Department

        Returns:
            ProductionChainRentResult encompassing vector and scalar phi
        """
        n = len(decomposed.industries)

        if len(final_demand) != n:
            msg = "Final demand array shape mismatch."
            raise ValueError(msg)

        # M = A_m @ L_d
        m_matrix = self.decomposer.import_content_matrix(decomposed)

        # Vectorized rent extraction calculation
        # Phi_j = sum_i(M[i,j] * (w_ratio_i - 1) * y_j)
        loss_ratio = labor_coeffs.wage_ratios - 1.0
        loss_ratio = np.maximum(loss_ratio, 0.0)  # ensure non-negative

        phi_vector = np.zeros(n, dtype=np.float64)
        for j in range(n):
            # Sum over all inputs i imported into the domestic production chain of j
            phi_j = np.sum(m_matrix[:, j] * loss_ratio * final_demand[j])
            phi_vector[j] = phi_j

        total_phi = float(np.sum(phi_vector))

        dept_phi: dict[Department, float] = {}
        if dept_mapping:
            pass  # We would populate this by iterating and aggregating

        return ProductionChainRentResult(
            year=decomposed.year,
            industries=decomposed.industries,
            phi_vector=phi_vector,
            total_phi=total_phi,
            dept_phi=dept_phi,
        )
