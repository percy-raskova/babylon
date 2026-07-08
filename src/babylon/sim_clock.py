"""Deterministic simulation clock (Constitution III.7).

Maps a weekly tick to a canonical in-world datetime so timestamps are a
pure function of tick, never of wall clock. Year mapping mirrors FR-013
(``year = start_year + tick // 52`` — see
:mod:`babylon.config.defines.cross_scale` and the headless bridge, which
uses the same 2010 epoch). Kept as a top-level leaf module so both the
engine (``event_bus``/``interceptor``, which must not import the heavy
:mod:`babylon.models` package) and :mod:`babylon.models.events` can import
it without cycles.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Final

#: FR-013 epoch year — tick 0 falls on Jan 1 of this year (UTC).
SIM_EPOCH_YEAR: Final[int] = 2010

#: Weekly-tick calendar: 52 ticks per simulated year (FR-013).
WEEKS_PER_YEAR: Final[int] = 52

#: Sentinel meaning "derive from tick" — frozen dataclass/model defaults
#: cannot see sibling fields, so construction sites leave this in place
#: and ``__post_init__`` / the before-validator replaces it.
UNSET_TIMESTAMP: Final[datetime] = datetime.min.replace(tzinfo=UTC)


def sim_datetime(tick: int) -> datetime:
    """Return the deterministic in-world datetime for ``tick``.

    The mapping is a pure function of ``tick`` (Constitution III.7): tick 0
    is Jan 1 of :data:`SIM_EPOCH_YEAR` (UTC); each tick advances one week,
    rolling the year every :data:`WEEKS_PER_YEAR` ticks per FR-013.

    Args:
        tick: Simulation tick (0-indexed, weekly).

    Returns:
        Timezone-aware UTC datetime for the tick.

    Raises:
        ValueError: If ``tick`` is negative.

    Example:
        >>> from babylon.sim_clock import sim_datetime
        >>> sim_datetime(0).isoformat()
        '2010-01-01T00:00:00+00:00'
        >>> sim_datetime(52).year
        2011
    """
    if tick < 0:
        raise ValueError(f"tick must be >= 0, got {tick}")
    year = SIM_EPOCH_YEAR + tick // WEEKS_PER_YEAR
    return datetime(year, 1, 1, tzinfo=UTC) + timedelta(weeks=tick % WEEKS_PER_YEAR)
