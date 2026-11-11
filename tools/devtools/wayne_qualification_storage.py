"""Media and evidence admission for the three disposable Wayne qualification runs."""

from __future__ import annotations

import errno
import grp
import hashlib
import json
import os
import pwd
import re
import stat
import struct
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, BinaryIO, Literal
from uuid import UUID, uuid4

import psycopg
from psycopg import sql
from pydantic import BaseModel, ConfigDict, Field
from tools.devtools.national_storage_qualification import (
    MeasurementMode,
    Sha256,
    measurement_mode,
    selected_policy,
    strict_json_bytes,
)

RUN_PARENT = Path("/media/user/data/worktrees/per364-wayne-solidarity-loop/qualification-18")
MEDIA = Path("/media/user/data")
PGDATA: Literal["/var/lib/postgresql/data"] = "/var/lib/postgresql/data"
TEST_NAME = (
    "runtime::live_tests::organizer_allocation_atomic::"
    "national_collection_and_local_cash_survive_sql_retries"
)
PROFILES = {
    "sql-01": ("organizer_allocation_atomic", ""),
    "smoke-01": ("national_storage", "2"),
    "walk-01": ("national_storage", "10"),
    "ordinary-01": ("national_storage", "10"),
}
STAGES = (
    "bootstrap",
    "clone",
    "schema",
    "foundation",
    "collect_preview",
    "collect_submit",
    "collect_conflict",
    "collect_pending_open",
    "p1_close",
    "aid_preview",
    "aid_submit",
    "aid_food_conflict",
    "aid_cash_conflict",
    "aid_pending_open",
    "stale_open",
    "p2_marker_rollback",
    "rollback_open",
    "p2_after_commit",
    "p2_stale_retry",
    "p2_completed_open",
    "p3_purchase",
)
DIR_FLAGS = os.O_DIRECTORY | os.O_NOFOLLOW | os.O_RDONLY | os.O_CLOEXEC
FILE_FLAGS = os.O_NOFOLLOW | os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC


class StorageRefusal(ValueError):
    """The source, fixture or evidence cannot be admitted."""


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Reference(Record):
    path: str
    bytes: Annotated[int, Field(ge=0)]
    sha256: Annotated[str, Field(pattern="^[0-9a-f]{64}$")]


def member_run(profile: str, mode: MeasurementMode) -> Path:
    if profile not in ("smoke-01", "walk-01"):
        raise StorageRefusal("unsupported paired native workload")
    return RUN_PARENT / profile / measurement_mode(mode)


def native_path(evidence: Path) -> tuple[str, MeasurementMode]:
    run = evidence.parent
    mode = measurement_mode(run.name)
    profile = run.parent.name
    if evidence != member_run(profile, mode) / "evidence":
        raise StorageRefusal("native evidence does not name its canonical workload and mode")
    return profile, mode


def owned_native_path(evidence: Path) -> tuple[str, MeasurementMode]:
    """Resolve media custody paths without admitting ordinary evidence to a pair."""
    if evidence == RUN_PARENT / "ordinary-01/normal_play/evidence":
        return "ordinary-01", "normal_play"
    return native_path(evidence)


def profile_run(profile: str, focus: str, periods: str, evidence: Path) -> Path:
    if PROFILES.get(profile) != (focus, periods):
        raise StorageRefusal("Wayne media profile, focus and period count disagree")
    if profile == "ordinary-01":
        if measurement_mode(os.environ.get("BABYLON_NATIVE_MEASUREMENT_MODE")) != "normal_play":
            raise StorageRefusal("ordinary prefix requires normal-only measurement")
        run = RUN_PARENT / profile / "normal_play"
        if evidence != run / "evidence":
            raise StorageRefusal("ordinary evidence does not name its independent normal-only run")
        return run
    run = (
        RUN_PARENT / profile
        if profile == "sql-01"
        else member_run(
            profile, measurement_mode(os.environ.get("BABYLON_NATIVE_MEASUREMENT_MODE"))
        )
    )
    if evidence != run / "evidence":
        raise StorageRefusal("Wayne evidence does not name its selected media run")
    return run


def verify_transcript(raw: bytes, status: int) -> None:
    lines = raw.decode("utf-8", "strict").splitlines()
    result = re.compile(
        r"test result: ok\. 1 passed; 0 failed; 0 ignored; 0 measured; "
        r"[0-9]+ filtered out; finished in [0-9]+(?:\.[0-9]+)?s"
    )
    names = [
        line for line in lines if line.startswith("test ") and not line.startswith("test result:")
    ]
    summaries = [line for line in lines if line.startswith("test result:")]
    if (
        status != 0
        or [line for line in lines if re.match(r"running .* tests?$", line)] != ["running 1 test"]
        or names != [f"test {TEST_NAME} ... ok"]
        or len(summaries) != 1
        or not result.fullmatch(summaries[0])
    ):
        raise StorageRefusal(
            "exact ignored test, single passing transcript and exit status required"
        )


def canonical_json(record: object) -> bytes:
    return (json.dumps(record, allow_nan=False, sort_keys=True) + "\n").encode()


def _path_components(name: str) -> list[str]:
    parts = name.split("/")
    if not parts or any(part in {"", ".", ".."} for part in parts) or "\x00" in name:
        raise StorageRefusal("evidence reference is not a confined relative path")
    return parts


def _private_dir(fd: int) -> None:
    info = os.fstat(fd)
    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise StorageRefusal("private evidence directory owner or mode differs")


