"""Independent storage budget, acknowledgment and restart evidence controls."""

import hashlib
from copy import deepcopy
from pathlib import Path

import pytest
from tools.devtools.national_storage_qualification import (
    PackageClaim,
    Policy,
    Snapshot,
    evaluate,
    package_claim_from_headers,
)


def policy():
    return Policy.model_validate_json(
        (
            Path(__file__).resolve().parents[3] / "contracts/national_storage_qualification_v3.json"
        ).read_bytes()
    )


def snapshot(tick=0, size=100, relation=100, opening=True):
    h = "ab" * 32
    return {
        "stage": f"tick-{tick}",
        "database": "game",
        "campaign": "campaign",
        "server": "17.11",
        "database_bytes": size,
        "relations_columns": [
            "schema",
            "relation",
            "base_heap_all_forks_bytes",
            "base_index_bytes",
            "toast_heap_and_index_bytes",
            "total_bytes",
            "estimated_rows",
        ],
        "relations": [["babylon_state", "history", relation, 0, 0, relation, 1]],
        "acknowledged_markers": {
            n: {"count": tick, "maximum_resolve_tick": tick}
            for n in ["tick_commit", "material_tick_v3"]
        },
        "wal_lsn_container_wide": f"0/{tick + 100:X}",
        "bytea_columns_count_canonical_octets_column_storage_compression": {
            "history.bytes": [tick, tick * 32, tick * 20, ["pglz"]],
            **{
                "material_tick_v3." + name: [
                    tick,
                    tick
                    * {
                        "identity_bytes": 32,
                        "register_storage_bytes": 200,
                        "receipt_storage_bytes": 2300,
                        "lookup_delta_bytes": 190,
                    }[name],
                    tick * 20,
                    ["pglz"],
                ]
                for name in (
                    "identity_bytes",
                    "register_storage_bytes",
                    "receipt_storage_bytes",
                    "lookup_delta_bytes",
                )
            },
        },
        "county_geoids": [f"{i:05}" for i in range(3144)] if opening else [],
        "marker_and_encoded_package_hashes": [[i, h, h, h, h] for i in range(1, tick + 1)],
        "lookup_delta_hashes": [[i, h] for i in range(1, tick + 1)],
        "index_diagnostics_not_additional_totals": [],
        "actual_rust_storage_package_claims": [
            {
                "storage_layout": "period_local_lookup_v3",
                "state_storage_version": 4,
                "tick": i,
                "register_storage_bytes": 200,
                "receipt_storage_bytes": 2300,
                "lookup_delta_bytes": 190,
                "total_storage_package_bytes": 2690,
                "canonical_register_bytes": 10000,
                "canonical_register_sha256": h,
                "canonical_receipt_bytes": 10000,
                "canonical_receipt_sha256": h,
                "receipt_period": i,
                "opening_register_sha256": h,
                "opening_lookup_entries": 100,
                "previous_lookup_chain_sha256": h,
                "lookup_chain_sha256": h,
                "state_lookup_entries": 101,
                "complete_lookup_entries": 102,
                "period_lookup_entries": 2,
                "lookup_packed_bytes": 70,
                "lookup_descriptor_bytes": 20,
                "lookup_descriptor_sha256": h,
                "state_period_lookup_entries": 1,
                "receipt_period_lookup_entries": 1,
                "claim_qualification": "Header claims authenticated by actual Rust cold-open; Python does not replace codec/canonical validation.",
            }
            for i in range(1, tick + 1)
        ],
    }


def run(ticks, reopens=None):
    return evaluate(
        policy(),
        Snapshot.model_validate(snapshot(opening=False)),
        Snapshot.model_validate(snapshot()),
        tuple(Snapshot.model_validate(s) for s in ticks),
        tuple(Snapshot.model_validate(s) for s in (ticks if reopens is None else reopens)),
    )


def test_short_run_is_incomplete_and_annualizes_exactly():
    r = run([snapshot(1, 101, 101)])
    assert r["status"] == "incomplete"
    assert r["annualized_growth_bytes"] == {"numerator": 13, "denominator": 1}
    assert r["twelve_tick_comparison_bytes"] == {"numerator": 12, "denominator": 1}


def test_positive_relation_growth_cannot_be_hidden_by_database_shrink():
    r = run([snapshot(1, 90, 40_000_101)])
    assert r["ticks"][0]["database_delta_bytes"] == -10
    assert r["ticks"][0]["charged_growth_bytes"] == 40_000_001
    assert r["status"] == "failed"


def test_positive_unattributed_growth_cannot_hide_behind_known_relation_shrink():
    item = snapshot(1, 40_000_051, 0)
    item["relations"].append(["babylon_meta", "new_history", 40_000_000, 0, 0, 40_000_000, 1])
    result = run([item])
    period = result["ticks"][0]
    assert period["charged_growth_bytes"] == 40_000_051
    assert period["unattributed_database_growth_bytes"] == 51
    assert not period["budget_passed"]
    assert result["status"] == "failed"


def test_recovery_allocation_cannot_hide_behind_committed_relation_shrink():
    committed = snapshot(1, 110, 110)
    reopened = snapshot(1, 110, 100)
    reopened["relations"].append(["babylon_meta", "recovery_history", 10, 0, 0, 10, 1])
    result = run([committed], [reopened])
    period = result["ticks"][0]
    assert period["charged_growth_bytes"] == 20
    assert period["restart_growth"]["database_delta_bytes"] == 0
    assert period["restart_growth"]["charged_growth_bytes"] == 10


@pytest.mark.parametrize("version", [1, 2, 4])
def test_unsupported_storage_policy_versions_refuse(version):
    data = policy().model_dump()
    data["version"] = version
    with pytest.raises(ValueError):
        Policy.model_validate(data)


def test_storage_charge_method_cannot_change_with_an_unversioned_override():
    data = policy().model_dump()
    data["storage_charge_method"] = "maximum_net_or_parent_growth"
    with pytest.raises(ValueError):
        Policy.model_validate(data)


@pytest.mark.parametrize("growth,passed", [(40_000_000, True), (40_000_001, False)])
def test_canonical_development_budget_boundary(growth, passed):
    result = run([snapshot(1, 100 + growth, 100 + growth)])
    assert policy().maximum_tick_growth_bytes == 40_000_000
    assert result["ticks"][0]["budget_passed"] is passed
    assert result["status"] == ("incomplete" if passed else "failed")


def test_toast_is_in_parent_total_and_not_counted_twice():
    s = snapshot(1, 110, 110)
    s["relations"][0][2:6] = [80, 10, 20, 110]
    assert run([s])["ticks"][0]["charged_growth_bytes"] == 10


@pytest.mark.parametrize("mutation", ["gap", "marker", "roster", "hash", "bytea", "identity"])
def test_refuses_untrusted_or_changed_restart_evidence(mutation):
    a = snapshot(1, 101, 101)
    b = deepcopy(a)
    if mutation == "gap":
        a = snapshot(2, 101, 101)
        b = deepcopy(a)
    elif mutation == "marker":
        a["acknowledged_markers"]["tick_commit"]["count"] = 0
    elif mutation == "roster":
        b["county_geoids"][0] = "99999"
    elif mutation == "hash":
        b["marker_and_encoded_package_hashes"][0][1] = "cd" * 32
    elif mutation == "bytea":
        b["bytea_columns_count_canonical_octets_column_storage_compression"]["history.bytes"][
            1
        ] += 1
    else:
        b["database"] = "other"
    with pytest.raises(ValueError):
        run([a], [b])


def test_fifty_two_committed_reopened_ticks_qualify_and_duplicate_refuses():
    ticks = [snapshot(i, 100 + i, 100 + i) for i in range(1, 53)]
    assert run(ticks)["status"] == "qualified"
    with pytest.raises(ValueError):
        run([ticks[0], ticks[0]])


def test_missing_restart_is_incomplete_and_models_are_frozen():
    assert run([snapshot(1)], [])["status"] == "incomplete"
    with pytest.raises(ValueError):
        policy().county_count = 1


def test_fractional_annualization_does_not_round_or_use_twelve_ticks():
    r = run([snapshot(1, 101, 101), snapshot(2, 103, 103)])
    assert r["annualized_growth_bytes"] == {"numerator": 39, "denominator": 2}
    assert r["twelve_tick_comparison_bytes"] == {"numerator": 18, "denominator": 1}


