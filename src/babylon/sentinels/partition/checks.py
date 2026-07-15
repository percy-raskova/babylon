"""Partition-sentinel analysis: per-run pole stashes → :class:`PartitionReport`.

Pure data-in/data-out (layer 0.5, no engine import): the analyzer consumes the
raw per-tick ``pole_readings`` graph-attribute dumps an engine-running harness
collected (``tools/partition_probe.py`` for the CLI; a test can hand-build
them) and the run's seeded ``role`` map, and reports:

- ``agreement_rate`` — of nodes bearing BOTH a derived cell and a seeded role,
  the fraction whose role falls inside the declared crosswalk
  (:data:`~babylon.sentinels.partition.registry.CELL_TO_SEEDED_ROLES`).
  ``None`` when no node bears both — never a fabricated 0.0/1.0.
- ``divergent_nodes`` — the named disagreements, the program's key evidence.
- ``unpositioned`` — per axis, how many seeded class nodes carry no reading
  at the final tick (an expected state for e.g. unwaged capital poles —
  reported, not judged).
- ``multi_occupancy`` — occupant count per derived cell (N>1 is the
  ADR070 §D multiplicity signal, surfaced not acted on).
- ``side_flips`` — per (axis, node), tick-to-tick side changes: the
  chattering instrument that GATES Phase 3+ cutovers.

ADVISORY tier only in Phase 1 (never exit 1): the data is the deliverable.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.partition.registry import (
    CELL_TO_SEEDED_ROLES,
    PRINCIPAL_AXES,
    cell_name,
)

__all__ = ["PartitionReport", "advisory_findings", "analyze_partition", "report_lines"]

#: One tick's ``pole_readings`` dump: axis -> entity_id -> PoleReading dump.
TickStash = Mapping[str, Mapping[str, Mapping[str, Any]]]


@dataclass(frozen=True)
class PartitionReport:
    """One scenario run's seeded-vs-derived partition evidence.

    :ivar scenario: Scenario name the run was built from.
    :ivar ticks: Number of ticks captured (``len(tick_stashes)``).
    :ivar class_node_count: Seeded class nodes considered (the role map size).
    :ivar cell_bearing_count: Nodes with BOTH a derived cell and a seeded role.
    :ivar agreements: Of those, how many fall inside the crosswalk.
    :ivar agreement_rate: ``agreements / cell_bearing_count``; ``None`` when
        the denominator is zero (no fabricated rate).
    :ivar divergent_nodes: ``(node_id, seeded_role, derived_cell)`` rows,
        sorted by node id.
    :ivar unpositioned: ``(axis, count)`` per principal axis — seeded nodes
        with no reading on that axis at the final tick.
    :ivar multi_occupancy: ``(cell, occupant_count)`` rows, sorted by cell.
    :ivar side_flips: ``(axis, node_id, flips)`` rows with ``flips > 0``,
        sorted — tick-adjacent side changes only (an absence gap breaks
        adjacency and is never counted as a flip).
    """

    scenario: str
    ticks: int
    class_node_count: int
    cell_bearing_count: int
    agreements: int
    agreement_rate: float | None
    divergent_nodes: tuple[tuple[str, str, str], ...]
    unpositioned: tuple[tuple[str, int], ...]
    multi_occupancy: tuple[tuple[str, int], ...]
    side_flips: tuple[tuple[str, str, int], ...]


def analyze_partition(
    scenario: str,
    seeded_roles: Mapping[str, str],
    tick_stashes: Sequence[TickStash],
) -> PartitionReport:
    """Turn a run's pole stashes + seeded roles into a :class:`PartitionReport`.

    :param scenario: Scenario name, stamped onto the report.
    :param seeded_roles: ``node_id -> SocialRole.value`` for the run's class
        nodes (the seeds under measurement).
    :param tick_stashes: The per-tick ``pole_readings`` dumps, oldest first.
    :returns: The frozen report.
    :raises SentinelCheckError: If no ticks were captured — an empty run is an
        infrastructure failure (exit 2), never an empty-but-clean report.
    """
    if not tick_stashes:
        raise SentinelCheckError(f"{scenario}: no tick stashes captured — probe ran zero ticks")

    final = tick_stashes[-1]
    final_sides: dict[str, dict[str, str]] = {
        axis: {
            entity_id: str(reading["side"]) for entity_id, reading in final.get(axis, {}).items()
        }
        for axis in PRINCIPAL_AXES
    }

    cell_nodes = sorted(set(final_sides[PRINCIPAL_AXES[0]]) & set(final_sides[PRINCIPAL_AXES[1]]))
    cells: dict[str, str] = {}
    for node_id in cell_nodes:
        cell = cell_name({axis: final_sides[axis][node_id] for axis in PRINCIPAL_AXES})
        if cell is not None:  # both axes present by construction
            cells[node_id] = cell

    agreements = 0
    cell_bearing = 0
    divergent: list[tuple[str, str, str]] = []
    for node_id in sorted(cells):
        role = seeded_roles.get(node_id)
        if role is None:
            continue
        cell_bearing += 1
        if role in CELL_TO_SEEDED_ROLES[cells[node_id]]:
            agreements += 1
        else:
            divergent.append((node_id, role, cells[node_id]))

    unpositioned = tuple(
        (axis, sum(1 for node_id in seeded_roles if node_id not in final_sides[axis]))
        for axis in PRINCIPAL_AXES
    )
    occupancy = Counter(cells.values())
    flips: dict[tuple[str, str], int] = {}
    for previous, current in zip(tick_stashes, tick_stashes[1:], strict=False):
        for axis in PRINCIPAL_AXES:
            previous_axis = previous.get(axis, {})
            for entity_id, reading in current.get(axis, {}).items():
                prior = previous_axis.get(entity_id)
                if prior is not None and str(prior["side"]) != str(reading["side"]):
                    flips[(axis, entity_id)] = flips.get((axis, entity_id), 0) + 1

    return PartitionReport(
        scenario=scenario,
        ticks=len(tick_stashes),
        class_node_count=len(seeded_roles),
        cell_bearing_count=cell_bearing,
        agreements=agreements,
        agreement_rate=(agreements / cell_bearing) if cell_bearing else None,
        divergent_nodes=tuple(divergent),
        unpositioned=unpositioned,
        multi_occupancy=tuple(sorted(occupancy.items())),
        side_flips=tuple(
            sorted((axis, entity_id, count) for (axis, entity_id), count in flips.items())
        ),
    )


def advisory_findings(report: PartitionReport) -> list[str]:
    """The report rows worth surfacing as ADVISORY findings (never gating).

    Divergences, side flips (the Phase-3+ chattering gate), and multi-occupied
    cells (the §D multiplicity signal). Unpositioned counts stay in the
    summary block — an unwaged capital pole having no wage reading is an
    expected state, not a finding.
    """
    findings: list[str] = []
    for node_id, role, cell in report.divergent_nodes:
        findings.append(f"{report.scenario}: {node_id} seeded '{role}' but derived '{cell}'")
    for axis, node_id, count in report.side_flips:
        findings.append(
            f"{report.scenario}: {node_id} flipped {axis} side {count}x in "
            f"{report.ticks} ticks (chattering instrument)"
        )
    for cell, count in report.multi_occupancy:
        if count > 1:
            findings.append(
                f"{report.scenario}: cell '{cell}' holds {count} nodes (multiplicity signal)"
            )
    return findings


def report_lines(report: PartitionReport) -> list[str]:
    """Human-readable evidence block for one report (the probe's stdout)."""
    rate = (
        "n/a (no cell-bearing nodes)"
        if report.agreement_rate is None
        else (f"{report.agreement_rate:.3f} ({report.agreements}/{report.cell_bearing_count})")
    )
    lines = [
        f"scenario={report.scenario} ticks={report.ticks} class_nodes={report.class_node_count}",
        f"  agreement_rate: {rate}",
        "  unpositioned:   " + ", ".join(f"{axis}={count}" for axis, count in report.unpositioned),
        "  occupancy:      "
        + (
            ", ".join(f"{cell}={count}" for cell, count in report.multi_occupancy)
            or "(no cells formed)"
        ),
    ]
    for node_id, role, cell in report.divergent_nodes:
        lines.append(f"  divergent:      {node_id}: seeded {role} vs derived {cell}")
    for axis, node_id, count in report.side_flips:
        lines.append(f"  flips:          {node_id} on {axis}: {count}")
    return lines
