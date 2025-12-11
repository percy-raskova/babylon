"""Factory functions for creating simulation entities.

These functions provide convenient ways to create SocialClass entities
with sensible defaults for class simulation. Each factory encapsulates
the defaults appropriate for a specific social class.

Factories support the ``**kwargs`` pattern for extensibility while
maintaining type safety through Pydantic validation.

Sprint 3.4.3 (George Jackson Refactor): ideology parameter accepts both
float (legacy) and IdeologicalProfile (new format). Float values are
automatically converted to IdeologicalProfile by the SocialClass validator.
"""

from __future__ import annotations

from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.enums import SocialRole
from babylon.models.types import Currency, Probability


def create_proletariat(
    id: str = "C001",
    name: str = "Proletariat",
    wealth: Currency = 0.5,
    ideology: float | IdeologicalProfile = -0.3,
    organization: Probability = 0.1,
    repression_faced: Probability = 0.5,
    subsistence_threshold: Currency = 0.3,
    p_acquiescence: Probability = 0.0,
    p_revolution: Probability = 0.0,
    description: str = "Exploited working class",
    effective_wealth: Currency = 0.0,
    unearned_increment: Currency = 0.0,
    ppp_multiplier: float = 1.0,
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
        effective_wealth: PPP-adjusted wealth (default: 0.0, calculated by engine)
        unearned_increment: PPP bonus (default: 0.0, calculated by engine)
        ppp_multiplier: PPP multiplier applied to wages (default: 1.0)

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
        ideology=ideology,  # type: ignore[arg-type]  # Validator converts float to IdeologicalProfile
        organization=organization,
        repression_faced=repression_faced,
        subsistence_threshold=subsistence_threshold,
        p_acquiescence=p_acquiescence,
        p_revolution=p_revolution,
        description=description,
        effective_wealth=effective_wealth,
        unearned_increment=unearned_increment,
        ppp_multiplier=ppp_multiplier,
    )


def create_bourgeoisie(
    id: str = "C002",
    name: str = "Bourgeoisie",
    wealth: Currency = 10.0,
    ideology: float | IdeologicalProfile = 0.8,
    organization: Probability = 0.7,
    repression_faced: Probability = 0.1,
    subsistence_threshold: Currency = 0.1,
    p_acquiescence: Probability = 0.0,
    p_revolution: Probability = 0.0,
    description: str = "Capital-owning exploiter class",
    effective_wealth: Currency = 0.0,
    unearned_increment: Currency = 0.0,
    ppp_multiplier: float = 1.0,
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
        effective_wealth: PPP-adjusted wealth (default: 0.0, calculated by engine)
        unearned_increment: PPP bonus (default: 0.0, calculated by engine)
        ppp_multiplier: PPP multiplier applied to wages (default: 1.0)

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
        ideology=ideology,  # type: ignore[arg-type]  # Validator converts float to IdeologicalProfile
        organization=organization,
        repression_faced=repression_faced,
        subsistence_threshold=subsistence_threshold,
        p_acquiescence=p_acquiescence,
        p_revolution=p_revolution,
        description=description,
        effective_wealth=effective_wealth,
        unearned_increment=unearned_increment,
        ppp_multiplier=ppp_multiplier,
    )
