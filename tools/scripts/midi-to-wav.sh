#!/bin/bash
# Convert MIDI to WAV using FluidSynth
# Usage: midi-to-wav.sh <input.mid> [output.wav]

set -e

SOUNDFONT="${SOUNDFONT:-/usr/share/sounds/sf2/FluidR3_GM.sf2}"
AUDIO_OUTPUT_DIR="${AUDIO_OUTPUT_DIR:-assets/audio}"

INPUT="$1"
if [ -z "$INPUT" ]; then
    echo "Usage: midi-to-wav <input.mid> [output.wav]"
    exit 1
fi

# Default output: same name with .wav extension in audio output dir
if [ -z "$2" ]; then
    BASENAME=$(basename "$INPUT" .mid)
    mkdir -p "$AUDIO_OUTPUT_DIR"
    OUTPUT="$AUDIO_OUTPUT_DIR/$BASENAME.wav"
else
    OUTPUT="$2"
fi

echo "Converting: $INPUT -> $OUTPUT"
# -g 1.0 = gain boost (default 0.2 is too quiet)
fluidsynth -ni -g 1.0 "$SOUNDFONT" "$INPUT" -F "$OUTPUT" -r 44100
echo "Done: $OUTPUT"