def test_actual_rolling_year_growth_is_separate_from_short_run_projection():
    ticks = [snapshot(i, 100 + i * (i + 1) // 2, 100 + i * (i + 1) // 2) for i in range(1, 15)]
    assert run(ticks[:12])["rolling_model_year_growth"] == []
    result = run(ticks)
    assert result["rolling_model_year_growth"] == [
        {"first_tick": 1, "last_tick": 13, "charged_growth_bytes": 91},
        {"first_tick": 2, "last_tick": 14, "charged_growth_bytes": 104},
    ]
    assert result["annualized_growth_bytes"] == {"numerator": 195, "denominator": 2}


def test_cli_measurement_reports_failure_and_qualification_returns_nonzero(
    tmp_path, monkeypatch, capsys
):
    import json
    import sys

    from tools.devtools.national_storage_qualification import main

    data = {
        "policy": policy().model_dump(),
        "baseline": snapshot(opening=False),
        "opening": snapshot(),
        "tick": snapshot(1, 40_000_101, 40_000_101),
        "reopen": snapshot(1, 40_000_101, 40_000_101),
    }
    for name, value in data.items():
        (tmp_path / name).write_text(json.dumps(value))
    args = [
        "measure",
        "--policy",
        str(tmp_path / "policy"),
        "--baseline",
        str(tmp_path / "baseline"),
        "--opening",
        str(tmp_path / "opening"),
        "--ticks",
        str(tmp_path / "tick"),
        "--reopens",
        str(tmp_path / "reopen"),
    ]
    monkeypatch.setattr(sys, "argv", args)
    assert main() == 0
    assert json.loads(capsys.readouterr().out)["status"] == "failed"
    monkeypatch.setattr(sys, "argv", [*args, "--qualify"])
    assert main() == 1


def test_missing_physical_bytes_and_policy_extra_refuse():
    p = policy().model_dump()
    p["unreviewed_budget"] = 1
    with pytest.raises(ValueError):
        Policy.model_validate(p)
    s = snapshot()
    s["relations"][0][5] = -1
    with pytest.raises(ValueError):
        Snapshot.model_validate(s)


def test_restart_storage_growth_is_charged_to_its_committed_tick():
    a = snapshot(1, 101, 101)
    b = snapshot(1, 40_000_101, 40_000_101)
    result = run([a], [b])
    assert result["ticks"][0]["charged_growth_bytes"] == 40_000_001
    assert result["status"] == "failed"


@pytest.mark.parametrize("value", [True, 1.0, "1"])
def test_policy_version_does_not_coerce_json_scalar_types(value):
    data = policy().model_dump()
    data["version"] = value
    with pytest.raises(ValueError):
        Policy.model_validate(data)


def test_unmarked_material_byte_rows_refuse():
    data = snapshot()
    data["bytea_columns_count_canonical_octets_column_storage_compression"][
        "material_tick_v3.register_storage_bytes"
    ][0] = 1
    with pytest.raises(ValueError, match="acknowledged markers"):
        Snapshot.model_validate(data)


def test_new_tick_cannot_rewrite_prior_reopened_authoritative_history():
    first = snapshot(1, 101, 101)
    second = snapshot(2, 102, 102)
    second["marker_and_encoded_package_hashes"][0][1] = "cd" * 32
    with pytest.raises(ValueError, match="previous authoritative tick hashes changed"):
        run([first, second], [first, deepcopy(second)])


def test_missing_lookup_digest_is_an_explicit_qualification_gap():
    ticks = [snapshot(i, 100 + i, 100 + i) for i in range(1, 53)]
    for item in ticks:
        del item["lookup_delta_hashes"]
    result = run(ticks)
    assert result["status"] == "incomplete"
    assert not result["lookup_delta_hashes_verified"]
    assert result["authentication_gaps"] == [
        "lookup_delta_bytes SHA-256 absent from recorder evidence"
    ]


def test_new_tick_cannot_drop_recorded_lookup_history():
    first = snapshot(1, 101, 101)
    second = snapshot(2, 102, 102)
    del second["lookup_delta_hashes"]
    with pytest.raises(ValueError, match="previous encoded package or lookup history changed"):
        run([first, second])


@pytest.mark.parametrize(
    "field,value",
    [
        ("tick", True),
        ("state_storage_version", 3),
        ("state_storage_version", 4.0),
        ("state_storage_version", "4"),
        ("state_storage_version", None),
        ("canonical_register_bytes", 1.5),
        ("complete_lookup_entries", 2**32),
        ("lookup_packed_bytes", 71),
        ("receipt_period", 2),
        ("total_storage_package_bytes", 1),
        ("register_storage_bytes", 1),
        ("canonical_receipt_sha256", "AA" * 32),
    ],
)
def test_package_claims_refuse_coercion_bounds_and_inconsistent_headers(field, value):
    item = snapshot(1)
    item["actual_rust_storage_package_claims"][0][field] = value
    with pytest.raises(ValueError):
        Snapshot.model_validate(item)


@pytest.mark.parametrize("evidence", ["encoded", "canonical", "lookup"])
def test_restart_authenticates_every_storage_and_canonical_history(evidence):
    original = snapshot(1)
    changed = deepcopy(original)
    if evidence == "encoded":
        changed["marker_and_encoded_package_hashes"][0][3] = "cd" * 32
    elif evidence == "canonical":
        changed["actual_rust_storage_package_claims"][0]["canonical_register_sha256"] = "cd" * 32
    else:
        changed["lookup_delta_hashes"][0][1] = "cd" * 32
    with pytest.raises(ValueError, match="restart changed"):
        run([original], [changed])


def test_encoded_history_cannot_change_while_canonical_hashes_remain_equal():
    first, second = snapshot(1), snapshot(2)
    second["marker_and_encoded_package_hashes"][0][3] = "cd" * 32
    with pytest.raises(ValueError, match="previous encoded package"):
        run([first, second])


def test_claim_lengths_must_equal_wire_column_totals():
    item = snapshot(1)
    item["bytea_columns_count_canonical_octets_column_storage_compression"][
        "material_tick_v3.lookup_delta_bytes"
    ][1] += 1
    with pytest.raises(ValueError, match="wire package lengths"):
        Snapshot.model_validate(item)


def test_old_raw_snapshot_and_unreviewed_claim_fields_refuse():
    item = snapshot(1)
    item["authoritative_hashes"] = item["marker_and_encoded_package_hashes"]
    with pytest.raises(ValueError):
        Snapshot.model_validate(item)
    del item["authoritative_hashes"]
    item["actual_rust_storage_package_claims"][0]["unreviewed"] = 1
    with pytest.raises(ValueError):
        Snapshot.model_validate(item)


def test_index_diagnostics_are_validated_but_never_added_to_parent_growth():
    item = snapshot(1, 110, 110)
    item["relations"][0][2:6] = [80, 10, 20, 110]
    item["index_diagnostics_not_additional_totals"] = [
        ["babylon_state", "history", "history_idx", 10]
    ]
    assert run([item])["ticks"][0]["charged_growth_bytes"] == 10
    item["index_diagnostics_not_additional_totals"][0][3] = 11
    with pytest.raises(ValueError, match="index diagnostics exceed"):
        Snapshot.model_validate(item)


def current_headers():
    opening, canonical, previous, packed_hash = [bytes([i]) * 32 for i in range(1, 5)]
    tick = (1).to_bytes(8, "big")
    chain = hashlib.sha256(
        b"BabylonPeriodLookupChainV1\0" + opening + tick + previous + packed_hash
    ).digest()
    state = (
        b"babylon.state-storage.v4\0"
        + opening
        + canonical
        + chain
        + (10000).to_bytes(8, "big")
        + (101).to_bytes(4, "big")
        + bytes(32)
        + (70).to_bytes(2, "big")
    )
    receipt = (
        b"BabylonReceiptStorageV2\0"
        + (10000).to_bytes(8, "big")
        + canonical
        + tick
        + (102).to_bytes(8, "big")
        + bytes(32)
    )
    lookup = (
        b"BabylonPeriodLookupV3\0"
        + (3).to_bytes(2, "big")
        + opening
        + tick
        + previous
        + (70).to_bytes(8, "big")
        + packed_hash
        + (20).to_bytes(8, "big")
        + bytes([5]) * 32
        + (7).to_bytes(8, "big")
    )
    return state, receipt, lookup


def test_collector_current_headers_bind_opening_period_chain_and_local_prefix():
    state, receipt, lookup = current_headers()
    claim = package_claim_from_headers(1, state, receipt, lookup, 200, 2300, len(lookup) + 7)
    assert claim.storage_layout == "period_local_lookup_v3"
    assert claim.state_storage_version == 4
    assert claim.lookup_descriptor_bytes == 20
    assert claim.lookup_descriptor_sha256 == "05" * 32
    assert claim.opening_lookup_entries == 100
    assert claim.state_period_lookup_entries == claim.receipt_period_lookup_entries == 1
    assert claim.canonical_register_bytes == claim.canonical_receipt_bytes == 10000


@pytest.mark.parametrize("fault", ["old", "truncated", "opening", "tick", "chain", "length"])
def test_collector_refuses_unsupported_or_inconsistent_header_claims(fault):
    state, receipt, lookup = current_headers()
    if fault == "old":
        state = state.replace(b"state-storage.v4", b"state-storage.v3")
    elif fault == "truncated":
        state = state[:-1]
    elif fault == "opening":
        offset = len(b"BabylonPeriodLookupV3\0") + 2
        lookup = lookup[:offset] + bytes([lookup[offset] ^ 1]) + lookup[offset + 1 :]
    elif fault == "tick":
        offset = len(b"BabylonPeriodLookupV3\0") + 34
        lookup = lookup[:offset] + (2).to_bytes(8, "big") + lookup[offset + 8 :]
    elif fault == "chain":
        offset = len(b"babylon.state-storage.v4\0") + 64
        state = state[:offset] + bytes([state[offset] ^ 1]) + state[offset + 1 :]
    else:
        lookup = lookup[:-8] + (8).to_bytes(8, "big")
    with pytest.raises(ValueError):
        package_claim_from_headers(1, state, receipt, lookup, 200, 2300, len(lookup) + 7)


@pytest.mark.parametrize(
    "field,value",
    [
        ("opening_register_sha256", "cd" * 32),
        ("previous_lookup_chain_sha256", "cd" * 32),
    ],
)
def test_independent_period_tables_preserve_opening_and_chain_authority(field, value):
    item = snapshot(2)
    item["actual_rust_storage_package_claims"][1][field] = value
    with pytest.raises(ValueError):
        Snapshot.model_validate(item)


def test_period_lookup_size_can_shrink_without_losing_the_opening_seed():
    item = snapshot(2)
    later = item["actual_rust_storage_package_claims"][1]
    later.update(
        state_lookup_entries=100,
        complete_lookup_entries=101,
        period_lookup_entries=1,
        lookup_packed_bytes=37,
        state_period_lookup_entries=0,
        receipt_period_lookup_entries=1,
    )
    Snapshot.model_validate(item)


@pytest.mark.parametrize(
    "fault",
    [
        "v2",
        "version",
        "descriptor_short",
        "descriptor_long",
        "count",
        "stored_size",
        "stored_bound",
    ],
)
def test_collector_v3_refuses_old_wrapper_and_malformed_descriptor_claims(fault):
    state, receipt, lookup = current_headers()
    size = len(lookup) + 7
    domain = len(b"BabylonPeriodLookupV3\0")
    if fault == "v2":
        lookup = lookup.replace(b"BabylonPeriodLookupV3", b"BabylonPeriodLookupV2")
    elif fault == "version":
        lookup = lookup[:domain] + (2).to_bytes(2, "big") + lookup[domain + 2 :]
    elif fault in ("descriptor_short", "descriptor_long"):
        length = 13 if fault == "descriptor_short" else 71
        offset = domain + 114
        lookup = lookup[:offset] + length.to_bytes(8, "big") + lookup[offset + 8 :]
    elif fault == "count":
        offset = domain + 74
        lookup = lookup[:offset] + (136).to_bytes(8, "big") + lookup[offset + 8 :]
    elif fault == "stored_size":
        size += 1
    else:
        size = 1_000_000_000 + 1_000_000_000 // 256 + 1025
    with pytest.raises(ValueError):
        package_claim_from_headers(1, state, receipt, lookup, 200, 2300, size)


@pytest.mark.parametrize(
    "field,maximum",
    [
        ("canonical_receipt_bytes", 872_612_528),
        ("receipt_storage_bytes", 872_614_764),
    ],
)
def test_current_receipt_cap_boundary(field, maximum):
    item = snapshot(1)
    claim = item["actual_rust_storage_package_claims"][0]
    claim[field] = maximum
    if field == "receipt_storage_bytes":
        claim["total_storage_package_bytes"] = maximum + 200 + 190
    PackageClaim.model_validate(claim)
    claim[field] += 1
    if field == "receipt_storage_bytes":
        claim["total_storage_package_bytes"] += 1
    with pytest.raises(ValueError, match="length exceeds"):
        PackageClaim.model_validate(claim)


def test_collector_current_receipt_requires_complete_36_family_framing():
    state, receipt, lookup = current_headers()
    # Current V17 has36 mandatory59B storage family frames, including empty rows.
    minimum = len(b"BabylonReceiptStorageV2\0") + 88 + 36 * 59
    claim = package_claim_from_headers(1, state, receipt, lookup, 200, minimum, len(lookup) + 7)
    assert claim.receipt_storage_bytes == minimum
    with pytest.raises(ValueError, match="shorter than current header framing"):
        package_claim_from_headers(1, state, receipt, lookup, 200, minimum - 1, len(lookup) + 7)


def footprint_run(opening_size, growths, *, restart=True):
    total = opening_size
    ticks = []
    for tick, delta in enumerate(growths, 1):
        total += delta
        ticks.append(Snapshot.model_validate(snapshot(tick, total, total)))
    return evaluate(
        policy(),
        Snapshot.model_validate(snapshot(opening=False)),
        Snapshot.model_validate(snapshot(size=opening_size, relation=opening_size)),
        tuple(ticks),
        tuple(ticks) if restart else (),
    )


def test_large_opening_fails_long_save_without_failing_development_budget():
    result = footprint_run(10_000_000_001, [1])
    assert result["budget_passed"] is True
    assert result["status"] == "incomplete"
    footprint = result["save_footprint"]
    assert footprint["status"] == "failed"
    assert footprint["accumulated_charged_footprint_bytes"] == 10_000_000_002


@pytest.mark.parametrize("extra,passed", [(0, True), (1, False)])
def test_total_save_exact_ceiling_requires_real_horizon_and_restarts(extra, passed):
    result = footprint_run(10_000_000_000 - 325 + extra, [1] * 325)
    footprint = result["save_footprint"]
    assert footprint["budget_passed"] is passed
    assert footprint["status"] == ("qualified" if passed else "failed")
    assert footprint["accumulated_charged_footprint_bytes"] == 10_000_000_000 + extra
    assert result["budget_passed"] is True
    assert result["status"] == "qualified"


def test_short_save_or_missing_restart_cannot_be_qualified_by_projection():
    short = footprint_run(100, [1] * 52)
    assert short["status"] == "qualified"
    assert short["save_footprint"]["status"] == "incomplete"
    assert short["save_footprint"]["projections"][1]["projected_duration_ceiling_passed"] is True
    assert footprint_run(100, [1] * 325, restart=False)["save_footprint"]["status"] == "incomplete"


def test_increasing_average_updates_exact_projection_without_claiming_future_observation():
    first = footprint_run(100, [1])["save_footprint"]
    second_result = footprint_run(100, [1, 2])
    second = second_result["save_footprint"]
    assert first["projections"][1]["projected_total_bytes"] == {"numerator": 425, "denominator": 1}
    assert second["projections"][1]["projected_total_bytes"] == {
        "numerator": 1175,
        "denominator": 2,
    }
    assert [row["ticks"] for row in second["projections"]] == [130, 325, 650]
    assert second["accumulated_charged_footprint_bytes"] == 103
    assert second["observed_ticks"] == 2
    assert second["status"] == "incomplete"
    assert second_result["ticks"][0]["charged_growth_bytes"] == 1
    assert second_result["ticks"][1]["charged_growth_bytes"] == 2


def test_save_charge_keeps_growth_when_database_later_shrinks():
    result = run([snapshot(1, 110, 110), snapshot(2, 100, 110)])
    footprint = result["save_footprint"]
    assert footprint["observed_allocated_database_peak_bytes"] == 110
    assert footprint["cumulative_charged_tick_bytes"] == 10
    assert footprint["accumulated_charged_footprint_bytes"] == 110
    assert result["ticks"][1]["database_delta_bytes"] == -10


@pytest.mark.parametrize(
    "field,value",
    [
        ("maximum_total_save_bytes", 0),
        ("provisional_duration_years", 25.0),
        ("save_qualification_ticks", "325"),
    ],
)
def test_total_save_policy_is_exact_and_provisional(field, value):
    data = policy().model_dump()
    data[field] = value
    with pytest.raises(ValueError):
        Policy.model_validate(data)


@pytest.mark.parametrize("opening_size,ordinary_exit", [(100, 0), (10_000_000_001, 0)])
def test_cli_total_save_failure_and_short_horizon_have_separate_gates(
    tmp_path, monkeypatch, capsys, opening_size, ordinary_exit
):
    import json
    import sys

    from tools.devtools.national_storage_qualification import main

    data = {
        "policy": policy().model_dump(),
        "baseline": snapshot(opening=False),
        "opening": snapshot(size=opening_size, relation=opening_size),
    }
    tick_paths = []
    for tick in range(1, 53):
        name = f"tick-{tick}"
        data[name] = snapshot(tick, opening_size + tick, opening_size + tick)
        tick_paths.append(str(tmp_path / name))
    for name, value in data.items():
        (tmp_path / name).write_text(json.dumps(value))
    args = [
        "measure",
        "--policy",
        str(tmp_path / "policy"),
        "--baseline",
        str(tmp_path / "baseline"),
        "--opening",
        str(tmp_path / "opening"),
        "--ticks",
        *tick_paths,
        "--reopens",
        *tick_paths,
    ]
    monkeypatch.setattr(sys, "argv", [*args, "--qualify"])
    assert main() == ordinary_exit
    capsys.readouterr()
    monkeypatch.setattr(sys, "argv", [*args, "--qualify-save"])
    assert main() == 1
    result = json.loads(capsys.readouterr().out)
    assert result["save_footprint"]["status"] == (
        "failed" if opening_size > 10_000_000_000 else "incomplete"
    )


def test_projection_twenty_gb_concern_does_not_fail_observed_short_save():
    result = footprint_run(9_999_999_900, [23_000_000])
    # Use a small opening for projection-only concern; this first case is an observed deficit.
    assert result["status"] == "incomplete"
    assert result["save_footprint"]["status"] == "failed"
    result = footprint_run(100, [23_000_000])
    comparison = result["save_footprint"]["projections"][2]
    assert comparison["projected_duration_ceiling_passed"] is None
    assert comparison["projected_twenty_gb_boundary_reached"] is False
    # A high opening can produce a future >20GB projection while current bytes still fit.
    result = footprint_run(5_100_000_000, [23_000_000])
    comparison = result["save_footprint"]["projections"][2]
    assert comparison["projected_twenty_gb_boundary_reached"] is True
    assert result["status"] == "incomplete"


@pytest.mark.parametrize(
    "growth,target_met", [(23_000_000, True), (23_000_001, False), (40_000_000, False)]
)
def test_optimization_target_does_not_fail_development(growth, target_met):
    result = run([snapshot(1, 100 + growth, 100 + growth)])
    assert policy().optimization_tick_growth_bytes == 23_000_000
    assert result["ticks"][0]["optimization_target_met"] is target_met
    assert result["optimization_target_met"] is target_met
    assert result["budget_passed"] is True
    assert result["status"] == "incomplete"


def configured(**changes):
    return Policy.model_validate({**policy().model_dump(), **changes})


def timings(count=2, advance=90_000_000_000, cold=100_000_000_000):
    from tools.devtools.national_storage_qualification import NativeTimings

    return NativeTimings.model_validate(
        {
            "version": 2,
            "source": "authoritative_native_instants_v2",
            "clock": "monotonic",
            "campaign": "00000000-0000-0000-0000-000000000001",
            "advances": [{"tick": n, "elapsed_ns": advance} for n in range(1, count + 1)],
            "cold_reopens": [{"tick": n, "elapsed_ns": cold} for n in range(1, count + 1)],
            "archive_catchups": [],
            "production_reads": [],
            "run": {
                "periods": count,
                "elapsed_ns": (advance + cold) * count,
                "compilation_included": False,
            },
        }
    )


def timing_result(p=None, t=None):
    from tools.devtools.national_storage_qualification import evaluate_timings

    t = t or timings()
    snapshots = tuple(
        Snapshot.model_validate({**snapshot(n), "campaign": t.campaign})
        for n in range(1, t.run.periods + 1)
    )
    return evaluate_timings(p or policy(), t, snapshots, snapshots)


@pytest.mark.parametrize("value", [0, -1, True, 1.0, "40", 2**63])
def test_configurable_limits_are_strict_positive_integers(value):
    for field in (
        "maximum_tick_growth_bytes",
        "maximum_advance_p95_seconds",
        "maximum_focused_control_seconds",
    ):
        with pytest.raises(ValueError):
            configured(**{field: value})


def test_configurable_policy_preserves_hard_geography_and_horizon():
    assert (
        configured(
            maximum_tick_growth_bytes=50_000_000, maximum_total_save_bytes=20_000_000_000
        ).maximum_total_save_bytes
        == 20_000_000_000
    )
    assert (
        configured(
            provisional_duration_years=26, save_qualification_ticks=338
        ).save_qualification_ticks
        == 338
    )
    for changes in (
        {"p95_minimum_samples": 1},
        {"county_count": 1},
        {"qualification_ticks": 2},
        {"model_year_ticks": 12},
        {"save_qualification_ticks": 326},
        {"optimization_tick_growth_bytes": 40_000_001},
    ):
        with pytest.raises(ValueError):
            configured(**changes)


def test_save_projection_includes_the_configured_duration():
    p = configured(provisional_duration_years=26, save_qualification_ticks=338)
    opening = Snapshot.model_validate(snapshot())
    tick = Snapshot.model_validate(snapshot(1, 101, 101))
    result = evaluate(p, opening, opening, (tick,), (tick,))
    projections = result["save_footprint"]["projections"]
    assert [row["years"] for row in projections] == [10, 25, 26, 50]
    configured_row = next(row for row in projections if row["years"] == 26)
    assert configured_row["ticks"] == 338
    assert configured_row["projected_total_bytes"] == {"numerator": 438, "denominator": 1}
    assert configured_row["projected_duration_ceiling_passed"] is True
    assert result["save_footprint"]["status"] == "incomplete"


def test_single_timing_sample_cannot_claim_p95_or_ui():
    result = timing_result(t=timings(1))
    assert result["empirical_p95_ns"] is None
    assert result["status"] == "incomplete"
    assert result["individual_advance_compliance"] is True
    assert result["ui_responsiveness"].startswith("unqualified")


def test_nearest_rank_and_cold_exact_thresholds():
    assert (
        timing_result(configured(p95_minimum_samples=2), timings(2, 120_000_000_000))["p95_status"]
        == "qualified"
    )
    assert (
        timing_result(configured(p95_minimum_samples=2), timings(2, 120_000_000_001))["status"]
        == "failed"
    )
    assert timing_result(t=timings(2, cold=180_000_000_000))["cold_open_status"] == "failed"
    assert timing_result(t=timings(2, cold=179_999_999_999))["cold_open_status"] == "qualified"


def test_exact_empirical_p95_is_not_maximum_or_interpolated():
    from tools.devtools.national_storage_qualification import NativeTimings

    data = timings(20).model_dump()
    for index, row in enumerate(data["advances"]):
        row["elapsed_ns"] = index + 1
    result = timing_result(configured(p95_minimum_samples=2), NativeTimings.model_validate(data))
    assert result["empirical_p95_ns"] == 19


def test_missing_reopen_and_advisory_duration_cannot_fabricate_proof():
    from tools.devtools.national_storage_qualification import NativeTimings, evaluate_timings

    data = timings(2).model_dump()
    data["cold_reopens"] = ()
    t = NativeTimings.model_validate(data)
    rows = tuple(Snapshot.model_validate({**snapshot(n), "campaign": t.campaign}) for n in (1, 2))
    assert (
        evaluate_timings(configured(p95_minimum_samples=2), t, rows, ())["status"] == "incomplete"
    )
    t = timings(52)
    result = timing_result(configured(preferred_qualification_seconds=1), t)
    assert result["status"] == "qualified"
    assert result["full_qualification_duration_preference_met"] is False


@pytest.mark.parametrize(
    "mutation", ["campaign", "tick", "negative", "bool", "compile", "too_short"]
)
def test_native_timing_provenance_and_shape_refuse(mutation):
    from tools.devtools.national_storage_qualification import NativeTimings

    data = timings().model_dump()
    if mutation == "campaign":
        data["campaign"] = "not-a-uuid"
    if mutation == "tick":
        data["advances"][0]["tick"] = 2
    if mutation == "negative":
        data["advances"][0]["elapsed_ns"] = -1
    if mutation == "bool":
        data["advances"][0]["elapsed_ns"] = True
    if mutation == "compile":
        data["run"]["compilation_included"] = True
    if mutation == "too_short":
        data["run"]["elapsed_ns"] = 0
    with pytest.raises(ValueError):
        NativeTimings.model_validate(data)


@pytest.mark.parametrize("time,passed", [("59.999999999", True), ("60", False)])
def test_focused_control_exact_duration(tmp_path, time, passed):
    from tools.devtools.national_storage_qualification import evaluate_focused

    path = tmp_path / "controls.xml"
    path.write_text(
        f'<testsuite><testcase classname="suite" name="control" time="{time}"/></testsuite>'
    )
    result = evaluate_focused(policy(), path)
    assert result["status"] == ("qualified" if passed else "failed")
    assert result["junit_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    "body",
    [
        '<testcase classname="s" name="n"/>',
        '<testcase classname="s" name="n" time="NaN"/>',
        '<testcase classname="s" name="n" time="-1"/>',
        '<testcase classname="s" name="n" time="0.0000000001"/>',
        '<testcase classname="s" name="n" time="1"><skipped/></testcase>',
        '<testcase classname="s" name="n" time="1"/><testcase classname="s" name="n" time="1"/>',
    ],
)
def test_focused_malformed_or_nonexecuted_evidence_refuses(tmp_path, body):
    from tools.devtools.national_storage_qualification import evaluate_focused

    path = tmp_path / "controls.xml"
    path.write_text(f"<testsuite>{body}</testsuite>")
    with pytest.raises(ValueError):
        evaluate_focused(policy(), path)


def test_actual_failed_control_cannot_qualify(tmp_path):
    from tools.devtools.national_storage_qualification import evaluate_focused

    path = tmp_path / "controls.xml"
    path.write_text(
        '<testsuite><testcase classname="s" name="n" time="1"><failure/></testcase></testsuite>'
    )
    assert evaluate_focused(policy(), path)["status"] == "failed"


def test_smoke_boundary_and_configurable_limits():
    from tools.devtools.national_storage_qualification import NativeTimings

    data = timings().model_dump()
    data["run"]["elapsed_ns"] = 900_000_000_000
    assert timing_result(t=NativeTimings.model_validate(data))["smoke_status"] == "qualified"
    data["run"]["elapsed_ns"] += 1
    assert timing_result(t=NativeTimings.model_validate(data))["status"] == "failed"
    assert (
        timing_result(
            configured(maximum_routine_smoke_seconds=901), NativeTimings.model_validate(data)
        )["smoke_status"]
        == "qualified"
    )


def test_timing_campaign_and_reopen_evidence_must_match():
    from tools.devtools.national_storage_qualification import evaluate_timings

    t = timings()
    wrong = tuple(Snapshot.model_validate(snapshot(n)) for n in (1, 2))
    with pytest.raises(ValueError):
        evaluate_timings(policy(), t, wrong, wrong)
    right = tuple(Snapshot.model_validate({**snapshot(n), "campaign": t.campaign}) for n in (1, 2))
    with pytest.raises(ValueError):
        evaluate_timings(policy(), t, right, right[:1])


def test_policy_validation_and_focused_cli_need_no_database_inputs(tmp_path, monkeypatch, capsys):
    import json
    import sys

    from tools.devtools.national_storage_qualification import main

    selected = tmp_path / "policy.json"
    selected.write_text(json.dumps(policy().model_dump()))
    monkeypatch.setattr(sys, "argv", ["measure", "--validate-policy", "--policy", str(selected)])
    assert main() == 0
    assert json.loads(capsys.readouterr().out)["policy"]["maximum_tick_growth_bytes"] == 40_000_000
    junit = tmp_path / "controls.xml"
    junit.write_text('<testsuite><testcase classname="s" name="n" time="1"/></testsuite>')
    monkeypatch.setattr(
        sys,
        "argv",
        ["measure", "--policy", str(selected), "--focused-junit", str(junit), "--qualify-focused"],
    )
    assert main() == 0
    assert json.loads(capsys.readouterr().out)["status"] == "qualified"


def test_junit_document_type_refuses_without_entity_expansion(tmp_path):
    from tools.devtools.national_storage_qualification import evaluate_focused

    p = tmp_path / "controls.xml"
    p.write_text(
        '<!DOCTYPE testsuite [<!ENTITY secret "fake">]><testsuite><testcase classname="s" name="n" time="1"/></testsuite>'
    )
    with pytest.raises(ValueError):
        evaluate_focused(policy(), p)


@pytest.mark.parametrize(
    "body", ['{"budget":1,"budget":2}', '{"nested":{"tick":1,"tick":2}}', '{"time":NaN}']
)
def test_authoritative_json_rejects_duplicate_or_nonfinite_keys(tmp_path, body):
    from tools.devtools.national_storage_qualification import strict_json

    path = tmp_path / "evidence.json"
    path.write_text(body)
    with pytest.raises(ValueError):
        strict_json(path)


@pytest.mark.parametrize(
    "value", ["1e-999999999", "1e999999999", "9223372036.854775808", "0.0000000001"]
)
def test_junit_exponents_refuse_without_unbounded_denominator(value):
    from tools.devtools.national_storage_qualification import exact_testcase_nanoseconds

    with pytest.raises(ValueError):
        exact_testcase_nanoseconds(value)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1.0000000000000000000000000000000000000000", 1_000_000_000),
        ("0e-999999999", 0),
        ("0.0000000010000000000000", 1),
        ("9223372036.8547758070000", 2**63 - 1),
    ],
)
def test_junit_trailing_zero_exact_values_remain_valid(value, expected):
    from tools.devtools.national_storage_qualification import exact_testcase_nanoseconds

    assert exact_testcase_nanoseconds(value) == expected


