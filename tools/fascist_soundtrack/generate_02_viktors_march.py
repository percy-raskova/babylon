#!/usr/bin/env python3
"""
Track 02: "Viktor's March" (4:30)
Mood: MENACING - Militaristic, imposing, the strongman

Viktor Thule's theme - the leader of the National Revival Movement.
Military precision, jackboot rhythm, brass fanfares of state power.

Musical approach:
- Martial timpani rhythm (the jackboot march)
- Brass fanfares (state power on display)
- Organ providing dark majesty
- Snare drum patterns (military discipline)
- Minor key but with sense of power

Tempo: 100 BPM | Key: E minor/Phrygian
Target duration: 4:30 (~113 bars at 100 BPM)
"""

from . import (
    A4,
    B2,
    B3,
    B4,
    CH_BRASS,
    CH_DRUMS,
    CH_HARPSI,
    CH_ORGAN,
    CH_STRINGS,
    CH_TIMPANI,
    DRUM_BASS,
    DRUM_SNARE,
    E2,
    E3,
    E4,
    E5,
    F3,
    G3,
    G4,
    PROG_FRENCH_HORN,
    create_midi,
    save_midi,
    setup_standard_tracks,
)

TEMPO = 100
TOTAL_BARS = 113  # ~4:30 at 100 BPM


def create_viktors_march():
    """Generate Viktor's March - the strongman's theme."""
    midi = create_midi(7)  # Extra tracks for drums and horns
    setup_standard_tracks(midi, TEMPO)

    # Additional track setup for French horn
    midi.addTrackName(5, 0, "French Horn - Military Authority")
    midi.addProgramChange(5, 5, 0, PROG_FRENCH_HORN)

    # === SECTION A: The Approach (bars 1-28) ===
    section_a_approach(midi)

    # === SECTION B: The Leader Arrives (bars 29-56) ===
    section_b_arrival(midi)

    # === SECTION C: Display of Power (bars 57-84) ===
    section_c_power(midi)

    # === SECTION D: The March Continues (bars 85-113) ===
    section_d_continues(midi)

    return midi


def section_a_approach(midi):
    """Distant drums, the march approaches."""

    # Timpani march - starts quiet, builds
    for bar in range(28):
        time = bar * 4
        vel_base = min(45 + bar * 2, 80)

        # Basic march pattern: BOOM - - boom BOOM - boom -
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, vel_base)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 1.5, 0.25, vel_base - 20)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, vel_base - 5)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3, 0.25, vel_base - 15)

    # Snare enters at bar 8
    for bar in range(8, 28):
        time = bar * 4
        vel = min(50 + (bar - 8) * 2, 75)

        # Military snare pattern
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 1, 0.25, vel)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 1.5, 0.25, vel - 10)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 3, 0.25, vel)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 3.5, 0.25, vel - 10)

        # Extra snare rolls on every 4th bar
        if bar % 4 == 3:
            for i in range(4):
                midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 3.5 + i * 0.125, 0.1, vel - 5)

    # Low strings - ominous anticipation
    for bar in range(0, 28, 4):
        time = bar * 4
        vel = 40 + bar
        midi.addNote(CH_STRINGS, CH_STRINGS, E2, time, 16, min(vel, 60))

    # Organ enters at bar 16 - building majesty
    for bar in range(16, 28):
        time = bar * 4
        vel = 35 + (bar - 16) * 3
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, vel)
        if bar >= 20:
            midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, vel - 10)

    # Brass fanfare preview at bar 24
    time = 24 * 4
    fanfare = [(0, E3, 2), (2, B3, 1.5), (3.5, E4, 0.5)]
    for offset, note, dur in fanfare:
        midi.addNote(CH_BRASS, CH_BRASS, note, time + offset, dur, 75)


