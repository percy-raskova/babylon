"""Interactive trade wiring — P26 U2 (spec-101 parity for the playable game).

Spec-101 wired imperial-rent Φ-distribution end-to-end, but only the headless
batch runner ever supplied the gated context inputs
(``engine/headless_runner/runner.py:440-447``). This module carries the same
wiring to :class:`babylon.game.session.GameSession` — the playable
Archive-campaign driver — via the seam contract pinned in
``specs/101-trade-activation/u2-interactive-parity-contracts.md``.

:class:`TradeWiring` is a frozen carrier of live per-session service objects
(the :class:`~babylon.engine.services.ServiceContainer` precedent), not a
serializable game model — hence a dataclass rather than a Pydantic
``BaseModel``. All member data is established at campaign start; the session
only reads it.

:func:`build_interactive_trade_wiring` is the production builder used by the
``cli/play.py`` composition root. It is a thin composition of ALREADY-live
pieces (session initialization, the spec-100 county-exposure reader, the
tick-0 external-node Φ query) — no new math, per the P26 charter's
no-shadow-value-system constraint (ADR160). It fails LOUD
(:class:`TradeDataUnavailableError`) when the reference DB is absent
(Constitution III.11) — the composition root converts that into one visible
degradation warning, never a silent no-trade campaign.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from babylon.domain.economics.boundary_flow_register import BoundaryFlowRegister

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from pathlib import Path
    from uuid import UUID

    from babylon.config.defines import GameDefines
    from babylon.engine.systems.vol2_circulation import Vol2CirculationStep
    from babylon.persistence import PostgresRuntime


class TradeDataUnavailableError(RuntimeError):
    """The reference data needed to wire interactive trade is absent.

    Raised by :func:`build_interactive_trade_wiring` before any Postgres
    work happens. Loud by design: an interactive campaign silently running
    without external nodes and Φ flow is the exact defect class P26 U2
    exists to eliminate (program doc §1, "Absent from the playable game").
    """


@dataclass(frozen=True)
class TradeWiring:
    """Per-campaign trade wiring the session stamps into each tick's context.

    Mirrors the headless runner's per-run state: the four inputs
    ``ImperialRentSystem._invoke_phi_distribution_if_wired`` gates on, plus
    the ``simulated_year``/``vol2_step`` pair its Vol II sibling gate needs.

    :param boundary_register: this session's own per-tick DRAIN_EDGE buffer
        (never shared across sessions — the register's own isolation
        contract).
    :param external_nodes_phi: ``{node_id: phi_year_inflow_usd}`` for the
        external bloc nodes, from the tick-0
        ``dynamic_external_node_state`` rows.
    :param county_exposure_by_external: ``{node_id: {county_fips: weight}}``
        with each node's weights summing to 1.0 (spec-100 D2 contract —
        enforced downstream by ``distribute_phi_week_to_counties``).
    :param start_year: the campaign's first simulated calendar year;
        anchor for :meth:`simulated_year`.
    :param weeks_per_year: ticks per simulated year, from
        ``defines.timescale.weeks_per_year`` — threaded so no consumer
        hardcodes an independent ``52`` literal (III.1/DRY).
    :param vol2_step: the constructed Vol II circulation sub-stage, or
        ``None`` to leave that gate closed (its LODES/adjunction inputs are
        composition-root concerns; absence keeps the sub-stage honestly
        gated, not stubbed).
    """

    boundary_register: BoundaryFlowRegister
    external_nodes_phi: Mapping[str, float]
    county_exposure_by_external: Mapping[str, Mapping[str, float]]
    start_year: int
    weeks_per_year: int
    vol2_step: Vol2CirculationStep | None = None

    def simulated_year(self, tick: int) -> int:
        """Return the simulated calendar year for ``tick``.

        Derivation: ``start_year + tick // weeks_per_year`` — the integer
        form ``economic.py``'s Vol II gate casts to (the trace emitter's
        fractional ``start_year + tick / 52.0`` is a display concern, not a
        gate input).

        :param tick: absolute tick number (>= 0).
        :returns: the simulated calendar year as an ``int``.
        """
        return self.start_year + tick // self.weeks_per_year


def build_interactive_trade_wiring(
    *,
    session_id: UUID,
    runtime: PostgresRuntime,
    defines: GameDefines,
    sqlite_path: Path,
    start_year: int,
    counties: Collection[str] | None = None,
    vol2_step: Vol2CirculationStep | None = None,
    bootstrap_reference: bool = True,
    hex_hydration_counties: frozenset[str] | None = None,
) -> TradeWiring:
    """Build the production :class:`TradeWiring` for one fresh campaign.

    Thin composition of the already-live spec-101 estate, mirroring the
    headless runner's boot sequence (``runner.py:1318-1355``):

    1. :func:`~babylon.persistence.postgres_initialization.initialize_session`
       — hydrates the immutable reference series and bootstraps the
       external-node registry (tick-0 ``dynamic_external_node_state`` rows,
       Φ attributed per node).
    2. :func:`~babylon.domain.economics.county_exposure.load_county_exposure_map`
       — the bloc-invariant ``{county_fips: weight}`` map, fanned out per
       external node exactly as the runner does.
    3. The tick-0 external-node Φ query over ``runtime.pool``.

    :param session_id: the campaign's ``game_session.id`` (already created).
    :param runtime: the campaign's live Postgres runtime.
    :param defines: the campaign's own :class:`GameDefines` (the FR-029a
        alpha invariant is checked inside ``initialize_session``).
    :param sqlite_path: path to ``marxist-data-3NF.sqlite``.
    :param start_year: the campaign's first simulated year.
    :param counties: optional 5-digit FIPS scope (e.g. Wayne's
        ``["26163"]``); ``None`` = national exposure scope.
    :param vol2_step: optional constructed Vol II sub-stage to carry.
    :param bootstrap_reference: run ``initialize_session`` (fresh campaigns).
        Pass ``False`` on crash-resume — the session's reference copy and
        tick-0 external-node rows were persisted at creation; only the
        queries run.
    :param hex_hydration_counties: FIPS scope for tick-0 hex hydration
        (``hex_spatial_map`` + ``dynamic_hex_state``, the runner twin at
        ``runner.py:1224``) — P26 U5g: a populated hex→county adjunction is
        what makes :func:`~babylon.game.vol2.build_vol2_circulation_step`
        compose a live step. ``None`` (the pre-U5g default) skips
        hydration; only meaningful when ``bootstrap_reference`` is true
        (resumed sessions keep their creation-time rows).
    :returns: the frozen :class:`TradeWiring`.
    :raises TradeDataUnavailableError: when the reference DB is absent —
        before any Postgres work.
    """
    if not sqlite_path.is_file():
        raise TradeDataUnavailableError(
            f"reference DB absent at {sqlite_path}; interactive trade wiring "
            "requires marxist-data-3NF.sqlite (build it via `mise run "
            "data:build-db` or mount the data trove). Refusing to boot a "
            "silently trade-less campaign (Constitution III.11)."
        )

    # Local imports: the persistence/runner estate is heavyweight and only
    # needed on this production path — unit tests construct TradeWiring
    # directly with deterministic fakes (contract doc, Contract 1).
    from babylon.domain.economics.county_exposure import load_county_exposure_map
    from babylon.engine.headless_runner.runner import _query_external_nodes_phi
    from babylon.persistence.postgres_initialization import initialize_session

    if bootstrap_reference:
        initialize_session(
            session_id=session_id,
            sqlite_path=sqlite_path,
            runtime=runtime,
            defines=defines,
            start_year=start_year,
            counties=sorted(counties) if counties is not None else None,
            hex_hydration_counties=hex_hydration_counties,
        )

    exposure_map = load_county_exposure_map(
        sqlite_path=sqlite_path,
        year=start_year,
        scope_fips=frozenset(counties) if counties is not None else None,
    )
    external_nodes_phi = _query_external_nodes_phi(pool=runtime.pool, session_id=session_id)
    # Runner twin (runner.py:1354): the exposure map is bloc-invariant, so
    # every external node fans out over the same county weights.
    county_exposure_by_external: dict[str, Mapping[str, float]] = dict.fromkeys(
        sorted(external_nodes_phi), exposure_map
    )

    return TradeWiring(
        boundary_register=BoundaryFlowRegister(session_id=session_id),
        external_nodes_phi=external_nodes_phi,
        county_exposure_by_external=county_exposure_by_external,
        start_year=start_year,
        weeks_per_year=defines.timescale.weeks_per_year,
        vol2_step=vol2_step,
    )
