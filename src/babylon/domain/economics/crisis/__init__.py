"""Crisis and Devaluation Mechanics package (Feature 018).

Provides crisis detection, bifurcation risk assessment, and related
mechanics for modeling economic crisis lifecycle dynamics.

See Also:
    :mod:`babylon.domain.economics.tick.types`: CrisisPhase, CrisisState
    :mod:`babylon.domain.economics.tick.crisis_detector`: MultiPeriodCrisisDetector
    :mod:`babylon.domain.economics.crisis.bifurcation`: BifurcationRiskCalculator
"""

from babylon.domain.economics.crisis.bifurcation import BifurcationRiskCalculator
from babylon.domain.economics.crisis.wage_compression import (
    apply_wage_compression,
    should_halt_accumulation,
)

__all__ = [
    "BifurcationRiskCalculator",
    "apply_wage_compression",
    "should_halt_accumulation",
]
