"""Tests for the gate-blindness sensor.

``qa:regression`` is the project's Definition of Done. It nominally guards the
engine; it injected NO economics calculators at all, so its byte-identical
baselines never executed a line of the economics estate. A gate can be green and
blind. This sensor compares what a gate's harness actually injects against the
estate it claims to guard.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.sentinels.coverage.checks import check_gate_estate_coverage
from babylon.sentinels.coverage.registry import GATE_ESTATES, GateEstate

pytestmark = pytest.mark.unit


def test_registry_declares_the_regression_gate_estates() -> None:
    """The DoD gate's two claimed estates are declared."""
    names = {(row.gate_name, row.estate_name) for row in GATE_ESTATES}
    assert ("qa:regression", "economics_calculators") in names
    assert ("qa:regression", "financial_calculators") in names


def test_real_gate_is_not_blind() -> None:
    """INVARIANT: the DoD harness injects every key of each claimed estate."""
    assert check_gate_estate_coverage() == []


def test_efficacy_reds_when_the_harness_injects_nothing() -> None:
    """MUTATION: point the estate at a harness that injects none of its keys.

    ``web/game/map_contract.py`` is a real parseable file that mentions no
    economics service key — the exact shape of a gate that runs green while
    executing none of the estate it claims to guard.
    """
    blind = GateEstate(
        gate_name="phantom:gate",
        harness_file="web/game/map_contract.py",
        estate_name="economics_calculators",
        factory_file="src/babylon/domain/economics/factory.py",
        factory_symbol="create_economics_services",
    )
    findings = check_gate_estate_coverage((blind,))
    assert len(findings) == 1
    assert findings[0].startswith("[gate-blindness]")
    assert "phantom:gate" in findings[0]
    assert "melt_calculator" in findings[0]
    assert "REMEDY:" in findings[0]


def test_exempt_keys_narrow_the_claim_with_a_reason() -> None:
    """A key the gate deliberately does not inject is exempt WITH a reason."""
    narrowed = GateEstate(
        gate_name="phantom:gate",
        harness_file="web/game/map_contract.py",
        estate_name="economics_calculators",
        factory_file="src/babylon/domain/economics/factory.py",
        factory_symbol="create_economics_services",
        exempt_keys=(
            "melt_calculator",
            "basket_calculator",
            "gamma_calculator",
            "capital_calculator",
            "throughput_calculator",
            "transition_engine",
            "tensor_registry",
        ),
        exempt_reason="injected exemption covering the whole estate for this test",
    )
    assert check_gate_estate_coverage((narrowed,)) == []


def test_estate_rejects_exempt_keys_without_a_reason() -> None:
    """Narrowing a gate's claim silently is the failure mode; it is refused."""
    with pytest.raises(ValidationError, match="exempt_reason"):
        GateEstate(
            gate_name="phantom:gate",
            harness_file="tools/regression_test.py",
            estate_name="economics_calculators",
            factory_file="src/babylon/domain/economics/factory.py",
            factory_symbol="create_economics_services",
            exempt_keys=("melt_calculator",),
        )
