#!/usr/bin/env python3
"""
Track 05: "National Revival" (6:00)
Mood: FALSE TRIUMPH - Triumphant on surface, hollow underneath

The faction's public anthem - the lie they tell themselves.
Almost beautiful, almost heroic, but something is deeply wrong.

Musical approach:
- Most "anthem-like" - organ majesty, brass fanfares
- Almost beautiful, almost heroic
- Underlying timpani clock (can't escape the machine)
- Subtle wrongness that grows with each listen
- E minor that wants to be major but can't quite get there

Tempo: 104 BPM | Key: E minor (almost major, never quite)
Target duration: 6:00 (~156 bars at 104 BPM)
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
    F4,
    G3,
    G4,
    PROG_FRENCH_HORN,
    Bb2,
    Bb3,
    Fs4,
    create_midi,
    save_midi,
    setup_standard_tracks,
)

TEMPO = 104
TOTAL_BARS = 156  # ~6:00 at 104 BPM


def create_national_revival():
    """Generate National Revival - the hollow anthem."""
    midi = create_midi(7)
    setup_standard_tracks(midi, TEMPO)

    # French horn for anthem quality
    midi.addTrackName(5, 0, "French Horn - National Pride")
    midi.addProgramChange(5, 5, 0, PROG_FRENCH_HORN)

    # === SECTION A: Dawn of Revival (bars 1-36) ===
    section_a_dawn(midi)

    # === SECTION B: The Anthem (bars 37-84) ===
    section_b_anthem(midi)

    # === SECTION C: False Glory (bars 85-120) ===
    section_c_glory(midi)

    # === SECTION D: The Hollow Core (bars 121-156) ===
    section_d_hollow(midi)

    return midi


def section_a_dawn(midi):
    """Dawn of revival - hopeful beginning, but with undercurrents."""

    # Organ - majestic opening
    for bar in range(36):
        time = bar * 4
        vel = min(35 + bar, 60)

        # Building majesty
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, vel)
        if bar >= 8:
            midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, vel - 10)
        if bar >= 16:
            midi.addNote(CH_ORGAN, CH_ORGAN, E3, time, 4, vel - 15)

    # Strings - sweeping, hopeful
    string_melody = [
        # Bar, notes (note, duration pairs), base velocity
        (4, [(E4, 4), (G4, 4)], 50),
        (8, [(B4, 4), (A4, 4)], 55),
        (12, [(G4, 4), (Fs4, 4)], 55),  # F# for major feel
        (16, [(E4, 8)], 60),
        (20, [(E4, 2), (G4, 2), (B4, 4)], 60),
        (24, [(B4, 4), (A4, 4)], 65),
        (28, [(G4, 4), (F4, 4)], 62),  # F natural - dread creeps in
        (32, [(E4, 4)], 60),
    ]

    for bar, notes, base_vel in string_melody:
        time = bar * 4
        current_time = time
        for note, dur in notes:
            midi.addNote(CH_STRINGS, CH_STRINGS, note, current_time, dur * 4, base_vel)
            current_time += dur

    # Low strings foundation
    for bar in range(0, 36, 4):
        time = bar * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 16, 50)

    # Timpani - subtle heartbeat (the machine is always there)
    for bar in range(16, 36):
        time = bar * 4
        vel = 40 + (bar - 16)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 1, vel)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, vel - 10)

    # Brass enters bar 24 - fanfare preview
    time = 24 * 4
    midi.addNote(CH_BRASS, CH_BRASS, E3, time, 2, 65)
    midi.addNote(CH_BRASS, CH_BRASS, B3, time, 2, 60)
    midi.addNote(CH_BRASS, CH_BRASS, E4, time + 2, 2, 70)

    time = 32 * 4
    midi.addNote(CH_BRASS, CH_BRASS, E3, time, 2, 70)
    midi.addNote(CH_BRASS, CH_BRASS, G3, time, 2, 65)
    midi.addNote(CH_BRASS, CH_BRASS, B3, time, 2, 60)
    midi.addNote(CH_BRASS, CH_BRASS, E4, time + 2, 2, 75)


def section_b_anthem(midi):
    """The anthem proper - triumphant but with wrongness."""

    base_bar = 36

    # Organ - full majesty
    for bar in range(48):
        time = (base_bar + bar) * 4
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 65)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, 55)
        midi.addNote(CH_ORGAN, CH_ORGAN, E3, time, 4, 50)

        # Occasional attempt at major (G#) that falls back
        if bar % 16 >= 8 and bar % 16 < 12:
            midi.addNote(CH_ORGAN, CH_ORGAN, 56, time, 4, 45)  # G#3 - trying for major
        elif bar % 16 >= 12:
            midi.addNote(CH_ORGAN, CH_ORGAN, G3, time, 4, 45)  # Falls back to minor

    # Brass fanfares - the anthem theme
    # E - G - B - E (rising national pride)
    theme_entries = [0, 16, 32]
    for entry in theme_entries:
        time = (base_bar + entry) * 4

        # Main theme
        midi.addNote(CH_BRASS, CH_BRASS, E3, time, 2, 85)
        midi.addNote(CH_BRASS, CH_BRASS, E4, time, 2, 80)

        midi.addNote(CH_BRASS, CH_BRASS, G3, time + 2, 2, 85)
        midi.addNote(CH_BRASS, CH_BRASS, G4, time + 2, 2, 80)

        midi.addNote(CH_BRASS, CH_BRASS, B3, time + 4, 2, 90)
        midi.addNote(CH_BRASS, CH_BRASS, B4, time + 4, 2, 85)

        midi.addNote(CH_BRASS, CH_BRASS, E4, time + 6, 2, 95)
        midi.addNote(CH_BRASS, CH_BRASS, E5, time + 6, 2, 90)

    # Counter-theme with wrongness
    counter_entries = [8, 24, 40]
    for entry in counter_entries:
        time = (base_bar + entry) * 4

        midi.addNote(CH_BRASS, CH_BRASS, E3, time, 2, 80)
        midi.addNote(CH_BRASS, CH_BRASS, G3, time + 2, 2, 80)
        midi.addNote(CH_BRASS, CH_BRASS, B3, time + 4, 1.5, 85)
        midi.addNote(CH_BRASS, CH_BRASS, Bb3, time + 5.5, 0.5, 75)  # Wrong note
        midi.addNote(CH_BRASS, CH_BRASS, E4, time + 6, 2, 85)

    # French horn - national pride melody (channel 5)
    horn_melody = [
        (0, E3, 4),
        (4, G3, 4),
        (8, B3, 4),
        (12, A3, 4),
        (16, G3, 4),
        (20, E3, 4),
        (24, B3, 4),
        (28, E4, 4),
        (32, E3, 4),
        (36, G3, 4),
        (40, B3, 4),
        (44, A3, 4),
    ]
    for bar, note, dur in horn_melody:
        time = (base_bar + bar) * 4
        midi.addNote(5, 5, note, time, dur * 4, 70)

    # Strings - sweeping support
    for bar in range(48):
        time = (base_bar + bar) * 4

        if bar % 8 < 4:
            midi.addNote(CH_STRINGS, CH_STRINGS, E4, time, 4, 65)
            midi.addNote(CH_STRINGS, CH_STRINGS, B4, time, 4, 60)
        else:
            midi.addNote(CH_STRINGS, CH_STRINGS, G4, time, 4, 65)
            midi.addNote(CH_STRINGS, CH_STRINGS, E5, time, 4, 60)

    # Low strings
    for bar in range(0, 48, 4):
        time = (base_bar + bar) * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 16, 55)

    # Timpani - the clock beneath the glory
    for bar in range(48):
        time = (base_bar + bar) * 4
        # Slightly irregular - something is off
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, 70)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, 65)
        if bar % 4 == 3:
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3.5, 0.25, 55)  # Off-beat


def section_c_glory(midi):
    """False glory - maximum triumphalism, maximum wrongness."""

    base_bar = 84

    # Organ - overwhelming majesty
    for bar in range(36):
        time = (base_bar + bar) * 4
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 75)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, 65)
        midi.addNote(CH_ORGAN, CH_ORGAN, E3, time, 4, 60)
        midi.addNote(CH_ORGAN, CH_ORGAN, B3, time, 4, 55)

    # Brass - triumphant fanfares
    for bar in range(36):
        time = (base_bar + bar) * 4

        if bar % 8 == 0:
            # Grand fanfare
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 3, 100)
            midi.addNote(CH_BRASS, CH_BRASS, G3, time, 3, 95)
            midi.addNote(CH_BRASS, CH_BRASS, B3, time, 3, 90)
            midi.addNote(CH_BRASS, CH_BRASS, E4, time, 3, 95)

            midi.addNote(CH_BRASS, CH_BRASS, E4, time + 4, 3, 100)
            midi.addNote(CH_BRASS, CH_BRASS, G4, time + 4, 3, 95)
            midi.addNote(CH_BRASS, CH_BRASS, B4, time + 4, 3, 90)

        elif bar % 8 == 4:
            # Sustain with wrongness
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 2, 90)
            midi.addNote(CH_BRASS, CH_BRASS, G3, time, 2, 85)
            midi.addNote(CH_BRASS, CH_BRASS, Bb3, time + 2, 2, 80)  # Wrong!
            midi.addNote(CH_BRASS, CH_BRASS, E4, time + 2, 2, 85)

    # French horn - soaring but flawed
    for bar in range(0, 36, 4):
        time = (base_bar + bar) * 4
        midi.addNote(5, 5, E4, time, 8, 80)
        midi.addNote(5, 5, G4, time + 8, 8, 75)

    # Strings - maximum sweep
    for bar in range(36):
        time = (base_bar + bar) * 4

        # Tremolo effect through repeated notes
        midi.addNote(CH_STRINGS, CH_STRINGS, E4, time, 4, 75)
        midi.addNote(CH_STRINGS, CH_STRINGS, G4, time, 4, 70)
        midi.addNote(CH_STRINGS, CH_STRINGS, B4, time, 4, 70)

        if bar % 4 == 2:
            # Add high strings
            midi.addNote(CH_STRINGS, CH_STRINGS, E5, time, 4, 70)

    # Harpsichord - mechanical undercurrent appears
    for bar in range(18, 36):
        time = (base_bar + bar) * 4
        vel = 50 + (bar - 18)
        pattern = [E3, G3, B3, E4, B3, G3]
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, min(vel, 65))

    # Timpani - becoming more insistent
    for bar in range(36):
        time = (base_bar + bar) * 4
        vel = 75 + bar // 4

        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, min(vel, 90))
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 1, 0.25, min(vel - 20, 70))
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, min(vel - 5, 85))
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3, 0.25, min(vel - 15, 75))


def section_d_hollow(midi):
    """The hollow core - the falseness revealed."""

    base_bar = 120

    # Organ - still majestic but hollow
    for bar in range(36):
        time = (base_bar + bar) * 4
        vel = 65 - bar // 2

        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, max(vel, 40))
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, max(vel - 10, 35))

        # Tritone creeps in
        if bar >= 20:
            midi.addNote(CH_ORGAN, CH_ORGAN, Bb3, time, 4, max(vel - 20, 30))

    # Brass - fading glory
    fade_fanfares = [0, 12, 24]
    for entry in fade_fanfares:
        if base_bar + entry < TOTAL_BARS - 4:
            time = (base_bar + entry) * 4
            vel = 80 - entry

            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 2, max(vel, 55))
            midi.addNote(CH_BRASS, CH_BRASS, B3, time, 2, max(vel - 5, 50))
            midi.addNote(CH_BRASS, CH_BRASS, E4, time + 2, 2, max(vel, 55))

    # Final brass - hollow
    time = (TOTAL_BARS - 8) * 4
    midi.addNote(CH_BRASS, CH_BRASS, E3, time, 4, 55)
    midi.addNote(CH_BRASS, CH_BRASS, Bb3, time, 4, 50)  # Tritone exposed
    midi.addNote(CH_BRASS, CH_BRASS, E4, time, 4, 50)

    # French horn - fading pride
    for bar in range(0, 24, 8):
        time = (base_bar + bar) * 4
        vel = 65 - bar
        midi.addNote(5, 5, E3, time, 16, max(vel, 40))

    # Strings - becoming thin
    for bar in range(36):
        time = (base_bar + bar) * 4
        vel = 60 - bar

        if bar < 24:
            midi.addNote(CH_STRINGS, CH_STRINGS, E4, time, 4, max(vel, 35))
            midi.addNote(CH_STRINGS, CH_STRINGS, B4, time, 4, max(vel - 10, 30))
        else:
            midi.addNote(CH_STRINGS, CH_STRINGS, E4, time, 4, max(vel - 10, 25))

    # Harpsichord - the machine continues
    for bar in range(36):
        time = (base_bar + bar) * 4
        vel = 55 if bar < 24 else 45

        pattern = [E3, G3, B3, E4]
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i, 0.75, vel)

    # Timpani - mechanical, eternal
    for bar in range(36):
        time = (base_bar + bar) * 4

        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, 65)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, 60)

    # Final hollow chord - the revival is a lie
    time = (TOTAL_BARS - 4) * 4
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 16, 40)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, time, 16, 35)  # Tritone
    midi.addNote(CH_ORGAN, CH_ORGAN, E3, time, 16, 35)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 2, 50)


def main():
    """Generate and save National Revival."""
    midi = create_national_revival()
    save_midi(midi, "05_national_revival.mid", TEMPO, TOTAL_BARS)
    print()
    print("NATIONAL REVIVAL")
    print("The anthem of hollow triumph.")
    print("Almost beautiful. Almost heroic. Almost.")


if __name__ == "__main__":
    main()
