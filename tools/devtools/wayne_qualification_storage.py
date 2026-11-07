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
from pathlib import Path
from typing import Annotated, Any, BinaryIO, Literal
from uuid import UUID, uuid4

import psycopg
from psycopg import sql
from pydantic import BaseModel, ConfigDict, Field
from tools.devtools.national_storage_qualification import strict_json_bytes

RUN_PARENT = Path("/media/user/data/worktrees/per364-wayne-solidarity-loop/qualification-01")
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


def profile_run(profile: str, focus: str, periods: str, evidence: Path) -> Path:
    if PROFILES.get(profile) != (focus, periods):
        raise StorageRefusal("Wayne media profile, focus and period count disagree")
    run = RUN_PARENT / profile
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
    def file(self, name: str) -> Iterator[BinaryIO]:
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
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) & 0o077
            ):
                raise StorageRefusal("referenced evidence must be a private owned regular file")
            yield stream

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
        return self.publish(
            name, (json.dumps(record, allow_nan=False, sort_keys=True) + "\n").encode()
        )


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
    groups = {
        (parent.st_gid if tag == 4 else who): perm & group_mask
        for tag, perm, who in rows
        if tag in {4, 8}
    }
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
    path: str
    major: int
    minor: int
    inode: int
    uid: int
    gid: int
    mode: int
    access_acl: list[list[int]]
    default_acl: list[list[int]]


