#!/usr/bin/env python3
"""Harvest the Program 24 P2 Lane P social-class-projection fixture (WO-23).

Mirrors ``tools/record_projection_fixtures.py`` (WO-6, county) exactly: drives
the ``single_county`` scenario (Wayne County, Michigan, FIPS ``26163``) through
a small, fixed number of ticks on a PERSISTENT graph — the same direct
``ServiceContainer.create`` / ``TickContext`` / ``SimulationEngine.run_tick``
tick-driving idiom, kept for the identical reason: ``project_social_class``
needs the LIVE post-tick graph, since a class's own node attributes are
mutated in-place by several systems (Production, Struggle, MarketScissors) and
``WorldState.from_graph`` only round-trips the *declared* ``SocialClass``
model fields.

The result is projected through
:func:`babylon.projection.social_class.project_social_class` for the
``single_county`` scenario's Labor Aristocracy worker
(:data:`~babylon.models.entity_registry.LABOR_ARISTOCRACY_ID`, ``"C004"`` —
Wayne County's unionized core worker, the entity the county-financial-layer
scenario actually attributes and mutates every tick) and recorded via
:func:`babylon.projection.fixtures.recorder.record_social_class_fixture` — the
committed ``tests/fixtures/projection/social_class_C004.json`` this module
writes is what keeps every downstream view-consumer test DB- and engine-free.

Deterministic by construction: fixed scenario (no RNG), fixed tick count, no
wall-clock in the recorded output — running this script twice produces
byte-identical JSON.

Usage::

    uv run python tools/record_social_class_fixture.py
    uv run python tools/record_social_class_fixture.py --output /tmp/social_class.json
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
from babylon.models.entity_registry import LABOR_ARISTOCRACY_ID  # noqa: E402
from babylon.models.world_state import WorldState  # noqa: E402
from babylon.projection.fixtures.recorder import record_social_class_fixture  # noqa: E402
from babylon.projection.social_class import project_social_class  # noqa: E402
from babylon.projection.view_models import SocialClassView  # noqa: E402

#: Class id this harvester ships a fixture for — Wayne County's Labor
#: Aristocracy worker, the ``single_county`` scenario's mutated entity.
CLASS_ID: Final[str] = LABOR_ARISTOCRACY_ID

#: Fixed tick count driven before the projection is captured. Matches
#: ``tools/record_projection_fixtures.py``'s ``TICK_COUNT`` so both fixtures
#: are harvested from the same post-tick moment.
TICK_COUNT: Final[int] = 5

#: Default destination — the committed fixture downstream view tasks read.
DEFAULT_OUTPUT: Final[Path] = (
    _TOOLS_DIR.parent / "tests" / "fixtures" / "projection" / f"social_class_{CLASS_ID}.json"
)


def harvest_social_class_view() -> SocialClassView:
    """Build the ``single_county`` scenario, drive it ``TICK_COUNT`` ticks, project C004.

    :returns: The Labor Aristocracy worker's dossier projected from the live,
        post-tick graph — every field this scenario's systems attribute this
        run populated, honest ``None`` for the rest.
    """
    state, sim_config, defines = create_single_county_scenario()
    overrides = build_single_county_overrides(defines)
    graph = state.to_graph()

    for tick in range(TICK_COUNT):
        services = ServiceContainer.create(sim_config, defines, **overrides)
        context = TickContext(tick=tick, persistent_data={})
        _DEFAULT_ENGINE.run_tick(graph, services, context)

    world = WorldState.from_graph(graph, tick=TICK_COUNT)
    return project_social_class(CLASS_ID, graph=graph, world=world, tick=TICK_COUNT)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: harvest and record the social-class fixture.

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

    view = harvest_social_class_view()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record_social_class_fixture(view, args.output)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
