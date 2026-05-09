"""Spec 058 / FR-003 / SC-003: regression test that
``_compute_membership_overlap`` exists in exactly one location.

Per the spec's User Story 5: the helper was duplicated between
``babylon.ooda.action_costs`` and ``babylon.ooda.action_effects`` (flagged
as duplication by the file-analyzer in the project knowledge graph). This
test pins the canonical location at ``babylon.ooda._helpers`` and asserts
that no other module under ``src/babylon/ooda/`` defines its own copy.

If a future contributor re-introduces a local definition in either
``action_costs.py`` or ``action_effects.py`` (or anywhere else under
``src/babylon/ooda/``), this test fails — preventing the drift that
Bundle 1 was designed to eliminate.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

OODA_DIR = Path(__file__).resolve().parents[3] / "src" / "babylon" / "ooda"
DEFINITION_PATTERN = re.compile(r"^def\s+_compute_membership_overlap\s*\(", re.MULTILINE)


@pytest.mark.unit
class TestMembershipOverlapCanonicalization:
    """Spec 058 SC-003: exactly one definition of _compute_membership_overlap."""

    def test_exactly_one_definition_in_ooda_package(self) -> None:
        """grep equivalent of `git grep -c "def _compute_membership_overlap"`.

        The canonical home is ``src/babylon/ooda/_helpers.py``; no other
        module in the OODA package may define a local copy.
        """
        definitions: list[Path] = []
        for py_file in OODA_DIR.rglob("*.py"):
            if "__pycache__" in py_file.parts:
                continue
            source = py_file.read_text(encoding="utf-8")
            if DEFINITION_PATTERN.search(source):
                definitions.append(py_file)

        relative_paths = sorted(p.relative_to(OODA_DIR.parent.parent.parent) for p in definitions)
        assert len(definitions) == 1, (
            f"Spec 058 / SC-003: expected exactly one definition of "
            f"`_compute_membership_overlap` in src/babylon/ooda/, found "
            f"{len(definitions)}: {relative_paths!r}. The canonical home "
            f"is src/babylon/ooda/_helpers.py — re-imports from other "
            f"modules MUST NOT redefine the function locally."
        )
        assert definitions[0].name == "_helpers.py", (
            f"Spec 058 / FR-003: the canonical definition MUST live in "
            f"`src/babylon/ooda/_helpers.py`, but the only definition was "
            f"found in {definitions[0].relative_to(OODA_DIR.parent.parent.parent)!r}."
        )

    def test_canonical_helper_is_importable(self) -> None:
        """Smoke check: the canonical import path resolves to a callable."""
        from babylon.ooda._helpers import _compute_membership_overlap

        assert callable(_compute_membership_overlap), (
            "babylon.ooda._helpers._compute_membership_overlap must be callable"
        )

    def test_call_sites_import_from_helpers(self) -> None:
        """action_costs.py and action_effects.py MUST import from _helpers
        rather than redefining the function locally.

        Detects the import statement; complements
        :py:meth:`test_exactly_one_definition_in_ooda_package` by also
        checking that the historical call sites are wired through the
        canonical helper.
        """
        for module_name in ("action_costs.py", "action_effects.py"):
            source = (OODA_DIR / module_name).read_text(encoding="utf-8")
            assert "from babylon.ooda._helpers import _compute_membership_overlap" in source or (
                "from ._helpers import _compute_membership_overlap" in source
            ), (
                f"Spec 058 / FR-003: {module_name} MUST import "
                f"_compute_membership_overlap from babylon.ooda._helpers; "
                f"local re-definitions are not permitted."
            )
