"""Unit tests for the campaign composition root — protocol fakes only.

Pins the seams :mod:`babylon.game.session` glues together (per Program
v1.0.0 Unit C1): a real ``WayneCountyScenario`` + a real 30-system
``SimulationEngine`` tick loop run against a :class:`_FakeStore` satisfying
:class:`~babylon.game.session.GameRuntimeStore` structurally (the WO-37
trick) — no Postgres required. The PG-reachable integration leg lives at
``tests/integration/game/test_session_integration.py``.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

import babylon.game.session as session_module
from babylon.config.defines import GameDefines
from babylon.engine.scenarios import WayneCountyScenario
from babylon.game.session import (
    TickAdvanceResult,
    create_new_campaign,
    default_pause_predicate,
    open_runtime,
    resume_campaign,
    vault_page_source,
)
from babylon.kernel.event_bus import Event
from babylon.models.config import SimulationConfig
from babylon.models.enums.events import EventType
from babylon.models.world_state import WorldState
from babylon.persistence.envelope import PerTickTransactionEnvelope
from babylon.topology import BabylonGraph

pytestmark = [pytest.mark.unit]


class _FakeStore:
    """In-memory double satisfying ``GameRuntimeStore`` structurally.

    Mirrors ``PostgresRuntime``'s real per-method contract (return shapes,
    keyword-only ``session_id``/``tick`` splits) closely enough that
    :mod:`babylon.game.session` cannot tell the difference — the point of
    the WO-37 structural-Protocol seam.
    """

    def __init__(self) -> None:
        self.sessions: dict[UUID, dict[str, Any]] = {}
        self.persist_tick_calls: list[tuple[int, UUID | None]] = []
        self.persist_tick_atomic_calls: list[PerTickTransactionEnvelope] = []
        self.mark_resolved_calls: list[tuple[UUID, int]] = []
        self.get_pending_turns_calls: list[tuple[UUID, int]] = []
        self.submit_turn_calls: list[dict[str, Any]] = []
        self._graphs: dict[tuple[UUID, int], BabylonGraph] = {}
        self._last_committed: dict[UUID, int] = {}

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
        session_id = session_id if session_id is not None else uuid4()
        self.sessions[session_id] = {
            "id": session_id,
            "scenario": scenario,
            "config_json": config_json,
            "game_defines_json": game_defines_json,
            "rng_seed": rng_seed,
            "trace_level": trace_level,
            "player_id": player_id,
        }
        return session_id

    def get_session(self, session_id: UUID) -> dict[str, Any] | None:
        return self.sessions.get(session_id)

    def get_pending_turns(self, session_id: UUID, tick: int) -> list[dict[str, Any]]:
        self.get_pending_turns_calls.append((session_id, tick))
        return []

    def mark_turns_resolved(self, session_id: UUID, tick: int) -> int:
        self.mark_resolved_calls.append((session_id, tick))
        return 0

    def persist_tick(
        self,
        tick: int,
        graph: BabylonGraph,
        events: list[dict[str, Any]] | None = None,
        *,
        session_id: UUID | None = None,
    ) -> None:
        self.persist_tick_calls.append((tick, session_id))
        self._graphs[(session_id, tick)] = graph  # type: ignore[index]

    def hydrate_graph(
        self, tick: int | None = None, *, session_id: UUID | None = None
    ) -> BabylonGraph:
        if tick is None:
            tick = max(t for sid, t in self._graphs if sid == session_id)
        return self._graphs[(session_id, tick)]  # type: ignore[index]

    def persist_tick_atomic(
        self, envelope: PerTickTransactionEnvelope, *, write_commit_marker: bool = True
    ) -> None:
        self.persist_tick_atomic_calls.append(envelope)
        if write_commit_marker:
            self._last_committed[envelope.session_id] = envelope.tick

    def get_last_committed_tick(self, session_id: UUID) -> int | None:
        return self._last_committed.get(session_id)

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
        self.submit_turn_calls.append(
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
        return len(self.submit_turn_calls)


class _RecordingObserver:
    """``TickCommitObserver`` double — records every observed tick."""

    def __init__(self) -> None:
        self.ticks: list[int] = []

    def on_tick_committed(self, *, tick: int, world: Any, graph: Any) -> None:  # noqa: ARG002
        self.ticks.append(tick)


# --------------------------------------------------------------------------- #
# default_pause_predicate — the T1.1 seam's default implementation.           #
# --------------------------------------------------------------------------- #


def test_default_pause_predicate_true_only_for_critical_tier() -> None:
    """Ports the WO-48 crisis leg's own assertion (ENDGAME_REACHED IS
    critical; LIFECYCLE_TRANSITION is not — the pilot's own documented
    "only warning-tier events" scenario)."""
    critical = Event(type=EventType.ENDGAME_REACHED.value, tick=1, payload={})
    warning = Event(type=EventType.LIFECYCLE_TRANSITION.value, tick=1, payload={})

    assert default_pause_predicate((critical,)) is True
    assert default_pause_predicate((warning,)) is False
    assert default_pause_predicate(()) is False
    assert default_pause_predicate((warning, critical)) is True


def test_default_pause_predicate_raises_loud_on_unknown_event_type() -> None:
    """Constitution III.11: a bus event with a bogus ``.type`` raises rather
    than silently defaulting to non-critical."""
    bogus = Event(type="not_a_real_event_type", tick=1, payload={})
    with pytest.raises(ValueError):
        default_pause_predicate((bogus,))


# --------------------------------------------------------------------------- #
# create_new_campaign — fresh boot + tick-0 bake.                             #
# --------------------------------------------------------------------------- #


def test_create_new_campaign_boots_fresh_session_and_bakes_tick_zero() -> None:
    store = _FakeStore()
    observer = _RecordingObserver()

    session = create_new_campaign(
        store, scenario=WayneCountyScenario(), tick_commit_observer=observer
    )

    assert session.tick == 0
    assert session.scenario_name == "wayne_county"
    assert store.sessions[session.session_id]["scenario"] == "wayne_county"
    assert store.persist_tick_calls == [(0, session.session_id)]
    assert observer.ticks == [0]

    assert len(store.persist_tick_atomic_calls) == 1
    envelope = store.persist_tick_atomic_calls[0]
    assert envelope.session_id == session.session_id
    assert envelope.tick == 0
    assert len(envelope.determinism_hash) == 64
    assert store.get_last_committed_tick(session.session_id) == 0


def test_create_new_campaign_runs_with_no_vault_observer() -> None:
    """``tick_commit_observer=None`` (the default) must not error — a run
    with no vault is the pre-Archive byte-identical path."""
    store = _FakeStore()
    session = create_new_campaign(store, scenario=WayneCountyScenario())
    assert session.tick == 0


def test_create_new_campaign_honors_an_explicit_session_id() -> None:
    """Unit C2: the lobby's ``babylon_meta.campaign_id`` can double as the
    engine's ``game_session.id`` — one identity, not a maintained mapping."""
    store = _FakeStore()
    chosen_id = uuid4()

    session = create_new_campaign(store, scenario=WayneCountyScenario(), session_id=chosen_id)

    assert session.session_id == chosen_id
    assert store.sessions[chosen_id]["scenario"] == "wayne_county"
    assert store.persist_tick_calls == [(0, chosen_id)]


