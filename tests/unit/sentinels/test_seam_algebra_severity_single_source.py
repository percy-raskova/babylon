"""Tests for the seam-algebra severity single-source check (T1.1 Unit 6).

Four tiers, mirroring ``test_seam_algebra_gate_satisfaction.py``'s own shape:

- **Fixture semantics** — :func:`check_severity_single_source` is clean when
  neither surface carries a reintroduced ``_EVENT_SEVERITY``/``EVENT_SEVERITY``
  literal and both still reference ``resolve_severity``; it reds when a
  surface stops referencing ``resolve_severity`` at all, or when a
  reintroduced literal's value diverges from the generated table.
- **Mutation efficacy** — the canonical single-source mutation the design
  names verbatim (§4 U6): "hand-edit one surface's resolved severity for one
  member to differ from the generated table -> check reds."
- **Symmetry** — the same mutation shape reds regardless of which surface
  (web or Archive) it lands on, and regardless of which retired literal name
  is used.
- **Liveness + CLI wiring** — the real, shipped web bridge and Archive
  Chronicle are clean (post-U2 estate), and the family's CLI dispatch still
  exits 0 with all four gating checks wired.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from babylon.sentinels.seam_algebra import checks as checks_module
from babylon.sentinels.seam_algebra.checks import (
    _ARCHIVE_SEVERITY_PATH,
    _WEB_SEVERITY_PATH,
    check_severity_single_source,
)

pytestmark = pytest.mark.unit

_TOOL_PATH = Path(__file__).resolve().parents[3] / "tools" / "sentinel_check.py"

#: A minimal, self-contained stand-in for a clean, single-sourced classify
#: surface — no local literal, a real reference to ``resolve_severity``.
_CLEAN_SURFACE_SOURCE = (
    "from babylon.models.event_severity import resolve_severity\n"
    "\n"
    "def classify(event_type):\n"
    "    return resolve_severity(event_type).tier\n"
)


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Fixture semantics
# ---------------------------------------------------------------------------


def test_two_clean_fixtures_are_clean(tmp_path: Path) -> None:
    web = _write(tmp_path, "web.py", _CLEAN_SURFACE_SOURCE)
    archive = _write(tmp_path, "archive.py", _CLEAN_SURFACE_SOURCE)
    assert check_severity_single_source(web_path=web, archive_path=archive) == []


def test_a_surface_no_longer_referencing_resolve_severity_reds(tmp_path: Path) -> None:
    web = _write(tmp_path, "web.py", "def classify(event_type):\n    return 'warning'\n")
    archive = _write(tmp_path, "archive.py", _CLEAN_SURFACE_SOURCE)
    findings = check_severity_single_source(web_path=web, archive_path=archive)
    assert len(findings) == 1
    assert "resolve_severity" in findings[0]
    assert "web" in findings[0]


def test_a_reintroduced_literal_whose_values_match_the_table_is_clean(tmp_path: Path) -> None:
    """A reintroduced dict is only a violation if its VALUE diverges from the
    generated table -- a redundant-but-consistent literal is not itself the
    inequality this check's acceptance bar names."""
    web = _write(
        tmp_path,
        "web.py",
        _CLEAN_SURFACE_SOURCE + '\n_EVENT_SEVERITY = {"economic_crisis": "critical"}\n',
    )
    archive = _write(tmp_path, "archive.py", _CLEAN_SURFACE_SOURCE)
    table = {"economic_crisis": "critical"}
    findings = check_severity_single_source(
        web_path=web, archive_path=archive, generated_table=table
    )
    assert findings == []


def test_a_reintroduced_literal_naming_an_unknown_key_reds(tmp_path: Path) -> None:
    web = _write(
        tmp_path,
        "web.py",
        _CLEAN_SURFACE_SOURCE + '\n_EVENT_SEVERITY = {"not_a_real_event": "critical"}\n',
    )
    archive = _write(tmp_path, "archive.py", _CLEAN_SURFACE_SOURCE)
    findings = check_severity_single_source(
        web_path=web, archive_path=archive, generated_table={"economic_crisis": "critical"}
    )
    assert len(findings) == 1
    assert "not_a_real_event" in findings[0]


