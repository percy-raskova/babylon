#!/usr/bin/env python3
"""Harvest the Program 24 P1 keel county-projection fixture (WO-6).

Drives the ``single_county`` scenario (Wayne County, Michigan, FIPS ``26163``
— the smallest graph where the Vol III financial layer fires, see
``babylon.engine.scenarios.create_single_county_scenario``) through a small,
fixed number of ticks on a PERSISTENT graph — the same direct
``ServiceContainer.create`` / ``TickContext`` / ``SimulationEngine.run_tick``
tick-driving idiom ``tools/partition_probe.py`` already uses, and for the same
reason: ``simulation_engine.step()`` discards the graph after reconstructing a
``WorldState`` each call, and ``project_county`` needs the LIVE post-tick
graph — its territory ``tick_*`` attrs and ``legitimation_index`` are
graph-only writes that ``WorldState.from_graph`` drops on reconstruction (see
``TERRITORY_EXCLUDED_FIELDS`` in ``babylon.models.world_state``). Keeping one
graph object across every tick sidesteps that round-trip entirely, so no
``_restore_graph_context``/``_save_graph_context`` bookkeeping — needed only
when the graph is rebuilt fresh each tick, as ``step()`` does — is required
here either.

The result is projected through
:func:`babylon.projection.county.project_county` and recorded via
:func:`babylon.projection.fixtures.recorder.record_county_fixture` — the
committed ``tests/fixtures/projection/county_26163.json`` this module writes
is what keeps every downstream view-consumer test DB- and engine-free.

Deterministic by construction: fixed scenario (no RNG), fixed tick count, no
wall-clock in the recorded output — running this script twice produces
byte-identical JSON (part of WO-6's Definition of Done).

Usage::

    uv run python tools/record_projection_fixtures.py
    uv run python tools/record_projection_fixtures.py --output /tmp/county.json
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
from babylon.projection.county import project_county  # noqa: E402
from babylon.projection.fixtures.recorder import record_county_fixture  # noqa: E402
from babylon.projection.view_models import CountyView  # noqa: E402

#: FIPS this harvester ships a fixture for — Wayne County, Michigan (Detroit
#: metro), the ``single_county`` scenario's sole territory.
COUNTY_FIPS: Final[str] = "26163"

#: Fixed tick count driven before the projection is captured. Small on
#: purpose (determinism-run wall time) but past tick 0 — the annual
#: financial-layer boundary that fires on the very first tick (see
#: ``tests/unit/engine/scenarios/test_single_county.py``) — so the fixture
#: exercises a non-trivial post-boundary state, not just the bootstrap tick.
TICK_COUNT: Final[int] = 5

#: Default destination — the committed fixture downstream view tasks read.
DEFAULT_OUTPUT: Final[Path] = (
    _TOOLS_DIR.parent / "tests" / "fixtures" / "projection" / f"county_{COUNTY_FIPS}.json"
)


def harvest_county_view() -> CountyView:
    """Build the ``single_county`` scenario, drive it ``TICK_COUNT`` ticks, project Wayne.

    :returns: The Wayne County dossier projected from the live, post-tick
        graph — every field this scenario's systems attribute this run
        populated, honest ``None`` for the rest (the scenario seeds no
        CLAIMS edge, so ``sovereign_id`` is always ``None`` here).
    """
    state, sim_config, defines = create_single_county_scenario()
    overrides = build_single_county_overrides(defines)
    graph = state.to_graph()

    for tick in range(TICK_COUNT):
        services = ServiceContainer.create(sim_config, defines, **overrides)
        context = TickContext(tick=tick, persistent_data={})
        _DEFAULT_ENGINE.run_tick(graph, services, context)

    world = WorldState.from_graph(graph, tick=TICK_COUNT)
    return project_county(COUNTY_FIPS, graph=graph, world=world, tick=TICK_COUNT)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: harvest and record the county fixture.

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

    view = harvest_county_view()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record_county_fixture(view, args.output)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
