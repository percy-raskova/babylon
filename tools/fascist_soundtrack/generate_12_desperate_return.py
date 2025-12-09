#!/usr/bin/env python3
"""
Track 12: "Desperate Return" (4:00)
Mood: FRANTIC - Desperate, no escape, the machine must continue

The machine reasserts itself after glimpsing the void.
They CANNOT stop. The system must continue.

Musical approach:
- Follows "The Void" - the regime clawing back
- Timpani clock RESTARTS frantically
- Harpsichord patterns return with desperate energy
- Building to overwhelming mechanical reassertion
- Abrupt non-ending (must continue forever)

Tempo: 116 BPM | Key: E Phrygian
Target duration: 4:00 (~116 bars at 116 BPM)
"""

from . import (
    A3,
    B2,
    B3,
    B4,
    CH_BRASS,
    CH_HARPSI,
    CH_ORGAN,
    CH_STRINGS,
    CH_TIMPANI,
    E2,
    E3,
    E4,
    E5,
    F3,
    G3,
    G4,
    Bb2,
    create_midi,
    save_midi,
    setup_standard_tracks,
)

TEMPO = 116
TOTAL_BARS = 116  # ~4:00 at 116 BPM


def create_desperate_return():
    """Generate Desperate Return - the machine must not stop."""
    midi = create_midi(5)
    setup_standard_tracks(midi, TEMPO)

    # === SECTION A: The Silence Before (bars 1-16) ===
    section_a_silence(midi)

    # === SECTION B: Desperate Restart (bars 17-48) ===
    section_b_restart(midi)

    # === SECTION C: Frantic Reassertion (bars 49-88) ===
    section_c_frantic(midi)

    # === SECTION D: The Machine Continues (bars 89-116) ===
    section_d_continues(midi)

    return midi


def section_a_silence(midi):
    """The silence after the void - but it cannot last."""

    # Organ - tritone remnant from the void
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, 0, 32, 30)
    midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, 0, 32, 25)

    # Strings - trembling in the silence
    midi.addNote(CH_STRINGS, CH_STRINGS, E4, 8, 16, 30)
    midi.addNote(CH_STRINGS, CH_STRINGS, E3, 24, 8, 25)

    # Harpsichord - hesitant, trying to restart
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, 16, 2, 35)
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, 24, 2, 40)
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, 32, 2, 45)

    # First mechanical pattern attempt at bar 10
    time = 40
    pattern = [E3, F3, E3]
    for i, note in enumerate(pattern):
        midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 1, 0.75, 50)

    # Timpani - first attempts at clock
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, 32, 0.5, 35)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, 40, 0.5, 40)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, 48, 0.5, 45)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, 56, 0.5, 50)


def section_b_restart(midi):
    """Desperate restart - NO! Don't stop! The machine must continue!"""

    base_bar = 16

    # Timpani - clock RESTARTS frantically
    for bar in range(32):
        time = (base_bar + bar) * 4

        # Building intensity
        vel_base = min(55 + bar * 2, 95)

        for beat in range(4):
            vel = vel_base if beat == 0 else vel_base - 20
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, vel)
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat + 0.5, 0.25, vel - 25)

    # Harpsichord - mechanical pattern returns LOUDER, more desperate
    for bar in range(32):
        time = (base_bar + bar) * 4
        vel = min(60 + bar * 2, 85)

        pattern = [E3, F3, E3, G3, E3, F3, E3, A3]
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, vel)

    # Organ - returning foundation
    for bar in range(16, 32):
        time = (base_bar + bar) * 4
        vel = 40 + (bar - 16) * 2

        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, min(vel, 60))
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, min(vel - 10, 50))

    # Strings - anxiety but with determination
    for bar in range(32):
        time = (base_bar + bar) * 4
        vel = 45 + bar

        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 4, min(vel, 70))
        if bar >= 16:
            midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 4, min(vel - 10, 60))

    # Brass - state reasserts itself
    brass_bars = [8, 16, 24, 28]
    for bar in brass_bars:
        time = (base_bar + bar) * 4
        vel = 70 + bar

        midi.addNote(CH_BRASS, CH_BRASS, E3, time, 1, min(vel, 95))
        midi.addNote(CH_BRASS, CH_BRASS, B3, time, 1, min(vel - 5, 90))
        midi.addNote(CH_BRASS, CH_BRASS, E4, time, 1, min(vel - 10, 85))


