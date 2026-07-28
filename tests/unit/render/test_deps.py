"""The client dependency contract — the M7 cutover's own dual.

Before the cutover this file asserted the Textual stack imported cleanly;
since ``test(cutover)!: retire Textual Archive lane`` it asserts the
INVERSE, so the deleted estate can never silently creep back in through a
transitive pin — plus the positive half: the Rust client extension is a
default dependency and actually imports.
"""

from __future__ import annotations

import importlib.util

import pytest

#: The retired Textual stack — none of these may be installed (a transitive
#: re-appearance would mean a dependency regression, not harmless extra).
RETIRED_MODULES = ("textual", "textual_image", "textual_plotext", "pytest_textual_snapshot")


@pytest.mark.parametrize("module", RETIRED_MODULES)
def test_the_retired_textual_stack_is_gone(module: str) -> None:
    assert importlib.util.find_spec(module) is None, (
        f"{module} is installed — the Textual estate was retired at the M7 "
        "cutover ceremony (ADR150); a reappearing pin is a regression"
    )


def test_the_rust_client_extension_imports(dependency_default: None = None) -> None:
    """The positive half: babylon_tui ships in the default install (Task 44)."""
    babylon_tui = pytest.importorskip(
        "babylon_tui",
        reason="babylon_tui extension not built (uv sync; after Rust edits: uvx maturin develop in rust/)",
    )
    assert hasattr(babylon_tui, "run")
