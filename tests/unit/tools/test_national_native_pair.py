"""Designed command custody for serial native measurement members."""

import hashlib
import json
from uuid import UUID

import pytest
from tools.devtools.national_windowed_qualification import Commitment

CAMPAIGN = "d32bc4bc-d21f-4052-973f-f971a75092cb"
MARKER = "98" * 32


def wire(value):
    return json.dumps(value, separators=(",", ":")).encode()


def original(nonce, quantity=2, partner=17):
    command = {
        "campaign_id": list(UUID(CAMPAIGN).bytes),
        "actor_id": 11,
        "authority_id": [8] * 16,
        "expected_period": 0,
        "content_digest": [2] * 32,
        "resource_digest": [3] * 32,
        "nonce": [nonce] * 16,
        "choice": "remote_aid",
        "allocation": {"aid": {"food_quantity": quantity, "cash_micros": "280000000"}},
    }
    command_raw = wire(command)
    cid = list(hashlib.sha256(b"babylon.organizer-commitment.v3\0" + command_raw).digest())
    commit = {"command": command, "resolves_period": 1, "commitment_id": cid}
    rid = hashlib.sha256(
        b"babylon.organizer-receipt.v1\0" + wire([command["campaign_id"], 11, 1, cid])
    ).digest()
    receipt = {
        "commitment_id": cid,
        "receipt_id": list(rid),
        "choice": "remote_aid",
        "actor_id": 11,
        "partner_actor_id": None,
        "period": 1,
    }
    return (
        {
            "period": 1,
            "consumed": 1,
            "nonce": bytes(command["nonce"]).hex(),
            "command_hex": command_raw.hex(),
            "commitment_hex": wire(commit).hex(),
            "commitment_id": bytes(cid).hex(),
            "marker": MARKER,
            "receipt_id": rid.hex(),
            "receipt_hex": wire(receipt).hex(),
        },
        Commitment.model_validate(commit),
        partner,
    )


def test_independent_nonces_match_only_after_each_raw_receipt_and_marker_joins():
    from tools.devtools.national_native_pair import decision_semantics

    projections = []
    for nonce in (23, 94):
        row, accepted, partner = original(nonce)
        projections.append(decision_semantics([row], [accepted], [partner], {1: MARKER}, CAMPAIGN))
    assert projections[0] == projections[1]
    for changed in ("marker", "receipt_id", "command_hex", "receipt_hex", "nonce"):
        broken = dict(row)
        broken[changed] = "ab" * 32
        with pytest.raises(ValueError):
            decision_semantics([broken], [accepted], [partner], {1: MARKER}, CAMPAIGN)
    for q, p in ((3, 17), (2, 19)):
        row, accepted, partner = original(42, q, p)
        assert (
            decision_semantics([row], [accepted], [partner], {1: MARKER}, CAMPAIGN)
            != projections[0]
        )


def bind_originals(old_campaign, campaign, playable, database, selected, offset):
    ids = {}
    originals = []
    for n in (1, 2):
        command = dict(
            playable["aid_periods"][n - 1]["commitment"]["command"],
            campaign_id=list(UUID(campaign).bytes),
            nonce=[n + offset] * 16,
        )
        raw = wire(command)
        cid = hashlib.sha256(b"babylon.organizer-commitment.v3\0" + raw).digest()
        ids[n] = list(cid)
        accepted = {"command": command, "resolves_period": n, "commitment_id": list(cid)}
        rid = hashlib.sha256(
            b"babylon.organizer-receipt.v1\0" + wire([command["campaign_id"], 1, n, list(cid)])
        ).digest()
        receipt = {
            "actor_id": 1,
            "period": n,
            "choice": command["choice"],
            "partner_actor_id": None,
            "commitment_id": list(cid),
            "receipt_id": list(rid),
        }
        originals.append(
            {
                "period": n,
                "consumed": n,
                "nonce": bytes(command["nonce"]).hex(),
                "command_hex": raw.hex(),
                "commitment_hex": wire(accepted).hex(),
                "commitment_id": cid.hex(),
                "marker": "ab" * 32,
                "receipt_id": rid.hex(),
                "receipt_hex": wire(receipt).hex(),
            }
        )

    def bind(value, key=None):
        if isinstance(value, dict):
            return {k: bind(v, k) for k, v in value.items()}
        if isinstance(value, list):
            if key == "campaign_id":
                return list(UUID(campaign).bytes)
            if key == "nonce":
                return [value[0] + offset] * 16
            if (
                key not in ("content_digest", "resource_digest")
                and len(value) == 32
                and value[0] in (1, 2)
                and value == [value[0]] * 32
            ):
                return ids[value[0]]
            return [bind(v, key) for v in value]
        if key == "policy_sha256":
            return selected.sha256
        if key == "database" and value == "game":
            return database
        if value == old_campaign:
            return campaign
        return value

    return bind, ids, originals


