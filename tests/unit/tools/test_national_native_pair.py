"""Designed command custody for serial native measurement members."""

import hashlib
import io
import json
import os
import re
import struct
import subprocess
import tarfile
from functools import cache
from pathlib import Path
from uuid import UUID

import pytest
from tools.devtools.national_windowed_qualification import Commitment

CAMPAIGN = "d32bc4bc-d21f-4052-973f-f971a75092cb"
MARKER = "98" * 32


def wire(value):
    return json.dumps(value, separators=(",", ":")).encode()


def receipt_fields(choice):
    return {
        "standing_work": False,
        "outcome": "standing_paused" if choice == "pause_standing" else "aid_scheduled",
        "hours_spent": 0,
        "partner_response": "not_requested",
        "observation_ids": [],
        "contact_product_id": None,
        "time_use": [],
    }


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
        **receipt_fields("remote_aid"),
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


def bind_originals(old_campaign, campaign, records, database, selected, offset, markers):
    ids = {}
    originals = []
    for n in (1, 2):
        accepted = [
            a["state"]["commitment"]
            for a in records["native-controls.json"]["actions"]
            if a["action"] == "confirm"
        ][n - 1]
        command = dict(
            accepted["command"],
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
            **receipt_fields(command["choice"]),
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
                "marker": markers[n - 1]["hash"],
                "receipt_id": rid.hex(),
                "receipt_hex": wire(receipt).hex(),
            }
        )

    def bind(value, key=None, period=None):
        if isinstance(value, dict):
            period = next(
                (
                    value[k]
                    for k in (
                        "durable_tick",
                        "resolve_tick",
                        "tick",
                        "period",
                        "campaign_age_ticks",
                        "through_period",
                    )
                    if k in value
                ),
                period,
            )
            if "review" in value and "commitment" in value:
                period = value["commitment"]["command"]["expected_period"]
            return {k: bind(v, k, period) for k, v in value.items()}
        marker_fields = {
            "tick_content_hash": "hash",
            "captured_tail_tick_content_hash": "hash",
            "through_tick_content_hash": "hash",
            "canonical_receipt_sha256": "receipt",
            "world_hash": "world_after",
            "nominal_world_hash": "world_after",
            "envelope_digest": "envelope",
        }
        if key in marker_fields and value is not None:
            return markers[period - 1][marker_fields[key]]
        if isinstance(value, list):
            if key == "latest_marker":
                marker = markers[value[0] - 1]
                return [value[0], marker["hash"], marker["envelope"]]
            if key == "marker_and_encoded_package_hashes":
                return [
                    [n, markers[n - 1]["hash"], markers[n - 1]["envelope"], *rest]
                    for n, _, _, *rest in value
                ]
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
            return [bind(v, key, period) for v in value]
        if key == "policy_sha256":
            return selected.sha256
        if key == "database" and value == "game":
            return database
        if value == old_campaign:
            return campaign
        return value

    return bind, ids, originals


REPO = Path(__file__).resolve().parents[3]


@cache
def release_manifests():
    def manifest(function):
        return subprocess.run(
            [
                "bash",
                "-euo",
                "pipefail",
                "-c",
                f"source tools/postgres_national_lifecycle.sh; {function}",
            ],
            cwd=REPO,
            env={**os.environ, "REPO_ROOT": str(REPO)},
            capture_output=True,
            check=True,
        ).stdout

    return manifest("national_source_manifest"), manifest("national_input_manifest")


@cache
def capsule_bytes(manifest, excluded, altered):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz", compresslevel=1) as tar:
        for line in manifest.splitlines():
            _, name = line.decode().split("  ", 1)
            if name in excluded:
                continue
            raw = b"substituted input" if altered else (REPO / name).read_bytes()
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            tar.addfile(info, io.BytesIO(raw))
    return stream.getvalue()


