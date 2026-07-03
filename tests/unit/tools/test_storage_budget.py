"""Unit tests for the storage budget gate (spec-087 FR-012).

``tools/storage_budget.py`` compares a run bundle's manifest ``storage``
block against a committed baseline. Rows/tick is the deterministic signal
(byte counts fluctuate with vacuum timing and are informational only).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Mirror the import path used by tools/*.py (house pattern, see
# test_shared_signature.py).
TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import storage_budget  # type: ignore[import-not-found]  # noqa: E402


def _storage_block(rows_per_tick: dict[str, float]) -> dict:
    """Shape a manifest storage block from a rows/tick map."""
    return {
        "db_total_bytes": 13_631_488,
        "ticks_persisted": 5,
        "tables": [
            {
                "table": name,
                "total_bytes": 1000,
                "session_rows": int(rpt * 5),
                "session_rows_per_tick": rpt,
            }
            for name, rpt in rows_per_tick.items()
        ],
    }


class TestGenerateBaseline:
    def test_baseline_shape(self) -> None:
        storage = _storage_block({"dynamic_hex_state": 1045.0, "conservation_audit_log": 17.0})
        baseline = storage_budget.generate_baseline(
            storage,
            scope="detroit-tri-county",
            ticks=5,
            tolerance_pct=10.0,
        )
        assert baseline["schema_version"] == "1.0"
        assert baseline["generated_from"] == {"scope": "detroit-tri-county", "ticks": 5}
        assert baseline["tolerance_pct"] == 10.0
        assert baseline["rows_per_tick"]["dynamic_hex_state"] == 1045.0
        assert baseline["rows_per_tick"]["conservation_audit_log"] == 17.0


class TestCheckBundle:
    def _baseline(self) -> dict:
        return {
            "schema_version": "1.0",
            "generated_from": {"scope": "detroit-tri-county", "ticks": 5},
            "tolerance_pct": 10.0,
            "rows_per_tick": {"dynamic_hex_state": 1045.0, "conservation_audit_log": 17.0},
        }

    def test_passes_at_baseline(self) -> None:
        storage = _storage_block({"dynamic_hex_state": 1045.0, "conservation_audit_log": 17.0})
        ok, _report = storage_budget.check_bundle(storage, self._baseline())
        assert ok is True

    def test_fails_over_tolerance(self) -> None:
        """+10% tolerance: 1045 * 1.1 = 1149.5; 1200 must fail."""
        storage = _storage_block({"dynamic_hex_state": 1200.0, "conservation_audit_log": 17.0})
        ok, report = storage_budget.check_bundle(storage, self._baseline())
        assert ok is False
        assert any("dynamic_hex_state" in line for line in report)

    def test_passes_within_tolerance(self) -> None:
        storage = _storage_block({"dynamic_hex_state": 1100.0, "conservation_audit_log": 17.0})
        ok, _report = storage_budget.check_bundle(storage, self._baseline())
        assert ok is True

    def test_under_budget_passes(self) -> None:
        """Improvements (e.g. sprint-3 delta persistence) must pass."""
        storage = _storage_block({"dynamic_hex_state": 25.0, "conservation_audit_log": 17.0})
        ok, _report = storage_budget.check_bundle(storage, self._baseline())
        assert ok is True

    def test_table_missing_from_bundle_counts_as_zero(self) -> None:
        storage = _storage_block({"conservation_audit_log": 17.0})
        ok, _report = storage_budget.check_bundle(storage, self._baseline())
        assert ok is True

    def test_unbudgeted_new_table_noted_but_passes(self) -> None:
        storage = _storage_block(
            {
                "dynamic_hex_state": 1045.0,
                "conservation_audit_log": 17.0,
                "brand_new_table": 3.0,
            }
        )
        ok, report = storage_budget.check_bundle(storage, self._baseline())
        assert ok is True
        assert any("brand_new_table" in line for line in report)
