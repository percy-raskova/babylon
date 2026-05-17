"""Unit tests for the summary.json builder (T017, spec-064).

Validates that the summary payload satisfies the top-level key contract
in ``contracts/summary_json_schema.yaml`` and that optional sections
(``end_game_event``, ``error``) are gated on the corresponding
``exit_reason``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from babylon.engine.headless_runner.models import (
    AuditEntry,
    ExitReason,
    PerformanceBreakdown,
    SimulationRunConfig,
)
from babylon.engine.headless_runner.run_summary import build_summary


def _config(tmp_path: Path) -> SimulationRunConfig:
    return SimulationRunConfig(
        ticks=100,
        scope_name="detroit-tri-county",
        scope_fips=frozenset({"26163", "26125", "26099"}),
        output_dir=tmp_path,
    )


def _perf() -> PerformanceBreakdown:
    return PerformanceBreakdown(
        total_wallclock_sec=10.0,
        session_init_sec=1.0,
        hex_hydration_sec=0.5,
        tick_loop_sec=8.4,
        artifact_emission_sec=0.1,
        per_tick_median_ms=40.0,
        per_tick_p99_ms=80.0,
        per_tick_max_ms=120.0,
    )


def _terminal_state() -> dict[str, object]:
    return {
        "tick": 99,
        "counties_alive": 3,
        "total_population": 4_400_000,
        "total_v": 1_000_000.0,
        "total_c": 2_000_000.0,
        "total_s": 500_000.0,
        "total_k": 8_000_000.0,
        "mean_p_acquiescence": 0.6,
        "mean_p_revolution": 0.4,
        "mean_ideology_r": 0.5,
        "mean_ideology_l": 0.3,
        "mean_ideology_f": 0.2,
    }


class TestSummaryShape:
    """Required top-level keys are always present."""

    def test_completed_run_has_all_required_keys(self, tmp_path: Path) -> None:
        summary = build_summary(
            config=_config(tmp_path),
            session_id="00000000-0000-0000-0000-000000000000",
            exit_reason=ExitReason.COMPLETED,
            ticks_completed=100,
            wallclock_start=datetime(2026, 5, 14, 16, 30, tzinfo=UTC),
            wallclock_end=datetime(2026, 5, 14, 16, 38, tzinfo=UTC),
            terminal_state=_terminal_state(),
            external_node_flows=[],
            county_terminal_snapshot=[],
            conservation_audit=[],
            performance=_perf(),
        )
        for k in (
            "schema_version",
            "run_metadata",
            "terminal_state",
            "external_node_flows",
            "county_terminal_snapshot",
            "conservation_audit",
            "performance",
        ):
            assert k in summary
        assert summary["schema_version"] == "1.0"
        # Optional sections absent on clean completion.
        assert "end_game_event" not in summary
        assert "error" not in summary

    def test_run_metadata_echoes_config(self, tmp_path: Path) -> None:
        config = _config(tmp_path)
        summary = build_summary(
            config=config,
            session_id="01234567-89ab-cdef-0123-456789abcdef",
            exit_reason=ExitReason.COMPLETED,
            ticks_completed=100,
            wallclock_start=datetime(2026, 5, 14, 16, 30, tzinfo=UTC),
            wallclock_end=datetime(2026, 5, 14, 16, 38, tzinfo=UTC),
            terminal_state=_terminal_state(),
            external_node_flows=[],
            county_terminal_snapshot=[],
            conservation_audit=[],
            performance=_perf(),
        )
        meta = summary["run_metadata"]
        assert meta["session_id"] == "01234567-89ab-cdef-0123-456789abcdef"
        assert meta["exit_reason"] == "completed"
        assert meta["ticks_requested"] == 100
        assert meta["ticks_completed"] == 100
        assert meta["start_year"] == 2010
        assert meta["seed"] == 2010
        assert meta["scope_name"] == "detroit-tri-county"
        assert sorted(meta["scope_fips"]) == ["26099", "26125", "26163"]

    def test_end_game_event_present_on_early_termination(self, tmp_path: Path) -> None:
        summary = build_summary(
            config=_config(tmp_path),
            session_id="00000000-0000-0000-0000-000000000000",
            exit_reason=ExitReason.EARLY_TERMINATED,
            ticks_completed=50,
            wallclock_start=datetime(2026, 5, 14, 16, 30, tzinfo=UTC),
            wallclock_end=datetime(2026, 5, 14, 16, 32, tzinfo=UTC),
            terminal_state=_terminal_state(),
            external_node_flows=[],
            county_terminal_snapshot=[],
            conservation_audit=[],
            performance=_perf(),
            end_game_event={
                "tick": 50,
                "condition": "IMPERIAL_COLLAPSE",
                "details": {"trigger": "phi_collapse"},
            },
        )
        assert summary["end_game_event"]["condition"] == "IMPERIAL_COLLAPSE"
        assert summary["end_game_event"]["tick"] == 50

    def test_error_block_present_on_errored(self, tmp_path: Path) -> None:
        summary = build_summary(
            config=_config(tmp_path),
            session_id="00000000-0000-0000-0000-000000000000",
            exit_reason=ExitReason.ERRORED,
            ticks_completed=42,
            wallclock_start=datetime(2026, 5, 14, 16, 30, tzinfo=UTC),
            wallclock_end=datetime(2026, 5, 14, 16, 31, tzinfo=UTC),
            terminal_state=_terminal_state(),
            external_node_flows=[],
            county_terminal_snapshot=[],
            conservation_audit=[],
            performance=_perf(),
            error={
                "type": "ValueError",
                "message": "boom",
                "tick": 42,
                "traceback": "Traceback...",
            },
        )
        assert summary["error"]["type"] == "ValueError"
        assert summary["error"]["tick"] == 42

    def test_audit_entries_serialize_to_plain_dicts(self, tmp_path: Path) -> None:
        audits = [
            AuditEntry(
                tick=10,
                invariant_name="US1_no_double_counting",
                severity="warning",
                details={"discrepancy_pct": 0.01},
            ),
        ]
        summary = build_summary(
            config=_config(tmp_path),
            session_id="00000000-0000-0000-0000-000000000000",
            exit_reason=ExitReason.COMPLETED,
            ticks_completed=100,
            wallclock_start=datetime(2026, 5, 14, 16, 30, tzinfo=UTC),
            wallclock_end=datetime(2026, 5, 14, 16, 38, tzinfo=UTC),
            terminal_state=_terminal_state(),
            external_node_flows=[],
            county_terminal_snapshot=[],
            conservation_audit=audits,
            performance=_perf(),
        )
        assert len(summary["conservation_audit"]) == 1
        entry = summary["conservation_audit"][0]
        assert entry["tick"] == 10
        assert entry["invariant_name"] == "US1_no_double_counting"
        assert entry["severity"] == "warning"
        # Round-trip through JSON to prove there's nothing un-serializable.
        json.dumps(summary)
