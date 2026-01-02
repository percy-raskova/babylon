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
    EntityProtocol: Protocol for entities with lifecycle state (Sprint 1.X D2)

Usage:
    from babylon.models.types import Probability, Currency

    class SurvivalState(BaseModel):
        p_acquiescence: Probability  # Automatically validated [0, 1]
        wealth: Currency             # Automatically validated [0, inf)

All types serialize to plain floats in JSON for compatibility with
the Ledger (SQLite) and NetworkX graph storage.

Epoch 0 Physics Hardening (Gatekeeper Pattern):
    All constrained types apply SnapToGrid quantization via AfterValidator.
    Values are snapped to a 10^-5 grid (0.00001 resolution) to prevent
    floating-point drift accumulation over long simulations.
"""

from typing import Annotated, Protocol, runtime_checkable

from pydantic import AfterValidator, Field

from babylon.utils.math import quantize

# =============================================================================
# QUANTIZATION VALIDATOR (Gatekeeper Pattern)
# =============================================================================

# Reusable validator - applies quantization after Pydantic's range validation
# This ensures values are on the precision grid AFTER ge/le/gt validators run
SnapToGrid = AfterValidator(quantize)

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
    SnapToGrid,
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

Note: Values are quantized to 10^-5 precision via SnapToGrid.
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
    SnapToGrid,
]
"""Ideology: [-1.0, 1.0]

A class's ideological position on the revolutionary-reactionary spectrum.
Based on consciousness drift formula: dPsi_c/dt = k(1 - Wc/Vc) - lambda*Psi_c

Boundary values:
- -1.0 = fully revolutionary (class conscious, anti-capitalist)
- +1.0 = fully reactionary (false consciousness, pro-status-quo)
-  0.0 = neutral/apolitical

Note: Values are quantized to 10^-5 precision via SnapToGrid.
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
    SnapToGrid,
]
"""Currency: [0.0, inf)

Economic value that cannot be negative. Used for:
- wealth: Accumulated resources
- wages: Payment for labor
- rent: Imperial rent (Phi)
- GDP: Aggregate output

Note: Debt is not modeled as negative currency but as a separate
relationship/obligation between entities.

Note: Values are quantized to 10^-5 precision via SnapToGrid.
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
    SnapToGrid,
]
"""Intensity: [0.0, 1.0]

The intensity of a dialectical contradiction.
When intensity reaches 1.0, the contradiction triggers a phase transition
(synthesis, rupture, or suppression).

Boundary values:
- 0.0 = dormant (contradiction exists but not manifest)
- 1.0 = rupture threshold (phase transition imminent)

Note: Values are quantized to 10^-5 precision via SnapToGrid.
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
    SnapToGrid,
]
"""Coefficient: [0.0, 1.0]

A parameter that modifies the strength of an effect in formulas.
Used for:
- alpha: Extraction efficiency in imperial rent
- lambda: Decay rate in consciousness drift
- k: Sensitivity coefficient in survival calculus

Boundary values:
- 0.0 = no effect
- 1.0 = maximum effect

Note: Values are quantized to 10^-5 precision via SnapToGrid.
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
    SnapToGrid,
]
"""Ratio: (0.0, inf)

A ratio comparing two quantities. Zero is invalid because ratios
typically represent division results.

Used for:
- Wc/Vc: Labor aristocracy ratio (wages to value produced)
- epsilon: Exchange ratio in unequal exchange

Interpretation:
- Ratio = 1.0: Equal exchange / fair wages
- Ratio > 1.0: Core receives more than it gives (exploitation)
- Ratio < 1.0: Core receives less than it gives

Note: Values are quantized to 10^-5 precision via SnapToGrid.
"""

# =============================================================================
# GINI TYPE [0.0, 1.0] (Mass Line Refactor)
# =============================================================================

Gini = Annotated[
    float,
    Field(
        ge=0.0,
        le=1.0,
        description="Gini coefficient measuring intra-class inequality",
    ),
    SnapToGrid,
]
"""Gini: [0.0, 1.0]

Intra-class inequality coefficient (Mass Line Refactor).
Determines what fraction of wealth the marginal worker (bottom 40%) receives.

Used for:
- inequality: Intra-class wealth distribution within a demographic block

Boundary values:
- 0.0 = Perfect equality (mean = median, everyone gets equal share)
- 1.0 = Maximum tyranny (Pareto extreme: bottom majority has nothing)

The Grinding Attrition Formula uses this to calculate marginal wealth:
    marginal_wealth = per_capita_wealth × (1 - gini)

At gini=0: marginal_wealth = average (all survive if average suffices)
At gini=1: marginal_wealth = 0 (marginal workers always starve)

Note: Values are quantized to 10^-5 precision via SnapToGrid.
"""

# =============================================================================
# ENTITY PROTOCOL (Sprint 1.X Deliverable 2: Strict Typing)
# =============================================================================


@runtime_checkable
class EntityProtocol(Protocol):
    """Protocol for entities with lifecycle state.

    Any object implementing this protocol can be checked for death
    using is_dead() or similar lifecycle functions. This prevents
    type errors where floats, dicts, or other non-entity types are
    accidentally passed to lifecycle functions.

    Implementors:
        - SocialClass: Has active field (True = alive, False = dead)

    Sprint 1.X D2 Pain Point #3: Loose typing allowed bugs like
    is_dead(float) instead of is_dead(Entity).

    Example:
        >>> from babylon.models.types import EntityProtocol
        >>> from babylon.models import SocialClass
        >>>
        >>> worker = SocialClass(id="C001", name="Worker", ...)
        >>> isinstance(worker, EntityProtocol)  # True
        >>> is_dead(worker)  # Works
        >>>
        >>> is_dead(0.5)  # TypeError: expected EntityProtocol
    """

    @property
    def active(self) -> bool:
        """Whether the entity is alive/active.

        Returns:
            True if the entity is alive, False if dead.
        """
        ...
