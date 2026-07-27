"""RED-phase contract tests for spec-107 items that are specced but NOT built.

Program 26 Unit U1 charters spec-107 as "domain math + data artifact + red-phase
tests; no system insertion — consumption seams declared for U5" (`project/programs/
26-international-trade.md`). These tests pin the CURRENT, deliberate absence of
three things this spec describes but does not implement:

1. The precomputed σ-index data artifact (generation is environment-blocked —
   the ``babylon-data`` drive this repo's loaders read from is absent on this
   machine; see spec-107 tasks.md).
2. The engine's consumption of the ``"spectrum"`` contradiction field (U5,
   post-P25 — Program 26 §3's non-overlap covenant forbids touching
   ``engine/systems/*`` in this unit).
3. A ``SpectrumDefines`` category on ``GameDefines`` (the composition weights
   this package's pure functions require as explicit arguments have no
   canonical values yet — that is a Director-ruling item, spec.md Decision D1).

Each test is written to PASS today (documenting true current absence) and to
FAIL the day its subject is built — that failure is the intended signal to
come back, update the acceptance criteria, and drop the ``red_phase`` marker
(the same "twice-bitten" sentinel discipline as the codebase's other inert/
seam sentinels — see ``ai/anti-patterns.yaml``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.systems.contradiction_field import _OPPOSITION_FIELD_NAMES

# The repo root, derived from this test file's path (tests/unit/domain/economics/sigma/).
_REPO_ROOT = Path(__file__).resolve().parents[5]


@pytest.mark.red_phase
def test_sigma_index_artifact_not_yet_generated() -> None:
    """The declared checked-in artifact (spec-107 data contract §) doesn't exist.

    Generation is environment-blocked in this worktree (the babylon-data
    drive this repo's `tools/ingest/*` loaders read from is absent —
    dangling symlinks, a pre-existing condition). The declared future path
    follows the Tier-1 in-repo convention (`src/babylon/data/reference/*`,
    the same home as `babylon_hickel_final.csv` / `babylon_ricci_final.csv`).
    """
    declared_artifact_path = (
        _REPO_ROOT / "src" / "babylon" / "data" / "reference" / ("sigma_index.parquet")
    )
    assert not declared_artifact_path.exists(), (
        "sigma_index.parquet now exists — the σ-index artifact has been "
        "generated. Update spec-107 tasks.md (flip the environment-blocked "
        "task to done), write a real schema/contract test against its "
        "contents, and drop this red_phase marker."
    )


@pytest.mark.red_phase
def test_spectrum_field_not_yet_wired_into_engine() -> None:
    """The "spectrum" contradiction field is declared (spec-107) but not inserted.

    Program 26 U1 is explicitly off-pipeline: "no system insertion —
    consumption seams declared for U5." `_OPPOSITION_FIELD_NAMES` is System
    19's field registry (`engine/systems/contradiction_field.py`); adding
    "spectrum" to it is U5's job (post-P25, per Program 26 §4).
    """
    assert "spectrum" not in _OPPOSITION_FIELD_NAMES, (
        '"spectrum" now appears in _OPPOSITION_FIELD_NAMES — U5 has wired the '
        "field. Update spec-107's acceptance criteria to point at the live "
        "engine behavior and drop this red_phase marker."
    )


@pytest.mark.red_phase
def test_spectrum_defines_category_not_yet_added() -> None:
    """No ``SpectrumDefines`` category exists on ``GameDefines`` yet.

    This package's :class:`~babylon.domain.economics.sigma.types.ComponentWeights`
    requires every caller to supply explicit weights — by design, no default
    is hardcoded here (Constitution III.1). The canonical weight values (and
    the wage-gravitation rate for coupling 2) belong in a `SpectrumDefines`
    sub-model once a Director ruling settles the composition method (spec.md
    Decision D1) — this test pins that the settlement hasn't happened yet.
    """
    assert not hasattr(GameDefines(), "spectrum"), (
        "GameDefines now exposes a `spectrum` category — the pending "
        "GameDefines addition (spec-107 tasks.md) has landed. Update this "
        "package's callers to source weights from GameDefines and drop this "
        "red_phase marker."
    )
