#!/usr/bin/env python3
"""
Track 04: "Repression Protocol" (6:00)
Mood: MENACING - Overwhelming, crushing, relentless

State violence in action - crushing dissent.
The bureaucratic machinery of repression at work.

Musical approach:
- Aggressive brass dominance (the jackboot)
- Relentless timpani (the clock cannot be stopped)
- Strings in distress (representing victims)
- Mechanical harpsichord (bureaucracy of violence)
- Sforzando dynamics (sudden overwhelming force)

Tempo: 116 BPM | Key: E Phrygian with tritones
Target duration: 6:00 (~174 bars at 116 BPM)
"""

from . import (
    A3,
    B2,
    B3,
    B5,
    C5,
    CH_BRASS,
    CH_DRUMS,
    CH_HARPSI,
    CH_ORGAN,
    CH_STRINGS,
    CH_TIMPANI,
    DRUM_CRASH,
    E2,
    E3,
    E4,
    E5,
    F3,
    F4,
    F5,
    G3,
    G4,
    G5,
    Bb2,
    Bb3,
    Bb4,
    create_midi,
    save_midi,
    setup_standard_tracks,
)

TEMPO = 116
TOTAL_BARS = 174  # ~6:00 at 116 BPM


def create_repression_protocol():
    """Generate Repression Protocol - state violence crushing dissent."""
    midi = create_midi(6)
    setup_standard_tracks(midi, TEMPO)

    # === SECTION A: Protocol Initiates (bars 1-36) ===
    section_a_initiates(midi)

    # === SECTION B: Full Repression (bars 37-84) ===
    section_b_full_repression(midi)

    # === SECTION C: Crushing (bars 85-132) ===
    section_c_crushing(midi)

    # === SECTION D: Silence Imposed (bars 133-174) ===
    section_d_silence(midi)

    return midi


def section_a_initiates(midi):
    """Protocol initiates - the machinery of repression awakens."""

    # Timpani - official, relentless
    for bar in range(36):
        time = bar * 4
        vel = min(50 + bar * 2, 90)

        # Bureaucratic rhythm
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, vel)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 1, 0.25, vel - 20)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, vel - 5)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3, 0.25, vel - 15)

    # Harpsichord - mechanical bureaucracy
    for bar in range(8, 36):
        time = bar * 4
        vel = min(55 + (bar - 8), 72)

        # Typewriter-like pattern
        pattern = [E3, E3, E3, F3, E3, E3, G3, E3]
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.35, vel)

    # Organ - ominous presence
    for bar in range(16, 36):
        time = bar * 4
        vel = 40 + (bar - 16)
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, vel)
        if bar >= 24:
            midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, time, 4, vel - 10)  # Tritone

    # Strings - tension building
    for bar in range(0, 36, 4):
        time = bar * 4
        vel = 40 + bar
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 16, min(vel, 60))

    # Brass - warning announcements
    brass_warnings = [20, 28, 32]
    for bar in brass_warnings:
        time = bar * 4
        vel = 70 + (bar - 20) * 2
        midi.addNote(CH_BRASS, CH_BRASS, E3, time, 1, vel)
        midi.addNote(CH_BRASS, CH_BRASS, B3, time, 1, vel - 5)
        midi.addNote(CH_BRASS, CH_BRASS, E4, time + 2, 1, vel + 5)


