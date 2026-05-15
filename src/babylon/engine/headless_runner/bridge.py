"""WorldState ↔ Postgres bridge for the headless runner.

Spec: 065-engine-bridging (T002 / T040 / T041).

The bridge adapts the in-memory ``WorldState`` Pydantic model to the
per-tick Postgres subsystem tables (spec-062 schema + spec-065
additions in migrations 0020-0023). Lifecycle within one run:

  1. :meth:`WorldStateBridge.hydrate_initial` — one-shot at session
     init. Reads the tick-0 hex_state + external_node templates that
     the hex hydrator wrote, constructs per-county ``SocialClass``
     entity sets tagged with ``county_fips``, optionally subscribes
     :class:`EventCapture` to the engine's ``EventBus``, and returns
     the initial ``WorldState``.
  2. Each tick the runner mutates the ``WorldState`` in-place via
     ``engine.run_tick(graph, services, context)``.
  3. :meth:`WorldStateBridge.persist_tick` — calls the four
     :mod:`babylon.persistence.county_aggregation` helpers per county
     to derive the spec-065 subsystem state rows, re-emits the cached
     hex/external templates with the new tick number, assembles a
     :class:`PerTickTransactionEnvelope`, and writes via
     ``runtime.persist_tick_atomic``.

The bridge is a **derivation/aggregation adapter** (research.md §R10),
not a flat field-by-field serializer. See
``specs/065-engine-bridging/contracts/engine_bridge_protocol.yaml``
for the canonical contract.

Phase 3 first-cut simplification: the engine systems do not yet
mutate hex-resolution state (c/v/s/k per hex are computed by the
hex hydrator at tick 0). The bridge therefore re-emits the tick-0
hex_state values with the current tick on every ``persist_tick``,
keeping the view JOINs satisfied without requiring engine-side
hex disaggregation. When the engine becomes hex-aware in a future
spec, this carry-forward will be replaced by genuine per-tick
hex mutations.
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

from babylon.economics.boundary_flow_register import BoundaryFlowRegister
from babylon.engine.factories import create_bourgeoisie, create_proletariat
from babylon.models.world_state import WorldState
from babylon.persistence.county_aggregation import (
    ReferenceDataMissingError,
    aggregate_consciousness_for_county,
    aggregate_survival_for_county,
    fetch_employment_proxy_for_county_at_tick,
    fetch_population_for_county_at_tick,
)
from babylon.persistence.county_state import (
    DynamicConsciousnessState,
    DynamicDemographicsState,
    DynamicEmploymentState,
)
from babylon.persistence.envelope import PerTickTransactionEnvelope
from babylon.persistence.external_node import ExternalNode, ExternalNodeKind
from babylon.persistence.hex_state import DynamicHexState

if TYPE_CHECKING:
    from babylon.config.defines import GameDefines
    from babylon.engine.headless_runner.event_capture import EngineEvent, EventCapture

__all__ = ["WorldStateBridge"]


logger = logging.getLogger(__name__)


# Default path to the SQLite reference DB (canonical source of truth
# for QCEW, Census, BEA, FCC, Hickel/Ricci data). Overridable via the
# ``sqlite_path`` argument to ``hydrate_initial``.
_DEFAULT_SQLITE_PATH = Path("data/sqlite/marxist-data-3NF.sqlite")


# SQL: read the tick-0 hex_state rows for a scope. We re-emit these
# unchanged at each persist_tick during Phase 3 first cut (the engine
# doesn't yet mutate hex-resolution state — see module docstring).
_FETCH_TICK_ZERO_HEX_SQL = """
SELECT
    session_id, tick, h3_index,
    county_fips, state_fips, region_id,
    c, v, s, k,
    biocapacity_stock, energy_stock, raw_material_stock,
    internet_access_pct, surveillance_coupling
FROM dynamic_hex_state
WHERE session_id = %s AND tick = 0 AND county_fips = ANY(%s)
"""


# SQL: read the tick-0 external_node_state rows for the session.
_FETCH_TICK_ZERO_EXTERNAL_SQL = """
SELECT
    session_id, tick, node_id, kind,
    phi_year_inflow, bilateral_trade_value, bilateral_trade_tons, erdi_ratio
