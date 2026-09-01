"""Contract-first RED laws for the PER-281 full Rust persistence cutover."""

from __future__ import annotations

import hashlib
import json
import struct
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml
from tools.verify_rust_persistence_cutover_v1 import (
    CutoverFinding,
    RustPersistenceCutoverRefusal,
    _entrypoint_executes_required_command,
    _entrypoint_source,
    _verify_vectors,
    load_cutover_contract,
    validate_cutover_contract,
    verify_cutover_contract,
)

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT / "contracts" / "rust_persistence_cutover_v1.yaml"
CUTOVER_VECTORS = ROOT / "contracts" / "rust_persistence_cutover_v1_vectors.jsonl"
TICK_CONTENT_VECTORS = ROOT / "contracts" / "tick_content_hash_v1_vectors.jsonl"


def _contract() -> dict[str, Any]:
    return load_cutover_contract(CONTRACT)


def _vector_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return {str(row["id"]): row for row in rows}


def test_contract_freezes_the_one_accepted_production_root() -> None:
    contract = _contract()
    authority = contract["authority"]

    assert contract["meta"] == {
        "contract": "RustPersistenceCutoverV1",
        "version": 1,
        "issue": "PER-281",
        "parent": "PER-21",
        "stopped_with": "PER-280",
    }
    assert authority["canonical_crate"] == "babylon-persistence"
    assert authority["composition_type"] == "DurableReplayRuntimeV1"
    assert authority["prepared_tick_type"] == "PreparedCommittedTickV1"
    assert authority["prohibited_owners"] == ["babylon-tick", "babylon-client"]


def test_contract_refuses_a_synthetic_tick_zero_marker() -> None:
    foundation = _contract()["foundation"]

    assert foundation["tick_commit_starts_at"] == 1
    assert foundation["tick_zero_marker"] == "prohibited"
    assert foundation["relation"] == "babylon_state.campaign_foundation"


def test_authority_ledger_rows_have_one_language_neutral_preimage() -> None:
    ledger = _contract()["schema_epochs"]["activation_ledger"]
    wire = ledger["wire"]

    assert wire == {
        "domain_utf8": "babylon.persistence-authority-ledger-row.v1\0",
        "layout_u32": 1,
        "closed_state_tags": {"prepared": 1, "rust_active": 2},
        "fields": [
            "ordinal_u16_be",
            "state_tag_u8",
            "schema_epoch_u16_be",
            "contract_sha256",
            "reader_contract_sha256",
            "predecessor_optional_digest32",
        ],
        "optional_digest32": {"none_tag_u8": 0, "some_tag_u8": 1},
        "row_sha256": "sha256_exact_canonical_bytes",
        "predecessor_law": ("rust_active predecessor_sha256 equals the exact prepared-row SHA-256"),
        "vector_ids": ["authority-ledger-prepared", "authority-ledger-rust-active"],
    }

    def encode_row(data: dict[str, Any]) -> bytes:
        state_tags = wire["closed_state_tags"]
        assert state_tags[data["state"]] == data["state_tag"]
        predecessor = data["predecessor_sha256"]
        predecessor_bytes = b"\0" if predecessor is None else b"\x01" + bytes.fromhex(predecessor)
        return b"".join(
            [
                wire["domain_utf8"].encode("utf-8"),
                int(wire["layout_u32"]).to_bytes(4, "big"),
                int(data["ordinal"]).to_bytes(2, "big"),
                int(data["state_tag"]).to_bytes(1, "big"),
                int(data["schema_epoch"]).to_bytes(2, "big"),
                bytes.fromhex(data["contract_sha256"]),
                bytes.fromhex(data["reader_contract_sha256"]),
                predecessor_bytes,
            ]
        )

    rows = _vector_rows(CUTOVER_VECTORS)
    prepared = rows["authority-ledger-prepared"]
    active = rows["authority-ledger-rust-active"]
    assert prepared["kind"] == active["kind"] == "valid_authority_ledger"

    prepared_bytes = encode_row(prepared["data"])
    prepared_sha256 = hashlib.sha256(prepared_bytes).hexdigest()
    assert prepared["expected_hex"] == prepared_bytes.hex()
    assert prepared["expected_sha256"] == prepared_sha256
    assert prepared["data"]["predecessor_sha256"] is None

    active_bytes = encode_row(active["data"])
    assert active["data"]["predecessor_sha256"] == prepared_sha256
    assert active["expected_hex"] == active_bytes.hex()
    assert active["expected_sha256"] == hashlib.sha256(active_bytes).hexdigest()


@pytest.mark.parametrize("case", ["prepared_bytes", "active_predecessor"])
def test_verifier_refuses_digest_adjusted_authority_ledger_weakening(
    tmp_path: Path, case: str
) -> None:
    contract = deepcopy(_contract())
    rows = list(_vector_rows(CUTOVER_VECTORS).values())
    prepared = next(row for row in rows if row["id"] == "authority-ledger-prepared")
    active = next(row for row in rows if row["id"] == "authority-ledger-rust-active")
    if case == "prepared_bytes":
        weakened = bytes.fromhex(prepared["expected_hex"])[:-1] + b"\x01"
        prepared["expected_hex"] = weakened.hex()
        prepared["expected_sha256"] = hashlib.sha256(weakened).hexdigest()
    else:
        active["data"]["predecessor_sha256"] = "0" * 64
        weakened = bytes.fromhex(active["expected_hex"])[:-32] + bytes(32)
        active["expected_hex"] = weakened.hex()
        active["expected_sha256"] = hashlib.sha256(weakened).hexdigest()
    payload = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows
    ).encode("utf-8")
    destination = tmp_path / contract["vectors"]["path"]
    destination.parent.mkdir(parents=True)
    destination.write_bytes(payload)
    contract["vectors"]["sha256"] = hashlib.sha256(payload).hexdigest()
    findings: set[CutoverFinding] = set()

    _verify_vectors(contract, tmp_path, findings)

    assert "cutover_authority_ledger_identity" in {finding.code for finding in findings}