def section_b_arrival(midi):
    """The leader arrives - full military display."""

    base_bar = 28

    # Full timpani march
    for bar in range(28):
        time = (base_bar + bar) * 4

        # Accented march pattern
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, 90)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, B2, time + 1, 0.25, 60)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 1.5, 0.25, 65)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, 85)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, B2, time + 3, 0.25, 60)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3.5, 0.25, 55)

    # Snare - crisp military patterns
    for bar in range(28):
        time = (base_bar + bar) * 4

        # Main pattern
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 1, 0.25, 80)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 1.5, 0.25, 70)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 3, 0.25, 80)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 3.5, 0.25, 70)

        # Accent every 4 bars
        if bar % 4 == 3:
            midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_BASS, time + 4 - 0.5, 0.5, 85)

    # Organ - dark majesty
    for bar in range(28):
        time = (base_bar + bar) * 4
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 55)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, 45)
        if bar % 4 < 2:
            midi.addNote(CH_ORGAN, CH_ORGAN, E3, time, 4, 40)

    # Brass fanfares - Viktor's theme
    # Main theme: E - G - B - E (rising power)
    theme_bars = [0, 8, 16, 24]
    for bar in theme_bars:
        time = (base_bar + bar) * 4

        # Fanfare
        midi.addNote(CH_BRASS, CH_BRASS, E3, time, 1, 90)
        midi.addNote(CH_BRASS, CH_BRASS, B3, time, 1, 85)
        midi.addNote(CH_BRASS, CH_BRASS, G4, time + 1.5, 1, 95)
        midi.addNote(CH_BRASS, CH_BRASS, B4, time + 1.5, 1, 90)
        midi.addNote(CH_BRASS, CH_BRASS, E4, time + 3, 1, 100)
        midi.addNote(CH_BRASS, CH_BRASS, E5, time + 3, 1, 95)

    # French horn - authority countermelody (channel 5)
    for bar in range(0, 28, 2):
        time = (base_bar + bar) * 4
        # Simple authoritative line
        midi.addNote(5, 5, E3, time, 2, 70)
        midi.addNote(5, 5, B3, time + 2, 2, 65)

    # Strings - supporting harmony
    for bar in range(0, 28, 4):
        time = (base_bar + bar) * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 8, 55)
        midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 8, 50)
        midi.addNote(CH_STRINGS, CH_STRINGS, G4, time + 8, 8, 55)


def section_c_power(midi):
    """Display of power - the regime at its most imposing."""

    base_bar = 56

    # Timpani - aggressive, powerful
    for bar in range(28):
        time = (base_bar + bar) * 4

        # Heavy march with added weight
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, 95)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 0.5, 0.25, 70)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, B2, time + 1, 0.25, 75)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 1.5, 0.25, 70)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, 90)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, B2, time + 2.75, 0.25, 65)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3, 0.25, 75)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3.5, 0.25, 65)

    # Snare - more aggressive
    for bar in range(28):
        time = (base_bar + bar) * 4

        # Busier pattern
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 0.5, 0.25, 75)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 1, 0.25, 85)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 1.5, 0.25, 75)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 2.5, 0.25, 75)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 3, 0.25, 85)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 3.5, 0.25, 75)

    # Organ - full power
    for bar in range(28):
        time = (base_bar + bar) * 4
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 65)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, 55)
        midi.addNote(CH_ORGAN, CH_ORGAN, E3, time, 4, 50)

    # Brass - dominant, powerful phrases
    brass_phrases = [
        # Bar, notes with timing
        (0, [(0, E3, 1.5), (0, B3, 1.5), (2, G3, 1), (2, E4, 1), (3, B3, 1), (3, G4, 1)]),
        (4, [(0, E4, 2), (0, B4, 2), (2, E4, 1), (3, G4, 1)]),
        (8, [(0, E3, 1), (1, G3, 1), (2, B3, 1), (3, E4, 1)]),  # Rising power
        (12, [(0, E4, 2), (0, B4, 2), (2, A4, 1), (3, G4, 1)]),
        (16, [(0, E3, 1.5), (0, B3, 1.5), (2, G3, 1), (2, E4, 1), (3, B3, 1), (3, G4, 1)]),
        (20, [(0, E4, 3), (0, B4, 3), (3, E4, 1)]),  # Held power chord
        (24, [(0, E3, 1), (1, F3, 1), (2, G3, 1), (3, E4, 1)]),  # With dread note
    ]

    for bar_offset, notes in brass_phrases:
        time = (base_bar + bar_offset) * 4
        for offset, note, dur in notes:
            midi.addNote(CH_BRASS, CH_BRASS, note, time + offset, dur, 95)

    # French horn - sustained authority
    for bar in range(0, 28, 4):
        time = (base_bar + bar) * 4
        midi.addNote(5, 5, E3, time, 8, 70)
        midi.addNote(5, 5, B3, time, 8, 65)

    # Strings - swelling power
    for bar in range(28):
        time = (base_bar + bar) * 4
        vel = 55 + (bar % 8) * 3
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 4, min(vel, 70))
        midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 4, min(vel - 10, 60))

    # Harpsichord - mechanical underpinning
    for bar in range(28):
        time = (base_bar + bar) * 4
        figure = [E3, B3, E4, B3]
        for i, note in enumerate(figure):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i, 0.75, 60)


