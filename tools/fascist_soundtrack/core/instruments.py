"""
General MIDI instrument definitions with semantic meaning.

In Babylon's soundtrack, instruments are not arbitrary choices.
Each instrument carries thematic weight and philosophical meaning.
This module maps MIDI program numbers to their semantic roles.
"""

from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Final

from .types import MIDIChannel, MIDINote, validate_channel


class GMProgram(IntEnum):
    """General MIDI program numbers (0-127).

    Only instruments used in Babylon are defined here.
    See: https://www.midi.org/specifications/item/gm-level-1-sound-set
    """

    # Keyboards
    ACOUSTIC_PIANO = 0
    BRIGHT_PIANO = 1
    ELECTRIC_GRAND = 2
    HONKY_TONK = 3
    ELECTRIC_PIANO_1 = 4
    ELECTRIC_PIANO_2 = 5
    HARPSICHORD = 6  # The Machine / Surveillance
    CLAVINET = 7

    # Chromatic Percussion
    CELESTA = 8
    GLOCKENSPIEL = 9
    MUSIC_BOX = 10
    VIBRAPHONE = 11
    MARIMBA = 12
    XYLOPHONE = 13
    TUBULAR_BELLS = 14

    # Organ
    DRAWBAR_ORGAN = 16
    PERCUSSIVE_ORGAN = 17
    ROCK_ORGAN = 18
    CHURCH_ORGAN = 19  # False Grandeur / Propaganda

    # Strings
    VIOLIN = 40
    VIOLA = 41
    CELLO = 42  # Deep foreboding
    CONTRABASS = 43
    TREMOLO_STRINGS = 44  # Anxiety (never rests)
    PIZZICATO_STRINGS = 45
    ORCHESTRAL_HARP = 46
    TIMPANI = 47  # The Clock / The Jackboot

    # Ensemble
    STRING_ENSEMBLE_1 = 48  # Regular strings (for contrast)
    STRING_ENSEMBLE_2 = 49
    SYNTH_STRINGS_1 = 50
    SYNTH_STRINGS_2 = 51
    CHOIR_AAHS = 52
    VOICE_OOHS = 53
    SYNTH_VOICE = 54
    ORCHESTRA_HIT = 55

    # Brass
    TRUMPET = 56
    TROMBONE = 57  # Heavy brass
    TUBA = 58  # Deepest brass
    MUTED_TRUMPET = 59
    FRENCH_HORN = 60  # Military authority
    BRASS_SECTION = 61  # State Violence
    SYNTH_BRASS_1 = 62
    SYNTH_BRASS_2 = 63


class DrumNote(IntEnum):
    """General MIDI drum map (Channel 10).

    Note numbers for percussion on the GM drum channel.
    """

    ACOUSTIC_BASS_DRUM = 35
    BASS_DRUM = 36  # Kick drum
    SIDE_STICK = 37
    ACOUSTIC_SNARE = 38  # Snare
    HAND_CLAP = 39
    ELECTRIC_SNARE = 40
    LOW_FLOOR_TOM = 41
    CLOSED_HI_HAT = 42  # Closed hi-hat
    HIGH_FLOOR_TOM = 43
    PEDAL_HI_HAT = 44
    LOW_TOM = 45  # Low tom
    OPEN_HI_HAT = 46  # Open hi-hat
    LOW_MID_TOM = 47  # Mid tom
    HI_MID_TOM = 48
    CRASH_CYMBAL_1 = 49  # Crash cymbal
    HIGH_TOM = 50  # High tom
    RIDE_CYMBAL_1 = 51  # Ride cymbal
    CHINESE_CYMBAL = 52
    RIDE_BELL = 53
    TAMBOURINE = 54
    SPLASH_CYMBAL = 55
    COWBELL = 56
    CRASH_CYMBAL_2 = 57
    VIBRASLAP = 58
    RIDE_CYMBAL_2 = 59


class InstrumentRole(Enum):
    """Semantic roles for instruments in the fascist soundtrack.

    Each role has philosophical meaning in the context of
    modeling fascist aesthetics.
    """

    # The Machine - mechanical, clockwork, surveillance
    MACHINE = "machine"

    # Anxiety - trembling, never at rest
    ANXIETY = "anxiety"

    # State Violence - sudden, forceful, brass
    VIOLENCE = "violence"

    # The Clock - relentless time, inevitability
    CLOCK = "clock"

    # False Grandeur - propaganda, hollow majesty
    GRANDEUR = "grandeur"

    # Authority - military command, hierarchy
    AUTHORITY = "authority"

    # The Void - ambient, hollow, existential
    VOID = "void"


