"""The campaign's pacing policy (Program v1.0.0, Unit T4-core/C3).

Layers verb windows, run-until-paused auto-play, an autopause-ack flow, and
a permanent endgame lock on top of ONE :class:`TickAdvancer` — in
production a real :class:`~babylon.game.session.GameSession` (Unit C1),
driven exactly as Unit C2's own ``t`` binding already drives it
(:meth:`~babylon.game.session.GameSession.advance_tick`, unchanged). This
module adds no new way to resolve a tick; it adds a POLICY for WHEN to call
the one that already exists.

Per the adversarial finding this unit answers (program plan, master doc,
"the pacing loop is a BUILD"): ``AsyncSimulationRunner``
(``engine/runner.py``) wraps the wrong facade (the pre-Program-24
``Simulation``, not :class:`~babylon.engine.simulation_engine.
SimulationEngine`) and has zero production callers — this module does not
reuse or extend it.

**What is reused, not rebuilt** (DRY): the pause-predicate SEAM the program
plan's DEFERRED note asks for is :data:`~babylon.game.session.
PausePredicate` — already built in Unit C1, already injected into
:class:`~babylon.game.session.GameSession`, already defaulting to
:func:`~babylon.game.session.default_pause_predicate` (the EXISTING
``chronicle_salience`` ``EVENT_SEVERITY`` critical tier). This module does
NOT carry a second copy of that seam: it only reacts to the
:attr:`~babylon.game.session.TickAdvanceResult.paused` bit the session
already computed. When T1.1's derived-severity catalog lands, the ONE
place that changes is whatever ``pause_predicate=`` the composition root
hands to :func:`~babylon.game.session.create_new_campaign` /
:func:`~babylon.game.session.resume_campaign` — nothing here.

Unit C6 adds the SAME pattern for the autosave cadence:
:attr:`~babylon.game.session.TickAdvanceResult.autosaved` (``session.py``'s
own reuse of :func:`~babylon.persistence.delta.is_checkpoint_tick`) is
read, never re-derived — this module does not import
``babylon.persistence`` at all. :attr:`PacedTickDriver.last_autosave_tick`
tracks the most recent checkpoint tick this driver has itself observed, a
convenience for a status line ("last autosaved: tick N") that would
otherwise have to re-inspect every past result itself.

**What this module owns instead** — two invariants the wrapped advancer
does NOT itself enforce:

1. **Strict tick monotonicity.** :class:`PacedTickDriver` tracks its own
   last-observed tick and raises :class:`TickOrderError` the instant the
   wrapped advancer returns anything other than ``last_tick + 1`` — a
   skip, a repeat, or a regression. The driver "NEVER reorders or drops
   ticks" (program plan, determinism law) is enforced HERE, not merely
   assumed of the advancer.
2. **The endgame lock is permanent.** :class:`~babylon.engine.observers.
   endgame_detector.EndgameDetector` re-evaluates its five axes fresh every
   tick and its own ``recognized_pattern`` CAN dissolve back to ``None``
   (that is correct behavior for the detector — a recognizer, not a
   latch). The driver's OWN :attr:`~PacedTickDriver.locked` is a real
   latch: once any :class:`~babylon.models.enums.events.GameOutcome` is
   ever recognized, :attr:`~PacedTickDriver.locked` stays ``True`` forever
   after, regardless of what the detector reports on a later tick.

The autopause-ack flow is a separate, weaker gate layered on top of the
reused pause-predicate bit: a paused tick sets :attr:`~PacedTickDriver.
awaiting_ack`, which blocks every further advance until an explicit
:meth:`~PacedTickDriver.acknowledge_pause` call clears it — never
automatically on the next tick.

**Per-tick verb windows** need no new mechanism: :meth:`~babylon.game.
session.GameSession.submit_verb` already queues a turn for
``tick + 1`` and :meth:`~babylon.game.session.GameSession.advance_tick`
already reads ``get_pending_turns`` fresh each call — the "window" IS the
gap between two driver-issued ``advance_tick`` calls. In explicit-advance
mode that gap is as long as the player takes between key presses; in
:meth:`PacedTickDriver.run_until_paused` mode, :attr:`PacedTickDriver.
tick_delay` (wall-clock only, injected via :attr:`PacedTickDriver.sleep`
for tests — never consulted by ``run_tick`` itself) gives the SAME window
even while auto-play skips ahead through uneventful ticks.

Determinism: `EndgameDetector.on_tick(previous_state, new_state)`'s
``previous_state`` parameter is, as of this writing, entirely unused by
every one of its five axis evaluators (verified by inspection of
``engine/observers/endgame_detector.py`` — the parameter itself carries a
``# noqa: ARG002``); this module passes the freshly-resolved tick's own
world for BOTH arguments on the very first driven tick (there being no
prior world yet) rather than inventing a placeholder, and documents the
substitution here so a future change that starts consuming
``previous_state`` is not silently fed a wrong value without a maintainer
noticing this comment first.

**Re-entrancy** (Textual-worker hazard, verified against the installed
8.2.8 source and recorded in this program's own ``TEXTUAL_MANUAL.md``, Part
I §9.4/§9.5): the intended caller wraps :meth:`PacedTickDriver.
run_until_paused` in a Textual ``@work`` coroutine that ``await``\\ s
``asyncio.to_thread(...)`` so the UI stays responsive — but cancelling that
coroutine (e.g. an ``exclusive`` worker group, or a second key-press before
the first run finishes) is **cooperative-only**: it abandons the ``await``,
it does NOT stop the executor thread actually running underneath, which
keeps mutating this driver's state regardless. Two overlapping calls into
one :class:`PacedTickDriver` would race on :attr:`~PacedTickDriver.
last_tick`/:attr:`~PacedTickDriver.locked` with no lock between them — a
real determinism hazard, not a hypothetical one. :attr:`~PacedTickDriver.
busy` and the :class:`DriverBusyError` guard below exist specifically for
this: :meth:`~PacedTickDriver.advance_once` and :meth:`~PacedTickDriver.
run_until_paused` refuse loudly rather than interleaving two advances.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Final, Protocol, runtime_checkable

from babylon.engine.observers.endgame_detector import EndgameDetector
from babylon.kernel.event_bus import Event
from babylon.models.enums.events import GameOutcome
from babylon.models.world_state import WorldState
from babylon.tui.chronicle import ChronicleEvent

if TYPE_CHECKING:
    from babylon.game.session import GameSession

__all__ = [
    "DriverBusyError",
    "DriverLockedError",
    "EndgameObserver",
    "NoPendingAckError",
    "PacedTickDriver",
    "PacingError",
    "PauseNotice",
    "PausedAwaitingAckError",
    "TickAdvancer",
    "TickOrderError",
    "TickOutcomeLike",
    "paced_driver_for_session",
]


@runtime_checkable
class TickOutcomeLike(Protocol):
    """Structural shape of one resolved tick.

    :class:`~babylon.game.session.TickAdvanceResult` satisfies this
    without a hard import — the WO-37 trick, one layer up from
    :mod:`babylon.game.session`'s own use of it: this module's own tests
    drive :class:`PacedTickDriver` with a minimal "fake engine callable"
    double, no engine/persistence machinery required.
    """

    @property
    def tick(self) -> int:
        """The committed tick number."""
        ...

    @property
    def paused(self) -> bool:
        """The wrapped advancer's OWN pause-predicate verdict for this tick."""
        ...

    @property
    def autosaved(self) -> bool:
        """The wrapped advancer's OWN checkpoint-cadence verdict for this
        tick (Unit C6 — :attr:`~babylon.game.session.TickAdvanceResult.
        autosaved`, ``is_checkpoint_tick`` reused, never re-derived here)."""
        ...

    @property
    def world(self) -> WorldState:
        """The post-tick :class:`~babylon.models.world_state.WorldState`."""
        ...

    @property
    def events(self) -> tuple[Event, ...]:
        """This tick's raw event-bus history (chronological)."""
        ...

    @property
    def chronicle(self) -> tuple[ChronicleEvent, ...]:
        """This tick's chronicle events, chronological (Program 24 P3) — the seam
        :meth:`~babylon.tui.app.ArchiveApp._refresh_chronicle` reads through
        :class:`~babylon.tui.app.PacedDriverHandle`'s own widened
        :class:`~babylon.tui.app.TickOutcome`."""
        ...


