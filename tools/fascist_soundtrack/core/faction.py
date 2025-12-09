"""
Faction abstraction for multi-faction soundtrack support.

This module provides the infrastructure for creating soundtracks
for different factions in Babylon. Each faction has:
- A unique musical identity (scale, instruments, patterns)
- Thematic moods and emotional registers
- Track metadata and game integration hooks

Supported factions:
- FASCIST: National Revival Movement (E Phrygian, surveillance/violence)
- COMMUNIST: Revolutionary Front (D Dorian, solidarity/struggle) [planned]
- LIBERAL: Democratic Coalition (C Major, optimism/decay) [planned]
- COMPRADOR: Collaborator Network (A Minor, anxiety/duplicity) [planned]
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Final

from .instruments import GMProgram, InstrumentConfig, InstrumentRole
from .scales import Mode, Note, Scale
from .track import TrackMood, TrackRegistry


class FactionType(Enum):
    """Enumeration of playable factions in Babylon."""

    FASCIST = "fascist"
    COMMUNIST = "communist"
    LIBERAL = "liberal"
    COMPRADOR = "comprador"


@dataclass(frozen=True)
class FactionMusicalIdentity:
    """Defines the musical DNA of a faction.

    Each faction has a distinct musical vocabulary that reflects
    its ideological character and narrative role.
    """

    # Harmonic identity
    primary_scale: Scale
    secondary_scale: Scale | None = None

    # Instrumental character
    lead_instrument: GMProgram = GMProgram.HARPSICHORD
    bass_instrument: GMProgram = GMProgram.CHURCH_ORGAN
    accent_instrument: GMProgram = GMProgram.BRASS_SECTION

    # Rhythmic character
    default_tempo_range: tuple[int, int] = (80, 120)

    # Philosophical description
    description: str = ""


@dataclass
class FactionConfig:
    """Configuration for a faction's soundtrack.

    Contains all the parameters needed to generate a faction's
    complete musical identity.
    """

    faction_type: FactionType
    faction_name: str
    musical_identity: FactionMusicalIdentity
    output_subdir: str

    # Instrument setup
    instruments: dict[InstrumentRole, InstrumentConfig] = field(default_factory=dict)

    # Track registry
    track_registry: TrackRegistry = field(default_factory=lambda: TrackRegistry("unknown"))

    # Available moods for this faction
    available_moods: list[TrackMood] = field(default_factory=list)

    @property
    def output_dir(self) -> Path:
        """Get the output directory for this faction's tracks."""
        base = Path(__file__).parent.parent.parent.parent / "assets" / "music"
        return base / self.output_subdir


# =============================================================================
# PREDEFINED FACTION CONFIGURATIONS
# =============================================================================

# Fascist faction - National Revival Movement
FASCIST_IDENTITY: Final[FactionMusicalIdentity] = FactionMusicalIdentity(
    primary_scale=Scale(Note.E, Mode.PHRYGIAN),
    secondary_scale=None,  # Uses tritone for tension
    lead_instrument=GMProgram.HARPSICHORD,
    bass_instrument=GMProgram.CHURCH_ORGAN,
    accent_instrument=GMProgram.BRASS_SECTION,
    default_tempo_range=(66, 116),
    description=(
        "The sound of the surveillance state. E Phrygian's flat 2nd creates "
        "inherent dread. The harpsichord represents mechanical efficiency, "
        "the organ false grandeur, brass state violence."
    ),
)

FASCIST_CONFIG: Final[FactionConfig] = FactionConfig(
    faction_type=FactionType.FASCIST,
    faction_name="National Revival Movement",
    musical_identity=FASCIST_IDENTITY,
    output_subdir="fascist",
    available_moods=[
        TrackMood.MENACING,
        TrackMood.MILITARISTIC,
        TrackMood.VIOLENT,
        TrackMood.ANXIOUS,
        TrackMood.DESPERATE,
        TrackMood.HOLLOW,
        TrackMood.DREAD,
        TrackMood.HAUNTING,
    ],
)

# Communist faction - Revolutionary Front (planned)
COMMUNIST_IDENTITY: Final[FactionMusicalIdentity] = FactionMusicalIdentity(
    primary_scale=Scale(Note.D, Mode.DORIAN),  # Worker solidarity
    secondary_scale=Scale(Note.A, Mode.AEOLIAN),  # Struggle
    lead_instrument=GMProgram.STRING_ENSEMBLE_1,
    bass_instrument=GMProgram.CONTRABASS,
    accent_instrument=GMProgram.FRENCH_HORN,
    default_tempo_range=(72, 132),
    description=(
        "The sound of collective struggle. D Dorian's raised 6th "
        "provides hope within minor context. Strings represent "
        "the masses, horns the call to action."
    ),
)

