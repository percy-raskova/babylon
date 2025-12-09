#!/usr/bin/env python3
"""
Track 09: "The Juggling Act" (5:30)
Mood: DESPERATE - Frantic, barely-controlled, spinning plates

The regime barely holding together - a thousand spinning plates.
This is the anxious reality behind the facade of power.

Musical approach:
- Most chaotic track - irregular meters (5/4, 7/8, 9/8)
- Multiple independent melodic lines almost colliding
- Frantic harpsichord patterns
- Brass stabs as desperate interventions
- High tempo, constant tension

Tempo: 120 BPM | Key: E Phrygian
Target duration: 5:30 (~165 bars at 120 BPM)
"""

from . import (
    A3,
    B2,
    B3,
    B4,
    C4,
    CH_BRASS,
    CH_HARPSI,
    CH_ORGAN,
    CH_STRINGS,
    CH_TIMPANI,
    D3,
    D4,
    E2,
    E3,
    E4,
    E5,
    F3,
    F5,
    G3,
    G5,
    Bb3,
    create_midi,
    save_midi,
    setup_standard_tracks,
)

TEMPO = 120
TOTAL_BARS = 165  # ~5:30 at 120 BPM


def create_juggling_act():
    """Generate The Juggling Act - spinning plates about to fall."""
    midi = create_midi(5)
    setup_standard_tracks(midi, TEMPO)

    # === SECTION A: Plates Start Spinning (bars 1-36) ===
    section_a_spinning(midi)

    # === SECTION B: Full Juggle (bars 37-84) ===
    section_b_juggle(midi)

    # === SECTION C: Almost Dropping (bars 85-132) ===
    section_c_almost(midi)

    # === SECTION D: Desperate Recovery (bars 133-165) ===
    section_d_recovery(midi)

    return midi


def section_a_spinning(midi):
    """The plates start spinning - building complexity."""

    # Harpsichord - starting patterns
    for bar in range(36):
        time = bar * 4

        if bar < 12:
            # Simple start - building
            vel = 60 + bar
            pattern = [E3, F3, E3, G3, E3, F3, E3, A3]
            for i, note in enumerate(pattern):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, min(vel, 75))

        elif bar < 24:
            # 5/4 patterns emerge
            vel = 72
            pattern_5 = [E3, F3, G3, A3, B3]
            for i, note in enumerate(pattern_5):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.8, 0.6, vel)
            # Fill remaining time
            midi.addNote(CH_HARPSI, CH_HARPSI, E4, time + 4 - 0.5, 0.4, vel - 5)

        else:
            # 7/8 patterns
            vel = 75
            pattern_7 = [E3, F3, E3, G3, E3, A3, E3]
            for i, note in enumerate(pattern_7):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.57, 0.5, vel)

    # Timpani - irregular heartbeat
    for bar in range(12, 36):
        time = bar * 4
        vel = 55 + bar - 12

        if bar % 3 == 0:
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, min(vel, 80))
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 1.5, 0.25, min(vel - 15, 65))
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2.5, 0.5, min(vel - 5, 75))
        elif bar % 3 == 1:
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 0.5, 0.5, min(vel - 5, 75))
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, min(vel, 80))
        else:
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, min(vel, 80))
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.25, min(vel - 10, 70))
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3, 0.25, min(vel - 10, 70))

    # Strings - building tension
    for bar in range(16, 36):
        time = bar * 4
        vel = 45 + (bar - 16)

        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 4, min(vel, 65))
        if bar >= 24:
            midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 4, min(vel - 10, 55))

    # Organ - undercurrent
    for bar in range(24, 36):
        time = bar * 4
        vel = 40 + (bar - 24)

        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, vel)


