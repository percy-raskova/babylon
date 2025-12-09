#!/usr/bin/env python3
"""
Track 08: "Propaganda Broadcast" (7:00)
Mood: SEDUCTIVE/ANXIOUS - The beautiful lie

Ideological mystification - what they tell the masses vs. reality.
Seductive and beautiful on the surface, disturbing underneath.

Musical approach:
- Organ-heavy (false grandeur at its peak)
- Moments of almost-beauty, immediately undercut
- Harpsichord "signal" patterns (broadcasting)
- Underlying anxiety breaking through the veneer
- Major/Phrygian modal mixture - hope vs dread

Tempo: 100 BPM | Key: Modal mixture (major/Phrygian)
Target duration: 7:00 (~175 bars at 100 BPM)
"""

from . import (
    A3,
    A4,
    B2,
    B3,
    B4,
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
    F4,
    F5,
    G3,
    G4,
    Bb3,
    Fs4,
    create_midi,
    save_midi,
    setup_standard_tracks,
)

TEMPO = 100
TOTAL_BARS = 175  # ~7:00 at 100 BPM


def create_propaganda_broadcast():
    """Generate Propaganda Broadcast - the beautiful lie."""
    midi = create_midi(5)
    setup_standard_tracks(midi, TEMPO)

    # === SECTION A: The Signal (bars 1-32) ===
    section_a_signal(midi)

    # === SECTION B: The Beautiful Lie (bars 33-80) ===
    section_b_beautiful(midi)

    # === SECTION C: Cracks Appear (bars 81-128) ===
    section_c_cracks(midi)

    # === SECTION D: The Broadcast Continues (bars 129-175) ===
    section_d_continues(midi)

    return midi


def section_a_signal(midi):
    """The signal begins - broadcasting starts."""

    # Harpsichord - broadcast signal pattern
    for bar in range(32):
        time = bar * 4
        vel = min(45 + bar, 70)

        # Signal pattern - like morse code
        if bar % 4 == 0:
            signal = [E4, E4, E4]  # Short-short-short
            for i, note in enumerate(signal):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.3, 0.2, vel)
            midi.addNote(CH_HARPSI, CH_HARPSI, E4, time + 1, 0.8, vel)  # Long
        elif bar % 4 == 2:
            signal = [E5, E5]
            for i, note in enumerate(signal):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.3, 0.2, vel - 5)
            midi.addNote(CH_HARPSI, CH_HARPSI, E5, time + 0.8, 0.6, vel - 5)

        # Underlying pattern
        if bar >= 8:
            underlying = [E3, G3, E3, G3]
            for i, note in enumerate(underlying):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i, 0.75, vel - 15)

    # Organ - warming up
    for bar in range(16, 32):
        time = bar * 4
        vel = 35 + (bar - 16)

        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, vel)
        if bar >= 24:
            midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, vel - 10)

    # Strings - gentle entrance
    for bar in range(24, 32):
        time = bar * 4
        vel = 40 + (bar - 24) * 2

        # Beautiful, hopeful - the seduction begins
        midi.addNote(CH_STRINGS, CH_STRINGS, E4, time, 4, vel)
        midi.addNote(CH_STRINGS, CH_STRINGS, G4, time, 4, vel - 5)

    # Timpani - subtle heartbeat
    for bar in range(20, 32):
        time = bar * 4
        vel = 35 + (bar - 20)

        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, vel)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, vel - 10)