def member_bundle(releases, mode):
    """Rebind valid designed material, timing, and memory leaves to a fresh fixture."""
    from pathlib import Path

    from tools.devtools import national_native_pair as pair
    from tools.devtools import wayne_qualification_storage as storage

    from tests.unit.tools.test_national_storage_qualification import (
        native_join_evidence,
        smoke_evidence,
    )

    profile = "smoke-01"
    run = storage.member_run(profile, mode)
    for path in (run.parent, run, run / "evidence", run / "backup"):
        path.mkdir(exist_ok=True, mode=0o700)
    store = storage.PrivateEvidence(run / "evidence")
    backup = storage.PrivateEvidence(run / "backup")
    base = store.path
    offset = 20 if mode == "normal_play" else 60
    canary = f"{offset:02d}" * 16
    container = canary * 2
    database = "national_" + canary[:12]
    owner = [
        "national-storage-runner-media-v2",
        str(storage.MEDIA_CHECKOUT),
        canary,
        "fixture",
        container,
        str(run / "pgdata"),
        "sha256:" + "ab" * 32,
        database,
        "national_writer_" + canary[:12],
        "123",
        str(base),
        profile,
        "daemon",
        "1",
        str(offset),
        "1000",
        "1000",
        "70",
        "1000",
        "23456",
        str(offset),
    ]
    manifest, playable, timing, memory, _, _, records = native_join_evidence(base)
    shared = (
        Path(__file__).resolve().parents[3] / "contracts/national_storage_qualification_v6.json"
    ).read_bytes()
    selected = store.publish("policy.json", shared)
    owner_ref = store.publish("ownership", ("\n".join(owner) + "\n").encode())
    source = store.publish("source-before.sha256", b"designed source")
    store.publish("source-head", b"a" * 40 + b"\n")
    products = {}
    for name in ("babylon-runtime", "babylon-client", "babylon-material-audit"):
        products[name] = store.publish("normal-" + name, name.encode()).model_dump()
    products_ref = store.publish_json("normal-binaries.json", products)
    if mode == "normal_play":
        cap = releases.publish_json(profile + "-capacity.json", {})
        releases.publish_json(
            profile + "-native-expectations.json",
            {
                "source_head": "a" * 40,
                "capacity": cap.model_dump(),
                "runtime": products["babylon-runtime"],
                "client": products["babylon-client"],
                "material_audit": products["babylon-material-audit"],
            },
        )
    store.publish_json(
        "media-creation.json",
        {
            "profile": profile,
            "run": str(run),
            "source_head": "a" * 40,
            "native_expectations": releases.reference(
                profile + "-native-expectations.json"
            ).model_dump(),
        },
    )
    _, declaration = pair.declaration_for(base, create=True)
    campaign = declaration.campaign
    store.publish("campaign", (campaign + "\n").encode())
    bind, ids, originals = bind_originals(
        manifest["campaign"], campaign, playable, database, selected, offset
    )
    records = bind(records)
    playable = bind(playable)
    for n in (1, 2):
        old = "aid-" + bytes([n] * 32).hex() + ".json"
        fresh = "aid-" + bytes(ids[n]).hex() + ".json"
        original = records.pop(old)
        original["review"]["before"]["aid"] = [
            {"kind": "remote" if n == 1 else "local", "period": n - 1, "recipient_actor_id": 10}
        ]
        records[fresh] = original
        manifest["aid_originals"][n - 1]["name"] = fresh
        (base / old).unlink()
    for artifact in (
        manifest["controls"],
        manifest["opening"],
        *manifest["boundaries"],
        *manifest["advances"],
        *manifest["archives"],
        *manifest["recoveries"],
        *manifest["aid_originals"],
    ):
        name = artifact["name"]
        if name.startswith("advance-"):
            records[name]["material_record_sha256"] = manifest["boundaries"][
                records[name]["committed_tail"]["resolve_tick"] - 1
            ]["sha256"]
        (base / name).write_bytes(wire(records[name]))
        (base / name).chmod(0o600)
        artifact["sha256"] = store.reference(name).sha256
    manifest.update(
        campaign=campaign,
        policy_sha256=selected.sha256,
        ownership_record_sha256=owner_ref.sha256,
        source_manifest_sha256=source.sha256,
        executable_manifest_sha256=products_ref.sha256,
        measurement_mode=mode,
    )
    store.publish_json("native-window-evidence.json", manifest)
    store.publish_json("national-playable-qualification.json", playable)
    store.publish_json("native-timings.json", bind(timing.model_dump(mode="json")))
    _, _, baseline, opening, ticks, reopens = smoke_evidence()
    store.publish_json("schema-baseline.json", bind(baseline))
    store.publish_json("opening-created.json", bind(opening))
    store.publish_json("progress-000-starting.json", {})
    for n in (1, 2):
        store.publish_json(f"tick-{n:02}.json", bind(ticks[n - 1]))
        store.publish_json(f"tick-{n:02}-reopened.json", bind(reopens[n - 1]))
        for stage in ("committed", "archive", "accounting", "production", "reopened"):
            store.publish_json(f"progress-{n:03}-{stage}.json", {})
    store.publish_json(
        "national-capture-mode.json",
        {
            "version": 1,
            "mode": "playable-aid",
            "consumer": "windowed_runtime_session",
            "preset": "national-world",
            "periods": 2,
            "campaign": campaign,
        },
    )
    store.publish_json(
        "physical.json",
        {
            "container": container,
            "label": canary,
            "image": {"id": owner[6]},
            "cluster": str(offset),
            "port": 23456,
            "path": owner[5],
            "name": owner[3],
            "host": {"major": 0, "minor": 1, "inode": offset},
        },
    )
    for name in ("reader-role", "observer-role"):
        store.publish_json(name, {"designed": True})
    role_digests = {
        "native-client": products["babylon-client"]["sha256"],
        "engine-runtime": products["babylon-runtime"]["sha256"],
        "game-postgresql": "ab" * 32,
    }
    boot = memory.boot_id
    store.publish_json("host-native-admission.json", {"boot_id": boot})
    processes = {
        "client": [offset + 1, 10, role_digests["native-client"]],
        "runtime": [offset + 2, 10, role_digests["engine-runtime"]],
        "postgres": [offset + 3, 10, role_digests["game-postgresql"]],
    }
    store.publish_json(
        "processes-smoke.json",
        {
            **processes,
            "owner_sha256": owner_ref.sha256,
            "boot_id": boot,
            "container": container,
            "segment": "smoke",
        },
    )
    store.publish_json(
        "cold-installed-smoke.json",
        {
            "elapsed_ns": 15,
            "started_monotonic_ns": 1,
            "installed_monotonic_ns": 16,
            "ownership_sha256": owner_ref.sha256,
            "source_head": "a" * 40,
            "state": records["native-controls.json"]["actions"][0]["state"],
            "processes": [processes["runtime"], processes["client"]],
        },
    )
    if mode == "memory_capture":
        row = memory.model_dump(mode="json")
        row.update(
            campaign=campaign,
            policy_sha256=selected.sha256,
            ownership_record_sha256=owner_ref.sha256,
        )
        row["source_manifest_sha256"] = store.publish(
            "combined-memory-source.sha256", b"designed source"
        ).sha256
        row["executable_manifest_sha256"] = store.publish_json(
            "combined-memory-executables.json",
            {"version": 1, "roles": {k: [v] for k, v in role_digests.items()}},
        ).sha256
        row["capture_implementation_sha256"] = store.publish(
            "combined-memory-sampler-source.py", b"designed sampler"
        ).sha256
        row["tooling_report_sha256"] = store.publish_json(
            "combined-memory-tooling.json",
            {
                "version": 1,
                "compilation_peak_rss_upper_bound_bytes": None,
                "external_test_tooling_peak_rss_upper_bound_bytes": None,
                "scope": "separate_tooling_not_running_game_compliance",
            },
        ).sha256
        for sample in row["samples"]:
            for proc in sample["processes"]:
                proc["pid"] += offset
                proc["executable_sha256"] = role_digests[proc["role"]]
        store.publish_json("combined-memory.json", row)
    functional = {
        "period": 2,
        "campaign": campaign,
        "database": {"allows_connections": True},
        "organizer_decisions": originals,
        "markers": [{"tick": n, "hash": "ab" * 32} for n in (1, 2)],
    }
    terminal = store.publish_json("functional-terminal.json", functional)
    member = pair.evaluate_member(base)
    completed = store.publish_json("completed-member.json", member.model_dump(mode="json"))
    retired = store.publish_json(
        "retired-container.json",
        {"container": container, "retained_pgdata": {"major": 0, "minor": 1, "inode": offset}},
    )
    retained = [
        backup.publish_json("original-terminal.json", functional),
        backup.publish_json(
            "restored-terminal.json", {**functional, "database": {"allows_connections": False}}
        ),
    ]
    for name in (
        "database.dump",
        "pgdata.tar",
        "pgdata-second.tar",
        "original-probes.json",
        "restored-probes.json",
        "verification-admission.json",
    ):
        retained.append(backup.publish_json(name, {"designed": True}))
    backup.publish_json(
        "recovery-seal.json",
        {
            "completed_member": completed.model_dump(),
            "owner": owner_ref.model_dump(),
            "functional": terminal.model_dump(),
            **{
                key: store.publish_json(key + ".json", {}).model_dump()
                for key in ("shutdown", "fenced_stop", "stop_attempt")
            },
            "retained": [r.model_dump() for r in retained],
        },
    )
    return member, retired


