"""MarxianHydrator for transforming QCEW data into Marxian value tensors.

The hydrator is a pure transformation service that converts county-level
QCEW wage data into 4x3 Marxian reproduction schema tensors. It uses:

1. DepartmentMapper: Maps NAICS codes to departments (I, IIa, IIb, III)
2. BEADataSource: Provides industry c/v and s/v ratios (with YAML fallbacks)
3. QCEWDataSource: Provides county-level wage data by NAICS code

Example:
    >>> from babylon.economics.hydrator import MarxianHydrator
    >>> hydrator = MarxianHydrator(qcew_source, bea_source, dept_mapper)
    >>> tensor = hydrator.hydrate("26163", 2022)  # Wayne County, MI
    >>> tensor.dept_I.organic_composition
    3.0

See Also:
    :mod:`babylon.economics.tensor`: ValueTensor4x3 output format.
    :mod:`babylon.economics.department_mapper`: NAICS to department mapping.
    :mod:`babylon.economics.adapters`: Data source protocols.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.economics.adapters import BEADataSource, QCEWDataSource
from babylon.economics.department_mapper import Department, DepartmentMapper
from babylon.economics.tensor import DepartmentRow, ValueTensor4x3

if TYPE_CHECKING:
    pass


class MarxianHydrator:
    """Transforms QCEW wage data into Marxian value tensors.

    The hydrator performs a pure transformation: it takes county-level wage
    data and produces a ValueTensor4x3 representing the Marxian reproduction
    schema with four departments, each decomposed into c, v, s.

    The transformation algorithm:
    1. Fetch QCEW wages by NAICS for the county-year
    2. Allocate wages to departments via DepartmentMapper
    3. Track excluded wages (NAICS 92 government) as metadata
    4. For each department:
       - Get weighted s/v ratio from BEA (or YAML default)
       - Get weighted c/v ratio from BEA (or YAML default)
       - Compute s = v * sv_ratio
       - Compute c = v * cv_ratio
    5. Compute naics_granularity metric
    6. Return immutable ValueTensor4x3

    Args:
        qcew_source: Data source for QCEW wage data.
        bea_source: Data source for BEA industry ratios.
        dept_mapper: NAICS-to-department mapper with default ratios.

    Example:
        >>> hydrator = MarxianHydrator(qcew_source, bea_source, dept_mapper)
        >>> wayne = hydrator.hydrate("26163", 2022)
        >>> oakland = hydrator.hydrate("26125", 2022)
        >>> oakland.dept_IIb.v / oakland.dept_IIa.v > wayne.dept_IIb.v / wayne.dept_IIa.v
        True  # Gentrification signal
    """

    def __init__(
        self,
        qcew_source: QCEWDataSource,
        bea_source: BEADataSource,
        dept_mapper: DepartmentMapper,
    ) -> None:
        """Initialize the hydrator with data sources and mapper.

        Args:
            qcew_source: Source for QCEW wage data (implements QCEWDataSource).
            bea_source: Source for BEA industry ratios (implements BEADataSource).
            dept_mapper: NAICS-to-department mapper with default ratios.
        """
        self._qcew_source = qcew_source
        self._bea_source = bea_source
        self._dept_mapper = dept_mapper

    def hydrate(self, fips_code: str, year: int) -> ValueTensor4x3:
        """Transform QCEW data into a Marxian value tensor.

        This is the main transformation method. It is a pure function:
        given the same inputs and data sources, it produces the same output.

        Args:
            fips_code: 5-digit FIPS county code.
            year: Data year.

        Returns:
            ValueTensor4x3 with c, v, s for each department.
        """
        # Step 1: Fetch QCEW wages by NAICS
        qcew_records = self._qcew_source.fetch_county_wages(fips_code, year)

        # Step 2 & 3: Allocate wages to departments, tracking exclusions
        dept_wages: dict[Department, float] = dict.fromkeys(Department, 0.0)
        excluded_wages: float = 0.0
        total_wages: float = 0.0
        granular_wages: float = 0.0  # Wages with 6-digit NAICS

        for naics_code, wages, _employment in qcew_records:
            total_wages += wages
            allocation = self._dept_mapper.get_allocation(naics_code)

            if allocation is None:
                # Excluded sector (e.g., government NAICS 92)
                excluded_wages += wages
            else:
                # Allocate to departments
                allocated = allocation.allocate(wages)
                for dept, amt in allocated.items():
                    dept_wages[dept] += amt

                # Track granularity (6-digit codes are most specific)
                if len(naics_code.strip()) >= 6:
                    granular_wages += wages

        # Step 4: Compute c and s for each department using ratios
        dept_rows: dict[Department, DepartmentRow] = {}

        for dept in Department:
            v = dept_wages[dept]

            # Get weighted ratios from BEA or fall back to defaults
            sv_ratio = self._get_dept_sv_ratio(dept, qcew_records, year)
            cv_ratio = self._get_dept_cv_ratio(dept, qcew_records, year)

            # Compute s and c from v and ratios
            s = v * sv_ratio
            c = v * cv_ratio

            dept_rows[dept] = DepartmentRow(c=c, v=v, s=s)

        # Step 5: Compute naics_granularity metric
        allocated_wages = total_wages - excluded_wages
        naics_granularity = granular_wages / allocated_wages if allocated_wages > 0 else 0.0

        # Clamp to [0, 1] for safety
        naics_granularity = max(0.0, min(1.0, naics_granularity))

        # Step 6: Return immutable tensor
        return ValueTensor4x3(
            fips_code=fips_code,
            year=year,
            dept_I=dept_rows[Department.I],
            dept_IIa=dept_rows[Department.IIa],
            dept_IIb=dept_rows[Department.IIb],
            dept_III=dept_rows[Department.III],
            naics_granularity=naics_granularity,
            excluded_wages=excluded_wages,
        )

    def _get_dept_sv_ratio(
        self,
        dept: Department,
        qcew_records: list[tuple[str, float, int]],
        year: int,
    ) -> float:
        """Get weighted s/v ratio for a department.

        Lookup order for each NAICS code:
        1. BEA source (industry-level empirical data)
        2. Sector-level ratios (2-digit NAICS from YAML)
        3. Department default (if nothing found)

        Args:
            dept: Target department.
            qcew_records: QCEW records for weighting.
            year: Data year.

        Returns:
            Weighted s/v ratio or department default.
        """
        ratios: list[tuple[float, float]] = []  # (ratio, weight)

        for naics_code, wages, _employment in qcew_records:
            allocation = self._dept_mapper.get_allocation(naics_code)
            if allocation is None:
                continue

            # Get weight for this department
            dept_weight = getattr(allocation, dept.value, 0.0)
            if dept_weight == 0.0:
                continue

            weighted_wages = wages * dept_weight

            # Try to get BEA ratio first (most specific)
            bea_ratio = self._bea_source.get_sv_ratio(naics_code, year)
            if bea_ratio is not None:
                ratios.append((bea_ratio, weighted_wages))
                continue

            # Fall back to sector-level ratio (2-digit NAICS)
            sector = naics_code[:2]
            sector_ratio = self._dept_mapper.get_sector_sv_ratio(sector)
            if sector_ratio is not None:
                ratios.append((sector_ratio, weighted_wages))

        # Calculate weighted average if we have any ratios
        if ratios:
            total_weight = sum(w for _, w in ratios)
            if total_weight > 0:
                weighted_avg = sum(r * w for r, w in ratios) / total_weight
                return weighted_avg

        # Fall back to department default
        return self._dept_mapper.get_default_sv_ratio(dept)

    def _get_dept_cv_ratio(
        self,
        dept: Department,
        qcew_records: list[tuple[str, float, int]],
        year: int,
    ) -> float:
        """Get weighted c/v ratio for a department.

        Lookup order for each NAICS code:
        1. BEA source (industry-level empirical data)
        2. Sector-level ratios (2-digit NAICS from YAML)
        3. Department default (if nothing found)

        Args:
            dept: Target department.
            qcew_records: QCEW records for weighting.
            year: Data year.

        Returns:
            Weighted c/v ratio or department default.
        """
        ratios: list[tuple[float, float]] = []  # (ratio, weight)

        for naics_code, wages, _employment in qcew_records:
            allocation = self._dept_mapper.get_allocation(naics_code)
            if allocation is None:
                continue

            # Get weight for this department
            dept_weight = getattr(allocation, dept.value, 0.0)
            if dept_weight == 0.0:
                continue

            weighted_wages = wages * dept_weight

            # Try to get BEA ratio first (most specific)
            bea_ratio = self._bea_source.get_cv_ratio(naics_code, year)
            if bea_ratio is not None:
                ratios.append((bea_ratio, weighted_wages))
                continue

            # Fall back to sector-level ratio (2-digit NAICS)
            sector = naics_code[:2]
            sector_ratio = self._dept_mapper.get_sector_cv_ratio(sector)
            if sector_ratio is not None:
                ratios.append((sector_ratio, weighted_wages))

        # Calculate weighted average if we have any ratios
        if ratios:
            total_weight = sum(w for _, w in ratios)
            if total_weight > 0:
                weighted_avg = sum(r * w for r, w in ratios) / total_weight
                return weighted_avg

        # Fall back to department default
        return self._dept_mapper.get_default_cv_ratio(dept)


__all__ = [
    "MarxianHydrator",
]
