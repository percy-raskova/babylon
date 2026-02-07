"""Crisis and Devaluation Mechanics package (Feature 018).

Provides crisis detection, bifurcation risk assessment, and related
mechanics for modeling economic crisis lifecycle dynamics.

See Also:
    :mod:`babylon.economics.tick.types`: CrisisPhase, CrisisState
    :mod:`babylon.economics.tick.crisis_detector`: MultiPeriodCrisisDetector
    :mod:`babylon.economics.crisis.bifurcation`: BifurcationRiskCalculator
"""

from babylon.economics.crisis.bifurcation import BifurcationRiskCalculator

__all__ = ["BifurcationRiskCalculator"]
