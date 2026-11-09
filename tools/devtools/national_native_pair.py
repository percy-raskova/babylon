"""Admit, retain, and join independently owned native timing and memory runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

import psycopg
from pydantic import Field, StrictStr, TypeAdapter, model_validator
from tools.devtools import wayne_qualification_storage as storage
from tools.devtools.national_native_evidence import (
    CONTROLS_RECORD_BYTES,
    MANIFEST_BYTES,
    MATERIAL_RECORD_BYTES,
    AidOriginal,
    ColdInstallation,
    NativeRecord,
    NativeRunEvidence,
    _artifact,
    evaluate_native,
    evaluate_wayne_walk,
)
from tools.devtools.national_storage_qualification import (
    CombinedMemoryEvidence,
    FixedPeriodMemory,
    MeasurementMode,
    NativeTimings,
    Nonnegative,
    PlayableReport,
    Policy,
    Positive,
    Sha256,
    Snapshot,
    authenticate_combined_memory_capture,
    evaluate,
    evaluate_playable,
    evaluate_smoke,
    evaluate_timings,
    measurement_mode,
    selected_policy,
    strict_json_bytes,
)
from tools.devtools.national_windowed_qualification import (
    Bytes16,
    Bytes32,
    Command,
    Commitment,
    ControlsEvidence,
    SelectedAllocation,
)
from tools.devtools.wayne_qualification_storage import PrivateEvidence, Reference

Workload = Literal["smoke-01", "walk-01"]
Process = tuple[Positive, Nonnegative, Sha256]
MODES: tuple[MeasurementMode, MeasurementMode] = ("normal_play", "memory_capture")


class Declaration(NativeRecord):
    version: Literal[1]
    workload: Workload
    campaign: StrictStr
    periods: Positive
    source_head: Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{40}$")]
    source_sha256: Sha256
    inputs_sha256: Sha256
    policy_sha256: Sha256
    release: Reference


class ProcessPair(NativeRecord):
    segment: Literal["smoke", "opening", "walk", "completed"]
    boot_id: StrictStr
    runtime: Process
    client: Process
    postgres: Process
    container: Sha256
    owner_sha256: Sha256


class OriginalDecision(NativeRecord):
    period: Positive
    consumed: Positive
    nonce: StrictStr
    command_hex: StrictStr
    commitment_hex: StrictStr
    commitment_id: Sha256
    marker: Sha256
    receipt_id: Sha256
    receipt_hex: StrictStr


class Decision(SelectedAllocation):
    period: Positive
    actor: Positive
    authority: Bytes16
    partner: Nonnegative | None
    recipient: Nonnegative | None


class CompletedMember(NativeRecord):
    version: Literal[1]
    scope: Literal["completed_native_member_for_restore_and_retirement"]
    measurement_mode: MeasurementMode
    declaration_sha256: Sha256
    evidence: tuple[Reference, ...]
    owner: Sha256
    container: Sha256
    database: StrictStr
    cluster: StrictStr
    pgdata: tuple[Nonnegative, Positive]
    processes: tuple[ProcessPair, ...]
    decisions: tuple[Decision, ...]
    foundation: Sha256
    graph_foundation: Sha256
    native: dict[str, Any]
    walk: dict[str, Any] | None


class RetiredMember(NativeRecord):
    measurement_mode: MeasurementMode
    completed: Reference
    recovery: Reference
    retirement: Reference


class NativePairEvidence(NativeRecord):
    version: Literal[1]
    scope: Literal["native_timing_and_memory_pair_v1"]
    declaration: Reference
    normal_play: RetiredMember
    memory_capture: RetiredMember

    @model_validator(mode="after")
    def exact_members(self) -> NativePairEvidence:
        if (
            self.declaration.path != "pair-declaration.json"
            or (self.normal_play.measurement_mode, self.memory_capture.measurement_mode) != MODES
        ):
            raise ValueError("native pair declaration or measurement purpose differs")
        for member in (self.normal_play, self.memory_capture):
            if (member.completed.path, member.recovery.path, member.retirement.path) != (
                "completed-member.json",
                "recovery-seal.json",
                "retired-container.json",
            ):
                raise ValueError("native pair references a substituted member bundle")
        if self.normal_play.completed.sha256 == self.memory_capture.completed.sha256:
            raise ValueError("native pair repeats its completed member")
        return self


def _json(store: PrivateEvidence, name: str, maximum: int = MANIFEST_BYTES) -> Any:
    return strict_json_bytes(store.read_reference(store.reference(name), maximum))


def _receipt_id(command: Command, period: int, cid: bytes) -> bytes:
    parts = [list(command.campaign_id), command.actor_id, period, list(cid)]
    raw = json.dumps(parts, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(b"babylon.organizer-receipt.v1\0" + raw).digest()


def terminal_decisions(
    connection: psycopg.Connection[Any], campaign: str
) -> list[dict[str, object]]:
    """The terminal repeatable-read snapshot includes actual bytes under each committed marker."""
    rows = connection.execute(
        """
        SELECT c.resolves_period,c.consumed_period,c.nonce,c.command_bytes,c.commitment_bytes,
               c.commitment_sha256,encode(t.tick_content_hash,'hex')
        FROM babylon_state.organizer_command_v1 c
        LEFT JOIN babylon_state.tick_commit t ON t.campaign_id=c.campaign_id AND t.resolve_tick=c.consumed_period
        WHERE c.campaign_id=%s::uuid ORDER BY c.resolves_period
    """,
        (campaign,),
    ).fetchall()
    originals = []
    for period, consumed, nonce, raw, commitment, cid, marker in rows:
        command = Command.model_validate(strict_json_bytes(bytes(raw)))
        rid = _receipt_id(command, period, bytes(cid))
        receipts = connection.execute(
            """
            SELECT receipt_bytes FROM babylon_state.organizer_receipt_v1
            WHERE campaign_id=%s::uuid AND receipt_id=%s AND resolve_tick=%s AND actor_id=%s
        """,
            (campaign, rid, period, str(command.actor_id)),
        ).fetchall()
        if len(receipts) != 1:
            raise ValueError("accepted command lacks its exact persisted resolution receipt")
        originals.append(
            OriginalDecision(
                period=period,
                consumed=consumed,
                nonce=bytes(nonce).hex(),
                command_hex=bytes(raw).hex(),
                commitment_hex=bytes(commitment).hex(),
                commitment_id=bytes(cid).hex(),
                marker=marker,
                receipt_id=rid.hex(),
                receipt_hex=bytes(receipts[0][0]).hex(),
            ).model_dump(mode="json")
        )
    return originals


def decision_semantics(
    rows: object,
    accepted: list[Commitment],
    recipients: list[int | None],
    markers: dict[int, str],
    campaign: str,
) -> tuple[Decision, ...]:
    originals = TypeAdapter(tuple[OriginalDecision, ...]).validate_python(rows)
    result = []
    if not originals or [r.period for r in originals] != sorted({r.period for r in originals}):
        raise ValueError("ordered decision roster is empty or repeats a period")
    for row, admission, recipient in zip(originals, accepted, recipients, strict=True):
        raw = bytes.fromhex(row.command_hex)
        command = Command.model_validate(strict_json_bytes(raw))
        commitment = Commitment.model_validate(strict_json_bytes(bytes.fromhex(row.commitment_hex)))
        receipt = strict_json_bytes(bytes.fromhex(row.receipt_hex))
        cid = hashlib.sha256(b"babylon.organizer-commitment.v3\0" + raw).digest()
        rid = _receipt_id(command, row.period, cid)
        if (
            commitment != admission
            or commitment.command != command
            or bytes(command.campaign_id) != UUID(campaign).bytes
            or bytes(command.nonce).hex() != row.nonce
            or cid.hex() != row.commitment_id
            or bytes(commitment.commitment_id) != cid
            or row.consumed != row.period
            or row.period != command.expected_period + 1
            or row.period != commitment.resolves_period
            or markers.get(row.period) != row.marker
            or rid.hex() != row.receipt_id
            or not isinstance(receipt, dict)
            or bytes(TypeAdapter(Bytes32).validate_python(receipt.get("receipt_id"))) != rid
            or bytes(TypeAdapter(Bytes32).validate_python(receipt.get("commitment_id"))) != cid
            or type(receipt.get("actor_id")) is not int
            or receipt["actor_id"] != command.actor_id
            or type(receipt.get("period")) is not int
            or receipt["period"] != row.period
            or receipt.get("choice") != command.model_dump(mode="json")["choice"]
        ):
            raise ValueError(
                "persisted command, native acceptance, receipt or committed marker differs"
            )
        result.append(
            Decision(
                period=row.period,
                actor=command.actor_id,
                authority=command.authority_id,
                partner=receipt["partner_actor_id"],
                recipient=recipient,
                choice=command.choice,
                allocation=command.allocation,
            )
        )
    return tuple(result)


def declaration_for(base: Path, *, create: bool = False) -> tuple[Reference, Declaration]:
    profile, mode = storage.native_path(base)
    store = PrivateEvidence(base)
    pair = PrivateEvidence(base.parent.parent)
    creation = _json(store, "media-creation.json")
    release = Reference.model_validate(creation["native_expectations"])
    release_store = PrivateEvidence(storage.RUN_PARENT)
    expected = storage.read_typed(release_store, release, storage.NativeExpectations)
    selected_policy(base / "policy.json")
    if base.resolve(strict=True) != base:
        raise ValueError("native member path contains redirected ancestry")
    if (
        release.path != f"{profile}-native-expectations.json"
        or creation["profile"] != profile
        or creation["run"] != str(base.parent)
        or creation["source_head"] != expected.source_head
        or store.read_reference(store.reference("source-head"))
        != (expected.source_head + "\n").encode()
    ):
        raise ValueError("member release differs from its source, workload or directory")
    name = "pair-declaration.json"
    if create and mode == "normal_play":
        campaign = str(uuid4())
    else:
        declaration = Declaration.model_validate(_json(pair, name))
        campaign = declaration.campaign
    if str(UUID(campaign)) != campaign or UUID(campaign).version != 4:
        raise ValueError("pair requires its newly declared canonical campaign UUID")
    packet = Declaration(
        version=1,
        workload="smoke-01" if profile == "smoke-01" else "walk-01",
        campaign=campaign,
        periods=int(storage.PROFILES[profile][1]),
        source_head=expected.source_head,
        inputs_sha256=store.reference("inputs.sha256").sha256,
        source_sha256=store.reference("source-before.sha256").sha256,
        policy_sha256=store.reference("policy.json").sha256,
        release=release,
    )
    if create and mode == "normal_play":
        ref = pair.publish_json(name, packet.model_dump(mode="json"))
    else:
        ref = pair.reference(name)
        if Declaration.model_validate(strict_json_bytes(pair.read_reference(ref))) != packet:
            raise ValueError(
                "member source, inputs, build, policy or horizon differs from declared pair"
            )
    if create:
        store.publish("pair-declaration.json", pair.read_reference(ref))
    elif store.reference(name).sha256 != ref.sha256:
        raise ValueError("member declaration differs from the admitted pair")
    return ref, packet


def _custody(
    store: PrivateEvidence, native: NativeRunEvidence, declaration: Declaration
) -> tuple[list[str], dict[str, Reference]]:
    fields = store.read_reference(store.reference("ownership"), 4096).decode().splitlines()
    if (
        len(fields) != 21
        or fields[0] != "national-storage-runner-media-v2"
        or fields[1] != str(storage.MEDIA_CHECKOUT)
        or fields[5] != str(store.path.parent / "pgdata")
        or fields[10:12] != [str(store.path), declaration.workload]
        or fields[7] != "national_" + fields[2][:12]
        or fields[8] != "national_writer_" + fields[2][:12]
    ):
        raise ValueError("member evidence differs from actual retained media owner")
    expected = storage.read_typed(
        PrivateEvidence(storage.RUN_PARENT), declaration.release, storage.NativeExpectations
    )
    products = {
        k: Reference.model_validate(v) for k, v in _json(store, "normal-binaries.json").items()
    }
    if products != expected.products():
        raise ValueError("actual role-to-binary inventory differs from admitted release")
    for ref in products.values():
        store.verify(ref)
    physical = _json(store, "physical.json")
    host = physical["host"]
    if (
        physical["container"] != fields[4]
        or physical["label"] != fields[2]
        or physical["image"]["id"] != fields[6]
        or physical["cluster"] != fields[20]
        or physical["port"] != int(fields[19])
        or physical["path"] != fields[5]
        or physical["name"] != fields[3]
        or (os.makedev(host["major"], host["minor"]), host["inode"])
        != (int(fields[13]), int(fields[14]))
    ):
        raise ValueError("actual fixture identity differs from the retained owner")

    if (
        native.campaign,
        native.requested_periods,
        native.policy_sha256,
        native.source_manifest_sha256,
        native.inputs_sha256,
        native.executable_manifest_sha256,
        native.ownership_record_sha256,
    ) != (
        declaration.campaign,
        declaration.periods,
        declaration.policy_sha256,
        declaration.source_sha256,
        declaration.inputs_sha256,
        store.reference("normal-binaries.json").sha256,
        store.reference("ownership").sha256,
    ):
        raise ValueError(
            "native source, executables, owner, input or campaign differs from declaration"
        )
    return fields, products


def evaluate_member(base: Path) -> CompletedMember:
    """Reopen every required input from the selected workload/mode's private retained bundle."""
    profile, mode = storage.native_path(base)
    store = PrivateEvidence(base)
    run = PrivateEvidence(base.parent)
    ref, declaration = declaration_for(base)
    policy = Policy.model_validate(_json(store, "policy.json"))
    native = NativeRunEvidence.model_validate(_json(store, "native-window-evidence.json"))
    captured = mode == "memory_capture"
    if native.status != "completed" or native.measurement_mode != mode:
        raise ValueError("native member has a different measurement mode or incomplete run")
    owner, products = _custody(store, native, declaration)
    periods = range(1, declaration.periods + 1)
    names = {
        "policy.json",
        "inputs.sha256",
        "pair-declaration.json",
        "source-before.sha256",
        "normal-binaries.json",
        "source-head",
        "media-creation.json",
        "ownership",
        "functional-terminal.json",
        "campaign",
        "host-native-admission.json",
        "physical.json",
        "native-window-evidence.json",
        "native-timings.json",
        "national-playable-qualification.json",
        "schema-baseline.json",
        "opening-created.json",
        "national-capture-mode.json",
        "reader-role",
        "observer-role",
    }
    names.update(
        a.name
        for a in (
            native.controls,
            native.opening,
            *native.advances,
            *native.boundaries,
            *native.archives,
            *native.recoveries,
            *native.aid_originals,
        )
    )
    names.update(f"tick-{n:02}{suffix}.json" for n in periods for suffix in ("", "-reopened"))
    names.add("progress-000-starting.json")
    names.update(
        f"progress-{n:03}-{stage}.json"
        for n in periods
        for stage in ("committed", "archive", "accounting", "production", "reopened")
    )
    names.update(p.name for p in base.glob("progress-*.json"))
    material = PlayableReport.model_validate(
        _json(store, "national-playable-qualification.json", CONTROLS_RECORD_BYTES)
    )
    timing = NativeTimings.model_validate(_json(store, "native-timings.json"))

    def snapshot(name: str) -> Snapshot:
        return Snapshot.model_validate(_json(store, name, CONTROLS_RECORD_BYTES))

    opening = snapshot("opening-created.json")
    ticks = tuple(snapshot(f"tick-{n:02}.json") for n in periods)
    reopens = tuple(snapshot(f"tick-{n:02}-reopened.json") for n in periods)
    if any(
        s.database != owner[7] or s.campaign != native.campaign for s in (opening, *ticks, *reopens)
    ):
        raise ValueError("material snapshots name another member database or campaign")
    storage_result = evaluate(policy, snapshot("schema-baseline.json"), opening, ticks, reopens)
    timing_result = evaluate_timings(policy, timing, ticks, reopens)
    smoke = evaluate_smoke(policy, storage_result, timing_result)
    playable = evaluate_playable(
        policy,
        declaration.policy_sha256,
        material,
        timing,
        opening,
        ticks,
        storage_result,
        timing_result,
        smoke,
        captured=captured,
    )
    walk = profile == "walk-01"
    memory = None
    if captured:
        memory = CombinedMemoryEvidence.model_validate(
            _json(store, "combined-memory.json", CONTROLS_RECORD_BYTES)
        )
        authenticate_combined_memory_capture(memory, base)
        names.add("combined-memory.json")
    elif any(base.glob("**/*memory*.json")):
        raise ValueError("normal member contains a memory certificate")
    result = evaluate_native(
        policy,
        declaration.policy_sha256,
        native,
        base,
        material,
        timing,
        opening,
        ticks,
        playable,
        memory,
        wayne_walk=walk,
    )
    walk_report = (
        evaluate_wayne_walk(policy, native, base, material, timing, memory, result, storage_result)
        if walk
        else None
    )
    if walk_report is not None and captured:
        # Only the opening segment covers creation. All three measured intervals
        # were verified by the walkthrough evaluator, including its complete main interval.
        result["combined_memory_status"] = "qualified"
    if (
        (walk_report or result)["status"] != "qualified"
        or captured
        and result["combined_memory_status"] != "qualified"
    ):
        raise ValueError("native member lacks complete passing workload evidence")
    if _json(store, "national-capture-mode.json") != {
        "version": 1,
        "mode": "playable-aid",
        "consumer": "windowed_runtime_session",
        "preset": "national-world",
        "periods": declaration.periods,
        "campaign": declaration.campaign,
    }:
        raise ValueError("native capture workload differs from its declaration")
    if store.read_reference(store.reference("campaign")).decode().strip() != declaration.campaign:
        raise ValueError("actual campaign differs from the declaration")
    functional = _json(store, "functional-terminal.json", CONTROLS_RECORD_BYTES)
    markers = {t.tick: t.marker_and_encoded_package_hashes[-1][1] for t in ticks}
    if (
        functional["campaign"] != native.campaign
        or functional["period"] != native.requested_periods
        or {m["tick"]: m["hash"] for m in functional["markers"]} != markers
    ):
        raise ValueError("functional recovery markers differ from measured member")
    segments = ("opening", "walk", "completed") if walk else ("smoke",)
    processes = []
    confirmed = []
    recipients = []
    boot = _json(store, "host-native-admission.json")["boot_id"]
    for segment in segments:
        prefix = "segment-" + segment + "/" if segment in ("opening", "completed") else ""
        trace_name = prefix + "native-controls.json"
        proc_name = "processes-" + segment + ".json"
        cold_name = "cold-installed-" + segment + ".json"
        names.update((trace_name, proc_name, cold_name))
        trace = ControlsEvidence.model_validate(_json(store, trace_name, CONTROLS_RECORD_BYTES))
        pair = ProcessPair.model_validate(_json(store, proc_name))
        cold = ColdInstallation.model_validate(_json(store, cold_name))
        if (
            pair.segment != segment
            or cold.processes != (pair.runtime, pair.client)
            or pair.boot_id != boot
            or pair.container != owner[4]
            or pair.owner_sha256 != native.ownership_record_sha256
            or cold.ownership_sha256 != pair.owner_sha256
            or cold.source_head != declaration.source_head
            or cold.elapsed_ns != cold.installed_monotonic_ns - cold.started_monotonic_ns
            or not native.started_monotonic_ns
            <= cold.started_monotonic_ns
            <= trace.actions[0].started_monotonic_ns
            or not cold.installed_monotonic_ns
            <= trace.actions[-1].completed_monotonic_ns
            <= native.completed_monotonic_ns
            or not any(
                a.state == cold.state and a.completed_monotonic_ns <= cold.installed_monotonic_ns
                for a in trace.actions
            )
            or cold.state.campaign_id != declaration.campaign
            or cold.state.durable_tick != (10 if segment == "completed" else 0)
            or pair.runtime[2] != products["babylon-runtime"].sha256
            or pair.client[2] != products["babylon-client"].sha256
            or (not captured and cold.elapsed_ns >= policy.maximum_cold_open_seconds * 10**9)
        ):
            raise ValueError(
                "actual process-cold installation differs from release, controls or mode"
            )
        if not captured and any(
            a.completed_monotonic_ns - a.started_monotonic_ns
            > policy.maximum_focused_control_seconds * 10**9
            for a in trace.actions
            if a.action
            not in ("step", "reopen", "status", "play", "open_organizer", "dismiss_splash", "quit")
        ):
            raise ValueError("normal focused control exceeded its phase ceiling")
        if captured:
            interval: FixedPeriodMemory | CombinedMemoryEvidence
            if prefix:
                interval = FixedPeriodMemory.model_validate(
                    _json(store, prefix + "segment-memory.json", CONTROLS_RECORD_BYTES)
                )
                names.update(
                    (prefix + "segment-memory.json", prefix + "ownership", prefix + "policy.json")
                )
            else:
                assert memory is not None
                interval = memory
            names.update(
                prefix + n
                for n in (
                    "combined-memory-source.sha256",
                    "combined-memory-executables.json",
                    "combined-memory-sampler-source.py",
                    "combined-memory-tooling.json",
                )
            )
            for sample in interval.samples:
                observed = {
                    (p.role, p.pid, p.start_time_ticks, p.executable_sha256)
                    for p in sample.processes
                }
                native_processes = {row for row in observed if row[0] != "game-postgresql"}
                if (
                    interval.boot_id != boot
                    or native_processes
                    != {("native-client", *pair.client), ("engine-runtime", *pair.runtime)}
                    or ("game-postgresql", *pair.postgres) not in observed
                    or any(
                        row[3] != pair.postgres[2]
                        for row in observed
                        if row[0] == "game-postgresql"
                    )
                ):
                    raise ValueError(
                        "memory sample does not contain actual owned process incarnations"
                    )
        processes.append(pair)
        for a in trace.actions:
            if a.action == "confirm" and a.event == "acceptance_admitted":
                c = Commitment.model_validate(a.state.commitment)
                recipient = None
                if c.command.choice in ("local_aid", "remote_aid"):
                    original = AidOriginal.model_validate(
                        _artifact(
                            base,
                            next(
                                r
                                for r in native.aid_originals
                                if r.name == "aid-" + bytes(c.commitment_id).hex() + ".json"
                            ),
                            MATERIAL_RECORD_BYTES,
                        )
                    )
                    kind = "local" if c.command.choice == "local_aid" else "remote"
                    offers = original.review.before.get("aid")
                    if not isinstance(offers, list):
                        raise ValueError("original aid review lacks offered recipients")
                    targets = [
                        offer.get("recipient_actor_id")
                        for offer in offers
                        if isinstance(offer, dict)
                        and offer.get("kind") == kind
                        and offer.get("period") == c.command.expected_period
                    ]
                    if len(targets) != 1 or type(targets[0]) is not int:
                        raise ValueError("admitted aid command lacks exact recipient")
                    recipient = targets[0]
                confirmed.append(c)
                recipients.append(recipient)
    if (
        len({(p[0], p[1]) for pair in processes for p in (pair.client, pair.runtime)})
        != 2 * len(segments)
        or len({p.postgres for p in processes}) != 1
    ):
        raise ValueError("cold launches reused a native process or changed the fixture")
    decisions = decision_semantics(
        functional["organizer_decisions"], confirmed, recipients, markers, native.campaign
    )
    if walk:
        names.update(p.name for p in base.glob("walk-*.json"))
        names.update(
            (
                "pending-before-cold.json",
                "pending-after-cold.json",
                "mixed-pending-before-reopen.json",
                "mixed-pending-after-reopen.json",
                "completed-before-cold.json",
                "completed-after-cold.json",
                "before-history-archive-return.json",
                "after-history-archive-return.json",
                "functional-terminal-reopened.json",
            )
        )
        if functional != _json(store, "functional-terminal-reopened.json", CONTROLS_RECORD_BYTES):
            raise ValueError("restored terminal differs from actual original")
    artifacts = [run.reference("evidence/" + name) for name in sorted(names)]
    if walk:
        artifacts.extend(
            run.reference("raw/" + p.name)
            for p in sorted((run.path / "raw").iterdir())
            if p.suffix in (".json", ".png")
        )
    return CompletedMember(
        version=1,
        scope="completed_native_member_for_restore_and_retirement",
        measurement_mode=mode,
        declaration_sha256=ref.sha256,
        evidence=tuple(artifacts),
        owner=native.ownership_record_sha256,
        container=owner[4],
        database=owner[7],
        cluster=owner[20],
        pgdata=(int(owner[13]), int(owner[14])),
        processes=tuple(processes),
        decisions=decisions,
        foundation=native.foundation_sha256,
        graph_foundation=native.graph_foundation_sha256,
        native=result,
        walk=walk_report,
    )


