#!/usr/bin/env python3
"""
Fascist Faction Soundtrack - Generate All Tracks

Generates the complete ~63 minute soundtrack for the National Revival Movement.

12 tracks exploring two faces of fascism:
- PUBLIC (Menacing): The Apparatus, Viktor's March, The Nationalist Guard,
                     Repression Protocol, National Revival
- PRIVATE (Anxious): Economic Crisis, The Corporate State, Propaganda Broadcast,
                     The Juggling Act, The Mirror, The Void Beneath, Desperate Return

Usage:
    cd babylon/tools/fascist_soundtrack
    poetry run python generate_all.py
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from generate_01_apparatus import main as gen_01
from generate_02_viktors_march import main as gen_02
from generate_03_nationalist_guard import main as gen_03
from generate_04_repression_protocol import main as gen_04
from generate_05_national_revival import main as gen_05
from generate_06_economic_crisis import main as gen_06
from generate_07_corporate_state import main as gen_07
from generate_08_propaganda_broadcast import main as gen_08
from generate_09_juggling_act import main as gen_09
from generate_10_the_mirror import main as gen_10
from generate_11_the_void_beneath import main as gen_11
from generate_12_desperate_return import main as gen_12


def print_header() -> None:
    """Print soundtrack generation header."""
    print("=" * 60)
    print("FASCIST FACTION SOUNDTRACK")
    print("National Revival Movement - 12 Tracks")
    print("=" * 60)
    print()
    print("Generating ~63 minutes of MIDI music...")
    print()


def print_section(name: str) -> None:
    """Print section header."""
    print("-" * 40)
    print(f"  {name}")
    print("-" * 40)


def print_footer() -> None:
    """Print completion summary."""
    print()
    print("=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print()
    print("Track List:")
    print()
    print("  MENACING (Public Face)")
    print("  01. The Apparatus       - 5:00  - Cold, efficient surveillance")
    print("  02. Viktor's March      - 4:30  - The strongman's theme")
    print("  03. The Nationalist Guard - 6:00 - Paramilitary violence")
    print("  04. Repression Protocol - 6:00  - State violence crushing dissent")
    print("  05. National Revival    - 6:00  - The hollow anthem")
    print()
    print("  ANXIOUS (Private Reality)")
    print("  06. Economic Crisis     - 5:30  - The chaos that birthed fascism")
    print("  07. The Corporate State - 4:00  - Cold bureaucratic evil")
    print("  08. Propaganda Broadcast - 7:00 - The beautiful lie")
    print("  09. The Juggling Act    - 5:30  - Spinning plates")
    print("  10. The Mirror          - 4:30  - Self-awareness/dread")
    print("  11. The Void Beneath    - 5:00  - The abyss under everything")
    print("  12. Desperate Return    - 4:00  - The machine must continue")
    print()
    print("  TOTAL: ~63:00")
    print()
    print("Output: babylon/assets/music/fascist/")
    print()
    print("They know what they are. They cannot stop.")
    print("=" * 60)


def generate_all() -> None:
    """Generate all 12 tracks of the fascist soundtrack."""
    print_header()

    # Menacing tracks (Public Face)
    print_section("MENACING TRACKS (Public Face)")
    print()

    print("Track 01: The Apparatus")
    gen_01()
    print()

    print("Track 02: Viktor's March")
    gen_02()
    print()

    print("Track 03: The Nationalist Guard")
    gen_03()
    print()

    print("Track 04: Repression Protocol")
    gen_04()
    print()

    print("Track 05: National Revival")
    gen_05()
    print()

    # Anxious tracks (Private Reality)
    print_section("ANXIOUS TRACKS (Private Reality)")
    print()

    print("Track 06: Economic Crisis")
    gen_06()
    print()

    print("Track 07: The Corporate State")
    gen_07()
    print()

    print("Track 08: Propaganda Broadcast")
    gen_08()
    print()

    print("Track 09: The Juggling Act")
    gen_09()
    print()

    print("Track 10: The Mirror")
    gen_10()
    print()

    print("Track 11: The Void Beneath")
    gen_11()
    print()

    print("Track 12: Desperate Return")
    gen_12()
    print()

    print_footer()


if __name__ == "__main__":
    generate_all()