def _receipt(stream: BinaryIO, name: str) -> Reference:
    before = os.fstat(stream.fileno())
    size = before.st_size
    hashed = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        hashed.update(chunk)
    digest = hashed.hexdigest()
    after = os.fstat(stream.fileno())
    if (size, before.st_mode, before.st_uid, before.st_mtime_ns, before.st_ctime_ns) != (
        after.st_size,
        after.st_mode,
        after.st_uid,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise StorageRefusal("evidence changed during verification")
    return Reference(path=name, bytes=size, sha256=digest)


class PrivateEvidence:
    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def _owned_file(self, name: str) -> Iterator[BinaryIO]:
        parts = _path_components(name)
        with ExitStack() as stack:
            directory = os.open(self.path, DIR_FLAGS)
            stack.callback(os.close, directory)
            _private_dir(directory)
            for part in parts[:-1]:
                directory = os.open(part, DIR_FLAGS, dir_fd=directory)
                stack.callback(os.close, directory)
                _private_dir(directory)
            fd = os.open(parts[-1], FILE_FLAGS, dir_fd=directory)
            stream = stack.enter_context(os.fdopen(fd, "rb"))
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
                raise StorageRefusal("referenced evidence must be a private owned regular file")
            yield stream

    @contextmanager
    def file(self, name: str) -> Iterator[BinaryIO]:
        with self._owned_file(name) as stream:
            if os.fstat(stream.fileno()).st_mode & 0o077:
                raise StorageRefusal("referenced evidence must be a private owned regular file")
            yield stream

    def extracted_member(self, name: str, *, executable: bool = False) -> Reference:
        """Seal the selected file inside nextest's fresh, private extraction tree."""
        with self._owned_file(name) as stream:
            fd = stream.fileno()
            info = os.fstat(fd)
            if info.st_nlink != 1 or (executable and not info.st_mode & stat.S_IXUSR):
                raise StorageRefusal("extracted nextest member has unexpected links or mode")
            # tar may restore group/other bits inside the new 0700 extraction tree.
            os.fchmod(fd, 0o700 if executable else 0o600)
            os.fsync(fd)
            return _receipt(stream, name)

    def reference(self, name: str) -> Reference:
        with self.file(name) as source:
            return _receipt(source, name)

    def verify(self, ref: Reference) -> None:
        if self.reference(ref.path) != ref:
            raise StorageRefusal("evidence reference length or digest differs: " + ref.path)

    def read_reference(self, ref: Reference, maximum: int = 8_388_608) -> bytes:
        if ref.bytes > maximum:
            raise StorageRefusal("structured evidence exceeds its read limit")
        with self.file(ref.path) as source:
            value = source.read(maximum + 1)
        if len(value) != ref.bytes or hashlib.sha256(value).hexdigest() != ref.sha256:
            raise StorageRefusal("evidence reference length or digest differs: " + ref.path)
        return value

    def publish(self, name: str, data: bytes) -> Reference:
        if len(_path_components(name)) != 1:
            raise StorageRefusal("operator publication must name one evidence file")
        fd = os.open(self.path, DIR_FLAGS)
        try:
            _private_dir(fd)
            with tempfile.NamedTemporaryFile(
                dir=self.path, prefix=name + ".", suffix=".partial", delete=False
            ) as temporary:
                temporary.write(data)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.link(Path(temporary.name).name, name, src_dir_fd=fd, dst_dir_fd=fd)
            os.fsync(fd)
            ref = Reference(path=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            self.verify(ref)
            os.unlink(Path(temporary.name).name, dir_fd=fd)
            os.fsync(fd)
            return ref
        finally:
            os.close(fd)

    def publish_json(self, name: str, record: object) -> Reference:
        return self.publish(name, canonical_json(record))


def _acl(fd: int, name: str) -> list[tuple[int, int, int]]:
    try:
        raw = os.getxattr(fd, name)
    except OSError as exc:
        if exc.errno == errno.ENODATA:
            return []
        raise
    if len(raw) < 4 or (len(raw) - 4) % 8 or struct.unpack_from("<I", raw)[0] != 2:
        raise StorageRefusal("could not decode POSIX ACL")
    rows = list(struct.iter_unpack("<HHI", raw[4:]))
    if any(tag not in {1, 2, 4, 8, 16, 32} or perm > 7 for tag, perm, _ in rows):
        raise StorageRefusal("unknown POSIX ACL tag or permission")
    return rows


def _can_replace(parent: os.stat_result, rows: list[tuple[int, int, int]], child_uid: int) -> None:
    trusted = {0, os.geteuid()}
    if parent.st_uid not in trusted or child_uid not in trusted:
        raise StorageRefusal("directory component has an outside replacement authority")
    if parent.st_mode & stat.S_ISVTX:
        return
    # An outside writer also needs search permission to replace a child.
    if not rows:
        rows = [(4, (parent.st_mode >> 3) & 7, 0), (32, parent.st_mode & 7, 0)]
    group_mask = next((perm for tag, perm, _ in rows if tag == 16), 7)
    if any(tag == 32 and perm & 3 == 3 for tag, perm, _ in rows):
        raise StorageRefusal("public can replace media directory entries")
    # Group permissions combine across matching owning/named groups. Enumerate
    # only on hosts with local account authority, never infer remote NSS rosters.
    groups: dict[int, int] = {}
    for tag, perm, who in rows:
        if tag in (4, 8):
            gid = parent.st_gid if tag == 4 else who
            groups[gid] = groups.get(gid, 0) | (perm & group_mask)
    users = {who: perm & group_mask for tag, perm, who in rows if tag == 2}
    if any(uid not in trusted and perm & 3 == 3 for uid, perm in users.items()):
        raise StorageRefusal("an ACL user can replace media directory entries")
    if not any(bits & 2 for bits in groups.values()):
        return
    nss = Path("/etc/nsswitch.conf").read_text()
    for database in ("group", "passwd"):
        entry = re.search(rf"^{database}:\s*([^#\n]+)", nss, re.MULTILINE)
        if entry is None or entry.group(1).split() != ["files"]:
            raise StorageRefusal("writable ancestry group has non-enumerable authority")
    accounts = pwd.getpwall()
    names = {account.pw_name for account in accounts}
    if any(member not in names for gid in groups for member in grp.getgrgid(gid).gr_mem):
        raise StorageRefusal("writable ancestry group contains an unresolved member")
    for account in accounts:
        if account.pw_uid in trusted or account.pw_uid in users:
            continue
        effective = 0
        for gid in os.getgrouplist(account.pw_name, account.pw_gid):
            effective |= groups.get(gid, 0)
        if effective & 3 == 3:
            raise StorageRefusal("a group member can replace media directory entries")


class DirectoryPin(Record):
    mount_id: int
    path: str
    major: int
    minor: int
    inode: int
    uid: int
    gid: int
    mode: int
    access_acl: list[list[int]]
    default_acl: list[list[int]]


def _mount_id(fd: int) -> int:
    mount = re.search(
        r"^mnt_id:\s+(\d+)$", Path(f"/proc/self/fdinfo/{fd}").read_text(), re.MULTILINE
    )
    if mount is None:
        raise StorageRefusal("could not verify component mount identity")
    return int(mount[1])


def _directory_pin(fd: int, path: Path) -> DirectoryPin:
    info = os.fstat(fd)
    return DirectoryPin(
        mount_id=_mount_id(fd),
        path=str(path),
        major=os.major(info.st_dev),
        minor=os.minor(info.st_dev),
        inode=info.st_ino,
        uid=info.st_uid,
        gid=info.st_gid,
        mode=stat.S_IMODE(info.st_mode),
        access_acl=[list(row) for row in _acl(fd, "system.posix_acl_access")],
        default_acl=[list(row) for row in _acl(fd, "system.posix_acl_default")],
    )


def check_media_mount(media: DirectoryPin, pins: list[DirectoryPin]) -> None:
    if any(
        (pin.major, pin.minor, pin.mount_id) != (media.major, media.minor, media.mount_id)
        for pin in pins
        if Path(pin.path).is_relative_to(media.path)
    ):
        raise StorageRefusal("unexpected nested mount under the media drive")


@contextmanager
def pinned_ancestry(directory: Path) -> Iterator[list[DirectoryPin]]:
    if not directory.is_absolute() or ".." in directory.parts:
        raise StorageRefusal("absolute canonical ancestry required")
    with ExitStack() as stack:
        path = Path("/")
        fd = os.open(path, DIR_FLAGS)
        stack.callback(os.close, fd)
        pins = [_directory_pin(fd, path)]
        for component in directory.parts[1:]:
            path /= component
            child = os.open(component, DIR_FLAGS, dir_fd=fd)
            stack.callback(os.close, child)
            _can_replace(os.fstat(fd), _acl(fd, "system.posix_acl_access"), os.fstat(child).st_uid)
            pins.append(_directory_pin(child, path))
            fd = child
        if not MEDIA.is_mount() or not directory.is_relative_to(MEDIA):
            raise StorageRefusal("Wayne qualification requires the actual mounted media drive")
        media = next(pin for pin in pins if pin.path == str(MEDIA))
        check_media_mount(media, pins)
        yield pins


def exact_output(args: list[str], *, timeout: int = 15) -> str:
    return (
        subprocess.run(args, capture_output=True, check=True, timeout=timeout)
        .stdout.decode()
        .strip()
    )


# SQL and native identities are separate. A claim or fixture never authorizes a drop.

Digest = Annotated[str, Field(pattern="^[0-9a-f]{64}$")]
Oid = Annotated[int, Field(gt=0, le=2**32 - 1)]
Cluster = Annotated[str, Field(pattern="^[1-9][0-9]{0,19}$")]
Canary = Annotated[str, Field(pattern="^[0-9a-f]{32}$")]


class Database(Record):
    name: str
    oid: Oid
    owner_oid: Oid


class Fixture(Record):
    tag: Literal["sql-fixture-v1"]
    focus: Literal["organizer_allocation_atomic"]
    test: str
    checkout: str
    run: str
    evidence: str
    source_head: Annotated[str, Field(pattern="^[0-9a-f]{40}$")]
    source: Reference
    inputs: Reference
    policy: Reference
    physical: Reference
    executable: Reference
    host: Literal["127.0.0.1"]
    host_port: Annotated[int, Field(gt=0, le=65535)]
    container_port: Literal[5432]
    canary: Canary
    ack: Literal["I_UNDERSTAND_THIS_DISPOSABLE_RUNTIME_DROPS_ITS_SCRATCH_DATABASES_AND_ROLES"]
    data_directory: Literal["/var/lib/postgresql/data"]
    cluster: Cluster
    login: Literal["test"]
    role_oid: Oid
    bootstrap: Database
    template: Database
    campaign: str
    preset: Literal["national-world"]
    session: Literal["national-independent-aid"]
    seed: Literal[319]


class Claim(Record):
    tag: Literal["sql-clone-claim-v1"]
    fixture: Reference
    pid: Annotated[int, Field(gt=0)]
    clone_name: str
    template: Database
    owner_oid: Oid
    campaign: str


class CloneIdentity(Record):
    tag: Literal["sql-clone-identity-v1"]
    claim: Reference
    clone: Database
    template: Database
    canary: Canary
    cluster: Cluster


class SQLOwner(Record):
    tag: Literal["sql-owner-v1"]
    fixture: Reference
    clone_identity: Reference
    bootstrap: Database
    template: Database
    clone: Database
    campaign: str
    preset: str
    session: str
    seed: int
    content_sha256: Digest
    foundation_sha256: Digest
    graph_foundation_sha256: Digest
    source: Reference
    inputs: Reference
    executable_sha256: Digest


class Stage(Record):
    tag: Literal["sql-stage-v1"]
    phase: Literal["attempt", "reached"]
    index: Annotated[int, Field(ge=1, le=21)]
    stage: str
    previous: Reference
    authority: Reference
    artifacts: list[Reference]


class InTestSeal(Record):
    tag: Literal["sql-in-test-seal-v1"]
    owner: Reference
    last: Reference
    stage_count: Literal[21]
    terminal_period: Literal[3]
    terminal_identity: Reference


def read_typed[T: Record](directory: PrivateEvidence, ref: Reference, cls: type[T]) -> T:
    return cls.model_validate(strict_json_bytes(directory.read_reference(ref)))


def admitted_sql_evidence(
    directory: PrivateEvidence, fixture_ref: Reference, test_pid: int
) -> tuple[SQLOwner, Reference, InTestSeal]:
    fixture = read_typed(directory, fixture_ref, Fixture)
    if (
        fixture_ref.path != "sql-fixture-v1.json"
        or fixture.test != TEST_NAME
        or fixture.run != str(RUN_PARENT / "sql-01")
        or fixture.evidence != str(directory.path)
        or directory.path != Path(fixture.run) / "evidence"
        or str(UUID(fixture.campaign)) != fixture.campaign
        or UUID(fixture.campaign).int == 0
        or fixture.template.name != "per281_runtime_template_" + fixture.canary[:12]
        or fixture.bootstrap.name != "postgres"
        or fixture.template.owner_oid != fixture.role_oid
        or int(fixture.cluster) >= 2**64
    ):
        raise StorageRefusal("SQL fixture identity differs from this exact run")
    for ref in [
        fixture.physical,
        fixture.inputs,
        fixture.source,
        fixture.policy,
        fixture.executable,
    ]:
        directory.verify(ref)
    if (
        len(
            {
                ref.path
                for ref in (
                    fixture.physical,
                    fixture.inputs,
                    fixture.source,
                    fixture.policy,
                    fixture.executable,
                )
            }
        )
        != 5
    ):
        raise StorageRefusal("SQL fixture artifacts have overlapping roles")
    claim_ref = directory.reference("sql-clone-claim-v1.json")
    claim = read_typed(directory, claim_ref, Claim)
    if (
        claim.fixture != fixture_ref
        or claim.pid != test_pid
        or claim.clone_name != f"per281_runtime_allocationatomic_{test_pid}"
        or claim.campaign != fixture.campaign
        or claim.template != fixture.template
        or claim.owner_oid != fixture.role_oid
    ):
        raise StorageRefusal("SQL clone claim does not bind the invoked test")
    clone_ref = directory.reference("sql-clone-identity-v1.json")
    clone = read_typed(directory, clone_ref, CloneIdentity)
    if (
        clone.claim != claim_ref
        or clone.clone.name != claim.clone_name
        or clone.clone.owner_oid != fixture.role_oid
        or clone.template != fixture.template
        or clone.canary != fixture.canary
        or clone.cluster != fixture.cluster
        or len({clone.clone.oid, fixture.bootstrap.oid, fixture.template.oid}) != 3
    ):
        raise StorageRefusal("SQL clone identity differs from the fixture or claim")
    owner_ref = directory.reference("sql-owner-v1.json")
    owner = read_typed(directory, owner_ref, SQLOwner)
    if (
        owner.fixture != fixture_ref
        or owner.clone_identity != clone_ref
        or owner.clone != clone.clone
        or owner.bootstrap != fixture.bootstrap
        or owner.template != fixture.template
        or owner.campaign != fixture.campaign
        or owner.source != fixture.source
        or owner.inputs != fixture.inputs
        or owner.preset != fixture.preset
        or owner.session != fixture.session
        or owner.seed != fixture.seed
        or owner.executable_sha256 != fixture.executable.sha256
    ):
        raise StorageRefusal("complete SQL owner differs from pinned fixture and clone")
    previous = fixture_ref
    verified: set[Reference] = set()
    transition_authorities = (
        (fixture_ref, fixture_ref),
        (fixture_ref, clone_ref),
        (clone_ref, clone_ref),
        (clone_ref, owner_ref),
    )
    for index, stage_name in enumerate(STAGES, 1):
        for phase in ("attempt", "reached"):
            name = f"stage-{index:02}-{stage_name}-{phase}.json"
            ref = directory.reference(name)
            stage = read_typed(directory, ref, Stage)
            if (
                (stage.phase, stage.index, stage.stage, stage.previous)
                != (phase, index, stage_name, previous)
                or stage.authority
                != (
                    transition_authorities[index - 1][int(phase == "reached")]
                    if index <= 4
                    else owner_ref
                )
                or (phase == "reached" and not stage.artifacts)
            ):
                raise StorageRefusal("SQL stage order or authority differs: " + name)
            for artifact in stage.artifacts:
                if artifact not in verified:
                    directory.verify(artifact)
                    verified.add(artifact)
            previous = ref
    seal_ref = directory.reference("in-test-seal-v1.json")
    seal = read_typed(directory, seal_ref, InTestSeal)
    if seal.owner != owner_ref or seal.last != previous or not seal.terminal_identity.bytes:
        raise StorageRefusal("SQL test seal omits its terminal authority")
    directory.verify(seal.terminal_identity)
    if os.path.lexists(directory.path / "first-divergence-v1.json"):
        raise StorageRefusal("SQL run published a divergence; retain exact fixture")
    return owner, seal_ref, seal


LINEAGE = (
    "babylon-postgres-lineage-v1|postgres=17|locale-provider=builtin|locale=C.UTF-8|"
    "encoding=UTF8|postgis=3.5.7|h3=4.5.0|h3_postgis=4.5.0|vector=0.8.5"
)
MEDIA_CHECKOUT = RUN_PARENT.parent / "babylon"


class DiskReservation(Record):
    tag: Literal["wayne-disk-reservation-v1"]
    profile: Literal["sql-01", "smoke-01", "walk-01", "ordinary-01"]
    source_head: str
    build_bytes: Annotated[int, Field(ge=0)]
    primary_bytes: Annotated[int, Field(gt=0)]
    evidence_bytes: Annotated[int, Field(gt=0)]
    restore_bytes: Annotated[int, Field(ge=0)]
    dump_bytes: Annotated[int, Field(ge=0)]
    archive_bytes: Annotated[int, Field(ge=0)]
    measured_basis: Annotated[str, Field(min_length=1)]


class NativeExpectations(Record):
    source_sha256: Sha256
    inputs_sha256: Sha256
    host_context_sha256: Sha256
    image_id: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    source_head: Annotated[str, Field(pattern="^[0-9a-f]{40}$")]
    capacity: Reference
    runtime: Reference
    client: Reference
    material_audit: Reference

    def products(self) -> dict[str, Reference]:
        return {
            "babylon-runtime": self.runtime,
            "babylon-client": self.client,
            "babylon-material-audit": self.material_audit,
        }


def _native_expectations(
    parent: PrivateEvidence, profile: str
) -> tuple[Reference, NativeExpectations]:
    raw = os.environ.get("BABYLON_WAYNE_NATIVE_EXPECTATION_REF")
    if not raw:
        raise StorageRefusal("missing released native expectation reference")
    try:
        ref = Reference.model_validate(strict_json_bytes(raw.encode()))
        if ref.path != f"{profile}-native-expectations.json":
            raise StorageRefusal("released native expectation reference names another run")
        packet = NativeExpectations.model_validate(
            strict_json_bytes(parent.read_reference(ref, 8192))
        )
    except StorageRefusal:
        raise
    except (OSError, ValueError) as error:
        raise StorageRefusal("invalid released native expectation reference or record") from error
    if packet.capacity.path != f"{profile}-capacity.json" or any(
        product.path != "normal-" + name for name, product in packet.products().items()
    ):
        raise StorageRefusal("released native expectations name a different capacity or product")
    return ref, packet


def released_inventory(root: Path) -> tuple[str, str]:
    """Hash the two manifests using the same source closure and preset order as capture."""
    result = subprocess.run(
        [
            "bash",
            "-euo",
            "pipefail",
            "-c",
            'die() { echo "$*" >&2; exit 2; }; source "$REPO_ROOT/tools/postgres_national_lifecycle.sh"; national_release_inventory',
        ],
        cwd=root,
        env={**os.environ, "REPO_ROOT": str(root)},
        capture_output=True,
        timeout=120,
        check=False,
    )
    hashes = result.stdout.decode("ascii").splitlines()
    if (
        result.returncode
        or len(hashes) != 2
        or not all(re.fullmatch(r"[0-9a-f]{64}  -", row) for row in hashes)
    ):
        raise StorageRefusal("cannot enumerate both native release manifests")
    return hashes[0][:64], hashes[1][:64]


def verify_release_inputs(root: Path, profile: str) -> tuple[Reference, NativeExpectations]:
    parent = PrivateEvidence(RUN_PARENT)
    reference, expected = _native_expectations(parent, profile)
    if (
        expected.capacity != parent.reference(f"{profile}-capacity.json")
        or expected.image_id != os.environ.get("BABYLON_POSTGRES_IMAGE_ID")
        or expected.host_context_sha256 != os.environ.get("BABYLON_WAYNE_HOST_CONTEXT_SHA256")
        or expected.host_context_sha256 != parent.reference("host-process-context.json").sha256
        or expected.source_head != exact_output(["git", "-C", str(root), "rev-parse", "HEAD"])
        or exact_output(["git", "-C", str(root), "status", "--porcelain"])
        or (expected.source_sha256, expected.inputs_sha256) != released_inventory(root)
    ):
        raise StorageRefusal("released native source, inputs, host context or image differ")
    return reference, expected


def _exec_bytes(args: list[str], *, timeout: int = 15) -> bytes:
    return subprocess.run(args, capture_output=True, check=True, timeout=timeout).stdout


def _one_docker(kind: str, target: str) -> dict[str, Any]:
    packet = strict_json_bytes(_exec_bytes(["docker", kind, "inspect", target]))
    if not isinstance(packet, list) or len(packet) != 1 or not isinstance(packet[0], dict):
        raise StorageRefusal("Docker inspection did not return one exact object")
    return packet[0]


def container_mounts(
    record: dict[str, Any], checkout: Path, run: Path, canary: str, cid: str, image: str
) -> dict[str, object]:
    if (
        re.fullmatch("[0-9a-f]{32}", canary) is None
        or re.fullmatch("[0-9a-f]{64}", cid) is None
        or re.fullmatch("sha256:[0-9a-f]{64}", image) is None
        or record["Id"] != cid
        or record["Name"] != "/babylon-runtime-pg-" + canary[:12]
        or record["Image"] != image
        or record["Config"]["Labels"]["babylon.disposable_runtime"] != canary
    ):
        raise StorageRefusal("Docker container, image, name or canary label changed")
    required = {
        PGDATA: (str(run / "pgdata"), True),
        "/etc/postgresql/postgresql.conf": (
            str(checkout / "docker/postgres/postgresql.ci.conf"),
            False,
        ),
        "/docker-entrypoint-initdb.d": (str(checkout / "docker/postgres/initdb"), False),
    }
    mounts = record["Mounts"]
    if len(mounts) != len(required) or {m["Destination"] for m in mounts} != set(required):
        raise StorageRefusal("Docker mount roster differs from the three selected mounts")
    for mount in mounts:
        path, writable = required[mount["Destination"]]
        if (
            mount["Type"] != "bind"
            or mount["Source"] != path
            or mount["RW"] is not writable
            or mount["Propagation"] != "rprivate"
            or mount.get("Name")
        ):
            raise StorageRefusal("Docker mount source, write mode or propagation differs")
    request = record["HostConfig"]["PortBindings"]
    if (
        record["HostConfig"]["PublishAllPorts"] is not False
        or not isinstance(request, dict)
        or set(request) != {"5432/tcp"}
        or not isinstance(request["5432/tcp"], list)
        or len(request["5432/tcp"]) != 1
        or request["5432/tcp"][0]
        not in ({"HostIp": "127.0.0.1", "HostPort": ""}, {"HostIp": "127.0.0.1", "HostPort": "0"})
    ):
        raise StorageRefusal("Docker port request is not one dynamic loopback endpoint")
    return {"mounts": mounts, "port_request": request}


def _daemon() -> str:
    daemon = exact_output(["docker", "info", "--format", "{{.ID}}"])
    if not daemon or re.fullmatch("[A-Za-z0-9:-]+", daemon) is None:
        raise StorageRefusal("Docker engine ID is absent or malformed")
    return daemon


def _daemon_endpoint() -> str:
    if any(
        key in os.environ
        for key in ("DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH")
    ):
        raise StorageRefusal("inherited Docker daemon override")
    context = exact_output(["docker", "context", "show"])
    endpoint = exact_output(
        ["docker", "context", "inspect", context, "--format", "{{.Endpoints.docker.Host}}"]
    )
    if not endpoint.startswith("unix:///") or not stat.S_ISSOCK(Path(endpoint[7:]).stat().st_mode):
        raise StorageRefusal("physical admission requires a local Docker engine socket")
    return endpoint


def _image(image_id: str) -> dict[str, object]:
    if re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
        raise StorageRefusal("selected media profiles require the full local image SHA")
    record = _one_docker("image", "babylon-postgres-runtime:local")
    if (
        record["Id"] != image_id
        or record["Os"] != "linux"
        or record["Architecture"] != "amd64"
        or record["Config"]["Entrypoint"] != ["docker-entrypoint.sh"]
    ):
        raise StorageRefusal("local image ID, platform or entrypoint differs")
    return {
        "id": image_id,
        "entrypoint": record["Config"]["Entrypoint"],
        "os": record["Os"],
        "architecture": record["Architecture"],
        "repo_digests": record["RepoDigests"],
    }


def _host_identity(path: Path) -> dict[str, int]:
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode):
        raise StorageRefusal("PGDATA is not a directory")
    return {
        "major": os.major(info.st_dev),
        "minor": os.minor(info.st_dev),
        "inode": info.st_ino,
        "uid": info.st_uid,
        "gid": info.st_gid,
        "mode": stat.S_IMODE(info.st_mode),
    }


def _pin_json(pins: list[DirectoryPin]) -> list[dict[str, object]]:
    return [pin.model_dump() for pin in pins]


def reserve_run(profile: str, focus: str, periods: str, evidence: Path, root: Path) -> None:
    run = profile_run(profile, focus, periods, evidence)
    if root != MEDIA_CHECKOUT or root.resolve(strict=True) != root:
        raise StorageRefusal("Wayne operation must run in its released canonical checkout")
    if any(
        key.startswith("PG") or key.endswith("_DSN") or key == "CARGO_TARGET_DIR"
        for key in os.environ
    ):
        raise StorageRefusal("Wayne admission has an inherited SQL or target override")
    context = None
    if profile != "sql-01":
        selected_policy(
            Path(
                os.environ.get("BABYLON_STORAGE_POLICY_PATH")
                or root / "contracts/national_storage_qualification_v6.json"
            )
        )
        context = actual_host_context()
    _daemon_endpoint()
    _image(os.environ["BABYLON_POSTGRES_IMAGE_ID"])
    if exact_output(["git", "-C", str(root), "status", "--porcelain"]):
        raise StorageRefusal("Wayne admission requires a clean source and operator")
    head = exact_output(["git", "-C", str(root), "rev-parse", "HEAD"])
    # The released operator supplies measured capacity values before each run.
    # statvfs already accounts for all previously retained primary and evidence bytes.
    if not RUN_PARENT.is_dir():
        if profile != "sql-01":
            raise StorageRefusal("native admission requires its existing private release directory")
        with pinned_ancestry(RUN_PARENT.parent):
            RUN_PARENT.mkdir(mode=0o700)
    with pinned_ancestry(RUN_PARENT) as parent_pins:
        if parent_pins[-1].uid != os.geteuid() or parent_pins[-1].mode != 0o700:
            raise StorageRefusal("Wayne run parent must be private and operator owned")
        # Shell redirection requests 0666. Linux uses an inherited default ACL
        # in place of the umask and encodes its mask in the file's group bits.
        default = {tag: perm for tag, perm, _ in parent_pins[-1].default_acl}
        if default and (default.get(16, default[4]) & 6 or default[32] & 6 or default[1] != 7):
            raise StorageRefusal(
                "inherited default ACL cannot create private readable shell evidence"
            )
        reservations = PrivateEvidence(RUN_PARENT)
        reservation_ref = reservations.reference(f"{profile}-capacity.json")
        native_ref = None
        if profile != "sql-01":
            native_ref, expected = verify_release_inputs(root, profile)
            if head != expected.source_head or reservation_ref != expected.capacity:
                raise StorageRefusal("released native source HEAD or capacity reference differs")
        reservation = read_typed(reservations, reservation_ref, DiskReservation)
        if reservation.profile != profile or reservation.source_head != head:
            raise StorageRefusal("disk capacity evidence does not name this run and source")
        if profile != "sql-01" and not (
            reservation.restore_bytes and reservation.dump_bytes and reservation.archive_bytes
        ):
            raise StorageRefusal("native capacity omits restore, dump or offline archive")
        required = sum(
            (
                reservation.build_bytes,
                reservation.primary_bytes,
                reservation.evidence_bytes,
                reservation.restore_bytes,
                reservation.dump_bytes,
                reservation.archive_bytes,
            )
        )
        available = os.statvfs(RUN_PARENT)
        free = available.f_bavail * available.f_frsize
        if free < required:
            raise StorageRefusal("available media space is below the measured run reservation")
        if profile != "sql-01":
            if run.name == "memory_capture":
                from tools.devtools.national_native_pair import verify_retired_predecessor

                assert native_ref is not None
                verify_retired_predecessor(profile, native_ref)
            run.parent.mkdir(mode=0o700, exist_ok=True)
            with pinned_ancestry(run.parent) as workload_pins:
                if (
                    workload_pins[:-1] != parent_pins
                    or workload_pins[-1].mode != 0o700
                    or workload_pins[-1].uid != os.geteuid()
                ):
                    raise StorageRefusal(
                        "native workload parent differs from private media admission"
                    )
                parent_pins = workload_pins
        run.mkdir(mode=0o700)
        with pinned_ancestry(run) as run_pins:
            if (
                run_pins[:-1] != parent_pins
                or run_pins[-1].mode != 0o700
                or run_pins[-1].uid != os.geteuid()
            ):
                raise StorageRefusal("private run directory or pinned ancestry changed")
            pgdata = run / "pgdata"
            pgdata.mkdir(mode=0o700)
            initial = _host_identity(pgdata)
            if initial["mode"] != 0o700 or initial["uid"] != os.geteuid() or any(pgdata.iterdir()):
                raise StorageRefusal("new PGDATA was not empty, private and operator owned")
            if profile != "sql-01":
                for name in ("xdg", "raw", "backup"):
                    (run / name).mkdir(mode=0o700)
                for name in ("state", "data", "config", "cache"):
                    (run / "xdg" / name).mkdir(mode=0o700)
            evidence.mkdir(mode=0o700)
            declaration = {
                "profile": profile,
                "run": str(run),
                "source_head": head,
                "capacity": reservation.model_dump(),
                "reservation": reservation_ref.model_dump(),
                "free_bytes": free,
                "ancestry": _pin_json(run_pins),
                "creator": initial,
                "uid_namespace": Path("/proc/self/uid_map").read_text(),
                "gid_namespace": Path("/proc/self/gid_map").read_text(),
                "daemon": _daemon(),
                "image": _image(os.environ["BABYLON_POSTGRES_IMAGE_ID"]),
            }
            if native_ref is not None:
                declaration["native_expectations"] = native_ref.model_dump()
            selected = PrivateEvidence(evidence)
            selected.publish_json("media-creation.json", declaration)
            selected.publish("source-head", (head + "\n").encode())
            if context is not None:
                selected.publish_json("host-native-admission.json", context.model_dump())


def released_head(directory: PrivateEvidence, root: Path) -> str:
    packet = strict_json_bytes(directory.read_reference(directory.reference("media-creation.json")))
    current = exact_output(["git", "-C", str(root), "rev-parse", "HEAD"])
    if (
        not isinstance(packet, dict)
        or packet.get("source_head") != current
        or re.fullmatch(r"[0-9a-f]{40}", current) is None
        or exact_output(["git", "-C", str(root), "status", "--porcelain"])
    ):
        raise StorageRefusal("released HEAD differs from the current clean source")
    parent = PrivateEvidence(RUN_PARENT)
    profile = (
        "sql-01"
        if directory.path == RUN_PARENT / "sql-01/evidence"
        else owned_native_path(directory.path)[0]
    )
    reference = parent.reference(f"{profile}-capacity.json")
    reservation = read_typed(parent, reference, DiskReservation)
    if (
        reservation.source_head != current
        or packet.get("reservation") != reference.model_dump()
        or packet.get("capacity") != reservation.model_dump()
        or reservation.profile != profile
        or directory.read_reference(directory.reference("source-head")) != (current + "\n").encode()
    ):
        raise StorageRefusal("released HEAD or the original capacity reservation changed")
    return current


def _media_creation(directory: PrivateEvidence, pins: list[DirectoryPin]) -> dict[str, Any]:
    released_head(directory, MEDIA_CHECKOUT)
    ref = directory.reference("media-creation.json")
    data = strict_json_bytes(directory.read_reference(ref))
    if not isinstance(data, dict) or data.get("ancestry") != _pin_json(pins):
        raise StorageRefusal("creator proof differs from the current media ancestry")
    if data.get("daemon") != _daemon() or data.get("image") != _image(
        os.environ["BABYLON_POSTGRES_IMAGE_ID"]
    ):
        raise StorageRefusal("creator proof differs from the current daemon/image")
    creator = data["creator"]
    data_path = directory.path.parent / "pgdata"
    fd = os.open(data_path, os.O_PATH | os.O_NOFOLLOW | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        if _mount_id(fd) != pins[-1].mount_id:
            raise StorageRefusal("PGDATA has an unexpected nested mount")
    finally:
        os.close(fd)
    current = _host_identity(data_path)
    if any(current[field] != creator[field] for field in ("major", "minor", "inode", "mode")):
        raise StorageRefusal("PGDATA is no longer the same private directory")
    return data


def create_and_start(directory: PrivateEvidence, root: Path, canary: str, image: str) -> str:
    run = directory.path.parent
    with pinned_ancestry(run) as pins:
        created = _media_creation(directory, pins)
        pgdata = run / "pgdata"
        if _host_identity(pgdata) != created["creator"] or any(pgdata.iterdir()):
            raise StorageRefusal("new PGDATA changed before Docker creation")
        cid = exact_output(
            [
                "docker",
                "create",
                "--log-driver",
                "local",
                "--log-opt",
                "max-size=10m",
                "--log-opt",
                "max-file=2",
                "--name",
                "babylon-runtime-pg-" + canary[:12],
                "--label",
                "babylon.disposable_runtime=" + canary,
                "--publish",
                "127.0.0.1::5432",
                "--mount",
                f"type=bind,source={pgdata},target={PGDATA}",
                "--mount",
                f"type=bind,source={root}/docker/postgres/postgresql.ci.conf,target=/etc/postgresql/postgresql.conf,readonly",
                "--mount",
                f"type=bind,source={root}/docker/postgres/initdb,target=/docker-entrypoint-initdb.d,readonly",
                "--shm-size=1g",
                "--env",
                "POSTGRES_USER=test",
                "--env",
                "POSTGRES_PASSWORD=test",
                "--env",
                "POSTGRES_DB=babylon_test",
                image,
                "postgres",
                "-c",
                "config_file=/etc/postgresql/postgresql.conf",
                "-c",
                "babylon.disposable_runtime=" + canary,
                *(["-c", "max_wal_senders=0"] if run.name != "sql-01" else []),
            ],
            timeout=30,
        )
        record = _one_docker("container", cid)
        mounts = container_mounts(record, root, run, canary, cid, image)
        if record["State"]["Status"] != "created" or record["State"]["Running"] is not False:
            raise StorageRefusal(
                "selected PostgreSQL entrypoint already ran before mount admission"
            )
        directory.publish_json(
            "media-container-created.json",
            {
                "container": cid,
                "canary": canary,
                "daemon": created["daemon"],
                "image": image,
                **mounts,
            },
        )
        with pinned_ancestry(run) as current:
            if (
                current != pins
                or _host_identity(pgdata) != created["creator"]
                or any(pgdata.iterdir())
            ):
                raise StorageRefusal("ancestry or empty source changed before Docker start")
            _media_creation(directory, current)
            if exact_output(["docker", "start", cid], timeout=60) != cid:
                raise StorageRefusal("Docker did not start the exact inspected container")
        return cid


def _mapped(value: int, mapping: str) -> int:
    candidates: list[int] = []
    for line in mapping.splitlines():
        columns = line.split()
        if len(columns) != 3 or any(not item.isascii() or not item.isdecimal() for item in columns):
            raise StorageRefusal("unverifiable user namespace map")
        inside, outside, length = map(int, columns)
        if inside <= value < inside + length:
            candidates.append(outside + value - inside)
    if len(candidates) != 1:
        raise StorageRefusal("numeric UID or GID has no unique namespace mapping")
    return candidates[0]


def _assigned_port(record: dict[str, Any], cid: str) -> int:
    ports = record["NetworkSettings"]["Ports"]
    if not isinstance(ports, dict) or set(ports) != {"5432/tcp"}:
        raise StorageRefusal("unexpected published PostgreSQL port")
    bindings = ports["5432/tcp"]
    if (
        not isinstance(bindings, list)
        or len(bindings) != 1
        or not isinstance(bindings[0], dict)
        or set(bindings[0]) != {"HostIp", "HostPort"}
        or bindings[0]["HostIp"] != "127.0.0.1"
        or re.fullmatch("[1-9][0-9]{0,4}", bindings[0]["HostPort"]) is None
    ):
        raise StorageRefusal("published PostgreSQL binding is not one assigned loopback endpoint")
    port = int(bindings[0]["HostPort"])
    if port > 65535 or exact_output(["docker", "port", cid, "5432/tcp"]) != f"127.0.0.1:{port}":
        raise StorageRefusal("daemon and actual mapped endpoint differ")
    return port


def native_wal_senders(observed: tuple[object, ...] | None) -> int:
    if (
        observed is None
        or len(observed) != 1
        or not isinstance(observed[0], str)
        or observed[0] != "0"
    ):
        raise StorageRefusal("native physical admission requires zero WAL senders")
    return int(observed[0])


@contextmanager
def physical_session(
    port: int, supplied: psycopg.Connection[Any] | None
) -> Iterator[psycopg.Connection[Any]]:
    if supplied is None:
        with _connect(port, "template1") as connection:
            yield connection
    else:
        info = supplied.info
        if (info.host, info.port, info.dbname, info.user) != (
            "127.0.0.1",
            port,
            "template1",
            "test",
        ):
            raise StorageRefusal(
                "maintenance connection is not the selected loopback template1 login"
            )
        yield supplied


def _postgres_pid1_credentials(status: str) -> tuple[int, int]:
    fields: dict[str, list[str]] = {}
    for line in status.splitlines():
        key, _, value = line.partition(":")
        if key in ("Name", "Pid", "Uid", "Gid"):
            if key in fields:
                raise StorageRefusal("duplicate PostgreSQL PID 1 status field")
            fields[key] = value.split()
    if fields.get("Name") != ["postgres"] or fields.get("Pid") != ["1"]:
        raise StorageRefusal("container PID 1 is not postgres")
    # The entrypoint switches to the postgres account for all four Linux IDs
    # (real, effective, saved and filesystem) before starting the server.
    for key in ("Uid", "Gid"):
        ids = fields.get(key, [])
        if (
            len(ids) != 4
            or len(set(ids)) != 1
            or not re.fullmatch(r"[1-9][0-9]{0,9}", ids[1])
            or int(ids[1]) >= 2**32 - 1
        ):
            raise StorageRefusal("invalid PostgreSQL PID 1 credentials")
    return int(fields["Uid"][1]), int(fields["Gid"][1])


def physical_observation(
    directory: PrivateEvidence,
    root: Path,
    cid: str,
    canary: str,
    image: str,
    *,
    physical_connection: psycopg.Connection[Any] | None = None,
) -> dict[str, object]:
    run = directory.path.parent
    with pinned_ancestry(run) as pins:
        created = _media_creation(directory, pins)
        record = _one_docker("container", cid)
        mounts = container_mounts(record, root, run, canary, cid, image)
        if record["State"]["Status"] != "running" or record["State"]["Running"] is not True:
            raise StorageRefusal("selected container is not running")
        checked = strict_json_bytes(
            directory.read_reference(directory.reference("media-container-created.json"))
        )
        if checked != {
            "container": cid,
            "canary": canary,
            "daemon": created["daemon"],
            "image": image,
            **mounts,
        }:
            raise StorageRefusal("created and live container ownership differ")
        port = _assigned_port(record, cid)
        inside = ["docker", "exec", cid]
        stat_fields = exact_output([*inside, "stat", "-c", "%d %i %u %g %a", PGDATA]).split()
        if len(stat_fields) != 5:
            raise StorageRefusal("container PGDATA metadata is incomplete")
        dev, inode, uid, gid = map(int, stat_fields[:4])
        internal = {
            "major": os.major(dev),
            "minor": os.minor(dev),
            "inode": inode,
            "uid": uid,
            "gid": gid,
            "mode": int(stat_fields[4], 8),
        }
        host = _host_identity(run / "pgdata")
        pid = record["State"]["Pid"]
        if type(pid) is not int or pid < 1:
            raise StorageRefusal("container has no verified host process")
        uid_map = Path(f"/proc/{pid}/uid_map").read_text()
        gid_map = Path(f"/proc/{pid}/gid_map").read_text()
        if (
            internal["mode"] != 0o700
            or any(host[k] != internal[k] for k in ("major", "minor", "inode", "mode"))
            or host["uid"] != _mapped(uid, uid_map)
            or host["gid"] != _mapped(gid, gid_map)
        ):
            raise StorageRefusal("actual host/container PGDATA or mapped owner differs")
        # The pinned entrypoint changes PGDATA's owner and preserves its original group.
        if host["gid"] != created["creator"]["gid"]:
            raise StorageRefusal("PGDATA host group changed since creation")
        process = exact_output([*inside, "cat", "/proc/1/status"])
        server_uid, server_gid = _postgres_pid1_credentials(process)
        if (
            server_uid != uid
            or _exec_bytes([*inside, "id", "-u", "postgres"]) != f"{server_uid}\n".encode()
            or _exec_bytes([*inside, "id", "-g", "postgres"]) != f"{server_gid}\n".encode()
        ):
            raise StorageRefusal(
                "PostgreSQL process differs from the postgres account or PGDATA owner"
            )
        lineage = _exec_bytes([*inside, "cat", PGDATA + "/.babylon-postgres-lineage-v1"])
        major = _exec_bytes([*inside, "cat", PGDATA + "/PG_VERSION"])
        if lineage != (LINEAGE + "\n").encode() or major != b"17\n":
            raise StorageRefusal("actual cluster version or lineage marker differs")
        native_settings: dict[str, int] = {}
        with physical_session(port, physical_connection) as conn:
            if run.name != "sql-01":
                slots = conn.execute("SELECT current_setting('max_connections')").fetchone()
                if slots != ("50",):
                    raise StorageRefusal("native backup requires the released 50 connection slots")
                native_settings["max_connections"] = int(slots[0])
                native_settings["max_wal_senders"] = native_wal_senders(
                    conn.execute("SELECT current_setting('max_wal_senders')").fetchone()
                )
            row = conn.execute("""
                SELECT session_user::text, current_user::text, current_database()::text,
                       current_setting('babylon.disposable_runtime',true), current_setting('data_directory'),
                       current_setting('server_version_num'), (pg_control_system()).system_identifier::text,
                       pg_encoding_to_char(encoding), datlocprovider::text, datlocale
                FROM pg_catalog.pg_database WHERE datname=current_database()
            """).fetchone()
            if (
                row is None
                or row[:6] != ("test", "test", "template1", canary, PGDATA, "170011")
                or row[7:] != ("UTF8", "b", "C.UTF-8")
            ):
                raise StorageRefusal(
                    "actual SQL canary, cluster version, locale or directory differs"
                )
            cluster = str(row[6])
            extensions = conn.execute("""
                SELECT name,default_version,installed_version FROM pg_catalog.pg_available_extensions
                WHERE name IN ('postgis','vector','h3','h3_postgis') ORDER BY name
            """).fetchall()
            expected = {"postgis": "3.5.7", "vector": "0.8.5", "h3": "4.5.0", "h3_postgis": "4.5.0"}
            if {name: default for name, default, _ in extensions} != expected or any(
                actual != expected[name]
                for name, _, actual in extensions
                if name in {"postgis", "vector"} or actual is not None
            ):
                raise StorageRefusal("actual installed or available extensions differ")
        return {
            "daemon": created["daemon"],
            "container": cid,
            "name": record["Name"][1:],
            "image": created["image"],
            "label": canary,
            **mounts,
            "port": port,
            "cluster": cluster,
            "path": str(run / "pgdata"),
            "destination": PGDATA,
            "creator": created["creator"],
            "host": host,
            "container_root": internal,
            **native_settings,
            "uid_map": uid_map,
            "gid_map": gid_map,
            "ancestry": created["ancestry"],
            "lineage": lineage.decode(),
            "pg_version": major.decode(),
            "extensions": [list(entry) for entry in extensions],
            "sql": list(row),
            "server_uid": server_uid,
            "server_gid": server_gid,
            "pid": pid,
        }


def _new_stream(directory: PrivateEvidence, name: str, *, executable: bool = False) -> BinaryIO:
    if len(_path_components(name)) != 1:
        raise StorageRefusal("output must be an immediate private evidence file")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    return os.fdopen(os.open(directory.path / name, flags, 0o700 if executable else 0o600), "wb")


def _archive_file(
    directory: PrivateEvidence, source: Path, name: str, *, executable: bool = False
) -> Reference:
    from shutil import copyfileobj

    with os.fdopen(os.open(source, FILE_FLAGS), "rb") as original:
        info = os.fstat(original.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise StorageRefusal("archive source is not a regular file")
        with _new_stream(directory, name, executable=executable) as output:
            copyfileobj(original, output, 1024 * 1024)
            output.flush()
            os.fsync(output.fileno())
        original.seek(0)
        expected = _receipt(original, name)
    directory.verify(expected)
    return expected


ARCHIVE_NAME = "ignored-tests.tar.zst"
SQL_PACKAGE = "babylon-persistence"
SQL_LIB = "babylon_persistence"
CARGO_DISPATCH = Path("/home/user/.local/share/codex-rust-host/bin/cargo")
NEXTEST = Path("/home/user/.cargo/bin/cargo-nextest")


def _pinned_archive_tools() -> dict[str, str]:
    """The operator uses the same installed plugin for archive creation and reuse."""
    installed = CARGO_DISPATCH.parent.parent / "v13/cargo"
    if CARGO_DISPATCH.resolve(strict=True) != installed:
        raise StorageRefusal("governed Cargo dispatcher differs from installed v13")
    tools = {
        installed: "daed14c184f307fbe93a643e0886f1cc2015184e16e619bd9badd7a029f9c504",
        installed.with_name(
            "policy.sh"
        ): "6d92ebafa2b03bbcb6492c1db958846090ee64ee30bdd239fd6c4e1e5b933080",
        NEXTEST: "1281390452db2ecc1c1a70f2d335004bec1f7ee5986ea4d26919bf2de614c8c6",
    }
    for path, digest in tools.items():
        with os.fdopen(os.open(path, FILE_FLAGS), "rb") as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or _receipt(source, str(path)).sha256 != digest:
                raise StorageRefusal(f"SQL archive tool identity differs: {path}")
    if Path(os.environ.get("CARGO_HOME", Path.home() / ".cargo")) != NEXTEST.parent.parent:
        raise StorageRefusal("Cargo plugin discovery requires the pinned Cargo home")
    return {str(path): digest for path, digest in tools.items()}


def _publish_test_archive(directory: PrivateEvidence, staging: PrivateEvidence) -> Reference:
    # nextest can overwrite a destination. Only link its successful, fsynced output
    # from this run's freshly created staging directory into the final namespace.
    with staging.file(ARCHIVE_NAME) as stream:
        if os.fstat(stream.fileno()).st_nlink != 1:
            raise StorageRefusal("staged nextest archive has another hard link")
        os.fchmod(stream.fileno(), 0o400)
        os.fsync(stream.fileno())
        reference = _receipt(stream, ARCHIVE_NAME)
        if not reference.bytes:
            raise StorageRefusal("empty nextest archive")
        os.link(staging.path / ARCHIVE_NAME, directory.path / ARCHIVE_NAME, follow_symlinks=False)
        parent = os.open(directory.path, DIR_FLAGS)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
        directory.verify(reference)
        (staging.path / ARCHIVE_NAME).unlink()
    return reference


def _sql_archive_member(
    root: Path,
    compiler: bytes,
    cargo: dict[str, Any],
    archive: dict[str, Any],
    listed: dict[str, Any],
) -> str:
    rust = root / "rust"
    manifest = str(rust / "crates" / SQL_PACKAGE / "Cargo.toml")
    target = str(rust / "target")
    if cargo.get("workspace_root") != str(rust) or cargo.get("target_directory") != target:
        raise StorageRefusal("archived Cargo workspace or target directory differs")
    packages = [
        p for p in cargo["packages"] if p["name"] == SQL_PACKAGE and p["manifest_path"] == manifest
    ]
    if len(packages) != 1 or packages[0]["id"] not in cargo["workspace_members"]:
        raise StorageRefusal("archived Cargo package is not the checkout persistence crate")
    artifacts = []
    for line in compiler.splitlines():
        row = strict_json_bytes(line)
        if (
            isinstance(row, dict)
            and row.get("reason") == "compiler-artifact"
            and row["profile"]["test"] is True
            and row["executable"] is not None
        ):
            artifacts.append(row)
    if len(artifacts) != 1:
        raise StorageRefusal("expected exactly one compiled test executable")
    row = artifacts[0]
    if (
        row["package_id"] != packages[0]["id"]
        or row["manifest_path"] != manifest
        or row["target"]["name"] != SQL_LIB
        or row["target"]["kind"] != ["lib"]
        or row["target"]["src_path"] != str(Path(manifest).parent / "src/lib.rs")
        or row["executable"] not in row["filenames"]
    ):
        raise StorageRefusal("compiled test executable does not identify the persistence lib")
    # Cargo's original build directory is metadata only. Never open anything under it.
    build = cargo["build_directory"]
    filename = Path(row["executable"]).name
    suffix = Path("debug/deps") / filename
    if (
        not isinstance(build, str)
        or not Path(build).is_absolute()
        or ".." in Path(build).parts
        or build != str(Path(build))
        or not re.fullmatch(r"babylon_persistence-[0-9a-f]{16}", filename)
        or row["executable"] != str(Path(build) / suffix)
    ):
        raise StorageRefusal("compiler executable differs from the expected build-directory member")
    expected = {
        "binary-id": SQL_PACKAGE,
        "binary-name": SQL_LIB,
        "kind": "lib",
        "package-id": row["package_id"],
        "build-platform": "target",
        "binary-path": str(rust / "target" / suffix),
    }
    # 0.9.143 omits the separate build directory in archive metadata. Its
    # binaries-only listing materializes the normalized target as the build directory.
    if (
        "build-directory" in archive["rust-build-meta"]
        or listed["rust-build-meta"].get("build-directory") != target
    ):
        raise StorageRefusal("nextest archive and list disagree on normalized build directory")
    for metadata in (archive, listed):
        build_meta = metadata["rust-build-meta"]
        if build_meta["target-directory"] != target or metadata["rust-binaries"] != {
            SQL_PACKAGE: expected
        }:
            raise StorageRefusal("nextest binary identity or normalized target path differs")
    return str(Path("target") / suffix)


def _nextest_output(
    directory: PrivateEvidence,
    root: Path,
    command: list[str],
    stdout_name: str,
    stderr_name: str,
    *,
    timeout: int,
    env: dict[str, str] | None = None,
) -> tuple[Reference, bytes]:
    try:
        result = subprocess.run(
            command,
            cwd=root / "rust",
            env=env,
            capture_output=True,
            timeout=timeout,
            check=False,
            umask=0o077,
        )
    except subprocess.TimeoutExpired as error:
        directory.publish(stdout_name, error.stdout or b"")
        directory.publish(stderr_name, error.stderr or b"")
        raise
    stdout = directory.publish(stdout_name, result.stdout)
    directory.publish(stderr_name, result.stderr)
    result.check_returncode()
    return stdout, result.stdout


def _build_test(directory: PrivateEvidence, root: Path) -> Reference:
    tool_ref = directory.publish_json("ignored-archive-tools.json", _pinned_archive_tools())
    staging = PrivateEvidence(directory.path / "ignored-build-staging")
    staging.path.mkdir(mode=0o700)
    compiler_ref, compiler = _nextest_output(
        directory,
        root,
        [
            str(CARGO_DISPATCH),
            "nextest",
            "archive",
            "-p",
            SQL_PACKAGE,
            "--lib",
            "--locked",
            "--cargo-message-format=json",
            "--archive-file",
            str(staging.path / ARCHIVE_NAME),
        ],
        "ignored-build.jsonl",
        "ignored-build.stderr",
        env={
            **os.environ,
            "PATH": os.pathsep.join(
                (str(CARGO_DISPATCH.parent), str(NEXTEST.parent), os.environ["PATH"])
            ),
        },
        timeout=900,
    )
    archive = _publish_test_archive(directory, staging)
    source_unchanged(root, directory.path)
    extracted = PrivateEvidence(directory.path / "ignored-extracted")
    extracted.path.mkdir(mode=0o700)
    _pinned_archive_tools()
    directory.verify(archive)
    sealed = (directory.path / archive.path).lstat()
    list_ref, list_bytes = _nextest_output(
        directory,
        root,
        [
            str(NEXTEST),
            "nextest",
            "list",
            "--archive-file",
            str(directory.path / archive.path),
            "--extract-to",
            str(extracted.path),
            "--list-type",
            "binaries-only",
            "--message-format=json",
        ],
        "ignored-binaries.json",
        "ignored-extract.stderr",
        timeout=120,
    )
    after = (directory.path / archive.path).lstat()
    if (sealed.st_dev, sealed.st_ino, sealed.st_ctime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_ctime_ns,
    ):
        raise StorageRefusal("nextest archive changed during extraction")
    directory.verify(archive)

    def metadata(name: str) -> tuple[Reference, dict[str, Any]]:
        ref = directory.extracted_member(
            f"{extracted.path.name}/target/nextest/{name}-metadata.json"
        )
        raw = strict_json_bytes(directory.read_reference(ref))
        if not isinstance(raw, dict):
            raise StorageRefusal(f"expected nextest {name} metadata object")
        return ref, raw

    cargo_ref, cargo = metadata("cargo")
    binaries_ref, binaries = metadata("binaries")
    listing = strict_json_bytes(list_bytes)
    if not isinstance(listing, dict):
        raise StorageRefusal("expected nextest binary list object")
    member = _sql_archive_member(root, compiler, cargo, binaries, listing)
    selected = directory.extracted_member(f"{extracted.path.name}/{member}", executable=True)
    archived = _archive_file(
        directory, directory.path / selected.path, "ignored-test", executable=True
    )
    if (archived.bytes, archived.sha256) != (selected.bytes, selected.sha256):
        raise StorageRefusal("extracted nextest member changed before custody transfer")
    directory.publish_json(
        "ignored-archive-custody.json",
        {
            "tools": tool_ref.model_dump(),
            "archive": archive.model_dump(),
            "compiler": compiler_ref.model_dump(),
            "cargo_metadata": cargo_ref.model_dump(),
            "binaries_metadata": binaries_ref.model_dump(),
            "binary_list": list_ref.model_dump(),
            "member": selected.model_dump(),
            "executable": archived.model_dump(),
        },
    )
    listed = subprocess.run(
        [str(directory.path / archived.path), TEST_NAME, "--ignored", "--exact", "--list"],
        cwd=root / "rust",
        capture_output=True,
        timeout=90,
        check=False,
    )
    directory.publish("ignored-list.stdout", listed.stdout)
    directory.publish("ignored-list.stderr", listed.stderr)
    listed.check_returncode()
    lines = [item for item in listed.stdout.decode().splitlines() if item]
    if lines != [TEST_NAME + ": test", "1 test, 0 benchmarks"] or listed.stderr:
        raise StorageRefusal("archived ignored-test listing did not select exactly the named test")
    return archived


def _database(conn: psycopg.Connection[Any], name: str) -> Database:
    row = conn.execute(
        "SELECT datname::text,oid,datdba FROM pg_catalog.pg_database WHERE datname=%s", (name,)
    ).fetchone()
    if row is None:
        raise StorageRefusal("selected database identity is absent")
    return Database(name=row[0], oid=row[1], owner_oid=row[2])


def _connect(port: int, dbname: str = "postgres") -> psycopg.Connection[Any]:
    return psycopg.connect(
        host="127.0.0.1",
        port=port,
        user="test",
        password="test",  # noqa: S106 - fixed bootstrap LOGIN on the authenticated disposable loopback cluster
        dbname=dbname,
        sslmode="disable",
        connect_timeout=5,
        autocommit=True,
    )


def _current_physical(
    directory: PrivateEvidence,
    root: Path,
    cid: str,
    canary: str,
    image: str,
    *,
    physical_connection: psycopg.Connection[Any] | None = None,
) -> dict[str, Any]:
    current = physical_observation(
        directory, root, cid, canary, image, physical_connection=physical_connection
    )
    captured = strict_json_bytes(directory.read_reference(directory.reference("physical.json")))
    if not isinstance(captured, dict) or captured != current:
        raise StorageRefusal("physical SQL or daemon identity changed from its frozen evidence")
    return captured


def _sql_fixture(
    directory: PrivateEvidence, root: Path, cid: str, canary: str, image: str, executable: Reference
) -> tuple[Fixture, Reference]:
    physical = _current_physical(directory, root, cid, canary, image)
    port = physical["port"]
    with _connect(port) as conn:
        role = conn.execute(
            "SELECT oid FROM pg_catalog.pg_roles WHERE rolname=session_user AND session_user='test'"
        ).fetchone()
        if role is None:
            raise StorageRefusal("bootstrap role test is absent")
        bootstrap = _database(conn, "postgres")
        template = _database(conn, "per281_runtime_template_" + canary[:12])
    source = directory.reference("source-before.sha256")
    inputs = directory.reference("inputs.sha256")
    policy = _archive_file(
        directory, root / "contracts/national_storage_qualification_v6.json", "policy.json"
    )
    ack = os.environ["BABYLON_POSTGRES_DISPOSABLE_ACK"]
    if ack != "I_UNDERSTAND_THIS_DISPOSABLE_RUNTIME_DROPS_ITS_SCRATCH_DATABASES_AND_ROLES":
        raise StorageRefusal("bootstrap disposable acknowledgement differs")
    fixture = Fixture(
        tag="sql-fixture-v1",
        focus="organizer_allocation_atomic",
        test=TEST_NAME,
        checkout=str(root),
        run=str(directory.path.parent),
        evidence=str(directory.path),
        source_head=released_head(directory, root),
        source=source,
        inputs=inputs,
        policy=policy,
        physical=directory.reference("physical.json"),
        executable=executable,
        host="127.0.0.1",
        host_port=port,
        container_port=5432,
        canary=canary,
        ack="I_UNDERSTAND_THIS_DISPOSABLE_RUNTIME_DROPS_ITS_SCRATCH_DATABASES_AND_ROLES",
        data_directory=PGDATA,
        cluster=physical["cluster"],
        login="test",
        role_oid=role[0],
        bootstrap=bootstrap,
        template=template,
        campaign=str(uuid4()),
        preset="national-world",
        session="national-independent-aid",
        seed=319,
    )
    return fixture, directory.publish_json("sql-fixture-v1.json", fixture.model_dump())


def _sql_terminal(
    fixture: Fixture, owner: SQLOwner, directory: PrivateEvidence, seal: InTestSeal
) -> None:
    expected = directory.read_reference(seal.terminal_identity)
    with _connect(fixture.host_port, owner.clone.name) as conn:
        with conn.transaction():
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            if _database(conn, owner.clone.name) != owner.clone:
                raise StorageRefusal("terminal clone OID/owner differs")
            row = conn.execute(
                """
                SELECT campaign_id::text,preset_id,encode(content_sha256,'hex'),encode(foundation_sha256,'hex'),
                       encode(graph_foundation_sha256,'hex') FROM public.v_observer_material_foundation_v1
                WHERE campaign_id=%s::uuid
            """,
                (owner.campaign,),
            ).fetchone()
            if row != (
                owner.campaign,
                owner.preset,
                owner.content_sha256,
                owner.foundation_sha256,
                owner.graph_foundation_sha256,
            ):
                raise StorageRefusal(
                    "terminal SQL campaign, content or foundations differ from its sealed owner"
                )
            markers = conn.execute(
                """
                SELECT t.resolve_tick,m.identity_bytes FROM babylon_state.tick_commit t
                JOIN babylon_state.material_tick_v3 m USING(campaign_id,resolve_tick)
                WHERE t.campaign_id=%s::uuid ORDER BY t.resolve_tick
            """,
                (owner.campaign,),
            ).fetchall()
            if [row[0] for row in markers] != [1, 2, 3] or bytes(markers[-1][1]) != expected:
                raise StorageRefusal(
                    "sealed P3 identity differs from the contiguous committed SQL terminal"
                )


def _zero_sessions(conn: psycopg.Connection[Any]) -> None:
    count = conn.execute("""
        SELECT count(*) FROM pg_catalog.pg_stat_activity WHERE backend_type='client backend'
        AND pid<>pg_backend_pid()
    """).fetchone()
    if count != (0,):
        raise StorageRefusal("an additional client is connected to the disposable cluster")


def run_sql_witness(
    directory: PrivateEvidence, root: Path, cid: str, canary: str, image: str
) -> None:
    source_unchanged(root, directory.path)
    executable = _build_test(directory, root)
    fixture, fixture_ref = _sql_fixture(directory, root, cid, canary, image, executable)
    directory.verify(executable)
    source_unchanged(root, directory.path)
    _current_physical(directory, root, cid, canary, image)
    with _new_stream(directory, "ignored-test.transcript") as transcript:
        with subprocess.Popen(
            [
                str(directory.path / executable.path),
                TEST_NAME,
                "--exact",
                "--ignored",
                "--test-threads=1",
            ],
            cwd=root / "rust",
            env={
                **os.environ,
                "BABYLON_SQL_FIXTURE_FILE": str(directory.path / fixture_ref.path),
                "BABYLON_SQL_FIXTURE_SHA256": fixture_ref.sha256,
            },
            stdout=transcript,
            stderr=subprocess.STDOUT,
        ) as process:
            pid = process.pid
            status = process.wait()
        transcript.flush()
        os.fsync(transcript.fileno())
    transcript_ref = directory.reference("ignored-test.transcript")
    verify_transcript(directory.read_reference(transcript_ref, maximum=64 * 1024 * 1024), status)
    owner, in_test_ref, seal = admitted_sql_evidence(directory, fixture_ref, pid)
    _current_physical(directory, root, cid, canary, image)
    _sql_terminal(fixture, owner, directory, seal)
    outer = directory.publish_json(
        "outer-seal-v1.json",
        {
            "tag": "sql-outer-seal-v1",
            "fixture": fixture_ref.model_dump(),
            "owner": directory.reference("sql-owner-v1.json").model_dump(),
            "in_test_seal": in_test_ref.model_dump(),
            "transcript": transcript_ref.model_dump(),
            "executable_sha256": executable.sha256,
            "test": TEST_NAME,
            "exit_code": 0,
            "passed": 1,
        },
    )
    directory.verify(outer)
    source_unchanged(root, directory.path)
    _current_physical(directory, root, cid, canary, image)
    with _connect(fixture.host_port) as conn:
        if (
            _database(conn, owner.clone.name) != owner.clone
            or _database(conn, fixture.template.name) != fixture.template
        ):
            raise StorageRefusal("clone or template changed after SQL transcript sealing")
        _zero_sessions(conn)
        # Disallow new connections, then prove zero again. Never eject a client.
        conn.execute(
            sql.SQL("ALTER DATABASE {} ALLOW_CONNECTIONS false").format(
                sql.Identifier(owner.clone.name)
            )
        )
        _zero_sessions(conn)
        if _database(conn, owner.clone.name) != owner.clone:
            raise StorageRefusal("SQL clone identity changed immediately before exact removal")
        conn.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(owner.clone.name)))
        _zero_sessions(conn)
    _current_physical(directory, root, cid, canary, image)
    stop_checked(directory, cid)
    remove_stopped(directory, root, cid, canary, image)


def shutdown_events(data: bytes, since: datetime, finished: datetime) -> list[tuple[datetime, str]]:
    events = []
    for line in data.decode("utf-8", "strict").splitlines():
        match = re.fullmatch(
            r"(\S+) .*?\[1\]\s+LOG:\s+(received fast shutdown request|database system is shut down)",
            line,
        )
        if match:
            stamp = datetime.fromisoformat(match[1])
            if stamp.tzinfo is None or not since <= stamp <= finished:
                raise StorageRefusal(
                    "PostgreSQL shutdown log occurs outside the actual stop interval"
                )
            events.append((stamp, match[2]))
    if [entry[1] for entry in events] != [
        "received fast shutdown request",
        "database system is shut down",
    ] or events[1][0] < events[0][0]:
        raise StorageRefusal(
            "fenced shutdown lacks ordered fresh PostgreSQL PID 1 fast and clean log records"
        )
    return events


def _fenced_stop(directory: PrivateEvidence, cid: str, image: str) -> None:
    """A verified fast shutdown keeps the caller's ordinary connection slots occupied."""
    from datetime import UTC, datetime

    run = directory.path.parent
    owned_native_path(directory.path)
    physical = strict_json_bytes(directory.read_reference(directory.reference("physical.json")))
    if (
        not isinstance(physical, dict)
        or physical.get("container") != cid
        or physical["image"]["id"] != image
        or re.fullmatch("[0-9a-f]{64}", cid) is None
        or re.fullmatch("sha256:[0-9a-f]{64}", image) is None
    ):
        raise StorageRefusal("fenced shutdown differs from the admitted image or container")
    with pinned_ancestry(run) as pins:
        creation = _media_creation(directory, pins)
        before = _one_docker("container", cid)
        actual_image = _one_docker("image", image)
        bind = container_mounts(before, MEDIA_CHECKOUT, run, physical["label"], cid, image)
        state = before["State"]
        if (
            actual_image["Id"] != image
            or creation["image"]["id"] != image
            or before["Id"] != cid
            or before["Image"] != image
            or before["Config"].get("StopSignal") != "SIGINT"
            or actual_image["Config"].get("StopSignal") != "SIGINT"
            or state["Status"] != "running"
            or state["Running"] is not True
            or state["Pid"] != physical["pid"]
            or bind != {"mounts": physical["mounts"], "port_request": physical["port_request"]}
            or _host_identity(run / "pgdata") != physical["host"]
        ):
            raise StorageRefusal(
                "fenced shutdown needs the exact running bind and image with configured SIGINT"
            )
        uid, gid = physical["server_uid"], physical["server_gid"]
        inside = ["docker", "exec", "--user", f"{uid}:{gid}", cid]
        status = exact_output([*inside, "cat", "/proc/1/status"])
        executable = exact_output([*inside, "readlink", "/proc/1/exe"])
        postgres = exact_output([*inside, "which", "postgres"])
        if (
            _postgres_pid1_credentials(status) != (uid, gid)
            or executable != postgres
            or not Path(postgres).is_absolute()
            or Path(postgres).name != "postgres"
        ):
            raise StorageRefusal("fenced shutdown requires the actual admitted PostgreSQL PID 1")
        since = datetime.now(UTC)
        attempt = directory.publish_json(
            "native-fenced-stop-attempt-v1.json",
            {
                "container": cid,
                "image": image,
                "host_pid": state["Pid"],
                "container_pid": 1,
                "executable": executable,
                "uid": uid,
                "gid": gid,
                "stop_signal": before["Config"]["StopSignal"],
                "image_stop_signal": actual_image["Config"]["StopSignal"],
                "since": since.isoformat(),
                "bind": bind,
                "host": physical["host"],
            },
        )
        if exact_output(["docker", "stop", "--timeout", "-1", cid], timeout=180) != cid:
            raise StorageRefusal("fenced shutdown was not acknowledged by the selected container")
        after = _one_docker("container", cid)
        final = after["State"]
        if (
            after["Id"] != cid
            or after["Image"] != image
            or final["Status"] != "exited"
            or final["Running"] is not False
            or final["ExitCode"] != 0
            or final["OOMKilled"] is not False
            or final["Pid"] != 0
            or container_mounts(after, MEDIA_CHECKOUT, run, physical["label"], cid, image) != bind
            or _host_identity(run / "pgdata") != physical["host"]
        ):
            raise StorageRefusal("fenced shutdown changed the bind or did not exit cleanly")
        finished = datetime.fromisoformat(final["FinishedAt"])
        logs = subprocess.run(
            ["docker", "logs", "--timestamps", "--since", since.isoformat(), cid],
            capture_output=True,
            timeout=15,
            check=True,
        )
        data = logs.stdout + logs.stderr
        raw = directory.publish("clean-shutdown.log", data)
        events = shutdown_events(data, since, finished)
        directory.publish_json(
            "native-fenced-stop-v1.json",
            {
                "attempt": attempt.model_dump(),
                "log": raw.model_dump(),
                "fast": events[0][0].isoformat(),
                "clean": events[1][0].isoformat(),
                "finished": finished.isoformat(),
                "container": cid,
                "image": image,
                "host": physical["host"],
                "exit_code": final["ExitCode"],
                "oom_killed": final["OOMKilled"],
            },
        )


def stop_checked(directory: PrivateEvidence, cid: str, *, fenced_image: str | None = None) -> None:
    from datetime import UTC, datetime

    if fenced_image is not None:
        _fenced_stop(directory, cid, fenced_image)
        return

    since = datetime.now(UTC).isoformat()
    if exact_output(["docker", "stop", "--timeout", "60", cid], timeout=75) != cid:
        raise StorageRefusal("Docker did not stop the selected full container ID")
    state = _one_docker("container", cid)["State"]
    logs = subprocess.run(
        ["docker", "logs", "--since", since, cid], capture_output=True, timeout=15, check=True
    )
    directory.publish("clean-shutdown.log", logs.stdout + logs.stderr)
    if (
        state["Status"] != "exited"
        or state["ExitCode"] != 0
        or state["OOMKilled"] is not False
        or b"database system is shut down" not in logs.stdout + logs.stderr
    ):
        raise StorageRefusal("container lacks a verified clean shutdown; preserve it")


def remove_stopped(
    directory: PrivateEvidence, root: Path, cid: str, canary: str, image: str
) -> None:
    with pinned_ancestry(directory.path.parent) as pins:
        _media_creation(directory, pins)
        record = _one_docker("container", cid)
        container_mounts(record, root, directory.path.parent, canary, cid, image)
        if (
            record["State"]["Status"] != "exited"
            or record["State"]["ExitCode"] != 0
            or record["State"]["OOMKilled"] is not False
        ):
            raise StorageRefusal(
                "only the exact cleanly stopped task-owned container can be removed"
            )
        before = _host_identity(directory.path.parent / "pgdata")
        if exact_output(["docker", "rm", cid]) != cid:
            raise StorageRefusal("exact stopped container removal was not acknowledged")
        ids = exact_output(
            ["docker", "container", "ls", "--all", "--no-trunc", "--format", "{{.ID}}"]
        ).splitlines()
        if cid in ids or _host_identity(directory.path.parent / "pgdata") != before:
            raise StorageRefusal("container absence or retained PGDATA inode could not be verified")
        directory.publish_json(
            "retired-container.json", {"container": cid, "retained_pgdata": before}
        )


class HostContext(Record):
    tag: Literal["wayne-host-process-context-v2"]
    mount_namespace: str
    init_start_ticks: int
    init_comm: Literal["systemd"]
    boot_id: str
    pid_namespace: str
    proc_mount_id: int
    operator_uid: int


def host_proc_mount(mountinfo: str) -> tuple[list[str], list[str]]:
    proc_mount = []
    for line in mountinfo.splitlines():
        before, after = line.split(" - ", 1)
        fields = before.split()
        mountpoint = fields[4]
        if (
            re.match(r"/proc/(?:[0-9]+|self|thread-self)(?:/|$)", mountpoint)
            or mountpoint != "/proc"
            and Path("/proc/sys/kernel/random/boot_id").is_relative_to(mountpoint)
            and mountpoint.startswith("/proc/")
        ):
            raise StorageRefusal("proc submount obscures a process or host identity")
        if mountpoint == "/proc":
            proc_mount.append((fields, after.split()))
    if len(proc_mount) != 1:
        raise StorageRefusal("host /proc mount is not unique")
    return proc_mount[0]


def actual_host_context() -> HostContext:
    """Authenticate the external actual-host observation before enumerating candidates."""
    from tools.devtools.national_game_memory import parse_start_time

    parent = PrivateEvidence(RUN_PARENT)
    ref = parent.reference("host-process-context.json")
    if ref.sha256 != os.environ.get("BABYLON_WAYNE_HOST_CONTEXT_SHA256"):
        raise StorageRefusal("host view lacks the externally released context digest")
    witness = read_typed(parent, ref, HostContext)
    fields, detail = host_proc_mount(Path("/proc/self/mountinfo").read_text())
    if (
        detail[0] != "proc"
        or fields[3] != "/"
        or int(fields[0]) != witness.proc_mount_id
        or any(
            option.startswith("hidepid=") and option not in ("hidepid=0", "hidepid=off")
            for option in fields[5].split(",") + detail[2].split(",")
        )
        or "subset=pid" in fields[5].split(",") + detail[2].split(",")
        or os.readlink("/proc/self/ns/mnt") != witness.mount_namespace
        or Path("/proc/1").stat().st_uid != 0
        or Path("/proc/1/comm").read_text().strip() != witness.init_comm
        or parse_start_time(Path("/proc/1/stat").read_bytes(), 1) != witness.init_start_ticks
        or os.geteuid() != witness.operator_uid
        or os.readlink("/proc/self/ns/pid") != witness.pid_namespace
        or Path("/proc/sys/kernel/random/boot_id").read_text().strip() != witness.boot_id
    ):
        raise StorageRefusal("this process table does not prove absence on the released host")
    for candidate in Path("/proc").iterdir():
        if not candidate.name.isdecimal():
            continue
        try:
            name = (candidate / "comm").read_text().strip()
            if name not in {"babylon-runtime", "babylon-client", "babylon-material"[:15]}:
                continue
            pid = int(candidate.name)
            start = parse_start_time((candidate / "stat").read_bytes(), pid)
            exe = os.readlink(candidate / "exe")
            uid = candidate.stat().st_uid
            if parse_start_time((candidate / "stat").read_bytes(), pid) != start:
                raise StorageRefusal("candidate PID changed while verifying the host process table")
            raise StorageRefusal(
                f"active Babylon process pid={pid} start={start} uid={uid} exe={exe}"
            )
        except FileNotFoundError:
            if candidate.exists():
                raise StorageRefusal(
                    "candidate process executable could not be identified"
                ) from None
    return witness


def process_guard(directory: PrivateEvidence) -> None:
    if (
        read_typed(directory, directory.reference("host-native-admission.json"), HostContext)
        != actual_host_context()
    ):
        raise StorageRefusal("native admission host context changed")


def native_roles(
    port: int, canary: str, *, physical_connection: psycopg.Connection[Any] | None = None
) -> dict[str, int]:
    names = ["national_" + role + "_" + canary[:12] for role in ("writer", "reader", "observer")]
    with physical_session(port, physical_connection) as connection:
        rows = connection.execute(
            "SELECT rolname,oid FROM pg_catalog.pg_roles WHERE rolname=ANY(%s)", (names,)
        ).fetchall()
    values = dict(rows)
    if (
        set(values) != set(names)
        or len(set(values.values())) != 3
        or any(type(oid) is not int or oid <= 0 for oid in values.values())
    ):
        raise StorageRefusal("native role OID roster is incomplete")
    return values


def owner_lines(
    directory: PrivateEvidence,
    root: Path,
    canary: str,
    cid: str,
    image: str,
    database_oid: str,
    *,
    physical_connection: psycopg.Connection[Any] | None = None,
) -> str:
    if re.fullmatch("[1-9][0-9]*", database_oid) is None:
        raise StorageRefusal("native owner requires a complete database OID")
    physical = _current_physical(
        directory, root, cid, canary, image, physical_connection=physical_connection
    )
    expected_roles = strict_json_bytes(
        directory.read_reference(directory.reference("native-role-oids.json"))
    )
    if expected_roles != native_roles(
        physical["port"], canary, physical_connection=physical_connection
    ):
        raise StorageRefusal("native role OID changed after admission")
    host = physical["host"]
    creator = physical["creator"]
    run = directory.path.parent
    profile, _mode = owned_native_path(directory.path)
    fields = [
        "national-storage-runner-media-v2",
        str(root),
        canary,
        physical["name"],
        cid,
        str(run / "pgdata"),
        image,
        "national_" + canary[:12],
        "national_writer_" + canary[:12],
        database_oid,
        str(directory.path),
        profile,
        physical["daemon"],
        str(os.makedev(host["major"], host["minor"])),
        str(host["inode"]),
        str(creator["uid"]),
        str(creator["gid"]),
        str(host["uid"]),
        str(host["gid"]),
        str(physical["port"]),
        physical["cluster"],
    ]
    if len(fields) != 21 or any(not field or "\n" in field for field in fields):
        raise StorageRefusal("media owner contains an empty or ambiguous identity")
    return "\n".join(fields)


def held_native_lock(root: Path) -> Path:
    common = Path(
        exact_output(
            ["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-common-dir"]
        )
    )
    control = common / "babylon-national-storage"
    path = control / "runner.lock"
    if control.resolve(strict=True) != control or path.is_symlink():
        raise StorageRefusal("common native lock path is redirected")
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
        raise StorageRefusal("common native lock is not an owned regular file")
    current = os.getppid()
    ancestors = set()
    while current > 1 and current not in ancestors:
        ancestors.add(current)
        status = Path(f"/proc/{current}/status").read_text()
        parent = re.search(r"^PPid:\s+(\d+)$", status, re.MULTILINE)
        if not parent:
            raise StorageRefusal("could not identify lock ancestor")
        current = int(parent[1])
    for line in Path("/proc/locks").read_text().splitlines():
        columns = line.split()
        if (
            len(columns) != 8
            or columns[1:4] != ["FLOCK", "ADVISORY", "WRITE"]
            or columns[6:] != ["0", "EOF"]
        ):
            continue
        pid = int(columns[4])
        device = columns[5].split(":")
        if (
            len(device) == 3
            and pid in ancestors
            and (int(device[0], 16), int(device[1], 16), int(device[2]))
            == (os.major(info.st_dev), os.minor(info.st_dev), info.st_ino)
            and Path(f"/proc/{pid}/comm").read_text().strip() == "flock"
        ):
            return control
    raise StorageRefusal("no ancestor holds the exclusive common native runner lock")


def source_unchanged(root: Path, evidence: Path) -> None:
    head = released_head(PrivateEvidence(evidence), root)
    expected = (evidence / "source-head").read_text().strip()
    if head != expected or exact_output(["git", "-C", str(root), "status", "--porcelain"]):
        raise StorageRefusal("released checkout changed after admission")
    subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; national_verify_source_capture',
            "wayne-verify",
            str(root / "tools/postgres_national_lifecycle.sh"),
        ],
        cwd=root,
        env={
            **os.environ,
            "REPO_ROOT": str(root),
            "BABYLON_STORAGE_REPORT_DIRECTORY": str(evidence),
        },
        capture_output=True,
        check=True,
        timeout=120,
    )


