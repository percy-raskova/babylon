"""Reactionary-subject formulas (spec-071).

The fascism branch of the George Jackson bifurcation (Constitution I.4). When
the imperial bribe (Φ) decays, crisis agitation that would route to
revolution under solidarity instead routes to **fascism** in its absence. The
privileged strata (labor aristocracy, petty/comprador bourgeoisie) carry an
**entitlement** — a stake in the imperial order — that amplifies agitation
into a **fascist pull**.

Structural provenance (Constitution III.8): ``entitlement`` is the material
stake in imperial rent; ``solidarity`` in the denominator is the
cross-colonial bridge (I.4) that reroutes agitation to revolution — its
presence suppresses the fascist pull. These are pure, deterministic
functions; all defaults trace to :class:`babylon.config.defines.ReactionaryDefines`.

See Also:
    :class:`babylon.engine.systems.reactionary.FascistFactionSystem`: the
        system that applies these formulas.
    :func:`babylon.formulas.consciousness_routing.route_agitation_to_ternary`:
        the revolutionary-vs-fascist split of raw agitation.
"""

from __future__ import annotations

import math

from babylon.config.defines import GameDefines

_DEFINES = GameDefines()
_REACT = _DEFINES.reactionary


def calculate_fascist_pull(
    agitation: float,
    entitlement: float,
    solidarity: float,
    epsilon: float = _REACT.solidarity_pull_epsilon,
) -> float:
    """Fascist pull on an entitled stratum under crisis.

    ``Fascist_Pull = Agitation × (Entitlement / (Solidarity + ε))``.

    Crisis-gated: with zero agitation the pull is zero (hegemony holds — the
    Fundamental Theorem). Solidarity in the denominator suppresses the pull
    (I.4: solidarity across the colonial divide reroutes agitation to
    revolution). The ``ε`` guard both prevents division by zero and sets the
    maximal unsuppressed pull.

    Args:
        agitation: Raw crisis energy [0, ∞) from falling wages / rising
            exploitation (:mod:`babylon.formulas.consciousness_routing`).
        entitlement: The stratum's stake in the imperial order [0, 1].
        solidarity: Incident solidarity strength [0, 1] — the cross-colonial
            bridge that dampens reaction.
        epsilon: Denominator guard (default from ReactionaryDefines).

    Returns:
        The fascist pull (≥ 0). Compared against
        ``ReactionaryDefines.fascist_pull_threshold`` by the system.

    Example:
        >>> calculate_fascist_pull(agitation=2.0, entitlement=0.8, solidarity=0.0, epsilon=0.1)
        16.0
        >>> calculate_fascist_pull(agitation=0.0, entitlement=0.8, solidarity=0.0)
        0.0
    """
    return agitation * (entitlement / (solidarity + epsilon))


def calculate_defection_probability(chauvinism: float, discipline: float) -> float:
    """Probability an entitled org member defects under crisis.

    ``P_defection = sigmoid(chauvinism − discipline)``. Chauvinism is the
    accumulated reactionary sentiment of a labor-aristocratic recruit;
    discipline is the organization's counter-pressure. At parity the
    probability is 0.5.

    Args:
        chauvinism: Accumulated reactionary sentiment [0, 1].
        discipline: Organizational counter-pressure [0, 1].

    Returns:
        Defection probability in [0, 1] (bounded by the sigmoid).

    Example:
        >>> calculate_defection_probability(chauvinism=0.5, discipline=0.5)
        0.5
    """
    exponent = -(chauvinism - discipline)
    exponent = max(-500.0, min(500.0, exponent))
    return 1.0 / (1.0 + math.exp(exponent))


def calculate_spontaneous_riot_risk(volatility: float, discipline: float) -> float:
    """Undirected-disorder risk for the declassed lumpenproletariat.

    ``riot_risk = volatility × (1 − discipline)``, clamped to [0, 1]. High
    volatility with low organizational discipline produces spontaneous,
    non-revolutionary disorder — the reactionary inverse of the organized,
    solidarity-building UPRISING (it destroys wealth but builds no solidarity).

    Args:
        volatility: The stratum's disorder propensity [0, 1].
        discipline: Organizational discipline gating the volatility [0, 1].

    Returns:
        Riot risk in [0, 1]. Compared against
        ``ReactionaryDefines.spontaneous_riot_threshold``.

    Example:
        >>> calculate_spontaneous_riot_risk(volatility=0.8, discipline=0.0)
        0.8
        >>> calculate_spontaneous_riot_risk(volatility=0.8, discipline=1.0)
        0.0
    """
    risk = volatility * (1.0 - discipline)
    return max(0.0, min(1.0, risk))


def calculate_entitlement_effective(
    base_entitlement: float,
    threat: float,
    threat_gain: float = _REACT.entitlement_threat_gain,
) -> float:
    """Effective entitlement under threat (a threatened stake reacts harder).

    ``effective = clamp(base + threat_gain × threat × (1 − base), 0, 1)``. A
    stake under threat (loss of privilege) amplifies toward the ceiling; with
    no threat the effective value passes the base through unchanged.

    Args:
        base_entitlement: The node's base entitlement [0, 1].
        threat: Perceived threat to the stake [0, 1] (e.g., falling Φ).
        threat_gain: Amplification coefficient (default from ReactionaryDefines).

    Returns:
        Effective entitlement in [0, 1].

    Example:
        >>> calculate_entitlement_effective(base_entitlement=0.8, threat=0.0)
        0.8
    """
    effective = base_entitlement + threat_gain * threat * (1.0 - base_entitlement)
    return max(0.0, min(1.0, effective))


__all__ = [
    "calculate_defection_probability",
    "calculate_entitlement_effective",
    "calculate_fascist_pull",
    "calculate_spontaneous_riot_risk",
]
