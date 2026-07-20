"""Declared source of truth: public surfaces pinned by a baseline test.

Each :class:`PinnedSurface` names a package whose ``__all__`` is pinned by a
frozenset baseline in a test file. The static sensor in
:mod:`babylon.sentinels.surface.checks` proves the two agree — so an ``__all__``
edit without a matching baseline edit reds a scoped run, not only the full gate
(the cross-cutting public-surface baseline-blindness class).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator


class PinnedSurface(BaseModel):
    """One package surface pinned by a baseline frozenset.

    Frozen and ``extra="forbid"`` so a malformed row is a loud failure at
    import time (Constitution III.11) rather than a quiet ``None`` at check
    time.

    :ivar name: stable identity (e.g. ``"config.defines"``).
    :ivar package_init: repo-relative path to the ``__init__.py`` declaring ``__all__``.
    :ivar baseline_file: repo-relative path to the test declaring the baseline.
    :ivar baseline_var: the frozenset variable name (e.g. ``EXPECTED_DEFINES_PUBLIC``).
    :ivar material_relation: why drift matters (Aleksandrov Test).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    package_init: str
    baseline_file: str
    baseline_var: str
    material_relation: str

    @model_validator(mode="after")
    def _validate_shape(self) -> PinnedSurface:
        """Reject empty identity/location fields loudly at import (III.11).

        :returns: ``self`` when valid.
        :raises ValueError: if ``name``/``baseline_var`` is blank, or either
            path field is not the expected file kind.
        """
        if not self.name.strip():
            raise ValueError("PinnedSurface.name must be non-empty")
        if not self.baseline_var.strip():
            raise ValueError(f"{self.name!r}: baseline_var must be non-empty")
        if not self.package_init.endswith("__init__.py"):
            raise ValueError(f"{self.name!r}: package_init must be an __init__.py path")
        if not self.baseline_file.endswith(".py"):
            raise ValueError(f"{self.name!r}: baseline_file must be a .py path")
        return self


#: The known public surfaces pinned by a baseline frozenset. Each row's
#: ``__all__`` must equal its ``baseline_var`` exactly; the static sensor in
#: :mod:`babylon.sentinels.surface.checks` proves it.
PINNED_SURFACES: tuple[PinnedSurface, ...] = (
    PinnedSurface(
        name="config.defines",
        package_init="src/babylon/config/defines/__init__.py",
        baseline_file="tests/unit/test_public_import_surface.py",
        baseline_var="EXPECTED_DEFINES_PUBLIC",
        material_relation=(
            "The moddable coefficient surface; a *Defines class silently added "
            "to __all__ without a baseline edit is a public-API change no "
            "scoped test sees (live specimen: CapitalVolumeIIIDefines, U2.3)."
        ),
    ),
    PinnedSurface(
        name="models.enums",
        package_init="src/babylon/models/enums/__init__.py",
        baseline_file="tests/unit/test_public_import_surface.py",
        baseline_var="EXPECTED_ENUMS_PUBLIC",
        material_relation=(
            "The enum vocabulary surface; an enum added to __all__ without a "
            "baseline edit ships an unpinned public symbol."
        ),
    ),
)
