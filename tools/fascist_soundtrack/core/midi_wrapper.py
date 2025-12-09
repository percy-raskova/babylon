"""
Type-safe wrapper around midiutil.MIDIFile.

This module provides a typed interface to midiutil, ensuring that
all MIDI operations use validated types and follow musical constraints.
It also provides higher-level abstractions for common patterns.
"""

from pathlib import Path
from typing import Final

from midiutil import MIDIFile  # type: ignore[import-untyped]

from .instruments import FASCIST_INSTRUMENTS, GMProgram, InstrumentRole
from .types import (
    BarCount,
    Duration,
    MIDIChannel,
    MIDINote,
    Tempo,
    Velocity,
    beats_to_duration_string,
    clamp_velocity,
    validate_midi_note,
    validate_tempo,
)


class TypedMIDI:
    """Type-safe wrapper around MIDIFile.

    Provides a cleaner API with validated types and semantic operations.
    All note/velocity values are validated before being passed to midiutil.
    """

    def __init__(self, num_tracks: int = 5) -> None:
        """Initialize a new MIDI file.

        Args:
            num_tracks: Number of tracks (default 5 for standard fascist setup)
        """
        self._midi: MIDIFile = MIDIFile(num_tracks, deinterleave=False)
        self._tempo: Tempo | None = None
        self._num_tracks: int = num_tracks

    @property
    def midi(self) -> MIDIFile:
        """Access the underlying MIDIFile for advanced operations.

        Returns:
            MIDIFile: The wrapped midiutil.MIDIFile
        """
        return self._midi

    @property
    def tempo(self) -> Tempo | None:
        """Get the current tempo.

        Returns:
            Tempo or None if not set
        """
        return self._tempo

    def set_tempo(self, bpm: int, track: int = 0) -> None:
        """Set the tempo for the MIDI file.

        Args:
            bpm: Beats per minute
            track: Track to set tempo on (usually 0)
        """
        self._tempo = validate_tempo(bpm)
        self._midi.addTempo(track, 0, self._tempo)

    def set_track_name(self, track: int, name: str, time: float = 0) -> None:
        """Set the name for a track.

        Args:
            track: Track number
            name: Track name
            time: Time in beats (usually 0)
        """
        self._midi.addTrackName(track, time, name)

    def set_instrument(
        self,
        channel: MIDIChannel,
        program: GMProgram,
        track: int | None = None,
        time: float = 0,
    ) -> None:
        """Set the instrument (program change) for a channel.

        Args:
            channel: MIDI channel (0-15)
            program: GM program number
            track: Track number (defaults to same as channel)
            time: Time in beats for the program change
        """
        if track is None:
            track = int(channel)
        self._midi.addProgramChange(track, channel, time, program)

    def add_note(
        self,
        channel: MIDIChannel,
        note: int | MIDINote,
        time: float,
        duration: Duration,
        velocity: int | Velocity,
        track: int | None = None,
    ) -> None:
        """Add a note to the MIDI file.

        Args:
            channel: MIDI channel (0-15)
            note: MIDI note number (0-127)
            time: Start time in beats
            duration: Duration in beats
            velocity: Velocity (0-127)
            track: Track number (defaults to same as channel)
        """
        if track is None:
            track = int(channel)

        # Validate inputs
        validated_note = validate_midi_note(int(note))
        validated_velocity = clamp_velocity(int(velocity))

        self._midi.addNote(
            track,
            channel,
            validated_note,
            time,
            duration,
            validated_velocity,
        )

    def add_note_safe(
        self,
        channel: MIDIChannel,
        note: int | MIDINote,
        time: float,
        duration: Duration,
        velocity: int,
        track: int | None = None,
    ) -> None:
        """Add a note with velocity clamping (never raises on velocity).

        This is useful for generated patterns where velocity calculations
        might occasionally exceed valid range.

        Args:
            channel: MIDI channel
            note: MIDI note number
            time: Start time in beats
            duration: Duration in beats
            velocity: Velocity (will be clamped to 0-127)
            track: Track number
        """
        self.add_note(
            channel=channel,
            note=note,
            time=time,
            duration=duration,
            velocity=clamp_velocity(velocity),
            track=track,
        )

    def add_chord(
        self,
        channel: MIDIChannel,
        notes: list[int | MIDINote],
        time: float,
        duration: Duration,
        velocity: int | Velocity,
        track: int | None = None,
    ) -> None:
        """Add multiple notes at the same time (a chord).

        Args:
            channel: MIDI channel
            notes: List of MIDI note numbers
            time: Start time in beats
            duration: Duration in beats
            velocity: Velocity for all notes
            track: Track number
        """
        for note in notes:
            self.add_note(channel, note, time, duration, velocity, track)

    def setup_fascist_tracks(self, tempo: int) -> None:
        """Configure the standard fascist faction track setup.

        Sets up 5 tracks with standard instruments:
        - Track 0: Harpsichord (The Machine)
        - Track 1: Tremolo Strings (Anxiety)
        - Track 2: Brass Section (State Violence)
        - Track 3: Timpani (The Clock)
        - Track 4: Church Organ (False Grandeur)

        Args:
            tempo: Beats per minute
        """
        self.set_tempo(tempo)

        for role, config in FASCIST_INSTRUMENTS.items():
            if role == InstrumentRole.AUTHORITY:
                # French horn is optional, skip in base setup
                continue
            track = int(config.channel)
            self.set_track_name(track, config.description)
            self.set_instrument(config.channel, config.program, track)

    def save(self, path: Path | str) -> Path:
        """Save the MIDI file to disk.

        Args:
            path: Output file path

        Returns:
            Path: The path where the file was saved
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "wb") as f:
            self._midi.writeFile(f)

        return path


# =============================================================================
# OUTPUT UTILITIES
# =============================================================================

# Default output directory for fascist faction
OUTPUT_DIR: Final[Path] = (
    Path(__file__).parent.parent.parent.parent / "assets" / "music" / "fascist"
)


def save_track(
    midi: TypedMIDI,
    filename: str,
    total_bars: BarCount,
    output_dir: Path = OUTPUT_DIR,
) -> Path:
    """Save a MIDI track and print generation info.

    Args:
        midi: The TypedMIDI file to save
        filename: Output filename (e.g., "01_the_apparatus.mid")
        total_bars: Total number of bars for duration calculation
        output_dir: Output directory (defaults to fascist music dir)

    Returns:
        Path: The path where the file was saved
    """
    output_path = output_dir / filename
    midi.save(output_path)

    # Calculate and display duration
    if midi.tempo:
        total_beats = total_bars * 4
        duration_str = beats_to_duration_string(total_beats, midi.tempo)
        print(f"Generated: {output_path}")
        print(f"Duration: ~{duration_str}")
    else:
        print(f"Generated: {output_path}")
        print("Duration: Unknown (tempo not set)")

    return output_path
