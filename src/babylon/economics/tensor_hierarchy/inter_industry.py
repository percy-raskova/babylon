"""InterIndustryFlow tensor source and Leontief computation.

Feature: 025-tensor-hierarchy
Date: 2026-02-26

Implements:
- DefaultInterIndustryFlowSource: Reads BEA I-O coefficients from SQLite.
- DefaultLeontiefComputer: Computes L = (I - A)^{-1}.
- DefaultDepartmentAggregator: Aggregates ~70 BEA industries to 4 Marxian departments.

See Also:
    :mod:`babylon.economics.tensor_hierarchy.types`: InterIndustryFlow, LeontiefInverse.
    :mod:`babylon.data.bea.io_loader`: BEAIOLoader for ingesting XLSX data.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from babylon.economics.tensor import NoDataSentinel
from babylon.economics.tensor_hierarchy.types import (
    Department,
    InterIndustryFlow,
    IOTableType,
    LeontiefInverse,
)
from babylon.economics.tensor_hierarchy.validation import (
    validate_io_column_sums,
    validate_leontief_properties,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Path to TOML mapping (relative to this file)
_TOML_PATH = Path(__file__).parent / "mappings" / "bea_to_department.toml"


# =============================================================================
# DEFAULT INTER-INDUSTRY FLOW SOURCE
# =============================================================================


class DefaultInterIndustryFlowSource:
    """Reads BEA I-O direct requirements coefficients from SQLite.

    Reads from fact_bea_io_coefficient populated by BEAIOLoader.
    Returns InterIndustryFlow with the A matrix for a given year.

    Args:
        session_factory: Callable returning a SQLAlchemy Session context manager.

    Example:
        >>> source = DefaultInterIndustryFlowSource(session_factory)
        >>> flow = source.get_direct_requirements(2021)
        >>> print(f"Industries: {flow.n_industries}")
    """

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        """Initialize with session factory.

        Args:
            session_factory: Returns a Session context manager.
        """
        self._session_factory = session_factory
        self._industry_codes_cache: list[str] | None = None
        self._available_years_cache: frozenset[int] | None = None

    def get_direct_requirements(self, year: int) -> InterIndustryFlow | NoDataSentinel:
        """Load the direct requirements coefficient matrix A for a given year.

        Args:
            year: Calendar year for the I-O table.

        Returns:
            InterIndustryFlow with the A matrix, or NoDataSentinel if unavailable.
        """
        from babylon.reference.schema import (
            DimBEAIndustry,
            DimBEAIOTableType,
            DimTime,
            FactBEAIOCoefficient,
        )

        with self._session_factory() as session:
            # Look up time_id for this year
            time_rec = (
                session.query(DimTime)
                .filter(DimTime.year == year, DimTime.is_annual.is_(True))
                .first()
            )
            if time_rec is None:
                return NoDataSentinel(
                    "national", year, f"No time record for year {year} in dim_time"
                )

            # Look up USE table type
            table_type_rec = (
                session.query(DimBEAIOTableType)
                .filter(DimBEAIOTableType.table_type == "USE")
                .first()
            )
            if table_type_rec is None:
                return NoDataSentinel(
                    "national", year, "No USE table type in dim_bea_io_table_type"
                )

            # Load all coefficients for this year + USE table
            coeffs = (
                session.query(FactBEAIOCoefficient)
                .filter(
                    FactBEAIOCoefficient.time_id == time_rec.time_id,
                    FactBEAIOCoefficient.table_type_id == table_type_rec.id,
                )
                .all()
            )

            if not coeffs:
                return NoDataSentinel(
                    "national",
                    year,
                    f"No I-O coefficients in fact_bea_io_coefficient for year {year}",
                )

            # Build ordered industry list from dim_bea_industry
            industries = (
                session.query(DimBEAIndustry)
                .order_by(DimBEAIndustry.line_number, DimBEAIndustry.bea_code)
                .all()
            )
            code_list = [ind.bea_code for ind in industries]
            code_to_idx: dict[str, int] = {c: i for i, c in enumerate(code_list)}
            n = len(code_list)

            # Build id -> code map
            id_to_code: dict[int, str] = {ind.bea_industry_id: ind.bea_code for ind in industries}

            # Fill matrix
            matrix = np.zeros((n, n), dtype=np.float64)
            for coeff in coeffs:
                src_code = id_to_code.get(coeff.source_industry_id)
                tgt_code = id_to_code.get(coeff.target_industry_id)
                if src_code is None or tgt_code is None:
                    continue
                src_idx = code_to_idx.get(src_code)
                tgt_idx = code_to_idx.get(tgt_code)
                if src_idx is None or tgt_idx is None:
                    continue
                matrix[src_idx, tgt_idx] = coeff.coefficient

        return InterIndustryFlow(
            year=year,
            table_type=IOTableType.USE,
            industries=code_list,
            coefficients=matrix,
        )

    def get_industry_codes(self) -> list[str]:
        """Return ordered list of BEA industry codes at Summary level.

        Returns:
            List of BEA Summary-level industry codes in canonical order.
        """
        if self._industry_codes_cache is not None:
            return self._industry_codes_cache

        from babylon.reference.schema import DimBEAIndustry

        with self._session_factory() as session:
            industries = (
                session.query(DimBEAIndustry)
                .order_by(DimBEAIndustry.line_number, DimBEAIndustry.bea_code)
                .all()
            )
            self._industry_codes_cache = [ind.bea_code for ind in industries]

        return self._industry_codes_cache

    def available_years(self) -> frozenset[int]:
        """Return set of years with I-O data available.

        Returns:
            Frozenset of years with loaded coefficient data.
        """
        if self._available_years_cache is not None:
            return self._available_years_cache

        from babylon.reference.schema import DimTime, FactBEAIOCoefficient

        with self._session_factory() as session:
            time_ids = session.query(FactBEAIOCoefficient.time_id).distinct().all()
            if not time_ids:
                self._available_years_cache = frozenset()
                return self._available_years_cache

            tid_list = [row[0] for row in time_ids]
            times = session.query(DimTime).filter(DimTime.time_id.in_(tid_list)).all()
            self._available_years_cache = frozenset(t.year for t in times)

        return self._available_years_cache


# =============================================================================
# DEFAULT LEONTIEF COMPUTER
# =============================================================================


class DefaultLeontiefComputer:
    """Computes Leontief inverse L = (I - A)^{-1} from InterIndustryFlow.

    The Leontief inverse captures both direct and indirect supply chain
    requirements. Element L[i,j] is the total output of industry i needed
    per unit of final demand for industry j.

    Example:
        >>> computer = DefaultLeontiefComputer()
        >>> inverse = computer.compute_inverse(flow)
        >>> computer.total_labor_coefficients(inverse, direct_labor)
    """

    def compute_inverse(self, flow: InterIndustryFlow) -> LeontiefInverse:
        """Compute L = (I - A)^{-1}.

        Validates that the resulting matrix satisfies Leontief properties
        (non-negative elements, diagonal >= 1.0).

        Args:
            flow: InterIndustryFlow with direct requirements matrix A.

        Returns:
            LeontiefInverse with the total requirements matrix.

        Raises:
            numpy.linalg.LinAlgError: If (I - A) is singular.
        """
        a_matrix = flow.coefficients
        n = a_matrix.shape[0]
        i_minus_a = np.eye(n) - a_matrix

        # Validate Hawkins-Simon condition before attempting inversion
        valid, msg = validate_io_column_sums(a_matrix)
        if not valid and msg:
            logger.warning("I-O matrix may not be invertible: %s", msg)

        inverse = np.linalg.inv(i_minus_a)

        # Validate Leontief properties
        valid, msg = validate_leontief_properties(inverse)
        if not valid and msg:
            logger.warning("Leontief inverse properties violated: %s", msg)

        return LeontiefInverse(
            year=flow.year,
            industries=flow.industries,
            inverse_matrix=inverse,
        )

    def total_labor_coefficients(
        self,
        leontief: LeontiefInverse,
        direct_labor: np.ndarray,
    ) -> np.ndarray:
        """Compute total labor (direct + indirect) per unit of final demand.

        Formula: l_total = l_direct @ L
        where l_direct[j] is direct labor hours per dollar of industry j output.

        Args:
            leontief: LeontiefInverse matrix L.
            direct_labor: Direct labor coefficients, shape (n,).

        Returns:
            Total labor coefficients, shape (n,).
        """
        result: np.ndarray = direct_labor @ leontief.inverse_matrix
        return result


# =============================================================================
# DEFAULT DEPARTMENT AGGREGATOR
# =============================================================================


class DefaultDepartmentAggregator:
    """Aggregates ~70 BEA industries to 4 Marxian departments via TOML mapping.

    Loads the BEA-to-department mapping from bea_to_department.toml and
    produces a 4x4 department-level I-O matrix via weighted aggregation.
    Weights are industry output shares (column sums of A relative to total).

    Example:
        >>> aggregator = DefaultDepartmentAggregator()
        >>> mapping = aggregator.get_default_mapping()
        >>> dept_flow = aggregator.aggregate(flow, mapping)
        >>> dept_flow.n_industries
        4
    """

    _DEPT_ORDER = [Department.I, Department.IIA, Department.IIB, Department.III]

    def get_default_mapping(self) -> dict[str, str]:
        """Load the BEA-to-department mapping from TOML data file.

        Returns:
            Dict mapping BEA Summary industry code -> Department value string
            (e.g. "111CA" -> "I", "621" -> "III").
        """
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]

        if not _TOML_PATH.exists():
            logger.warning("TOML mapping not found at %s", _TOML_PATH)
            return {}

        with _TOML_PATH.open("rb") as f:
            data = tomllib.load(f)

        mapping: dict[str, str] = {}
        departments = data.get("departments", {})
        for dept_key, codes in departments.items():
            for code in codes:
                mapping[code] = dept_key

        return mapping

    def aggregate(self, flow: InterIndustryFlow, mapping: dict[str, str]) -> InterIndustryFlow:
        """Produce a 4x4 department-level I-O matrix.

        Uses weighted aggregation: each industry's contribution to its
        department is proportional to its output share (column sum weight).

        Args:
            flow: InterIndustryFlow with industry-level A matrix.
            mapping: Dict mapping BEA industry code -> Department value string.

        Returns:
            InterIndustryFlow with 4 departments as industries (order: I, IIA, IIB, III).
        """
        n = flow.n_industries
        dept_labels = [d.value for d in self._DEPT_ORDER]
        n_dept = len(dept_labels)

        # Assign each industry to a department (0-indexed in _DEPT_ORDER)
        dept_values = [d.value for d in self._DEPT_ORDER]
        industry_to_dept: dict[int, int] = {}
        for idx, code in enumerate(flow.industries):
            dept_str = mapping.get(code)
            if dept_str is not None and dept_str in dept_values:
                industry_to_dept[idx] = dept_values.index(dept_str)
            # Industries not in mapping are dropped (treated as unmapped)

        # Compute output shares for weighting (sum of each column of A)
        col_sums = flow.coefficients.sum(axis=0)
        # Avoid division by zero: industries with zero col_sum get equal weight
        total_col_sum = col_sums.sum()
        if total_col_sum > 0.0:
            weights = col_sums / total_col_sum
        else:
            weights = np.ones(n, dtype=np.float64) / n

        # Build 4x4 aggregated matrix
        dept_matrix = np.zeros((n_dept, n_dept), dtype=np.float64)
        dept_weights = np.zeros(n_dept, dtype=np.float64)

        # Accumulate column weights per department
        for col_idx in range(n):
            dept_idx = industry_to_dept.get(col_idx)
            if dept_idx is not None:
                dept_weights[dept_idx] += weights[col_idx]

        # Fill department matrix
        for src_idx in range(n):
            src_dept = industry_to_dept.get(src_idx)
            if src_dept is None:
                continue
            for tgt_idx in range(n):
                tgt_dept = industry_to_dept.get(tgt_idx)
                if tgt_dept is None:
                    continue
                coeff = flow.coefficients[src_idx, tgt_idx]
                if coeff == 0.0:
                    continue
                w = weights[tgt_idx]
                dept_col_w = dept_weights[tgt_dept]
                if dept_col_w > 0.0:
                    dept_matrix[src_dept, tgt_dept] += coeff * (w / dept_col_w)

        return InterIndustryFlow(
            year=flow.year,
            table_type=flow.table_type,
            industries=dept_labels,
            coefficients=dept_matrix,
        )


__all__ = [
    "DefaultDepartmentAggregator",
    "DefaultInterIndustryFlowSource",
    "DefaultLeontiefComputer",
]