def _directory_pin(fd: int, path: Path) -> DirectoryPin:
    info = os.fstat(fd)
    return DirectoryPin(
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
        if any(
            (pin.major, pin.minor) != (media.major, media.minor)
            for pin in pins
            if Path(pin.path).is_relative_to(MEDIA)
        ):
            raise StorageRefusal("unexpected nested filesystem under the media drive")
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
    profile: Literal["sql-01", "smoke-01", "walk-01"]
    source_head: str
    build_bytes: Annotated[int, Field(ge=0)]
    primary_bytes: Annotated[int, Field(gt=0)]
    evidence_bytes: Annotated[int, Field(gt=0)]
    restore_bytes: Annotated[int, Field(ge=0)]
    dump_bytes: Annotated[int, Field(ge=0)]
    archive_bytes: Annotated[int, Field(ge=0)]
    measured_basis: Annotated[str, Field(min_length=1)]


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
    _daemon_endpoint()
    _image(os.environ["BABYLON_POSTGRES_IMAGE_ID"])
    if exact_output(["git", "-C", str(root), "status", "--porcelain"]):
        raise StorageRefusal("Wayne admission requires a clean source and operator")
    head = exact_output(["git", "-C", str(root), "rev-parse", "HEAD"])
    # The released operator supplies measured capacity values before each run.
    # statvfs already accounts for all previously retained primary and evidence bytes.
    if not RUN_PARENT.is_dir():
        with pinned_ancestry(RUN_PARENT.parent):
            RUN_PARENT.mkdir(mode=0o700)
    with pinned_ancestry(RUN_PARENT) as parent_pins:
        if parent_pins[-1].uid != os.geteuid() or parent_pins[-1].mode != 0o700:
            raise StorageRefusal("Wayne run parent must be private and operator owned")
        reservations = PrivateEvidence(RUN_PARENT)
        reservation_ref = reservations.reference(f"{profile}-capacity.json")
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
            PrivateEvidence(evidence).publish_json("media-creation.json", declaration)


def _media_creation(directory: PrivateEvidence, pins: list[DirectoryPin]) -> dict[str, Any]:
    ref = directory.reference("media-creation.json")
    data = strict_json_bytes(directory.read_reference(ref))
    if not isinstance(data, dict) or data.get("ancestry") != _pin_json(pins):
        raise StorageRefusal("creator proof differs from the current media ancestry")
    if data.get("daemon") != _daemon() or data.get("image") != _image(
        os.environ["BABYLON_POSTGRES_IMAGE_ID"]
    ):
        raise StorageRefusal("creator proof differs from the current daemon/image")
    creator = data["creator"]
    current = _host_identity(directory.path.parent / "pgdata")
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
                *(["-c", "max_wal_senders=0"] if run.name in ("smoke-01", "walk-01") else []),
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


def physical_observation(
    directory: PrivateEvidence, root: Path, cid: str, canary: str, image: str
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
        process = exact_output([*inside, "cat", "/proc/1/status"])
        owner = re.search(r"^Uid:\s+[0-9]+\s+([0-9]+)\s", process, re.MULTILINE)
        group = re.search(r"^Gid:\s+[0-9]+\s+([0-9]+)\s", process, re.MULTILINE)
        if (
            not owner
            or not group
            or (int(owner[1]), int(group[1])) != (uid, gid)
            or not re.search(r"^Name:\s+postgres$", process, re.MULTILINE)
        ):
            raise StorageRefusal("actual PostgreSQL server identity differs from bound owner")
        lineage = _exec_bytes([*inside, "cat", PGDATA + "/.babylon-postgres-lineage-v1"])
        major = _exec_bytes([*inside, "cat", PGDATA + "/PG_VERSION"])
        if lineage != (LINEAGE + "\n").encode() or major != b"17\n":
            raise StorageRefusal("actual cluster version or lineage marker differs")
        native_settings: dict[str, int] = {}
        with psycopg.connect(
            host="127.0.0.1",
            port=port,
            user="test",
            password="test",  # noqa: S106 - fixed bootstrap LOGIN on the authenticated disposable loopback cluster
            dbname="template1",
            connect_timeout=5,
            sslmode="disable",
        ) as conn:
            if run.name in ("smoke-01", "walk-01"):
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
            "server_uid": uid,
            "server_gid": gid,
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


def _build_test(directory: PrivateEvidence, root: Path) -> Reference:
    log = subprocess.run(
        [
            "cargo",
            "test",
            "-p",
            "babylon-persistence",
            "--lib",
            "--locked",
            "--no-run",
            "--message-format=json-render-diagnostics",
        ],
        cwd=root / "rust",
        capture_output=True,
        timeout=900,
        check=False,
    )
    directory.publish("ignored-build.jsonl", log.stdout)
    directory.publish("ignored-build.stderr", log.stderr)
    log.check_returncode()
    candidates = []
    for line in log.stdout.splitlines():
        entry = strict_json_bytes(line)
        if (
            isinstance(entry, dict)
            and entry.get("reason") == "compiler-artifact"
            and entry["target"]["name"] == "babylon_persistence"
            and "lib" in entry["target"]["kind"]
            and entry["profile"]["test"] is True
            and entry["executable"] is not None
        ):
            candidates.append(Path(entry["executable"]))
    if len(candidates) != 1 or candidates[0].parent != root / "rust/target/debug/deps":
        raise StorageRefusal(
            "Cargo did not select one checkout-local persistence lib test executable"
        )
    archived = _archive_file(directory, candidates[0], "ignored-test", executable=True)
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
    directory: PrivateEvidence, root: Path, cid: str, canary: str, image: str
) -> dict[str, Any]:
    current = physical_observation(directory, root, cid, canary, image)
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
        source_head=exact_output(["git", "-C", str(root), "rev-parse", "HEAD"]),
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


def stop_checked(directory: PrivateEvidence, cid: str) -> None:
    from datetime import UTC, datetime

    since = datetime.now(UTC).isoformat()
    if exact_output(["docker", "stop", "--time", "60", cid], timeout=75) != cid:
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
    tag: Literal["wayne-host-process-context-v1"]
    boot_id: str
    pid_namespace: str
    proc_mount_id: int
    operator_uid: int


def process_guard(directory: PrivateEvidence, *, capture: bool = True) -> None:
    """The approved host is the only authority for negative process observations."""
    from tools.devtools.national_game_memory import parse_start_time

    parent = PrivateEvidence(RUN_PARENT)
    witness = read_typed(parent, parent.reference("host-process-context.json"), HostContext)
    proc_mount = []
    for line in Path("/proc/self/mountinfo").read_text().splitlines():
        before, after = line.split(" - ", 1)
        fields = before.split()
        if fields[4] == "/proc":
            proc_mount.append((fields, after.split()))
    if len(proc_mount) != 1:
        raise StorageRefusal("host /proc mount is not unique")
    fields, detail = proc_mount[0]
    if (
        detail[0] != "proc"
        or fields[3] != "/"
        or int(fields[0]) != witness.proc_mount_id
        or any(
            option.startswith("hidepid=") and option not in ("hidepid=0", "hidepid=off")
            for option in fields[5].split(",") + detail[2].split(",")
        )
        or os.geteuid() != witness.operator_uid
        or os.readlink("/proc/self/ns/pid") != witness.pid_namespace
        or os.readlink("/proc/1/ns/pid") != witness.pid_namespace
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
    if capture:
        directory.publish_json("host-native-admission.json", witness.model_dump())
    elif (
        read_typed(directory, directory.reference("host-native-admission.json"), HostContext)
        != witness
    ):
        raise StorageRefusal("native admission host context changed")


def owner_lines(
    directory: PrivateEvidence, root: Path, canary: str, cid: str, image: str, database_oid: str
) -> str:
    if re.fullmatch("[1-9][0-9]*", database_oid) is None:
        raise StorageRefusal("native owner requires a complete database OID")
    physical = _current_physical(directory, root, cid, canary, image)
    host = physical["host"]
    creator = physical["creator"]
    run = directory.path.parent
    if run.name not in ("smoke-01", "walk-01") or run.parent != RUN_PARENT:
        raise StorageRefusal("media owner requires the exact selected native run")
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
        run.name,
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
    head = exact_output(["git", "-C", str(root), "rev-parse", "HEAD"])
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


def reauthenticate_native_owner(root: Path, evidence: Path, owner: tuple[str, ...]) -> None:
    if (
        len(owner) != 21
        or owner[0] != "national-storage-runner-media-v2"
        or owner[1] != str(root)
        or owner[10] != str(evidence)
        or owner[11] not in ("smoke-01", "walk-01")
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
        or owner_lines(directory, root, owner[2], owner[4], owner[6], owner[9]) != "\n".join(owner)
    ):
        raise StorageRefusal(
            "active lease, frozen native owner or actual physical ownership differs"
        )
    process_guard(directory, capture=False)
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


def main() -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation",
        choices=("reserve", "create", "physical", "verify", "owner", "sql", "pin-binaries"),
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--profile", choices=tuple(PROFILES), required=True)
    parser.add_argument("--focus", required=True)
    parser.add_argument("--periods", required=True)
    parser.add_argument("--canary", required=True)
    parser.add_argument("--container")
    parser.add_argument("--database-oid")
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
            if args.profile != "sql-01":
                process_guard(directory)
        elif args.operation == "create":
            print(create_and_start(directory, args.root, args.canary, image))
        else:
            if not args.container:
                raise StorageRefusal("complete selected container ID is required")
            if args.operation == "physical":
                directory.publish_json(
                    "physical.json",
                    physical_observation(directory, args.root, args.container, args.canary, image),
                )
            elif args.operation == "verify":
                _current_physical(directory, args.root, args.container, args.canary, image)
            elif args.operation == "pin-binaries":
                if args.profile == "sql-01":
                    raise StorageRefusal("SQL fixture cannot admit native executables")
                source_unchanged(args.root, args.evidence)
                roster = {}
                for name in ("babylon-runtime", "babylon-client", "babylon-material-audit"):
                    binary = args.root / "rust/target/debug" / name
                    roster[name] = _archive_file(
                        directory, binary, "normal-" + name, executable=True
                    ).model_dump()
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
    ) as error:
        # SQL and Docker exception representations may embed connection secrets.
        reason = str(error) if isinstance(error, StorageRefusal) else type(error).__name__
        print("Wayne media qualification refused: " + reason, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
