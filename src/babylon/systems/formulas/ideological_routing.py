"""Ideological Routing formulas (Sprint 3.4.3 - George Jackson Refactor).

Theory
------
Multi-dimensional consciousness routing based on George Jackson's analysis:
"Fascism is the defensive form of capitalism."

When material conditions deteriorate (wage cuts, wealth extraction), workers
experience "agitation energy" that must route somewhere:

- **With Solidarity**: Agitation -> Class Consciousness (revolutionary path)
- **Without Solidarity**: Agitation -> National Identity (fascist path)

Historical Examples:

- Germany 1933: Crisis + atomized workers -> Fascism
- Russia 1917: Crisis + organized workers -> Revolution

Formulas
--------
Agitation Generation::

    agitation = |material_loss| * LOSS_AVERSION_COEFFICIENT

Routing Split::

    class_delta = agitation * solidarity_factor * 0.1
    nation_delta = agitation * (1 - solidarity_factor) * 0.1

See Also
--------
:mod:`~babylon.systems.formulas.fundamental_theorem` : Consciousness drift
:mod:`~babylon.systems.formulas.solidarity` : Solidarity transmission
"""

from babylon.systems.formulas.constants import LOSS_AVERSION_COEFFICIENT

# Routing scale factor (converts agitation to consciousness change)
_ROUTING_SCALE = 0.1


def _calculate_material_loss(wage_change: float, wealth_change: float) -> float:
    """Sum absolute values of negative wage/wealth changes."""
    loss = 0.0
    if wage_change < 0:
        loss += abs(wage_change)
    if wealth_change < 0:
        loss += abs(wealth_change)
    return loss


def _route_agitation(
    agitation: float,
    solidarity_pressure: float,
    current_class: float,
    current_nation: float,
    decay: float,
) -> tuple[float, float, float]:
    """Route agitation to class consciousness or national identity."""
    if agitation <= 0:
        return current_class, current_nation, agitation

    solidarity_factor = min(1.0, solidarity_pressure)

    class_delta = agitation * solidarity_factor * _ROUTING_SCALE
    nation_delta = agitation * (1.0 - solidarity_factor) * _ROUTING_SCALE

    new_class = min(1.0, current_class + class_delta)
    new_nation = min(1.0, current_nation + nation_delta)
    new_agitation = max(0.0, agitation * (1.0 - decay))

    return new_class, new_nation, new_agitation


def calculate_ideological_routing(
    wage_change: float,
    wealth_change: float,
    solidarity_pressure: float,
    current_class_consciousness: float,
    current_national_identity: float,
    current_agitation: float,
    agitation_decay: float = 0.1,
) -> tuple[float, float, float]:
    """Route agitation energy based on solidarity infrastructure.

    Args:
        wage_change: Change in wages (negative = crisis).
        wealth_change: Change in wealth (negative = extraction).
        solidarity_pressure: Incoming SOLIDARITY edge strengths [0, inf).
        current_class_consciousness: Current class consciousness [0, 1].
        current_national_identity: Current national identity [0, 1].
        current_agitation: Accumulated agitation [0, inf).
        agitation_decay: Decay rate per tick (default 0.1).

    Returns:
        Tuple of (new_class_consciousness, new_national_identity, new_agitation).

    Example:
        >>> cc, ni, ag = calculate_ideological_routing(-20.0, 0.0, 0.9, 0.5, 0.5, 0.0)
        >>> cc > 0.5  # High solidarity routes to class consciousness
        True
    """
    # Generate agitation from material loss
    material_loss = _calculate_material_loss(wage_change, wealth_change)
    new_agitation = current_agitation
    if material_loss > 0:
        new_agitation += material_loss * LOSS_AVERSION_COEFFICIENT

    # Route agitation based on solidarity
    return _route_agitation(
        new_agitation,
        solidarity_pressure,
        current_class_consciousness,
        current_national_identity,
        agitation_decay,
    )