def section_b_full_repression(midi):
    """Full repression mode - overwhelming force."""

    base_bar = 36

    # Timpani - relentless, unstoppable
    for bar in range(48):
        time = (base_bar + bar) * 4

        # Heavy, mechanical rhythm
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, 100)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 0.5, 0.25, 70)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 1, 0.25, 75)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 1.5, 0.25, 70)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, 95)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, B2, time + 2.5, 0.25, 65)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3, 0.25, 80)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3.5, 0.25, 70)

    # Brass - dominant, violent
    for bar in range(48):
        time = (base_bar + bar) * 4

        # Every bar has brass presence
        if bar % 4 == 0:
            # Power chord
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 2, 100)
            midi.addNote(CH_BRASS, CH_BRASS, B3, time, 2, 95)
            midi.addNote(CH_BRASS, CH_BRASS, E4, time, 2, 90)
        elif bar % 4 == 2:
            # Shorter stab
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 0.5, 95)
            midi.addNote(CH_BRASS, CH_BRASS, E4, time, 0.5, 90)
        elif bar % 2 == 1:
            # Off-beat violence
            midi.addNote(CH_BRASS, CH_BRASS, E3, time + 2, 0.5, 90)
            midi.addNote(CH_BRASS, CH_BRASS, B3, time + 2, 0.5, 85)

        # Tritone threat every 8 bars
        if bar % 8 == 4:
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 1, 100)
            midi.addNote(CH_BRASS, CH_BRASS, Bb3, time, 1, 95)  # Tritone
            midi.addNote(CH_BRASS, CH_BRASS, E4, time, 1, 90)

    # Organ - bureaucratic authority
    for bar in range(48):
        time = (base_bar + bar) * 4
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 60)
        if bar % 4 < 2:
            midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, 50)
        else:
            midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, time, 4, 50)  # Alternating tritone

    # Harpsichord - relentless bureaucracy
    for bar in range(48):
        time = (base_bar + bar) * 4

        # Mechanical pattern
        pattern = [E3, E3, F3, E3, G3, E3, F3, E3]
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, 75)

        # Upper octave counterpoint
        if bar % 2 == 1:
            counter = [E4, F4, E4, G4]
            for i, note in enumerate(counter):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.35, 65)

    # Strings - victims in distress
    distress_phrases = [
        (0, E5, 8, 70),
        (8, F5, 8, 75),  # Dread note - screaming
        (16, E5, 4, 70),
        (20, G5, 4, 72),
        (24, F5, 8, 78),  # Sustained dread
        (32, E5, 8, 70),
        (40, F5, 6, 72),
        (46, E5, 2, 65),
    ]
    for bar_offset, note, dur, vel in distress_phrases:
        time = (base_bar + bar_offset) * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, note, time, dur * 4, vel)

    # Low strings foundation
    for bar in range(0, 48, 4):
        time = (base_bar + bar) * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E2, time, 16, 55)


def section_c_crushing(midi):
    """The crushing - maximum violence, total suppression."""

    base_bar = 84

    # Timpani - brutal, overwhelming
    for bar in range(48):
        time = (base_bar + bar) * 4

        # Maximum intensity
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, 105)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 0.5, 0.25, 80)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 1, 0.25, 85)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 1.5, 0.25, 80)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, 100)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2.5, 0.25, 75)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3, 0.25, 90)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3.5, 0.25, 80)

        # Extra violence on accents
        if bar % 4 == 0:
            midi.addNote(CH_TIMPANI, CH_TIMPANI, B2, time, 0.5, 95)

    # Drums - crash accents
    for bar in range(48):
        time = (base_bar + bar) * 4
        if bar % 4 == 0:
            midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_CRASH, time, 1, 100)

    # Brass - constant assault
    for bar in range(48):
        time = (base_bar + bar) * 4

        # Sforzando on every bar
        midi.addNote(CH_BRASS, CH_BRASS, E3, time, 0.5, 105)
        midi.addNote(CH_BRASS, CH_BRASS, B3, time, 0.5, 100)
        midi.addNote(CH_BRASS, CH_BRASS, E4, time, 0.5, 95)

        # Additional violence
        if bar % 2 == 0:
            midi.addNote(CH_BRASS, CH_BRASS, E3, time + 2, 0.5, 100)
            midi.addNote(CH_BRASS, CH_BRASS, E4, time + 2, 0.5, 95)

        # Tritone assault every 4 bars
        if bar % 4 == 2:
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 1, 105)
            midi.addNote(CH_BRASS, CH_BRASS, Bb3, time, 1, 100)
            midi.addNote(CH_BRASS, CH_BRASS, E4, time, 1, 95)
            midi.addNote(CH_BRASS, CH_BRASS, Bb4, time, 1, 90)

    # Organ - full power
    for bar in range(48):
        time = (base_bar + bar) * 4
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 70)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, 60)
        midi.addNote(CH_ORGAN, CH_ORGAN, E3, time, 4, 55)

        # Tritone bass every 8 bars
        if bar % 8 >= 4:
            midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, time, 4, 55)

    # Harpsichord - frantic bureaucratic machinery
    for bar in range(48):
        time = (base_bar + bar) * 4

        # Double-time mechanical pattern
        pattern = [E3, F3, E3, G3, E3, F3, E3, A3, E3, F3, E3, G3, E3, F3, E3, B3]
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.25, 0.2, 80)

    # Strings - sustained screaming
    for bar in range(48):
        time = (base_bar + bar) * 4

        if bar % 8 < 4:
            midi.addNote(CH_STRINGS, CH_STRINGS, E5, time, 4, 75)
            midi.addNote(CH_STRINGS, CH_STRINGS, B5, time, 4, 70)
        else:
            midi.addNote(CH_STRINGS, CH_STRINGS, F5, time, 4, 78)  # Dread note
            midi.addNote(CH_STRINGS, CH_STRINGS, C5, time, 4, 72)

    # Low strings foundation
    for bar in range(0, 48, 2):
        time = (base_bar + bar) * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E2, time, 8, 60)


