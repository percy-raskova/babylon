#!/usr/bin/env python3
"""Program 27 Phase 0, Task 8 — test-estate disposition tallies.

Classifies every ``*.py`` file under ``tests/`` into one of three
rewrite-disposition tiers, per the 2026-07-09 stratification doctrine
(``project/assessments/TEST_SUITE_REWRITE_AUDIT-2026-07-09.md``, Amendment Q /
Constitution III.12, ADR063: "tests are REHOMED, never rewritten... scaffolding
dies only with its code"):

- ``transcribe``               — durable behavioral contracts: baselines,
  property/hypothesis laws, contract-boundary tests, scenario/emergence
  tests, and integration tests shaped like a DB-schema or HTTP-contract.
  These "port in spirit" or "survive byte-for-byte" in a Rust rewrite.
- ``retire-with-code``         — Python-implementation-coupled scaffolding
  (unit tests mirroring one src/babylon module 1:1, benchmarks, test
  support/fixture/mock code). Dies when its src module is ported.
- ``re-derive-as-property-law``— unit/integration tests pinning a
  cross-cutting LAW (conservation, determinism, invariant, ordering,
  enum/hash closure) rather than one module's behavior. These should become
  abstract property-law statements (Hypothesis/proptest-shaped), not be
  hand-ported line by line.

Classification is by PATH + mechanical markers only (no semantic reading of
every file) per the task's own instruction: "the tool prints
``tier<TAB>count<TAB>example paths`` and a per-directory breakdown; the report
carries the table plus the judgment calls (files whose tier the path alone
couldn't decide...)". Rule precedence (first match wins):

  1. ``tests/baselines/**``                                   -> transcribe
  2. file greps positive for ``hypothesis`` or ``@given``      -> transcribe
  3. ``tests/contract/**`` | ``tests/property/**`` |
     ``tests/scenarios/**``                                    -> transcribe
  4. ``tests/benchmark/**``                                    -> retire-with-code
  5. filename stem matches a cross-cutting LAW marker           -> re-derive-as-property-law
  6. ``tests/integration/**`` AND filename matches a
     contract-shape marker (endpoint/schema/postgres/db/api/
     serialization/bridge/round_trip)                          -> transcribe
  7. ``tests/unit/**`` | ``tests/integration/**`` (remaining)   -> retire-with-code
  8. everything else (factories/fixtures/mocks/install/scripts/
     _helpers/root conftest.py, __init__.py)                   -> retire-with-code

Rules 5 and 6 are the "path alone couldn't decide" judgment calls — the
top-level directory alone doesn't determine the tier there, a filename marker
does. Those files are listed individually in the report with a one-line reason.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"

TRANSCRIBE = "transcribe"
RETIRE_WITH_CODE = "retire-with-code"
RE_DERIVE_AS_PROPERTY_LAW = "re-derive-as-property-law"

LAW_MARKER = re.compile(
    r"determinis|conservation|invariant|closure|ordering|thread_cap"
    r"|constants_sync|round_trip|numeraire",
    re.IGNORECASE,
)
CONTRACT_SHAPE_MARKER = re.compile(
    r"endpoint|schema|postgres|db_|_db|api|serialization|bridge|contract"
    r"|atomicity|atomic|two_phase|commit",
    re.IGNORECASE,
)


def _relpath(p: Path) -> str:
    return str(p.relative_to(REPO_ROOT))


def _hypothesis_files() -> set[Path]:
    """Files anywhere under tests/ that grep positive for hypothesis usage."""
    out = subprocess.run(
        ["rg", "-l", "hypothesis|@given", str(TESTS_DIR), "-t", "py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {Path(line).resolve() for line in out.stdout.splitlines() if line}


def classify(path: Path, hypothesis_files: set[Path]) -> tuple[str, str | None]:
    """Return (tier, judgment_reason). judgment_reason is None for plain
    directory-only decisions (rules 1/3/4/7/8); set for the marker-driven
    calls (rules 2/5/6) the path alone couldn't settle."""
    rel = _relpath(path)
    parts = Path(rel).parts  # ('tests', 'unit', 'formulas', 'test_x.py')
    stem = path.stem

    # Rule 1: baselines survive byte-for-byte.
    if len(parts) > 1 and parts[1] == "baselines":
        return TRANSCRIBE, None

    # Rule 2: hypothesis/@given anywhere -> transcribe (mechanical proptest port).
    if path.resolve() in hypothesis_files:
        return TRANSCRIBE, "uses hypothesis/@given — mechanical property-law port"

    # Rule 3: contract/property/scenarios port in spirit.
    if len(parts) > 1 and parts[1] in ("contract", "property", "scenarios"):
        return TRANSCRIBE, None

    # Rule 4: benchmarks die happily.
    if len(parts) > 1 and parts[1] == "benchmark":
        return RETIRE_WITH_CODE, None

    # Rule 5: cross-cutting LAW filename marker -> re-derive-as-property-law.
    if LAW_MARKER.search(stem):
        return (
            RE_DERIVE_AS_PROPERTY_LAW,
            "filename pins a cross-cutting law (conservation/determinism/"
            "invariant/ordering/closure), not one module's behavior",
        )

    # Rule 6: integration test shaped like a DB-schema/HTTP-contract boundary.
    if len(parts) > 1 and parts[1] == "integration" and CONTRACT_SHAPE_MARKER.search(stem):
        return (
            TRANSCRIBE,
            "integration test shaped like a DB-schema/HTTP/persistence "
            "contract boundary — survives in spirit per the 2026-07-09 audit",
        )

    # Rule 7: remaining unit/integration files mirror one src module.
    if len(parts) > 1 and parts[1] in ("unit", "integration"):
        return RETIRE_WITH_CODE, None

    # Rule 8: support/scaffolding directories and root files.
    return RETIRE_WITH_CODE, None


