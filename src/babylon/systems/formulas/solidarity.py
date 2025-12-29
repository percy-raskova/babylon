"""Solidarity Transmission formula (Sprint 3.4.2).

Consciousness spreads via solidarity edges: dPsi = sigma * (Psi_src - Psi_tgt).

Activation requires source_consciousness > threshold AND solidarity_strength > 0.
This implements the Fascist Bifurcation: no solidarity means no transmission.
"""


def calculate_solidarity_transmission(
    source_consciousness: float,
    target_consciousness: float,
    solidarity_strength: float,
    activation_threshold: float = 0.3,
) -> float:
    """Calculate consciousness delta via solidarity edge.

    Args:
        source_consciousness: Source consciousness level [0, 1].
        target_consciousness: Target consciousness level [0, 1].
        solidarity_strength: Edge strength [0, 1].
        activation_threshold: Minimum source level for transmission.

    Returns:
        Change in target consciousness. Negative if target > source.

    Examples:
        >>> round(calculate_solidarity_transmission(0.8, 0.2, 0.5), 2)
        0.3
        >>> calculate_solidarity_transmission(0.2, 0.5, 0.5)  # Below threshold
        0.0
    """
    if source_consciousness <= activation_threshold or solidarity_strength <= 0:
        return 0.0

    return solidarity_strength * (source_consciousness - target_consciousness)
