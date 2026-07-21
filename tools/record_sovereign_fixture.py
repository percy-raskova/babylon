#!/usr/bin/env python3
"""Harvest the Program 24 P2 WO-20 sovereign-projection fixture.

Mirrors ``tools/record_projection_fixtures.py`` (the P1 keel county
harvester) exactly: drives the ``single_county`` scenario (Wayne County,
Michigan, FIPS ``26163``) through the same fixed ``TICK_COUNT`` ticks on a
PERSISTENT graph, then projects and records.

**Honest-absence finding (documented, not silently worked around):** the
``single_county`` scenario seeds **no** ``sovereign`` node and **no** CLAIMS
edges — confirmed by ``tools/record_projection_fixtures.py``'s own docstring
("the scenario seeds no CLAIMS edge, so sovereign_id is always None here")
and independently, by grepping every module under ``babylon.engine.scenarios``
for ``NodeType.SOVEREIGN`` / ``Sovereign(`` / ``sovereigns=`` — zero hits. No
scenario in this codebase currently populates ``WorldState.sovereigns``.

``NodeType.SOVEREIGN`` is nonetheless a real, production-stamped node type
(``WorldState.to_graph()`` writes it; ``CollapseTransitionSystem`` and
``FactionInfluenceSystem`` read it) — this is a scenario-coverage gap, not a
dead node type, so it does not get the "no live producer" honest-absence-page
treatment WO-21 (key_figure) uses. Instead: this harvester runs the exact
same scenario + tick recipe as the county harvester (for parity across every
Wave-1 Lane P fixture) and projects the canonical seed sovereign id
``SOV_USA_FED`` (``babylon.data.game.balkanization.seed_sovereigns.json``) —
a real, meaningful id this particular scenario's graph genuinely does not
contain. The result is the honest-absence :class:`~babylon.projection.
view_models.SovereignView`: every field ``None`` except identity/provenance.
``project_sovereign``'s own unit tests
(``tests/unit/projection/test_sovereign.py``) cover the fully-attributed and
partially-attributed shapes via hand-built graphs, exactly as
``test_county.py`` does for county — this harvester's committed fixture
exists so ``TestCommittedFixture`` (``tests/unit/projection/
test_fixture_recorder_sovereign.py``) can assert a real harvested artifact
stays present and well-shaped, the same contract the county fixture serves.

Deterministic by construction: fixed scenario (no RNG), fixed tick count, no
wall-clock in the recorded output — running this script twice produces
byte-identical JSON.

Usage::

    uv run python tools/record_sovereign_fixture.py
    uv run python tools/record_sovereign_fixture.py --output /tmp/sovereign.json
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
from babylon.projection.fixtures.recorder import record_sovereign_fixture  # noqa: E402
from babylon.projection.sovereign import project_sovereign  # noqa: E402
from babylon.projection.view_models import SovereignView  # noqa: E402

#: SOV_USA_FED — the canonical spec-070 seed sovereign id
#: (``babylon/data/game/balkanization/seed_sovereigns.json``). NOT seeded by
#: ``create_single_county_scenario`` (see module docstring finding); this
#: harvester's fixture is therefore the honest-absence projection.
SOVEREIGN_ID: Final[str] = "SOV_USA_FED"

#: Fixed tick count, matching ``tools/record_projection_fixtures.py`` for
#: harvest-recipe parity across every Wave-1 Lane P fixture.
TICK_COUNT: Final[int] = 5

#: Default destination — the committed fixture downstream view tasks read.
DEFAULT_OUTPUT: Final[Path] = (
    _TOOLS_DIR.parent / "tests" / "fixtures" / "projection" / f"sovereign_{SOVEREIGN_ID}.json"
)


def harvest_sovereign_view() -> SovereignView:
    """Build the ``single_county`` scenario, drive it ``TICK_COUNT`` ticks, project SOV_USA_FED.

    :returns: The honest-absence ``SovereignView`` — this scenario's graph
        contains no ``sovereign`` node under any id, so every field beyond
        identity/provenance projects ``None`` (see module docstring).
    """
    state, sim_config, defines = create_single_county_scenario()
    overrides = build_single_county_overrides(defines)
    graph = state.to_graph()

    for tick in range(TICK_COUNT):
        services = ServiceContainer.create(sim_config, defines, **overrides)
        context = TickContext(tick=tick, persistent_data={})
        _DEFAULT_ENGINE.run_tick(graph, services, context)

    world = WorldState.from_graph(graph, tick=TICK_COUNT)
    return project_sovereign(SOVEREIGN_ID, graph=graph, world=world, tick=TICK_COUNT)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: harvest and record the sovereign fixture.

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

    view = harvest_sovereign_view()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record_sovereign_fixture(view, args.output)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