FROM dynamic_external_node_state
WHERE session_id = %s AND tick = 0
"""


class WorldStateBridge:
    """Adapter between in-memory ``WorldState`` and per-tick Postgres state.

    See ``specs/065-engine-bridging/contracts/engine_bridge_protocol.yaml``
    for the canonical contract.

    The bridge is bound to a single ``(session_id, scope_fips)`` pair
    for its lifetime. ``hydrate_initial`` is one-shot; ``persist_tick``
    is called once per tick.
    """

    def __init__(self, runtime: Any, defines: GameDefines) -> None:
        self._runtime = runtime
        self._defines = defines
        self._session_id: UUID | None = None
        self._scope_fips: frozenset[str] | None = None
        self._start_year: int = 2010  # set by hydrate_initial
        self._sqlite_path: Path = _DEFAULT_SQLITE_PATH  # set by hydrate_initial
        self._hex_template: tuple[DynamicHexState, ...] = ()
        self._external_template: tuple[ExternalNode, ...] = ()
        self._hydrated = False
        self._event_capture: EventCapture | None = None
        self._endgame_detector: Any = None
        # Spec-065 T055: BoundaryFlowRegister — created at hydrate_initial.
        # Engine systems push rows via context.services; persist_tick
        # flushes them to the envelope each tick.
        self._boundary_register: BoundaryFlowRegister | None = None

    @property
    def runtime(self) -> Any:
        return self._runtime

    @property
    def event_capture(self) -> EventCapture | None:
        return self._event_capture

    @property
    def hydrated(self) -> bool:
        return self._hydrated

    @property
    def boundary_register(self) -> BoundaryFlowRegister | None:
        """The session's BoundaryFlowRegister (T055).

        Engine systems can push BoundaryFlowRegisterRow entries here;
        :meth:`persist_tick` flushes them into the envelope each tick.
        Returns None before :meth:`hydrate_initial` is called.
        """
        return self._boundary_register

    # ------------------------------------------------------------------
    # T040: hydrate_initial
    # ------------------------------------------------------------------

    def hydrate_initial(
        self,
        session_id: UUID,
        scope_fips: frozenset[str],
        event_capture: EventCapture | None = None,
        *,
        start_year: int = 2010,
        sqlite_path: Path | None = None,
    ) -> WorldState:
        """Build the initial ``WorldState`` and cache persistence templates.

        Steps (in order):

        1. Query ``dynamic_hex_state`` at tick 0 for the scope counties
           — cached as :attr:`_hex_template` for re-emission on each
           subsequent tick.
        2. Query ``dynamic_external_node_state`` at tick 0 — cached
           as :attr:`_external_template`.
        3. For each county in ``scope_fips``, instantiate one
           proletariat + one bourgeoisie SocialClass entity tagged
           with that FIPS via the spec-065 factory updates.
        4. (Optional) store the ``event_capture`` reference for later
           subscription to the engine's EventBus (US5 / T071 wires
           the actual subscription).
        5. Commit instance state — ``_hydrated`` is set LAST so any
           failure above is retry-safe.

        Args:
            session_id:    Active session UUID.
            scope_fips:    5-digit FIPS codes for the scope counties.
            event_capture: Optional EventCapture instance (US5).
            start_year:    Calendar year for tick 0 (FR-022; default 2010).
            sqlite_path:   Optional override for the SQLite reference DB.

        Returns:
            Initial :class:`WorldState` with per-county entities tagged
            with ``county_fips``.

        Raises:
            RuntimeError: If called twice on the same bridge instance.
            FileNotFoundError: If ``sqlite_path`` does not exist
                (deferred — the SQLite reads happen at persist_tick).
        """
        if self._hydrated:
            raise RuntimeError(
                "WorldStateBridge.hydrate_initial called twice on the same "
                "instance; one bridge per session"
            )
        if not scope_fips:
            raise ValueError("scope_fips must be non-empty")

        sqlite_path_resolved = sqlite_path or _DEFAULT_SQLITE_PATH

        # 1. Cache tick-0 hex_state rows (re-emitted per tick during persist_tick).
        hex_rows = self._fetch_tick_zero_hex_template(session_id, scope_fips)

        # 2. Cache tick-0 external_node rows.
        external_rows = self._fetch_tick_zero_external_template(session_id)

        # 3. Build per-county entity sets.
        entities = self._build_per_county_entities(scope_fips)

        # 4. Construct initial WorldState. Tick 0 — entities only;
        #    territories deliberately empty for spec-065 first cut
        #    (engine systems requiring territories are not part of
        #    the bridged loop yet).
        world = WorldState(tick=0, entities=entities)

        # 5. Commit instance state (LAST — retry-safe).
        self._session_id = session_id
        self._scope_fips = scope_fips
        self._event_capture = event_capture
        self._start_year = start_year
        self._sqlite_path = sqlite_path_resolved
        self._hex_template = tuple(hex_rows)
        self._external_template = tuple(external_rows)
        # Spec-065 T055: one BoundaryFlowRegister per session.
        self._boundary_register = BoundaryFlowRegister()
        self._hydrated = True

        logger.info(
            "WorldStateBridge.hydrate_initial: session=%s scope_size=%d "
            "hex_template=%d external_template=%d",
            session_id,
            len(scope_fips),
            len(self._hex_template),
            len(self._external_template),
        )
        return world

    # ------------------------------------------------------------------
    # T041: persist_tick
    # ------------------------------------------------------------------

    def persist_tick(
        self,
        world: WorldState,
        tick: int,
        determinism_hash: str,
    ) -> None:
        """Derive subsystem rows + re-emit hex/external + persist atomically.

        Per research.md §R10, the four spec-065 subsystem rows are
        derivations (engine-state aggregation or reference-data
        lookups), not flat field reads. The bridge calls the four
        county_aggregation helpers per county in ``self._scope_fips``,
        assembles a :class:`PerTickTransactionEnvelope` carrying the
        three new row-lists plus the cached hex/external rows
        re-stamped with the current tick, and calls
        ``runtime.persist_tick_atomic`` for atomic commit.

        Args:
            world:             Current in-memory WorldState (post-engine-run).
            tick:              Tick number being persisted.
            determinism_hash:  64-char SHA-256 of the canonical envelope
                payload (Constitution III.7).

        Raises:
            RuntimeError: If called before :meth:`hydrate_initial`.
            ReferenceDataMissingError: If a county's reference data is
                outside the SQLite window (FR-022 preflight should
                catch this earlier).
        """
        if not self._hydrated:
            raise RuntimeError("WorldStateBridge.persist_tick called before hydrate_initial")
        assert self._session_id is not None
        assert self._scope_fips is not None

        consciousness_rows: list[DynamicConsciousnessState] = []
        demographics_rows: list[DynamicDemographicsState] = []
        employment_rows: list[DynamicEmploymentState] = []

        for county_fips in sorted(self._scope_fips):
            (
                consciousness_row,
                demographics_row,
                employment_row,
            ) = self._derive_subsystem_rows_for_county(
                world=world,
                tick=tick,
                county_fips=county_fips,
            )
            if consciousness_row is not None:
                consciousness_rows.append(consciousness_row)
            if demographics_row is not None:
                demographics_rows.append(demographics_row)
            if employment_row is not None:
                employment_rows.append(employment_row)

        # Re-emit cached templates with the current tick. The engine
        # doesn't yet mutate hex-resolution state, so values are
        # unchanged from tick 0; only `tick` differs.
        hex_rows = [row.model_copy(update={"tick": tick}) for row in self._hex_template]
        external_rows = [row.model_copy(update={"tick": tick}) for row in self._external_template]

        # Spec-065 T056: flush BoundaryFlowRegister for this tick.
        # Empty list when the engine has not pushed any boundary rows
        # (current state — engine integration is a follow-up).
        boundary_rows = (
            list(self._boundary_register.flush())
            if self._boundary_register is not None
            else []
        )

        envelope = PerTickTransactionEnvelope(
            session_id=self._session_id,
            tick=tick,
            hex_state_rows=hex_rows,
            external_node_rows=external_rows,
            boundary_register_rows=boundary_rows,
            consciousness_state_rows=consciousness_rows,
            demographics_state_rows=demographics_rows,
            employment_state_rows=employment_rows,
            determinism_hash=determinism_hash,
        )
        self._runtime.persist_tick_atomic(envelope)

        logger.debug(
            "WorldStateBridge.persist_tick: session=%s tick=%d "
            "consciousness=%d demographics=%d employment=%d hex=%d external=%d",
            self._session_id,
            tick,
            len(consciousness_rows),
            len(demographics_rows),
            len(employment_rows),
            len(hex_rows),
            len(external_rows),
        )

    # ------------------------------------------------------------------
    # Phase-2 stubs that remain (subscribe events / poll endgame)
    # ------------------------------------------------------------------

    def refresh_event_log(self) -> tuple[EngineEvent, ...]:
        """Drain accumulated engine events for ``summary.json.events``."""
        if self._event_capture is None:
            return ()
        return self._event_capture.drain()

    def set_endgame_detector(self, dotted_path: str) -> None:
        """Resolve a dotted import path to an ``EndgameDetector`` instance.

        Phase-2 stub for resolution; final wiring (poll-per-tick into
        runner) lands in T063.
        """
        module_path, _, attr = dotted_path.rpartition(".")
        if not module_path:
            raise ImportError(f"--endgame-detector value {dotted_path!r} is not a dotted path")
        try:
            module = importlib.import_module(module_path)
        except ImportError as exc:
            raise ImportError(
                f"--endgame-detector module {module_path!r} could not be imported: {exc}"
            ) from exc
        detector_cls = getattr(module, attr, None)
        if detector_cls is None:
            raise ImportError(
                f"--endgame-detector path {dotted_path!r}: "
                f"module {module_path!r} has no attribute {attr!r}"
            )
        self._endgame_detector = detector_cls() if callable(detector_cls) else detector_cls

    def poll_endgame(self, world: WorldState, tick: int) -> Any:
        """Invoke the configured endgame detector. None if none configured."""
        if self._endgame_detector is None:
            return None
        return self._endgame_detector.check(world, tick)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_tick_zero_hex_template(
        self,
        session_id: UUID,
        scope_fips: frozenset[str],
    ) -> list[DynamicHexState]:
        """Query dynamic_hex_state at tick 0 for the scope counties."""
        fips_list = sorted(scope_fips)  # deterministic order for tests
        with self._runtime._pool.connection() as conn:  # noqa: SLF001
            rows = conn.execute(
                _FETCH_TICK_ZERO_HEX_SQL,
                (str(session_id), fips_list),
            ).fetchall()

        return [
            DynamicHexState(
                session_id=row[0],
                tick=row[1],
                h3_index=row[2],
                county_fips=row[3],
                state_fips=row[4],
                region_id=row[5],
                c=row[6],
                v=row[7],
                s=row[8],
                k=row[9],
                biocapacity_stock=row[10],
                energy_stock=row[11],
                raw_material_stock=row[12],
                internet_access_pct=row[13],
                surveillance_coupling=row[14],
            )
            for row in rows
        ]

    def _fetch_tick_zero_external_template(
        self,
        session_id: UUID,
    ) -> list[ExternalNode]:
        """Query dynamic_external_node_state at tick 0."""
        with self._runtime._pool.connection() as conn:  # noqa: SLF001
            rows = conn.execute(
                _FETCH_TICK_ZERO_EXTERNAL_SQL,
                (str(session_id),),
            ).fetchall()

        return [
            ExternalNode(
                session_id=row[0],
                tick=row[1],
                node_id=row[2],
                kind=ExternalNodeKind(row[3]) if isinstance(row[3], str) else row[3],
                phi_year_inflow=row[4],
                bilateral_trade_value=row[5],
                bilateral_trade_tons=row[6],
                erdi_ratio=row[7],
            )
            for row in rows
        ]

    def _build_per_county_entities(
        self,
        scope_fips: frozenset[str],
    ) -> dict[str, Any]:
        """Instantiate one proletariat + one bourgeoisie per county.

        ID scheme: proletariat IDs are ``C001..C{N:03d}`` over sorted
        FIPS; bourgeoisie IDs are offset by 500 (``C501..C{N+500:03d}``).
        Default ideology/wealth values come from the factories;
        spec-065 first cut uses small synthetic populations (proletariat
        block size 85, bourgeoisie block size 15 per county). The
        engine will evolve these over time; the bridge just needs a
        valid initial state with per-county attribution.

        Returns:
            ``{entity_id: SocialClass}`` mapping suitable for
            ``WorldState.entities``.
        """
        entities: dict[str, Any] = {}
        for i, county_fips in enumerate(sorted(scope_fips), start=1):
            proletariat_id = f"C{i:03d}"
            bourgeoisie_id = f"C{i + 500:03d}"

            entities[proletariat_id] = create_proletariat(
                id=proletariat_id,
                county_fips=county_fips,
            ).model_copy(update={"population": 85})
            entities[bourgeoisie_id] = create_bourgeoisie(
                id=bourgeoisie_id,
                county_fips=county_fips,
            ).model_copy(update={"population": 15})

        return entities

    def _derive_subsystem_rows_for_county(
        self,
        *,
        world: WorldState,
        tick: int,
        county_fips: str,
    ) -> tuple[
        DynamicConsciousnessState | None,
        DynamicDemographicsState | None,
        DynamicEmploymentState | None,
    ]:
        """Build the three subsystem rows for one county at one tick.

        Wraps the four county_aggregation helpers. Returns ``(None, None, None)``
        for any row that can't be derived (e.g., no entities tagged
        with this FIPS, or reference data missing for this year);
        the caller logs and emits an audit row for these cases.
        """
        # Engine-state aggregations (always available).
        p_acq, p_rev, total_population = aggregate_survival_for_county(world, county_fips)
        consciousness = aggregate_consciousness_for_county(world, county_fips)

        consciousness_row: DynamicConsciousnessState | None = None
        if total_population > 0:
            consciousness_row = DynamicConsciousnessState(
                session_id=self._session_id,  # type: ignore[arg-type]
                tick=tick,
                county_fips=county_fips,
                p_acquiescence=p_acq,
                p_revolution=p_rev,
                ideology_r=consciousness.r,
                ideology_l=consciousness.l,
                ideology_f=consciousness.f,
            )

        # Reference-data fetchers — may raise ReferenceDataMissingError
        # if outside the SQLite year window.
        demographics_row: DynamicDemographicsState | None = None
        employment_row: DynamicEmploymentState | None = None
        try:
            population = fetch_population_for_county_at_tick(
                self._sqlite_path, county_fips, tick, self._start_year
            )
            demographics_row = DynamicDemographicsState(
                session_id=self._session_id,  # type: ignore[arg-type]
                tick=tick,
                county_fips=county_fips,
                population=population,
            )
        except ReferenceDataMissingError as exc:
            logger.warning(
                "persist_tick: population missing for county=%s tick=%d (year=%d): %s",
                county_fips,
                tick,
                self._start_year + tick // 52,
                exc,
            )

        try:
            employment_proxy = fetch_employment_proxy_for_county_at_tick(
                self._sqlite_path, county_fips, tick, self._start_year
            )
            employment_row = DynamicEmploymentState(
                session_id=self._session_id,  # type: ignore[arg-type]
                tick=tick,
                county_fips=county_fips,
                employment_proxy=employment_proxy,
            )
        except ReferenceDataMissingError as exc:
            logger.warning(
                "persist_tick: employment missing for county=%s tick=%d (year=%d): %s",
                county_fips,
                tick,
                self._start_year + tick // 52,
                exc,
            )

        return consciousness_row, demographics_row, employment_row