def source_capsules(store, defect):
    source_manifest, input_manifest = release_manifests()
    if defect in ("omitted-crate-source", "omitted-preset-input"):
        remove = (
            b"rust/crates/babylon-client/Cargo.toml"
            if defect == "omitted-crate-source"
            else input_manifest.splitlines()[0].split(b"  ")[1]
        )
        source_manifest, input_manifest = (
            b"".join(
                line
                for line in data.splitlines(keepends=True)
                if not line.endswith(b"  " + remove + b"\n")
            )
            for data in (source_manifest, input_manifest)
        )
    (store.path / "inputs.sha256").write_bytes(input_manifest)
    ref = store.publish("source-before.sha256", source_manifest)
    excluded = frozenset(line.decode().split("  ")[1] for line in input_manifest.splitlines())
    for kind, prefix, manifest, omit in (
        ("source", "source", source_manifest, excluded),
        ("input", "inputs", input_manifest, frozenset()),
    ):
        name = f"{prefix}-{hashlib.sha256(manifest).hexdigest()}.tar.gz"
        capsule = store.publish(
            name,
            capsule_bytes(manifest, omit, kind == "input" and defect == "altered-input-content"),
        )
        checksum = f"{capsule.sha256}  {store.path / name}\n".encode()
        store.publish(name + ".sha256", checksum)
        store.publish(kind + "-archive.sha256", checksum)
        store.publish(kind + "-archive-bytes", f"{capsule.bytes}\n".encode())
    return ref


def terminal_markers():
    from tools.devtools.wayne_qualification_backup import _markers

    h = "ab" * 32

    def digest(kind, tick):
        return hashlib.sha256(f"{kind}-{tick}".encode()).digest()

    rows = []
    for tick in (1, 2):
        identity = (
            b"babylon.material-tick-content.v3\0"
            + struct.pack(">IQ", 3, tick)
            + bytes.fromhex(h)
            + digest("graph-tick", tick)
            + digest("graph-world", tick - 1)
            + digest("graph-world", tick)
            + digest("world", tick - 1)
            + digest("world", tick)
            + digest("receipt", tick)
        )
        rows.append(
            (
                tick,
                hashlib.sha256(identity).hexdigest(),
                digest("envelope", tick).hex(),
                identity.hex(),
                digest("checkpoint", tick).hex(),
            )
        )
    return _markers(rows, 2, h)


def functional_snapshot(campaign, owner, originals, markers):
    from tools.devtools.wayne_qualification_backup import REQUIRED_ROWS

    h = "ab" * 32
    schemas = ["babylon_meta", "babylon_ref", "babylon_state", "public"]
    authority = [["schema", ns, "", owner, owner, owner, "USAGE", False] for ns in schemas]
    crate = REPO / "rust/crates/babylon-persistence"
    census = (crate / "src/fixtures/current_schema_census.txt").read_text().splitlines()
    for line in census:
        kind, ns, ident, *_ = line.split("|") if not line.startswith("#") else ("", "", "")
        if kind in ("relation", "view"):
            authority.append(
                [
                    "r" if kind == "relation" else "v",
                    ns,
                    ident,
                    owner,
                    owner,
                    owner,
                    "SELECT",
                    False,
                ]
            )
    for view, role in (
        ("v_observer_material_foundation_v1", "babylon_observer"),
        ("v_observer_material_state_v1", "babylon_observer"),
        ("v_archive_revision_known_v2", "babylon_reader"),
    ):
        authority.append(["v", "public", view, owner, owner, role, "SELECT", False])
    tables = set()
    for name in ("current_schema.sql", "current_archive.sql"):
        ddl = (crate / "migrations" / name).read_text()
        for table, body in re.findall(r"CREATE TABLE ([a-z0-9_.]+) \((.*?)\n\)", ddl, flags=re.S):
            if re.search(r"^ +campaign_id ", body, flags=re.M):
                tables.add(table)
    assert tables >= REQUIRED_ROWS
    rows = {table: [] for table in sorted(tables)}
    for table in REQUIRED_ROWS | {"babylon_meta.archive_receipt_consumption_v1"}:
        count = (
            1
            if table.endswith(
                (".campaign", ".campaign_foundation", ".material_campaign_foundation_v3")
            )
            else len(markers)
        )
        rows[table] = sorted(
            hashlib.sha256(f"{table}:{n}".encode()).hexdigest() for n in range(count)
        )
    # Hash designed rows of the same five SQL columns in JSONB key order.
    subjects = [
        ("workplace", "31", "Wayne workplace"),
        ("organization", "1", "Wayne Organizing Collective"),
        ("organization", "10", "Wayne Workplace Committee"),
        ("organization", "11", "Wayne Neighborhood Contact Group"),
        ("organization", "12", "Wayne Local Aid Partners"),
        ("organization", "17", "Cook Independent Solidarity Partners"),
    ]
    rows["babylon_state.organizer_subject_v1"] = sorted(
        hashlib.sha256(
            json.dumps(
                {
                    "title": title,
                    "actor_id": "1",
                    "subject_id": subject_id,
                    "campaign_id": campaign,
                    "subject_kind": kind,
                }
            ).encode()
        ).hexdigest()
        for kind, subject_id, title in subjects
    )
    return {
        "campaign": campaign,
        "period": len(markers),
        "identity": [campaign, "national-world", h, h, "cd" * 32, h, h, h, h],
        "markers": markers,
        "organizer_decisions": originals,
        "campaign_rows_sha256": rows,
        "object_authority": authority,
        "database": {
            "owner": owner,
            "encoding": "UTF8",
            "collate": "C",
            "ctype": "C",
            "provider": "b",
            "locale": "C.UTF-8",
            "icu_rules": None,
            "allows_connections": True,
            "connection_limit": -1,
            "acl_default": False,
            "acl": [[owner, owner, "CONNECT", False]],
            "settings": [],
        },
        "archive_terminal": {
            "terminal_marker": markers[-1]["hash"],
            "watermark": len(markers),
            "pending": 0,
            "receipts": [
                {"tick": m["tick"], "marker": m["hash"], "batch": h, "worker": h, "knowledge": h}
                for m in markers
            ],
        },
    }


