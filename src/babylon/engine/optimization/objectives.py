"""Objective functions for parameter optimization.

The Carceral Equilibrium scoring (``PHASE_WINDOWS``,
``calculate_carceral_equilibrium_score``, ``format_phase_report``) is moved
verbatim from ``tools/carceral_scoring.py`` — the pre-package single source
of truth for this scoring logic. :class:`Objective` is the small ``Protocol``
every algorithm (sweep, Monte Carlo, sensitivity, Bayesian search) optimizes
against; :func:`carceral_objective` and :func:`survival_objective` are the
two concrete, ready-to-use scorers built on
:class:`~babylon.engine.optimization.backends.types.Result`.

See Also:
    ai/carceral-equilibrium.md: Full Carceral Equilibrium theory specification.
    ai/theory.md: MLM-TW foundation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Protocol

from babylon.engine.optimization.backends.types import Result
from babylon.models.enums import EventType

# =============================================================================
# CONSTANTS
# =============================================================================

TICKS_PER_YEAR: Final[int] = 52
"""Simulation ticks per year (1 tick = 1 week)."""


# =============================================================================
# PHASE WINDOW DEFINITIONS
# =============================================================================


@dataclass(frozen=True)
class PhaseWindow:
    """Expected timing window for a Carceral Equilibrium phase transition.

    :ivar name: Human-readable phase name (matches milestone dict keys).
    :ivar event_type: The ``EventType`` that signals this phase transition.
    :ivar earliest_year: Beginning of acceptable window (full credit).
    :ivar latest_year: End of acceptable window (full credit).
    :ivar weight: Scoring weight (0-1), all weights should sum to 1.0.
    """

    name: str
    event_type: EventType
    earliest_year: int
    latest_year: int
    weight: float


# Phase windows based on ai/carceral-equilibrium.md
# Windows are slightly wider than the theoretical ranges to allow for
# parameter variation while still rewarding correct sequencing.
PHASE_WINDOWS: Final[tuple[PhaseWindow, ...]] = (
    PhaseWindow(
        name="superwage_crisis",
        event_type=EventType.SUPERWAGE_CRISIS,
        earliest_year=20,
        latest_year=40,
        weight=0.25,
    ),
    PhaseWindow(
        name="class_decomposition",
        event_type=EventType.CLASS_DECOMPOSITION,
        earliest_year=25,
        latest_year=50,
        weight=0.25,
    ),
    PhaseWindow(
        name="control_ratio_crisis",
        event_type=EventType.CONTROL_RATIO_CRISIS,
        earliest_year=35,
        latest_year=60,
        weight=0.25,
    ),
    PhaseWindow(
        name="terminal_decision",
        event_type=EventType.TERMINAL_DECISION,
        earliest_year=45,
        latest_year=100,
        weight=0.25,
    ),
)


# =============================================================================
# SCORING FUNCTIONS
# =============================================================================


def calculate_timing_score(
    tick: int,
    window: PhaseWindow,
    max_years: float,
) -> float:
    """Calculate timing score for a single phase transition.

    :param tick: The simulation tick when the phase occurred.
    :param window: The ``PhaseWindow`` defining expected timing.
    :param max_years: Maximum simulation length in years.
    :returns: Score from 0.0 to 1.0:
        1.0 if the phase occurred within the expected window; linear decay
        if early (0 at tick 0 to 1.0 at ``earliest_year``); linear decay if
        late (1.0 at ``latest_year`` to 0 at ``max_years``).
    """
    year = tick / TICKS_PER_YEAR

    if window.earliest_year <= year <= window.latest_year:
        # Within expected window: full credit
        return 1.0
    elif year < window.earliest_year:
        # Early: linear decay from 0 at year 0 to 1.0 at earliest_year
        if window.earliest_year == 0:
            return 1.0
        return max(0.0, year / window.earliest_year)
    else:
        # Late: linear decay from 1.0 at latest_year to 0 at max_years
        remaining = max_years - window.latest_year
        if remaining <= 0:
            return 0.0
        return max(0.0, 1.0 - (year - window.latest_year) / remaining)


def calculate_carceral_equilibrium_score(
    phase_milestones: dict[str, int | None],
    terminal_outcome: str | None,
    max_ticks: int,
) -> float:
    """Score a simulation run based on Carceral Equilibrium phase timing.

    This is the main objective function for parameter optimization. It
    rewards simulations that exhibit the theoretically correct phase
    transition sequence within expected timing windows.

    :param phase_milestones: Dict mapping phase name -> tick when occurred.
        Keys should match ``PhaseWindow.name`` values. ``None`` indicates
        the phase never occurred.
    :param terminal_outcome: The outcome of the TERMINAL_DECISION event:
        ``"revolution"`` (workers organized, overthrew system),
        ``"genocide"`` (atomized surplus population eliminated), or
        ``None`` (terminal decision never reached).
    :param max_ticks: Total simulation length in ticks.
    :returns: Score from 0.0 (no phases occurred) to 100.0 (perfect
        trajectory).

    Scoring formula:
        Each phase contributes up to ``weight * 100`` points; full points
        if the phase occurs within its expected window, partial points if
        early/late (linear decay), zero points if the phase never occurs.
        A 10% bonus applies for a revolutionary outcome; a 10% penalty for
        a genocide outcome.

    Example::

        >>> milestones = {
        ...     "superwage_crisis": 1300,      # Year 25 (in window)
        ...     "class_decomposition": 1820,   # Year 35 (in window)
        ...     "control_ratio_crisis": 2340,  # Year 45 (in window)
        ...     "terminal_decision": 2860,     # Year 55 (in window)
        ... }
        >>> score = calculate_carceral_equilibrium_score(
        ...     milestones, "revolution", max_ticks=5200
        ... )
        >>> score  # Near 100 due to perfect timing + revolution bonus
    """
    score = 0.0
    max_years = max_ticks / TICKS_PER_YEAR

    for window in PHASE_WINDOWS:
        tick = phase_milestones.get(window.name)
        if tick is None:
            # Phase never occurred: 0 points for this phase
            continue

        timing_score = calculate_timing_score(tick, window, max_years)
        score += timing_score * window.weight * 100

    # Terminal outcome modifiers
    if terminal_outcome == "revolution":
        score *= 1.1  # 10% bonus for revolutionary outcome
    elif terminal_outcome == "genocide":
        score *= 0.9  # 10% penalty for genocide (still valid trajectory)

    return min(100.0, score)


def format_phase_report(
    phase_milestones: dict[str, int | None],
    terminal_outcome: str | None,
    max_ticks: int,
) -> str:
    """Format a human-readable report of phase timing and scoring.

    :param phase_milestones: Dict mapping phase name -> tick.
    :param terminal_outcome: ``"revolution"``, ``"genocide"``, or ``None``.
    :param max_ticks: Total simulation length.
    :returns: Multi-line string report suitable for console output.
    """
    lines = ["=" * 60, "CARCERAL EQUILIBRIUM PHASE REPORT", "=" * 60, ""]
    max_years = max_ticks / TICKS_PER_YEAR

    for window in PHASE_WINDOWS:
        tick = phase_milestones.get(window.name)
        if tick is None:
            status = "NOT REACHED"
            year_str = "---"
            timing_str = "0.00"
        else:
            year = tick / TICKS_PER_YEAR
            year_str = f"{year:.1f}"
            timing_score = calculate_timing_score(tick, window, max_years)
            timing_str = f"{timing_score:.2f}"
            if window.earliest_year <= year <= window.latest_year:
                status = "IN WINDOW"
            elif year < window.earliest_year:
                status = "EARLY"
            else:
                status = "LATE"

        lines.append(f"{window.name.upper()}")
        lines.append(f"  Expected: Years {window.earliest_year}-{window.latest_year}")
        lines.append(f"  Actual:   Year {year_str} ({status})")
        lines.append(f"  Score:    {timing_str} (weight: {window.weight:.2f})")
        lines.append("")

    # Overall score
    score = calculate_carceral_equilibrium_score(phase_milestones, terminal_outcome, max_ticks)
    lines.append("-" * 60)
    lines.append(f"Terminal Outcome: {terminal_outcome or 'NOT REACHED'}")
    lines.append(f"TOTAL SCORE: {score:.2f} / 100.00")
    lines.append("=" * 60)

    return "\n".join(lines)


# =============================================================================
# OBJECTIVE PROTOCOL + RESULT-BASED SCORERS
# =============================================================================


class Objective(Protocol):
    """Structural contract every optimization algorithm scores trials against.

    An ``Objective`` is any callable that reduces one trial's
    :class:`~babylon.engine.optimization.backends.types.Result` to a single
    float. Higher is always better — algorithms (sweep, Monte Carlo,
    sensitivity, Bayesian search) maximize whatever ``Objective`` they are
    given.
    """

    def __call__(self, result: Result) -> float:
        """Score one trial result.

        :param result: The trial's normalized :class:`Result`.
        :returns: A float score; higher is better.
        """
        ...


def carceral_objective(result: Result) -> float:
    """Score a trial by Carceral Equilibrium phase-timing (0.0-100.0).

    Thin adapter over :func:`calculate_carceral_equilibrium_score`, reading
    ``result.phase_milestones`` and ``result.terminal_outcome``.

    :param result: The trial's normalized :class:`Result`.
    :returns: Score from 0.0 to 100.0. Always 0.0 for a backend/scenario
        that cannot observe phase milestones (all ``None`` — honest
        degradation per Constitution III.11, not a fabricated score).
    """
    return calculate_carceral_equilibrium_score(
        result.phase_milestones,
        result.terminal_outcome,
        # ticks_survived (not a fixed configured max_ticks) is the best
        # available proxy for "total simulation length in ticks" from a
        # bare Result — a trial that died early has a shorter timing
        # denominator than one that ran to the configured max_ticks.
        max_ticks=max(result.ticks_survived, 1),
    )


def survival_objective(result: Result) -> float:
    """Score a trial by raw survival duration.

    :param result: The trial's normalized :class:`Result`.
    :returns: ``result.ticks_survived`` as a float.
    """
    return float(result.ticks_survived)


def endgame_objective(result: Result) -> float:
    """Track-B stub: score by :class:`~babylon.engine.observers.EndgameDetector` outcome.

    .. warning::
       **Opt-in and currently a stub.** The 5 terminal outcomes
       (REVOLUTIONARY_VICTORY, ECOLOGICAL_COLLAPSE, FASCIST_CONSOLIDATION,
       RED_OGV, FRAGMENTED_COLLAPSE) are detected by
       ``babylon.engine.observers.EndgameDetector`` against a live
       ``SimulationRunResult`` / graph state — information not carried on
       the backend-agnostic :class:`Result` contract. Wiring this
       correctly requires either extending ``Result.extra`` with the
       detector's verdict at trial time, or invoking the detector inside a
       backend before reshaping. Neither is done in this phase; this stub
       exists so callers can name the intended objective now and get a
       loud, explicit failure rather than a silently wrong score.

    :raises NotImplementedError: Always, until Track-B wiring lands.
    """
    raise NotImplementedError(
        "endgame_objective is a Track-B stub — EndgameDetector is not yet wired "
        "into any optimization backend's Result. See the docstring for what's missing."
    )


__all__ = [
    "TICKS_PER_YEAR",
    "PhaseWindow",
    "PHASE_WINDOWS",
    "calculate_timing_score",
    "calculate_carceral_equilibrium_score",
    "format_phase_report",
    "Objective",
    "carceral_objective",
    "survival_objective",
    "endgame_objective",
]
