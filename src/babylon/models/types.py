"""Constrained value types for the Babylon simulation.

These Annotated type aliases provide runtime validation for numeric values.
Using Pydantic v2's Annotated pattern allows these types to be used
directly in any BaseModel field.

Types defined:
    Probability: [0.0, 1.0] - for P(S|A), P(S|R), tension
    Ideology: [-1.0, 1.0] - revolutionary to reactionary spectrum
    Currency: [0.0, inf) - wealth, wages, rent, GDP
    Intensity: [0.0, 1.0] - contradiction intensity
    Coefficient: [0.0, 1.0] - formula parameters (alpha, lambda, k)
    Ratio: (0.0, inf) - wage ratios, exchange ratios

Usage:
    from babylon.models.types import Probability, Currency

    class SurvivalState(BaseModel):
        p_acquiescence: Probability  # Automatically validated [0, 1]
        wealth: Currency             # Automatically validated [0, inf)

All types serialize to plain floats in JSON for compatibility with
the Ledger (SQLite) and NetworkX graph storage.
"""

from typing import Annotated

from pydantic import Field

# =============================================================================
# PROBABILITY TYPE [0.0, 1.0]
# =============================================================================

Probability = Annotated[
    float,
    Field(
        ge=0.0,
        le=1.0,
        description="Value in range [0.0, 1.0] representing likelihood",
    ),
]
"""Probability: [0.0, 1.0]

A probability represents the likelihood of an event occurring.
Used for:
- P(S|A): Probability of survival through acquiescence
- P(S|R): Probability of survival through revolution
- tension: Contradiction tension level

Boundary values:
- 0.0 = impossible event
- 1.0 = certain event
"""

# =============================================================================
# IDEOLOGY TYPE [-1.0, 1.0]
# =============================================================================

Ideology = Annotated[
    float,
    Field(
        ge=-1.0,
        le=1.0,
        description="Ideological position from revolutionary (-1) to reactionary (+1)",
    ),
]
"""Ideology: [-1.0, 1.0]

A class's ideological position on the revolutionary-reactionary spectrum.
Based on consciousness drift formula: dΨc/dt = k(1 - Wc/Vc) - λΨc

Boundary values:
- -1.0 = fully revolutionary (class conscious, anti-capitalist)
- +1.0 = fully reactionary (false consciousness, pro-status-quo)
-  0.0 = neutral/apolitical
"""

# =============================================================================
# CURRENCY TYPE [0.0, infinity)
# =============================================================================

Currency = Annotated[
    float,
    Field(
        ge=0.0,
        description="Non-negative economic value (wealth, wages, rent, GDP)",
    ),
]
"""Currency: [0.0, inf)

Economic value that cannot be negative. Used for:
- wealth: Accumulated resources
- wages: Payment for labor
- rent: Imperial rent (Φ)
- GDP: Aggregate output

Note: Debt is not modeled as negative currency but as a separate
relationship/obligation between entities.
"""

# =============================================================================
# INTENSITY TYPE [0.0, 1.0]
# =============================================================================

Intensity = Annotated[
    float,
    Field(
        ge=0.0,
        le=1.0,
        description="Contradiction intensity from dormant (0) to rupture (1)",
    ),
]
"""Intensity: [0.0, 1.0]

The intensity of a dialectical contradiction.
When intensity reaches 1.0, the contradiction triggers a phase transition
(synthesis, rupture, or suppression).

Boundary values:
- 0.0 = dormant (contradiction exists but not manifest)
- 1.0 = rupture threshold (phase transition imminent)
"""

# =============================================================================
# COEFFICIENT TYPE [0.0, 1.0]
# =============================================================================

Coefficient = Annotated[
    float,
    Field(
        ge=0.0,
        le=1.0,
        description="Formula parameter in range [0, 1]",
    ),
]
"""Coefficient: [0.0, 1.0]

A parameter that modifies the strength of an effect in formulas.
Used for:
- α (alpha): Extraction efficiency in imperial rent
- λ (lambda): Decay rate in consciousness drift
- k: Sensitivity coefficient in survival calculus

Boundary values:
- 0.0 = no effect
- 1.0 = maximum effect
"""

# =============================================================================
# RATIO TYPE (0.0, infinity)
# =============================================================================

Ratio = Annotated[
    float,
    Field(
        gt=0.0,
        description="Positive ratio comparing two quantities",
    ),
]
"""Ratio: (0.0, inf)

A ratio comparing two quantities. Zero is invalid because ratios
typically represent division results.

Used for:
- Wc/Vc: Labor aristocracy ratio (wages to value produced)
- ε: Exchange ratio in unequal exchange

Interpretation:
- Ratio = 1.0: Equal exchange / fair wages
- Ratio > 1.0: Core receives more than it gives (exploitation)
- Ratio < 1.0: Core receives less than it gives
"""
