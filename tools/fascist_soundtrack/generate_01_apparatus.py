#!/usr/bin/env python3
"""
Track 01: "The Apparatus" (5:00)
Mood: MENACING - Cold, efficient, unstoppable

The surveillance state at peak operation.
Cold, efficient, all-seeing - the machine that never sleeps.

=== CONCEPTUAL BRIEF ===
This is the sound of being watched by something that does not care about you.
The Apparatus is not malicious - it is indifferent. That is worse.

The piece represents the Panopticon: you are always potentially observed,
so you must always behave as if observed. The machine does not need to
watch everyone all the time - the knowledge of its existence is enough.

=== MUSICAL ARCHITECTURE ===
Key: E Phrygian (flat 2nd = inherent dread)
Tempo: 72 BPM (slower = heavier, more oppressive)
Time Signature: 4/4
Duration: ~5:00 (90 bars at 72 BPM = 5:00 exactly)

HARMONIC ARC:
  Section A (1-18):   E5 power chord - hollow stability
  Section B (19-42):  E5 to E-B-F - dread creeps in
  Section C (43-72):  E-Bb tritone dominant - full unease
  Section D (73-90):  Return to E5 - false resolution, eternal

DYNAMIC ARC:
  Section A: pp -> mp (velocity 30-70)
  Section B: mp -> mf (velocity 60-85)
  Section C: mf -> fff (velocity 75-127)
  Section D: fff -> mp fade (velocity 100 -> 65)

INSTRUMENTAL ROLES:
  - Harpsichord: The Machine itself (cold, precise, mechanical)
  - Timpani: The Jackboot Rhythm (relentless 8th notes, never stops)
  - Organ: The Facade (hollow grandeur, propaganda)
  - Tremolo Strings: Ambient Dread (constant low hum of anxiety)
  - Brass: State Violence (sudden, brutal, unpredictable)

=== INTEGRATION GUIDANCE ===
Trigger: When player enters fascist faction menu or views surveillance mechanics
Loop Point: Bars 19-90 can loop indefinitely
Fade Trigger: When player exits fascist context, fade over 3 seconds
"""

from typing import Any, Final

from . import (
    A3,
    A4,
    B2,
    B3,
    C4,
    CH_BRASS,
    CH_HARPSI,
    CH_ORGAN,
    CH_STRINGS,
    CH_TIMPANI,
    E2,
    E3,
    E4,
    E5,
    F2,
    F3,
    F4,
    F5,
    G3,
    G4,
    G5,
    Bb2,
    Bb3,
    Bb4,
    clamp_velocity,
    create_midi,
    save_midi,
    setup_standard_tracks,
)

# Type alias for midi parameter (untyped external library)
MidiType = Any

# =============================================================================
# TRACK CONSTANTS
# =============================================================================

TEMPO: Final[int] = 72  # Slower = heavier, more oppressive
TOTAL_BARS: Final[int] = 90  # 90 bars at 72 BPM = exactly 5:00

# Section boundaries
SECTION_A_START: Final[int] = 0
SECTION_A_END: Final[int] = 18
SECTION_B_START: Final[int] = 18
SECTION_B_END: Final[int] = 42
SECTION_C_START: Final[int] = 42
SECTION_C_END: Final[int] = 72
SECTION_D_START: Final[int] = 72
SECTION_D_END: Final[int] = 90


# =============================================================================
# MECHANICAL FIGURES - The language of the machine
# =============================================================================


def add_machine_pulse(
    midi: MidiType,
    start_bar: int,
    num_bars: int,
    velocity_base: int = 65,
    include_ghost_notes: bool = False,
) -> None:
    """The core harpsichord mechanical figure - cold, precise.

    This is the heartbeat of the machine. It never varies, because
    machines do not tire, do not hesitate, do not feel.

    Pattern: E-F-E-G-E-F-E-A (8th notes, one bar)
    The F (dread note) appears twice, creating subliminal unease.
    """
    figure: list[int] = [E3, F3, E3, G3, E3, F3, E3, A3]
    note_duration: float = 0.45  # Slightly detached for mechanical feel

    for bar in range(num_bars):
        time: float = (start_bar + bar) * 4.0

        for i, note in enumerate(figure):
            # Slight velocity variation for human-like imperfection
            vel_offset: int = -3 if i % 2 == 1 else 0
            vel: int = clamp_velocity(velocity_base + vel_offset)

            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, note_duration, vel)

        # Ghost notes on beat 4.25 and 4.75 (16th notes between main notes)
        if include_ghost_notes and bar % 2 == 0:
            midi.addNote(
                CH_HARPSI, CH_HARPSI, E3, time + 3.25, 0.2, clamp_velocity(velocity_base - 25)
            )
            midi.addNote(
                CH_HARPSI, CH_HARPSI, F3, time + 3.75, 0.2, clamp_velocity(velocity_base - 25)
            )


