"""Metabolic Rift formulas (Slice 1.4).

Ecological limits on capital accumulation:
- Biocapacity Delta: dB = R - (E * eta) where R=regeneration, E=extraction, eta=entropy
- Overshoot Ratio: O = C / B where C=consumption, B=biocapacity (O>1 = ecological overshoot)
"""


def calculate_biocapacity_delta(
    regeneration_rate: float,
    max_biocapacity: float,
    extraction_intensity: float,
    current_biocapacity: float,
    entropy_factor: float = 1.2,
) -> float:
    """Calculate change in biocapacity stock: dB = R - (E * eta).

    The core metabolic formula. Extraction always costs more than
    the raw value obtained due to entropy/waste (eta > 1.0).

    Args:
        regeneration_rate: Fraction of max_biocapacity restored per tick [0, 1]
        max_biocapacity: Maximum biocapacity ceiling
        extraction_intensity: Current extraction pressure [0, 1]
        current_biocapacity: Current biocapacity stock
        entropy_factor: Waste multiplier for extraction (default 1.2)

    Returns:
        Change in biocapacity (positive = regeneration, negative = depletion)

    Examples:
        >>> calculate_biocapacity_delta(0.02, 100.0, 0.0, 50.0)  # No extraction
        2.0
        >>> calculate_biocapacity_delta(0.02, 100.0, 0.05, 50.0)  # Light extraction
        -1.0
        >>> calculate_biocapacity_delta(0.02, 100.0, 0.0, 100.0)  # At max, no regen
        0.0
    """
    # Regeneration logic: Linear up to max
    regeneration = regeneration_rate * max_biocapacity

    # If already at/above max, no regen
    if current_biocapacity >= max_biocapacity:
        regeneration = 0.0

    # Extraction logic (scales with availability)
    raw_extraction = extraction_intensity * current_biocapacity

    # Entropy penalty
    ecological_cost = raw_extraction * entropy_factor

    delta = regeneration - ecological_cost
    return delta


def calculate_overshoot_ratio(
    total_consumption: float,
    total_biocapacity: float,
    max_ratio: float = 999.0,
) -> float:
    """Calculate ecological overshoot ratio: O = C / B.

    When O > 1.0, consumption exceeds biocapacity (overshoot).
    When O <= 1.0, the system is within ecological limits.

    Args:
        total_consumption: Total consumption needs across all entities
        total_biocapacity: Total available biocapacity
        max_ratio: Cap for ratio when biocapacity depleted (default 999.0)

    Returns:
        Overshoot ratio (>1.0 = ecological overshoot)

    Examples:
        >>> calculate_overshoot_ratio(100.0, 200.0)  # Sustainable
        0.5
        >>> calculate_overshoot_ratio(200.0, 100.0)  # Overshoot
        2.0
        >>> calculate_overshoot_ratio(100.0, 0.0)  # Depleted biocapacity
        999.0
    """
    if total_biocapacity <= 0:
        return max_ratio  # Cap at high value instead of inf

    return total_consumption / total_biocapacity