def reauthenticate_native_owner(
    root: Path,
    evidence: Path,
    owner: tuple[str, ...],
    *,
    physical_connection: psycopg.Connection[Any] | None = None,
) -> None:
    if (
        len(owner) != 21
        or owner[0] != "national-storage-runner-media-v2"
        or owner[1] != str(root)
        or owner[10] != str(evidence)
        or owner[11] not in ("smoke-01", "walk-01", "ordinary-01")
    ):
        raise StorageRefusal("native backup needs its complete current media owner")
    profile_run(owner[11], "national_storage", "2" if owner[11] == "smoke-01" else "10", evidence)
    directory = PrivateEvidence(evidence)
    control = held_native_lock(root)
    expected = ("\n".join(owner) + "\n").encode()
    live = PrivateEvidence(control)
    if (
        live.read_reference(live.reference("active")) != expected
        or directory.read_reference(directory.reference("ownership")) != expected
        or owner_lines(
            directory,
            root,
            owner[2],
            owner[4],
            owner[6],
            owner[9],
            physical_connection=physical_connection,
        )
        != "\n".join(owner)
    ):
        raise StorageRefusal(
            "active lease, frozen native owner or actual physical ownership differs"
        )
    process_guard(directory)
    source_unchanged(root, evidence)
    roster = strict_json_bytes(
        directory.read_reference(directory.reference("normal-binaries.json"))
    )
    if not isinstance(roster, dict) or set(roster) != {
        "babylon-runtime",
        "babylon-client",
        "babylon-material-audit",
    }:
        raise StorageRefusal("release binary roster is incomplete")
    for name, entry in roster.items():
        ref = Reference.model_validate(entry)
        directory.verify(ref)
        with (root / "rust/target/debug" / name).open("rb") as binary:
            if _receipt(binary, ref.path) != ref:
                raise StorageRefusal("archived and installed native binary differ")