def test_create_new_campaign_still_mints_when_session_id_is_none() -> None:
    """The default (``session_id=None``) mints a fresh id, unchanged."""
    store = _FakeStore()
    session = create_new_campaign(store, scenario=WayneCountyScenario())
    assert session.session_id in store.sessions


# --------------------------------------------------------------------------- #
# advance_tick — the pacing driver's one step (clear_history/run_tick/        #
# get_history + real persistence + observer hookup).                         #
# --------------------------------------------------------------------------- #


def test_advance_tick_runs_one_real_tick_and_persists_and_bakes() -> None:
    store = _FakeStore()
    observer = _RecordingObserver()
    session = create_new_campaign(
        store, scenario=WayneCountyScenario(), tick_commit_observer=observer
    )

    result = session.advance_tick()

    assert isinstance(result, TickAdvanceResult)
    assert session.tick == 1
    assert result.tick == 1
    assert isinstance(result.world, WorldState)
    assert result.world.tick == 1
    assert isinstance(result.events, tuple)
    assert len(result.determinism_hash) == 64

    assert store.get_pending_turns_calls == [(session.session_id, 1)]
    assert (1, session.session_id) in store.persist_tick_calls
    assert store.mark_resolved_calls == [(session.session_id, 1)]
    assert observer.ticks == [0, 1]
    assert any(env.tick == 1 for env in store.persist_tick_atomic_calls)

    # The determinism hash matches the session's own replay-identity formula
    # (mirrors headless_runner.runner's sha256(f"{session_id}:{tick}:{seed}")).
    expected_hash = session_module._replay_identity_hash(session.session_id, 1, 0)
    assert result.determinism_hash == expected_hash