def section_b_juggle(midi):
    """Full juggle - maximum complexity, almost colliding patterns."""

    base_bar = 36

    # Multiple harpsichord patterns running simultaneously
    for bar in range(48):
        time = (base_bar + bar) * 4

        # Pattern 1: 5/4 ascending (one voice)
        if bar % 4 < 2:
            p1 = [E3, F3, G3, A3, B3]
            for i, note in enumerate(p1):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.8, 0.6, 75)

        # Pattern 2: 7/8 descending (another voice)
        if bar % 4 >= 2:
            p2 = [E4, D4, C4, B3, A3, G3, F3]
            for i, note in enumerate(p2):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.57, 0.5, 72)

        # Counter-pattern (always running)
        counter = [E3, E4, E3, E4] if bar % 2 == 0 else [E4, E3, E4, E3]
        for i, note in enumerate(counter):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + 0.25 + i * 0.75, 0.5, 65)

    # Timpani - chaotic but trying to maintain order
    for bar in range(48):
        time = (base_bar + bar) * 4

        # Different irregular patterns
        if bar % 5 == 0:
            beats = [0, 0.75, 1.5, 2.5, 3.25]
        elif bar % 5 == 1:
            beats = [0, 0.5, 1.25, 2, 3, 3.5]
        elif bar % 5 == 2:
            beats = [0, 1, 1.75, 2.5, 3.25]
        elif bar % 5 == 3:
            beats = [0.25, 0.75, 1.5, 2.25, 3, 3.75]
        else:
            beats = [0, 0.5, 1.5, 2, 2.75, 3.5]

        for beat in beats:
            vel = 85 if beat in [0, 2] else 65
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, vel)

    # Strings - two independent lines almost colliding
    for bar in range(48):
        time = (base_bar + bar) * 4

        # High strings - anxious melody
        if bar % 4 == 0:
            midi.addNote(CH_STRINGS, CH_STRINGS, E5, time, 2, 70)
            midi.addNote(CH_STRINGS, CH_STRINGS, F5, time + 2, 2, 72)
        elif bar % 4 == 1:
            midi.addNote(CH_STRINGS, CH_STRINGS, G5, time, 2, 68)
            midi.addNote(CH_STRINGS, CH_STRINGS, E5, time + 2, 2, 70)
        elif bar % 4 == 2:
            midi.addNote(CH_STRINGS, CH_STRINGS, F5, time, 3, 72)  # Dread note held
        else:
            midi.addNote(CH_STRINGS, CH_STRINGS, E5, time, 4, 68)

        # Low strings - counter movement
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 4, 60)
        if bar % 2 == 1:
            midi.addNote(CH_STRINGS, CH_STRINGS, B3, time + 2, 2, 55)

    # Brass - desperate interventions
    intervention_bars = [4, 12, 20, 28, 36, 44]
    for bar in intervention_bars:
        time = (base_bar + bar) * 4

        # Quick stabs - trying to keep things together
        midi.addNote(CH_BRASS, CH_BRASS, E3, time, 0.25, 95)
        midi.addNote(CH_BRASS, CH_BRASS, B3, time, 0.25, 90)
        midi.addNote(CH_BRASS, CH_BRASS, E4, time, 0.25, 85)

        # Follow-up correction
        midi.addNote(CH_BRASS, CH_BRASS, E3, time + 0.5, 0.25, 85)
        midi.addNote(CH_BRASS, CH_BRASS, E4, time + 0.5, 0.25, 80)

    # Organ - trying to maintain foundation
    for bar in range(48):
        time = (base_bar + bar) * 4
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 55)


def section_c_almost(midi):
    """Almost dropping - maximum tension, near collapse."""

    base_bar = 84

    # Harpsichord - frantic, patterns breaking down
    for bar in range(48):
        time = (base_bar + bar) * 4

        # Alternating 5/4 and 7/8 creating polyrhythmic chaos
        if bar % 2 == 0:
            # 5/4 pattern
            p5 = [E3, F3, G3, A3, B3, C4, D4, E4]  # Extended
            for i, note in enumerate(p5):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, 80)
        else:
            # 7/8 against it
            p7 = [E4, D4, C4, B3, A3, G3, F3, E3, D3]  # Extended
            for i, note in enumerate(p7):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.44, 0.35, 78)

        # Constant 8ths trying to maintain
        for beat in range(8):
            midi.addNote(
                CH_HARPSI, CH_HARPSI, E3 if beat % 2 == 0 else E4, time + beat * 0.5, 0.25, 60
            )

    # Timpani - desperately irregular
    for bar in range(48):
        time = (base_bar + bar) * 4

        # Frantic pattern - almost random
        base_pattern = [0, 0.33, 0.66, 1, 1.5, 2, 2.33, 2.75, 3, 3.5, 3.75]
        for i, beat in enumerate(base_pattern):
            # Vary velocity wildly
            vel = 90 if i in [0, 5] else (75 if i % 2 == 0 else 60)
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.2, vel)

    # Strings - screaming high, groaning low
    for bar in range(48):
        time = (base_bar + bar) * 4

        # High strings - sustained anxiety
        midi.addNote(CH_STRINGS, CH_STRINGS, E5, time, 4, 75)
        if bar % 2 == 1:
            midi.addNote(CH_STRINGS, CH_STRINGS, F5, time, 4, 78)  # Dread layer

        # Low strings - groaning
        midi.addNote(CH_STRINGS, CH_STRINGS, E2, time, 4, 65)
        midi.addNote(CH_STRINGS, CH_STRINGS, B2, time, 4, 55)

    # Brass - constant interventions (barely holding)
    for bar in range(48):
        time = (base_bar + bar) * 4

        if bar % 2 == 0:
            # Quick fix stab
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 0.25, 100)
            midi.addNote(CH_BRASS, CH_BRASS, E4, time, 0.25, 95)

        if bar % 4 == 2:
            # Panicked correction
            midi.addNote(CH_BRASS, CH_BRASS, E3, time + 2, 0.5, 95)
            midi.addNote(CH_BRASS, CH_BRASS, B3, time + 2, 0.5, 90)

        if bar % 8 == 6:
            # Tritone alarm - something went wrong
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 0.5, 100)
            midi.addNote(CH_BRASS, CH_BRASS, Bb3, time, 0.5, 95)

    # Organ - barely audible under chaos
    for bar in range(48):
        time = (base_bar + bar) * 4
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, 50)