def bind_dated_decisions(store, records, originals, manifest, timing, defect):
    from tests.unit.tools.test_national_windowed_qualification import installed_opening_view

    records["native-controls.json"]["actions"][0]["state"]["installed_organizer"] = (
        installed_opening_view()
    )
    for n in (1, 2):
        store.publish_json(f"resolved-decisions-{n}.json", originals[:n])
    if defect == "early-loading":
        actions = records["native-controls.json"]["actions"]
        early = {**actions[0], "state": {**actions[0]["state"], "phase": "Loading"}}
        for a in actions:
            a["sequence"] += 1
            for key in ("started_monotonic_ns", "completed_monotonic_ns"):
                a[key] += 181 * 10**9
        actions.insert(0, early)
        manifest["completed_monotonic_ns"] += 181 * 10**9
        clock = timing.model_dump(mode="json")
        clock["run"]["elapsed_ns"] += 181 * 10**9
        timing = type(timing).model_validate(clock)
    if defect in ("truncated-receipt", "changed-receipt"):
        raw = json.loads(bytes.fromhex(originals[0]["receipt_hex"]))
        if defect == "truncated-receipt":
            del raw["hours_spent"]
        else:
            raw["hours_spent"] += 1
        originals[0]["receipt_hex"] = wire(raw).hex()
    return timing


def rebind_period_proofs(store, records, manifest):
    for action in records["native-controls.json"]["actions"]:
        if proof := action["state"]["period_proof"]:
            proof["material_record_sha256"] = manifest["boundaries"][proof["tick"] - 1]["sha256"]
    (store.path / "native-controls.json").write_bytes(wire(records["native-controls.json"]))
    manifest["controls"]["sha256"] = store.reference("native-controls.json").sha256


