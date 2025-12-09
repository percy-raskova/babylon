"""
Musical scale and mode abstractions.

This module provides a theoretical framework for working with scales,
modes, and musical intervals. Rather than hardcoding note values,
we define scales as patterns of intervals that can be transposed
to any root note.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Final

from .types import MIDINote, validate_midi_note


class Note(Enum):
    """Chromatic note names (pitch classes).

    These represent the 12 notes of the chromatic scale without
    regard to octave. Each value is the semitone offset from C.
    """

    C = 0
    Cs = 1  # C# / Db
    D = 2
    Ds = 3  # D# / Eb
    E = 4
    F = 5
    Fs = 6  # F# / Gb
    G = 7
    Gs = 8  # G# / Ab
    A = 9
    As = 10  # A# / Bb
    B = 11

    # Enharmonic aliases
    Db = 1
    Eb = 3
    Gb = 6
    Ab = 8
    Bb = 10


class Octave(Enum):
    """MIDI octave designations.

    MIDI octave 0 starts at note 0 (C0 = MIDI 0).
    Middle C is C4 (MIDI 60).
    """

    OCTAVE_0 = 0  # C0 = MIDI 12 (some systems use different numbering)
    OCTAVE_1 = 1  # C1 = MIDI 24
    OCTAVE_2 = 2  # C2 = MIDI 36
    OCTAVE_3 = 3  # C3 = MIDI 48
    OCTAVE_4 = 4  # C4 = MIDI 60 (Middle C)
    OCTAVE_5 = 5  # C5 = MIDI 72
    OCTAVE_6 = 6  # C6 = MIDI 84
    OCTAVE_7 = 7  # C7 = MIDI 96


# Base MIDI note for each octave (C note)
# Using standard MIDI octave numbering where C4 = 60
OCTAVE_BASE: Final[dict[Octave, int]] = {
    Octave.OCTAVE_0: 12,
    Octave.OCTAVE_1: 24,
    Octave.OCTAVE_2: 36,
    Octave.OCTAVE_3: 48,
    Octave.OCTAVE_4: 60,
    Octave.OCTAVE_5: 72,
    Octave.OCTAVE_6: 84,
    Octave.OCTAVE_7: 96,
}


@dataclass(frozen=True)
class ScaleNote:
    """A specific note with pitch class and octave.

    This represents a concrete musical note that can be converted
    to a MIDI note number.
    """

    note: Note
    octave: Octave

    def to_midi(self) -> MIDINote:
        """Convert to MIDI note number.

        Returns:
            MIDINote: The MIDI note number (0-127)
        """
        midi_value = OCTAVE_BASE[self.octave] + self.note.value
        return validate_midi_note(midi_value)

    def transpose(self, semitones: int) -> "ScaleNote":
        """Transpose by a number of semitones.

        Args:
            semitones: Number of semitones to transpose (can be negative)

        Returns:
            ScaleNote: New note at transposed pitch
        """
        midi = self.to_midi() + semitones
        # Calculate new note and octave
        new_note_value = midi % 12
        new_octave_value = (midi - 12) // 12  # Adjust for octave numbering

        # Find matching Note enum
        new_note = Note(new_note_value)

        # Find matching Octave enum (clamp to valid range)
        new_octave_value = max(0, min(7, new_octave_value))
        new_octave = Octave(new_octave_value)

        return ScaleNote(new_note, new_octave)

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.note.name}{self.octave.value}"


class Mode(Enum):
    """Musical modes (scale patterns).

    Each mode is defined by its interval pattern (semitones from root).
    These patterns can be applied to any root note.
    """

    # Major modes
    IONIAN = (0, 2, 4, 5, 7, 9, 11)  # Major scale
    DORIAN = (0, 2, 3, 5, 7, 9, 10)  # Minor with raised 6th
    PHRYGIAN = (0, 1, 3, 5, 7, 8, 10)  # Minor with flat 2nd - THE DREAD
    LYDIAN = (0, 2, 4, 6, 7, 9, 11)  # Major with raised 4th
    MIXOLYDIAN = (0, 2, 4, 5, 7, 9, 10)  # Major with flat 7th
    AEOLIAN = (0, 2, 3, 5, 7, 8, 10)  # Natural minor
    LOCRIAN = (0, 1, 3, 5, 6, 8, 10)  # Diminished character

    # Additional useful scales
    HARMONIC_MINOR = (0, 2, 3, 5, 7, 8, 11)  # Aeolian with raised 7th
    MELODIC_MINOR = (0, 2, 3, 5, 7, 9, 11)  # Ascending melodic minor
    WHOLE_TONE = (0, 2, 4, 6, 8, 10)  # Symmetrical, dreamlike
    CHROMATIC = tuple(range(12))  # All 12 notes


@dataclass(frozen=True)
class Scale:
    """A musical scale rooted on a specific note.

    A Scale combines a root note with a mode to generate
    concrete MIDI note values.
    """

    root: Note
    mode: Mode

    def degree_to_semitones(self, degree: int) -> int:
        """Get semitones from root for a scale degree.

        Args:
            degree: Scale degree (1-based, 1 = root)

        Returns:
            Semitones from root note
        """
        intervals = self.mode.value
        octave_offset = (degree - 1) // len(intervals)
        degree_in_scale = (degree - 1) % len(intervals)
        return intervals[degree_in_scale] + (octave_offset * 12)

    def note_at_degree(self, degree: int, octave: Octave) -> MIDINote:
        """Get the MIDI note for a scale degree at a given octave.

        Args:
            degree: Scale degree (1 = root, 2 = second, etc.)
            octave: Base octave for the root

        Returns:
            MIDINote: MIDI note number
        """
        root_midi = OCTAVE_BASE[octave] + self.root.value
        semitones = self.degree_to_semitones(degree)
        return validate_midi_note(root_midi + semitones)

    def notes_in_octave(self, octave: Octave) -> list[MIDINote]:
        """Get all scale notes within an octave.

        Args:
            octave: The octave to generate notes for

        Returns:
            List of MIDI notes in the scale
        """
        root_midi = OCTAVE_BASE[octave] + self.root.value
        return [validate_midi_note(root_midi + interval) for interval in self.mode.value]

    def tritone_from_root(self, octave: Octave) -> MIDINote:
        """Get the tritone (augmented 4th / diminished 5th) from root.

        The tritone is 6 semitones from the root - the "devil's interval".
        This is crucial for the fascist faction's musical vocabulary.

        Args:
            octave: Octave for the root note

        Returns:
            MIDINote: The tritone note
        """
        root_midi = OCTAVE_BASE[octave] + self.root.value
        return validate_midi_note(root_midi + 6)


# =============================================================================
# PRE-DEFINED SCALES FOR BABYLON
# =============================================================================

# The fascist faction's primary scale - E Phrygian
# The flat 2nd (F natural) creates inherent dread
E_PHRYGIAN: Final[Scale] = Scale(Note.E, Mode.PHRYGIAN)

# Alternative scales for other factions (future use)
C_MAJOR: Final[Scale] = Scale(Note.C, Mode.IONIAN)  # Liberal optimism (false)
D_DORIAN: Final[Scale] = Scale(Note.D, Mode.DORIAN)  # Worker solidarity
A_MINOR: Final[Scale] = Scale(Note.A, Mode.AEOLIAN)  # Peripheral suffering


# =============================================================================
# CONVENIENT NOTE GENERATORS
# =============================================================================


def e_phrygian_note(degree: int, octave: Octave) -> MIDINote:
    """Get a note from E Phrygian scale.

    Args:
        degree: Scale degree (1 = E, 2 = F, 3 = G, etc.)
        octave: Octave for the root

    Returns:
        MIDINote: The MIDI note
    """
    return E_PHRYGIAN.note_at_degree(degree, octave)


def tritone_e(octave: Octave) -> MIDINote:
    """Get the tritone of E (Bb) at a given octave.

    Args:
        octave: Octave for the E root

    Returns:
        MIDINote: Bb at the appropriate octave
    """
    return E_PHRYGIAN.tritone_from_root(octave)
