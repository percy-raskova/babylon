"""Real production supplier for :func:`initialize_session`'s LODES hydration kwargs.

Vol II Circulation program, Unit U2 (data path). Wires the checked-in Detroit
tri-county LODES artifact (:mod:`babylon.domain.economics.lodes_study_area`)
into the headless runner's
:func:`babylon.persistence.postgres_initialization.initialize_session` call
so the LODES OD-matrix hydration path — dormant since spec-063 because
nothing in ``src/`` ever supplied its four gating kwargs (``lodes_root``,
``lodes_crosswalk``, ``lodes_study_area_hexes``, ``lodes_study_area_states`` —
see the Vol II program prompt §2a) — actually runs in production, honoring
the CI-no-drive rule: the artifact is a checked-in file under
``src/babylon/data/reference/lodes/``, never a ``/media/user/data`` read.

Honest-absence discipline (Constitution III.8): the checked-in artifact only
covers the Detroit tri-county study area (Wayne/Oakland/Macomb, Michigan). A
run whose ``scope_fips`` doesn't intersect that area gets ``None`` back — no
fabricated hydration — logged once at INFO level.
"""

from __future__ import annotations

import logging
from typing import Any

from babylon.domain.economics.lodes_study_area import (
    LODES_ARTIFACT_CROSSWALK,
    LODES_ARTIFACT_ROOT,
    LODES_STUDY_AREA_STATES,
    lodes_tri_county_hexes_res7,
)
from babylon.engine.headless_runner.scopes import DETROIT_TRI_COUNTY_FIPS

logger = logging.getLogger(__name__)


def resolve_lodes_hydration_kwargs(scope_fips: frozenset[str]) -> dict[str, Any] | None:
    """Return the four ``initialize_session`` LODES kwargs for ``scope_fips``.

    Args:
        scope_fips: The run's county FIPS scope (``SimulationRunConfig.scope_fips``).

    Returns:
        A dict suitable for ``**``-unpacking into
        :func:`~babylon.persistence.postgres_initialization.initialize_session`
        (``lodes_root``, ``lodes_crosswalk``, ``lodes_study_area_hexes``,
        ``lodes_study_area_states``), or ``None`` when ``scope_fips`` doesn't
        intersect the Detroit tri-county study area the checked-in artifact
        covers (honest absence — no fabricated hydration).
    """
    if not (scope_fips & DETROIT_TRI_COUNTY_FIPS):
        logger.info(
            "LODES hydration skipped: scope_fips (e.g. %s) doesn't intersect "
            "the Detroit tri-county study area %s the checked-in LODES "
            "artifact covers.",
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