@runtime_checkable
class TickAdvancer(Protocol):
    """Structural seam: anything that can resolve exactly one further tick.

    :class:`~babylon.game.session.GameSession` satisfies this structurally
    (its :meth:`~babylon.game.session.GameSession.advance_tick` already has
    this exact shape) without this module importing that class at runtime.
    """

    def advance_tick(self) -> TickOutcomeLike:
        """Resolve exactly one further tick."""
        ...


@runtime_checkable
class EndgameObserver(Protocol):
    """Structural seam matching the two members of :class:`~babylon.engine.
    observers.endgame_detector.EndgameDetector` this module actually uses —
    not its full ``SimulationObserver`` contract (no
    ``on_simulation_start``/``on_simulation_end`` here: this driver's
    lifetime IS the campaign's, so there is no separate start/end to mark).
    """

    @property
    def recognized_pattern(self) -> GameOutcome | None:
        """The currently-recognized terminal pattern, or ``None``."""
        ...

    def on_tick(self, previous_state: WorldState, new_state: WorldState) -> None:
        """Re-evaluate every endgame axis against this tick's states."""
        ...


class PacingError(RuntimeError):
    """Base class for :class:`PacedTickDriver` invariant violations."""


class DriverLockedError(PacingError):
    """Raised when advancing is attempted after the endgame lock engaged."""