def test_per280_reader_contract_is_exactly_linked() -> None:
    boundary = _contract()["reader_boundary"]
    path = ROOT / boundary["contract"]

    assert path.is_file(), "the stopped PER-280 contract must join this lane"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == boundary["sha256"]
    assert (
        boundary["edges"],
        boundary["source_files"],
        boundary["runtime_consumer_edges"],
        boundary["views"],
    ) == (
        0,
        0,
        0,
        0,
    )
    assert (
        boundary["epoch7_edges"],
        boundary["epoch7_source_files"],
        boundary["epoch7_views"],
    ) == (
        13,
        5,
        10,
    )


def test_joined_python_reader_retirement_has_no_surviving_api_or_edge_claim() -> None:
    contract = _contract()
    legacy_path = "src/babylon/persistence/postgres_runtime/_legacy.py"
    retired_symbols = {
        "persist_hex_state",
        "persist_infrastructure_state",
        "query_infrastructure_link_state",
        "get_hex_state_for_tick",
        "get_hex_time_series",
        "persist_hex_activity",
        "refresh_hex_latest",
        "reconstruct_hex_state",
    }
    declared = next(
        row["symbols"]
        for row in contract["python_authority"]["must_delete"]
        if row["path"] == legacy_path
    )
    assert retired_symbols <= set(declared)
    for relative in [
        "src/babylon/persistence/protocols.py",
        "src/babylon/persistence/runtime_db.py",
        legacy_path,
    ]:
        path = ROOT / relative
        source = path.read_text(encoding="utf-8") if path.exists() else ""
        assert not any(f"def {symbol}(" in source for symbol in retired_symbols)

    assert contract["reader_boundary"]["projection_relations"] == []
    assert contract["reader_boundary"]["edges"] == 0
    assert contract["python_authority"]["census"]["inventory_entries"] == 131
    assert contract["python_authority"]["census"]["scan_roots"] == [
        "src/babylon",
        "tools",
        ".mise.toml",
        ".mise/tasks",
    ]


def test_exact_rust_runtime_root_exists_and_absorbs_schema_epoch_cli() -> None:
    authority = _contract()["authority"]
    module = ROOT / authority["composition_module"]
    binary = ROOT / authority["composition_binary"]
    absorbed = ROOT / authority["absorbed_binary"]

    assert module.is_file()
    assert binary.is_file()
    assert not absorbed.exists(), "a second production migrator command must not survive"

    module_source = module.read_text(encoding="utf-8")
    binary_source = binary.read_text(encoding="utf-8")
    for symbol in [
        authority["composition_type"],
        authority["prepared_tick_type"],
        authority["activation_function"],
    ]:
        assert symbol in module_source
    assert authority["composition_type"] in binary_source


def test_tick_and_client_do_not_gain_persistence_authority() -> None:
    tick_manifest = (ROOT / "rust/crates/babylon-tick/Cargo.toml").read_text(encoding="utf-8")
    client_manifest = (ROOT / "rust/crates/babylon-client/Cargo.toml").read_text(encoding="utf-8")

    assert "babylon-persistence" not in tick_manifest
    assert "babylon-persistence" not in client_manifest


def test_old_opaque_rows_are_not_the_final_semantic_store() -> None:
    contract = _contract()
    storage_path = ROOT / "rust/crates/babylon-persistence/src/committed_tick_storage.rs"
    storage_source = storage_path.read_text(encoding="utf-8") if storage_path.exists() else ""

    for relation in contract["storage"]["prohibited_final_relations"]:
        assert relation not in storage_source
    for column in contract["storage"]["prohibited_final_columns"]:
        assert f'"{column}"' not in storage_source


def test_python_game_managed_authority_is_absent() -> None:
    rows = _contract()["python_authority"]["must_delete"]

    survivors: list[str] = []
    for row in rows:
        path = ROOT / row["path"]
        source = path.read_text(encoding="utf-8") if path.exists() else ""
        for symbol in row["symbols"]:
            if symbol.rsplit(".", 1)[-1] in source:
                survivors.append(f"{row['path']}::{symbol}")

    assert survivors == [], "Python authority survivors: " + ", ".join(survivors)


def test_python_coupled_tests_and_false_adapter_entrypoints_are_absent() -> None:
    """The one-way cutover deletes coupled tests and does not leave command shims."""
    authority = _contract()["python_authority"]

    for relative in authority["must_delete_coupled_tests"]:
        assert not (ROOT / relative).exists(), f"coupled Python test survived: {relative}"

    for row in authority["must_retire_entrypoints"]:
        path = ROOT / row["path"]
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8")
        if row["path"] == ".mise.toml":
            assert f'[tasks."{row["entrypoint"]}"]' not in source
        else:
            assert f"def {row['entrypoint']}(" not in source


def test_first_python_retirement_tranche_removes_only_caller_dead_authority() -> None:
    assert not (ROOT / "src/babylon/persistence/balkanization_history.py").exists()
    assert not (ROOT / "tests/integration/balkanization/test_audit_round_trip.py").exists()
    assert not (ROOT / "tests/integration/persistence/test_retention.py").exists()

    retention = (ROOT / "src/babylon/persistence/retention.py").read_text(encoding="utf-8")
    assert "def live_sessions(" not in retention
    assert "def enforce_single_live_session(" not in retention
    for preserved in [
        "def check_disk_preflight(",
        "def disk_warning_message(",
        "def default_archive_root(",
    ]:
        assert preserved in retention

    for preserved_path in [
        "src/babylon/persistence/hex_init.py",
        "src/babylon/persistence/migrations",
        "contracts/h3_reader_cutover_v1.yaml",
    ]:
        assert (ROOT / preserved_path).exists()
    assert not (ROOT / "src/babylon/persistence/archival.py").exists()


