"""
Track composition infrastructure.

This module provides the base classes and protocols for
defining tracks in a structured, extensible way.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol

from .midi_wrapper import TypedMIDI, save_track
from .types import BarCount, Tempo


class TrackMood(Enum):
    """Emotional register of a track.

    These moods inform both musical choices and game integration.
    """

    # Menacing moods (public face of fascism)
    MENACING = "menacing"  # Cold, efficient, unstoppable
    MILITARISTIC = "militaristic"  # Martial, imposing
    VIOLENT = "violent"  # Aggressive, crushing

    # Anxious moods (private reality of fascism)
    ANXIOUS = "anxious"  # Fearful, unstable
    DESPERATE = "desperate"  # Frantic, no escape
    HOLLOW = "hollow"  # Empty, false

    # Dread moods (existential)
    DREAD = "dread"  # Existential horror
    HAUNTING = "haunting"  # Ambient, void


@dataclass(frozen=True)
class TrackMetadata:
    """Metadata for a track.

    Contains information needed for both composition and
    game integration (trigger conditions, crossfades, etc.).
    """

    # Identity
    track_number: int
    title: str
    filename: str

    # Musical parameters
    tempo: Tempo
    total_bars: BarCount
    key: str  # e.g., "E Phrygian", "Tritone drones"

    # Emotional register
    mood: TrackMood
    mood_description: str

    # Game integration
    faction: str = "fascist"
    trigger_contexts: list[str] = field(default_factory=list)
    loop_compatible: bool = True

    @property
    def duration_beats(self) -> float:
        """Total duration in beats."""
        return float(self.total_bars * 4)

    @property
    def duration_seconds(self) -> float:
        """Approximate duration in seconds."""
        return (self.duration_beats * 60) / self.tempo

    @property
    def duration_string(self) -> str:
        """Human-readable duration (M:SS)."""
        seconds = int(self.duration_seconds)
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"


@dataclass
class TrackConfig:
    """Configuration for track generation.

    Separates track parameters from implementation,
    allowing the same generator to produce variations.
    """

    metadata: TrackMetadata
    output_dir: Path | None = None

    # Musical parameters that can be overridden
    velocity_scale: float = 1.0  # Global velocity multiplier
    transpose: int = 0  # Semitones to transpose


class Section(Protocol):
    """Protocol for track sections.

    Each section is a callable that renders to a TypedMIDI.
    """

    def __call__(self, midi: TypedMIDI) -> None:
        """Render this section to the MIDI file.

        Args:
            midi: TypedMIDI instance to render to
        """
        ...


@dataclass
class SectionBuilder:
    """Builder for defining track sections.

    Sections are the structural units of a track (A, B, C, D).
    This builder provides a fluent API for defining sections.
    """

    name: str
    start_bar: int
    num_bars: int
    description: str = ""
    _render_fn: Callable[[TypedMIDI, int, int], None] | None = None

    def with_renderer(self, fn: Callable[[TypedMIDI, int, int], None]) -> "SectionBuilder":
        """Set the render function for this section.

        The render function takes (midi, start_bar, num_bars).

        Args:
            fn: Function to render this section

        Returns:
            Self for method chaining
        """
        self._render_fn = fn
        return self

    def render(self, midi: TypedMIDI) -> None:
        """Render this section to MIDI.

        Args:
            midi: TypedMIDI instance

        Raises:
            ValueError: If no render function is set
        """
        if self._render_fn is None:
            msg = f"Section '{self.name}' has no render function"
            raise ValueError(msg)
        self._render_fn(midi, self.start_bar, self.num_bars)


class TrackGenerator(ABC):
    """Abstract base class for track generators.

    Subclasses implement specific tracks by defining sections
    and their musical content.
    """

    def __init__(self, config: TrackConfig) -> None:
        """Initialize the track generator.

        Args:
            config: Track configuration
        """
        self.config = config
        self._sections: list[SectionBuilder] = []

    @property
    def metadata(self) -> TrackMetadata:
        """Get track metadata."""
        return self.config.metadata

    @property
    def tempo(self) -> Tempo:
        """Get track tempo."""
        return self.metadata.tempo

    @property
    def total_bars(self) -> BarCount:
        """Get total bars."""
        return self.metadata.total_bars

    def add_section(self, section: SectionBuilder) -> "TrackGenerator":
        """Add a section to the track.

        Args:
            section: Section builder

        Returns:
            Self for method chaining
        """
        self._sections.append(section)
        return self

    @abstractmethod
    def define_sections(self) -> None:
        """Define the sections for this track.

        Subclasses implement this to add sections via add_section().
        """
        raise NotImplementedError

    def create_midi(self, num_tracks: int = 5) -> TypedMIDI:
        """Create and configure the MIDI file.

        Args:
            num_tracks: Number of MIDI tracks

        Returns:
            TypedMIDI: Configured MIDI file
        """
        midi = TypedMIDI(num_tracks)
        midi.setup_fascist_tracks(self.tempo)
        return midi

    def compose(self) -> TypedMIDI:
        """Compose the complete track.

        Returns:
            TypedMIDI: The composed track
        """
        # Define sections if not already done
        if not self._sections:
            self.define_sections()

        # Create MIDI file
        midi = self.create_midi()

        # Render each section
        for section in self._sections:
            section.render(midi)

        return midi

    def generate(self) -> Path:
        """Generate and save the track.

        Returns:
            Path: Path to the saved MIDI file
        """
        midi = self.compose()
        return save_track(
            midi,
            self.metadata.filename,
            self.total_bars,
            self.config.output_dir
            or Path(__file__).parent.parent.parent.parent / "assets" / "music" / "fascist",
        )

    def print_completion_message(self) -> None:
        """Print a completion message with track info."""
        print()
        print(self.metadata.title.upper())
        print(self.metadata.mood_description)


# =============================================================================
# TRACK REGISTRY
# =============================================================================


@dataclass
class TrackRegistry:
    """Registry for all tracks in a faction.

    Allows iteration over tracks and batch generation.
    """

    faction: str
    tracks: dict[int, type[TrackGenerator]] = field(default_factory=dict)
    configs: dict[int, TrackConfig] = field(default_factory=dict)

    def register(
        self,
        track_number: int,
        generator_class: type[TrackGenerator],
        config: TrackConfig,
    ) -> None:
        """Register a track generator.

        Args:
            track_number: Track number (1-based)
            generator_class: TrackGenerator subclass
            config: Configuration for this track
        """
        self.tracks[track_number] = generator_class
        self.configs[track_number] = config

    def generate_track(self, track_number: int) -> Path:
        """Generate a single track.

        Args:
            track_number: Track number to generate

        Returns:
            Path: Path to generated file

        Raises:
            KeyError: If track number not registered
        """
        generator_class = self.tracks[track_number]
        config = self.configs[track_number]
        generator = generator_class(config)
        path = generator.generate()
        generator.print_completion_message()
        return path

    def generate_all(self) -> list[Path]:
        """Generate all registered tracks.

        Returns:
            List of paths to generated files
        """
        paths: list[Path] = []
        for track_number in sorted(self.tracks.keys()):
            path = self.generate_track(track_number)
            paths.append(path)
            print()
        return paths

    def list_tracks(self) -> list[TrackMetadata]:
        """List all registered track metadata.

        Returns:
            List of TrackMetadata
        """
        return [self.configs[n].metadata for n in sorted(self.configs.keys())]
