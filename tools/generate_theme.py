#!/usr/bin/env python3
"""
Babylon Theme: "Φ > 0" (Imperial Rent)

A musical interpretation of the game's aesthetic:
- The inexorable grind of historical materialism
- Class struggle as counterpoint
- The impossibility of core revolution while imperial rent flows
- Dialectical tension that never fully resolves

Instruments:
- Piano: The observer, documenting history
- Cello/Bass: The material base, imperial rent extraction
- Strings: The masses, class consciousness stirring
- Brass: The state apparatus, repression
"""

from pathlib import Path

from midiutil import MIDIFile

# Constants
TEMPO = 76  # BPM - the pace of inevitability
BEATS_PER_BAR = 4
TOTAL_BARS = 32

# MIDI channels
CH_PIANO = 0
CH_BASS = 1
CH_STRINGS = 2
CH_BRASS = 3

# General MIDI programs
PROG_PIANO = 0
PROG_CELLO = 42
PROG_STRINGS = 48
PROG_BRASS = 61

# D minor scale (MIDI note numbers)
# D=50 (bass), D=62 (middle), D=74 (high)
D2, E2, F2, G2, A2, Bb2, C3 = 38, 40, 41, 43, 45, 46, 48
D3, E3, F3, G3, A3, Bb3, C4 = 50, 52, 53, 55, 57, 58, 60
D4, E4, F4, G4, A4, Bb4, C5 = 62, 64, 65, 67, 69, 70, 72
D5, E5, F5, G5, A5 = 74, 76, 77, 79, 81

# Dorian mode has raised 6th (B natural instead of Bb)
B3 = 59  # The note of hope
B4 = 71


def create_babylon_theme() -> MIDIFile:
    """Generate the Babylon theme MIDI file."""
    midi = MIDIFile(4, deinterleave=False)

    # Track names
    midi.addTrackName(CH_PIANO, 0, "Piano - Observer")
    midi.addTrackName(CH_BASS, 0, "Cello - Material Base")
    midi.addTrackName(CH_STRINGS, 0, "Strings - The Masses")
    midi.addTrackName(CH_BRASS, 0, "Brass - State Apparatus")

    # Set tempo
    midi.addTempo(CH_PIANO, 0, TEMPO)

    # Set instruments
    midi.addProgramChange(CH_PIANO, CH_PIANO, 0, PROG_PIANO)
    midi.addProgramChange(CH_BASS, CH_BASS, 0, PROG_CELLO)
    midi.addProgramChange(CH_STRINGS, CH_STRINGS, 0, PROG_STRINGS)
    midi.addProgramChange(CH_BRASS, CH_BRASS, 0, PROG_BRASS)

    # === SECTION A: "The Material Base" (bars 1-8) ===
    # Deep bass ostinato - the unchanging extraction
    section_a_bass(midi)
    section_a_piano(midi)

    # === SECTION B: "Consciousness Stirs" (bars 9-16) ===
    # Melody emerges, tentative, questioning
    section_b_bass(midi)
    section_b_strings(midi)
    section_b_piano(midi)

    # === SECTION C: "The Contradiction Sharpens" (bars 17-24) ===
    # Dissonance, urgency, state responds
    section_c_bass(midi)
    section_c_strings(midi)
    section_c_brass(midi)
    section_c_piano(midi)

    # === SECTION D: "Resolution?" (bars 25-32) ===
    # Co-optation, but a distant echo remains
    section_d_all(midi)

    return midi


def section_a_bass(midi: MIDIFile) -> None:
    """The material base - relentless, mechanical extraction."""
    # Ostinato pattern: D - A - D - F (imperial rent cycle)
    pattern = [D2, A2, D2, F2]
    velocity = 90

    for bar in range(8):
        time = bar * BEATS_PER_BAR
        for i, note in enumerate(pattern):
            midi.addNote(CH_BASS, CH_BASS, note, time + i, 0.9, velocity)


def section_a_piano(midi: MIDIFile) -> None:
    """Sparse piano - observing, documenting."""
    # Occasional chord stabs on the downbeat
    chords = [
        (0, [D4, F4, A4]),  # Dm
        (4, [D4, F4, A4]),  # Dm
        (12, [Bb3, D4, F4]),  # Bb
        (16, [D4, F4, A4]),  # Dm
        (24, [G3, Bb3, D4]),  # Gm
        (28, [A3, C4, E4]),  # Am (dominant prep)
    ]

    for time, notes in chords:
        for note in notes:
            midi.addNote(CH_PIANO, CH_PIANO, note, time, 1.5, 60)