def test_caller_dead_python_game_session_and_trade_authority_are_absent() -> None:
    for relative in [
        "src/babylon/game/session.py",
        "src/babylon/game/trade.py",
        "tests/integration/game/test_session_integration.py",
        "tests/unit/game/test_session.py",
        "tests/unit/game/test_trend_view.py",
        "tests/unit/game/test_choropleth_view.py",
        "tests/unit/game/test_session_trade.py",
    ]:
        assert not (ROOT / relative).exists(), f"caller-dead Python authority: {relative}"

    pacing_test = (ROOT / "tests/unit/game/test_pacing.py").read_text(encoding="utf-8")
    assert "from babylon.game.session import create_new_campaign" not in pacing_test
    assert "class _MinimalFakeStore:" not in pacing_test


def test_independent_cutover_verifier_is_wired_into_the_static_gate() -> None:
    verifier = ROOT / "tools/verify_rust_persistence_cutover_v1.py"
    mise = (ROOT / ".mise.toml").read_text(encoding="utf-8")

    assert verifier.is_file()
    assert '[tasks."check:rust-persistence-cutover"]' in mise
    static = mise.split('[tasks."check:sentinels-static"]', 1)[1].split("\n[", 1)[0]
    assert '"check:rust-persistence-cutover"' in static


def test_only_losslessly_proved_whole_table_drop_is_predeclared() -> None:
    disposition = _contract()["data_disposition"]

    assert disposition["whole_table_drop_after_parity"] == ["public.hex_latest"]
    assert (
        "public.hex_r8_linear_features_reference"
        in disposition["identity_columns_only_until_lossless_destination_exists"]
    )
    assert disposition["lodes_destination"]["variants"] == [
        "hex_cell_id",
        "canada",
        "rest_of_usa",
    ]


def test_false_sidecar_producers_are_absent_and_relations_wait_for_zero_census() -> None:
    contract = _contract()
    vectors = list(_vector_rows(CUTOVER_VECTORS).values())
    semantic_rows = contract["semantic_rows"]
    false_codecs = {
        "hex_activity_v1",
        "hex_material_state_v1",
        "hex_terrain_state_v1",
        "infrastructure_link_state_v1",
    }
    false_relations = {
        "public.hex_activity",
        "public.hex_state",
        "public.hex_terrain_state",
        "public.infrastructure_link_state",
    }

    assert contract["vectors"]["rows"] == 56
    assert contract["vectors"]["valid_row_count"] == 14
    assert len(vectors) == 56
    assert false_codecs.isdisjoint({str(row["id"]) for row in semantic_rows["row_codecs"]})
    assert false_codecs.isdisjoint({str(row.get("codec", "")) for row in vectors})
    material = next(
        row for row in semantic_rows["producer_inventory"] if row["id"] == "material_state_rows_v1"
    )
    assert material["row_codecs"] == [
        "world_register_v1",
        "territory_state_v1",
        "dynamic_hex_state_v1",
        "organization_state_v1",
    ]
    assert material["closed_variants"] == [
        "world_register",
        "territory",
        "dynamic_hex",
        "organization",
    ]
    assert "emptiness_proof_type" not in material
    normalized = contract["storage"]["normalized_child_relations"]
    assert not any(
        any(codec in json.dumps(row, sort_keys=True) for codec in false_codecs)
        for row in normalized
    )

    disposition = contract["data_disposition"]
    assert (
        set(disposition["preserve_until_zero_row_census_then_drop_without_typed_replacement"])
        == false_relations
    )
    assert false_relations.isdisjoint(
        disposition["replace_then_drop_after_ordered_count_and_hash_parity"]
    )
    assert false_relations.isdisjoint(
        disposition["python_written_relation_disposition"]["typed_tick_replacement"]
    )
    assert contract["reader_boundary"]["projection_relations"] == []
    activity_backed_views = {
        "public.v_hex_mobilize",
        "public.v_hex_heat",
        "public.v_hex_intel",
    }
    future_views = {row["name"] for row in contract["reader_boundary"]["view_projections"]}
    assert activity_backed_views.isdisjoint(future_views)
    reader_contract = yaml.safe_load(
        (ROOT / contract["reader_boundary"]["contract"]).read_text(encoding="utf-8")
    )
    current_views = {row["canonical_relation"] for row in reader_contract["current_views"]}
    assert len(current_views) == contract["reader_boundary"]["epoch7_views"] == 10
    assert contract["reader_boundary"]["views"] == 0
    assert future_views == set()
    assert activity_backed_views < current_views
    assert all(
        finding.code != "reader_view_crosswalk"
        for finding in verify_cutover_contract(contract, ROOT)
    )


