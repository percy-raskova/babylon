#!/usr/bin/env python3
"""
Track 10: "The Mirror" (4:30)
Mood: DREAD - Introspective, disturbing, existential dread

The regime looking at what it has become - self-awareness.
The most "quiet" track but the most disturbing.

Musical approach:
- Sparse texture exposing the void
- Tritone drone (the "devil's interval")
- Trembling strings
- Slow timpani heartbeat
- Long silences that make you uncomfortable

Tempo: 72 BPM | Key: Tritone drones
Target duration: 4:30 (~81 bars at 72 BPM)
"""

from . import (
    A3,
    B3,
    CH_BRASS,
    CH_HARPSI,
    CH_ORGAN,
    CH_STRINGS,
    CH_TIMPANI,
    D3,
    E2,
    E3,
    E4,
    E5,
    F4,
    F5,
    Bb2,
    Bb3,
    Bb4,
    Eb3,
    Eb5,
    create_midi,
    save_midi,
    setup_standard_tracks,
)

TEMPO = 72
TOTAL_BARS = 81  # ~4:30 at 72 BPM


def create_the_mirror():
    """Generate The Mirror - staring at what they've become."""
    midi = create_midi(5)
    setup_standard_tracks(midi, TEMPO)

    # === SECTION A: Facing the Mirror (bars 1-20) ===
    section_a_facing(midi)

    # === SECTION B: The Reflection (bars 21-44) ===
    section_b_reflection(midi)

    # === SECTION C: Recognition (bars 45-64) ===
    section_c_recognition(midi)

    # === SECTION D: Looking Away (bars 65-81) ===
    section_d_looking_away(midi)

    return midi


def section_a_facing(midi):
    """Facing the mirror - first glimpse of the horror."""

    # Organ - tritone drone (the devil's interval)
    # E to Bb is the tritone - pure unresolved dread
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, 0, 80, 35)  # Held throughout
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, 0, 80, 30)  # Tritone drone

    # Strings - sparse, trembling entries
    string_entries = [
        (8, E4, 8, 30),  # First hesitant note
        (20, F4, 12, 35),  # Dread note
        (36, E5, 16, 32),  # Higher - more exposed
        (56, Bb4, 12, 28),  # Tritone in strings
    ]

    for start_beat, note, dur, vel in string_entries:
        midi.addNote(CH_STRINGS, CH_STRINGS, note, start_beat, dur, vel)

    # Timpani - slow heartbeat (of dread)
    heartbeat_times = [0, 8, 18, 28, 40, 52, 64, 76]
    for i, start_beat in enumerate(heartbeat_times):
        vel = 40 - i * 2  # Getting quieter - as if heart is stopping
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, start_beat, 2, max(vel, 25))

    # Harpsichord - single questioning notes
    questions = [
        (16, E3, 35),
        (32, Bb3, 30),  # Tritone question
        (48, E3, 28),
        (64, Bb3, 25),
    ]

    for start_beat, note, vel in questions:
        midi.addNote(CH_HARPSI, CH_HARPSI, note, start_beat, 4, vel)


def section_b_reflection(midi):
    """The reflection - seeing the horror clearly."""

    base_time = 80  # Bar 21

    # Organ - tritone continues but with chromatic descent
    chromatic_descent = [
        (0, E3, Bb3, 32, 40, 35),
        (32, Eb3, A3, 28, 38, 33),  # Descending
        (60, D3, 68, 28, 36, 31),  # Ab3
        (92, Eb3, A3, 32, 34, 29),  # Back but wrong
    ]

    for offset, note1, note2, dur, vel1, vel2 in chromatic_descent:
        midi.addNote(CH_ORGAN, CH_ORGAN, note1, base_time + offset, dur, vel1)
        midi.addNote(CH_ORGAN, CH_ORGAN, note2, base_time + offset, dur, vel2)

    # Low drone continues
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, base_time, 96, 30)

    # Strings - fragile, exposed
    string_phrases = [
        (0, E5, 16, 35),
        (20, F5, 12, 38),  # Dread
        (36, Eb5, 16, 33),  # Chromatic pain
        (56, E5, 20, 30),
        (80, Bb4, 16, 28),  # Tritone exposed
    ]

    for offset, note, dur, vel in string_phrases:
        midi.addNote(CH_STRINGS, CH_STRINGS, note, base_time + offset, dur, vel)

    # Lower strings - sparse
    midi.addNote(CH_STRINGS, CH_STRINGS, E3, base_time + 24, 32, 30)
    midi.addNote(CH_STRINGS, CH_STRINGS, Bb3, base_time + 60, 28, 25)

    # Timpani - slower heartbeat
    heartbeat_times = [0, 16, 36, 56, 80]
    for i, offset in enumerate(heartbeat_times):
        vel = 35 - i * 3
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time + offset, 2, max(vel, 20))

    # Harpsichord - haunting fragments
    fragments = [
        (8, [E3, B3], 25),
        (28, [E3, Bb3], 22),  # Tritone
        (48, [E3, B3], 20),
        (72, [E3, Bb3], 18),  # Tritone again
    ]

    for offset, notes, vel in fragments:
        for note in notes:
            midi.addNote(CH_HARPSI, CH_HARPSI, note, base_time + offset, 8, vel)