class DriverBusyError(PacingError):
    """Raised when advancing is attempted while a previous advance on the
    SAME driver is already in flight (see the module docstring's
    Re-entrancy note — an executor-thread call an outer coroutine's
    cancellation could not actually stop)."""


class PausedAwaitingAckError(PacingError):
    """Raised when advancing is attempted while an autopause is unacknowledged."""


class NoPendingAckError(PacingError):
    """Raised when acknowledging is attempted with no autopause pending."""


class TickOrderError(PacingError):
    """Raised when the wrapped advancer returns a tick out of strict +1 order."""


class PauseNotice:
    """One autopause's reason — what the autopause-ack flow requires the UI
    to acknowledge before ticking can resume.

    Plain (not frozen-Pydantic), mirroring :class:`~babylon.game.session.
    TickAdvanceResult`'s own reasoning (its docstring: "wrapping an
    already-immutable model in another validation layer buys nothing
    here"): it carries the SAME raw ``Event`` tuple that result already
    validated, with no second layer.

    :param tick: the tick whose :attr:`~babylon.game.session.
        TickAdvanceResult.paused` came back ``True``.
    :param events: that tick's raw event-bus history (the exact tuple
        :attr:`~babylon.game.session.TickAdvanceResult.events` carried).
    """

    __slots__ = ("events", "tick")

    def __init__(self, *, tick: int, events: tuple[Event, ...]) -> None:
        self.tick = tick
        self.events = events

    @property
    def summary(self) -> str:
        """A human-readable, UI-safe one-liner.

        Lists the distinct event TYPES this tick raised — never a
        re-derived severity judgement (that classification already
        happened inside the reused pause-predicate seam; this is only
        what to SHOW, not a second opinion on why it paused).
        """
        kinds = sorted({event.type for event in self.events})
        return f"tick {self.tick}: " + (", ".join(kinds) if kinds else "critical event")


#: Safety bound for :meth:`PacedTickDriver.run_until_paused` — the
#: canonical 100-year/5200-tick campaign horizon (``EndgameDefines.
#: campaign_horizon_years`` x 52 weeks/year; mirrors ``engine.optimization.
#: sensitivity.DEFAULT_MAX_TICKS``). A run-until-paused call can, in the
#: limit, cover an entire un-paused campaign; Power-of-10 rule 2 requires
#: every loop's upper bound be a fixed, statically-checkable constant —
#: never an unbounded ``while True``.
_DEFAULT_MAX_TICKS_PER_RUN: Final[int] = 5200


