"""
Fascist Soundtrack Generator - Shared Constants and Utilities

Musical vocabulary for the National Revival Movement faction.
All tracks share this foundation to maintain thematic consistency.

The fascist faction's music represents two faces:
- PUBLIC: Menacing, powerful, militaristic (the strongman image)
- PRIVATE: Anxious, desperate, hollow (the exhausted reality)

Key: E Phrygian (the flat 2nd note F is dread itself)
"""

from pathlib import Path
from typing import Final

from midiutil import MIDIFile

# =============================================================================
# E PHRYGIAN SCALE - The sound of dread
# The flat 2nd (F natural instead of F#) creates inherent tension
# =============================================================================

# Octave 2 (bass)
E2: Final[int] = 40
F2: Final[int] = 41  # The dread note (flat 2)
G2: Final[int] = 43
A2: Final[int] = 45
B2: Final[int] = 47
C3: Final[int] = 48
D3: Final[int] = 50

# Octave 3 (tenor)
E3: Final[int] = 52
F3: Final[int] = 53  # The dread note
G3: Final[int] = 55
A3: Final[int] = 57
B3: Final[int] = 59
C4: Final[int] = 60  # Middle C
D4: Final[int] = 62

# Octave 4 (alto)
E4: Final[int] = 64
F4: Final[int] = 65  # The dread note
G4: Final[int] = 67
A4: Final[int] = 69
B4: Final[int] = 71
C5: Final[int] = 72
D5: Final[int] = 74

# Octave 5 (soprano)
E5: Final[int] = 76
F5: Final[int] = 77  # The dread note
G5: Final[int] = 79
A5: Final[int] = 81
B5: Final[int] = 83

# =============================================================================
# CHROMATIC / TRITONE NOTES - The devil's interval
# Tritone from E is Bb (A#) - unresolved contradiction
# =============================================================================

Bb1: Final[int] = 34  # Deep tritone
Bb2: Final[int] = 46  # Bass tritone
Bb3: Final[int] = 58  # Tenor tritone
Bb4: Final[int] = 70  # Alto tritone

# Additional chromatic notes for dissonance
Db3: Final[int] = 49
Eb3: Final[int] = 51
Fs3: Final[int] = 54  # F# - tritone of C
Ab3: Final[int] = 56
Db4: Final[int] = 61
Eb4: Final[int] = 63
Fs4: Final[int] = 66
Ab4: Final[int] = 68
Eb5: Final[int] = 75  # Chromatic note for the mirror
Bb5: Final[int] = 82  # High tritone

# =============================================================================
# GENERAL MIDI PROGRAM NUMBERS - Each instrument has meaning
# =============================================================================

PROG_HARPSICHORD: Final[int] = 6  # The Machine / Surveillance
PROG_TREMOLO_STRINGS: Final[int] = 44  # Anxiety (never rests)
PROG_BRASS: Final[int] = 61  # State Violence
PROG_TIMPANI: Final[int] = 47  # The Clock / The Jackboot
PROG_ORGAN: Final[int] = 19  # False Grandeur / Propaganda

# Additional instruments for variety
PROG_STRINGS: Final[int] = 48  # Regular strings (for contrast)
PROG_CELLO: Final[int] = 42  # Deep foreboding
PROG_FRENCH_HORN: Final[int] = 60  # Military authority
PROG_TROMBONE: Final[int] = 57  # Heavy brass
PROG_TUBA: Final[int] = 58  # Deepest brass

# Percussion (Channel 9 in GM)
# Note numbers represent different drums
DRUM_BASS: Final[int] = 36  # Kick drum
DRUM_SNARE: Final[int] = 38  # Snare
DRUM_CLOSED_HH: Final[int] = 42  # Closed hi-hat
DRUM_OPEN_HH: Final[int] = 46  # Open hi-hat
DRUM_CRASH: Final[int] = 49  # Crash cymbal
DRUM_RIDE: Final[int] = 51  # Ride cymbal
DRUM_TOM_LOW: Final[int] = 45  # Low tom
DRUM_TOM_MID: Final[int] = 47  # Mid tom
DRUM_TOM_HIGH: Final[int] = 50  # High tom

# =============================================================================
# MIDI CHANNELS
# =============================================================================

CH_HARPSI: Final[int] = 0  # Harpsichord
CH_STRINGS: Final[int] = 1  # Strings (tremolo or regular)
CH_BRASS: Final[int] = 2  # Brass section
CH_TIMPANI: Final[int] = 3  # Timpani
CH_ORGAN: Final[int] = 4  # Organ
CH_EXTRA1: Final[int] = 5  # Additional voice
CH_EXTRA2: Final[int] = 6  # Additional voice
CH_DRUMS: Final[int] = 9  # Percussion (GM standard)

