"""Contract for the M2 "Playable" RustClientHost surface (Tasks 21-25, ADR150).

Companion to ``test_host_contract.py`` (the M0/M1 lobby + read surface):
this module exercises the eleven write/tick methods
``docs/superpowers/specs/2026-07-27-m2-seam-contracts.md`` pins —
:meth:`~babylon.tui.host.RustClientHost.pacing_state_json` through
:meth:`~babylon.tui.host.RustClientHost.save_nav_state`. Unit tier only (no
Postgres): ``_FakeDriver``/``_FakeOutcome`` mirror
``tests/unit/game/test_pacing.py``'s own ``_FakeAdvancer``/``_FakeOutcome``
convention one layer up (faking the DRIVER seam the host calls, not the
advancer underneath it); ``_FakeSession`` mirrors this module's own
``test_host_contract.py`` sibling's ``_FakeCampaign`` convention (only the
``CampaignHandle`` members the M2 write methods actually call).

The verb-resolution mirror (``TestVerbResolutionMirror``) rebuilds
``tests/integration/archive/test_verb_resolution.py``'s minimal in-process
graph/journal fixture locally (that module is ``pytest.mark.integration``;
this one stays unit-tier) to pin the contract's own RECORDED DEVIATION: no
"remaining actions decrement" assertion exists in production
(``OODAProfile.action_points``/``enforce_action_points`` are declared but
never called on the live path — the dead-feature anti-pattern
``CLAUDE.md``'s vocabulary-sentinel section documents) — only the two REAL
behaviors that integration test pins: a submitted verb reaches
``turn_resolution.action_phase_results`` after ``OODASystem().step``, and
an unaffordable submission is refused before the queue.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.context import TickContext
from babylon.engine.systems.ooda import OODASystem
from babylon.models.enums import OrgType
from babylon.models.enums.events import EventType, GameOutcome
from babylon.models.enums.topology import NodeType
from babylon.projection.endgame import EndgameStatus
from babylon.projection.verbs.submit import build_player_actions, submit_verb
from babylon.projection.verbs.view_models import VerbPlateView, VerbPreview, VerbRow
from babylon.topology import BabylonGraph
from babylon.tui.campaign_menu import InMemoryCampaignCatalog
from babylon.tui.chronicle import CHRONICLE_ROW_CEILING, ChronicleEvent, TickBulletin
from babylon.tui.contract import PacedDriverHandle, TickOutcome
from babylon.tui.host import RustClientHost
from babylon.tui.nav import InMemoryNavPersistence
from babylon.tui.watchlist import DEFAULT_WATCHLIST_CAPACITY, InMemoryWatchlistPersistence

pytestmark = [pytest.mark.unit]

_DEFINES_HASH = "cafebabe" * 8
_ENGINE_VERSION = "9.9.9"
_SESSION_ID = UUID("00000000-0000-0000-0000-0000000000f2")


# --------------------------------------------------------------------------- #
# Fakes.                                                                       #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _FakeOutcome:
    """A minimal ``TickOutcome`` double — ``tick``/``paused``/``chronicle``
    only (the narrower seam :class:`~babylon.tui.app.PacedDriverHandle`
    actually needs, one layer up from ``test_pacing.py``'s own fuller
    ``TickOutcomeLike`` double)."""

    tick: int
    paused: bool = False
    chronicle: tuple[ChronicleEvent, ...] = ()


@dataclass
class _FakeDriver:
    """A minimal ``PacedDriverHandle`` double — scripted outcomes, no real
    ``PacedTickDriver`` machinery (mirrors ``test_pacing.py``'s own
    ``_FakeAdvancer`` convention one layer up: this fakes the seam the host
    actually calls)."""

    outcomes: list[_FakeOutcome] = field(default_factory=list)
    locked: bool = False
    lock_reason: str | None = None
    awaiting_ack: bool = False
    busy: bool = False
    pause_summary: str | None = None
    advance_calls: int = field(default=0, init=False)
    acknowledge_calls: int = field(default=0, init=False)

    def advance_once(self) -> _FakeOutcome:
        self.advance_calls += 1
        return self.outcomes.pop(0)

    def run_until_paused(self) -> tuple[_FakeOutcome, ...]:
        results = tuple(self.outcomes)
        self.outcomes = []
        return results

    def acknowledge_pause(self) -> None:
        self.acknowledge_calls += 1
        self.awaiting_ack = False


class _FakeSession:
    """A minimal ``CampaignHandle`` double covering only what the M2 write
    methods call (mirrors ``test_host_contract.py``'s own ``_FakeCampaign``
    convention: only the members actually exercised)."""

    def __init__(
        self,
        *,
        session_id: UUID = _SESSION_ID,
        verb_plate_view: VerbPlateView | None = None,
        endgame_status: EndgameStatus | None = None,
        issue_verb_result: object = 1,
    ) -> None:
        self.session_id = session_id
        self._verb_plate_view = verb_plate_view
        self._endgame_status = endgame_status
        self._issue_verb_result = issue_verb_result
        self.issue_verb_calls: list[tuple[str, str | None, str | None]] = []

    def verb_plate_view(self) -> VerbPlateView | None:
        return self._verb_plate_view

    def endgame_status(self) -> EndgameStatus | None:
        return self._endgame_status

    def issue_verb(
        self,
        action_id: str,
        *,
        target_id: str | None = None,
        target_community: str | None = None,
    ) -> int:
        self.issue_verb_calls.append((action_id, target_id, target_community))
        if isinstance(self._issue_verb_result, BaseException):
            raise self._issue_verb_result
        assert isinstance(self._issue_verb_result, int)
        return self._issue_verb_result


def _event(
    *, tick: int, event_type: EventType, summary: str, data: dict[str, Any] | None = None
) -> ChronicleEvent:
    return ChronicleEvent(tick=tick, event_type=event_type, summary=summary, data=data or {})


def _verb_plate_view() -> VerbPlateView:
    preview = VerbPreview(
        estimated_consciousness_delta=0.01,
        estimated_heat_delta=0.01,
        action_point_cost=1.0,
        success_probability=0.7,
        affected_territory_ids=(),
        warnings=(),
    )
    row = VerbRow(
        verb="educate",
        eligible=True,
        reason=None,
        remedy=None,
        can_afford=True,
        afford_note=None,
        preview=preview,
        candidate_target_ids=(),
    )
    return VerbPlateView(org_id="rev_workers", tick=3, verbs=(row,))


def _endgame_status() -> EndgameStatus:
    return EndgameStatus(
        pattern=None,
        outcome=GameOutcome.UNRESOLVED,
        game_over=False,
        horizon_tick=5200,
        since_tick=None,
        locked=False,
        axes={
            "revolutionary_victory": 0.1,
            "ecological_collapse": 0.0,
            "fascist_consolidation": 0.0,
            "red_ogv": 0.0,
            "fragmented_collapse": 0.0,
        },
    )


def _host(
    *,
    session: object | None = None,
    driver: object | None = None,
    watchlist_persistence: InMemoryWatchlistPersistence | None = None,
    nav_persistence: InMemoryNavPersistence | None = None,
) -> RustClientHost:
    host = RustClientHost(
        InMemoryCampaignCatalog(),
        defines_hash=_DEFINES_HASH,
        engine_version=_ENGINE_VERSION,
        watchlist_persistence=watchlist_persistence,
        nav_persistence=nav_persistence,
    )
    if session is not None:
        host.bind_session(session, driver)  # type: ignore[arg-type]
    return host


# --------------------------------------------------------------------------- #
# Fake seam conformance (mirrors test_pacing.py's own TestSeams).             #
# --------------------------------------------------------------------------- #


class TestFakeSeamConformance:
    def test_fake_outcome_satisfies_tick_outcome(self) -> None:
        assert isinstance(_FakeOutcome(tick=1), TickOutcome)

    def test_fake_driver_satisfies_paced_driver_handle(self) -> None:
        assert isinstance(_FakeDriver(), PacedDriverHandle)


# --------------------------------------------------------------------------- #
# (a) advance_tick.                                                            #
# --------------------------------------------------------------------------- #


class TestAdvanceTick:
    def test_no_driver_attached_is_a_refusal(self) -> None:
        payload = json.loads(_host().advance_tick())
        assert payload == {
            "ok": False,
            "error": "advance_tick: no paced driver attached — no live campaign bound",
        }

    def test_session_bound_but_no_driver_factory_is_still_a_refusal(self) -> None:
        # A legal M1 state (session bound, driver never wired) must not be
        # confused with "attached" — the same driver-is-None check governs.
        payload = json.loads(_host(session=_FakeSession()).advance_tick())
        assert payload["ok"] is False

    def test_success_envelope_and_exact_key_order(self) -> None:
        chronicle = (_event(tick=5, event_type=EventType.UPRISING, summary="revolt"),)
        driver = _FakeDriver(outcomes=[_FakeOutcome(tick=5, paused=False, chronicle=chronicle)])
        host = _host(session=_FakeSession(), driver=driver)

        raw = host.advance_tick()
        payload = json.loads(raw)

        assert payload["ok"] is True
        assert list(payload["outcome"].keys()) == ["tick", "paused", "chronicle"]
        assert payload["outcome"]["tick"] == 5
        assert payload["outcome"]["paused"] is False
        assert len(payload["outcome"]["chronicle"]) == 1
        assert payload["outcome"]["chronicle"][0]["event_type"] == "uprising"
        # Belt-and-suspenders: pin the RAW string's own key sequence too, not
        # just the round-tripped dict's (json.loads already preserves
        # insertion order in CPython, but the contract asks for both).
        start = raw.index('"outcome"')
        assert (
            raw.index('"tick"', start)
            < raw.index('"paused"', start)
            < raw.index('"chronicle"', start)
        )

    def test_advance_calls_the_driver_exactly_once(self) -> None:
        driver = _FakeDriver(outcomes=[_FakeOutcome(tick=1)])
        host = _host(session=_FakeSession(), driver=driver)
        host.advance_tick()
        assert driver.advance_calls == 1


# --------------------------------------------------------------------------- #
# (b) run_until_paused.                                                        #
# --------------------------------------------------------------------------- #


class TestRunUntilPaused:
    def test_no_driver_attached_is_a_refusal(self) -> None:
        payload = json.loads(_host().run_until_paused())
        assert payload == {
            "ok": False,
            "error": "run_until_paused: no paced driver attached — no live campaign bound",
        }

    def test_returns_one_outcome_per_tick_in_order(self) -> None:
        driver = _FakeDriver(
            outcomes=[
                _FakeOutcome(tick=1, paused=False),
                _FakeOutcome(tick=2, paused=False),
                _FakeOutcome(tick=3, paused=True),
            ]
        )
        host = _host(session=_FakeSession(), driver=driver)

        payload = json.loads(host.run_until_paused())

        assert payload["ok"] is True
        assert [o["tick"] for o in payload["outcomes"]] == [1, 2, 3]
        assert [o["paused"] for o in payload["outcomes"]] == [False, False, True]
        for outcome in payload["outcomes"]:
            assert list(outcome.keys()) == ["tick", "paused", "chronicle"]


# --------------------------------------------------------------------------- #
# (c) pacing_state_json.                                                       #
# --------------------------------------------------------------------------- #


class TestPacingStateJson:
    def test_no_driver_is_the_unattached_shape(self) -> None:
        assert json.loads(_host().pacing_state_json()) == {
            "attached": False,
            "locked": False,
            "lock_reason": None,
            "awaiting_ack": False,
            "pause_summary": None,
            "busy": False,
        }

    def test_key_order(self) -> None:
        payload = json.loads(_host().pacing_state_json())
        assert list(payload.keys()) == [
            "attached",
            "locked",
            "lock_reason",
            "awaiting_ack",
            "pause_summary",
            "busy",
        ]

    def test_ready_driver(self) -> None:
        host = _host(session=_FakeSession(), driver=_FakeDriver())
        payload = json.loads(host.pacing_state_json())
        assert payload == {
            "attached": True,
            "locked": False,
            "lock_reason": None,
            "awaiting_ack": False,
            "pause_summary": None,
            "busy": False,
        }

    def test_locked_driver(self) -> None:
        driver = _FakeDriver(locked=True, lock_reason="RED_OGV")
        host = _host(session=_FakeSession(), driver=driver)
        payload = json.loads(host.pacing_state_json())
        assert payload["locked"] is True
        assert payload["lock_reason"] == "RED_OGV"

    def test_awaiting_ack_driver(self) -> None:
        driver = _FakeDriver(awaiting_ack=True, pause_summary="tick 3: uprising")
        host = _host(session=_FakeSession(), driver=driver)
        payload = json.loads(host.pacing_state_json())
        assert payload["awaiting_ack"] is True
        assert payload["pause_summary"] == "tick 3: uprising"

    def test_busy_driver(self) -> None:
        driver = _FakeDriver(busy=True)
        host = _host(session=_FakeSession(), driver=driver)
        assert json.loads(host.pacing_state_json())["busy"] is True


# --------------------------------------------------------------------------- #
# (d) acknowledge_pause.                                                       #
# --------------------------------------------------------------------------- #


class TestAcknowledgePause:
    def test_no_driver_attached_is_a_refusal(self) -> None:
        assert json.loads(_host().acknowledge_pause()) == {
            "ok": False,
            "error": "acknowledge_pause: no paced driver attached",
        }

    def test_success_clears_the_pending_ack(self) -> None:
        driver = _FakeDriver(awaiting_ack=True, pause_summary="tick 3: uprising")
        host = _host(session=_FakeSession(), driver=driver)

        result = json.loads(host.acknowledge_pause())

        assert result == {"ok": True}
        assert driver.acknowledge_calls == 1
        assert driver.awaiting_ack is False


# --------------------------------------------------------------------------- #
# (e) chronicle rail — accumulator, pipeline order, autopause, row shapes.     #
# --------------------------------------------------------------------------- #


class TestChronicleRail:
    def test_unbound_host_is_honest_absence(self) -> None:
        assert json.loads(_host().chronicle_rail_json()) == {"autopause_line": None, "rows": []}

    def test_bound_host_with_no_ticks_yet_is_empty_rows(self) -> None:
        host = _host(session=_FakeSession(), driver=_FakeDriver())
        assert json.loads(host.chronicle_rail_json()) == {"autopause_line": None, "rows": []}

    def test_two_ticks_accumulate(self) -> None:
        driver = _FakeDriver(
            outcomes=[
                _FakeOutcome(
                    tick=1,
                    chronicle=(
                        _event(
                            tick=1,
                            event_type=EventType.MASS_AWAKENING,
                            summary="stirring",
                            data={"target_id": "C001"},
                        ),
                    ),
                ),
                _FakeOutcome(
                    tick=2,
                    chronicle=(_event(tick=2, event_type=EventType.UPRISING, summary="revolt"),),
                ),
            ]
        )
        host = _host(session=_FakeSession(), driver=driver)

        host.advance_tick()
        host.advance_tick()

        payload = json.loads(host.chronicle_rail_json())
        headers = [row for row in payload["rows"] if row["kind"] == "header"]
        assert {h["tick"] for h in headers} == {1, 2}

    def test_cap_respected(self) -> None:
        # Distinct per-tick node_ids keep every event's dedup key unique:
        # chronicle_subject's precedence walk reads node_id (target_id is
        # only the class-scoped NAVIGABLE-subject field, not a dedup field),
        # and without it every row keys as "mass_awakening:global" and
        # tick-independent dedupe_consecutive collapses the whole run to one
        # row before the cap could ever be observed.
        total_ticks = CHRONICLE_ROW_CEILING + 5
        driver = _FakeDriver(
            outcomes=[
                _FakeOutcome(
                    tick=t,
                    chronicle=(
                        _event(
                            tick=t,
                            event_type=EventType.MASS_AWAKENING,
                            summary=f"s{t}",
                            data={"target_id": f"C{t:03d}", "node_id": f"C{t:03d}"},
                        ),
                    ),
                )
                for t in range(1, total_ticks + 1)
            ]
        )
        host = _host(session=_FakeSession(), driver=driver)
        for _ in range(total_ticks):
            host.advance_tick()

        payload = json.loads(host.chronicle_rail_json())
        event_rows = [row for row in payload["rows"] if row["kind"] == "event"]
        assert len(event_rows) == CHRONICLE_ROW_CEILING
        ticks_present = {row["tick"] for row in event_rows}
        assert min(ticks_present) == total_ticks - CHRONICLE_ROW_CEILING + 1
        assert max(ticks_present) == total_ticks

    def test_pipeline_runs_volume_floors_before_dedupe(self) -> None:
        """Two ORGANIZATIONAL_ACTION events in one tick, plus a
        distinguishing third event. The PRODUCTION order
        (``dedupe_consecutive(apply_volume_floors(history))``) rolls the
        pair up into ONE "2 organizational actions" card BEFORE dedupe ever
        runs. The WRONG order (dedupe first) would instead leave a "1
        organizational action" card, since ``aggregate_organizational_actions``
        aggregates whatever survived dedupe's own (unrelated) collapse —
        this fixture is engineered so the two orders diverge, pinning that
        floors really does run first.
        """
        org_a = _event(tick=9, event_type=EventType.ORGANIZATIONAL_ACTION, summary="org acted (a)")
        org_b = _event(tick=9, event_type=EventType.ORGANIZATIONAL_ACTION, summary="org acted (b)")
        other = _event(
            tick=9,
            event_type=EventType.MASS_AWAKENING,
            summary="stirring",
            data={"target_id": "C001"},
        )
        driver = _FakeDriver(outcomes=[_FakeOutcome(tick=9, chronicle=(org_a, org_b, other))])
        host = _host(session=_FakeSession(), driver=driver)

        host.advance_tick()
        payload = json.loads(host.chronicle_rail_json())

        rollup_rows = [
            row
            for row in payload["rows"]
            if row["kind"] == "event" and "organizational action" in row["text"]
        ]
        assert len(rollup_rows) == 1
        assert rollup_rows[0]["text"] == "2 organizational actions this tick"

    def test_autopause_line_present_iff_critical_event_in_salient_window(self) -> None:
        driver = _FakeDriver(
            outcomes=[
                _FakeOutcome(
                    tick=1,
                    chronicle=(_event(tick=1, event_type=EventType.UPRISING, summary="revolt"),),
                )
            ]
        )
        host = _host(session=_FakeSession(), driver=driver)
        assert json.loads(host.chronicle_rail_json())["autopause_line"] is None

        host.advance_tick()
        payload = json.loads(host.chronicle_rail_json())
        assert payload["autopause_line"] == "⏸ AUTOPAUSE — THIS CANNOT PASS UNREAD"

    def test_autopause_line_absent_with_no_critical_event(self) -> None:
        driver = _FakeDriver(
            outcomes=[
                _FakeOutcome(
                    tick=1,
                    chronicle=(
                        _event(
                            tick=1,
                            event_type=EventType.MASS_AWAKENING,
                            summary="stirring",
                            data={"target_id": "C001"},
                        ),
                    ),
                )
            ]
        )
        host = _host(session=_FakeSession(), driver=driver)
        host.advance_tick()
        assert json.loads(host.chronicle_rail_json())["autopause_line"] is None

    def test_header_row_shape(self) -> None:
        rows = RustClientHost._bulletin_rows(
            TickBulletin(
                tick=847,
                events=(
                    _event(
                        tick=847,
                        event_type=EventType.MASS_AWAKENING,
                        summary="stirring",
                        data={"target_id": "C001"},
                    ),
                ),
            )
        )
        assert rows[0] == {
            "subject": None,
            "kind": "header",
            "tick": 847,
            "severity": None,
            "actor": None,
            "text": "T0847",
        }

    def test_event_row_shape(self) -> None:
        rows = RustClientHost._bulletin_rows(
            TickBulletin(
                tick=847,
                events=(
                    _event(
                        tick=847,
                        event_type=EventType.MASS_AWAKENING,
                        summary="stirring",
                        data={"target_id": "C001"},
                    ),
                ),
            )
        )
        # MASS_AWAKENING is CROSSING + INTRA_LEVEL => "informational" via
        # resolve_severity (the production path); _LEGACY_HAND_TIERS' old
        # "warning" row is retired drift documentation, not the contract.
        assert rows[1] == {
            "subject": "social_class/C001",
            "kind": "event",
            "tick": 847,
            "severity": "informational",
            "actor": "the Periphery Proletariat",
            "text": "stirring",
        }

    def test_no_quiet_kind_exists(self) -> None:
        """chronicle_stream never emits an empty bulletin (its own
        documented contract), so the rail has NO "quiet" row kind — an
        empty rail is the client-side honest-absence state. This pin keeps
        the dead variant from quietly returning."""
        rows = RustClientHost._bulletin_rows(
            TickBulletin(
                tick=846,
                events=(_event(tick=846, event_type=EventType.UPRISING, summary="x"),),
            )
        )
        assert {row["kind"] for row in rows} == {"header", "event"}

    def test_reset_on_rebind(self) -> None:
        driver1 = _FakeDriver(
            outcomes=[
                _FakeOutcome(
                    tick=1,
                    chronicle=(_event(tick=1, event_type=EventType.UPRISING, summary="revolt"),),
                )
            ]
        )
        host = _host(session=_FakeSession(), driver=driver1)
        host.advance_tick()
        assert json.loads(host.chronicle_rail_json())["rows"]

        host.bind_session(_FakeSession(session_id=UUID(int=99)), _FakeDriver())  # type: ignore[arg-type]

        assert json.loads(host.chronicle_rail_json()) == {"autopause_line": None, "rows": []}


# --------------------------------------------------------------------------- #
# (f) verb_plate_view_json.                                                    #
# --------------------------------------------------------------------------- #


class TestVerbPlateViewJson:
    def test_unbound_host_is_null(self) -> None:
        assert _host().verb_plate_view_json() == "null"

    def test_no_plate_wired_is_null(self) -> None:
        host = _host(session=_FakeSession(verb_plate_view=None))
        assert host.verb_plate_view_json() == "null"

    def test_bound_session_round_trips_the_real_view_model(self) -> None:
        view = _verb_plate_view()
        host = _host(session=_FakeSession(verb_plate_view=view))

        payload = json.loads(host.verb_plate_view_json())

        assert payload["kind"] == "verb_plate"
        assert payload["org_id"] == "rev_workers"
        assert payload["tick"] == 3
        assert payload["verbs"][0]["verb"] == "educate"
        assert payload["verbs"][0]["preview"]["action_point_cost"] == 1.0


# --------------------------------------------------------------------------- #
# (g) issue_verb.                                                              #
# --------------------------------------------------------------------------- #


class TestIssueVerb:
    def test_no_session_is_a_refusal(self) -> None:
        args = json.dumps({"verb": "educate", "target_id": None, "target_community": None})
        payload = json.loads(_host().issue_verb(args))
        assert payload == {
            "ok": False,
            "error": "issue_verb: no live campaign attached — nothing to act on",
        }

    def test_success_envelope_threads_the_args_through(self) -> None:
        session = _FakeSession(issue_verb_result=17)
        host = _host(session=session)
        args = json.dumps({"verb": "educate", "target_id": "sc-x", "target_community": None})

        payload = json.loads(host.issue_verb(args))

        assert payload == {"ok": True, "turn_id": 17}
        assert session.issue_verb_calls == [("educate", "sc-x", None)]

    @pytest.mark.parametrize(
        "exc",
        [RuntimeError("institutional macro-action"), ValueError("cannot afford"), KeyError("nope")],
    )
    def test_each_caught_exception_type_is_a_refusal(self, exc: Exception) -> None:
        session = _FakeSession(issue_verb_result=exc)
        host = _host(session=session)
        args = json.dumps({"verb": "attack", "target_id": None, "target_community": None})

        payload = json.loads(host.issue_verb(args))

        assert payload["ok"] is False
        assert payload["error"]

    def test_an_uncaught_exception_type_propagates(self) -> None:
        session = _FakeSession(issue_verb_result=TypeError("not one of the three"))
        host = _host(session=session)
        args = json.dumps({"verb": "attack", "target_id": None, "target_community": None})

        with pytest.raises(TypeError, match="not one of the three"):
            host.issue_verb(args)


# --------------------------------------------------------------------------- #
# (h) endgame_status_json.                                                     #
# --------------------------------------------------------------------------- #


class TestEndgameStatusJson:
    def test_unbound_host_is_null(self) -> None:
        assert _host().endgame_status_json() == "null"

    def test_bound_session_with_no_projection_wired_is_null(self) -> None:
        host = _host(session=_FakeSession(endgame_status=None))
        assert host.endgame_status_json() == "null"

    def test_bound_session_round_trips_the_real_status_model(self) -> None:
        status = _endgame_status()
        host = _host(session=_FakeSession(endgame_status=status))

        payload = json.loads(host.endgame_status_json())

        assert payload["pattern"] is None
        assert payload["game_over"] is False
        assert payload["horizon_tick"] == 5200
        assert payload["axes"]["revolutionary_victory"] == 0.1


# --------------------------------------------------------------------------- #
# (i) pin_watchlist.                                                           #
# --------------------------------------------------------------------------- #


class TestPinWatchlist:
    def test_no_session_or_store_is_a_refusal(self) -> None:
        args = json.dumps({"subject": "county/26163", "pinned": True})
        payload = json.loads(_host().pin_watchlist(args))
        assert payload["ok"] is False

    def test_no_watchlist_store_wired_is_a_refusal(self) -> None:
        args = json.dumps({"subject": "county/26163", "pinned": True})
        payload = json.loads(_host(session=_FakeSession()).pin_watchlist(args))
        assert payload["ok"] is False

    def test_pin_then_unpin_round_trips(self) -> None:
        persistence = InMemoryWatchlistPersistence()
        host = _host(session=_FakeSession(), watchlist_persistence=persistence)

        pin_payload = json.loads(
            host.pin_watchlist(json.dumps({"subject": "county/26163", "pinned": True}))
        )
        assert pin_payload == {"ok": True, "pinned": True}
        assert json.loads(host.watchlist_json()) == [{"subject": "county/26163"}]

        unpin_payload = json.loads(
            host.pin_watchlist(json.dumps({"subject": "county/26163", "pinned": False}))
        )
        assert unpin_payload == {"ok": True, "pinned": False}
        assert json.loads(host.watchlist_json()) == []

    def test_pin_is_idempotent(self) -> None:
        persistence = InMemoryWatchlistPersistence()
        host = _host(session=_FakeSession(), watchlist_persistence=persistence)
        args = json.dumps({"subject": "county/26163", "pinned": True})

        host.pin_watchlist(args)
        second = json.loads(host.pin_watchlist(args))

        assert second == {"ok": True, "pinned": True}
        assert json.loads(host.watchlist_json()) == [{"subject": "county/26163"}]

    def test_unpin_is_idempotent(self) -> None:
        persistence = InMemoryWatchlistPersistence()
        host = _host(session=_FakeSession(), watchlist_persistence=persistence)
        args = json.dumps({"subject": "county/26163", "pinned": False})

        first = json.loads(host.pin_watchlist(args))

        assert first == {"ok": True, "pinned": False}
        assert json.loads(host.watchlist_json()) == []

    def test_capacity_value_error_is_a_refusal(self) -> None:
        persistence = InMemoryWatchlistPersistence()
        host = _host(session=_FakeSession(), watchlist_persistence=persistence)
        for i in range(DEFAULT_WATCHLIST_CAPACITY):
            host.pin_watchlist(json.dumps({"subject": f"county/{i:05d}", "pinned": True}))

        payload = json.loads(
            host.pin_watchlist(json.dumps({"subject": "county/overflow", "pinned": True}))
        )

        assert payload["ok"] is False
        assert "capacity" in payload["error"]
        # The refused pin never landed.
        assert len(json.loads(host.watchlist_json())) == DEFAULT_WATCHLIST_CAPACITY


# --------------------------------------------------------------------------- #
# (j) nav_state_json / save_nav_state.                                        #
# --------------------------------------------------------------------------- #


class TestNavState:
    def test_unbound_host_is_empty(self) -> None:
        assert json.loads(_host().nav_state_json()) == {"jumplist": [], "breadcrumbs": []}

    def test_no_persistence_wired_is_empty(self) -> None:
        host = _host(session=_FakeSession())
        assert json.loads(host.nav_state_json()) == {"jumplist": [], "breadcrumbs": []}

    def test_save_nav_state_no_session_is_a_refusal(self) -> None:
        args = json.dumps({"jumplist": [], "breadcrumbs": []})
        payload = json.loads(_host().save_nav_state(args))
        assert payload["ok"] is False

    def test_round_trip_via_in_memory_nav_persistence(self) -> None:
        persistence = InMemoryNavPersistence()
        host = _host(session=_FakeSession(), nav_persistence=persistence)
        nav = {"jumplist": ["county/26163", "org/uaw-9999"], "breadcrumbs": ["county/26163"]}

        save_result = json.loads(host.save_nav_state(json.dumps(nav)))

        assert save_result == {"ok": True}
        assert json.loads(host.nav_state_json()) == nav

    def test_duplicates_are_allowed_not_deduped(self) -> None:
        # Only the watchlist enforces uniqueness — jumplist/breadcrumb rows
        # allow duplicates; the round-trip must NOT assert dedup.
        persistence = InMemoryNavPersistence()
        host = _host(session=_FakeSession(), nav_persistence=persistence)
        nav = {"jumplist": ["a", "a", "b"], "breadcrumbs": ["a", "a"]}

        host.save_nav_state(json.dumps(nav))

        assert json.loads(host.nav_state_json()) == nav


# --------------------------------------------------------------------------- #
# (k) Verb-resolution mirror (contract §3's RECORDED DEVIATION).              #
# --------------------------------------------------------------------------- #

_ORG = "rev_workers"
_COMMUNITY = "comm_detroit"


class _TurnJournal:
    """Structural ``TurnSink`` — plays the ``game_turn`` table's role
    in-memory (rebuilt locally, per this unit-tier module's own docstring —
    the source ``test_verb_resolution.py`` is ``pytest.mark.integration``)."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

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
        params_json: dict[str, Any] | None = None,
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


