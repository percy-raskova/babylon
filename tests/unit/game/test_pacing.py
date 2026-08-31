"""Unit tests for the paced tick driver (Program v1.0.0 Unit T4-core/C3).

Drives :class:`~babylon.game.pacing.PacedTickDriver` with a fake engine
callable (:class:`_FakeAdvancer`) — no real engine, Postgres, or WorldState
required — per the unit's own test mandate: pause/ack/lock semantics and
strict tick monotonicity.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import pytest

from babylon.game.pacing import (
    DriverBusyError,
    DriverLockedError,
    EndgameObserver,
    NoPendingAckError,
    PacedTickDriver,
    PausedAwaitingAckError,
    TickAdvancer,
    TickOrderError,
    TickOutcomeLike,
)
from babylon.models.enums.events import GameOutcome
from babylon.projection.chronicle import ChronicleEvent

pytestmark = [pytest.mark.unit]


@dataclass(frozen=True)
class _FakeOutcome:
    """A minimal ``TickOutcomeLike`` double — no real ``WorldState`` needed.

    ``world`` defaults to a ``SimpleNamespace(tick=...)`` mirroring this
    outcome's own tick (so :class:`_FakeEndgameObserver`'s ``new_state.tick``
    lookup works without a real ``WorldState``); pass an explicit ``world``
    to test identity/pass-through behavior instead.
    """

    tick: int
    paused: bool = False
    autosaved: bool = False
    world: Any = None
    events: tuple[Any, ...] = ()
    chronicle: tuple[ChronicleEvent, ...] = ()

    def __post_init__(self) -> None:
        if self.world is None:
            object.__setattr__(self, "world", SimpleNamespace(tick=self.tick))


class _FakeAdvancer:
    """The "fake engine callable" — a scripted ``TickAdvancer`` double."""

    def __init__(self, outcomes: list[_FakeOutcome]) -> None:
        self._outcomes = list(outcomes)
        self.call_count = 0

    def advance_tick(self) -> _FakeOutcome:
        self.call_count += 1
        if not self._outcomes:
            raise AssertionError("advance_tick() called past the scripted outcomes")
        return self._outcomes.pop(0)


@dataclass
class _FakeEndgameObserver:
    """A scripted ``EndgameObserver`` double: ``pattern_at_tick`` maps a
    tick number to the recognized pattern that tick should report (absent
    keys report ``None``)."""

    pattern_at_tick: dict[int, GameOutcome] = field(default_factory=dict)
    seen: list[tuple[Any, Any]] = field(default_factory=list)
    _current_tick: int = 0

    def on_tick(self, previous_state: Any, new_state: Any) -> None:
        self.seen.append((previous_state, new_state))
        self._current_tick = new_state.tick if hasattr(new_state, "tick") else new_state

    @property
    def recognized_pattern(self) -> GameOutcome | None:
        return self.pattern_at_tick.get(self._current_tick)


class _CountingSleep:
    """A ``sleep`` double that records every delay it was asked for, never
    actually waiting on wall-clock time."""

    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, delay: float) -> None:
        self.calls.append(delay)


# --------------------------------------------------------------------------- #
# Protocol seam conformance.                                                   #
# --------------------------------------------------------------------------- #


class TestSeams:
    def test_fake_outcome_satisfies_tick_outcome_like(self) -> None:
        assert isinstance(_FakeOutcome(tick=1), TickOutcomeLike)

    def test_fake_advancer_satisfies_tick_advancer(self) -> None:
        assert isinstance(_FakeAdvancer([]), TickAdvancer)

    def test_fake_endgame_observer_satisfies_endgame_observer(self) -> None:
        assert isinstance(_FakeEndgameObserver(), EndgameObserver)


# --------------------------------------------------------------------------- #
# Strict tick monotonicity.                                                    #
# --------------------------------------------------------------------------- #


class TestMonotonicity:
    def test_advance_once_accepts_the_expected_next_tick(self) -> None:
        driver = PacedTickDriver(_FakeAdvancer([_FakeOutcome(tick=1)]), starting_tick=0)
        result = driver.advance_once()
        assert result.tick == 1
        assert driver.last_tick == 1

    def test_advance_once_raises_on_a_skipped_tick(self) -> None:
        driver = PacedTickDriver(_FakeAdvancer([_FakeOutcome(tick=2)]), starting_tick=0)
        with pytest.raises(TickOrderError, match="expected tick 1"):
            driver.advance_once()

    def test_advance_once_raises_on_a_repeated_tick(self) -> None:
        advancer = _FakeAdvancer([_FakeOutcome(tick=1), _FakeOutcome(tick=1)])
        driver = PacedTickDriver(advancer, starting_tick=0)
        driver.advance_once()
        with pytest.raises(TickOrderError, match="expected tick 2"):
            driver.advance_once()

    def test_monotonicity_baseline_honors_a_resumed_starting_tick(self) -> None:
        """A driver wrapping a crash-resumed session at tick 37 must expect
        the very next tick to be 38 — never re-basing at 0."""
        driver = PacedTickDriver(_FakeAdvancer([_FakeOutcome(tick=38)]), starting_tick=37)
        result = driver.advance_once()
        assert result.tick == 38


# --------------------------------------------------------------------------- #
# Autopause-ack flow.                                                         #
# --------------------------------------------------------------------------- #


class TestAutopauseAck:
    def test_a_paused_tick_sets_awaiting_ack_and_a_summary(self) -> None:
        outcome = _FakeOutcome(tick=1, paused=True, events=(_Event("ENDGAME_REACHED"),))
        driver = PacedTickDriver(_FakeAdvancer([outcome]), starting_tick=0)

        driver.advance_once()

        assert driver.awaiting_ack is True
        assert driver.pending_pause is not None
        assert driver.pending_pause.tick == 1
        summary = driver.pause_summary
        assert summary is not None
        assert "ENDGAME_REACHED" in summary

    def test_further_advance_is_refused_while_awaiting_ack(self) -> None:
        advancer = _FakeAdvancer([_FakeOutcome(tick=1, paused=True), _FakeOutcome(tick=2)])
        driver = PacedTickDriver(advancer, starting_tick=0)
        driver.advance_once()

        with pytest.raises(PausedAwaitingAckError):
            driver.advance_once()
        assert advancer.call_count == 1  # the second tick was never even attempted

    def test_acknowledge_pause_clears_the_gate_and_permits_the_next_tick(self) -> None:
        advancer = _FakeAdvancer([_FakeOutcome(tick=1, paused=True), _FakeOutcome(tick=2)])
        driver = PacedTickDriver(advancer, starting_tick=0)
        driver.advance_once()

        driver.acknowledge_pause()
        assert driver.awaiting_ack is False
        assert driver.pending_pause is None

        result = driver.advance_once()
        assert result.tick == 2

    def test_acknowledge_pause_raises_when_nothing_is_pending(self) -> None:
        driver = PacedTickDriver(_FakeAdvancer([_FakeOutcome(tick=1)]), starting_tick=0)
        driver.advance_once()
        with pytest.raises(NoPendingAckError):
            driver.acknowledge_pause()

    def test_pause_summary_and_pending_pause_are_none_with_no_pause(self) -> None:
        driver = PacedTickDriver(_FakeAdvancer([_FakeOutcome(tick=1)]), starting_tick=0)
        driver.advance_once()
        assert driver.pending_pause is None
        assert driver.pause_summary is None


# --------------------------------------------------------------------------- #
# Autosave-cadence tracking (Unit T4-core/C6) — reads                         #
# TickAdvanceResult.autosaved, never re-derives is_checkpoint_tick here.      #
# --------------------------------------------------------------------------- #


class TestAutosaveTracking:
    def test_last_autosave_tick_is_none_before_any_checkpoint(self) -> None:
        driver = PacedTickDriver(
            _FakeAdvancer([_FakeOutcome(tick=1, autosaved=False)]), starting_tick=0
        )
        driver.advance_once()
        assert driver.last_autosave_tick is None

    def test_last_autosave_tick_updates_exactly_on_a_checkpoint_tick(self) -> None:
        advancer = _FakeAdvancer(
            [
                _FakeOutcome(tick=1, autosaved=False),
                _FakeOutcome(tick=2, autosaved=True),
                _FakeOutcome(tick=3, autosaved=False),
            ]
        )
        driver = PacedTickDriver(advancer, starting_tick=0)

        driver.advance_once()
        assert driver.last_autosave_tick is None

        driver.advance_once()
        assert driver.last_autosave_tick == 2

        # A later non-checkpoint tick does not clear the last observed one.
        driver.advance_once()
        assert driver.last_autosave_tick == 2

    def test_run_until_paused_tracks_the_last_checkpoint_across_a_whole_run(self) -> None:
        advancer = _FakeAdvancer(
            [
                _FakeOutcome(tick=1, autosaved=False),
                _FakeOutcome(tick=2, autosaved=True),
                _FakeOutcome(tick=3, paused=True, autosaved=False),
            ]
        )
        driver = PacedTickDriver(advancer, starting_tick=0)

        driver.run_until_paused()

        assert driver.last_autosave_tick == 2


@dataclass(frozen=True)
class _Event:
    """A minimal event double — only ``.type`` matters to :class:`PauseNotice`."""

    type: str


# --------------------------------------------------------------------------- #
# The endgame lock — permanent, overrides autopause-ack.                      #
# --------------------------------------------------------------------------- #


class TestEndgameLock:
    def test_a_recognized_pattern_locks_the_driver_permanently(self) -> None:
        observer = _FakeEndgameObserver(pattern_at_tick={2: GameOutcome.RED_OGV})
        advancer = _FakeAdvancer([_FakeOutcome(tick=1), _FakeOutcome(tick=2)])
        driver = PacedTickDriver(advancer, starting_tick=0, endgame_observer=observer)

        driver.advance_once()
        assert driver.locked is False

        driver.advance_once()
        assert driver.locked is True
        assert driver.lock_reason == GameOutcome.RED_OGV

    def test_further_advance_raises_once_locked_even_if_the_pattern_later_dissolves(
        self,
    ) -> None:
        """``EndgameDetector`` re-evaluates fresh every tick and CAN dissolve
        a pattern back to ``None`` — the driver's OWN latch must not."""
        observer = _FakeEndgameObserver(pattern_at_tick={1: GameOutcome.RED_OGV})
        advancer = _FakeAdvancer([_FakeOutcome(tick=1), _FakeOutcome(tick=2)])
        driver = PacedTickDriver(advancer, starting_tick=0, endgame_observer=observer)

        driver.advance_once()
        assert driver.locked is True

        # Even though tick 2 (were it ever attempted) would dissolve the
        # observer's own pattern back to None (absent from pattern_at_tick),
        # the driver must refuse BEFORE ever calling the advancer again.
        with pytest.raises(DriverLockedError):
            driver.advance_once()
        assert advancer.call_count == 1

    def test_lock_clears_any_pending_ack(self) -> None:
        """A tick that is BOTH critical-paused and endgame-recognized locks
        rather than leaving a dangling, now-moot ack requirement."""
        observer = _FakeEndgameObserver(pattern_at_tick={1: GameOutcome.FASCIST_CONSOLIDATION})
        outcome = _FakeOutcome(tick=1, paused=True)
        driver = PacedTickDriver(
            _FakeAdvancer([outcome]), starting_tick=0, endgame_observer=observer
        )

        driver.advance_once()

        assert driver.locked is True
        assert driver.awaiting_ack is False
        assert driver.pending_pause is None

    def test_acknowledge_pause_raises_locked_error_once_locked(self) -> None:
        observer = _FakeEndgameObserver(pattern_at_tick={1: GameOutcome.ECOLOGICAL_COLLAPSE})
        driver = PacedTickDriver(
            _FakeAdvancer([_FakeOutcome(tick=1)]), starting_tick=0, endgame_observer=observer
        )
        driver.advance_once()
        with pytest.raises(DriverLockedError):
            driver.acknowledge_pause()

    def test_no_endgame_observer_never_locks(self) -> None:
        """``endgame_observer=None`` (the default) — a valid no-lock config."""
        driver = PacedTickDriver(_FakeAdvancer([_FakeOutcome(tick=1)]), starting_tick=0)
        driver.advance_once()
        assert driver.locked is False
        assert driver.lock_reason is None

    def test_first_driven_tick_feeds_its_own_world_as_previous_state(self) -> None:
        """No prior world exists yet on the very first tick — the module
        docstring's documented substitution (previous_state is unused by
        every current axis evaluator)."""
        observer = _FakeEndgameObserver()
        driver = PacedTickDriver(
            _FakeAdvancer([_FakeOutcome(tick=1, world=object())]),
            starting_tick=0,
            endgame_observer=observer,
        )
        driver.advance_once()
        previous_seen, new_seen = observer.seen[0]
        assert previous_seen is new_seen


