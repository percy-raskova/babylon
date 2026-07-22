#!/usr/bin/env python3
"""Aggregation-symmetry sentinel probe: all-masked input must yield ``None``.

The dynamic harness for ``babylon.sentinels.aggregation`` (Track 1 Task 10).
The sentinel package is layer 0.5 and may not import ``web.game.engine_bridge``
(a Django app that itself imports ``babylon.*`` — the reverse dependency
direction), so the harness lives here — the same split
``tools/partition_probe.py`` uses for the engine: this module builds
synthetic, ALL-MASKED input for each declared row in
``babylon.sentinels.aggregation.registry.DECLARED_AGGREGATES``, calls the
REAL aggregation function, and asserts the returned field is ``None`` — an
honest "unknown", never a fabricated ``0.0``.

Both declared rows are checked with independent, hand-written builders (a
small, closed dispatch keyed by ``row.name`` — see :data:`_PROBES` — rather
than generic reflection over two functions with unrelated signatures).
Adding a third aggregation to the family means adding both a registry row
AND a probe function here; this is a deliberate, declared-growth posture
(mirrors every other sentinel's registry-plus-check split), not an
oversight.

Run directly::

    uv run python tools/aggregation_symmetry_probe.py --check

or through the family CLI: ``uv run python tools/sentinel_check.py
aggregation --check``.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_WEB_DIR = _REPO_ROOT / "web"
if str(_WEB_DIR) not in sys.path:
    sys.path.insert(0, str(_WEB_DIR))

from babylon.models.world_state import WorldState  # noqa: E402
from babylon.sentinels.aggregation.registry import (  # noqa: E402
    AGGREGATION_EXEMPTIONS,
    DECLARED_AGGREGATES,
    DeclaredPartialCoverageAggregate,
)
from babylon.sentinels.base import LabelledCheck, SentinelCheckError, run_sensor  # noqa: E402
from babylon.sentinels.exemptions import is_exempt  # noqa: E402

_WHY: str = (
    "WHY THIS FAILS: Constitution III.11 (Loud Failure / honest-null) forbids a "
    "fabricated 0.0 standing in for 'unknown' -- when every member of a group is "
    "fog-masked, the aggregate must read as None (the player genuinely does not know), "
    "never as a real-looking zero that misreads as 'no repression pressure' or 'a fully "
    "pacified region'. This is not hypothetical: this is the exact shape the "
    "state-apparatus dashboard's own docstring names as the legitimation-index trap."
)


def _check_hex_features_heat(row: DeclaredPartialCoverageAggregate) -> list[str]:
    """All hexes in a group fog-masked on ``heat`` -> the group's ``heat`` is ``None``.

    :param row: The declared registry row (for the violation message).
    :returns: A single-element violation list, or ``[]`` when clean.
    :raises SentinelCheckError: If the real function cannot be imported or
        called — an infrastructure failure, never a silent pass.
    """
    try:
        from game.engine_bridge import EngineBridge
        from game.fog.ledger import IntelLedger
    except Exception as exc:  # noqa: BLE001 — infrastructure boundary
        raise SentinelCheckError(f"cannot import EngineBridge/IntelLedger: {exc}") from exc

    hex_states = [
        SimpleNamespace(
            h3_index="8928308280fffff",
            county_fips="26163",
            state_fips="26",
            bea_ea_code="EA1",
            msa_code="MSA1",
            pop_total=100,
            heat=75.0,
            org_count=0,
            profit_rate=None,
            exploitation_rate=None,
            occ=None,
            imperial_rent=None,
            county_name="Synthetic County",
            attributes={},
            dominant_class=None,
        )
    ]
    try:
        features = EngineBridge._aggregate_hex_features(
            hex_states,
            "county",
            reach=frozenset(),  # nothing in reach -> every hex is out-of-reach
            ledger=IntelLedger(),  # empty ledger -> tier is always "unknown"
            tick=0,
            staleness_ticks=10,
            unknown_ticks=20,
            h3_to_territory={},
        )
    except Exception as exc:  # noqa: BLE001 — infrastructure boundary
        raise SentinelCheckError(f"_aggregate_hex_features raised: {exc}") from exc

    heat = features[0]["properties"]["heat"]
    if heat is None:
        return []
    return [
        f"{row.name!r}: {row.function_name} returned heat={heat!r} for an all-masked "
        "group -- expected None.\n"
        f"    denominator: {row.denominator_note}\n"
        f"    consequence: {row.consequence_if_regressed}\n"
        "    fix: restore the heat_pop partial-coverage denominator, or add a reasoned "
        "SentinelExemption (key=('aggregate', name), reason, owner, date, tracking_task) "
        "to AGGREGATION_EXEMPTIONS -- never a silent registry removal.\n"
        f"    {_WHY}"
    ]


def _check_state_apparatus_dashboard_heat(row: DeclaredPartialCoverageAggregate) -> list[str]:
    """All state-apparatus orgs fog-masked on ``heat`` -> ``total_heat`` is ``None``.

    :param row: The declared registry row (for the violation message).
    :returns: A single-element violation list, or ``[]`` when clean.
    :raises SentinelCheckError: If the real function cannot be imported or
        called — an infrastructure failure, never a silent pass.
    """
    try:
        from game.engine_bridge import _build_state_apparatus_dashboard
    except Exception as exc:  # noqa: BLE001 — infrastructure boundary
        raise SentinelCheckError(f"cannot import _build_state_apparatus_dashboard: {exc}") from exc

    state = WorldState(tick=0)
    organizations: list[dict[str, Any]] = [
        {"id": "PROBE_ORG_1", "org_type": "state_apparatus", "budget": 100.0, "heat": None},
        {"id": "PROBE_ORG_2", "org_type": "state_apparatus", "budget": 50.0, "heat": None},
    ]
    try:
        dashboard = _build_state_apparatus_dashboard(state, organizations, recent_actions=[])
    except Exception as exc:  # noqa: BLE001 — infrastructure boundary
        raise SentinelCheckError(f"_build_state_apparatus_dashboard raised: {exc}") from exc

    total_heat = dashboard["total_heat"]
    if total_heat is None:
        return []
    return [
        f"{row.name!r}: {row.function_name} returned total_heat={total_heat!r} for an "
        "all-masked session -- expected None.\n"
        f"    denominator: {row.denominator_note}\n"
        f"    consequence: {row.consequence_if_regressed}\n"
        "    fix: restore the visible_heats-only sum, or add a reasoned SentinelExemption "
        "(key=('aggregate', name), reason, owner, date, tracking_task) to "
        "AGGREGATION_EXEMPTIONS -- never a silent registry removal.\n"
        f"    {_WHY}"
    ]


#: Closed dispatch: row.name -> its probe function. Mirrors every other
#: sentinel's declared-registry-plus-check split; a new row here means
#: adding both a registry row (aggregation/registry.py) and a probe function
#: (this module), never silently reusing an unrelated probe.
_PROBES: dict[str, Callable[[DeclaredPartialCoverageAggregate], list[str]]] = {
    "hex_features_heat": _check_hex_features_heat,
    "state_apparatus_dashboard_heat": _check_state_apparatus_dashboard_heat,
}


def check_all_declared_aggregates() -> list[str]:
    """Run every declared row's probe and collect violations.

    :returns: One violation string per row whose all-masked output is not
        ``None`` (empty when every declared row is symmetric).
    :raises SentinelCheckError: If a row names a probe this module has not
        declared (a stale/incomplete registration), or if a probe itself
        hits an infrastructure failure.
    """
    violations: list[str] = []
    for row in DECLARED_AGGREGATES:
        if is_exempt(("aggregate", row.name), AGGREGATION_EXEMPTIONS):
            continue
        probe = _PROBES.get(row.name)
        if probe is None:
            raise SentinelCheckError(
                f"{row.name!r} is declared in DECLARED_AGGREGATES but has no probe "
                f"function in tools/aggregation_symmetry_probe.py's _PROBES dispatch"
            )
        violations.extend(probe(row))
    return sorted(violations)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point (also routed from ``tools/sentinel_check.py aggregation``).

    :param argv: CLI args; ``--check`` is accepted for family-CLI parity
        (the behavior is always to gate).
    :returns: 0 clean, 1 gating violations found, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Aggregation partial-coverage symmetry — all-masked input must yield "
            "None, never a fabricated 0.0 (Constitution III.11)."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the tool always gates (exit 1 on violations).",
    )
    parser.parse_args(argv)

    gating: tuple[LabelledCheck, ...] = (("all-masked-yields-none", check_all_declared_aggregates),)

    def summary(advisory_count: int) -> str:
        _ = advisory_count
        return (
            f"AGGREGATION clean: {len(DECLARED_AGGREGATES)} declared aggregate(s) all "
            "return None (never a fabricated 0.0) when every member is fog-masked."
        )

    return run_sensor("AGGREGATION", gating, (), summary)


if __name__ == "__main__":
    sys.exit(main())
