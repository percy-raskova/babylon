"""Spec-116 Task 4: wire the fixed-horizon bridge (resolve_tick + objectives).

Program 17 / Item 1c wired a REAL, per-session-cached EndgameDetector into
``resolve_tick`` (Task 3: pattern *recognition*, never adjudication). Task 4
finishes the wiring:

- Recognizing a pattern no longer ends the game — the fixed century horizon
  does (``defines.endgame.campaign_horizon_years * defines.timescale.weeks_per_year``).
- A ``PATTERN_SHIFT`` event fires exactly when the recognized pattern
  changes (including dissolving to ``None``).
- ``snapshot["endgame_progress"]`` is served every tick (the live "how
  close" HUD); ``snapshot["endgame"]`` only appears once the horizon is
  reached, with ``outcome`` = the recognized pattern or ``"unresolved"``.
- ``get_journal_objectives`` reads its 5 progress values from the same
  persisted ``endgame_progress["axes"]`` block (not the in-process detector
  cache), so it survives a worker restart.

All tests drive the REAL ``EndgameDetector`` through ``resolve_tick`` with a
``MagicMock`` persistence layer (no Postgres needed) — genuine RED against
pre-Task-4 code (no ``endgame_progress`` key, no PATTERN_SHIFT event, game
ending the moment a pattern was recognized).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.entities.territory import Territory
from babylon.models.enums import SectorType, SocialRole
from babylon.models.world_state import WorldState
from game.engine_bridge import EngineBridge

pytestmark = pytest.mark.unit

_SESSION = UUID("bbbbbbbb-cccc-dddd-eeee-ffffffffffff")


@pytest.fixture(autouse=True)
def _clear_endgame_detector_cache() -> Any:
    """``_session_endgame_detectors`` is a module-level, per-process cache
    keyed by session_id (required so cross-tick counters survive separate
    ``resolve_tick`` calls — see engine_bridge.py). Every test in this file
    reuses the same ``_SESSION`` UUID, so without clearing the cache a
    detector state from one test would leak into the next."""
    from game.engine_bridge import _session_endgame_detectors

    _session_endgame_detectors.clear()
    yield
    _session_endgame_detectors.clear()


def _make_mock_persistence(endgame_overrides: dict[str, Any] | None = None) -> MagicMock:
    mock = MagicMock()
    mock.get_metadata.return_value = None
    endgame_defines: dict[str, Any] = {
        # EndgameDefines.ecological_overshoot_threshold is gt=0.0 (a literal
        # 0.0 fails Pydantic validation) — 0.5 sits well below the overshoot
        # fixture's ratio (2.0) and well above the healthy fixture's (0.0001).
        "ecological_overshoot_threshold": 0.5,
        "ecological_sustained_ticks": 2,
    }
    if endgame_overrides:
        endgame_defines.update(endgame_overrides)
    mock.get_session.return_value = {"game_defines_json": {"endgame": endgame_defines}}
    mock.get_pending_turns.return_value = []
    mock.mark_turns_resolved.return_value = 0
    mock.persist_tick.return_value = None
    return mock


def _overshoot_state(tick: int) -> WorldState:
    """A minimal WorldState whose consumption permanently exceeds
    biocapacity (overshoot_ratio == 2.0), so with
    ``ecological_overshoot_threshold=0.5`` every tick counts toward the
    sustained-overshoot window regardless of tick number."""
    entity = SocialClass(
        id="C001",
        name="Workers",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        s_bio=1.0,
        s_class=1.0,
        # Spec-116: fascist_consolidation gates on a FRACTION of
        # ideology-bearing nodes, not an absolute count — IdeologicalProfile's
        # own defaults (national_identity=0.5 > class_consciousness=0.0) would
        # make this single-entity fixture spuriously read as 100% fascist.
        # Pin an explicitly non-fascist profile so this fixture only probes
        # the ecological_collapse axis it's named for.
        ideology=IdeologicalProfile(national_identity=0.1, class_consciousness=0.5),
    )
    territory = Territory(
        id="T001",
        name="Zone",
        sector_type=SectorType.RESIDENTIAL,
        biocapacity=1.0,
        max_biocapacity=1.0,
    )
    return WorldState(tick=tick, entities={"C001": entity}, territories={"T001": territory})


def _healthy_state(tick: int) -> WorldState:
    """A perfectly healthy state: biocapacity comfortably exceeds
    consumption, and ideology is pinned non-fascist — no axis ever matches."""
    entity = SocialClass(
        id="C001",
        name="Workers",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        s_bio=0.01,
        s_class=0.0,
        ideology=IdeologicalProfile(national_identity=0.1, class_consciousness=0.5),
    )
    territory = Territory(
        id="T001",
        name="Zone",
        sector_type=SectorType.RESIDENTIAL,
        biocapacity=100.0,
        max_biocapacity=100.0,
    )
    return WorldState(tick=tick, entities={"C001": entity}, territories={"T001": territory})


def _fascist_state(tick: int) -> WorldState:
    """A single-entity WorldState whose lone ideology-bearing node has
    national_identity > class_consciousness — fascist_fraction = 1/1 = 1.0,
    comfortably clearing the default 0.9 fascist_majority_fraction (spec-116
    Task 6 calibration, was 0.75), so the FASCIST_CONSOLIDATION axis matches
    every tick this state is held. Biocapacity is generous so
    ecological_collapse never also fires."""
    entity = SocialClass(
        id="C001",
        name="Workers",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        s_bio=0.01,
        s_class=0.0,
        ideology=IdeologicalProfile(national_identity=0.9, class_consciousness=0.1),
    )
    territory = Territory(
        id="T001",
        name="Zone",
        sector_type=SectorType.RESIDENTIAL,
        biocapacity=100.0,
        max_biocapacity=100.0,
    )
    return WorldState(tick=tick, entities={"C001": entity}, territories={"T001": territory})


def _wire_fake_engine(
    bridge: EngineBridge, monkeypatch: pytest.MonkeyPatch, state_fn: Any
) -> dict[str, WorldState]:
    """Wire ``hydrate_state``/``step`` so consecutive ``resolve_tick`` calls
    replay ``state_fn(tick)`` exactly like a real hydrate->step->persist
    loop. Returns the mutable ``current_state`` box so callers can inspect
    or override it between calls."""
    current_state: dict[str, WorldState] = {"state": state_fn(0)}

    def fake_hydrate_state(session_id: UUID) -> tuple[WorldState, Any]:
        return current_state["state"], MagicMock()

    def fake_step(state: WorldState, *_args: Any, **_kwargs: Any) -> WorldState:
        new_state = state_fn(state.tick + 1)
        current_state["state"] = new_state
        return new_state

    monkeypatch.setattr(bridge, "hydrate_state", fake_hydrate_state)
    monkeypatch.setattr("game.engine_bridge.step", fake_step)
    return current_state


class TestRecognitionNeverEndsTheGame:
    """Spec-116 owner ruling 2026-07-17: recognizing a pattern is a HUD
    signal, never a terminator — only the fixed century horizon ends
    the game (see TestFixedHorizonGameOver below)."""

    def test_recognition_does_not_end_game(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        _wire_fake_engine(bridge, monkeypatch, _fascist_state)

        snapshot = bridge.resolve_tick(_SESSION)

        assert "endgame" not in snapshot
        assert snapshot["endgame_progress"]["pattern"] == "fascist_consolidation"

    def test_sustained_ecological_overshoot_recognized_but_no_endgame(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FOLLOW-PATTERN sibling of the fascist case above, using the
        pre-existing sustained-overshoot fixture: recognition after 2
        consecutive overshoot ticks (ecological_sustained_ticks=2) never
        populates snapshot['endgame'] — only the horizon does."""
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        _wire_fake_engine(bridge, monkeypatch, _overshoot_state)

        result_1 = bridge.resolve_tick(_SESSION)
        assert "endgame" not in result_1
        assert result_1["endgame_progress"]["pattern"] is None  # only 1 tick so far

        result_2 = bridge.resolve_tick(_SESSION)
        assert "endgame" not in result_2
        assert result_2["endgame_progress"]["pattern"] == "ecological_collapse"

    def test_no_endgame_stays_absent_when_conditions_never_hold(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A perfectly healthy state must never populate snapshot['endgame']
        nor recognize any pattern."""
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        _wire_fake_engine(bridge, monkeypatch, _healthy_state)

        result = bridge.resolve_tick(_SESSION)

        assert "endgame" not in result
        assert result["endgame_progress"]["pattern"] is None


class TestPatternShiftEvent:
    """A PATTERN_SHIFT event fires exactly on a recognized-pattern change."""

    def test_pattern_shift_event_fires_exactly_on_change(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        _wire_fake_engine(bridge, monkeypatch, _fascist_state)

        # Tick of recognition (None -> fascist_consolidation): one PATTERN_SHIFT.
        snapshot_1 = bridge.resolve_tick(_SESSION)
        shifts_1 = [e for e in snapshot_1["events"] if e.get("type") == "pattern_shift"]
        assert len(shifts_1) == 1
        assert shifts_1[0]["data"]["pattern"] == "fascist_consolidation"
        assert shifts_1[0]["data"]["previous"] is None

        # Next tick, same pattern held: no PATTERN_SHIFT.
        snapshot_2 = bridge.resolve_tick(_SESSION)
        shifts_2 = [e for e in snapshot_2["events"] if e.get("type") == "pattern_shift"]
        assert len(shifts_2) == 0

    def test_pattern_shift_fires_on_dissolution_to_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The pattern dissolving back to None is itself a shift."""
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        current_state = _wire_fake_engine(bridge, monkeypatch, _fascist_state)

        bridge.resolve_tick(_SESSION)  # recognizes fascist_consolidation

        # Force the NEXT step() to return a healthy (non-fascist) state.
        def fake_step_dissolve(state: WorldState, *_a: Any, **_kw: Any) -> WorldState:
            new_state = _healthy_state(state.tick + 1)
            current_state["state"] = new_state
            return new_state

        monkeypatch.setattr("game.engine_bridge.step", fake_step_dissolve)

        snapshot = bridge.resolve_tick(_SESSION)
        shifts = [e for e in snapshot["events"] if e.get("type") == "pattern_shift"]
        assert len(shifts) == 1
        assert shifts[0]["data"]["pattern"] is None
        assert shifts[0]["data"]["previous"] == "fascist_consolidation"
        assert snapshot["endgame_progress"]["pattern"] is None


class TestFixedHorizonGameOver:
    """Game over iff tick >= horizon_tick; outcome = pattern or 'unresolved'."""

    def test_horizon_ends_game_unresolved(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # campaign_horizon_years=1 * default weeks_per_year=52 => horizon 52.
        mock_persistence = _make_mock_persistence({"campaign_horizon_years": 1})
        bridge = EngineBridge(mock_persistence)

        def jump_to_horizon(tick: int) -> WorldState:
            return _healthy_state(52 if tick else 0)

        _wire_fake_engine(bridge, monkeypatch, jump_to_horizon)

        snapshot = bridge.resolve_tick(_SESSION)

        assert snapshot["endgame"]["outcome"] == "unresolved"
        assert snapshot["endgame"]["tick"] == 52
        assert snapshot["endgame_progress"]["horizon_tick"] == 52

    def test_horizon_ends_game_with_recognized_pattern(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When a pattern IS held at the horizon tick, outcome is that
        pattern's value, not 'unresolved'."""
        mock_persistence = _make_mock_persistence({"campaign_horizon_years": 1})
        bridge = EngineBridge(mock_persistence)

        def jump_to_horizon(tick: int) -> WorldState:
            return _fascist_state(52 if tick else 0)

        _wire_fake_engine(bridge, monkeypatch, jump_to_horizon)

        snapshot = bridge.resolve_tick(_SESSION)

        assert snapshot["endgame"]["outcome"] == "fascist_consolidation"
        assert snapshot["endgame"]["tick"] == 52

    def test_below_horizon_never_populates_endgame(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_persistence = _make_mock_persistence({"campaign_horizon_years": 1})
        bridge = EngineBridge(mock_persistence)
        _wire_fake_engine(bridge, monkeypatch, _healthy_state)

        snapshot = bridge.resolve_tick(_SESSION)  # tick 1, horizon 52

        assert "endgame" not in snapshot


class TestEndgameProgressEveryTick:
    """endgame_progress is served on every tick, with the lock computed from
    (tick - since_tick + 1) >= pattern_lock_ticks."""

    def test_endgame_progress_present_every_tick(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        _wire_fake_engine(bridge, monkeypatch, _healthy_state)

        snapshot = bridge.resolve_tick(_SESSION)

        progress = snapshot["endgame_progress"]
        assert set(progress["axes"].keys()) == {
            "revolutionary_victory",
            "ecological_collapse",
            "fascist_consolidation",
            "red_ogv",
            "fragmented_collapse",
        }
        assert progress["pattern"] is None
        assert progress["since_tick"] is None
        assert progress["locked"] is False
        assert progress["horizon_tick"] == 5200  # 100 years * 52 weeks (defaults)

    def test_endgame_progress_every_tick_with_lock(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_persistence = _make_mock_persistence({"pattern_lock_ticks": 2})
        bridge = EngineBridge(mock_persistence)
        _wire_fake_engine(bridge, monkeypatch, _fascist_state)

        # Tick 1: pattern just recognized (since_tick=1) — (1-1+1)=1 < 2.
        snapshot_1 = bridge.resolve_tick(_SESSION)
        assert snapshot_1["endgame_progress"]["pattern"] == "fascist_consolidation"
        assert snapshot_1["endgame_progress"]["locked"] is False

        # Tick 2: pattern held a 2nd tick — (2-1+1)=2 >= 2 -> locked.
        snapshot_2 = bridge.resolve_tick(_SESSION)
        assert snapshot_2["endgame_progress"]["locked"] is True


class TestObjectivesReadSnapshotProgress:
    """get_journal_objectives progress = the persisted endgame_progress.axes
    from the latest snapshot — not the in-process detector cache."""

    def test_objectives_read_snapshot_progress(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_persistence = _make_mock_persistence()
        # Simulate real persist_tick/hydrate_graph round-tripping the graph
        # (with its stashed endgame_progress attr) through the mock.
        captured: dict[str, Any] = {}

        def fake_persist_tick(*, tick: int, graph: Any, events: Any, session_id: UUID) -> None:
            captured["graph"] = graph

        mock_persistence.persist_tick.side_effect = fake_persist_tick
        mock_persistence.hydrate_graph.side_effect = lambda *_a, **_kw: captured["graph"]

        bridge = EngineBridge(mock_persistence)
        _wire_fake_engine(bridge, monkeypatch, _fascist_state)

        snapshot = bridge.resolve_tick(_SESSION)
        objectives = bridge.get_journal_objectives(_SESSION)

        axes = snapshot["endgame_progress"]["axes"]
        progress_by_id = {o["id"]: o["progress"] for o in objectives["objectives"]}

        assert progress_by_id["revolution"] == axes["revolutionary_victory"]
        assert progress_by_id["ecological_collapse"] == axes["ecological_collapse"]
        assert progress_by_id["fascist_consolidation"] == axes["fascist_consolidation"]
        assert progress_by_id["red_ogv"] == axes["red_ogv"]
        assert progress_by_id["fragmented_collapse"] == axes["fragmented_collapse"]
        # The fascist axis is actually recognized (progress == 1.0), so this
        # is a real assertion, not a 0.0 == 0.0 vacuity.
        assert progress_by_id["fascist_consolidation"] == 1.0

    def test_objectives_honest_zero_with_no_snapshot_yet(self) -> None:
        """No resolve_tick has ever run for this session — hydrate_graph
        returns a graph with no endgame_progress attr. Progress is an
        honest 0.0 for every axis (Constitution III.11: never fabricated)."""
        mock_persistence = _make_mock_persistence()
        empty_graph = MagicMock()
        empty_graph.graph = {"tick": 0}
        mock_persistence.hydrate_graph.return_value = empty_graph
        bridge = EngineBridge(mock_persistence)

        objectives = bridge.get_journal_objectives(_SESSION)

        assert all(o["progress"] == 0.0 for o in objectives["objectives"])
        # No endgame has fired, so every objective stays active — the
        # documented 3-value status contract (specs/095-endgame-chronicle/
        # contracts/objectives.yaml) is unaffected by the missing snapshot.
        assert all(o["status"] == "active" for o in objectives["objectives"])


class TestGetSnapshotServesEndgameProgress:
    """Task 5 Concern 2 (task-5-report.md): resolve_tick's own response
    snapshot has carried ``endgame_progress`` since Task 4, but nothing in
    the frontend ever reads that channel (``timeSlice.resolveOnce`` discards
    the resolve-tick body) — the real UI hydrates from ``GET /state/``, i.e.
    ``EngineBridge.get_snapshot`` -> ``_state_to_snapshot``. That path must
    read the same persisted ``endgame_progress`` graph attr
    ``get_journal_objectives`` already reads, FOLLOW-PATTERN
    ``TestObjectivesReadSnapshotProgress`` above."""

    def test_get_snapshot_reads_persisted_endgame_progress(self) -> None:
        """``get_snapshot`` -> ``hydrate_state`` -> ``WorldState.from_graph``
        needs a REAL ``BabylonGraph`` (unlike ``accept_outcome``/
        ``get_journal_objectives``, which read ``_persistence.hydrate_graph``
        straight off without ever reconstructing a WorldState) — so this
        stashes the endgame_progress attr directly on a real graph via
        ``set_graph_attr``, exactly as ``resolve_tick`` itself does."""
        endgame_progress = {
            "axes": {
                "revolutionary_victory": 0.0,
                "ecological_collapse": 0.0,
                "fascist_consolidation": 1.0,
                "red_ogv": 0.0,
                "fragmented_collapse": 0.0,
            },
            "pattern": "fascist_consolidation",
            "since_tick": 2,
            "horizon_tick": 5200,
            "locked": True,
        }
        graph = _fascist_state(3).to_graph()
        graph.set_graph_attr("endgame_progress", endgame_progress)
        mock_persistence = _make_mock_persistence()
        mock_persistence.hydrate_graph.return_value = graph
        bridge = EngineBridge(mock_persistence)

        snapshot = bridge.get_snapshot(_SESSION)

        assert snapshot["endgame_progress"] == endgame_progress
        assert snapshot["endgame_progress"]["pattern"] == "fascist_consolidation"
        assert snapshot["endgame_progress"]["locked"] is True

    def test_get_snapshot_omits_endgame_progress_when_none_persisted_yet(self) -> None:
        """No resolve_tick has ever run for this session — the hydrated
        graph carries no endgame_progress attr. Honest absence: the key is
        missing entirely (mirrors the pre-existing ``traps`` optional-block
        contract in ``_state_to_snapshot`` — ``if traps_dict is not None:
        snapshot["traps"] = traps_dict`` — never a fabricated all-zero
        block; Constitution III.11)."""
        mock_persistence = _make_mock_persistence()
        seeded_graph = _healthy_state(0).to_graph()
        mock_persistence.hydrate_graph.return_value = seeded_graph
        bridge = EngineBridge(mock_persistence)

        snapshot = bridge.get_snapshot(_SESSION)

        assert "endgame_progress" not in snapshot


class TestForceEndgameTestHook:
    """G7-crisis (spec-116 first-session e2e crisis leg): ``resolve_tick``'s
    ``force_endgame_test_hook`` parameter lets an e2e-only caller end the
    game through the exact same real ``EndgameEvent`` construction a
    genuine horizon termination uses, years before the fixed century
    horizon — the frontend's autopause/critical-event machinery fires ONLY
    on ``endgame_reached`` (spec-116 FR-116-2's salience re-tier), so this
    is the only way to exercise it deterministically inside a short e2e
    window. Inert unless BOTH the kwarg is True *and* the server process has
    ``BABYLON_E2E_TEST_HOOKS=1`` exported (``_e2e_test_hooks_enabled``) —
    either alone is a no-op, so neither a stray kwarg nor a leaked env var
    can fire this alone in production."""

    def test_force_hook_ends_game_far_below_horizon_when_env_enabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("BABYLON_E2E_TEST_HOOKS", "1")
        mock_persistence = _make_mock_persistence()  # default horizon: 5200
        bridge = EngineBridge(mock_persistence)
        _wire_fake_engine(bridge, monkeypatch, _healthy_state)

        snapshot = bridge.resolve_tick(_SESSION, force_endgame_test_hook=True)

        assert snapshot["endgame"]["outcome"] == "unresolved"
        assert snapshot["endgame"]["tick"] == 1
        endgame_events = [e for e in snapshot["events"] if e.get("type") == "endgame_reached"]
        assert len(endgame_events) == 1

    def test_force_hook_reports_a_recognized_pattern_as_the_outcome(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FOLLOW-PATTERN sibling of
        ``test_horizon_ends_game_with_recognized_pattern`` — the forced
        endgame's outcome is still the currently-recognized pattern, not
        always ``unresolved``, matching real horizon-termination semantics
        exactly (this hook only moves *when* the check fires, never *how*
        the outcome is computed)."""
        monkeypatch.setenv("BABYLON_E2E_TEST_HOOKS", "1")
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        _wire_fake_engine(bridge, monkeypatch, _fascist_state)

        snapshot = bridge.resolve_tick(_SESSION, force_endgame_test_hook=True)

        assert snapshot["endgame"]["outcome"] == "fascist_consolidation"

    def test_force_hook_is_inert_without_the_kwarg(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The env var alone (server opted in) never fires this — a caller
        must also explicitly ask via the kwarg."""
        monkeypatch.setenv("BABYLON_E2E_TEST_HOOKS", "1")
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        _wire_fake_engine(bridge, monkeypatch, _healthy_state)

        snapshot = bridge.resolve_tick(_SESSION)  # force_endgame_test_hook defaults False

        assert "endgame" not in snapshot

    def test_force_hook_is_inert_without_the_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The kwarg alone (a request header some caller sent) never fires
        this — the server process must also have explicitly opted in. This
        is what makes the hook inert in production: the header can only
        ever come from an e2e page, but even a stray/forged one is a no-op
        against a server that never exported the env var."""
        monkeypatch.delenv("BABYLON_E2E_TEST_HOOKS", raising=False)
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)
        _wire_fake_engine(bridge, monkeypatch, _healthy_state)

        snapshot = bridge.resolve_tick(_SESSION, force_endgame_test_hook=True)

        assert "endgame" not in snapshot