def test_advance_tick_clears_bus_history_before_each_tick() -> None:
    """Two advances never accumulate the first tick's events into the
    second (the WO-50 pilot's ``clear_history`` contract)."""
    store = _FakeStore()
    session = create_new_campaign(store, scenario=WayneCountyScenario())

    session.advance_tick()
    second = session.advance_tick()

    assert second.tick == 2
    # The bus is cleared each tick, so every tick-2 event carries tick=2 —
    # none of tick 1's events leaked forward (the WO-50 clear_history contract).
    assert all(event.tick == 2 for event in second.events)


def test_pause_predicate_seam_is_injectable() -> None:
    """The T1.1 requirement: a caller-supplied predicate overrides the
    default entirely, with no change to ``GameSession`` itself."""
    store = _FakeStore()

    always_pause = create_new_campaign(
        store,
        scenario=WayneCountyScenario(),
        pause_predicate=lambda events: True,  # noqa: ARG005
    )
    assert always_pause.advance_tick().paused is True

    never_pause = create_new_campaign(
        store,
        scenario=WayneCountyScenario(),
        pause_predicate=lambda events: False,  # noqa: ARG005
    )
    assert never_pause.advance_tick().paused is False


# --------------------------------------------------------------------------- #
# submit_verb — thin passthrough to projection.verbs.submit.submit_verb.      #
# --------------------------------------------------------------------------- #


