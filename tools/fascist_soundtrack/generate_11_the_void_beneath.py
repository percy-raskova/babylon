#!/usr/bin/env python3
"""
Track 11: "The Void Beneath" (5:00)
Mood: HAUNTING - Ambient, empty, the abyss

What lies under the facade - emptiness, contradiction, doom.
The abyss that the regime constantly runs from.

Musical approach:
- Most ambient/atmospheric track
- Tritone organ drone as foundation
- Whispered strings
- Sparse, haunting harpsichord
- Extended silences - the abyss stares back

Tempo: 66 BPM | Key: Tritone drones
Target duration: 5:00 (~82.5 bars at 66 BPM, using 83 bars)
"""

from . import (
    CH_BRASS,
    CH_HARPSI,
    CH_ORGAN,
    CH_STRINGS,
    CH_TIMPANI,
    E2,
    E3,
    E4,
    E5,
    F5,
    Bb2,
    Bb3,
    Bb4,
    create_midi,
    save_midi,
    setup_standard_tracks,
)

TEMPO = 66
TOTAL_BARS = 83  # ~5:00 at 66 BPM


def create_the_void_beneath():
    """Generate The Void Beneath - the abyss under everything."""
    midi = create_midi(5)
    setup_standard_tracks(midi, TEMPO)

    # === SECTION A: Approaching the Void (bars 1-20) ===
    section_a_approaching(midi)

    # === SECTION B: The Void Opens (bars 21-44) ===
    section_b_opens(midi)

    # === SECTION C: Staring Into It (bars 45-64) ===
    section_c_staring(midi)

    # === SECTION D: The Void Stares Back (bars 65-83) ===
    section_d_stares_back(midi)

    return midi


def section_a_approaching(midi):
    """Approaching the void - descent into emptiness."""

    # Organ - tritone drone emerges from silence
    # Very slow fade-in
    for bar in range(20):
        time = bar * 4
        # Gradual fade in
        vel_e = min(15 + bar * 2, 35)
        vel_bb = min(10 + bar * 2, 30)

        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, vel_e)
        if bar >= 4:
            midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, time, 4, vel_bb)

    # Strings - whispered entries
    # Very sparse, very quiet
    string_whispers = [
        (16, E4, 12, 20),
        (36, Bb4, 16, 18),  # Tritone
        (60, E5, 12, 22),
    ]

    for start_beat, note, dur, vel in string_whispers:
        midi.addNote(CH_STRINGS, CH_STRINGS, note, start_beat, dur, vel)

    # Harpsichord - single notes into the void
    harp_notes = [
        (24, E3, 15),
        (48, Bb3, 12),
    ]

    for start_beat, note, vel in harp_notes:
        midi.addNote(CH_HARPSI, CH_HARPSI, note, start_beat, 8, vel)

    # Timpani - distant thuds
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, 0, 2, 25)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, 32, 2, 22)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, 64, 2, 20)


def section_b_opens(midi):
    """The void opens - maximum emptiness."""

    base_time = 80  # Bar 21

    # Organ - sustained tritone drone (the void's voice)
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, base_time, 96, 38)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, base_time, 96, 33)

    # Higher tritone appears
    midi.addNote(CH_ORGAN, CH_ORGAN, E3, base_time + 32, 64, 28)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb3, base_time + 48, 48, 25)

    # Strings - ghost notes
    # Very quiet, very exposed
    ghost_notes = [
        (8, E5, 20, 22),
        (36, F5, 16, 25),  # Dread note
        (60, E5, 24, 20),
        (88, Bb4, 8, 18),  # Tritone
    ]

    for offset, note, dur, vel in ghost_notes:
        midi.addNote(CH_STRINGS, CH_STRINGS, note, base_time + offset, dur, vel)

    # Low strings - abyss rumble
    midi.addNote(CH_STRINGS, CH_STRINGS, E2, base_time + 24, 72, 25)

    # Harpsichord - questioning the void
    void_questions = [
        (16, E3, 18),
        (40, Bb3, 15),
        (64, E3, 12),
        (80, Bb3, 10),
    ]

    for offset, note, vel in void_questions:
        midi.addNote(CH_HARPSI, CH_HARPSI, note, base_time + offset, 8, vel)

    # Timpani - heartbeat of emptiness
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time + 24, 2, 22)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time + 56, 2, 18)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time + 88, 2, 15)


