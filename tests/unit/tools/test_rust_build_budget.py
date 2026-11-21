"""The operator's Cargo inventory distinguishes pinned allocations from digest matches."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

TOOL = Path(__file__).resolve().parents[3] / "tools" / "rust_build_budget.py"


def inventory(checkout: Path) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(TOOL), "{}", str(checkout), str(checkout / "cache")],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def proof(checkout: Path, content: bytes) -> tuple[Path, Path, Path, str]:
    report = checkout / "reports/test-results/fixture"
    debug = checkout / "rust/target/debug"
    report.mkdir(parents=True)
    debug.mkdir(parents=True)
    runtime = debug / "babylon-runtime"
    client = debug / "babylon-client"
    runtime.write_bytes(content)
    runtime.chmod(0o700)
    os.link(runtime, client)
    digest = hashlib.sha256(content).hexdigest()
    (report / "native-executables.sha256").write_text(f"{digest}  {runtime}\n{digest}  {client}\n")
    return report, runtime, client, digest


def test_counts_all_referenced_allocations_and_only_matches_once(tmp_path: Path) -> None:
    report, runtime, client, digest = proof(tmp_path, b"reviewed")
    (report / "operator-native-build-context.json").write_text(
        json.dumps(
            {
                "build_exit": 0,
                "build_cwd": str(tmp_path / "rust"),
                "runtime_sha256": digest,
                "client_sha256": "f" * 64,
            }
        )
    )
    result = inventory(tmp_path)
    pins = result["pinned_files"]
    size = runtime.stat().st_blocks * 512
    assert pins["referenced_bytes"] == pins["matching_bytes"] == size
    assert result["checkout_target_bytes"] >= size
    assert pins["receipts"] == 2
    assert pins["files"]["babylon-client"]["matching_digests"] == 1
    assert pins["files"]["babylon-client"]["mismatched_digests"] == 1
    client.unlink()
    client.write_bytes(b"drift")
    client.chmod(0o700)
    pins = inventory(tmp_path)["pinned_files"]
    assert pins["referenced_bytes"] == size + client.stat().st_blocks * 512
    assert pins["matching_bytes"] == size
    assert pins["files"]["babylon-client"]["mismatched_digests"] == 2
    runtime.unlink()
    pins = inventory(tmp_path)["pinned_files"]
    assert pins["files"]["babylon-runtime"]["state"] == "missing"
    assert pins["matching_bytes"] == 0


@pytest.mark.parametrize(
    "fault",
    [
        "escape",
        "file_symlink",
        "dir_symlink",
        "receipt_symlink",
        "receipt_hardlink",
        "run_symlink",
        "malformed",
        "deep_json",
    ],
)
def test_refuses_unsafe_or_incomplete_pin_evidence(tmp_path: Path, fault: str) -> None:
    checkout = tmp_path / "checkout"
    report, runtime, _, digest = proof(checkout, b"safe")
    outside = tmp_path / "private"
    outside.write_bytes(b"do not disclose")
    manifest = report / "native-executables.sha256"
    if fault == "escape":
        manifest.write_text(f"{digest}  {outside}\n")
    elif fault == "file_symlink":
        runtime.unlink()
        runtime.symlink_to(outside)
    elif fault == "dir_symlink":
        runtime.parent.rename(tmp_path / "binaries")
        runtime.parent.symlink_to(tmp_path / "binaries", target_is_directory=True)
    elif fault == "receipt_symlink":
        manifest.unlink()
        manifest.symlink_to(outside)
    elif fault == "receipt_hardlink":
        os.link(manifest, tmp_path / "other-copy")
    elif fault == "run_symlink":
        report.rename(tmp_path / "other-run")
        report.symlink_to(tmp_path / "other-run", target_is_directory=True)
    elif fault == "deep_json":
        nested = "[" * 10_000 + "0" + "]" * 10_000
        (report / "operator-native-build-context.json").write_text(nested)
    else:
        manifest.write_text("partial")
    pins = inventory(checkout)["pinned_files"]
    assert pins["referenced_bytes"] is None and pins["matching_bytes"] is None
    assert str(outside) not in json.dumps(pins)


def test_absent_receipts_report_no_claims(tmp_path: Path) -> None:
    assert inventory(tmp_path)["pinned_files"] == {
        "receipts": 0,
        "unreadable_or_invalid": 0,
        "referenced_bytes": 0,
        "matching_bytes": 0,
        "files": {},
    }
