"""Derived tensor metrics for TRPF analysis.

This module provides the DerivedTensorMetrics container, which combines
primitive tensor data with derived capital stock to provide comprehensive
economic metrics for Tendency of the Rate of Profit to Fall (TRPF) analysis.

Theoretical Foundation:
    The TRPF (Marx, Capital Vol. III) predicts that as the organic composition
    of capital (OCC = c/v) rises over time, the rate of profit tends to fall.

    This module distinguishes two profit rate measures:

    **Flow-based profit rate** (per-period turnover)::

        r_flow = s / (c + v)

    This is the existing `profit_rate` on ValueTensor4x3 and measures
    profit relative to capital turned over during a single period.

    **Stock-based profit rate** (accumulated capital, TVT Section 3.6)::

        r_stock = s / (K + v)

    This measures profit relative to the total accumulated capital stock K,
    which better captures the TRPF dynamic since K grows with accumulated
    investment while s is limited by living labor (v).

Key Distinction:
    Flow-based rate: Useful for analyzing single-period efficiency
    Stock-based rate: Necessary for testing TRPF, which concerns
    the accumulation dynamics of capital over time

    As OCC rises (more machinery per worker), K grows faster than s can grow
    (since s comes from exploiting living labor v), causing r_stock to fall.

Example:
    >>> from babylon.domain.economics.capital_stock import CapitalStockCalculator
    >>> metrics = calculator.get_metrics("26163", 2022)
    >>> if metrics:
    ...     print(f"Stock profit rate: {metrics.profit_rate_stock:.4f}")
    ...     print(f"Flow profit rate: {metrics.profit_rate_flow:.4f}")
    ...     print(f"OCC: {metrics.organic_composition:.2f}")

See Also:
    :class:`babylon.domain.economics.capital_stock.CapitalStockCalculator`: Computes K and metrics.
    :class:`babylon.domain.economics.tensor.ValueTensor4x3`: Source tensor with flow-based rate.
    TVT Section 3.6: Stock-based profit rate formula.
    TVT Prediction 9: TRPF hypothesis specification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from babylon.domain.economics.tensor import ValueTensor4x3

__all__ = [
    "DerivedTensorMetrics",
]


@dataclass(frozen=True)
class DerivedTensorMetrics:
    """Container for derived economic ratios computed from tensor + capital stock.

    This is the primary output type for TRPF analysis, combining primitive
    tensor data with derived capital stock K.

    The key distinction between flow-based and stock-based profit rates:

    - **profit_rate_flow** = s/(c+v): Per-period turnover measure from tensor
    - **profit_rate_stock** = s/(K+v): Accumulated capital measure for TRPF

    The stock-based rate uses capital stock K instead of period flow c.
    This captures the TRPF dynamic: as capital accumulates (K grows),
    surplus value s (extracted from living labor v) cannot keep pace,
    causing the profit rate to fall over time.

    Attributes:
        fips_code: 5-digit FIPS county code.
        year: Calendar year.
        capital_stock: K (accumulated capital stock in labor-hours).
        profit_rate_stock: r = s / (K + v) (stock-based profit rate).
        organic_composition: OCC = c / v (from tensor).
        exploitation_rate: e = s / v (from tensor).
        tensor: Source ValueTensor4x3.
        depreciation_rate: δ used for K computation.

    Example:
        >>> metrics = calculator.get_metrics("26163", 2022)
        >>> if metrics:
        ...     print(f"Stock-based profit rate: {metrics.profit_rate_stock:.4f}")
        ...     print(f"OCC: {metrics.organic_composition:.2f}")
    """

    fips_code: str
    year: int
    capital_stock: float  # K
    profit_rate_stock: float  # r = s / (K + v)
    organic_composition: float  # c / v
    exploitation_rate: float  # s / v
    tensor: ValueTensor4x3
    depreciation_rate: float

    @property
    def profit_rate_flow(self) -> float:
        """Flow-based profit rate s/(c+v) from underlying tensor.

        This is the per-period profit rate measuring return on capital
        turned over during a single period. It differs from the stock-based
        rate which uses accumulated capital stock K.

        Flow-based: r = s / (c + v) - period turnover
        Stock-based: r = s / (K + v) - accumulated capital (TRPF measure)

        Returns:
            Flow-based profit rate from tensor.profit_rate.
        """
        return self.tensor.profit_rate

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for analysis/export.

        Returns:
            Dictionary with all metrics suitable for DataFrame creation
            or JSON serialization. Includes both computed metrics and
            source tensor totals.

        Example:
            >>> import pandas as pd
            >>> data = [m.to_dict() for m in metrics_list if m]
            >>> df = pd.DataFrame(data)
        """
        return {
            "fips_code": self.fips_code,
            "year": self.year,
            "capital_stock": self.capital_stock,
            "profit_rate_stock": self.profit_rate_stock,
            "profit_rate_flow": self.profit_rate_flow,
            "organic_composition": self.organic_composition,
            "exploitation_rate": self.exploitation_rate,
            "depreciation_rate": self.depreciation_rate,
            "total_c": float(self.tensor.total_c),
            "total_v": float(self.tensor.total_v),
            "total_s": float(self.tensor.total_s),
        }
