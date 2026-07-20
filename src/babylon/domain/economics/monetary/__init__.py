"""Value basis conversion and the monetary anchor (Capital Volume III).

Expresses economic values in nominal dollars, real (inflation-adjusted)
dollars, and labor-time (SNLT hours), and exposes the monetary anchor that
calibrates the value-price scissors against real federal data where it exists.

See Also:
    :mod:`babylon.domain.economics.melt`: MELT calculator and basket visibility
    :mod:`babylon.domain.economics.snlt`: Socially Necessary Labor Time computation
"""

from babylon.domain.economics.monetary.anchor import (
    NATIONAL_FIPS,
    UNKNOWN_YEAR,
    fictitious_anchor,
    serviceability_anchor,
)
from babylon.domain.economics.monetary.converter import (
    DefaultValueBasisConverter,
    ValueBasisConverter,
)
from babylon.domain.economics.monetary.data_sources import PriceIndexSource
from babylon.domain.economics.monetary.types import MonetaryAdjustment, ValueBasis

__all__: list[str] = [
    # Types
    "MonetaryAdjustment",
    "ValueBasis",
    # Data sources
    "PriceIndexSource",
    # Converter
    "DefaultValueBasisConverter",
    "ValueBasisConverter",
    # Anchor (design 2026-07-18 §3.3)
    "NATIONAL_FIPS",
    "UNKNOWN_YEAR",
    "fictitious_anchor",
    "serviceability_anchor",
]