def test_material_row_contract_matches_the_accepted_typed_source_vocabulary() -> None:
    contract = _contract()
    semantic = contract["semantic_rows"]
    codecs = semantic["scalar_codecs"]
    rows = {row["id"]: row for row in semantic["row_codecs"]}

    assert codecs["stable_element_key_v1"] == {
        "domain_ascii_nul": "babylon.stable-element",
        "layout_u32": 1,
        "closed_kinds": {
            "stable_node_key": {
                "key_kind_u8": 1,
                "fields": ["scenario_qname", "local_name_lower_symbol"],
            },
            "stable_edge_key": {
                "key_kind_u8": 2,
                "fields": [
                    "scenario_qname",
                    "edge_type_ascii_graphic",
                    "source_local_name_lower_symbol",
                    "target_local_name_lower_symbol",
                ],
            },
            "stable_hyperedge_key": {
                "key_kind_u8": 3,
                "fields": ["scenario_qname", "local_name_lower_symbol"],
            },
        },
        "canonical_bytes": "exact_StableElementKeyV1_canonical_bytes",
        "runtime_graph_handles": "prohibited",
    }
    assert codecs["ordered_stable_element_keys_v1"] == {
        "layout": ["count_u32_be", "exact_ordered_items"],
        "item_layout": [
            "item_length_u32_be",
            "stable_element_key_v1_canonical_bytes",
        ],
        "order": "strictly_ascending_stable_element_key_v1_canonical_bytes",
        "duplicate_key": "refused",
        "maximum_items": 1_048_576,
    }
    assert rows["territory_state_v1"]["key_fields"] == ["territory_id:stable_element_key_v1"]
    assert rows["territory_state_v1"]["payload_fields"] == [
        "ordered_fields:ordered_named_bsl_fields_v1"
    ]
    assert rows["dynamic_hex_state_v1"]["payload_fields"] == [
        "c:f64_be_canonical",
        "v:f64_be_canonical",
        "s:f64_be_canonical",
        "k:f64_be_canonical",
        "biocapacity_stock:f64_be_canonical",
        "energy_stock:f64_be_canonical",
        "raw_material_stock:f64_be_canonical",
        "internet_access_pct:f64_be_canonical",
        "surveillance_coupling:f64_be_canonical",
    ]
    assert rows["organization_state_v1"]["key_fields"] == ["organization_id:stable_element_key_v1"]
    assert rows["organization_state_v1"]["payload_fields"] == [
        "organization_kind:stable_bsl_value_v1",
        "ordered_territory_ids:ordered_stable_element_keys_v1",
        "ordered_fields:ordered_named_bsl_fields_v1",
    ]
    material_vocabulary = json.dumps(
        [
            rows["territory_state_v1"],
            rows["dynamic_hex_state_v1"],
            rows["organization_state_v1"],
        ],
        sort_keys=True,
    )
    for stale_field in [
        "county_fips",
        "state_fips",
        "region_id",
        "organization_type",
        "home_county",
        "home_cell_id",
    ]:
        assert stale_field not in material_vocabulary
    assert {
        "Territory and organization identities are full checked StableElementKeyV1 "
        "canonical bytes, never shortened text aliases.",
        "Dynamic hex rows contain one H3 identity and exactly nine canonical f64 lanes; "
        "county, state, and region membership remain separate foundation authority.",
        "Organization kind is an exact OrgKind StableBslValueV1 enum and ordered "
        "territories are exact source-owned PRESENCE targets.",
    } <= set(semantic["laws"])


def test_h3_identity_codec_names_the_kernel_owned_type() -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))

    assert (
        contract["semantic_rows"]["scalar_codecs"]["h3_cell_id_i64_be"]["validation"]
        == "babylon_kernel::H3CellId::try_from(u64)"
    )
    assert (
        contract["storage"]["physical_scalar_columns"]["h3_cell_id_i64_be"]["rust_validation"]
        == "babylon_kernel::H3CellId::try_from(i64)"
    )
    assert (
        contract["storage"]["physical_scalar_columns"]["optional_h3_cell_id_i64_be"][
            "rust_validation"
        ]
        == "babylon_kernel::H3CellId::try_from(i64)"
    )
    assert "babylon_persistence::H3CellId" not in CONTRACT.read_text(encoding="utf-8")


def test_material_vectors_use_full_stable_keys_and_exact_source_owned_fields() -> None:
    vectors = _vector_rows(CUTOVER_VECTORS)

    assert vectors["row-territory-state"]["data"] == {
        "territory_id": {
            "tag": "stable_node_key",
            "scenario": "demo/territory-derived",
            "local_name": "aa",
        },
        "ordered_fields": [
            {"name": "heat", "value": {"tag": "real_f64_bits", "value": "0.375"}},
            {"name": "population", "value": {"tag": "int_i64", "value": "13"}},
            {
                "name": "production-total",
                "value": {"tag": "real_f64_bits", "value": "1.25"},
            },
            {
                "name": "territory-type",
                "value": {
                    "tag": "enum_type_and_member",
                    "enum_type": "TerritoryType",
                    "member": "CORE",
                },
            },
            {
                "name": "treasury",
                "value": {"tag": "currency_i128", "micro_units": "7000000"},
            },
        ],
    }
    assert vectors["row-dynamic-hex-state"]["data"] == {
        "cell_id": "608661359088893951",
        "c": "1",
        "v": "1",
        "s": "1",
        "k": "1",
        "biocapacity_stock": "1",
        "energy_stock": "1",
        "raw_material_stock": "1",
        "internet_access_pct": "1",
        "surveillance_coupling": "1",
    }
    assert vectors["row-organization-state"]["data"] == {
        "organization_id": {
            "tag": "stable_node_key",
            "scenario": "demo/organization-derived",
            "local_name": "f",
        },
        "organization_kind": {
            "tag": "enum_type_and_member",
            "enum_type": "OrgKind",
            "member": "POLITICAL_FACTION",
        },
        "ordered_territory_ids": [
            {
                "tag": "stable_node_key",
                "scenario": "demo/organization-derived",
                "local_name": "z",
            },
            {
                "tag": "stable_node_key",
                "scenario": "demo/organization-derived",
                "local_name": "aa",
            },
        ],
        "ordered_fields": [
            {"name": "members", "value": {"tag": "int_i64", "value": "15"}},
            {
                "name": "productivity",
                "value": {"tag": "real_f64_bits", "value": "1.25"},
            },
            {
                "name": "status",
                "value": {
                    "tag": "enum_type_and_member",
                    "enum_type": "OrgStatus",
                    "member": "ACTIVE",
                },
            },
            {
                "name": "treasury",
                "value": {"tag": "currency_i128", "micro_units": "7000000"},
            },
        ],
    }


