"""Unit tests for reproduction capacity mechanics (Feature 040, US5).

Validates:
- SC-010: Reproduction capacity formula
- Budget independence weighting
- Pipeline degradation effects
"""

from __future__ import annotations

import pytest

from .conftest import make_institution, make_reproduction


class TestReproductionFormula:
    """Reproduction capacity = (bool_sum/4)*0.7 + budget_independence*0.3."""

    @pytest.mark.math
    def test_full_capacity(self) -> None:
        """All mechanisms active + full budget independence = max capacity."""
        repro = make_reproduction(
            recruitment_pipeline=True,
            training_program=True,
            succession_protocol=True,
            legal_self_perpetuation=True,
            budget_independence=1.0,
        )
        # (4/4)*0.7 + 1.0*0.3 = 1.0
        assert abs(repro.reproduction_capacity - 1.0) < 1e-6

    @pytest.mark.math
    def test_zero_capacity(self) -> None:
        """No mechanisms + zero budget independence = zero capacity."""
        repro = make_reproduction(
            recruitment_pipeline=False,
            training_program=False,
            succession_protocol=False,
            legal_self_perpetuation=False,
            budget_independence=0.0,
        )
        assert abs(repro.reproduction_capacity - 0.0) < 1e-6

    @pytest.mark.math
    def test_half_mechanisms(self) -> None:
        """Two of four mechanisms active."""
        repro = make_reproduction(
            recruitment_pipeline=True,
            training_program=True,
            succession_protocol=False,
            legal_self_perpetuation=False,
            budget_independence=0.5,
        )
        # (2/4)*0.7 + 0.5*0.3 = 0.35 + 0.15 = 0.50
        expected = 0.5 * 0.7 + 0.5 * 0.3
        assert abs(repro.reproduction_capacity - expected) < 1e-6

    @pytest.mark.math
    def test_budget_independence_weighting(self) -> None:
        """Budget independence accounts for 30% of capacity."""
        high_budget = make_reproduction(
            recruitment_pipeline=False,
            training_program=False,
            succession_protocol=False,
            legal_self_perpetuation=False,
            budget_independence=1.0,
        )
        # (0/4)*0.7 + 1.0*0.3 = 0.3
        assert abs(high_budget.reproduction_capacity - 0.3) < 1e-6


class TestReproductionInInstitution:
    """Reproduction capacity within institution context."""

    @pytest.mark.math
    def test_doj_high_reproduction(self) -> None:
        """DOJ with full mechanisms should have high capacity."""
        doj = make_institution()
        assert doj.reproduction.reproduction_capacity > 0.8

    @pytest.mark.math
    def test_dps_lower_reproduction(self) -> None:
        """DPS with low budget independence should have lower capacity."""
        from .conftest import make_isa_institution

        dps = make_isa_institution()
        # budget_independence=0.3, all bools true
        # (4/4)*0.7 + 0.3*0.3 = 0.79
        assert dps.reproduction.reproduction_capacity < 0.8
        assert dps.reproduction.reproduction_capacity > 0.7

    @pytest.mark.math
    def test_degraded_reproduction(self) -> None:
        """Institution with missing mechanisms has lower capacity."""
        inst = make_institution(
            reproduction=make_reproduction(
                recruitment_pipeline=False,
                training_program=False,
                budget_independence=0.5,
            ),
        )
        # 2/4=0.5 bools, 0.5*0.7 + 0.5*0.3 = 0.35 + 0.15 = 0.50
        expected = 0.5 * 0.7 + 0.5 * 0.3
        assert abs(inst.reproduction.reproduction_capacity - expected) < 1e-6
