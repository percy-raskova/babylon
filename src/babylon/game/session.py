"""The campaign composition root (Program v1.0.0, Unit T4-core/C1).

Glues real objects into the engine's, persistence's, and projection's
EXISTING seams to run one live campaign session: a real
:class:`~babylon.engine.simulation_engine.SimulationEngine` tick loop over a
real :class:`~babylon.topology.BabylonGraph`, backed by a real
:class:`~babylon.persistence.postgres_runtime.PostgresRuntime` for session/
turn bookkeeping and crash-resume, with the vault's ``ArchiveTickBaker``
wired in as the engine's ``TickCommitObserver`` and a per-tick event-bus
collection (the WO-50 pilot pattern —
``tests/integration/archive/test_pilot_first_action.py``).

This module is deliberately OUTSIDE both ``babylon.tui`` (projection-pure by
contract — ``pyproject.toml``'s import-linter contracts forbid it from
importing the engine or persistence) and ``babylon.projection`` (never
imports the engine): the composition root is the ONE place both meet (the
WO-37 trick, generalized from store-seams to the whole session).

Two complementary, ALREADY-EXISTING ``PostgresRuntime`` persistence
mechanisms are composed here, not one reinvented:

* :meth:`~PostgresRuntime.persist_tick` / :meth:`~PostgresRuntime.
  hydrate_graph` (Feature 037) — a full node/edge/graph-metadata snapshot
  every tick. This is what a crash-resume actually RECONSTRUCTS from: an
  exact prior state, not a replay (so it carries no RNG-continuity
  assumption).
* :meth:`~PostgresRuntime.persist_tick_atomic` / :meth:`~PostgresRuntime.
  get_last_committed_tick` (spec-062/089) — the ``tick_commit`` marker
  table. This answers "how far did we get" cheaply; :func:`resume_campaign`
  uses it to pick WHICH tick to :meth:`~PostgresRuntime.hydrate_graph` from.
  The envelope this module builds carries empty hex/econ row lists (honest
  absence): the nationwide hex/econ delta pipeline is ruling 3's SEPARATE
  incremental dirty-entity-baker unit, not this one.

Scope boundary (read literally from the program plan, Part 2 "The campaign
runtime"; everything below is a stated non-goal here, not a silent gap):
the nationwide hex/econ hydration pipeline (``initialize_session`` /
``WorldStateBridge``), the lobby's campaign-picker screen and the
lobby-briefing-campaign multi-screen flow (``ArchiveApp`` is still
single-page), the narrator, and the derived-severity autopause table
(T1.1's concurrent build — see :data:`PausePredicate`).
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol
from uuid import UUID

from babylon.config.defines import GameDefines
from babylon.engine.context import TickContext
from babylon.engine.headless_runner.runner import TickCommitObserver
from babylon.engine.scenarios import WayneCountyScenario
from babylon.engine.services import ServiceContainer
from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS, SimulationEngine
from babylon.kernel.event_bus import Event
from babylon.models.config import SimulationConfig
from babylon.models.enums.events import EventType
from babylon.models.world_state import WorldState
from babylon.persistence.envelope import PerTickTransactionEnvelope
from babylon.persistence.postgres_schema import ensure_ddl_applied
from babylon.projection.verbs.submit import TurnSink, build_player_actions, submit_verb
from babylon.topology import BabylonGraph
from babylon.tui.chronicle_salience import classify_event_salience

if TYPE_CHECKING:
    from babylon.engine.scenarios.base import Scenario
    from babylon.persistence import PostgresRuntime

__all__ = [
    "GameRuntimeStore",
    "PausePredicate",
    "VaultPageSource",
    "TickAdvanceResult",
    "GameSession",
    "default_pause_predicate",
    "create_new_campaign",
    "resume_campaign",
    "ensure_schema",
    "open_runtime",
    "vault_page_source",
]


class GameRuntimeStore(TurnSink, Protocol):
    """Structural seam for everything :class:`GameSession` needs from Postgres.

    Satisfied by :class:`~babylon.persistence.postgres_runtime.PostgresRuntime`
    without this module importing a concrete backend (the WO-37 trick, no
    subclassing required — structural typing only); unit tests satisfy it
    with an in-memory fake. Extends the projection layer's own
    :class:`~babylon.projection.verbs.submit.TurnSink` (the ``submit_turn``
    seam player-verb submission already owns) with the rest of the session
    lifecycle named in the program plan (spine D): ``create_session`` /
    ``get_session`` / ``get_pending_turns`` / ``mark_turns_resolved`` /
    ``persist_tick`` / ``hydrate_graph`` / ``persist_tick_atomic`` /
    ``get_last_committed_tick``.
    """

    def create_session(
        self,
        scenario: str,
        config_json: dict[str, Any],
        game_defines_json: dict[str, Any],
        rng_seed: int,
        *,
        trace_level: str = "NONE",
        player_id: int | None = None,
    ) -> UUID:
        """Insert one ``game_session`` row and return its UUID."""
        ...

    def get_session(self, session_id: UUID) -> dict[str, Any] | None:
        """Read one ``game_session`` row back, or ``None`` if absent."""
        ...

    def get_pending_turns(self, session_id: UUID, tick: int) -> list[dict[str, Any]]:
        """Unresolved ``game_turn`` rows queued for ``tick``."""
        ...

    def mark_turns_resolved(self, session_id: UUID, tick: int) -> int:
        """Mark every unresolved turn at ``tick`` resolved; return the count."""
        ...

    def persist_tick(
        self,
        tick: int,
        graph: BabylonGraph,
        events: list[dict[str, Any]] | None = None,
        *,
        session_id: UUID | None = None,
    ) -> None:
        """Persist a full node/edge/graph-metadata snapshot at ``tick``."""
        ...

    def hydrate_graph(
        self, tick: int | None = None, *, session_id: UUID | None = None
    ) -> BabylonGraph:
        """Reconstruct the full graph snapshot at ``tick`` (latest if ``None``)."""
        ...

    def persist_tick_atomic(
        self, envelope: PerTickTransactionEnvelope, *, write_commit_marker: bool = True
    ) -> None:
        """Persist one tick's envelope + ``tick_commit`` marker atomically."""
        ...

    def get_last_committed_tick(self, session_id: UUID) -> int | None:
        """The largest tick with a committed ``tick_commit`` marker, or ``None``."""
        ...


