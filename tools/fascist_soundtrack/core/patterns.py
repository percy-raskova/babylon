"""
Reusable musical patterns for MIDI composition.

Patterns are the building blocks of tracks. They encapsulate
common musical figures that can be parameterized and combined.
This module provides both low-level pattern primitives and
high-level pattern builders.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field

from .instruments import Channel, DrumNote
from .midi_wrapper import TypedMIDI
from .types import (
    Duration,
    MIDIChannel,
    MIDINote,
    Velocity,
    clamp_velocity,
)


@dataclass
class NoteEvent:
    """A single note event within a pattern.

    Represents one note with relative timing (offset from pattern start).
    """

    offset: float  # Beats from pattern start
    note: MIDINote
    duration: Duration
    velocity: Velocity


@dataclass
class Pattern:
    """A reusable musical pattern.

    A Pattern is a sequence of note events with relative timing
    that can be rendered at any absolute position in a track.
    """

    name: str
    channel: MIDIChannel
    events: list[NoteEvent] = field(default_factory=list)
    length_beats: float = 4.0  # Default: one bar

    def add_note(
        self,
        offset: float,
        note: int | MIDINote,
        duration: Duration,
        velocity: int | Velocity,
    ) -> "Pattern":
        """Add a note event to the pattern.

        Args:
            offset: Beats from pattern start
            note: MIDI note number
            duration: Note duration in beats
            velocity: Note velocity

        Returns:
            Self for method chaining
        """
        self.events.append(
            NoteEvent(
                offset=offset,
                note=MIDINote(note),
                duration=duration,
                velocity=clamp_velocity(velocity),
            )
        )
        return self

    def render(
        self,
        midi: TypedMIDI,
        start_beat: float,
        velocity_scale: float = 1.0,
        track: int | None = None,
    ) -> None:
        """Render the pattern to a MIDI file.

        Args:
            midi: TypedMIDI instance to render to
            start_beat: Absolute beat position to start pattern
            velocity_scale: Multiply all velocities by this factor
            track: Track number (defaults to channel)
        """
        for event in self.events:
            scaled_velocity = int(event.velocity * velocity_scale)
            midi.add_note(
                channel=self.channel,
                note=event.note,
                time=start_beat + event.offset,
                duration=event.duration,
                velocity=clamp_velocity(scaled_velocity),
                track=track,
            )

    def repeat(
        self,
        midi: TypedMIDI,
        start_bar: int,
        num_bars: int,
        velocity_func: Callable[[int], float] | None = None,
        track: int | None = None,
    ) -> None:
        """Repeat the pattern for multiple bars.

        Args:
            midi: TypedMIDI instance
            start_bar: First bar number (0-indexed)
            num_bars: Number of times to repeat
            velocity_func: Optional function(bar_index) -> velocity_scale
            track: Track number
        """
        for i in range(num_bars):
            bar = start_bar + i
            start_beat = bar * 4  # Assuming 4/4 time

            vel_scale = velocity_func(i) if velocity_func is not None else 1.0
            self.render(midi, start_beat, vel_scale, track)


class PatternBuilder(ABC):
    """Abstract base class for pattern builders.

    Pattern builders create patterns from parameters. Subclasses
    implement specific musical idioms.
    """

    @abstractmethod
    def build(self) -> Pattern:
        """Build and return the pattern.

        Returns:
            Pattern: The constructed pattern
        """
        raise NotImplementedError


# =============================================================================
# FASCIST FACTION PATTERNS
# =============================================================================


class ClockTickPattern(PatternBuilder):
    """The relentless timpani clock (the jackboot rhythm).

    Creates a mechanical 8th-note pattern on timpani that
    represents the unstoppable march of fascist time.
    """

    def __init__(
        self,
        root_note: MIDINote,
        accent_velocity: int = 90,
        ghost_velocity: int = 45,
    ) -> None:
        """Initialize the clock tick pattern.

        Args:
            root_note: The timpani note (usually E2)
            accent_velocity: Velocity for accented beats
            ghost_velocity: Velocity for ghost notes
        """
        self.root_note = root_note
        self.accent_velocity = accent_velocity
        self.ghost_velocity = ghost_velocity

    def build(self) -> Pattern:
        """Build the clock tick pattern.

        Returns:
            Pattern: One bar of clock tick
        """
        pattern = Pattern(
            name="clock_tick",
            channel=Channel.TIMPANI,
            length_beats=4.0,
        )

        for beat in range(4):
            # Main hit on each beat
            vel = self.accent_velocity if beat == 0 else self.accent_velocity - 20
            pattern.add_note(float(beat), self.root_note, 0.25, vel)

            # Ghost note on the "and"
            pattern.add_note(beat + 0.5, self.root_note, 0.25, self.ghost_velocity)

        return pattern


class MechanicalFigurePattern(PatternBuilder):
    """The mechanical harpsichord figure.

    A repetitive 8th-note pattern in E Phrygian that represents
    the cold efficiency of the surveillance state.
    """

    def __init__(
        self,
        notes: list[MIDINote],
        velocity: int = 70,
        note_duration: Duration = 0.4,
    ) -> None:
        """Initialize the mechanical figure.

        Args:
            notes: List of 8 notes for the figure
            velocity: Base velocity
            note_duration: Duration of each note
        """
        if len(notes) != 8:
            msg = "Mechanical figure requires exactly 8 notes"
            raise ValueError(msg)
        self.notes = notes
        self.velocity = velocity
        self.note_duration = note_duration

    def build(self) -> Pattern:
        """Build the mechanical figure pattern.

        Returns:
            Pattern: One bar of mechanical figure
        """
        pattern = Pattern(
            name="mechanical_figure",
            channel=Channel.HARPSICHORD,
            length_beats=4.0,
        )

        for i, note in enumerate(self.notes):
            pattern.add_note(i * 0.5, note, self.note_duration, self.velocity)

        return pattern


class SurveillancePingsPattern(PatternBuilder):
    """High harpsichord surveillance pings.

    Irregular high notes that represent the invasive nature
    of the surveillance apparatus.
    """

    def __init__(
        self,
        ping_notes: list[tuple[float, MIDINote]],
        velocity: int = 65,
    ) -> None:
        """Initialize surveillance pings.

        Args:
            ping_notes: List of (offset, note) tuples
            velocity: Ping velocity
        """
        self.ping_notes = ping_notes
        self.velocity = velocity

    def build(self) -> Pattern:
        """Build the surveillance pings pattern.

        Returns:
            Pattern: Surveillance pings
        """
        pattern = Pattern(
            name="surveillance_pings",
            channel=Channel.HARPSICHORD,
            length_beats=4.0,
        )

        for offset, note in self.ping_notes:
            pattern.add_note(offset, note, 0.25, self.velocity)

        return pattern


class DronePattern(PatternBuilder):
    """Sustained drone notes.

    Long held notes (typically on organ or strings) that
    create an ominous foundation.
    """

    def __init__(
        self,
        channel: MIDIChannel,
        notes: list[MIDINote],
        duration: Duration = 4.0,
        velocity: int = 55,
    ) -> None:
        """Initialize drone pattern.

        Args:
            channel: Channel for the drone
            notes: Notes to sustain
            duration: Duration in beats
            velocity: Drone velocity
        """
        self.channel = channel
        self.notes = notes
        self.duration = duration
        self.velocity = velocity

    def build(self) -> Pattern:
        """Build the drone pattern.

        Returns:
            Pattern: Drone pattern
        """
        pattern = Pattern(
            name="drone",
            channel=self.channel,
            length_beats=self.duration,
        )

        for note in self.notes:
            pattern.add_note(0, note, self.duration, self.velocity)

        return pattern


class TritoneDronePattern(PatternBuilder):
    """The devil's interval drone.

    The tritone (augmented 4th / diminished 5th) creates
    maximum harmonic tension - unresolved, contradictory.
    """

    def __init__(
        self,
        root_note: MIDINote,
        tritone_note: MIDINote,
        duration: Duration = 4.0,
        root_velocity: int = 50,
        tritone_velocity: int = 45,
    ) -> None:
        """Initialize tritone drone.

        Args:
            root_note: Root note (usually E)
            tritone_note: Tritone note (Bb from E)
            duration: Duration in beats
            root_velocity: Velocity for root
            tritone_velocity: Velocity for tritone
        """
        self.root_note = root_note
        self.tritone_note = tritone_note
        self.duration = duration
        self.root_velocity = root_velocity
        self.tritone_velocity = tritone_velocity

    def build(self) -> Pattern:
        """Build the tritone drone pattern.

        Returns:
            Pattern: Tritone drone
        """
        pattern = Pattern(
            name="tritone_drone",
            channel=Channel.ORGAN,
            length_beats=self.duration,
        )

        pattern.add_note(0, self.root_note, self.duration, self.root_velocity)
        pattern.add_note(0, self.tritone_note, self.duration, self.tritone_velocity)

        return pattern


class BrassStabPattern(PatternBuilder):
    """Sudden brass stab (state violence).

    Sharp, powerful brass chords that represent
    the sudden violence of state intervention.
    """

    def __init__(
        self,
        notes: list[MIDINote],
        duration: Duration = 0.5,
        velocity: int = 100,
    ) -> None:
        """Initialize brass stab.

        Args:
            notes: Chord notes
            duration: Stab duration
            velocity: Stab velocity
        """
        self.notes = notes
        self.duration = duration
        self.velocity = velocity

    def build(self) -> Pattern:
        """Build the brass stab pattern.

        Returns:
            Pattern: Brass stab
        """
        pattern = Pattern(
            name="brass_stab",
            channel=Channel.BRASS,
            length_beats=self.duration,
        )

        for note in self.notes:
            pattern.add_note(0, note, self.duration, self.velocity)

        return pattern


class MarchPattern(PatternBuilder):
    """Military march drum pattern.

    Creates a martial rhythm for tracks like Viktor's March.
    """

    def __init__(
        self,
        kick_velocity: int = 90,
        snare_velocity: int = 80,
    ) -> None:
        """Initialize march pattern.

        Args:
            kick_velocity: Bass drum velocity
            snare_velocity: Snare velocity
        """
        self.kick_velocity = kick_velocity
        self.snare_velocity = snare_velocity

    def build(self) -> Pattern:
        """Build the march pattern.

        Returns:
            Pattern: March rhythm
        """
        pattern = Pattern(
            name="march",
            channel=Channel.DRUMS,
            length_beats=4.0,
        )

        # Bass drum on 1 and 3
        pattern.add_note(0, DrumNote.BASS_DRUM, 0.5, self.kick_velocity)
        pattern.add_note(2, DrumNote.BASS_DRUM, 0.5, self.kick_velocity - 5)

        # Snare on 2 and 4
        pattern.add_note(1, DrumNote.ACOUSTIC_SNARE, 0.25, self.snare_velocity)
        pattern.add_note(3, DrumNote.ACOUSTIC_SNARE, 0.25, self.snare_velocity)

        return pattern


# =============================================================================
# PATTERN RENDERING HELPERS
# =============================================================================


def render_clock_tick(
    midi: TypedMIDI,
    start_bar: int,
    num_bars: int,
    root_note: MIDINote,
    base_velocity: int = 80,
    accent_velocity: int = 90,
) -> None:
    """Render the relentless timpani clock pattern.

    Convenience function for adding the clock tick across multiple bars.

    Args:
        midi: TypedMIDI instance
        start_bar: First bar (0-indexed)
        num_bars: Number of bars
        root_note: Timpani note
        base_velocity: Base velocity
        accent_velocity: Accent velocity
    """
    pattern = ClockTickPattern(
        root_note=root_note,
        accent_velocity=accent_velocity,
        ghost_velocity=base_velocity - 35,
    ).build()

    pattern.repeat(midi, start_bar, num_bars)


def render_mechanical_figure(
    midi: TypedMIDI,
    start_bar: int,
    num_bars: int,
    notes: list[MIDINote],
    velocity: int = 70,
) -> None:
    """Render the mechanical harpsichord figure.

    Args:
        midi: TypedMIDI instance
        start_bar: First bar
        num_bars: Number of bars
        notes: 8-note figure
        velocity: Base velocity
    """
    pattern = MechanicalFigurePattern(notes=notes, velocity=velocity).build()
    pattern.repeat(midi, start_bar, num_bars)


def render_drone(
    midi: TypedMIDI,
    channel: MIDIChannel,
    start_bar: int,
    num_bars: int,
    notes: list[MIDINote],
    velocity: int = 55,
) -> None:
    """Render a sustained drone.

    Args:
        midi: TypedMIDI instance
        channel: Channel for drone
        start_bar: First bar
        num_bars: Number of bars
        notes: Drone notes
        velocity: Drone velocity
    """
    pattern = DronePattern(
        channel=channel,
        notes=notes,
        velocity=velocity,
    ).build()

    pattern.repeat(midi, start_bar, num_bars)


def render_tritone_drone(
    midi: TypedMIDI,
    start_bar: int,
    num_bars: int,
    root_note: MIDINote,
    tritone_note: MIDINote,
    velocity: int = 45,
) -> None:
    """Render the devil's interval drone.

    Args:
        midi: TypedMIDI instance
        start_bar: First bar
        num_bars: Total duration in bars (creates one long note)
        root_note: Root note
        tritone_note: Tritone note
        velocity: Drone velocity
    """
    # Tritone drone is typically a single long note
    duration = float(num_bars * 4)
    start_beat = start_bar * 4

    midi.add_note(Channel.ORGAN, root_note, start_beat, duration, velocity)
    midi.add_note(Channel.ORGAN, tritone_note, start_beat, duration, velocity - 5)


def render_brass_stab(
    midi: TypedMIDI,
    time: float,
    notes: list[MIDINote],
    duration: Duration = 0.5,
    velocity: int = 100,
) -> None:
    """Render a brass stab at a specific time.

    Args:
        midi: TypedMIDI instance
        time: Time in beats
        notes: Chord notes
        duration: Stab duration
        velocity: Stab velocity
    """
    for note in notes:
        midi.add_note(Channel.BRASS, note, time, duration, velocity)
