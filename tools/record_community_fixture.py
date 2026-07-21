#!/usr/bin/env python3
"""Harvest the Program 24 P2 community-projection fixture (WO-24).

Drives the ``single_county`` scenario (Wayne County, Michigan, FIPS
``26163``) through a small, fixed number of ticks on a PERSISTENT graph —
the same direct ``ServiceContainer.create`` / ``TickContext`` /
``SimulationEngine.run_tick`` tick-driving idiom
``tools/record_projection_fixtures.py`` (WO-6) already uses, for the same
reason: keeping one graph object across every tick sidesteps the
``WorldState.from_graph``/``to_graph`` round-trip's dropped-field traps.

**Honest result, not a bug:** no scenario builder in this codebase ever
populates ``SocialClass.community_memberships`` — ``CommunitySystem.step``
(``src/babylon/engine/systems/community.py``) is a structural no-op every
tick because ``services.community_hypergraph`` is never wired by any
scenario (confirmed absent from ``build_single_county_overrides`` and every
``engine/scenarios/*.py`` builder), and the seam registry
(``src/babylon/sentinels/seam/registry.py:1969-1991``) marks the
``community_memberships`` payload ``STRUCTURALLY_IMPOSSIBLE`` for exactly
this reason. The fixture this script writes is therefore the honest
all-absent dossier — ``roster``, ``formation_tick``, and ``overlaps`` are
all ``None`` — and that is the true state of the substrate today, not a
harvesting defect. See ``babylon.projection.community``'s module docstring
for the full citation trail, and the WO-24 integrator report for the
disposition of this finding.

Deterministic by construction: fixed scenario (no RNG), fixed tick count, no
wall-clock in the recorded output — running this script twice produces
byte-identical JSON.

Usage::

    uv run python tools/record_community_fixture.py
    uv run python tools/record_community_fixture.py --output /tmp/community.json
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
from babylon.models.enums import CommunityType  # noqa: E402
from babylon.models.world_state import WorldState  # noqa: E402
from babylon.projection.community import project_community  # noqa: E402
from babylon.projection.fixtures.recorder import record_community_fixture  # noqa: E402
from babylon.projection.view_models import CommunityView  # noqa: E402

#: Which of the 14 fixed community types this harvester ships a fixture for.
#: Arbitrary among the 14 — every one projects identically all-absent in
#: this scenario (see module docstring); SETTLER is CommunityType's first
#: declared member and the design canon's own S9 worked example.
COMMUNITY_ID: Final[CommunityType] = CommunityType.SETTLER

#: Fixed tick count, matching the WO-6 county harvester exactly (past tick
#: 0's annual financial-layer boundary, small for determinism-run wall time).
TICK_COUNT: Final[int] = 5

#: Default destination — the committed fixture downstream view tasks read.
DEFAULT_OUTPUT: Final[Path] = (
    _TOOLS_DIR.parent / "tests" / "fixtures" / "projection" / f"community_{COMMUNITY_ID.value}.json"
)


def harvest_community_view() -> CommunityView:
    """Build the ``single_county`` scenario, drive it ``TICK_COUNT`` ticks, project SETTLER.

    :returns: The SETTLER community dossier projected from the live,
        post-tick world — honestly all-absent, since no scenario in this
        codebase wires a ``community_memberships`` producer today (see the
        module docstring).
    """
    state, sim_config, defines = create_single_county_scenario()
    overrides = build_single_county_overrides(defines)
    graph = state.to_graph()

    for tick in range(TICK_COUNT):
        services = ServiceContainer.create(sim_config, defines, **overrides)
        context = TickContext(tick=tick, persistent_data={})
        _DEFAULT_ENGINE.run_tick(graph, services, context)

    world = WorldState.from_graph(graph, tick=TICK_COUNT)
    return project_community(COMMUNITY_ID.value, world=world, tick=TICK_COUNT)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: harvest and record the community fixture.

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

    view = harvest_community_view()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record_community_fixture(view, args.output)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
