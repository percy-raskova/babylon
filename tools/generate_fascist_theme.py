#!/usr/bin/env python3
"""
Babylon Theme: "The Panopticon"

The fascist perspective - not triumphant evil, but ANXIOUS evil:
- The exhaustion of maintaining oppression
- A thousand spinning plates that must not fall
- Self-aware villainy - they KNOW what they are
- The void beneath the jackboot
- Surveillance, paranoia, brittle power

Instruments:
- Harpsichord: Cold, mechanical baroque - aestheticized violence
- Strings tremolo: Constant underlying anxiety
- Brass: State violence, sudden and overwhelming
- Timpani: The jackboot, the clock
- Organ: False grandeur masking the void
"""

from pathlib import Path

from midiutil import MIDIFile

# Constants
TEMPO = 108  # BPM - the pace of barely-controlled panic
TOTAL_BARS = 40

# MIDI channels
CH_HARPSI = 0
CH_STRINGS = 1
CH_BRASS = 2
CH_TIMPANI = 3
CH_ORGAN = 4

# General MIDI programs
PROG_HARPSICHORD = 6
PROG_TREMOLO_STRINGS = 44
PROG_BRASS = 61
PROG_TIMPANI = 47
PROG_ORGAN = 19

# E Phrygian scale - that flat 2 (F) is DREAD
E2, F2, G2, A2, B2, C3, D3 = 40, 41, 43, 45, 47, 48, 50
E3, F3, G3, A3, B3, C4, D4 = 52, 53, 55, 57, 59, 60, 62
E4, F4, G4, A4, B4, C5, D5 = 64, 65, 67, 69, 71, 72, 74
E5, F5, G5 = 76, 77, 79

# Chromatic notes for dissonance
Bb2 = 46  # Tritone from E - the devil's interval
Eb3, Bb3, Db4 = 51, 58, 61
Eb4, Ab4, Bb4 = 63, 68, 70


def create_panopticon_theme() -> MIDIFile:
    """Generate the fascist panopticon theme."""
    midi = MIDIFile(5, deinterleave=False)

    # Track names
    midi.addTrackName(CH_HARPSI, 0, "Harpsichord - The Machine")
    midi.addTrackName(CH_STRINGS, 0, "Strings - Anxiety")
    midi.addTrackName(CH_BRASS, 0, "Brass - State Violence")
    midi.addTrackName(CH_TIMPANI, 0, "Timpani - The Clock")
    midi.addTrackName(CH_ORGAN, 0, "Organ - False Grandeur")

    # Set tempo
    midi.addTempo(CH_HARPSI, 0, TEMPO)

    # Set instruments
    midi.addProgramChange(CH_HARPSI, CH_HARPSI, 0, PROG_HARPSICHORD)
    midi.addProgramChange(CH_STRINGS, CH_STRINGS, 0, PROG_TREMOLO_STRINGS)
    midi.addProgramChange(CH_BRASS, CH_BRASS, 0, PROG_BRASS)
    midi.addProgramChange(CH_TIMPANI, CH_TIMPANI, 0, PROG_TIMPANI)
    midi.addProgramChange(CH_ORGAN, CH_ORGAN, 0, PROG_ORGAN)

    # === SECTION A: "The Apparatus" (bars 1-8) ===
    section_a_apparatus(midi)

    # === SECTION B: "The Juggling" (bars 9-20) ===
    section_b_juggling(midi)

    # === SECTION C: "The Mirror" (bars 21-28) ===
    section_c_mirror(midi)

    # === SECTION D: "The Void / Return" (bars 29-40) ===
    section_d_void(midi)

    return midi


def section_a_apparatus(midi: MIDIFile) -> None:
    """The machine state - ticking, watching, controlling."""

    # Timpani: Relentless clock ticking
    for bar in range(8):
        time = bar * 4
        # Mechanical precision
        for beat in range(4):
            vel = 80 if beat == 0 else 50
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, vel)
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat + 0.5, 0.25, 35)

    # Harpsichord: Cold surveillance pings - high notes
    surveillance_pings = [
        (0.5, E5, 0.25),
        (1.5, F5, 0.25),
        (2.5, E5, 0.25),
        (3.5, G5, 0.25),
        (4.5, E5, 0.25),
        (5.0, F5, 0.25),
        (6.5, E5, 0.25),
        (7.5, F5, 0.25),
    ]
    for bar in range(8):
        time = bar * 4
        for offset, note, dur in surveillance_pings:
            if (bar + offset) % 2 < 1.5:  # Irregular pattern
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + offset, dur, 70)

    # Strings: Low drone - the machine hum
    for bar in range(8):
        time = bar * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E2, time, 4, 60)
        midi.addNote(CH_STRINGS, CH_STRINGS, B2, time, 4, 50)

    # Harpsichord: Mechanical figure in the middle
    mech_figure = [E3, F3, E3, G3, E3, F3, E3, A3]
    for bar in range(8):
        time = bar * 4
        for i, note in enumerate(mech_figure):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, 65)