def verify_retirement(run: Path) -> RetiredMember:
    """Require the original restore and clean stopped-removal proof for this exact member."""
    evidence = PrivateEvidence(run / "evidence")
    _, mode = storage.native_path(evidence.path)
    backup = PrivateEvidence(run / "backup")
    completed = evidence.reference("completed-member.json")
    member = CompletedMember.model_validate(
        strict_json_bytes(evidence.read_reference(completed, CONTROLS_RECORD_BYTES))
    )
    seal = backup.reference("recovery-seal.json")
    record = strict_json_bytes(backup.read_reference(seal))
    if not isinstance(record, dict):
        raise ValueError("member recovery seal is malformed")
    retired = _json(evidence, "retired-container.json")
    original = _json(evidence, "functional-terminal.json", CONTROLS_RECORD_BYTES)
    if (
        mode != member.measurement_mode
        or record["owner"] != evidence.reference("ownership").model_dump()
        or member.owner != record["owner"]["sha256"]
        or record["functional"] != evidence.reference("functional-terminal.json").model_dump()
        or record["completed_member"] != completed.model_dump()
        or retired["container"] != member.container
        or (
            os.makedev(retired["retained_pgdata"]["major"], retired["retained_pgdata"]["minor"]),
            retired["retained_pgdata"]["inode"],
        )
        != member.pgdata
    ):
        raise ValueError("member retirement owner, PGDATA, completion or functional state differs")
    required = {
        "original-terminal.json",
        "restored-terminal.json",
        "database.dump",
        "pgdata.tar",
        "pgdata-second.tar",
        "original-probes.json",
        "restored-probes.json",
        "verification-admission.json",
    }
    refs = [Reference.model_validate(row) for row in record["retained"]]
    if not required.issubset({r.path for r in refs}) or len({r.path for r in refs}) != len(refs):
        raise ValueError("recovery seal lacks independent restore and archive evidence")
    for item in refs:
        backup.verify(item)
    for key in ("shutdown", "fenced_stop", "stop_attempt"):
        evidence.verify(Reference.model_validate(record[key]))
    expected = {**original, "database": {**original["database"], "allows_connections": False}}
    if (
        _json(backup, "original-terminal.json", CONTROLS_RECORD_BYTES) != original
        or _json(backup, "restored-terminal.json", CONTROLS_RECORD_BYTES) != expected
        or _json(backup, "original-probes.json") != _json(backup, "restored-probes.json")
    ):
        raise ValueError("restored member changed functional state or access")
    return RetiredMember(
        measurement_mode=mode,
        completed=completed,
        recovery=seal,
        retirement=evidence.reference("retired-container.json"),
    )


