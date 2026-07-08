"""Regression: babylon.formulas.balkanization must be importable FIRST.

The module-level Sovereign import of ``calculate_metabolic_impact`` created a
models <-> formulas cycle that broke any process whose first babylon import
was ``formulas.balkanization`` (e.g. ``pytest --doctest-modules``): the chain
``formulas.balkanization`` -> ``babylon.models.enums`` -> ``babylon.models``
-> ``entities.sovereign`` -> back into the half-initialized formulas module
raised ``ImportError: cannot import name 'calculate_metabolic_impact' from
partially initialized module``.
"""

from __future__ import annotations

import subprocess
import sys

import pytest


@pytest.mark.unit
def test_balkanization_imports_standalone() -> None:
    """A fresh interpreter whose first import is formulas.balkanization works."""
    proc = subprocess.run(
        [sys.executable, "-c", "import babylon.formulas.balkanization"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
