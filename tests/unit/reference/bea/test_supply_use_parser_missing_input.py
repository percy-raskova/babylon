"""T021a: Negative test — missing Supply-Use XLSX must halt with clear error.

Per spec.md Edge Case: "Empty source CSVs: halts with clear error rather
than silently producing partial data."
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.reference.bea.ingest.supply_use_parser import (
    BEAIngestError,
    parse_use_summary,
)


@pytest.mark.unit
class TestMissingSupplyUseXLSX:
    """Empty/missing source must produce a clear, immediately-actionable error."""

    def test_missing_path_raises_bea_ingest_error(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist.xlsx"
        with pytest.raises(BEAIngestError) as exc_info:
            list(parse_use_summary(missing, range(2010, 2011), session=None))  # type: ignore[arg-type]
        # The path must appear in the error message so operators can fix it.
        assert str(missing) in str(exc_info.value)