def add_upper_machine_pulse(
    midi: MidiType,
    start_bar: int,
    num_bars: int,
    velocity_base: int = 60,
) -> None:
    """Upper octave mechanical figure - the watchtower.

    Offset by one 8th note from the main pulse, creating
    the sensation of overlapping surveillance systems.
    """
    figure: list[int] = [E4, G4, F4, E4, G4, A4, G4, F4]

    for bar in range(num_bars):
        time: float = (start_bar + bar) * 4.0 + 0.5  # Offset by half beat

        for i, note in enumerate(figure):
            if i < 6:  # Only play 6 notes, leaving space
                vel: int = clamp_velocity(velocity_base - (i * 2))
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.35, vel)


def add_surveillance_pings(
    midi: MidiType,
    start_bar: int,
    num_bars: int,
    velocity_base: int = 55,
    dense: bool = False,
) -> None:
    """High register surveillance pings - the camera turning toward you.

    Irregular pattern creates sense of unpredictable observation.
    Dense mode adds more pings for heightened tension.
    """
    # Base pattern: asymmetric, unsettling
    base_pings: list[tuple[float, int]] = [
        (0.5, E5),
        (1.75, F5),  # Dread note
        (2.5, E5),
        (3.25, G5),
    ]

    # Dense pattern adds more surveillance
    dense_pings: list[tuple[float, int]] = [
        (0.25, E5),
        (0.75, F5),
        (1.25, E5),
        (1.75, F5),
        (2.25, G5),
        (2.75, F5),
        (3.25, E5),
        (3.75, F5),
    ]

    pings: list[tuple[float, int]] = dense_pings if dense else base_pings

    for bar in range(num_bars):
        time: float = (start_bar + bar) * 4.0

        for offset, note in pings:
            # Skip some pings irregularly - the machine has patterns we cannot predict
            skip: bool = (bar + int(offset * 3)) % 5 == 0
            if not skip:
                vel: int = clamp_velocity(velocity_base + (5 if note == F5 else 0))
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + offset, 0.2, vel)


# =============================================================================
# THE JACKBOOT RHYTHM - Timpani clock that never stops
# =============================================================================


def add_jackboot_clock(
    midi: MidiType,
    start_bar: int,
    num_bars: int,
    velocity_base: int = 70,
    include_16ths: bool = False,
) -> None:
    """The relentless timpani rhythm - the sound of boots on pavement.

    Pattern: 8th notes on E2, accented on beats 1 and 3
    The rhythm never varies. Time marches on. There is no escape.
    """
    for bar in range(num_bars):
        time: float = (start_bar + bar) * 4.0

        for beat in range(4):
            beat_time: float = time + beat

            # Accented on 1 and 3 (like marching)
            is_accent: bool = beat in (0, 2)
            accent_vel: int = velocity_base + 15 if is_accent else velocity_base - 10

            # Main 8th notes
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, beat_time, 0.25, clamp_velocity(accent_vel))
            midi.addNote(
                CH_TIMPANI,
                CH_TIMPANI,
                E2,
                beat_time + 0.5,
                0.25,
                clamp_velocity(accent_vel - 20),
            )

            # 16th note subdivisions for intensity
            if include_16ths and bar % 2 == 1:
                midi.addNote(
                    CH_TIMPANI,
                    CH_TIMPANI,
                    E2,
                    beat_time + 0.25,
                    0.1,
                    clamp_velocity(accent_vel - 35),
                )
                midi.addNote(
                    CH_TIMPANI,
                    CH_TIMPANI,
                    E2,
                    beat_time + 0.75,
                    0.1,
                    clamp_velocity(accent_vel - 35),
                )