class _VerbResolutionSession:
    """A ``CampaignHandle`` double whose ``issue_verb`` really queues
    through :func:`~babylon.projection.verbs.submit.submit_verb` — mirrors
    ``GameSession.issue_verb``'s own real write path, minus the registry
    persona gate (which needs no live registry row for this fixture's
    org/verb)."""

    def __init__(
        self, *, session_id: UUID, tick: int, graph: BabylonGraph, journal: _TurnJournal
    ) -> None:
        self.session_id = session_id
        self.tick = tick
        self._graph = graph
        self._journal = journal

    def issue_verb(
        self,
        action_id: str,
        *,
        target_id: str | None = None,
        target_community: str | None = None,
    ) -> int:
        return submit_verb(
            self._journal,
            session_id=self.session_id,
            tick=self.tick,
            org_id=_ORG,
            verb=action_id,
            graph=self._graph,
            target_id=target_id,
            target_community=target_community,
        )


def _verb_graph() -> BabylonGraph:
    """One player faction with a community in reach (OODA-minimal shape) —
    same fixture shape as ``test_verb_resolution.py``'s own ``_graph``."""
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


def _ooda_services() -> MagicMock:
    services = MagicMock()
    services.defines = GameDefines()
    services.event_bus = MagicMock()
    return services


