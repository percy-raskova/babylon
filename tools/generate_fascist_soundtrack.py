#!/usr/bin/env python3
"""
Fascist Faction Soundtrack - Generate All Tracks

Generates the complete ~63 minute soundtrack for the National Revival Movement.

Usage:
    cd babylon/tools
    poetry run python generate_fascist_soundtrack.py
"""

from pathlib import Path

from midiutil import MIDIFile

# =============================================================================
# SHARED CONSTANTS (copied from __init__.py to avoid import issues)
# =============================================================================

# E Phrygian scale - The sound of dread
E2, F2, G2, A2, B2, C3, D3 = 40, 41, 43, 45, 47, 48, 50
E3, F3, G3, A3, B3, C4, D4 = 52, 53, 55, 57, 59, 60, 62
E4, F4, G4, A4, B4, C5, D5 = 64, 65, 67, 69, 71, 72, 74
E5, F5, G5, A5, B5 = 76, 77, 79, 81, 83

# Chromatic/tritone notes
Bb1, Bb2, Bb3, Bb4 = 34, 46, 58, 70
Db3, Eb3, Fs3, Ab3 = 49, 51, 54, 56
Db4, Eb4, Fs4, Ab4 = 61, 63, 66, 68

# General MIDI Programs
PROG_HARPSICHORD = 6
PROG_TREMOLO_STRINGS = 44
PROG_BRASS = 61
PROG_TIMPANI = 47
PROG_ORGAN = 19
PROG_STRINGS = 48
PROG_CELLO = 42
PROG_FRENCH_HORN = 60
PROG_TROMBONE = 57
PROG_TUBA = 58

# Percussion
DRUM_BASS = 36
DRUM_SNARE = 38
DRUM_CLOSED_HH = 42
DRUM_OPEN_HH = 46
DRUM_CRASH = 49
DRUM_RIDE = 51
DRUM_TOM_LOW = 45
DRUM_TOM_MID = 47
DRUM_TOM_HIGH = 50

# MIDI Channels (for program changes and note assignment)
CH_HARPSI = 0
CH_STRINGS = 1
CH_BRASS = 2
CH_TIMPANI = 3
CH_ORGAN = 4
CH_EXTRA1 = 5
CH_EXTRA2 = 6

# MIDI Channel 9 (0-indexed) = Channel 10 = General MIDI Percussion
MIDI_DRUM_CHANNEL = 9
# Track number for drums (when using 6+ tracks)
TRACK_DRUMS = 5

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "assets" / "music" / "fascist"


def create_midi(num_tracks: int = 5) -> MIDIFile:
    """Create a new MIDI file with standard configuration."""
    return MIDIFile(num_tracks, deinterleave=False)


def setup_standard_tracks(midi: MIDIFile, tempo: int) -> None:
    """Configure the standard 5-voice fascist soundtrack."""
    midi.addTrackName(CH_HARPSI, 0, "Harpsichord - The Machine")
    midi.addTrackName(CH_STRINGS, 0, "Strings - Anxiety")
    midi.addTrackName(CH_BRASS, 0, "Brass - State Violence")
    midi.addTrackName(CH_TIMPANI, 0, "Timpani - The Clock")
    midi.addTrackName(CH_ORGAN, 0, "Organ - False Grandeur")

    midi.addTempo(CH_HARPSI, 0, tempo)

    midi.addProgramChange(CH_HARPSI, CH_HARPSI, 0, PROG_HARPSICHORD)
    midi.addProgramChange(CH_STRINGS, CH_STRINGS, 0, PROG_TREMOLO_STRINGS)
    midi.addProgramChange(CH_BRASS, CH_BRASS, 0, PROG_BRASS)
    midi.addProgramChange(CH_TIMPANI, CH_TIMPANI, 0, PROG_TIMPANI)
    midi.addProgramChange(CH_ORGAN, CH_ORGAN, 0, PROG_ORGAN)


