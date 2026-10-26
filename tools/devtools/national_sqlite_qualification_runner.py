"""Serially run and evaluate the national SQLite qualification ladder.

The Rust runner owns campaign creation, every ordinary advance, positive growth
accounting and scoped reads. This driver only samples the actual process
resident set no slower than the frozen interval, invokes the Rust policy
evaluator, and preserves every rung's evidence whether it passes or fails.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

CONTRACT = Path("contracts/national_sqlite_qualification_v1.json")
# Sample four times faster than the frozen 250 ms ceiling so scheduler jitter
# cannot manufacture a sampling-gap failure; the evaluator still enforces 250 ms.
SAMPLE_INTERVAL_NS = 100_000_000
MAX_RSS_BYTES = 4_000_000_000
MAX_GAP_NS = 250_000_000
LADDER: tuple[tuple[str, int], ...] = (
    ("smoke", 2),
    ("window", 52),
    ("aging", 325),
)


class RunnerRefusal(RuntimeError):
    """A safe operator refusal without campaign data or credentials."""


@dataclass(frozen=True)
class MemoryPeak:
    peak_rss_bytes: int
    maximum_gap_ns: int
    samples: tuple[dict[str, int], ...]


def read_rss_bytes(proc_root: Path, pid: int) -> int:
    """Read the kernel's rolled-up resident set for one exact process."""
    path = proc_root / str(pid) / "smaps_rollup"
    try:
        raw = path.read_text(encoding="ascii")
    except FileNotFoundError:
        raise RunnerRefusal("sampled process ended before its resident set was read") from None
    for line in raw.splitlines():
        if line.startswith("Rss:"):
            fields = line.split()
            if len(fields) != 3 or fields[2] != "kB":
                raise RunnerRefusal("resident-set record is malformed")
            try:
                return int(fields[1]) * 1024
            except ValueError:
                raise RunnerRefusal("resident-set record is not an integer") from None
    raise RunnerRefusal("resident-set record has no Rss line")


class MemorySampler:
    """Sample one process resident set at the frozen interval until it exits."""

    def __init__(
        self,
        pid: int,
        *,
        proc_root: Path = Path("/proc"),
        interval_ns: int = SAMPLE_INTERVAL_NS,
        clock: Callable[[], int] = time.monotonic_ns,
        sleep: Callable[[float], None] = time.sleep,
        reader: Callable[[Path, int], int] = read_rss_bytes,
    ) -> None:
        if interval_ns <= 0:
            raise RunnerRefusal("sampling interval must be positive")
        self.pid = pid
        self.proc_root = proc_root
        self.interval_ns = interval_ns
        self.clock = clock
        self.sleep = sleep
        self.reader = reader
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="national-sqlite-rss")
        self._samples: list[dict[str, int]] = []

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> MemoryPeak:
        self._stop.set()
        self._thread.join(timeout=5)
        if self._thread.is_alive():
            raise RunnerRefusal("memory sampler did not stop")
        return self._peak()

    def sample_once(self, elapsed_ns: int) -> None:
        try:
            rss = self.reader(self.proc_root, self.pid)
        except RunnerRefusal:
            return
        self._samples.append({"elapsed_ns": elapsed_ns, "rss_bytes": rss})

    def _run(self) -> None:
        started = self.clock()
        while not self._stop.is_set():
            self.sample_once(self.clock() - started)
            self._stop.wait(self.interval_ns / 1_000_000_000)

    def _peak(self) -> MemoryPeak:
        peak = max((sample["rss_bytes"] for sample in self._samples), default=0)
        gap = 0
        prior: int | None = None
        for sample in self._samples:
            if prior is not None:
                gap = max(gap, sample["elapsed_ns"] - prior)
            prior = sample["elapsed_ns"]
        return MemoryPeak(
            peak_rss_bytes=peak,
            maximum_gap_ns=gap,
            samples=tuple(self._samples),
        )


