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
from babylon.engine.event_bus import EventBus
from babylon.engine.factories import create_bourgeoisie, create_proletariat
from babylon.engine.headless_runner.reference_data_cache import (
    ReferenceDataCache,
    derive_year_set,
)
from babylon.models import Relationship
from babylon.models.entities.social_class import IdeologicalProfile
from babylon.models.enums import EdgeType
from babylon.models.enums.events import EventType
from babylon.models.world_state import WorldState
from babylon.persistence.county_aggregation import (
    aggregate_consciousness_for_county,
    aggregate_survival_for_county,
)
from babylon.persistence.county_state import (
    DynamicConsciousnessState,
    DynamicDemographicsState,
    DynamicEmploymentState,
)
from babylon.persistence.envelope import PerTickTransactionEnvelope
from babylon.persistence.external_node import ExternalNode, ExternalNodeKind
from babylon.persistence.hex_state import DynamicHexState
from babylon.persistence.relationship_state import DynamicRelationshipState

if TYPE_CHECKING:
    from babylon.config.defines import GameDefines
    from babylon.engine.headless_runner.event_capture import EngineEvent, EventCapture
    from babylon.persistence.conservation_audit import ConservationAuditor

__all__ = ["WorldStateBridge"]


logger = logging.getLogger(__name__)


# Default path to the SQLite reference DB (canonical source of truth
# for QCEW, Census, BEA, FCC, Hickel/Ricci data). Overridable via the
# ``sqlite_path`` argument to ``hydrate_initial``.
_DEFAULT_SQLITE_PATH = Path("data/sqlite/marxist-data-3NF.sqlite")