def section_d_recovery(midi):
    """Desperate recovery - pulling it back together (barely)."""

    base_bar = 132

    # Harpsichord - forcing order back
    for bar in range(33):
        time = (base_bar + bar) * 4

        if bar < 16:
            # Still chaotic
            if bar % 2 == 0:
                p5 = [E3, F3, G3, A3, B3]
                for i, note in enumerate(p5):
                    midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.8, 0.6, 78)
            else:
                p7 = [E4, D4, C4, B3, A3, G3, F3]
                for i, note in enumerate(p7):
                    midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.57, 0.5, 75)
        else:
            # Forced return to mechanical order
            pattern = [E3, F3, E3, G3, E3, F3, E3, A3]
            for i, note in enumerate(pattern):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, 72)

    # Timpani - forcing regular rhythm
    for bar in range(33):
        time = (base_bar + bar) * 4

        if bar < 16:
            # Still irregular
            beats = [0, 0.75, 1.5, 2.25, 3] if bar % 2 == 0 else [0, 0.5, 1, 2, 2.75, 3.5]
            for beat in beats:
                vel = 85 if beat < 1 else 70
                midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, vel)
        else:
            # Forcing regularity
            for beat in range(4):
                vel = 85 if beat == 0 else 60
                midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, vel)
                midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat + 0.5, 0.25, vel - 25)

    # Strings - calming (forcibly)
    for bar in range(33):
        time = (base_bar + bar) * 4
        vel = 70 if bar < 16 else 60

        if bar < 16:
            midi.addNote(CH_STRINGS, CH_STRINGS, E5, time, 4, vel)
            midi.addNote(CH_STRINGS, CH_STRINGS, F5, time + 2, 2, vel + 5)
        else:
            midi.addNote(CH_STRINGS, CH_STRINGS, E4, time, 4, vel - 5)
            midi.addNote(CH_STRINGS, CH_STRINGS, B4, time, 4, vel - 10)

        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 4, vel - 15)

    # Brass - final interventions then steady
    for bar in range(33):
        time = (base_bar + bar) * 4

        if bar < 16 and bar % 4 == 0:
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 0.5, 90)
            midi.addNote(CH_BRASS, CH_BRASS, E4, time, 0.5, 85)
        elif bar >= 16 and bar % 8 == 0:
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 1, 80)
            midi.addNote(CH_BRASS, CH_BRASS, B3, time, 1, 75)

    # Organ - returning foundation
    for bar in range(33):
        time = (base_bar + bar) * 4
        vel = 50 if bar < 16 else 55
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, vel)

    # Final desperate statement
    time = (TOTAL_BARS - 4) * 4
    midi.addNote(CH_BRASS, CH_BRASS, E3, time, 2, 85)
    midi.addNote(CH_BRASS, CH_BRASS, B3, time, 2, 80)
    midi.addNote(CH_BRASS, CH_BRASS, E4, time, 2, 75)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 1, 80)
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 8, 55)


def main():
    """Generate and save The Juggling Act."""
    midi = create_juggling_act()
    save_midi(midi, "09_juggling_act.mid", TEMPO, TOTAL_BARS)
    print()
    print("THE JUGGLING ACT")
    print("A thousand spinning plates.")
    print("They must not fall.")


if __name__ == "__main__":
    main()