def section_b_juggling(midi: MIDIFile) -> None:
    """The spinning plates - multiple independent voices, irregular meter feel."""

    base_time = 32  # Bar 9 starts at beat 32

    # Voice 1: Harpsichord - frantic ascending patterns
    patterns_1 = [
        # Bar 9-10
        (0, [E3, F3, G3, A3, B3, C4, D4, E4], 0.5),
        (4, [E4, D4, C4, B3, A3, G3, F3, E3], 0.5),
        # Bar 11-12 - getting faster, more frantic
        (8, [E3, G3, B3, E4, D4, B3, G3, E3], 0.45),
        (12, [F3, A3, C4, F4, E4, C4, A3, F3], 0.45),
        # Bar 13-14
        (16, [E3, F3, G3, A3, B3, C4, D4, E4, F4, E4], 0.4),
        (20, [E4, D4, C4, B3, A3, G3, F3, E3, D3, E3], 0.4),
        # Bar 15-16 - 7/8 feel (accents)
        (24, [E3, F3, G3, E3, F3, G3, A3], 0.5),
        (28, [B3, C4, D4, B3, C4, D4, E4], 0.5),
        # Bar 17-18 - 5/4 feel
        (32, [E4, D4, C4, B3, A3], 0.8),
        (36, [G3, A3, B3, C4, D4], 0.8),
        # Bar 19-20 - return to frantic 4/4
        (40, [E3, F3, G3, A3, B3, C4, D4, E4], 0.45),
        (44, [F4, E4, D4, C4, B3, A3, G3, F3], 0.45),
    ]

    for offset, notes, dur in patterns_1:
        for i, note in enumerate(notes):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, base_time + offset + i * dur, dur * 0.9, 75)

    # Voice 2: Strings - counter-rhythm, almost colliding
    for bar in range(12):
        time = base_time + bar * 4
        # Syncopated entries - always slightly off
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time + 0.5, 1.5, 70)
        midi.addNote(CH_STRINGS, CH_STRINGS, B3, time + 2.5, 1.5, 65)
        if bar % 3 == 2:  # Extra anxiety note
            midi.addNote(CH_STRINGS, CH_STRINGS, F3, time + 1.5, 1, 75)

    # Voice 3: Brass stabs - state interventions
    brass_stabs = [
        (36, [E3, B3, E4], 0.5, 90),  # Bar 10
        (44, [F3, C4, F4], 0.5, 95),  # Bar 12
        (52, [E3, B3, E4], 0.25, 100),  # Bar 14 - sharper
        (53, [E3, B3, E4], 0.25, 95),
        (60, [F3, Bb3, Db4], 0.75, 100),  # Bar 16 - dissonant!
        (68, [E3, Bb3, E4], 1, 90),  # Bar 18 - tritone
        (76, [E3, B3, E4, G4], 0.5, 100),  # Bar 20 - climax
    ]

    for time, notes, dur, vel in brass_stabs:
        for note in notes:
            midi.addNote(CH_BRASS, CH_BRASS, note, time, dur, vel)

    # Timpani: Irregular accents, the juggling rhythm
    for bar in range(12):
        time = base_time + bar * 4
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, 85)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, B2, time + 1.5, 0.5, 70)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, 75)
        if bar % 2 == 1:
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3.5, 0.5, 80)


def section_c_mirror(midi: MIDIFile) -> None:
    """The self-awareness - staring into what they are."""

    base_time = 80  # Bar 21

    # Organ: The false grandeur revealed as hollow
    # Descending chromatic line - looking into the abyss
    chromatic_descent = [
        (0, [E4, B4], 4),
        (4, [Eb4, Bb4], 4),
        (8, [D4, A4], 4),
        (12, [Db4, Ab4], 4),
        (16, [C4, G4], 4),
        (20, [B3, 66], 4),  # F#4
        (24, [Bb3, F4], 6),  # Held - staring
        (30, [A3, E4], 2),  # Resolution that isn't
    ]

    for offset, notes, dur in chromatic_descent:
        for note in notes:
            midi.addNote(CH_ORGAN, CH_ORGAN, note, base_time + offset, dur, 55)

    # Low organ pedal - the void underneath
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, base_time, 32, 45)

    # Strings: Trembling, fragile
    string_fragments = [
        (2, E5, 2, 40),
        (6, F5, 2, 35),
        (10, E5, 3, 30),
        (14, Eb4, 2, 35),
        (18, D4, 4, 30),
        (24, C4, 4, 25),
        (28, B3, 4, 20),  # Fading
    ]

    for offset, note, dur, vel in string_fragments:
        midi.addNote(CH_STRINGS, CH_STRINGS, note, base_time + offset, dur, vel)

    # Harpsichord: Sparse, questioning - they know
    questions = [
        (4, [E3, B3], 1),
        (12, [F3, Bb3], 1),  # Tritone - the horror
        (20, [E3, Bb3], 2),  # Held tritone
        (26, [E3, B3, E4], 2),  # Return to "normal" - but hollow
    ]

    for offset, notes, dur in questions:
        for note in notes:
            midi.addNote(CH_HARPSI, CH_HARPSI, note, base_time + offset, dur, 50)

    # Timpani: Slow heartbeat of dread
    for i in range(8):
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time + i * 4, 0.5, 50 - i * 3)