def join_members(
    declaration: Reference, normal: CompletedMember, captured: CompletedMember
) -> None:
    if (normal.measurement_mode, captured.measurement_mode) != MODES or any(
        member.declaration_sha256 != declaration.sha256 for member in (normal, captured)
    ):
        raise ValueError("pair requires one complete member per mode from the same declaration")
    if (
        normal.native["combined_memory_status"] != "not_measured"
        or captured.native["combined_memory_status"] != "qualified"
        or any((m.walk or m.native)["status"] != "qualified" for m in (normal, captured))
    ):
        raise ValueError("both timing and memory members must independently pass")

    def incarnations(member: CompletedMember) -> set[tuple[str, int, int]]:
        return {
            (p.boot_id, role[0], role[1])
            for p in member.processes
            for role in (p.client, p.runtime, p.postgres)
        }

    if (
        normal.owner == captured.owner
        or normal.database == captured.database
        or normal.cluster == captured.cluster
        or normal.pgdata == captured.pgdata
        or normal.container == captured.container
        or incarnations(normal) & incarnations(captured)
    ):
        raise ValueError("pair reused its actual fixture owner or process incarnation")

    def roles(member: CompletedMember) -> list[tuple[str, str, str, str]]:
        return [(p.segment, p.runtime[2], p.client[2], p.postgres[2]) for p in member.processes]

    if (normal.foundation, normal.graph_foundation, normal.decisions, roles(normal)) != (
        captured.foundation,
        captured.graph_foundation,
        captured.decisions,
        roles(captured),
    ):
        raise ValueError("actual material foundation, decisions or role binaries differ")


