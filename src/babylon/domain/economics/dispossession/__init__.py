"""Dispossession Events economics module (Feature 021, US2).

Tracks aggregate dispossession events per territory-tick with value
transfer accounting and computes territory-level dispossession intensity.
"""

from babylon.domain.economics.dispossession.data_sources import TerritoryDispossessionDataSource
from babylon.domain.economics.dispossession.intensity import DispossessionIntensityCalculator
from babylon.domain.economics.dispossession.types import (
    DispossessionEvent,
    TerritoryDispossessionState,
)

__all__ = [
    "DispossessionEvent",
    "TerritoryDispossessionState",
    "TerritoryDispossessionDataSource",
    "DispossessionIntensityCalculator",
]