@pytest.mark.parametrize("failure", ["failure", "error"])
def test_junit_failure_cannot_hide_behind_skipped(tmp_path, failure):
    from tools.devtools.national_storage_qualification import evaluate_focused

    path = tmp_path / "controls.xml"
    path.write_text(
        f'<testsuite><testcase classname="s" name="n" time="1"><skipped/><{failure}/></testcase><testcase classname="s" name="other" time="1"/></testsuite>'
    )
    with pytest.raises(ValueError):
        evaluate_focused(policy(), path)


def test_cli_no_reopen_evidence_reports_incomplete(tmp_path, monkeypatch, capsys):
    import json
    import sys

    from tools.devtools.national_storage_qualification import main

    data = {
        "policy": policy().model_dump(),
        "baseline": snapshot(opening=False),
        "opening": snapshot(),
        "tick": snapshot(1, 101, 101),
    }
    for name, value in data.items():
        (tmp_path / name).write_text(json.dumps(value))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "measure",
            "--policy",
            str(tmp_path / "policy"),
            "--baseline",
            str(tmp_path / "baseline"),
            "--opening",
            str(tmp_path / "opening"),
            "--ticks",
            str(tmp_path / "tick"),
            "--qualify",
        ],
    )
    assert main() == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "incomplete"
    assert report["restart_verified_ticks"] == 0