@dataclass(frozen=True)
class InstrumentConfig:
    """Configuration for an instrument in a track.

    Maps a semantic role to a specific MIDI program and channel,
    along with default velocity and other parameters.
    """

    role: InstrumentRole
    program: GMProgram
    channel: MIDIChannel
    default_velocity: int = 80
    description: str = ""


# =============================================================================
# STANDARD FASCIST FACTION INSTRUMENT SETUP
# =============================================================================

# Channel assignments for the fascist faction
CH_HARPSICHORD: Final[MIDIChannel] = validate_channel(0)
CH_STRINGS: Final[MIDIChannel] = validate_channel(1)
CH_BRASS: Final[MIDIChannel] = validate_channel(2)
CH_TIMPANI: Final[MIDIChannel] = validate_channel(3)
CH_ORGAN: Final[MIDIChannel] = validate_channel(4)
CH_FRENCH_HORN: Final[MIDIChannel] = validate_channel(5)
CH_EXTRA: Final[MIDIChannel] = validate_channel(6)
CH_DRUMS: Final[MIDIChannel] = validate_channel(9)  # GM drum channel

# Standard instrument configurations for fascist tracks
FASCIST_INSTRUMENTS: Final[dict[InstrumentRole, InstrumentConfig]] = {
    InstrumentRole.MACHINE: InstrumentConfig(
        role=InstrumentRole.MACHINE,
        program=GMProgram.HARPSICHORD,
        channel=CH_HARPSICHORD,
        default_velocity=70,
        description="Harpsichord - The Machine / Surveillance",
    ),
    InstrumentRole.ANXIETY: InstrumentConfig(
        role=InstrumentRole.ANXIETY,
        program=GMProgram.TREMOLO_STRINGS,
        channel=CH_STRINGS,
        default_velocity=60,
        description="Tremolo Strings - Anxiety (never rests)",
    ),
    InstrumentRole.VIOLENCE: InstrumentConfig(
        role=InstrumentRole.VIOLENCE,
        program=GMProgram.BRASS_SECTION,
        channel=CH_BRASS,
        default_velocity=90,
        description="Brass Section - State Violence",
    ),
    InstrumentRole.CLOCK: InstrumentConfig(
        role=InstrumentRole.CLOCK,
        program=GMProgram.TIMPANI,
        channel=CH_TIMPANI,
        default_velocity=80,
        description="Timpani - The Clock / The Jackboot",
    ),
    InstrumentRole.GRANDEUR: InstrumentConfig(
        role=InstrumentRole.GRANDEUR,
        program=GMProgram.CHURCH_ORGAN,
        channel=CH_ORGAN,
        default_velocity=55,
        description="Church Organ - False Grandeur / Propaganda",
    ),
    InstrumentRole.AUTHORITY: InstrumentConfig(
        role=InstrumentRole.AUTHORITY,
        program=GMProgram.FRENCH_HORN,
        channel=CH_FRENCH_HORN,
        default_velocity=70,
        description="French Horn - Military Authority",
    ),
}


class Channel:
    """Convenient access to channel constants.

    This class provides namespace organization for channel constants
    and can be extended to include validation or dynamic assignment.
    """

    HARPSICHORD: Final[MIDIChannel] = CH_HARPSICHORD
    STRINGS: Final[MIDIChannel] = CH_STRINGS
    BRASS: Final[MIDIChannel] = CH_BRASS
    TIMPANI: Final[MIDIChannel] = CH_TIMPANI
    ORGAN: Final[MIDIChannel] = CH_ORGAN
    FRENCH_HORN: Final[MIDIChannel] = CH_FRENCH_HORN
    EXTRA: Final[MIDIChannel] = CH_EXTRA
    DRUMS: Final[MIDIChannel] = CH_DRUMS

    @classmethod
    def for_role(cls, role: InstrumentRole) -> MIDIChannel:
        """Get the channel for a given instrument role.

        Args:
            role: The instrument role

        Returns:
            MIDIChannel: The assigned channel

        Raises:
            KeyError: If role has no assigned channel
        """
        return FASCIST_INSTRUMENTS[role].channel


def drum_note_to_midi(drum: DrumNote) -> MIDINote:
    """Convert a drum note enum to MIDINote type.

    Args:
        drum: Drum note from GM drum map

    Returns:
        MIDINote: The MIDI note number
    """
    return MIDINote(drum.value)
