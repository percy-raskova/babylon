"""Factory functions for creating simulation entities.

These functions provide convenient ways to create SocialClass entities
with sensible defaults for class simulation. Each factory encapsulates
the defaults appropriate for a specific social class.

Factories support the **kwargs pattern for extensibility while
maintaining type safety through Pydantic validation.
"""

from __future__ import annotations

from babylon.models.entities.social_class import SocialClass
from babylon.models.enums import SocialRole
from babylon.models.types import Currency, Ideology, Probability


def create_proletariat(
    id: str = "C001",
    name: str = "Proletariat",
    wealth: Currency = 0.5,
    ideology: Ideology = -0.3,
    organization: Probability = 0.1,
    repression_faced: Probability = 0.5,
    subsistence_threshold: Currency = 0.3,
    p_acquiescence: Probability = 0.0,
    p_revolution: Probability = 0.0,
    description: str = "Exploited working class",
    **kwargs: object,
) -> SocialClass:
    """Create a proletariat (exploited class) social class.

    The proletariat is defined by:
    - PERIPHERY_PROLETARIAT role (exploited in the world system)
    - Low default wealth (0.5)
    - Slightly revolutionary ideology (-0.3)
    - Low organization (0.1 = 10%)
    - Moderate repression faced (0.5)

    Args:
        id: Unique identifier matching ^C[0-9]{3}$ pattern (default: "C001")
        name: Human-readable name (default: "Proletariat")
        wealth: Economic resources (default: 0.5)
        ideology: Ideological position, -1=revolutionary to +1=reactionary (default: -0.3)
        organization: Collective cohesion (default: 0.1)
        repression_faced: State violence level (default: 0.5)
        subsistence_threshold: Minimum wealth for survival (default: 0.3)
        p_acquiescence: P(S|A) - survival through acquiescence (default: 0.0, calculated by engine)
        p_revolution: P(S|R) - survival through revolution (default: 0.0, calculated by engine)
        description: Optional description (default: "Exploited working class")
        **kwargs: Additional fields passed to SocialClass

    Returns:
        SocialClass configured as proletariat

    Example:
        >>> worker = create_proletariat()
        >>> worker.role
        <SocialRole.PERIPHERY_PROLETARIAT: 'periphery_proletariat'>
        >>> worker.wealth
        0.5
    """
    return SocialClass(
        id=id,
        name=name,
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=wealth,
        ideology=ideology,
        organization=organization,
        repression_faced=repression_faced,
        subsistence_threshold=subsistence_threshold,
        p_acquiescence=p_acquiescence,
        p_revolution=p_revolution,
        description=description,
        **kwargs,
    )


def create_bourgeoisie(
    id: str = "C002",
    name: str = "Bourgeoisie",
    wealth: Currency = 10.0,
    ideology: Ideology = 0.8,
    organization: Probability = 0.7,
    repression_faced: Probability = 0.1,
    subsistence_threshold: Currency = 0.1,
    p_acquiescence: Probability = 0.0,
    p_revolution: Probability = 0.0,
    description: str = "Capital-owning exploiter class",
    **kwargs: object,
) -> SocialClass:
    """Create a bourgeoisie (exploiter class) social class.

    The bourgeoisie is defined by:
    - CORE_BOURGEOISIE role (exploiter in the world system)
    - High default wealth (10.0)
    - Reactionary ideology (0.8)
    - High organization (0.7 = 70%)
    - Low repression faced (0.1 - protected by state)

    Args:
        id: Unique identifier matching ^C[0-9]{3}$ pattern (default: "C002")
        name: Human-readable name (default: "Bourgeoisie")
        wealth: Economic resources (default: 10.0)
        ideology: Ideological position, -1=revolutionary to +1=reactionary (default: 0.8)
        organization: Collective cohesion (default: 0.7)
        repression_faced: State violence level (default: 0.1)
        subsistence_threshold: Minimum wealth for survival (default: 0.1)
        p_acquiescence: P(S|A) - survival through acquiescence (default: 0.0, calculated by engine)
        p_revolution: P(S|R) - survival through revolution (default: 0.0, calculated by engine)
        description: Optional description (default: "Capital-owning exploiter class")
        **kwargs: Additional fields passed to SocialClass

    Returns:
        SocialClass configured as bourgeoisie

    Example:
        >>> owner = create_bourgeoisie()
        >>> owner.role
        <SocialRole.CORE_BOURGEOISIE: 'core_bourgeoisie'>
        >>> owner.wealth
        10.0
    """
    return SocialClass(
        id=id,
        name=name,
        role=SocialRole.CORE_BOURGEOISIE,
        wealth=wealth,
        ideology=ideology,
        organization=organization,
        repression_faced=repression_faced,
        subsistence_threshold=subsistence_threshold,
        p_acquiescence=p_acquiescence,
        p_revolution=p_revolution,
        description=description,
        **kwargs,
    )
