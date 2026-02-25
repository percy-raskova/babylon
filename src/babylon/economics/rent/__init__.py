"""Ground rent extraction module (Capital Volume III).

Decomposes ground rent by category (agricultural, resource, urban) and
housing value into construction, capitalized rent, and speculative premium.

See Also:
    :mod:`babylon.economics.distribution`: Surplus value distribution
    :mod:`babylon.economics.tensor`: ValueTensor4x3 production data
"""

from babylon.economics.rent.calculator import (
    DefaultHousingDecompositionCalculator,
    DefaultRentCalculator,
    HousingDecompositionCalculator,
    RentCalculator,
)
from babylon.economics.rent.data_sources import (
    CountyRentalIncomeSource,
    HousingDataSource,
)
from babylon.economics.rent.types import (
    HousingValueDecomposition,
    RentCategory,
    RentExtraction,
)

__all__: list[str] = [
    # Types
    "RentCategory",
    "RentExtraction",
    "HousingValueDecomposition",
    # Protocols
    "RentCalculator",
    "HousingDecompositionCalculator",
    "CountyRentalIncomeSource",
    "HousingDataSource",
    # Implementations
    "DefaultRentCalculator",
    "DefaultHousingDecompositionCalculator",
]
