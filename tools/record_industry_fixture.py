#!/usr/bin/env python3
"""Harvest the Program 24 P2 industry-projection fixture (WO-22).

Mirrors ``tools/record_projection_fixtures.py`` exactly: drives the
``single_county`` scenario (Wayne County, Michigan, FIPS ``26163``) through a
small, fixed number of ticks on a PERSISTENT graph, then projects and records
the result. See that module's docstring for the full rationale (persistent
graph vs ``simulation_engine.step()``'s discard-and-reconstruct).

**Honest-absence disposition (vocabulary-sentinel discipline):** the
``single_county`` scenario seeds no ``industries`` at all
(``babylon.engine.scenarios.single_county.create_single_county_scenario``
never populates ``WorldState.industries`` — confirmed by inspection, no
``NodeType.INDUSTRY`` node producer exists anywhere in ``domain/`` or
``engine/`` tick systems; the only real producer is
``babylon.engine.hydration.reference.hydrate_industry_hyperedges``, a
DB-backed reference-data hydrator not wired into this scenario). This
harvester therefore records the **honest-absence** fixture: a graph with no
``INDUSTRY`` node at all, projected for the representative id
``"ind_31-33"`` (NAICS Manufacturing — thematically apt for Wayne County's
``SectorType.INDUSTRIAL`` territory), yielding an ``IndustryView`` with every
field ``None`` except identity/``verified_tick``. This is not a placeholder
or a shortcut: it is the true, current state of this scenario's graph, and
the fixture says so rather than fabricating industry data that does not
exist (Constitution III.11).

Usage::

    uv run python tools/record_industry_fixture.py
    uv run python tools/record_industry_fixture.py --output /tmp/industry.json
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
from babylon.projection.fixtures.recorder import record_industry_fixture  # noqa: E402
from babylon.projection.industry import project_industry  # noqa: E402
from babylon.projection.view_models import IndustryView  # noqa: E402

#: The representative industry id this harvester projects — see the module
#: docstring's honest-absence disposition. Not a real node in this scenario's
#: graph; the projection is all-``None`` by construction, and that is the
#: point of recording it.
INDUSTRY_ID: Final[str] = "ind_31-33"

#: Fixed tick count driven before the projection is captured — same rationale
#: as ``tools/record_projection_fixtures.py::TICK_COUNT``.
TICK_COUNT: Final[int] = 5

#: Default destination — the committed fixture downstream view tasks read.
DEFAULT_OUTPUT: Final[Path] = (
    _TOOLS_DIR.parent / "tests" / "fixtures" / "projection" / f"industry_{INDUSTRY_ID}.json"
)


def harvest_industry_view() -> IndustryView:
    """Build the ``single_county`` scenario, drive it ``TICK_COUNT`` ticks, project.

    :returns: The honest-absence :class:`IndustryView` for :data:`INDUSTRY_ID`
        — every field ``None`` but identity/``verified_tick``, since this
        scenario seeds no ``industries`` at all.
    """
    state, sim_config, defines = create_single_county_scenario()
    overrides = build_single_county_overrides(defines)
    graph = state.to_graph()

    for tick in range(TICK_COUNT):
        services = ServiceContainer.create(sim_config, defines, **overrides)
        context = TickContext(tick=tick, persistent_data={})
        _DEFAULT_ENGINE.run_tick(graph, services, context)

    world = WorldState.from_graph(graph, tick=TICK_COUNT)
    return project_industry(INDUSTRY_ID, graph=graph, world=world, tick=TICK_COUNT)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: harvest and record the industry fixture.

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

    view = harvest_industry_view()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record_industry_fixture(view, args.output)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
