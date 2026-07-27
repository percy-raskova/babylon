"""Behavioral contract for the ``politics:`` defines namespace (P25 U1, ADR127).

Pins the A6 tier invariants declared at birth: the valve suppresses and never
amplifies (Θ_theory sign law), the Φ social share is a bounded slice (the
anti-list row: no θ may let the social wage mint value), and the election
clocks are strictly positive tick counts.
"""

import pytest
from pydantic import ValidationError

from babylon.config.defines import GameDefines, PoliticsDefines


def test_game_defines_carries_politics_category():
    defines = GameDefines()
    assert isinstance(defines.politics, PoliticsDefines)


def test_politics_defines_is_frozen():
    politics = PoliticsDefines()
    with pytest.raises(ValidationError):
        politics.valve_strength = 0.9


def test_valve_strength_is_a_suppression_share():
    # Θ_theory sign law: the valve multiplies conversion by (1 − v·H); v ∈ [0, 1]
    # keeps the multiplier in [0, 1] for any H ∈ [0, 1] — hope never AMPLIFIES organizing.
    assert 0.0 <= PoliticsDefines().valve_strength <= 1.0
    with pytest.raises(ValidationError):
        PoliticsDefines(valve_strength=1.5)
    with pytest.raises(ValidationError):
        PoliticsDefines(valve_strength=-0.1)


def test_phi_social_share_is_a_bounded_slice():
    # Anti-list row (brief §5.3): reform redistributes WITHIN measured surplus —
    # a share above 1.0 would let SW_deliverable mint value and break T-6's premise.
    with pytest.raises(ValidationError):
        PoliticsDefines(phi_social_share=1.2)


def test_election_clocks_are_positive_per_level():
    clocks = PoliticsDefines().cycle_ticks
    assert set(clocks) == {"federal", "state", "local"}
    assert all(ticks >= 1 for ticks in clocks.values())
    with pytest.raises(ValidationError):
        PoliticsDefines(cycle_ticks={"federal": 0, "state": 104, "local": 52})


def test_disillusion_window_is_at_least_one_tick():
    with pytest.raises(ValidationError):
        PoliticsDefines(disillusion_window_ticks=0)


def test_u8_drift_and_conversion_rates_are_bounded_shares():
    """U8 (ADR134): the Agitation->Organization conversion rate and the two
    live allegiance-drift rates (align/contact) are [0,1]-bounded pacing
    knobs — the media and betrayal drift terms wait for their producers
    (ISA_COMM apparatus; U9 delivery gaps)."""
    defines = PoliticsDefines()
    assert 0.0 <= defines.organizing_conversion_rate <= 1.0
    assert 0.0 <= defines.allegiance_align_rate <= 1.0
    assert 0.0 <= defines.allegiance_contact_rate <= 1.0
    with pytest.raises(ValidationError):
        PoliticsDefines(organizing_conversion_rate=1.5)
    with pytest.raises(ValidationError):
        PoliticsDefines(allegiance_align_rate=-0.1)
    with pytest.raises(ValidationError):
        PoliticsDefines(allegiance_contact_rate=2.0)