def section_c_frantic(midi):
    """Frantic reassertion - maximum mechanical energy."""

    base_bar = 48

    # Timpani - relentless, desperate
    for bar in range(40):
        time = (base_bar + bar) * 4

        for beat in range(4):
            vel = 100 if beat == 0 else 75
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, vel)
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat + 0.5, 0.25, vel - 30)

        # Extra urgency every 4 bars
        if bar % 4 == 3:
            midi.addNote(CH_TIMPANI, CH_TIMPANI, B2, time + 3.5, 0.25, 70)

    # Harpsichord - frantic patterns
    for bar in range(40):
        time = (base_bar + bar) * 4

        # Main pattern - desperate energy
        pattern = [E3, F3, E3, G3, E3, F3, E3, A3]
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.35, 85)

        # Counter pattern
        if bar % 2 == 1:
            counter = [E4, G4, E4, B3]
            for i, note in enumerate(counter):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + 0.25 + i * 0.5, 0.3, 70)

    # Organ - full foundation
    for bar in range(40):
        time = (base_bar + bar) * 4
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 65)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, 55)
        midi.addNote(CH_ORGAN, CH_ORGAN, E3, time, 4, 50)

    # Strings - tremolo anxiety with determination
    for bar in range(40):
        time = (base_bar + bar) * 4

        midi.addNote(CH_STRINGS, CH_STRINGS, E4, time, 4, 70)
        midi.addNote(CH_STRINGS, CH_STRINGS, B4, time, 4, 65)

        # High anxiety notes
        if bar % 4 >= 2:
            midi.addNote(CH_STRINGS, CH_STRINGS, E5, time, 4, 65)

    # Low strings
    for bar in range(0, 40, 4):
        time = (base_bar + bar) * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 16, 60)

    # Brass - constant reassertion
    for bar in range(40):
        time = (base_bar + bar) * 4

        if bar % 4 == 0:
            # Power chord
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 1.5, 100)
            midi.addNote(CH_BRASS, CH_BRASS, B3, time, 1.5, 95)
            midi.addNote(CH_BRASS, CH_BRASS, E4, time, 1.5, 90)

        if bar % 8 == 4:
            # Additional stab
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 0.5, 95)
            midi.addNote(CH_BRASS, CH_BRASS, E4, time, 0.5, 90)


def section_d_continues(midi):
    """The machine continues - it cannot stop, it will not stop."""

    base_bar = 88

    # Timpani - eternal clock
    for bar in range(28):
        time = (base_bar + bar) * 4

        # No fade - the clock continues
        for beat in range(4):
            vel = 95 if beat == 0 else 70
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, vel)
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat + 0.5, 0.25, vel - 25)

    # Harpsichord - eternal mechanical pattern
    for bar in range(28):
        time = (base_bar + bar) * 4

        pattern = [E3, F3, E3, G3, E3, F3, E3, A3]
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, 82)

    # Organ - sustained
    for bar in range(28):
        time = (base_bar + bar) * 4
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 60)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, 50)

    # Strings - continuous
    for bar in range(28):
        time = (base_bar + bar) * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E4, time, 4, 65)
        midi.addNote(CH_STRINGS, CH_STRINGS, B4, time, 4, 60)

    for bar in range(0, 28, 4):
        time = (base_bar + bar) * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 16, 55)

    # Brass - final statements
    brass_bars = [0, 8, 16, 24]
    for bar in brass_bars:
        time = (base_bar + bar) * 4

        midi.addNote(CH_BRASS, CH_BRASS, E3, time, 1.5, 90)
        midi.addNote(CH_BRASS, CH_BRASS, B3, time, 1.5, 85)
        midi.addNote(CH_BRASS, CH_BRASS, E4, time, 1.5, 80)

    # ABRUPT END - mid phrase
    # The final notes at bar 116 just... stop
    # But the machine continues (implied)
    # We simply stop listening - the machine never stops

    # Final bar - maximum energy, cut off abruptly
    time = (TOTAL_BARS - 1) * 4
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.25, 100)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 0.5, 0.25, 70)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 1, 0.25, 95)
    # Cut - the clock continues, we stop listening

    midi.addNote(CH_HARPSI, CH_HARPSI, E3, time, 0.5, 85)
    midi.addNote(CH_HARPSI, CH_HARPSI, F3, time + 0.5, 0.5, 85)
    midi.addNote(CH_HARPSI, CH_HARPSI, E3, time + 1, 0.5, 85)
    # Cut - mid phrase

    midi.addNote(CH_BRASS, CH_BRASS, E3, time, 0.5, 95)
    midi.addNote(CH_BRASS, CH_BRASS, E4, time, 0.5, 90)
    # Cut


def main():
    """Generate and save Desperate Return."""
    midi = create_desperate_return()
    save_midi(midi, "12_desperate_return.mid", TEMPO, TOTAL_BARS)
    print()
    print("DESPERATE RETURN")
    print("The machine must continue.")
    print("They cannot stop.")
    print("[ABRUPT CUT]")


if __name__ == "__main__":
    main()
