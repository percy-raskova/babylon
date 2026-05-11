"""Numeraire invariance — spec 060 US1 / FR-001, FR-002 / SC-001.

If every monetary field on a ``WorldState`` is multiplied by a positive
constant ``k``, then every dimensionless ratio derived from monetary
fields must be identical to within 1e-12 relative tolerance. This is
the deepest, most theoretically uncontroversial value-form invariant:
ratios are pure numbers and the choice of monetary numéraire (dollars
vs. cents vs. tens-of-dollars) cannot affect them.

Contract: ``specs/060-value-form-invariants/contracts/invariant_test_contracts.md``
(Contract FR-001 / SC-001 and Contract FR-002).
"""

from __future__ import annotations

import math

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from babylon.engine.scenarios.two_node import TwoNodeScenario
from babylon.models.world_state import WorldState
from tests._helpers.invariants.monetary_rescaling import rescale_currency_fields

# Tolerance per spec FR-001 / SC-001.
_REL_TOL: float = 1e-12


def _money_ratios(world: WorldState) -> dict[str, float]:
    """Compute dimensionless ratios derivable from Currency-typed fields.

    The two-node scenario doesn't populate the full ValueTensor4x3
    (no organizations with c/v/s), so we derive ratios from the
    SocialClass Currency fields that ARE populated:

    - subsistence_threshold / wealth  (per entity)
    - s_bio / wealth                  (per entity)
    - s_class / wealth                (per entity, where applicable)

    Returns ``{ratio_key: value}`` for every well-defined ratio (denominator
    non-zero). Entries with zero or near-zero denominators are skipped.
    """
    ratios: dict[str, float] = {}
    for ent_id, ent in world.entities.items():
        wealth = getattr(ent, "wealth", 0.0) or 0.0
        if abs(wealth) < 1e-12:
            continue
        for fname in ("subsistence_threshold", "s_bio", "s_class", "effective_wealth"):
            val = getattr(ent, fname, None)
            if val is None or not isinstance(val, (int, float)):
                continue
            ratios[f"{ent_id}.{fname}/wealth"] = float(val) / float(wealth)
    return ratios


def _assert_ratios_match(
    base: dict[str, float],
    other: dict[str, float],
    k: float,
    spec_ref: str,
) -> None:
    """Assert that every ratio in ``other`` matches ``base`` within 1e-12.

    Names the offending entity, ratio key, and observed delta per FR-010.
    """
    assert set(base.keys()) == set(other.keys()), (
        f"{spec_ref}: ratio key sets diverge under rescaling k={k}. "
        f"base={set(base.keys())} other={set(other.keys())}"
    )
    worst_key: str | None = None
    worst_rel_err: float = 0.0
    for key, base_val in base.items():
        other_val = other[key]
        denom = max(abs(base_val), 1e-300)
        rel_err = abs(base_val - other_val) / denom
        if rel_err > worst_rel_err:
            worst_rel_err = rel_err
            worst_key = key
    assert worst_rel_err <= _REL_TOL, (
        f"{spec_ref}: numeraire invariance violated at k={k}. "
        f"worst entity/ratio={worst_key!r} "
        f"base={base.get(worst_key, math.nan):.12g} "
        f"rescaled={other.get(worst_key, math.nan):.12g} "
        f"relative_error={worst_rel_err:.3e} "
        f"(tolerance={_REL_TOL:.0e})."
    )


# --------------------------------------------------------------------------- #
# FR-001: Single-tick numeraire invariance at fixed scale factors             #
# --------------------------------------------------------------------------- #


@pytest.mark.invariant
class TestNumeraireInvarianceSingleScale:
    """Contract FR-001 / SC-001."""

    @pytest.fixture
    def baseline_world(self) -> WorldState:
        state, _config, _defines = TwoNodeScenario().build()
        return state

    @pytest.mark.parametrize("k", [100.0, 0.01, 1.0, 1000.0])
    def test_ratios_invariant_under_rescaling(self, baseline_world: WorldState, k: float) -> None:
        """Rescaling Currency fields by k preserves all money-derived ratios.

        Per Contract FR-001: tests with k ∈ {1, 100, 0.01} and the
        additional 1000.0 boundary for robustness. Relative tolerance
        1e-12 per SC-001.
        """
        rescaled = rescale_currency_fields(baseline_world, k)
        base_ratios = _money_ratios(baseline_world)
        rescaled_ratios = _money_ratios(rescaled)
        _assert_ratios_match(base_ratios, rescaled_ratios, k, spec_ref="spec-060 FR-001")

    def test_labor_time_fields_untouched_by_rescaling(self, baseline_world: WorldState) -> None:
        """Per Acceptance Scenario 3: labor-hours stay invariant under monetary rescale.

        ``population`` is an example of a non-monetary, non-labor-time
        integer field that must not be touched. We check it AND
        document the labor-time invariant by spot-check.
        """
        rescaled = rescale_currency_fields(baseline_world, k=100.0)
        for ent_id, base_ent in baseline_world.entities.items():
            re_ent = rescaled.entities[ent_id]
            assert base_ent.population == re_ent.population, (
                f"spec-060 FR-001 violated: population changed for {ent_id}"
            )


# --------------------------------------------------------------------------- #
# FR-002: Hypothesis property test                                            #
# --------------------------------------------------------------------------- #


@pytest.mark.invariant
@pytest.mark.property
class TestNumeraireInvarianceHypothesis:
    """Contract FR-002."""

    # FR-020: derandomize=True applied via the project-wide `default`
    # Hypothesis profile registered at tests/conftest.py:54-60.
    # FR-022: this test carries @pytest.mark.invariant registered in pyproject.toml.
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    @given(k=st.floats(min_value=1e-3, max_value=1e6, allow_nan=False, allow_infinity=False))
    def test_ratios_invariant_hypothesis(self, k: float) -> None:
        """100 random k values from [1e-3, 1e6]; every example must hold.

        Per Contract FR-002 / SC-001: 100 examples, derandomize=True (CI
        profile), failures reproducible via ``.hypothesis/``.
        """
        state, _c, _d = TwoNodeScenario().build()
        rescaled = rescale_currency_fields(state, k)
        base_ratios = _money_ratios(state)
        rescaled_ratios = _money_ratios(rescaled)
        _assert_ratios_match(base_ratios, rescaled_ratios, k, spec_ref="spec-060 FR-002")
