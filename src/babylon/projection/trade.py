"""Trade projections — P26 U6 phase 1 (the backend `observe()` seam).

Successor to spec-103's dead web trade panels (`BlocFlowLines` /
`TradePanel`), projected for the Archive client instead: pure functions
over plain session-held data. Contract:
``specs/103-trade-surfaces/u6-archive-trade-surfaces-contracts.md``.

Layering: this module imports NOTHING above the projection layer — the
session (``babylon.game.session``) calls these with data it already holds
(its ``TradeWiring`` fields and the last tick's flushed DRAIN_EDGE
magnitudes folded to ``{node_id: total}``); no graph or ``WorldState``
dependency at all. Every absent input projects honest ``None`` (the
:func:`~babylon.projection.county.project_county` documented shape), never
a fabricated zero.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.projection.view_models import (
    CountyExposureShare,
    TradeBlocPhiShare,
    TradeBlocView,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = ["project_trade_bloc", "project_trade_overview"]

#: Cap on the per-bloc exposure rows a dossier carries — display slice, not
#: data truncation (the full map stays in the wiring; a slice of the top
#: contributors is what the panel renders). Static bound (Power-of-10 #2).
_EXPOSURE_TOP_N = 10


def _exposure_rows(
    exposure: Mapping[str, float] | None,
) -> tuple[CountyExposureShare, ...] | None:
    """Fold one bloc's exposure map into sorted display rows, or ``None``.

    :param exposure: ``{county_fips: weight}`` for one bloc, or ``None``.
    :returns: up to :data:`_EXPOSURE_TOP_N` rows, weight DESC then FIPS
        ASC (deterministic), or ``None`` for an absent/empty map.
    """
    if not exposure:
        return None
    ordered = sorted(exposure.items(), key=lambda item: (-item[1], item[0]))
    return tuple(
        CountyExposureShare(county_fips=fips, weight=weight)
        for fips, weight in ordered[:_EXPOSURE_TOP_N]
    )


def project_trade_bloc(
    node_id: str,
    *,
    external_nodes_phi: Mapping[str, float],
    county_exposure_by_external: Mapping[str, Mapping[str, float]],
    weeks_per_year: int,
    last_flows: Mapping[str, float],
    tick: int,
) -> TradeBlocView | None:
    """Project one external bloc's trade dossier.

    :param node_id: The external node id (e.g. ``"canada"``).
    :param external_nodes_phi: ``{node_id: phi_year_inflow_usd}`` — the
        wiring's static attribution map; a ``node_id`` absent from it is an
        honest absence (``None`` return), matching the sibling projectors'
        unknown-entity contract.
    :param county_exposure_by_external: ``{node_id: {county_fips: weight}}``.
    :param weeks_per_year: ticks per simulated year (``defines.timescale``).
    :param last_flows: ``{node_id: summed DRAIN_EDGE magnitude}`` from the
        most recent tick's flushed register rows; a node with no entry
        recorded no flow that tick (``None``, not ``0.0``).
    :param tick: the committed tick this dossier is projected from.
    :returns: the view, or ``None`` for an unknown ``node_id``.
    """
    if node_id not in external_nodes_phi:
        return None
    phi_year = external_nodes_phi[node_id]
    flow = last_flows.get(node_id)
    return TradeBlocView(
        node_id=node_id,
        verified_tick=tick,
        phi_year_inflow=phi_year,
        phi_week_slice=phi_year / weeks_per_year,
        exposure_top=_exposure_rows(county_exposure_by_external.get(node_id)),
        last_tick_flow=flow,
    )


def project_trade_overview(
    *,
    external_nodes_phi: Mapping[str, float],
    county_exposure_by_external: Mapping[str, Mapping[str, float]],
    weeks_per_year: int,
    last_flows: Mapping[str, float],
    tick: int,
) -> TradeBlocView:
    """Project the national trade overview (spec-103 ``TradePanel`` semantics).

    ``phi_year_inflow`` is the national total across blocs (conservation:
    the attribution already sums to national Φ — spec-101 D3), the
    breakdown carries per-bloc rows Φ DESC then node_id ASC, and
    ``last_tick_flow`` is the tick's total flushed DRAIN_EDGE magnitude
    (``None`` when the tick recorded no flow at all).

    :param external_nodes_phi: as :func:`project_trade_bloc`.
    :param county_exposure_by_external: as :func:`project_trade_bloc`
        (unused in the fold today; accepted so both projectors share one
        call shape at the ``subject_view`` seam).
    :param weeks_per_year: as :func:`project_trade_bloc`.
    :param last_flows: as :func:`project_trade_bloc`.
    :param tick: as :func:`project_trade_bloc`.
    :returns: the ``node_id="overview"`` view.
    """
    _ = county_exposure_by_external
    total_phi = sum(external_nodes_phi.values())
    breakdown = tuple(
        TradeBlocPhiShare(node_id=node, phi_year_inflow=phi)
        for node, phi in sorted(external_nodes_phi.items(), key=lambda item: (-item[1], item[0]))
    )
    total_flow = sum(last_flows.values()) if last_flows else None
    return TradeBlocView(
        node_id="overview",
        verified_tick=tick,
        phi_year_inflow=total_phi,
        phi_week_slice=total_phi / weeks_per_year,
        breakdown=breakdown or None,
        last_tick_flow=total_flow,
    )
