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

from pathlib import Path

from babylon.sentinels._ast import referenced_names
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