PausePredicate = Callable[[Sequence[Event]], bool]
"""The pacing driver's autopause SEAM: one tick's raw bus events -> pause?

Deliberately narrow (events in, bool out) so T1.1's derived-severity catalog
(built concurrently, per the program plan's DEFERRED note) can supply a
stricter/table-driven predicate later with NO change to :class:`GameSession`
or its callers — only the callable the composition root injects changes.
"""

VaultPageSource = Callable[[str], "str | None"]
"""A subject id -> baked-page-markdown-or-None reader. Structurally identical
to :data:`babylon.tui.app.PageSource`; kept as a plain type alias here (not
imported from ``babylon.tui.app``) so this module does not pull in Textual
merely to describe :func:`vault_page_source`'s return shape."""


def default_pause_predicate(events: Sequence[Event]) -> bool:
    """Pause iff any of this tick's REAL bus events classify as critical.

    Ports the WO-48 ``chronicle_salience`` taxonomy — the SAME hand-
    maintained ``EVENT_SEVERITY`` table the WO-50 pilot's crisis leg
    (``test_forced_endgame_crisis_autopauses_amber_then_ack_clears``)
    exercises — not a new severity mechanism. A bus event carrying a
    non-``EventType`` ``.type`` raises loudly (Constitution III.11) rather
    than being silently ignored, mirroring the pilot's own
    ``_chronicle_events_from_bus`` adapter.

    :param events: the tick's raw event-bus history.
    :returns: ``True`` iff at least one event is critical-tier.
    """
    return any(
        classify_event_salience(EventType(event.type)).tier == "critical" for event in events
    )


