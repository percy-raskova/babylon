"""Tests for the undeclared-coupling sensor (both directions).

- **Invariant** — on the real catalog + registry, every declared edge between
  two registered oppositions is grounded in a real read, and every real read
  between two registered oppositions is declared.
- **Efficacy (MUTATION)** — direction A reds on an edge whose target's producer
  reads nothing the source publishes; direction B reds on a real read with no
  declaring edge.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from babylon.sentinels.coupling.checks import (
    check_declared_edges_are_grounded,
    check_real_dependencies_are_declared,
    main,
)
from babylon.sentinels.coupling.registry import MeasurementDependency

pytestmark = pytest.mark.unit

_TOOL_PATH = Path(__file__).resolve().parents[3] / "tools" / "sentinel_check.py"


def test_real_declared_edges_are_grounded() -> None:
    """INVARIANT: every declared edge maps to a real measurement dependency."""
    assert check_declared_edges_are_grounded() == []


def test_real_dependencies_are_all_declared() -> None:
    """INVARIANT: every real cross-opposition read carries a declaring edge."""
    assert check_real_dependencies_are_declared() == []


def test_efficacy_reds_on_a_declared_edge_with_no_real_dependency() -> None:
    """MUTATION: an edge whose target reads nothing the source publishes reds.

    ``web/game/map_contract.py`` is a real, parseable file that mentions neither
    ``phantom_published_symbol`` nor the source's fields — so the declared edge
    is a claim about the code that the code does not support.
    """
    source = MeasurementDependency(
        opposition_key="phantom_source",
        inputs_fields=("phantom_input",),
        producer_file="src/babylon/engine/systems/contradiction.py",
        produces_symbols=("phantom_published_symbol",),
    )
    target = MeasurementDependency(
        opposition_key="phantom_target",
        inputs_fields=("other_input",),
        producer_file="web/game/map_contract.py",
        produces_symbols=("other_published_symbol",),
    )
    findings = check_declared_edges_are_grounded(
        edges=(("phantom_source", "phantom_target", "transforms"),),
        dependencies=(source, target),
    )
    assert len(findings) == 1
    assert findings[0].startswith("[undeclared-coupling]")
    assert "phantom_source -> phantom_target" in findings[0]
    assert "REMEDY:" in findings[0]


def test_efficacy_reds_on_a_real_dependency_that_is_undeclared() -> None:
    """MUTATION: a real cross-opposition read with no declaring edge reds.

    ``market_scissors.py`` really does mention ``price_log``, so declaring it as
    the source's published symbol while declaring NO edge is exactly the
    ``momentum_coupling`` failure: a real dependency nobody wrote down.

    The fixture is deliberately ONE-DIRECTIONAL. ``check_real_dependencies_are_declared``
    loops every ORDERED pair, so the reverse pair (``phantom_financial ->
    phantom_price``) is judged too, and it asks whether ``contradiction.py``
    mentions ``phantom_financial``'s published symbols. ``fictitious_log`` would
    fail that test: ``referenced_names`` collects string constants, and U5.7
    writes the literal ``"fictitious_log"`` into ``contradiction.py`` to derive
    ``financialization_index`` — so the reverse pair would fire a second finding
    and this assertion would see 2. ``PRICE_DIVERGENCE_ATTR`` is a real
    module-level constant in ``market_scissors.py`` that appears nowhere in
    ``contradiction.py`` and is added to it by no task in this plan, so exactly
    one direction is a real read and exactly one finding is produced.
    """
    source = MeasurementDependency(
        opposition_key="phantom_price",
        inputs_fields=("market_balance",),
        producer_file="src/babylon/engine/systems/contradiction.py",
        produces_symbols=("price_log",),
    )
    target = MeasurementDependency(
        opposition_key="phantom_financial",
        inputs_fields=("financialization_index",),
        producer_file="src/babylon/engine/systems/market_scissors.py",
        produces_symbols=("PRICE_DIVERGENCE_ATTR",),
    )
    findings = check_real_dependencies_are_declared(
        edges=(),
        dependencies=(source, target),
    )
    assert len(findings) == 1
    assert findings[0].startswith("[undeclared-coupling]")
    assert "phantom_price" in findings[0]
    assert "phantom_financial" in findings[0]
    assert "price_log" in findings[0]


def test_declared_edge_silences_the_real_dependency_finding() -> None:
    """Declaring the edge makes direction B clean — the two directions agree.

    Same one-directional fixture as the test above, for the same reason: the
    reverse pair must contribute NO finding of its own, or ``== []`` would see
    the reverse finding and fail for a reason that has nothing to do with the
    declared edge.
    """
    source = MeasurementDependency(
        opposition_key="phantom_price",
        inputs_fields=("market_balance",),
        producer_file="src/babylon/engine/systems/contradiction.py",
        produces_symbols=("price_log",),
    )
    target = MeasurementDependency(
        opposition_key="phantom_financial",
        inputs_fields=("financialization_index",),
        producer_file="src/babylon/engine/systems/market_scissors.py",
        produces_symbols=("PRICE_DIVERGENCE_ATTR",),
    )
    assert (
        check_real_dependencies_are_declared(
            edges=(("phantom_price", "phantom_financial", "feeds"),),
            dependencies=(source, target),
        )
        == []
    )


def test_unregistered_endpoints_are_skipped_not_invented() -> None:
    """An edge to an unregistered opposition yields no claim either way."""
    source = MeasurementDependency(
        opposition_key="phantom_source",
        inputs_fields=("x",),
        producer_file="src/babylon/engine/systems/contradiction.py",
        produces_symbols=("x",),
    )
    assert (
        check_declared_edges_are_grounded(
            edges=(("phantom_source", "not_registered", "transforms"),),
            dependencies=(source,),
        )
        == []
    )


def test_main_exits_zero_because_coupling_is_advisory() -> None:
    """The sensor is advisory: findings print, the process never gates."""
    assert main([]) == 0


def test_cli_dispatches_the_coupling_sensor() -> None:
    """``sentinel_check.py coupling`` routes to this sensor and exits cleanly."""
    result = subprocess.run(
        [sys.executable, str(_TOOL_PATH), "coupling"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Coupling" in result.stdout
