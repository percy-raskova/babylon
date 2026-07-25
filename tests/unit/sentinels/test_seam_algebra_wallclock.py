"""Tests for the seam-algebra wall-clock-call-site check (T1.1 Unit 7).

Four tiers, mirroring ``test_seam_algebra_gate_satisfaction.py``'s /
``test_seam_algebra_stub_vs_calculator.py``'s own shape:

- **Registry shape teeth** — a malformed :class:`WallclockCallSite` row fails
  loudly at construction (Constitution III.11).
- **Grounding + exemption semantics** (fixture files) — :func:`check_wallclock_call_sites`
  distinguishes a genuinely-live, non-exempt wall-clock read from an exempted
  one, and treats a stale registry row (the call was moved/edited/removed) as
  an infrastructure failure, never a silent pass.
- **Mutation efficacy** — the two literal mutation tests the design names
  verbatim (§4 U7): (1) a fixture ``datetime.now()`` call site feeding a
  hashed artifact reds; (2) deleting a known-leak exemption row reds the
  REAL shipped registry.
- **Liveness + CLI wiring** — the real, shipped registry is clean (with the
  six dated exemptions), and the family's CLI dispatch still exits 0.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.exemptions import SentinelExemption
from babylon.sentinels.seam_algebra import checks as checks_module
from babylon.sentinels.seam_algebra.checks import _REPO_ROOT, check_wallclock_call_sites
from babylon.sentinels.seam_algebra.registry import (
    WALLCLOCK_EXEMPTIONS,
    WALLCLOCK_REGISTRY,
    WallclockCallSite,
)

pytestmark = pytest.mark.unit

_TOOL_PATH = Path(__file__).resolve().parents[3] / "tools" / "sentinel_check.py"


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Registry shape teeth
# ---------------------------------------------------------------------------


def test_wallclock_call_site_rejects_blank_name() -> None:
    with pytest.raises(ValidationError):
        WallclockCallSite(
            name="", def_file="a.py", line=1, wallclock_call="datetime.now", artifact="x"
        )


def test_wallclock_call_site_rejects_blank_artifact() -> None:
    with pytest.raises(ValidationError):
        WallclockCallSite(
            name="x", def_file="a.py", line=1, wallclock_call="datetime.now", artifact=""
        )


def test_wallclock_call_site_rejects_non_py_def_file() -> None:
    with pytest.raises(ValidationError):
        WallclockCallSite(
            name="x", def_file="a.txt", line=1, wallclock_call="datetime.now", artifact="x"
        )


def test_wallclock_call_site_rejects_non_positive_line() -> None:
    with pytest.raises(ValidationError):
        WallclockCallSite(
            name="x", def_file="a.py", line=0, wallclock_call="datetime.now", artifact="x"
        )


def test_wallclock_call_site_rejects_unknown_wallclock_call() -> None:
    with pytest.raises(ValidationError):
        WallclockCallSite(
            name="x", def_file="a.py", line=1, wallclock_call="clock.tick", artifact="x"
        )


@pytest.mark.parametrize(
    "symbol",
    ["datetime.now", "datetime.utcnow", "time.time", "time.perf_counter", "time.monotonic"],
)
def test_wallclock_call_site_accepts_every_declared_symbol(symbol: str) -> None:
    """Positive control: each declared symbol is valid, not just whatever
    happens to be seeded today."""
    WallclockCallSite(
        name=f"probe_{symbol}", def_file="a.py", line=1, wallclock_call=symbol, artifact="x"
    )


def test_wallclock_call_site_is_frozen() -> None:
    site = WallclockCallSite(
        name="x", def_file="a.py", line=1, wallclock_call="datetime.now", artifact="y"
    )
    with pytest.raises(ValidationError):
        site.name = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Grounding + exemption semantics (fixture files)
# ---------------------------------------------------------------------------


def _patch_repo_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Redirect the check module's ``_REPO_ROOT`` to ``tmp_path``, mirroring
    ``test_seam_algebra_gate_satisfaction.py``'s own monkeypatch pattern."""
    monkeypatch.setattr("babylon.sentinels.seam_algebra.checks._REPO_ROOT", tmp_path)


def test_a_live_wallclock_read_with_no_exemption_reds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        tmp_path,
        "producer.py",
        "from datetime import datetime\n\ndef build():\n    return {'ts': datetime.now()}\n",
    )
    _patch_repo_root(monkeypatch, tmp_path)
    site = WallclockCallSite(
        name="fixture_live",
        def_file="producer.py",
        line=4,
        wallclock_call="datetime.now",
        artifact="a fixture hashed payload",
    )
    findings = check_wallclock_call_sites(sites=(site,), exemptions=())
    assert len(findings) == 1
    assert "wallclock-call-site" in findings[0]
    assert "datetime.now" in findings[0]


def test_an_exempted_wallclock_read_is_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        tmp_path,
        "producer.py",
        "from datetime import datetime\n\ndef build():\n    return {'ts': datetime.now()}\n",
    )
    _patch_repo_root(monkeypatch, tmp_path)
    site = WallclockCallSite(
        name="fixture_exempted",
        def_file="producer.py",
        line=4,
        wallclock_call="datetime.now",
        artifact="a fixture hashed payload",
    )
    exemption = SentinelExemption(
        key=("wallclock", "fixture_exempted"),
        reason="fixture exemption",
        owner="test",
        date="2026-07-21",
        tracking_task="#1",
    )
    assert check_wallclock_call_sites(sites=(site,), exemptions=(exemption,)) == []


