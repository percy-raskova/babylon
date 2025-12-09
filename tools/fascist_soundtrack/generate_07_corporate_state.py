#!/usr/bin/env python3
"""
Track 07: "The Corporate State" (4:00)
Mood: COLD/ANXIOUS - Calculating, deeply unsettling

Capitalism's marriage to authoritarianism - board rooms and jackboots.
Cold, precise, inhuman bureaucracy serving profit and power.

Musical approach:
- Harpsichord representing bureaucratic coldness
- Strings providing veneer of respectability
- Brass interventions (state backing corporate interests)
- Precise, mechanical, inhuman
- Slower tempo - calculated, deliberate evil

Tempo: 96 BPM | Key: E Phrygian
Target duration: 4:00 (~96 bars at 96 BPM)
"""

from . import (
    A3,
    B2,
    B3,
    CH_BRASS,
    CH_HARPSI,
    CH_ORGAN,
    CH_STRINGS,
    CH_TIMPANI,
    E2,
    E3,
    E4,
    E5,
    F3,
    G3,
    G4,
    Bb3,
    create_midi,
    save_midi,
    setup_standard_tracks,
)

TEMPO = 96
TOTAL_BARS = 96  # ~4:00 at 96 BPM


def create_corporate_state():
    """Generate The Corporate State - cold bureaucratic evil."""
    midi = create_midi(5)
    setup_standard_tracks(midi, TEMPO)

    # === SECTION A: The Board Room (bars 1-24) ===
    section_a_boardroom(midi)

    # === SECTION B: Corporate Machinery (bars 25-52) ===
    section_b_machinery(midi)

    # === SECTION C: State Backing (bars 53-76) ===
    section_c_backing(midi)

    # === SECTION D: The Calculation (bars 77-96) ===
    section_d_calculation(midi)

    return midi


def section_a_boardroom(midi):
    """The board room - cold, precise, calculating."""

    # Harpsichord - typewriter-like precision
    for bar in range(24):
        time = bar * 4
        vel = 55 + bar // 2

        # Precise, measured pattern
        pattern = [E3, E3, E3, F3, E3, E3, E3, G3]  # Repetitive, cold
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.35, min(vel, 68))

    # Strings - veneer of respectability
    for bar in range(8, 24):
        time = bar * 4
        vel = 40 + (bar - 8)

        # Smooth, polite surface
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 4, min(vel, 55))
        if bar >= 16:
            midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 4, min(vel - 10, 50))

    # Timpani - subtle clock (time is money)
    for bar in range(12, 24):
        time = bar * 4
        vel = 35 + (bar - 12) * 2

        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, min(vel, 55))
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, min(vel - 10, 50))

    # Organ - barely audible authority
    for bar in range(16, 24):
        time = bar * 4
        vel = 30 + (bar - 16) * 2

        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, vel)


def section_b_machinery(midi):
    """Corporate machinery - the bureaucratic machine in motion."""

    base_bar = 24

    # Harpsichord - full bureaucratic operation
    for bar in range(28):
        time = (base_bar + bar) * 4

        # Layer 1: Base pattern
        pattern = [E3, E3, F3, E3, E3, G3, E3, A3]
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.35, 68)

        # Layer 2: Counter-pattern (offset)
        if bar % 2 == 1:
            counter = [E4, G4, E4, B3]
            for i, note in enumerate(counter):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + 0.25 + i * 0.5, 0.3, 58)

    # Strings - continuous respectability
    for bar in range(28):
        time = (base_bar + bar) * 4

        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 4, 55)
        midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 4, 50)

        # Occasional higher register - board room presentation
        if bar % 8 >= 4:
            midi.addNote(CH_STRINGS, CH_STRINGS, E4, time, 4, 50)

    # Timpani - steady clock
    for bar in range(28):
        time = (base_bar + bar) * 4

        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, 60)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, 55)

    # Organ - growing presence
    for bar in range(28):
        time = (base_bar + bar) * 4
        vel = 40 + bar // 2

        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, min(vel, 55))

    # Brass - corporate announcements
    announcement_bars = [8, 16, 24]
    for bar in announcement_bars:
        time = (base_bar + bar) * 4

        midi.addNote(CH_BRASS, CH_BRASS, E3, time, 1, 70)
        midi.addNote(CH_BRASS, CH_BRASS, B3, time, 1, 65)


