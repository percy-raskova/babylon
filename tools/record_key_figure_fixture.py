#!/usr/bin/env python3
"""Harvest the Program 24 P2 key-figure honest-absence fixture (WO-21).

Mirrors ``tools/record_projection_fixtures.py``'s ``single_county`` harvest
idiom (same persistent-graph tick-driving pattern, same scenario), for
exactly one reason: to turn "no producer" from a static-analysis claim
(the vocabulary sentinel, ``ai/decisions/ADR084_retire_dead_models.yaml``,
and the ``NodeType.KEY_FIGURE``/``MODEL_FIELDS_BY_NODE_TYPE`` audit already
in ``babylon.projection.key_figure``'s module docstring) into a *checked
runtime fact* the fixture ships alongside: this script asserts the live
post-tick graph mints zero ``key_figure`` nodes before recording the
fixture, so a future engine change that starts stamping one fails this
harvester loudly instead of silently leaving a stale honest-absence fixture
in place.

The recorded :class:`~babylon.projection.view_models.KeyFigureView` itself
carries no field beyond identity — see ``projection.key_figure``'s module
docstring for why (ADR084) — so unlike the county harvester, driving the
engine here does not change what gets recorded; it only backs the "zero
producer" premise with a live check.

Deterministic by construction: fixed scenario (no RNG), fixed tick count, no
wall-clock in the recorded output — running this script twice produces
byte-identical JSON.

Usage::

    uv run python tools/record_key_figure_fixture.py
    uv run python tools/record_key_figure_fixture.py --output /tmp/kf.json
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
from babylon.models.enums.topology import NodeType  # noqa: E402
from babylon.models.world_state import WorldState  # noqa: E402
from babylon.projection.fixtures.recorder import record_key_figure_fixture  # noqa: E402
from babylon.projection.key_figure import project_key_figure  # noqa: E402
from babylon.projection.view_models import KeyFigureView  # noqa: E402

#: Representative id this harvester ships a fixture for. Not a real graph
#: node id — no scenario ever mints one (ADR084) — just a stable, readable
#: placeholder the honest-absence dossier is projected for.
KEY_FIGURE_ID: Final[str] = "kf-001"

#: Fixed tick count driven before the projection is captured — matches the
#: county harvester's ``TICK_COUNT`` so both fixtures are harvested from the
#: same post-boundary scenario state.
TICK_COUNT: Final[int] = 5

#: Default destination — the committed fixture downstream view tasks read.
DEFAULT_OUTPUT: Final[Path] = (
    _TOOLS_DIR.parent / "tests" / "fixtures" / "projection" / f"key_figure_{KEY_FIGURE_ID}.json"
)


def harvest_key_figure_view() -> KeyFigureView:
    """Drive ``single_county`` ``TICK_COUNT`` ticks, confirm zero key_figure nodes, project.

    :raises AssertionError: if the live post-tick graph ever mints a
        ``key_figure`` node — the empirical check backing this WO's
        honest-absence design; a future engine change that starts stamping
        one should fail this loudly, not silently drift the fixture out from
        under ``projection.key_figure``'s "no producer" claim.
    :returns: The honest-absence :class:`KeyFigureView` for :data:`KEY_FIGURE_ID`.
    """
    state, sim_config, defines = create_single_county_scenario()
    overrides = build_single_county_overrides(defines)
    graph = state.to_graph()

    for tick in range(TICK_COUNT):
        services = ServiceContainer.create(sim_config, defines, **overrides)
        context = TickContext(tick=tick, persistent_data={})
        _DEFAULT_ENGINE.run_tick(graph, services, context)

    key_figure_nodes = list(graph.query_nodes(node_type=NodeType.KEY_FIGURE.value))
    if key_figure_nodes:
        msg = (
            f"expected zero key_figure nodes in single_county (ADR084 dead producer); "
            f"found {len(key_figure_nodes)} -- the honest-absence premise no longer "
            "holds, re-audit babylon.projection.key_figure before regenerating this "
            "fixture"
        )
        raise AssertionError(msg)

    world = WorldState.from_graph(graph, tick=TICK_COUNT)
    return project_key_figure(KEY_FIGURE_ID, graph=graph, world=world, tick=TICK_COUNT)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: harvest and record the key-figure fixture.

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

    view = harvest_key_figure_view()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record_key_figure_fixture(view, args.output)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
