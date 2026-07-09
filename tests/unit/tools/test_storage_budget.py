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

    def test_baseline_emits_floors_for_delta_critical_tables(self) -> None:
        """Spec-089 Gate C: the delta-critical tables get a two-sided floor.

        ``dynamic_hex_state`` and ``tick_commit`` must never silently drop
        to zero rows/tick (the §1d silent-no-op failure). The floor stores
        the baseline rows/tick; ``check_bundle`` applies ``floor_pct``.
        """
        storage = _storage_block({"dynamic_hex_state": 209.0, "tick_commit": 1.0})
        baseline = storage_budget.generate_baseline(
            storage,
            scope="detroit-tri-county",
            ticks=5,
        )
        assert baseline["floor_pct"] == 50.0
        assert baseline["floors"]["dynamic_hex_state"] == 209.0
        assert baseline["floors"]["tick_commit"] == 1.0

    def test_floors_only_cover_present_delta_tables(self) -> None:
        """A table absent from the run cannot be floored (no data to floor)."""
        storage = _storage_block({"dynamic_hex_state": 209.0})
        baseline = storage_budget.generate_baseline(
            storage,
            scope="detroit-tri-county",
            ticks=5,
        )
        assert "dynamic_hex_state" in baseline["floors"]
        assert "tick_commit" not in baseline["floors"]


class TestCheckBundle:
    def _baseline(self) -> dict:
        return {
            "schema_version": "1.0",
            "generated_from": {"scope": "detroit-tri-county", "ticks": 5},
            "tolerance_pct": 10.0,
            "rows_per_tick": {"dynamic_hex_state": 1045.0, "conservation_audit_log": 17.0},
        }

    def _baseline_with_floors(self) -> dict:
        """A two-sided baseline: ceiling (tolerance_pct) + floor (floor_pct).

        floor_limit(dynamic_hex_state) = 209.0 * (1 - 50/100) = 104.5.
        """
        return {
            "schema_version": "1.0",
            "generated_from": {"scope": "detroit-tri-county", "ticks": 5},
            "tolerance_pct": 10.0,
            "floor_pct": 50.0,
            "rows_per_tick": {"dynamic_hex_state": 209.0, "tick_commit": 1.0},
            "floors": {"dynamic_hex_state": 209.0, "tick_commit": 1.0},
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


class TestFloors:
    """Spec-089 Gate C: two-sided floors catch the silent-zero-writes path.

    A run where hex hydration silently no-ops (0 rows/tick) or the tick
    commit-marker stops being written is a delta-persistence regression
    that the one-sided ceiling check passes today (under-budget = good).
    Floors make it loud.
    """

    def _floored(self) -> dict:
        return TestCheckBundle._baseline_with_floors(TestCheckBundle())

    def test_floor_breach_fails_on_zero_hex_writes(self) -> None:
        """The §1d silent-no-op: hex resolves 0 rows/tick — must FAIL."""
        storage = _storage_block({"dynamic_hex_state": 0.0, "tick_commit": 1.0})
        ok, report = storage_budget.check_bundle(storage, self._floored())
        assert ok is False
        assert any("dynamic_hex_state" in line and "floor" in line for line in report)

    def test_floor_breach_fails_just_below_floor(self) -> None:
        """floor_limit = 104.5; 100 rows/tick is below it — must FAIL."""
        storage = _storage_block({"dynamic_hex_state": 100.0, "tick_commit": 1.0})
        ok, _report = storage_budget.check_bundle(storage, self._floored())
        assert ok is False

    def test_at_floor_passes(self) -> None:
        """floor_limit = 104.5; exactly at the floor is not a breach."""
        storage = _storage_block({"dynamic_hex_state": 104.5, "tick_commit": 1.0})
        ok, _report = storage_budget.check_bundle(storage, self._floored())
        assert ok is True

    def test_above_floor_below_budget_passes(self) -> None:
        """Between floor (104.5) and budget (209) is a legitimate delta run."""
        storage = _storage_block({"dynamic_hex_state": 150.0, "tick_commit": 1.0})
        ok, _report = storage_budget.check_bundle(storage, self._floored())
        assert ok is True

    def test_tick_commit_floor_breach_fails(self) -> None:
        """Markers stop being written (0 rows/tick) — must FAIL."""
        storage = _storage_block({"dynamic_hex_state": 209.0, "tick_commit": 0.0})
        ok, report = storage_budget.check_bundle(storage, self._floored())
        assert ok is False
        assert any("tick_commit" in line and "floor" in line for line in report)

    def test_baseline_without_floors_is_ceiling_only(self) -> None:
        """Backward-compat: a pre-Gate-C baseline (no ``floors`` key) checks
        ceilings only — an under-budget bundle still passes."""
        baseline = TestCheckBundle()._baseline()  # no floors key
        assert "floors" not in baseline
        storage = _storage_block({"dynamic_hex_state": 0.0, "conservation_audit_log": 17.0})
        ok, _report = storage_budget.check_bundle(storage, baseline)
        assert ok is True
