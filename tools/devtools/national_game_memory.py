"""Read kernel memory counters and quiesce the launcher's exact native children.

The existing supervisor owns campaign/database admission. Sequential readings
remain incomplete diagnostics; native suspension alone never admits PostgreSQL
or establishes a complete running-game sample.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import re
import select
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from pydantic import StrictBool, StrictStr, field_validator, model_validator
from tools.devtools.national_storage_qualification import (
    CombinedMemoryEvidence,
    FrozenRecord,
    MemoryProcess,
    MemoryRole,
    MemorySample,
    Nonnegative,
    Policy,
    Positive,
    Sha256,
)

MAX_INTEGER = 2**63 - 1
COUNTERS = {
    "Rss": "rss_bytes",
    "Pss": "pss_bytes",
    "Swap": "swap_bytes",
    "Private_Hugetlb": "private_hugetlb_bytes",
    "Shared_Hugetlb": "shared_hugetlb_bytes",
}
CAPTURE_FILES = {
    "policy_sha256": "policy.json",
    "ownership_record_sha256": "ownership",
    "source_manifest_sha256": "combined-memory-source.sha256",
    "executable_manifest_sha256": "combined-memory-executables.json",
    "capture_implementation_sha256": "combined-memory-sampler-source.py",
    "tooling_report_sha256": "combined-memory-tooling.json",
}


class CaptureRefusal(ValueError):
    """A safe specific refusal without process command, environment or lease data."""


class KernelRecordMissing(CaptureRefusal):
    """A missing record, distinguishable from permission or malformed data."""


class ThreadCensusChanged(CaptureRefusal):
    """Verified task membership changed while the exact process remained live."""


class DockerOperationRefusal(CaptureRefusal):
    def __init__(self, operation: str, exit_code: int, diagnostic: bytes) -> None:
        super().__init__(f"owned Docker {operation} refused with exit code {exit_code}")
        # The operator may retain this locally after inspecting its scope. It
        # never appears in the public exception, progress or qualification data.
        self.private_diagnostic = diagnostic[:65_536]


def _sampler_clock() -> int | None:
    return time.monotonic_ns() if os.environ.get("BABYLON_TIMINGS") == "1" else None


def _sampler_timing(
    stage: str,
    started_ns: int | None,
    *,
    sequence: int | None = None,
    restored: bool | None = None,
    body_failed: bool | None = None,
) -> None:
    if started_ns is None:
        return
    record: dict[str, int | str | bool] = {
        "version": 1,
        "scope": "sampler_timing_not_memory_qualification",
        "stage": stage,
        "elapsed_ns": time.monotonic_ns() - started_ns,
    }
    for key, value in (
        ("sequence", sequence),
        ("restored", restored),
        ("body_failed", body_failed),
    ):
        if value is not None:
            record[key] = value
    sys.stderr.write(json.dumps(record, separators=(",", ":")) + "\n")


@contextmanager
def _timed_sampler_stage(stage: str, sequence: int) -> Iterator[None]:
    started = _sampler_clock()
    try:
        yield
    finally:
        _sampler_timing(stage, started, sequence=sequence)


class ProcessBinding(FrozenRecord):
    pid: Positive
    start_time_ticks: Nonnegative
    role: MemoryRole
    executable_sha256: Sha256


class ProcessStat(FrozenRecord):
    pid: Positive
    parent_pid: Nonnegative
    start_time_ticks: Nonnegative
    state: Literal["R", "S", "D", "T", "t", "Z", "X", "I", "W", "K", "P"]


class ThreadObservation(FrozenRecord):
    tid: Positive
    start_time_ticks: Nonnegative
    state: StrictStr
    children: tuple[Positive, ...]


class SequentialBatch(FrozenRecord):
    boot_id: StrictStr
    monotonic_ns: Nonnegative
    capture_duration_ns: Nonnegative
    processes: tuple[MemoryProcess, ...]
    simultaneous_capture: Literal["sequential_unstopped"] = "sequential_unstopped"


class AgeMarker(FrozenRecord):
    campaign_age_ticks: Nonnegative
    tick_content_hash: Sha256 | None

    @model_validator(mode="after")
    def committed_identity(self) -> AgeMarker:
        if (self.campaign_age_ticks == 0) != (self.tick_content_hash is None):
            raise ValueError("age must bind its actual authenticated committed marker")
        return self


class CampaignMemoryMarker(AgeMarker):
    campaign: StrictStr
    foundation_sha256: Sha256 | None

    @model_validator(mode="after")
    def actual_campaign(self) -> CampaignMemoryMarker:
        if str(UUID(self.campaign)) != self.campaign or UUID(self.campaign).int == 0:
            raise ValueError("memory capture requires an authenticated canonical campaign")
        if self.foundation_sha256 is None and self.campaign_age_ticks:
            raise ValueError("absent campaign foundation cannot have a committed period")
        return self


class UnassignedMemoryCapture(FrozenRecord):
    """Retain a publication crossing without assigning its counters to either state."""

    version: Literal[1]
    scope: Literal["unassigned_capture_not_memory_qualification"]
    boot_id: StrictStr
    before: CampaignMemoryMarker
    after: CampaignMemoryMarker
    monotonic_ns: Nonnegative
    capture_duration_ns: Nonnegative
    processes: tuple[MemoryProcess, ...]

    @field_validator("version", mode="before")
    @classmethod
    def exact_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("unassigned capture version must be an exact integer")
        return value

    @model_validator(mode="after")
    def normal_publication(self) -> UnassignedMemoryCapture:
        before, after = self.before, self.after
        if (
            before.campaign != after.campaign
            or (
                before.foundation_sha256 is not None
                and before.foundation_sha256 != after.foundation_sha256
            )
            or after.campaign_age_ticks < before.campaign_age_ticks
            or (
                before.foundation_sha256 == after.foundation_sha256
                and before.campaign_age_ticks == after.campaign_age_ticks
            )
        ):
            raise ValueError("memory committed identity regressed or was replaced")
        pids = tuple(process.pid for process in self.processes)
        if not pids or len(set(pids)) != len(pids):
            raise ValueError("unassigned capture requires a unique nonempty process roster")
        return self


class PublicationAdvanced(CaptureRefusal):
    def __init__(self, record: UnassignedMemoryCapture) -> None:
        super().__init__("committed game identity advanced during capture")
        self.record = record


class QuiescentBatch(FrozenRecord):
    boot_id: StrictStr
    sample: MemorySample


class PostgresAdmission(FrozenRecord):
    """Facts supplied after the existing supervisor verifies its private lease."""

    container_id: Sha256
    image_id: StrictStr
    host_pid: Positive
    start_time_ticks: Nonnegative
    uid: Nonnegative
    gid: Nonnegative
    cgroup_directory: Path
    cgroup_device: Nonnegative
    cgroup_inode: Positive
    executable_sha256: Sha256

    @model_validator(mode="after")
    def exact_paths(self) -> PostgresAdmission:
        if re.fullmatch(r"sha256:[0-9a-f]{64}", self.image_id) is None:
            raise ValueError("admitted PostgreSQL image identity malformed")
        if (
            not self.cgroup_directory.is_absolute()
            or self.cgroup_directory != Path(os.path.normpath(self.cgroup_directory))
            or not self.cgroup_directory.is_relative_to("/sys/fs/cgroup")
        ):
            raise ValueError("admitted cgroup path must be normalized and absolute")
        return self


class DockerState(FrozenRecord):
    container_id: Sha256
    image_id: StrictStr
    host_pid: Positive
    running: StrictBool
    paused: StrictBool


def read_kernel_record(path: Path, *, allow_empty: bool = False) -> bytes:
    """One bounded kernel record; unavailable records never become zero."""
    try:
        with path.open("rb", buffering=0) as source:
            raw = source.read(65_536)
            if (not raw and not allow_empty) or len(raw) == 65_536 or source.read(1):
                raise CaptureRefusal("kernel record unavailable or exceeds capture bound")
            return raw
    except (FileNotFoundError, ProcessLookupError):
        raise KernelRecordMissing("admitted process or scope disappeared") from None
    except PermissionError:
        raise CaptureRefusal("kernel record permission refused") from None
    except OSError:
        raise CaptureRefusal("kernel record read failed") from None


def parse_process_stat(raw: bytes, pid: int) -> ProcessStat:
    # comm can contain spaces, newlines and ')'; its numeric suffix cannot.
    closing = raw.rfind(b")")
    if type(pid) is not int or pid <= 0 or not raw.startswith(f"{pid} (".encode()) or closing < 0:
        raise CaptureRefusal("process stat identity malformed")
    suffix = raw[closing + 1 :].split()
    if len(suffix) < 20 or not suffix[1].isdigit() or not suffix[19].isdigit():
        raise CaptureRefusal("process stat start/parent identity unavailable")
    if suffix[0] not in {b"R", b"S", b"D", b"T", b"t", b"Z", b"X", b"I", b"W", b"K", b"P"}:
        raise CaptureRefusal("process stat state unsupported")
    parent, start = int(suffix[1]), int(suffix[19])
    if max(pid, parent, start) > MAX_INTEGER:
        raise CaptureRefusal("process stat identity exceeds capture range")
    return ProcessStat.model_validate(
        {"pid": pid, "parent_pid": parent, "start_time_ticks": start, "state": suffix[0].decode()}
    )


def parse_start_time(raw: bytes, pid: int) -> int:
    return parse_process_stat(raw, pid).start_time_ticks


def parse_rollup(raw: bytes) -> dict[str, int]:
    values: dict[str, int] = {}
    for line in raw.splitlines():
        tokens = line.split()
        if not tokens:
            continue
        name = tokens[0].removesuffix(b":").decode("ascii", errors="replace")
        if name not in COUNTERS:
            continue
        if name in values or len(tokens) != 3 or tokens[2] != b"kB" or not tokens[1].isdigit():
            raise CaptureRefusal("required smaps_rollup counter malformed or duplicated")
        amount = int(tokens[1]) * 1024
        if amount > MAX_INTEGER:
            raise CaptureRefusal("smaps_rollup counter exceeds capture range")
        values[name] = amount
    if set(values) != set(COUNTERS) or values["Pss"] > values["Rss"]:
        raise CaptureRefusal("required smaps_rollup counters absent or inconsistent")
    return {COUNTERS[key]: amount for key, amount in values.items()}


def parse_process_ids(raw: bytes) -> tuple[int, ...]:
    rows = raw.split()
    if any(not re.fullmatch(rb"[1-9][0-9]*", row) for row in rows):
        raise CaptureRefusal("process census malformed")
    pids = tuple(int(row) for row in rows)
    if any(pid > MAX_INTEGER for pid in pids) or len(pids) != len(set(pids)):
        raise CaptureRefusal("process census duplicated or out of range")
    return tuple(sorted(pids))


def cgroup_members(admitted_directory: Path) -> tuple[int, ...]:
    """Close a complete domain subtree census; the caller must admit ownership."""
    if admitted_directory.is_symlink() or not admitted_directory.is_dir():
        raise CaptureRefusal("admitted cgroup subtree unavailable")

    def census() -> tuple[tuple[tuple[str, int, int], ...], tuple[int, ...]]:
        def walk_refusal(_error: OSError) -> None:
            raise CaptureRefusal("admitted cgroup subtree unreadable") from None

        directories: list[tuple[str, int, int]] = []
        pids: list[int] = []
        for parent, children, _files in os.walk(
            admitted_directory, onerror=walk_refusal, followlinks=False
        ):
            children.sort()
            directory = Path(parent)
            if directory.is_symlink() or any(
                (directory / child).is_symlink() for child in children
            ):
                raise CaptureRefusal("cgroup subtree contains a symlink")
            if read_kernel_record(directory / "cgroup.type").strip() != b"domain":
                raise CaptureRefusal("threaded or unsupported cgroup subtree refused")
            identity = directory.stat()
            directories.append((str(directory), identity.st_dev, identity.st_ino))
            pids.extend(
                parse_process_ids(read_kernel_record(directory / "cgroup.procs", allow_empty=True))
            )
        if not directories:
            raise CaptureRefusal("admitted cgroup root process census missing")
        if len(pids) != len(set(pids)):
            raise CaptureRefusal("process moved during cgroup census")
        return tuple(directories), tuple(sorted(pids))

    before, after = census(), census()
    if before != after:
        raise CaptureRefusal("cgroup subtree or membership changed during capture")
    return before[1]


def verify_cgroup_frozen(directory: Path) -> None:
    events: dict[bytes, bytes] = {}
    for line in read_kernel_record(directory / "cgroup.events").splitlines():
        fields = line.split()
        if len(fields) != 2 or fields[0] in events or fields[1] not in {b"0", b"1"}:
            raise CaptureRefusal("cgroup freezer barrier malformed")
        events[fields[0]] = fields[1]
    if events.get(b"frozen") != b"1":
        raise CaptureRefusal("admitted cgroup is not frozen")


@dataclass(frozen=True)
class _ExecutableIdentity:
    device: int
    inode: int
    size: int
    modified_ns: int
    changed_ns: int

    @classmethod
    def from_stat(cls, record: os.stat_result) -> _ExecutableIdentity:
        if not stat.S_ISREG(record.st_mode):
            raise CaptureRefusal("admitted executable is not a regular file")
        return cls(
            record.st_dev, record.st_ino, record.st_size, record.st_mtime_ns, record.st_ctime_ns
        )


def _executable_identity(path: Path) -> _ExecutableIdentity:
    try:
        return _ExecutableIdentity.from_stat(path.stat())
    except FileNotFoundError:
        raise CaptureRefusal("admitted executable disappeared") from None
    except PermissionError:
        raise CaptureRefusal("executable provenance permission refused") from None
    except OSError:
        raise CaptureRefusal("executable provenance read failed") from None


def _authenticate_executable(path: Path) -> tuple[str, _ExecutableIdentity]:
    """Authenticate bytes and bind them to one unchanged running file inode."""
    try:
        with path.open("rb") as executable:
            before = _ExecutableIdentity.from_stat(os.fstat(executable.fileno()))
            digest = hashlib.file_digest(executable, "sha256").hexdigest()
            after = _ExecutableIdentity.from_stat(os.fstat(executable.fileno()))
            if before != after or after != _executable_identity(path):
                raise CaptureRefusal("executable changed during authentication")
            return digest, after
    except FileNotFoundError:
        raise CaptureRefusal("admitted executable disappeared") from None
    except PermissionError:
        raise CaptureRefusal("executable provenance permission refused") from None
    except OSError:
        raise CaptureRefusal("executable provenance read failed") from None


def executable_digest(path: Path) -> str:
    """Hash the running executable inode through its kernel magic link."""
    return _authenticate_executable(path)[0]


def observe_process(binding: ProcessBinding, proc_root: Path = Path("/proc")) -> MemoryProcess:
    directory = proc_root / str(binding.pid)
    before = parse_start_time(read_kernel_record(directory / "stat"), binding.pid)
    if before != binding.start_time_ticks:
        raise CaptureRefusal("admitted PID incarnation differs")
    if executable_digest(directory / "exe") != binding.executable_sha256:
        raise CaptureRefusal("admitted executable provenance differs")
    counters = parse_rollup(read_kernel_record(directory / "smaps_rollup"))
    if parse_start_time(read_kernel_record(directory / "stat"), binding.pid) != before:
        raise CaptureRefusal("PID incarnation changed during observation")
    if executable_digest(directory / "exe") != binding.executable_sha256:
        raise CaptureRefusal("executable changed during observation")
    return MemoryProcess.model_validate({**binding.model_dump(), **counters})


def boot_identity(proc_root: Path = Path("/proc")) -> str:
    try:
        boot = read_kernel_record(proc_root / "sys/kernel/random/boot_id").decode("ascii").strip()
        if str(UUID(boot)) != boot:
            raise ValueError
    except (ValueError, UnicodeError):
        raise CaptureRefusal("kernel boot identity malformed") from None
    return boot


def collect_sequential(
    bindings: tuple[ProcessBinding, ...], proc_root: Path = Path("/proc")
) -> SequentialBatch:
    if not bindings or len({binding.pid for binding in bindings}) != len(bindings):
        raise CaptureRefusal("observation requires unique nonempty process bindings")
    started = time.monotonic_ns()
    boot = boot_identity(proc_root)
    rows = tuple(observe_process(binding, proc_root) for binding in bindings)
    if boot_identity(proc_root) != boot:
        raise CaptureRefusal("kernel boot identity changed")
    return SequentialBatch(
        boot_id=boot,
        monotonic_ns=started,
        capture_duration_ns=time.monotonic_ns() - started,
        processes=rows,
    )


def diagnostic_sample(
    batch: SequentialBatch,
    sequence: int,
    age: AgeMarker,
    native_client_mode: Literal["windowed", "headless", "not_running"],
) -> MemorySample:
    return MemorySample(
        sequence=sequence,
        foundation_sha256=None,
        **age.model_dump(),
        monotonic_ns=batch.monotonic_ns,
        capture_duration_ns=batch.capture_duration_ns,
        simultaneous_capture="sequential_unstopped",
        roster_complete="incomplete",
        native_client_mode=native_client_mode,
        processes=batch.processes,
    )


def verify_frozen_files(directory: Path, expected: Mapping[str, str]) -> dict[str, str]:
    if set(expected) != set(CAPTURE_FILES):
        raise CaptureRefusal("frozen capture binding set incomplete")
    digests: dict[str, str] = {}
    for key, name in CAPTURE_FILES.items():
        if not re.fullmatch(r"[0-9a-f]{64}", expected[key]):
            raise CaptureRefusal("frozen capture binding digest invalid")
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise CaptureRefusal("frozen capture file missing or redirected")
        digests[key] = executable_digest(path)
        if digests[key] != expected[key]:
            raise CaptureRefusal("frozen capture binding changed")
    return digests


def thread_census(
    binding: ProcessBinding, proc_root: Path = Path("/proc")
) -> tuple[ThreadObservation, ...]:
    directory = proc_root / str(binding.pid)

    def verify_incarnation() -> None:
        if (
            parse_start_time(read_kernel_record(directory / "stat"), binding.pid)
            != binding.start_time_ticks
        ):
            raise CaptureRefusal("native PID incarnation differs")

    def tasks() -> tuple[Path, ...]:
        return tuple(sorted((directory / "task").iterdir(), key=lambda path: int(path.name)))

    verify_incarnation()
    try:
        task_paths = tasks()
        if not task_paths:
            raise CaptureRefusal("native thread census empty")
        result = []
        try:
            for task in task_paths:
                row = parse_process_stat(read_kernel_record(task / "stat"), int(task.name))
                children = parse_process_ids(
                    read_kernel_record(task / "children", allow_empty=True)
                )
                result.append(
                    ThreadObservation(
                        tid=row.pid,
                        start_time_ticks=row.start_time_ticks,
                        state=row.state,
                        children=children,
                    )
                )
        except KernelRecordMissing:
            # A vanished task can be ordinary worker retirement. Establish the
            # exact live process and a changed task set before permitting retry.
            # Missing process identity, unchanged membership and access failures
            # remain fatal; no partially read census is returned.
            verify_incarnation()
            after = tasks()
            verify_incarnation()
            if task_paths != after:
                raise ThreadCensusChanged("native thread census changed") from None
            raise
        after = tasks()
        verify_incarnation()
        if task_paths != after:
            raise ThreadCensusChanged("native thread census changed")
    except (OSError, ValueError) as error:
        if isinstance(error, CaptureRefusal):
            raise
        raise CaptureRefusal("native thread census unavailable") from None
    return tuple(result)


def stable_thread_census(binding: ProcessBinding, deadline: float) -> tuple[ThreadObservation, ...]:
    """Retry only verified running-task races within the owning operation's budget."""
    while time.monotonic() < deadline:
        try:
            return thread_census(binding)
        except ThreadCensusChanged:
            time.sleep(min(0.005, max(0, deadline - time.monotonic())))
    raise CaptureRefusal("native stable thread census deadline exceeded")