def _replay_identity_hash(session_id: UUID, tick: int, rng_seed: int) -> str:
    """The envelope's replay-identity stamp.

    Mirrors ``headless_runner.runner``'s own
    ``sha256(f"{session_id}:{tick}:{seed}")`` formula (see
    :class:`~babylon.persistence.envelope.PerTickTransactionEnvelope`'s
    docstring) so the two independently-built tick loops share one hash
    convention rather than inventing a second.
    """
    return hashlib.sha256(f"{session_id}:{tick}:{rng_seed}".encode()).hexdigest()


def _as_dict(value: Any) -> dict[str, Any]:
    """Normalize a JSONB column read-back to a plain dict.

    psycopg3 auto-decodes ``jsonb`` to ``dict``/``list`` in the common case;
    this defensively handles the rarer already-a-string case the same way
    :meth:`~PostgresRuntime.hydrate_graph` guards ``row["attributes"]``.
    """
    if isinstance(value, str):
        loaded: Any = json.loads(value)
        return dict(loaded) if isinstance(loaded, dict) else {}
    return dict(value) if isinstance(value, dict) else {}


class TickAdvanceResult:
    """One resolved tick's outcome — returned by :meth:`GameSession.advance_tick`.

    Plain (not frozen-Pydantic) by deliberate choice: it carries a live
    :class:`~babylon.kernel.event_bus.Event` tuple whose entries are
    stdlib dataclasses, and a :class:`~babylon.models.world_state.WorldState`
    that is ALREADY frozen Pydantic — wrapping an already-immutable model in
    another validation layer buys nothing here; the tuple + explicit
    attributes below are themselves immutable in effect (no setters).

    :param tick: the committed tick number.
    :param world: the post-tick, post-``from_graph`` :class:`WorldState`.
    :param events: this tick's raw event-bus history (chronological).
    :param paused: the pacing driver's pause-predicate verdict for this tick.
    :param determinism_hash: the tick's replay-identity stamp (see
        :func:`_replay_identity_hash`).
    """

    __slots__ = ("determinism_hash", "events", "paused", "tick", "world")

    def __init__(
        self,
        *,
        tick: int,
        world: WorldState,
        events: tuple[Event, ...],
        paused: bool,
        determinism_hash: str,
    ) -> None:
        self.tick = tick
        self.world = world
        self.events = events
        self.paused = paused
        self.determinism_hash = determinism_hash


