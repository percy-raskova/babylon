"""Minimal conftest for engine tests.

No database, no heavy fixtures. Pure unit tests.
"""

import pytest


@pytest.fixture
def clean_engine():
    """Provide a fresh ContradictionAnalysis instance."""
    from babylon.systems.contradiction_analysis import ContradictionAnalysis

    return ContradictionAnalysis()