# Spec-066 T050 / ADR043 (placeholder): every county entity starts at
# (cc=0.1, ni=0.5) which the bridge ternary mapping resolves to
#   r = cc * (1 - ni)         = 0.05  (revolutionary)
#   l = max(0, 1 - r - f)     = 0.50  (liberal — dominant)
#   f = ni * (1 - cc)         = 0.45  (fascist)
# Per Clarifications Q3, this is an explicit placeholder until a future
# spec ships per-county data-driven seeding (ACS, election results, etc.).
BASELINE_IDEOLOGY = IdeologicalProfile(class_consciousness=0.1, national_identity=0.5)


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

    def __init__(
        self,
        runtime: Any,
        defines: GameDefines,
        *,
        boundary_register: BoundaryFlowRegister | None = None,
        event_bus: EventBus | None = None,
        auditor: ConservationAuditor | None = None,
    ) -> None:
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
        # Spec-065 T055: BoundaryFlowRegister is owned by runner.run() and
        # injected here. When not supplied (older callers / unit tests), the
        # bridge instantiates its own so behavior stays equivalent.
        # Engine systems push rows via services.boundary_register; persist_tick
        # flushes them to the envelope each tick.
        self._boundary_register: BoundaryFlowRegister = (
            boundary_register if boundary_register is not None else BoundaryFlowRegister()
        )
        # Spec-065 T071: EventBus is owned by runner.run() so engine systems
        # (spec-066) and the EventCapture subscriber share the same bus.
        # When not supplied (older callers / unit tests), the bridge spins up
        # its own so subscribe() calls remain valid.
        self._event_bus: EventBus = event_bus if event_bus is not None else EventBus()
        # Spec-065 T049: ConservationAuditor is owned by runner.run() and
        # injected so the bridge can call audit_end_of_tick() during
        # persist_tick. Audit rows are appended to the per-tick envelope so
        # they hit the conservation_audit_log table durably; the in-memory
        # ``audit_log_buffer`` lets runner._check_strict_alarms read alarms
        # without a Postgres round-trip.
        self._auditor: ConservationAuditor | None = auditor
        # Spec-069: per-bridge reference-data cache. None until hydrate_initial
        # populates it. Constitution II.6 — no DB I/O during tick — is enforced
        # by routing all per-tick population / employment-proxy reads through
        # this cache.
        self._ref_cache: ReferenceDataCache | None = None

    @property
    def runtime(self) -> Any:
        return self._runtime

    @property
    def event_capture(self) -> EventCapture | None:
        return self._event_capture

    @property
    def event_bus(self) -> EventBus:
        """The session's EventBus (T071).

        Owned by ``runner.run()`` and injected at __init__ so the
        engine-side publishers (spec-066) and the bridge-side
        :class:`EventCapture` subscriber share the same bus.
        """
        return self._event_bus

    @property
    def auditor(self) -> ConservationAuditor | None:
        """The session's ConservationAuditor (T049).

        Owned by ``runner.run()`` and injected at __init__. ``persist_tick``
        calls ``auditor.audit_end_of_tick(...)`` after the envelope is
        built, merging any newly-produced audit rows into the same
        per-tick transaction.
        """
        return self._auditor

    @property
    def hydrated(self) -> bool:
        return self._hydrated

    @property
    def population_db_reads(self) -> int:
        """Spec-069 SC-002: count of population reads issued at hydrate time.

        Returns 0 before ``hydrate_initial`` is called (per
        ``contracts/instrumentation_contract.md`` §I1).
        """
        return 0 if self._ref_cache is None else self._ref_cache.population_db_reads

    @property
    def employment_db_reads(self) -> int:
        """Spec-069 SC-002: count of employment-proxy reads issued at hydrate time."""
        return 0 if self._ref_cache is None else self._ref_cache.employment_db_reads

    @property
    def total_db_reads(self) -> int:
        """Spec-069 SC-002: ``population_db_reads + employment_db_reads``."""
        return 0 if self._ref_cache is None else self._ref_cache.total_db_reads

    @property
    def boundary_register(self) -> BoundaryFlowRegister:
        """The session's BoundaryFlowRegister (T055).

        Engine systems push BoundaryFlowRegisterRow entries here;
        :meth:`persist_tick` flushes them into the envelope each tick.
        Spec-065 T055: the register is owned by runner.run() and injected
        into the bridge at construction time, so it's always available.
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
        total_ticks: int,
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
        5. Spec-069: hydrate the per-bridge ``ReferenceDataCache`` with
           the full ``(scope_fips × year_set)`` covered by the run.
           ``year_set`` is derived from ``(start_year, total_ticks)``
           under the weekly cadence; the cache then serves all per-tick
           population / employment-proxy reads from memory.
        6. Commit instance state — ``_hydrated`` is set LAST so any
           failure above is retry-safe.

        Args:
            session_id:    Active session UUID.
            scope_fips:    5-digit FIPS codes for the scope counties.
            event_capture: Optional EventCapture instance (US5).
            total_ticks:   Total tick count for the run; drives the
                spec-069 cache hydrate year-set derivation. Must be
                ``>= 0``. (Spec-069 FR-001.)
            start_year:    Calendar year for tick 0 (FR-022; default 2010).
            sqlite_path:   Optional override for the SQLite reference DB.

        Returns:
            Initial :class:`WorldState` with per-county entities tagged
            with ``county_fips``.

        Raises:
            RuntimeError: If called twice on the same bridge instance.
            ValueError: If ``scope_fips`` is empty or ``total_ticks < 0``.
            FileNotFoundError: If ``sqlite_path`` does not exist.
        """
        if self._hydrated:
            raise RuntimeError(
                "WorldStateBridge.hydrate_initial called twice on the same "
                "instance; one bridge per session"
            )
        if not scope_fips:
            raise ValueError("scope_fips must be non-empty")
        if total_ticks < 0:
            raise ValueError(f"total_ticks must be >= 0; got {total_ticks}")

        sqlite_path_resolved = sqlite_path or _DEFAULT_SQLITE_PATH

        # 1. Cache tick-0 hex_state rows (re-emitted per tick during persist_tick).
        hex_rows = self._fetch_tick_zero_hex_template(session_id, scope_fips)

        # 2. Cache tick-0 external_node rows.
        external_rows = self._fetch_tick_zero_external_template(session_id)

        # 3. Build per-county entity sets.
        entities = self._build_per_county_entities(scope_fips)

        # 3a. Spec-066 T032/T033: seed one EXPLOITATION edge per county
        #     between proletariat and bourgeoisie. Without this edge,
        #     ImperialRentSystem has no graph path to walk -> no Φ
        #     extraction -> no agitation -> no consciousness drift.
        #     SOLIDARITY edges are deliberately NOT seeded; per
        #     Constitution III.5 + Clarifications Q4 they are strategic
        #     intervention from player verbs, not data-derived.
        relationships = self._build_per_county_relationships(
            scope_fips=scope_fips,
            entities=entities,
        )

        # 4. Construct initial WorldState. Tick 0 — entities + per-county
        #    EXPLOITATION edges; territories deliberately empty for
        #    spec-065 first cut (engine systems requiring territories
        #    are not part of the bridged loop yet).
        world = WorldState(tick=0, entities=entities, relationships=relationships)

        # 5. Spec-069: hydrate the reference-data cache for the full
        #    (scope × year) Cartesian product the run will touch. After
        #    this call the per-tick path NEVER opens a new connection
        #    to the SQLite reference DB (FR-003 / II.6 compliance).
        ref_cache = ReferenceDataCache(sqlite_path_resolved)
        ref_cache.hydrate(
            scope_fips=scope_fips,
            year_set=derive_year_set(start_year, total_ticks),
        )

        # 6. Commit instance state (LAST — retry-safe).
        self._session_id = session_id
        self._scope_fips = scope_fips
        self._event_capture = event_capture
        self._start_year = start_year
        self._sqlite_path = sqlite_path_resolved
        self._hex_template = tuple(hex_rows)
        self._external_template = tuple(external_rows)
        self._ref_cache = ref_cache
        # Spec-065 T055: BoundaryFlowRegister is now owned by runner.run()
        # and injected at __init__; no per-hydrate instantiation needed.

        # Spec-065 T071: subscribe EventCapture.on_event to every known
        # engine EventType so any event a system publishes via
        # services.event_bus is captured into summary.events. The bus may
        # be empty of publishers today (engine integration is spec-066) but
        # the wiring is correct so spec-066 simply turns it on.
        if event_capture is not None:
            for event_type in EventType:
                self._event_bus.subscribe(event_type.value, event_capture.on_event)

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
        boundary_rows = list(self._boundary_register.flush())

        # Spec-065 T080: persist per-tick dyadic relationship state so the
        # summary's ``max_tension`` is a true cross-tick MAX over all
        # EXPLOITATION edges (spec wording: "across all ticks"). Today
        # WorldState.relationships is empty (engine doesn't mutate it),
        # so this is a no-op; once spec-066 ships the rows arrive
        # automatically without further wiring.
        relationship_rows = self._build_relationship_rows(world=world, tick=tick)

        # Spec-065 T049: run the conservation auditor against the about-to-
        # commit hex state and merge its rows into the envelope so they
        # land in conservation_audit_log inside the same transaction
        # (FR-008a). Auditor evaluators are empty in the spec-065 first
        # cut — once spec-066 registers concrete invariants this fills
        # naturally without further wiring.
        audit_rows: list[Any] = []
        if self._auditor is not None:
            audit_rows_typed, _alarms = self._auditor.audit_end_of_tick(
                session_id=self._session_id,
                tick=tick,
                hex_rows=hex_rows,
            )
            audit_rows = list(audit_rows_typed)

        envelope = PerTickTransactionEnvelope(
            session_id=self._session_id,
            tick=tick,
            hex_state_rows=hex_rows,
            external_node_rows=external_rows,
            boundary_register_rows=boundary_rows,
            audit_log_rows=audit_rows,
            consciousness_state_rows=consciousness_rows,
            demographics_state_rows=demographics_rows,
            employment_state_rows=employment_rows,
            relationship_state_rows=relationship_rows,
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

            # Spec-066 T050: pass the BASELINE_IDEOLOGY placeholder to
            # both factories so every county starts at (r=0.05, l=0.50,
            # f=0.45) per ADR043. The IdeologicalProfile is frozen, so
            # sharing the same instance is safe.
            entities[proletariat_id] = create_proletariat(
                id=proletariat_id,
                county_fips=county_fips,
                ideology=BASELINE_IDEOLOGY,
            ).model_copy(update={"population": 85})
            entities[bourgeoisie_id] = create_bourgeoisie(
                id=bourgeoisie_id,
                county_fips=county_fips,
                ideology=BASELINE_IDEOLOGY,
            ).model_copy(update={"population": 15})

        return entities

    def _build_per_county_relationships(
        self,
        *,
        scope_fips: frozenset[str],
        entities: dict[str, Any],
    ) -> list[Relationship]:
        """Spec-066 T032: seed one EXPLOITATION edge per county at tick 0.

        For each county, this maps the proletariat (``C{i:03d}``) -> the
        bourgeoisie (``C{i+500:03d}``) with edge_type=EXPLOITATION and
        starting tension=0.1 / value_flow=0.0. The ID scheme mirrors
        :meth:`_build_per_county_entities`.

        Per Constitution III.5 + Clarifications Q4, SOLIDARITY edges are
        NOT seeded here: they emerge from player verbs (Mobilize, Organize,
        Educate per Constitution V) and from a future strategic-intervention
        layer. This bridge only seeds the EXTRACTIVE relationships that
        are data-derived from the QCEW + BEA reference data via the
        ImperialRentSystem.

        Args:
            scope_fips: 5-digit FIPS codes for the scope counties.
            entities: The dict returned by :meth:`_build_per_county_entities`,
                used to confirm both endpoints exist.

        Returns:
            A list of ``Relationship`` instances, one per county.
        """
        relationships: list[Relationship] = []
        for i, _county_fips in enumerate(sorted(scope_fips), start=1):
            proletariat_id = f"C{i:03d}"
            bourgeoisie_id = f"C{i + 500:03d}"
            if proletariat_id not in entities or bourgeoisie_id not in entities:
                # _build_per_county_entities is the only producer; this is
                # defensive — surfaces silent ID drift, not a real failure
                # mode in the current call chain.
                continue
            relationships.append(
                Relationship(
                    source_id=proletariat_id,
                    target_id=bourgeoisie_id,
                    edge_type=EdgeType.EXPLOITATION,
                    value_flow=0.0,
                    tension=0.1,
                )
            )
        return relationships

    def _build_relationship_rows(
        self,
        *,
        world: WorldState,
        tick: int,
    ) -> list[DynamicRelationshipState]:
        """Convert ``world.relationships`` into per-tick rows for migration 0024.

        Spec-065 T080. Today ``world.relationships`` is empty for the
        bridged path (the engine that mutates this collection is wired
        in spec-066), so this returns ``[]`` and the SQL aggregate over
        ``dynamic_relationship_state`` yields NULL (handled gracefully
        by the consumer with a 0.0 default). The wiring is correct from
        day one: when spec-066 starts mutating ``world.relationships``,
        the rows simply start arriving without any further change.

        For SOLIDARITY edges the ``tension`` field is reused as the
        solidarity intensity since :class:`Relationship` carries one
        scalar; ``solidarity`` is mirrored from ``tension`` for SOLIDARITY
        edges and defaults to 0.0 otherwise.
        """
        if not getattr(world, "relationships", None):
            return []
        assert self._session_id is not None
        rows: list[DynamicRelationshipState] = []
        allowed = {"EXPLOITATION", "SOLIDARITY", "WAGES", "TRIBUTE", "TENANCY", "ADJACENCY"}
        for rel in world.relationships:
            edge_type_raw = (
                rel.edge_type.value if hasattr(rel.edge_type, "value") else str(rel.edge_type)
            )
            # Spec-066: EdgeType StrEnum values are lowercase ("exploitation"),
            # but the migration 0024 CHECK constraint requires uppercase
            # ('EXPLOITATION', 'SOLIDARITY', ...). Uppercase + truncate to
            # the 32-char cap; map unknown edge types to 'OTHER'.
            normalized = edge_type_raw.upper()[:32]
            edge_type = normalized if normalized in allowed else "OTHER"
            tension = float(getattr(rel, "tension", 0.0) or 0.0)
            solidarity = tension if edge_type == "SOLIDARITY" else 0.0
            rows.append(
                DynamicRelationshipState(
                    session_id=self._session_id,
                    tick=tick,
                    source_node_id=str(rel.source_id)[:64],
                    target_node_id=str(rel.target_id)[:64],
                    edge_type=edge_type,
                    tension=max(0.0, min(1.0, tension)),
                    solidarity=max(0.0, min(1.0, solidarity)),
                )
            )
        return rows

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

        # Spec-069: reference-data reads come from the in-memory cache
        # populated at hydrate_initial. No new SQLite connection is opened
        # on this per-tick path (II.6 / FR-003).
        assert self._ref_cache is not None  # hydrate_initial sets this
        demographics_row: DynamicDemographicsState | None = None
        employment_row: DynamicEmploymentState | None = None
        year = self._start_year + tick // 52

        population = self._ref_cache.lookup_population(county_fips, year)
        if population is not None:
            demographics_row = DynamicDemographicsState(
                session_id=self._session_id,  # type: ignore[arg-type]
                tick=tick,
                county_fips=county_fips,
                population=population,
            )
        elif self._ref_cache.mark_population_miss_logged(county_fips, year):
            logger.warning(
                "persist_tick: population missing for county=%s tick=%d (year=%d): "
                "no data in Census or QCEW fallback",
                county_fips,
                tick,
                year,
            )

        employment_proxy = self._ref_cache.lookup_employment_proxy(county_fips, year)
        if employment_proxy is not None:
            employment_row = DynamicEmploymentState(
                session_id=self._session_id,  # type: ignore[arg-type]
                tick=tick,
                county_fips=county_fips,
                employment_proxy=employment_proxy,
            )
        elif self._ref_cache.mark_employment_miss_logged(county_fips, year):
            logger.warning(
                "persist_tick: employment missing for county=%s tick=%d (year=%d): no QCEW data",
                county_fips,
                tick,
                year,
            )

        return consciousness_row, demographics_row, employment_row