def section_b_bass(midi: MIDIFile) -> None:
    """Bass continues but with slight variation."""
    pattern = [D2, A2, D2, F2]
    pattern_var = [D2, A2, G2, F2]  # Slight variation
    velocity = 85

    for bar in range(8, 16):
        time = bar * BEATS_PER_BAR
        p = pattern_var if bar % 4 == 3 else pattern
        for i, note in enumerate(p):
            midi.addNote(CH_BASS, CH_BASS, note, time + i, 0.9, velocity)


def section_b_strings(midi: MIDIFile) -> None:
    """The masses stir - tentative melody in Dorian mode."""
    # A searching melody, reaching upward
    melody = [
        # Bar 9-10: First awakening
        (32, D4, 2),
        (34, E4, 1),
        (35, F4, 1),
        (36, G4, 2),
        (38, A4, 1),
        (39, B4, 1),  # B natural! Hope!
        # Bar 11-12: Reaching
        (40, A4, 2),
        (42, G4, 1),
        (43, F4, 1),
        (44, E4, 2),
        (46, D4, 2),
        # Bar 13-14: Trying again
        (48, D4, 1),
        (49, F4, 1),
        (50, A4, 2),
        (52, B4, 1),
        (53, A4, 1),
        (54, G4, 2),  # Hope wavers
        # Bar 15-16: Falling back
        (56, F4, 2),
        (58, E4, 1),
        (59, D4, 1),
        (60, D4, 3),
        (63, C4, 1),  # Ends unresolved
    ]

    for time, note, duration in melody:
        midi.addNote(CH_STRINGS, CH_STRINGS, note, time, duration, 70)


def section_b_piano(midi: MIDIFile) -> None:
    """Piano accompanies, more active."""
    accompaniment = [
        (32, [D3, A3], 2),
        (36, [F3, A3], 2),
        (40, [G3, Bb3], 2),
        (44, [A3, E4], 2),
        (48, [D3, F3, A3], 2),
        (52, [G3, B3, D4], 2),  # G major - moment of hope
        (56, [Bb3, D4, F4], 2),
        (60, [A3, C4, E4], 2),  # Unresolved
    ]

    for time, notes, duration in accompaniment:
        for note in notes:
            midi.addNote(CH_PIANO, CH_PIANO, note, time, duration, 55)


def section_c_bass(midi: MIDIFile) -> None:
    """Bass becomes more aggressive - the extraction intensifies."""
    velocity = 100

    for bar in range(16, 24):
        time = bar * BEATS_PER_BAR
        # More driving rhythm
        midi.addNote(CH_BASS, CH_BASS, D2, time, 0.5, velocity)
        midi.addNote(CH_BASS, CH_BASS, D2, time + 0.5, 0.5, velocity - 20)
        midi.addNote(CH_BASS, CH_BASS, A2, time + 1, 0.5, velocity)
        midi.addNote(CH_BASS, CH_BASS, D2, time + 2, 0.5, velocity)
        midi.addNote(CH_BASS, CH_BASS, D2, time + 2.5, 0.5, velocity - 20)
        # Tritone! The devil's interval - contradiction
        if bar >= 20:
            midi.addNote(CH_BASS, CH_BASS, 44, time + 3, 1, velocity)  # Ab - tritone from D


def section_c_strings(midi: MIDIFile) -> None:
    """Strings fight harder, more urgent."""
    melody = [
        # Bar 17-18: Urgency
        (64, A4, 1),
        (65, B4, 1),
        (66, C5, 1),
        (67, D5, 1),
        (68, D5, 1),
        (69, C5, 1),
        (70, B4, 1),
        (71, A4, 1),
        # Bar 19-20: Struggle
        (72, G4, 1),
        (73, A4, 1),
        (74, B4, 2),
        (76, A4, 1),
        (77, G4, 1),
        (78, F4, 2),
        # Bar 21-22: Conflict peaks
        (80, D5, 1),
        (81, C5, 1),
        (82, Bb4, 1),
        (83, A4, 1),
        (84, 68, 2),
        (86, F4, 2),  # Ab (68) - dissonance!
        # Bar 23-24: Being pushed down
        (88, E4, 2),
        (90, D4, 1),
        (91, C4, 1),
        (92, D4, 4),  # Held, defeated
    ]

    for time, note, duration in melody:
        midi.addNote(CH_STRINGS, CH_STRINGS, note, time, duration, 85)