@pytest.mark.parametrize("target", ["policy", "tick", "timing"])
def test_cli_authoritative_inputs_refuse_duplicate_json(tmp_path, monkeypatch, capsys, target):
    import json
    import sys

    from tools.devtools.national_storage_qualification import main

    t = timings(1)
    data = {
        "policy": policy().model_dump(),
        "baseline": {**snapshot(opening=False), "campaign": t.campaign},
        "opening": {**snapshot(), "campaign": t.campaign},
        "tick": {**snapshot(1, 101, 101), "campaign": t.campaign},
        "timing": t.model_dump(),
    }
    for name, value in data.items():
        text = json.dumps(value)
        if name == target:
            key = (
                "maximum_tick_growth_bytes"
                if target == "policy"
                else ("campaign" if target == "tick" else "version")
            )
            text = text[:-1] + f', "{key}": {json.dumps(value[key])}' + "}"
        (tmp_path / name).write_text(text)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "measure",
            "--policy",
            str(tmp_path / "policy"),
            "--baseline",
            str(tmp_path / "baseline"),
            "--opening",
            str(tmp_path / "opening"),
            "--ticks",
            str(tmp_path / "tick"),
            "--reopens",
            str(tmp_path / "tick"),
            "--timings",
            str(tmp_path / "timing"),
        ],
    )
    with pytest.raises(SystemExit) as refused:
        main()
    assert refused.value.code == 2
    assert "duplicate JSON key" in capsys.readouterr().err