def main() -> int:
    files = sorted(TESTS_DIR.rglob("*.py"))
    files = [f for f in files if "__pycache__" not in f.parts]
    hypothesis_files = _hypothesis_files()

    tier_counts: dict[str, int] = defaultdict(int)
    tier_examples: dict[str, list[str]] = defaultdict(list)
    per_dir: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    judgment_calls: list[tuple[str, str, str]] = []  # (path, tier, reason)

    for f in files:
        tier, reason = classify(f, hypothesis_files)
        rel = _relpath(f)
        tier_counts[tier] += 1
        if len(tier_examples[tier]) < 5:
            tier_examples[tier].append(rel)
        top_dir = "(root)" if f.parent == TESTS_DIR else f.relative_to(TESTS_DIR).parts[0]
        per_dir[top_dir][tier] += 1
        if reason is not None:
            judgment_calls.append((rel, tier, reason))

    total = len(files)
    print(f"# Test-estate disposition tally — {total} files under tests/\n")
    print("tier\tcount\texample paths")
    for tier in (TRANSCRIBE, RETIRE_WITH_CODE, RE_DERIVE_AS_PROPERTY_LAW):
        examples = "; ".join(tier_examples[tier])
        print(f"{tier}\t{tier_counts[tier]}\t{examples}")

    print("\n# Per-directory breakdown (top-level dir under tests/)\n")
    print("directory\ttranscribe\tretire-with-code\tre-derive-as-property-law\ttotal")
    for d in sorted(per_dir):
        row = per_dir[d]
        row_total = sum(row.values())
        print(
            f"{d}\t{row[TRANSCRIBE]}\t{row[RETIRE_WITH_CODE]}\t"
            f"{row[RE_DERIVE_AS_PROPERTY_LAW]}\t{row_total}"
        )

    print(
        f"\n# Judgment calls: {len(judgment_calls)} files whose tier the path "
        f"(top-level dir) alone couldn't decide\n"
    )
    for rel, tier, reason in judgment_calls:
        print(f"{rel}\t{tier}\t{reason}")

    assert (
        tier_counts[TRANSCRIBE]
        + tier_counts[RETIRE_WITH_CODE]
        + tier_counts[RE_DERIVE_AS_PROPERTY_LAW]
        == total
    ), "tier counts must exhaust the file set"
    return 0


if __name__ == "__main__":
    sys.exit(main())
