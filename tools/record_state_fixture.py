#!/usr/bin/env python3
"""Harvest the Program 24 P2 WO-16 state-projection fixture.

Mirrors ``tools/record_projection_fixtures.py`` exactly, one tier up: drives
the ``single_county`` scenario (Wayne County, Michigan, FIPS ``26163`` — the
smallest graph where the Vol III financial layer fires, see
``babylon.engine.scenarios.create_single_county_scenario``) through a small,
fixed number of ticks on a PERSISTENT graph — the same direct
``ServiceContainer.create`` / ``TickContext`` / ``SimulationEngine.run_tick``
tick-driving idiom ``tools/partition_probe.py`` and
``tools/record_projection_fixtures.py`` already use, and for the same
reason: ``simulation_engine.step()`` discards the graph after reconstructing
a ``WorldState`` each call, and ``project_state`` needs the LIVE post-tick
graph — its territories' ``tick_*`` attrs and ``legitimation_index`` are
graph-only writes that ``WorldState.from_graph`` drops on reconstruction
(see ``TERRITORY_EXCLUDED_FIELDS`` in ``babylon.models.world_state``).
Keeping one graph object across every tick sidesteps that round-trip
entirely.

The result is projected through
:func:`babylon.projection.state.project_state` for Michigan (FIPS ``"26"``
— Wayne County's state, the only county the ``single_county`` scenario
seeds) and recorded via
:func:`babylon.projection.fixtures.recorder.record_state_fixture` — the
committed ``tests/fixtures/projection/state_26.json`` this module writes is
what keeps every downstream view-consumer test DB- and engine-free.

Deterministic by construction: fixed scenario (no RNG), fixed tick count, no
wall-clock in the recorded output — running this script twice produces
byte-identical JSON.

Usage::

    uv run python tools/record_state_fixture.py
    uv run python tools/record_state_fixture.py --output /tmp/state.json
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
from babylon.projection.fixtures.recorder import record_state_fixture  # noqa: E402
from babylon.projection.state import project_state  # noqa: E402
from babylon.projection.view_models import StateView  # noqa: E402

#: State FIPS this harvester ships a fixture for — Michigan, the sole state
#: the ``single_county`` scenario's one territory (Wayne, ``26163``) falls
#: under.
STATE_FIPS: Final[str] = "26"

#: Fixed tick count driven before the projection is captured. Matches
#: ``tools/record_projection_fixtures.py``'s ``TICK_COUNT`` so both
#: committed fixtures describe the identical post-tick world.
TICK_COUNT: Final[int] = 5

#: Default destination — the committed fixture downstream view tasks read.
DEFAULT_OUTPUT: Final[Path] = (
    _TOOLS_DIR.parent / "tests" / "fixtures" / "projection" / f"state_{STATE_FIPS}.json"
)


def harvest_state_view() -> StateView:
    """Build the ``single_county`` scenario, drive it ``TICK_COUNT`` ticks, project Michigan.

    :returns: The Michigan state dossier rolled up from its sole county
        (Wayne, ``26163``) — every field this scenario's systems attribute
        this run populated, honest ``None`` for the rest (the scenario
        seeds no CLAIMS edge, so ``sovereign_id`` is always ``None`` here).
    """
    state, sim_config, defines = create_single_county_scenario()
    overrides = build_single_county_overrides(defines)
    graph = state.to_graph()

    for tick in range(TICK_COUNT):
        services = ServiceContainer.create(sim_config, defines, **overrides)
        context = TickContext(tick=tick, persistent_data={})
        _DEFAULT_ENGINE.run_tick(graph, services, context)

    world = WorldState.from_graph(graph, tick=TICK_COUNT)
    return project_state(STATE_FIPS, graph=graph, world=world, tick=TICK_COUNT)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: harvest and record the state fixture.

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

    view = harvest_state_view()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record_state_fixture(view, args.output)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