class PacedTickDriver:
    """The campaign's pacing policy, layered over one :class:`TickAdvancer`.

    See the module docstring for the invariants this class enforces
    (strict tick monotonicity, the permanent endgame lock, and — the
    Re-entrancy note — :attr:`busy`, refusing an overlapping advance
    rather than racing two calls against the same state) versus the one
    it deliberately reuses rather than re-implements (the pause-predicate
    seam, already computed inside the wrapped advancer's own
    :attr:`~babylon.game.session.TickAdvanceResult.paused`).

    :param advancer: the wrapped one-tick resolver.
    :param starting_tick: the advancer's own last-committed tick at
        construction time (``0`` for a fresh campaign, the resumed tick
        for a crash-resume) — the monotonicity check's baseline.
    :param endgame_observer: fed ``(previous_world, new_world)`` after
        every tick; ``None`` (the default) runs with no endgame lock at
        all — a valid configuration for tests, never for
        :func:`paced_driver_for_session`'s own production wiring.
    :param tick_delay: seconds to wait, via :attr:`sleep`, between two
        successive ticks inside :meth:`run_until_paused` only — a
        presentation-cadence knob, never consulted by :meth:`advance_once`
        and never fed back into what any tick computes. ``0.0`` (the
        default) never sleeps.
    :param sleep: the delay function; defaults to :func:`time.sleep`.
        Tests inject a counting no-op so the suite never actually waits on
        wall-clock time.
    """

    def __init__(
        self,
        advancer: TickAdvancer,
        *,
        starting_tick: int,
        endgame_observer: EndgameObserver | None = None,
        tick_delay: float = 0.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._advancer = advancer
        self._endgame_observer = endgame_observer
        self._tick_delay = tick_delay
        self._sleep = sleep
        self._last_tick: int = starting_tick
        self._last_world: WorldState | None = None
        self._last_autosave_tick: int | None = None
        self._locked = False
        self._lock_reason: GameOutcome | None = None
        self._pending_pause: PauseNotice | None = None
        self._busy_lock = threading.Lock()

    @property
    def busy(self) -> bool:
        """``True`` while a previous :meth:`advance_once`/
        :meth:`run_until_paused` call on THIS driver is still in flight
        (see the module docstring's Re-entrancy note)."""
        return self._busy_lock.locked()

    @property
    def last_tick(self) -> int:
        """The last tick this driver has itself observed and validated."""
        return self._last_tick

    @property
    def last_autosave_tick(self) -> int | None:
        """The most recent checkpoint tick this driver has itself observed
        (Unit C6), or ``None`` if no observed tick has been a checkpoint
        yet. Updated from :attr:`~babylon.game.session.TickAdvanceResult.
        autosaved` — never recomputed from ``last_tick`` via a second
        ``is_checkpoint_tick`` call site."""
        return self._last_autosave_tick

    @property
    def locked(self) -> bool:
        """``True`` once an endgame pattern has EVER been recognized — permanent."""
        return self._locked

    @property
    def lock_reason(self) -> GameOutcome | None:
        """The recognized terminal :class:`~babylon.models.enums.events.
        GameOutcome`, or ``None`` while unlocked."""
        return self._lock_reason

    @property
    def awaiting_ack(self) -> bool:
        """``True`` while a tick's autopause is unacknowledged."""
        return self._pending_pause is not None

    @property
    def pending_pause(self) -> PauseNotice | None:
        """The unacknowledged autopause's structured reason, or ``None``."""
        return self._pending_pause

    @property
    def pause_summary(self) -> str | None:
        """:attr:`pending_pause`'s UI-safe one-liner, or ``None``.

        A plain ``str`` (not :class:`PauseNotice`) so a caller across a
        structural-Protocol boundary (``babylon.tui.app``'s
        ``PacedDriverHandle``) never needs to import
        :class:`~babylon.kernel.event_bus.Event` just to render a status
        line.
        """
        return self._pending_pause.summary if self._pending_pause is not None else None

    def acknowledge_pause(self) -> None:
        """Clear a pending autopause, permitting the next advance.

        :raises DriverLockedError: the endgame lock has already engaged —
            there is nothing left to acknowledge into.
        :raises NoPendingAckError: called with no autopause pending —
            never a silent no-op (Constitution III.11).
        """
        if self._locked:
            raise DriverLockedError(
                f"cannot acknowledge — driver permanently locked at {self._lock_reason!r}"
            )
        if self._pending_pause is None:
            raise NoPendingAckError("acknowledge_pause() called with no autopause pending")
        self._pending_pause = None

    def advance_once(self) -> TickOutcomeLike:
        """Resolve exactly one further tick — the Unit C2 binding's own
        seam, now invariant-checked.

        :raises DriverBusyError: another advance on THIS driver is already
            in flight (module docstring's Re-entrancy note).
        :raises DriverLockedError: the endgame lock has already engaged.
        :raises PausedAwaitingAckError: a prior autopause is unacknowledged.
        :raises TickOrderError: the wrapped advancer returned a tick other
            than ``last_tick + 1``.
        """
        self._acquire_busy()
        try:
            return self._advance_and_check()
        finally:
            self._busy_lock.release()

    def run_until_paused(
        self, *, max_ticks: int = _DEFAULT_MAX_TICKS_PER_RUN
    ) -> tuple[TickOutcomeLike, ...]:
        """Advance repeatedly until an autopause, the endgame lock, or
        ``max_ticks`` — whichever comes first.

        Never advances past ``max_ticks`` ticks in one call (Power-of-10
        rule 2's fixed, statically-checkable loop bound) — the canonical
        5200-tick campaign horizon by default, never an unbounded loop.
        Holds :attr:`busy` for the ENTIRE call (not re-acquired per tick):
        a caller running this inside a Textual worker is exactly the
        scenario the module docstring's Re-entrancy note describes.

        :param max_ticks: the hard per-call ceiling.
        :returns: every resolved tick's outcome, in order (never empty:
            at least one tick is always resolved before this method can
            return, or an exception propagates instead).
        :raises DriverBusyError: another advance on THIS driver is already
            in flight.
        :raises DriverLockedError: the endgame lock had ALREADY engaged
            before this call.
        :raises PausedAwaitingAckError: a prior autopause is unacknowledged.
        :raises TickOrderError: as :meth:`advance_once`.
        """
        self._acquire_busy()
        try:
            results: list[TickOutcomeLike] = []
            for _ in range(max_ticks):
                result = self._advance_and_check()
                results.append(result)
                if self._locked or self.awaiting_ack:
                    break
                if self._tick_delay > 0.0:
                    self._sleep(self._tick_delay)
            return tuple(results)
        finally:
            self._busy_lock.release()

    def _acquire_busy(self) -> None:
        """Claim the re-entrancy guard or raise :class:`DriverBusyError`."""
        if not self._busy_lock.acquire(blocking=False):
            raise DriverBusyError(
                "a previous advance on this driver is still in flight "
                "(see PacedTickDriver's Re-entrancy note)"
            )

    def _advance_and_check(self) -> TickOutcomeLike:
        """The one-tick step shared by :meth:`advance_once` and
        :meth:`run_until_paused`: guard, advance, monotonicity check,
        endgame-lock update, autopause-ack update."""
        if self._locked:
            raise DriverLockedError(f"driver permanently locked at {self._lock_reason!r}")
        if self.awaiting_ack:
            raise PausedAwaitingAckError(
                "an autopause is unacknowledged — call acknowledge_pause() first"
            )

        result = self._advancer.advance_tick()
        expected = self._last_tick + 1
        if result.tick != expected:
            raise TickOrderError(
                f"expected tick {expected}, wrapped advancer returned {result.tick}"
            )

        # See the module docstring's Determinism note: `previous_state` is
        # unused by every current EndgameDetector axis evaluator, so the
        # very first driven tick (no prior world yet) passes this tick's
        # own world for both arguments rather than inventing a placeholder.
        previous_world = self._last_world if self._last_world is not None else result.world
        self._last_tick = result.tick
        self._last_world = result.world
        if result.autosaved:
            self._last_autosave_tick = result.tick

        if self._endgame_observer is not None:
            self._endgame_observer.on_tick(previous_world, result.world)
            pattern = self._endgame_observer.recognized_pattern
            if pattern is not None:
                self._locked = True
                self._lock_reason = pattern
                self._pending_pause = None
                return result

        if result.paused:
            self._pending_pause = PauseNotice(tick=result.tick, events=result.events)

        return result


def paced_driver_for_session(
    session: GameSession,
    *,
    endgame_observer: EndgameObserver | None = None,
    tick_delay: float = 0.0,
    sleep: Callable[[float], None] = time.sleep,
) -> PacedTickDriver:
    """Wrap a real :class:`~babylon.game.session.GameSession` in a
    :class:`PacedTickDriver`, wiring the endgame lock to a REAL
    :class:`~babylon.engine.observers.endgame_detector.EndgameDetector` by
    default (production callers should use this factory, not construct
    :class:`PacedTickDriver` directly, so the endgame lock is never
    silently absent).

    :param session: the booted or resumed session (Unit C1) to pace.
    :param endgame_observer: overrides the default
        :class:`~babylon.engine.observers.endgame_detector.EndgameDetector`
        (constructed with ``session``'s OWN :class:`~babylon.config.
        defines.GameDefines` — the same thresholds the tick loop itself
        runs under, not a mismatched fresh default set); tests inject a
        double here.
    :param tick_delay: forwarded to :class:`PacedTickDriver`.
    :param sleep: forwarded to :class:`PacedTickDriver`.
    :returns: a driver whose :attr:`~PacedTickDriver.last_tick` baseline is
        ``session``'s own current tick.
    """
    observer = (
        endgame_observer
        if endgame_observer is not None
        else EndgameDetector(defines=session.services.defines)
    )
    return PacedTickDriver(
        session,
        starting_tick=session.tick,
        endgame_observer=observer,
        tick_delay=tick_delay,
        sleep=sleep,
    )
