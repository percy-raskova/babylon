"""Public-surface baseline blindness (sixth sentinel) — the static drift gate.

Proves, without importing or running anything, that every declared
:class:`~babylon.sentinels.surface.registry.PinnedSurface`'s package ``__all__``
agrees exactly with its pinned baseline frozenset
(``EXPECTED_*_PUBLIC`` in ``tests/unit/test_public_import_surface.py``). A
scoped test run of the package that gained the symbol stays green; only the
full gate's ``test_all_matches_baseline`` would catch the drift — this sensor
closes that blind spot at the fast-gate layer instead (live specimen:
``CapitalVolumeIIIDefines`` added to ``babylon.config.defines.__all__`` in
U2.3 without a baseline edit).

**Static by contract.** Both sides are read with :mod:`ast`
(:func:`~babylon.sentinels._ast.literal_str_tuple` for ``__all__``,
:func:`~babylon.sentinels._ast.frozenset_str_members` for the baseline) — no
import, no test run — so the gate is cheap enough for the always-on dev
fast-gate (``mise run check`` -> ``check:surface``).

Run via the family CLI: ``poetry run python tools/sentinel_check.py surface --check``.
Exit 0 = clean, 1 = gating drift found, 2 = infrastructure failure (source
missing or unparseable — itself a loud failure, never swallowed).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from babylon.sentinels._ast import frozenset_str_members, literal_str_tuple
from babylon.sentinels.base import LabelledCheck, run_sensor
from babylon.sentinels.report import finding
from babylon.sentinels.surface.registry import PINNED_SURFACES, PinnedSurface

#: Repo root (this file is ``<root>/src/babylon/sentinels/surface/checks.py``).
_REPO_ROOT: Path = Path(__file__).resolve().parents[4]


def _resolve(path_str: str) -> Path:
    """Join a registry path against the repo root, unless it is absolute.

    Registry rows hold repo-relative paths; the fixture-based mutation test
    passes absolute paths, which are used as-is (idempotent join).

    :param path_str: A repo-relative or absolute path string.
    :returns: The resolved :class:`Path`.
    """
    path = Path(path_str)
    return path if path.is_absolute() else _REPO_ROOT / path


def _drift_finding(surface: PinnedSurface) -> str | None:
    """Return an agent-legible finding if ``surface``'s ``__all__`` and baseline disagree.

    :param surface: The pinned surface to check.
    :returns: A rendered finding string, or ``None`` when the two sets are equal.
    :raises SentinelCheckError: If either source file is missing or unparseable.
    """
    exported = set(literal_str_tuple(_resolve(surface.package_init), "__all__"))
    baseline = set(frozenset_str_members(_resolve(surface.baseline_file), surface.baseline_var))
    missing = baseline - exported  # in baseline, dropped from __all__
    extra = exported - baseline  # added to __all__, no baseline edit
    if not missing and not extra:
        return None
    return finding(
        error_class="public-surface baseline blindness",
        symbol=f"{surface.name}.__all__",
        file=surface.package_init,
        line=0,
        problem=(
            f"__all__ diverged from {surface.baseline_var} in "
            f"{surface.baseline_file}: added-without-baseline={sorted(extra)}, "
            f"dropped-but-still-pinned={sorted(missing)}"
        ),
        remedy=(
            f"Edit {surface.baseline_var} in {surface.baseline_file} to match "
            f"{surface.name}.__all__ in the SAME commit that changed __all__."
        ),
    )


def check_pinned_surfaces(
    registry: tuple[PinnedSurface, ...] = PINNED_SURFACES,
) -> list[str]:
    """Every pinned surface's ``__all__`` must agree with its baseline frozenset.

    :param registry: The surfaces to check (defaults to the real
        :data:`PINNED_SURFACES`; injectable so tests can supply a deliberately
        drifted row to prove the sensor reds).
    :returns: Sorted finding strings (empty when every surface agrees).
    :raises SentinelCheckError: If any declared source file is missing or
        unparseable (an infrastructure failure, distinct from drift).
    """
    findings: list[str] = []
    for surface in registry:
        drift = _drift_finding(surface)
        if drift is not None:
            findings.append(drift)
    return sorted(findings)


#: Gating checks: a violation reds the dev fast-gate (exit 1).
_GATING_CHECKS: tuple[LabelledCheck, ...] = (
    ("__all__ diverged from its pinned baseline frozenset", check_pinned_surfaces),
)

#: No advisory tier — unlike liveness/aggregation/coupling (U7.5/U7.6/U7.8),
#: check:surface is wired as a real gate per owner ruling 2026-07-19.
_ADVISORY_CHECKS: tuple[LabelledCheck, ...] = ()


def _summary(advisory_count: int) -> str:
    """Build the clean one-line summary printed when no gating violation occurred.

    :param advisory_count: Number of advisory findings (always 0 — no advisory
        tier; kept for the shared :func:`run_sensor` signature).
    :returns: The summary line naming the count of pinned surfaces checked.
    """
    del advisory_count  # unused: no advisory tier for this sentinel
    return f"Public surface (static): clean — {len(PINNED_SURFACES)} pinned surfaces agree with their baselines."


def main(argv: list[str] | None = None) -> int:
    """Run the public-surface baseline check and return the process exit code.

    :param argv: CLI args (``--check`` is accepted as the CI-mode alias; the
        behavior is always to gate).
    :returns: 0 clean, 1 drift found, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(
        description="Public-surface baseline blindness — sixth sentinel (III.11 gate)."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the tool always gates (exit 1 on violations).",
    )
    parser.parse_args(argv)
    return run_sensor("SURFACE", _GATING_CHECKS, _ADVISORY_CHECKS, _summary)


if __name__ == "__main__":
    sys.exit(main())