def test_a_stale_line_raises_instead_of_reading_as_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A registry row citing a line that no longer holds the declared
    wall-clock call is an infrastructure failure -- never a silent pass."""
    _write(tmp_path, "producer.py", "def build():\n    return {'ts': 1}\n")
    _patch_repo_root(monkeypatch, tmp_path)
    site = WallclockCallSite(
        name="fixture_stale",
        def_file="producer.py",
        line=2,
        wallclock_call="datetime.now",
        artifact="a fixture hashed payload",
    )
    with pytest.raises(SentinelCheckError, match="registry row is stale"):
        check_wallclock_call_sites(sites=(site,), exemptions=())


def test_exemption_does_not_leak_across_unrelated_site_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The kind-tagged exemption key (`("wallclock", name)`) must not clear a
    DIFFERENT live site sharing no name with the exempted row."""
    _write(
        tmp_path,
        "producer.py",
        "from datetime import datetime\n\ndef build():\n    return {'ts': datetime.now()}\n",
    )
    _patch_repo_root(monkeypatch, tmp_path)
    site = WallclockCallSite(
        name="unrelated_live",
        def_file="producer.py",
        line=4,
        wallclock_call="datetime.now",
        artifact="a fixture hashed payload",
    )
    exemption = SentinelExemption(
        key=("wallclock", "some_other_site"),
        reason="an exemption for a DIFFERENT site",
        owner="test",
        date="2026-07-21",
        tracking_task="#1",
    )
    findings = check_wallclock_call_sites(sites=(site,), exemptions=(exemption,))
    assert len(findings) == 1
    assert "producer.py:4" in findings[0]


# ---------------------------------------------------------------------------
# Mutation efficacy — the two mutation tests the design names verbatim
# ---------------------------------------------------------------------------


def test_mutation_adding_a_datetime_now_at_a_hashed_fixture_call_site_reds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION (design §4 U7): 'add a datetime.now() at a fixture call site
    feeding a hashed artifact -> check reds'."""
    _write(
        tmp_path,
        "hashed_producer.py",
        "from datetime import datetime\n\n"
        "def build_hashed_payload():\n"
        "    return {'input_hash_component': 1, 'ts': datetime.now()}\n",
    )
    _patch_repo_root(monkeypatch, tmp_path)
    site = WallclockCallSite(
        name="mutation_witness",
        def_file="hashed_producer.py",
        line=4,
        wallclock_call="datetime.now",
        artifact="the fixture's hashed input_hash_component sibling field",
    )
    findings = check_wallclock_call_sites(sites=(site,), exemptions=())
    assert len(findings) == 1
    assert "wallclock-call-site" in findings[0]
    assert "datetime.now" in findings[0]
    assert "hashed_producer.py" in findings[0]


def test_mutation_removing_a_known_leak_exemption_reds_the_real_registry() -> None:
    """MUTATION (design §4 U7): 'delete a known-leak exemption row -> real run reds.'"""
    remaining = tuple(
        exemption
        for exemption in WALLCLOCK_EXEMPTIONS
        if exemption.key != ("wallclock", "tick_state_recorder_generated_at")
    )
    assert len(remaining) == len(WALLCLOCK_EXEMPTIONS) - 1
    findings = check_wallclock_call_sites(exemptions=remaining)
    assert len(findings) == 1
    assert "metrics.py" in findings[0]


def test_removing_all_exemptions_reds_every_known_leak() -> None:
    findings = check_wallclock_call_sites(exemptions=())
    assert len(findings) == len(WALLCLOCK_REGISTRY) == 6


# ---------------------------------------------------------------------------
# Liveness: the real, shipped registry against the current tree
# ---------------------------------------------------------------------------


def test_real_registry_is_clean_with_the_shipped_exemptions() -> None:
    assert check_wallclock_call_sites() == []


def test_shipped_exemptions_hold_exactly_the_six_known_leaks() -> None:
    keys = {exemption.key for exemption in WALLCLOCK_EXEMPTIONS}
    assert keys == {
        ("wallclock", "jsonl_recorder_session_dir_timestamp"),
        ("wallclock", "jsonl_recorder_summary_ended_at"),
        ("wallclock", "jsonl_recorder_export_zip_timestamp"),
        ("wallclock", "tick_state_recorder_generated_at"),
        ("wallclock", "run_manifest_wallclock_start"),
        ("wallclock", "run_manifest_wallclock_end"),
    }


def test_repo_root_resolves_to_the_real_repository_root() -> None:
    for site in WALLCLOCK_REGISTRY:
        assert (_REPO_ROOT / site.def_file).is_file(), site.def_file


# ---------------------------------------------------------------------------
# run_sensor exit-code contract — through main(), not direct calls
# ---------------------------------------------------------------------------


def test_check_wallclock_call_sites_is_registered_in_gating_checks() -> None:
    """WIRING: the check function sits in the tuple ``main()`` actually
    iterates -- a deleted or mistyped ``_GATING_CHECKS`` entry must fail this
    test even though the direct-call tests above stay green."""
    wired_checks = [check for _, check in checks_module._GATING_CHECKS]
    assert check_wallclock_call_sites in wired_checks


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def test_cli_entry_point_is_still_clean_with_wallclock_check_wired() -> None:
    """``sentinel_check.py seam-algebra --check`` exits 0 with ALL FIVE checks
    now wired."""
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
    assert "Seam-algebra clean" in result.stdout