# --------------------------------------------------------------------------- #
# run_until_paused — bounded loop, presentation-only wall-clock delay.        #
# --------------------------------------------------------------------------- #


class _BlockingAdvancer:
    """A ``TickAdvancer`` double whose ``advance_tick`` blocks on a
    ``threading.Event`` until released — holds one call genuinely "in
    flight" on a background thread so a test can attempt a real, second,
    overlapping call from the main thread (the module docstring's
    Re-entrancy scenario, reproduced for real rather than asserted by
    inspection)."""

    def __init__(self, tick: int) -> None:
        self._tick = tick
        self.entered = threading.Event()
        self.release = threading.Event()
        self.call_count = 0

    def advance_tick(self) -> _FakeOutcome:
        self.call_count += 1
        self.entered.set()
        released = self.release.wait(timeout=5.0)
        assert released, "test never released the blocked advancer"
        return _FakeOutcome(tick=self._tick)


class TestBusyReentrancy:
    def test_busy_is_false_before_and_after_a_call(self) -> None:
        driver = PacedTickDriver(_FakeAdvancer([_FakeOutcome(tick=1)]), starting_tick=0)
        assert driver.busy is False
        driver.advance_once()
        assert driver.busy is False

    def test_an_overlapping_advance_once_from_another_thread_raises_driver_busy_error(
        self,
    ) -> None:
        advancer = _BlockingAdvancer(tick=1)
        driver = PacedTickDriver(advancer, starting_tick=0)

        worker = threading.Thread(target=driver.advance_once)
        worker.start()
        try:
            assert advancer.entered.wait(timeout=5.0), "background advance never started"
            assert driver.busy is True
            with pytest.raises(DriverBusyError):
                driver.advance_once()
        finally:
            advancer.release.set()
            worker.join(timeout=5.0)

        assert driver.busy is False
        # The racing call never reached the wrapped advancer at all — it
        # was refused BEFORE ever touching driver/advancer state.
        assert advancer.call_count == 1

    def test_run_until_paused_also_raises_driver_busy_error_while_another_call_is_in_flight(
        self,
    ) -> None:
        advancer = _BlockingAdvancer(tick=1)
        driver = PacedTickDriver(advancer, starting_tick=0)

        worker = threading.Thread(target=driver.advance_once)
        worker.start()
        try:
            assert advancer.entered.wait(timeout=5.0)
            with pytest.raises(DriverBusyError):
                driver.run_until_paused()
        finally:
            advancer.release.set()
            worker.join(timeout=5.0)


