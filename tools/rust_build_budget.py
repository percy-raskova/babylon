"""Add current-checkout allocations and native launch pins to the manager's JSON status."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path

EXECUTABLES = ("babylon-runtime", "babylon-client")
MANIFEST = "native-executables.sha256"
TARGET = Path("rust/target")
MAX_RECEIPT_BYTES = 1024 * 1024


def mount_id(fd: int) -> str:
    for line in Path(f"/proc/self/fdinfo/{fd}").read_text().splitlines():
        if line.startswith("mnt_id:"):
            return line
    raise ValueError("mount identity unavailable")


@contextmanager
def open_beneath(parent: int, path: Path, *, directory: bool) -> Iterator[int]:
    """Open from an anchored directory, refusing symlinks and nested mounts."""
    expected_mount = mount_id(parent)
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    with ExitStack() as stack:
        for index, component in enumerate(path.parts):
            if component in ("/", ".."):
                raise ValueError("path outside checkout")
            is_dir = directory or index < len(path.parts) - 1
            parent = os.open(component, flags | (os.O_DIRECTORY if is_dir else 0), dir_fd=parent)
            stack.callback(os.close, parent)
            if mount_id(parent) != expected_mount:
                raise ValueError("nested mount")
        yield parent


def sha256_digest(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch("[a-f0-9]{64}", value) is None:
        raise ValueError("invalid SHA-256 digest")
    return value


def receipt_pins(fd: int, name: str, checkout: Path) -> dict[str, str]:
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_RECEIPT_BYTES:
        raise ValueError("unsafe receipt")
    with os.fdopen(fd, "rb", closefd=False) as stream:
        data = stream.read(MAX_RECEIPT_BYTES + 1)
    if len(data) != info.st_size or os.fstat(fd).st_ctime_ns != info.st_ctime_ns:
        raise ValueError("receipt changed while reading")
    if name == MANIFEST:
        # The same exact two-path SHA-256 format admitted by postgres_national_lifecycle.sh.
        paths = {str(checkout / TARGET / "debug" / exe): exe for exe in EXECUTABLES}
        pins = {}
        for line in data.decode().splitlines():
            digest, separator, path = line.partition("  ")
            if not separator or path not in paths or paths[path] in pins:
                raise ValueError("invalid executable manifest")
            pins[paths[path]] = sha256_digest(digest)
    else:
        source = json.loads(data)
        if (
            not isinstance(source, dict)
            or type(source.get("build_exit")) is not int
            or source.get("build_exit") != 0
            or source.get("build_cwd") != str(checkout / "rust")
        ):
            raise ValueError("build receipt is not for this checkout")
        pins = {
            "babylon-runtime": sha256_digest(source.get("runtime_sha256")),
            "babylon-client": sha256_digest(source.get("client_sha256")),
        }
    if set(pins) != set(EXECUTABLES):
        raise ValueError("incomplete pins")
    return pins


def discover(checkout_fd: int, checkout: Path) -> tuple[dict[str, set[str]], int, int]:
    digests: dict[str, set[str]] = {}
    receipts = invalid = 0
    try:
        with open_beneath(checkout_fd, Path("reports/test-results"), directory=True) as runs:
            for run in os.listdir(runs):
                # PostgreSQL clusters and runner internals hold private state.
                if run.endswith("-pgdata") or run in {"pgdata", "national-storage-runner"}:
                    continue
                try:
                    mode = os.stat(run, dir_fd=runs, follow_symlinks=False).st_mode
                    if stat.S_ISLNK(mode):
                        raise ValueError("cannot establish receipt directory identity")
                    if not stat.S_ISDIR(mode):
                        continue
                    with open_beneath(runs, Path(run), directory=True) as run_fd:
                        names = os.listdir(run_fd)
                        for name in names:
                            if name != MANIFEST and not re.fullmatch(
                                r"operator-native-build-[\w-]+\.json", name
                            ):
                                continue
                            receipts += 1
                            try:
                                with open_beneath(run_fd, Path(name), directory=False) as fd:
                                    pins = receipt_pins(fd, name, checkout)
                                for exe, digest in pins.items():
                                    digests.setdefault(exe, set()).add(digest)
                            except (ValueError, OSError, RecursionError):
                                invalid += 1
                except (OSError, ValueError):
                    invalid += 1
    except FileNotFoundError:
        pass
    except (OSError, ValueError):
        invalid += 1
    return digests, receipts, invalid


def inspect_file(
    checkout_fd: int, exe: str, expected: set[str]
) -> tuple[dict[str, object], tuple[int, int] | None]:
    try:
        with open_beneath(checkout_fd, TARGET / "debug", directory=True) as debug:
            with open_beneath(debug, Path(exe), directory=False) as fd:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or not info.st_mode & 0o111:
                    raise ValueError("expected a regular executable")
                with os.fdopen(fd, "rb", closefd=False) as stream:
                    actual = hashlib.file_digest(stream, "sha256").hexdigest()
                after = os.stat(exe, dir_fd=debug, follow_symlinks=False)
                if (info.st_dev, info.st_ino, info.st_ctime_ns) != (
                    after.st_dev,
                    after.st_ino,
                    after.st_ctime_ns,
                ):
                    raise ValueError("executable changed during inspection")
                match = int(actual in expected)
                return {
                    "state": "present",
                    "allocated_bytes": info.st_blocks * 512,
                    "matching_digests": match,
                    "mismatched_digests": len(expected) - match,
                }, (info.st_dev, info.st_ino)
    except FileNotFoundError:
        return {"state": "missing", "allocated_bytes": 0}, None
    except (OSError, ValueError):
        return {"state": "unverified", "allocated_bytes": None}, None


def pin_inventory(checkout_fd: int, checkout: Path) -> dict[str, object]:
    digests, receipts, invalid = discover(checkout_fd, checkout)
    files = {}
    referenced: dict[tuple[int, int], int] = {}
    matched: set[tuple[int, int]] = set()
    complete = invalid == 0
    for exe, expected in sorted(digests.items()):
        row, identity = inspect_file(checkout_fd, exe, expected)
        files[exe] = row
        size = row["allocated_bytes"]
        if identity is not None and isinstance(size, int):
            referenced[identity] = size
            if row["matching_digests"]:
                matched.add(identity)
        elif size is None:
            complete = False
    return {
        "receipts": receipts,
        "unreadable_or_invalid": invalid,
        "files": files,
        "referenced_bytes": sum(referenced.values()) if complete else None,
        "matching_bytes": sum(referenced[i] for i in matched) if complete else None,
    }


def allocated_bytes(path: str | Path, pass_fds: tuple[int, ...] = ()) -> int | None:
    measured = subprocess.run(
        ["du", "-sx", "-B1", "--", path], capture_output=True, pass_fds=pass_fds
    )  # noqa: S603, S607 -- fixed read-only operator utility
    return int(measured.stdout.split()[0]) if measured.returncode == 0 else None


def add_checkout_status(result: dict[str, object], checkout: Path, cache: Path) -> None:
    fd = os.open(checkout, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        result["pinned_files"] = pin_inventory(fd, checkout)
        try:
            with open_beneath(fd, TARGET, directory=True) as target:
                result["checkout_target_bytes"] = allocated_bytes(
                    f"/proc/self/fd/{target}/", (target,)
                )
        except FileNotFoundError:
            result["checkout_target_bytes"] = 0
        except (OSError, ValueError):
            result["checkout_target_bytes"] = None
    finally:
        os.close(fd)
    result["sccache_bytes"] = allocated_bytes(cache) if os.path.lexists(cache) else 0


if __name__ == "__main__":
    status = json.loads(sys.argv[1])
    add_checkout_status(status, Path(sys.argv[2]), Path(sys.argv[3]))
    print(json.dumps(status, indent=2))
