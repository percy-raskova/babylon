#!/usr/bin/env python3
"""
Track 03: "The Nationalist Guard" (6:00)
Mood: MENACING - Aggressive, intimidating, brutal

The paramilitary forces - 3,500 Nationalist Guard units.
Street-level violence, organized intimidation, the boots on the ground.

Musical approach:
- Aggressive snare patterns (paramilitary drums)
- Brass stabs representing sudden violence
- Low strings providing menacing atmosphere
- Building intensity, sudden releases
- More chaotic than Viktor's March - street-level chaos

Tempo: 112 BPM | Key: E Phrygian
Target duration: 6:00 (~168 bars at 112 BPM)
"""

from . import (
    A3,
    B2,
    B3,
    C4,
    CH_BRASS,
    CH_DRUMS,
    CH_HARPSI,
    CH_STRINGS,
    CH_TIMPANI,
    D4,
    DRUM_BASS,
    DRUM_CLOSED_HH,
    DRUM_CRASH,
    DRUM_SNARE,
    DRUM_TOM_HIGH,
    DRUM_TOM_LOW,
    DRUM_TOM_MID,
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
    Bb3,
    create_midi,
    save_midi,
    setup_standard_tracks,
)

TEMPO = 112
TOTAL_BARS = 168  # ~6:00 at 112 BPM


def create_nationalist_guard():
    """Generate The Nationalist Guard - paramilitary violence."""
    midi = create_midi(10)  # Need 10 tracks to support drum channel (9)
    setup_standard_tracks(midi, TEMPO)

    # === SECTION A: Gathering (bars 1-32) ===
    section_a_gathering(midi)

    # === SECTION B: The March (bars 33-72) ===
    section_b_march(midi)

    # === SECTION C: Street Violence (bars 73-120) ===
    section_c_violence(midi)

    # === SECTION D: Aftermath (bars 121-168) ===
    section_d_aftermath(midi)

    return midi


def section_a_gathering(midi):
    """The Guard assembles - tension before violence."""

    # Low timpani - ominous presence
    for bar in range(32):
        time = bar * 4
        vel = min(40 + bar * 2, 75)

        # Slow, heavy beats
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 1, vel)
        if bar >= 8:
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, vel - 15)

    # Snare enters bar 12 - military readiness
    for bar in range(12, 32):
        time = bar * 4
        vel = min(50 + (bar - 12) * 2, 80)

        # Building pattern
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 1.5, 0.25, vel)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 2, 0.25, vel - 10)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 3.5, 0.25, vel)

        # Hi-hat pulse
        if bar >= 20:
            for beat in range(4):
                midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_CLOSED_HH, time + beat + 0.5, 0.25, 50)

    # Strings - building menace
    for bar in range(0, 32, 4):
        time = bar * 4
        vel = 35 + bar
        midi.addNote(CH_STRINGS, CH_STRINGS, E2, time, 16, min(vel, 60))
        if bar >= 16:
            midi.addNote(CH_STRINGS, CH_STRINGS, B2, time, 16, min(vel - 10, 50))

    # Harpsichord enters bar 20 - mechanical anticipation
    for bar in range(20, 32):
        time = bar * 4
        vel = 55 + (bar - 20) * 2
        figure = [E3, E3, F3, E3]  # Simple, tense
        for i, note in enumerate(figure):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i, 0.75, min(vel, 70))

    # Brass - warning stabs
    brass_times = [24, 28, 30]
    for bar in brass_times:
        time = bar * 4
        midi.addNote(CH_BRASS, CH_BRASS, E3, time, 0.5, 75)
        midi.addNote(CH_BRASS, CH_BRASS, B3, time, 0.5, 70)


