"""Class transition engine for simulating class distribution changes.

Feature: 016-class-dynamics-engine
Date: 2026-02-06

Implements the main simulation loop: ClassDistribution + EconomicConditions
-> TransitionRates -> ClassDistribution(t+1). Integrates accumulation,
dispossession, precaritization, stabilization, and crisis amplification.

Flow equations (data-model.md):
    LA'     = LA     - dispossession*LA     + accumulation*Proletariat
    Prol'   = Prol   + dispossession*LA     - accumulation*Proletariat
                     - precaritization*Prol + stabilization*Lumpen
    Lumpen' = Lumpen + precaritization*Prol - stabilization*Lumpen

See Also:
    :mod:`babylon.economics.dynamics.data_sources`: ClassTransitionEngine protocol
    ``specs/016-class-dynamics-engine/data-model.md``: State transition diagram
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from babylon.economics.dynamics.types import (
    ClassDistribution,
    TransitionRates,
)
from babylon.economics.dynamics.validation import (
    validate_class_shares,
    validate_transition_rates,
)
from babylon.economics.melt.types import ClassPosition
from babylon.economics.tensor import NoDataSentinel

if TYPE_CHECKING:
    from babylon.economics.dynamics.data_sources import (
        AccumulationCalculator,
        CrisisAmplifier,
        DispossessionCalculator,
    )
    from babylon.economics.dynamics.types import (
        EconomicConditions,
    )

logger = logging.getLogger(__name__)

# Default parameters
_DEFAULT_WEALTH_THRESHOLD: float = 142_000.0
_DEFAULT_EVICTION_WEIGHT: float = 0.5
_DEFAULT_BASE_STABILIZATION: float = 0.10
_MAX_ACCUMULATION_RATE: float = 0.08  # Warning upper bound


class DefaultClassTransitionEngine:
    """Default implementation of ClassTransitionEngine.

    Orchestrates one period of class distribution transitions by:
    1. Computing accumulation rate from AccumulationCalculator
    2. Computing dispossession rates from DispossessionCalculator
    3. Computing precaritization and stabilization from EconomicConditions
    4. Applying crisis amplification
    5. Applying flow equations
    6. Normalizing to sum=1.0

    Args:
        accumulation_calculator: Computes wealth accumulation.
        dispossession_calculator: Computes dispossession risk.
        crisis_amplifier: Amplifies rates during crisis.
        wealth_threshold: LA entry wealth level ($). Default 142,000.
        eviction_weight: Weight for eviction in precaritization. Default 0.5.
        base_stabilization: Max stabilization rate. Default 0.10.

    Example:
        >>> engine = DefaultClassTransitionEngine(acc, disp, crisis)
        >>> new_dist = engine.simulate_transitions(dist, conditions)
    """

    def __init__(
        self,
        accumulation_calculator: AccumulationCalculator,
        dispossession_calculator: DispossessionCalculator,
        crisis_amplifier: CrisisAmplifier,
        wealth_threshold: float = _DEFAULT_WEALTH_THRESHOLD,
        eviction_weight: float = _DEFAULT_EVICTION_WEIGHT,
        base_stabilization: float = _DEFAULT_BASE_STABILIZATION,
    ) -> None:
        """Initialize with calculator dependencies.

        Args:
            accumulation_calculator: Computes wealth accumulation.
            dispossession_calculator: Computes dispossession risk.
            crisis_amplifier: Amplifies rates during crisis.
            wealth_threshold: LA entry wealth level ($).
            eviction_weight: Weight for eviction in precaritization.
            base_stabilization: Max stabilization rate.
        """
        self._acc_calc = accumulation_calculator
        self._disp_calc = dispossession_calculator
        self._crisis_amp = crisis_amplifier
        self._wealth_threshold = wealth_threshold
        self._eviction_weight = eviction_weight
        self._base_stabilization = base_stabilization

    def simulate_transitions(
        self,
        dist: ClassDistribution,
        conditions: EconomicConditions,
    ) -> ClassDistribution | NoDataSentinel:
        """Simulate one period of class distribution transitions.

        Args:
            dist: Current class distribution.
            conditions: Economic conditions for this period.

        Returns:
            Updated ClassDistribution or NoDataSentinel if data unavailable.

        Raises:
            ValueError: If dist.fips != conditions.fips.
        """
        if dist.fips != conditions.fips:
            msg = f"FIPS mismatch: dist={dist.fips}, conditions={conditions.fips}"
            raise ValueError(msg)

        # 1. Compute accumulation rate
        acc_result = self._acc_calc.compute(
            wage=conditions.median_wage,
            phi_hour=conditions.phi_hour,
            class_position=ClassPosition.PROLETARIAT,
        )
        accumulation_rate = self._convert_accumulation_to_rate(
            acc_result.annual_accumulation,
        )

        # 2. Compute dispossession rates
        disp_result = self._disp_calc.compute(conditions.fips, conditions.year)
        if isinstance(disp_result, NoDataSentinel):
            return disp_result
        dispossession_rate = disp_result.la_to_p_rate

        # 3. Compute precaritization and stabilization
        precaritization_rate = self._compute_precaritization_rate(conditions)
        stabilization_rate = self._compute_stabilization_rate(conditions)

        # 4. Build transition rates and apply crisis amplification
        rates = TransitionRates(
            fips=conditions.fips,
            year=conditions.year,
            dispossession=dispossession_rate,
            accumulation=accumulation_rate,
            precaritization=precaritization_rate,
            stabilization=stabilization_rate,
        )
        rates = self._crisis_amp.amplify(rates, conditions.crisis)

        # Validate and log
        self._log_validation(rates)

        # 5. Apply flow equations
        la, prol, lumpen = dist.dynamic_shares()
        new_la, new_prol, new_lumpen = self._apply_flows(
            la,
            prol,
            lumpen,
            rates,
        )

        # 6. Clamp and normalize
        new_la, new_prol, new_lumpen = self._normalize(
            new_la,
            new_prol,
            new_lumpen,
            dist.bourgeoisie_share + dist.petit_bourgeoisie_share,
        )

        # Validate output shares
        valid, message = validate_class_shares(new_la, new_prol, new_lumpen)
        if message is not None:
            logger.warning("Class share validation: %s", message)
        if not valid:
            logger.error("Class share FAIL: %s", message)

        return dist.with_updated_dynamics(
            la=new_la,
            prol=new_prol,
            lumpen=new_lumpen,
        )

    def _convert_accumulation_to_rate(
        self,
        annual_accumulation: float,
    ) -> float:
        """Convert dollar accumulation to transition rate.

        Rate = min(annual_accumulation / wealth_threshold, max_rate),
        clamped to 0 if negative.

        Args:
            annual_accumulation: Annual wealth change ($).

        Returns:
            Accumulation rate [0, max_rate].
        """
        if annual_accumulation <= 0.0:
            return 0.0
        return min(annual_accumulation / self._wealth_threshold, _MAX_ACCUMULATION_RATE)

    def _compute_precaritization_rate(
        self,
        conditions: EconomicConditions,
    ) -> float:
        """Compute precaritization rate (P->L) per FR-015.

        Formula: unemployment_rate * eviction_weight + eviction_rate * (1 - eviction_weight)

        Args:
            conditions: Economic conditions.

        Returns:
            Precaritization rate [0, 1].
        """
        rate = conditions.unemployment_rate * self._eviction_weight + conditions.eviction_rate * (
            1.0 - self._eviction_weight
        )
        return min(max(rate, 0.0), 1.0)

    def _compute_stabilization_rate(
        self,
        conditions: EconomicConditions,
    ) -> float:
        """Compute stabilization rate (L->P) per FR-016.

        Formula: base_stabilization * (1 - unemployment_rate)

        Args:
            conditions: Economic conditions.

        Returns:
            Stabilization rate [0, base_stabilization].
        """
        rate = self._base_stabilization * (1.0 - conditions.unemployment_rate)
        return min(max(rate, 0.0), 1.0)

    def _apply_flows(
        self,
        la: float,
        prol: float,
        lumpen: float,
        rates: TransitionRates,
    ) -> tuple[float, float, float]:
        """Apply transition flow equations.

        Flow equations from data-model.md:
            LA'     = LA     - dispossession*LA     + accumulation*Prol
            Prol'   = Prol   + dispossession*LA     - accumulation*Prol
                             - precaritization*Prol + stabilization*Lumpen
            Lumpen' = Lumpen + precaritization*Prol - stabilization*Lumpen

        Args:
            la: Current LA share.
            prol: Current proletariat share.
            lumpen: Current lumpenproletariat share.
            rates: Transition rates.

        Returns:
            Tuple of (new_la, new_prol, new_lumpen).
        """
        new_la = la - rates.dispossession * la + rates.accumulation * prol
        new_prol = (
            prol
            + rates.dispossession * la
            - rates.accumulation * prol
            - rates.precaritization * prol
            + rates.stabilization * lumpen
        )
        new_lumpen = lumpen + rates.precaritization * prol - rates.stabilization * lumpen

        return (new_la, new_prol, new_lumpen)

    def _normalize(
        self,
        la: float,
        prol: float,
        lumpen: float,
        fixed_share: float,
    ) -> tuple[float, float, float]:
        """Clamp and normalize dynamic shares to preserve sum-to-one.

        Algorithm (research.md §6):
        1. Clamp each share to [0.0, 1.0]
        2. Normalize so dynamic shares sum to (1.0 - fixed_share)

        Args:
            la: Raw LA share.
            prol: Raw proletariat share.
            lumpen: Raw lumpenproletariat share.
            fixed_share: Sum of bourgeoisie + petit-bourgeoisie shares.

        Returns:
            Normalized (la, prol, lumpen) tuple.
        """
        la = max(la, 0.0)
        prol = max(prol, 0.0)
        lumpen = max(lumpen, 0.0)

        total_dynamic = la + prol + lumpen
        target = 1.0 - fixed_share

        if total_dynamic > 0.0:
            scale = target / total_dynamic
            la *= scale
            prol *= scale
            lumpen *= scale
        else:
            # Degenerate case: distribute equally
            la = target / 3.0
            prol = target / 3.0
            lumpen = target / 3.0

        return (la, prol, lumpen)

    def _log_validation(self, rates: TransitionRates) -> None:
        """Log transition rate validation results.

        Args:
            rates: Transition rates to validate.
        """
        valid, message = validate_transition_rates(rates)
        if message is not None:
            logger.warning("Transition rate validation: %s", message)
        if not valid:
            logger.error("Transition rate FAIL: %s", message)


__all__ = ["DefaultClassTransitionEngine"]
