"""`babylon play` — launch the game (currently the bundled two-node demo).

Delegates to the existing ``babylon.__main__`` entry logic rather than
duplicating it (DRY); the TUI client replaces this body in a later plan.
"""

from __future__ import annotations


def run() -> None:
    """Run the bundled demo simulation. Imported lazily so importing the CLI
    package never triggers ``babylon.__main__``'s import-time logging setup."""
    from babylon.__main__ import main as run_demo

    run_demo()


def play() -> None:
    """Play Babylon (currently the bundled two-node demo scenario)."""
    run()