def section_b_march(midi):
    """The march begins - organized aggression."""

    base_bar = 32

    # Full drum kit - aggressive march
    for bar in range(40):
        time = (base_bar + bar) * 4

        # Kick pattern
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_BASS, time, 0.5, 90)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_BASS, time + 2, 0.5, 85)
        if bar % 2 == 1:
            midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_BASS, time + 3.5, 0.25, 75)

        # Aggressive snare
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 1, 0.25, 90)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 1.5, 0.25, 75)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 3, 0.25, 90)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 3.5, 0.25, 75)

        # Hi-hat driving pulse
        for beat in range(8):
            midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_CLOSED_HH, time + beat * 0.5, 0.25, 60)

    # Timpani - heavy accents
    for bar in range(40):
        time = (base_bar + bar) * 4
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, 95)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, 90)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, B2, time + 3, 0.5, 75)

    # Strings - menacing sustain
    for bar in range(0, 40, 4):
        time = (base_bar + bar) * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 8, 65)
        midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 8, 55)
        if bar % 8 == 4:
            midi.addNote(CH_STRINGS, CH_STRINGS, F3, time + 8, 8, 60)  # Dread note

    # Harpsichord - driving mechanical pattern
    for bar in range(40):
        time = (base_bar + bar) * 4
        pattern = [E3, E3, F3, E3, E3, G3, E3, A3]  # Tense, repetitive
        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, 72)

    # Brass - punctuating violence
    brass_hits = [
        (36, [E3, B3, E4], 0.5, 90),
        (44, [E3, B3, F4], 0.5, 95),  # Dread
        (52, [E3, B3, E4], 0.25, 95),
        (53, [E3, B3, E4], 0.25, 90),
        (60, [E3, Bb3, E4], 0.5, 100),  # Tritone
        (68, [E3, B3, G4], 1, 95),
    ]

    for bar, notes, dur, vel in brass_hits:
        time = bar * 4
        for note in notes:
            midi.addNote(CH_BRASS, CH_BRASS, note, time, dur, vel)


def section_c_violence(midi):
    """Street violence - chaos and aggression."""

    base_bar = 72

    # Chaotic drums - violence erupting
    for bar in range(48):
        time = (base_bar + bar) * 4

        # Aggressive kick
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_BASS, time, 0.5, 100)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_BASS, time + 1.5, 0.25, 80)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_BASS, time + 2, 0.5, 95)
        midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_BASS, time + 3, 0.25, 85)

        # Snare frenzy
        snare_pattern = [0.5, 1, 1.25, 1.75, 2.5, 3, 3.25, 3.75]
        for offset in snare_pattern:
            vel = 95 if offset in [1, 3] else 80
            midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + offset, 0.2, vel)

        # Crashes on accents
        if bar % 4 == 0:
            midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_CRASH, time, 1, 90)

        # Tom fills every 8 bars
        if bar % 8 == 7:
            midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_TOM_HIGH, time + 3, 0.25, 85)
            midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_TOM_MID, time + 3.25, 0.25, 85)
            midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_TOM_LOW, time + 3.5, 0.25, 90)
            midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_TOM_LOW, time + 3.75, 0.25, 85)

    # Timpani - pounding aggression
    for bar in range(48):
        time = (base_bar + bar) * 4
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, 100)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 1, 0.25, 75)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, 95)
        midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3, 0.25, 80)

        # Extra hits on chaos bars
        if bar % 4 == 3:
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 3.5, 0.25, 85)
            midi.addNote(CH_TIMPANI, CH_TIMPANI, B2, time + 3.75, 0.25, 75)

    # Strings - screaming high notes (distress)
    string_phrases = [
        (0, E5, 8, 70),
        (8, F5, 8, 75),  # Dread note high
        (16, E5, 4, 70),
        (20, G5, 4, 75),
        (24, F5, 8, 80),  # More dread
        (32, E5, 8, 75),
        (40, F5, 8, 70),
    ]
    for bar_offset, note, dur, vel in string_phrases:
        time = (base_bar + bar_offset) * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, note, time, dur * 4, vel)

    # Low strings counterpoint
    for bar in range(0, 48, 4):
        time = (base_bar + bar) * 4
        midi.addNote(CH_STRINGS, CH_STRINGS, E2, time, 16, 60)

    # Harpsichord - frantic patterns
    for bar in range(48):
        time = (base_bar + bar) * 4

        if bar % 4 < 2:
            # Ascending panic
            pattern = [E3, F3, G3, A3, B3, C4, D4, E4]
        else:
            # Descending chaos
            pattern = [E4, D4, C4, B3, A3, G3, F3, E3]

        for i, note in enumerate(pattern):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i * 0.5, 0.4, 80)

    # Brass - constant violence stabs
    for bar in range(48):
        time = (base_bar + bar) * 4

        if bar % 2 == 0:
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 0.5, 100)
            midi.addNote(CH_BRASS, CH_BRASS, B3, time, 0.5, 95)
            midi.addNote(CH_BRASS, CH_BRASS, E4, time, 0.5, 90)

        if bar % 4 == 2:
            midi.addNote(CH_BRASS, CH_BRASS, E3, time + 2, 0.25, 95)
            midi.addNote(CH_BRASS, CH_BRASS, F4, time + 2, 0.25, 90)  # Dread

        if bar % 8 == 6:
            # Tritone violence
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 0.5, 100)
            midi.addNote(CH_BRASS, CH_BRASS, Bb3, time, 0.5, 95)
            midi.addNote(CH_BRASS, CH_BRASS, E4, time, 0.5, 90)


