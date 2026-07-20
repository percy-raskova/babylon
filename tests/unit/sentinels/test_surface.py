"""U7.11: the public-surface sentinel reds on an __all__ that added a symbol
without a matching baseline edit (the U2.3 CapitalVolumeIIIDefines class),
and greens when they agree — proven on a fixture, independent of repo state."""

from __future__ import annotations

import pytest

from babylon.sentinels.surface.checks import _drift_finding
from babylon.sentinels.surface.registry import PinnedSurface

pytestmark = pytest.mark.unit


def _fixture(tmp_path, all_symbols: list[str], baseline: set[str]) -> PinnedSurface:
    """A pinned surface whose paths are ABSOLUTE (used as-is by ``_resolve``)."""
    init = tmp_path / "pkg" / "__init__.py"
    init.parent.mkdir(parents=True)
    init.write_text(f"__all__ = {all_symbols!r}\n")
    base = tmp_path / "test_surface_pin.py"
    base.write_text(f"EXPECTED = frozenset({sorted(baseline)!r})\n")
    return PinnedSurface(
        name="fixture.pkg",
        package_init=str(init),  # absolute -> _resolve returns it unchanged
        baseline_file=str(base),
        baseline_var="EXPECTED",
        material_relation="fixture",
    )


class TestSurfaceSentinel:
    def test_reds_on_symbol_added_without_baseline(self, tmp_path) -> None:
        # Literal reproduction of the live specimen: a symbol in __all__ that
        # the baseline frozenset does not pin.
        surface = _fixture(tmp_path, ["Foo", "CapitalVolumeIIIDefines"], {"Foo"})
        finding = _drift_finding(surface)
        assert finding is not None
        assert "CapitalVolumeIIIDefines" in finding

    def test_reds_on_baseline_symbol_dropped_from_all(self, tmp_path) -> None:
        surface = _fixture(tmp_path, ["Foo"], {"Foo", "Bar"})
        finding = _drift_finding(surface)
        assert finding is not None
        assert "Bar" in finding

    def test_greens_when_all_matches_baseline(self, tmp_path) -> None:
        surface = _fixture(tmp_path, ["Foo", "Bar"], {"Foo", "Bar"})
        assert _drift_finding(surface) is None
