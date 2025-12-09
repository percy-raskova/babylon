"""
Fascist Soundtrack Generator - Core Module

This module provides the foundational abstractions for MIDI composition
in Babylon. It is designed to be faction-agnostic, allowing the same
infrastructure to support Fascist, Communist, Liberal, and Comprador factions.

Architecture:
    - types.py: Type definitions and constrained types for MIDI
    - scales.py: Musical scale and mode abstractions
    - instruments.py: General MIDI instrument mappings with semantic meaning
    - patterns.py: Reusable musical pattern generators
    - track.py: Base classes for track composition
    - midi_wrapper.py: Type-safe wrapper around midiutil
    - faction.py: Multi-faction support infrastructure
"""

from .faction import (
    Faction,
    FactionConfig,
    FactionMusicalIdentity,
    FactionType,
)
from .instruments import (
    Channel,
    DrumNote,
    GMProgram,
    InstrumentRole,
)
from .midi_wrapper import TypedMIDI
from .patterns import (
    Pattern,
    PatternBuilder,
)
from .scales import (
    Mode,
    Note,
    Octave,
    Scale,
    ScaleNote,
)
from .track import (
    Section,
    SectionBuilder,
    TrackConfig,
    TrackGenerator,
    TrackMetadata,
    TrackMood,
)
from .types import (
    BarCount,
    BeatOffset,
    BeatPosition,
    Duration,
    MIDINote,
    Tempo,
    Velocity,
)

__all__ = [
    # Types
    "MIDINote",
    "Velocity",
    "Tempo",
    "Duration",
    "BeatPosition",
    "BeatOffset",
    "BarCount",
    # Scales
    "Note",
    "Octave",
    "Mode",
    "Scale",
    "ScaleNote",
    # Instruments
    "GMProgram",
    "Channel",
    "DrumNote",
    "InstrumentRole",
    # Patterns
    "Pattern",
    "PatternBuilder",
    # Track
    "TrackConfig",
    "TrackMetadata",
    "TrackMood",
    "TrackGenerator",
    "Section",
    "SectionBuilder",
    # MIDI
    "TypedMIDI",
    # Faction
    "Faction",
    "FactionConfig",
    "FactionMusicalIdentity",
    "FactionType",
]