def section_d_aftermath(midi):
    """The aftermath - violence subsides but threat remains."""

    base_bar = 120

    # Drums - gradually calming
    for bar in range(48):
        time = (base_bar + bar) * 4

        # Decreasing intensity (vel_modifier used implicitly in velocity calculations)
        if bar < 32:
            # Still aggressive but fading
            midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_BASS, time, 0.5, 85 - bar)
            midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_BASS, time + 2, 0.5, 80 - bar)

            midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 1, 0.25, 80 - bar // 2)
            midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 3, 0.25, 80 - bar // 2)

            # Hi-hat continues
            for beat in range(4):
                midi.addNote(
                    CH_DRUMS, CH_DRUMS, DRUM_CLOSED_HH, time + beat + 0.5, 0.25, 50 - bar // 2
                )
        elif bar < 40:
            # Sparse
            midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_BASS, time, 0.5, 60)
            midi.addNote(CH_DRUMS, CH_DRUMS, DRUM_SNARE, time + 2, 0.25, 55)

    # Timpani - slowing heartbeat of violence
    for bar in range(48):
        time = (base_bar + bar) * 4

        if bar < 32:
            vel = 85 - bar
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 0.5, max(vel, 50))
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time + 2, 0.5, max(vel - 10, 45))
        elif bar < 40:
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 1, 50)
        else:
            midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 2, 40)

    # Strings - return to low menace
    for bar in range(0, 48, 4):
        time = (base_bar + bar) * 4
        vel = 60 if bar < 24 else 50 - (bar - 24)
        midi.addNote(CH_STRINGS, CH_STRINGS, E3, time, 16, max(vel, 35))
        midi.addNote(CH_STRINGS, CH_STRINGS, B3, time, 16, max(vel - 10, 30))

    # Harpsichord - mechanical continues but softer
    for bar in range(32):
        time = (base_bar + bar) * 4
        vel = 65 - bar
        figure = [E3, E3, F3, E3]
        for i, note in enumerate(figure):
            midi.addNote(CH_HARPSI, CH_HARPSI, note, time + i, 0.75, max(vel, 40))

    # Brass - occasional reminders of violence
    reminder_bars = [124, 132, 140, 156]
    for bar in reminder_bars:
        if bar < base_bar + 48:
            time = bar * 4
            vel = 70 if bar < 140 else 55
            midi.addNote(CH_BRASS, CH_BRASS, E3, time, 0.5, vel)
            midi.addNote(CH_BRASS, CH_BRASS, B3, time, 0.5, vel - 5)

    # Final menacing note
    time = 164 * 4
    midi.addNote(CH_BRASS, CH_BRASS, E3, time, 2, 60)
    midi.addNote(CH_BRASS, CH_BRASS, E4, time, 2, 55)
    midi.addNote(CH_TIMPANI, CH_TIMPANI, E2, time, 2, 50)


def main():
    """Generate and save The Nationalist Guard."""
    midi = create_nationalist_guard()
    save_midi(midi, "03_nationalist_guard.mid", TEMPO, TOTAL_BARS)
    print()
    print("THE NATIONALIST GUARD")
    print("3,500 boots on the ground.")
    print("Street-level violence, organized.")


if __name__ == "__main__":
    main()
