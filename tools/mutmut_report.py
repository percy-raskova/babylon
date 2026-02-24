#!/usr/bin/env python3
"""Parse mutmut .meta files and produce mutation testing reports.

Subcommands:
    report    Print human-readable summary, write reports/mutation_report.json
    baseline  Snapshot current scores to tests/baselines/mutation_baseline.json

Flags:
    --diff    (report only) Compare against baseline and show deltas

Exit code mapping (from mutmut .meta files):
    1  = killed      (test caught the mutation)
    0  = survived    (test missed the mutation)
    33 = no_tests    (no tests cover this code)
    -6 = suspicious  (potential code quality issue)
   -24 = timeout     (mutant caused infinite loop or hang)

Score formula: killed / (killed + survived) * 100
    Excludes no_tests/suspicious/timeout from denominator.

See Also:
    :func:`tools.run_mutmut.main` for running mutation tests
    ADR036 for shared tooling rationale
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

# =============================================================================
# CONSTANTS
# =============================================================================

MUTANTS_DIR: Final[Path] = Path("mutants")
REPORT_PATH: Final[Path] = Path("reports/mutation_report.json")
BASELINE_PATH: Final[Path] = Path("tests/baselines/mutation_baseline.json")

EXIT_CODE_LABELS: Final[dict[int, str]] = {
    1: "killed",
    0: "survived",
    33: "no_tests",
    -6: "suspicious",
    -24: "timeout",
}

# mutmut uses ǁ (U+01C1) as class/method separator
CLASS_SEP: Final[str] = "\u01c1"


# =============================================================================
# DATA STRUCTURES
# =============================================================================


@dataclass
class FunctionStats:
    """Mutation stats for a single function or method."""

    name: str
    killed: int = 0
    survived: int = 0
    no_tests: int = 0
    suspicious: int = 0
    timeout: int = 0
    survivors: list[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        denom = self.killed + self.survived
        if denom == 0:
            return 100.0
        return self.killed / denom * 100.0


@dataclass
class FileStats:
    """Mutation stats for a single source file."""

    path: str
    functions: dict[str, FunctionStats] = field(default_factory=dict)

    def _sum(self, attr: str) -> int:
        return sum(getattr(f, attr) for f in self.functions.values())

    @property
    def killed(self) -> int:
        return self._sum("killed")

    @property
    def survived(self) -> int:
        return self._sum("survived")

    @property
    def no_tests(self) -> int:
        return self._sum("no_tests")

    @property
    def suspicious(self) -> int:
        return self._sum("suspicious")

    @property
    def timeout(self) -> int:
        return self._sum("timeout")

    @property
    def total(self) -> int:
        return self.killed + self.survived + self.no_tests + self.suspicious + self.timeout

    @property
    def score(self) -> float:
        denom = self.killed + self.survived
        if denom == 0:
            return 100.0
        return self.killed / denom * 100.0


# =============================================================================
# PARSING
# =============================================================================


def _meta_to_source(meta_path: Path) -> str:
    """Convert .meta file path to source file path.

    Example:
        mutants/src/babylon/foo.py.meta -> src/babylon/foo.py
    """
    # Strip mutants/ prefix and .meta suffix
    relative = meta_path.relative_to(MUTANTS_DIR)
    return str(relative).removesuffix(".meta")


def _parse_function_name(mutant_key: str) -> str:
    """Extract human-readable function name from mutant key.

    Examples:
        babylon.formulas.foo.x_calculate_rent__mutmut_5  -> calculate_rent
        babylon.tick.system.xǁMyClassǁmethod__mutmut_3  -> MyClass.method
    """
    # Split on .x to separate module path from function spec
    parts = mutant_key.split(".x", 1)
    if len(parts) < 2:
        return mutant_key
    func_spec = parts[1]

    # Strip __mutmut_N suffix
    if "__mutmut_" in func_spec:
        func_spec = func_spec[: func_spec.rindex("__mutmut_")]

    # Handle class methods: ǁClassǁmethod -> Class.method
    if CLASS_SEP in func_spec:
        segments = func_spec.split(CLASS_SEP)
        # Filter empty segments (leading separator)
        segments = [s for s in segments if s]
        return ".".join(segments)

    # Free function: strip leading underscore from x_ prefix
    if func_spec.startswith("_"):
        func_spec = func_spec[1:]
    return func_spec


def parse_meta_files() -> list[FileStats]:
    """Parse all .meta files under mutants/ and return per-file stats."""
    results: list[FileStats] = []

    for meta_path in sorted(MUTANTS_DIR.rglob("*.meta")):
        raw = json.loads(meta_path.read_text())
        exit_codes: dict[str, int] = raw.get("exit_code_by_key", {})

        if not exit_codes:
            continue

        source_path = _meta_to_source(meta_path)
        file_stats = FileStats(path=source_path)

        for mutant_key, code in exit_codes.items():
            func_name = _parse_function_name(mutant_key)
            label = EXIT_CODE_LABELS.get(code, f"unknown_{code}")

            if func_name not in file_stats.functions:
                file_stats.functions[func_name] = FunctionStats(name=func_name)

            func = file_stats.functions[func_name]
            if label == "killed":
                func.killed += 1
            elif label == "survived":
                func.survived += 1
                func.survivors.append(mutant_key)
            elif label == "no_tests":
                func.no_tests += 1
            elif label == "suspicious":
                func.suspicious += 1
            elif label == "timeout":
                func.timeout += 1

        results.append(file_stats)

    return results


# =============================================================================
# REPORT GENERATION
# =============================================================================


def _git_commit_short() -> str:
    """Get short git commit hash, or 'unknown' on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return "unknown"