class OrdinaryRetention(Record):
    tag: Literal["ordinary-prefix-retained-v1"] = "ordinary-prefix-retained-v1"
    scope: Literal["ordinary_prefix_only_not_qualification_or_backup"] = (
        "ordinary_prefix_only_not_qualification_or_backup"
    )
    measurement_status: Literal["completed", "incomplete"]
    measurement_exit_status: Annotated[int, Field(ge=0, le=255)]
    campaign: str
    container: Annotated[str, Field(pattern="^[0-9a-f]{64}$")]
    image: Annotated[str, Field(pattern="^sha256:[0-9a-f]{64}$")]
    pgdata: str
    host: dict[str, int]
    campaign_connections_allowed: Literal[False] = False
    owner: Reference
    shutdown: Reference
    evidence: tuple[Reference, ...]
    raw: tuple[Reference, ...]


def _ordinary_stopped(
    directory: PrivateEvidence, root: Path, owner: tuple[str, ...], physical: dict[str, Any]
) -> None:
    current = _one_docker("container", owner[4])
    state = current["State"]
    if (
        current["Id"] != owner[4]
        or current["Image"] != owner[6]
        or state["Status"] != "exited"
        or state["Running"] is not False
        or state["ExitCode"] != 0
        or state["OOMKilled"] is not False
        or state["Pid"] != 0
        or container_mounts(current, root, directory.path.parent, owner[2], owner[4], owner[6])
        != {"mounts": physical["mounts"], "port_request": physical["port_request"]}
        or _host_identity(directory.path.parent / "pgdata") != physical["host"]
    ):
        raise StorageRefusal(
            "ordinary preservation requires the exact still-stopped container and primary"
        )


