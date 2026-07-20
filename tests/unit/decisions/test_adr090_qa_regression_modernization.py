"""Structural gate: every ADR file's declared top-level key matches its
filename, and every ADR file has a corresponding index.yaml catalog entry.
Mirrors the existing repo convention (every file under ai/decisions/ pairs
one YAML top-level key == filename stem, catalogued in index.yaml's
``decisions:`` map) -- this test targets specifically the new ADR this task
adds, so it fails until the file exists and both edits are made.
"""

from __future__ import annotations

from pathlib import Path

import yaml

DECISIONS_DIR = Path(__file__).resolve().parents[3] / "ai" / "decisions"
INDEX_PATH = DECISIONS_DIR / "index.yaml"

NEW_ADR_STEM = "ADR090_qa_regression_modernization"


def test_new_adr_file_exists_with_matching_top_level_key() -> None:
    adr_path = DECISIONS_DIR / f"{NEW_ADR_STEM}.yaml"
    assert adr_path.exists(), f"missing {adr_path}"
    data = yaml.safe_load(adr_path.read_text())
    assert list(data.keys()) == [NEW_ADR_STEM], (
        f"{adr_path} top-level key must equal its filename stem"
    )
    entry = data[NEW_ADR_STEM]
    assert entry["status"] == "accepted"
    for required_field in ("date", "title", "context", "decision", "consequences", "evidence"):
        assert required_field in entry, f"{adr_path} missing required field {required_field!r}"


def test_new_adr_is_catalogued_in_index() -> None:
    index = yaml.safe_load(INDEX_PATH.read_text())
    assert NEW_ADR_STEM in index["decisions"], (
        f"{NEW_ADR_STEM} is missing from ai/decisions/index.yaml's decisions: map"
    )
    catalog_entry = index["decisions"][NEW_ADR_STEM]
    assert catalog_entry["file"] == f"{NEW_ADR_STEM}.yaml"
    assert catalog_entry["status"] == "accepted"


def test_state_yaml_records_the_qa_regression_modernization() -> None:
    """The state file must name the ADR and a real construct it introduced, not just the branch."""
    state_path = Path(__file__).resolve().parents[3] / "ai" / "state.yaml"
    text = state_path.read_text()
    assert NEW_ADR_STEM.split("_")[0] in text, "state.yaml does not cite the new ADR id"
    assert "CoverageGap" in text, (
        "state.yaml does not name the E1 construct this program introduced"
    )
    assert "QA:REGRESSION GATE MODERNIZED" in text


def test_no_unfilled_placeholders_in_the_governance_records() -> None:
    """Every <FILL> / <SUBSTITUTE> marker must be resolved before these land.

    Permanent governance history the moment this task commits it. Zero
    tolerance, no carve-out.
    """
    adr_path = DECISIONS_DIR / f"{NEW_ADR_STEM}.yaml"
    state_path = Path(__file__).resolve().parents[3] / "ai" / "state.yaml"
    if not adr_path.exists():
        return  # covered by test_new_adr_file_exists_with_matching_top_level_key
    for path in (adr_path, state_path):
        text = path.read_text()
        assert "<FILL" not in text, f"{path} still has an unresolved <FILL marker"
        assert "<SUBSTITUTE" not in text, f"{path} still has an unresolved <SUBSTITUTE marker"