def add_timpani_buildup(
    midi: MidiType,
    start_bar: int,
    num_bars: int,
    start_vel: int = 40,
    end_vel: int = 90,
) -> None:
    """Gradual timpani entrance - the machine awakening."""
    vel_step: float = (end_vel - start_vel) / max(1, num_bars)

    for bar in range(num_bars):
        time: float = (start_bar + bar) * 4.0
        current_vel: int = int(start_vel + bar * vel_step)

        for beat in range(4):
            beat_time: float = time + beat
            vel: int = clamp_velocity(current_vel if beat == 0 else current_vel - 15)
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, beat_time, 0.25, vel)

            # Second 8th note only after first few bars
            if bar >= 3:
                midi.addNote(
                    CH_TIMPANI, CH_TIMPANI, E2, beat_time + 0.5, 0.25, clamp_velocity(vel - 25)
                )


# =============================================================================
# THE DRONE - Organ and strings creating ambient dread
# =============================================================================


def add_organ_drone(
    midi: MidiType,
    start_bar: int,
    num_bars: int,
    notes: list[int],
    velocity: int = 45,
) -> None:
    """Sustained organ tones - the hollow grandeur of the state.

    The organ represents propaganda: impressive on the surface,
    empty underneath. Long tones that never resolve.
    """
    for bar in range(num_bars):
        time: float = (start_bar + bar) * 4.0

        for note in notes:
            midi.addNote(CH_ORGAN, CH_ORGAN, note, time, 4.0, clamp_velocity(velocity))


def add_tritone_drone(
    midi: MidiType,
    start_bar: int,
    num_bars: int,
    velocity: int = 40,
) -> None:
    """The devil's interval - E and Bb - unresolved contradiction.

    The tritone was called "diabolus in musica" - the devil in music.
    It creates tension that demands resolution but never receives it.
    This is the sound of a system that cannot sustain itself.
    """
    time: float = start_bar * 4.0
    duration: float = num_bars * 4.0

    midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, duration, clamp_velocity(velocity))
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, time, duration, clamp_velocity(velocity - 5))


def add_anxiety_strings(
    midi: MidiType,
    start_bar: int,
    num_bars: int,
    velocity_base: int = 50,
    include_high: bool = False,
) -> None:
    """Tremolo strings - the constant hum of low-grade anxiety.

    These strings never rest. They represent the permanent state
    of alertness required when living under surveillance.
    """
    for bar in range(num_bars):
        time: float = (start_bar + bar) * 4.0

        # Low strings - constant presence
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 4.0, clamp_velocity(velocity_base))
        midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 4.0, clamp_velocity(velocity_base - 10))

        # High strings for extra tension
        if include_high and bar % 4 < 2:
            midi.addNote(CH_STRINGS, CH_STRINGS, E4, time, 2.0, clamp_velocity(velocity_base - 15))


def add_tritone_strings(
    midi: MidiType,
    start_bar: int,
    num_bars: int,
    velocity: int = 55,
) -> None:
    """Strings playing the tritone - rising dread."""
    for bar in range(num_bars):
        time: float = (start_bar + bar) * 4.0
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 4.0, clamp_velocity(velocity))
        midi.addNote(CH_STRINGS, CH_STRINGS, Bb3, time, 4.0, clamp_velocity(velocity - 10))


# =============================================================================
# STATE VIOLENCE - Sudden brass interventions
# =============================================================================


def add_brass_stab(
    midi: MidiType,
    bar: int,
    beat: float,
    notes: list[int],
    velocity: int = 110,
    duration: float = 0.5,
) -> None:
    """A sudden brass stab - the moment the state acts.

    State violence is sudden, overwhelming, and brief.
    These stabs should INTERRUPT the texture, not blend into it.
    """
    time: float = bar * 4.0 + beat

    for note in notes:
        midi.addNote(CH_BRASS, CH_BRASS, note, time, duration, clamp_velocity(velocity))


