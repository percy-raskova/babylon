#!/usr/bin/env python3
"""
Track 06: "Economic Crisis" (5:30)
Mood: ANXIOUS - Chaotic, unstable, fearful

The conditions that birthed fascism - economic crisis, fear, instability.
The chaos that fascism promises to resolve (but never truly does).

Musical approach:
- Chaotic, dissonant opening (the crisis)
- Multiple voices competing (class anxiety)
- Irregular meters creating instability (5/4, 7/8)
- Gradual imposition of "order" through mechanical patterns
- Chromatic/atonal start resolving to E Phrygian

Tempo: 110 BPM | Key: Chromatic/atonal → E Phrygian
Target duration: 5:30 (~151 bars at 110 BPM)
"""

from . import (
    A3,
    B2,
    B3,
    C3,
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
    F4,
    F5,
    G3,
    G4,
    Ab3,
    Bb2,
    Bb3,
    Db3,
    Db4,
    Eb3,
    Eb4,
    Fs3,
    create_midi,
    save_midi,
    setup_standard_tracks,
)

TEMPO = 110
TOTAL_BARS = 151  # ~5:30 at 110 BPM


def create_economic_crisis():
    """Generate Economic Crisis - the chaos that birthed fascism."""
    midi = create_midi(5)
    setup_standard_tracks(midi, TEMPO)

    # === SECTION A: The Collapse (bars 1-40) ===
    section_a_collapse(midi)

    # === SECTION B: Chaos Deepens (bars 41-80) ===
    section_b_chaos(midi)

    # === SECTION C: False Order (bars 81-120) ===
    section_c_order(midi)

    # === SECTION D: The New Normal (bars 121-151) ===
    section_d_new_normal(midi)

    return midi


def section_a_collapse(midi):
    """The collapse begins - economic terror, dissonance."""

    # Strings - trembling, unstable
    # Using chromatic clusters to represent financial panic
    for bar in range(40):
        time = bar * 4

        if bar < 16:
            # Initial trembling - atonal clusters
            vel = 40 + bar * 2
            # Chromatic cluster
            midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 2, vel)
            midi.addNote(CH_STRINGS, CH_STRINGS, F3, time + 0.5, 2, vel - 5)
            midi.addNote(CH_STRINGS, CH_STRINGS, Eb3, time + 1, 1.5, vel - 10)

            if bar % 4 == 2:
                midi.addNote(CH_STRINGS, CH_STRINGS, Db4, time + 2, 2, vel - 5)
                midi.addNote(CH_STRINGS, CH_STRINGS, E4, time + 2.5, 1.5, vel)

        elif bar < 32:
            # Growing panic
            vel = 60 + (bar - 16) // 2
            midi.addNote(CH_STRINGS, CH_STRINGS, E4, time, 2, vel)
            if bar % 2 == 0:
                midi.addNote(CH_STRINGS, CH_STRINGS, F4, time + 1, 2, vel)
                midi.addNote(CH_STRINGS, CH_STRINGS, Eb4, time + 2, 2, vel - 5)
            else:
                midi.addNote(CH_STRINGS, CH_STRINGS, Fs3, time + 1, 2, vel - 10)
                midi.addNote(CH_STRINGS, CH_STRINGS, G4, time + 2.5, 1.5, vel)

        else:
            # Screaming high strings
            vel = 70
            midi.addNote(CH_STRINGS, CH_STRINGS, E5, time, 4, vel)
            if bar % 2 == 1:
                midi.addNote(CH_STRINGS, CH_STRINGS, F5, time + 2, 2, vel + 5)

    # Harpsichord - chaotic, irregular patterns
    for bar in range(8, 40):
        time = bar * 4

        if bar % 5 == 0:
            # 5/4 feel
            pattern = [E3, Db4, G3, Bb3, E4]
            for i, note in enumerate(pattern):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.8, 0.6, 65)
        elif bar % 7 == 0:
            # 7/8 feel
            pattern = [E3, F3, Ab3, E3, G3, Bb3, E3]
            for i, note in enumerate(pattern):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.57, 0.5, 68)
        else:
            # Irregular 4/4
            pattern = (
                [E3, Fs3, G3, Ab3, A3, Bb3, B3, E4]
                if bar % 2 == 0
                else [E4, Eb4, D4, Db4, C4, B3, Bb3, E3]
            )
            for i, note in enumerate(pattern):
                offset = i * 0.5 + (0.1 if i % 2 == 1 else 0)  # Irregular timing
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + offset, 0.4, 62)

    # Timpani - irregular, panicked
    for bar in range(16, 40):
        time = bar * 4
        vel = 50 + (bar - 16) * 2

        # Irregular beats - not a steady pulse
        if bar % 3 == 0:
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, min(vel, 80))
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 1.5, 0.25, min(vel - 15, 65))
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2.5, 0.5, min(vel - 10, 70))
        elif bar % 3 == 1:
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 0.5, 0.5, min(vel - 5, 75))
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, min(vel, 80))
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3.5, 0.25, min(vel - 20, 60))
        else:
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, min(vel, 80))
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 1, 0.25, min(vel - 10, 70))
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.25, min(vel - 15, 65))
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3, 0.5, min(vel - 5, 75))

    # Brass - alarm stabs
    alarm_bars = [24, 28, 32, 36, 38]
    for bar in alarm_bars:
        time = bar * 4
        vel = 80 + (bar - 24) * 2

        midi.addNote(CH_BRASS, CH_BRASS, E3, time, 0.5, min(vel, 95))
        midi.addNote(CH_BRASS, CH_BRASS, Bb3, time, 0.5, min(vel - 5, 90))  # Tritone alarm