def section_d_continues(midi):
    """The march continues - Viktor is eternal."""

    base_bar = 84

    # Timpani - steady, eternal
    for bar in range(29):
        time = (base_bar + bar) * 4
        vel = 85 if bar < 24 else 80 - (bar - 24) * 2  # Slight fade

        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, vel)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 1.5, 0.25, vel - 20)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, vel - 5)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3.5, 0.25, vel - 15)

    # Snare - continuing
    for bar in range(29):
        time = (base_bar + bar) * 4
        vel = 75 if bar < 24 else 70 - (bar - 24)

        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 1, 0.25, vel)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 1.5, 0.25, vel - 10)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 3, 0.25, vel)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 3.5, 0.25, vel - 10)

    # Organ - sustained
    for bar in range(29):
        time = (base_bar + bar) * 4
        vel = 55 if bar < 24 else 50 - (bar - 24)
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, vel)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, vel - 10)

    # Brass - occasional statements
    brass_bars = [0, 8, 16, 24]
    for bar in brass_bars:
        if base_bar + bar < 113:
            time = (base_bar + bar) * 4
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 1.5, 85)
            midi.addNote(CH_BRASS, CH_BRASS, B3, time, 1.5, 80)
            midi.addNote(CH_BRASS, CH_BRASS, E4, time + 2, 1.5, 90)

    # Final fanfare at bar 108
    time = 108 * 4
    midi.addNote(CH_BRASS, CH_BRASS, E3, time, 2, 95)
    midi.addNote(CH_BRASS, CH_BRASS, B3, time, 2, 90)
    midi.addNote(CH_BRASS, CH_BRASS, E4, time, 2, 100)
    midi.addNote(CH_BRASS, CH_BRASS, G4, time + 2, 2, 95)
    midi.addNote(CH_BRASS, CH_BRASS, B4, time + 2, 2, 90)

    # Strings - fading
    for bar in range(0, 29, 4):
        time = (base_bar + bar) * 4
        vel = 55 if bar < 20 else 45
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 16, vel)
        midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 16, vel - 10)

    # French horn - final statement
    time = 108 * 4
    midi.addNote(5, 5, E3, time, 4, 70)
    midi.addNote(5, 5, B3, time, 4, 65)


def main():
    """Generate and save Viktor's March."""
    midi = create_viktors_march()
    save_midi(midi, "02_viktors_march.mid", TEMPO, TOTAL_BARS)
    print()
    print("VIKTOR'S MARCH")
    print("The strongman approaches.")
    print("The jackboot rhythm never falters.")


if __name__ == "__main__":
    main()