def add_brass_crescendo(
    midi: MidiType,
    start_bar: int,
    notes: list[int],
    start_vel: int = 50,
    end_vel: int = 127,
    duration_bars: int = 2,
) -> None:
    """Brass crescendo - the state showing its power."""
    time: float = start_bar * 4.0
    duration: float = duration_bars * 4.0

    for note in notes:
        midi.addNote(CH_BRASS, CH_BRASS, note, time, duration, clamp_velocity(end_vel))

    # Add crescendo marking via controller (CC 7 = volume, CC 11 = expression)
    # Note: Pure MIDI note events don't have true crescendo, so we approximate
    # by adding layered notes at different velocities
    for step in range(4):
        step_time: float = time + step * (duration / 4)
        step_vel: int = int(start_vel + (end_vel - start_vel) * (step / 4))
        for note in notes:
            midi.addNote(
                CH_BRASS, CH_BRASS, note, step_time, duration / 4, clamp_velocity(step_vel)
            )


# =============================================================================
# SECTION COMPOSERS
# =============================================================================


def section_a_awakening(midi: MidiType) -> None:
    """SECTION A: The Machine Awakens (bars 0-17)

    The surveillance apparatus boots up. Systems coming online one by one.
    Sparse, quiet, building slowly. The dread is not yet obvious.

    Musical Elements:
    - Organ drone fades in (E5 power chord)
    - Timpani enters gradually (bar 6)
    - Harpsichord mechanical figure enters (bar 10)
    - First surveillance pings (bar 14)
    - Strings enter last (bar 8)

    Dynamic Arc: pp -> mp (30 -> 70)
    """
    # === ORGAN: The machine hum (fades in over 8 bars) ===
    for bar in range(SECTION_A_END):
        time: float = bar * 4.0
        vel: int = clamp_velocity(25 + bar * 3)  # 25 -> 76 over 18 bars

        # Start with just E2 (pure, hollow)
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4.0, vel)

        # Add fifth at bar 4
        if bar >= 4:
            midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4.0, clamp_velocity(vel - 10))

    # === TIMPANI: The clock starts (bar 6) ===
    add_timpani_buildup(midi, 6, SECTION_A_END - 6, start_vel=35, end_vel=70)

    # === STRINGS: Ambient anxiety (bar 8) ===
    for bar in range(8, SECTION_A_END):
        time: float = bar * 4.0
        vel: int = clamp_velocity(35 + (bar - 8) * 3)
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 4.0, vel)
        if bar >= 12:
            midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 4.0, clamp_velocity(vel - 10))

    # === HARPSICHORD: Mechanical figure (bar 10) ===
    for bar in range(10, SECTION_A_END):
        vel: int = clamp_velocity(45 + (bar - 10) * 3)
        add_machine_pulse(midi, bar, 1, velocity_base=vel)

    # === HARPSICHORD: First surveillance pings (bar 14) ===
    add_surveillance_pings(midi, 14, SECTION_A_END - 14, velocity_base=50)


def section_b_operation(midi: MidiType) -> None:
    """SECTION B: Full Operation (bars 18-41)

    All surveillance systems are now online. The machine runs at full capacity.
    Patterns interlock. The dread note (F) becomes more prominent.

    Musical Elements:
    - Full timpani clock (continuous)
    - Harpsichord in two octaves
    - Regular surveillance pings
    - Strings sustain
    - First brass stabs (bars 26, 34) - random security interventions
    - Organ adds the dread note F at bar 30

    Dynamic Arc: mp -> mf (60 -> 85)
    """
    section_length: int = SECTION_B_END - SECTION_B_START

    # === TIMPANI: Full jackboot rhythm ===
    add_jackboot_clock(midi, SECTION_B_START, section_length, velocity_base=75)

    # === ORGAN: Drone with dread note appearing ===
    for bar in range(SECTION_B_START, SECTION_B_END):
        time: float = bar * 4.0

        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4.0, 50)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4.0, 42)

        # Dread note creeps in (bar 30+)
        if bar >= 30:
            midi.addNote(CH_ORGAN, CH_ORGAN, F2, time, 4.0, 35)

    # === HARPSICHORD: Two-layer mechanical pattern ===
    for bar in range(SECTION_B_START, SECTION_B_END):
        relative_bar: int = bar - SECTION_B_START

        # Lower octave every bar
        add_machine_pulse(midi, bar, 1, velocity_base=70)

        # Upper octave every other bar (watchtower layer)
        if relative_bar % 2 == 1:
            add_upper_machine_pulse(midi, bar, 1, velocity_base=60)

    # === HARPSICHORD: Surveillance pings ===
    add_surveillance_pings(midi, SECTION_B_START, section_length, velocity_base=60)

    # === STRINGS: Sustained anxiety ===
    add_anxiety_strings(midi, SECTION_B_START, section_length, velocity_base=55)

    # === BRASS: Security interventions ===
    # Bar 26: First stab - the state reminds you it is watching
    add_brass_stab(midi, 26, 0.0, [E3, B3, E4], velocity=100, duration=0.5)

    # Bar 34: Second stab - with dread note
    add_brass_stab(midi, 34, 0.0, [E3, B3, F4], velocity=105, duration=0.5)

    # Bar 40: Third stab - tritone hint (things are about to escalate)
    add_brass_stab(midi, 40, 0.0, [E3, Bb3, E4], velocity=95, duration=0.75)