def section_b_chaos(midi):
    """Chaos deepens - total economic panic."""

    base_bar = 40

    # All instruments in chaos

    # Strings - competing voices, class panic
    for bar in range(40):
        time = (base_bar + bar) * 4

        # High strings screaming
        midi.addNote(CH_STRINGS, CH_STRINGS, E5, time, 2, 75)
        if bar % 2 == 0:
            midi.addNote(CH_STRINGS, CH_STRINGS, F5, time + 2, 2, 78)
        else:
            midi.addNote(CH_STRINGS, CH_STRINGS, Eb4, time + 2, 2, 72)

        # Low strings groaning
        midi.addNote(CH_STRINGS, CH_STRINGS, E2, time, 4, 60)
        if bar % 4 >= 2:
            midi.addNote(CH_STRINGS, CH_STRINGS, Bb2, time, 4, 55)  # Tritone

    # Harpsichord - frantic, multiple patterns colliding
    for bar in range(40):
        time = (base_bar + bar) * 4

        # Pattern 1: Ascending panic (5/4 feel)
        if bar % 4 < 2:
            p1 = [E3, F3, G3, Ab3, Bb3]
            for i, note in enumerate(p1):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.8, 0.6, 70)
        # Pattern 2: Descending doom (7/8 feel)
        else:
            p2 = [E4, Eb4, D4, Db4, C4, B3, Bb3]
            for i, note in enumerate(p2):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.57, 0.5, 68)

        # Counter-pattern every 4 bars
        if bar % 4 == 3:
            counter = [E3, E4, E3, E4, E3, E4, E3, E4]
            for i, note in enumerate(counter):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, 65)

    # Timpani - irregular, panicked, building
    for bar in range(40):
        time = (base_bar + bar) * 4
        vel = 75 + bar // 4

        # Chaotic pattern
        beats = (
            [0, 0.5, 1, 1.75, 2, 2.5, 3, 3.5]
            if bar % 2 == 0
            else [0, 0.75, 1.5, 2, 2.25, 3, 3.25, 3.75]
        )
        for beat in beats:
            if beat in [0, 2]:
                midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, min(vel, 90))
            else:
                midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.2, min(vel - 15, 75))

    # Brass - crisis stabs
    for bar in range(40):
        time = (base_bar + bar) * 4

        if bar % 4 == 0:
            # Crisis chord
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 0.5, 95)
            midi.addNote(CH_BRASS, CH_BRASS, Bb3, time, 0.5, 90)
            midi.addNote(CH_BRASS, CH_BRASS, E4, time, 0.5, 85)

        if bar % 8 == 4:
            # Alarm fanfare
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 0.25, 100)
            midi.addNote(CH_BRASS, CH_BRASS, F3, time + 0.5, 0.25, 95)
            midi.addNote(CH_BRASS, CH_BRASS, E3, time + 1, 0.5, 100)

    # Organ - ominous undercurrent
    for bar in range(20, 40):
        time = (base_bar + bar) * 4
        vel = 40 + (bar - 20)
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, vel)
        midi.addNote(CH_ORGAN, CH_ORGAN, Bb2, time, 4, vel - 10)  # Tritone foundation