def section_b_beautiful(midi):
    """The beautiful lie - seductive propaganda."""

    base_bar = 32

    # Organ - full false grandeur
    for bar in range(48):
        time = (base_bar + bar) * 4

        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 60)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, 50)
        midi.addNote(CH_ORGAN, CH_ORGAN, E3, time, 4, 45)

        # Modal mixture - sometimes major (hope), sometimes Phrygian (dread)
        if bar % 16 < 8:
            # E major feel - hopeful propaganda
            midi.addNote(CH_ORGAN, CH_ORGAN, 56, time, 4, 40)  # G#3
        else:
            # E Phrygian - dread underneath
            midi.addNote(CH_ORGAN, CH_ORGAN, G3, time, 4, 40)

    # Strings - beautiful melodies
    melody = [
        # Beautiful, seductive melody
        (0, [(E4, 2), (Fs4, 2), (G4, 4)], 65),  # Major feel
        (8, [(G4, 2), (A4, 2), (B4, 4)], 68),
        (16, [(B4, 4), (A4, 4)], 70),
        (24, [(G4, 2), (F4, 2), (E4, 4)], 65),  # F natural - dread
        (32, [(E4, 2), (Fs4, 2), (G4, 4)], 68),  # Back to major
        (40, [(A4, 4), (B4, 4)], 70),
    ]

    for bar_offset, notes, vel in melody:
        time = (base_bar + bar_offset) * 4
        current_time = time
        for note, dur in notes:
            midi.addNote(CH_STRINGS, CH_STRINGS, note, current_time, dur * 4, vel)
            current_time += dur * 4

    # Lower strings
    for bar in range(48):
        time = (base_bar + bar) * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 4, 55)

    # Harpsichord - continuing broadcast signal underneath
    for bar in range(48):
        time = (base_bar + bar) * 4

        # Quieter signal pattern
        if bar % 8 == 0:
            signal = [E5, E5, E5]
            for i, note in enumerate(signal):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.25, 0.2, 50)

        # Harmonic support
        pattern = [E3, B3, E3, B3]
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i, 0.75, 55)

    # Brass - noble fanfares (the lie sounds heroic)
    fanfare_bars = [8, 24, 40]
    for bar in fanfare_bars:
        time = (base_bar + bar) * 4

        midi.addNote(CH_BRASS, CH_BRASS, E3, time, 2, 75)
        midi.addNote(CH_BRASS, CH_BRASS, G3, time, 2, 70)  # Major
        midi.addNote(CH_BRASS, CH_BRASS, B3, time, 2, 65)
        midi.addNote(CH_BRASS, CH_BRASS, E4, time + 2, 2, 80)

    # Timpani - steady, reassuring
    for bar in range(48):
        time = (base_bar + bar) * 4

        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, 60)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, 55)


def section_c_cracks(midi):
    """Cracks appear - the lie starts to show through."""

    base_bar = 80

    # Organ - still majestic but darker
    for bar in range(48):
        time = (base_bar + bar) * 4

        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 55)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, 45)

        # More Phrygian, less major
        if bar % 8 < 2:
            midi.addNote(CH_ORGAN, CH_ORGAN, 56, time, 4, 40)  # G# - hope
        else:
            midi.addNote(CH_ORGAN, CH_ORGAN, G3, time, 4, 40)  # G natural
            if bar % 8 >= 6:
                midi.addNote(CH_ORGAN, CH_ORGAN, F3, time, 4, 35)  # Dread note

    # Strings - melody becomes anxious
    for bar in range(48):
        time = (base_bar + bar) * 4

        if bar % 4 < 2:
            # Still beautiful
            midi.addNote(CH_STRINGS, CH_STRINGS, E4, time, 4, 65)
            midi.addNote(CH_STRINGS, CH_STRINGS, G4, time, 4, 60)
        else:
            # Anxious tremolo
            midi.addNote(CH_STRINGS, CH_STRINGS, E5, time, 4, 60)
            midi.addNote(CH_STRINGS, CH_STRINGS, F5, time + 2, 2, 58)  # Dread

        # Low strings grow ominous
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 4, 55)
        if bar >= 24:
            midi.addNote(CH_STRINGS, CH_STRINGS, Bb3, time, 4, 45)  # Tritone

    # Harpsichord - signal becomes erratic
    for bar in range(48):
        time = (base_bar + bar) * 4

        # Signal pattern with glitches
        if bar % 4 == 0:
            signal = [E4, E4, F4]  # Wrong note in signal
            for i, note in enumerate(signal):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.3, 0.2, 65)

        # Mechanical pattern
        if bar % 2 == 0:
            pattern = [E3, F3, E3, G3, E3, F3, E3, A3]
        else:
            pattern = [E3, F3, E3, G3, E3, Bb3, E3, A3]  # Tritone intrusion
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, 62)

    # Brass - becoming forced
    for bar in range(48):
        time = (base_bar + bar) * 4

        if bar % 8 == 0:
            # Still trying to be noble
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 1.5, 75)
            midi.addNote(CH_BRASS, CH_BRASS, B3, time, 1.5, 70)
            midi.addNote(CH_BRASS, CH_BRASS, E4, time + 2, 1.5, 75)

        if bar % 8 == 4:
            # Wrong notes creeping in
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 1, 70)
            midi.addNote(CH_BRASS, CH_BRASS, Bb3, time, 1, 65)  # Tritone

    # Timpani - clock becoming insistent
    for bar in range(48):
        time = (base_bar + bar) * 4

        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, 70)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 1, 0.25, 50)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, 65)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3, 0.25, 50)