def section_c_intensify(midi: MidiType) -> None:
    """SECTION C: Surveillance Intensifies (bars 42-71)

    The tension peaks. The tritone becomes dominant.
    Brass stabs become more frequent and violent.
    The machine shows its true face.

    Musical Elements:
    - Timpani adds 16th note subdivisions
    - Harpsichord patterns become denser (ghost notes)
    - Dense surveillance pings
    - Tritone drone replaces open fifth
    - Strings on tritone
    - Multiple brass stabs culminating in fortissimo

    Dynamic Arc: mf -> fff (75 -> 127)
    """
    section_length: int = SECTION_C_END - SECTION_C_START

    # === TIMPANI: Aggressive rhythm with 16ths ===
    add_jackboot_clock(midi, SECTION_C_START, section_length, velocity_base=85, include_16ths=True)

    # === ORGAN: Tritone drone (the devil's interval) ===
    add_tritone_drone(midi, SECTION_C_START, section_length, velocity=50)

    # === HARPSICHORD: Dense mechanical patterns ===
    for bar in range(SECTION_C_START, SECTION_C_END):
        relative_bar: int = bar - SECTION_C_START
        vel: int = clamp_velocity(72 + relative_bar)

        # Main mechanical figure with ghost notes
        add_machine_pulse(midi, bar, 1, velocity_base=vel, include_ghost_notes=True)

        # Upper layer alternating
        if relative_bar % 2 == 1:
            add_upper_machine_pulse(midi, bar, 1, velocity_base=vel - 10)

    # === HARPSICHORD: Dense surveillance ===
    add_surveillance_pings(midi, SECTION_C_START, section_length, velocity_base=70, dense=True)

    # === STRINGS: Tritone anxiety ===
    add_tritone_strings(midi, SECTION_C_START, section_length, velocity=65)

    # Additional high strings for tension (bar 54+)
    for bar in range(54, SECTION_C_END):
        time: float = bar * 4.0
        midi.addNote(CH_STRINGS, CH_STRINGS, E4, time, 2.0, 50)
        if bar >= 62:
            midi.addNote(CH_STRINGS, CH_STRINGS, Bb4, time, 2.0, 45)

    # === BRASS: Escalating violence ===

    # Bar 48: Warning shot
    add_brass_stab(midi, 48, 0.0, [E3, B3, E4], velocity=105, duration=0.5)

    # Bar 54: Dread chord
    add_brass_stab(midi, 54, 0.0, [F3, C4, F4], velocity=115, duration=0.5)

    # Bar 58: Double stab (syncopated aggression)
    add_brass_stab(midi, 58, 0.0, [E3, B3, E4], velocity=110, duration=0.25)
    add_brass_stab(midi, 58, 0.5, [F3, B3, F4], velocity=108, duration=0.25)

    # Bar 62: Tritone power chord
    add_brass_stab(midi, 62, 0.0, [E3, Bb3, E4], velocity=120, duration=0.75)

    # Bar 66: Full dread (E-F-Bb - maximum dissonance)
    add_brass_stab(midi, 66, 0.0, [E3, F3, Bb3, E4], velocity=125, duration=1.0)

    # Bar 70: THE MOMENT - maximum state violence
    add_brass_stab(midi, 70, 0.0, [E3, Bb3, E4, Bb4], velocity=127, duration=1.5)