def test_organization_territories_have_one_typed_normalized_order_mapping() -> None:
    storage = _contract()["storage"]

    assert storage["physical_scalar_columns"]["stable_element_key_v1"] == {
        "postgresql": "BYTEA",
        "nullable": False,
        "rust_type": "StableElementKeyV1",
        "encoding": "exact_canonical_bytes",
        "validation": "checked_before_insert",
    }
    relation = next(
        row
        for row in storage["normalized_child_relations"]
        if row["relation"] == "babylon_state.organization_territory_v1"
    )
    assert relation == {
        "relation": "babylon_state.organization_territory_v1",
        "parent": "babylon_state.organization_state_v1",
        "parent_key": ["campaign_id", "resolve_tick", "organization_id"],
        "columns": [
            "position_INTEGER_CHECK_gte_0",
            "territory_id_BYTEA_NOT_NULL_STABLE_ELEMENT_KEY_V1",
        ],
        "primary_key": ["campaign_id", "resolve_tick", "organization_id", "position"],
        "unique": ["campaign_id", "resolve_tick", "organization_id", "territory_id"],
        "foreign_key": "exact_parent_key_cascade",
    }
    assert (
        "Organization territory positions preserve strictly ascending exact "
        "StableElementKeyV1 canonical bytes from the source-owned PRESENCE topology."
        in storage["normalized_child_laws"]
    )
    assert "JSON" not in json.dumps(relation, sort_keys=True).upper()


def test_verifier_independently_recomputes_accepted_material_row_bytes(
    tmp_path: Path,
) -> None:
    results: dict[str, set[str]] = {}
    cases = {
        "territory-identity": "row-territory-state",
        "dynamic-lane": "row-dynamic-hex-state",
        "organization-identity": "row-organization-state",
        "organization-kind": "row-organization-state",
        "organization-territory-order": "row-organization-state",
    }
    for case, row_id in cases.items():
        contract = deepcopy(_contract())
        rows = list(_vector_rows(CUTOVER_VECTORS).values())
        row = next(candidate for candidate in rows if candidate["id"] == row_id)
        if case == "territory-identity":
            identity = row["data"]["territory_id"]
            if isinstance(identity, dict):
                identity["local_name"] = "z"
            else:
                row["data"]["territory_id"] = "other"
        elif case == "dynamic-lane":
            row["data"]["c"] = "2"
        elif case == "organization-identity":
            identity = row["data"]["organization_id"]
            if isinstance(identity, dict):
                identity["local_name"] = "council"
            else:
                row["data"]["organization_id"] = "other"
        elif case == "organization-kind":
            row["data"]["organization_kind"]["enum_type"] = "OtherKind"
        else:
            row["data"]["ordered_territory_ids"].reverse()
        payload = "".join(
            json.dumps(candidate, sort_keys=True, separators=(",", ":")) + "\n"
            for candidate in rows
        ).encode("utf-8")
        destination = tmp_path / case / contract["vectors"]["path"]
        destination.parent.mkdir(parents=True)
        destination.write_bytes(payload)
        contract["vectors"]["sha256"] = hashlib.sha256(payload).hexdigest()
        findings: set[CutoverFinding] = set()

        _verify_vectors(contract, tmp_path / case, findings)
        results[case] = {finding.code for finding in findings}

    assert results == {case: {"cutover_valid_row_identity"} for case in cases}


def test_unproduced_envelope_families_and_fake_empty_proof_are_absent() -> None:
    contract = _contract()
    vectors = list(_vector_rows(CUTOVER_VECTORS).values())
    semantic_rows = contract["semantic_rows"]
    false_families = {"subsystem", "conservation", "boundary_flow"}
    false_codecs = {"subsystem_v1", "conservation_v1", "boundary_flow_v1"}

    assert semantic_rows["family_order"] == [
        {"family": "graph", "tag_u8": 0x10},
        {"family": "state", "tag_u8": 0x11},
        {"family": "event", "tag_u8": 0x12},
        {"family": "checkpoint", "tag_u8": 0x16},
        {"family": "archive_dirty_receipt", "tag_u8": 0x17},
    ]
    assert contract["vectors"]["rows"] == 56
    assert contract["vectors"]["valid_row_count"] == 14
    assert len(vectors) == 56
    assert false_codecs.isdisjoint({str(row["id"]) for row in semantic_rows["row_codecs"]})
    assert false_families.isdisjoint(
        {str(row["family"]) for row in semantic_rows["producer_inventory"]}
    )
    assert "babylon_state.subsystem_value_v1" not in {
        str(row["relation"]) for row in contract["storage"]["normalized_child_relations"]
    }
    assert {
        "babylon_state.tick_subsystem_row",
        "babylon_state.tick_conservation_row",
        "babylon_state.tick_boundary_flow_row",
    } <= set(contract["storage"]["prohibited_final_relations"])

    valid_empty = [row for row in vectors if row["kind"] == "valid_empty_family"]
    assert len(valid_empty) == 1
    assert valid_empty[0]["data"]["family"] == "event"
    assert valid_empty[0]["data"]["producer"] == "successful_event_batch_v1"
    assert false_codecs.isdisjoint({str(row.get("codec", "")) for row in vectors})