def wait_native_stopped(binding: ProcessBinding, deadline: float) -> tuple[ThreadObservation, ...]:
    previous: tuple[ThreadObservation, ...] | None = None
    while time.monotonic() < deadline:
        try:
            current = thread_census(binding)
        except ThreadCensusChanged:
            previous = None
            time.sleep(min(0.005, max(0, deadline - time.monotonic())))
            continue
        if any(row.children for row in current):
            raise CaptureRefusal("unadmitted native subprocess descendant")
        if all(row.state == "T" for row in current) and current == previous:
            return current
        previous = current
        time.sleep(min(0.005, max(0, deadline - time.monotonic())))
    raise CaptureRefusal("native all-thread suspension deadline exceeded")


def verify_native_stopped(
    binding: ProcessBinding, witness: tuple[ThreadObservation, ...], deadline: float
) -> None:
    """Revalidate one exact frozen census without starting another stabilization."""
    if time.monotonic() >= deadline:
        raise CaptureRefusal("native frozen-census verification deadline exceeded")
    current = thread_census(binding)
    if current != witness:
        raise CaptureRefusal("frozen native thread census changed")
    if time.monotonic() >= deadline:
        raise CaptureRefusal("native frozen-census verification deadline exceeded")


def wait_native_resumed(descriptor: int, binding: ProcessBinding, deadline: float) -> None:
    poller = select.poll()
    poller.register(descriptor, select.POLLIN)
    while time.monotonic() < deadline:
        if poller.poll(0):
            return
        try:
            threads = thread_census(binding)
        except ThreadCensusChanged:
            time.sleep(min(0.005, max(0, deadline - time.monotonic())))
            continue
        except CaptureRefusal:
            if poller.poll(0):
                return
            raise
        if all(row.state not in {"T", "t"} for row in threads):
            return
        time.sleep(min(0.005, max(0, deadline - time.monotonic())))
    raise CaptureRefusal("native restoration all-thread deadline exceeded")


