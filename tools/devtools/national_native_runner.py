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
import resource
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal, cast
from uuid import UUID

import psycopg
from psycopg.conninfo import conninfo_to_dict
from pydantic import BaseModel, Field, StrictInt, StrictStr
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
    mixed_food_terminal,
    private_bytes,
    verify_frame_png,
    verify_mixed_recovery,
)
from tools.devtools.national_storage_qualification import (
    ArchiveBoundary,
    NativeTimings,
    PlayableBoundary,
    PlayableReport,
    Policy,
    Snapshot,
    measurement_mode,
    selected_policy,
    strict_json_bytes,
)
from tools.devtools.national_windowed_qualification import (
    POLL_SECONDS,
    SMOKE_DECISIONS,
    WALK_FIXED_DECISIONS,
    ActionObservation,
    AidAllocation,
    Bytes32,
    Choice,
    ColdControlWindow,
    CollectionAllocation,
    Command,
    Commitment,
    ControlChannel,
    ControlState,
    FrozenRecord,
    Nonnegative,
    Observation,
    PlannedChoice,
    SelectAidPartner,
    UnitAction,
    drive_pair,
    submit_choice,
    wait_period_ready,
    walk_cash,
    walk_resume,
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


class VerificationSpan(FrozenRecord):
    """Private observer counters, never qualification or mechanical proof."""

    sequence: Nonnegative
    phase: str
    stage: str
    segment: str | None
    tick: Nonnegative | None
    scope_epoch: Nonnegative | None
    generation: Nonnegative | None
    start_monotonic_ns: Nonnegative
    end_monotonic_ns: Nonnegative
    thread_cpu_ns: Nonnegative
    thread_inblock_operations: Nonnegative
    thread_oublock_operations: Nonnegative
    reaped_children_cpu_ns: Nonnegative | None
    reaped_children_inblock_operations: Nonnegative | None
    reaped_children_oublock_operations: Nonnegative | None
    completed: bool


class NativeRun:
    def __init__(self, root: Path, directory: Path) -> None:
        self.mode = measurement_mode(os.environ.get("BABYLON_NATIVE_MEASUREMENT_MODE"))
        self.root = root
        self.directory = directory
        self.policy = Policy.model_validate_json((directory / "policy.json").read_bytes())
        self.policy_hash = memory.executable_digest(directory / "policy.json")
        self.campaign = (directory / "campaign").read_text().strip()
        if str(UUID(self.campaign)) != self.campaign or UUID(self.campaign).int == 0:
            raise NativeRunRefusal("national runner requires its canonical campaign")
        requested = os.environ.get("BABYLON_NATIONAL_STORAGE_PERIODS", "")
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
        if self.wayne_profile not in ("smoke-01", "walk-01", "ordinary-01"):
            raise NativeRunRefusal(
                "native qualification requires a released smoke or walk workload"
            )
        from tools.devtools.wayne_qualification_storage import profile_run, released_head

        selected_policy(directory / "policy.json")
        released_head(PrivateEvidence(directory), root)

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
        self.mixed_recovery: Artifact | None = None
        self.snapshots: list[Snapshot] = []
        self.stage = "admitting_supervisor"
        self.failed_pair: Reference | None = None
        self.segment: str | None = None
        self.pair_identity: list[tuple[int, int, str]] = []
        self.operation_lock = threading.RLock()
        self.verification_spans: list[VerificationSpan] = []
        self.verification_dropped = 0
        self.verification_sequence = 0
        self.verification_state: ControlState | None = None
        self.verification_published = False
        self.verify_live()
        self.verify_credentials(fields[2], fields[7], fields[8])
        self.verify_sources()
        roster = strict_json_bytes(private_bytes(directory / "normal-binaries.json", 16_384))
        if not isinstance(roster, dict) or set(roster) != {p.name for p in self.binaries}:
            raise NativeRunRefusal("captured executable roster differs from the normal binaries")
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
        if bindings[0].get("HostPort") != self.owner_fields[19]:
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
        for suffix in ("state", "data", "config", "cache"):
            common["XDG_" + suffix.upper() + "_HOME"] = str(self.directory.parent / "xdg" / suffix)
        common["BABYLON_RUNTIME_DSN"] = self.writer_dsn
        return launcher.child_environments(
            common,
            launcher.ReaderCredentials(self.observer_dsn, self.reader_dsn),
        )

    def verify_live(self) -> None:
        with self.operation_lock:
            self._verify_supervisor("national_verify_live")

    def _verify_physical_owner(self) -> None:
        self._verify_supervisor("national_verify_physical_owner")

    def _verify_capture_authority(self) -> None:
        self._verify_supervisor("national_verify_live_authority")

    def _verify_supervisor(
        self,
        operation: Literal[
            "national_verify_live",
            "national_verify_physical_owner",
            "national_verify_live_authority",
        ],
    ) -> None:
        if (
            private_bytes(self.lease, 4096) != self.ownership
            or private_bytes(self.directory / "ownership", 4096) != self.ownership
        ):
            raise NativeRunRefusal("national ownership changed during the native run")
        result = subprocess.run(
            [
                "bash",
                "-c",
                'source "$1" && "$2"',
                "national-native",
                str(self.root / "tools/postgres_national_lifecycle.sh"),
                operation,
            ],
            env=self.supervisor,
            cwd=self.root,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if result.returncode or result.stdout:
            raise NativeRunRefusal("national supervisor live ownership admission refused")

    @contextmanager
    def verification_span(self, phase: str, *, children: bool = False) -> Iterator[None]:
        # The released workloads have at most ten closes. Keep even a faulty caller bounded.
        self.verification_sequence += 1
        sequence = self.verification_sequence
        if sequence > 2048:
            self.verification_dropped += 1
            yield
            return
        state = self.verification_state
        stage, segment = self.stage, self.segment
        started = time.monotonic_ns()
        cpu = time.thread_time_ns()
        thread = resource.getrusage(resource.RUSAGE_THREAD)
        child = resource.getrusage(resource.RUSAGE_CHILDREN) if children else None
        completed = False
        try:
            yield
            completed = True
        finally:
            reaped = resource.getrusage(resource.RUSAGE_CHILDREN) if children else None
            finished_thread = resource.getrusage(resource.RUSAGE_THREAD)
            cpu_elapsed = time.thread_time_ns() - cpu
            ended = time.monotonic_ns()
            self.verification_spans.append(
                VerificationSpan(
                    sequence=sequence,
                    phase=phase,
                    stage=stage,
                    segment=segment,
                    tick=state.durable_tick if state is not None else None,
                    scope_epoch=state.scope_epoch if state is not None else None,
                    generation=state.generation if state is not None else None,
                    start_monotonic_ns=started,
                    end_monotonic_ns=ended,
                    thread_cpu_ns=cpu_elapsed,
                    thread_inblock_operations=finished_thread.ru_inblock - thread.ru_inblock,
                    thread_oublock_operations=finished_thread.ru_oublock - thread.ru_oublock,
                    reaped_children_cpu_ns=round(
                        ((reaped.ru_utime + reaped.ru_stime) - (child.ru_utime + child.ru_stime))
                        * 1_000_000_000
                    )
                    if reaped is not None and child is not None
                    else None,
                    reaped_children_inblock_operations=reaped.ru_inblock - child.ru_inblock
                    if reaped is not None and child is not None
                    else None,
                    reaped_children_oublock_operations=reaped.ru_oublock - child.ru_oublock
                    if reaped is not None and child is not None
                    else None,
                    completed=completed,
                )
            )

    def publish_verification_diagnostics(self) -> None:
        if self.verification_published:
            return
        publish(
            self.directory / "verification-diagnostics.json",
            {
                "version": 1,
                "purpose": "diagnostics_only",
                "campaign": self.campaign,
                "mode": self.mode,
                "clock": "monotonic",
                "cpu_scope": "supervisor_thread",
                "child_scope": "all_children_reaped_during_source_shell_including_other_children",
                "block_units": "operations_not_bytes",
                "dropped_spans": self.verification_dropped,
                "spans": [
                    row.model_dump(mode="json")
                    for row in sorted(self.verification_spans, key=lambda row: row.sequence)
                ],
            },
        )
        self.verification_published = True

    def verify_sources(self) -> None:
        with self.verification_span("source-shell", children=True):
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
        for path, digest in self.binaries.items():
            with self.verification_span("executable-" + path.name):
                if memory.executable_digest(path) != digest:
                    raise NativeRunRefusal("national executable changed during the native run")

    def progress(self, tick: int, stage: str, evidence: dict[str, object]) -> None:
        self.stage = stage
        with self.verification_span("progress-" + stage):
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

    def postgres_admission(self) -> memory.PostgresAdmission:
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
        return memory.PostgresAdmission(
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

    def capture(
        self, segment: Path | None = None, *, fixed_period: int | None = None
    ) -> memory.RunningMemoryCapture:
        segment = self.directory if segment is None else segment
        if segment != self.directory:
            for filename in ("ownership", "policy.json"):
                PrivateEvidence(segment).publish(filename, (self.directory / filename).read_bytes())
        admission = self.postgres_admission()
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
            postgres=memory.OwnedPostgresScope(
                admission, self._verify_physical_owner, self._verify_capture_authority
            ),
            read_marker=self.marker,
            sample_gap_seconds=self.policy.maximum_combined_memory_sample_gap_seconds,
            operation_timeout=30,
            operation_lock=self.operation_lock,
            cold_segment_period=fixed_period,
            stop_on_budget=True,
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

    def check_budget(
        self,
        stage: str,
        elapsed_ns: int,
        maximum_seconds: int,
        state: ControlState | None,
        *,
        strict: bool = False,
    ) -> None:
        if self.mode == "memory_capture":
            return
        ceiling = maximum_seconds * 1_000_000_000
        if elapsed_ns > ceiling or strict and elapsed_ns == ceiling:
            self.stage = stage
            publish(
                self.directory / "first-budget-divergence.json",
                {
                    "status": "incomplete",
                    "stage": stage,
                    "elapsed_ns": elapsed_ns,
                    "ceiling_ns": ceiling,
                    "strict": strict,
                    "state": state.model_dump(mode="json") if state else None,
                    "processes": getattr(self, "pair_identity", []),
                    "segment": getattr(self, "segment", None),
                },
            )
            raise NativeRunRefusal(f"{stage} exceeded its released timing budget")

    def on_boundary(self, state: ControlState) -> None:
        self.verification_state = state
        try:
            with self.verification_span("boundary-callback"):
                self._on_boundary(state)
        finally:
            self.verification_state = None

    def _on_boundary(self, state: ControlState) -> None:
        self.verify_sources()
        with self.verification_span("material-admission"):
            if state.campaign_id != self.campaign or state.foundation_sha256 is None:
                raise NativeRunRefusal("native UI admitted a different campaign foundation")
            if state.durable_tick and (
                not state.period_actionable
                or state.period_proof is None
                or state.archive_verified_tick != state.durable_tick
            ):
                raise NativeRunRefusal(
                    "native independent checks require the published period proof"
                )
            record = read_record(
                self.directory / f"material-{state.durable_tick}.json", MaterialRecord
            )
            if (record.tick, record.tick_content_hash) != (
                state.durable_tick,
                state.tick_content_hash,
            ):
                raise NativeRunRefusal(
                    "native material publication differs from its installed UI boundary"
                )
            self.check_budget(
                "production-read",
                record.production_read_elapsed_ns,
                self.policy.maximum_production_read_seconds,
                state,
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
                if self._capture is not None:
                    self._capture.bind_foundation(opening.foundation_sha256)
                self._foundation = opening.foundation_sha256
            self.opening = record
            self.snapshot("opening-created")
            self.progress(0, "native-opening", {"opening": record.opening.model_dump(mode="json")})
            return
        with self.verification_span("advance-proof-binding"):
            if state.foundation_sha256 != self.foundation:
                raise NativeRunRefusal("native UI admitted a different campaign foundation")
            if (
                record.facts is None
                or record.aid is None
                or record.tick != len(self.boundaries) + 1
            ):
                raise NativeRunRefusal(
                    "native committed facts omit or duplicate a requested period"
                )
            advance = read_record(self.directory / f"advance-{record.tick}.json", AdvanceRecord)
            proof = state.period_proof
            if (
                proof is None
                or advance.runtime_scope.campaign_id != self.campaign
                or advance.runtime_scope.epoch != state.scope_epoch
                or advance.foundation_sha256 != self.foundation
                or advance.policy_sha256 != self.policy_hash
                or advance.committed_tail.resolve_tick != record.tick
                or advance.committed_tail.tick_content_hash != record.tick_content_hash
                or advance.committed_tail.world_hash != record.facts.nominal_world_hash
                or proof.request_id != advance.request_id
                or state.advance_request_id != advance.request_id
                or proof.scope_epoch != record.runtime_epoch
                or proof.scope_epoch != state.scope_epoch
                or proof.generation != record.observation_generation
                or proof.generation != state.generation
                or proof.campaign_id != self.campaign
                or proof.tick != record.tick
                or proof.foundation_sha256 != state.foundation_sha256
                or proof.policy_sha256 != self.policy_hash
                or proof.tick_content_hash != record.tick_content_hash
                or proof.world_hash != record.facts.nominal_world_hash
                or proof.envelope_digest != record.facts.envelope_digest
                or proof.archive_verified_tick != record.tick
                or proof.material_record_sha256 != advance.material_record_sha256
                or proof.material_record_sha256
                != memory.executable_digest(self.directory / f"material-{record.tick}.json")
            ):
                raise NativeRunRefusal(
                    "native proof differs from actual material and Advance publication"
                )
        self.progress(record.tick, "committed", advance.model_dump(mode="json"))
        self.check_budget(
            "advance",
            advance.advance_elapsed_ns,
            self.policy.maximum_advance_p95_seconds,
            state,
        )
        self.check_budget(
            "archive-catchup",
            advance.archive_elapsed_ns,
            self.policy.maximum_archive_catchup_seconds,
            state,
        )
        archive = self.archive(record)
        archive_record = read_record(self.directory / f"archive-{record.tick}.json", ArchiveRecord)
        self.check_budget(
            "archive-read",
            archive_record.archive_read_elapsed_ns,
            self.policy.maximum_archive_catchup_seconds,
            state,
        )
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
        if self.wayne_profile == "smoke-01":
            from tools.devtools.national_native_pair import terminal_decisions

            with psycopg.connect(self.writer_dsn, connect_timeout=5) as connection:
                connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                originals = terminal_decisions(connection, self.campaign)
            PrivateEvidence(self.directory).publish_json(
                f"resolved-decisions-{record.tick}.json", originals
            )
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
        self.check_budget(
            "checkpoint-reopen",
            recovery.cold_reopen_elapsed_ns,
            self.policy.maximum_cold_open_seconds,
            state,
            strict=True,
        )
        self.check_budget(
            "restored-production-read",
            recovery.authenticated_read.production_read_elapsed_ns,
            self.policy.maximum_production_read_seconds,
            state,
        )
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
        audit["periods"] = [aid.model_dump(mode="json") for _facts, aid in audits]
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
        completed = time.monotonic_ns()
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
                    "elapsed_ns": completed - self.started,
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
                "version": 6,
                "scope": "native_material_timing_recovery_join_v6",
                "measurement_mode": self.mode,
                "started_monotonic_ns": self.started,
                "completed_monotonic_ns": completed,
                "inputs_sha256": memory.executable_digest(self.directory / "inputs.sha256"),
                "status": "completed",
                "policy_sha256": self.policy_hash,
                "campaign": self.campaign,
                "foundation_sha256": self.foundation,
                "graph_foundation_sha256": self.opening.opening.graph_foundation_sha256,
                "requested_periods": self.periods,
                "ownership_record_sha256": memory.executable_digest(self.directory / "ownership"),
                "source_manifest_sha256": memory.executable_digest(
                    self.directory / "source-before.sha256"
                ),
                "executable_manifest_sha256": memory.executable_digest(
                    self.directory / "normal-binaries.json"
                ),
                "controls": artifact("native-controls.json"),
                "opening": artifact("material-0.json"),
                "boundaries": [artifact(f"material-{i}.json") for i in range(1, self.periods + 1)],
                "advances": [artifact(f"advance-{i}.json") for i in range(1, self.periods + 1)],
                "archives": [artifact(f"archive-{i}.json") for i in range(1, self.periods + 1)],
                "recoveries": [artifact(name) for name, _row in self.recoveries]
                + ([self.mixed_recovery.model_dump(mode="json")] if self.mixed_recovery else []),
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

    def cold_seconds(self) -> int:
        return self.policy.maximum_cold_open_seconds if self.mode == "normal_play" else self.timeout

    def process_identity(
        self, process: subprocess.Popen[bytes], binary: Path
    ) -> tuple[int, int, str]:
        proc = Path("/proc") / str(process.pid)
        start = memory.parse_start_time((proc / "stat").read_bytes(), process.pid)
        if (
            proc.stat().st_uid != os.geteuid()
            or os.readlink(proc / "exe") != str(binary)
            or memory.executable_digest(proc / "exe") != self.binaries[binary]
        ):
            raise NativeRunRefusal("new owned child differs from the admitted executable")
        return process.pid, start, self.binaries[binary]

    def record_processes(self, segment: str) -> None:
        pg = self.postgres_admission()
        publish(
            self.directory / f"processes-{segment}.json",
            {
                "segment": segment,
                "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                "runtime": self.pair_identity[0],
                "client": self.pair_identity[1],
                "postgres": [pg.host_pid, pg.start_time_ticks, pg.executable_sha256],
                "container": pg.container_id,
                "owner_sha256": hashlib.sha256(self.ownership).hexdigest(),
            },
        )

    def ordinary(self, writer: dict[str, str], reader: dict[str, str]) -> int:
        """Run only the independently admitted ordinary prefix, then hand back custody."""
        if self.wayne_profile != "ordinary-01" or self.mode != "normal_play" or self.periods != 10:
            raise NativeRunRefusal(
                "ordinary prefix requires its separate normal ten-period fixture"
            )
        reauthenticate_native_owner(self.root, self.directory, self.owner_fields)
        self.stage = "ordinary-prefix"
        self.segment = "ordinary-prefix"

        def started(runtime: subprocess.Popen[bytes], client: subprocess.Popen[bytes]) -> None:
            self.pair_identity = [
                self.process_identity(process, binary)
                for process, binary in ((runtime, self.runtime), (client, self.client))
            ]
            self.record_processes("ordinary-prefix")
            self.verify_live()
            self.verify_sources()

        result = OrdinaryWarmPrefix(self).drive(writer, reader, on_started=started)
        if result:
            raise NativeRunRefusal("ordinary prefix pair did not exit cleanly")
        self.verify_live()
        self.verify_sources()
        recorded = read_record(self.directory / "ordinary-warm-prefix.json", OrdinaryWarmEvidence)
        marker = self.marker()
        if (
            recorded.status != "completed"
            or len(recorded.samples) != 3
            or marker.campaign != self.campaign
            or marker.campaign_age_ticks != 3
            or marker.foundation_sha256 != recorded.samples[-1].ready.state.foundation_sha256
            or marker.tick_content_hash != recorded.samples[-1].ready.state.tick_content_hash
        ):
            raise NativeRunRefusal("ordinary terminal marker differs from its three-close evidence")
        publish(self.directory / "ordinary-terminal.json", marker.model_dump(mode="json"))
        self.publish_verification_diagnostics()
        return 0

    def run(self) -> int:
        self.prepare()
        if self.marker().foundation_sha256 is not None:
            raise NativeRunRefusal("declared campaign already exists before native New")
        writer, reader = self.environments()
        if self.wayne_profile == "ordinary-01":
            return self.ordinary(writer, reader)
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
            self.publish_verification_diagnostics()
            self.reports()
            return 0
        cold_start = time.monotonic_ns()
        capture = self.capture() if self.mode == "memory_capture" else None
        reauthenticate_native_owner(self.root, self.directory, self.owner_fields)
        self.stage = "windowed_new_play_recovery"
        self.segment = "smoke"

        def started(runtime: subprocess.Popen[bytes], client: subprocess.Popen[bytes]) -> None:
            self.pair_identity = [
                self.process_identity(p, exe)
                for p, exe in ((runtime, self.runtime), (client, self.client))
            ]
            self.record_processes("smoke")
            self.verify_live()

        latest_smoke: ControlState | None = None

        def opened_smoke(ready: ActionObservation) -> None:
            state = ready.state
            elapsed = time.monotonic_ns() - cold_start
            self.check_budget(
                "cold-smoke", elapsed, self.policy.maximum_cold_open_seconds, state, strict=True
            )
            publish(
                self.directory / "cold-installed-smoke.json",
                {
                    "elapsed_ns": elapsed,
                    "started_monotonic_ns": cold_start,
                    "installed_monotonic_ns": cold_start + elapsed,
                    "readiness_sequence": ready.sequence,
                    "state": state.model_dump(mode="json"),
                    "processes": self.pair_identity,
                    "ownership_sha256": hashlib.sha256(self.ownership).hexdigest(),
                    "source_head": (self.directory / "source-head").read_text().strip(),
                },
            )

        def observed_smoke(state: ControlState) -> None:
            nonlocal latest_smoke
            latest_smoke = state
            self.check_budget(
                "smoke-wall",
                time.monotonic_ns() - self.started,
                self.policy.maximum_routine_smoke_seconds,
                state,
            )

        def expired_smoke() -> None:
            self.check_budget(
                "smoke-wall",
                time.monotonic_ns() - self.started,
                self.policy.maximum_routine_smoke_seconds,
                latest_smoke,
                strict=True,
            )

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
            on_started=started,
            cold_window=ColdControlWindow(cold_start, self.cold_seconds()),
            on_opened=opened_smoke,
            on_observed=observed_smoke if self.mode == "normal_play" else None,
            wall_deadline=self.started / 1e9 + self.policy.maximum_routine_smoke_seconds
            if self.mode == "normal_play"
            else None,
            on_wall_expired=expired_smoke if self.mode == "normal_play" else None,
            on_boundary=self.on_boundary,
            on_recovery=self.on_recovery,
            choices=SMOKE_DECISIONS,
            on_installed=(
                lambda _channel, _socket, state: (
                    self.functional_terminal(state) if state.durable_tick == self.periods else None
                )
            ),
            capture_lifecycle=capture.lifecycle if capture else None,
        )
        if result:
            raise NativeRunRefusal("windowed national pair did not exit cleanly")
        self.verify_live()
        self.verify_sources()
        self.publish_verification_diagnostics()
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


class CitationDraft(FrozenRecord):
    schema_version: Annotated[StrictInt, Field(alias="schema", ge=4, le=4)]
    campaign: StrictStr
    workplace: Nonnegative
    choice: Choice
    collection_allocation: Literal["none"] | CollectionAllocation
    aid_allocation: Literal["none"] | AidAllocation
    notes: StrictStr
    references: Annotated[tuple[Bytes32, ...], Field(max_length=32)]
    selected_reference: Bytes32 | None


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
        self.first_observed: ControlState | None = None
        self.latest_observed: ControlState | None = None
        self.segment_capture: memory.RunningMemoryCapture | None = None
        self.failed_frame: tuple[Path, str, int, int] | None = None
        self.attempted: list[tuple[str, int]] = []
        self.launch_stage = ""

    def draft_path(self) -> Path:
        return (
            self.run.directory.parent
            / "xdg/state/babylon/organizer-drafts"
            / (self.run.campaign + ".json")
        )

    def draft(self) -> dict[str, Any]:
        path = self.draft_path()
        if not os.path.lexists(path):
            return {"sha256": None, "draft": None}
        if path.resolve(strict=True) != path:
            raise NativeRunRefusal("owned campaign draft path is redirected")
        data = private_bytes(path, 64 * 1024)
        draft = strict_json_bytes(data)
        if not isinstance(draft, dict):
            raise NativeRunRefusal("owned draft is not an object")
        return {"sha256": hashlib.sha256(data).hexdigest(), "draft": draft}

    def wait_citation(self, rid: str, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        expected = tuple(bytes.fromhex(rid))
        prior_sha: str | None = None
        changed = 0
        while True:
            path = self.draft_path()
            if os.path.lexists(path):
                if path.resolve(strict=True) != path:
                    raise NativeRunRefusal("owned campaign draft path is redirected")
                raw = private_bytes(path, 64 * 1024)
                digest = hashlib.sha256(raw).hexdigest()
                if digest != prior_sha:
                    self.evidence.publish(f"citation-prior-{changed:02}.json", raw)
                    changed += 1
                    prior_sha = digest
                    if len(raw) <= 16_384:
                        draft: CitationDraft | None
                        try:
                            draft = CitationDraft.model_validate(strict_json_bytes(raw))
                        except ValueError:
                            draft = None
                        if (
                            draft is not None
                            and draft.campaign == self.run.campaign
                            and expected in draft.references
                            and len(set(draft.references)) == len(draft.references)
                            and draft.selected_reference == expected
                        ):
                            return
            remaining = deadline - time.monotonic()
            if remaining <= 0 or changed >= 32:
                self.evidence.publish_json(
                    "citation-incomplete.json",
                    {
                        "campaign": self.run.campaign,
                        "selected_reference": rid,
                        "last_sha256": prior_sha,
                        "versions": changed,
                    },
                )
                raise NativeRunRefusal(
                    "autosave deadline elapsed before the exact campaign citation was persisted"
                )
            time.sleep(min(remaining, 0.05))

    def facts(self, state: ControlState) -> dict[str, Any]:
        """Capture private SQL originals and material marker independently of UI."""
        organizer = state.installed_organizer
        if organizer is None or organizer.period != state.durable_tick:
            raise NativeRunRefusal(
                "dated report collection requires the current installed organizer"
            )
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
            receipt_bytes = {}
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
                receipt_bytes[bytes(receipt_id).hex()] = bytes(payload).hex()
            reports = {}
            for rid, actor, subject, observed, acquired, raw in connection.execute(
                """
                SELECT observation_id,actor_id,subject_id,observed_period,acquired_period,observation_bytes
                FROM babylon_state.organizer_observation_v1 WHERE campaign_id=%s::uuid AND actor_id=%s ORDER BY observation_id
            """,
                (self.run.campaign, str(organizer.actor_id)),
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
            "receipt_bytes": receipt_bytes,
            "reports": reports,
            "grants": [list(row) for row in grants],
            "markers": [list(row) for row in markers],
            "world_hash": state.world_hash,
            "draft": self.draft(),
        }

    def observe_failed_frame(
        self, path: Path, name: str, width: int, height: int
    ) -> dict[str, object]:
        limit = 32 * 1024 * 1024
        try:
            with PrivateEvidence(path.parent).file(path.name) as frame:
                length = os.fstat(frame.fileno()).st_size
                raw = frame.read(limit)
        except FileNotFoundError:
            return {"frame_state": "absent", "original_byte_length": None, "capture": None}
        ref = self.raw.publish(name + ".png", raw)
        if max(length, len(raw)) > limit:
            status = "bounded_prefix"
        elif not raw:
            status = "empty"
        else:
            try:
                verify_frame_png(raw, width, height)
            except ValueError:
                status = "partial_or_invalid_png"
            else:
                status = "complete_png"
        return {"frame_state": status, "original_byte_length": length, "capture": ref.model_dump()}

    def retain_stopped_frame(self) -> None:
        if self.failed_frame is not None:
            path, name, width, height = self.failed_frame
            final = name + "-stopped"
            self.raw.publish_json(
                final + ".json",
                {
                    "sequence_file": path.name,
                    "immediate": name + ".json",
                    **self.observe_failed_frame(path, final, width, height),
                },
            )
            self.failed_frame = None

    def capture_frame(
        self,
        channel: ControlChannel,
        socket_root: Path,
        stage: str,
        expected: ControlState,
        width: int,
        height: int,
    ) -> tuple[ControlState, bytes]:
        before = channel.sequence
        try:
            state = channel.perform("capture_frame", self.run.timeout)
            path = socket_root / f"frame-{channel.sequence}.png"
            raw = private_bytes(path, 32 * 1024 * 1024)
            if state != expected or channel.records[-1].event != "frame_captured":
                raise NativeRunRefusal("capture did not acknowledge the exact settled state")
            verify_frame_png(raw, width, height)
            return state, raw
        except BaseException:
            name = f"incomplete-{self.stage}-{stage}-seq{channel.sequence}"
            attempted = channel.sequence > before
            path = socket_root / f"frame-{channel.sequence}.png"
            observed: dict[str, object] = {
                "frame_state": "unsent",
                "original_byte_length": None,
                "capture": None,
            }
            if attempted:
                self.failed_frame = path, name, width, height
                observed = self.observe_failed_frame(path, name, width, height)
            response = (
                self.raw.publish(name + "-response.bin", bytes(channel.response_bytes))
                if attempted and channel.response_bytes
                else None
            )
            self.raw.publish_json(
                name + ".json",
                {
                    "status": "incomplete",
                    "sequence": channel.sequence,
                    "expected": expected.model_dump(mode="json"),
                    "observed": channel.state.model_dump(mode="json") if channel.state else None,
                    "acknowledgement": channel.last_response.model_dump(mode="json")
                    if attempted and channel.last_response
                    else None,
                    "actual_response_bytes": response.model_dump() if response else None,
                    "requested_file": str(path) if attempted else None,
                    "width": width,
                    "height": height,
                    **observed,
                },
            )
            raise

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
            state, raw = self.capture_frame(channel, socket_root, stage, changed, width, height)
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
        if stage == "cash-following-purchase" and report is not None:
            wanted = {
                key
                for key, row in facts["reports"].items()
                if row["actor_id"] == report["actor_id"]
                and row["subject_id"] == report["subject_id"]
                and row["observed_period"] == row["acquired_period"] == installed.viewed_tick
                and row["report"]["kind"] == "partner"
                and row["report"]["facts"]["basis"] == "food_provision"
            }
            seen: set[str] = set()
            while wanted and rid not in wanted:
                if (
                    rid is None
                    or rid in seen
                    or report is None
                    or report["observed_period"] < installed.viewed_tick
                ):
                    raise NativeRunRefusal(
                        "dated food disclosure is absent from the ordinary scoped report list"
                    )
                seen.add(rid)
                installed = channel.perform("next_evidence", self.run.timeout)
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
            path = self.draft_path()
            if os.path.lexists(path):
                if path.resolve(strict=True) != path:
                    raise NativeRunRefusal("owned campaign draft path is redirected")
                self.evidence.publish("citation-before-input.json", private_bytes(path, 64 * 1024))
            channel.perform("draft_from_report", self.run.timeout)
            self.wait_citation(rid, min(10, self.run.timeout))
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

    def observed(self, state: ControlState) -> None:
        if self.first_observed is None:
            self.first_observed = state
        self.latest_observed = state

    def cold_install(self, ready: ActionObservation) -> None:
        state = ready.state
        elapsed = time.monotonic_ns() - self.process_start
        self.run.check_budget(
            "cold-" + self.stage,
            elapsed,
            self.run.policy.maximum_cold_open_seconds,
            state,
            strict=True,
        )
        self.evidence.publish_json(
            "cold-installed-" + self.stage + ".json",
            {
                "elapsed_ns": elapsed,
                "started_monotonic_ns": self.process_start,
                "installed_monotonic_ns": self.process_start + elapsed,
                "readiness_sequence": ready.sequence,
                "processes": self.processes[-2:],
                "state": state.model_dump(mode="json"),
                "ownership_sha256": hashlib.sha256(self.run.ownership).hexdigest(),
                "source_head": (self.run.directory / "source-head").read_text().strip(),
            },
        )
        marker = self.run.marker()
        if state.foundation_sha256 is None or (
            marker.foundation_sha256,
            marker.campaign_age_ticks,
            marker.tick_content_hash,
        ) != (state.foundation_sha256, state.durable_tick, state.tick_content_hash):
            raise NativeRunRefusal(
                "cold installation differs from the committed foundation and tail"
            )
        if self.segment_capture is not None:
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
                WALK_FIXED_DECISIONS[0],
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
                WALK_FIXED_DECISIONS[1],
                "local-food",
            )
        elif tick == 2:
            self.submit(
                channel,
                socket_root,
                WALK_FIXED_DECISIONS[2],
                "remote-mixed",
            )
            current = channel.state
            if current is None or current.commitment is None:
                raise NativeRunRefusal("mixed pending acceptance is absent")
            before = self.capture_stage(current, "mixed-pending-before-reopen")
            after = channel.perform("reopen", self.run.timeout)
            self.run.stage = "mixed-pending-recovery"
            ref = self.evidence.reference(f"recovery-2-{after.scope_epoch}.json")
            recovery = RecoveryRecord.model_validate(
                strict_json_bytes(self.evidence.read_reference(ref, MATERIAL_RECORD_BYTES))
            )
            self.run.check_budget(
                "mixed-pending-reopen",
                recovery.cold_reopen_elapsed_ns,
                self.run.policy.maximum_cold_open_seconds,
                after,
                strict=True,
            )
            self.run.check_budget(
                "mixed-pending-production-read",
                recovery.authenticated_read.production_read_elapsed_ns,
                self.run.policy.maximum_production_read_seconds,
                after,
            )
            verify_mixed_recovery(
                current,
                channel.records[-1],
                self.run.material[-1],
                recovery,
                self.run.policy,
                self.run.policy_hash,
                captured=self.run.mode == "memory_capture",
            )
            if (
                recovery.previous_scope != self.run.recoveries[-1][1].restored_scope
                or recovery.source != self.run.recoveries[-1][1].source
            ):
                raise NativeRunRefusal(
                    "mixed pending recovery differs from its preceding P2 restart"
                )
            self.run.mixed_recovery = Artifact(name=ref.path, sha256=ref.sha256)
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
                WALK_FIXED_DECISIONS[3],
                "pause-standing",
            )
        else:
            mixed = self.originals["remote-mixed"]
            material = [record.aid for record in self.run.material if record.aid is not None]
            terminal_food = mixed_food_terminal(state, material, mixed)
            if self.cash_at is None and terminal_food and tick <= self.run.periods - 2:
                label = "local-cash" if self.extra_collect_at is None else "local-cash-retry"
                refused = self.submit(
                    channel,
                    socket_root,
                    walk_cash(tick + 1),
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
                        WALK_FIXED_DECISIONS[0].at_period(tick + 1),
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
                        walk_resume(tick + 1),
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

    def committed(self, state: ControlState) -> None:
        self.run.on_boundary(state)
        if state.durable_tick:
            self.capture_stage(state, f"walk-p{state.durable_tick}-committed")

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
        focused = (
            self.run.policy.maximum_focused_control_seconds
            if self.run.mode == "normal_play"
            else self.run.timeout
        )
        channel.perform("archive_report", focused)
        deadline = channel.records[-1].completed_monotonic_ns / 10**9 + (
            self.run.policy.maximum_archive_catchup_seconds
            if self.run.mode == "normal_play"
            else self.run.timeout
        )
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise NativeRunRefusal("restricted Archive report did not become ready")
            reply = channel._exchange("open_archive_evidence", min(remaining, focused))
            if reply.event == "applied" and reply.reason is None:
                break
            if reply.event != "refused" or reply.reason != "control_stale_or_unavailable":
                raise NativeRunRefusal("ordinary Archive evidence request refused")
            time.sleep(min(POLL_SECONDS, remaining))
        self.frame(channel, socket_root, "archive-report")
        after = channel.perform("open_organizer", focused)
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
        self.run.stage = "cold-" + stage
        self.run.segment = stage
        self.run.pair_identity = []
        self.attempted = []
        self.launch_stage = "prepare-segment"
        self.first_observed = self.latest_observed = None
        main = stage == "walk"
        directory = self.run.directory if main else self.run.directory / ("segment-" + stage)

        def started(runtime: subprocess.Popen[bytes], client: subprocess.Popen[bytes]) -> None:
            self.launch_stage = "verify-live-owner"
            self.run.verify_live()
            self.launch_stage = "verify-sources"
            self.run.verify_sources()
            for role, process, binary in (
                ("runtime", runtime, self.run.runtime),
                ("client", client, self.run.client),
            ):
                self.launch_stage = "authenticate-" + role
                fresh = self.run.process_identity(process, binary)
                if fresh in self.processes:
                    raise NativeRunRefusal("a process-cold segment reused its predecessor")
                self.processes.append(fresh)
                self.run.pair_identity.append(fresh)
            self.run.record_processes(stage)
            self.launch_stage = "install-and-drive"

        self.process_start = time.monotonic_ns()
        try:
            if not main:
                directory.mkdir(mode=0o700)
            self.launch_stage = "verify-previous-exit"
            if self.processes:
                for pid, start, _ in self.processes[-2:]:
                    try:
                        present = memory.parse_start_time(
                            Path(f"/proc/{pid}/stat").read_bytes(), pid
                        )
                    except FileNotFoundError:
                        continue
                    if present == start:
                        raise NativeRunRefusal(
                            "previous owned runtime or client has not exited normally"
                        )
            self.launch_stage = "prepare-memory-capture"
            self.segment_capture = (
                self.run.capture(directory, fixed_period=None if main else tick)
                if self.run.mode == "memory_capture"
                else None
            )
            self.launch_stage = "reauthenticate-native-owner"
            reauthenticate_native_owner(self.run.root, self.run.directory, self.run.owner_fields)
            if not main:
                reader = {
                    key: value
                    for key, value in reader.items()
                    if not key.startswith("BABYLON_QUALIFICATION_")
                }
            self.launch_stage = "spawn-runtime"
            self.drive_segment(tick, target, closes, writer, reader, directory, started, main)
        except BaseException:
            self.run.failed_pair = self.evidence.publish_json(
                "pair-incomplete-" + stage + ".json",
                {
                    "segment": stage,
                    "stage": self.run.stage,
                    "expected_open_tick": tick,
                    "elapsed_ns": time.monotonic_ns() - self.process_start,
                    "launch_stage": self.launch_stage,
                    "attempted_processes": self.attempted,
                    "authenticated_processes": self.run.pair_identity,
                    "first_observation": self.first_observed.model_dump(mode="json")
                    if self.first_observed
                    else None,
                    "latest_observation": self.latest_observed.model_dump(mode="json")
                    if self.latest_observed
                    else None,
                    "last_accepted_marker": [
                        self.run.boundaries[-1].tick,
                        self.run.boundaries[-1].tick_content_hash,
                    ]
                    if self.run.boundaries
                    else None,
                },
            )
            raise

    def spawned(self, role: Literal["runtime", "client"], process: subprocess.Popen[bytes]) -> None:
        self.attempted.append((role, process.pid))
        self.launch_stage = "spawn-client" if role == "runtime" else "admit-pair"

    def drive_segment(
        self,
        tick: int,
        target: launcher.NewCampaignTarget | launcher.OpenCampaignTarget,
        closes: int,
        writer: dict[str, str],
        reader: dict[str, str],
        directory: Path,
        started: Callable[[subprocess.Popen[bytes], subprocess.Popen[bytes]], None],
        main: bool,
    ) -> None:
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
            on_spawned=self.spawned,
            on_stopped=self.retain_stopped_frame,
            on_boundary=self.committed if main else lambda _state: None,
            on_recovery=self.run.on_recovery if main else lambda _state: None,
            on_opened=self.cold_install,
            on_observed=self.observed,
            cold_window=ColdControlWindow(self.process_start, self.run.cold_seconds()),
            on_installed=self.installed,
            play_penultimate_close=main,
            capture_lifecycle=self.segment_capture.lifecycle if self.segment_capture else None,
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


class OrdinaryWarmSample(FrozenRecord):
    """One ordinary close and its rendered, genuinely usable next decision."""

    period: Annotated[StrictInt, Field(ge=1, le=3)]
    accepted: ActionObservation
    step: ActionObservation
    ready: ActionObservation
    capture: ActionObservation
    next_acceptance: ActionObservation
    png: Reference
    ready_elapsed_ns: Nonnegative
    capture_elapsed_ns: Nonnegative
    usable_elapsed_ns: Nonnegative


class OrdinaryWarmEvidence(FrozenRecord):
    version: Literal[1] = 1
    scope: Literal["ordinary_three_close_tenwalk_prefix_plus_p4_acceptance"] = (
        "ordinary_three_close_tenwalk_prefix_plus_p4_acceptance"
    )
    status: Literal["completed", "incomplete"]
    width: Literal[1366] = 1366
    height: Literal[768] = 768
    audit_enabled: Literal[False] = False
    memory_sampler_enabled: Literal[False] = False
    maximum_usable_elapsed_ns: Literal[10000000000] = 10_000_000_000
    samples: tuple[OrdinaryWarmSample, ...]
    actions: tuple[ActionObservation, ...]
    failures: tuple[NativeFailureCause, ...]


class OrdinaryWarmPrefix:
    """Existing installed callback only; no accounting or qualification claim.

    The caller owns frozen-source/binary admission and the fresh campaign. Drive
    through the existing owned launcher without changing either qualified member.
    """

    def __init__(self, run: NativeRun) -> None:
        self.run = run
        self.walk = WayneWalk(run)
        self.walk.stage = "ordinary-prefix"
        self.used = False

    def drive(
        self,
        writer: dict[str, str],
        reader: dict[str, str],
        *,
        on_started: Callable[[subprocess.Popen[bytes], subprocess.Popen[bytes]], None],
    ) -> int:
        if self.used or os.path.lexists(self.run.directory / "ordinary-warm-prefix.json"):
            raise NativeRunRefusal("ordinary warm prefix refuses repeated execution or evidence")
        environments = [dict(writer), dict(reader)]
        for environment in environments:
            for name in (
                "BABYLON_QUALIFICATION_POLICY",
                "BABYLON_QUALIFICATION_POLICY_SHA256",
                "BABYLON_QUALIFICATION_PERIODS",
                "BABYLON_QUALIFICATION_MATERIAL_DIRECTORY",
            ):
                environment.pop(name, None)
        return drive_pair(
            self.run.runtime,
            self.run.client,
            self.run.root,
            environments[0],
            environments[1],
            defines_path=launcher.DEFAULT_DEFINES,
            initial_target=launcher.NewCampaignTarget(UUID(self.run.campaign), "national-world"),
            initial_tick=0,
            periods=0,
            directory=self.run.directory,
            operation_timeout=self.run.timeout,
            on_started=on_started,
            on_boundary=lambda _state: None,
            on_recovery=lambda _state: None,
            choices=(),
            on_installed=self,
            on_stopped=self.walk.retain_stopped_frame,
            cold_window=ColdControlWindow(
                time.monotonic_ns(), self.run.policy.maximum_cold_open_seconds
            ),
            capture_lifecycle=None,
        )

    @staticmethod
    def require_live(state: ControlState, opening: ControlState, period: int) -> None:
        if (
            not state.period_actionable
            or state.phase != "Ready"
            # The default selected report persists with its inspector closed.
            or state.inspector != "Closed"
            or state.larger_interface
            or state.production_details_open
            or state.period_proof is not None
            or state.advance_request_id is not None
            or state.durable_tick != period
            or state.viewed_tick != period
            or state.generation != opening.generation + period
            or (state.campaign_id, state.scope_epoch, state.foundation_sha256)
            != (opening.campaign_id, opening.scope_epoch, opening.foundation_sha256)
            or period > 0
            and (state.tick_content_hash is None or state.world_hash is None)
        ):
            raise NativeRunRefusal("ordinary warm endpoint lacks its exact live actionable context")

    def accept(self, channel: ControlChannel, planned: PlannedChoice) -> ActionObservation:
        before = len(channel.records)
        submit_choice(channel, planned, self.run.timeout)
        accepted = [record for record in channel.records[before:] if record.action == "confirm"]
        if len(accepted) != 1:
            raise NativeRunRefusal("ordinary next choice lacks exactly one actual acceptance")
        original = accepted[0]
        commitment = original.state.commitment
        if (
            original.event != "acceptance_admitted"
            or original.reason is not None
            or commitment is None
            or commitment.command.choice != planned.choice
            or commitment.command.allocation != planned.allocation
            or commitment.command.expected_period != planned.period - 1
            or commitment.resolves_period != planned.period
        ):
            raise NativeRunRefusal("ordinary accepted original differs from its planned period")
        return original

    def __call__(self, channel: ControlChannel, socket_root: Path, opening: ControlState) -> None:
        destination = self.run.directory / "ordinary-warm-prefix.json"
        if self.used or os.path.lexists(destination):
            raise NativeRunRefusal("ordinary warm prefix refuses repeated execution or evidence")
        self.used = True
        samples: list[OrdinaryWarmSample] = []
        failure: BaseException | None = None
        try:
            self.require_live(opening, opening, 0)
            channel.perform("standard_interface", self.run.timeout)
            current = channel.perform("resize1366x768", self.run.timeout)
            self.require_live(current, opening, 0)
            accepted = self.accept(channel, WALK_FIXED_DECISIONS[0])
            for period in range(1, 4):
                channel.perform("step", self.run.timeout)
                step = channel.records[-1]
                current = wait_period_ready(channel, self.run.timeout)
                ready = channel.records[-1]
                self.require_live(current, opening, period)
                if (
                    step.action != "step"
                    or step.event != "committed_and_installed"
                    or ready.action != "status"
                    or ready.event != "observed"
                    or ready.reason is not None
                    or step.state.period_identity() != ready.state.period_identity()
                ):
                    raise NativeRunRefusal(
                        "ordinary warm close lacks its first strict ready status"
                    )
                _, pixels = self.walk.capture_frame(
                    channel, socket_root, f"p{period}", current, 1366, 768
                )
                capture = channel.records[-1]
                png = self.walk.raw.publish(f"ordinary-p{period}-seq{capture.sequence}.png", pixels)
                self.walk.raw.publish_json(
                    f"ordinary-p{period}-seq{capture.sequence}.json",
                    capture.model_dump(mode="json"),
                )
                following = self.accept(channel, WALK_FIXED_DECISIONS[period])
                self.require_live(following.state, opening, period)
                if following.state.period_identity() != ready.state.period_identity():
                    raise NativeRunRefusal("ordinary next acceptance changed its captured source")
                samples.append(
                    OrdinaryWarmSample(
                        period=period,
                        accepted=accepted,
                        step=step,
                        ready=ready,
                        capture=capture,
                        next_acceptance=following,
                        png=png,
                        ready_elapsed_ns=ready.completed_monotonic_ns - step.started_monotonic_ns,
                        capture_elapsed_ns=capture.completed_monotonic_ns
                        - step.started_monotonic_ns,
                        usable_elapsed_ns=max(
                            capture.completed_monotonic_ns, following.completed_monotonic_ns
                        )
                        - step.started_monotonic_ns,
                    )
                )
                accepted = following
            if any(sample.usable_elapsed_ns > 10_000_000_000 for sample in samples):
                raise NativeRunRefusal("ordinary warm usable endpoint exceeded ten seconds")
        except BaseException as error:
            failure = error
            raise
        finally:
            report = OrdinaryWarmEvidence(
                status="incomplete" if failure else "completed",
                samples=tuple(samples),
                actions=tuple(channel.records),
                failures=failure_causes(failure) if failure else (),
            )
            self.walk.evidence.publish_json(destination.name, report.model_dump(mode="json"))


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
            try:
                run.publish_verification_diagnostics()
            except BaseException as diagnostic_error:
                raise BaseExceptionGroup(
                    "native run and diagnostic publication failed", [error, diagnostic_error]
                ) from None
            publish(
                run.directory / "native-run-incomplete.json",
                NativeRunIncomplete(
                    version=3,
                    failed_pair=run.failed_pair,
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
