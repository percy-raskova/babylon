#!/usr/bin/env python3
"""Freeze the two Python-era PostgreSQL DDL sequences as Rust byte fixtures."""

from __future__ import annotations

import argparse
import os
import stat
import sys
from collections.abc import Sequence
from itertools import islice
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
FIXTURES = ROOT / "rust/crates/babylon-persistence/tests/fixtures"
SCHEMA_FIXTURE = FIXTURES / "legacy_schema_ddl_v1.bin"
MIGRATION_FIXTURE = FIXTURES / "legacy_migrations_0010_0044_v1.bin"
MAX_CHUNKS = 256
MAX_BYTES = 1_048_576
MAX_MIGRATION_DIRECTORY_ENTRIES = 256
EXPECTED_LOCK_KEY = 0xBAB1_0537


def _numbered_migrations() -> list[str]:
    """Read exactly one bounded source file for each required migration version."""
    migration_dir = SRC / "babylon/persistence/migrations"
    try:
        with os.scandir(migration_dir) as directory:
            entries = list(islice(directory, MAX_MIGRATION_DIRECTORY_ENTRIES + 1))
    except FileNotFoundError:
        entries = []
    if len(entries) > MAX_MIGRATION_DIRECTORY_ENTRIES:
        raise RuntimeError(f"migration directory: entries exceed {MAX_MIGRATION_DIRECTORY_ENTRIES}")
    chunks: list[str] = []
    framed_bytes = 0
    for version in range(10, 45):
        matches = _migration_matches(entries, version)
        if len(matches) != 1:
            raise RuntimeError(f"migration {version:04d}: expected one file, found {len(matches)}")
        source_budget = MAX_BYTES - framed_bytes - 1
        if source_budget < 0:
            raise ValueError(f"migrations-0010-0044: framed bytes exceed {MAX_BYTES}")
        chunk, chunk_bytes = _read_migration_source(
            matches[0],
            max_bytes=source_budget,
            label="migrations-0010-0044",
        )
        chunks.append(chunk)
        framed_bytes += chunk_bytes + 1
    return chunks


def _migration_matches(entries: Sequence[os.DirEntry[str]], version: int) -> list[Path]:
    """Return no more than the two source paths needed to detect duplicates."""
    prefix = f"{version:04d}_"
    matches: list[Path] = []
    for entry in islice(entries, MAX_MIGRATION_DIRECTORY_ENTRIES):
        if entry.name.startswith(prefix) and entry.name.endswith(".sql") and entry.is_file():
            matches.append(Path(entry.path))
            if len(matches) == 2:
                break
    return matches


def _read_migration_source(path: Path, *, max_bytes: int, label: str) -> tuple[str, int]:
    """Read one migration within the remaining framed-byte budget."""
    if max_bytes < 0:
        raise ValueError(f"{label}: framed bytes exceed {MAX_BYTES}")
    with path.open("rb") as source:
        raw = source.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError(f"{label}: framed bytes exceed {MAX_BYTES}")
    return raw.decode("utf-8"), len(raw)


def _frame(chunks: Sequence[str], *, label: str) -> bytes:
    if not chunks:
        raise ValueError(f"{label}: empty sequence")
    if len(chunks) > MAX_CHUNKS:
        raise ValueError(f"{label}: {len(chunks)} chunks exceeds {MAX_CHUNKS}")
    framed = bytearray()
    for index, chunk in enumerate(islice(chunks, MAX_CHUNKS)):
        if not chunk:
            raise ValueError(f"{label}: empty chunk {index}")
        remaining = MAX_BYTES - len(framed) - 1
        if len(chunk) > remaining:
            raise ValueError(f"{label}: framed bytes exceed {MAX_BYTES}")
        encoded = chunk.encode("utf-8")
        if len(encoded) > remaining:
            raise ValueError(f"{label}: framed bytes exceed {MAX_BYTES}")
        if b"\0" in encoded:
            raise ValueError(f"{label}: embedded NUL in chunk {index}")
        framed.extend(encoded)
        framed.append(0)
    return bytes(framed)


def _expected() -> tuple[bytes, bytes]:
    sys.path.insert(0, str(SRC))
    from babylon.persistence.postgres_schema import (  # noqa: PLC0415
        POSTGRES_SCHEMA_DDL,
        SCHEMA_ADVISORY_LOCK_KEY,
    )

    if SCHEMA_ADVISORY_LOCK_KEY != EXPECTED_LOCK_KEY:
        raise RuntimeError(
            "schema advisory-lock key drifted: "
            f"{SCHEMA_ADVISORY_LOCK_KEY:#x} != {EXPECTED_LOCK_KEY:#x}"
        )
    return (
        _frame(POSTGRES_SCHEMA_DDL, label="POSTGRES_SCHEMA_DDL"),
        _frame(_numbered_migrations(), label="migrations-0010-0044"),
    )


def _check(path: Path, expected: bytes) -> bool:
    try:
        with path.open("rb") as fixture:
            metadata = os.fstat(fixture.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                print(f"invalid fixture: {path} is not a regular file", file=sys.stderr)
                return False
            if metadata.st_size != len(expected):
                print(f"stale fixture: {path}", file=sys.stderr)
                return False
            actual = fixture.read(len(expected) + 1)
    except FileNotFoundError:
        print(f"missing fixture: {path}", file=sys.stderr)
        return False
    except OSError as error:
        print(f"fixture access failed: {path}: {error}", file=sys.stderr)
        return False
    if actual != expected:
        print(f"stale fixture: {path}", file=sys.stderr)
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    schema, migrations = _expected()
    if args.write:
        FIXTURES.mkdir(parents=True, exist_ok=True)
        SCHEMA_FIXTURE.write_bytes(schema)
        MIGRATION_FIXTURE.write_bytes(migrations)
        print("wrote POSTGRES_SCHEMA_DDL=112 migrations=35")
        return 0
    checks = (
        _check(SCHEMA_FIXTURE, schema),
        _check(MIGRATION_FIXTURE, migrations),
    )
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
