"""Exact decision-index contract for ADR225's governed record."""

from __future__ import annotations

from pathlib import Path

import yaml

DECISIONS_DIR = Path(__file__).resolve().parents[3] / "ai" / "decisions"
ADR_STEM = "ADR225_relational_territory_dossier_contract"
ADR_PATH = DECISIONS_DIR / f"{ADR_STEM}.yaml"
INDEX_PATH = DECISIONS_DIR / "index.yaml"
EXPECTED_INDEX_ROW = {
    "title": (
        "Relational Territory Dossier V1 is a language-neutral administrative "
        "projection contract, not a live game or persistence boundary"
    ),
    "status": "accepted",
    "date": "2026-08-23",
    "file": f"{ADR_STEM}.yaml",
}


def test_adr225_declares_its_key_and_exact_index_row() -> None:
    """Catch an ADR225 rename or incomplete catalog row that the sentinel misses."""
    adr_document = yaml.safe_load(ADR_PATH.read_text(encoding="utf-8"))
    index_document = yaml.safe_load(INDEX_PATH.read_text(encoding="utf-8"))

    assert list(adr_document) == [ADR_STEM]
    assert index_document["decisions"][ADR_STEM] == EXPECTED_INDEX_ROW