def retain_ordinary(root: Path, evidence: Path, cid: str, exit_status: int) -> None:
    """Preserve an ordinary fixture after exact clean stop; never remove or qualify it."""
    from tools.devtools.national_native_runner import OrdinaryWarmEvidence

    if type(exit_status) is not int or not 0 <= exit_status <= 255:
        raise StorageRefusal(
            "ordinary preservation requires the actual bounded process exit status"
        )
    profile_run("ordinary-01", "national_storage", "10", evidence)
    directory = PrivateEvidence(evidence)
    owner_ref = directory.reference("ownership")
    owner_bytes = directory.read_reference(owner_ref, 4096)
    owner = tuple(owner_bytes.decode().splitlines())
    if len(owner) != 21 or owner[11] != "ordinary-01" or owner[4] != cid:
        raise StorageRefusal("ordinary preservation requires its exact independent fixture owner")
    campaign = directory.read_reference(directory.reference("campaign"), 128).decode().strip()
    if str(UUID(campaign)) != campaign or UUID(campaign).int == 0:
        raise StorageRefusal("ordinary preservation lacks its canonical actual campaign")
    physical = strict_json_bytes(directory.read_reference(directory.reference("physical.json")))
    if not isinstance(physical, dict) or physical.get("container") != cid:
        raise StorageRefusal("ordinary preservation physical record differs from its owner")
    report_ref = None
    measurement: Literal["completed", "incomplete"] = "incomplete"
    if os.path.lexists(evidence / "ordinary-warm-prefix.json"):
        report_ref = directory.reference("ordinary-warm-prefix.json")
        report = OrdinaryWarmEvidence.model_validate(
            strict_json_bytes(directory.read_reference(report_ref, 32 * 1024 * 1024))
        )
        if report.status == "completed" and exit_status == 0:
            if (
                tuple(sample.period for sample in report.samples) != (1, 2, 3)
                or any(sample.usable_elapsed_ns > 10_000_000_000 for sample in report.samples)
                or any(sample.ready.state.campaign_id != campaign for sample in report.samples)
                or not os.path.lexists(evidence / "ordinary-terminal.json")
            ):
                raise StorageRefusal(
                    "completed ordinary evidence lacks its exact three-close terminal"
                )
            measurement = "completed"
    names = (
        "campaign",
        "source-head",
        "source-before.sha256",
        "inputs.sha256",
        "physical.json",
        "normal-binaries.json",
        "native-role-oids.json",
        "host-native-admission.json",
    )
    references = [directory.reference(name) for name in names]
    references.extend(
        directory.reference(name)
        for name in (
            "ordinary-warm-prefix.json",
            "ordinary-terminal.json",
            "native-controls.json",
            "native-run-incomplete.json",
            "verification-diagnostics.json",
            "processes-ordinary-prefix.json",
        )
        if os.path.lexists(evidence / name)
    )
    raw = PrivateEvidence(evidence.parent / "raw")
    pixels = tuple(raw.reference(path.name) for path in sorted(raw.path.iterdir()))
    control = held_native_lock(root)
    lease = control / "active"
    lease_identity = lease.lstat()
    fenced = False
    with physical_session(physical["port"], None) as connection:
        reauthenticate_native_owner(root, evidence, owner, physical_connection=connection)
        _zero_sessions(connection)
        allowed = connection.execute(
            "SELECT datallowconn FROM pg_catalog.pg_database WHERE datname=%s AND oid=%s::oid",
            (owner[7], owner[9]),
        ).fetchone()
        if allowed != (True,):
            raise StorageRefusal("ordinary campaign connection flag differs before preservation")
        try:
            connection.execute(
                sql.SQL("ALTER DATABASE {} ALLOW_CONNECTIONS false").format(
                    sql.Identifier(owner[7])
                )
            )
            fenced = True
            directory.publish_json(
                "ordinary-stop-attempt.json",
                {
                    "measurement_status": measurement,
                    "measurement_exit_status": exit_status,
                    "owner": owner_ref.model_dump(),
                    "campaign": campaign,
                    "campaign_connections_allowed": False,
                    "ordinary": report_ref.model_dump() if report_ref else None,
                },
            )
            _zero_sessions(connection)
            stop_checked(directory, cid, fenced_image=owner[6])
        except BaseException as failure:
            if fenced:
                try:
                    current = _one_docker("container", cid)
                    if (
                        current["Id"] == cid
                        and current["Image"] == owner[6]
                        and current["State"]["Status"] == "running"
                        and current["State"]["Running"] is True
                    ):
                        connection.execute(
                            sql.SQL("ALTER DATABASE {} ALLOW_CONNECTIONS true").format(
                                sql.Identifier(owner[7])
                            )
                        )
                        directory.publish_json(
                            "ordinary-fence-restored.json", {"campaign_connections_allowed": True}
                        )
                except BaseException as restoration:
                    raise BaseExceptionGroup(
                        "ordinary stop and running-flag restoration failed", [failure, restoration]
                    ) from None
            raise
    process_guard(directory)
    source_unchanged(root, evidence)
    shutdown = directory.reference("native-fenced-stop-v1.json")
    for reference in references:
        directory.verify(reference)
    for reference in pixels:
        raw.verify(reference)
    directory.verify(owner_ref)
    _ordinary_stopped(directory, root, owner, physical)
    current_lease = lease.lstat()
    if (
        (current_lease.st_dev, current_lease.st_ino)
        != (lease_identity.st_dev, lease_identity.st_ino)
        or private_owner_bytes(control) != owner_bytes
        or directory.read_reference(owner_ref, 4096) != owner_bytes
        or _host_identity(evidence.parent / "pgdata") != physical["host"]
    ):
        raise StorageRefusal("ordinary stopped fixture or matching lease changed before release")
    retained = OrdinaryRetention(
        measurement_status=measurement,
        measurement_exit_status=exit_status,
        campaign=campaign,
        container=cid,
        image=owner[6],
        pgdata=str(evidence.parent / "pgdata"),
        host=physical["host"],
        owner=owner_ref,
        shutdown=shutdown,
        evidence=tuple(references),
        raw=pixels,
    )
    receipt = directory.publish_json("ordinary-retained.json", retained.model_dump())
    directory.verify(receipt)
    _ordinary_stopped(directory, root, owner, physical)
    final_lease = lease.lstat()
    if (
        held_native_lock(root) != control
        or private_owner_bytes(control) != owner_bytes
        or (
            final_lease.st_dev,
            final_lease.st_ino,
            final_lease.st_mtime_ns,
            final_lease.st_ctime_ns,
        )
        != (
            current_lease.st_dev,
            current_lease.st_ino,
            current_lease.st_mtime_ns,
            current_lease.st_ctime_ns,
        )
    ):
        raise StorageRefusal("ordinary lease changed after stopped preservation receipt")
    lease.unlink()
    descriptor = os.open(control, DIR_FLAGS)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def private_owner_bytes(control: Path) -> bytes:
    directory = PrivateEvidence(control)
    return directory.read_reference(directory.reference("active"), 4096)