def test_verifier_refuses_a_mutated_synthetic_tick_zero_contract() -> None:
    contract = deepcopy(_contract())
    contract["foundation"]["tick_commit_starts_at"] = 0

    with pytest.raises(RustPersistenceCutoverRefusal) as exc_info:
        validate_cutover_contract(contract)

    assert exc_info.value.code == "synthetic_tick_zero"


@pytest.mark.parametrize(
    ("section", "field", "weakened"),
    [
        ("schema_epochs", "reader_epoch", 999),
        ("foundation", "exact_fields", []),
        ("semantic_rows", "family_order", []),
        ("storage", "prohibited_final_relations", []),
        ("storage", "prohibited_final_columns", []),
        ("python_authority", "must_delete", []),
    ],
)
def test_verifier_refuses_weakened_critical_sections(
    section: str, field: str, weakened: object
) -> None:
    contract = deepcopy(_contract())
    contract[section][field] = weakened

    with pytest.raises(RustPersistenceCutoverRefusal):
        validate_cutover_contract(contract)


def test_verifier_refuses_a_dangling_row_codec() -> None:
    contract = deepcopy(_contract())
    contract["semantic_rows"]["producer_inventory"][0]["row_codecs"] = ["missing_v1"]

    with pytest.raises(RustPersistenceCutoverRefusal) as exc_info:
        validate_cutover_contract(contract)

    assert exc_info.value.code == "dangling_row_codec"


@pytest.mark.parametrize(
    ("section", "path", "weakened"),
    [
        ("schema_epochs", ("activation_ledger", "columns"), []),
        ("foundation", ("content_bundle", "fields"), []),
        ("semantic_rows", ("row_wire", "key_domain_ascii_nul"), "weakened"),
        (
            "semantic_rows",
            ("scalar_codecs", "f64_be_canonical", "normalization"),
            "preserve_negative_zero",
        ),
        ("semantic_rows", ("row_codecs", 0, "typed_relation"), ""),
        ("semantic_rows", ("producer_inventory", 0, "source_accessor"), ""),
        ("semantic_rows", ("emptiness_law", "valid_empty"), ""),
        ("storage", ("metadata_disposition", "relations", 0, "action"), "drop"),
        ("reader_boundary", ("epoch7_edges",), 0),
        ("reader_boundary", ("views",), 1),
        (
            "data_disposition",
            ("python_written_relation_disposition", "typed_tick_replacement"),
            [],
        ),
        (
            "python_authority",
            ("must_replace_entrypoints_without_python_adapter", 0, "required_rust_command"),
            "",
        ),
    ],
)
def test_verifier_refuses_exact_section_weakening(
    section: str, path: tuple[str | int, ...], weakened: object
) -> None:
    contract = deepcopy(_contract())
    cursor: Any = contract[section]
    for component in path[:-1]:
        cursor = cursor[component]
    cursor[path[-1]] = weakened

    with pytest.raises(RustPersistenceCutoverRefusal):
        validate_cutover_contract(contract)


def test_verifier_refuses_weakened_proofs_and_non_goals() -> None:
    for field in ["proofs", "non_goals"]:
        contract = deepcopy(_contract())
        contract[field] = []

        with pytest.raises(RustPersistenceCutoverRefusal):
            validate_cutover_contract(contract)


def test_verifier_refuses_changed_declared_vector_digest() -> None:
    contract = deepcopy(_contract())
    contract["vectors"]["sha256"] = "0" * 64

    with pytest.raises(RustPersistenceCutoverRefusal) as exc_info:
        validate_cutover_contract(contract)

    assert exc_info.value.code == "invalid_vectors"


def test_checked_in_cutover_vectors_match_the_declared_digest() -> None:
    raw = CUTOVER_VECTORS.read_bytes()

    assert len(raw) == 26_432
    assert hashlib.sha256(raw).hexdigest() == _contract()["vectors"]["sha256"]


def test_checked_in_repository_has_no_cutover_findings() -> None:
    assert verify_cutover_contract(_contract(), ROOT) == []


def test_verifier_refuses_a_renamed_game_writer_capability(tmp_path: Path) -> None:
    relative = "src/babylon/persistence/postgres_runtime/_spec_062.py"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text(
        """import os
import psycopg

def renamed_writer() -> None:
    renamed_target = os.environ["BABYLON_DSN"]
    conn = psycopg.connect(renamed_target)
    conn.execute("INSERT INTO babylon_state.tick_commit (campaign_id) VALUES ('x')")
""",
        encoding="utf-8",
    )
    findings = verify_cutover_contract(_contract(), tmp_path)

    assert any(
        finding.code == "python_write_capability_survivor" and finding.path == relative
        for finding in findings
    )


def test_verifier_closes_split_connection_and_dynamic_write_helpers(tmp_path: Path) -> None:
    helper = tmp_path / "src/babylon/connection_helper.py"
    helper.parent.mkdir(parents=True)
    helper.write_text(
        """import os
import psycopg

def renamed_connection():
    alias = os.environ["BABYLON_DSN"]
    return psycopg.connect(alias)
""",
        encoding="utf-8",
    )
    writer = tmp_path / "src/babylon/dynamic_writer.py"
    writer.write_text(
        """from psycopg import sql
from babylon.connection_helper import renamed_connection

def renamed_dynamic_writer(table: str) -> None:
    conn = renamed_connection()
    statement = sql.SQL("INSERT INTO {} (campaign_id) VALUES ('x')").format(
        sql.Identifier(table)
    )
    conn.execute(statement)
""",
        encoding="utf-8",
    )

    findings = verify_cutover_contract(_contract(), tmp_path)
    paths = {
        finding.path for finding in findings if finding.code == "uncensused_python_write_authority"
    }

    assert {
        "src/babylon/connection_helper.py",
        "src/babylon/dynamic_writer.py",
    } <= paths


