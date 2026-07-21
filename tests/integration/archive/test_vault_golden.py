"""WO-51 contract: the golden-vault byte-gate guards real drift, loudly.

Two legs: the ``single_county`` gate genuinely passes against the
committed manifest (two independent in-process bakes, byte-identical
HEAD + per-page sha map), and — the STANDING-RULE mutation validation —
a tampered golden REDs the gate with a per-file drift row, never a quiet
pass. The runner-backed ``detroit_tri_county`` leg lives in
``mise run qa:vault-regression`` (Postgres required) rather than here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_TOOLS_DIR = _REPO_ROOT / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import vault_regression  # type: ignore[import-not-found]  # noqa: E402

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def test_single_county_gate_passes_against_the_committed_golden() -> None:
    """Two independent bakes match each other AND the committed manifest."""
    assert vault_regression.compare(["single_county"]) == 0


def test_a_tampered_golden_reds_the_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Mutation validation: one flipped page sha must FAIL the compare."""
    committed = json.loads(
        (vault_regression.BASELINE_ROOT / "single_county" / "manifest.json").read_text(
            encoding="utf8"
        )
    )
    first_page = sorted(committed["files"])[0]
    committed["files"][first_page] = "0" * 64
    tampered = tmp_path / "single_county" / "manifest.json"
    tampered.parent.mkdir(parents=True)
    tampered.write_text(json.dumps(committed), encoding="utf8")

    monkeypatch.setattr(vault_regression, "_manifest_path", lambda _scenario: tampered)
    assert vault_regression.compare(["single_county"]) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert f"CHANGED {first_page}" in out


def test_drift_table_attributes_adds_removes_and_changes() -> None:
    """The drift table names every divergence class per file."""
    rows = vault_regression._drift_table(
        {"a.md": "1", "b.md": "2", "c.md": "3"},
        {"a.md": "1", "b.md": "9", "d.md": "4"},
    )
    assert rows == ["  CHANGED b.md", "  REMOVED c.md", "  ADDED   d.md"]


def test_missing_manifest_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    """No committed golden is an error, never a silent pass (III.11)."""
    monkeypatch.setattr(
        vault_regression, "_manifest_path", lambda _s: Path("/nonexistent/manifest.json")
    )
    assert vault_regression.compare(["single_county"]) == 1