def main() -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation",
        choices=(
            "reserve",
            "released-head",
            "create",
            "physical",
            "verify",
            "owner",
            "sql",
            "pin-binaries",
            "pin-roles",
            "retain-ordinary",
        ),
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--profile", choices=tuple(PROFILES), required=True)
    parser.add_argument("--focus", required=True)
    parser.add_argument("--periods", required=True)
    parser.add_argument("--canary", required=True)
    parser.add_argument("--container")
    parser.add_argument("--database-oid")
    parser.add_argument("--exit-status", type=int)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        profile_run(args.profile, args.focus, args.periods, args.evidence)
        if args.root != MEDIA_CHECKOUT or args.root.resolve(strict=True) != args.root:
            raise StorageRefusal("unreleased checkout for national operator")
        directory = PrivateEvidence(args.evidence)
        image = os.environ["BABYLON_POSTGRES_IMAGE_ID"]
        if args.operation == "reserve":
            reserve_run(args.profile, args.focus, args.periods, args.evidence, args.root)
        elif args.operation == "released-head":
            print(released_head(directory, args.root))
        elif args.operation == "create":
            print(create_and_start(directory, args.root, args.canary, image))
        else:
            if not args.container:
                raise StorageRefusal("complete selected container ID is required")
            if args.operation == "retain-ordinary":
                if args.profile != "ordinary-01" or args.exit_status is None:
                    raise StorageRefusal(
                        "ordinary retention requires its profile and actual exit status"
                    )
                retain_ordinary(args.root, args.evidence, args.container, args.exit_status)
            elif args.operation == "physical":
                directory.publish_json(
                    "physical.json",
                    physical_observation(directory, args.root, args.container, args.canary, image),
                )
            elif args.operation == "verify":
                _current_physical(directory, args.root, args.container, args.canary, image)
            elif args.operation == "pin-roles":
                if args.profile == "sql-01":
                    raise StorageRefusal("SQL fixture cannot freeze native roles")
                physical = _current_physical(
                    directory, args.root, args.container, args.canary, image
                )
                directory.publish_json(
                    "native-role-oids.json", native_roles(physical["port"], args.canary)
                )
            elif args.operation == "pin-binaries":
                if args.profile == "sql-01":
                    raise StorageRefusal("SQL fixture cannot admit native executables")
                source_unchanged(args.root, args.evidence)
                ref, expected = _native_expectations(PrivateEvidence(RUN_PARENT), args.profile)
                creation = strict_json_bytes(
                    directory.read_reference(directory.reference("media-creation.json"))
                )
                if (
                    not isinstance(creation, dict)
                    or creation.get("native_expectations") != ref.model_dump()
                ):
                    raise StorageRefusal(
                        "released native expectations differ from initial reservation"
                    )
                roster = {}
                for name, product in expected.products().items():
                    binary = args.root / "rust/target/debug" / name
                    captured = _archive_file(directory, binary, "normal-" + name, executable=True)
                    if captured != product:
                        raise StorageRefusal(
                            f"captured normal executable differs from native release: {name}"
                        )
                    roster[name] = captured.model_dump()
                directory.publish_json("normal-binaries.json", roster)
                directory.publish(
                    "native-combined-source.sha256",
                    (directory.path / "source-before.sha256").read_bytes(),
                )
                directory.publish(
                    "native-executables.sha256",
                    "".join(
                        entry["sha256"] + "  " + str(args.root / "rust/target/debug" / name) + "\n"
                        for name, entry in roster.items()
                        if name in ("babylon-runtime", "babylon-client")
                    ).encode(),
                )
            elif args.operation == "owner":
                print(
                    owner_lines(
                        directory,
                        args.root,
                        args.canary,
                        args.container,
                        image,
                        args.database_oid or "",
                    )
                )
            elif args.operation == "sql":
                if args.profile != "sql-01":
                    raise StorageRefusal(
                        "ignored allocation SQL requires its independent SQL fixture"
                    )
                run_sql_witness(directory, args.root, args.container, args.canary, image)
    except (
        StorageRefusal,
        OSError,
        psycopg.Error,
        KeyError,
        ValueError,
        subprocess.SubprocessError,
        BaseExceptionGroup,
    ) as error:
        # SQL and Docker exception representations may embed connection secrets.
        reason = str(error) if isinstance(error, StorageRefusal) else type(error).__name__
        print("Wayne media qualification refused: " + reason, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
