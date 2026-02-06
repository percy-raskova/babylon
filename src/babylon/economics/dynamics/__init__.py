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

__all__: list[str] = []