def executable_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def run_process(
    command: list[str],
    *,
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    memory_path: Path | None,
    environment: dict[str, str],
) -> dict[str, int]:
    """Spawn one measured process, sample it, and preserve its safe evidence."""
    with (
        stdout_path.open("wb") as stdout,
        stderr_path.open("wb") as stderr,
    ):
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=environment,
            stdout=stdout,
            stderr=stderr,
        )
        sampler = MemorySampler(process.pid)
        sampler.start()
        return_code = process.wait()
        peak = sampler.stop()
    if memory_path is not None:
        memory_path.write_text(
            json.dumps(
                {"samples": list(peak.samples)},
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
    if return_code != 0:
        diagnostic = stderr_path.read_text(encoding="utf-8", errors="replace")
        tail = "\n".join(diagnostic.splitlines()[-12:])
        raise RunnerRefusal(
            f"measured command exited {return_code}: {Path(command[0]).name}\n{tail}"
        )
    return {
        "peak_rss_bytes": peak.peak_rss_bytes,
        "maximum_gap_ns": peak.maximum_gap_ns,
        "samples": len(peak.samples),
    }


def require_object(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise RunnerRefusal(f"evidence {name} is not an object")
    return value


def load_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RunnerRefusal(f"evidence {path.name} is unreadable") from error
    if not isinstance(value, dict):
        raise RunnerRefusal(f"evidence {path.name} is not an object")
    return value


def run_controls(repo: Path, directory: Path) -> dict[str, object]:
    """Run the small accounting and Wayne organizer decision-loop controls."""
    directory.mkdir(parents=True, exist_ok=False)
    commands = (
        (
            "small_accounting",
            [
                "cargo",
                "test",
                "-p",
                "babylon-persistence",
                "--lib",
                "sqlite_store::tests",
            ],
        ),
        (
            "wayne_organizer",
            [
                "cargo",
                "test",
                "-p",
                "babylon-persistence",
                "--test",
                "captured_national_organizer",
            ],
        ),
    )
    results = []
    for name, command in commands:
        stdout_path = directory / f"{name}.stdout.log"
        stderr_path = directory / f"{name}.stderr.log"
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            completed = subprocess.run(
                command,
                cwd=repo / "rust",
                stdout=stdout,
                stderr=stderr,
                check=False,
            )
        results.append(
            {
                "control": name,
                "command": " ".join(command),
                "exit_code": completed.returncode,
                "passed": completed.returncode == 0,
            }
        )
        if completed.returncode != 0:
            raise RunnerRefusal(f"control {name} failed")
    value = {
        "schema": "babylon.qualification.national-sqlite.controls.v1",
        "passed": all(result["passed"] for result in results),
        "controls": results,
    }
    (directory / "controls.json").write_text(json.dumps(value, indent=2), encoding="utf-8")
    return value


def run_rung(
    binary: Path,
    repo: Path,
    rung_directory: Path,
    periods: int,
    contract: Path,
    policy_sha256: str,
    environment: dict[str, str],
) -> dict[str, object]:
    """Run one native rung, its cold open, and the frozen-policy evaluation."""
    rung_directory.mkdir(parents=True, exist_ok=False)
    store = rung_directory / "campaign.sqlite"
    process = run_process(
        [
            str(binary),
            "qualify-national",
            "--store",
            str(store),
            "--output",
            str(rung_directory),
            "--periods",
            str(periods),
        ],
        cwd=repo,
        stdout_path=rung_directory / "qualify.stdout.json",
        stderr_path=rung_directory / "qualify.stderr.log",
        memory_path=rung_directory / "memory.json",
        environment=environment,
    )
    cold = run_process(
        [
            str(binary),
            "qualify-open",
            "--store",
            str(store),
            "--output",
            str(rung_directory),
        ],
        cwd=repo,
        stdout_path=rung_directory / "cold-open.stdout.json",
        stderr_path=rung_directory / "cold-open.stderr.log",
        memory_path=None,
        environment=environment,
    )
    completed = subprocess.run(
        [
            str(binary),
            "qualify-evaluate",
            "--run",
            str(rung_directory),
            "--policy",
            str(contract),
            "--policy-sha256",
            policy_sha256,
            "--horizon",
            str(periods),
        ],
        cwd=repo,
        capture_output=True,
        check=False,
        env=environment,
    )
    (rung_directory / "evaluate.stdout.json").write_bytes(completed.stdout)
    (rung_directory / "evaluate.stderr.log").write_bytes(completed.stderr)
    if completed.returncode != 0:
        raise RunnerRefusal(
            f"policy evaluation failed for {periods} periods: "
            + completed.stderr.decode("utf-8", errors="replace")[-1200:]
        )
    evaluation = load_json(rung_directory / "evaluation.json")
    run = load_json(rung_directory / "run.json")
    cold_evidence = load_json(rung_directory / "cold-open.json")
    verdict = require_object(evaluation.get("verdict"), "verdict")
    return {
        "periods": periods,
        "run": run,
        "cold_open": cold_evidence,
        "evaluation": evaluation,
        "process_memory": process,
        "cold_open_memory": cold,
        "passed": bool(verdict.get("passed")),
    }


def contract_digest(contract: Path) -> str:
    return hashlib.sha256(contract.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--rung",
        action="append",
        choices=[name for name, _ in LADDER] + ["controls"],
        default=None,
    )
    arguments = parser.parse_args(argv)
    os.umask(0o077)
    repo = arguments.repo.resolve()
    binary = arguments.binary.resolve()
    output = arguments.output.resolve()
    contract = (repo / CONTRACT).resolve()
    selected = arguments.rung or ["controls"] + [name for name, _ in LADDER]
    if output.exists():
        print("National SQLite qualification refuses an existing output directory", file=sys.stderr)
        return 2
    output.mkdir(parents=True)
    environment = os.environ.copy()
    environment.pop("BABYLON_RUNTIME_DSN", None)
    policy_sha256 = contract_digest(contract)
    rungs: list[dict[str, object]] = []
    ledger: dict[str, object] = {
        "schema": "babylon.qualification.national-sqlite.ladder.v1",
        "contract_sha256": policy_sha256,
        "executable_sha256": executable_digest(binary),
        "build_mode": "debug-opt1" if "debug" in binary.parts else "release",
        "host": {
            "cpu_count": os.cpu_count(),
            "memory_total_bytes": _host_memory_bytes(),
        },
        "rungs": rungs,
    }
    for name in selected:
        if name == "controls":
            rungs.append({"name": "controls", "result": run_controls(repo, output / "controls")})
            continue
        periods = dict(LADDER)[name]
        result = run_rung(
            binary,
            repo,
            output / name,
            periods,
            contract,
            policy_sha256,
            environment,
        )
        rungs.append({"name": name, "result": result})
        (output / "ladder.json").write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    (output / "ladder.json").write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    return 0


def _host_memory_bytes() -> int:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    except OSError:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
