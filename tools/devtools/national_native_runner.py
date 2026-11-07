"""Run the owned national fixture through the actual windowed client.

The existing shell supervisor alone provisions and retires the fixture. This
consumer uses its frozen policy, collector, credentials and source capture;
the existing qualification evaluator alone decides admission.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast
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
    verify_frame_png,
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
from tools.devtools.national_windowed_qualification import (
    POLL_SECONDS,
    AidAllocation,
    AidAmounts,
    CollectionAllocation,
    CollectionAmount,
    Command,
    Commitment,
    ControlChannel,
    ControlState,
    Observation,
    PlannedChoice,
    SelectAidPartner,
    UnitAction,
    drive_pair,
    submit_choice,
)
from tools.devtools.wayne_qualification_storage import (
    PrivateEvidence,
    Reference,
    reauthenticate_native_owner,
)


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
        self.wayne_profile = os.environ.get("BABYLON_WAYNE_PROFILE")
        if self.wayne_profile is None:
            if len(fields) != 11 or fields[0] != "national-storage-runner-v1":
                raise NativeRunRefusal("anonymous national runner requires its original ownership")
        else:
            from tools.devtools.wayne_qualification_storage import profile_run

            run = profile_run(self.wayne_profile, "national_storage", str(self.periods), directory)
            if (
                len(fields) != 21
                or fields[0] != "national-storage-runner-media-v2"
                or fields[11] != self.wayne_profile
                or fields[5] != str(run / "pgdata")
                or not fields[12]
                or any(re.fullmatch(r"0|[1-9][0-9]*", item) is None for item in fields[13:21])
            ):
                raise NativeRunRefusal("selected native run requires its complete media owner")
        self.owner_fields = tuple(fields)
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
            "BABYLON_POSTGRES_IMAGE_ID": fields[6],
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
        if self.wayne_profile:
            roster = strict_json_bytes(private_bytes(directory / "normal-binaries.json", 16_384))
            if not isinstance(roster, dict) or set(roster) != {p.name for p in self.binaries}:
                raise NativeRunRefusal(
                    "captured executable roster differs from the normal binaries"
                )
            for binary, digest in self.binaries.items():
                entry = Reference.model_validate(roster[binary.name])
                PrivateEvidence(directory).verify(entry)
                if entry.sha256 != digest:
                    raise NativeRunRefusal(
                        "supervisor build differs from the archived normal executable"
                    )

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
        if (
            not isinstance(ports, dict)
            or set(ports) != {"5432/tcp"}
            or not isinstance(ports["5432/tcp"], list)
        ):
            raise NativeRunRefusal("owned native credentials have no explicit loopback binding")
        bindings = ports["5432/tcp"]
        if (
            len(bindings) != 1
            or not isinstance(bindings[0], dict)
            or bindings[0].get("HostIp") != "127.0.0.1"
        ):
            raise NativeRunRefusal("owned native credential binding differs")
        if (
            getattr(self, "wayne_profile", None)
            and bindings[0].get("HostPort") != self.owner_fields[19]
        ):
            raise NativeRunRefusal("owned native credentials differ from the media lease port")
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
        if self.wayne_profile is not None:
            for suffix in ("state", "data", "config", "cache"):
                common["XDG_" + suffix.upper() + "_HOME"] = str(
                    self.directory.parent / "xdg" / suffix
                )
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

    def capture(
        self, segment: Path | None = None, *, fixed_period: int | None = None
    ) -> memory.RunningMemoryCapture:
        segment = self.directory if segment is None else segment
        if segment != self.directory:
            for filename in ("ownership", "policy.json"):
                PrivateEvidence(segment).publish(filename, (self.directory / filename).read_bytes())
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
        (segment / "combined-memory-source.sha256").write_bytes(
            (self.directory / "source-before.sha256").read_bytes()
        )
        (segment / "combined-memory-sampler-source.py").write_bytes(
            (self.root / "tools/devtools/national_game_memory.py").read_bytes()
        )
        publish(
            segment / "combined-memory-executables.json",
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
            segment / "combined-memory-tooling.json",
            {
                "version": 1,
                "compilation_peak_rss_upper_bound_bytes": None,
                "external_test_tooling_peak_rss_upper_bound_bytes": None,
                "scope": "separate_tooling_not_running_game_compliance",
            },
        )
        expected = {
            key: memory.executable_digest(segment / name)
            for key, name in memory.CAPTURE_FILES.items()
        }
        self._capture = memory.RunningMemoryCapture(
            directory=segment,
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
            cold_segment_period=fixed_period,
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
            row.original_commitment
            for _facts, aid in audits
            for row in aid.independent_practices
            if row.food_consumed
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
                        "tail": {
                            "resolve_tick": record.tick,
                            "tick_content_hash": recovery.source.tick_content_hash,
                            "world_hash": recovery.source.nominal_world_hash,
                        },
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

    def functional_terminal(self, state: ControlState, *, restored: bool = False) -> None:
        from tools.devtools.wayne_qualification_backup import terminal_snapshot

        if (
            state.playing
            or state.advance_pending
            or state.organizer_pending
            or state.lifecycle_pending
            or state.viewed_tick != self.periods
            or state.durable_tick != self.periods
        ):
            raise NativeRunRefusal("functional snapshot requires the installed paused terminal")
        self.verify_live()
        with psycopg.connect(self.writer_dsn, connect_timeout=5) as connection:
            actual = terminal_snapshot(connection, self.campaign, self.periods)
        evidence = PrivateEvidence(self.directory)
        if restored:
            expected = strict_json_bytes(
                evidence.read_reference(
                    evidence.reference("functional-terminal.json"), 64 * 1024 * 1024
                )
            )
            if actual != expected:
                raise NativeRunRefusal(
                    "cold reopened functional terminal differs from the drained original"
                )
            evidence.publish_json("functional-terminal-reopened.json", actual)
        else:
            evidence.publish_json("functional-terminal.json", actual)

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
        if self.wayne_profile == "walk-01":
            WayneWalk(self).drive(writer, reader)
            self.verify_live()
            self.verify_sources()
            self.reports()
            return 0
        capture = self.capture()
        if self.wayne_profile:
            reauthenticate_native_owner(self.root, self.directory, self.owner_fields)
        choices = tuple(
            choice
            for choice in (
                PlannedChoice(
                    period=1,
                    choice="remote_aid",
                    allocation=AidAllocation(aid=AidAmounts(food_quantity=1, cash_micros="0")),
                ),
                PlannedChoice(period=2, choice="pause_standing", allocation="none"),
                PlannedChoice(
                    period=3,
                    choice="local_aid",
                    allocation=AidAllocation(aid=AidAmounts(food_quantity=1, cash_micros="0")),
                ),
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
            on_installed=(
                lambda _channel, _socket, state: (
                    self.functional_terminal(state) if state.durable_tick == self.periods else None
                )
            )
            if self.wayne_profile == "smoke-01"
            else None,
            capture_lifecycle=capture.lifecycle,
        )
        if result:
            raise NativeRunRefusal("windowed national pair did not exit cleanly")
        self.verify_live()
        self.verify_sources()
        self.reports()
        return 0


def retire_wayne(root: Path, evidence: Path, campaign: str, periods: int) -> None:
    from tools.devtools.wayne_qualification_backup import backup_and_retire
    from tools.devtools.wayne_qualification_storage import (
        held_native_lock,
        reauthenticate_native_owner,
    )

    control = held_native_lock(root)
    frozen = private_bytes(evidence / "ownership", 4096)
    if private_bytes(control / "active", 4096) != frozen:
        raise NativeRunRefusal("retained ownership changed before backup")
    owner = tuple(frozen.decode().splitlines())
    if (
        len(owner) != 21
        or owner[10] != str(evidence)
        or (owner[11], periods) not in (("smoke-01", 2), ("walk-01", 10))
    ):
        raise NativeRunRefusal("retained native profile differs from the requested backup")
    if (evidence / "campaign").read_text().strip() != campaign or str(UUID(campaign)) != campaign:
        raise NativeRunRefusal("retained backup campaign differs")
    reauthenticate_native_owner(root, evidence, owner)
    backup_and_retire(root, evidence, owner, campaign, periods)
    retired = strict_json_bytes(private_bytes(evidence / "retired-container.json", 16384))
    pgdata = Path(owner[5]).lstat()
    if (
        not isinstance(retired, dict)
        or retired.get("container") != owner[4]
        or (pgdata.st_dev, pgdata.st_ino) != (int(owner[13]), int(owner[14]))
        or held_native_lock(root) != control
        or private_bytes(control / "active", 4096) != frozen
    ):
        raise NativeRunRefusal("exact stopped removal, retained PGDATA or matching lease differs")
    (control / "active").unlink()


class WayneWalk:
    """Drive one bounded owned campaign through its normal process and UI boundaries."""

    def __init__(self, run: NativeRun) -> None:
        self.run = run
        self.evidence = PrivateEvidence(run.directory)
        self.raw = PrivateEvidence(run.directory.parent / "raw")
        self.originals: dict[str, Commitment] = {}
        self.first_report: str | None = None
        self.processes: list[tuple[int, int, str]] = []
        self.saved: dict[str, object] | None = None
        self.pending: Commitment | None = None
        self.stage = ""
        self.cash_at: int | None = None
        self.extra_collect_at: int | None = None
        self.initial_reports: dict[str, str] = {}
        self.process_start = 0
        self.segment_capture: memory.RunningMemoryCapture | None = None

    def draft(self) -> dict[str, Any]:
        path = (
            self.run.directory.parent
            / "xdg/state/babylon/organizer-drafts"
            / (self.run.campaign + ".json")
        )
        if not os.path.lexists(path):
            return {"sha256": None, "draft": None}
        if path.resolve(strict=True) != path:
            raise NativeRunRefusal("owned campaign draft path is redirected")
        data = private_bytes(path, 64 * 1024)
        draft = strict_json_bytes(data)
        if not isinstance(draft, dict):
            raise NativeRunRefusal("owned draft is not an object")
        return {"sha256": hashlib.sha256(data).hexdigest(), "draft": draft}

    def facts(self, state: ControlState) -> dict[str, Any]:
        """Capture private SQL originals and material marker independently of UI."""
        self.run.verify_live()
        self.run.verify_sources()
        with psycopg.connect(self.run.writer_dsn, connect_timeout=5) as connection:
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            foundation = connection.execute(
                """
                SELECT campaign_id::text,preset_id,encode(content_sha256,'hex'),
                       encode(foundation_sha256,'hex'),encode(graph_foundation_sha256,'hex')
                FROM public.v_observer_material_foundation_v1 WHERE campaign_id=%s::uuid
            """,
                (self.run.campaign,),
            ).fetchone()
            if (
                foundation is None
                or foundation[:2] != (self.run.campaign, "national-world")
                or foundation[3] != state.foundation_sha256
            ):
                raise NativeRunRefusal("installed and persisted national identities differ")
            rows = connection.execute(
                """
                SELECT resolves_period,consumed_period,nonce,command_bytes,commitment_bytes,commitment_sha256
                FROM babylon_state.organizer_command_v1 WHERE campaign_id=%s::uuid ORDER BY resolves_period
            """,
                (self.run.campaign,),
            ).fetchall()
            commands = []
            for period, consumed, nonce, command_bytes, commitment_bytes, commitment_id in rows:
                command = Command.model_validate(strict_json_bytes(bytes(command_bytes)))
                commitment = Commitment.model_validate(strict_json_bytes(bytes(commitment_bytes)))
                if (
                    commitment.command != command
                    or bytes(command.nonce) != bytes(nonce)
                    or bytes(commitment.commitment_id) != bytes(commitment_id)
                    or commitment.resolves_period != period
                    or consumed not in (None, period)
                    or bytes(command.campaign_id) != UUID(self.run.campaign).bytes
                ):
                    raise NativeRunRefusal("native original disagrees with its SQL row")
                commands.append(
                    {
                        "commitment": commitment.model_dump(mode="json"),
                        "consumed_period": consumed,
                        "command_sha256": hashlib.sha256(command_bytes).hexdigest(),
                        "commitment_bytes_sha256": hashlib.sha256(commitment_bytes).hexdigest(),
                    }
                )
            receipts = []
            for receipt_id, actor, period, payload in connection.execute(
                """
                SELECT receipt_id,actor_id,resolve_tick,receipt_bytes FROM babylon_state.organizer_receipt_v1
                WHERE campaign_id=%s::uuid ORDER BY resolve_tick,receipt_id
            """,
                (self.run.campaign,),
            ):
                receipt = strict_json_bytes(bytes(payload))
                if (
                    not isinstance(receipt, dict)
                    or bytes(receipt["receipt_id"]) != bytes(receipt_id)
                    or str(receipt["actor_id"]) != actor
                    or receipt["period"] != period
                ):
                    raise NativeRunRefusal(
                        "receipt identity differs from its committed SQL projection"
                    )
                receipts.append(receipt)
            reports = {}
            for rid, actor, subject, observed, acquired, raw in connection.execute(
                """
                SELECT observation_id,actor_id,subject_id,observed_period,acquired_period,observation_bytes
                FROM babylon_state.organizer_observation_v1 WHERE campaign_id=%s::uuid ORDER BY observation_id
            """,
                (self.run.campaign,),
            ):
                report = Observation.model_validate(strict_json_bytes(bytes(raw)))
                if (
                    bytes(rid) != bytes(report.observation_id)
                    or actor != str(report.actor_id)
                    or subject != str(report.subject_id)
                    or (observed, acquired) != (report.observed_period, report.acquired_period)
                ):
                    raise NativeRunRefusal(
                        "scoped report identity or observed/acquired dates differ"
                    )
                reports[bytes(rid).hex()] = report.model_dump(mode="json")
            grants = connection.execute(
                """
                SELECT subject_kind,subject_id,grant_key,granted_tick,provenance_source_id,provenance_locator
                FROM babylon_meta.archive_knowledge_grant_witness_v1 WHERE campaign_id=%s::uuid
                ORDER BY subject_kind,subject_id,grant_key
            """,
                (self.run.campaign,),
            ).fetchall()
            markers = connection.execute(
                """
                SELECT t.resolve_tick,encode(t.tick_content_hash,'hex'),encode(sha256(m.identity_bytes),'hex')
                FROM babylon_state.tick_commit t JOIN babylon_state.material_tick_v3 m USING(campaign_id,resolve_tick)
                WHERE t.campaign_id=%s::uuid ORDER BY t.resolve_tick
            """,
                (self.run.campaign,),
            ).fetchall()
        if [row[0] for row in markers] != list(range(1, state.durable_tick + 1)) or (
            markers[-1][1] if markers else None
        ) != state.tick_content_hash:
            raise NativeRunRefusal("installed UI does not match the terminal committed marker")
        return {
            "campaign_identity": list(foundation),
            "commands": commands,
            "receipts": receipts,
            "reports": reports,
            "grants": [list(row) for row in grants],
            "markers": [list(row) for row in markers],
            "world_hash": state.world_hash,
            "draft": self.draft(),
        }

    def frame(self, channel: ControlChannel, socket_root: Path, stage: str) -> None:
        anchor = channel.state
        if anchor is None or anchor.playing or anchor.advance_pending or anchor.organizer_pending:
            raise NativeRunRefusal("raw frame requires the installed paused view")
        for resize, width, height, large, scale in (
            ("resize1366x768", 1366, 768, False, "1.0"),
            ("resize1366x768", 1366, 768, True, "1.15"),
            ("resize1920x1080", 1920, 1080, False, "1.25"),
            ("resize1920x1080", 1920, 1080, True, "1.4375"),
        ):
            started = time.monotonic_ns()
            channel.perform("larger_interface" if large else "standard_interface", self.run.timeout)
            changed = channel.perform(cast(UnitAction, resize), self.run.timeout)
            if (
                changed.larger_interface is not large
                or changed.inspector != anchor.inspector
                or changed.campaign_id != anchor.campaign_id
                or changed.durable_tick != anchor.durable_tick
                or changed.viewed_tick != anchor.viewed_tick
                or changed.selected_subject != anchor.selected_subject
                or changed.selected_report_id != anchor.selected_report_id
                or changed.choice != anchor.choice
                or changed.selected_allocation != anchor.selected_allocation
            ):
                raise NativeRunRefusal("capture changed campaign, view, selected report or amounts")
            if stage.endswith("-reviewed"):
                channel.perform("close_inspector", self.run.timeout)
                # A layout action consumed any prior temporary Review witness.
                # Review anew before capture; the final capture preserves this exact nonce for Confirm.
                changed = channel.perform("review", self.run.timeout)
            state = channel.perform("capture_frame", self.run.timeout)
            if state != changed or channel.records[-1].event != "frame_captured":
                raise NativeRunRefusal("capture did not acknowledge the exact settled state")
            raw = private_bytes(socket_root / f"frame-{channel.sequence}.png", 32 * 1024 * 1024)
            verify_frame_png(raw, width, height)
            name = f"{stage}-p{state.viewed_tick}-{width}x{height}-{scale}-seq{channel.sequence}"
            original = self.raw.publish(name + ".png", raw)
            self.raw.publish_json(
                name + ".json",
                {
                    "utc": datetime.now(UTC).isoformat(),
                    "started_monotonic_ns": started,
                    "completed_monotonic_ns": time.monotonic_ns(),
                    "segment": self.stage,
                    "sequence": channel.sequence,
                    "stage": stage,
                    "role": "organizer",
                    "panel": state.inspector,
                    "width": width,
                    "height": height,
                    "scale": scale,
                    "capture": original.model_dump(),
                    "state": state.model_dump(mode="json"),
                },
            )

    def inspect_partner(
        self,
        channel: ControlChannel,
        socket_root: Path,
        kind: Literal["local", "remote"],
        *,
        cite: bool = False,
        stage: str | None = None,
    ) -> str:
        channel.perform("open_relationships", self.run.timeout)
        channel.perform(SelectAidPartner(select_aid_partner=kind), self.run.timeout)
        installed = channel.perform("inspect_subject_evidence", self.run.timeout)
        facts = self.facts(installed)
        rid = installed.selected_report_id
        report = facts["reports"].get(rid)
        if (
            installed.inspector != "Evidence"
            or rid is None
            or report is None
            or installed.selected_report_observed_period != report["observed_period"]
            or installed.selected_report_acquired_period != report["acquired_period"]
            or report["acquired_period"] > installed.viewed_tick
            or report["report"]["kind"] != "partner"
            or installed.selected_subject != f"AidPartner({report['subject_id']})"
        ):
            raise NativeRunRefusal("selected partner report differs from the scoped disclosure")
        label = stage or f"{self.stage}-{kind}-report"
        self.frame(channel, socket_root, label)
        if cite:
            channel.perform("draft_from_report", self.run.timeout)
            draft = self.draft()["draft"]
            if (
                not isinstance(draft, dict)
                or list(bytes.fromhex(rid)) not in draft["references"]
                or draft["selected_reference"] != list(bytes.fromhex(rid))
            ):
                raise NativeRunRefusal("the selected report was not cited in this campaign draft")
            self.first_report = rid
        else:
            channel.perform("close_inspector", self.run.timeout)
        return rid

    def submit(
        self,
        channel: ControlChannel,
        socket_root: Path,
        choice: PlannedChoice,
        label: str,
        *,
        allow_refusal: bool = False,
    ) -> ControlState | None:
        def selected(stage: str, state: ControlState) -> None:
            self.frame(channel, socket_root, label + "-" + stage)
            if stage == "confirmed":
                if state.commitment is None:
                    raise NativeRunRefusal("ordinary Confirm lacks its original")
                self.originals[label] = state.commitment

        return submit_choice(
            channel,
            choice,
            self.run.timeout,
            exercise_editor=label == "collection" or label == "local-food",
            on_stage=selected,
            allow_review_refusal=allow_refusal,
        )

    def capture_stage(self, state: ControlState, label: str) -> dict[str, Any]:
        facts = self.facts(state)
        self.evidence.publish_json(
            label + ".json",
            {
                "utc": datetime.now(UTC).isoformat(),
                "monotonic_ns": time.monotonic_ns(),
                "state": state.model_dump(mode="json"),
                "facts": facts,
            },
        )
        return facts

    def cold_install(self, state: ControlState) -> None:
        elapsed = time.monotonic_ns() - self.process_start
        if elapsed >= self.run.policy.maximum_cold_open_seconds * 1_000_000_000:
            raise NativeRunRefusal(
                "actual new process installation exceeded its cold opening budget"
            )
        self.evidence.publish_json(
            "cold-installed-" + self.stage + ".json",
            {
                "elapsed_ns": elapsed,
                "processes": self.processes[-2:],
                "state": state.model_dump(mode="json"),
                "ownership_sha256": hashlib.sha256(self.run.ownership).hexdigest(),
                "source_head": (self.run.directory / "source-head").read_text().strip(),
            },
        )
        if self.segment_capture is None or state.foundation_sha256 is None:
            raise NativeRunRefusal("cold installation has no captured foundation")
        self.segment_capture.bind_foundation(state.foundation_sha256)
        self.run._foundation = state.foundation_sha256

    def installed(self, channel: ControlChannel, socket_root: Path, state: ControlState) -> None:
        if self.stage == "opening":
            self.frame(channel, socket_root, "opening")
            self.initial_reports["local"] = self.inspect_partner(channel, socket_root, "local")
            self.initial_reports["remote"] = self.inspect_partner(
                channel, socket_root, "remote", cite=True
            )
            if len(set(self.initial_reports.values())) != 2:
                raise NativeRunRefusal("both known partners must disclose distinct opening reports")
            self.submit(
                channel,
                socket_root,
                PlannedChoice(
                    period=1,
                    choice="collect",
                    allocation=CollectionAllocation(
                        collection=CollectionAmount(target_cash_micros="1450000000")
                    ),
                ),
                "collection",
            )
            current = channel.state
            if current is None or current.commitment != self.originals["collection"]:
                raise NativeRunRefusal("P0 collection lacks its accepted original")
            self.pending = current.commitment
            self.saved = self.capture_stage(current, "pending-before-cold")
            return
        if self.stage == "completed":
            fresh = self.capture_stage(state, "completed-after-cold")
            if fresh != self.saved or state.commitment is not None:
                raise NativeRunRefusal(
                    "completed process-cold state differs from the installed terminal"
                )
            self.run.functional_terminal(state, restored=True)
            self.frame(channel, socket_root, "restored-completed")
            return
        tick = state.durable_tick
        if tick == 0:
            fresh = self.capture_stage(state, "pending-after-cold")
            if fresh != self.saved or self.pending is None or state.commitment != self.pending:
                raise NativeRunRefusal(
                    "pending original, reports or draft changed on process-cold Open"
                )
            return
        self.capture_stage(state, f"walk-p{tick}-installed")
        if tick == 1:
            self.submit(
                channel,
                socket_root,
                PlannedChoice(
                    period=2,
                    choice="local_aid",
                    allocation=AidAllocation(aid=AidAmounts(food_quantity=1, cash_micros="0")),
                ),
                "local-food",
            )
        elif tick == 2:
            self.submit(
                channel,
                socket_root,
                PlannedChoice(
                    period=3,
                    choice="remote_aid",
                    allocation=AidAllocation(
                        aid=AidAmounts(food_quantity=2, cash_micros="280000000")
                    ),
                ),
                "remote-mixed",
            )
            current = channel.state
            if current is None or current.commitment is None:
                raise NativeRunRefusal("mixed pending acceptance is absent")
            before = self.capture_stage(current, "mixed-pending-before-reopen")
            after = channel.perform("reopen", self.run.timeout)
            if (
                after.commitment != current.commitment
                or self.capture_stage(after, "mixed-pending-after-reopen") != before
            ):
                raise NativeRunRefusal("pending remote original changed across ordinary reopen")
        elif tick == 3:
            channel.perform("inspect_receipts", self.run.timeout)
            self.frame(channel, socket_root, "dispatch")
            channel.perform("close_inspector", self.run.timeout)
            self.submit(
                channel,
                socket_root,
                PlannedChoice(period=4, choice="pause_standing", allocation="none"),
                "pause-standing",
            )
        else:
            mixed = self.originals["remote-mixed"]
            material = [record.aid for record in self.run.material if record.aid is not None]
            original = list(mixed.commitment_id)
            freight = [
                leg
                for row in material
                for leg in row.selected_aid
                if leg["original_commitment"] == original
            ]
            terminal_food = any(
                leg["outcome"] in ("Granted", "Lost", "Unshipped", "FoodReceivingRefused")
                for leg in freight
            )
            if self.cash_at is None and terminal_food and tick <= self.run.periods - 2:
                label = "local-cash" if self.extra_collect_at is None else "local-cash-retry"
                refused = self.submit(
                    channel,
                    socket_root,
                    PlannedChoice(
                        period=tick + 1,
                        choice="local_aid",
                        allocation=AidAllocation(
                            aid=AidAmounts(food_quantity=0, cash_micros="1000000000")
                        ),
                    ),
                    label,
                    allow_refusal=True,
                )
                if refused is None:
                    self.cash_at = tick
                elif (
                    self.extra_collect_at is None
                    and tick <= self.run.periods - 3
                    and refused.preview is not None
                    and refused.preview.refusal in ("aid_unavailable", "collection_cash_refused")
                ):
                    self.extra_collect_at = tick
                    channel.perform("close_inspector", self.run.timeout)
                    self.submit(
                        channel,
                        socket_root,
                        PlannedChoice(
                            period=tick + 1,
                            choice="collect",
                            allocation=CollectionAllocation(
                                collection=CollectionAmount(target_cash_micros="1450000000")
                            ),
                        ),
                        "additional-collection",
                        allow_refusal=True,
                    )
                else:
                    raise NativeRunRefusal(
                        "actual local cash review refused: "
                        + str(refused.preview.refusal if refused.preview else None)
                    )
            elif self.cash_at is not None and tick == self.cash_at + 2:
                self.inspect_partner(channel, socket_root, "local", stage="cash-following-purchase")
                if tick < self.run.periods:
                    self.submit(
                        channel,
                        socket_root,
                        PlannedChoice(period=tick + 1, choice="resume_standing", allocation="none"),
                        "resume-standing",
                        allow_refusal=True,
                    )
        if tick == self.run.periods:
            self.terminal_navigation(channel, socket_root)
            final = channel.state
            if final is None:
                raise NativeRunRefusal("terminal installed state missing after Return")
            self.saved = self.capture_stage(final, "completed-before-cold")
            self.run.functional_terminal(final)

    def terminal_navigation(self, channel: ControlChannel, socket_root: Path) -> None:
        prior = channel.state
        if prior is None or prior.durable_tick <= 0:
            raise NativeRunRefusal("history requires an installed positive period")
        draft = self.draft()
        original = self.capture_stage(prior, "before-history-archive-return")
        history = channel.perform("previous_period", self.run.timeout)
        if (
            history.viewed_tick != prior.durable_tick - 1
            or history.durable_tick != prior.durable_tick
        ):
            raise NativeRunRefusal("ordinary history changed its durable boundary")
        channel.perform("return_live", self.run.timeout)
        channel.perform("open_relationships", self.run.timeout)
        channel.perform(SelectAidPartner(select_aid_partner="remote"), self.run.timeout)
        before = channel.perform("inspect_subject_evidence", self.run.timeout)
        rid = before.selected_report_id
        if rid is None:
            raise NativeRunRefusal("terminal partner report has no actual evidence identity")
        self.frame(channel, socket_root, "answer-report")
        channel.perform("archive_report", self.run.timeout)
        deadline = time.monotonic() + self.run.policy.maximum_archive_catchup_seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise NativeRunRefusal("restricted Archive report did not become ready")
            reply = channel._exchange("open_archive_evidence", remaining)
            if reply.event == "applied" and reply.reason is None:
                break
            if reply.event != "refused" or reply.reason != "control_stale_or_unavailable":
                raise NativeRunRefusal("ordinary Archive evidence request refused")
            time.sleep(min(POLL_SECONDS, remaining))
        self.frame(channel, socket_root, "archive-report")
        after = channel.perform("open_organizer", self.run.timeout)
        if (
            after.viewed_tick,
            after.durable_tick,
            after.selected_subject,
            after.selected_report_id,
        ) != (
            before.viewed_tick,
            before.durable_tick,
            before.selected_subject,
            rid,
        ) or self.draft() != draft:
            raise NativeRunRefusal("Return changed the report, period or private draft")
        if self.capture_stage(after, "after-history-archive-return") != original:
            raise NativeRunRefusal(
                "history, Archive or Return altered committed facts or the draft"
            )
        self.frame(channel, socket_root, "return")

    def pair(
        self,
        stage: str,
        target: launcher.NewCampaignTarget | launcher.OpenCampaignTarget,
        tick: int,
        closes: int,
        writer: dict[str, str],
        reader: dict[str, str],
    ) -> None:
        self.stage = stage
        main = stage == "walk"
        directory = self.run.directory if main else self.run.directory / ("segment-" + stage)
        if not main:
            directory.mkdir(mode=0o700)
        if self.processes:
            for pid, start, _ in self.processes[-2:]:
                try:
                    present = memory.parse_start_time(Path(f"/proc/{pid}/stat").read_bytes(), pid)
                except FileNotFoundError:
                    continue
                if present == start:
                    raise NativeRunRefusal(
                        "previous owned runtime or client has not exited normally"
                    )
        self.segment_capture = self.run.capture(directory, fixed_period=None if main else tick)

        def started(runtime: subprocess.Popen[bytes], client: subprocess.Popen[bytes]) -> None:
            self.run.verify_live()
            self.run.verify_sources()
            for process, binary in ((runtime, self.run.runtime), (client, self.run.client)):
                proc = Path("/proc") / str(process.pid)
                start = memory.parse_start_time((proc / "stat").read_bytes(), process.pid)
                if (
                    proc.stat().st_uid != os.geteuid()
                    or os.readlink(proc / "exe") != str(binary)
                    or memory.executable_digest(proc / "exe") != self.run.binaries[binary]
                ):
                    raise NativeRunRefusal(
                        "new owned child identity differs from admitted executable"
                    )
                fresh = (process.pid, start, self.run.binaries[binary])
                if fresh in self.processes:
                    raise NativeRunRefusal("a process-cold segment reused its predecessor")
                self.processes.append(fresh)

        reauthenticate_native_owner(self.run.root, self.run.directory, self.run.owner_fields)
        if not main:
            reader = {
                key: value
                for key, value in reader.items()
                if not key.startswith("BABYLON_QUALIFICATION_")
            }
        self.process_start = time.monotonic_ns()
        result = drive_pair(
            self.run.runtime,
            self.run.client,
            self.run.root,
            writer,
            reader,
            defines_path=launcher.DEFAULT_DEFINES,
            initial_target=target,
            initial_tick=tick,
            periods=closes,
            directory=directory,
            operation_timeout=self.run.timeout,
            on_started=started,
            on_boundary=self.run.on_boundary if main else lambda _state: None,
            on_recovery=self.run.on_recovery if main else lambda _state: None,
            on_opened=self.cold_install,
            on_installed=self.installed,
            play_last_close=main,
            capture_lifecycle=self.segment_capture.lifecycle,
        )
        if result:
            raise NativeRunRefusal("owned process pair did not exit normally")

    def drive(self, writer: dict[str, str], reader: dict[str, str]) -> None:
        campaign = UUID(self.run.campaign)
        started = time.monotonic_ns()
        self.pair(
            "opening", launcher.NewCampaignTarget(campaign, "national-world"), 0, 0, writer, reader
        )
        self.pair("walk", launcher.OpenCampaignTarget(campaign), 0, 10, writer, reader)
        self.pair("completed", launcher.OpenCampaignTarget(campaign), 10, 0, writer, reader)
        self.run.verify_live()
        self.run.verify_sources()
        self.evidence.publish_json(
            "walk-wall.json",
            {"start_ns": started, "end_ns": time.monotonic_ns(), "campaign": self.run.campaign},
        )


def main() -> int:
    os.umask(0o077)
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
