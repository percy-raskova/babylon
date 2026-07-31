"""Loud static checks for the fallback-coverage sentinel (ADR176 ruling 25).

Two gating rules over the disposition ledger in
:mod:`babylon.sentinels.fallback_coverage.registry`:

1. **bus-boundary coverage** — every ``EventType`` member has an
   ``EVENT_BUILDERS`` entry (else it drops to ``None`` at the bus->pydantic
   boundary and never reaches the player) or a cited ledger row; a ledgered
   member that gains a builder reds the gate until its row retires.
2. **chronicle coverage** — every wire-reaching member has a bespoke
   ``_SUMMARY_BUILDERS`` entry (else it renders the loud generic field-list
   line) or a cited ledger row, same ratchet; and a bespoke summary for a
   member that CANNOT reach the wire is the crafted-but-unreachable defect
   (content nobody can ever see reads as coverage).

Exit codes follow the family contract (:func:`babylon.sentinels.base.run_sensor`):
0 clean, 1 gating violations, 2 infrastructure failure.
"""

from __future__ import annotations

import argparse

from babylon.models.enums.events import EventType
from babylon.sentinels._ast import eventtype_dict_keys
from babylon.sentinels.base import SCOPE_NOT_DECLARED, LabelledCheck, run_sensor
from babylon.sentinels.fallback_coverage.registry import (
    BUS_BOUNDARY_LEDGER,
    CHRONICLE_DICT,
    CHRONICLE_LEDGER,
    CHRONICLE_PATH,
    EVENT_BUILDERS_DICT,
    EVENT_BUILDERS_PATH,
    EventCoverageRow,
)

_WHY = (
    "why: an EventType outside both registries either vanishes at the bus "
    "boundary or renders the generic field-list line — the dropped/flat "
    "verdict-surface class (ADR176 ruling 25; Standard §9 W.0)."
)


def ledger_violations(
    surface: str,
    scope: frozenset[str],
    covered: frozenset[str],
    rows: tuple[EventCoverageRow, ...],
) -> list[str]:
    """Enforce one surface's coverage law against its disposition ledger.

    :param surface: Human label for the surface ("bus-boundary"/"chronicle").
    :param scope: The member names obligated on this surface.
    :param covered: The member names the surface's registry actually covers.
    :param rows: The surface's ledger rows.
    :returns: One violation string per broken obligation.
    """
    ledgered = {row.member for row in rows}
    violations: list[str] = []
    for member in sorted(scope - covered - ledgered):
        violations.append(
            f"{surface}: EventType.{member} is uncovered and unledgered.\n"
            f"    fix: add its builder, or a cited CHARTER/DORMANT ledger row "
            f"(registry.py).\n    {_WHY}"
        )
    for row in rows:
        if row.member not in scope:
            violations.append(
                f'{surface}: ledger row "{row.member}" names no in-scope '
                f"EventType member — a typo, a retired member, or a row on "
                f"the wrong surface."
            )
            continue
        if row.member in covered:
            violations.append(
                f"{surface}: stale ledger row — EventType.{row.member} "
                f"({row.governance.value}) now HAS coverage.\n"
                f"    fix: remove the row — the ratchet only tightens "
                f"(Standard §9 W.3)."
            )
        if not row.citation:
            violations.append(
                f'{surface}: ledger row "{row.member}" '
                f"({row.governance.value}) is missing its citation — an "
                f"unruled absence is indistinguishable from an oversight "
                f"(Standard §9 W.2)."
            )
    return violations


def unreachable_bespoke_violations(
    bespoke: frozenset[str],
    wire_reaching: frozenset[str],
) -> list[str]:
    """A bespoke chronicle summary for a member with no bus builder is dead craft.

    The narrator-templates failure mode (crafted-but-unreachable content):
    the summary reads as coverage in every registry count while no event can
    ever render it.

    :param bespoke: Members with a bespoke ``_SUMMARY_BUILDERS`` entry.
    :param wire_reaching: Members with an ``EVENT_BUILDERS`` entry.
    :returns: One violation per unreachable bespoke summary.
    """
    return [
        f"chronicle: EventType.{member} has a bespoke summary but NO "
        f"EVENT_BUILDERS entry — crafted-but-unreachable content.\n"
        f"    fix: wire its bus builder (with its publisher's verified "
        f"payload shape), or remove the summary until one exists."
        for member in sorted(bespoke - wire_reaching)
    ]


def _members() -> frozenset[str]:
    return frozenset(member.name for member in EventType)


def _wire_reaching() -> frozenset[str]:
    return frozenset(eventtype_dict_keys(EVENT_BUILDERS_PATH, EVENT_BUILDERS_DICT))


def _bespoke() -> frozenset[str]:
    return frozenset(eventtype_dict_keys(CHRONICLE_PATH, CHRONICLE_DICT))


def _check_bus_boundary() -> list[str]:
    return ledger_violations(
        surface="bus-boundary",
        scope=_members(),
        covered=_wire_reaching(),
        rows=BUS_BOUNDARY_LEDGER,
    )


def _check_chronicle() -> list[str]:
    wire_reaching = _wire_reaching()
    bespoke = _bespoke()
    return ledger_violations(
        surface="chronicle",
        scope=wire_reaching & _members(),
        covered=bespoke,
        rows=CHRONICLE_LEDGER,
    ) + unreachable_bespoke_violations(bespoke, wire_reaching)


_GATING: tuple[LabelledCheck, ...] = (
    ("bus-boundary coverage (EventType -> EVENT_BUILDERS)", _check_bus_boundary),
    ("chronicle coverage (wire-reaching -> bespoke summary)", _check_chronicle),
)


def _summary(advisory_count: int) -> str:
    return (
        f"FALLBACK-COVERAGE clean: {len(EventType.__members__)} EventTypes "
        f"governed — {len(BUS_BOUNDARY_LEDGER)} bus-boundary dispositions "
        f"ledgered, {len(CHRONICLE_LEDGER)} chronicle exemptions "
        f"({advisory_count} advisories)."
    )


def main(argv: list[str] | None = None) -> int:
    """Run the fallback-coverage sentinel and return the exit code.

    :param argv: CLI args (``--check`` is accepted as the CI-mode alias; the
        behavior is always to gate).
    :returns: 0 clean, 1 gating violations, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Fallback coverage — EventType bus-boundary + chronicle bespoke "
            "closure (ADR176 ruling 25)."
        )
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the tool always gates (exit 1 on violations).",
    )
    parser.parse_args(argv)
    return run_sensor("FALLBACK-COVERAGE", _GATING, (), _summary, scope=SCOPE_NOT_DECLARED)
