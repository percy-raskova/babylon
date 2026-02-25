"""Type definitions for the TRPF counter-tendencies module.

Feature: 024-capital-volume-iii (US5)
"""

from __future__ import annotations

from typing import Final

# ============================================================================
# THRESHOLD CONSTANTS (Module-Level)
# ============================================================================

COUNTER_TENDENCY_WEIGHTS: Final[list[float]] = [0.20, 0.15, 0.15, 0.15, 0.20, 0.15]
"""Weights for the six TRPF counter-tendencies in net strength computation.

Order: [exploitation_rate, wage_suppression, capital_cheapening,
        reserve_army, imperial_rent, fictitious_profits]

Traceability: MLM-TW theory weights imperial rent (0.20) and exploitation
rate increase (0.20) higher than other counter-tendencies because these
are the primary mechanisms sustaining core profit rates. The remaining
four tendencies receive equal weight (0.15 each). Sum = 1.0.
"""