def section_d_void(midi: MIDIFile) -> None:
    """The void - what if it stops? Then desperate return."""

    base_time = 112  # Bar 29

    # THE VOID (bars 29-34): Everything thins out

    # Organ: Just the tritone, held, exposed
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, base_time, 16, 40)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, base_time, 16, 40)  # Tritone drone

    # Strings: Almost nothing - whispers
    midi.addNote(CH_STRINGS, CH_STRINGS, E5, base_time + 4, 8, 20)
    midi.addNote(CH_STRINGS, CH_STRINGS, F5, base_time + 12, 4, 15)  # The dread note

    # Harpsichord: Single notes, questioning the void
    void_notes = [(2, E4, 30), (6, F4, 25), (10, E4, 20), (14, Bb3, 25), (18, E3, 20)]
    for offset, note, vel in void_notes:
        midi.addNote(CH_HARPSI, CH_HARPSI, note, base_time + offset, 1, vel)

    # Timpani: The clock... stopping?
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time, 0.5, 40)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time + 4, 0.5, 30)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time + 10, 0.5, 20)
    # ... silence ...

    # === THE DESPERATE RETURN (bars 35-40) ===
    # NO! Don't stop! The machine must continue!

    return_time = base_time + 24  # Bar 35

    # Timpani: Clock RESTARTS - frantic
    for bar in range(5):
        time = return_time + bar * 4
        for beat in range(4):
            vel = 90 if beat == 0 else 60
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, vel)
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat + 0.5, 0.25, 45)

    # Harpsichord: Section A material but LOUDER, more desperate
    for bar in range(5):
        time = return_time + bar * 4
        mech_figure = [E3, F3, E3, G3, E3, F3, E3, A3]
        for i, note in enumerate(mech_figure):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, 85)

    # Brass: State reasserts itself - LOUD
    midi.addNote(CH_BRASS, CH_BRASS, E3, return_time, 2, 100)
    midi.addNote(CH_BRASS, CH_BRASS, B3, return_time, 2, 100)
    midi.addNote(CH_BRASS, CH_BRASS, E4, return_time, 2, 100)

    midi.addNote(CH_BRASS, CH_BRASS, E3, return_time + 8, 2, 100)
    midi.addNote(CH_BRASS, CH_BRASS, B3, return_time + 8, 2, 100)
    midi.addNote(CH_BRASS, CH_BRASS, E4, return_time + 8, 2, 100)

    # Organ: Returns with false grandeur
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, return_time, 16, 70)
    midi.addNote(CH_ORGAN, CH_ORGAN, E3, return_time, 16, 60)

    # Strings: Tremolo anxiety full force
    midi.addNote(CH_STRINGS, CH_STRINGS, E3, return_time, 8, 80)
    midi.addNote(CH_STRINGS, CH_STRINGS, B3, return_time, 8, 75)
    midi.addNote(CH_STRINGS, CH_STRINGS, E4, return_time + 8, 8, 80)
    midi.addNote(CH_STRINGS, CH_STRINGS, B4, return_time + 8, 8, 75)

    # ABRUPT END - mid phrase, cut off
    # The final notes at bar 40 just... stop
    # (The piece ends at beat 160, mid-phrase)
    # The panopticon never sleeps. It doesn't resolve. It continues.


def main() -> None:
    """Generate and save the Panopticon theme."""
    output_dir = Path(__file__).parent.parent / "assets" / "music"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "babylon_theme_panopticon.mid"

    midi = create_panopticon_theme()

    with open(output_path, "wb") as f:
        midi.writeFile(f)

    print(f"Generated: {output_path}")
    duration_beats = TOTAL_BARS * 4
    duration_seconds = (duration_beats * 60) // TEMPO
    print(f"Duration: ~{duration_seconds // 60}:{duration_seconds % 60:02d}")
    print()
    print("THE PANOPTICON")
    print("They know what they are.")
    print("They cannot stop.")
    print("The machine continues.")


if __name__ == "__main__":
    main()