def _score(killed: int, survived: int) -> float:
    denom = killed + survived
    if denom == 0:
        return 100.0
    return round(killed / denom * 100, 1)


def build_report_json(files: list[FileStats]) -> dict[str, Any]:
    """Build the full JSON report structure."""
    totals: dict[str, int] = defaultdict(int)
    for f in files:
        totals["killed"] += f.killed
        totals["survived"] += f.survived
        totals["no_tests"] += f.no_tests
        totals["suspicious"] += f.suspicious
        totals["timeout"] += f.timeout

    total = sum(totals.values())
    global_score = _score(totals["killed"], totals["survived"])

    # Sort files by survivor count descending
    sorted_files = sorted(files, key=lambda f: f.survived, reverse=True)

    file_entries = []
    for f in sorted_files:
        # Sort functions by survivor count descending
        sorted_funcs = sorted(f.functions.values(), key=lambda fn: fn.survived, reverse=True)
        func_entries = [
            {
                "name": fn.name,
                "killed": fn.killed,
                "survived": fn.survived,
                "score": round(fn.score, 1),
                "survivors": fn.survivors,
            }
            for fn in sorted_funcs
            if fn.survived > 0  # Only include functions with survivors
        ]
        file_entries.append(
            {
                "path": f.path,
                "killed": f.killed,
                "survived": f.survived,
                "no_tests": f.no_tests,
                "suspicious": f.suspicious,
                "timeout": f.timeout,
                "score": round(f.score, 1),
                "functions": func_entries,
            }
        )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit_short(),
        "global": {
            "total": total,
            "killed": totals["killed"],
            "survived": totals["survived"],
            "no_tests": totals["no_tests"],
            "suspicious": totals["suspicious"],
            "timeout": totals["timeout"],
            "score": global_score,
        },
        "files": file_entries,
    }


def print_summary(report: dict[str, Any]) -> None:
    """Print human-readable summary table to stdout."""
    g = report["global"]
    print(f"\nMutation Testing Report (commit {report['git_commit']})")
    print("=" * 60)
    print(f"  Total mutants:  {g['total']:>6}")
    print(f"  Killed:         {g['killed']:>6}  (tests caught mutation)")
    print(f"  Survived:       {g['survived']:>6}  (tests missed mutation)")
    print(f"  No tests:       {g['no_tests']:>6}  (no covering tests)")
    print(f"  Suspicious:     {g['suspicious']:>6}  (code quality issues)")
    print(f"  Timeout:        {g['timeout']:>6}  (hung/infinite loop)")
    print(f"  Score:          {g['score']:>5.1f}%  killed/(killed+survived)")
    print()

    files = report["files"]
    if not files:
        print("  No mutation results found.")
        return

    # Per-file breakdown (top 20 worst offenders)
    MAX_ROWS = 20
    print(f"{'File':<55} {'Kill':>5} {'Surv':>5} {'Score':>6}")
    print("-" * 75)
    for entry in files[:MAX_ROWS]:
        short_path = entry["path"].removeprefix("src/babylon/")
        print(
            f"  {short_path:<53} {entry['killed']:>5} {entry['survived']:>5} {entry['score']:>5.1f}%"
        )

    remaining = len(files) - MAX_ROWS
    if remaining > 0:
        print(f"  ... and {remaining} more files")
    print()


