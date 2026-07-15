#!/usr/bin/env python3
"""Partition-sentinel probe: run scenarios, collect pole stashes, report.

The engine-running harness for ``babylon.sentinels.partition`` (Program 19
Phase 1, ADR070). The sentinel package is layer 0.5 and may not import the
engine, so the harness lives here (the same split as the dynamic sentinels'
``shared_tick`` test fixture): this module runs each scenario on a
**persistent graph** — ``state.to_graph()`` once, then ``run_tick`` in place,
the bridged-runner altitude, so the ``pole_readings`` tie-inertia channel
genuinely persists across ticks — collects the per-tick stash dumps, and
hands them to the pure analyzer.

ADVISORY tier only (Phase 1): exit 0 with findings printed loudly, exit 2 on
infrastructure failure (a scenario that cannot build or run). Never exit 1 —
the DATA is the deliverable; the decision rules it feeds live in
``project/programs/19-emergent-class-partition.md`` §5.

Run directly (full evidence blocks on stdout)::

    poetry run python tools/partition_probe.py --scenario all
    poetry run python tools/partition_probe.py --scenario wayne_county --ticks 52

or through the family CLI: ``poetry run python tools/sentinel_check.py partition``.
``wayne_county`` is NEVER part of ``all`` — it hydrates from the local
reference DB, which CI must not touch (owner ruling 2026-07-14); run it
explicitly on a dev box.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import regression_test as rt  # type: ignore[import-not-found]  # noqa: E402

from babylon.engine.context import TickContext  # noqa: E402
from babylon.engine.services import ServiceContainer  # noqa: E402
from babylon.engine.simulation_engine import _DEFAULT_ENGINE  # noqa: E402
from babylon.sentinels.base import LabelledCheck, SentinelCheckError, run_sensor  # noqa: E402
from babylon.sentinels.partition.checks import (  # noqa: E402
    PartitionReport,
    advisory_findings,
    analyze_partition,
    report_lines,
)

#: The synthetic scenarios ``--scenario all`` covers (the 5 qa:regression ones).
PROBE_SCENARIOS: tuple[str, ...] = tuple(sorted(rt.SCENARIOS))

#: The bridged county scenario — explicit opt-in only (reads the reference DB).
WAYNE = "wayne_county"


def _create_scenario(scenario: str) -> tuple[Any, Any, Any]:
    """Build ``scenario`` → ``(WorldState, SimulationConfig, GameDefines)``.

    :raises SentinelCheckError: If the scenario cannot be built —
        infrastructure failure (exit 2), never a silent skip. The broad
        except is deliberate: this is the probe's infrastructure boundary
        (scenario factories touch the reference DB and filesystem), and every
        failure mode must land on the sentinel exit-code contract.
    """
    try:
        if scenario == WAYNE:
            from babylon.engine.scenarios import create_wayne_county_scenario

            return create_wayne_county_scenario()
        return rt.create_scenario(scenario)
    except Exception as exc:  # noqa: BLE001 — infrastructure boundary (see docstring)
        raise SentinelCheckError(f"cannot build scenario {scenario!r}: {exc}") from exc


def run_probe(scenario: str, ticks: int) -> PartitionReport:
    """Run ``scenario`` for ``ticks`` on a persistent graph and analyze it.

    :param scenario: One of :data:`PROBE_SCENARIOS` or :data:`WAYNE`.
    :param ticks: Tick count (positive).
    :returns: The scenario's :class:`PartitionReport`.
    :raises SentinelCheckError: If the scenario cannot be built or run.
    """
    state, sim_config, defines = _create_scenario(scenario)
    graph = state.to_graph()
    stashes: list[dict[str, Any]] = []
    try:
        for tick in range(ticks):
            services = ServiceContainer.create(sim_config, defines)
            context = TickContext(tick=tick, persistent_data={})
            _DEFAULT_ENGINE.run_tick(graph, services, context)
            # _step_pole_channel REPLACES the attr with a fresh dict each tick,
            # so holding the reference is safe (never mutated afterwards).
            stashes.append(graph.graph.get("pole_readings", {}))
    except Exception as exc:  # noqa: BLE001 — infrastructure boundary (exit-2 contract)
        raise SentinelCheckError(f"scenario {scenario!r} failed at run: {exc}") from exc

    seeded_roles: dict[str, str] = {}
    for node in graph.query_nodes(node_type="social_class"):
        role = node.attributes.get("role")
        if role is not None:
            seeded_roles[node.id] = str(role)
    return analyze_partition(scenario=scenario, seeded_roles=seeded_roles, tick_stashes=stashes)


def _probe_check(
    scenario: str, ticks: int, reports: list[PartitionReport]
) -> Callable[[], list[str]]:
    """Build one advisory check: run the probe, print evidence, return findings."""

    def check() -> list[str]:
        report = run_probe(scenario, ticks)
        reports.append(report)
        for line in report_lines(report):
            print(line)
        return advisory_findings(report)

    return check


def main(argv: list[str] | None = None) -> int:
    """CLI entry point (also routed from ``tools/sentinel_check.py partition``).

    :param argv: CLI args; ``--check`` is accepted for family-CLI parity and
        changes nothing — the partition sentinel is advisory-only in Phase 1.
    :returns: 0 clean/advisory, 2 infrastructure failure (never 1 in Phase 1).
    """
    parser = argparse.ArgumentParser(
        description="Partition sentinel probe — seeded-vs-derived class evidence (ADR070).",
    )
    parser.add_argument(
        "--scenario",
        default="all",
        choices=[*PROBE_SCENARIOS, WAYNE, "all"],
        help=f"scenario to probe; 'all' = the {len(PROBE_SCENARIOS)} synthetic scenarios "
        f"(never {WAYNE} — reference-DB opt-in)",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=rt.DEFAULT_MAX_TICKS,
        help="ticks to run per scenario (default: the qa:regression window)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="family-CLI parity flag; advisory-only, so this changes nothing in Phase 1",
    )
    args = parser.parse_args(argv)

    names = list(PROBE_SCENARIOS) if args.scenario == "all" else [args.scenario]
    reports: list[PartitionReport] = []
    advisory: tuple[LabelledCheck, ...] = tuple(
        (name, _probe_check(name, args.ticks, reports)) for name in names
    )

    def summary(advisory_count: int) -> str:
        rates = ", ".join(
            f"{report.scenario}="
            + ("n/a" if report.agreement_rate is None else f"{report.agreement_rate:.3f}")
            for report in reports
        )
        return f"PARTITION advisory: {advisory_count} findings; agreement [{rates}]"

    return run_sensor("PARTITION", gating=(), advisory=advisory, summary=summary)


if __name__ == "__main__":
    sys.exit(main())