def section_d_silence(midi):
    """Silence imposed - the crushing is complete."""

    base_bar = 132

    # Timpani - slowing, but still present
    for bar in range(42):
        time = (base_bar + bar) * 4

        if bar < 20:
            # Still strong but fading
            vel = 90 - bar * 2
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, max(vel, 60))
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, max(vel - 10, 55))
        elif bar < 32:
            # Sparse
            vel = 60 - (bar - 20)
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 1, max(vel, 40))
        else:
            # Final heartbeats
            if bar % 2 == 0:
                midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 1, 35)

    # Brass - occasional reminders
    brass_reminder_bars = [0, 8, 16, 24, 32]
    for bar in brass_reminder_bars:
        if base_bar + bar < TOTAL_BARS:
            time = (base_bar + bar) * 4
            vel = 80 - bar * 2
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 1, max(vel, 50))
            midi.addNote(CH_BRASS, CH_BRASS, B3, time, 1, max(vel - 5, 45))

    # Final brass statement
    time = (base_bar + 36) * 4
    midi.addNote(CH_BRASS, CH_BRASS, E3, time, 2, 60)
    midi.addNote(CH_BRASS, CH_BRASS, B3, time, 2, 55)
    midi.addNote(CH_BRASS, CH_BRASS, E4, time, 2, 50)

    # Organ - fading authority
    for bar in range(0, 32, 4):
        time = (base_bar + bar) * 4
        vel = 55 - bar
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 16, max(vel, 30))

    # Harpsichord - mechanical continues slowly
    for bar in range(24):
        time = (base_bar + bar) * 4
        vel = 60 - bar * 2
        pattern = [E3, E3, F3, E3]
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i, 0.75, max(vel, 35))

    # Strings - the silence after violence
    for bar in range(0, 32, 8):
        time = (base_bar + bar) * 4
        vel = 50 - bar
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 32, max(vel, 25))

    # Final tritone - the violence always lurks
    time = (TOTAL_BARS - 4) * 4
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 16, 35)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, time, 16, 30)  # Tritone remains


def main():
    """Generate and save Repression Protocol."""
    midi = create_repression_protocol()
    save_midi(midi, "04_repression_protocol.mid", TEMPO, TOTAL_BARS)
    print()
    print("REPRESSION PROTOCOL")
    print("The bureaucracy of violence.")
    print("Silence is imposed.")


if __name__ == "__main__":
    main()
