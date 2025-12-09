#!/bin/bash
# Play a MIDI file through speakers using FluidSynth
# Usage: midi-play.sh <input.mid>

SOUNDFONT="${SOUNDFONT:-/usr/share/sounds/sf2/FluidR3_GM.sf2}"

INPUT="$1"
if [ -z "$INPUT" ]; then
    echo "Usage: midi-play <input.mid>"
    exit 1
fi

echo "Playing: $INPUT (Ctrl+C to stop)"
echo "Soundfont: $SOUNDFONT"
# -g 1.0 = gain boost (default 0.2 is too quiet)
fluidsynth -ni -g 1.0 "$SOUNDFONT" "$INPUT" -a pulseaudio