def section_d_continues(midi):
    """The broadcast continues - the lie must not stop."""

    base_bar = 128

    # Organ - still broadcasting false hope
    for bar in range(47):
        time = (base_bar + bar) * 4
        vel = 55 if bar < 32 else 50 - (bar - 32) // 2

        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, max(vel, 40))
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, max(vel - 10, 35))

        # Mix of major and minor
        if bar % 4 < 2:
            midi.addNote(CH_ORGAN, CH_ORGAN, 56, time, 4, max(vel - 15, 30))  # G#
        else:
            midi.addNote(CH_ORGAN, CH_ORGAN, G3, time, 4, max(vel - 15, 30))

    # Strings - continued seduction with anxiety
    for bar in range(47):
        time = (base_bar + bar) * 4
        vel = 60 if bar < 32 else 55 - (bar - 32)

        if bar % 4 < 2:
            midi.addNote(CH_STRINGS, CH_STRINGS, E4, time, 4, max(vel, 40))
            midi.addNote(CH_STRINGS, CH_STRINGS, G4, time, 4, max(vel - 5, 35))
        else:
            midi.addNote(CH_STRINGS, CH_STRINGS, E5, time, 4, max(vel - 5, 35))

        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 4, max(vel - 10, 35))

    # Harpsichord - signal continues
    for bar in range(47):
        time = (base_bar + bar) * 4
        vel = 60 if bar < 32 else 55 - (bar - 32) // 2

        # Signal pattern
        if bar % 8 == 0:
            signal = [E5, E5, E5]
            for i, note in enumerate(signal):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.25, 0.2, max(vel, 45))

        # Mechanical pattern
        pattern = [E3, G3, E3, B3]
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i, 0.75, max(vel - 10, 40))

    # Brass - occasional reminder
    reminder_bars = [0, 16, 32]
    for bar in reminder_bars:
        time = (base_bar + bar) * 4
        vel = 70 if bar < 24 else 60

        midi.addNote(CH_BRASS, CH_BRASS, E3, time, 1.5, vel)
        midi.addNote(CH_BRASS, CH_BRASS, B3, time, 1.5, vel - 5)

    # Timpani - steady to the end
    for bar in range(47):
        time = (base_bar + bar) * 4
        vel = 60 if bar < 32 else 55 - (bar - 32)

        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, max(vel, 40))
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, max(vel - 10, 35))

    # Final broadcast signal
    time = (TOTAL_BARS - 4) * 4
    midi.addNote(CH_HARPSI, CH_HARPSI, E5, time, 0.2, 55)
    midi.addNote(CH_HARPSI, CH_HARPSI, E5, time + 0.3, 0.2, 55)
    midi.addNote(CH_HARPSI, CH_HARPSI, E5, time + 0.6, 0.8, 55)
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 16, 45)
    midi.addNote(CH_STRINGS, CH_STRINGS, E4, time, 16, 40)


def main():
    """Generate and save Propaganda Broadcast."""
    midi = create_propaganda_broadcast()
    save_midi(midi, "08_propaganda_broadcast.mid", TEMPO, TOTAL_BARS)
    print()
    print("PROPAGANDA BROADCAST")
    print("The beautiful lie.")
    print("The signal must not stop.")


if __name__ == "__main__":
    main()
