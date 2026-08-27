"""Exact decision-index contract for the governed Neel program architecture."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DECISIONS_DIR = Path(__file__).resolve().parents[3] / "ai" / "decisions"
ADR_STEM = "ADR232_neel_integration_program_architecture"
ADR_PATH = DECISIONS_DIR / f"{ADR_STEM}.yaml"
INDEX_PATH = DECISIONS_DIR / "index.yaml"
EXPECTED_TITLE = (
    "Neel integration freezes predecessor contracts, governs source quarantine, "
    "and requires an emergent material causal architecture"
)


def _mapping(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_adr232_declares_the_approved_program_law_and_exact_index_row() -> None:
    adr_document = _mapping(ADR_PATH)
    index_document = _mapping(INDEX_PATH)

    assert list(adr_document) == [ADR_STEM]
    decision = adr_document[ADR_STEM]
    assert decision["status"] == "accepted"
    assert decision["date"] == "2026-08-26"
    assert decision["title"] == EXPECTED_TITLE

    decision_text = " ".join(str(decision["decision"]).split())
    for required_text in (
        "Pannekoek, Bordiga, and Trotsky",
        "CPUSA",
        "Rust and BSL",
        "independently resolves participation",
        "no stored hinterland",
        "no authored sigmoid",
        "Linear alone owns current work",
    ):
        assert required_text in decision_text

    assert index_document["meta"]["version"] == "1.87.0"
    assert str(index_document["meta"]["updated"]) == "2026-08-26"
    assert index_document["decisions"][ADR_STEM] == {
        "title": EXPECTED_TITLE,
        "status": "accepted",
        "date": "2026-08-26",
        "file": ADR_PATH.name,
    }
