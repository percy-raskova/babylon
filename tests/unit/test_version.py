"""Tests for package version accessibility.

Ensures the babylon package exposes __version__ at runtime,
following PEP 566 conventions using importlib.metadata.
"""

from __future__ import annotations

import re

import pytest


@pytest.mark.unit
class TestPackageVersion:
    """Tests for babylon.__version__ accessibility."""

    def test_version_is_accessible(self) -> None:
        """Package exposes __version__ attribute."""
        import babylon

        assert hasattr(babylon, "__version__")
        assert isinstance(babylon.__version__, str)

    def test_version_is_not_empty(self) -> None:
        """Version string is not empty."""
        import babylon

        assert len(babylon.__version__) > 0

    def test_version_follows_semver_pattern(self) -> None:
        """Version string follows semantic versioning pattern."""
        import babylon

        # Match X.Y.Z with optional pre-release/build metadata
        # Examples: 0.2.0, 1.0.0, 0.3.0+unknown, 1.2.3-alpha.1
        pattern = r"^\d+\.\d+\.\d+([+\-].+)?$"
        assert re.match(pattern, babylon.__version__), (
            f"Version '{babylon.__version__}' does not follow semver pattern"
        )

    def test_version_in_all_exports(self) -> None:
        """__version__ is listed in __all__ for explicit export."""
        import babylon

        assert "__version__" in babylon.__all__
