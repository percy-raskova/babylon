"""Partition sentinel (Program 19, ADR070): seeded-vs-derived class evidence.

Registry = the canonical derived-cell vocabulary + the cell→SocialRole
crosswalk; checks = the pure analyzer. The engine-running probe harness lives
in ``tools/partition_probe.py`` (this package stays at layer 0.5).
"""

from babylon.sentinels.partition.checks import (
    PartitionReport,
    advisory_findings,
    analyze_partition,
    report_lines,
)
from babylon.sentinels.partition.registry import (
    CELL_AXIS_NAMES,
    CELL_TO_SEEDED_ROLES,
    KNOWN_CELLS,
    PRINCIPAL_AXES,
    cell_name,
)

__all__ = [
    "CELL_AXIS_NAMES",
    "CELL_TO_SEEDED_ROLES",
    "KNOWN_CELLS",
    "PRINCIPAL_AXES",
    "PartitionReport",
    "advisory_findings",
    "analyze_partition",
    "cell_name",
    "report_lines",
]