class GameSession:
    """One live campaign session — the engine's tick loop, seamed.

    Construct via :func:`create_new_campaign` (fresh) or
    :func:`resume_campaign` (crash-resume), not directly: both factories
    establish invariants (the ``game_session`` row, the tick-0 commit) this
    class assumes already hold.

    :param session_id: the campaign's ``game_session.id``.
    :param graph: the live, in-place-mutated engine graph.
    :param services: the constructed :class:`ServiceContainer`.
    :param engine: the 30-system :class:`SimulationEngine`.
    :param store: the Postgres runtime (or a structural fake in tests).
    :param rng_seed: the session's :class:`SimulationConfig` rng seed,
        folded into each tick's replay-identity ``determinism_hash``.
    :param tick: the last COMMITTED tick (0 immediately after a fresh
        session's tick-0 bake; the resumed tick for a crash-resume).
    :param scenario_name: the scenario's registry name, for display only —
        NOT used to reconstruct state (that is :attr:`graph`'s job).
    :param tick_commit_observer: the vault's tick-commit observer
        (:class:`~babylon.projection.vault.tick_baker.ArchiveTickBaker`),
        or ``None`` to run with no vault (tests).
    :param pause_predicate: the pacing driver's autopause SEAM; defaults to
        :func:`default_pause_predicate`.
    """

    def __init__(
        self,
        *,
        session_id: UUID,
        graph: BabylonGraph,
        services: ServiceContainer,
        engine: SimulationEngine,
        store: GameRuntimeStore,
        rng_seed: int,
        tick: int,
        scenario_name: str | None = None,
        tick_commit_observer: TickCommitObserver | None = None,
        pause_predicate: PausePredicate = default_pause_predicate,
    ) -> None:
        self.session_id = session_id
        self.graph = graph
        self.services = services
        self.engine = engine
        self.tick = tick
        self.scenario_name = scenario_name
        self._store = store
        self._rng_seed = rng_seed
        self._tick_commit_observer = tick_commit_observer
        self._pause_predicate = pause_predicate

    def submit_verb(
        self,
        *,
        org_id: str,
        verb: str,
        target_id: str | None = None,
        target_community: str | None = None,
        action_type: str | None = None,
        params_json: dict[str, Any] | None = None,
    ) -> int:
        """Queue one player verb for the NEXT tick.

        Thin passthrough to :func:`~babylon.projection.verbs.submit.submit_verb`
        with this session's own store as the ``TurnSink`` — the SAME
        affordability gate the verb plate preview shows runs here too, so a
        rejection here can never disagree with the plate's note.

        :raises ValueError: on an unknown verb, or one the org cannot afford.
        """
        return submit_verb(
            self._store,
            session_id=self.session_id,
            tick=self.tick + 1,
            org_id=org_id,
            verb=verb,
            graph=self.graph,
            action_type=action_type,
            target_id=target_id,
            target_community=target_community,
            params_json=params_json,
        )

    def advance_tick(self) -> TickAdvanceResult:
        """Resolve exactly one further tick — the pacing driver's one step.

        Mirrors the WO-50 pilot's ``_advance_tick`` (``clear_history``
        before ``run_tick``, ``get_history`` after — the exact per-tick
        event-bus collection the pilot test demonstrates) plus the REAL
        persistence (full-graph snapshot + commit marker) and vault-observer
        hookup the pilot's test-local ``_chronicle_events_from_bus`` adapter
        stands in for.

        HONEST GAP: the tick's raw events are collected and handed to the
        pause predicate, but are NOT yet written to the ``simulation_event``
        table (that table's row shape is the older ``SimulationEvent``
        pydantic model, not the kernel bus ``Event`` — a translation this
        unit does not invent without a verified contract) nor adapted into
        ``ChronicleEvent``s (the pilot's own documented gap: no production
        engine-event to ``ChronicleEvent`` adapter ships yet).
        """
        next_tick = self.tick + 1
        pending = self._store.get_pending_turns(self.session_id, next_tick)
        player_actions = build_player_actions(pending)
        context = TickContext(tick=next_tick, persistent_data={"player_actions": player_actions})

        bus = self.services.event_bus
        bus.clear_history()
        self.engine.run_tick(self.graph, self.services, context)
        events = tuple(bus.get_history())

        world = WorldState.from_graph(self.graph, tick=next_tick)
        determinism_hash = _replay_identity_hash(self.session_id, next_tick, self._rng_seed)

        self._store.persist_tick(next_tick, self.graph, session_id=self.session_id)
        self._store.persist_tick_atomic(
            PerTickTransactionEnvelope(
                session_id=self.session_id,
                tick=next_tick,
                determinism_hash=determinism_hash,
            )
        )
        self._store.mark_turns_resolved(self.session_id, next_tick)

        if self._tick_commit_observer is not None:
            self._tick_commit_observer.on_tick_committed(
                tick=next_tick, world=world, graph=self.graph
            )

        self.tick = next_tick
        paused = self._pause_predicate(events)
        return TickAdvanceResult(
            tick=next_tick,
            world=world,
            events=events,
            paused=paused,
            determinism_hash=determinism_hash,
        )


