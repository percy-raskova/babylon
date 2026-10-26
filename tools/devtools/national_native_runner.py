"""Run the owned national fixture through the actual windowed client.

The existing shell supervisor alone provisions and retires the fixture. This
consumer uses its frozen policy, collector, credentials and source capture;
the existing qualification evaluator alone decides admission.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from uuid import UUID

import psycopg
from psycopg.conninfo import conninfo_to_dict
from pydantic import BaseModel
from tools import run_observer_session as launcher
from tools.devtools import national_game_memory as memory
from tools.devtools.national_native_evidence import (
    MATERIAL_RECORD_BYTES,
    AdvanceRecord,
    AidBoundary,
    AidOriginal,
    ArchiveRecord,
    Artifact,
    BoundaryFacts,
    MaterialRecord,
    NativeFailureCause,
    NativeRunEvidence,
    NativeRunIncomplete,
    RecoveryRecord,
    private_bytes,
)
from tools.devtools.national_storage_qualification import (
    ArchiveBoundary,
    NativeTimings,
    PlayableBoundary,
    PlayableReport,
    Policy,
    Snapshot,
    strict_json_bytes,
)
from tools.devtools.national_windowed_qualification import ControlState, PlannedChoice, drive_pair


class NativeRunRefusal(ValueError):
    """A specific operator refusal safe to display without credential details."""


def failure_causes(error: BaseException) -> tuple[NativeFailureCause, ...]:
    """Retain ordered leaves; group messages and unknown exception text stay private."""
    pending = [error]
    causes = []
    while pending:
        current = pending.pop()
        if isinstance(current, BaseExceptionGroup):
            pending.extend(reversed(current.exceptions))
        else:
            causes.append(
                NativeFailureCause(
                    failure_type=type(current).__name__,
                    safe_reason=str(current)
                    if isinstance(current, (NativeRunRefusal, memory.CaptureRefusal))
                    else None,
                )
            )
    return tuple(causes)


def read_record[RecordType: BaseModel](path: Path, record_type: type[RecordType]) -> RecordType:
    return record_type.model_validate(strict_json_bytes(private_bytes(path, MATERIAL_RECORD_BYTES)))


def publish(path: Path, value: dict[str, object]) -> None:
    if path.exists() or path.is_symlink():
        raise NativeRunRefusal("native evidence refuses an existing result")
    memory.write_capture_record(path, value)


def committed_facts(record: MaterialRecord) -> tuple[BoundaryFacts, AidBoundary]:
    if record.facts is None or record.aid is None or record.opening is not None or not record.tick:
        raise NativeRunRefusal("native committed record lacks its exact material and aid facts")
    return record.facts, record.aid


def aid_identity(value: object) -> tuple[int, ...]:
    if not isinstance(value, (list, tuple)):
        raise NativeRunRefusal("native aid practice lacks its original command identity")
    result: list[int] = []
    for byte in value:
        if type(byte) is not int or not 0 <= byte <= 255:
            raise NativeRunRefusal("native aid command identity is malformed")
        result.append(byte)
    if len(result) != 32 or not any(result):
        raise NativeRunRefusal("native aid command identity must be an exact nonzero digest")
    return tuple(result)


class NativeRun:
    def __init__(self, root: Path, directory: Path) -> None:
        self.root = root
        self.directory = directory
        self.policy = Policy.model_validate_json((directory / "policy.json").read_bytes())
        self.policy_hash = memory.executable_digest(directory / "policy.json")
        self.campaign = (directory / "campaign").read_text().strip()
        if str(UUID(self.campaign)) != self.campaign or UUID(self.campaign).int == 0:
            raise NativeRunRefusal("national runner requires its canonical campaign")
        requested = os.environ.get("BABYLON_NATIONAL_STORAGE_PERIODS", "")
        requested = requested or str(self.policy.routine_smoke_periods)
        if re.fullmatch(r"[1-9][0-9]*", requested) is None or len(requested) > 10:
            raise NativeRunRefusal("national runner period request is malformed")
        self.periods = int(requested)
        if not 2 <= self.periods <= self.policy.save_qualification_ticks:
            raise NativeRunRefusal("native aid run exceeds the captured qualification horizon")
        if os.environ.get("BABYLON_NATIONAL_CAPTURE_MODE") != "playable-aid":
            raise NativeRunRefusal("windowed national runner requires playable aid scope")
        if directory != Path(os.environ["BABYLON_STORAGE_REPORT_DIRECTORY"]):
            raise NativeRunRefusal("national runner evidence directory differs")
        common = (
            subprocess.run(
                ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                cwd=root,
                capture_output=True,
                check=True,
                timeout=10,
            )
            .stdout.decode()
            .strip()
        )
        self.lease = Path(common) / "babylon-national-storage" / "active"
        self.ownership = private_bytes(directory / "ownership", 4096)
        if private_bytes(self.lease, 4096) != self.ownership:
            raise NativeRunRefusal("national runner original ownership differs from the live lease")
        fields = self.ownership.decode().splitlines()
        if len(fields) != 11 or fields[0] != "national-storage-runner-v1":
            raise NativeRunRefusal("national runner ownership version is unsupported")
        if fields[1] != str(root) or fields[10] != str(directory):
            raise NativeRunRefusal("national runner ownership scope differs")
        self.supervisor = {
            **os.environ,
            "REPO_ROOT": fields[1],
            "NATIONAL_RECORD": str(self.lease),
            "CANARY": fields[2],
            "CONTAINER": fields[3],
            "CONTAINER_ID": fields[4],
            "VOLUME": fields[5],
            "IMAGE_ID": fields[6],
            "NATIONAL_DATABASE": fields[7],
            "NATIONAL_WRITER": fields[8],
            "NATIONAL_DATABASE_OID": fields[9],
        }
        self.container = fields[4]
        self.writer_dsn = os.environ["BABYLON_NATIONAL_STORAGE_WRITER_DSN"]
        self.reader_dsn = os.environ["BABYLON_NATIONAL_STORAGE_READER_DSN"]
        self.observer_dsn = os.environ["BABYLON_NATIONAL_STORAGE_OBSERVER_DSN"]
        self.runtime = root / "rust/target/debug/babylon-runtime"
        self.client = root / "rust/target/debug/babylon-client"
        self.operator = root / "rust/target/debug/babylon-material-audit"
        self.binaries = {
            p: memory.executable_digest(p)
            for p in (
                self.runtime,
                self.client,
                self.operator,
            )
        }
        # Operational patience is distinct from the evaluator's phase budgets.
        self.timeout = self.policy.maximum_routine_smoke_seconds
        self.started = time.monotonic_ns()
        self._foundation: str | None = None
        self._capture: memory.RunningMemoryCapture | None = None
        self.opening: MaterialRecord | None = None
        self.boundaries: list[PlayableBoundary] = []
        self.material: list[MaterialRecord] = []
        self.advances: list[AdvanceRecord] = []
        self.recoveries: list[tuple[str, RecoveryRecord]] = []
        self.snapshots: list[Snapshot] = []
        self.stage = "admitting_supervisor"
        self.operation_lock = threading.RLock()
        self.verify_live()
        self.verify_credentials(fields[2], fields[7], fields[8])
        self.verify_sources()

    @property
    def foundation(self) -> str:
        if self._foundation is None:
            raise NativeRunRefusal("native operation requires its acknowledged opening foundation")
        return self._foundation

    def verify_credentials(self, canary: str, database: str, writer: str) -> None:
        ports = strict_json_bytes(
            memory.docker_command(
                [
                    "inspect",
                    "--format",
                    "{{json .NetworkSettings.Ports}}",
                    self.container,
                ],
                timeout=10,
            )
        )
        if not isinstance(ports, dict) or not isinstance(ports.get("5432/tcp"), list):
            raise NativeRunRefusal("owned native credentials have no explicit loopback binding")
        bindings = ports["5432/tcp"]
        if (
            len(bindings) != 1
            or not isinstance(bindings[0], dict)
            or bindings[0].get("HostIp") != "127.0.0.1"
        ):
            raise NativeRunRefusal("owned native credential binding differs")
        for dsn, role in (
            (self.writer_dsn, writer),
            (self.observer_dsn, "national_observer_" + canary[:12]),
            (self.reader_dsn, "national_reader_" + canary[:12]),
        ):
            try:
                parameters = conninfo_to_dict(dsn)
            except psycopg.Error:
                raise NativeRunRefusal("national credential parameters refused") from None
            if parameters != {
                "host": "127.0.0.1",
                "port": bindings[0].get("HostPort"),
                "dbname": database,
                "user": role,
                "password": canary,
            }:
                raise NativeRunRefusal(
                    "national credential does not name its exact owned capability"
                )

    def environments(self) -> tuple[dict[str, str], dict[str, str]]:
        common = {
            key: value
            for key, value in os.environ.items()
            if not key.upper().startswith("PG")
            and not key.endswith("_DSN")
            and not key.startswith(
                (
                    "BABYLON_QUALIFICATION_",
                    "BABYLON_NATIONAL_STORAGE_",
                    "BABYLON_STORAGE_",
                    "BABYLON_POSTGRES_",
                )
            )
        }
        common["BABYLON_RUNTIME_DSN"] = self.writer_dsn
        return launcher.child_environments(
            common,
            launcher.ReaderCredentials(self.observer_dsn, self.reader_dsn),
        )

    def verify_live(self) -> None:
        with self.operation_lock:
            self._verify_live_locked()

    def _verify_live_locked(self) -> None:
        if private_bytes(self.lease, 4096) != self.ownership:
            raise NativeRunRefusal("national ownership changed during the native run")
        result = subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; national_verify_live',
                "national-native",
                str(self.root / "tools/postgres_national_lifecycle.sh"),
            ],
            env=self.supervisor,
            cwd=self.root,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if result.returncode or result.stdout:
            raise NativeRunRefusal("national supervisor live ownership admission refused")

    def verify_sources(self) -> None:
        result = subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; national_verify_source_capture',
                "national-native",
                str(self.root / "tools/postgres_national_lifecycle.sh"),
            ],
            env=self.supervisor,
            cwd=self.root,
            capture_output=True,
            timeout=60,
            check=False,
        )
        if result.returncode:
            raise NativeRunRefusal("national source capture changed during the native run")
        if any(memory.executable_digest(p) != digest for p, digest in self.binaries.items()):
            raise NativeRunRefusal("national executable changed during the native run")

    def progress(self, tick: int, stage: str, evidence: dict[str, object]) -> None:
        self.stage = stage
        publish(
            self.directory / f"progress-{tick:03}-{stage}.json",
            {
                "version": 2,
                "status": "incomplete",
                "campaign": self.campaign,
                "tick": tick,
                "completed_stage": stage,
                "elapsed_ns": time.monotonic_ns() - self.started,
                "evidence": evidence,
            },
        )

    def snapshot(self, stage: str) -> Snapshot:
        with self.operation_lock:
            return self._snapshot_locked(stage)

    def _snapshot_locked(self, stage: str) -> Snapshot:
        self.verify_live()
        result = subprocess.run(
            [
                sys.executable,
                os.environ["BABYLON_STORAGE_SNAPSHOT_SCRIPT"],
                stage,
                "--campaign",
                self.campaign,
            ],
            cwd=self.root,
            env=dict(os.environ),
            capture_output=True,
            timeout=self.timeout,
            check=False,
        )
        if result.returncode:
            raise NativeRunRefusal("frozen PostgreSQL storage collector refused: " + stage)
        return read_record(self.directory / f"{stage}.json", Snapshot)

    def marker(self) -> memory.CampaignMemoryMarker:
        try:
            with psycopg.connect(
                self.reader_dsn,
                connect_timeout=5,
                options="-c default_transaction_read_only=on -c event_triggers=off",
            ) as connection:
                connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                identity = connection.execute(
                    "SELECT foundation_sha256 FROM public.v_material_campaign_identity_v2 "
                    "WHERE campaign_id=%s::uuid",
                    (self.campaign,),
                ).fetchone()
                tail = connection.execute(
                    "SELECT resolve_tick,tick_content_hash FROM public.v_committed_tick_status_v1 "
                    "WHERE campaign_id=%s::uuid ORDER BY resolve_tick DESC LIMIT 1",
                    (self.campaign,),
                ).fetchone()
        except psycopg.Error:
            raise NativeRunRefusal("confined committed memory marker read refused") from None
        if identity is None:
            if tail is not None or self._foundation is not None:
                raise NativeRunRefusal("memory marker has no authenticated campaign foundation")
            return memory.CampaignMemoryMarker(
                campaign=self.campaign,
                foundation_sha256=None,
                campaign_age_ticks=0,
                tick_content_hash=None,
            )
        try:
            marker = memory.CampaignMemoryMarker(
                campaign=self.campaign,
                foundation_sha256=bytes(identity[0]).hex(),
                campaign_age_ticks=0 if tail is None else tail[0],
                tick_content_hash=None if tail is None else bytes(tail[1]).hex(),
            )
        except (ValueError, TypeError, IndexError):
            raise NativeRunRefusal("memory marker campaign components are malformed") from None
        if self._foundation is not None and marker.foundation_sha256 != self._foundation:
            raise NativeRunRefusal("committed memory marker foundation changed")
        return marker

    def prepare(self) -> None:
        self.progress(
            0,
            "starting",
            {
                "requested_periods": self.periods,
                "policy_sha256": self.policy_hash,
            },
        )
        publish(
            self.directory / "national-capture-mode.json",
            {
                "version": 1,
                "mode": "playable-aid",
                "consumer": "windowed_runtime_session",
                "preset": "national-world",
                "periods": self.periods,
                "campaign": self.campaign,
            },
        )
        environment, _reader = self.environments()
        for command, failure in (
            ("bootstrap", "owned native schema bootstrap refused"),
            ("provision-readers", "owned native reader provisioning refused"),
        ):
            result = subprocess.run(
                [str(self.runtime), command],
                cwd=self.root,
                env=environment,
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )
            if result.returncode:
                raise NativeRunRefusal(failure)
        self.snapshot("schema-baseline")
        self.verify_sources()

    def capture(self) -> memory.RunningMemoryCapture:
        self.verify_live()
        state = memory.docker_state(self.container, timeout=10)
        pid = state.host_pid
        status = memory.read_kernel_record(Path(f"/proc/{pid}/status"))
        credentials = {
            line.split(b":", 1)[0]: line.split(b":", 1)[1].split()
            for line in status.splitlines()
            if b":" in line
        }
        uid, gid = int(credentials[b"Uid"][0]), int(credentials[b"Gid"][0])
        memory.verify_process_credentials(pid, uid, gid)
        cgroup = memory.read_kernel_record(Path(f"/proc/{pid}/cgroup")).decode().strip()
        if not cgroup.startswith("0::/") or "\n" in cgroup:
            raise NativeRunRefusal("owned PostgreSQL unified cgroup is absent")
        directory = Path("/sys/fs/cgroup") / cgroup[4:]
        inode = directory.stat()
        executable = (
            memory.docker_command(
                [
                    "exec",
                    "--user",
                    f"{uid}:{gid}",
                    self.container,
                    "sha256sum",
                    "/proc/1/exe",
                ],
                timeout=10,
            )
            .decode()
            .strip()
            .split(maxsplit=1)
        )
        if len(executable) != 2 or executable[1] != "/proc/1/exe":
            raise NativeRunRefusal("owned PostgreSQL executable admission differs")
        admission = memory.PostgresAdmission(
            container_id=state.container_id,
            image_id=state.image_id,
            host_pid=pid,
            start_time_ticks=memory.parse_start_time(
                memory.read_kernel_record(Path(f"/proc/{pid}/stat")),
                pid,
            ),
            uid=uid,
            gid=gid,
            cgroup_directory=directory,
            cgroup_device=inode.st_dev,
            cgroup_inode=inode.st_ino,
            executable_sha256=executable[0],
        )
        (self.directory / "combined-memory-source.sha256").write_bytes(
            (self.directory / "source-before.sha256").read_bytes()
        )
        (self.directory / "combined-memory-sampler-source.py").write_bytes(
            (self.root / "tools/devtools/national_game_memory.py").read_bytes()
        )
        publish(
            self.directory / "combined-memory-executables.json",
            {
                "version": 1,
                "roles": {
                    "engine-runtime": [self.binaries[self.runtime]],
                    "native-client": [self.binaries[self.client]],
                    "game-postgresql": [admission.executable_sha256],
                },
            },
        )
        publish(
            self.directory / "combined-memory-tooling.json",
            {
                "version": 1,
                "compilation_peak_rss_upper_bound_bytes": None,
                "external_test_tooling_peak_rss_upper_bound_bytes": None,
                "scope": "separate_tooling_not_running_game_compliance",
            },
        )
        expected = {
            key: memory.executable_digest(self.directory / name)
            for key, name in memory.CAPTURE_FILES.items()
        }
        self._capture = memory.RunningMemoryCapture(
            directory=self.directory,
            expected_hashes=expected,
            campaign=self.campaign,
            foundation_sha256=self._foundation,
            runtime_sha256=self.binaries[self.runtime],
            client_sha256=self.binaries[self.client],
            postgres=memory.OwnedPostgresScope(admission, self.verify_live),
            read_marker=self.marker,
            sample_gap_seconds=self.policy.maximum_combined_memory_sample_gap_seconds,
            operation_timeout=30,
            operation_lock=self.operation_lock,
        )
        return self._capture

    def archive(self, record: MaterialRecord) -> ArchiveBoundary:
        with self.operation_lock:
            return self._archive_locked(record)

    def _archive_locked(self, record: MaterialRecord) -> ArchiveBoundary:
        if self.opening is None or self.opening.opening is None or record.facts is None:
            raise NativeRunRefusal("native Archive read lacks its admitted opening or boundary")
        result = subprocess.run(
            [
                str(self.operator),
                "--view",
                "archive",
                "--campaign",
                self.campaign,
                "--foundation",
                self.foundation,
                "--graph-foundation",
                self.opening.opening.graph_foundation_sha256,
                "--policy",
                str(self.directory / "policy.json"),
                "--policy-sha256",
                self.policy_hash,
                "--periods",
                str(self.periods),
            ],
            input=json.dumps(
                {
                    "version": 1,
                    "tick": record.tick,
                    "tick_content_hash": record.tick_content_hash,
                }
            ).encode()
            + b"\n",
            cwd=self.root,
            capture_output=True,
            timeout=self.timeout,
            check=False,
        )
        if result.returncode or len(result.stdout) > MATERIAL_RECORD_BYTES:
            raise NativeRunRefusal("independent authenticated Archive operator refused")
        value = ArchiveRecord.model_validate(strict_json_bytes(result.stdout))
        if (
            value.campaign,
            value.foundation_sha256,
            value.graph_foundation_sha256,
            value.policy_sha256,
            value.tick,
            value.tick_content_hash,
        ) != (
            self.campaign,
            self.foundation,
            self.opening.opening.graph_foundation_sha256,
            self.policy_hash,
            record.tick,
            record.tick_content_hash,
        ):
            raise NativeRunRefusal("independent Archive identity differs from the native boundary")
        publish(self.directory / f"archive-{record.tick}.json", value.model_dump(mode="json"))
        boundary = ArchiveBoundary.model_validate(
            value.archive.model_dump(
                include={
                    "expected_tick",
                    "durable_tick",
                    "processed_tick",
                    "pending_count",
                    "dossier_sha256",
                }
            )
        )
        if (
            boundary.expected_tick,
            boundary.durable_tick,
            boundary.processed_tick,
            boundary.pending_count,
        ) != (record.tick, record.tick, record.tick, 0):
            raise NativeRunRefusal("native committed boundary has incomplete authenticated Archive")
        return boundary

    def on_boundary(self, state: ControlState) -> None:
        self.verify_sources()
        if state.campaign_id != self.campaign or state.foundation_sha256 is None:
            raise NativeRunRefusal("native UI admitted a different campaign foundation")
        record = read_record(self.directory / f"material-{state.durable_tick}.json", MaterialRecord)
        if (record.tick, record.tick_content_hash) != (state.durable_tick, state.tick_content_hash):
            raise NativeRunRefusal(
                "native material publication differs from its installed UI boundary"
            )
        if not record.tick:
            if record.opening is None or self.opening is not None:
                raise NativeRunRefusal("native run requires one authenticated opening")
            opening = record.opening
            if (opening.campaign, opening.foundation_sha256, opening.policy_sha256) != (
                self.campaign,
                state.foundation_sha256,
                self.policy_hash,
            ):
                raise NativeRunRefusal("native opening identity differs from its admitted source")
            with self.operation_lock:
                opening_marker = self.marker()
                if (
                    opening_marker.foundation_sha256 != opening.foundation_sha256
                    or opening_marker.campaign_age_ticks
                ):
                    raise NativeRunRefusal(
                        "native opening differs from independent committed identity"
                    )
                if self._capture is None:
                    raise NativeRunRefusal("native opening has no owned memory capture")
                self._capture.bind_foundation(opening.foundation_sha256)
                self._foundation = opening.foundation_sha256
            self.opening = record
            self.snapshot("opening-created")
            self.progress(0, "native-opening", {"opening": record.opening.model_dump(mode="json")})
            return
        if state.foundation_sha256 != self.foundation:
            raise NativeRunRefusal("native UI admitted a different campaign foundation")
        if record.facts is None or record.aid is None or record.tick != len(self.boundaries) + 1:
            raise NativeRunRefusal("native committed facts omit or duplicate a requested period")
        advance = read_record(self.directory / f"advance-{record.tick}.json", AdvanceRecord)
        self.progress(record.tick, "committed", advance.model_dump(mode="json"))
        archive = self.archive(record)
        self.progress(record.tick, "archive", archive.model_dump(mode="json"))
        self.progress(record.tick, "accounting", record.aid.model_dump(mode="json"))
        snapshot = self.snapshot(f"tick-{record.tick:02}")
        marker = snapshot.marker_and_encoded_package_hashes[-1]
        if marker[:3] != (record.tick, record.tick_content_hash, record.facts.envelope_digest):
            raise NativeRunRefusal(
                "PostgreSQL committed package differs from the native material boundary"
            )
        if snapshot.lookup_delta_hashes is None:
            raise NativeRunRefusal("native storage boundary lacks authenticated lookup hashes")
        facts = record.facts
        boundary = PlayableBoundary.model_validate(
            {
                "tick": facts.tick,
                "campaign": facts.campaign,
                "foundation_sha256": facts.foundation_sha256,
                "tick_content_hash": facts.tick_content_hash,
                "envelope_digest": facts.envelope_digest,
                "register_storage_sha256": marker[3],
                "receipt_storage_sha256": marker[4],
                "lookup_storage_sha256": snapshot.lookup_delta_hashes[-1][1],
                "canonical_receipt_sha256": facts.canonical_receipt_sha256,
                "nominal_world_hash": facts.nominal_world_hash,
                "archive": archive.model_dump(mode="json"),
                "production": {
                    "tick": facts.tick,
                    "nominal_world_hash": facts.nominal_world_hash,
                    "snapshot_sha256": facts.production_evidence_sha256,
                    "county_roster_sha256": facts.county_roster_sha256,
                    "material_register_bytes": facts.material_register_bytes,
                    "production_evidence_body_bytes": facts.production_evidence_body_bytes,
                },
                "trade": facts.trade.model_dump(mode="json"),
                "economic": facts.economic.model_dump(mode="json"),
            }
        )
        self.progress(record.tick, "production", boundary.production.model_dump(mode="json"))
        self.boundaries.append(boundary)
        self.material.append(record)
        self.advances.append(advance)
        self.snapshots.append(snapshot)

    def on_recovery(self, state: ControlState) -> None:
        name = f"recovery-{state.durable_tick}-{state.scope_epoch}.json"
        recovery = read_record(self.directory / name, RecoveryRecord)
        restored = self.snapshot(f"tick-{state.durable_tick:02}-reopened")
        original = self.snapshots[-1]
        if (
            restored.campaign != original.campaign
            or restored.marker_and_encoded_package_hashes
            != original.marker_and_encoded_package_hashes
            or restored.lookup_delta_hashes != original.lookup_delta_hashes
            or restored.actual_rust_storage_package_claims
            != original.actual_rust_storage_package_claims
        ):
            raise NativeRunRefusal(
                "native recovered PostgreSQL packages differ from their committed boundary"
            )
        self.progress(state.durable_tick, "reopened", recovery.model_dump(mode="json"))
        self.recoveries.append((name, recovery))

    def reports(self) -> None:
        if (
            self.opening is None
            or self.opening.opening is None
            or len(self.boundaries) != self.periods
            or len(self.recoveries) != self.periods
        ):
            raise NativeRunRefusal(
                "native run cannot publish a completed report from a partial horizon"
            )
        final = self.material[-1]
        audits = [committed_facts(record) for record in self.material]
        final_facts, _aid = audits[-1]
        originals = [
            (path, read_record(path, AidOriginal))
            for path in sorted(self.directory.glob("aid-*.json"))
        ]
        posted = {
            aid_identity(row.get("original_commitment"))
            for _facts, aid in audits
            for row in aid.independent_practices
            if row.get("consumed_support") is True
        }
        consumed = {
            original.commitment.command.choice
            for _path, original in originals
            if original.commitment.commitment_id in posted
        }
        remote, local = "remote_aid" in consumed, "local_aid" in consumed
        audit = final.aid_summary.model_dump(mode="json")
        audit["periods"] = [
            aid.model_dump(mode="json", exclude={"version"}) for _facts, aid in audits
        ]
        report = PlayableReport.model_validate(
            {
                "version": 6,
                "capture_mode": "playable-aid",
                "policy_sha256": self.policy_hash,
                "campaign": self.campaign,
                "foundation_sha256": self.foundation,
                "requested_periods": self.periods,
                "county_geoids": self.opening.opening.county_geoids,
                "aid_periods": [
                    {
                        "period": original.commitment.resolves_period,
                        "commitment": original.commitment.model_dump(mode="json"),
                        "preview": original.review.admission,
                    }
                    for _path, original in originals
                ],
                "continuations": [
                    {
                        "period": record.tick,
                        "tail": recovery.source.model_dump(
                            include={"tick_content_hash"},
                            mode="json",
                        )
                        | {"resolve_tick": record.tick},
                        "organizer_snapshot_sha256": recovery.original_organizer_sha256,
                        "latest_marker": list(snapshot.marker_and_encoded_package_hashes[-1][:3]),
                        "nominal_world_hash": facts.nominal_world_hash,
                    }
                    for record, (_name, recovery), snapshot, (facts, _aid) in zip(
                        self.material,
                        self.recoveries,
                        self.snapshots,
                        audits,
                        strict=True,
                    )
                ],
                "boundaries": [row.model_dump(mode="json") for row in self.boundaries],
                "canonical_protocol_recovery": "passed",
                "positive_aid_consequences": "passed" if remote and local else "incomplete",
                "remote_consumed": remote,
                "local_consumed": local,
                "independent_finite_aid_practice": final.aid_practices,
                "independent_account_posting_audit": audit,
                "independent_trade_accounting": final.trade_summary.model_dump(mode="json"),
                "independent_economic_accounting": final.economic_summary.model_dump(mode="json"),
                "independent_production_renewal": final_facts.production_renewal.model_dump(
                    mode="json"
                )
                if final_facts.production_renewal is not None
                else None,
                "native_window_evidence": "not_run",
            }
        )
        publish(
            self.directory / "national-playable-qualification.json", report.model_dump(mode="json")
        )
        timing = NativeTimings.model_validate(
            {
                "version": 2,
                "source": "authoritative_native_instants_v2",
                "clock": "monotonic",
                "campaign": self.campaign,
                "advances": [
                    {"tick": i, "elapsed_ns": row.advance_elapsed_ns}
                    for i, row in enumerate(self.advances, 1)
                ],
                "archive_catchups": [
                    {"tick": i, "elapsed_ns": row.archive_elapsed_ns}
                    for i, row in enumerate(self.advances, 1)
                ],
                "cold_reopens": [
                    {"tick": i, "elapsed_ns": row.cold_reopen_elapsed_ns}
                    for i, (_name, row) in enumerate(self.recoveries, 1)
                ],
                "production_reads": [
                    {"tick": row.tick, "elapsed_ns": row.production_read_elapsed_ns}
                    for row in self.material
                ],
                "run": {
                    "periods": self.periods,
                    "compilation_included": False,
                    "elapsed_ns": time.monotonic_ns() - self.started,
                },
            }
        )
        publish(self.directory / "native-timings.json", timing.model_dump(mode="json"))

        def artifact(name: str) -> dict[str, str]:
            return Artifact(
                name=name,
                sha256=memory.executable_digest(
                    self.directory / name,
                ),
            ).model_dump(mode="json")

        manifest = NativeRunEvidence.model_validate(
            {
                "version": 4,
                "scope": "native_material_timing_recovery_join_v4",
                "status": "completed",
                "policy_sha256": self.policy_hash,
                "campaign": self.campaign,
                "foundation_sha256": self.foundation,
                "graph_foundation_sha256": self.opening.opening.graph_foundation_sha256,
                "requested_periods": self.periods,
                "ownership_record_sha256": memory.executable_digest(self.directory / "ownership"),
                "source_manifest_sha256": memory.executable_digest(
                    self.directory / "combined-memory-source.sha256"
                ),
                "executable_manifest_sha256": memory.executable_digest(
                    self.directory / "combined-memory-executables.json"
                ),
                "controls": artifact("native-controls.json"),
                "opening": artifact("material-0.json"),
                "boundaries": [artifact(f"material-{i}.json") for i in range(1, self.periods + 1)],
                "advances": [artifact(f"advance-{i}.json") for i in range(1, self.periods + 1)],
                "archives": [artifact(f"archive-{i}.json") for i in range(1, self.periods + 1)],
                "recoveries": [artifact(name) for name, _row in self.recoveries],
                "aid_originals": [artifact(path.name) for path, _row in originals],
            }
        )
        publish(self.directory / "native-window-evidence.json", manifest.model_dump(mode="json"))

    def run(self) -> int:
        self.prepare()
        writer, reader = self.environments()
        reader.update(
            {
                "BABYLON_QUALIFICATION_POLICY": str(self.directory / "policy.json"),
                "BABYLON_QUALIFICATION_POLICY_SHA256": self.policy_hash,
                "BABYLON_QUALIFICATION_PERIODS": str(self.periods),
                "BABYLON_QUALIFICATION_MATERIAL_DIRECTORY": str(self.directory),
            }
        )
        capture = self.capture()
        choices = tuple(
            choice
            for choice in (
                PlannedChoice(period=1, choice="remote_aid"),
                PlannedChoice(period=2, choice="pause_standing"),
                PlannedChoice(period=3, choice="local_aid"),
            )
            if choice.period <= self.periods
        )
        self.stage = "windowed_new_play_recovery"
        result = drive_pair(
            self.runtime,
            self.client,
            self.root,
            writer,
            reader,
            defines_path=launcher.DEFAULT_DEFINES,
            initial_target=launcher.NewCampaignTarget(UUID(self.campaign), "national-world"),
            initial_tick=0,
            periods=self.periods,
            directory=self.directory,
            operation_timeout=self.timeout,
            on_started=lambda _runtime, _client: self.verify_live(),
            on_boundary=self.on_boundary,
            on_recovery=self.on_recovery,
            choices=choices,
            capture_lifecycle=capture.lifecycle,
        )
        if result:
            raise NativeRunRefusal("windowed national pair did not exit cleanly")
        self.verify_live()
        self.verify_sources()
        self.reports()
        return 0


def main() -> int:
    os.umask(0o077)
    if os.environ.get("BABYLON_SQLITE_QUALIFICATION") == "1":
        from tools.devtools.national_sqlite_qualification_runner import (
            main as sqlite_qualification_main,
        )

        return sqlite_qualification_main()
    run: NativeRun | None = None
    try:
        root = Path(__file__).resolve().parents[2]
        directory = Path(os.environ["BABYLON_STORAGE_REPORT_DIRECTORY"])
        run = NativeRun(root, directory)
        return run.run()
    except (Exception, KeyboardInterrupt, BaseExceptionGroup) as error:
        causes = failure_causes(error)
        if run is not None:
            publish(
                run.directory / "native-run-incomplete.json",
                NativeRunIncomplete(
                    version=2,
                    status="incomplete",
                    last_recorded_stage=run.stage,
                    complete_boundary_records=len(run.boundaries),
                    authenticated_recoveries=len(run.recoveries),
                    failure_type=type(error).__name__,
                    failures=causes,
                ).model_dump(mode="json"),
            )
        print("National native run incomplete: " + type(error).__name__, file=sys.stderr)
        for cause in causes:
            if cause.safe_reason is not None:
                print("Native run refusal: " + cause.safe_reason, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