def section_c_brass(midi: MIDIFile) -> None:
    """State apparatus responds - ominous brass."""
    # Distant, threatening brass chords
    brass_hits = [
        (68, [D3, F3, A3], 2, 50),  # Dm - warning
        (72, [D3, F3, A3], 1, 60),  # Dm - louder
        (74, [D3, F3, A3], 1, 70),
        (76, [Bb2, D3, F3], 2, 75),  # Bb - ominous
        (80, [D3, F3, A3], 1, 80),  # Peak repression
        (82, [D3, 68, A3], 2, 85),  # Dm with Ab - brutal dissonance
        (88, [A2, C3, E3], 4, 70),  # Am - lingering threat
    ]

    for time, notes, duration, velocity in brass_hits:
        for note in notes:
            midi.addNote(CH_BRASS, CH_BRASS, note, time, duration, velocity)


def section_c_piano(midi: MIDIFile) -> None:
    """Piano becomes percussive, hammering."""
    for bar in range(16, 24):
        time = bar * BEATS_PER_BAR
        # Repeated octave hammering
        midi.addNote(CH_PIANO, CH_PIANO, D3, time, 0.5, 75)
        midi.addNote(CH_PIANO, CH_PIANO, D4, time, 0.5, 75)
        midi.addNote(CH_PIANO, CH_PIANO, D3, time + 1, 0.5, 65)
        midi.addNote(CH_PIANO, CH_PIANO, D4, time + 1, 0.5, 65)
        midi.addNote(CH_PIANO, CH_PIANO, D3, time + 2, 0.5, 75)
        midi.addNote(CH_PIANO, CH_PIANO, D4, time + 2, 0.5, 75)
        if bar < 22:
            midi.addNote(CH_PIANO, CH_PIANO, D3, time + 3, 0.5, 55)
            midi.addNote(CH_PIANO, CH_PIANO, D4, time + 3, 0.5, 55)


def section_d_all(midi: MIDIFile) -> None:
    """Resolution? - Co-optation, but a distant echo remains."""

    # Bass: Returns to opening pattern, but slower, quieter - the grind continues
    pattern = [D2, A2, D2, F2]
    for bar in range(24, 30):
        time = bar * BEATS_PER_BAR
        velocity = 80 - (bar - 24) * 5  # Fading
        for i, note in enumerate(pattern):
            midi.addNote(CH_BASS, CH_BASS, note, time + i, 0.9, velocity)

    # Final bass notes - unresolved
    midi.addNote(CH_BASS, CH_BASS, D2, 120, 2, 60)
    midi.addNote(CH_BASS, CH_BASS, A2, 124, 4, 50)  # Ends on dominant - unresolved!

    # Strings: Subsumed, but a ghost remains
    melody = [
        (96, D4, 4, 60),  # The melody tries once more
        (100, E4, 2, 50),
        (102, F4, 2, 45),
        (104, E4, 4, 40),  # Fading
        (108, D4, 4, 35),
        # The distant echo - high strings, very quiet (the periphery?)
        (112, D5, 4, 25),
        (116, A5, 4, 20),  # A high A... waiting
        (120, A5, 8, 15),  # Held, barely audible... the revolution waits elsewhere
    ]

    for time, note, duration, velocity in melody:
        midi.addNote(CH_STRINGS, CH_STRINGS, note, time, duration, velocity)

    # Piano: Sparse, observing the aftermath
    chords = [
        (96, [D3, A3, D4], 4, 50),
        (104, [D3, F3, A3], 4, 40),
        (112, [D3, A3], 4, 30),
        (120, [D3, A3, E4], 8, 25),  # Final chord: Dm add9 - unresolved, questioning
    ]

    for time, notes, duration, velocity in chords:
        for note in notes:
            midi.addNote(CH_PIANO, CH_PIANO, note, time, duration, velocity)

    # Brass: One last distant note
    midi.addNote(CH_BRASS, CH_BRASS, A2, 120, 8, 30)  # The state persists...


def main() -> None:
    """Generate and save the Babylon theme."""
    output_dir = Path(__file__).parent.parent / "assets" / "music"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "babylon_theme_phi.mid"

    midi = create_babylon_theme()

    with open(output_path, "wb") as f:
        midi.writeFile(f)

    print(f"Generated: {output_path}")
    print(
        f"Duration: ~{(TOTAL_BARS * BEATS_PER_BAR * 60) // TEMPO // 60}:{((TOTAL_BARS * BEATS_PER_BAR * 60) // TEMPO) % 60:02d}"
    )
    print()
    print("Φ > 0")
    print("The imperial rent flows.")
    print("The contradiction continues.")
    print("History is not over.")


if __name__ == "__main__":
    main()