def create_new_campaign(
    store: GameRuntimeStore,
    *,
    scenario: Scenario | None = None,
    tick_commit_observer: TickCommitObserver | None = None,
    pause_predicate: PausePredicate = default_pause_predicate,
) -> GameSession:
    """Boot a brand-new campaign: build the scenario, then bake tick 0.

    :param store: the Postgres runtime (or a structural fake in tests).
    :param scenario: the scenario builder; defaults to
        :class:`~babylon.engine.scenarios.WayneCountyScenario` (ruling 3:
        "Wayne stays in lobby" — the sanctioned lightweight default).
        Scenario-specific ``build()`` kwargs (e.g. Wayne's
        ``extraction_efficiency``) are NOT threaded through here — a stated
        non-goal of this unit, not a silent omission.
    :param tick_commit_observer: the vault's tick-commit observer; when
        given, tick 0 is baked immediately (WO-44 tick-0 bake-gap parity:
        the player's first-opened dossier must exist before any turn is
        ever submitted).
    :param pause_predicate: the pacing driver's autopause SEAM (see
        :data:`PausePredicate`).
    :returns: a fresh :class:`GameSession` at tick 0.
    """
    chosen: Scenario = scenario if scenario is not None else WayneCountyScenario()
    world0, sim_config, defines = chosen.build()

    session_id = store.create_session(
        scenario=chosen.name,
        config_json=sim_config.model_dump(mode="json"),
        game_defines_json=defines.model_dump(mode="json"),
        rng_seed=sim_config.rng_seed,
    )

    graph = world0.to_graph()
    services = ServiceContainer.create(config=sim_config, defines=defines)
    engine = SimulationEngine(list(_DEFAULT_SYSTEMS))

    store.persist_tick(0, graph, session_id=session_id)
    tick0_hash = _replay_identity_hash(session_id, 0, sim_config.rng_seed)
    store.persist_tick_atomic(
        PerTickTransactionEnvelope(session_id=session_id, tick=0, determinism_hash=tick0_hash)
    )
    if tick_commit_observer is not None:
        # Uses world0 (not a from_graph round-trip) at tick 0 — mirrors the
        # headless runner's own tick-0 bake exactly (runner.py ~1616-1621):
        # the graph round-trip loses computed fields the freshly-built
        # WorldState still carries.
        tick_commit_observer.on_tick_committed(tick=0, world=world0, graph=graph)

    return GameSession(
        session_id=session_id,
        graph=graph,
        services=services,
        engine=engine,
        store=store,
        rng_seed=sim_config.rng_seed,
        tick=0,
        scenario_name=chosen.name,
        tick_commit_observer=tick_commit_observer,
        pause_predicate=pause_predicate,
    )


def resume_campaign(
    store: GameRuntimeStore,
    session_id: UUID,
    *,
    tick_commit_observer: TickCommitObserver | None = None,
    pause_predicate: PausePredicate = default_pause_predicate,
) -> GameSession:
    """Crash-resume a campaign from its last atomically-committed tick.

    Composes two complementary EXISTING ``PostgresRuntime`` mechanisms:
    :meth:`~PostgresRuntime.get_last_committed_tick` (the ``tick_commit``
    marker :meth:`~PostgresRuntime.persist_tick_atomic` writes every tick)
    answers "how far did we get"; the Feature-037 full-graph snapshot
    (:meth:`~PostgresRuntime.hydrate_graph`, written every tick by
    :meth:`~PostgresRuntime.persist_tick`) answers "what was the state
    there" — an EXACT reconstruction, not a replay.

    :param store: the Postgres runtime (or a structural fake in tests).
    :param session_id: the campaign's ``game_session.id``.
    :param tick_commit_observer: the vault's tick-commit observer.
    :param pause_predicate: the pacing driver's autopause SEAM.
    :raises ValueError: if ``session_id`` has no ``game_session`` row, or
        (a genuinely broken state — every session commits tick 0 at
        creation) has a row but no committed tick at all.
    """
    row = store.get_session(session_id)
    if row is None:
        raise ValueError(f"no game_session row for {session_id}")

    last_tick = store.get_last_committed_tick(session_id)
    if last_tick is None:
        raise ValueError(
            f"session {session_id} has a game_session row but no committed "
            "tick — it was never bootstrapped via create_new_campaign, or "
            "its tick_commit rows were lost."
        )

    graph = store.hydrate_graph(tick=last_tick, session_id=session_id)
    defines = GameDefines.model_validate(_as_dict(row["game_defines_json"]))
    sim_config = SimulationConfig.model_validate(_as_dict(row["config_json"]))
    services = ServiceContainer.create(config=sim_config, defines=defines)
    engine = SimulationEngine(list(_DEFAULT_SYSTEMS))

    return GameSession(
        session_id=session_id,
        graph=graph,
        services=services,
        engine=engine,
        store=store,
        rng_seed=sim_config.rng_seed,
        tick=last_tick,
        scenario_name=str(row.get("scenario")) if row.get("scenario") is not None else None,
        tick_commit_observer=tick_commit_observer,
        pause_predicate=pause_predicate,
    )


