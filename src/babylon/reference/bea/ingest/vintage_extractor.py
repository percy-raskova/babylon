"""Extract the BEA publication ``vintage_published_date`` from XLSX metadata.

Per research.md R10, the BEA XLSX files carry a "Release Date" header
cell or workbook-property field. When that is absent, fall back to the
filesystem mtime as the conservative-best vintage signal.

The vintage is per-workbook (not per-sheet) — BEA publishes a whole
workbook on one release date, even though the workbook holds multiple
year-keyed sheets.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook  # type: ignore[import-untyped]

log = logging.getLogger(__name__)


def extract_vintage_date(xlsx_path: Path) -> date | None:
    """Return the BEA publication date for the workbook at ``xlsx_path``.

    Preference order:

    1. ``Workbook.properties.modified`` (the BEA-set "modified" datetime
       on the file — corresponds to when BEA prepared the release).
    2. ``Workbook.properties.created`` if ``modified`` is absent.
    3. Filesystem mtime of the XLSX file as the last-resort fallback.

    Args:
        xlsx_path: Path to a BEA Supply-Use / Make+Use / TDR XLSX file.

    Returns:
        ``date`` instance, or ``None`` if ``xlsx_path`` does not exist.
    """
    if not xlsx_path.exists():
        return None

    try:
        wb = load_workbook(xlsx_path, read_only=True, data_only=True)
        props = wb.properties
        if props.modified is not None:
            return _datetime_to_date(props.modified)
        if props.created is not None:
            return _datetime_to_date(props.created)
    except Exception:  # noqa: BLE001  — defensive; fall through to mtime
        log.warning(
            "extract_vintage_date: workbook properties unreadable on %s — using mtime",
            xlsx_path,
        )

    return datetime.fromtimestamp(xlsx_path.stat().st_mtime).date()


def _datetime_to_date(value: datetime | date) -> date:
    """Coerce a ``datetime`` to ``date`` (a no-op for inputs that are already dates)."""
    if isinstance(value, datetime):
        return value.date()
    return value
