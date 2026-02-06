"""Class Dynamics Engine for modeling class position transitions over time.

Feature: 016-class-dynamics-engine
Date: 2026-02-06

This module models how class positions (labor aristocracy, proletariat,
lumpenproletariat) change over time through four mechanisms:

1. **Accumulation** (Proletariat -> LA): Sustained savings cross wealth threshold
2. **Dispossession** (LA -> Proletariat): Foreclosure, bankruptcy destroy wealth
3. **Precaritization** (Proletariat -> Lumpen): Job loss, eviction exclude from labor
4. **Stabilization** (Lumpen -> Proletariat): Gaining stable employment

Theoretical Framework:
    - Bourgeoisie and petit-bourgeoisie shares are externally determined
    - Dynamics engine operates on LA/proletariat/lumpen transitions only
    - All transitions are continuous flows preserving sum-to-one invariant

See Also:
    :mod:`babylon.economics.melt.types`: ClassPosition enum (Feature 013)
    :mod:`babylon.economics.tensor`: NoDataSentinel pattern
"""

# Types
# Data source protocols
# Implementations
from babylon.economics.dynamics.accumulation import (
    DefaultAccumulationCalculator,
)
from babylon.economics.dynamics.crisis import (
    DefaultCrisisAmplifier,
)
from babylon.economics.dynamics.data_sources import (
    AccumulationCalculator,
    ClassTransitionEngine,
    CrisisAmplifier,
    DispossessionCalculator,
    DispossessionDataSource,
    SavingsRateSource,
)
from babylon.economics.dynamics.dispossession import (
    DefaultDispossessionCalculator,
)

# MVP data sources
from babylon.economics.dynamics.hardcoded_data import (
    HardcodedNationalDispossessionSource,
)
from babylon.economics.dynamics.savings_schedule import (
    HOURS_PER_YEAR,
    DefaultSavingsRateSchedule,
)
from babylon.economics.dynamics.transition_engine import (
    DefaultClassTransitionEngine,
)
from babylon.economics.dynamics.types import (
    AccumulationResult,
    ClassDistribution,
    DispossessionRisk,
    EconomicConditions,
    SavingsRateSchedule,
    TransitionRates,
)

# Validation
from babylon.economics.dynamics.validation import (
    validate_class_shares,
    validate_transition_rates,
)

__all__ = [
    # Types
    "AccumulationResult",
    "ClassDistribution",
    "DispossessionRisk",
    "EconomicConditions",
    "SavingsRateSchedule",
    "TransitionRates",
    # Protocols
    "AccumulationCalculator",
    "ClassTransitionEngine",
    "CrisisAmplifier",
    "DispossessionCalculator",
    "DispossessionDataSource",
    "SavingsRateSource",
    # MVP data sources
    "HardcodedNationalDispossessionSource",
    "DefaultSavingsRateSchedule",
    "HOURS_PER_YEAR",
    # Implementations
    "DefaultAccumulationCalculator",
    "DefaultClassTransitionEngine",
    "DefaultCrisisAmplifier",
    "DefaultDispossessionCalculator",
    # Validation
    "validate_class_shares",
    "validate_transition_rates",
]
