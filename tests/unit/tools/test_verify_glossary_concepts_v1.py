"""Independent behavioral checks for GlossaryConceptsV1."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from tools.verify_glossary_concepts_v1 import (
    GlossaryConceptsRefusal,
    compute_semantic_sha256,
    load_concepts,
    load_contract,
    main,
    verify_all,
)

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "contracts" / "glossary_concepts_v1.yaml"
FIXTURE = ROOT / "contracts" / "fixtures" / "glossary_concepts_v1.jsonl"


def test_shared_contract_verifies_independently() -> None:
    contract = load_contract(SCHEMA)

    assert contract["meta"]["contract"] == "GlossaryConceptsV1"
    assert verify_all(contract, load_concepts(FIXTURE), ROOT) == []


def test_required_concepts_cover_the_dossier_display_labels() -> None:
    contract = load_contract(SCHEMA)
    concepts = {row["concept_id"]: row for row in load_concepts(FIXTURE)}

    assert set(concepts) == set(contract["constants"]["required_concept_ids"])
    assert concepts["median-wage"]["display_label"] == "Median wage"
    assert concepts["phi-hour"]["display_label"] == "Imperial rent Φ"
    assert concepts["census-identity"]["display_label"] == "Census identity"


def test_fixture_bytes_and_semantic_digest_match_the_contract() -> None:
    contract = load_contract(SCHEMA)
    concepts = load_concepts(FIXTURE)

    assert contract["constants"]["fixture_sha256"] != contract["constants"]["semantic_sha256"]
    assert compute_semantic_sha256(concepts) == contract["constants"]["semantic_sha256"]


def test_unexpected_concept_refuses() -> None:
    contract = load_contract(SCHEMA)
    concepts = copy.deepcopy(load_concepts(FIXTURE))
    concepts.append(
        {
            "concept_id": "mystery-term",
            "term": "Mystery",
            "display_label": "Mystery",
            "definition": "Not part of the pinned set.",
            "evidence_class": "Designed",
            "citation_source_id": "glossary-concepts-v1",
            "citation_locator": "contracts/fixtures/glossary_concepts_v1.jsonl#concept_id=mystery-term",
        }
    )

    errors = verify_all(contract, concepts, ROOT)

    assert any("mystery-term" in error for error in errors)


def test_display_label_drift_refuses() -> None:
    contract = load_contract(SCHEMA)
    concepts = copy.deepcopy(load_concepts(FIXTURE))
    row = next(item for item in concepts if item["concept_id"] == "median-wage")
    row["display_label"] = "Median Wage"

    errors = verify_all(contract, concepts, ROOT)

    assert any("median-wage" in error for error in errors)


def test_evidence_class_outside_the_compact_refuses() -> None:
    contract = load_contract(SCHEMA)
    concepts = copy.deepcopy(load_concepts(FIXTURE))
    concepts[0]["evidence_class"] = "Speculative"

    errors = verify_all(contract, concepts, ROOT)

    assert any("evidence_class" in error for error in errors)


def test_fixture_digest_drift_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    contract = load_contract(SCHEMA)
    # Point the pinned fixture path at an existing file with different bytes:
    # the SHA-256 census must refuse before any row is trusted.
    monkeypatch.setattr(
        "tools.verify_glossary_concepts_v1.FIXTURE_PATH", "contracts/glossary_concepts_v1.yaml"
    )

    with pytest.raises(GlossaryConceptsRefusal) as exc_info:
        verify_all(contract, load_concepts(FIXTURE), ROOT)

    assert exc_info.value.code == "fixture_digest"


def test_compiled_contract_drift_refuses() -> None:
    contract = load_contract(SCHEMA)
    contract["constants"]["grant_tick"] = 1

    with pytest.raises(GlossaryConceptsRefusal) as exc_info:
        verify_all(contract, load_concepts(FIXTURE), ROOT)

    assert exc_info.value.code == "compiled_contract_drift"


def test_concept_id_shape_refuses() -> None:
    contract = load_contract(SCHEMA)
    concepts = copy.deepcopy(load_concepts(FIXTURE))
    concepts[0]["concept_id"] = "Bad Id"

    errors = verify_all(contract, concepts, ROOT)

    assert any("concept id shape drift" in error for error in errors)


def test_loader_refuses_malformed_fixture(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fixture.jsonl"
    fixture_path.write_text('{"concept_id": "x"}\n', encoding="utf-8")

    with pytest.raises(GlossaryConceptsRefusal) as exc_info:
        load_concepts(fixture_path)

    assert exc_info.value.code == "concept_row_shape"


def test_cli_derives_repo_root_independently_of_fixture_location(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture_path = tmp_path / "elsewhere" / "copied.jsonl"
    fixture_path.parent.mkdir(parents=True)
    fixture_path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "verify_glossary_concepts_v1.py",
            "--schema",
            str(SCHEMA),
            "--fixture",
            str(fixture_path),
        ],
    )

    assert main() == 0


def test_cli_prints_typed_refusal_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fixture_path = tmp_path / "malformed.jsonl"
    rows = [json.loads(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines()]
    rows[0].pop("concept_id")
    fixture_path.write_text(
        "\n".join(json.dumps(row, separators=(",", ":")) for row in rows),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "verify_glossary_concepts_v1.py",
            "--schema",
            str(SCHEMA),
            "--fixture",
            str(fixture_path),
        ],
    )

    assert main() == 1
    assert capsys.readouterr().out == "concept_row_shape: 1\n"