def test_complete_pair_reopens_both_real_evidence_bundles_and_fails_closed(tmp_path, monkeypatch):
    from tools.devtools import national_native_pair as pair
    from tools.devtools import wayne_qualification_storage as storage

    monkeypatch.setattr(storage, "RUN_PARENT", tmp_path)
    releases = storage.PrivateEvidence(tmp_path)
    normal, _ = member_bundle(releases, "normal_play")
    with pytest.raises(FileNotFoundError):
        pair.qualify_pair("smoke-01")
    memory, _ = member_bundle(releases, "memory_capture")
    assert normal.decisions == memory.decisions
    result = pair.qualify_pair("smoke-01")
    assert result["status"] == "qualified" and result["qualification_report_version"] == 8
    declaration = releases.reference("smoke-01/pair-declaration.json")
    for change in (
        {"measurement_mode": "normal_play"},
        {"owner": normal.owner},
        {"processes": normal.processes},
        {"declaration_sha256": "fa" * 32},
        {"native": {**memory.native, "combined_memory_status": "incomplete"}},
    ):
        with pytest.raises(ValueError):
            pair.join_members(declaration, normal, memory.model_copy(update=change))
    base = storage.member_run("smoke-01", "memory_capture") / "evidence"
    for name in (
        "inputs.sha256",
        "source-before.sha256",
        "policy.json",
        "normal-binaries.json",
        "combined-memory.json",
        "native-window-evidence.json",
        "functional-terminal.json",
        "advance-1.json",
        "completed-member.json",
    ):
        path = base / name
        old = path.read_bytes()
        path.write_bytes(b"{}")
        with pytest.raises((ValueError, KeyError)):
            pair.qualify_pair("smoke-01")
        path.write_bytes(old)