def test_verifier_refuses_an_uncensused_game_writer_capability(tmp_path: Path) -> None:
    relative = "src/babylon/new_game_writer.py"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text(
        """def renamed_writer(conn: object) -> None:
    conn.execute("DELETE FROM babylon_meta.campaign WHERE campaign_id = 'x'")
""",
        encoding="utf-8",
    )

    findings = verify_cutover_contract(_contract(), tmp_path)

    assert any(
        finding.code == "uncensused_python_write_authority" and finding.path == relative
        for finding in findings
    )


def test_verifier_enforces_required_rust_command_in_the_exact_mise_task(
    tmp_path: Path,
) -> None:
    mise = tmp_path / ".mise.toml"
    mise.write_text(
        '[tasks.setup]\nrun = "python legacy_setup.py" # babylon-runtime bootstrap\n',
        encoding="utf-8",
    )

    findings = verify_cutover_contract(_contract(), tmp_path)

    assert any(
        finding.code == "missing_rust_entrypoint"
        and finding.path == ".mise.toml"
        and finding.detail.startswith("setup:")
        for finding in findings
    )

    mise.write_text(
        '[tasks.setup]\ndescription = "babylon-runtime bootstrap"\n'
        'run = "python legacy_setup.py"\n',
        encoding="utf-8",
    )
    findings = verify_cutover_contract(_contract(), tmp_path)
    assert any(
        finding.code == "missing_rust_entrypoint"
        and finding.path == ".mise.toml"
        and finding.detail.startswith("setup:")
        for finding in findings
    )

    mise.write_text('[tasks.setup]\nrun = "babylon-runtime bootstrap"\n', encoding="utf-8")
    findings = verify_cutover_contract(_contract(), tmp_path)
    assert not any(
        finding.code == "missing_rust_entrypoint"
        and finding.path == ".mise.toml"
        and finding.detail.startswith("setup:")
        for finding in findings
    )


def test_entrypoint_source_selects_one_standalone_mise_task() -> None:
    source = """["sim:e2e-michigan"]
description = "Run the governed Michigan smoke path"
run = "babylon-runtime michigan-smoke"

["sim:probe"]
description = "Probe the governed runtime"
run = "babylon-runtime probe"
"""

    selected = _entrypoint_source(".mise/tasks/simulation.toml", source, "sim:e2e-michigan")

    assert 'run = "babylon-runtime michigan-smoke"' in selected
    assert "sim:probe" not in selected
    assert _entrypoint_executes_required_command(
        ".mise/tasks/simulation.toml",
        selected,
        "babylon-runtime michigan-smoke",
    )
    assert not _entrypoint_executes_required_command(
        ".mise/tasks/simulation.toml",
        selected,
        "babylon-runtime probe",
    )


def test_verifier_refuses_a_retired_python_adapter_even_when_it_executes_rust(
    tmp_path: Path,
) -> None:
    shared = tmp_path / "tools/shared.py"
    shared.parent.mkdir(parents=True)
    shared.write_text(
        '''def run_simulation() -> None:
    """babylon-runtime"""
''',
        encoding="utf-8",
    )

    findings = verify_cutover_contract(_contract(), tmp_path)
    assert any(
        finding.code == "retired_entrypoint_survivor"
        and finding.path == "tools/shared.py"
        and finding.detail == "run_simulation"
        for finding in findings
    )

    shared.write_text(
        """import subprocess

def run_simulation() -> None:
    subprocess.run(["babylon-runtime"], check=True)
""",
        encoding="utf-8",
    )
    findings = verify_cutover_contract(_contract(), tmp_path)
    assert any(
        finding.code == "retired_entrypoint_survivor"
        and finding.path == "tools/shared.py"
        and finding.detail == "run_simulation"
        for finding in findings
    )


def test_verifier_refuses_a_split_stopped_train(tmp_path: Path) -> None:
    findings = verify_cutover_contract(_contract(), tmp_path)
    codes = {finding.code for finding in findings}

    assert "missing_reader_contract" in codes
    assert "missing_cutover_vectors" in codes


def test_verifier_refuses_changed_vector_bytes(tmp_path: Path) -> None:
    contract = _contract()
    path = tmp_path / contract["vectors"]["path"]
    path.parent.mkdir(parents=True)
    path.write_text('{"kind":"weakened"}\n', encoding="utf-8")

    findings = verify_cutover_contract(contract, tmp_path)

    assert "cutover_vector_digest" in {finding.code for finding in findings}


@pytest.mark.parametrize(
    ("cutover_id", "tick_id", "tag", "expected_input"),
    [
        (
            "bsl-stable-node",
            "bsl-value-node-ref",
            "07",
            {
                "tag": "stable_node_key",
                "scenario": "demo/cross-allocation",
                "local_name": "workers",
            },
        ),
        (
            "bsl-stable-hyperedge",
            "bsl-value-hyperedge-ref",
            "08",
            {
                "tag": "stable_hyperedge_key",
                "scenario": "demo/cross-allocation",
                "local_name": "coalition-one",
            },
        ),
        (
            "bsl-stable-edge",
            "bsl-value-edge-ref",
            "09",
            {
                "tag": "stable_edge_key",
                "scenario": "demo/cross-allocation",
                "edge_type": "OWNS",
                "source_local_name": "capital",
                "target_local_name": "workers",
            },
        ),
    ],
)
def test_stable_reference_vectors_reuse_tick_content_identity(
    cutover_id: str,
    tick_id: str,
    tag: str,
    expected_input: dict[str, str],
) -> None:
    cutover = _vector_rows(CUTOVER_VECTORS)[cutover_id]
    tick = _vector_rows(TICK_CONTENT_VECTORS)[tick_id]

    assert cutover["input"] == expected_input
    assert tick["data"]["canonical_hex"].startswith(tag)
    assert cutover["expected_hex"] == tick["data"]["canonical_hex"]