def ensure_schema(runtime: PostgresRuntime) -> None:
    """Apply the legacy DDL + every numbered migration (idempotent).

    ``runtime.init_schema()`` covers the Feature-037 tables this module's
    session/turn/full-graph-snapshot lifecycle needs (``game_session``,
    ``game_turn``, ``node_state``, ``edge_state``, ``graph_metadata``, ...);
    the numbered migrations under ``persistence/migrations/`` additionally
    carry the spec-062/065/089 ``tick_commit`` marker
    :meth:`~PostgresRuntime.persist_tick_atomic`'s crash-resume contract
    depends on. Mirrors the glob-and-apply pattern
    ``headless_runner.runner._apply_migrations`` uses internally (kept as
    a separate small helper rather than imported: that one is module-
    private and raises the headless runner's own ``RunnerError`` family,
    which this interactive composition root does not want to depend on).

    :param runtime: the real :class:`PostgresRuntime` to migrate.
    :raises RuntimeError: if no migration files are found (a broken
        install, not a state to silently proceed past).
    """
    runtime.init_schema()
    migrations_dir = Path(__file__).resolve().parents[1] / "persistence" / "migrations"
    sql_files = sorted(migrations_dir.glob("[0-9]*.sql"))
    if not sql_files:
        raise RuntimeError(f"no migrations found at {migrations_dir}")
    with runtime.pool.connection() as conn:
        conn.autocommit = True
        ensure_ddl_applied(conn, [sql_file.read_text() for sql_file in sql_files])


def open_runtime(dsn: str | None = None) -> PostgresRuntime:
    """Open a real :class:`PostgresRuntime` from ``BABYLON_PG_DSN``.

    :param dsn: an explicit DSN; otherwise read from ``BABYLON_PG_DSN``
        (falling back to ``BABYLON_TEST_PG_DSN``, mirroring
        ``headless_runner.runner._open_postgres_pool``'s own fallback).
    :raises RuntimeError: if no DSN is available anywhere — a loud refusal
        (Constitution III.11), never a silent demo fallback.
    """
    from psycopg_pool import ConnectionPool

    from babylon.persistence import PostgresRuntime

    resolved = dsn or os.environ.get("BABYLON_PG_DSN") or os.environ.get("BABYLON_TEST_PG_DSN")
    if not resolved:
        raise RuntimeError(
            "No Postgres DSN: set BABYLON_PG_DSN (or BABYLON_TEST_PG_DSN), or pass dsn= explicitly."
        )
    pool = ConnectionPool(resolved, min_size=1, max_size=4, open=True)
    return PostgresRuntime(pool=pool)


def vault_page_source(vault_root: Path) -> VaultPageSource:
    """A page source reading REAL baked vault pages (no fabricated content).

    Reads the exact ``<subject>.md`` path :class:`~babylon.projection.vault.
    tick_baker.ArchiveTickBaker` writes (its ``f"{kind}/{id}.md"``
    convention — e.g. ``county/26163.md``), so a subject id IS its
    vault-relative path with no extension. Returns ``None`` (never
    fabricated) for any subject the vault hasn't baked yet;
    ``ArchiveApp``'s own ``_absence_page`` renders that loudly
    (Constitution III.11).

    :param vault_root: the campaign's vault repository root.
    :returns: the page-source callable ``ArchiveApp(pages=...)`` accepts.
    """

    def _read(subject: str) -> str | None:
        try:
            return (vault_root / f"{subject}.md").read_text()
        except FileNotFoundError:
            return None

    return _read
