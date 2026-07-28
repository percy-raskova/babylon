"""Vol II circulation composer for interactive campaigns — P26 U5g.

Closes ADR162's disclosed inert half (the ``vol2_step`` seam was wired
through :meth:`~babylon.game.session.GameSession.advance_tick` in U2 with
zero production constructors anywhere). The composer assembles a
:class:`~babylon.engine.systems.vol2_circulation.Vol2CirculationStep` from
its two already-live production suppliers:

1. the checked-in Detroit tri-county LODES artifact, resolved by
   :func:`~babylon.engine.headless_runner.lodes_hydration.
   resolve_lodes_hydration_kwargs` (honest ``None`` outside its coverage);
2. the session's real hex→county
   :class:`~babylon.domain.dialectics.instances.scale.ScaleAdjunction`,
   read by :func:`~babylon.persistence.hex_hydrator.
   read_hex_county_adjunction` from ``hex_spatial_map``.

Degradation law (Constitution III.8/III.11, contract §U5g): every absent
input yields ``None`` with ONE loud warning naming what was missing —
never a vacuous step over an empty adjunction, never a fabricated path.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from babylon.engine.headless_runner.lodes_hydration import (
    resolve_lodes_hydration_kwargs,
)
from babylon.engine.systems.vol2_circulation import Vol2CirculationStep
from babylon.persistence.hex_hydrator import read_hex_county_adjunction

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from babylon.domain.dialectics.instances.scale import ScaleAdjunction
    from babylon.persistence.protocols import RuntimePersistence

__all__ = ["build_vol2_circulation_step"]

logger = logging.getLogger(__name__)


def build_vol2_circulation_step(
    *,
    runtime: RuntimePersistence,
    session_id: UUID,
    counties: frozenset[str],
    adjunction_reader: Callable[
        [RuntimePersistence, UUID], ScaleAdjunction
    ] = read_hex_county_adjunction,
) -> Vol2CirculationStep | None:
    """Compose the interactive campaign's Vol II circulation sub-stage.

    :param runtime: the session's PostgreSQL runtime (adjunction source).
    :param session_id: the active session UUID.
    :param counties: the campaign's county FIPS scope.
    :param adjunction_reader: injected for unit tests (explicit dependency,
        per the repo's injection doctrine); production callers keep the
        default :func:`read_hex_county_adjunction`.
    :returns: a live :class:`Vol2CirculationStep`, or ``None`` (loudly)
        when the LODES artifact does not cover ``counties`` or the
        session's hex hydration never populated ``hex_spatial_map``.
    """
    lodes_kwargs = resolve_lodes_hydration_kwargs(counties)
    if lodes_kwargs is None:
        logger.warning(
            "vol2 circulation step NOT composed: county scope %s is outside "
            "the checked-in Detroit tri-county LODES artifact coverage — the "
            "vol2_step seam stays honestly absent for this campaign.",
            sorted(counties),
        )
        return None

    adjunction = adjunction_reader(runtime, session_id)
    if not adjunction.mapping:
        logger.warning(
            "vol2 circulation step NOT composed: session %s has an empty "
            "hex->county adjunction (hex hydration never ran or populated no "
            "county-assigned rows) — refusing to build a vacuous step.",
            session_id,
        )
        return None

    # Local import: the loader touches scipy/pandas at import time — only
    # the composing production path pays it.
    from babylon.domain.economics.lodes_commute_matrix import LODESCommuteMatrixLoader

    loader = LODESCommuteMatrixLoader(
        lodes_root=lodes_kwargs["lodes_root"],
        crosswalk_path=lodes_kwargs["lodes_crosswalk"],
        study_area_hexes=lodes_kwargs["lodes_study_area_hexes"],
        study_area_states=lodes_kwargs["lodes_study_area_states"],
    )
    return Vol2CirculationStep(od_loader=loader, hex_county_adjunction=adjunction)