class TestRunUntilPaused:
    def test_runs_until_the_first_paused_tick_inclusive(self) -> None:
        advancer = _FakeAdvancer(
            [
                _FakeOutcome(tick=1),
                _FakeOutcome(tick=2),
                _FakeOutcome(tick=3, paused=True),
                _FakeOutcome(tick=4),
            ]
        )
        driver = PacedTickDriver(advancer, starting_tick=0)

        results = driver.run_until_paused()

        assert [r.tick for r in results] == [1, 2, 3]
        assert driver.awaiting_ack is True
        assert advancer.call_count == 3  # tick 4 never attempted

    def test_runs_until_the_endgame_lock_engages(self) -> None:
        observer = _FakeEndgameObserver(pattern_at_tick={2: GameOutcome.FRAGMENTED_COLLAPSE})
        advancer = _FakeAdvancer([_FakeOutcome(tick=1), _FakeOutcome(tick=2), _FakeOutcome(tick=3)])
        driver = PacedTickDriver(advancer, starting_tick=0, endgame_observer=observer)

        results = driver.run_until_paused()

        assert [r.tick for r in results] == [1, 2]
        assert driver.locked is True
        assert advancer.call_count == 2

    def test_respects_the_max_ticks_bound_even_with_no_pause_or_lock(self) -> None:
        advancer = _FakeAdvancer([_FakeOutcome(tick=t) for t in range(1, 11)])
        driver = PacedTickDriver(advancer, starting_tick=0)

        results = driver.run_until_paused(max_ticks=3)

        assert [r.tick for r in results] == [1, 2, 3]
        assert advancer.call_count == 3

    def test_run_until_paused_raises_immediately_if_already_locked(self) -> None:
        observer = _FakeEndgameObserver(pattern_at_tick={1: GameOutcome.RED_OGV})
        advancer = _FakeAdvancer([_FakeOutcome(tick=1), _FakeOutcome(tick=2)])
        driver = PacedTickDriver(advancer, starting_tick=0, endgame_observer=observer)
        driver.advance_once()

        with pytest.raises(DriverLockedError):
            driver.run_until_paused()
        assert advancer.call_count == 1

    def test_tick_delay_sleeps_between_ticks_but_not_after_the_stopping_tick(self) -> None:
        sleeper = _CountingSleep()
        advancer = _FakeAdvancer(
            [_FakeOutcome(tick=1), _FakeOutcome(tick=2), _FakeOutcome(tick=3, paused=True)]
        )
        driver = PacedTickDriver(advancer, starting_tick=0, tick_delay=0.5, sleep=sleeper)

        driver.run_until_paused()

        # Two continuing ticks (1 -> 2, 2 -> 3) sleep; the stopping tick (3,
        # paused) does not sleep again afterward.
        assert sleeper.calls == [0.5, 0.5]

    def test_zero_tick_delay_never_sleeps(self) -> None:
        sleeper = _CountingSleep()
        advancer = _FakeAdvancer([_FakeOutcome(tick=1), _FakeOutcome(tick=2, paused=True)])
        driver = PacedTickDriver(advancer, starting_tick=0, tick_delay=0.0, sleep=sleeper)

        driver.run_until_paused()

        assert sleeper.calls == []