def section_c_staring(midi):
    """Staring into the void - maximum exposure."""

    base_time = 176  # Bar 45

    # Organ - tritone fully exposed, pulsing slightly
    for bar in range(20):
        time = base_time + bar * 4
        # Slight variation in velocity - breathing
        vel_mod = 2 if bar % 4 < 2 else 0
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 35 + vel_mod)
        midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, time, 4, 30 + vel_mod)

    # Upper tritone
    midi.addNote(CH_ORGAN, CH_ORGAN, E3, base_time, 80, 28)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb3, base_time + 16, 64, 25)

    # Strings - sustained void
    midi.addNote(CH_STRINGS, CH_STRINGS, E5, base_time, 40, 25)
    midi.addNote(CH_STRINGS, CH_STRINGS, Bb4, base_time + 24, 32, 22)
    midi.addNote(CH_STRINGS, CH_STRINGS, E5, base_time + 48, 32, 20)

    # Low string drone
    midi.addNote(CH_STRINGS, CH_STRINGS, E2, base_time, 80, 25)

    # Harpsichord - sparse, haunting
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, base_time + 16, 8, 18)
    midi.addNote(CH_HARPSI, CH_HARPSI, Bb3, base_time + 40, 8, 15)
    midi.addNote(CH_HARPSI, CH_HARPSI, E4, base_time + 64, 8, 18)

    # Timpani - rare, ominous
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time + 8, 2, 20)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time + 48, 2, 18)

    # Brass - single muted note (the void responds)
    midi.addNote(CH_BRASS, CH_BRASS, E3, base_time + 56, 8, 35)
    midi.addNote(CH_BRASS, CH_BRASS, Bb3, base_time + 56, 8, 30)


def section_d_stares_back(midi):
    """The void stares back - Nietzschean horror."""

    base_time = 256  # Bar 65

    # Organ - the void's final statement
    # Extended tritone drone - the void is eternal
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, base_time, 76, 35)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, base_time, 76, 30)

    # Fading upper notes
    midi.addNote(CH_ORGAN, CH_ORGAN, E3, base_time, 48, 25)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb3, base_time + 16, 32, 22)

    # Final organ - very quiet
    midi.addNote(CH_ORGAN, CH_ORGAN, E3, base_time + 56, 20, 18)

    # Strings - withdrawing into nothing
    midi.addNote(CH_STRINGS, CH_STRINGS, E5, base_time, 24, 22)
    midi.addNote(CH_STRINGS, CH_STRINGS, E4, base_time + 32, 20, 18)
    midi.addNote(CH_STRINGS, CH_STRINGS, E3, base_time + 56, 16, 15)

    # Low strings final
    midi.addNote(CH_STRINGS, CH_STRINGS, E2, base_time, 72, 22)

    # Harpsichord - final question into the void
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, base_time + 8, 4, 15)
    midi.addNote(CH_HARPSI, CH_HARPSI, Bb3, base_time + 24, 4, 12)
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, base_time + 48, 8, 10)  # Fading

    # Timpani - final heartbeat
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time, 2, 18)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time + 36, 2, 15)
    # No more - silence

    # Extended silence at the end
    # The void remains

    # Final tritone - barely audible
    final_time = base_time + 64
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, final_time, 12, 15)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, final_time, 12, 12)


def main():
    """Generate and save The Void Beneath."""
    midi = create_the_void_beneath()
    save_midi(midi, "11_the_void_beneath.mid", TEMPO, TOTAL_BARS)
    print()
    print("THE VOID BENEATH")
    print("The abyss beneath the facade.")
    print("It stares back.")


if __name__ == "__main__":
    main()
