#!/usr/bin/env python3
"""Harvest the Program 24 P2 WO-19 institution-projection fixture.

Mirrors ``tools/record_projection_fixtures.py`` (the WO-6 county harvester)
exactly: drives the ``single_county`` scenario (Wayne County, Michigan, FIPS
``26163``) through a small, fixed number of ticks on a PERSISTENT graph —
the same direct ``ServiceContainer.create`` / ``TickContext`` /
``SimulationEngine.run_tick`` tick-driving idiom, for the same
graph-vs-``WorldState.from_graph()`` round-trip-loss reason documented there.

**Honest result, disclosed up front:** neither ``create_single_county_
scenario`` nor any other ``src/babylon/engine/scenarios/*.py`` builder, nor
any ``_DEFAULT_SYSTEMS`` system, ever constructs an ``Institution`` or writes
an institution node (confirmed by grep: zero ``Institution(`` call sites
under ``src/babylon/engine/`` at the time this harvester was written). This
script still drives the real scenario and projects a real (placeholder)
institution id against the real post-tick graph — the committed fixture it
writes is therefore an honestly **all-absent** dossier (every field ``None``
but identity/provenance), proving via a real engine run rather than an
assertion that today's engine ships zero institutions. See
``src/babylon/projection/institution.py``'s module docstring for the full
disclosure and ``tests/unit/projection/test_institution.py`` for the
full-dossier / loud-failure paths this scenario cannot exercise, covered
instead via in-test ``BabylonGraph()`` construction.

Deterministic by construction: fixed scenario (no RNG), fixed tick count, no
wall-clock in the recorded output — running this script twice produces
byte-identical JSON.

Usage::

    uv run python tools/record_institution_fixture.py
    uv run python tools/record_institution_fixture.py --output /tmp/institution.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

_TOOLS_DIR = Path(__file__).resolve().parent
_SRC_DIR = _TOOLS_DIR.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from regression_test import (  # type: ignore[import-not-found]  # noqa: E402
    build_single_county_overrides,
)

from babylon.engine.context import TickContext  # noqa: E402
from babylon.engine.scenarios import create_single_county_scenario  # noqa: E402
from babylon.engine.services import ServiceContainer  # noqa: E402
from babylon.engine.simulation_engine import _DEFAULT_ENGINE  # noqa: E402
from babylon.projection.fixtures.recorder import record_institution_fixture  # noqa: E402
from babylon.projection.institution import project_institution  # noqa: E402
from babylon.projection.view_models import InstitutionView  # noqa: E402

#: Placeholder institution id this harvester probes for. No scenario seeds
#: any institution today (see module docstring), so the *choice* of id is
#: immaterial to the result — every id projects all-absent. "doj" matches
#: the ``tests/unit/institution/conftest.py`` Department-of-Justice test
#: fixture convention, kept here only for a recognizable, documented name.
INSTITUTION_ID: Final[str] = "doj"

#: Fixed tick count driven before the projection is captured — matches the
#: WO-6 county harvester's ``TICK_COUNT`` for parity (same scenario, same
#: run).
TICK_COUNT: Final[int] = 5

#: Default destination — the committed fixture downstream view tasks read.
DEFAULT_OUTPUT: Final[Path] = (
    _TOOLS_DIR.parent / "tests" / "fixtures" / "projection" / f"institution_{INSTITUTION_ID}.json"
)


def harvest_institution_view() -> InstitutionView:
    """Build the ``single_county`` scenario, drive it ``TICK_COUNT`` ticks, project.

    :returns: The honestly all-absent :class:`~babylon.projection.
        view_models.InstitutionView` for :data:`INSTITUTION_ID` — this
        scenario seeds zero institutions, so every field beyond identity/
        provenance is ``None``.
    """
    state, sim_config, defines = create_single_county_scenario()
    overrides = build_single_county_overrides(defines)
    graph = state.to_graph()

    for tick in range(TICK_COUNT):
        services = ServiceContainer.create(sim_config, defines, **overrides)
        context = TickContext(tick=tick, persistent_data={})
        _DEFAULT_ENGINE.run_tick(graph, services, context)

    return project_institution(INSTITUTION_ID, graph=graph, tick=TICK_COUNT)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: harvest and record the institution fixture.

    :param argv: Argument vector (``None`` uses ``sys.argv``).
    :returns: Process exit code (always ``0`` — a failure to harvest raises
        rather than reporting a non-zero code, per the Loud Failure
        discipline: a partially-written fixture is worse than a crash).
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Destination JSON path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args(argv)

    view = harvest_institution_view()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record_institution_fixture(view, args.output)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