def smoke_evidence(count=2, growth=1, missing_recovery=False, lookup_gap=False, timing=None):
    from tools.devtools.national_storage_qualification import NativeTimings

    t = timing or timings(count)
    if missing_recovery:
        data = t.model_dump()
        data["cold_reopens"] = ()
        t = NativeTimings.model_validate(data)
    baseline = {**snapshot(opening=False), "campaign": t.campaign}
    opening = {**snapshot(), "campaign": t.campaign}
    ticks = []
    for n in range(1, count + 1):
        row = {**snapshot(n, 100 + n * growth, 100 + n * growth), "campaign": t.campaign}
        if lookup_gap:
            row.pop("lookup_delta_hashes")
        ticks.append(row)
    reopens = [] if missing_recovery else ticks
    storage = evaluate(
        policy(),
        Snapshot.model_validate(baseline),
        Snapshot.model_validate(opening),
        tuple(Snapshot.model_validate(row) for row in ticks),
        tuple(Snapshot.model_validate(row) for row in reopens),
    )
    return storage, t, baseline, opening, ticks, reopens


def smoke_result(p=None, **kwargs):
    from tools.devtools.national_storage_qualification import evaluate_smoke, evaluate_timings

    p = p or policy()
    storage, timing, _, _, ticks, reopens = smoke_evidence(**kwargs)
    report = evaluate_timings(
        p,
        timing,
        tuple(Snapshot.model_validate(row) for row in ticks),
        tuple(Snapshot.model_validate(row) for row in reopens),
    )
    return evaluate_smoke(p, storage, report)