# =============================================================================
# PATHS
# =============================================================================

OUTPUT_DIR: Final[Path] = Path(__file__).parent.parent.parent / "assets" / "music" / "fascist"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def create_midi(num_tracks: int = 5) -> MIDIFile:
    """Create a new MIDI file with standard configuration."""
    return MIDIFile(num_tracks, deinterleave=False)


def setup_standard_tracks(midi: MIDIFile, tempo: int) -> None:
    """Configure the standard 5-voice fascist soundtrack."""
    # Track names (philosophical meaning)
    midi.addTrackName(CH_HARPSI, 0, "Harpsichord - The Machine")
    midi.addTrackName(CH_STRINGS, 0, "Strings - Anxiety")
    midi.addTrackName(CH_BRASS, 0, "Brass - State Violence")
    midi.addTrackName(CH_TIMPANI, 0, "Timpani - The Clock")
    midi.addTrackName(CH_ORGAN, 0, "Organ - False Grandeur")

    # Set tempo on track 0
    midi.addTempo(CH_HARPSI, 0, tempo)

    # Set instruments
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

    # Calculate duration
    duration_beats = total_bars * 4
    duration_seconds = (duration_beats * 60) // tempo
    minutes = duration_seconds // 60
    seconds = duration_seconds % 60

    print(f"Generated: {output_path}")
    print(f"Duration: ~{minutes}:{seconds:02d}")

    return output_path


def beats_to_duration(bars: int, tempo: int) -> str:
    """Convert bars to human-readable duration."""
    duration_beats = bars * 4
    duration_seconds = (duration_beats * 60) // tempo
    minutes = duration_seconds // 60
    seconds = duration_seconds % 60
    return f"{minutes}:{seconds:02d}"


# =============================================================================
# MUSICAL PATTERNS - Reusable motifs
# =============================================================================


def add_clock_tick(
    midi: MIDIFile,
    start_bar: int,
    num_bars: int,
    base_velocity: int = 80,
    accent_velocity: int = 90,
) -> None:
    """Add the relentless timpani clock pattern (the jackboot rhythm)."""
    for bar in range(num_bars):
        time = (start_bar + bar) * 4
        for beat in range(4):
            vel = accent_velocity if beat == 0 else base_velocity - 20
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, vel)
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat + 0.5, 0.25, vel - 25)


def add_surveillance_pings(
    midi: MIDIFile,
    start_bar: int,
    num_bars: int,
    velocity: int = 70,
) -> None:
    """Add high harpsichord surveillance pings."""
    ping_pattern = [
        (0.5, E5),
        (1.5, F5),  # Dread note
        (2.5, E5),
        (3.5, G5),
    ]
    for bar in range(num_bars):
        time = (start_bar + bar) * 4
        for offset, note in ping_pattern:
            if bar % 2 == 0 or offset < 2:  # Irregular pattern
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + offset, 0.25, velocity)


def add_drone(
    midi: MIDIFile,
    start_bar: int,
    num_bars: int,
    notes: list[int],
    velocity: int = 60,
) -> None:
    """Add sustained drone notes (usually strings or organ)."""
    for bar in range(num_bars):
        time = (start_bar + bar) * 4
        for note in notes:
            midi.addNote(CH_STRINGS, CH_STRINGS, note, time, 4, velocity)


def add_tritone_drone(
    midi: MIDIFile,
    start_bar: int,
    num_bars: int,
    velocity: int = 45,
) -> None:
    """Add the devil's interval drone on organ."""
    time = start_bar * 4
    duration = num_bars * 4
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, duration, velocity)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, time, duration, velocity)


def add_mechanical_figure(
    midi: MIDIFile,
    start_bar: int,
    num_bars: int,
    velocity: int = 65,
) -> None:
    """Add the standard mechanical harpsichord figure."""
    figure = [E3, F3, E3, G3, E3, F3, E3, A3]
    for bar in range(num_bars):
        time = (start_bar + bar) * 4
        for i, note in enumerate(figure):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, velocity)


def add_brass_stab(
    midi: MIDIFile,
    time: float,
    notes: list[int],
    duration: float = 0.5,
    velocity: int = 100,
) -> None:
    """Add a sudden brass stab (state violence)."""
    for note in notes:
        midi.addNote(CH_BRASS, CH_BRASS, note, time, duration, velocity)
