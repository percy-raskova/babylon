#!/usr/bin/env python3
"""Harvest the Program 24 P2 organization-projection fixture (WO-18).

Mirrors ``tools/record_projection_fixtures.py`` (the WO-6 county harvester)
exactly: drives the ``single_county`` scenario through a small, fixed number
of ticks on a PERSISTENT graph (the same ``ServiceContainer.create`` /
``TickContext`` / ``SimulationEngine.run_tick`` tick-driving idiom, for the
same reason — ``simulation_engine.step()`` discards the graph after
reconstructing a ``WorldState`` each call, and a live post-tick graph is what
:func:`babylon.projection.organization.project_organization` reads).

**Honest absence, by construction.** ``create_single_county_scenario`` seeds
exactly two ``SocialClass`` entities and one ``Territory`` — zero
``Organization`` entities (its ``WorldState.organizations`` is never
populated). :data:`ORG_ID` therefore never resolves to a real node in this
scenario's graph, so the fixture this script writes
(``tests/fixtures/projection/organization_org_rwp.json``) is the WO-18
no-producer contingency's honest-absence dossier end to end — every field
``None`` but identity/provenance — not a fabricated stand-in. This is the
expected, documented outcome (see
``babylon.projection.organization``'s module docstring), not a bug in this
harvester.

Deterministic by construction: fixed scenario (no RNG), fixed tick count, no
wall-clock in the recorded output — running this script twice produces
byte-identical JSON.

Usage::

    uv run python tools/record_organization_fixture.py
    uv run python tools/record_organization_fixture.py --output /tmp/org.json
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
from babylon.projection.fixtures.recorder import record_organization_fixture  # noqa: E402
from babylon.projection.organization import project_organization  # noqa: E402
from babylon.projection.view_models import OrganizationView  # noqa: E402

#: The org id this harvester ships a fixture for. A placeholder id in the
#: style of ``tests/integration/test_organization_detroit.py``'s Detroit
#: fixtures ("Revolutionary Workers Party") — NOT a real seeded entity; see
#: the module docstring's honest-absence note.
ORG_ID: Final[str] = "org_rwp"

#: Fixed tick count driven before the projection is captured. Matches the
#: county harvester's ``TICK_COUNT`` for parity (past tick 0, the annual
#: financial-layer boundary).
TICK_COUNT: Final[int] = 5

#: Default destination — the committed fixture downstream view tasks read.
DEFAULT_OUTPUT: Final[Path] = (
    _TOOLS_DIR.parent / "tests" / "fixtures" / "projection" / f"organization_{ORG_ID}.json"
)


def harvest_organization_view() -> OrganizationView:
    """Build the ``single_county`` scenario, drive it ``TICK_COUNT`` ticks, project :data:`ORG_ID`.

    :returns: The honest-absence :class:`OrganizationView` for :data:`ORG_ID`
        — this scenario seeds no organizations, so every field beyond
        identity/provenance is ``None``.
    """
    state, sim_config, defines = create_single_county_scenario()
    overrides = build_single_county_overrides(defines)
    graph = state.to_graph()

    for tick in range(TICK_COUNT):
        services = ServiceContainer.create(sim_config, defines, **overrides)
        context = TickContext(tick=tick, persistent_data={})
        _DEFAULT_ENGINE.run_tick(graph, services, context)

    world = WorldState.from_graph(graph, tick=TICK_COUNT)
    return project_organization(ORG_ID, graph=graph, world=world, tick=TICK_COUNT)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: harvest and record the organization fixture.

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

    view = harvest_organization_view()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record_organization_fixture(view, args.output)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
