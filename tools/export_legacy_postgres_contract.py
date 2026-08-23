#!/usr/bin/env python3
"""Freeze the two Python-era PostgreSQL DDL sequences as Rust byte fixtures."""

from __future__ import annotations

import argparse
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
EXPECTED_LOCK_KEY = 0xBAB1_0537


def _numbered_migrations() -> list[str]:
    migration_dir = SRC / "babylon/persistence/migrations"
    chunks: list[str] = []
    for version in range(10, 45):
        matches = list(islice(migration_dir.glob(f"{version:04d}_*.sql"), 2))
        if len(matches) != 1:
            raise RuntimeError(f"migration {version:04d}: expected one file, found {len(matches)}")
        chunks.append(matches[0].read_text(encoding="utf-8"))
    return chunks


def _frame(chunks: Sequence[str], *, label: str) -> bytes:
    if not chunks:
        raise ValueError(f"{label}: empty sequence")
    if len(chunks) > MAX_CHUNKS:
        raise ValueError(f"{label}: {len(chunks)} chunks exceeds {MAX_CHUNKS}")
    framed = bytearray()
    for index, chunk in enumerate(chunks[:MAX_CHUNKS]):
        encoded = chunk.encode("utf-8")
        if not encoded:
            raise ValueError(f"{label}: empty chunk {index}")
        if b"\0" in encoded:
            raise ValueError(f"{label}: embedded NUL in chunk {index}")
        framed.extend(encoded)
        framed.append(0)
        if len(framed) > MAX_BYTES:
            raise ValueError(f"{label}: framed bytes exceed {MAX_BYTES}")
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
    if not path.is_file():
        print(f"missing fixture: {path}", file=sys.stderr)
        return False
    if path.read_bytes() != expected:
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