def member_bundle(releases, mode, *, defect=None, retire=True):
    """Rebind valid designed material, timing, and memory leaves to a fresh fixture."""
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
        "551",
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
    manifest, playable, timing, memory, _, _, records = native_join_evidence(
        base, named_smoke=defect != "wrong-decisions"
    )
    shared = (
        Path(__file__).resolve().parents[3] / "contracts/national_storage_qualification_v6.json"
    ).read_bytes()
    selected = store.publish("policy.json", shared)
    if defect == "different-image" and mode == "memory_capture":
        owner[6] = "sha256:" + "fe" * 32
    owner_ref = store.publish("ownership", ("\n".join(owner) + "\n").encode())
    source = source_capsules(store, defect)
    manifest["inputs_sha256"] = store.reference("inputs.sha256").sha256
    store.publish("source-head", b"a" * 40 + b"\n")
    products = {}
    for name in ("babylon-runtime", "babylon-client", "babylon-material-audit"):
        products[name] = store.publish("normal-" + name, name.encode()).model_dump()
    products_ref = store.publish_json("normal-binaries.json", products)
    host = {
        "tag": "wayne-host-process-context-v2",
        "mount_namespace": "mnt:[421]",
        "init_start_ticks": 1,
        "init_comm": "systemd",
        "boot_id": memory.boot_id,
        "pid_namespace": "pid:[431]",
        "proc_mount_id": 42,
        "operator_uid": 1000,
    }
    image = {
        "id": owner[6],
        "entrypoint": ["docker-entrypoint.sh"],
        "os": "linux",
        "architecture": "amd64",
        "repo_digests": [],
    }
    if mode == "normal_play":
        released_host = releases.publish_json("host-process-context.json", host)
        released_source, released_inputs = release_manifests()
        cap = releases.publish_json(
            profile + "-capacity.json",
            {
                "tag": "wayne-disk-reservation-v1",
                "profile": profile,
                "source_head": "a" * 40,
                "build_bytes": 0,
                "primary_bytes": 1,
                "evidence_bytes": 1,
                "restore_bytes": 1,
                "dump_bytes": 1,
                "archive_bytes": 1,
                "measured_basis": "designed capacity",
            },
        )
        releases.publish_json(
            profile + "-native-expectations.json",
            {
                "source_head": "a" * 40,
                "capacity": cap.model_dump(),
                "source_sha256": hashlib.sha256(released_source).hexdigest(),
                "inputs_sha256": hashlib.sha256(released_inputs).hexdigest(),
                "image_id": image["id"],
                "host_context_sha256": released_host.sha256,
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
            "image": image,
            "reservation": releases.reference(profile + "-capacity.json").model_dump(),
            "capacity": json.loads((releases.path / (profile + "-capacity.json")).read_bytes()),
            "native_expectations": releases.reference(
                profile + "-native-expectations.json"
            ).model_dump(),
        },
    )
    _, declaration = pair.declaration_for(base, create=True)
    campaign = declaration.campaign
    store.publish("campaign", (campaign + "\n").encode())
    markers = terminal_markers()
    bind, ids, originals = bind_originals(
        manifest["campaign"], campaign, records, database, selected, offset, markers
    )
    records = bind(records)
    playable = bind(playable)
    for n in range(1, len(manifest["aid_originals"]) + 1):
        old = "aid-" + bytes([n] * 32).hex() + ".json"
        fresh = "aid-" + bytes(ids[n]).hex() + ".json"
        original = records.pop(old)
        original["review"]["before"]["aid"] = [
            {"kind": "remote" if n == 1 else "local", "period": n - 1, "recipient_actor_id": 10}
        ]
        records[fresh] = original
        manifest["aid_originals"][n - 1]["name"] = fresh
        (base / old).unlink()
    timing = bind_dated_decisions(store, records, originals, manifest, timing, defect)
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
    rebind_period_proofs(store, records, manifest)
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
    from tools.devtools.wayne_qualification_backup import Run

    from tests.unit.tools.test_wayne_qualification_backup import fixture as physical_fixture
    from tests.unit.tools.test_wayne_qualification_backup import retained_pair_recovery

    _, witness = physical_fixture()
    physical = {
        k: v
        for k, v in witness.physical.items()
        if k not in ("source_checkpoint", "relation_sizes", "relation_page_occupancy", "pgss")
    }
    physical.update(
        {
            "container": container,
            "label": canary,
            "image": image,
            "cluster": str(offset),
            "port": 23456,
            "path": owner[5],
            "name": owner[3],
            "host": {**physical["host"], "major": 0, "minor": 1, "inode": offset},
            "pid": offset + 3,
            "mounts": [],
            "port_request": {},
            "container_root": {**physical["container_root"], "major": 0, "minor": 1},
            "lineage": "reviewed lineage\n",
            "pg_version": "17\n",
            "max_connections": 50,
            "max_wal_senders": 0,
        }
    )
    store.publish_json("physical.json", physical)
    for name in ("reader-role", "observer-role"):
        store.publish_json(name, {"designed": True})
    role_digests = {
        "native-client": products["babylon-client"]["sha256"],
        "engine-runtime": products["babylon-runtime"]["sha256"],
        "game-postgresql": "ab" * 32,
    }
    boot = memory.boot_id
    store.publish_json("host-native-admission.json", host)
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
        "native-cold-clock.json",
        pair.ColdControlWindow(1, 180 if mode == "normal_play" else 900).clock_record(),
    )
    store.publish_json(
        "cold-installed-smoke.json",
        {
            "elapsed_ns": 15,
            "started_monotonic_ns": 1,
            "installed_monotonic_ns": 16,
            "readiness_sequence": 1,
            "ownership_sha256": owner_ref.sha256,
            "source_head": "a" * 40,
            "state": records["native-controls.json"]["actions"][0]["state"],
            "processes": [processes["runtime"], processes["client"]],
        },
    )
    if mode == "memory_capture":
        row = bind(memory.model_dump(mode="json"))
        row.update(
            campaign=campaign,
            policy_sha256=selected.sha256,
            ownership_record_sha256=owner_ref.sha256,
        )
        row["source_manifest_sha256"] = store.publish(
            "combined-memory-source.sha256", store.read_reference(source)
        ).sha256
        row["executable_manifest_sha256"] = store.publish_json(
            "combined-memory-executables.json",
            {"version": 1, "roles": {k: [v] for k, v in role_digests.items()}},
        ).sha256
        row["capture_implementation_sha256"] = store.publish(
            "combined-memory-sampler-source.py",
            b"different sampler"
            if defect == "spoofed-sampler"
            else (REPO / "tools/devtools/national_game_memory.py").read_bytes(),
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
    functional = functional_snapshot(campaign, owner[8], originals, markers)
    store.publish_json("functional-terminal.json", functional)
    member = pair.evaluate_member(base)
    store.publish_json("completed-member.json", member.model_dump(mode="json"))
    if not retire:
        return member, None
    retired = store.publish_json(
        "retired-container.json",
        {"container": container, "retained_pgdata": {"major": 0, "minor": 1, "inode": offset}},
    )
    retained_pair_recovery(
        Run(storage.MEDIA_CHECKOUT, base, tuple(owner), campaign, 2),
        store,
        backup,
        physical,
        functional,
    )
    return member, retired


def check_recovery_substitution(pair, storage):
    run = storage.member_run("smoke-01", "normal_play")
    b = storage.PrivateEvidence(run / "backup")
    e = storage.PrivateEvidence(run / "evidence")
    seal_path = b.path / "recovery-seal.json"
    saved = seal_path.read_bytes()
    for name, field, replacement, reason in (
        ("verification-identity.json", "name", "other", "verification database"),
        (
            "pgdata-second.tar.manifest.json",
            "root_and_source",
            e.reference("ownership").model_dump(),
            "independent offline archive",
        ),
        ("fenced-client-exits.json", "expected", [], "held-client exits"),
    ):
        path = b.path / name
        old = path.read_bytes()
        path.write_bytes(wire({**json.loads(old), field: replacement}))
        packet = json.loads(saved)
        packet["retained"] = [
            b.reference(name).model_dump() if r["path"] == name else r for r in packet["retained"]
        ]
        seal_path.write_bytes(wire(packet))
        with pytest.raises(ValueError, match=reason):
            pair.qualify_pair("smoke-01")
        path.write_bytes(old)
    packet = json.loads(saved)
    packet["shutdown"] = e.reference("ownership").model_dump()
    seal_path.write_bytes(wire(packet))
    with pytest.raises(ValueError, match="canonical stop evidence"):
        pair.qualify_pair("smoke-01")
    seal_path.write_bytes(saved)


def test_complete_pair_reopens_both_real_evidence_bundles_and_fails_closed(tmp_path, monkeypatch):
    from tools.devtools import national_native_pair as pair
    from tools.devtools import wayne_qualification_storage as storage

    monkeypatch.setattr(storage, "MEDIA_CHECKOUT", REPO)
    monkeypatch.setattr(storage, "RUN_PARENT", tmp_path)
    releases = storage.PrivateEvidence(tmp_path)
    normal, _ = member_bundle(releases, "normal_play")
    release = releases.reference("smoke-01-native-expectations.json")
    packet = json.loads(releases.read_reference(release))
    monkeypatch.setenv("BABYLON_WAYNE_NATIVE_EXPECTATION_REF", release.model_dump_json())
    monkeypatch.setenv("BABYLON_POSTGRES_IMAGE_ID", packet["image_id"])
    monkeypatch.setenv("BABYLON_WAYNE_HOST_CONTEXT_SHA256", packet["host_context_sha256"])
    monkeypatch.setattr(
        storage, "exact_output", lambda args: packet["source_head"] if "HEAD" in args else ""
    )
    monkeypatch.setattr(storage, "held_native_lock", lambda _: tmp_path / "lease")
    normal_run = storage.member_run("smoke-01", "normal_play")
    memory_run = storage.member_run("smoke-01", "memory_capture")
    first_bytes = (normal_run / "evidence/completed-member.json").read_bytes()
    first_uuid = (normal_run / "evidence/campaign").read_bytes()
    assert pair.operator_next("smoke-01") == "memory_capture"
    assert not memory_run.exists()
    assert (normal_run / "evidence/completed-member.json").read_bytes() == first_bytes
    assert (normal_run / "evidence/campaign").read_bytes() == first_uuid
    (normal_run / "evidence/failure-summary.json").touch()
    with pytest.raises(ValueError, match="failed native owner"):
        pair.operator_next("smoke-01")
    (normal_run / "evidence/failure-summary.json").unlink()
    memory_run.mkdir(mode=0o700)
    with pytest.raises(FileNotFoundError):
        pair.operator_next("smoke-01")
    assert not any(memory_run.iterdir())
    memory_run.rmdir()
    with pytest.raises(FileNotFoundError):
        pair.qualify_pair("smoke-01")
    memory, _ = member_bundle(releases, "memory_capture")
    assert normal.decisions == memory.decisions
    result = pair.qualify_pair("smoke-01")
    assert result["status"] == "qualified" and result["qualification_report_version"] == 8
    assert pair.operator_next("smoke-01") == "complete"
    published = normal_run.parent / "qualification.json"
    valid = published.read_bytes()
    for nested in (False, True):
        wrong = json.loads(valid)
        if nested:
            wrong["native_pair"]["version"] = True
        else:
            wrong["qualification_report_version"] = 8.0
        published.write_bytes(wire(wrong))
        with pytest.raises(ValueError, match="published qualification differs"):
            pair.publish_pair("smoke-01")
        assert published.read_bytes() == wire(wrong)
    published.write_bytes(valid)
    check_recovery_substitution(pair, storage)
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


@pytest.mark.parametrize(
    ("defect", "reason"),
    [
        ("wrong-decisions", "released smoke workload"),
        ("omitted-crate-source", "member release differs"),
        ("omitted-preset-input", "member release differs"),
        ("different-image", "member release differs"),
        ("partial-recovery", "complete restore and physical archive roster"),
        ("missing-capsule", "source-"),
        ("altered-input-content", "content differs from its frozen manifest"),
        ("spoofed-sampler", "sampler implementation differs from admitted source"),
        ("truncated-receipt", "hours_spent"),
        ("changed-receipt", "differs from the independently retained dated original"),
        ("early-loading", "process-cold installation differs"),
    ],
)
def test_final_pair_refuses_review_defects(tmp_path, monkeypatch, defect, reason):
    from tools.devtools import national_native_pair as pair
    from tools.devtools import wayne_qualification_storage as storage

    monkeypatch.setattr(storage, "RUN_PARENT", tmp_path)
    releases = storage.PrivateEvidence(tmp_path)
    if defect == "wrong-decisions":
        # Model two completed legacy fixtures that agreed on the wrong second command.
        # Final qualification below uses the actual current workload and both sealed packets.
        with monkeypatch.context() as legacy:
            remote, _pause = pair.SMOKE_DECISIONS
            local = pair.PlannedChoice(period=2, choice="local_aid", allocation=remote.allocation)
            legacy.setattr(pair, "SMOKE_DECISIONS", (remote, local))
            one, _ = member_bundle(releases, "normal_play", defect=defect)
            two, _ = member_bundle(releases, "memory_capture", defect=defect)
            assert one.decisions == two.decisions
        with pytest.raises(ValueError, match=reason):
            pair.qualify_pair("smoke-01")
        return
    with pytest.raises((ValueError, FileNotFoundError), match=reason):
        member_bundle(releases, "normal_play", defect=defect)
        member_bundle(
            releases,
            "memory_capture",
            defect=defect if defect in ("spoofed-sampler", "different-image") else None,
        )
        run = storage.member_run("smoke-01", "normal_play")
        if defect == "missing-capsule":
            for capsule in (run / "evidence").glob("source-*.tar.gz"):
                capsule.unlink()
        if defect == "partial-recovery":
            seal = run / "backup/recovery-seal.json"
            packet = json.loads(seal.read_bytes())
            packet["retained"] = [
                r for r in packet["retained"] if r["path"] != "pre-stop-physical.json"
            ]
            seal.write_bytes(wire(packet))
        pair.qualify_pair("smoke-01")


@pytest.mark.parametrize(
    "field",
    [
        "cold-clock",
        "postmaster",
        "functional-terminal",
        "shifted-start",
        "host-only-boot",
        "duplicate-process",
        "malformed-marker",
        "broken-world",
        "missing-authority",
        "pending-archive",
    ],
)
def test_member_rejects_unanchored_measurements(tmp_path, monkeypatch, field):
    from tools.devtools import national_native_pair as pair
    from tools.devtools import wayne_qualification_storage as storage

    monkeypatch.setattr(storage, "RUN_PARENT", tmp_path)
    member_bundle(storage.PrivateEvidence(tmp_path), "normal_play", retire=False)
    base = storage.member_run("smoke-01", "normal_play") / "evidence"
    if field == "cold-clock":
        (base / "native-cold-clock.json").unlink(missing_ok=True)
    elif field == "postmaster":
        path = base / "processes-smoke.json"
        row = json.loads(path.read_bytes())
        row["postgres"][0] += 41
        path.write_bytes(wire(row))
    elif field == "shifted-start":
        path = base / "cold-installed-smoke.json"
        row = json.loads(path.read_bytes())
        row["started_monotonic_ns"] += 1
        row["elapsed_ns"] -= 1
        path.write_bytes(wire(row))
    elif field == "host-only-boot":
        path = base / "host-native-admission.json"
        path.write_bytes(wire({"boot_id": json.loads(path.read_bytes())["boot_id"]}))
    elif field == "duplicate-process":
        path = base / "processes-smoke.json"
        row = json.loads(path.read_bytes())
        row["client"][0] = row["postgres"][0]
        path.write_bytes(wire(row))
        cold = base / "cold-installed-smoke.json"
        receipt = json.loads(cold.read_bytes())
        receipt["processes"][1] = row["client"]
        cold.write_bytes(wire(receipt))
    elif field in ("broken-world", "malformed-marker", "missing-authority", "pending-archive"):
        path = base / "functional-terminal.json"
        row = json.loads(path.read_bytes())
        if field == "broken-world":
            row["markers"][1]["world_after"] = "ce" * 32
        elif field == "malformed-marker":
            row["markers"][1]["identity"] = "0a" * 256
        elif field == "missing-authority":
            row["object_authority"] = []
        else:
            row["archive_terminal"]["pending"] = 1
        path.write_bytes(wire(row))
    elif field == "functional-terminal":
        path = base / "functional-terminal.json"
        row = json.loads(path.read_bytes())
        row.pop("archive_terminal", None)
        path.write_bytes(wire(row))
    with pytest.raises((ValueError, FileNotFoundError)):
        pair.evaluate_member(base)


@pytest.mark.parametrize("segment", ["opening", "walk", "completed", "smoke"])
@pytest.mark.parametrize("mode", ["normal_play", "memory_capture"])
def test_each_cold_segment_uses_its_actual_clock_and_terminal_archive_span(tmp_path, segment, mode):
    from tools.devtools import national_native_pair as pair
    from tools.devtools.national_windowed_qualification import ActionObservation
    from tools.devtools.wayne_qualification_storage import PrivateEvidence

    from tests.unit.tools.test_national_storage_qualification import policy

    store = PrivateEvidence(tmp_path)
    folder = tmp_path / ("segment-" + segment) if segment in ("opening", "completed") else tmp_path
    folder.mkdir(exist_ok=True, mode=0o700)
    clock = pair.ColdControlWindow(17, 180 if mode == "normal_play" else 900)
    receipt = pair.ColdInstallation.model_construct(
        started_monotonic_ns=17, installed_monotonic_ns=37, readiness_sequence=3
    )
    controls = pair.ControlsEvidence.model_construct(actions=())

    def action(name, sequence, start, finish, event="applied"):
        from tools.devtools.national_windowed_qualification import ControlState

        return ActionObservation.model_construct(
            sequence=sequence,
            action=name,
            started_monotonic_ns=start,
            completed_monotonic_ns=finish,
            event=event,
            reason="control_stale_or_unavailable" if event == "refused" else None,
            state=ControlState.model_construct(durable_tick=10),
        )

    second = 10**9
    navigation = (
        action("archive_report", 4, second, 2 * second),
        action("open_archive_evidence", 5, 50 * second, 51 * second, "refused"),
        action("open_archive_evidence", 6, 96 * second, 97 * second, "refused"),
        action("open_archive_evidence", 7, 140 * second, 141 * second),
        action("open_organizer", 8, 150 * second, 151 * second),
    )
    if segment == "walk":
        controls = controls.model_copy(update={"actions": navigation})
    with pytest.raises(FileNotFoundError):
        pair.verify_segment_timing(store, segment, mode, policy(), receipt, controls)
    clock_path = PrivateEvidence(folder).publish_json(
        "native-cold-clock.json", clock.clock_record()
    )
    assert pair.verify_segment_timing(store, segment, mode, policy(), receipt, controls) == str(
        (folder / clock_path.path).relative_to(tmp_path)
    )
    if segment == "smoke":
        proof = controls.model_copy(
            update={
                "actions": (
                    action("await_period_proof", 4, second, 121 * second, "period_proof_published"),
                )
            }
        )
        pair.verify_segment_timing(store, segment, mode, policy(), receipt, proof)
        too_long = controls.model_copy(
            update={
                "actions": (
                    action("await_period_proof", 4, second, 902 * second, "period_proof_published"),
                )
            }
        )
        with pytest.raises(ValueError, match="ceiling"):
            pair.verify_segment_timing(store, segment, mode, policy(), receipt, too_long)
    for changed in (
        pair.ColdControlWindow(16, clock.maximum_seconds),
        pair.ColdControlWindow(17, clock.maximum_seconds + 1),
    ):
        (folder / clock_path.path).write_bytes(wire(changed.clock_record()))
        with pytest.raises(ValueError, match="prelaunch clock"):
            pair.verify_segment_timing(store, segment, mode, policy(), receipt, controls)
    if segment == "walk":
        (folder / clock_path.path).write_bytes(wire(clock.clock_record()))
        for late in (
            (
                *navigation[:3],
                action("open_archive_evidence", 7, 182 * second, 183 * second),
                action("open_organizer", 8, 190 * second, 191 * second),
            ),
            (*navigation[:4], action("open_organizer", 8, 150 * second, 211 * second)),
        ):
            trace = controls.model_copy(update={"actions": late})
            if mode == "normal_play":
                with pytest.raises(ValueError, match="ceiling|total deadline"):
                    pair.verify_segment_timing(store, segment, mode, policy(), receipt, trace)
            else:
                pair.verify_segment_timing(store, segment, mode, policy(), receipt, trace)
