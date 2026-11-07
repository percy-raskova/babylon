"""Synthetic admission and retention checks, without a Docker daemon or database."""

from pathlib import Path

import pytest
from tools.devtools import wayne_qualification_storage as storage


def test_three_media_profiles_require_the_exact_run_and_horizon() -> None:
    for profile, focus, periods, leaf in (
        ("sql-01", "organizer_allocation_atomic", "", "sql-01"),
        ("smoke-01", "national_storage", "2", "smoke-01"),
        ("walk-01", "national_storage", "10", "walk-01"),
    ):
        evidence = storage.RUN_PARENT / leaf / "evidence"
        assert storage.profile_run(profile, focus, periods, evidence) == evidence.parent
        with pytest.raises(storage.StorageRefusal):
            storage.profile_run(profile, focus, periods, evidence / "..")
        with pytest.raises(storage.StorageRefusal):
            storage.profile_run(profile, focus, "9", evidence)


def test_test_result_binds_the_ignored_case_and_exact_pass_count() -> None:
    result = (
        f"\nrunning 1 test\ntest {storage.TEST_NAME} ... ok\n\n"
        "test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 47 filtered out; "
        "finished in 2.53s\n"
    ).encode()
    storage.verify_transcript(result, 0)
    for changed in [
        result.replace(b"1 passed", b"0 passed"),
        result.replace(b"0 ignored", b"1 ignored"),
        result.replace(b"... ok", b"... ignored"),
        result.replace(storage.TEST_NAME.encode(), b"some_other_test"),
        result + result,
    ]:
        with pytest.raises(storage.StorageRefusal):
            storage.verify_transcript(changed, 0)
    with pytest.raises(storage.StorageRefusal):
        storage.verify_transcript(result, 1)


def test_evidence_reference_refuses_replacement_escape_and_unsealed_bytes(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    root = storage.PrivateEvidence(tmp_path)
    reference = root.publish("stage.json", b'{"actual": 3}\n')
    assert root.read_reference(reference) == b'{"actual": 3}\n'
    with pytest.raises(FileExistsError):
        root.publish("stage.json", b"replacement")
    (tmp_path / "linked.json").symlink_to(tmp_path / "stage.json")
    for path in ["../stage.json", "linked.json", "/stage.json", "a/../stage.json"]:
        with pytest.raises((storage.StorageRefusal, OSError)):
            root.read_reference(reference.model_copy(update={"path": path}))
    (tmp_path / "stage.json").write_bytes(b'{"actual": 4}\n')
    with pytest.raises(storage.StorageRefusal):
        root.read_reference(reference)


@pytest.mark.parametrize("profile", ["sql-01", "smoke-01", "walk-01"])
def test_new_container_wal_senders_profile_is_scoped_to_native_create(
    tmp_path, monkeypatch, profile
):
    from contextlib import nullcontext

    run = tmp_path / profile
    (run / "pgdata").mkdir(parents=True)
    recorded = []
    monkeypatch.setattr(storage, "pinned_ancestry", lambda _path: nullcontext([]))
    monkeypatch.setattr(
        storage,
        "_media_creation",
        lambda *_args: {"profile": profile, "creator": storage._host_identity(run / "pgdata")},
    )

    class StopAfterCreate(Exception):
        pass

    def capture(command, **_kwargs):
        recorded.extend(command)
        raise StopAfterCreate

    monkeypatch.setattr(storage, "exact_output", capture)
    with pytest.raises(StopAfterCreate):
        storage.create_and_start(
            storage.PrivateEvidence(run / "evidence"), tmp_path, "a" * 32, "sha256:" + "b" * 64
        )
    assert recorded[:2] == ["docker", "create"]
    assert ("max_wal_senders=0" in recorded) == (profile != "sql-01")
    if profile != "sql-01":
        assert recorded[-2:] == ["-c", "max_wal_senders=0"]


@pytest.mark.parametrize("actual", [None, ("1",), ("00",), (False,), ("0",)])
def test_physical_native_wal_sender_setting_requires_actual_exact_zero(actual):
    if actual == ("0",):
        assert storage.native_wal_senders(actual) == 0
    else:
        with pytest.raises(storage.StorageRefusal, match="WAL senders"):
            storage.native_wal_senders(actual)