def verify_completed(evidence: PrivateEvidence) -> CompletedMember:
    old = CompletedMember.model_validate(
        _json(evidence, "completed-member.json", CONTROLS_RECORD_BYTES)
    )
    member = evaluate_member(evidence.path)
    if old.model_dump(mode="json") != member.model_dump(mode="json"):
        raise ValueError("substituted member evidence differs from original completion")
    for ref in member.evidence:
        PrivateEvidence(evidence.path.parent).verify(ref)
    return member


def qualify_pair(profile: str) -> dict[str, object]:
    members = []
    retired = []
    for mode in MODES:
        run = storage.member_run(profile, mode)
        evidence = PrivateEvidence(run / "evidence")
        retirement = verify_retirement(run)
        member = verify_completed(evidence)
        members.append(member)
        retired.append(retirement)
    pair_store = PrivateEvidence(storage.member_run(profile, "normal_play").parent)
    declaration = pair_store.reference("pair-declaration.json")
    join_members(declaration, *members)
    pair = NativePairEvidence(
        version=1,
        scope="native_timing_and_memory_pair_v1",
        declaration=declaration,
        normal_play=retired[0],
        memory_capture=retired[1],
    )
    result = {
        "qualification_report_version": 8,
        "scope": pair.scope,
        "status": "qualified",
        "workload": profile,
        "native_pair": pair.model_dump(mode="json"),
        "enjoyment_status": "unqualified",
    }

    if (pair_store.path / "qualification.json").exists():
        existing = _json(pair_store, "qualification.json")
        if existing != result:
            raise ValueError(
                "published qualification differs from the two authenticated member bundles"
            )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation", choices=("path", "admit", "member", "verify-member", "qualify")
    )
    parser.add_argument("workload", choices=("smoke-01", "walk-01"))
    args = parser.parse_args()
    try:
        if args.operation == "qualify":
            packet = qualify_pair(args.workload)
            pair = PrivateEvidence(storage.member_run(args.workload, "normal_play").parent)
            if not (pair.path / "qualification.json").exists():
                pair.publish_json("qualification.json", packet)
        else:
            mode = measurement_mode(os.environ.get("BABYLON_NATIVE_MEASUREMENT_MODE"))
            evidence = PrivateEvidence(storage.member_run(args.workload, mode) / "evidence")
            if args.operation == "path":
                print(evidence.path)
                return 0
            if evidence.path != Path(os.environ["BABYLON_STORAGE_REPORT_DIRECTORY"]):
                raise ValueError("operator selected another native evidence directory")
            if args.operation == "admit":
                print(declaration_for(evidence.path, create=True)[1].campaign)
            elif args.operation == "member":
                member = evaluate_member(evidence.path)
                for item in member.evidence:
                    PrivateEvidence(evidence.path.parent).verify(item)
                evidence.publish_json("completed-member.json", member.model_dump(mode="json"))
            else:
                verify_completed(evidence)
        return 0
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
