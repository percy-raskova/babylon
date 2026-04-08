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

from typing import TYPE_CHECKING

from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.entity_registry import COMPRADOR_ID, PERIPHERY_WORKER_ID
from babylon.models.enums import SocialRole
from babylon.models.types import Currency, Probability

if TYPE_CHECKING:
    from babylon.models.entities.contradiction import ContradictionFrame


def create_proletariat(
    id: str = PERIPHERY_WORKER_ID,
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
    id: str = COMPRADOR_ID,
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


def create_contradiction_frame(scope: str = "global") -> ContradictionFrame:
    """Create a ContradictionFrame for the given simulation scope.

    Args:
        scope: The scope identifier (e.g., "global", "national").

    Returns:
        A new ContradictionFrame for the given scope.
    """
    # Import locally to avoid circular dependencies
    from babylon.models.entities.contradiction import Contradiction, ContradictionFrame
    from babylon.models.enums import CommunityType, ContradictionType, EdgeMode, SocialRole

    if scope == "global":
        return ContradictionFrame(
            principal=Contradiction(
                id="global_imperial_contradiction",
                type=ContradictionType.IMPERIAL,
                aspect_a=CommunityType.SETTLER,
                aspect_b=CommunityType.NEW_AFRIKAN,  # Proxy for oppressed nations in default test scenarios
                principal_aspect="a",
                identity=0.5,
                form_of_struggle=EdgeMode.EXTRACTIVE,
                intensity=0.5,
                aspect_balance=0.0,
            ),
            secondary=Contradiction(
                id="global_class_contradiction",
                type=ContradictionType.CLASS,
                aspect_a=SocialRole.CORE_BOURGEOISIE,
                aspect_b=SocialRole.PERIPHERY_PROLETARIAT,
                principal_aspect="a",
                identity=0.8,
                form_of_struggle=EdgeMode.EXTRACTIVE,
                intensity=0.3,
                aspect_balance=0.0,
            ),
        )

    # Fallback to a default generic frame
    return ContradictionFrame(
        principal=Contradiction(
            id=f"{scope}_principal_contradiction",
            type=ContradictionType.CLASS,
            aspect_a=SocialRole.CORE_BOURGEOISIE,
            aspect_b=SocialRole.PERIPHERY_PROLETARIAT,
            principal_aspect="a",
            identity=0.8,
            form_of_struggle=EdgeMode.EXTRACTIVE,
            intensity=0.1,
            aspect_balance=0.0,
        ),
        secondary=Contradiction(
            id=f"{scope}_secondary_contradiction",
            type=ContradictionType.NATIONAL,
            aspect_a=CommunityType.SETTLER,
            aspect_b=CommunityType.NEW_AFRIKAN,
            principal_aspect="a",
            identity=0.5,
            form_of_struggle=EdgeMode.EXTRACTIVE,
            intensity=0.05,
            aspect_balance=0.0,
        ),
    )
