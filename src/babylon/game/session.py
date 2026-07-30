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
``WorldStateBridge``), the narrator, and the derived-severity autopause
table (T1.1's concurrent build — see :data:`PausePredicate`).

Unit C2 (the lobby's campaign-picker screen and the lobby->briefing->
campaign-shell multi-screen flow — since the M7 cutover, the Rust client) closes
the "still single-page" gap the paragraph above used to name here: this
module now additionally supports being booted with an EXPLICIT
``session_id`` (:func:`create_new_campaign`'s ``session_id=`` parameter) so
the lobby's own ``babylon_meta.campaign.campaign_id`` — a client-owned
epistemic identity — can double as the engine's ``game_session.id``, one
identity by construction rather than a maintained mapping between two
separate ID spaces; and an optional injected :data:`VaultPageSource`
(``pages=``) :meth:`GameSession.read_page` thinly wraps, satisfying the
TUI's ``CampaignHandle`` seam (``babylon.tui.contract``) without either module
importing the other.

Unit C6 (the save wire — progress + autosave + resume) closes the
remaining gap this module used to carry silently:
:meth:`~babylon.persistence.babylon_meta.BabylonMetaStore.record_progress`
is now called every tick a :class:`ProgressStore` is wired (see
:class:`ProgressStore` below — previously unwired to zero production
callers); :attr:`TickAdvanceResult.autosaved` marks the program plan's
"autosave cadence 52 (``CHECKPOINT_EVERY_TICKS`` analog)" release
requirement by reusing :func:`~babylon.persistence.delta.
is_checkpoint_tick` — the SAME spec-089 constant the hex-delta pipeline
already checkpoints on, not a second, competing cadence constant; and
crash-resume is :func:`resume_campaign` composing the two ALREADY-EXISTING
mechanisms named above (:meth:`~PostgresRuntime.get_last_committed_tick` +
:meth:`~PostgresRuntime.hydrate_graph`) — this unit adds no new
persistence mechanism there, only the proof
(``tests/integration/game/test_session_integration.py``) that the
composition wired here actually round-trips through real Postgres.
Pg_dump-style save ARTIFACTS (a portable file a player can copy/share) are
T7's installer-scoped concern, not this module's.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Protocol
from uuid import UUID

from babylon.config.defines import GameDefines
from babylon.engine.context import TickContext
from babylon.engine.headless_runner.runner import TickCommitObserver
from babylon.engine.observers.endgame_detector import EndgameDetector
from babylon.engine.scenarios import WayneCountyScenario
from babylon.engine.services import ServiceContainer
from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS, SimulationEngine
from babylon.game.actions.player_driver import issue_action
from babylon.game.chronicle_adapter import chronicle_events_from_bus
from babylon.kernel.event_bus import Event
from babylon.models.config import SimulationConfig
from babylon.models.enums import CommunityType
from babylon.models.enums.events import EventType, GameOutcome
from babylon.models.world_state import WorldState
from babylon.persistence.delta import is_checkpoint_tick
from babylon.persistence.envelope import PerTickTransactionEnvelope
from babylon.persistence.postgres_aggregation import NationalValueAggregate
from babylon.persistence.postgres_schema import ensure_ddl_applied
from babylon.projection.community import project_community
from babylon.projection.county import project_county
from babylon.projection.economy import project_economy
from babylon.projection.endgame import EndgameStatus
from babylon.projection.endgame import endgame_status as fold_endgame_status
from babylon.projection.field_state import project_field_state
from babylon.projection.fog.county_status import county_fog_status
from babylon.projection.fog.ledger import IntelLedger
from babylon.projection.industry import project_industry
from babylon.projection.institution import project_institution
from babylon.projection.key_figure import project_key_figure
from babylon.projection.national import project_national
from babylon.projection.organization import project_organization
from babylon.projection.social_class import project_social_class
from babylon.projection.sovereign import project_sovereign
from babylon.projection.state import project_state
from babylon.projection.tick_summary import build_tick_summary_kwargs
from babylon.projection.topology.incidence import adjacency_ordering, incidence_ordering
from babylon.projection.topology.layout import bipartite_shell_layout
from babylon.projection.topology.levi import levi_ego_tree
from babylon.projection.topology.map_lenses import (
    FOG_BANDS,
    TENSION_BANDS,
    VALUE_BANDS,
    county_value_cells,
    state_fog_status,
    state_tension_cells,
    state_value_cells,
)
from babylon.projection.topology.paoh import paoh_ordering
from babylon.projection.topology.tension import county_tension_cells
from babylon.projection.trade import project_trade_bloc, project_trade_overview
from babylon.projection.verbs.plate import build_verb_plate
from babylon.projection.verbs.submit import TurnSink, build_player_actions, submit_verb
from babylon.projection.verbs.view_models import VerbPlateView
from babylon.projection.view_models import (
    CommunityView,
    EconomyView,
    FieldStateView,
    NationalTrendView,
    ProjectionRecord,
    TradeBlocView,
)
from babylon.topology import BabylonGraph
from babylon.tui.chronicle import ChronicleEvent
from babylon.tui.chronicle_salience import classify_event_salience
from babylon.tui.trade_dossier import render_trade_page

if TYPE_CHECKING:
    from collections.abc import Mapping

    from babylon.domain.economics.boundary_flow_register import BoundaryFlowRegisterRow
    from babylon.engine.scenarios.base import Scenario
    from babylon.game.trade import TradeWiring
    from babylon.persistence import PostgresRuntime

__all__ = [
    "EndgameProgressObserver",
    "GameRuntimeStore",
    "KnownSubjectsSource",
    "NarratorScheduler",
    "PausePredicate",
    "ProgressStore",
    "VaultPageSource",
    "TickAdvanceResult",
    "GameSession",
    "default_pause_predicate",
    "create_new_campaign",
    "resume_campaign",
    "ensure_schema",
    "open_runtime",
    "vault_known_subjects",
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
    ``get_last_committed_tick`` / ``persist_tick_summary`` (T5 Unit U2 — the
    ``tick_summary`` read-model write, previously only reachable through the
    legacy web bridge).
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
        session_id: UUID | None = None,
    ) -> UUID:
        """Insert one ``game_session`` row and return its UUID.

        :param session_id: an explicit id to insert, rather than letting
            the store mint one (Unit C2: lets a lobby-chosen
            ``babylon_meta.campaign_id`` double as this row's own id — one
            identity, not a maintained mapping); ``None`` mints one as
            before.
        """
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
        self,
        envelope: PerTickTransactionEnvelope,
        *,
        write_commit_marker: bool = True,
        graph: BabylonGraph | None = None,
        events: list[dict[str, Any]] | None = None,
    ) -> None:
        """Persist one tick's envelope + ``tick_commit`` marker atomically.

        ``graph`` (ADR176 ruling 28, the torn-tick fix): when supplied, the
        adjudicating node/edge/graph-metadata snapshot rides the SAME
        transaction as the commit marker — the session never again writes
        topology in a transaction the marker doesn't cover.
        """
        ...

    def get_last_committed_tick(self, session_id: UUID) -> int | None:
        """The largest tick with a committed ``tick_commit`` marker, or ``None``."""
        ...

    def persist_tick_summary(
        self,
        tick: int,
        summary: dict[str, Any],
        *,
        session_id: UUID,
    ) -> None:
        """Persist one pre-aggregated ``tick_summary`` row (T5 Unit U2)."""
        ...

    def fetch_national_trend(self, session_id: UUID, last_n: int) -> list[NationalTrendView]:
        """The last ``last_n`` ``v_national_trend`` rows, oldest→newest
        (M6 Task 41 — the market dashboard's trend read)."""
        ...

    def fetch_latest_national_aggregate(self, session_id: UUID) -> NationalValueAggregate | None:
        """The most recent ``v_national_value_aggregate`` row, or ``None``
        (M6 Task 41 — the ``national_value`` snapshot read)."""
        ...


class ProgressStore(Protocol):
    """Structural seam for the client-owned ``babylon_meta.campaign`` lobby row.

    Satisfied by :class:`~babylon.persistence.babylon_meta.BabylonMetaStore`'s
    :meth:`~babylon.persistence.babylon_meta.BabylonMetaStore.record_progress`
    without this module importing that store (the same WO-37 trick
    :class:`GameRuntimeStore` already uses) — kept as its own narrow seam
    rather than folded into :class:`GameRuntimeStore` because it writes a
    DIFFERENT tier (the client-owned epistemic catalog, not the engine's
    Ledger). Optional everywhere it is threaded through: a session with no
    ``progress_store`` runs exactly as it did before this seam existed (unit
    tests, and any caller with no lobby catalog to keep live).
    """

    def record_progress(self, campaign_id: UUID, *, last_tick: int) -> None:
        """Record that ``campaign_id`` reached ``last_tick`` just now."""
        ...


class NarratorScheduler(Protocol):
    """Structural seam for the async narrator side-process (T5 Unit U1).

    Satisfied by :class:`~babylon.projection.vault.narrator_cache.
    NarratorSideProcess` (fire-and-forget: :meth:`schedule` never blocks and
    never raises, per that class's own docstring) without this module
    importing that concrete class — the same WO-37 trick
    :class:`GameRuntimeStore`/:class:`ProgressStore` already use. ``None``
    (the constructor default) means the narrator lane is OFF:
    :meth:`GameSession.advance_tick` then never calls :meth:`schedule` at
    all, so narrator-OFF stays the exact pre-Unit-U1 byte-identical path
    (Constitution's determinism tiering — narrator-ON is non-reproducible
    BY DESIGN and only ever touches the vault's ``narrative/`` subtree,
    never a baked deterministic page).
    """

    def schedule(self, entity_id: str, tick: int, *, system: str, prompt: str) -> object:
        """Submit one narration generation for ``(entity_id, tick)``; never
        blocks, never raises (the implementation's own contract)."""
        ...


class EndgameProgressObserver(Protocol):
    """Structural seam for :class:`GameSession`'s own endgame-progress detector
    (Program 24 P4 — the live HUD's "how close" read-model).

    :class:`~babylon.engine.observers.endgame_detector.EndgameDetector`
    satisfies this structurally (the WO-37 trick — no runtime dependency
    beyond what this composition-root module already carries directly
    elsewhere; this Protocol exists so a unit test can inject a deterministic
    double, matching :class:`TickCommitObserver`'s own already-established
    pattern in this file). A STRICT SUPERSET of :mod:`~babylon.game.pacing`'s
    OWN, narrower ``EndgameObserver`` (which reads only ``recognized_pattern``/
    ``on_tick`` for the pacing driver's permanent lock latch): this
    session-owned instance additionally exposes ``pattern_since_tick`` and
    ``axis_progress`` for :meth:`GameSession.endgame_status`'s fold.

    Deliberately a SEPARATE detector instance from whatever
    :func:`~babylon.game.pacing.paced_driver_for_session` constructs for the
    SAME campaign when a driver is wired, rather than one shared object: both
    are pure re-derivations of the identical committed-tick world stream
    (:meth:`~babylon.engine.observers.endgame_detector.EndgameDetector.on_tick`'s
    own docstring notes ``previous_state`` is unused by every current axis
    evaluator, so the two instances can never disagree on what they report)
    — this trades a small amount of duplicate per-tick computation for a HUD
    accessor that needs no coupling to whether, or how, a pacing driver
    happens to be wired for this particular boot.
    """

    @property
    def recognized_pattern(self) -> GameOutcome | None:
        """The currently recognized terminal pattern, or ``None``."""
        ...

    @property
    def pattern_since_tick(self) -> int | None:
        """The tick ``recognized_pattern`` was last set (or cleared)."""
        ...

    def axis_progress(self) -> dict[str, float]:
        """This tick's five-axis progress payload, each in ``[0.0, 1.0]``."""
        ...

    def on_tick(self, previous_state: WorldState, new_state: WorldState) -> None:
        """Re-evaluate every endgame axis against this tick's states."""
        ...


PausePredicate = Callable[[Sequence[Event]], bool]
"""The pacing driver's autopause SEAM: one tick's raw bus events -> pause?

Deliberately narrow (events in, bool out) so T1.1's derived-severity catalog
(built concurrently, per the program plan's DEFERRED note) can supply a
stricter/table-driven predicate later with NO change to :class:`GameSession`
or its callers — only the callable the composition root injects changes.
"""

VaultPageSource = Callable[[str], "str | None"]

#: The county-geometry seam (M5 Task 37): given the county FIPS set a
#: choropleth call emits, return ``fips -> WKT`` for whatever subset the
#: reference data can serve. ``None`` (the default) is honest geometry
#: absence — cells ship ``wkt: null`` and the client renders centroid-
#: less absence, never a fabricated polygon.
CountyWktSource = Callable[[frozenset[str]], dict[str, str]]
"""A subject id -> baked-page-markdown-or-None reader. Structurally identical
to :data:`babylon.tui.contract (the read_page seam)`; kept as a plain type alias here (not
imported from the client package) so this module stays layer-clean
merely to describe :func:`vault_page_source`'s return shape."""

KnownSubjectsSource = Callable[[], "frozenset[str]"]
"""A zero-arg reader of every subject id a campaign's vault has baked so far.
Structurally identical to the return shape of
:data:`babylon.tui.contract.CampaignHandle`'s ``known_subjects`` seam (Unit U1);
kept as a plain type alias here for the same reason :data:`VaultPageSource`
is — no Textual import merely to describe :func:`vault_known_subjects`'s
return shape."""


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


#: The one narration subject id :meth:`GameSession.advance_tick` schedules
#: against per committed tick — mirrors ``tick_baker._NATIONAL_ID``'s
#: ``"national/USA"`` sentinel/subject-id convention (the one nationwide
#: "wind is blowing" beat), so its narrative page lands at
#: ``narrative/national/USA/<tick>--<pin>.md`` alongside the deterministic
#: ``national/USA.md`` dossier it narrates.
_NARRATOR_SUBJECT: Final[str] = "national/USA"

#: The one economy dossier id :meth:`GameSession.dashboard_view` projects
#: against — mirrors ``tick_baker._ECONOMY_ID``'s own ``"USA"`` singleton
#: convention (the one nationwide economy dossier), so the live dashboard
#: HUD and the vault-baked ``economy/USA`` page describe the same economy.
_DASHBOARD_ECONOMY_ID: Final[str] = "USA"

#: The human player's fixed :class:`~babylon.game.actions.registry.ActionSpec`
#: ``agent_types`` persona (Program 24 P5) — distinct from the acting org
#: node's own ``org_type`` attribute (``political_faction``/``civil_society``/
#: etc.): every Article V verb in the registry is gated to this one bucket,
#: so :meth:`GameSession.issue_verb` always issues as "organizer", never a
#: value derived from the org's graph attributes.
_PLAYER_AGENT_TYPE: Final[str] = "organizer"


def _narrator_beat(tick: int, chronicle: tuple[ChronicleEvent, ...]) -> tuple[str, str]:
    """The ``(system, prompt)`` pair one committed tick schedules narration with.

    Minimal and honest by deliberate scope choice: built ONLY from this
    tick's own committed chronicle (real per-event summaries from
    :func:`~babylon.game.chronicle_adapter.chronicle_events_from_bus`),
    never fabricated (Constitution III.11). Doctrine-conditioning of prompts
    and the trend-view digest ("the wind is blowing" build, spine E) are
    DEFERRED past this unit — :mod:`~babylon.projection.vault.narrator_cache`
    already treats ``(system, prompt)`` as opaque caller-supplied text.

    :param tick: the committed tick number.
    :param chronicle: this tick's chronicle events, chronological (see
        :attr:`TickAdvanceResult.chronicle`).
    :returns: the ``(system, prompt)`` pair for :meth:`NarratorScheduler.schedule`.
    """
    system = (
        "You are the Narrator: observe this committed tick's material state "
        "and write one brief, grounded prose beat. Never invent facts beyond "
        "what is given."
    )
    body = "; ".join(event.summary for event in chronicle) if chronicle else "no events recorded"
    prompt = f"Tick {tick} committed. {body}."
    return system, prompt


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


def _project_community_or_none(
    entity_id: str, *, world: WorldState, tick: int
) -> ProjectionRecord | None:
    """``project_community``, guarded against a caller-typed non-enum id.

    Every other Lane P kind's :func:`project_<kind>` returns an
    all-``None``-but-``id`` view for an id that names no real node/entity
    (:func:`~babylon.projection.county.project_county`'s own documented
    shape). ``community`` is the one exception: its identity check
    (``CommunityType(community_id)``, inside :func:`~babylon.projection.
    community.project_community` itself) raises a plain ``ValueError`` for
    a value outside the enum — **verified against the actual enum
    construction, not that module's own docstring claim of
    ``pydantic.ValidationError``** — rather than degrading to absence.

    :meth:`GameSession.subject_view` can be asked to resolve an arbitrary
    pinned subject id, including one a player free-typed into a
    ``babylon://community/...`` URI that the client's navigation already
    renders as an honest absence *page* (Constitution III.11); this wrapper
    converts that ONE documented, caller-identity failure into the SAME
    honest ``None`` :meth:`GameSession.subject_view` already returns for an
    unrecognized subject kind — never a bare crash reaching the shell — a
    genuinely malformed *value* deeper inside a valid community's own
    membership rows (a real data-integrity bug) still raises loud, unmasked.

    :param entity_id: the subject id's segment after ``"community/"``.
    :param world: the committed post-tick world state.
    :param tick: the committed tick this dossier is projected from.
    :returns: the projected :class:`~babylon.projection.view_models.
        CommunityView`, or ``None`` when ``entity_id`` names no real
        :class:`~babylon.models.enums.CommunityType` member.
    """
    try:
        CommunityType(entity_id)
    except ValueError:
        return None
    return project_community(entity_id, world=world, tick=tick)


def _community_views(world: WorldState, *, tick: int) -> tuple[CommunityView, ...]:
    """Project every community's dossier, in ``CommunityType``'s own sorted order (M4 §1).

    Shared by :meth:`GameSession.topology_view`'s ``paoh``/``incidence``/
    ``adjacency`` kinds — the identical 14-member fan-out those three
    ordering providers (:func:`~babylon.projection.topology.paoh.
    paoh_ordering`, :func:`~babylon.projection.topology.incidence.
    incidence_ordering`/:func:`~babylon.projection.topology.incidence.
    adjacency_ordering`) each need over the SAME already-built
    :class:`WorldState`, extracted once rather than repeated inline three
    times (the contract's own "extracted as a small shared helper" ruling).

    :param world: the already-built post-tick world — built EXACTLY ONCE per
        :meth:`GameSession.topology_view` call; this helper never calls
        ``WorldState.from_graph`` itself.
    :param tick: the committed tick this dossier batch is projected from.
    :returns: one :class:`~babylon.projection.view_models.CommunityView` per
        :class:`~babylon.models.enums.CommunityType` member, in the enum's
        own sorted (lexicographic) order. Every downstream ordering provider
        re-sorts its own rosters/hyperedges anyway (each module's own
        docstring), so this order is not itself load-bearing — only
        completeness (every one of the 14 members represented, attributed or
        not) is.
    """
    return tuple(
        project_community(community_type.value, world=world, tick=tick)
        for community_type in sorted(CommunityType)
    )


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
    :param chronicle: this tick's raw ``events``, promoted to
        :class:`~babylon.tui.chronicle.ChronicleEvent`\\ s via
        :func:`~babylon.game.chronicle_adapter.chronicle_events_from_bus`
        (Unit C4) — same order, one-to-one with ``events``. The Chronicle
        client's real content source; never re-derived from ``world``.
        Class-scoped events (e.g. UPRISING) carry a resolved territory
        ``anchor`` when the graph's TENANCY edges make one resolvable
        (Unit U5), since ``chronicle`` is built from :attr:`graph` itself,
        not ``world``.
    :param paused: the pacing driver's pause-predicate verdict for this tick.
    :param autosaved: ``True`` iff this tick is a checkpoint tick under
        :func:`~babylon.persistence.delta.is_checkpoint_tick` (Unit C6 —
        the program plan's "autosave cadence 52" release requirement,
        reusing the SAME spec-089 ``CHECKPOINT_EVERY_TICKS`` constant the
        hex-delta pipeline already checkpoints on rather than a second,
        competing cadence). Marks the OFFICIAL yearly savepoints; every
        tick (checkpoint or not) already persists a full snapshot via
        :meth:`~PostgresRuntime.persist_tick` +
        :meth:`~PostgresRuntime.persist_tick_atomic` above — this flag
        never means "only checkpoint ticks are safe to resume from," it
        flags the coarser cadence a UI/save-browser should advertise to
        the player.
    :param determinism_hash: the tick's replay-identity stamp (see
        :func:`_replay_identity_hash`).
    """

    __slots__ = ("autosaved", "chronicle", "determinism_hash", "events", "paused", "tick", "world")

    def __init__(
        self,
        *,
        tick: int,
        world: WorldState,
        events: tuple[Event, ...],
        chronicle: tuple[ChronicleEvent, ...],
        paused: bool,
        autosaved: bool,
        determinism_hash: str,
    ) -> None:
        self.tick = tick
        self.world = world
        self.events = events
        self.chronicle = chronicle
        self.paused = paused
        self.autosaved = autosaved
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
    :param pages: this campaign's own :data:`VaultPageSource` (typically
        :func:`vault_page_source` over its own vault root), read via
        :meth:`read_page`; ``None`` (the default) reads honestly absent for
        every subject — the pre-Unit-C2 no-vault path.
    :param known_subjects: this campaign's own :data:`KnownSubjectsSource`
        (typically :func:`vault_known_subjects` over its own vault root,
        Unit U1), read via :meth:`known_subjects`; ``None`` (the default)
        reads honestly empty — the pre-Unit-U1 no-vault path.
    :param progress_store: the lobby's :class:`ProgressStore` seam
        (typically the same ``BabylonMetaStore`` the composition root's
        ``CampaignMenu`` already holds); ``None`` (the default) runs with no
        lobby catalog to keep live — the pre-writeback no-op path.
    :param narrator: this campaign's own :class:`NarratorScheduler` seam
        (typically a real :class:`~babylon.projection.vault.narrator_cache.
        NarratorSideProcess` over this campaign's own vault root, T5 Unit
        U1); ``None`` (the default) means the narrator lane is OFF —
        :meth:`advance_tick` never calls :meth:`~NarratorScheduler.schedule`
        at all, the pre-Unit-U1 byte-identical path.
    :param endgame_detector: this session's own :class:`EndgameProgressObserver`
        seam (Program 24 P4), read by :meth:`endgame_status`; ``None`` (the
        default) self-constructs a real
        :class:`~babylon.engine.observers.endgame_detector.EndgameDetector`
        over ``services.defines`` — the same coefficients the tick loop
        itself already runs under, not a mismatched fresh default set. Tests
        inject a deterministic double here.
    :param trade: this campaign's :class:`~babylon.game.trade.TradeWiring`
        seam (P26 U2 — ``specs/101-trade-activation/
        u2-interactive-parity-contracts.md``). When wired,
        :meth:`advance_tick` stamps the spec-101 Φ-distribution context
        inputs (plus ``simulated_year``/``vol2_step``) each tick and folds
        the register's DRAIN_EDGE rows into the per-tick envelope; ``None``
        (the default) is the byte-identical pre-U2 path — no key stamped,
        both ``economic.py`` sub-stages stay gated.
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
        pages: VaultPageSource | None = None,
        known_subjects: KnownSubjectsSource | None = None,
        progress_store: ProgressStore | None = None,
        narrator: NarratorScheduler | None = None,
        endgame_detector: EndgameProgressObserver | None = None,
        trade: TradeWiring | None = None,
        county_wkt: CountyWktSource | None = None,
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
        self._pages = pages
        self._known_subjects = known_subjects
        self._progress_store = progress_store
        self._narrator = narrator
        self._trade = trade
        self._county_wkt = county_wkt
        # P26 U6: the most recent tick's flushed DRAIN_EDGE rows, retained
        # for the trade dossiers (the register itself is empty post-flush).
        self._last_boundary_rows: list[BoundaryFlowRegisterRow] = []
        self._endgame_detector: EndgameProgressObserver = (
            endgame_detector
            if endgame_detector is not None
            else EndgameDetector(defines=services.defines)
        )

    def read_page(self, subject: str) -> str | None:
        """Read one REAL baked vault page for this campaign (Unit C2).

        Thin passthrough to the injected :data:`VaultPageSource` (see
        :attr:`pages` on the constructor); satisfies ``babylon.tui.contract``'s
        ``CampaignHandle.read_page`` seam without that module importing
        this one.

        P26 U6 phase 2: ``trade/*`` subjects are the ONE exception — they
        are never baked into the persisted vault (Contract 2's deferral
        still stands in phase 2: baking lands with a declared §6.5
        ceremony alongside U5's content, not as a side effect here), so
        this method renders them LIVE instead, via
        :func:`~babylon.tui.trade_dossier.render_trade_page` over
        :meth:`_project_trade_subject`'s fresh view-model — computed on
        every call, never cached, the same posture :meth:`dashboard_view`/
        :meth:`subject_view` already use. An unwired campaign or an
        unknown bloc id degrades to ``None`` here too (honest absence,
        Constitution III.11) — :meth:`~babylon.tui.contract.CampaignHandle.
        _navigate` already renders that as its own loud absence page.

        :param subject: the vault-relative subject id (e.g.
            ``"county/26163"``, ``"briefing/<session_id>"``, or
            ``"trade/overview"``/``"trade/<node_id>"``).
        :returns: the page's rendered markdown, or ``None`` if no vault is
            wired (constructor default), the vault hasn't baked that
            subject yet, or (``trade/*`` only) the campaign has no trade
            wiring / names an unknown bloc — never fabricated content
            (Constitution III.11).
        """
        kind, separator, entity_id = subject.partition("/")
        if separator and kind == "trade":
            view = self._project_trade_subject(entity_id)
            # `_project_trade_subject` only ever returns a `TradeBlocView` (or
            # `None`) — its return type is the wider `ProjectionRecord` union
            # only because it satisfies `subject_view`'s own shared return
            # type; narrow explicitly rather than asking `render_trade_page`
            # to accept a union it cannot actually receive a non-trade member
            # of.
            if isinstance(view, TradeBlocView):
                return render_trade_page(view)
            return None
        return self._pages(subject) if self._pages is not None else None

    def known_subjects(self) -> frozenset[str]:
        """Every subject id this campaign's vault has baked so far (Unit U1).

        Thin passthrough to the injected :data:`KnownSubjectsSource` (see
        :attr:`known_subjects` on the constructor), read fresh on every
        call; satisfies ``babylon.tui.contract``'s ``CampaignHandle.
        known_subjects`` seam the same way :meth:`read_page` satisfies
        ``read_page`` — without either module importing the other.

        P26 U6 phase 2: unioned with this campaign's own live trade ids
        (``"trade/overview"`` plus one ``"trade/<node_id>"`` per attributed
        bloc) whenever :attr:`_trade` is wired — the same live-not-baked
        posture :meth:`read_page` documents for ``trade/*``, so a trade
        subject is discoverable via the command palette
        (:class:`~babylon.tui.palette.EntityNavigatorProvider`) and
        classifies as a known (not redlink) wikilink target the instant
        trade is wired, with no vault bake required. An unwired campaign
        (``_trade is None``) contributes nothing — honest absence, never a
        fabricated demo set (Constitution III.11).

        :returns: the current baked-subject frozenset, unioned with the
            live trade subject set, or just the baked set if no vault
            reader is wired and trade is unwired — never fabricated
            (Constitution III.11).
        """
        baked = self._known_subjects() if self._known_subjects is not None else frozenset()
        if self._trade is None:
            return baked
        trade_ids = {"trade/overview"}
        trade_ids.update(f"trade/{node_id}" for node_id in self._trade.external_nodes_phi)
        return baked | frozenset(trade_ids)

    def dashboard_view(self) -> EconomyView:
        """Project this campaign's live economy dashboard (Program 24 P2).

        Computed FRESH on every call via :func:`~babylon.projection.economy.
        project_economy`, over this session's own live, in-place-mutated
        :attr:`graph` — the same ``WorldState.from_graph`` reconstruction
        :meth:`advance_tick` already performs post-tick, not a cached,
        potentially-stale snapshot, so a call between ticks always reflects
        the graph's CURRENT state. Satisfies ``babylon.tui.contract.
        CampaignHandle.dashboard_view`` without either module importing the
        other (the same WO-37 trick :meth:`read_page`/:meth:`known_subjects`
        already use) — this is the ONE place ``project_economy`` is ever
        called from a live campaign; ``babylon.tui`` only ever renders the
        :class:`~babylon.projection.view_models.EconomyView` this returns.

        :returns: the freshly-projected :class:`~babylon.projection.
            view_models.EconomyView`. Never ``None`` for a real
            ``GameSession`` (there is always a live graph/tick to project
            from) — the Protocol's ``EconomyView | None`` return
            accommodates OTHER ``CampaignHandle`` implementations/test
            doubles that choose not to wire a live projection at all.
        """
        world = WorldState.from_graph(self.graph, tick=self.tick)
        return project_economy(_DASHBOARD_ECONOMY_ID, graph=self.graph, world=world, tick=self.tick)

    def trend_view(self, last_n: int) -> tuple[NationalTrendView, ...]:
        """The last ``last_n`` committed trend rows, oldest→newest (M6 Task 41).

        Computed FRESH on every call (the :meth:`dashboard_view` contract —
        never a cached snapshot) via the store seam's
        ``fetch_national_trend`` over the ``v_national_trend`` declared view
        (Constitution II.11; raw ``tick_summary`` is prohibited). Satisfies
        ``babylon.tui.contract.CampaignHandle.trend_view`` without either module
        importing the other (the WO-37 trick every sibling method uses).

        :param last_n: How many most-recent ticks to window.
        :returns: Chart-ready rows in ascending tick order; empty before
            the first committed tick (honest absence, never fabricated).
        :raises ValueError: on a non-positive ``last_n`` — LOUD, the M4
            out-of-vocabulary precedent, refused BEFORE any read runs.
        """
        if last_n < 1:
            raise ValueError(f"trend_view last_n must be positive, got {last_n}")
        return tuple(self._store.fetch_national_trend(self.session_id, last_n))

    def national_value_snapshot(self) -> NationalValueAggregate | None:
        """The most recent national value-composition row, or ``None`` (M6).

        Read via the store seam from ``v_national_value_aggregate`` — the
        c/v/s/k sums live in the hex ledger, not the graph (spec-089), and
        that ledger is written at hydration time and never re-written by
        :meth:`advance_tick` (the M5 recon's finding of record), so the
        returned row's own ``tick`` IS the staleness disclosure consumers
        must surface. ``None`` = no hex hydration ran (honest absence).
        """
        return self._store.fetch_latest_national_aggregate(self.session_id)

    def _project_trade_subject(self, entity_id: str) -> ProjectionRecord | None:
        """Project one ``trade/*`` dossier (P26 U6 phase 1).

        Projected from session-held wiring plus the last tick's flushed
        DRAIN_EDGE rows — no graph/world reconstruction needed. An unwired
        campaign (``trade=None``) is an honest absence for EVERY trade
        subject (contract: ``specs/103-trade-surfaces/
        u6-archive-trade-surfaces-contracts.md``).

        :param entity_id: an external node id, or ``"overview"``.
        :returns: the projected view, or ``None`` (unwired campaign /
            unknown node).
        """
        if self._trade is None:
            return None
        last_flows: dict[str, float] = {}
        for row in self._last_boundary_rows:
            last_flows[row.source_node_id] = last_flows.get(row.source_node_id, 0.0) + row.magnitude
        if entity_id == "overview":
            return project_trade_overview(
                external_nodes_phi=self._trade.external_nodes_phi,
                county_exposure_by_external=self._trade.county_exposure_by_external,
                weeks_per_year=self._trade.weeks_per_year,
                last_flows=last_flows,
                tick=self.tick,
            )
        return project_trade_bloc(
            entity_id,
            external_nodes_phi=self._trade.external_nodes_phi,
            county_exposure_by_external=self._trade.county_exposure_by_external,
            weeks_per_year=self._trade.weeks_per_year,
            last_flows=last_flows,
            tick=self.tick,
        )

    def subject_view(self, subject_id: str) -> ProjectionRecord | None:
        """Project one pinnable subject's live dossier view-model (shell-interconnect).

        Computed FRESH on every call — the SAME ``WorldState.from_graph``
        reconstruction over this session's own live, in-place-mutated
        :attr:`graph` :meth:`dashboard_view` already establishes the
        "compute fresh, never cache" contract for — dispatching by
        ``subject_id``'s ``"<kind>/<entity_id>"`` shape onto whichever of
        the ten already-existing Lane P ``project_<kind>`` functions
        (:mod:`babylon.projection.county`/``state``/``national``/
        ``organization``/``institution``/``sovereign``/``industry``/
        ``social_class``/``community``/``key_figure``) that kind names —
        the exact per-kind call shape :mod:`~babylon.projection.vault.
        tick_baker`/:mod:`~babylon.projection.vault.incremental_baker`
        already use to bake real vault pages, reused here rather than
        reinvented. Satisfies ``babylon.tui.contract.CampaignHandle.
        subject_view`` without either module importing the other (the
        WO-37 trick :meth:`read_page`/:meth:`known_subjects`/
        :meth:`dashboard_view`/:meth:`verb_plate_view` already use) — this
        is the ONE place any of these ten ``project_<kind>`` functions is
        ever called for a single pinned subject from a live campaign;
        ``babylon.tui`` only ever renders the :data:`~babylon.projection.
        view_models.ProjectionRecord` this returns.

        Every kind's own ``project_<kind>`` already degrades a real-but-
        unresolvable entity id to an honest all-``None``-but-``id`` view
        (never a crash — :func:`~babylon.projection.county.project_county`'s
        documented shape, shared by every sibling Lane P projector except
        ``community``, guarded by :func:`_project_community_or_none`
        instead); this method's OWN absence case is a subject id whose
        *kind* (the segment before the first ``"/"``) names none of the
        ten, or carries no ``"/"`` at all.

        :param subject_id: the vault-relative subject id (e.g.
            ``"county/26163"`` or ``"organization/ORG001"``).
        :returns: the freshly-projected view-model, or ``None`` when
            ``subject_id``'s kind is not one of the ten pinnable Lane P
            kinds, or (``community`` only) names no real
            :class:`~babylon.models.enums.CommunityType` member — an
            honest absence (Constitution III.11), rendered by
            :meth:`~babylon.tui.contract.CampaignHandle._refresh_watchlist`'s own
            already-established "no longer resolvable" row, never a crash
            or a silently dropped pin.
        """
        kind, separator, entity_id = subject_id.partition("/")
        if not separator:
            return None
        if kind == "trade":
            return self._project_trade_subject(entity_id)
        world = WorldState.from_graph(self.graph, tick=self.tick)
        if kind == "county":
            return project_county(entity_id, graph=self.graph, world=world, tick=self.tick)
        if kind == "state":
            return project_state(entity_id, graph=self.graph, world=world, tick=self.tick)
        if kind == "national":
            return project_national(entity_id, graph=self.graph, world=world, tick=self.tick)
        if kind == "organization":
            return project_organization(entity_id, graph=self.graph, world=world, tick=self.tick)
        if kind == "institution":
            return project_institution(entity_id, graph=self.graph, tick=self.tick)
        if kind == "sovereign":
            return project_sovereign(entity_id, graph=self.graph, world=world, tick=self.tick)
        if kind == "industry":
            return project_industry(entity_id, graph=self.graph, world=world, tick=self.tick)
        if kind == "social_class":
            return project_social_class(entity_id, graph=self.graph, world=world, tick=self.tick)
        if kind == "community":
            return _project_community_or_none(entity_id, world=world, tick=self.tick)
        if kind == "key_figure":
            return project_key_figure(entity_id, graph=self.graph, world=world, tick=self.tick)
        return None

    def endgame_status(self) -> EndgameStatus:
        """Fold this session's own endgame-progress detector into the
        Archive HUD's live status (Program 24 P4).

        Reads :attr:`_endgame_detector` — updated exactly once per real
        committed tick, inside :meth:`advance_tick` (never re-derived here) —
        through :func:`~babylon.projection.endgame.endgame_status`, the SAME
        fold :meth:`dashboard_view`'s own P2 seam already established the
        pattern for: this composition root is the ONE place the fold is ever
        called from a live campaign; ``babylon.tui`` only ever renders the
        :class:`~babylon.projection.endgame.EndgameStatus` this returns.
        Satisfies ``babylon.tui.contract.CampaignHandle.endgame_status`` without
        either module importing the other (the WO-37 trick
        :meth:`read_page`/:meth:`known_subjects`/:meth:`dashboard_view`
        already use).

        :returns: the freshly-folded :class:`~babylon.projection.endgame.
            EndgameStatus`. Never ``None`` for a real ``GameSession`` (there
            is always a live detector to fold from — see
            :attr:`_endgame_detector`'s own constructor default) — the
            Protocol's ``EndgameStatus | None`` return accommodates OTHER
            ``CampaignHandle`` implementations/test doubles that choose not
            to wire a live projection at all.
        """
        return fold_endgame_status(
            tick=self.tick,
            pattern=self._endgame_detector.recognized_pattern,
            since_tick=self._endgame_detector.pattern_since_tick,
            defines=self.services.defines,
            axes=self._endgame_detector.axis_progress(),
        )

    def verb_plate_view(self) -> VerbPlateView | None:
        """Project this campaign's live verb-plate (Program 24 P5).

        Computed FRESH on every call via :func:`~babylon.projection.verbs.plate.
        build_verb_plate`, over this session's own live, in-place-mutated
        :attr:`graph` and its stamped ``player_org_id`` (the WayneCountyScenario's
        own EH-ruling-6 pointer — see :attr:`~babylon.models.world_state.
        WorldState.player_org_id` / :meth:`~babylon.models.world_state.
        WorldState.to_graph`'s own player-org-pointer stamp) — the same
        "compute fresh, never cache" contract :meth:`dashboard_view` already
        established. Satisfies ``babylon.tui.contract.CampaignHandle.
        verb_plate_view`` without either module importing the other (the WO-37
        trick :meth:`read_page`/:meth:`known_subjects`/:meth:`dashboard_view`/
        :meth:`endgame_status` already use) — this is the ONE place
        ``build_verb_plate`` is ever called from a live campaign; ``babylon.tui``
        only ever renders the :class:`~babylon.projection.verbs.view_models.
        VerbPlateView` this returns.

        :returns: the freshly-built plate, or ``None`` when this campaign's
            graph carries no ``player_org_id`` (a scenario that never set
            :attr:`~babylon.models.world_state.WorldState.player_org_id`) —
            an honest absence (Constitution III.11), never a fabricated plate
            for an org that does not exist.
        """
        org_id = self.graph.graph.get("player_org_id")
        if not isinstance(org_id, str):
            return None
        return build_verb_plate(self.graph, org_id, tick=self.tick, defines=self.services.defines)

    _OVERLAY_ABSENT = "national overlay ruled (ADR171); Phase-0 incidence artifact not yet built"
    _TENSION_ABSENT = (
        "the tension lens has no norm \u2014 no county bears recoverable v/s data this tick"
    )

    def _choropleth_pairs(
        self, tier: str, lens: str
    ) -> tuple[list[tuple[str, object]] | None, str | None]:
        """``(region_id, wire_value)`` pairs for one tier/lens, plus an
        optional whole-lens absence reason.

        ``(None, None)`` means the graph carries NO county-bearing
        territory at all (the TUTORIAL-CAMPAIGN DISCLOSURE case \u2014 the
        caller renders ``None`` \u2192 the host's ``"null"``). ``([],
        reason)`` means territories exist but the lens has nothing honest
        to say (tension without a norm). ``float("inf")`` crosses the wire
        as the string ``"inf"`` \u2014 JSON has no Infinity, and a serde
        parse failure would be the WRONG loud failure (contract \u00a76
        deviation).
        """
        graph = self.graph
        if lens == "fog":
            horizon = self.services.defines.epistemic_horizon
            fog = county_fog_status if tier == "county" else state_fog_status
            status = fog(
                graph,
                graph.graph.get("player_org_id"),
                IntelLedger(),
                self.tick,
                radius=horizon.organizing_reach_radius,
                staleness_ticks=horizon.intel_staleness_ticks,
                unknown_ticks=horizon.intel_unknown_ticks,
            )
            if not status:
                return None, None
            return sorted(status.items()), None
        if lens == "value":
            value_cells = (
                county_value_cells(graph) if tier == "county" else state_value_cells(graph)
            )
            if value_cells is None:
                return None, None
            return [(c.region_id, _wire_value(c.value)) for c in value_cells], None
        tension_cells = (
            county_tension_cells(graph) if tier == "county" else state_tension_cells(graph)
        )
        if tension_cells is not None:
            return [(c.region_id, c.w) for c in tension_cells], None
        if county_value_cells(graph) is None:
            return None, None
        return [], self._TENSION_ABSENT

    def choropleth_view(self, tier: str, lens: str) -> dict[str, object] | None:
        """Project one map choropleth surface as a hand-built envelope dict
        (M5 Task 37, contract \u00a71 as amended through ADR170/ADR171).

        Computed FRESH on every call over this session's own live graph
        (the :meth:`topology_view` contract verbatim) \u2014 GRAPH-FIRST: the
        TickDynamics stamps are the nationwide medium, the hex-ledger
        views stay a tri-county enrichment path (contract \u00a76). Bands ship
        AS DATA per lens; ``overlay_absent`` carries the ADR171 national-
        overlay absence string until the Phase-0 incidence artifact exists
        (the \u00a79.9 pin-goes-red mechanism); county-tier cells thread the
        injected :data:`CountyWktSource` (``wkt: null`` everywhere when the
        seam is absent \u2014 honest geometry absence, III.11). Satisfies
        ``babylon.tui.contract.CampaignHandle.choropleth_view`` without either
        module importing the other (the WO-37 trick every sibling
        projection method uses).

        :param tier: ``"county"``, ``"state"``, or ``"ea"`` (``ea`` has NO
            producer \u2014 honest ``None``, the client's tier cycle skips it).
        :param lens: ``"value"``, ``"tension"``, or ``"fog"``.
        :raises ValueError: ``tier`` or ``lens`` outside the RULED
            vocabulary \u2014 a caller-protocol error, never absence.
        :returns: the envelope dict in PINNED field order, or ``None`` when
            no county-bearing territory exists (or ``tier="ea"``).
        """
        if tier not in ("county", "state", "ea"):
            raise ValueError(
                f"unknown choropleth tier {tier!r} \u2014 RULED tiers: county, state, ea"
            )
        if lens not in ("value", "tension", "fog"):
            raise ValueError(
                f"unknown choropleth lens {lens!r} \u2014 RULED lenses: value, tension, fog"
            )
        if tier == "ea":
            return None
        pairs, absent_reason = self._choropleth_pairs(tier, lens)
        if pairs is None:
            return None
        wkt_by_fips: dict[str, str] = {}
        if tier == "county" and self._county_wkt is not None and pairs:
            wkt_by_fips = self._county_wkt(frozenset(region for region, _ in pairs))
        bands = {"value": VALUE_BANDS, "tension": TENSION_BANDS, "fog": FOG_BANDS}[lens]
        envelope: dict[str, object] = {
            "tier": tier,
            "lens": lens,
            "verified_tick": self.tick,
            "bands": [list(band) for band in bands],
            "overlay_absent": self._OVERLAY_ABSENT,
        }
        if absent_reason is not None:
            envelope["lens_absent_reason"] = absent_reason
        envelope["cells"] = [
            {
                "region_id": region,
                "value": value,
                "wkt": wkt_by_fips.get(region),
                "centroid": None,
            }
            for region, value in pairs
        ]
        return envelope

    def topology_view(self, kind: str, focus: str | None = None) -> dict[str, object] | None:
        """Project one topology surface as a hand-built envelope dict (Task 30, M4 §1).

        Computed FRESH on every call, over this session's own live,
        in-place-mutated :attr:`graph` — the same "compute fresh, never
        cache" contract :meth:`dashboard_view`/:meth:`subject_view` already
        established. Builds exactly ONE ``WorldState.from_graph(self.graph,
        tick=self.tick)`` per call — never once per community — reused
        across every kind below, including the 14-member fan-out
        :func:`_community_views` does for the three community-derived kinds
        (the contract's own aggregation ruling). Satisfies ``babylon.tui.
        app.CampaignHandle.topology_view`` without either module importing
        the other (the WO-37 trick every sibling projection method already
        uses).

        There is deliberately no shared discriminated-union model across the
        four kinds (the contract's own "hand-built dicts" ruling — an
        ``egotree`` is not a :data:`~babylon.projection.view_models.
        ProjectionRecord` member); each kind below returns its own dict
        literal, in the contract's pinned field order (``json.dumps``
        preserves Python dict insertion order, so the field order here IS
        the wire order — load-bearing for Rust's serde parse).

        :param kind: one of the four RULED kinds — ``"paoh"``, ``"egotree"``,
            ``"incidence"``, ``"adjacency"``.
        :param focus: the ego-tree root id. REQUIRED for ``kind="egotree"``
            (``None`` there is an honest absence, never an error); IGNORED
            for the other three kinds (documented, not an error).
        :raises ValueError: ``kind`` names none of the four RULED kinds — a
            caller-protocol error (Rust only ever sends one of the four),
            never absence.
        :returns: the resolved kind's envelope dict, or ``None`` when:
            ``kind == "egotree"`` and ``focus`` is ``None``; ``focus`` names
            no recognized :class:`~babylon.models.enums.CommunityType`
            member NOR a known entity id (:func:`~babylon.projection.
            topology.levi.levi_ego_tree`'s own ``ValueError``, caught HERE —
            a stale focus after a tick must never propagate and kill the
            client); or ``focus`` is a recognized identity with zero
            bipartite edges (``levi_ego_tree``'s own honest ``None``). All
            three collapse to the SAME ``None`` (Constitution III.11) —
            :meth:`~babylon.tui.host.RustClientHost.topology_json` renders
            every one of them as the literal ``"null"``.
        """
        world = WorldState.from_graph(self.graph, tick=self.tick)

        if kind == "egotree":
            if focus is None:
                return None
            try:
                tree = levi_ego_tree(focus, world=world)
            except ValueError:
                return None
            if tree is None:
                return None
            return {
                "kind": "egotree",
                "verified_tick": self.tick,
                "root_id": tree.root_id,
                "root_side": tree.root_side,
                "children": [
                    {"node_id": child.node_id, "neighbors": list(child.neighbors)}
                    for child in tree.children
                ],
            }

        if kind not in ("paoh", "incidence", "adjacency"):
            msg = f"GameSession.topology_view: unrecognized kind {kind!r}"
            raise ValueError(msg)

        views = _community_views(world, tick=self.tick)

        if kind == "paoh":
            nodes, edges = paoh_ordering(views)
            community_ids = sorted({edge.community_id.value for edge in edges})
            layout = bipartite_shell_layout(nodes, community_ids)
            return {
                "kind": "paoh",
                "verified_tick": self.tick,
                "nodes": list(nodes),
                "edges": [
                    {
                        "community_id": edge.community_id.value,
                        "formation_tick": edge.formation_tick,
                        "members": sorted(edge.members),
                    }
                    for edge in edges
                ],
                # Rounded to 9 decimals at the envelope boundary — the
                # declared reproducibility policy (contract §1): the shell
                # layout uses libm sin/cos, whose last-ulp results are not
                # guaranteed to reproduce across platforms, and these
                # coordinates reach a byte-compared transcript golden.
                "layout": {
                    node_id: [round(x, 9), round(y, 9)] for node_id, (x, y) in layout.items()
                },
            }

        if kind == "incidence":
            incidence = incidence_ordering(views)
            return {
                "kind": "incidence",
                "verified_tick": self.tick,
                "nodes": list(incidence.nodes),
                "hyperedges": [hyperedge.value for hyperedge in incidence.hyperedges],
                "cells": [list(row) for row in incidence.cells],
            }

        adjacency = adjacency_ordering(views)
        return {
            "kind": "adjacency",
            "verified_tick": self.tick,
            "nodes": list(adjacency.nodes),
            "cells": [list(row) for row in adjacency.cells],
        }

    def field_state_view(self) -> FieldStateView:
        """Project this campaign's live field-state dossier (Task 30, M4 §2).

        Calls :func:`~babylon.projection.field_state.project_field_state`
        DIRECTLY on the live post-tick :attr:`graph` — NEVER through
        ``WorldState.from_graph``, which drops every ``tick_``/``flow_``
        node attr and the graph-level ``principal_field``/
        ``dialectical_regime`` attrs the field stack needs (see that
        function's own module docstring — the contract's own §2 ruling).
        Fresh every call, no cache — the same "compute fresh" contract
        :meth:`dashboard_view` already established. Satisfies ``babylon.tui.
        app.CampaignHandle.field_state_view`` without either module
        importing the other (the WO-37 trick).

        :returns: the freshly-projected :class:`~babylon.projection.
            view_models.FieldStateView` for the singleton ``"USA"`` dossier
            (the field stack is national-scale by construction). Never
            ``None`` for a real ``GameSession`` (there is always a live
            graph to project from) — the Protocol's ``FieldStateView | None``
            return accommodates OTHER ``CampaignHandle`` implementations/test
            doubles that choose not to wire a live projection at all.
        """
        return project_field_state("USA", graph=self.graph, tick=self.tick)

    def issue_verb(
        self,
        action_id: str,
        *,
        target_id: str | None = None,
        target_community: str | None = None,
    ) -> int:
        """Issue one player verb through the registry-gated write path (Program 24 P5).

        The FIRST real write the player can make on the world from the Archive
        shell's action bar. Delegates to :func:`~babylon.game.actions.
        player_driver.issue_action` with the registry persona fixed to
        :data:`_PLAYER_AGENT_TYPE` ("organizer"), this campaign's own
        ``player_org_id`` as the acting org, :attr:`_store` as the
        :class:`~babylon.projection.verbs.submit.TurnSink` (:class:`
        GameRuntimeStore` already extends it), and ``tick + 1`` — the SAME
        "queued for the next tick" convention :meth:`submit_verb` already
        uses. ``issue_action`` gates on the registry's ``agent_types``/
        ``status`` BEFORE ever reaching :func:`~babylon.projection.verbs.
        submit.submit_verb`'s own affordability gate: an institutional
        macro-action (``status="STUB"``) or an action outside the organizer's
        registry row is refused loudly here, never silently queued
        (Constitution III.11) — unlike :meth:`submit_verb`, which carries NO
        registry gating at all and must never be substituted for this method
        as the shell's write path.

        :param action_id: one of the nine canonical Article V verbs (a
            :class:`~babylon.projection.verbs.view_models.VerbPlateView`
            row's own ``verb``).
        :param target_id: unit "verb-targeting" (shell-interconnect) — an
            explicit target node id (an honest candidate from
            :meth:`verb_plate_view`'s own :attr:`~babylon.projection.verbs.
            view_models.VerbRow.candidate_target_ids`), threaded verbatim to
            :func:`~babylon.game.actions.player_driver.issue_action` /
            :func:`~babylon.projection.verbs.submit.submit_verb`. ``None``
            (the default, unchanged from before this unit) leaves
            ``submit_verb``'s own self-target fallback
            (:func:`~babylon.projection.verbs.submit.build_player_actions`'s
            ``target_id or org_id``) in effect exactly as before this unit.
        :param target_community: unit "verb-targeting" — passed through
            verbatim for parity with ``issue_action``'s own signature; no
            production caller supplies a real one yet (there is no community
            picker in the shell today) — an honest, unused-but-threaded seam,
            never a fabricated default.
        :raises RuntimeError: this campaign's graph carries no
            ``player_org_id`` (see :meth:`verb_plate_view`'s identical
            absence case) — or, via ``issue_action``'s own
            ``ActionNotPermitted``/``ActionNotLive`` (both ``RuntimeError``
            subclasses, never imported by name into ``babylon.tui`` — the
            WO-37 primitives-only crossing :class:`~babylon.tui.app.
            PacedDriverHandle` already established), the organizer may not
            issue ``action_id``, or it is a STUB with no wired effect yet.
        :raises KeyError: ``action_id`` names no registered action at all.
        :raises ValueError: propagated from :func:`~babylon.projection.verbs.
            submit.submit_verb`'s own gate (a non-canonical verb, or the org
            cannot afford it).
        :returns: the queued ``game_turn`` row's integer id.
        """
        org_id = self.graph.graph.get("player_org_id")
        if not isinstance(org_id, str):
            raise RuntimeError(
                "GameSession.issue_verb: no player_org_id stamped on this campaign's graph"
            )
        return issue_action(
            action_id,
            _PLAYER_AGENT_TYPE,
            org_id,
            self._store,
            session_id=self.session_id,
            tick=self.tick + 1,
            graph=self.graph,
            target_id=target_id,
            target_community=target_community,
        )

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
        hookup the pilot's test-local ``_chronicle_events_from_bus`` stood
        in for. That stand-in is now the PRODUCTION
        :func:`~babylon.game.chronicle_adapter.chronicle_events_from_bus`
        (Unit C4), called here on every tick's real bus history —
        :attr:`TickAdvanceResult.chronicle` is real content, not a seam
        with no caller.

        REMAINING HONEST GAP: the tick's raw events are collected and handed
        to the pause predicate and the Chronicle adapter, but are NOT yet
        written to the ``simulation_event`` table (that table's row shape is
        the older ``SimulationEvent`` pydantic model, not the kernel bus
        ``Event`` — a translation this unit does not invent without a
        verified contract).

        Also keeps the lobby's ``babylon_meta.campaign.last_tick`` live when
        a :class:`ProgressStore` is wired — the review fix for the gap where
        the catalog was written only at campaign creation and never again.

        T5 Unit U1: when a :class:`NarratorScheduler` is wired, schedules
        exactly ONE narration generation for this tick, AFTER the
        deterministic bake (:attr:`_tick_commit_observer`) completes —
        fire-and-forget, never blocking this method and never able to raise
        into it (the side process's own isolation contract). ``narrator=None``
        (the default) means :meth:`~NarratorScheduler.schedule` is never
        called at all — the exact pre-Unit-U1 byte-identical path.

        Unit C6: also stamps :attr:`TickAdvanceResult.autosaved` via
        :func:`~babylon.persistence.delta.is_checkpoint_tick` — the same
        52-tick (one simulated year) cadence the hex-delta pipeline already
        checkpoints on.

        T5 Unit U2: also persists this tick's ``tick_summary`` row (the
        national trend read-model's source table — the ``v_national_trend``
        declared view's ``LAG`` windows read this table) at the SAME commit
        boundary as :meth:`~PostgresRuntime.persist_tick`, via
        :func:`~babylon.projection.tick_summary.build_tick_summary_kwargs`
        over this tick's own ``world``/``graph`` — previously reachable only
        through the legacy web bridge, so a real Archive campaign wrote
        nothing to ``tick_summary`` at all. REVIEW FIX: also threads this
        tick's own ``events`` (the SAME bus history collected above for the
        Chronicle adapter) so ``uprising_count``/``repression_count`` count
        REAL events, not the always-empty ``world.events``
        (``WorldState.from_graph()`` never restamps ``graph.graph['events']``
        per tick — see :func:`build_tick_summary_kwargs`'s own docstring).
        """
        next_tick = self.tick + 1
        pending = self._store.get_pending_turns(self.session_id, next_tick)
        player_actions = build_player_actions(pending)
        context = TickContext(tick=next_tick, persistent_data={"player_actions": player_actions})

        # P26 U2 (W-C motions #1/#2): supply the spec-101 gate inputs the
        # headless runner supplies at runner.py:440-447, so
        # ImperialRentSystem's Φ-distribution (and, when a vol2_step is
        # carried, the Vol II circulation sub-stage) runs interactively.
        # trade=None stamps nothing — the byte-identical pre-U2 path.
        if self._trade is not None:
            context["session_id"] = self.session_id
            context["boundary_flow_register"] = self._trade.boundary_register
            context["external_nodes_phi"] = self._trade.external_nodes_phi
            context["county_exposure_by_external"] = self._trade.county_exposure_by_external
            context["simulated_year"] = self._trade.simulated_year(next_tick)
            if self._trade.vol2_step is not None:
                context["vol2_step"] = self._trade.vol2_step

        bus = self.services.event_bus
        bus.clear_history()
        self.engine.run_tick(self.graph, self.services, context)
        events = tuple(bus.get_history())
        # Unit U5: threads the session's OWN live, post-tick graph so the
        # adapter can resolve event-to-territory anchors (TENANCY edges) —
        # never a WorldState.from_graph() round trip, which drops them.
        chronicle = chronicle_events_from_bus(events, graph=self.graph)

        world = WorldState.from_graph(self.graph, tick=next_tick)
        determinism_hash = _replay_identity_hash(self.session_id, next_tick, self._rng_seed)

        # Program 24 P4: re-evaluate this session's OWN endgame-progress detector for
        # :meth:`endgame_status`'s HUD fold — exactly once per real committed tick, mirroring
        # babylon.game.pacing.PacedTickDriver's own "previous_state is unused by every current
        # axis evaluator" substitution (this tick's own world for BOTH arguments; see
        # EndgameDetector.on_tick's docstring) rather than tracking a second prior-world slot
        # purely to satisfy a parameter nothing reads.
        self._endgame_detector.on_tick(world, world)

        self._store.persist_tick_summary(
            next_tick,
            build_tick_summary_kwargs(world, graph=self.graph, events=events),
            session_id=self.session_id,
        )
        # P26 U2: fold this tick's DRAIN_EDGE rows into the atomic envelope
        # (the register's own once-per-tick flush contract — mirrors
        # bridge.py:505) so the buffer never accumulates across ticks and
        # the rows commit with the tick. trade=None folds the same empty
        # list the envelope already defaulted to.
        boundary_rows = (
            list(self._trade.boundary_register.flush()) if self._trade is not None else []
        )
        # P26 U6: retain this tick's rows for the trade dossiers (the
        # register is now empty — subject_view reads this snapshot).
        self._last_boundary_rows = boundary_rows
        # ADR176 ruling 28 (the torn-tick fix): the adjudicating topology
        # rides the envelope's ONE transaction with the tick_commit marker —
        # the old separate persist_tick call left a crash window where
        # node_state rows existed for a tick whose marker never landed, and
        # latest-hydration resumed from the torn tick (postgres brief §D1).
        self._store.persist_tick_atomic(
            PerTickTransactionEnvelope(
                session_id=self.session_id,
                tick=next_tick,
                determinism_hash=determinism_hash,
                boundary_register_rows=boundary_rows,
            ),
            graph=self.graph,
        )
        self._store.mark_turns_resolved(self.session_id, next_tick)

        if self._tick_commit_observer is not None:
            self._tick_commit_observer.on_tick_committed(
                tick=next_tick, world=world, graph=self.graph
            )
        if self._narrator is not None:
            system, prompt = _narrator_beat(next_tick, chronicle)
            self._narrator.schedule(_NARRATOR_SUBJECT, next_tick, system=system, prompt=prompt)
        if self._progress_store is not None:
            self._progress_store.record_progress(self.session_id, last_tick=next_tick)

        self.tick = next_tick
        paused = self._pause_predicate(events)
        autosaved = is_checkpoint_tick(next_tick)
        return TickAdvanceResult(
            tick=next_tick,
            world=world,
            events=events,
            chronicle=chronicle,
            paused=paused,
            autosaved=autosaved,
            determinism_hash=determinism_hash,
        )


def _wire_value(value: float | None) -> float | str | None:
    """The one wire transform: ``inf`` becomes the string ``"inf"`` (JSON
    has no Infinity; a fabricated big float would lie and a raw ``Infinity``
    token would fail serde loudly for the wrong reason)."""
    import math

    if value is not None and math.isinf(value):
        return "inf"
    return value


def create_new_campaign(
    store: GameRuntimeStore,
    *,
    scenario: Scenario | None = None,
    session_id: UUID | None = None,
    tick_commit_observer: TickCommitObserver | None = None,
    pause_predicate: PausePredicate = default_pause_predicate,
    pages: VaultPageSource | None = None,
    known_subjects: KnownSubjectsSource | None = None,
    progress_store: ProgressStore | None = None,
    narrator: NarratorScheduler | None = None,
    endgame_detector: EndgameProgressObserver | None = None,
    trade: TradeWiring | None = None,
    county_wkt: CountyWktSource | None = None,
    economics_overrides: Mapping[str, Any] | None = None,
) -> GameSession:
    """Boot a brand-new campaign: build the scenario, then bake tick 0.

    :param store: the Postgres runtime (or a structural fake in tests).
    :param scenario: the scenario builder; defaults to
        :class:`~babylon.engine.scenarios.WayneCountyScenario` (ruling 3:
        "Wayne stays in lobby" — the sanctioned lightweight default).
        Scenario-specific ``build()`` kwargs (e.g. Wayne's
        ``extraction_efficiency``) are NOT threaded through here — a stated
        non-goal of this unit, not a silent omission.
    :param session_id: an explicit id for the new ``game_session`` row
        (Unit C2: the lobby's own ``babylon_meta.campaign_id``, so the two
        stores share one identity); ``None`` lets the store mint one, the
        pre-Unit-C2 behavior.
    :param tick_commit_observer: the vault's tick-commit observer; when
        given, tick 0 is baked immediately (WO-44 tick-0 bake-gap parity:
        the player's first-opened dossier must exist before any turn is
        ever submitted).
    :param pause_predicate: the pacing driver's autopause SEAM (see
        :data:`PausePredicate`).
    :param pages: this campaign's :data:`VaultPageSource`, read via
        :meth:`GameSession.read_page` (Unit C2's ``CampaignHandle`` seam).
    :param known_subjects: this campaign's :data:`KnownSubjectsSource`, read
        via :meth:`GameSession.known_subjects` (Unit U1's ``CampaignHandle``
        seam).
    :param progress_store: the lobby's :class:`ProgressStore` seam; when
        given, the freshly-minted campaign's ``last_tick`` is stamped ``0``
        immediately (the lobby row already defaults to 0 at
        ``create_campaign``, so this is a harmless, honest sync rather than
        a required correction).
    :param narrator: this campaign's :class:`NarratorScheduler` seam (T5 Unit
        U1); ``None`` (the default) means the narrator lane is OFF for every
        subsequent :meth:`GameSession.advance_tick`. Tick 0's bake above
        never schedules narration itself — a stated non-goal of this unit
        (there is no chronicle yet at boot; narration begins at tick 1).
    :param endgame_detector: this campaign's :class:`EndgameProgressObserver`
        seam (Program 24 P4); ``None`` (the default) self-constructs a real
        :class:`~babylon.engine.observers.endgame_detector.EndgameDetector`
        over the freshly-built ``defines`` (see :class:`GameSession`'s own
        constructor docstring).
    :param trade: this campaign's :class:`~babylon.game.trade.TradeWiring`
        (P26 U2); when given, ``services.boundary_register`` is assigned
        from it (the runner-twin assignment, ``runner.py:1330``) and every
        :meth:`GameSession.advance_tick` stamps the spec-101 gate inputs.
        ``None`` (the default) is the byte-identical pre-U2 path.
    :param county_wkt: this campaign's :data:`CountyWktSource` (M5 Task
        37) — the county-geometry seam ``GameSession.choropleth_view``
        threads into county-tier cells; ``None`` ships ``wkt: null``
        everywhere (honest absence).
    :param economics_overrides: optional service overrides ``**``-unpacked
        into :meth:`ServiceContainer.create` — the same contract the
        headless runner's ``_build_economics_overrides`` documents — so an
        interactive campaign runs the real gamma/melt/Leontief/Vol I-III
        stack instead of the zero-stub defaults. ``None`` keeps today's
        default container.
    :returns: a fresh :class:`GameSession` at tick 0.
    """
    chosen: Scenario = scenario if scenario is not None else WayneCountyScenario()
    world0, sim_config, defines = chosen.build()

    created_session_id = store.create_session(
        scenario=chosen.name,
        config_json=sim_config.model_dump(mode="json"),
        game_defines_json=defines.model_dump(mode="json"),
        rng_seed=sim_config.rng_seed,
        session_id=session_id,
    )

    graph = world0.to_graph()
    services = ServiceContainer.create(
        config=sim_config, defines=defines, **dict(economics_overrides or {})
    )
    if trade is not None:
        # Runner twin (runner.py:1330): engine systems that publish boundary
        # flows must see the SAME buffer advance_tick stamps into context.
        services.boundary_register = trade.boundary_register
    engine = SimulationEngine(list(_DEFAULT_SYSTEMS))

    tick0_hash = _replay_identity_hash(created_session_id, 0, sim_config.rng_seed)
    # Tick-0 topology rides the envelope transaction with its marker —
    # same torn-tick closure as advance_tick (ADR176 ruling 28).
    store.persist_tick_atomic(
        PerTickTransactionEnvelope(
            session_id=created_session_id, tick=0, determinism_hash=tick0_hash
        ),
        graph=graph,
    )
    if tick_commit_observer is not None:
        # Uses world0 (not a from_graph round-trip) at tick 0 — mirrors the
        # headless runner's own tick-0 bake exactly (runner.py ~1616-1621):
        # the graph round-trip loses computed fields the freshly-built
        # WorldState still carries.
        tick_commit_observer.on_tick_committed(tick=0, world=world0, graph=graph)
    if progress_store is not None:
        progress_store.record_progress(created_session_id, last_tick=0)

    return GameSession(
        session_id=created_session_id,
        graph=graph,
        services=services,
        engine=engine,
        store=store,
        rng_seed=sim_config.rng_seed,
        tick=0,
        scenario_name=chosen.name,
        tick_commit_observer=tick_commit_observer,
        pause_predicate=pause_predicate,
        pages=pages,
        known_subjects=known_subjects,
        progress_store=progress_store,
        narrator=narrator,
        endgame_detector=endgame_detector,
        trade=trade,
        county_wkt=county_wkt,
    )


def resume_campaign(
    store: GameRuntimeStore,
    session_id: UUID,
    *,
    tick_commit_observer: TickCommitObserver | None = None,
    pause_predicate: PausePredicate = default_pause_predicate,
    pages: VaultPageSource | None = None,
    known_subjects: KnownSubjectsSource | None = None,
    progress_store: ProgressStore | None = None,
    narrator: NarratorScheduler | None = None,
    endgame_detector: EndgameProgressObserver | None = None,
    trade: TradeWiring | None = None,
    county_wkt: CountyWktSource | None = None,
    economics_overrides: Mapping[str, Any] | None = None,
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
    :param pages: this campaign's :data:`VaultPageSource` (see
        :func:`create_new_campaign`'s identical parameter).
    :param known_subjects: this campaign's :data:`KnownSubjectsSource` (see
        :func:`create_new_campaign`'s identical parameter).
    :param progress_store: the lobby's :class:`ProgressStore` seam; when
        given, the lobby row is synced to the Ledger's own
        ``last_committed_tick`` right here — the fix for a campaign whose
        catalog row drifted (or never moved past its creation-time ``0``)
        while the Ledger kept advancing.
    :param narrator: this campaign's :class:`NarratorScheduler` seam (see
        :func:`create_new_campaign`'s identical parameter, T5 Unit U1).
    :param endgame_detector: this campaign's :class:`EndgameProgressObserver`
        seam (see :func:`create_new_campaign`'s identical parameter, Program
        24 P4) — ``None`` (the default) self-constructs a fresh
        :class:`~babylon.engine.observers.endgame_detector.EndgameDetector`
        over the resumed ``defines``, so a resumed campaign's axis-progress
        counters (habitability window, consecutive-tick streaks) start from
        zero rather than replaying every prior tick — an honest, documented
        approximation (the same shape :func:`resume_campaign` already
        accepts for reconstructing state via ``hydrate_graph`` rather than a
        full replay), never a fabricated carried-over reading.
    :param trade: this campaign's :class:`~babylon.game.trade.TradeWiring`
        (P26 U2 — see :func:`create_new_campaign`'s identical parameter). A
        resumed campaign dropped trade silently before this parameter
        existed — the same defect class U2 fixes at creation.
    :param economics_overrides: optional service overrides (see
        :func:`create_new_campaign`'s identical parameter).
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
    services = ServiceContainer.create(
        config=sim_config, defines=defines, **dict(economics_overrides or {})
    )
    if trade is not None:
        services.boundary_register = trade.boundary_register
    engine = SimulationEngine(list(_DEFAULT_SYSTEMS))

    if progress_store is not None:
        progress_store.record_progress(session_id, last_tick=last_tick)

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
        pages=pages,
        known_subjects=known_subjects,
        progress_store=progress_store,
        narrator=narrator,
        endgame_detector=endgame_detector,
        trade=trade,
        county_wkt=county_wkt,
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
    """Open a real :class:`PostgresRuntime` from the environment DSN.

    :param dsn: an explicit DSN; otherwise resolved via
        :func:`babylon.config.dsn.resolve_dsn` — the canonical ``BABYLON_DSN``
        first, then the deprecated ``BABYLON_PG_DSN`` /
        ``BABYLON_TEST_PG_DSN`` (the same precedence chain
        ``headless_runner.runner._open_postgres_pool`` and ``babylon doctor``
        use, so "doctor says reachable" and "the game boots" never diverge).
    :raises RuntimeError: if no DSN is available anywhere — a loud refusal
        (Constitution III.11), never a silent demo fallback.
    """
    from psycopg_pool import ConnectionPool

    from babylon.config.dsn import resolve_dsn
    from babylon.persistence import PostgresRuntime

    resolved = dsn or resolve_dsn(legacy_env=("BABYLON_PG_DSN", "BABYLON_TEST_PG_DSN"))
    if not resolved:
        raise RuntimeError(
            "No Postgres DSN: set BABYLON_DSN (or the deprecated BABYLON_PG_DSN / "
            "BABYLON_TEST_PG_DSN), or pass dsn= explicitly."
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


#: Repo loop-bound rule (CLAUDE.md Power-of-10 #2): the nationwide worst case
#: is ~3,300 baked pages (``commit_pages``'s own "~3,156 pages per tick"
#: figure, plus briefing/narrative pages); this cap sits generously above
#: that, so slicing ``all_pages[:_MAX_VAULT_PAGES]`` below is a trivially
#: bounded loop, not a runtime-dependent walk of the vault's actual size.
_MAX_VAULT_PAGES: Final = 100_000


def vault_known_subjects(vault_root: Path) -> KnownSubjectsSource:
    """A reader enumerating every subject id a vault has baked (Unit U1).

    Walks ``vault_root`` for the exact ``<subject>.md`` files
    :class:`~babylon.projection.vault.tick_baker.ArchiveTickBaker` writes —
    the same convention :func:`vault_page_source` reads in reverse: a
    subject id is a baked file's vault-relative POSIX path, minus the
    ``.md`` suffix. Excludes the vault's own ``.git/`` directory (never a
    page) and a top-level ``narrative/`` subtree if present (the WO-42
    narrator prose cache — attributed blocks a dossier page's
    ``{narrative}`` fence pulls IN, never standalone navigable subjects in
    their own right).

    :param vault_root: the campaign's vault repository root.
    :returns: a zero-arg callable producing the CURRENT known-subject
        frozenset (:data:`KnownSubjectsSource`), read fresh on every call —
        pages bake as ticks advance, so this is deliberately never cached.
    """

    def _known_subjects() -> frozenset[str]:
        if not vault_root.is_dir():
            return frozenset()
        all_pages = sorted(vault_root.rglob("*.md"))
        if len(all_pages) > _MAX_VAULT_PAGES:
            # Loud refusal (Constitution III.11), never a silent truncation
            # of the known-subject set.
            raise RuntimeError(
                f"vault at {vault_root} has grown past the "
                f"{_MAX_VAULT_PAGES}-page static scan bound"
            )
        subjects: set[str] = set()
        for page_path in all_pages[:_MAX_VAULT_PAGES]:
            relative = page_path.relative_to(vault_root)
            if ".git" in relative.parts or relative.parts[0] == "narrative":
                continue
            subjects.add(relative.with_suffix("").as_posix())
        return frozenset(subjects)

    return _known_subjects