# ---------------------------------------------------------------------------
# Mutation efficacy — the canonical single-source mutation (design §4 U6)
# ---------------------------------------------------------------------------


def test_mutation_one_surface_hand_edited_to_differ_from_generated_table_reds(
    tmp_path: Path,
) -> None:
    """MUTATION (design §4 U6, verbatim): 'hand-edit one surface's resolved
    severity for one member to differ from the generated table -> check
    reds (the canonical single-source mutation).'"""
    web = _write(
        tmp_path,
        "web.py",
        _CLEAN_SURFACE_SOURCE + '\n_EVENT_SEVERITY = {"bifurcation_threshold": "warning"}\n',
    )
    archive = _write(tmp_path, "archive.py", _CLEAN_SURFACE_SOURCE)
    generated_table = {"bifurcation_threshold": "critical"}
    findings = check_severity_single_source(
        web_path=web, archive_path=archive, generated_table=generated_table
    )
    assert len(findings) == 1
    assert "bifurcation_threshold" in findings[0]
    assert "'warning'" in findings[0]
    assert "'critical'" in findings[0]


def test_the_same_mutation_on_the_archive_surface_also_reds(tmp_path: Path) -> None:
    """Symmetry: the mutation catches on EITHER surface, not just web."""
    web = _write(tmp_path, "web.py", _CLEAN_SURFACE_SOURCE)
    archive = _write(
        tmp_path,
        "archive.py",
        _CLEAN_SURFACE_SOURCE + '\nEVENT_SEVERITY = {"bifurcation_threshold": "warning"}\n',
    )
    generated_table = {"bifurcation_threshold": "critical"}
    findings = check_severity_single_source(
        web_path=web, archive_path=archive, generated_table=generated_table
    )
    assert len(findings) == 1
    assert "archive" in findings[0]
    assert "bifurcation_threshold" in findings[0]


def test_mutation_under_the_other_retired_literal_name_also_reds(tmp_path: Path) -> None:
    """A mutation reintroducing the OTHER surface's canonical name
    (``EVENT_SEVERITY`` in the web bridge, ``_EVENT_SEVERITY`` in the Archive
    file) is caught too -- the check does not assume a fixed name-per-file."""
    web = _write(
        tmp_path,
        "web.py",
        _CLEAN_SURFACE_SOURCE + '\nEVENT_SEVERITY = {"pogrom": "informational"}\n',
    )
    archive = _write(tmp_path, "archive.py", _CLEAN_SURFACE_SOURCE)
    generated_table = {"pogrom": "warning"}
    findings = check_severity_single_source(
        web_path=web, archive_path=archive, generated_table=generated_table
    )
    assert len(findings) == 1
    assert "pogrom" in findings[0]


# ---------------------------------------------------------------------------
# Liveness: the real, shipped surfaces against the current tree
# ---------------------------------------------------------------------------


def test_real_surfaces_are_clean_on_the_post_u2_estate() -> None:
    assert check_severity_single_source() == []


def test_paths_resolve_to_the_real_shipped_surfaces() -> None:
    assert _WEB_SEVERITY_PATH.is_file()
    assert _ARCHIVE_SEVERITY_PATH.is_file()
    assert _WEB_SEVERITY_PATH.name == "engine_bridge.py"
    assert _ARCHIVE_SEVERITY_PATH.name == "chronicle_salience.py"


# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------


def test_check_severity_single_source_is_registered_in_gating_checks() -> None:
    """WIRING: the check function sits in the tuple ``main()`` actually
    iterates -- a deleted or mistyped ``_GATING_CHECKS`` entry must fail this
    test even though the direct-call tests above stay green."""
    wired_checks = [check for _, check in checks_module._GATING_CHECKS]
    assert check_severity_single_source in wired_checks


def test_cli_entry_point_is_still_clean_with_severity_single_source_wired() -> None:
    """``sentinel_check.py seam-algebra --check`` exits 0 with all four gating
    checks (disconnected-subsystem + gate-satisfaction + severity-single-source
    + stub-vs-calculator) now wired."""
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, trusted path
        [sys.executable, str(_TOOL_PATH), "seam-algebra", "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "SEAM-ALGEBRA sensor reds against the shipped registry:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "severity single-sourced" in result.stdout