def save_midi(midi: MIDIFile, filename: str, tempo: int, total_bars: int) -> Path:
    """Save MIDI file and print duration info."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / filename

    with open(output_path, "wb") as f:
        midi.writeFile(f)

    duration_beats = total_bars * 4
    duration_seconds = (duration_beats * 60) // tempo
    minutes = duration_seconds // 60
    seconds = duration_seconds % 60

    print(f"  Generated: {output_path}")
    print(f"  Duration: ~{minutes}:{seconds:02d}")

    return output_path


# =============================================================================
# TRACK GENERATORS - Inline implementations
# =============================================================================


def generate_track_01_apparatus():
    """Track 01: The Apparatus (5:00) - Cold surveillance state."""
    TEMPO = 108
    TOTAL_BARS = 135

    midi = create_midi(5)
    setup_standard_tracks(midi, TEMPO)

    # Section A: Machine Awakening (bars 1-24)
    for bar in range(24):
        time = bar * 4
        vel = min(50, 20 + bar * 3)
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, vel)
        if bar >= 8:
            midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, vel - 10)

    for bar in range(5, 24):
        time = bar * 4
        base_vel = 50 + (bar - 5) * 2
        for beat in range(4):
            vel = base_vel if beat == 0 else base_vel - 15
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, min(vel, 80))
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat + 0.5, 0.25, min(vel - 25, 55))

    mech_figure = [E3, F3, E3, G3, E3, F3, E3, A3]
    for bar in range(12, 24):
        time = bar * 4
        vel = 55 + (bar - 12) * 2
        for i, note in enumerate(mech_figure):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, min(vel, 70))

    # Section B: Full Operation (bars 25-64)
    for bar in range(40):
        time = (24 + bar) * 4
        for beat in range(4):
            vel = 85 if beat == 0 else 60
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, vel)
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat + 0.5, 0.25, 40)

        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 50)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, 40)

        figure = (
            [E3, F3, E3, G3, E3, F3, E3, A3] if bar % 4 < 2 else [E4, F4, E4, G4, E4, F4, E4, A4]
        )
        for i, note in enumerate(figure):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, 70)

    # Section C & D: Intensify and Eternal (bars 65-135)
    for bar in range(71):
        time = (64 + bar) * 4
        for beat in range(4):
            vel = 90 if beat == 0 else 70
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, vel)
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat + 0.5, 0.25, 45)

        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 55)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, 45)

        for i, note in enumerate(mech_figure):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, 72)

    # Strings throughout
    for bar in range(0, TOTAL_BARS, 4):
        time = bar * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 16, 55)
        midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 16, 45)

    # Brass stabs
    for bar in [32, 48, 80, 96, 112]:
        if bar < TOTAL_BARS:
            time = bar * 4
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 0.5, 90)
            midi.addNote(CH_BRASS, CH_BRASS, B3, time, 0.5, 85)
            midi.addNote(CH_BRASS, CH_BRASS, E4, time, 0.5, 80)

    save_midi(midi, "01_the_apparatus.mid", TEMPO, TOTAL_BARS)
    print("  THE APPARATUS - Cold. Efficient. All-seeing.")


def generate_track_02_viktors_march():
    """Track 02: Viktor's March (4:30) - The strongman's theme."""
    TEMPO = 100
    TOTAL_BARS = 113

    midi = create_midi(7)
    setup_standard_tracks(midi, TEMPO)
    midi.addTrackName(5, 0, "French Horn - Military Authority")
    midi.addProgramChange(5, 5, 0, PROG_FRENCH_HORN)

    # March throughout
    for bar in range(TOTAL_BARS):
        time = bar * 4
        vel = min(45 + bar, 90)

        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, vel)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 1.5, 0.25, vel - 20)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, vel - 5)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3, 0.25, vel - 15)

    # Organ
    for bar in range(16, TOTAL_BARS):
        time = bar * 4
        vel = min(35 + (bar - 16), 60)
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, vel)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, vel - 10)

    # Brass fanfares
    for bar in [28, 36, 44, 56, 64, 72, 84, 96, 108]:
        if bar < TOTAL_BARS:
            time = bar * 4
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 2, 85)
            midi.addNote(CH_BRASS, CH_BRASS, B3, time, 2, 80)
            midi.addNote(CH_BRASS, CH_BRASS, E4, time + 2, 2, 90)

    # Strings
    for bar in range(0, TOTAL_BARS, 4):
        time = bar * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 16, 55)

    save_midi(midi, "02_viktors_march.mid", TEMPO, TOTAL_BARS)
    print("  VIKTOR'S MARCH - The jackboot rhythm never falters.")


def generate_track_03_nationalist_guard():
    """Track 03: The Nationalist Guard (6:00) - Paramilitary violence."""
    TEMPO = 112
    TOTAL_BARS = 168

    midi = create_midi(6)
    setup_standard_tracks(midi, TEMPO)

    # Aggressive drums throughout
    for bar in range(TOTAL_BARS):
        time = bar * 4
        vel = min(50 + bar // 4, 95)

        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, vel)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, vel - 5)

        if bar >= 32:
            midi.addNote(TRACK_DRUMS, MIDI_DRUM_CHANNEL, DRUM_BASS, time, 0.5, vel)
            midi.addNote(TRACK_DRUMS, MIDI_DRUM_CHANNEL, DRUM_BASS, time + 2, 0.5, vel - 5)
            midi.addNote(TRACK_DRUMS, MIDI_DRUM_CHANNEL, DRUM_SNARE, time + 1, 0.25, vel - 10)
            midi.addNote(TRACK_DRUMS, MIDI_DRUM_CHANNEL, DRUM_SNARE, time + 3, 0.25, vel - 10)

    # Harpsichord
    pattern = [E3, E3, F3, E3, E3, G3, E3, A3]
    for bar in range(20, TOTAL_BARS):
        time = bar * 4
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, 72)

    # Brass
    for bar in range(32, TOTAL_BARS, 8):
        time = bar * 4
        midi.addNote(CH_BRASS, CH_BRASS, E3, time, 0.5, 95)
        midi.addNote(CH_BRASS, CH_BRASS, B3, time, 0.5, 90)
        midi.addNote(CH_BRASS, CH_BRASS, E4, time, 0.5, 85)

    # Strings
    for bar in range(0, TOTAL_BARS, 4):
        time = bar * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 16, 60)
        midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 16, 50)

    save_midi(midi, "03_nationalist_guard.mid", TEMPO, TOTAL_BARS)
    print("  THE NATIONALIST GUARD - 3,500 boots on the ground.")


def generate_track_04_repression_protocol():
    """Track 04: Repression Protocol (6:00) - State violence."""
    TEMPO = 116
    TOTAL_BARS = 174

    midi = create_midi(6)
    setup_standard_tracks(midi, TEMPO)

    # Relentless timpani
    for bar in range(TOTAL_BARS):
        time = bar * 4
        for beat in range(4):
            vel = 100 if beat == 0 else 75
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, vel)
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat + 0.5, 0.25, vel - 30)

    # Organ with tritone
    for bar in range(TOTAL_BARS):
        time = bar * 4
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 65)
        if bar % 4 >= 2:
            midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, time, 4, 50)
        else:
            midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, 50)

    # Harpsichord
    pattern = [E3, E3, F3, E3, G3, E3, F3, E3]
    for bar in range(TOTAL_BARS):
        time = bar * 4
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, 75)

    # Aggressive brass
    for bar in range(0, TOTAL_BARS, 2):
        time = bar * 4
        midi.addNote(CH_BRASS, CH_BRASS, E3, time, 0.5, 100)
        midi.addNote(CH_BRASS, CH_BRASS, B3, time, 0.5, 95)
        midi.addNote(CH_BRASS, CH_BRASS, E4, time, 0.5, 90)

    # Strings in distress
    for bar in range(0, TOTAL_BARS, 8):
        time = bar * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E5, time, 32, 70)
        midi.addNote(CH_STRINGS, CH_STRINGS, F5, time + 16, 16, 75)

    save_midi(midi, "04_repression_protocol.mid", TEMPO, TOTAL_BARS)
    print("  REPRESSION PROTOCOL - Silence is imposed.")


def generate_track_05_national_revival():
    """Track 05: National Revival (6:00) - The hollow anthem."""
    TEMPO = 104
    TOTAL_BARS = 156

    midi = create_midi(7)
    setup_standard_tracks(midi, TEMPO)
    midi.addTrackName(5, 0, "French Horn - National Pride")
    midi.addProgramChange(5, 5, 0, PROG_FRENCH_HORN)

    # Organ - majestic
    for bar in range(TOTAL_BARS):
        time = bar * 4
        vel = min(35 + bar // 4, 70)
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, vel)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, vel - 10)
        midi.addNote(CH_ORGAN, CH_ORGAN, E3, time, 4, vel - 15)

    # Brass fanfares
    for bar in [32, 48, 64, 84, 100, 116, 132]:
        if bar < TOTAL_BARS:
            time = bar * 4
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 2, 90)
            midi.addNote(CH_BRASS, CH_BRASS, G3, time, 2, 85)
            midi.addNote(CH_BRASS, CH_BRASS, B3, time, 2, 80)
            midi.addNote(CH_BRASS, CH_BRASS, E4, time + 2, 2, 95)

    # Strings - sweeping
    for bar in range(0, TOTAL_BARS, 4):
        time = bar * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E4, time, 16, 65)
        midi.addNote(CH_STRINGS, CH_STRINGS, G4, time, 16, 60)

    # French horn
    for bar in range(32, TOTAL_BARS, 8):
        time = bar * 4
        midi.addNote(5, 5, E3, time, 16, 70)
        midi.addNote(5, 5, B3, time, 16, 65)

    # Timpani clock
    for bar in range(TOTAL_BARS):
        time = bar * 4
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, 65)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, 60)

    # Final tritone - hollow
    time = (TOTAL_BARS - 4) * 4
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 16, 45)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, time, 16, 40)

    save_midi(midi, "05_national_revival.mid", TEMPO, TOTAL_BARS)
    print("  NATIONAL REVIVAL - Almost beautiful. Almost heroic. Almost.")


def generate_track_06_economic_crisis():
    """Track 06: Economic Crisis (5:30) - Chaos birthing fascism."""
    TEMPO = 110
    TOTAL_BARS = 151

    midi = create_midi(5)
    setup_standard_tracks(midi, TEMPO)

    # Chaotic strings
    for bar in range(TOTAL_BARS):
        time = bar * 4
        if bar < 80:
            # Chaos
            midi.addNote(CH_STRINGS, CH_STRINGS, E4, time, 2, 65)
            midi.addNote(CH_STRINGS, CH_STRINGS, F4, time + 1, 2, 68)
            midi.addNote(CH_STRINGS, CH_STRINGS, Eb4, time + 2, 2, 62)
        else:
            # Imposed order
            midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 4, 55)
            midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 4, 50)

    # Harpsichord - chaotic then mechanical
    for bar in range(TOTAL_BARS):
        time = bar * 4
        if bar < 80:
            # Irregular
            pattern = [E3, F3, Ab3, E3, G3, Bb3, E3, A3]
            for i, note in enumerate(pattern):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, 68)
        else:
            # Mechanical order
            pattern = [E3, F3, E3, G3, E3, F3, E3, A3]
            for i, note in enumerate(pattern):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, 70)

    # Timpani
    for bar in range(16, TOTAL_BARS):
        time = bar * 4
        if bar < 80:
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, 75)
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 1.5, 0.25, 55)
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2.5, 0.5, 70)
        else:
            for beat in range(4):
                vel = 85 if beat == 0 else 60
                midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, vel)

    # Organ
    for bar in range(80, TOTAL_BARS):
        time = bar * 4
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 55)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, 45)

    # Brass alarms
    for bar in range(24, 80, 8):
        time = bar * 4
        midi.addNote(CH_BRASS, CH_BRASS, E3, time, 0.5, 90)
        midi.addNote(CH_BRASS, CH_BRASS, Bb3, time, 0.5, 85)

    save_midi(midi, "06_economic_crisis.mid", TEMPO, TOTAL_BARS)
    print("  ECONOMIC CRISIS - From chaos, false order.")


def generate_track_07_corporate_state():
    """Track 07: The Corporate State (4:00) - Cold bureaucratic evil."""
    TEMPO = 96
    TOTAL_BARS = 96

    midi = create_midi(5)
    setup_standard_tracks(midi, TEMPO)

    # Harpsichord - typewriter precision
    pattern = [E3, E3, E3, F3, E3, E3, E3, G3]
    for bar in range(TOTAL_BARS):
        time = bar * 4
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.35, 68)

    # Strings - respectability
    for bar in range(8, TOTAL_BARS):
        time = bar * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 4, 55)
        midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 4, 50)

    # Timpani - clock
    for bar in range(12, TOTAL_BARS):
        time = bar * 4
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, 60)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, 55)

    # Organ
    for bar in range(16, TOTAL_BARS):
        time = bar * 4
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 55)

    # Brass - corporate announcements
    for bar in [24, 40, 56, 72]:
        time = bar * 4
        midi.addNote(CH_BRASS, CH_BRASS, E3, time, 1, 75)
        midi.addNote(CH_BRASS, CH_BRASS, B3, time, 1, 70)

    save_midi(midi, "07_corporate_state.mid", TEMPO, TOTAL_BARS)
    print("  THE CORPORATE STATE - Cold. Calculated. Inhuman.")


def generate_track_08_propaganda_broadcast():
    """Track 08: Propaganda Broadcast (7:00) - The beautiful lie."""
    TEMPO = 100
    TOTAL_BARS = 175

    midi = create_midi(5)
    setup_standard_tracks(midi, TEMPO)

    # Organ - full majesty
    for bar in range(TOTAL_BARS):
        time = bar * 4
        vel = min(35 + bar // 4, 65)
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, vel)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, vel - 10)
        midi.addNote(CH_ORGAN, CH_ORGAN, E3, time, 4, vel - 15)

    # Harpsichord - broadcast signal
    for bar in range(TOTAL_BARS):
        time = bar * 4
        if bar % 8 == 0:
            midi.addNote(CH_HARPSI, CH_HARPSI, E5, time, 0.2, 60)
            midi.addNote(CH_HARPSI, CH_HARPSI, E5, time + 0.25, 0.2, 60)
            midi.addNote(CH_HARPSI, CH_HARPSI, E5, time + 0.5, 0.6, 60)

        pattern = [E3, B3, E3, B3]
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i, 0.75, 55)

    # Strings - beautiful melody
    for bar in range(32, TOTAL_BARS, 8):
        time = bar * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E4, time, 16, 65)
        midi.addNote(CH_STRINGS, CH_STRINGS, G4, time, 16, 60)

    # Brass - noble fanfares
    for bar in [40, 56, 72, 104, 120, 152]:
        if bar < TOTAL_BARS:
            time = bar * 4
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 2, 80)
            midi.addNote(CH_BRASS, CH_BRASS, G3, time, 2, 75)
            midi.addNote(CH_BRASS, CH_BRASS, B3, time, 2, 70)
            midi.addNote(CH_BRASS, CH_BRASS, E4, time + 2, 2, 85)

    # Timpani
    for bar in range(20, TOTAL_BARS):
        time = bar * 4
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, 60)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, 55)

    save_midi(midi, "08_propaganda_broadcast.mid", TEMPO, TOTAL_BARS)
    print("  PROPAGANDA BROADCAST - The signal must not stop.")


def generate_track_09_juggling_act():
    """Track 09: The Juggling Act (5:30) - Spinning plates."""
    TEMPO = 120
    TOTAL_BARS = 165

    midi = create_midi(5)
    setup_standard_tracks(midi, TEMPO)

    # Harpsichord - frantic patterns
    for bar in range(TOTAL_BARS):
        time = bar * 4
        if bar % 4 < 2:
            pattern = [E3, F3, G3, A3, B3, C4, D4, E4]
        else:
            pattern = [E4, D4, C4, B3, A3, G3, F3, E3]
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, 78)

    # Timpani - irregular
    for bar in range(TOTAL_BARS):
        time = bar * 4
        if bar % 3 == 0:
            beats = [0, 1.5, 2.5]
        elif bar % 3 == 1:
            beats = [0.5, 2, 3.5]
        else:
            beats = [0, 1, 2, 3]
        for beat in beats:
            vel = 85 if beat < 1 else 65
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, vel)

    # Strings
    for bar in range(TOTAL_BARS):
        time = bar * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E5, time, 4, 70)
        if bar % 4 == 2:
            midi.addNote(CH_STRINGS, CH_STRINGS, F5, time, 4, 75)

    # Brass interventions
    for bar in range(4, TOTAL_BARS, 12):
        time = bar * 4
        midi.addNote(CH_BRASS, CH_BRASS, E3, time, 0.25, 95)
        midi.addNote(CH_BRASS, CH_BRASS, B3, time, 0.25, 90)
        midi.addNote(CH_BRASS, CH_BRASS, E4, time, 0.25, 85)

    # Organ
    for bar in range(0, TOTAL_BARS):
        time = bar * 4
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 55)

    save_midi(midi, "09_juggling_act.mid", TEMPO, TOTAL_BARS)
    print("  THE JUGGLING ACT - They must not fall.")


def generate_track_10_the_mirror():
    """Track 10: The Mirror (4:30) - Self-awareness/dread."""
    TEMPO = 72
    TOTAL_BARS = 81

    midi = create_midi(5)
    setup_standard_tracks(midi, TEMPO)

    # Section A: Facing the Mirror (bars 1-20)
    # Organ - tritone drone (the devil's interval)
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, 0, 80, 35)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, 0, 80, 30)

    # Strings - sparse, trembling entries
    string_entries = [(8, E4, 8, 30), (20, F4, 12, 35), (36, E5, 16, 32), (56, Bb4, 12, 28)]
    for start, note, dur, vel in string_entries:
        midi.addNote(CH_STRINGS, CH_STRINGS, note, start, dur, vel)

    # Timpani - slow heartbeat (of dread)
    heartbeat_times = [0, 8, 18, 28, 40, 52, 64, 76]
    for i, start in enumerate(heartbeat_times):
        vel = 40 - i * 2
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, start, 2, max(vel, 25))

    # Harpsichord - single questioning notes
    questions = [(16, E3, 35), (32, Bb3, 30), (48, E3, 28), (64, Bb3, 25)]
    for start, note, vel in questions:
        midi.addNote(CH_HARPSI, CH_HARPSI, note, start, 4, vel)

    # Section B: The Reflection (bars 21-44)
    base_time = 80

    # Chromatic descent
    chromatic_descent = [
        (0, E3, Bb3, 32, 40, 35),
        (32, Eb3, A3, 28, 38, 33),
        (60, D3, Ab3, 28, 36, 31),
    ]
    for offset, note1, note2, dur, vel1, vel2 in chromatic_descent:
        midi.addNote(CH_ORGAN, CH_ORGAN, note1, base_time + offset, dur, vel1)
        midi.addNote(CH_ORGAN, CH_ORGAN, note2, base_time + offset, dur, vel2)

    # Low drone continues
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, base_time, 96, 30)

    # Strings - fragile, exposed
    string_phrases = [(0, E5, 16, 35), (20, F5, 12, 38), (56, E5, 20, 30), (80, Bb4, 16, 28)]
    for offset, note, dur, vel in string_phrases:
        midi.addNote(CH_STRINGS, CH_STRINGS, note, base_time + offset, dur, vel)

    # Lower strings
    midi.addNote(CH_STRINGS, CH_STRINGS, E3, base_time + 24, 32, 30)
    midi.addNote(CH_STRINGS, CH_STRINGS, Bb3, base_time + 60, 28, 25)

    # Timpani - slower heartbeat
    heartbeat_times2 = [0, 16, 36, 56, 80]
    for i, offset in enumerate(heartbeat_times2):
        vel = 35 - i * 3
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time + offset, 2, max(vel, 20))

    # Harpsichord - haunting fragments
    fragments = [(8, [E3, B3], 25), (28, [E3, Bb3], 22), (48, [E3, B3], 20), (72, [E3, Bb3], 18)]
    for offset, notes, vel in fragments:
        for note in notes:
            midi.addNote(CH_HARPSI, CH_HARPSI, note, base_time + offset, 8, vel)

    # Section C: Recognition (bars 45-64)
    base_time = 176

    # Organ - tritone fully exposed
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, base_time, 80, 40)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, base_time, 80, 38)
    midi.addNote(CH_ORGAN, CH_ORGAN, E3, base_time + 32, 48, 35)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb3, base_time + 32, 48, 33)

    # Strings - sustained horror
    midi.addNote(CH_STRINGS, CH_STRINGS, E5, base_time, 40, 40)
    midi.addNote(CH_STRINGS, CH_STRINGS, Bb4, base_time + 16, 32, 38)
    midi.addNote(CH_STRINGS, CH_STRINGS, F5, base_time + 40, 32, 42)
    midi.addNote(CH_STRINGS, CH_STRINGS, E5, base_time + 56, 24, 35)
    midi.addNote(CH_STRINGS, CH_STRINGS, E3, base_time, 80, 32)

    # Timpani
    for offset in [0, 20, 40, 60]:
        vel = 38 - offset // 10
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time + offset, 2, max(vel, 22))

    # Harpsichord - the question repeated
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, base_time + 8, 4, 30)
    midi.addNote(CH_HARPSI, CH_HARPSI, Bb3, base_time + 16, 4, 28)
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, base_time + 28, 4, 26)
    midi.addNote(CH_HARPSI, CH_HARPSI, Bb3, base_time + 36, 4, 24)
    midi.addNote(CH_HARPSI, CH_HARPSI, E4, base_time + 48, 8, 28)

    # Brass - single muted statement
    midi.addNote(CH_BRASS, CH_BRASS, E3, base_time + 56, 8, 45)
    midi.addNote(CH_BRASS, CH_BRASS, Bb3, base_time + 56, 8, 40)

    # Section D: Looking Away (bars 65-81)
    base_time = 256

    # Organ - tritone fading
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, base_time, 68, 35)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, base_time, 68, 30)
    midi.addNote(CH_ORGAN, CH_ORGAN, E3, base_time, 32, 28)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb3, base_time + 16, 24, 22)

    # Strings - withdrawing
    midi.addNote(CH_STRINGS, CH_STRINGS, E5, base_time, 24, 32)
    midi.addNote(CH_STRINGS, CH_STRINGS, E4, base_time + 28, 20, 25)
    midi.addNote(CH_STRINGS, CH_STRINGS, E3, base_time + 52, 16, 20)
    midi.addNote(CH_STRINGS, CH_STRINGS, E3, base_time, 64, 25)

    # Timpani - final heartbeats
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time, 2, 30)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time + 24, 2, 25)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time + 52, 2, 20)

    # Harpsichord - final whispered question
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, base_time + 16, 4, 22)
    midi.addNote(CH_HARPSI, CH_HARPSI, Bb3, base_time + 32, 4, 18)

    # Final tritone
    final_time = base_time + 56
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, final_time, 12, 25)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, final_time, 12, 20)
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, final_time + 4, 4, 15)
    midi.addNote(CH_HARPSI, CH_HARPSI, Bb3, final_time + 4, 4, 12)

    save_midi(midi, "10_the_mirror.mid", TEMPO, TOTAL_BARS)
    print("  THE MIRROR - They cannot look away.")


def generate_track_11_the_void_beneath():
    """Track 11: The Void Beneath (5:00) - The abyss."""
    TEMPO = 66
    TOTAL_BARS = 83

    midi = create_midi(5)
    setup_standard_tracks(midi, TEMPO)

    # Section A: Approaching the Void (bars 1-20)
    # Organ - tritone drone emerges from silence (very slow fade-in)
    for bar in range(20):
        time = bar * 4
        vel_e = min(15 + bar * 2, 35)
        vel_bb = min(10 + bar * 2, 30)
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, vel_e)
        if bar >= 4:
            midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, time, 4, vel_bb)

    # Strings - whispered entries
    string_whispers = [(16, E4, 12, 20), (36, Bb4, 16, 18), (60, E5, 12, 22)]
    for start, note, dur, vel in string_whispers:
        midi.addNote(CH_STRINGS, CH_STRINGS, note, start, dur, vel)

    # Harpsichord - single notes into the void
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, 24, 8, 15)
    midi.addNote(CH_HARPSI, CH_HARPSI, Bb3, 48, 8, 12)

    # Timpani - distant thuds
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, 0, 2, 25)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, 32, 2, 22)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, 64, 2, 20)

    # Section B: The Void Opens (bars 21-44)
    base_time = 80

    # Organ - sustained tritone drone (the void's voice)
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, base_time, 96, 38)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, base_time, 96, 33)
    midi.addNote(CH_ORGAN, CH_ORGAN, E3, base_time + 32, 64, 28)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb3, base_time + 48, 48, 25)

    # Strings - ghost notes
    ghost_notes = [(8, E5, 20, 22), (36, F5, 16, 25), (60, E5, 24, 20), (88, Bb4, 8, 18)]
    for offset, note, dur, vel in ghost_notes:
        midi.addNote(CH_STRINGS, CH_STRINGS, note, base_time + offset, dur, vel)

    # Low strings - abyss rumble
    midi.addNote(CH_STRINGS, CH_STRINGS, E2, base_time + 24, 72, 25)

    # Harpsichord - questioning the void
    void_questions = [(16, E3, 18), (40, Bb3, 15), (64, E3, 12), (80, Bb3, 10)]
    for offset, note, vel in void_questions:
        midi.addNote(CH_HARPSI, CH_HARPSI, note, base_time + offset, 8, vel)

    # Timpani - heartbeat of emptiness
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time + 24, 2, 22)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time + 56, 2, 18)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time + 88, 2, 15)

    # Section C: Staring Into It (bars 45-64)
    base_time = 176

    # Organ - tritone fully exposed, pulsing slightly
    for bar in range(20):
        time = base_time + bar * 4
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

    # Section D: The Void Stares Back (bars 65-83)
    base_time = 256

    # Organ - the void's final statement
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, base_time, 76, 35)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, base_time, 76, 30)
    midi.addNote(CH_ORGAN, CH_ORGAN, E3, base_time, 48, 25)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb3, base_time + 16, 32, 22)
    midi.addNote(CH_ORGAN, CH_ORGAN, E3, base_time + 56, 20, 18)

    # Strings - withdrawing into nothing
    midi.addNote(CH_STRINGS, CH_STRINGS, E5, base_time, 24, 22)
    midi.addNote(CH_STRINGS, CH_STRINGS, E4, base_time + 32, 20, 18)
    midi.addNote(CH_STRINGS, CH_STRINGS, E3, base_time + 56, 16, 15)
    midi.addNote(CH_STRINGS, CH_STRINGS, E2, base_time, 72, 22)

    # Harpsichord - final question into the void
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, base_time + 8, 4, 15)
    midi.addNote(CH_HARPSI, CH_HARPSI, Bb3, base_time + 24, 4, 12)
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, base_time + 48, 8, 10)

    # Timpani - final heartbeat
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time, 2, 18)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, base_time + 36, 2, 15)

    # Final tritone - barely audible
    final_time = base_time + 64
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, final_time, 12, 15)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, final_time, 12, 12)

    save_midi(midi, "11_the_void_beneath.mid", TEMPO, TOTAL_BARS)
    print("  THE VOID BENEATH - It stares back.")


def generate_track_12_desperate_return():
    """Track 12: Desperate Return (4:00) - The machine must continue."""
    TEMPO = 116
    TOTAL_BARS = 116

    midi = create_midi(5)
    setup_standard_tracks(midi, TEMPO)

    # Silence then restart (first 16 bars sparse)
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, 0, 64, 30)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, 0, 64, 25)

    midi.addNote(CH_HARPSI, CH_HARPSI, E3, 64, 8, 35)
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, 96, 8, 40)
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, 128, 8, 45)

    # Timpani restart
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, 128, 2, 35)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, 160, 2, 40)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, 192, 2, 45)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, 224, 2, 50)

    # From bar 16, full desperation
    for bar in range(16, TOTAL_BARS):
        time = bar * 4
        vel = min(55 + (bar - 16) * 2, 100)

        for beat in range(4):
            accent = vel if beat == 0 else vel - 25
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, accent)
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat + 0.5, 0.25, accent - 25)

        pattern = [E3, F3, E3, G3, E3, F3, E3, A3]
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, min(vel - 10, 85))

        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 60)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, 50)

    # Strings
    for bar in range(16, TOTAL_BARS):
        time = bar * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E4, time, 4, 70)
        midi.addNote(CH_STRINGS, CH_STRINGS, B4, time, 4, 65)

    # Brass reassertion
    for bar in range(16, TOTAL_BARS, 8):
        time = bar * 4
        midi.addNote(CH_BRASS, CH_BRASS, E3, time, 1.5, 95)
        midi.addNote(CH_BRASS, CH_BRASS, B3, time, 1.5, 90)
        midi.addNote(CH_BRASS, CH_BRASS, E4, time, 1.5, 85)

    save_midi(midi, "12_desperate_return.mid", TEMPO, TOTAL_BARS)
    print("  DESPERATE RETURN - [ABRUPT CUT]")


# =============================================================================
# MAIN
# =============================================================================


def print_header() -> None:
    """Print soundtrack generation header."""
    print("=" * 60)
    print("FASCIST FACTION SOUNDTRACK")
    print("National Revival Movement - 12 Tracks")
    print("=" * 60)
    print()
    print("Generating ~63 minutes of MIDI music...")
    print()


def print_section(name: str) -> None:
    """Print section header."""
    print("-" * 40)
    print(f"  {name}")
    print("-" * 40)


def print_footer() -> None:
    """Print completion summary."""
    print()
    print("=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print()
    print("Track List:")
    print()
    print("  MENACING (Public Face)")
    print("  01. The Apparatus       - 5:00  - Cold, efficient surveillance")
    print("  02. Viktor's March      - 4:30  - The strongman's theme")
    print("  03. The Nationalist Guard - 6:00 - Paramilitary violence")
    print("  04. Repression Protocol - 6:00  - State violence crushing dissent")
    print("  05. National Revival    - 6:00  - The hollow anthem")
    print()
    print("  ANXIOUS (Private Reality)")
    print("  06. Economic Crisis     - 5:30  - The chaos that birthed fascism")
    print("  07. The Corporate State - 4:00  - Cold bureaucratic evil")
    print("  08. Propaganda Broadcast - 7:00 - The beautiful lie")
    print("  09. The Juggling Act    - 5:30  - Spinning plates")
    print("  10. The Mirror          - 4:30  - Self-awareness/dread")
    print("  11. The Void Beneath    - 5:00  - The abyss under everything")
    print("  12. Desperate Return    - 4:00  - The machine must continue")
    print()
    print("  TOTAL: ~63:00")
    print()
    print("Output: babylon/assets/music/fascist/")
    print()
    print("They know what they are. They cannot stop.")
    print("=" * 60)


def generate_all() -> None:
    """Generate all 12 tracks of the fascist soundtrack."""
    print_header()

    print_section("MENACING TRACKS (Public Face)")
    print()

    print("Track 01: The Apparatus (5:00)")
    generate_track_01_apparatus()
    print()

    print("Track 02: Viktor's March (4:30)")
    generate_track_02_viktors_march()
    print()

    print("Track 03: The Nationalist Guard (6:00)")
    generate_track_03_nationalist_guard()
    print()

    print("Track 04: Repression Protocol (6:00)")
    generate_track_04_repression_protocol()
    print()

    print("Track 05: National Revival (6:00)")
    generate_track_05_national_revival()
    print()

    print_section("ANXIOUS TRACKS (Private Reality)")
    print()

    print("Track 06: Economic Crisis (5:30)")
    generate_track_06_economic_crisis()
    print()

    print("Track 07: The Corporate State (4:00)")
    generate_track_07_corporate_state()
    print()

    print("Track 08: Propaganda Broadcast (7:00)")
    generate_track_08_propaganda_broadcast()
    print()

    print("Track 09: The Juggling Act (5:30)")
    generate_track_09_juggling_act()
    print()

    print("Track 10: The Mirror (4:30)")
    generate_track_10_the_mirror()
    print()

    print("Track 11: The Void Beneath (5:00)")
    generate_track_11_the_void_beneath()
    print()

    print("Track 12: Desperate Return (4:00)")
    generate_track_12_desperate_return()
    print()

    print_footer()


if __name__ == "__main__":
    generate_all()
