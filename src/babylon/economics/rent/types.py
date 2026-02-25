"""Type definitions for the ground rent extraction module.

Feature: 024-capital-volume-iii (US4)
"""

from __future__ import annotations

from enum import StrEnum


class RentCategory(StrEnum):
    """Category of ground rent extraction.

    Feature: 024-capital-volume-iii (FR-007)

    Marx distinguished differential rent (surplus profit from better
    land/location) and absolute rent (monopoly payment for any land
    access). Both operate across three economic sectors.

    Values:
        AGRICULTURAL: Farmland rent (differential by soil fertility/location).
        RESOURCE: Mining, oil/gas rent (differential by deposit quality).
        URBAN: Building site rent, commercial real estate (differential by location).
    """

    AGRICULTURAL = "agricultural"
    RESOURCE = "resource"
    URBAN = "urban"