def section_c_recognition(midi):
    """Recognition - they know what they are."""

    base_time = 176  # Bar 45

    # Organ - tritone fully exposed
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, base_time, 80, 40)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, base_time, 80, 38)
    midi.addNote(CH_ORGAN, CH_ORGAN, E3, base_time + 32, 48, 35)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb3, base_time + 32, 48, 33)

    # Strings - sustained horror
    midi.addNote(CH_STRINGS, CH_STRINGS, E5, base_time, 40, 40)
    midi.addNote(CH_STRINGS, CH_STRINGS, Bb4, base_time + 16, 32, 38)  # Tritone layer
    midi.addNote(CH_STRINGS, CH_STRINGS, F5, base_time + 40, 32, 42)  # Dread note
    midi.addNote(CH_STRINGS, CH_STRINGS, E5, base_time + 56, 24, 35)

    # Low strings
    midi.addNote(CH_STRINGS, CH_STRINGS, E3, base_time, 80, 32)

    # Timpani - heartbeat of horror
    for offset in [0, 20, 40, 60]:
        vel = 38 - offset // 10
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time + offset, 2, max(vel, 22))

    # Harpsichord - the question repeated
    # "They know what they are"
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, base_time + 8, 4, 30)
    midi.addNote(CH_HARPSI, CH_HARPSI, Bb3, base_time + 16, 4, 28)
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, base_time + 28, 4, 26)
    midi.addNote(CH_HARPSI, CH_HARPSI, Bb3, base_time + 36, 4, 24)
    midi.addNote(CH_HARPSI, CH_HARPSI, E4, base_time + 48, 8, 28)  # Higher - recognition

    # Brass - single muted statement (they see themselves)
    midi.addNote(CH_BRASS, CH_BRASS, E3, base_time + 56, 8, 45)
    midi.addNote(CH_BRASS, CH_BRASS, Bb3, base_time + 56, 8, 40)  # Tritone


def section_d_looking_away(midi):
    """Looking away - but unable to forget."""

    base_time = 256  # Bar 65

    # Organ - tritone fading but ever-present
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, base_time, 68, 35)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, base_time, 68, 30)

    # Fading upper notes
    midi.addNote(CH_ORGAN, CH_ORGAN, E3, base_time, 32, 28)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb3, base_time + 16, 24, 22)

    # Strings - withdrawing
    midi.addNote(CH_STRINGS, CH_STRINGS, E5, base_time, 24, 32)
    midi.addNote(CH_STRINGS, CH_STRINGS, E4, base_time + 28, 20, 25)
    midi.addNote(CH_STRINGS, CH_STRINGS, E3, base_time + 52, 16, 20)

    # Low strings final
    midi.addNote(CH_STRINGS, CH_STRINGS, E3, base_time, 64, 25)

    # Timpani - final heartbeats
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time, 2, 30)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time + 24, 2, 25)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time + 52, 2, 20)

    # Harpsichord - final whispered question
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, base_time + 16, 4, 22)
    midi.addNote(CH_HARPSI, CH_HARPSI, Bb3, base_time + 32, 4, 18)  # Final tritone

    # Extended silence - then final tritone
    final_time = base_time + 56

    # The mirror remains
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, final_time, 12, 25)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, final_time, 12, 20)
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, final_time + 4, 4, 15)
    midi.addNote(CH_HARPSI, CH_HARPSI, Bb3, final_time + 4, 4, 12)


def main():
    """Generate and save The Mirror."""
    midi = create_the_mirror()
    save_midi(midi, "10_the_mirror.mid", TEMPO, TOTAL_BARS)
    print()
    print("THE MIRROR")
    print("They see what they are.")
    print("They cannot look away.")


if __name__ == "__main__":
    main()
