"""Stream the trace.csv artifact from the trace-emission view.

Spec: 064-headless-sim-runner (T025).

The emitter is decoupled from Postgres: it accepts an iterable of
``TraceRow`` instances (or row-shaped tuples / mappings) and writes them
in the canonical 22-column order. Postgres-backed runs feed it the
result of ``SELECT ... FROM view_runtime_trace_emission ORDER BY tick,
entity_id``; unit tests feed synthetic fixtures.

CSV format follows ``contracts/trace_csv_schema.yaml``:

* utf-8 encoding
* RFC 4180 minimal quoting
* trailing newline
* ``""`` for None / NULL (FR-008)
* header row in the order declared below
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from babylon.engine.headless_runner.models import TraceRow

#: Canonical 22-column ordering. MUST match
#: ``contracts/trace_csv_schema.yaml`` and the SQL view.
TRACE_COLUMNS: tuple[str, ...] = (
    "tick",
    "simulated_year",
    "entity_id",
    "entity_kind",
    "v",
    "c",
    "s",
    "k",
    "p_acquiescence",
    "p_revolution",
    "ideology_r",
    "ideology_l",
    "ideology_f",
    "surveillance_coupling",
    "internet_access_pct",
    "biocapacity_stock",
    "energy_stock",
    "raw_material_stock",
    "profit_rate",
    "exploitation_rate",
    "population",
    "employment_proxy",
)


class TraceEmitter:
    """Stream trace rows into a CSV file at the configured path."""

    def __init__(self, output_path: Path) -> None:
        """Open the CSV writer on ``output_path``.

        Args:
            output_path: Filesystem path where trace.csv will be written.
        """
        self._path = output_path
        self._fh = output_path.open("w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._fh, quoting=csv.QUOTE_MINIMAL)
        self._writer.writerow(TRACE_COLUMNS)
        self._row_count = 0

    @property
    def row_count(self) -> int:
        """Number of data rows emitted (excludes header)."""
        return self._row_count

    @property
    def path(self) -> Path:
        """Filesystem path of the written CSV."""
        return self._path

    def write_row(self, row: TraceRow | Mapping[str, Any]) -> None:
        """Emit one trace row in canonical column order."""
        if isinstance(row, TraceRow):
            data: Mapping[str, Any] = row.model_dump()
        else:
            data = row
        cells = [_format_cell(data.get(col)) for col in TRACE_COLUMNS]
        self._writer.writerow(cells)
        self._row_count += 1

    def write_rows(self, rows: Iterable[TraceRow | Mapping[str, Any]]) -> None:
        """Emit many rows; thin wrapper over :meth:`write_row`."""
        for row in rows:
            self.write_row(row)

    def close(self) -> None:
        """Flush + close the underlying file handle."""
        self._fh.close()

    def __enter__(self) -> TraceEmitter:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _format_cell(value: Any) -> str:
    """Render one cell value per the trace_csv contract.

    None becomes ``""``; everything else uses ``str(value)``. This matches
    FR-008 and the ``null_representation`` clause of the YAML contract.
    """
    if value is None:
        return ""
    return str(value)


__all__ = ["TRACE_COLUMNS", "TraceEmitter"]
