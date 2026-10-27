"""The ladder driver only samples and preserves evidence; the Rust policy decides."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from tools.devtools import national_sqlite_qualification_runner as runner


def write_rollup(root: Path, pid: int, rss_kb: int) -> None:
    directory = root / str(pid)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "smaps_rollup").write_text(
        f"Rss:  {rss_kb} kB\nPss:                 1 kB\n",
        encoding="ascii",
    )


def test_reads_the_kernel_rolled_up_resident_set(tmp_path: Path) -> None:
    write_rollup(tmp_path, 17, 2048)
    assert runner.read_rss_bytes(tmp_path, 17) == 2048 * 1024


def test_refuses_a_missing_or_malformed_resident_set(tmp_path: Path) -> None:
    with pytest.raises(runner.RunnerRefusal):
        runner.read_rss_bytes(tmp_path, 99)
    write_rollup(tmp_path, 17, 1)
    (tmp_path / "17" / "smaps_rollup").write_text("Pss: 1 kB\n", encoding="ascii")
    with pytest.raises(runner.RunnerRefusal):
        runner.read_rss_bytes(tmp_path, 17)
    (tmp_path / "17" / "smaps_rollup").write_text("Rss: nope kB\n", encoding="ascii")
    with pytest.raises(runner.RunnerRefusal):
        runner.read_rss_bytes(tmp_path, 17)


def test_peak_and_gap_are_measured_from_exact_samples(tmp_path: Path) -> None:
    write_rollup(tmp_path, 17, 1024)
    sampler = runner.MemorySampler(17, proc_root=tmp_path)
    sampler.sample_once(0)
    write_rollup(tmp_path, 17, 4096)
    sampler.sample_once(250_000_000)
    sampler.sample_once(500_000_000)
    peak = sampler._peak()
    assert peak.peak_rss_bytes == 4096 * 1024
    assert peak.maximum_gap_ns == 250_000_000
    assert len(peak.samples) == 3


def test_process_sampling_preserves_evidence_and_refuses_failure(tmp_path: Path) -> None:
    memory = tmp_path / "memory.json"
    result = runner.run_process(
        [sys.executable, "-c", "import time; time.sleep(0.35)"],
        cwd=tmp_path,
        stdout_path=tmp_path / "stdout.log",
        stderr_path=tmp_path / "stderr.log",
        memory_path=memory,
        environment={},
    )
    assert result["samples"] >= 1
    assert json.loads(memory.read_text(encoding="utf-8"))["samples"]
    with pytest.raises(runner.RunnerRefusal):
        runner.run_process(
            [sys.executable, "-c", "import sys; sys.exit(3)"],
            cwd=tmp_path,
            stdout_path=tmp_path / "bad.stdout.log",
            stderr_path=tmp_path / "bad.stderr.log",
            memory_path=tmp_path / "bad-memory.json",
            environment={},
        )


def test_ladder_runs_the_frozen_uncapped_sequence() -> None:
    assert [name for name, _ in runner.LADDER] == ["smoke", "window", "aging"]
    assert dict(runner.LADDER) == {"smoke": 2, "window": 52, "aging": 325}


def test_contract_records_the_interim_advance_bar_and_its_target_debt() -> None:
    contract = json.loads(
        (
            Path(__file__).resolve().parents[3] / "contracts/national_sqlite_qualification_v1.json"
        ).read_text(encoding="utf-8")
    )
    assert contract["version"] == 2
    assert contract["name"] == "national_sqlite_qualification_v1"
    assert contract["storage_charge_method"] == ("positive_growth_by_component_and_boundary_v1")
    assert contract["maximum_combined_running_game_memory_bytes"] == 4_000_000_000
    assert contract["memory_sample_interval_nanoseconds"] == 250_000_000
    assert contract["advance_bar"] == "interim"
    assert contract["maximum_advance_nanoseconds"] == 60_000_000_000
    assert contract["target_maximum_advance_nanoseconds"] == 30_000_000_000
    assert contract["optimization_debt"] == [
        {
            "metric": "advance",
            "interim_limit_nanoseconds": 60_000_000_000,
            "target_limit_nanoseconds": 30_000_000_000,
        }
    ]
    assert contract["maximum_cold_open_nanoseconds"] == 30_000_000_000
    assert contract["maximum_warm_query_nanoseconds"] == 1_000_000_000
    assert contract["maximum_cold_query_nanoseconds"] == 2_000_000_000
    assert contract["maximum_charged_growth_bytes_per_period"] == 10_000_000
    assert contract["maximum_charged_growth_bytes_13_periods"] == 130_000_000
    assert contract["maximum_charged_growth_bytes_52_periods"] == 520_000_000
    assert contract["maximum_charged_growth_bytes_325_periods"] == 3_250_000_000
    assert contract["qualification_periods"] == 325


def test_each_verdict_is_named_after_the_contract_that_produced_it(tmp_path: Path) -> None:
    first = runner.evaluation_path(tmp_path, "a" * 64)
    second = runner.evaluation_path(tmp_path, "b" * 64)
    assert first.name == f"evaluation-{'a' * 64}.json"
    assert first != second
    assert first.parent == second.parent == tmp_path
    for malformed in ("A" * 64, "a" * 63, "a" * 65, "g" * 64):
        with pytest.raises(runner.RunnerRefusal):
            runner.evaluation_path(tmp_path, malformed)
