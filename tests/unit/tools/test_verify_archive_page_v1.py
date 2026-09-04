"""Independent behavioral checks for ArchivePageV1."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from tools.verify_archive_page_v1 import (
    ArchivePageContractRefusal,
    compose_batch_sha256,
    load_contract,
    load_vectors,
    main,
    verify_all,
)

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "contracts" / "archive_page_v1.yaml"
VECTORS = ROOT / "contracts" / "archive_page_v1_vectors.jsonl"


def test_shared_contract_verifies_independently() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)

    assert contract["meta"]["contract"] == "ArchivePageV1"
    assert verify_all(contract, vectors, ROOT) == []


def test_every_vector_kind_is_present() -> None:
    vectors = load_vectors(VECTORS)

    assert {row["kind"] for row in vectors} == {"render", "refusal", "batch", "identity"}
    assert len(vectors) == 6
    assert [row["id"] for row in vectors if row["kind"] == "render"] == [
        "render-known-county",
        "render-link-grant-absent",
    ]


@pytest.mark.parametrize("field", ["markdown_hex", "content_sha256_hex", "search_text"])
def test_render_mutation_refuses_stale_semantic_bytes(field: str) -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    render = next(row for row in vectors if row["id"] == "render-known-county")
    if field == "markdown_hex":
        raw = bytearray.fromhex(render["data"][field])
        raw[0] ^= 0xFF
        render["data"][field] = raw.hex()
    elif field == "content_sha256_hex":
        render["data"][field] = "0" + render["data"][field][1:]
    else:
        render["data"][field] = render["data"][field] + " drift"

    errors = verify_all(contract, vectors, ROOT)

    assert any("render-known-county" in error for error in errors)


def test_markdown_mutation_that_keeps_the_digest_also_refuses() -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    render = next(row for row in vectors if row["id"] == "render-known-county")
    markdown = bytearray.fromhex(render["data"]["markdown_hex"])
    witness = b"Detroit"
    offset = bytes(markdown).index(witness)
    markdown[offset] = ord("X")
    render["data"]["markdown_hex"] = markdown.hex()
    render["data"]["content_sha256_hex"] = hashlib.sha256(bytes(markdown)).hexdigest()

    errors = verify_all(contract, vectors, ROOT)

    assert any("render-known-county" in error for error in errors)


def test_redlink_grant_presence_is_semantically_forced() -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    sparse = next(row for row in vectors if row["id"] == "render-link-grant-absent")
    sparse["data"]["knowledge"].append(
        {
            "page_ref": {"kind": "place", "id": "2622000"},
            "grant_key": "subject",
            "granted_tick": 42,
            "citation": {"source_id": "archive-subject", "locator": "place/2622000"},
        }
    )

    errors = verify_all(contract, vectors, ROOT)

    assert any("render-link-grant-absent" in error for error in errors)


def test_refusal_becomes_a_mismatch_when_the_subject_grant_appears() -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    refusal = next(row for row in vectors if row["id"] == "refusal-unknown-subject")
    refusal["data"]["knowledge"].insert(
        0,
        {
            "page_ref": {"kind": "county", "id": "26163"},
            "grant_key": "subject",
            "granted_tick": 42,
            "citation": {"source_id": "archive-subject", "locator": "county/26163"},
        },
    )

    errors = verify_all(contract, vectors, ROOT)

    assert any("refusal-unknown-subject" in error for error in errors)


def test_batch_semantic_mutation_moves_the_batch_digest() -> None:
    vectors = copy.deepcopy(load_vectors(VECTORS))
    batch = next(row for row in vectors if row["id"] == "batch-one-page")
    original = compose_batch_sha256(batch["data"])
    assert original == batch["data"]["sha256_hex"]
    page = batch["data"]["pages"][0]
    page["decision_question"] = page["decision_question"] + " drift"

    assert compose_batch_sha256(batch["data"]) != original


def test_identity_pins_the_checked_in_template_and_schema_bytes() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)
    identity = next(row for row in vectors if row["id"] == "identity-template-and-worker")
    template_bytes = (
        ROOT / "rust/crates/babylon-persistence/src/archive_page_v1.md.j2"
    ).read_bytes()
    schema_bytes = (
        ROOT / "rust/crates/babylon-persistence/migrations/semantic_archive_v1.sql"
    ).read_bytes()
    atom_schema_bytes = (
        ROOT / "rust/crates/babylon-persistence/migrations/archive_atom_v1.sql"
    ).read_bytes()
    template_sha256 = hashlib.sha256(template_bytes).hexdigest()
    worker = hashlib.sha256()
    worker.update(b"babylon.semantic-archive-worker.v1\x00")
    worker.update(schema_bytes)
    worker.update(atom_schema_bytes)
    worker.update(bytes.fromhex(template_sha256))

    assert identity["data"]["template_sha256_hex"] == template_sha256
    assert identity["data"]["worker_contract_sha256_hex"] == worker.hexdigest()
    assert contract["constants"]["template_sha256"] == template_sha256
    assert verify_all(contract, vectors, ROOT) == []


def test_compiled_contract_drift_refuses() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)
    contract["constants"]["max_pages_per_batch"] = 255

    with pytest.raises(ArchivePageContractRefusal) as exc_info:
        verify_all(contract, vectors, ROOT)

    assert exc_info.value.code == "compiled_contract_drift"


def test_missing_vector_kind_refuses() -> None:
    contract = load_contract(SCHEMA)
    vectors = [row for row in load_vectors(VECTORS) if row["kind"] != "refusal"]

    with pytest.raises(ArchivePageContractRefusal) as exc_info:
        verify_all(contract, vectors, ROOT)

    assert exc_info.value.code == "vector_kind_drift"


def test_duplicate_vector_id_refuses_before_indexing() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)
    duplicate = copy.deepcopy(vectors[1])
    duplicate["id"] = vectors[0]["id"]
    vectors.append(duplicate)

    with pytest.raises(ArchivePageContractRefusal) as exc_info:
        verify_all(contract, vectors, ROOT)

    assert exc_info.value.code == "duplicate_vector_id"


def test_cli_prints_typed_refusal_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vectors = copy.deepcopy(load_vectors(VECTORS))
    vectors[0].pop("id")
    vectors_path = tmp_path / "malformed.jsonl"
    vectors_path.write_text(
        "\n".join(json.dumps(row, separators=(",", ":")) for row in vectors),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "verify_archive_page_v1.py",
            "--schema",
            str(SCHEMA),
            "--vectors",
            str(vectors_path),
        ],
    )

    assert main() == 1
    assert capsys.readouterr().out == "vector_row_shape: 1\n"


def test_vector_loader_refuses_row_and_line_overflow(tmp_path: Path) -> None:
    row = '{"id":"x","kind":"x","data":{}}'
    rows_path = tmp_path / "rows.jsonl"
    rows_path.write_text("\n".join([row] * 33), encoding="utf-8")
    with pytest.raises(ArchivePageContractRefusal, match="too_many_rows"):
        load_vectors(rows_path)

    line_path = tmp_path / "line.jsonl"
    line_path.write_text("x" * 16_385, encoding="utf-8")
    with pytest.raises(ArchivePageContractRefusal, match="invalid_line_length"):
        load_vectors(line_path)


def test_vector_loader_refuses_duplicate_json_keys(tmp_path: Path) -> None:
    vectors_path = tmp_path / "duplicate-key.jsonl"
    vectors_path.write_text(
        '{"id":"a","id":"b","kind":"x","data":{}}',
        encoding="utf-8",
    )

    with pytest.raises(ArchivePageContractRefusal) as exc_info:
        load_vectors(vectors_path)

    assert exc_info.value.code == "duplicate_json_key"


def test_compiled_layout_drift_refuses() -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)
    fields = contract["layouts"]["page_input_v1"]["fields"]
    fields[0], fields[1] = fields[1], fields[0]

    with pytest.raises(ArchivePageContractRefusal) as exc_info:
        verify_all(contract, vectors, ROOT)

    assert exc_info.value.code == "compiled_contract_drift"
    assert exc_info.value.detail == "layouts"


def test_identity_cross_checks_the_contract_template_constant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract = load_contract(SCHEMA)
    vectors = load_vectors(VECTORS)
    monkeypatch.setattr("tools.verify_archive_page_v1.TEMPLATE_SHA256", "0" * 64)

    errors = verify_all(contract, vectors, ROOT)

    assert any("template SHA-256 drift from contract constant" in error for error in errors)


@pytest.mark.parametrize("material_field", ["value", "locator"])
def test_ungranted_signal_material_in_markdown_refuses(material_field: str) -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    sparse = next(row for row in vectors if row["id"] == "render-link-grant-absent")
    sparse["data"]["signals"].append(
        {
            "grant_key": "income",
            "label": "Income",
            "value": "999999 dollars",
            "citation": {
                "source_id": "acs-2022",
                "locator": "fact_acs_income county_fips=26163",
            },
        }
    )
    markdown = bytearray.fromhex(sparse["data"]["markdown_hex"])
    leak = "999999 dollars" if material_field == "value" else "fact_acs_income county_fips=26163"
    markdown.extend(f"\n\n{leak}\n".encode())
    sparse["data"]["markdown_hex"] = markdown.hex()
    sparse["data"]["content_sha256_hex"] = hashlib.sha256(bytes(markdown)).hexdigest()

    errors = verify_all(contract, vectors, ROOT)

    expected = (
        "ungranted signal value leaked: income"
        if material_field == "value"
        else "ungranted signal locator leaked: income"
    )
    assert any(expected in error for error in errors)


def test_redlink_known_label_substring_outside_the_link_token_is_not_a_leak() -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    sparse = next(row for row in vectors if row["id"] == "render-link-grant-absent")
    markdown = bytearray.fromhex(sparse["data"]["markdown_hex"])
    markdown.extend(b"\n\nSee Riverview annex notes.\n")
    sparse["data"]["markdown_hex"] = markdown.hex()
    sparse["data"]["content_sha256_hex"] = hashlib.sha256(bytes(markdown)).hexdigest()

    assert verify_all(contract, vectors, ROOT) == []


def test_cli_derives_repo_root_independently_of_vectors_location(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vectors_path = tmp_path / "elsewhere" / "copied.jsonl"
    vectors_path.parent.mkdir(parents=True)
    vectors_path.write_text(VECTORS.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "verify_archive_page_v1.py",
            "--schema",
            str(SCHEMA),
            "--vectors",
            str(vectors_path),
        ],
    )

    assert main() == 0


def test_resolve_tick_zero_refuses_like_the_rust_batch_constructor() -> None:
    vectors = copy.deepcopy(load_vectors(VECTORS))
    batch = next(row for row in vectors if row["id"] == "batch-empty")
    batch["data"]["resolve_tick"] = 0

    errors = verify_all(load_contract(SCHEMA), vectors, ROOT)

    assert any("batch-empty: invalid_tick" in error for error in errors)


def test_page_verified_tick_zero_refuses_with_the_typed_refusal() -> None:
    vectors = copy.deepcopy(load_vectors(VECTORS))
    render = next(row for row in vectors if row["id"] == "render-known-county")
    render["data"]["verified_tick"] = 0

    with pytest.raises(ArchivePageContractRefusal) as exc_info:
        verify_all(load_contract(SCHEMA), vectors, ROOT)

    assert exc_info.value.code == "invalid_tick"
    assert "data.verified_tick" in exc_info.value.detail


def test_knowledge_granted_tick_zero_remains_valid_like_the_rust_constructor() -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    render = next(row for row in vectors if row["id"] == "render-known-county")
    render["data"]["knowledge"][0]["granted_tick"] = 0

    assert verify_all(contract, vectors, ROOT) == []


def test_digest32_rejects_whitespace_padding() -> None:
    vectors = copy.deepcopy(load_vectors(VECTORS))
    batch = next(row for row in vectors if row["id"] == "batch-empty")
    digest = batch["data"]["tick_content_hash_hex"]
    batch["data"]["tick_content_hash_hex"] = digest[:2] + "  " + digest[4:]

    errors = verify_all(load_contract(SCHEMA), vectors, ROOT)

    assert any("batch-empty: invalid_digest" in error for error in errors)


def test_batch_vector_row_ids_are_pinned() -> None:
    vectors = copy.deepcopy(load_vectors(VECTORS))
    batch = next(row for row in vectors if row["id"] == "batch-empty")
    batch["id"] = "batch-empty-renamed"

    with pytest.raises(ArchivePageContractRefusal) as exc_info:
        verify_all(load_contract(SCHEMA), vectors, ROOT)

    assert exc_info.value.code == "vector_id_drift"


def test_non_dict_page_element_refuses_with_the_typed_code() -> None:
    vectors = copy.deepcopy(load_vectors(VECTORS))
    batch = next(row for row in vectors if row["id"] == "batch-one-page")
    batch["data"]["pages"][0] = ["not", "a", "page"]

    errors = verify_all(load_contract(SCHEMA), vectors, ROOT)

    assert any("batch-one-page: invalid_pages" in error for error in errors)
    with pytest.raises(ArchivePageContractRefusal) as exc_info:
        compose_batch_sha256(batch["data"])
    assert exc_info.value.code == "invalid_pages"
    assert exc_info.value.detail == "pages[0]"


def test_refusal_details_carry_full_field_paths() -> None:
    contract = load_contract(SCHEMA)
    vectors = copy.deepcopy(load_vectors(VECTORS))
    render = next(row for row in vectors if row["id"] == "render-known-county")
    render["data"]["signals"][0]["citation"]["source_id"] = ""

    with pytest.raises(ArchivePageContractRefusal) as exc_info:
        verify_all(contract, vectors, ROOT)

    assert "signals[0].citation.source_id" in exc_info.value.detail

    vectors = copy.deepcopy(load_vectors(VECTORS))
    render = next(row for row in vectors if row["id"] == "render-known-county")
    render["data"]["links"][0]["known_label"] = ""

    with pytest.raises(ArchivePageContractRefusal) as exc_info:
        verify_all(contract, vectors, ROOT)

    assert "links[0].known_label" in exc_info.value.detail