def section_c_order(midi):
    """False order - fascism imposes its mechanical control."""

    base_bar = 80

    # Transition: chaos becomes mechanical

    # Timpani - becoming regular (the machine takes over)
    for bar in range(40):
        time = (base_bar + bar) * 4

        if bar < 16:
            # Still chaotic but regularizing
            vel = 80
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, vel)
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 1.5, 0.25, vel - 15)
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, vel - 5)
            if bar % 2 == 1:
                midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3, 0.25, vel - 20)
        else:
            # Regular mechanical clock
            vel = 85
            for beat in range(4):
                accent = vel if beat == 0 else vel - 20
                midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, accent)
                midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat + 0.5, 0.25, accent - 20)

    # Harpsichord - transitioning to mechanical order
    for bar in range(40):
        time = (base_bar + bar) * 4

        if bar < 16:
            # Still irregular
            pattern = (
                [E3, F3, E3, G3, E3, Ab3, E3, A3]
                if bar % 2 == 0
                else [E3, Eb3, E3, D3, E3, Db3, E3, C3]
            )
            for i, note in enumerate(pattern):
                offset = i * 0.5 + (0.05 if i % 3 == 1 else 0)
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + offset, 0.4, 70)
        else:
            # Regular E Phrygian pattern - order imposed
            pattern = [E3, F3, E3, G3, E3, F3, E3, A3]
            for i, note in enumerate(pattern):
                midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, 72)

    # Strings - calming (forcibly)
    for bar in range(40):
        time = (base_bar + bar) * 4

        if bar < 16:
            # Still anxious
            vel = 65 - bar // 2
            midi.addNote(CH_STRINGS, CH_STRINGS, E4, time, 4, vel)
            if bar % 4 < 2:
                midi.addNote(CH_STRINGS, CH_STRINGS, F4, time, 4, vel - 5)
        else:
            # Forced calm
            vel = 55
            midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 4, vel)
            midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 4, vel - 10)

    # Organ - establishing authority
    for bar in range(16, 40):
        time = (base_bar + bar) * 4
        vel = 45 + (bar - 16) // 2
        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, vel)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, vel - 10)

    # Brass - imposing order
    order_bars = [16, 24, 32, 36]
    for bar in order_bars:
        time = (base_bar + bar) * 4
        vel = 80
        midi.addNote(CH_BRASS, CH_BRASS, E3, time, 1, vel)
        midi.addNote(CH_BRASS, CH_BRASS, B3, time, 1, vel - 5)
        midi.addNote(CH_BRASS, CH_BRASS, E4, time + 2, 1, vel + 5)


def section_d_new_normal(midi):
    """The new normal - order imposed, but tension remains."""

    base_bar = 120

    # Everything is now mechanical - the fascist order

    # Timpani - regular clock
    for bar in range(31):
        time = (base_bar + bar) * 4
        vel = 80 if bar < 24 else 75 - (bar - 24)

        for beat in range(4):
            accent = vel if beat == 0 else vel - 20
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat, 0.25, max(accent, 50))
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + beat + 0.5, 0.25, max(accent - 25, 35))

    # Harpsichord - mechanical pattern
    for bar in range(31):
        time = (base_bar + bar) * 4
        vel = 68 if bar < 24 else 60

        pattern = [E3, F3, E3, G3, E3, F3, E3, A3]
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, vel)

    # Organ - steady authority
    for bar in range(31):
        time = (base_bar + bar) * 4
        vel = 55 if bar < 24 else 50

        midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 4, vel)
        midi.addNote(CH_ORGAN, CH_ORGAN, B2, time, 4, vel - 10)

    # Strings - subdued
    for bar in range(0, 31, 4):
        time = (base_bar + bar) * 4
        vel = 50 if bar < 20 else 45

        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 16, vel)
        midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 16, vel - 10)

    # Brass - occasional reminder of authority
    reminder_bars = [0, 12, 24]
    for bar in reminder_bars:
        time = (base_bar + bar) * 4
        vel = 70 if bar < 20 else 60

        midi.addNote(CH_BRASS, CH_BRASS, E3, time, 1, vel)
        midi.addNote(CH_BRASS, CH_BRASS, B3, time, 1, vel - 5)

    # Final statement - order is imposed
    time = (TOTAL_BARS - 4) * 4
    midi.addNote(CH_BRASS, CH_BRASS, E3, time, 2, 70)
    midi.addNote(CH_BRASS, CH_BRASS, B3, time, 2, 65)
    midi.addNote(CH_BRASS, CH_BRASS, E4, time, 2, 60)
    midi.addNote(CH_ORGAN, CH_ORGAN, E2, time, 8, 50)


def main():
    """Generate and save Economic Crisis."""
    midi = create_economic_crisis()
    save_midi(midi, "06_economic_crisis.mid", TEMPO, TOTAL_BARS)
    print()
    print("ECONOMIC CRISIS")
    print("From chaos, false order.")
    print("The conditions that birth fascism.")


if __name__ == "__main__":
    main()