def test_verifier_refuses_cross_scenario_stable_reference_collision(
    tmp_path: Path,
) -> None:
    contract = deepcopy(_contract())
    rows = list(_vector_rows(CUTOVER_VECTORS).values())
    node = next(row for row in rows if row["id"] == "bsl-stable-node")
    node["input"]["scenario"] = "demo/other-scenario"
    payload = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows
    ).encode("utf-8")
    destination = tmp_path / contract["vectors"]["path"]
    destination.parent.mkdir(parents=True)
    destination.write_bytes(payload)
    contract["vectors"]["sha256"] = hashlib.sha256(payload).hexdigest()

    findings: set[CutoverFinding] = set()
    _verify_vectors(contract, tmp_path, findings)

    assert "cutover_stable_bsl_identity" in {finding.code for finding in findings}


@pytest.mark.parametrize(
    "row_id",
    [
        row_id
        for row_id, row in _vector_rows(CUTOVER_VECTORS).items()
        if row["kind"] == "valid_scalar"
    ],
)
def test_verifier_recomputes_every_valid_scalar_layout(tmp_path: Path, row_id: str) -> None:
    contract = deepcopy(_contract())
    rows = list(_vector_rows(CUTOVER_VECTORS).values())
    scalar = next(row for row in rows if row["id"] == row_id)
    expected_hex = str(scalar["expected_hex"])
    replacement = "00" if expected_hex[-2:] != "00" else "01"
    scalar["expected_hex"] = expected_hex[:-2] + replacement
    payload = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows
    ).encode("utf-8")
    destination = tmp_path / contract["vectors"]["path"]
    destination.parent.mkdir(parents=True)
    destination.write_bytes(payload)
    contract["vectors"]["sha256"] = hashlib.sha256(payload).hexdigest()
    findings: set[CutoverFinding] = set()

    _verify_vectors(contract, tmp_path, findings)

    assert "cutover_valid_scalar_identity" in {finding.code for finding in findings}


@pytest.mark.parametrize(
    "case",
    [
        "invalid_h3",
        "invalid_enum",
        "invalid_stable_key",
        "off_grid_ratio",
        "nul_optional_utf8",
        "extra_nested_key",
    ],
)
def test_verifier_refuses_digest_adjusted_invalid_scalar_semantics(
    tmp_path: Path, case: str
) -> None:
    contract = deepcopy(_contract())
    rows = list(_vector_rows(CUTOVER_VECTORS).values())
    if case == "invalid_h3":
        row = next(row for row in rows if row["id"] == "scalar-h3-r9-cell")
        row["input"] = "1"
        row["expected_hex"] = (1).to_bytes(8, "big", signed=True).hex()
    elif case == "invalid_enum":
        row = next(row for row in rows if row["id"] == "bsl-enum")
        row["input"]["enum_type"] = "mode"
        row["expected_hex"] = (
            b"\x06"
            + len(b"mode").to_bytes(4, "big")
            + b"mode"
            + len(b"ON").to_bytes(4, "big")
            + b"ON"
        ).hex()
    elif case == "invalid_stable_key":
        row = next(row for row in rows if row["id"] == "bsl-stable-node")
        row["input"]["scenario"] = "Demo/cross-allocation"
        encoded = bytes.fromhex(str(row["expected_hex"]))
        row["expected_hex"] = encoded.replace(
            b"demo/cross-allocation", b"Demo/cross-allocation"
        ).hex()
    elif case == "off_grid_ratio":
        row = next(row for row in rows if row["id"] == "bsl-ratio-unbounded")
        row["input"]["value"] = "1.5000004"
        row["expected_hex"] = (b"\x04" + struct.pack(">d", 1.5000004) + b"\0\0").hex()
    elif case == "nul_optional_utf8":
        row = next(row for row in rows if row["id"] == "scalar-optional-some")
        row["input"] = "M\0"
        row["expected_hex"] = (b"\x01\0\0\0\x02M\0").hex()
    else:
        row = next(row for row in rows if row["id"] == "bsl-int")
        row["input"]["ignored"] = "forbidden"
    payload = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows
    ).encode("utf-8")
    destination = tmp_path / contract["vectors"]["path"]
    destination.parent.mkdir(parents=True)
    destination.write_bytes(payload)
    contract["vectors"]["sha256"] = hashlib.sha256(payload).hexdigest()
    findings: set[CutoverFinding] = set()

    _verify_vectors(contract, tmp_path, findings)

    assert "cutover_valid_scalar_identity" in {finding.code for finding in findings}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("operation", "invented_operation"),
        ("expected_code", "invented_error"),
        ("expected_code", None),
    ],
)
def test_vector_refusal_vocabulary_and_shape_are_closed(
    tmp_path: Path, field: str, value: object
) -> None:
    contract = deepcopy(_contract())
    source = ROOT / contract["vectors"]["path"]
    rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
    refusal = next(row for row in rows if row["kind"] == "refusal")
    if value is None:
        refusal.pop(field)
    else:
        refusal[field] = value
    payload = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows
    ).encode("utf-8")
    destination = tmp_path / contract["vectors"]["path"]
    destination.parent.mkdir(parents=True)
    destination.write_bytes(payload)
    contract["vectors"]["sha256"] = hashlib.sha256(payload).hexdigest()
    findings: set[CutoverFinding] = set()

    _verify_vectors(contract, tmp_path, findings)

    codes = {finding.code for finding in findings}
    assert {"cutover_vector_refusal_vocabulary", "cutover_vector_shape"} & codes
