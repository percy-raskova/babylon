#!/usr/bin/env python3
"""
Track 01: "The Apparatus" (5:00)
Mood: MENACING - Cold, efficient, unstoppable

The surveillance state at peak operation.
Cold, efficient, all-seeing - the machine that never sleeps.

Musical approach:
- Mechanical 8th-note patterns in harpsichord (clockwork precision)
- Timpani clock ticking relentlessly (the machine that never stops)
- Low drone establishing machine atmosphere
- Surveillance "pings" that feel invasive
- Brass stabs as random security interventions

Tempo: 108 BPM | Key: E Phrygian
Target duration: 5:00 (~135 bars at 108 BPM)
"""

from . import (
    A3,
    A4,
    B2,
    B3,
    C4,
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
    G5,
    Bb3,
    create_midi,
    save_midi,
    setup_standard_tracks,
)

TEMPO = 108
TOTAL_BARS = 135  # ~5:00 at 108 BPM


def create_the_apparatus():
    """Generate 'The Apparatus' - cold surveillance state power."""
    midi = create_midi(5)
    setup_standard_tracks(midi, TEMPO)

    # === SECTION A: Machine Awakening (bars 1-24) ===
    section_a_awakening(midi)

    # === SECTION B: Full Operation (bars 25-64) ===
    section_b_operation(midi)

    # === SECTION C: Surveillance Intensifies (bars 65-104) ===
    section_c_intensify(midi)

    # === SECTION D: Eternal Watch (bars 105-135) ===
    section_d_eternal(midi)

    return midi


def section_a_awakening(midi):
    """The machine starts up - gradual introduction of elements."""

    # Low organ drone - the machine hum starts quietly
    for bar in range(24):
        time = bar * 4
        # Fade in over first 8 bars
        vel = min(50, 20 + bar * 3)
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, vel)
        if bar >= 8:
            midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, vel - 10)

    # Timpani clock starts at bar 5 - very mechanical
    for bar in range(5, 24):
        time = bar * 4
        base_vel = 50 + (bar - 5) * 2  # Gradually louder
        for beat in range(4):
            vel = base_vel if beat == 0 else base_vel - 15
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, min(vel, 80))
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat + 0.5, 0.25, min(vel - 25, 55))

    # Harpsichord mechanical figure enters at bar 12
    mech_figure = [E3, F3, E3, G3, E3, F3, E3, A3]
    for bar in range(12, 24):
        time = bar * 4
        vel = 55 + (bar - 12) * 2
        for i, note in enumerate(mech_figure):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, min(vel, 70))

    # First surveillance pings at bar 18
    for bar in range(18, 24):
        time = bar * 4
        pings = [(0.5, E5), (1.5, F5), (2.5, E5), (3.5, G5)]
        for offset, note in pings:
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + offset, 0.25, 60)


def section_b_operation(midi):
    """Full surveillance operation - all systems online."""

    base_bar = 24

    # Constant timpani clock
    for bar in range(40):
        time = (base_bar + bar) * 4
        for beat in range(4):
            vel = 85 if beat == 0 else 60
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, vel)
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat + 0.5, 0.25, 40)

    # Organ drone - continuous
    for bar in range(40):
        time = (base_bar + bar) * 4
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 50)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, 40)

    # Mechanical harpsichord - two-octave patterns
    for bar in range(40):
        time = (base_bar + bar) * 4
        if bar % 4 < 2:
            # Lower octave pattern
            figure = [E3, F3, E3, G3, E3, F3, E3, A3]
        else:
            # Upper octave pattern
            figure = [E4, F4, E4, G4, E4, F4, E4, A4]
        for i, note in enumerate(figure):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, 70)

    # Surveillance pings - irregular but persistent
    for bar in range(40):
        time = (base_bar + bar) * 4
        if bar % 3 == 0:
            pings = [(0.5, E5), (1.5, F5), (3.0, G5)]
        elif bar % 3 == 1:
            pings = [(1.0, F5), (2.5, E5), (3.5, F5)]
        else:
            pings = [(0.5, G5), (2.0, E5), (3.0, F5)]
        for offset, note in pings:
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + offset, 0.25, 65)

    # Strings - low anxiety undertone
    for bar in range(0, 40, 2):
        time = (base_bar + bar) * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 8, 55)
        midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 8, 45)

    # Brass stabs - random security interventions (4 bars each)
    interventions = [
        (32, [E3, B3, E4]),  # Bar 8 of section
        (48, [E3, B3, F4]),  # Bar 24 - with dread note
        (56, [E3, Bb3, E4]),  # Bar 32 - tritone hint
    ]
    for bar, notes in interventions:
        time = (base_bar + bar - 24) * 4
        for note in notes:
            midi.addNote(CH_BRASS, CH_BRASS, note, time, 0.5, 90)