def section_c_backing(midi):
    """State backing - the marriage of corporate and state power."""

    base_bar = 52

    # Harpsichord - continues relentless
    for bar in range(24):
        time = (base_bar + bar) * 4

        pattern = [E3, F3, E3, G3, E3, F3, E3, A3]
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.35, 70)

    # Strings - tension underneath respectability
    for bar in range(24):
        time = (base_bar + bar) * 4

        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 4, 58)
        midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 4, 52)

        # Tremolo on high strings - anxiety under surface
        if bar % 4 >= 2:
            midi.addNote(CH_STRINGS, CH_STRINGS, E5, time, 4, 45)

    # Timpani - more insistent
    for bar in range(24):
        time = (base_bar + bar) * 4

        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, 70)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 1, 0.25, 50)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, 65)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3, 0.25, 50)

    # Organ - state authority
    for bar in range(24):
        time = (base_bar + bar) * 4

        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 60)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, 50)

    # Brass - state power backing corporate interests
    for bar in range(24):
        time = (base_bar + bar) * 4

        if bar % 4 == 0:
            # Corporate-state chord
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 1, 80)
            midi.addNote(CH_BRASS, CH_BRASS, B3, time, 1, 75)
            midi.addNote(CH_BRASS, CH_BRASS, E4, time, 1, 70)

        if bar % 8 == 4:
            # State enforcement
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 0.5, 85)
            midi.addNote(CH_BRASS, CH_BRASS, E4, time, 0.5, 80)

        # Tritone hint - the evil underneath
        if bar % 12 == 8:
            midi.addNote(CH_BRASS, CH_BRASS, E3, time + 2, 0.5, 75)
            midi.addNote(CH_BRASS, CH_BRASS, Bb3, time + 2, 0.5, 70)


def section_d_calculation(midi):
    """The calculation - pure bureaucratic evil."""

    base_bar = 76

    # Harpsichord - coldest, most precise
    for bar in range(20):
        time = (base_bar + bar) * 4
        vel = 65 if bar < 12 else 60 - (bar - 12)

        pattern = [E3, E3, F3, E3, E3, G3, E3, E3]  # Extra cold
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.35, max(vel, 50))

    # Strings - fading respectability
    for bar in range(20):
        time = (base_bar + bar) * 4
        vel = 55 if bar < 12 else 50 - (bar - 12) * 2

        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 4, max(vel, 35))
        if bar < 12:
            midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 4, max(vel - 10, 30))

    # Timpani - clock continues
    for bar in range(20):
        time = (base_bar + bar) * 4
        vel = 60 if bar < 12 else 55 - (bar - 12)

        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, max(vel, 40))
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, max(vel - 10, 35))

    # Organ - sustained authority
    for bar in range(0, 16, 4):
        time = (base_bar + bar) * 4
        vel = 55 if bar < 8 else 45

        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 16, vel)

    # Brass - final corporate statement
    time = (base_bar + 12) * 4
    midi.addNote(CH_BRASS, CH_BRASS, E3, time, 2, 70)
    midi.addNote(CH_BRASS, CH_BRASS, B3, time, 2, 65)
    midi.addNote(CH_BRASS, CH_BRASS, E4, time, 2, 60)

    # Final cold chord
    time = (TOTAL_BARS - 4) * 4
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 16, 45)
    midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 16, 40)
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, time, 1, 55)
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, time + 2, 1, 50)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 1, 45)


def main():
    """Generate and save The Corporate State."""
    midi = create_corporate_state()
    save_midi(midi, "07_corporate_state.mid", TEMPO, TOTAL_BARS)
    print()
    print("THE CORPORATE STATE")
    print("Cold. Calculated. Inhuman.")
    print("The marriage of profit and power.")


if __name__ == "__main__":
    main()
