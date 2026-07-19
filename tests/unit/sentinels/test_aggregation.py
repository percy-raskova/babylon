"""Tests for the intensive-aggregation sensor.

An *intensive* quantity — a rate, ratio, share, balance, index — does not
average across space or class. The aggregate profit rate is ``Σs / Σ(c+v)``, not
``mean(rᵢ)``: the unweighted form lets a county of four hundred people swing a
national threshold as hard as Wayne County. This sensor finds the unweighted
form statically.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.sentinels.aggregation.checks import (
    check_no_unweighted_intensive_means,
    unweighted_mean_sites,
)
from babylon.sentinels.aggregation.registry import AggregationExemption

pytestmark = pytest.mark.unit


def test_detects_the_total_over_count_form(tmp_path: Path) -> None:
    """MUTATION: the classic ``total / count`` unweighted mean of a rate is found."""
    target = tmp_path / "scissors.py"
    target.write_text(
        "\n".join(
            [
                "def _mean_profit_rate(graph):",
                "    total = 0.0",
                "    count = 0",
                "    for node in sorted(graph.nodes()):",
                "        total += float(node.rate)",
                "        count += 1",
                "    return total / count if count else None",
            ]
        ),
        encoding="utf-8",
    )
    sites = unweighted_mean_sites(target)
    assert sites == (("_mean_profit_rate", 7),)


def test_detects_the_sum_over_len_form(tmp_path: Path) -> None:
    """MUTATION: ``sum(x) / len(x)`` over an intensive is the same defect."""
    target = tmp_path / "ratio.py"
    target.write_text(
        "\n".join(
            [
                "def mean_debt_ratio(values):",
                "    return sum(values) / len(values)",
            ]
        ),
        encoding="utf-8",
    )
    assert unweighted_mean_sites(target) == (("mean_debt_ratio", 2),)


def test_ignores_a_weighted_aggregate(tmp_path: Path) -> None:
    """A capital-weighted aggregate is the CORRECT form and must not be flagged."""
    target = tmp_path / "weighted.py"
    target.write_text(
        "\n".join(
            [
                "def mean_profit_rate(graph):",
                "    surplus = 0.0",
                "    capital = 0.0",
                "    for node in sorted(graph.nodes()):",
                "        surplus += node.surplus",
                "        capital += node.capital_stock",
                "    return surplus / capital if capital else None",
            ]
        ),
        encoding="utf-8",
    )
    assert unweighted_mean_sites(target) == ()


def test_ignores_an_extensive_mean(tmp_path: Path) -> None:
    """Averaging an extensive quantity (a count of people) is legitimate."""
    target = tmp_path / "extensive.py"
    target.write_text(
        "\n".join(
            [
                "def mean_population(values):",
                "    return sum(values) / len(values)",
            ]
        ),
        encoding="utf-8",
    )
    assert unweighted_mean_sites(target) == ()


def test_real_scanned_files_are_clean_or_exempt() -> None:
    """INVARIANT: the declared scan set carries no undeclared unweighted mean."""
    assert check_no_unweighted_intensive_means() == []


def test_check_reports_agent_legible_finding(tmp_path: Path) -> None:
    """MUTATION: an injected offending file produces a full agent-legible finding."""
    target = tmp_path / "offender.py"
    target.write_text(
        "\n".join(
            [
                "def mean_credit_fragility(values):",
                "    return sum(values) / len(values)",
            ]
        ),
        encoding="utf-8",
    )
    findings = check_no_unweighted_intensive_means(
        files=(str(target),), exemptions=(), repo_root=Path("/")
    )
    assert len(findings) == 1
    assert findings[0].startswith("[intensive-aggregation]")
    assert "mean_credit_fragility" in findings[0]
    assert "REMEDY:" in findings[0]


def test_exemption_silences_a_declared_site(tmp_path: Path) -> None:
    """A declared exemption with a reason silences its own site only."""
    target = tmp_path / "exempt.py"
    target.write_text(
        "\n".join(
            [
                "def mean_solidarity_index(values):",
                "    return sum(values) / len(values)",
            ]
        ),
        encoding="utf-8",
    )
    exemption = AggregationExemption(
        file=str(target),
        symbol="mean_solidarity_index",
        reason="the index is defined per-node with equal weight by construction",
    )
    assert (
        check_no_unweighted_intensive_means(
            files=(str(target),), exemptions=(exemption,), repo_root=Path("/")
        )
        == []
    )