def section_c_intensify(midi):
    """Surveillance intensifies - more complex patterns, higher tension."""

    base_bar = 64

    # Timpani - more aggressive pattern
    for bar in range(40):
        time = (base_bar + bar) * 4
        for beat in range(4):
            vel = 90 if beat == 0 else 70
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, vel)
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat + 0.5, 0.25, 50)
            # Additional 16th note hits
            if bar % 2 == 1:
                midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat + 0.25, 0.125, 35)

    # Organ - more presence, occasional tritone
    for bar in range(40):
        time = (base_bar + bar) * 4
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 55)
        if bar % 8 < 4:
            midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, 45)
        else:
            # Tritone creeps in
            midi.addNote(CH_ORGAN, CH_ORGAN, Bb3, time, 4, 40)

    # Complex harpsichord - interlocking patterns
    for bar in range(40):
        time = (base_bar + bar) * 4

        # Primary mechanical figure
        figure = [E3, F3, E3, G3, E3, F3, E3, A3]
        for i, note in enumerate(figure):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.35, 72)

        # Counter-figure in upper octave (offset by 0.25)
        if bar % 2 == 1:
            counter = [E4, G4, F4, E4]
            for i, note in enumerate(counter):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + 0.25 + i * 0.5, 0.3, 60)

    # More urgent surveillance pings
    for bar in range(40):
        time = (base_bar + bar) * 4
        # Denser ping pattern
        pings = [
            (0.25, E5),
            (0.75, F5),
            (1.5, E5),
            (2.0, G5),
            (2.75, F5),
            (3.25, E5),
        ]
        for offset, note in pings:
            if (bar + int(offset * 4)) % 3 != 0:  # Irregular omissions
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + offset, 0.2, 68)

    # Strings - rising tension
    string_phrases = [
        (0, [E3, B3], 16),
        (16, [E3, C4], 12),  # Minor tension
        (28, [E3, Bb3], 12),  # Tritone
    ]
    for bar_offset, notes, dur in string_phrases:
        time = (base_bar + bar_offset) * 4
        for note in notes:
            midi.addNote(CH_STRINGS, CH_STRINGS, note, time, dur * 4, 60)

    # Brass - more frequent interventions
    brass_hits = [
        (72, [E3, B3, E4], 0.5, 95),
        (80, [E3, B3, F4], 0.5, 100),  # Dread
        (88, [E3, Bb3, E4], 0.75, 100),  # Tritone
        (96, [E3, B3, E4], 0.25, 95),
        (97, [F3, C4, F4], 0.25, 90),  # Dread chord
    ]
    for bar, notes, dur, vel in brass_hits:
        time = bar * 4
        for note in notes:
            midi.addNote(CH_BRASS, CH_BRASS, note, time, dur, vel)


def section_d_eternal(midi):
    """The eternal watch - the machine never stops."""

    base_bar = 104

    # Timpani - unwavering, perhaps slightly fatigued
    for bar in range(31):
        time = (base_bar + bar) * 4
        for beat in range(4):
            vel = 80 if beat == 0 else 55
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, vel)
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat + 0.5, 0.25, 35)

    # Organ - steady drone
    for bar in range(31):
        time = (base_bar + bar) * 4
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 50)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, 40)

    # Harpsichord - mechanical but endless
    for bar in range(31):
        time = (base_bar + bar) * 4
        figure = [E3, F3, E3, G3, E3, F3, E3, A3]
        vel = 65 if bar < 24 else 60  # Slight fade at end
        for i, note in enumerate(figure):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, vel)

    # Surveillance pings - persistent
    for bar in range(31):
        time = (base_bar + bar) * 4
        pings = [(0.5, E5), (1.5, F5), (2.5, E5), (3.5, G5)]
        vel = 62 if bar < 24 else 55
        for offset, note in pings:
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + offset, 0.25, vel)

    # Strings - low continuous presence
    for bar in range(0, 31, 4):
        time = (base_bar + bar) * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 16, 50)
        midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 16, 40)

    # Final brass statement at bar 128 - the apparatus is eternal
    time = 128 * 4
    for note in [E3, B3, E4]:
        midi.addNote(CH_BRASS, CH_BRASS, note, time, 2, 85)

    # Abrupt end - mid-phrase at bar 135
    # The machine doesn't stop, we just stop listening


def main():
    """Generate and save The Apparatus."""
    midi = create_the_apparatus()
    save_midi(midi, "01_the_apparatus.mid", TEMPO, TOTAL_BARS)
    print()
    print("THE APPARATUS")
    print("Cold. Efficient. All-seeing.")
    print("The machine never sleeps.")


if __name__ == "__main__":
    main()
