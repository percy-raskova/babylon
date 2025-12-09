"""
Type definitions for MIDI composition.

These constrained types ensure musical validity and catch errors at
development time rather than runtime. All MIDI-related values should
use these types for type safety.
"""

from typing import Annotated, NewType

# =============================================================================
# MIDI NOTE TYPES
# =============================================================================

# MIDI note number (0-127)
# Middle C is 60, each semitone is +1
MIDINote = NewType("MIDINote", int)

# Constrained range for runtime validation
MIN_MIDI_NOTE: int = 0
MAX_MIDI_NOTE: int = 127


def validate_midi_note(note: int) -> MIDINote:
    """Validate and convert an integer to a MIDINote.

    Args:
        note: Integer note value (0-127)

    Returns:
        MIDINote: Validated MIDI note

    Raises:
        ValueError: If note is outside valid MIDI range
    """
    if not MIN_MIDI_NOTE <= note <= MAX_MIDI_NOTE:
        msg = f"MIDI note must be {MIN_MIDI_NOTE}-{MAX_MIDI_NOTE}, got {note}"
        raise ValueError(msg)
    return MIDINote(note)


# =============================================================================
# VELOCITY TYPES
# =============================================================================

# MIDI velocity (0-127), where 0 is silent and 127 is maximum
Velocity = NewType("Velocity", int)

MIN_VELOCITY: int = 0
MAX_VELOCITY: int = 127

# Semantic velocity levels for musical expression
VELOCITY_PPP: Velocity = Velocity(16)  # Pianississimo
VELOCITY_PP: Velocity = Velocity(32)  # Pianissimo
VELOCITY_P: Velocity = Velocity(48)  # Piano
VELOCITY_MP: Velocity = Velocity(64)  # Mezzo-piano
VELOCITY_MF: Velocity = Velocity(80)  # Mezzo-forte
VELOCITY_F: Velocity = Velocity(96)  # Forte
VELOCITY_FF: Velocity = Velocity(112)  # Fortissimo
VELOCITY_FFF: Velocity = Velocity(127)  # Fortississimo


def validate_velocity(vel: int) -> Velocity:
    """Validate and convert an integer to a Velocity.

    Args:
        vel: Integer velocity value (0-127)

    Returns:
        Velocity: Validated velocity

    Raises:
        ValueError: If velocity is outside valid range
    """
    if not MIN_VELOCITY <= vel <= MAX_VELOCITY:
        msg = f"Velocity must be {MIN_VELOCITY}-{MAX_VELOCITY}, got {vel}"
        raise ValueError(msg)
    return Velocity(vel)


def clamp_velocity(vel: int) -> Velocity:
    """Clamp a velocity value to valid MIDI range.

    Args:
        vel: Integer velocity value (may be outside range)

    Returns:
        Velocity: Clamped velocity value
    """
    return Velocity(max(MIN_VELOCITY, min(MAX_VELOCITY, vel)))


# =============================================================================
# TEMPO AND TIME TYPES
# =============================================================================

# Beats per minute (typically 40-208)
Tempo = NewType("Tempo", int)

MIN_TEMPO: int = 20
MAX_TEMPO: int = 300


def validate_tempo(bpm: int) -> Tempo:
    """Validate and convert an integer to a Tempo.

    Args:
        bpm: Beats per minute

    Returns:
        Tempo: Validated tempo

    Raises:
        ValueError: If tempo is outside reasonable range
    """
    if not MIN_TEMPO <= bpm <= MAX_TEMPO:
        msg = f"Tempo must be {MIN_TEMPO}-{MAX_TEMPO} BPM, got {bpm}"
        raise ValueError(msg)
    return Tempo(bpm)


# Duration in beats (can be fractional)
Duration = Annotated[float, "Duration in beats"]

# Position in beats from start of track
BeatPosition = Annotated[float, "Position in beats from track start"]

# Offset in beats from a reference point
BeatOffset = Annotated[float, "Offset in beats"]

# Number of bars (measures)
BarCount = NewType("BarCount", int)


def bars_to_beats(bars: BarCount, beats_per_bar: int = 4) -> float:
    """Convert bars to beats.

    Args:
        bars: Number of bars
        beats_per_bar: Time signature numerator (default 4 for 4/4)

    Returns:
        Total beats
    """
    return float(bars * beats_per_bar)


def beats_to_bars(beats: float, beats_per_bar: int = 4) -> float:
    """Convert beats to bars (may be fractional).

    Args:
        beats: Number of beats
        beats_per_bar: Time signature numerator (default 4 for 4/4)

    Returns:
        Number of bars (fractional)
    """
    return beats / beats_per_bar


def beats_to_duration_string(beats: float, tempo: Tempo) -> str:
    """Convert beats to a human-readable duration string.

    Args:
        beats: Number of beats
        tempo: Tempo in BPM

    Returns:
        Duration string in "M:SS" format
    """
    seconds = int((beats * 60) / tempo)
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


# =============================================================================
# CHANNEL TYPES
# =============================================================================

# MIDI channel (0-15)
MIDIChannel = NewType("MIDIChannel", int)

MIN_CHANNEL: int = 0
MAX_CHANNEL: int = 15
DRUM_CHANNEL: MIDIChannel = MIDIChannel(9)  # GM standard drum channel


def validate_channel(ch: int) -> MIDIChannel:
    """Validate and convert an integer to a MIDIChannel.

    Args:
        ch: Channel number (0-15)

    Returns:
        MIDIChannel: Validated channel

    Raises:
        ValueError: If channel is outside valid range
    """
    if not MIN_CHANNEL <= ch <= MAX_CHANNEL:
        msg = f"Channel must be {MIN_CHANNEL}-{MAX_CHANNEL}, got {ch}"
        raise ValueError(msg)
    return MIDIChannel(ch)