class TestVerbResolutionMirror:
    """See this module's own docstring: the RECORDED DEVIATION fixture —
    no "remaining actions decrement" assertion (that counter is dormant in
    production); only the two REAL behaviors the integration test pins."""

    def test_a_submitted_verb_reaches_turn_resolution_through_the_engine(self) -> None:
        graph = _verb_graph()
        journal = _TurnJournal()
        session = _VerbResolutionSession(
            session_id=_SESSION_ID, tick=1, graph=graph, journal=journal
        )
        host = _host(session=session)

        args = json.dumps({"verb": "educate", "target_id": _COMMUNITY, "target_community": None})
        payload = json.loads(host.issue_verb(args))
        assert payload["ok"] is True

        player_actions = build_player_actions(journal.rows)
        context = TickContext(tick=1, persistent_data={"player_actions": player_actions})
        OODASystem().step(graph, _ooda_services(), context)

        resolution = context.persistent_data["turn_resolution"]
        ours = [r for r in resolution["action_phase_results"] if r["action"]["org_id"] == _ORG]
        assert ours, "the queued player action must resolve in the action phase"
        assert any(r["action"]["action_type"] == "educate" for r in ours)

    def test_an_unaffordable_submission_is_refused_before_the_queue(self) -> None:
        graph = _verb_graph()
        graph.update_node(_ORG, budget=0.0, cadre_level=0.0, cohesion=0.0)
        journal = _TurnJournal()
        session = _VerbResolutionSession(
            session_id=_SESSION_ID, tick=1, graph=graph, journal=journal
        )
        host = _host(session=session)

        args = json.dumps({"verb": "educate", "target_id": _COMMUNITY, "target_community": None})
        payload = json.loads(host.issue_verb(args))

        assert payload["ok"] is False
        assert "Cannot afford" in payload["error"]
        assert journal.rows == []