def test_captured_phase_elapsed_is_diagnostic_and_normal_open_enforces_its_limit(tmp_path):
    from tests.unit.tools.test_national_storage_qualification import (
        native_join_evidence,
        native_join_result,
    )

    manifest, playable, timing, memory, opening, ticks, records = native_join_evidence(tmp_path)
    record = records["material-0.json"]
    timing_data = timing.model_dump(mode="json")
    timing_data["run"]["elapsed_ns"] = 182 * 10**9
    timing = type(timing).model_validate(timing_data)
    manifest["completed_monotonic_ns"] = manifest["started_monotonic_ns"] + timing.run.elapsed_ns
    record["production_read_elapsed_ns"] = 181 * 10**9
    raw = wire(record)
    (tmp_path / "material-0.json").write_bytes(raw)
    manifest["opening"]["sha256"] = hashlib.sha256(raw).hexdigest()
    captured = native_join_result(tmp_path, manifest, playable, timing, memory, opening, ticks)
    assert (
        captured["status"] == "qualified"
        and captured["native_read_and_reopen_budgets_passed"] is None
    )
    normal = native_join_result(
        tmp_path,
        {**manifest, "measurement_mode": "normal_play"},
        playable,
        timing,
        None,
        opening,
        ticks,
    )
    assert normal["status"] == "failed" and normal["native_read_and_reopen_budgets_passed"] is False