def print_diff(report: dict[str, Any]) -> None:
    """Compare report against baseline and print deltas."""
    if not BASELINE_PATH.exists():
        print(f"No baseline found at {BASELINE_PATH}")
        print("Run: poetry run python tools/mutmut_report.py baseline")
        sys.exit(1)

    baseline = json.loads(BASELINE_PATH.read_text())
    bl_global = baseline["global"]
    rp_global = report["global"]

    bl_files: dict[str, dict[str, Any]] = baseline.get("files", {})

    delta = rp_global["score"] - bl_global["score"]
    print(
        f"\nMutation Score Delta (vs baseline {baseline.get('generated_at', '?')[:10]} @ {baseline.get('git_commit', '?')})"
    )
    print("=" * 60)
    print(f"Global: {bl_global['score']:.1f}% -> {rp_global['score']:.1f}% ({delta:+.1f}%)")
    print()

    improved: list[tuple[float, str, float, float]] = []
    regressed: list[tuple[float, str, float, float]] = []
    unchanged = 0

    for entry in report["files"]:
        path = entry["path"]
        new_score = entry["score"]
        if path in bl_files:
            old_score = bl_files[path]["score"]
            file_delta = new_score - old_score
            if file_delta > 0.05:
                improved.append((file_delta, path, old_score, new_score))
            elif file_delta < -0.05:
                regressed.append((file_delta, path, old_score, new_score))
            else:
                unchanged += 1
        # New files not in baseline are silently skipped

    if improved:
        improved.sort(reverse=True)
        print(f"Improved ({len(improved)} files):")
        for file_delta, path, old_score, new_score in improved:
            short = path.removeprefix("src/babylon/")
            print(f"  {file_delta:>+5.1f}%  {short:<45} {old_score:.1f}% -> {new_score:.1f}%")
        print()

    if regressed:
        regressed.sort()
        print(f"Regressed ({len(regressed)} files):")
        for file_delta, path, old_score, new_score in regressed:
            short = path.removeprefix("src/babylon/")
            print(f"  {file_delta:>+5.1f}%  {short:<45} {old_score:.1f}% -> {new_score:.1f}%")
        print()

    print(f"Unchanged: {unchanged} files")
    print()


# =============================================================================
# BASELINE
# =============================================================================


def save_baseline(files: list[FileStats]) -> None:
    """Snapshot current scores to baseline JSON."""
    totals: dict[str, int] = defaultdict(int)
    for f in files:
        totals["killed"] += f.killed
        totals["survived"] += f.survived
        totals["no_tests"] += f.no_tests
        totals["suspicious"] += f.suspicious
        totals["timeout"] += f.timeout

    total = sum(totals.values())
    global_score = _score(totals["killed"], totals["survived"])

    file_dict = {}
    for f in files:
        file_dict[f.path] = {
            "killed": f.killed,
            "survived": f.survived,
            "score": round(f.score, 1),
        }

    baseline = {
        "generated_at": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit_short(),
        "global": {
            "total": total,
            "killed": totals["killed"],
            "survived": totals["survived"],
            "score": global_score,
        },
        "files": file_dict,
    }

    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(baseline, indent=2) + "\n")
    print(f"Baseline saved to {BASELINE_PATH} ({len(file_dict)} files, score {global_score}%)")


# =============================================================================
# CLI
# =============================================================================


def main() -> int:
    """Entry point for mutation report CLI."""
    parser = argparse.ArgumentParser(description="Mutation testing report generator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    report_parser = subparsers.add_parser("report", help="Generate mutation report")
    report_parser.add_argument("--diff", action="store_true", help="Compare against baseline")

    subparsers.add_parser("baseline", help="Snapshot current scores as baseline")

    args = parser.parse_args()

    if not MUTANTS_DIR.exists():
        print(f"No mutants directory found at {MUTANTS_DIR}/")
        print("Run: mise run mutate:full")
        return 1

    files = parse_meta_files()
    if not files:
        print("No .meta files found. Run mutation tests first.")
        return 1

    if args.command == "report":
        report = build_report_json(files)
        print_summary(report)

        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")
        print(f"JSON report: {REPORT_PATH}")

        if args.diff:
            print_diff(report)

        return 0

    if args.command == "baseline":
        save_baseline(files)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
