"""Class mobility calculator for Chetty-derived parameters (Feature 030, US6).

Parameterizes intergenerational class mobility using Opportunity Atlas KFR
data. Models D-to-P class transition outcomes by race and parental income,
with covariate adjustments and event-driven parameter shifts.

See Also:
    :mod:`babylon.domain.economics.lifecycle.types`: ClassMobilityParams model.
    ``specs/030-dpd-lifecycle-circuit/spec.md`` FR-014 through FR-018.
"""

from __future__ import annotations

from typing import Protocol

from babylon.domain.economics.lifecycle.types import ClassMobilityParams


class ClassMobilityCalculator(Protocol):
    """Protocol for class mobility computation."""

    def compute_mobility_outcome(
        self,
        parental_percentile: float,
        race: str,
        params: ClassMobilityParams,
    ) -> float:
        """Compute child income percentile from parental position.

        Args:
            parental_percentile: Parent's income percentile (0-100).
            race: Race category ("white", "black", etc.).
            params: Chetty-derived mobility parameters.

        Returns:
            Child's expected income percentile [0, 1].
        """
        ...

    def compute_premature_exit_rate(
        self,
        base_rate: float,
        mortality_modifier: float,
        carceral_modifier: float,
    ) -> float:
        """Compute modified P→D' transition rate.

        Args:
            base_rate: Baseline P→D' transition rate.
            mortality_modifier: Early mortality multiplier.
            carceral_modifier: Incarceration rate multiplier.

        Returns:
            Modified rate, capped at 1.0.
        """
        ...

    def apply_covariate_adjustment(
        self,
        base_outcome: float,
        params: ClassMobilityParams,
    ) -> float:
        """Adjust mobility outcome by county-level covariates.

        Args:
            base_outcome: Pre-adjustment mobility outcome.
            params: Contains covariate values.

        Returns:
            Adjusted outcome.
        """
        ...

    def apply_event_modifier(
        self,
        params: ClassMobilityParams,
        event_type: str,
        magnitude: float,
    ) -> ClassMobilityParams:
        """Shift mobility parameters in response to in-game events.

        Args:
            params: Current mobility parameters.
            event_type: Event category.
            magnitude: Event magnitude (fractional shift).

        Returns:
            Modified ClassMobilityParams.
        """
        ...


class DefaultClassMobilityCalculator:
    """Default implementation of ClassMobilityCalculator.

    Implements FR-014 through FR-018 for Chetty-derived class mobility.
    Linear interpolation between P25/P75 anchor rates with racial gap,
    covariate adjustments, and event-driven parameter modification.
    """

    def compute_mobility_outcome(
        self,
        parental_percentile: float,
        race: str,
        params: ClassMobilityParams,
    ) -> float:
        """Compute child income percentile via KFR interpolation."""
        # Linear interpolation between P25 and P75 anchors
        p25 = 25.0
        p75 = 75.0
        if parental_percentile <= p25:
            baseline = params.mobility_base_rate
        elif parental_percentile >= p75:
            baseline = params.mobility_base_rate_p75
        else:
            t = (parental_percentile - p25) / (p75 - p25)
            baseline = params.mobility_base_rate + t * (
                params.mobility_base_rate_p75 - params.mobility_base_rate
            )

        # Racial gap applied additively for Black population
        if race.lower() == "black":
            baseline = baseline - params.mobility_racial_gap

        return max(0.0, baseline)

    def compute_premature_exit_rate(
        self,
        base_rate: float,
        mortality_modifier: float,
        carceral_modifier: float,
    ) -> float:
        """Compute modified P→D' rate with mortality and carceral modifiers."""
        modified = base_rate * mortality_modifier * carceral_modifier
        return min(1.0, modified)

    def apply_covariate_adjustment(
        self,
        base_outcome: float,
        params: ClassMobilityParams,
    ) -> float:
        """Adjust mobility by county covariates.

        Positive factors (improve mobility): college_rate, employment_rate.
        Negative factors (reduce mobility): poverty_share, single_parent_fraction.
        Neutral context: baseline_gini (inequality level).

        Coefficients derived from Chetty multivariate regressions.
        """
        # Regression coefficients (from Chetty Table 9 approximation)
        c_college = 0.10
        c_employment = 0.05
        c_poverty = -0.08
        c_single_parent = -0.06

        adjustment = (
            c_college * params.college_rate
            + c_employment * params.employment_rate
            + c_poverty * params.poverty_share
            + c_single_parent * params.single_parent_fraction
        )

        return max(0.0, min(1.0, base_outcome + adjustment))

    def apply_event_modifier(
        self,
        params: ClassMobilityParams,
        event_type: str,
        magnitude: float,
    ) -> ClassMobilityParams:
        """Shift mobility parameters based on in-game events."""
        event_type_lower = event_type.lower()

        if event_type_lower == "racial_discrimination":
            new_gap = params.mobility_racial_gap * (1.0 + magnitude)
            return params.model_copy(update={"mobility_racial_gap": min(1.0, new_gap)})

        if event_type_lower == "carceral_expansion":
            new_carceral = params.carceral_modifier * (1.0 + magnitude)
            return params.model_copy(update={"carceral_modifier": min(10.0, new_carceral)})

        if event_type_lower == "education_improvement":
            new_college = params.college_rate * (1.0 + magnitude)
            return params.model_copy(update={"college_rate": min(1.0, new_college)})

        if event_type_lower == "healthcare_access":
            new_mortality = params.early_mortality_modifier * (1.0 - magnitude)
            return params.model_copy(update={"early_mortality_modifier": max(0.0, new_mortality)})

        # Unknown event → no change
        return params


__all__ = ["ClassMobilityCalculator", "DefaultClassMobilityCalculator"]
