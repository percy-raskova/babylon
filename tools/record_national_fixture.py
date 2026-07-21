#!/usr/bin/env python3
"""Harvest the Program 24 P2 national-projection fixture (WO-17).

Mirrors ``tools/record_projection_fixtures.py`` exactly: drives the
``single_county`` scenario (Wayne County, Michigan, FIPS ``26163``) through a
small, fixed number of ticks on a PERSISTENT graph — ``project_national``
needs the same LIVE post-tick graph ``project_county`` does (territory
``tick_*`` attrs and ``legitimation_index`` are graph-only writes
``WorldState.from_graph`` drops on reconstruction).

Honest scope note: the ``single_county`` scenario attributes exactly one
county (Wayne), so this harvest's national rollup is mathematically
identical to that one county's own aggregates — a small but real nationwide
dossier, not a placeholder. The six value-composition fields
(``c_sum``…``hex_count``) are Postgres-only (``v_national_value_aggregate``
sums ``dynamic_hex_state``, spec-089) and this harvester opens no database
connection, so it passes ``national_aggregate=None`` and those six fields are
recorded as honest absence — never a fabricated sum. A future harvester with
a live Postgres session can inject a fetched
:class:`~babylon.persistence.postgres_aggregation.NationalValueAggregate` row
to fill them in.

Deterministic by construction: fixed scenario (no RNG), fixed tick count, no
wall-clock in the recorded output — running this script twice produces
byte-identical JSON.

Usage::

    uv run python tools/record_national_fixture.py
    uv run python tools/record_national_fixture.py --output /tmp/national.json
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
from babylon.models.world_state import WorldState  # noqa: E402
from babylon.projection.fixtures.recorder import record_national_fixture  # noqa: E402
from babylon.projection.national import project_national  # noqa: E402
from babylon.projection.view_models import NationalView  # noqa: E402

#: The nation this harvester ships a fixture for — matches
#: ``NationalValueAggregate.national_id``'s documented literal.
NATIONAL_ID: Final[str] = "USA"

#: Fixed tick count driven before the projection is captured — identical to
#: the county harvester's, past tick 0's annual financial-layer boundary.
TICK_COUNT: Final[int] = 5

#: Default destination — the committed fixture downstream view tasks read.
DEFAULT_OUTPUT: Final[Path] = (
    _TOOLS_DIR.parent / "tests" / "fixtures" / "projection" / f"national_{NATIONAL_ID}.json"
)


def harvest_national_view() -> NationalView:
    """Build the ``single_county`` scenario, drive it ``TICK_COUNT`` ticks, project USA.

    :returns: The USA dossier projected from the live, post-tick graph —
        every population-weighted field this scenario's systems attribute
        this run populated (a one-county nation), honest ``None`` for the
        rest, and honest ``None`` for every value-composition field (no
        Postgres session here — see the module docstring).
    """
    state, sim_config, defines = create_single_county_scenario()
    overrides = build_single_county_overrides(defines)
    graph = state.to_graph()

    for tick in range(TICK_COUNT):
        services = ServiceContainer.create(sim_config, defines, **overrides)
        context = TickContext(tick=tick, persistent_data={})
        _DEFAULT_ENGINE.run_tick(graph, services, context)

    world = WorldState.from_graph(graph, tick=TICK_COUNT)
    return project_national(NATIONAL_ID, graph=graph, world=world, tick=TICK_COUNT)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: harvest and record the national fixture.

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

    view = harvest_national_view()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record_national_fixture(view, args.output)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
