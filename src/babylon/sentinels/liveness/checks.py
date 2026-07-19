"""Liveness sensors — correct-but-inert and computed-but-never-consumed.

Proves, statically via :mod:`ast` (no import, no engine run — the sentinels'
layer-0.5 boundary forbids importing ``engine``/``domain``/``web``), that every
output declared in :data:`babylon.sentinels.liveness.registry.LIVENESS_ROWS` is
actually mentioned by at least one of its declared production consumers, and
that no producer is wholly dormant.

Both checks are **advisory** per the standing owner ruling: they print loudly and
locally, and never gate CI. Run:
``poetry run python tools/sentinel_check.py liveness``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from babylon.sentinels._ast import referenced_names
from babylon.sentinels.base import LabelledCheck, run_sensor
from babylon.sentinels.liveness.registry import LIVENESS_ROWS, LivenessRow
from babylon.sentinels.report import finding

#: Repo root (this file is ``<root>/src/babylon/sentinels/liveness/checks.py``).
_REPO_ROOT: Path = Path(__file__).resolve().parents[4]


def check_outputs_have_readers(
    registry: tuple[LivenessRow, ...] = LIVENESS_ROWS,
) -> list[str]:
    """Every declared non-dormant output must be read by a declared consumer.

    For each row with consumers, parse each consumer file and assert it mentions
    ``output_symbol`` (as a name, attribute, keyword, or string key — see
    :func:`babylon.sentinels._ast.referenced_names`). A row whose consumers all
    fail to mention it is **computed-but-never-consumed**: the producer runs
    every tick and its result reaches nothing.

    :param registry: Rows to check (defaults to the real
        :data:`LIVENESS_ROWS`; injectable so the efficacy tests can supply an
        injected defect).
    :returns: Sorted agent-legible finding strings (empty when every output is
        read or declared dormant).
    :raises SentinelCheckError: If a declared consumer file is missing or
        unparseable — infrastructure failure, never a silent pass.
    """
    findings: list[str] = []
    for row in registry:
        if not row.consumer_files:
            continue
        readers = [
            consumer
            for consumer in row.consumer_files
            if row.output_symbol in referenced_names(_REPO_ROOT / consumer)
        ]
        if readers:
            continue
        findings.append(
            finding(
                error_class="computed-but-never-consumed",
                symbol=row.output_symbol,
                file=row.producer_file,
                line=0,
                problem=(
                    f"{row.producer_symbol} stamps it, but none of its declared "
                    f"consumers ({', '.join(row.consumer_files)}) mention it"
                ),
                remedy=(
                    "wire a real production reader and point consumer_files at it, "
                    "or set dormant_reason on the liveness registry row explaining "
                    "why the output legitimately has none yet"
                ),
            )
        )
    return sorted(findings)


def check_producers_are_not_inert(
    registry: tuple[LivenessRow, ...] = LIVENESS_ROWS,
) -> list[str]:
    """No declared producer may have an all-dormant output set.

    Groups rows by ``producer_symbol``. A producer every one of whose outputs is
    dormant is **correct-but-inert**: it executes, its models validate, and
    nothing downstream changes because of it — the Volume III failure mode. One
    live output redeems the producer; zero does not.

    :param registry: Rows to check (defaults to the real :data:`LIVENESS_ROWS`;
        injectable so the efficacy test can supply an injected inert producer).
    :returns: Sorted agent-legible finding strings, one per inert producer.
    """
    outputs_by_producer: dict[str, list[LivenessRow]] = {}
    for row in registry:
        outputs_by_producer.setdefault(row.producer_symbol, []).append(row)

    findings: list[str] = []
    for producer, rows in sorted(outputs_by_producer.items()):
        if any(row.consumer_files for row in rows):
            continue
        dead = ", ".join(sorted(row.output_symbol for row in rows))
        findings.append(
            finding(
                error_class="correct-but-inert",
                symbol=producer,
                file=rows[0].producer_file,
                line=0,
                problem=(
                    f"runs every tick but every declared output is dormant ({dead}) "
                    "— nothing downstream changes because it ran"
                ),
                remedy=(
                    "wire at least one output to a production consumer and record it "
                    "in consumer_files, or retire the producer; a producer that only "
                    "computes is decoration (Constitution III.10)"
                ),
            )
        )
    return sorted(findings)


#: Nothing gates: per the standing owner ruling the liveness sensor is advisory
#: and local/on-demand (no nightly CI plumbing).
_GATING_CHECKS: tuple[LabelledCheck, ...] = ()

#: Both liveness classes report advisorily.
_ADVISORY_CHECKS: tuple[LabelledCheck, ...] = (
    ("declared output has no production reader", check_outputs_have_readers),
    ("producer runs but every output is dormant", check_producers_are_not_inert),
)


def _summary(advisory_count: int) -> str:
    """Build the clean one-line summary printed when nothing gated.

    :param advisory_count: Number of advisory findings emitted above.
    :returns: The summary line naming the size of the declared registry.
    """
    live = sum(1 for row in LIVENESS_ROWS if row.consumer_files)
    dormant = len(LIVENESS_ROWS) - live
    summary = (
        f"Liveness (static, advisory): {len(LIVENESS_ROWS)} declared outputs — "
        f"{live} consumed, {dormant} declared dormant with a reason."
    )
    if advisory_count:
        summary += f" ({advisory_count} advisory findings above.)"
    return summary


def main(argv: list[str] | None = None) -> int:
    """Run both liveness sensors and return the process exit code.

    :param argv: CLI args (``--check`` accepted for family symmetry; this
        sensor is advisory and never gates, so it does not change behavior).
    :returns: 0 clean or advisory-only, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(
        description="Liveness — correct-but-inert / computed-but-never-consumed (advisory).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Accepted for family symmetry; this sensor is advisory and never gates.",
    )
    parser.parse_args(argv)
    return run_sensor("LIVENESS", _GATING_CHECKS, _ADVISORY_CHECKS, _summary)


if __name__ == "__main__":
    sys.exit(main())
