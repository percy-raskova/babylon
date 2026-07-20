"""The intensive-aggregation sensor (static, advisory).

Walks each scanned file with :mod:`ast` and reports every division whose shape
is an unweighted mean of an intensive quantity: ``total / count``,
``sum(xs) / len(xs)``, or ``statistics.mean(xs)`` where the enclosing function or
the accumulated name is intensive by :data:`INTENSIVE_LEXICON`.

Reports the enclosing function and the line of the offending division, so the
finding points at the arithmetic, not the module.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

from babylon.sentinels._ast import parse_module
from babylon.sentinels.aggregation.intensive_registry import (
    AGGREGATION_EXEMPTIONS,
    INTENSIVE_LEXICON,
    MEAN_LEXICON,
    SCANNED_FILES,
    AggregationExemption,
)
from babylon.sentinels.base import LabelledCheck, run_sensor
from babylon.sentinels.report import finding

#: Repo root (this file is ``<root>/src/babylon/sentinels/aggregation/checks.py``).
_REPO_ROOT: Path = Path(__file__).resolve().parents[4]

#: Denominator names that merely COUNT members rather than weight them.
_COUNTING_NAMES: frozenset[str] = frozenset({"count", "n", "num", "n_nodes", "size"})


def _is_intensive(name: str) -> bool:
    """Whether a symbol name marks an intensive quantity.

    :param name: A function, variable, or attribute name.
    :returns: Whether any :data:`INTENSIVE_LEXICON` fragment occurs in it.
    """
    lowered = name.lower()
    return any(fragment in lowered for fragment in INTENSIVE_LEXICON)


def _is_counting_denominator(node: ast.expr) -> bool:
    """Whether a division's denominator counts members instead of weighting them.

    :param node: The right-hand expression of a division.
    :returns: Whether it is a bare counting name or a ``len(...)`` call.
    """
    if isinstance(node, ast.Name):
        return node.id.lower() in _COUNTING_NAMES
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "len"


def _numerator_names(node: ast.expr) -> set[str]:
    """Collect the names appearing in a division's numerator.

    :param node: The left-hand expression of a division.
    :returns: Every ``Name`` id occurring in it.
    """
    return {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}


def unweighted_mean_sites(path: Path) -> tuple[tuple[str, int], ...]:
    """Find unweighted means of intensive quantities in one source file.

    A site qualifies when a division's denominator merely counts members
    (:func:`_is_counting_denominator`) AND the enclosing function name or one of
    the numerator's names is intensive (:func:`_is_intensive`). ``mean`` in the
    function name alone is not enough — averaging an extensive quantity is
    legitimate — and a division by a weighting total (``capital``, ``surplus``)
    is the correct form and is never reported.

    :param path: Source file to scan.
    :returns: ``(enclosing_function, line)`` pairs, in source order.
    :raises SentinelCheckError: If the file is missing or unparseable.
    """
    tree = parse_module(path)
    sites: list[tuple[str, int]] = []
    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(func):
            if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)):
                continue
            if not _is_counting_denominator(node.right):
                continue
            names = _numerator_names(node.left)
            if (
                _is_intensive(func.name)
                or any(_is_intensive(name) for name in names)
                or any(fragment in func.name.lower() for fragment in MEAN_LEXICON)
                and any(_is_intensive(name) for name in names)
            ):
                sites.append((func.name, node.lineno))
    return tuple(sorted(set(sites), key=lambda site: (site[1], site[0])))


def check_no_unweighted_intensive_means(
    files: tuple[str, ...] = SCANNED_FILES,
    exemptions: tuple[AggregationExemption, ...] = AGGREGATION_EXEMPTIONS,
    repo_root: Path = _REPO_ROOT,
) -> list[str]:
    """No scanned file may average an intensive across space or class undeclared.

    :param files: Paths to scan (repo-relative by default; injectable so the
        efficacy tests can supply an injected offender).
    :param exemptions: Declared-legitimate sites (each carrying its reason).
    :param repo_root: Root the ``files`` entries resolve against.
    :returns: Sorted agent-legible finding strings (empty when clean).
    :raises SentinelCheckError: If any scanned file is missing or unparseable.
    """
    exempt = {(row.file, row.symbol) for row in exemptions}
    findings: list[str] = []
    for relative in files:
        for symbol, line in unweighted_mean_sites(repo_root / relative):
            if (relative, symbol) in exempt:
                continue
            findings.append(
                finding(
                    error_class="intensive-aggregation",
                    symbol=symbol,
                    file=relative,
                    line=line,
                    problem=(
                        "takes an unweighted mean of an intensive quantity across "
                        "space or class — a tiny member swings the aggregate as hard "
                        "as a large one"
                    ),
                    remedy=(
                        "aggregate the numerator and the denominator separately "
                        "(the profit rate is sum(surplus) / sum(capital), not "
                        "mean(rate)); if equal weighting is materially correct here, "
                        "declare an AggregationExemption with the reason"
                    ),
                )
            )
    return sorted(findings)


#: Nothing gates — advisory and local/on-demand per the standing owner ruling.
_GATING_CHECKS: tuple[LabelledCheck, ...] = ()

#: The single advisory check.
_ADVISORY_CHECKS: tuple[LabelledCheck, ...] = (
    ("unweighted mean of an intensive across space/class", check_no_unweighted_intensive_means),
)


def _summary(advisory_count: int) -> str:
    """Build the clean one-line summary printed when nothing gated.

    :param advisory_count: Number of advisory findings emitted above.
    :returns: The summary line naming the scan size.
    """
    summary = (
        f"Aggregation (static, advisory): {len(SCANNED_FILES)} files scanned, "
        f"{len(AGGREGATION_EXEMPTIONS)} declared exemptions."
    )
    if advisory_count:
        summary += f" ({advisory_count} advisory findings above.)"
    return summary


def main(argv: list[str] | None = None) -> int:
    """Run the intensive-aggregation sensor and return the process exit code.

    :param argv: CLI args (``--check`` accepted for family symmetry; advisory).
    :returns: 0 clean or advisory-only, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(
        description="Aggregation — no unweighted mean of an intensive (advisory).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Accepted for family symmetry; this sensor is advisory and never gates.",
    )
    parser.parse_args(argv)
    return run_sensor("AGGREGATION", _GATING_CHECKS, _ADVISORY_CHECKS, _summary)


if __name__ == "__main__":
    sys.exit(main())