class OwnedNativePair:
    """Own pidfds from actual live Popen handles; never select arbitrary PIDs.

    This scope controls only the two direct children. Any descendant causes
    refusal. A quiescent context restores every stop requested by this owner,
    including a request whose all-thread barrier subsequently failed.
    """

    def __init__(
        self,
        runtime: subprocess.Popen[bytes],
        client: subprocess.Popen[bytes],
        *,
        runtime_sha256: str,
        client_sha256: str,
    ) -> None:
        self._children = (runtime, client)
        self._pidfds: list[int] = []
        self._identities: tuple[_ExecutableIdentity, ...] = ()
        self._capture_lock = threading.Lock()
        self.bindings: tuple[ProcessBinding, ...] = ()
        try:
            bindings = []
            identities = []
            for child, role, digest in (
                (runtime, "engine-runtime", runtime_sha256),
                (client, "native-client", client_sha256),
            ):
                if child.poll() is not None:
                    raise CaptureRefusal("owned native child already exited")
                descriptor = os.pidfd_open(child.pid, 0)
                self._pidfds.append(descriptor)
                stat = parse_process_stat(
                    read_kernel_record(Path(f"/proc/{child.pid}/stat")), child.pid
                )
                binding = ProcessBinding.model_validate(
                    {
                        "pid": child.pid,
                        "start_time_ticks": stat.start_time_ticks,
                        "role": role,
                        "executable_sha256": digest,
                    }
                )
                identities.append(self._verify(child, descriptor, binding))
                bindings.append(binding)
            if runtime.pid == client.pid:
                raise CaptureRefusal("native pair requires distinct owned children")
            self.bindings = tuple(bindings)
            self._identities = tuple(identities)
        except BaseException:
            self.close()
            raise

    @staticmethod
    def _verify(
        child: subprocess.Popen[bytes],
        descriptor: int,
        binding: ProcessBinding,
        identity: _ExecutableIdentity | None = None,
    ) -> _ExecutableIdentity:
        poller = select.poll()
        poller.register(descriptor, select.POLLIN)
        if child.poll() is not None or poller.poll(0):
            raise CaptureRefusal("owned native child exited")
        stat = parse_process_stat(
            read_kernel_record(Path(f"/proc/{binding.pid}/stat")), binding.pid
        )
        if stat.start_time_ticks != binding.start_time_ticks or stat.parent_pid != os.getpid():
            raise CaptureRefusal("native child ownership or incarnation differs")
        executable = Path(f"/proc/{binding.pid}/exe")
        if identity is None:
            digest, identity = _authenticate_executable(executable)
            if digest != binding.executable_sha256:
                raise CaptureRefusal("native executable admission differs")
        elif _executable_identity(executable) != identity:
            raise CaptureRefusal("native executable changed during capture")
        after = parse_process_stat(
            read_kernel_record(Path(f"/proc/{binding.pid}/stat")), binding.pid
        )
        if after.start_time_ticks != binding.start_time_ticks or after.parent_pid != os.getpid():
            raise CaptureRefusal("native child ownership or incarnation changed during admission")
        if poller.poll(0):
            raise CaptureRefusal("owned native child exited during admission")
        return identity

    def _verify_capture(self, identities: tuple[_ExecutableIdentity, ...]) -> None:
        for child, descriptor, binding, identity in zip(
            self._children, self._pidfds, self.bindings, identities, strict=True
        ):
            self._verify(child, descriptor, binding, identity)

    def verify(self) -> None:
        if len(self._pidfds) != 2:
            raise CaptureRefusal("native capture scope is closed")
        self._verify_capture(self._identities)

    @contextmanager
    def quiescent(self, *, timeout: float) -> Iterator[_NativeCapture]:
        if type(timeout) not in {int, float} or not math.isfinite(timeout) or timeout <= 0:
            raise CaptureRefusal("native suspension requires a finite positive deadline")
        if not self._capture_lock.acquire(blocking=False):
            raise CaptureRefusal("native suspension is already active")
        stopped: list[tuple[int, ProcessBinding]] = []
        stopped_witnesses: list[tuple[ThreadObservation, ...]] = []
        capture: _NativeCapture | None = None
        failure: BaseException | None = None
        suspension_started: int | None = None
        deadline = time.monotonic() + timeout
        try:
            if len(self._pidfds) != 2:
                raise CaptureRefusal("native capture scope is closed")
            identities = self._identities
            self._verify_capture(identities)
            for binding in self.bindings:
                threads = stable_thread_census(binding, deadline)
                if any(row.state in {"T", "t"} for row in threads):
                    raise CaptureRefusal("owned native process already stopped externally")
                if any(row.children for row in threads):
                    raise CaptureRefusal("unadmitted native subprocess descendant")
            for descriptor, binding in zip(self._pidfds, self.bindings, strict=True):
                if not stopped:
                    suspension_started = _sampler_clock()
                stopped.append(
                    (descriptor, binding)
                )  # Ledger before a cancellation can follow the accepted syscall.
                signal.pidfd_send_signal(descriptor, signal.SIGSTOP, None, 0)
                stopped_witnesses.append(wait_native_stopped(binding, deadline))
            self._verify_capture(identities)
            for binding, witness in zip(self.bindings, stopped_witnesses, strict=True):
                verify_native_stopped(binding, witness, deadline)
            capture = _NativeCapture(self, identities)
            yield capture
            self._verify_capture(identities)
            for binding, witness in zip(self.bindings, stopped_witnesses, strict=True):
                verify_native_stopped(binding, witness, deadline)
        except BaseException as error:
            failure = error
            raise
        finally:
            if capture is not None:
                capture.close()
            restoration: list[BaseException] = []
            continued: list[tuple[int, ProcessBinding]] = []
            for descriptor, binding in reversed(stopped):
                try:
                    signal.pidfd_send_signal(descriptor, signal.SIGCONT, None, 0)
                    continued.append((descriptor, binding))
                except ProcessLookupError:
                    pass  # An exited exact pidfd is never replaced by a numeric-PID fallback.
                except BaseException as error:
                    restoration.append(error)
            restoration_deadline = time.monotonic() + timeout
            for descriptor, binding in continued:
                try:
                    wait_native_resumed(descriptor, binding, restoration_deadline)
                except BaseException as error:
                    restoration.append(error)
            self._capture_lock.release()
            # This interval begins at the first stop attempt and ends only
            # after restoration, including marker reads and both PG barriers.
            # Publish after resuming children; it is not a new memory witness.
            _sampler_timing(
                "NativeStopToRestoration",
                suspension_started,
                restored=not restoration,
                body_failed=failure is not None,
            )
            if restoration:
                errors = [*([failure] if failure is not None else []), *restoration]
                raise BaseExceptionGroup("native capture/restoration failed", errors) from None

    def close(self) -> None:
        if self._capture_lock.locked():
            raise CaptureRefusal("cannot close native scope during suspension")
        while self._pidfds:
            os.close(self._pidfds.pop())
        self._identities = ()

    def __enter__(self) -> OwnedNativePair:
        return self

    def __exit__(self, *_exception: object) -> None:
        self.close()