def test_two_period_smoke_qualifies_without_full_storage_or_p95_claim():
    result = smoke_result()
    assert result["status"] == "qualified"
    assert result["full_storage_status"] == "incomplete"
    assert result["full_timing_status"] == "incomplete"


@pytest.mark.parametrize("count", [1, 3])
def test_smoke_requires_exact_configured_period_count(count):
    assert smoke_result(count=count)["status"] == "incomplete"
    assert smoke_result(configured(routine_smoke_periods=3), count=3)["status"] == "qualified"


@pytest.mark.parametrize("defect", ["recovery", "lookup", "timing"])
def test_missing_smoke_evidence_never_qualifies(defect):
    from tools.devtools.national_storage_qualification import evaluate_smoke

    if defect == "timing":
        storage, *_ = smoke_evidence()
        result = evaluate_smoke(policy(), storage, {"status": "incomplete"})
    else:
        result = smoke_result(missing_recovery=defect == "recovery", lookup_gap=defect == "lookup")
    assert result["status"] == "incomplete"


@pytest.mark.parametrize("growth,passed", [(40_000_000, True), (40_000_001, False)])
def test_smoke_development_budget_boundary(growth, passed):
    assert smoke_result(growth=growth)["status"] == ("qualified" if passed else "failed")


@pytest.mark.parametrize("advance,passed", [(120_000_000_000, True), (120_000_000_001, False)])
def test_smoke_observed_advance_limit_is_enforced_without_p95_claim(advance, passed):
    result = smoke_result(timing=timings(2, advance=advance))
    assert result["status"] == ("qualified" if passed else "failed")
    assert result["full_timing_status"] == "incomplete"


def test_smoke_cold_and_whole_duration_are_hard_limits():
    from tools.devtools.national_storage_qualification import NativeTimings

    assert smoke_result(timing=timings(2, cold=180_000_000_000))["status"] == "failed"
    data = timings().model_dump()
    data["run"]["elapsed_ns"] = 900_000_000_001
    assert smoke_result(timing=NativeTimings.model_validate(data))["status"] == "failed"


@pytest.mark.parametrize(
    "defect,exit_code", [(None, 0), ("recovery", 1), ("timing", 1), ("budget", 1)]
)
def test_cli_smoke_gate_separates_short_run_acceptance(
    tmp_path, monkeypatch, capsys, defect, exit_code
):
    import json
    import sys

    from tools.devtools.national_storage_qualification import main

    _storage, timing, baseline, opening, ticks, reopens = smoke_evidence(
        missing_recovery=defect == "recovery", growth=40_000_001 if defect == "budget" else 1
    )
    values = {
        "policy": policy().model_dump(),
        "baseline": baseline,
        "opening": opening,
        "timing": timing.model_dump(),
    }
    values.update({f"tick-{n}": row for n, row in enumerate(ticks, 1)})
    for name, value in values.items():
        (tmp_path / name).write_text(json.dumps(value))
    args = [
        "measure",
        "--policy",
        str(tmp_path / "policy"),
        "--baseline",
        str(tmp_path / "baseline"),
        "--opening",
        str(tmp_path / "opening"),
        "--ticks",
        *[str(tmp_path / f"tick-{n}") for n in range(1, 3)],
        "--qualify-smoke",
    ]
    if reopens:
        args.extend(["--reopens", *[str(tmp_path / f"tick-{n}") for n in range(1, 3)]])
    if defect != "timing":
        args.extend(["--timings", str(tmp_path / "timing")])
    monkeypatch.setattr(sys, "argv", args)
    assert main() == exit_code
    result = json.loads(capsys.readouterr().out)
    assert result["development_smoke"]["status"] == (
        "qualified" if defect is None else ("failed" if defect == "budget" else "incomplete")
    )
    if defect is None:
        assert result["status"] == "incomplete"
        assert result["timings"]["p95_status"] == "incomplete"


@pytest.mark.parametrize(
    "extra",
    [
        ["--qualify"],
        ["--qualify-smoke"],
        ["--qualify-timing"],
        ["--qualify-save"],
        ["--qualify-focused"],
        ["--baseline", "unused"],
        ["--opening", "unused"],
        ["--ticks", "unused"],
        ["--reopens"],
        ["--timings", "unused"],
        ["--focused-junit", "unused"],
    ],
)
def test_validation_only_refuses_ignored_acceptance_or_evidence(
    tmp_path, monkeypatch, capsys, extra
):
    import json
    import sys

    from tools.devtools.national_storage_qualification import main

    selected = tmp_path / "policy.json"
    selected.write_text(json.dumps(policy().model_dump()))
    monkeypatch.setattr(
        sys, "argv", ["measure", "--policy", str(selected), "--validate-policy", *extra]
    )
    with pytest.raises(SystemExit) as refused:
        main()
    assert refused.value.code == 2
    assert (
        "validation-only mode cannot accept qualification flags or evidence"
        in capsys.readouterr().err
    )


def test_routine_smoke_must_fit_current_admitted_producer_horizon():
    assert configured(routine_smoke_periods=325).routine_smoke_periods == 325
    with pytest.raises(ValueError, match="routine smoke must fit the admitted save horizon"):
        configured(routine_smoke_periods=326)


def test_p95_sample_count_accepts_complete_admitted_horizon():
    assert configured(p95_minimum_samples=325).p95_minimum_samples == 325


def test_p95_sample_count_refuses_unreachable_horizon():
    with pytest.raises(ValueError, match="p95 samples must fit the admitted save horizon"):
        configured(p95_minimum_samples=326)


@pytest.mark.parametrize(
    "field", ["maximum_archive_catchup_seconds", "maximum_production_read_seconds"]
)
def test_playable_phase_limits_are_positive_and_default_180(field):
    assert getattr(policy(), field) == 180
    for value in (0, -1, True, 1.0, "180"):
        with pytest.raises(ValueError):
            configured(**{field: value})


def test_native_timing_rejects_old_shape():
    from tools.devtools.national_storage_qualification import NativeTimings

    data = timings().model_dump()
    data["version"] = 1
    data["source"] = "authoritative_native_instants_v1"
    with pytest.raises(ValueError):
        NativeTimings.model_validate(data)