def test_session_submit_verb_forwards_to_projection_submit_verb(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _FakeStore()
    session = create_new_campaign(store, scenario=WayneCountyScenario())
    captured: dict[str, Any] = {}

    def _fake_submit_verb(
        persistence: Any,
        *,
        session_id: UUID,
        tick: int,
        org_id: str,
        verb: str,
        graph: Any,
        **kwargs: Any,
    ) -> int:
        captured.update(
            persistence=persistence,
            session_id=session_id,
            tick=tick,
            org_id=org_id,
            verb=verb,
            graph=graph,
            kwargs=kwargs,
        )
        return 7

    monkeypatch.setattr(session_module, "submit_verb", _fake_submit_verb)

    result = session.submit_verb(org_id="ORG001", verb="educate", target_id="comm_x")

    assert result == 7
    assert captured["persistence"] is store
    assert captured["session_id"] == session.session_id
    assert captured["tick"] == 1  # session.tick (0) + 1 — queued for the NEXT tick
    assert captured["org_id"] == "ORG001"
    assert captured["verb"] == "educate"
    assert captured["graph"] is session.graph
    assert captured["kwargs"]["target_id"] == "comm_x"


# --------------------------------------------------------------------------- #
# resume_campaign — crash-resume via get_last_committed_tick + hydrate_graph. #
# --------------------------------------------------------------------------- #


def test_resume_campaign_reconstructs_from_last_committed_tick() -> None:
    store = _FakeStore()
    session_id = uuid4()
    defines = GameDefines()
    sim_config = SimulationConfig(rng_seed=42)
    store.sessions[session_id] = {
        "id": session_id,
        "scenario": "wayne_county",
        "config_json": sim_config.model_dump(mode="json"),
        "game_defines_json": defines.model_dump(mode="json"),
        "rng_seed": 42,
    }
    graph = BabylonGraph()
    store._graphs[(session_id, 3)] = graph
    store._last_committed[session_id] = 3

    resumed = resume_campaign(store, session_id)

    assert resumed.tick == 3
    assert resumed.session_id == session_id
    assert resumed.graph is graph
    assert resumed.scenario_name == "wayne_county"

    # The resumed session's rng_seed round-tripped: advancing computes the
    # SAME replay-identity hash formula with seed=42, not the default 0.
    next_result = resumed.advance_tick()
    assert next_result.determinism_hash == session_module._replay_identity_hash(session_id, 4, 42)


def test_resume_campaign_tolerates_jsonb_read_back_as_a_string() -> None:
    """Defensive branch: some psycopg configurations hand JSONB columns back
    as an undecoded string rather than an auto-decoded dict — mirrors
    ``PostgresRuntime.hydrate_graph``'s own defensive ``isinstance`` guard
    on ``row["attributes"]``."""
    import json

    store = _FakeStore()
    session_id = uuid4()
    defines = GameDefines()
    sim_config = SimulationConfig(rng_seed=7)
    store.sessions[session_id] = {
        "id": session_id,
        "scenario": "wayne_county",
        "config_json": json.dumps(sim_config.model_dump(mode="json")),
        "game_defines_json": json.dumps(defines.model_dump(mode="json")),
        "rng_seed": 7,
    }
    graph = BabylonGraph()
    store._graphs[(session_id, 5)] = graph
    store._last_committed[session_id] = 5

    resumed = resume_campaign(store, session_id)

    assert resumed.tick == 5
    next_result = resumed.advance_tick()
    assert next_result.determinism_hash == session_module._replay_identity_hash(session_id, 6, 7)


def test_resume_campaign_raises_when_no_session_row() -> None:
    store = _FakeStore()
    with pytest.raises(ValueError, match="no game_session row"):
        resume_campaign(store, uuid4())


def test_resume_campaign_raises_when_no_committed_tick() -> None:
    store = _FakeStore()
    session_id = uuid4()
    store.sessions[session_id] = {
        "id": session_id,
        "scenario": "wayne_county",
        "config_json": SimulationConfig().model_dump(mode="json"),
        "game_defines_json": GameDefines().model_dump(mode="json"),
        "rng_seed": 0,
    }
    with pytest.raises(ValueError, match="no committed tick"):
        resume_campaign(store, session_id)


# --------------------------------------------------------------------------- #
# vault_page_source — reads REAL baked pages, honest None for absence.       #
# --------------------------------------------------------------------------- #


def test_vault_page_source_reads_real_files_and_returns_none_for_absent(
    tmp_path: Any,
) -> None:
    (tmp_path / "county").mkdir()
    (tmp_path / "county" / "26163.md").write_text("# county/26163 — Wayne\n")

    read_page = vault_page_source(tmp_path)

    assert read_page("county/26163") == "# county/26163 — Wayne\n"
    assert read_page("county/99999") is None


# --------------------------------------------------------------------------- #
# GameSession.read_page — the ``CampaignHandle.read_page`` seam (Unit C2).    #
# --------------------------------------------------------------------------- #


def test_read_page_wraps_the_injected_vault_page_source(tmp_path: Any) -> None:
    (tmp_path / "briefing").mkdir()
    (tmp_path / "briefing" / "abc.md").write_text("# briefing\n")
    store = _FakeStore()
    session = create_new_campaign(
        store, scenario=WayneCountyScenario(), pages=vault_page_source(tmp_path)
    )

    assert session.read_page("briefing/abc") == "# briefing\n"
    assert session.read_page("briefing/nonexistent") is None


def test_read_page_is_honestly_none_with_no_vault_wired() -> None:
    """``pages=None`` (the default) — never a fabricated page."""
    store = _FakeStore()
    session = create_new_campaign(store, scenario=WayneCountyScenario())
    assert session.read_page("county/26163") is None


# --------------------------------------------------------------------------- #
# open_runtime — loud refusal without a DSN, never a silent demo fallback.    #
# --------------------------------------------------------------------------- #


def test_open_runtime_raises_without_a_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BABYLON_PG_DSN", raising=False)
    monkeypatch.delenv("BABYLON_TEST_PG_DSN", raising=False)
    with pytest.raises(RuntimeError, match="No Postgres DSN"):
        open_runtime()