class _NativeCapture:
    """Observe only inside this thread's one suspension interval.

    Linux denies writes to the live executable inode. Replacing its pathname
    does not replace /proc/PID/exe; an exec changes that kernel link's identity.
    The owner hashes bytes once per exact live child and revalidates its full
    executable identity and incarnation on every capture. Thread observations
    expire on restoration; this capability cannot survive into another capture.
    """

    def __init__(
        self, native: OwnedNativePair, identities: tuple[_ExecutableIdentity, ...]
    ) -> None:
        self._native = native
        self._identities = identities
        self._thread = threading.get_ident()
        self._active = True

    def close(self) -> None:
        self._active = False

    def observe(self) -> tuple[MemoryProcess, ...]:
        if not self._active or self._thread != threading.get_ident():
            raise CaptureRefusal("native observation requires its active owning capture")
        self._native._verify_capture(self._identities)
        rows = []
        for binding, identity in zip(self._native.bindings, self._identities, strict=True):
            directory = Path(f"/proc/{binding.pid}")
            counters = parse_rollup(read_kernel_record(directory / "smaps_rollup"))
            if _executable_identity(directory / "exe") != identity:
                raise CaptureRefusal("native executable changed during observation")
            rows.append(MemoryProcess.model_validate({**binding.model_dump(), **counters}))
        self._native._verify_capture(self._identities)
        return tuple(rows)