# Liberal faction - Democratic Coalition (planned)
LIBERAL_IDENTITY: Final[FactionMusicalIdentity] = FactionMusicalIdentity(
    primary_scale=Scale(Note.C, Mode.IONIAN),  # False optimism
    secondary_scale=Scale(Note.A, Mode.AEOLIAN),  # Underlying decay
    lead_instrument=GMProgram.ACOUSTIC_PIANO,
    bass_instrument=GMProgram.STRING_ENSEMBLE_1,
    accent_instrument=GMProgram.TRUMPET,
    default_tempo_range=(90, 140),
    description=(
        "The sound of managed decline. Major key projects optimism "
        "while underlying minor passages reveal decay. Piano suggests "
        "civility, strings institutional weight."
    ),
)

# Comprador faction - Collaborator Network (planned)
COMPRADOR_IDENTITY: Final[FactionMusicalIdentity] = FactionMusicalIdentity(
    primary_scale=Scale(Note.A, Mode.AEOLIAN),  # Peripheral suffering
    secondary_scale=Scale(Note.E, Mode.PHRYGIAN),  # Inherited dread
    lead_instrument=GMProgram.ELECTRIC_PIANO_1,
    bass_instrument=GMProgram.SYNTH_STRINGS_1,
    accent_instrument=GMProgram.MUTED_TRUMPET,
    default_tempo_range=(80, 110),
    description=(
        "The sound of extraction and duplicity. Minor key reflects "
        "peripheral suffering. Electronic instruments suggest modernity "
        "imposed from outside. Muted brass hints at suppressed violence."
    ),
)


class Faction(ABC):
    """Abstract base class for faction soundtrack managers.

    Each faction implementation provides:
    - Configuration of its musical identity
    - Registration of its tracks
    - Generation utilities
    """

    def __init__(self, config: FactionConfig) -> None:
        """Initialize the faction manager.

        Args:
            config: Faction configuration
        """
        self.config = config
        self._setup_track_registry()

    @property
    def name(self) -> str:
        """Get faction name."""
        return self.config.faction_name

    @property
    def faction_type(self) -> FactionType:
        """Get faction type."""
        return self.config.faction_type

    @property
    def output_dir(self) -> Path:
        """Get output directory for tracks."""
        return self.config.output_dir

    @property
    def tracks(self) -> TrackRegistry:
        """Get track registry."""
        return self.config.track_registry

    @abstractmethod
    def _setup_track_registry(self) -> None:
        """Register all tracks for this faction.

        Subclasses implement this to register their tracks.
        """
        raise NotImplementedError

    def generate_track(self, track_number: int) -> Path:
        """Generate a single track.

        Args:
            track_number: Track number to generate

        Returns:
            Path to generated file
        """
        return self.tracks.generate_track(track_number)

    def generate_all(self) -> list[Path]:
        """Generate all tracks for this faction.

        Returns:
            List of paths to generated files
        """
        return self.tracks.generate_all()

    def list_tracks(self) -> None:
        """Print a list of all tracks."""
        print(f"\n{self.name} Soundtrack")
        print("=" * 40)
        for metadata in self.tracks.list_tracks():
            print(f"  {metadata.track_number:02d}. {metadata.title}")
            print(f"      {metadata.duration_string} - {metadata.mood_description}")
        print()


# =============================================================================
# FACTION FACTORY
# =============================================================================


def get_faction_config(faction_type: FactionType) -> FactionConfig:
    """Get the configuration for a faction type.

    Args:
        faction_type: The faction to get config for

    Returns:
        FactionConfig for the specified faction

    Raises:
        ValueError: If faction type is not implemented
    """
    configs = {
        FactionType.FASCIST: FASCIST_CONFIG,
        # FactionType.COMMUNIST: ...,  # TODO: Implement
        # FactionType.LIBERAL: ...,    # TODO: Implement
        # FactionType.COMPRADOR: ...,  # TODO: Implement
    }

    if faction_type not in configs:
        msg = f"Faction {faction_type.value} is not yet implemented"
        raise ValueError(msg)

    return configs[faction_type]


def get_faction_identity(faction_type: FactionType) -> FactionMusicalIdentity:
    """Get the musical identity for a faction type.

    Args:
        faction_type: The faction

    Returns:
        FactionMusicalIdentity
    """
    identities = {
        FactionType.FASCIST: FASCIST_IDENTITY,
        FactionType.COMMUNIST: COMMUNIST_IDENTITY,
        FactionType.LIBERAL: LIBERAL_IDENTITY,
        FactionType.COMPRADOR: COMPRADOR_IDENTITY,
    }
    return identities[faction_type]
