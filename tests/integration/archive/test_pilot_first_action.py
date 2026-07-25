"""WO-50 Pilot e2e — the first-session spine ported onto the Archive seams.

This is the acceptance evidence that a fresh player's first session works
end-to-end in the ARCHIVE stack (engine + projection + TUI pure logic), the
Program-24 cutover gate #2. It ports the *behavioral spine* of the legacy web
trunk e2e ``src/frontend/e2e/first-session.spec.ts`` (483 lines) — every
Playwright assertion re-expressed as an observable of a real Archive seam.
The web client is legacy and is never imported here; each browser leg maps to
a pure engine/projection/TUI contract instead (row-by-row map in
``specs/24-archive/test-port-ledger.md``, WO-50 section).

The order a real first session hits the seams, and where each lands below:

* lobby codenames ..... ``test_lobby_every_catalog_row_carries_a_derived_codename``
* scenario briefing ... ``test_briefing_five_patterns_win_condition_and_century_horizon``
* verb plate .......... ``test_verb_preview_precedes_submit_then_the_engine_adjudicates``
                        + ``test_unaffordable_verb_is_refused_before_the_engine``
* forced first crisis . ``test_forced_endgame_crisis_autopauses_amber_then_ack_clears``
* event dedup / floors  ``test_event_dedup_and_volume_floors_over_real_tick_events``
* objectives honesty .. ``test_objective_progress_after_two_real_ticks_never_pinned``
* epilogue (horizon) .. ``test_rigged_horizon_crosses_into_the_unresolved_epilogue``
* terminal-state ...... ``test_terminal_epilogue_is_stable_across_a_further_tick``

Real engine ticks run in-process through the FULL 30-system default pipeline
(``WorldState.to_graph() -> SimulationEngine.run_tick() -> from_graph()``,
``ServiceContainer.create()``, no Postgres) — the same harness
``tests/integration/web/test_static_economy_flow.py`` uses. The verb leg reuses
``test_verb_resolution.py``'s proven OODA harness verbatim; the lobby leg uses a
real ``BabylonMetaStore`` over the ``pg_pool`` fixture.

HONEST GAPS recorded here (each a code comment at its site + a report row —
never a fabricated assertion):

* **Engine->Chronicle feed IS shipped (Unit T4-core/C4).** ``babylon.tui.
  chronicle`` itself still renders a plain fixture list ("no engine" — that
  module's own concern is rendering, not sourcing). The event-dedup leg below
  reshapes REAL bus events into ``ChronicleEvent`` via the PRODUCTION adapter
  :func:`~babylon.game.chronicle_adapter.chronicle_events_from_bus`
  (``babylon.game.chronicle_adapter`` — promoted from what used to be this
  test's own test-local stand-in, per the program plan's Part 2 spine D): the
  events are real, the summaries are real (per-``EventType``, generated from
  the payload — see that module's docstring), and the dedup/floor logic
  exercised is the real production code too.
* **Narrative-cap floor is vacuous on the in-process minimal scenario.** That
  scenario emits only warning-tier events (``lifecycle_transition`` +
  ``organizational_action``); the informational-tier per-tick cap holds but caps
  nothing. The ORGANIZATIONAL_ACTION aggregation floor IS exercised live. A
  future WO wiring the headless wayne run into the Chronicle feed would exercise
  the informational cap against real informational events.
* **``endgame_reached`` is critical but NOT the sole critical tier.** The web
  frontend re-tiered critical to endgame-only (FR-116-2); T1.1's derived
  ``SEVERITY_BY_EVENT`` (``babylon.models.event_severity``) keeps a broad
  critical tier (22 of 47 classified types — a CROSSING is binary
  critical-or-informational under the pure kind x terminal_proximity rule).
  The crisis leg asserts endgame_reached is critical and drives autopause, and
  documents that it is not uniquely so in the Archive.
* **The pure endgame fold is memoryless.** ``endgame_status`` recomputes every
  tick; the web's "first ENDGAME_REACHED row is authoritative" immutability
  (``ORDER BY tick ASC LIMIT 1``) is a persistence guarantee absent from the
  pure projection. The terminal-state leg asserts the outcome is stable across a
  further tick *because the material state never crosses into a pattern*, and
  documents that a future WO must persist the first endgame event to lock the
  outcome against a LATER pattern recognition.
* **No shipped autopause-acknowledgement state machine.** ``chronicle_salience``
  deliberately omits the once-per-key ack layer (WO-46 ``babylon_meta``). The
  crisis leg models acknowledgement as the pilot loop dropping the acknowledged
  critical event from the surfaced slice, over which ``compute_autopause_state``
  (stateless) then reads inactive.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, NamedTuple
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from babylon.config.defines import GameDefines
from babylon.config.defines.endgame import EndgameDefines
from babylon.config.defines.tunables import TimescaleDefines
from babylon.engine.context import TickContext
from babylon.engine.factories import create_bourgeoisie, create_proletariat
from babylon.engine.observers.endgame_detector import EndgameDetector
from babylon.engine.services import ServiceContainer
from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS, SimulationEngine
from babylon.engine.systems.ooda import OODASystem
from babylon.game.chronicle_adapter import chronicle_events_from_bus
from babylon.kernel.event_bus import Event
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import SocialClass
from babylon.models.entities.territory import Territory
from babylon.models.enums import EdgeType, OperationalProfile, OrgType, SectorType
from babylon.models.enums.events import EventType, GameOutcome
from babylon.models.enums.topology import NodeType
from babylon.models.event_severity import SEVERITY_BY_EVENT
from babylon.models.world_state import WorldState
from babylon.persistence.babylon_meta import BabylonMetaStore
from babylon.projection.briefing import (
    WIN_OBJECTIVE_ID,
    journal_objectives,
    operation_codename,
    project_briefing,
)
from babylon.projection.endgame import campaign_horizon_tick, endgame_status
from babylon.projection.vault.epilogues import EPILOGUES
from babylon.projection.vault.render_briefing import render_briefing
from babylon.projection.vault.render_epilogue import render_epilogue
from babylon.projection.verbs.preview import preview_verb
from babylon.projection.verbs.submit import build_player_actions, submit_verb
from babylon.topology import BabylonGraph
from babylon.tui.campaign_menu import CampaignMenu
from babylon.tui.chronicle import ChronicleEvent
from babylon.tui.chronicle_salience import (
    apply_volume_floors,
    classify_event_salience,
    compute_autopause_state,
    dedup_key,
    dedupe_consecutive,
    render_autopause_indicator,
)
from babylon.tui.theme import AMBER

if TYPE_CHECKING:  # pragma: no cover - typing only
    from psycopg_pool import ConnectionPool

pytestmark = [pytest.mark.integration]

_WAYNE_FIPS = "26163"
_N_TERRITORIES = 4
#: Two-uppercase-word codename shape (``LOBBY-ROUTE.tsx``'s parity: never blank).
_CODENAME_RE = re.compile(r"^[A-Z]+ [A-Z]+$")
#: Fixed session UUID so the briefing leg's codename is deterministic.
_BRIEFING_SESSION = UUID("00000000-0000-0000-0000-000000000050")


# --------------------------------------------------------------------------- #
# Real in-process full-engine harness (no Postgres) — the "resolve a tick"     #
# spine legs 5-8 ride, mirroring test_static_economy_flow.py's usage.          #
# --------------------------------------------------------------------------- #


class _Harness(NamedTuple):
    """One live engine session: a persistent graph + services + detector."""

    graph: BabylonGraph
    services: ServiceContainer
    engine: SimulationEngine
    detector: EndgameDetector


def _multi_territory_state(n: int) -> WorldState:
    """A deterministic worker+owner+territory world across ``n`` districts.

    Richer than the OODA-minimal fixture so a real tick emits several events
    (one ``lifecycle_transition`` per territory + one ``organizational_action``)
    — enough to exercise dedup over real distinct-subject cards.
    """
    entities: dict[str, SocialClass] = {}
    territories: dict[str, Territory] = {}
    relationships: list[Relationship] = []
    for i in range(n):  # loop bound: n (fixed, <= 10 for the id patterns)
        worker_id, owner_id, terr_id = f"C{i}00", f"C{i}01", f"T{i:03d}"
        entities[worker_id] = create_proletariat(id=worker_id, county_fips=_WAYNE_FIPS)
        entities[owner_id] = create_bourgeoisie(id=owner_id, county_fips=_WAYNE_FIPS)
        territories[terr_id] = Territory(
            id=terr_id,
            name=f"district {i}",
            sector_type=SectorType.INDUSTRIAL,
            profile=OperationalProfile.LOW_PROFILE,
            biocapacity=500.0,
            county_fips=_WAYNE_FIPS,
        )
        relationships.append(
            Relationship(
                source_id=worker_id,
                target_id=owner_id,
                edge_type=EdgeType.EXPLOITATION,
                value_flow=5.0,
                tension=0.4,
            )
        )
        relationships.append(
            Relationship(source_id=worker_id, target_id=terr_id, edge_type=EdgeType.TENANCY)
        )
    return WorldState(
        tick=0, entities=entities, territories=territories, relationships=relationships
    )


def _fresh_engine() -> tuple[_Harness, WorldState]:
    """Build a fresh live session at tick 0 and return it with the tick-0 world."""
    world0 = _multi_territory_state(_N_TERRITORIES)
    graph = world0.to_graph()
    services = ServiceContainer.create()
    engine = SimulationEngine(list(_DEFAULT_SYSTEMS))
    detector = EndgameDetector()
    return _Harness(graph, services, engine, detector), world0


def _advance_tick(
    harness: _Harness, prev_world: WorldState, tick: int
) -> tuple[list[Event], WorldState]:
    """Resolve exactly one real tick; return that tick's bus events + new world.

    The EndgameDetector observes the post-tick state (the same recognizer the
    headless runner threads through ``bridge.poll_endgame``).
    """
    bus = harness.services.event_bus
    bus.clear_history()
    harness.engine.run_tick(harness.graph, harness.services, TickContext(tick=tick))
    raw_events = bus.get_history()
    new_world = WorldState.from_graph(harness.graph, tick)
    harness.detector.on_tick(prev_world, new_world)
    return raw_events, new_world


def _pilot_can_step(active: bool) -> bool:
    """The pilot loop's own Step gate: no stepping while autopause is active.

    Ports ``TimeControls.tsx``'s ``disabled={!isPaused}`` — the CLIENT gate is
    what is terminal (the engine has no refusal gate; see the terminal-state
    leg). ``active`` is ``compute_autopause_state(...).active``.
    """
    return not active


# --------------------------------------------------------------------------- #
# Leg 1 — lobby: every catalog row carries a real derived codename.            #
# (first-session.spec.ts:100-116)                                              #
# --------------------------------------------------------------------------- #


def test_lobby_every_catalog_row_carries_a_derived_codename(pg_pool: ConnectionPool) -> None:
    """No unnamed lobby rows: every row's codename is the real derived name.

    Ports the web lobby's "no blank/undefined codename" contract against a real
    ``BabylonMetaStore`` (satisfies the ``CampaignCatalog`` seam structurally),
    read through the real ``CampaignMenu`` the TUI lobby uses.
    """
    store = BabylonMetaStore(pg_pool)
    store.ensure_schema()

    minted: list[UUID] = []
    try:
        for _ in range(3):  # loop bound: 3
            record = store.create_campaign(
                slug=f"wo50-pilot-{uuid4().hex[:12]}",
                engine_version="0.24.0",
                defines_hash="wo50-pilot",
            )
            minted.append(record.campaign_id)

        menu = CampaignMenu(store, engine_version="0.24.0", defines_hash="wo50-pilot")
        rows = menu.rows()

        # The invariant the web pinned over EVERY lobby row.
        assert rows, "the lobby lists the minted campaigns"
        for row in rows:  # loop bound: len(rows)
            assert row.codename, "a lobby row must carry a real codename, not blank"
            assert _CODENAME_RE.match(row.codename), row.codename
            # The codename is DERIVED from the campaign UUID, never stored.
            assert row.codename == operation_codename(row.campaign_id)

        # And every campaign we minted appears with its derived codename.
        by_id = {row.campaign_id: row for row in rows}
        for campaign_id in minted:  # loop bound: len(minted)
            assert campaign_id in by_id
            assert by_id[campaign_id].codename == operation_codename(campaign_id)
    finally:
        for campaign_id in minted:  # loop bound: len(minted)
            store.delete_campaign(campaign_id)


# --------------------------------------------------------------------------- #
# Leg 2 — scenario briefing: five patterns, win condition, century horizon,    #
# honest zero progress on a fresh campaign. (first-session.spec.ts:118-158)    #
# --------------------------------------------------------------------------- #


def test_briefing_five_patterns_win_condition_and_century_horizon() -> None:
    """The briefing projects exactly five patterns, names the win condition, and
    frames a fixed century horizon — none of it fabricated when no tick has run.
    """
    view = project_briefing(_BRIEFING_SESSION, tick=0, defines=GameDefines())

    # Exactly five recognized patterns (the fixed EndgameDetector axis count).
    assert len(view.objectives) == 5
    assert {obj.id for obj in view.objectives} == {
        "revolution",
        "ecological_collapse",
        "fascist_consolidation",
        "red_ogv",
        "fragmented_collapse",
    }

    # The win condition is named.
    assert view.win_objective_id == WIN_OBJECTIVE_ID == "revolution"
    win = next(obj for obj in view.objectives if obj.is_win_condition)
    assert win.id == "revolution"
    assert win.title == "Revolutionary Victory"
    assert sum(1 for obj in view.objectives if obj.is_win_condition) == 1

    # Fixed-horizon framing: a century, not a termination condition.
    assert view.horizon_years == 100
    assert view.horizon_ticks == campaign_horizon_tick(GameDefines()) == 5200
    page = render_briefing(view)
    assert "100 years" in page
    assert "Five Ways the Century Can Land" in page

    # Honest absence (Constitution III.11): a fresh campaign's five progress
    # readings are genuinely 0.0 (no endgame_progress yet), all "active" — never
    # a fabricated non-zero default.
    for obj in view.objectives:  # loop bound: 5
        assert obj.progress == 0.0
        assert obj.status == "active"


# --------------------------------------------------------------------------- #
# Leg 3 — verb plate: preview (probability + cost) precedes submit; a submitted #
# verb reaches turn resolution through the real engine; an unaffordable verb is #
# refused at the queue door. (first-session.spec.ts:223-259; ports             #
# test_verb_resolution.py's proof into the pilot spine.)                        #
# --------------------------------------------------------------------------- #

_ORG = "rev_workers"
_COMMUNITY = "comm_detroit"


class _TurnJournal:
    """Structural ``TurnSink`` that plays the game_turn table in-memory."""

    def __init__(self) -> None:
        self.rows: list[dict[str, object]] = []

    def submit_turn(
        self,
        session_id: UUID,
        tick: int,
        org_id: str,
        verb: str,
        *,
        action_type: str | None = None,
        target_id: str | None = None,
        target_community: str | None = None,
        params_json: dict[str, object] | None = None,
    ) -> int:
        self.rows.append(
            {
                "session_id": session_id,
                "tick": tick,
                "org_id": org_id,
                "verb": verb,
                "action_type": action_type,
                "target_id": target_id,
                "target_community": target_community,
                "params_json": params_json,
            }
        )
        return len(self.rows)


def _verb_graph() -> BabylonGraph:
    """One player faction with a community in reach (OODA-minimal shape)."""
    graph = BabylonGraph()
    graph.add_node(
        _ORG,
        NodeType.ORGANIZATION,
        id=_ORG,
        org_type=OrgType.POLITICAL_FACTION.value,
        territory_ids=["detroit"],
        consciousness_tendency="revolutionary",
        cadre_level=0.6,
        cohesion=0.6,
        budget=50.0,
        heat=0.1,
    )
    graph.add_node(
        _COMMUNITY,
        NodeType.COMMUNITY,
        id=_COMMUNITY,
        collective_identity=0.3,
        ideological_contestation=0.2,
        heat=0.0,
        infrastructure=0.5,
    )
    graph.add_node("detroit", NodeType.TERRITORY)
    return graph


def _verb_services() -> MagicMock:
    services = MagicMock()
    services.defines = GameDefines()
    services.event_bus = MagicMock()
    return services


def test_verb_preview_precedes_submit_then_the_engine_adjudicates() -> None:
    """Preview (probability + AP cost) is available BEFORE submit; the submitted
    verb resolves under our org through the real OODASystem.

    The web trunk submits Campaign; in the OODA-minimal fixture that
    ``test_verb_resolution.py`` proves end-to-end, EDUCATE is the resource-
    affordable eligible consciousness verb, so it carries the spine here (both
    are ``_CONSCIOUSNESS_VERBS``; the preview surface and write-side chain are
    identical). A submit-then-resolve on Campaign is blocked only by
    sympathizer-labor affordability in that minimal fixture, not by the plate.
    """
    graph = _verb_graph()

    # Preview is a pure read-only estimate available with no write.
    preview = preview_verb(graph, _ORG, "educate", target_id=_COMMUNITY)
    assert 0.0 <= preview.success_probability <= 1.0
    assert preview.action_point_cost == 1.0

    journal = _TurnJournal()
    submit_verb(
        journal,
        session_id=uuid4(),
        tick=1,
        org_id=_ORG,
        verb="educate",
        graph=graph,
        target_id=_COMMUNITY,
    )
    assert len(journal.rows) == 1

    player_actions = build_player_actions(journal.rows)
    context = TickContext(tick=1, persistent_data={"player_actions": player_actions})
    OODASystem().step(graph, _verb_services(), context)

    resolution = context.persistent_data["turn_resolution"]
    ours = [r for r in resolution["action_phase_results"] if r["action"]["org_id"] == _ORG]
    assert ours, "the queued player action must resolve in the action phase"
    assert any(r["action"]["action_type"] == "educate" for r in ours)


def test_unaffordable_verb_is_refused_before_the_engine() -> None:
    """An unaffordable verb is refused at the queue door — the engine never sees
    it, and the plate's afford note matches the rejection copy.
    """
    graph = _verb_graph()
    graph.update_node(_ORG, budget=0.0, cadre_level=0.0, cohesion=0.0)
    journal = _TurnJournal()

    with pytest.raises(ValueError, match="Cannot afford"):
        submit_verb(
            journal,
            session_id=uuid4(),
            tick=1,
            org_id=_ORG,
            verb="educate",
            graph=graph,
            target_id=_COMMUNITY,
        )

    assert journal.rows == []
    assert build_player_actions(journal.rows) == {}


# --------------------------------------------------------------------------- #
# Leg 4 — forced first crisis: the endgame_reached critical event autopauses    #
# (AMBER), gates the pilot's Step, and clears on acknowledgement.               #
# (first-session.spec.ts:261-304)                                              #
# --------------------------------------------------------------------------- #


def test_forced_endgame_crisis_autopauses_amber_then_ack_clears() -> None:
    """A forced ``endgame_reached`` event drives autopause with the AMBER token,
    disables the pilot's Step, and is cleared by acknowledgement.
    """
    # endgame_reached IS a critical-tier type (the autopause trigger).
    assert classify_event_salience(EventType.ENDGAME_REACHED).tier == "critical"
    # DEVIATION from the web's FR-116-2 re-tier: T1.1's derived SEVERITY_BY_EVENT
    # keeps a broad critical tier, so endgame_reached is critical but NOT the sole
    # critical type. Documented, not asserted as unique.
    assert sum(1 for tier in SEVERITY_BY_EVENT.values() if tier == "critical") > 1

    crisis = ChronicleEvent(
        tick=1,
        event_type=EventType.ENDGAME_REACHED,
        summary="The century closes — the contradiction did not resolve.",
        data={"outcome": GameOutcome.UNRESOLVED.value},
    )

    # Acceptance gate 3, HARD-asserted: the critical event autopauses (AMBER).
    paused = compute_autopause_state([crisis])
    assert paused.active is True
    assert paused.token == AMBER
    indicator = render_autopause_indicator(paused)
    assert indicator is not None  # the takeover line renders, not a muted blank

    # "Step disabled once AUTOPAUSED": the pilot loop's own gate refuses to step.
    assert _pilot_can_step(paused.active) is False

    # Acknowledgement clears it. HONEST GAP: chronicle_salience ships no
    # once-per-key ack state machine (that is WO-46 babylon_meta). The pilot
    # models ack as dropping the acknowledged critical event from the surfaced
    # slice; the stateless recompute then reads inactive and the Step re-enables.
    acknowledged_view: list[ChronicleEvent] = [
        ev for ev in [crisis] if dedup_key(ev) != dedup_key(crisis)
    ]
    resumed = compute_autopause_state(acknowledged_view)
    assert resumed.active is False
    assert render_autopause_indicator(resumed) is None
    assert _pilot_can_step(resumed.active) is True


# --------------------------------------------------------------------------- #
# Leg 5 — event dedup + volume floors exercised against REAL tick events.       #
# (first-session.spec.ts:319-350)                                              #
# --------------------------------------------------------------------------- #


def test_event_dedup_and_volume_floors_over_real_tick_events() -> None:
    """No two consecutive kept cards share a ``{type}:{subject}`` dedup key, and
    the volume floors hold — over REAL events from a real engine tick.
    """
    harness, world0 = _fresh_engine()
    raw_tick1, world1 = _advance_tick(harness, world0, tick=1)
    cards = chronicle_events_from_bus(raw_tick1)
    assert cards, "the real tick emitted event cards to render"

    # Acceptance gate 2: after consecutive-run dedup, no two adjacent kept cards
    # share a dedup key. The real tick emits distinct-subject lifecycle cards
    # (one per territory) + one org card, so the invariant holds non-trivially
    # across several real distinct-subject cards.
    deduped = dedupe_consecutive(cards)
    assert deduped, "dedup keeps at least one real card"
    for i in range(1, len(deduped)):  # loop bound: len(deduped)
        assert dedup_key(deduped[i]) != dedup_key(deduped[i - 1])

    # Dedup collapses a GENUINE consecutive repeat: one territory's
    # lifecycle_transition across two ticks carries the SAME tick-independent key
    # (dedup_key is tick-independent by design — "the same thing still
    # happening"). Rendering that one territory's two-tick timeline collapses to
    # one card.
    raw_tick2, _ = _advance_tick(harness, world1, tick=2)
    both = chronicle_events_from_bus(raw_tick1) + chronicle_events_from_bus(raw_tick2)
    t000_timeline = tuple(ev for ev in both if ev.data.get("territory_id") == "T000")
    assert len(t000_timeline) == 2, "T000 fired a lifecycle card on each of two ticks"
    assert len({dedup_key(ev) for ev in t000_timeline}) == 1
    assert len(dedupe_consecutive(t000_timeline)) == 1

    # Volume floors hold over the real stream. ORGANIZATIONAL_ACTION aggregation
    # is exercised LIVE (one real org card per tick -> one rollup card carrying
    # its count).
    floored = apply_volume_floors(cards)
    org_cards = [ev for ev in floored if ev.event_type is EventType.ORGANIZATIONAL_ACTION]
    assert len(org_cards) == 1
    assert org_cards[0].data["count"] == 1
    assert "organizational action" in org_cards[0].summary

    # Informational-tier per-tick cap invariant holds. HONEST GAP: this minimal
    # in-process scenario emits only warning-tier events, so the narrative cap
    # caps nothing here (it holds vacuously). The cap mechanism is unit-covered
    # in tests/unit/tui/test_chronicle_salience.py; a future WO wiring the
    # headless wayne run into the Chronicle would exercise it against real
    # informational events.
    informational = [
        ev for ev in floored if classify_event_salience(ev.event_type).tier == "informational"
    ]
    assert len(informational) <= 1


# --------------------------------------------------------------------------- #
# Leg 6 — objectives honesty: after two real ticks the five progress readings   #
# exist and none is pinned at 1.00. (first-session.spec.ts:352-362)            #
# --------------------------------------------------------------------------- #


def test_objective_progress_after_two_real_ticks_never_pinned() -> None:
    """Five real objective readings after two real ticks, none fabricated at 1.00.

    The axes are the REAL EndgameDetector's ``axis_progress()`` after two real
    ticks; the objectives are the real ``journal_objectives`` fold over them.
    """
    harness, world0 = _fresh_engine()
    _, world1 = _advance_tick(harness, world0, tick=1)
    _advance_tick(harness, world1, tick=2)

    axes = harness.detector.axis_progress()
    objectives = journal_objectives(axes=axes, outcome=harness.detector.recognized_pattern)

    assert len(objectives) == 5
    for objective in objectives:  # loop bound: 5
        # A real reading in [0, 1] — never pinned at a fabricated 1.00 two ticks
        # in (the century has barely begun).
        assert 0.0 <= objective.progress < 1.0


# --------------------------------------------------------------------------- #
# Leg 7 — rigged horizon: one real tick crosses a horizon_tick==1 campaign into #
# the genuine UNRESOLVED epilogue. (first-session.spec.ts:365-439)             #
# --------------------------------------------------------------------------- #


def _rigged_horizon_defines() -> GameDefines:
    """GameDefines whose campaign horizon is exactly tick 1.

    ``horizon_tick = campaign_horizon_years * weeks_per_year`` (the web spec's
    ``campaign_horizon_years: 1, weeks_per_year: 1`` rig), so the very first
    resolved tick crosses the fixed-horizon gate for real.
    """
    return GameDefines(
        endgame=EndgameDefines(campaign_horizon_years=1),
        timescale=TimescaleDefines(weeks_per_year=1),
    )


def test_rigged_horizon_crosses_into_the_unresolved_epilogue() -> None:
    """One real tick on a horizon_tick==1 campaign resolves to the genuine
    UNRESOLVED epilogue — its body byte-identical to the epilogues constant.
    """
    rigged = _rigged_horizon_defines()
    assert campaign_horizon_tick(rigged) == 1

    harness, world0 = _fresh_engine()
    _advance_tick(harness, world0, tick=1)

    # The REAL detector recognizes no pattern at tick 1 (no pattern before the
    # calibrated recognition window) — the honest input to the fold.
    assert harness.detector.recognized_pattern is None

    status = endgame_status(
        tick=1,
        pattern=harness.detector.recognized_pattern,
        since_tick=harness.detector.pattern_since_tick,
        defines=rigged,
        axes=harness.detector.axis_progress(),
    )
    # A genuine horizon crossing: the fixed gate fired, and with no pattern held
    # the outcome is UNRESOLVED (owner ruling 2026-07-17: horizon, not verdict).
    assert status.game_over is True
    assert status.outcome is GameOutcome.UNRESOLVED

    # Sanity: an UNRIGGED campaign does NOT cross at tick 1 — the rig is what
    # crosses it, not a fluke of the tick.
    assert (
        endgame_status(
            tick=1, pattern=None, since_tick=None, defines=GameDefines(), axes={}
        ).game_over
        is False
    )

    # The selected epilogue IS the genuine "unresolved" entry — body byte-equal
    # to projection.vault.epilogues' constant (the same object, not a re-typed
    # copy).
    selected = EPILOGUES[status.outcome.value]
    assert selected is EPILOGUES["unresolved"]
    assert selected.headline == "THE STRUGGLE CONTINUES"
    assert selected.palette == "unresolved"
    assert selected.body == EPILOGUES["unresolved"].body
    page = render_epilogue(status.outcome.value)
    assert EPILOGUES["unresolved"].body in page


# --------------------------------------------------------------------------- #
# Leg 8 — terminal-state honesty: the crossed outcome/epilogue is stable across #
# a further real tick; the engine has no refusal gate. (spec.ts:441-482)        #
# --------------------------------------------------------------------------- #


def test_terminal_epilogue_is_stable_across_a_further_tick() -> None:
    """The first-crossing outcome/epilogue is unchanged by a further real tick,
    and the engine itself never refuses that further tick.
    """
    rigged = _rigged_horizon_defines()
    harness, world0 = _fresh_engine()

    _, world1 = _advance_tick(harness, world0, tick=1)
    status_1 = endgame_status(
        tick=1,
        pattern=harness.detector.recognized_pattern,
        since_tick=harness.detector.pattern_since_tick,
        defines=rigged,
        axes=harness.detector.axis_progress(),
    )
    epilogue_1 = EPILOGUES[status_1.outcome.value]

    # The engine has NO game-over refusal gate: a FURTHER real tick still
    # resolves and still emits events (ports the web's "a further resolve
    # succeeds" — the terminal thing is the client Step gate + the persisted
    # epilogue, not an engine refusal).
    raw_tick2, _ = _advance_tick(harness, world1, tick=2)
    assert raw_tick2, "the engine resolved a further tick with no refusal gate"

    status_2 = endgame_status(
        tick=2,
        pattern=harness.detector.recognized_pattern,
        since_tick=harness.detector.pattern_since_tick,
        defines=rigged,
        axes=harness.detector.axis_progress(),
    )
    epilogue_2 = EPILOGUES[status_2.outcome.value]

    # The crossed outcome/epilogue is stable across the further tick.
    assert status_2.game_over is True
    assert status_2.outcome is status_1.outcome is GameOutcome.UNRESOLVED
    assert epilogue_2 is epilogue_1

    # HONEST GAP: this stability holds because the material state never crosses
    # into a recognized pattern (the detector reads None at both ticks), so the
    # memoryless fold returns UNRESOLVED both times. The web's stronger guarantee
    # — the FIRST ENDGAME_REACHED row is authoritative even if a LATER tick would
    # recognize a different pattern (get_endgame_state's ORDER BY tick ASC LIMIT
    # 1) — is a PERSISTENCE guarantee absent from the pure endgame_status fold. A
    # future WO must persist the first endgame event to lock the outcome against
    # a later pattern recognition.
    assert harness.detector.recognized_pattern is None