def docker_command(arguments: list[str], *, timeout: float) -> bytes:
    """No shell/environment inspection; bounded operator output stays private."""
    try:
        result = subprocess.run(  # noqa: S603 — argument vectors, never a shell or credential payload.
            ["docker", *arguments],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise CaptureRefusal("owned Docker operation unavailable or timed out") from None
    if result.returncode != 0:
        raise DockerOperationRefusal(arguments[0], result.returncode, result.stderr)
    if len(result.stdout) > 4_194_304:
        raise CaptureRefusal("owned Docker observation exceeds capture bound")
    return result.stdout


def docker_state(container_id: str, *, timeout: float) -> DockerState:
    # Selected fields only. Full container inspect includes credential-bearing Env.
    template = (
        '{"container_id":{{json .Id}},"image_id":{{json .Image}},'
        '"host_pid":{{json .State.Pid}},"running":{{json .State.Running}},'
        '"paused":{{json .State.Paused}}}'
    )
    raw = docker_command(
        ["container", "inspect", "--format", template, container_id], timeout=timeout
    )
    try:
        return DockerState.model_validate_json(raw)
    except ValueError:
        raise CaptureRefusal("owned Docker identity observation malformed") from None


def verify_process_credentials(pid: int, uid: int, gid: int) -> None:
    fields = {}
    for line in read_kernel_record(Path(f"/proc/{pid}/status")).splitlines():
        key, separator, value = line.partition(b":")
        if key in {b"Uid", b"Gid", b"CapPrm", b"CapEff"}:
            if not separator or key in fields:
                raise CaptureRefusal("PostgreSQL credential observation malformed")
            fields[key] = value.split()
    if (
        fields.get(b"Uid") != [str(uid).encode()] * 4
        or fields.get(b"Gid") != [str(gid).encode()] * 4
        or fields.get(b"CapPrm") != [b"0000000000000000"]
        or fields.get(b"CapEff") != [b"0000000000000000"]
    ):
        raise CaptureRefusal(
            "PostgreSQL credentials/capabilities differ from narrow helper admission"
        )


class OwnedPostgresScope:
    """Freeze only an already admitted container; restore partial Docker pauses.

    This is not another lease authority. The required supervisor callback checks
    its exact active record, volume, database and credentials outside the pause.
    During suspension we recheck exact container, cgroup inode and membership.
    """

    def __init__(self, admission: PostgresAdmission, verify_ownership: Callable[[], None]) -> None:
        self.admission = admission
        self._verify_ownership = verify_ownership

    def verify(self, *, timeout: float, paused: bool) -> tuple[int, ...]:
        expected = self.admission
        observed = docker_state(expected.container_id, timeout=timeout)
        if (
            observed.container_id != expected.container_id
            or observed.image_id != expected.image_id
            or observed.host_pid != expected.host_pid
            or not observed.running
            or observed.paused != paused
        ):
            raise CaptureRefusal("PostgreSQL container incarnation or pause state differs")
        directory = expected.cgroup_directory
        try:
            if directory.is_symlink():
                raise CaptureRefusal("admitted PostgreSQL cgroup redirected")
            identity = directory.stat()
            if (identity.st_dev, identity.st_ino) != (
                expected.cgroup_device,
                expected.cgroup_inode,
            ):
                raise CaptureRefusal("PostgreSQL cgroup incarnation differs")
        except OSError:
            raise CaptureRefusal("admitted PostgreSQL cgroup disappeared") from None
        cgroup = read_kernel_record(Path(f"/proc/{expected.host_pid}/cgroup")).splitlines()
        expected_cgroup = b"0::/" + str(directory.relative_to("/sys/fs/cgroup")).encode()
        if cgroup != [expected_cgroup]:
            raise CaptureRefusal("PostgreSQL init is outside its admitted host cgroup")
        if (
            parse_start_time(
                read_kernel_record(Path(f"/proc/{expected.host_pid}/stat")), expected.host_pid
            )
            != expected.start_time_ticks
        ):
            raise CaptureRefusal("PostgreSQL init incarnation differs")
        if paused:
            verify_cgroup_frozen(directory)
        members = cgroup_members(directory)
        if expected.host_pid not in members:
            raise CaptureRefusal("PostgreSQL cgroup census omits its admitted init")
        return members

    @contextmanager
    def quiescent(self, *, timeout: float) -> Iterator[tuple[ProcessBinding, ...]]:
        self._verify_ownership()
        self.verify(timeout=timeout, paused=False)
        attempted = False
        failure: BaseException | None = None
        try:
            # A failed/timed-out pause can still have frozen the exact container.
            attempted = True
            docker_command(["pause", self.admission.container_id], timeout=timeout)
            before = self.verify(timeout=timeout, paused=True)
            bindings = tuple(
                ProcessBinding(
                    pid=pid,
                    start_time_ticks=parse_start_time(
                        read_kernel_record(Path(f"/proc/{pid}/stat")), pid
                    ),
                    role="game-postgresql",
                    executable_sha256=self.admission.executable_sha256,
                )
                for pid in before
            )
            for binding in bindings:
                verify_process_credentials(binding.pid, self.admission.uid, self.admission.gid)
            yield bindings
            if self.verify(timeout=timeout, paused=True) != before:
                raise CaptureRefusal("PostgreSQL membership changed while frozen")
            for binding in bindings:
                if (
                    parse_start_time(
                        read_kernel_record(Path(f"/proc/{binding.pid}/stat")), binding.pid
                    )
                    != binding.start_time_ticks
                ):
                    raise CaptureRefusal("PostgreSQL PID incarnation changed while frozen")
        except BaseException as error:
            failure = error
            raise
        finally:
            restoration: list[BaseException] = []
            if attempted:
                try:
                    state = docker_state(self.admission.container_id, timeout=timeout)
                    if (
                        state.container_id != self.admission.container_id
                        or state.image_id != self.admission.image_id
                        or state.host_pid != self.admission.host_pid
                    ):
                        raise CaptureRefusal("cannot restore changed PostgreSQL container")
                    if state.paused:
                        docker_command(["unpause", self.admission.container_id], timeout=timeout)
                    self.verify(timeout=timeout, paused=False)
                    self._verify_ownership()
                except BaseException as error:
                    restoration.append(error)
            if restoration:
                raise BaseExceptionGroup(
                    "PostgreSQL capture/restoration failed",
                    [*([failure] if failure is not None else []), *restoration],
                ) from None

    def observe(
        self, bindings: tuple[ProcessBinding, ...], *, timeout: float
    ) -> tuple[MemoryProcess, ...]:
        """A separate capability-free helper reads allowlisted frozen proc records.

        It runs outside the paused game cgroup, never invokes postgres, and
        mounts no data volume or Docker socket. This host's runc refused the
        direct exe magic-link mount; each exact admitted proc directory is mounted
        read-only instead. Other entries are exposed but never read. The fixed
        script reads only stat, user namespace, exe and smaps_rollup records.
        """
        if not bindings or any(binding.role != "game-postgresql" for binding in bindings):
            raise CaptureRefusal("PostgreSQL helper requires its exact nonempty frozen roster")
        if len({binding.pid for binding in bindings}) != len(bindings):
            raise CaptureRefusal("PostgreSQL helper roster duplicated")
        token = uuid4().hex
        with tempfile.TemporaryDirectory(prefix="babylon-memory-") as name:
            cidfile = Path(name) / "helper-id"
            arguments = [
                "run",
                "--rm",
                "--pull",
                "never",
                "--name",
                "babylon-memory-" + token,
                "--label",
                "babylon.memory-sampler=" + token,
                "--cidfile",
                str(cidfile),
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--user",
                f"{self.admission.uid}:{self.admission.gid}",
                "--userns",
                "host",
                "--mount",
                "type=tmpfs,destination=/var/lib/postgresql/data,tmpfs-size=1048576",
            ]
            for binding in bindings:
                arguments.extend(
                    [
                        "--mount",
                        f"type=bind,source=/proc/{binding.pid},"
                        f"destination=/owned/{binding.pid},readonly",
                    ]
                )
            script = (
                'set -eu; stat -Lc "%i" /proc/self/ns/user; '
                'for pid do printf "%s\\n" "$pid"; '
                'stat -Lc "%i" "/owned/$pid/ns/user"; '
                'base64 -w0 "/owned/$pid/stat"; printf "\\n"; '
                'sha256sum "/owned/$pid/exe"; '
                'base64 -w0 "/owned/$pid/smaps_rollup"; printf "\\n"; '
                'base64 -w0 "/owned/$pid/stat"; printf "\\n"; done'
            )
            arguments.extend(
                [
                    "--entrypoint",
                    "/bin/sh",
                    self.admission.image_id,
                    "-c",
                    script,
                    "babylon-memory-reader",
                    *(str(binding.pid) for binding in bindings),
                ]
            )
            failure: BaseException | None = None
            try:
                raw = docker_command(arguments, timeout=timeout)
                return decode_postgres_observations(raw, bindings)
            except BaseException as error:
                failure = error
                raise
            finally:
                # Cancellation may kill only the Docker CLI. Remove only the
                # exact CID created by this call, authenticated by its label.
                if cidfile.exists():
                    try:
                        cid = cidfile.read_text().strip()
                        if re.fullmatch(r"[0-9a-f]{64}", cid) is None:
                            raise CaptureRefusal("memory helper creation identity malformed")
                        ids = docker_command(
                            [
                                "ps",
                                "-aq",
                                "--no-trunc",
                                "--filter",
                                "id=" + cid,
                            ],
                            timeout=timeout,
                        ).splitlines()
                        if ids:
                            if ids != [cid.encode()]:
                                raise CaptureRefusal("memory helper cleanup scope differs")
                            template = (
                                '{{index .Config.Labels "babylon.memory-sampler"}}|{{.Image}}'
                            )
                            helper_identity = docker_command(
                                [
                                    "container",
                                    "inspect",
                                    "--format",
                                    template,
                                    cid,
                                ],
                                timeout=timeout,
                            ).strip()
                            if helper_identity != f"{token}|{self.admission.image_id}".encode():
                                raise CaptureRefusal("memory helper cleanup ownership differs")
                            docker_command(["container", "rm", "--force", cid], timeout=timeout)
                    except BaseException as cleanup:
                        raise BaseExceptionGroup(
                            "memory helper/read cleanup failed",
                            [*([failure] if failure is not None else []), cleanup],
                        ) from None


def decode_postgres_observations(
    raw: bytes, bindings: tuple[ProcessBinding, ...]
) -> tuple[MemoryProcess, ...]:
    lines = raw.splitlines()
    if len(lines) != 1 + 6 * len(bindings) or not re.fullmatch(rb"[1-9][0-9]*", lines[0]):
        raise CaptureRefusal("PostgreSQL helper observation framing malformed")
    user_namespace = lines[0]
    results = []
    for index, binding in enumerate(bindings):
        pid, namespace, before, digest, rollup, after = lines[1 + 6 * index : 7 + 6 * index]
        if pid != str(binding.pid).encode() or namespace != user_namespace:
            raise CaptureRefusal("PostgreSQL helper PID/user namespace differs")
        if digest != f"{binding.executable_sha256}  /owned/{binding.pid}/exe".encode():
            raise CaptureRefusal("PostgreSQL running executable differs from admission")
        try:
            before_record = base64.b64decode(before, validate=True)
            after_record = base64.b64decode(after, validate=True)
            counters = parse_rollup(base64.b64decode(rollup, validate=True))
        except ValueError:
            raise CaptureRefusal("PostgreSQL helper kernel record malformed") from None
        if (
            parse_start_time(before_record, binding.pid) != binding.start_time_ticks
            or parse_start_time(after_record, binding.pid) != binding.start_time_ticks
        ):
            raise CaptureRefusal("PostgreSQL process incarnation differs during helper read")
        results.append(MemoryProcess.model_validate({**binding.model_dump(), **counters}))
    return tuple(results)


def collect_running_game(
    native: OwnedNativePair,
    postgres: OwnedPostgresScope,
    read_marker: Callable[[], CampaignMemoryMarker],
    *,
    campaign: str,
    foundation_sha256: str | None,
    sequence: int,
    timeout: float,
) -> QuiescentBatch:
    """Close exact barriers and committed identity before admitting one sample.

    The independent reader must authenticate campaign/foundation/tick_commit;
    UI observations and pending requests are not this callback's authority.
    Kernel reclaim can continue: this is a quiescent scoped capture, not an
    atomic global snapshot or proof of a continuous resident-memory peak.
    """
    boot = boot_identity()
    with native.quiescent(timeout=timeout) as native_capture:
        with _timed_sampler_stage("OpeningMarker", sequence):
            before = read_marker()
        if before.campaign != campaign or (
            foundation_sha256 is not None and before.foundation_sha256 != foundation_sha256
        ):
            raise CaptureRefusal("memory committed campaign/foundation differs")
        with _timed_sampler_stage("PostgresQuiescentScope", sequence):
            with postgres.quiescent(timeout=timeout) as pg_bindings:
                started = time.monotonic_ns()  # Both barriers now hold.
                with _timed_sampler_stage("NativeCounterRead", sequence):
                    processes = native_capture.observe()
                with _timed_sampler_stage("PostgresCounterRead", sequence):
                    processes += postgres.observe(pg_bindings, timeout=timeout)
                finished = time.monotonic_ns()
        with _timed_sampler_stage("ClosingMarker", sequence):
            after = read_marker()
    if boot_identity() != boot:
        raise CaptureRefusal("kernel boot identity changed during coherent capture")
    # Compare only after native and PostgreSQL restoration succeeded. The
    # independent repeatable-read markers bracket the stopped counter interval;
    # append-only publication makes equality an optimistic epoch validation.
    if after != before:
        try:
            unassigned = UnassignedMemoryCapture(
                version=1,
                scope="unassigned_capture_not_memory_qualification",
                boot_id=boot,
                before=before,
                after=after,
                monotonic_ns=started,
                capture_duration_ns=finished - started,
                processes=processes,
            )
        except ValueError:
            raise CaptureRefusal("memory committed identity regressed or was replaced") from None
        raise PublicationAdvanced(unassigned)
    return QuiescentBatch(
        boot_id=boot,
        sample=MemorySample(
            sequence=sequence,
            foundation_sha256=before.foundation_sha256,
            campaign_age_ticks=before.campaign_age_ticks,
            tick_content_hash=before.tick_content_hash,
            monotonic_ns=started,
            capture_duration_ns=finished - started,
            simultaneous_capture="owned_game_group_stopped",
            roster_complete="all_game_processes_in_owned_scope",
            native_client_mode="windowed",
            processes=processes,
        ),
    )


def write_capture_record(destination: Path, record: Mapping[str, object]) -> None:
    descriptor, name = tempfile.mkstemp(prefix=destination.name + ".", dir=destination.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(record, output, allow_nan=False, separators=(",", ":"))
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


class RunningMemoryCapture:
    """Periodic owned captures under the existing driver's lifecycle hook.

    Immutable sample records and an atomic progress pointer preserve an
    interrupted prefix. Only the sole existing evaluator can qualify results;
    this producer never publishes a passing status or derives game ownership.
    """

    def __init__(
        self,
        *,
        directory: Path,
        expected_hashes: Mapping[str, str],
        campaign: str,
        foundation_sha256: str | None,
        runtime_sha256: str,
        client_sha256: str,
        postgres: OwnedPostgresScope,
        read_marker: Callable[[], CampaignMemoryMarker],
        sample_gap_seconds: int,
        operation_timeout: float,
        operation_lock: AbstractContextManager[object] | None = None,
    ) -> None:
        self.directory = directory
        self._expected = dict(expected_hashes)
        verify_frozen_files(directory, self._expected)
        for name in ("combined-memory.json", "combined-memory-progress.json"):
            if (directory / name).exists() or (directory / name).is_symlink():
                raise CaptureRefusal("memory capture refuses an existing result or progress record")
        policy = Policy.model_validate_json((directory / "policy.json").read_bytes())
        if type(sample_gap_seconds) is not int or sample_gap_seconds <= 0:
            raise CaptureRefusal(
                "memory capture cadence must use the admitted positive policy limit"
            )
        if sample_gap_seconds != policy.maximum_combined_memory_sample_gap_seconds:
            raise CaptureRefusal("memory capture cadence differs from the frozen policy")
        if (
            type(operation_timeout) not in {int, float}
            or not math.isfinite(operation_timeout)
            or operation_timeout <= 0
        ):
            raise CaptureRefusal("memory capture operation deadline must be finite and positive")
        self._campaign = campaign
        self._foundation = foundation_sha256
        self._runtime_sha = runtime_sha256
        self._client_sha = client_sha256
        self._postgres = postgres
        self._read_marker = read_marker
        self._gap = sample_gap_seconds / 2
        self._timeout = operation_timeout
        self._operation_lock = operation_lock if operation_lock is not None else nullcontext()
        self._stop = threading.Event()
        self._worker_finished = threading.Event()
        self._thread: threading.Thread | None = None
        self._native: OwnedNativePair | None = None
        self._failure: BaseException | None = None
        self._samples: list[MemorySample] = []
        self._unassigned_count = 0
        self._boot: str | None = None
        self._started_ns = 0
        self._finished = False
        self._records = directory / "memory-samples"
        self._records.mkdir(mode=0o700)  # Exclusive new run, never overwrite another prefix.
        self._unassigned_records = directory / "memory-unassigned"
        self._unassigned_records.mkdir(mode=0o700)

    def bind_foundation(self, foundation_sha256: str) -> None:
        """Authenticate the native acknowledgment against the immutable observed prefix."""
        marker = CampaignMemoryMarker(
            campaign=self._campaign,
            foundation_sha256=foundation_sha256,
            campaign_age_ticks=0,
            tick_content_hash=None,
        )
        with self._operation_lock:
            self.check()
            if self._native is None or not self._samples or self._finished:
                raise CaptureRefusal("foundation acknowledgment requires a running memory capture")
            if self._foundation is not None and self._foundation != marker.foundation_sha256:
                raise CaptureRefusal("acknowledged memory foundation changed")
            if any(
                sample.foundation_sha256 is not None
                and sample.foundation_sha256 != marker.foundation_sha256
                for sample in self._samples
            ):
                raise CaptureRefusal("acknowledged memory foundation differs from observed prefix")
            self._foundation = marker.foundation_sha256
            self._progress()

    def _progress(self) -> None:
        write_capture_record(
            self.directory / "combined-memory-progress.json",
            {
                "version": 3,
                "status": "incomplete",
                "scope": "capture_progress_not_qualification",
                "campaign": self._campaign,
                "foundation_sha256": self._foundation,
                "policy_sha256": self._expected["policy_sha256"],
                "sample_count": len(self._samples),
                "last_sample": None
                if not self._samples
                else f"memory-samples/{len(self._samples):08d}.json",
                "capture_failed": self._failure is not None,
                "unassigned_capture_count": self._unassigned_count,
            },
        )

    def _capture_one(self, native: OwnedNativePair) -> None:
        # The runner shares this admission/barrier lock with its independent
        # PostgreSQL readers. No admin probe or snapshot can cross a pause.
        with self._operation_lock:
            self._capture_locked(native)

    def _capture_locked(self, native: OwnedNativePair) -> None:
        verify_frozen_files(self.directory, self._expected)
        batch = collect_running_game(
            native,
            self._postgres,
            self._read_marker,
            campaign=self._campaign,
            foundation_sha256=self._foundation,
            sequence=len(self._samples) + 1,
            timeout=self._timeout,
        )
        if self._boot is not None and self._boot != batch.boot_id:
            raise CaptureRefusal("memory capture boot identity changed between samples")
        if self._samples and self._samples[-1].foundation_sha256 is not None:
            if batch.sample.foundation_sha256 != self._samples[-1].foundation_sha256:
                raise CaptureRefusal("memory capture observed foundation changed or disappeared")
        verify_frozen_files(self.directory, self._expected)
        self._boot = batch.boot_id
        write_capture_record(
            self._records / f"{batch.sample.sequence:08d}.json",
            batch.sample.model_dump(mode="json"),
        )
        self._samples.append(batch.sample)
        self._progress()

    def _capture_periodic(self, native: OwnedNativePair) -> None:
        with self._operation_lock:
            try:
                self._capture_locked(native)
            except PublicationAdvanced as crossing:
                record = crossing.record
                if self._boot is not None and self._boot != record.boot_id:
                    raise CaptureRefusal(
                        "memory capture boot identity changed between samples"
                    ) from None
                if self._samples and self._samples[-1].foundation_sha256 is not None:
                    if record.before.foundation_sha256 != self._samples[-1].foundation_sha256:
                        raise CaptureRefusal(
                            "memory capture observed foundation changed or disappeared"
                        ) from None
                verify_frozen_files(self.directory, self._expected)
                write_capture_record(
                    self._unassigned_records / f"{self._unassigned_count + 1:08d}.json",
                    record.model_dump(mode="json"),
                )
                self._boot = record.boot_id
                self._unassigned_count += 1
                self._progress()

    def _run(self, native: OwnedNativePair, signal_mask: set[signal.Signals]) -> None:
        try:
            signal.pthread_sigmask(signal.SIG_SETMASK, signal_mask)
            if self._samples:
                self._stop.wait(self._gap)
            while not self._stop.is_set():
                started = time.monotonic()
                self._capture_periodic(native)
                # Capture already consumes part of the cadence. Adding a full
                # sleep afterwards made measured collection overhead a gap.
                self._stop.wait(max(0, self._gap - (time.monotonic() - started)))
        except BaseException as error:
            self._failure = error
            self._stop.set()
        finally:
            # Thread.join's bookkeeping can report stopped after interruption
            # while the thread is still unwinding. Only the worker publishes
            # this token, after every owned barrier/context has returned.
            self._worker_finished.set()

    def _start_worker(self, native: OwnedNativePair) -> None:
        # Defer SIGINT delivery to this caller while recording worker startup.
        # The worker restores its inherited mask before capture. Cleanup relies
        # on ownership and the actual finished token, not signal masking alone.
        previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT})
        try:
            self._thread = threading.Thread(
                target=self._run, args=(native, previous_mask), name="national-memory-capture"
            )
            try:
                self._thread.start()
            except RuntimeError:
                if self._thread.ident is None:
                    # Standard Thread.start resource refusal created no worker.
                    self._thread = None
                raise
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)

    def check(self) -> None:
        if self._failure is not None:
            raise self._failure

    def finish(self) -> None:
        try:
            self._finish()
        except BaseException as error:
            prior = self._failure
            self._failure = (
                BaseExceptionGroup("capture and completion failed", [prior, error])
                if prior is not None and prior is not error
                else error
            )
            try:
                self._progress()
            except BaseException as publication:
                self._failure = BaseExceptionGroup(
                    "memory capture and failure evidence publication failed",
                    [self._failure, publication],
                )
            raise self._failure from None

    def _drain(self) -> None:
        self._stop.set()
        interruptions: list[BaseException] = []
        if self._thread is not None:
            # Preserve cancellation, but do not release the native scope or
            # let the launcher reap its children before actual worker unwind.
            while not self._worker_finished.is_set():
                try:
                    self._worker_finished.wait(0.05)
                except BaseException as error:
                    interruptions.append(error)
            try:
                self._thread.join(0)
            except BaseException as error:
                interruptions.append(error)
        if interruptions:
            raise BaseExceptionGroup("memory capture drain interrupted", interruptions)

    def _finish(self) -> None:
        if self._finished:
            if self._failure is not None:
                raise self._failure
            return
        self._drain()
        self._finished = True
        if self._failure is not None:
            raise self._failure
        if self._native is None:
            raise CaptureRefusal("memory capture lifecycle was not started")
        # The final committed boundary may arrive between periodic captures.
        # Bind it while both actual children still exist, before ordinary Quit.
        self._capture_one(self._native)
        verify_frozen_files(self.directory, self._expected)
        if not self._samples or self._boot is None or self._samples[-1].campaign_age_ticks == 0:
            raise CaptureRefusal("memory capture has no actual positive committed horizon")
        if self._foundation is None:
            raise CaptureRefusal("memory capture has no acknowledged campaign foundation")
        ended = time.monotonic_ns()
        evidence = CombinedMemoryEvidence(
            version=2,
            source="linux_proc_smaps_rollup_v1",
            evidence_class="Observed",
            campaign=self._campaign,
            foundation_sha256=self._foundation,
            boot_id=self._boot,
            periods=self._samples[-1].campaign_age_ticks,
            interval_start_monotonic_ns=self._started_ns,
            interval_end_monotonic_ns=ended,
            samples=tuple(self._samples),
            **self._expected,
        )
        write_capture_record(
            self.directory / "combined-memory.json", evidence.model_dump(mode="json")
        )

    @contextmanager
    def lifecycle(
        self, runtime: subprocess.Popen[bytes], client: subprocess.Popen[bytes]
    ) -> Iterator[RunningMemoryCapture]:
        if self._thread is not None:
            raise CaptureRefusal("memory capture lifecycle cannot be reused")
        with OwnedNativePair(
            runtime,
            client,
            runtime_sha256=self._runtime_sha,
            client_sha256=self._client_sha,
        ) as native:
            self._native = native
            self._started_ns = time.monotonic_ns()
            self._progress()
            failure: BaseException | None = None
            try:
                if self._foundation is None:
                    # The native client waits on its private startup admission.
                    # Capture real absence before permitting any New operation.
                    self._capture_one(native)
                    if self._samples[0].foundation_sha256 is not None:
                        raise CaptureRefusal("startup memory capture requires an absent campaign")
                self._start_worker(native)
                yield self  # The driver checks failures and finishes before ordinary Quit.
            except BaseException as error:
                failure = error
                raise
            finally:
                try:
                    self.finish()
                except BaseException as capture_error:
                    if failure is not None and capture_error is not failure:
                        raise BaseExceptionGroup(
                            "native drive and memory capture failed", [failure, capture_error]
                        ) from None
                    raise
