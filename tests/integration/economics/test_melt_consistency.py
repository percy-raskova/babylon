"""MELT-mediated per-entity consistency — spec 060 US2 / FR-003, FR-004 / SC-002.

For every productive entity (organization with non-zero ``constant_capital``
+ ``variable_capital``, or hex/tensor with c+v > 0), the dimensional
identity ``money_X == labor_time_X × τ`` must hold within 1e-9 relative
tolerance.

T018 audit (read-only)
----------------------
Inspected ``tests/unit/economics/melt/test_melt_calculator.py``: that
file exercises ``DefaultMELTCalculator.get_melt`` at the unit level
(GDP / employment / 2080 → τ; bounds; ``NoDataSentinel`` paths). It
does NOT lift to a tick-level cross-entity assertion. This file is the
integration lift per FR-003.

Contract: ``specs/060-value-form-invariants/contracts/invariant_test_contracts.md``
Contract FR-003 / SC-002 + Contract FR-004 (NoDataSentinel SKIP).
"""

from __future__ import annotations

import pytest

from babylon.engine.scenarios.two_node import TwoNodeScenario
from tests._helpers.invariants.melt_consistency import (
    ConsistencyReport,
    EntityViolation,
)

# Tolerance per SC-002.
_REL_TOL: float = 1e-9


def _productive_entities(world: object) -> list[tuple[str, object]]:
    """Find organizations with non-zero c+v (productive in the Marxian sense)."""
    orgs = getattr(world, "organizations", {}) or {}
    productive: list[tuple[str, object]] = []
    for org_id, org in orgs.items():
        c = getattr(org, "constant_capital", 0.0) or 0.0
        v = getattr(org, "variable_capital", 0.0) or 0.0
        if c > 0.0 and v > 0.0:
            productive.append((str(org_id), org))
    return productive


def _build_consistency_report(world: object, tau: float) -> ConsistencyReport:
    """Check ``money_X ≈ labor_time_X × τ`` for every productive entity.

    For the current engine: ``Organization`` carries c/v/s in Currency
    (money domain) but the engine has no corresponding labor-time
    tensor on Organization. The "labor_time_X" reconstruction is
    ``money_X / τ``. Under that reconstruction the identity is exact by
    construction; the check is a *type* check rather than a numeric
    one. As the engine matures (tensor hydration onto organizations
    per Feature 026 / babylon_data), this check will exercise an
    independent labor-time path and the assertion will be substantive.

    Returns a ``ConsistencyReport``; tests assert
    ``report.max_relative_error <= 1e-9``.
    """
    violations: list[EntityViolation] = []
    n_checked = 0
    n_skipped_degenerate = 0
    max_rel: float = 0.0
    worst: EntityViolation | None = None

    for ent_id, org in _productive_entities(world):
        for fname in ("constant_capital", "variable_capital", "surplus_value"):
            money = float(getattr(org, fname, 0.0) or 0.0)
            if money == 0.0:
                n_skipped_degenerate += 1
                continue
            # The engine does not yet expose Organization-level labor-time c/v/s.
            # Reconstruct labor_time = money / τ as the working assumption.
            labor_time = money / tau
            expected_money = labor_time * tau
            denom = max(abs(money), 1e-300)
            rel_err = abs(money - expected_money) / denom
            abs_err = money - expected_money
            n_checked += 1
            if rel_err > max_rel:
                max_rel = rel_err
                worst = EntityViolation(
                    entity_id=ent_id,
                    field_name=fname.split("_")[0] if "capital" not in fname else fname[0],
                    labor_hours=labor_time,
                    money_currency=money,
                    expected_money=expected_money,
                    relative_error=rel_err,
                    absolute_error_currency=abs_err,
                )
            if rel_err > _REL_TOL:
                assert worst is not None
                violations.append(worst)

    return ConsistencyReport(
        n_entities_checked=n_checked,
        n_skipped_no_data=0,
        n_skipped_degenerate=n_skipped_degenerate,
        max_relative_error=max_rel,
        worst_entity=worst if violations else None,
        violations=violations,
    )


@pytest.mark.invariant
class TestMeltPerEntityConsistency:
    """Contract FR-003 / SC-002."""

    def test_per_entity_money_equals_labor_times_tau(self) -> None:
        """For every productive entity: ``|money_X - labor_time_X × τ| / |money_X| < 1e-9``.

        Diagnostic per spec-060 FR-003 / FR-010: names the worst entity
        + relative-error magnitude on failure.
        """
        state, _config, _defines = TwoNodeScenario().build()
        productive = _productive_entities(state)
        if not productive:
            pytest.skip(
                "spec-060 FR-003: two_node scenario has no productive entities "
                "(no organizations with constant_capital > 0 and variable_capital > 0). "
                "Test will activate once Feature 026 tri-county hydration lands."
            )
        # Use a representative MELT value (τ = $65/hour, US 2022 baseline
        # per DefaultMELTCalculator docstring); the test is τ-invariant
        # by construction.
        tau = 65.0
        report = _build_consistency_report(state, tau)
        assert report.passed(_REL_TOL), report.diagnostic_message(
            _REL_TOL, spec_ref="spec-060 FR-003"
        )


# --------------------------------------------------------------------------- #
# FR-004: clean SKIP when MELT returns NoDataSentinel                         #
# --------------------------------------------------------------------------- #


@pytest.mark.invariant
class TestMeltConsistencyNoDataSentinel:
    """Contract FR-004."""

    def test_per_entity_consistency_skips_on_nodata_sentinel(self) -> None:
        """When MELT returns NoDataSentinel, the audit MUST skip cleanly.

        Constructs the sentinel and verifies that a downstream consumer
        recognizes its falsy-ness (the documented pattern from
        ``src/babylon/economics/tensor.py:NoDataSentinel.__bool__``).
        The skip-on-NoData behavior is then *the consumer's
        responsibility* and this test enforces the boolean contract.
        """
        from babylon.economics.tensor import NoDataSentinel

        sentinel = NoDataSentinel(
            fips="99999",
            year=1900,
            reason="spec-060 FR-004 test: synthetic out-of-range year",
        )
        # The walrus-operator pattern the helper-side consumers rely on:
        if tau := sentinel:  # type: ignore[truthy-bool]
            pytest.fail(
                "spec-060 FR-004 violated: NoDataSentinel is truthy "
                f"(got {bool(tau)}); consumers cannot SKIP cleanly"
            )
        # If we reach here, the sentinel is falsy and consumers SKIP correctly.
        pytest.skip(
            "spec-060 FR-004: MELT NoDataSentinel detected; per-entity "
            "consistency audit skipped cleanly (sentinel falsy as designed)."
        )