def section_d_eternal(midi: MidiType) -> None:
    """SECTION D: The Eternal Watch (bars 72-89)

    The machine returns to equilibrium. Not resolution - it simply continues.
    The violence subsides but the surveillance never stops.
    The ending is not an ending - we simply stop listening.

    Musical Elements:
    - Timpani returns to steady pattern (no 16ths)
    - Organ returns to open fifth (false resolution)
    - Harpsichord simplifies to single layer
    - Surveillance pings continue indefinitely
    - One final brass chord (bar 88) - reminder of power
    - Fade out (velocity decrease) but pattern continues to last bar

    Dynamic Arc: fff -> mp fade (100 -> 65)
    """
    # === TIMPANI: Steady march continues ===
    for bar in range(SECTION_D_START, SECTION_D_END):
        relative_bar: int = bar - SECTION_D_START
        # Gradual velocity decrease
        vel: int = clamp_velocity(85 - relative_bar)
        add_jackboot_clock(midi, bar, 1, velocity_base=vel)

    # === ORGAN: Return to open fifth (false stability) ===
    for bar in range(SECTION_D_START, SECTION_D_END):
        time: float = bar * 4.0
        relative_bar: int = bar - SECTION_D_START
        vel: int = clamp_velocity(55 - relative_bar)

        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4.0, vel)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4.0, clamp_velocity(vel - 10))

    # === HARPSICHORD: Simplified mechanical figure ===
    for bar in range(SECTION_D_START, SECTION_D_END):
        relative_bar: int = bar - SECTION_D_START
        vel: int = clamp_velocity(70 - relative_bar)
        add_machine_pulse(midi, bar, 1, velocity_base=vel)

    # === HARPSICHORD: Persistent surveillance ===
    for bar in range(SECTION_D_START, SECTION_D_END):
        relative_bar: int = bar - SECTION_D_START
        vel: int = clamp_velocity(60 - relative_bar // 2)
        add_surveillance_pings(midi, bar, 1, velocity_base=vel)

    # === STRINGS: Low anxiety fading ===
    for bar in range(SECTION_D_START, SECTION_D_END):
        time: float = bar * 4.0
        relative_bar: int = bar - SECTION_D_START
        vel: int = clamp_velocity(55 - relative_bar)

        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 4.0, vel)
        midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 4.0, clamp_velocity(vel - 10))

    # === BRASS: Final reminder (bar 88) ===
    # One last chord - the apparatus remains. It always remains.
    add_brass_stab(midi, 88, 0.0, [E3, B3, E4], velocity=85, duration=2.0)


# =============================================================================
# MAIN COMPOSITION
# =============================================================================


def create_the_apparatus() -> MidiType:
    """Generate 'The Apparatus' - the sound of the surveillance state.

    This composition represents the fascist faction's core identity:
    cold, mechanical, all-seeing, indifferent. The player should feel
    watched, measured, categorized.

    The music does not threaten directly - it creates ambient dread.
    The violence is implied, occasional, sudden when it comes.
    Mostly, there is just the machine. Watching. Waiting. Forever.

    Returns:
        MIDIFile: The complete composition
    """
    midi = create_midi(5)
    setup_standard_tracks(midi, TEMPO)

    # Build the composition section by section
    section_a_awakening(midi)
    section_b_operation(midi)
    section_c_intensify(midi)
    section_d_eternal(midi)

    return midi


def main() -> None:
    """Generate and save The Apparatus."""
    midi = create_the_apparatus()
    save_midi(midi, "01_the_apparatus.mid", TEMPO, TOTAL_BARS)

    print()
    print("=" * 60)
    print("THE APPARATUS")
    print("=" * 60)
    print()
    print("Track 01 of the Fascist Faction Soundtrack")
    print()
    print("Tempo: 72 BPM | Key: E Phrygian | Duration: 5:00")
    print()
    print("The machine awakens. The machine watches. The machine waits.")
    print("It does not hate you. It does not care.")
    print("That is worse.")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