def playable_evidence(count=2):
    import json

    from tools.devtools.national_storage_qualification import NativeTimings

    storage, native, baseline, opening, ticks, reopens = smoke_evidence(count=count)
    data = native.model_dump()
    for phase in ("archive_catchups", "production_reads"):
        data[phase] = [{"tick": n, "elapsed_ns": 1} for n in range(1, count + 1)]
    data["run"]["elapsed_ns"] += 2 * count
    native = NativeTimings.model_validate(data)
    h = "ab" * 32
    commands = [[n] * 32 for n in (1, 2)]
    report = {
        "version": 3,
        "capture_mode": "playable-aid",
        "policy_sha256": h,
        "campaign": native.campaign,
        "foundation_sha256": h,
        "requested_periods": count,
        "county_geoids": opening["county_geoids"],
        "aid_periods": [
            {"period": n, "commitment": {"commitment_id": commands[n - 1]}} for n in (1, 2)
        ],
        "boundaries": [
            {
                "tick": n,
                "campaign": native.campaign,
                "foundation_sha256": h,
                **dict.fromkeys(
                    (
                        "tick_content_hash",
                        "envelope_digest",
                        "register_storage_sha256",
                        "receipt_storage_sha256",
                        "lookup_storage_sha256",
                        "canonical_receipt_sha256",
                        "nominal_world_hash",
                    ),
                    h,
                ),
                "archive": {
                    "processed_tick": n,
                    "durable_tick": n,
                    "expected_tick": n,
                    "pending_count": 0,
                    "dossier_sha256": h,
                },
                "production": {
                    "tick": n,
                    "nominal_world_hash": h,
                    "snapshot_sha256": h,
                    "county_roster_sha256": hashlib.sha256(
                        json.dumps(opening["county_geoids"], separators=(",", ":")).encode("ascii")
                    ).hexdigest(),
                },
                "trade": {
                    "period": n,
                    "tick_content_hash": h,
                    "canonical_receipt_sha256": h,
                    "imports": {"settled_deliveries": 0, "settled_cash_micros": "0"},
                    "exports": {"settled_deliveries": 0, "settled_cash_micros": "0"},
                    "positive_foreign_production_receipts": 0,
                    "productive_foreign_sites": 0,
                    "unresolved_trade_orders": 2,
                },
            }
            for n in range(1, count + 1)
        ],
        "continuations": [
            {
                "period": n,
                "tail": {"resolve_tick": n, "tick_content_hash": h},
                "organizer_snapshot_sha256": h,
                "latest_marker": [n, h, h],
                "nominal_world_hash": h,
            }
            for n in range(1, count + 1)
        ],
        "canonical_protocol_recovery": "passed",
        "positive_aid_consequences": "passed",
        "remote_consumed": True,
        "local_consumed": True,
        "native_window_evidence": "not_run",
        "independent_trade_accounting": {
            "version": 1,
            "status": "incomplete",
            "periods": count,
            "basis": "committed_recurring_procurement_delivery_realization_and_exact_settlement",
            "imports": {"settled_deliveries": 0, "settled_cash_micros": "0"},
            "exports": {"settled_deliveries": 0, "settled_cash_micros": "0"},
            "positive_foreign_production_receipts": 0,
            "productive_foreign_sites": 0,
            "unresolved_trade_orders": 2,
        },
        "independent_finite_aid_practice": {
            "status": "passed",
            "completed_original_commands": commands,
            "terminal_original_commands": commands,
            "basis": "actual_consumed_support_independent_partner_response_and_authenticated_finite_debits",
        },
        "independent_account_posting_audit": {
            "cash_and_in_kind_postings": "passed",
            "time_partition_and_residual_bound": "passed",
            "exact_final_contribution_debit_ledger": "passed",
            "accepted_original_commands": 2,
            "periods": [
                {
                    "period": n,
                    "tick_content_hash": h,
                    "canonical_receipt_sha256": h,
                    "selected_aid": [
                        {
                            "original_commitment": commands[n - 1],
                            "quantity": 1,
                            "outcome": "Granted",
                        }
                    ]
                    if n <= 2
                    else [],
                    "independent_practices": [
                        {
                            "original_commitment": commands[n - 1],
                            "consumed_support": True,
                            "recipient_debited_hours": 1,
                            "finite_practice_completed": True,
                            "period": n,
                            "partner_response": "participated",
                            "outcome": "aid_practice_completed",
                        }
                    ]
                    if n <= 2
                    else [],
                }
                for n in range(1, count + 1)
            ],
        },
    }
    return report, storage, native, baseline, opening, ticks, reopens


def playable_result(report=None, timing=None, count=2, selected_policy=None):
    from tools.devtools.national_storage_qualification import (
        PlayableReport,
        evaluate_playable,
        evaluate_smoke,
        evaluate_timings,
    )

    raw, storage, native, _baseline, opening, ticks, reopens = playable_evidence(count=count)
    selected_policy = selected_policy or policy()
    native = timing or native
    parsed_ticks = tuple(Snapshot.model_validate(t) for t in ticks)
    timing_report = evaluate_timings(
        selected_policy, native, parsed_ticks, tuple(Snapshot.model_validate(t) for t in reopens)
    )
    smoke = evaluate_smoke(selected_policy, storage, timing_report)
    return evaluate_playable(
        selected_policy,
        "ab" * 32,
        PlayableReport.model_validate(report or raw),
        native,
        Snapshot.model_validate(opening),
        parsed_ticks,
        storage,
        timing_report,
        smoke,
    )


def test_actual_material_playable_admission_keeps_window_and_fun_unqualified():
    result = playable_result()
    assert result["status"] == "qualified"
    assert result["native_window_status"] == "unqualified"
    assert "fun remain unqualified" in result["scope"]


def test_playable_evidence_refuses_omitted_trade_accounting():
    report = playable_evidence()[0]
    report.pop("independent_trade_accounting", None)
    for boundary in report["boundaries"]:
        boundary.pop("trade", None)
    with pytest.raises(ValueError, match="trade"):
        playable_result(report)


def settled_trade(report):
    for index, direction in enumerate(("imports", "exports")):
        fact = report["boundaries"][index]["trade"]
        movement = {"settled_deliveries": 1, "settled_cash_micros": str(7 + index)}
        fact[direction] = movement.copy()
        fact["positive_foreign_production_receipts"] = 1
        fact["productive_foreign_sites"] = 1
        report["independent_trade_accounting"][direction] = movement.copy()
    report["independent_trade_accounting"].update(
        status="passed", positive_foreign_production_receipts=2, productive_foreign_sites=1
    )
    return report


def test_smoke_preserves_pending_trade_without_claiming_economic_acceptance():
    result = playable_result()
    assert result["status"] == "qualified"
    assert result["trade_accounting_status"] == "incomplete"
    assert result["trade_required_for_run"] is False


def test_full_national_admission_requires_settled_trade_and_foreign_production():
    result = playable_result(count=52)
    assert result["status"] == "incomplete"
    assert result["trade_accounting_status"] == "incomplete"
    assert result["trade_required_for_run"] is True
    report = settled_trade(playable_evidence(count=52)[0])
    result = playable_result(report, count=52)
    assert result["status"] == "qualified"
    assert result["trade_accounting_status"] == "qualified"
    assert result["native_window_status"] == "unqualified"


@pytest.mark.parametrize("missing", ["imports", "exports", "foreign-production"])
def test_severed_trade_direction_or_production_removes_full_acceptance(missing):
    report = settled_trade(playable_evidence(count=52)[0])
    for boundary in report["boundaries"]:
        if missing == "foreign-production":
            boundary["trade"].update(
                positive_foreign_production_receipts=0, productive_foreign_sites=0
            )
        else:
            boundary["trade"][missing] = {"settled_deliveries": 0, "settled_cash_micros": "0"}
    summary = report["independent_trade_accounting"]
    summary["status"] = "incomplete"
    if missing == "foreign-production":
        summary.update(positive_foreign_production_receipts=0, productive_foreign_sites=0)
    else:
        summary[missing] = {"settled_deliveries": 0, "settled_cash_micros": "0"}
    assert playable_result(report, count=52)["status"] == "incomplete"


def test_smoke_override_cannot_bypass_full_run_trade_requirement():
    selected = configured(routine_smoke_periods=52, maximum_routine_smoke_seconds=11_000)
    result = playable_result(count=52, selected_policy=selected)
    assert result["status"] == "incomplete"
    assert result["trade_required_for_run"] is True


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r.update(version=2),
        lambda r: r["boundaries"][0]["trade"].update(period=2),
        lambda r: r["boundaries"][0]["trade"].update(tick_content_hash="cd" * 32),
        lambda r: r["boundaries"][0]["trade"].update(canonical_receipt_sha256="cd" * 32),
        lambda r: r["independent_trade_accounting"].update(periods=1),
        lambda r: r["independent_trade_accounting"]["imports"].update(settled_cash_micros="9"),
        lambda r: r["independent_trade_accounting"]["imports"].update(settled_deliveries=2),
        lambda r: r["independent_trade_accounting"].update(positive_foreign_production_receipts=3),
        lambda r: r["independent_trade_accounting"].update(unresolved_trade_orders=0),
        lambda r: r["independent_trade_accounting"].update(status="incomplete"),
        lambda r: r["independent_trade_accounting"].update(version=True),
    ],
    ids=[
        "old-playable-version",
        "period",
        "tick-hash",
        "receipt-hash",
        "summary-periods",
        "summary-cash",
        "summary-deliveries",
        "summary-production",
        "summary-pending",
        "summary-status",
        "boolean-version",
    ],
)
def test_trade_proofs_refuse_wrong_identity_or_unexplained_totals(mutation):
    report = settled_trade(playable_evidence()[0])
    mutation(report)
    with pytest.raises(ValueError):
        playable_result(report)


@pytest.mark.parametrize("invalid", ["7.0", "-1", "07", 7, True, str(2**127)])
def test_trade_cash_refuses_inexact_or_unsupported_values(invalid):
    report = settled_trade(playable_evidence()[0])
    report["boundaries"][0]["trade"]["imports"]["settled_cash_micros"] = invalid
    with pytest.raises(ValueError):
        playable_result(report)


