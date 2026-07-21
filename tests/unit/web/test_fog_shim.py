"""Program 24 P1 WO-1 (the Hoist, part A): legacy shim parity.

``web/game/fog/`` was relocated to ``babylon.projection.fog`` verbatim (it
was already transport-neutral). ``web/game/fog/{__init__,reach,ledger,
filter}.py`` are now thin re-export shims so the legacy web app
(``engine_bridge.py``'s ``from .fog.* import ...`` lines) and any other
``game.fog`` importer keep working unchanged until the P4 cutover retires
``web/`` entirely.

This test pins that the shim can't rot silently: every name the real
package exports under each submodule must resolve, identically, through
the legacy ``game.fog`` import path — same object, not just same name (a
shim that re-implements rather than re-exports would still pass a
name-only check).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


class TestFogShimExposesDeclaredNames:
    """``game.fog``'s ``__all__`` must resolve to real attributes — the
    minimal name-parity check, sharpened below by identity checks against
    the canonical submodules."""

    def test_every_declared_name_resolves(self) -> None:
        import game.fog as shim

        for name in shim.__all__:
            assert hasattr(shim, name), f"game.fog is missing {name!r}"


class TestFogShimSubmodulesReexportCanonical:
    """Each ``game.fog.<submodule>`` shim must expose the SAME objects
    (not merely same-named copies) as its ``babylon.projection.fog.<submodule>``
    counterpart — proving the shim delegates rather than re-implements."""

    def test_reach_organizing_reach_is_canonical_object(self) -> None:
        from babylon.projection.fog.reach import organizing_reach as canonical
        from game.fog.reach import organizing_reach as shimmed

        assert shimmed is canonical

    def test_ledger_names_are_canonical_objects(self) -> None:
        import babylon.projection.fog.ledger as canonical
        import game.fog.ledger as shimmed

        for name in (
            "IntelEntry",
            "IntelLedger",
            "IntelReading",
            "VisibilityTier",
            "ledger_from_events",
            "read_intel",
        ):
            assert getattr(shimmed, name) is getattr(canonical, name), name

    def test_filter_names_are_canonical_objects(self) -> None:
        import babylon.projection.fog.filter as canonical
        import game.fog.filter as shimmed

        for name in (
            "ORG_INTERNAL_STATE_FIELDS",
            "ORG_POLITICAL_FIELDS",
            "POLITICAL_FIELDS",
            "apply_fog",
            "political_field_group",
        ):
            assert getattr(shimmed, name) is getattr(canonical, name), name

    def test_package_init_reexports_are_canonical_objects(self) -> None:
        import babylon.projection.fog.filter as canonical_filter
        import babylon.projection.fog.ledger as canonical_ledger
        import babylon.projection.fog.reach as canonical_reach
        import game.fog as shim

        assert shim.organizing_reach is canonical_reach.organizing_reach
        assert shim.apply_fog is canonical_filter.apply_fog
        assert shim.IntelLedger is canonical_ledger.IntelLedger
