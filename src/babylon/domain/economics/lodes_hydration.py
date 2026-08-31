"""Resolve the checked-in Detroit LODES artifact for Python reference use."""

from __future__ import annotations

import logging
from typing import Any

from babylon.data.reference_scope import DETROIT_TRI_COUNTY_FIPS
from babylon.domain.economics.lodes_study_area import (
    LODES_ARTIFACT_CROSSWALK,
    LODES_ARTIFACT_ROOT,
    LODES_STUDY_AREA_STATES,
    lodes_tri_county_hexes_res7,
)

logger = logging.getLogger(__name__)


def resolve_lodes_hydration_kwargs(scope_fips: frozenset[str]) -> dict[str, Any] | None:
    """Return exact checked-in artifact paths, or honest absence outside coverage."""
    if not (scope_fips & DETROIT_TRI_COUNTY_FIPS):
        logger.info(
            "LODES reference absent: scope %s does not intersect %s",
            sorted(scope_fips)[:5],
            sorted(DETROIT_TRI_COUNTY_FIPS),
        )
        return None
    return {
        "lodes_root": LODES_ARTIFACT_ROOT,
        "lodes_crosswalk": LODES_ARTIFACT_CROSSWALK,
        "lodes_study_area_hexes": lodes_tri_county_hexes_res7(),
        "lodes_study_area_states": LODES_STUDY_AREA_STATES,
    }


__all__ = ["resolve_lodes_hydration_kwargs"]