def test_trade_cash_preserves_integers_beyond_float_precision():
    report = settled_trade(playable_evidence()[0])
    exact = str(2**53 + 1)
    report["boundaries"][0]["trade"]["imports"]["settled_cash_micros"] = exact
    report["independent_trade_accounting"]["imports"]["settled_cash_micros"] = exact
    assert playable_result(report)["trade_accounting_status"] == "qualified"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r.update(version=1),
        lambda r: r.update(policy_sha256="cd" * 32),
        lambda r: r.update(campaign="00000000-0000-0000-0000-000000000002"),
        lambda r: r["boundaries"][0].update(foundation_sha256="cd" * 32),
        lambda r: r["boundaries"][0].update(tick_content_hash="cd" * 32),
        lambda r: r["boundaries"][0].update(register_storage_sha256="cd" * 32),
        lambda r: r["boundaries"][0].update(lookup_storage_sha256="cd" * 32),
        lambda r: r["boundaries"][0].update(canonical_receipt_sha256="cd" * 32),
        lambda r: r["boundaries"][0]["archive"].update(expected_tick=2),
        lambda r: r["boundaries"][0]["archive"].update(dossier_sha256=""),
        lambda r: r["boundaries"][0]["production"].update(snapshot_sha256=""),
        lambda r: r.update(county_geoids=["00000"]),
        lambda r: r["boundaries"][0]["production"].update(nominal_world_hash="cd" * 32),
        lambda r: r["continuations"][0].update(nominal_world_hash="cd" * 32),
        lambda r: r["boundaries"].pop(),
        lambda r: r["independent_account_posting_audit"]["periods"].pop(),
        lambda r: r["independent_account_posting_audit"]["periods"][0].update(
            tick_content_hash="cd" * 32
        ),
        lambda r: r.update(native_window_evidence="passed"),
    ],
    ids=[
        "old-version",
        "policy",
        "campaign",
        "foundation",
        "tick-hash",
        "encoded-register",
        "lookup",
        "canonical-receipt",
        "archive-period",
        "missing-dossier",
        "missing-snapshot",
        "truncated-roster",
        "production-world",
        "recovery-world",
        "truncated-boundaries",
        "truncated-audit",
        "audit-hash",
        "invented-window",
    ],
)
def test_playable_refuses_malformed_stale_or_disconnected_evidence(mutation):
    raw = playable_evidence()[0]
    mutation(raw)
    with pytest.raises(ValueError):
        playable_result(raw)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r["boundaries"][0]["archive"].update(processed_tick=0),
        lambda r: r["boundaries"][0]["archive"].update(durable_tick=0),
        lambda r: r["boundaries"][0]["archive"].update(pending_count=1),
        lambda r: r.update(remote_consumed=False),
        lambda r: r["independent_account_posting_audit"].update(
            cash_and_in_kind_postings="incomplete"
        ),
        lambda r: r["independent_account_posting_audit"]["periods"][0].update(selected_aid=[]),
        lambda r: r["independent_account_posting_audit"]["periods"][0]["independent_practices"][
            0
        ].update(consumed_support=False),
        lambda r: r["independent_account_posting_audit"]["periods"][0]["independent_practices"][
            0
        ].update(recipient_debited_hours=0),
        lambda r: r["independent_finite_aid_practice"].update(completed_original_commands=[]),
    ],
    ids=[
        "processed",
        "durable",
        "pending",
        "remote",
        "audit-status",
        "delivery",
        "consumption",
        "debit",
        "practice",
    ],
)
def test_queued_delayed_or_unproven_aid_remains_incomplete(mutation):
    raw = playable_evidence()[0]
    mutation(raw)
    assert playable_result(raw)["status"] == "incomplete"


@pytest.mark.parametrize("phase", ["archive_catchups", "production_reads"])
def test_playable_phase_timing_requires_exact_period_set_and_limit(phase):
    from tools.devtools.national_storage_qualification import NativeTimings

    raw = playable_evidence()[2].model_dump()
    raw[phase][0]["elapsed_ns"] = 180_000_000_000
    raw["run"]["elapsed_ns"] += 180_000_000_000
    assert playable_result(timing=NativeTimings.model_validate(raw))["status"] == "qualified"
    raw[phase][0]["elapsed_ns"] += 1
    assert playable_result(timing=NativeTimings.model_validate(raw))["status"] == "failed"
    raw[phase] = raw[phase][:-1]
    with pytest.raises(ValueError):
        playable_result(timing=NativeTimings.model_validate(raw))


def test_atomic_partial_playable_progress_cannot_claim_requested_completion():
    raw = playable_evidence()[0]
    raw["requested_periods"] = 52
    assert playable_result(raw)["status"] == "incomplete"


@pytest.mark.parametrize("defect", [None, "policy", "archive", "timing", "missing"])
def test_cli_unified_playable_admission(tmp_path, monkeypatch, capsys, defect):
    import json
    import sys

    from tools.devtools.national_storage_qualification import main

    report, _storage, native, baseline, opening, ticks, reopens = playable_evidence()
    chosen = tmp_path / "policy.json"
    chosen.write_text(json.dumps(policy().model_dump()))
    report["policy_sha256"] = hashlib.sha256(chosen.read_bytes()).hexdigest()
    if defect == "policy":
        report["policy_sha256"] = "cd" * 32
    if defect == "archive":
        report["boundaries"][0]["archive"]["pending_count"] = 1
    data = native.model_dump(mode="json")
    if defect == "timing":
        data["production_reads"] = []
    evidence = {"baseline": baseline, "opening": opening, "native": data, "playable": report}
    evidence.update({f"tick-{n}": row for n, row in enumerate(ticks, 1)})
    evidence.update({f"reopen-{n}": row for n, row in enumerate(reopens, 1)})
    for name, raw in evidence.items():
        (tmp_path / name).write_text(json.dumps(raw))
    args = [
        "measure",
        "--policy",
        str(chosen),
        "--baseline",
        str(tmp_path / "baseline"),
        "--opening",
        str(tmp_path / "opening"),
        "--ticks",
        str(tmp_path / "tick-1"),
        str(tmp_path / "tick-2"),
        "--reopens",
        str(tmp_path / "reopen-1"),
        str(tmp_path / "reopen-2"),
        "--timings",
        str(tmp_path / "native"),
        "--qualify-playable",
    ]
    if defect != "missing":
        args.extend(["--playable-report", str(tmp_path / "playable")])
    monkeypatch.setattr(sys, "argv", args)
    if defect in ("policy", "timing", "missing"):
        with pytest.raises(SystemExit) as refused:
            main()
        assert refused.value.code == 2
    else:
        assert main() == int(defect == "archive")
        output = json.loads(capsys.readouterr().out)
        assert output["policy_sha256"] == report["policy_sha256"]
        assert output["material_playable"]["status"] == (
            "qualified" if defect is None else "incomplete"
        )
        assert output["material_playable"]["native_window_status"] == "unqualified"


def test_production_roster_digest_matches_shared_actual_roster():
    raw = playable_evidence()[0]
    assert len(raw["county_geoids"]) == 3144
    assert all("county_geoids" not in b["production"] for b in raw["boundaries"])
    assert playable_result(raw)["status"] == "qualified"
    raw["boundaries"][1]["production"]["county_roster_sha256"] = "cd" * 32
    with pytest.raises(ValueError, match="county roster digest"):
        playable_result(raw)


def test_shared_roster_is_checked_against_each_actual_storage_snapshot():
    from tools.devtools.national_storage_qualification import (
        PlayableReport,
        evaluate_playable,
        evaluate_smoke,
        evaluate_timings,
    )

    raw, storage, native, _baseline, opening, ticks, reopens = playable_evidence()
    parsed = tuple(Snapshot.model_validate(t) for t in ticks)
    timing = evaluate_timings(
        policy(), native, parsed, tuple(Snapshot.model_validate(t) for t in reopens)
    )
    changed = deepcopy(ticks)
    changed[1]["county_geoids"] = sorted(["99999", *changed[1]["county_geoids"][1:]])
    with pytest.raises(ValueError, match="actual storage period roster"):
        evaluate_playable(
            policy(),
            "ab" * 32,
            PlayableReport.model_validate(raw),
            native,
            Snapshot.model_validate(opening),
            tuple(Snapshot.model_validate(t) for t in changed),
            storage,
            timing,
            evaluate_smoke(policy(), storage, timing),
        )


def test_collector_current_receipt_storage_domain_refuses_v1():
    state, receipt, lookup = current_headers()
    receipt = b"BabylonReceiptStorageV1\0" + receipt[len(b"BabylonReceiptStorageV2\0") :]
    with pytest.raises(ValueError, match="unsupported or truncated"):
        package_claim_from_headers(1, state, receipt, lookup, 200, 2300, len(lookup) + 7)


def test_collector_current_state_storage_domain_refuses_v3():
    state, receipt, lookup = current_headers()
    state = state.replace(b"state-storage.v4", b"state-storage.v3")
    with pytest.raises(ValueError):
        package_claim_from_headers(1, state, receipt, lookup, 200, 2300, len(lookup) + 7)
