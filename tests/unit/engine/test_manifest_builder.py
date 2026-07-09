"""Unit tests for the manifest.json builder (T018, spec-064).

Validates that ``input_hash`` is stable across two builds with identical
deterministic inputs (i.e., canonical JSON serialization is in fact
canonical), and that the manifest payload mirrors
``contracts/manifest_json_schema.yaml``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from babylon.engine.headless_runner.manifest import (
    TRACE_COLUMN_DICT,
    build_manifest,
    input_hash,
)
from babylon.engine.headless_runner.models import (
    ExitReason,
    ScheduledBlocShock,
    SimulationRunConfig,
)


def _make_config(tmp_path: Path) -> SimulationRunConfig:
    return SimulationRunConfig(
        ticks=100,
        start_year=2010,
        random_seed=2010,
        scope_name="detroit-tri-county",
        scope_fips=frozenset({"26163", "26125", "26099"}),
        external_node_ids=frozenset({"canada"}),
        output_dir=tmp_path,
    )


def _write_artifact(
    tmp_path: Path, name: str, body: str = "stub\n"
) -> tuple[str, str, int, int | None]:
    """Write a stub file + return the artifact_files tuple shape."""
    p = tmp_path / name
    p.write_text(body)
    return (name, f"{name.split('.')[0]}_v1", p.stat().st_size, None)


class TestInputHashDeterminism:
    """SHA-256 over deterministic_inputs is stable across rebuilds."""

    def test_identical_inputs_yield_identical_hash(self) -> None:
        inputs = {
            "seed": 2010,
            "ticks": 100,
            "start_year": 2010,
            "scope_fips": ["26099", "26125", "26163"],
            "external_node_ids": ["canada"],
            "defines_hash": "deadbeef" * 8,
            "data_versions": {"tiger_vintage": "2024", "lodes_max_year": 2022},
        }
        assert input_hash(inputs) == input_hash(inputs)

    def test_different_seed_yields_different_hash(self) -> None:
        base = {
            "seed": 2010,
            "ticks": 100,
            "start_year": 2010,
            "scope_fips": ["26099"],
            "external_node_ids": [],
            "defines_hash": "x",
            "data_versions": {},
        }
        other = dict(base, seed=99)
        assert input_hash(base) != input_hash(other)

    def test_key_order_invariant(self) -> None:
        """Differently-ordered dicts MUST produce identical hashes."""
        a = {"seed": 2010, "ticks": 100, "data_versions": {}}
        b = {"ticks": 100, "data_versions": {}, "seed": 2010}
        assert input_hash(a) == input_hash(b)


class TestManifestPayload:
    """Manifest dict has the contracted shape and key set."""

    def test_top_level_keys(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        trace = _write_artifact(tmp_path, "trace.csv")
        summary = _write_artifact(tmp_path, "summary.json")
        manifest = build_manifest(
            config=config,
            session_id="01234567-89ab-cdef-0123-456789abcdef",
            exit_reason=ExitReason.COMPLETED,
            wallclock_start=datetime(2026, 5, 14, 16, 30, tzinfo=UTC),
            wallclock_end=datetime(2026, 5, 14, 16, 38, 42, tzinfo=UTC),
            artifact_dir=tmp_path,
            artifact_files=[trace, summary],
            defines_hash="d" * 64,
            data_versions={"tiger_vintage": "2024"},
        )
        assert manifest["schema_version"] == "1.0"
        for k in ("generator", "files", "reproducibility", "column_dictionaries"):
            assert k in manifest

    def test_generator_partial_flag(self, tmp_path: Path) -> None:
        """``partial`` is True iff exit_reason ∈ (user_interrupted, errored)."""
        config = _make_config(tmp_path)
        common = {
            "config": config,
            "session_id": "00000000-0000-0000-0000-000000000000",
            "wallclock_start": datetime(2026, 5, 14, 16, 30, tzinfo=UTC),
            "wallclock_end": datetime(2026, 5, 14, 16, 38, tzinfo=UTC),
            "artifact_dir": tmp_path,
            "artifact_files": [_write_artifact(tmp_path, "trace.csv")],
            "defines_hash": "d" * 64,
            "data_versions": {},
        }
        assert (
            build_manifest(exit_reason=ExitReason.COMPLETED, **common)["generator"]["partial"]
            is False
        )
        assert (
            build_manifest(exit_reason=ExitReason.EARLY_TERMINATED, **common)["generator"][
                "partial"
            ]
            is False
        )
        assert (
            build_manifest(exit_reason=ExitReason.USER_INTERRUPTED, **common)["generator"][
                "partial"
            ]
            is True
        )
        assert (
            build_manifest(exit_reason=ExitReason.ERRORED, **common)["generator"]["partial"] is True
        )

    def test_column_dictionary_has_22_entries(self) -> None:
        assert len(TRACE_COLUMN_DICT) == 22
        for entry in TRACE_COLUMN_DICT:
            assert "name" in entry
            assert "type" in entry
            assert "units" in entry
            assert "semantics" in entry
            assert "nullable" in entry

    def test_storage_block_included_when_provided(self, tmp_path: Path) -> None:
        """Spec-087 FR-009: optional ``storage`` block lands top-level."""
        config = _make_config(tmp_path)
        storage = {
            "db_total_bytes": 13_631_488,
            "ticks_persisted": 5,
            "tables": [
                {
                    "table": "dynamic_hex_state",
                    "total_bytes": 1_523_712,
                    "session_rows": 5225,
                    "session_rows_per_tick": 1045.0,
                }
            ],
        }
        manifest = build_manifest(
            config=config,
            session_id="00000000-0000-0000-0000-000000000000",
            exit_reason=ExitReason.COMPLETED,
            wallclock_start=datetime(2026, 7, 3, 16, 30, tzinfo=UTC),
            wallclock_end=datetime(2026, 7, 3, 16, 38, tzinfo=UTC),
            artifact_dir=tmp_path,
            artifact_files=[_write_artifact(tmp_path, "trace.csv")],
            defines_hash="d" * 64,
            data_versions={},
            storage=storage,
        )
        assert manifest["storage"] == storage

    def test_storage_block_absent_when_not_provided(self, tmp_path: Path) -> None:
        """Storage collection is best-effort; None must leave no key behind."""
        config = _make_config(tmp_path)
        manifest = build_manifest(
            config=config,
            session_id="00000000-0000-0000-0000-000000000000",
            exit_reason=ExitReason.COMPLETED,
            wallclock_start=datetime(2026, 7, 3, 16, 30, tzinfo=UTC),
            wallclock_end=datetime(2026, 7, 3, 16, 38, tzinfo=UTC),
            artifact_dir=tmp_path,
            artifact_files=[_write_artifact(tmp_path, "trace.csv")],
            defines_hash="d" * 64,
            data_versions={},
        )
        assert "storage" not in manifest

    def test_economics_fallbacks_block_included_when_provided(self, tmp_path: Path) -> None:
        """C.8 (spec 2.R): optional ``economics_fallbacks`` block lands top-level."""
        config = _make_config(tmp_path)
        fallbacks = {
            "national_params_observations": 11,
            "melt_calculator_wired": True,
            "basket_calculator_wired": False,
            "gamma_calculator_wired": True,
            "melt_unavailable": 0,
            "gamma_basket_calculator_none": 11,
            "gamma_iii_calculator_none": 0,
            "gamma_iii_returned_none": 0,
        }
        manifest = build_manifest(
            config=config,
            session_id="00000000-0000-0000-0000-000000000000",
            exit_reason=ExitReason.COMPLETED,
            wallclock_start=datetime(2026, 7, 3, 16, 30, tzinfo=UTC),
            wallclock_end=datetime(2026, 7, 3, 16, 38, tzinfo=UTC),
            artifact_dir=tmp_path,
            artifact_files=[_write_artifact(tmp_path, "trace.csv")],
            defines_hash="d" * 64,
            data_versions={},
            economics_fallbacks=fallbacks,
        )
        assert manifest["economics_fallbacks"] == fallbacks

    def test_economics_fallbacks_block_absent_when_not_provided(self, tmp_path: Path) -> None:
        """None economics_fallbacks must leave no key behind (pre-C.8 / non-bridged)."""
        config = _make_config(tmp_path)
        manifest = build_manifest(
            config=config,
            session_id="00000000-0000-0000-0000-000000000000",
            exit_reason=ExitReason.COMPLETED,
            wallclock_start=datetime(2026, 7, 3, 16, 30, tzinfo=UTC),
            wallclock_end=datetime(2026, 7, 3, 16, 38, tzinfo=UTC),
            artifact_dir=tmp_path,
            artifact_files=[_write_artifact(tmp_path, "trace.csv")],
            defines_hash="d" * 64,
            data_versions={},
        )
        assert "economics_fallbacks" not in manifest

    def test_economics_fallbacks_excluded_from_input_hash(self, tmp_path: Path) -> None:
        """Observability block must NOT enter the deterministic input_hash."""
        config = _make_config(tmp_path)
        common: dict[str, object] = {
            "config": config,
            "session_id": "00000000-0000-0000-0000-000000000000",
            "exit_reason": ExitReason.COMPLETED,
            "wallclock_start": datetime(2026, 7, 3, 16, 30, tzinfo=UTC),
            "wallclock_end": datetime(2026, 7, 3, 16, 38, tzinfo=UTC),
            "artifact_dir": tmp_path,
            "artifact_files": [_write_artifact(tmp_path, "trace.csv")],
            "defines_hash": "d" * 64,
            "data_versions": {},
        }
        without = build_manifest(**common)  # type: ignore[arg-type]
        with_block = build_manifest(
            **common,  # type: ignore[arg-type]
            economics_fallbacks={"gamma_basket_calculator_none": 11},
        )
        assert (
            without["reproducibility"]["input_hash"] == with_block["reproducibility"]["input_hash"]
        )

    def test_file_entry_includes_sha256_and_size(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        trace = _write_artifact(tmp_path, "trace.csv", body="header\n0,2010.0\n")
        manifest = build_manifest(
            config=config,
            session_id="00000000-0000-0000-0000-000000000000",
            exit_reason=ExitReason.COMPLETED,
            wallclock_start=datetime(2026, 5, 14, 16, 30, tzinfo=UTC),
            wallclock_end=datetime(2026, 5, 14, 16, 38, tzinfo=UTC),
            artifact_dir=tmp_path,
            artifact_files=[trace],
            defines_hash="d" * 64,
            data_versions={},
        )
        entry = manifest["files"][0]
        assert entry["name"] == "trace.csv"
        assert len(entry["sha256"]) == 64
        assert entry["size_bytes"] > 0


class TestShockScheduleInInputHash:
    """shock_schedule is determinism-relevant and must participate in input_hash."""

    def _build(self, tmp_path: Path, shock_schedule: tuple[ScheduledBlocShock, ...] = ()) -> dict:
        config = SimulationRunConfig(
            ticks=100,
            start_year=2010,
            random_seed=2010,
            scope_name="detroit-tri-county",
            scope_fips=frozenset({"26163", "26125", "26099"}),
            external_node_ids=frozenset({"canada"}),
            output_dir=tmp_path,
            shock_schedule=shock_schedule,
        )
        _write_artifact(tmp_path, "trace.csv")
        return build_manifest(
            config=config,
            session_id="00000000-0000-0000-0000-000000000000",
            exit_reason=ExitReason.COMPLETED,
            wallclock_start=datetime(2026, 7, 4, 12, 0, tzinfo=UTC),
            wallclock_end=datetime(2026, 7, 4, 12, 5, tzinfo=UTC),
            artifact_dir=tmp_path,
            artifact_files=[_write_artifact(tmp_path, "trace.csv")],
            defines_hash="d" * 64,
            data_versions={},
        )

    def test_different_shock_schedules_produce_different_hash(self, tmp_path: Path) -> None:
        no_shocks = self._build(tmp_path)
        with_shock = self._build(
            tmp_path,
            shock_schedule=(ScheduledBlocShock(tick=52, bloc="china", phi_multiplier=2.0),),
        )
        assert (
            no_shocks["reproducibility"]["input_hash"]
            != with_shock["reproducibility"]["input_hash"]
        )

    def test_identical_shock_schedules_produce_same_hash(self, tmp_path: Path) -> None:
        shock = (ScheduledBlocShock(tick=52, bloc="china", phi_multiplier=2.0),)
        a = self._build(tmp_path, shock_schedule=shock)
        b = self._build(tmp_path, shock_schedule=shock)
        assert a["reproducibility"]["input_hash"] == b["reproducibility"]["input_hash"]
