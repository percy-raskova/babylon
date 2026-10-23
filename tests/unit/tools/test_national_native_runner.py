"""The real failure writer preserves compound refusals without exporting secrets."""

import json
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from tools.devtools import national_game_memory as memory
from tools.devtools import national_native_runner as runner
from tools.devtools.national_native_evidence import NativeRunIncomplete

PRIVATE = "postgresql://private-user:private-password@private-host/private-database"


@pytest.mark.parametrize("failed_stage", [None, "bootstrap", "provision-readers"])
def test_preparation_admits_confined_readers_before_absent_campaign_capture(
    tmp_path, monkeypatch, failed_stage
):
    run = object.__new__(runner.NativeRun)
    run.root = tmp_path
    run.directory = tmp_path
    run.campaign = "81b979ee-a9c1-48fd-8835-06cbfe594675"
    run.policy_hash = "c" * 64
    run.periods = 2
    run.runtime = Path("/owned/babylon-runtime")
    run.timeout = 900
    calls = []
    run.progress = lambda *_args: None
    run.environments = lambda: ({"PRIVATE": PRIVATE}, {})
    run.snapshot = lambda stage: calls.append(stage)
    run.verify_sources = lambda: calls.append("verified")

    def execute(arguments, **options):
        assert arguments[0] == str(run.runtime)
        assert options["env"] == {"PRIVATE": PRIVATE}
        calls.append(arguments[1])
        return SimpleNamespace(returncode=int(arguments[1] == failed_stage))

    monkeypatch.setattr(runner.subprocess, "run", execute)
    if failed_stage:
        with pytest.raises(runner.NativeRunRefusal):
            run.prepare()
        assert calls == (
            ["bootstrap"] if failed_stage == "bootstrap" else ["bootstrap", "provision-readers"]
        )
        assert not (tmp_path / "schema-baseline.json").exists()
    else:
        run.prepare()
        assert calls == ["bootstrap", "provision-readers", "schema-baseline", "verified"]
    assert not list(tmp_path.glob("material-*.json"))


@pytest.mark.parametrize("kind", ["nested", "cancelled", "single"])
def test_main_retains_safe_failure_leaves_and_exact_incomplete_counts(
    tmp_path, monkeypatch, capsys, kind
):
    safe = runner.NativeRunRefusal("national source capture changed during the native run")
    if kind == "nested":
        error = ExceptionGroup(
            PRIVATE,
            [
                safe,
                RuntimeError(PRIVATE),
                ExceptionGroup(
                    PRIVATE, [memory.DockerOperationRefusal("run", 42, PRIVATE.encode())]
                ),
            ],
        )
        expected = [
            {"failure_type": "NativeRunRefusal", "safe_reason": str(safe)},
            {"failure_type": "RuntimeError", "safe_reason": None},
            {
                "failure_type": "DockerOperationRefusal",
                "safe_reason": "owned Docker run refused with exit code 42",
            },
        ]
    elif kind == "cancelled":
        error = BaseExceptionGroup(PRIVATE, [safe, KeyboardInterrupt(PRIVATE)])
        expected = [
            {"failure_type": "NativeRunRefusal", "safe_reason": str(safe)},
            {"failure_type": "KeyboardInterrupt", "safe_reason": None},
        ]
    else:
        error = safe
        expected = [{"failure_type": "NativeRunRefusal", "safe_reason": str(safe)}]

    def fail():
        raise error

    run = SimpleNamespace(
        directory=tmp_path,
        stage="archive",
        boundaries=[object()],
        recoveries=[],
        run=fail,
    )
    monkeypatch.setenv("BABYLON_STORAGE_REPORT_DIRECTORY", str(tmp_path))
    monkeypatch.setattr(runner, "NativeRun", lambda _root, _directory: run)
    assert runner.main() == 1
    data = (tmp_path / "native-run-incomplete.json").read_text()
    evidence = json.loads(data)
    assert evidence == {
        "version": 2,
        "status": "incomplete",
        "last_recorded_stage": "archive",
        "complete_boundary_records": 1,
        "authenticated_recoveries": 0,
        "failure_type": type(error).__name__,
        "failures": expected,
    }
    assert "qualified" not in data
    output = capsys.readouterr()
    assert PRIVATE not in data + output.out + output.err
    assert not list(tmp_path.glob("*.partial"))
    NativeRunIncomplete.model_validate(evidence)


@pytest.mark.parametrize("version", [1, 3, "2", True])
def test_failure_reader_refuses_unsupported_and_noninteger_versions(version):
    with pytest.raises(ValueError):
        NativeRunIncomplete.model_validate(
            {
                "version": version,
                "status": "incomplete",
                "last_recorded_stage": "archive",
                "complete_boundary_records": 0,
                "authenticated_recoveries": 0,
                "failure_type": "NativeRunRefusal",
                "failures": [{"failure_type": "NativeRunRefusal", "safe_reason": "refused"}],
            }
        )


def marker_run(monkeypatch, identity, tail, acknowledged=None):
    """Exercise the actual confined marker reader with modeled database rows."""
    rows = iter((identity, tail))

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def execute(self, query, _parameters=None):
            if query.startswith("SET TRANSACTION"):
                return None
            value = next(rows)
            return SimpleNamespace(fetchone=lambda: value)

    monkeypatch.setattr(runner.psycopg, "connect", lambda *_args, **_kwargs: Connection())
    run = object.__new__(runner.NativeRun)
    run.campaign = "81b979ee-a9c1-48fd-8835-06cbfe594675"
    run.reader_dsn = PRIVATE
    run._foundation = acknowledged
    return run


def test_marker_distinguishes_absence_from_a_provisionally_committed_foundation(monkeypatch):
    absent = marker_run(monkeypatch, None, None).marker()
    assert absent.foundation_sha256 is None and absent.campaign_age_ticks == 0
    present = marker_run(monkeypatch, (bytes.fromhex("a" * 64),), None).marker()
    assert present.foundation_sha256 == "a" * 64 and present.campaign_age_ticks == 0


@pytest.mark.parametrize(
    "identity,tail,acknowledged",
    [
        (None, (1, bytes.fromhex("b" * 64)), None),
        ((b"malformed",), None, None),
        ((bytes.fromhex("a" * 64),), (1, None), None),
        ((bytes.fromhex("a" * 64),), (0, bytes.fromhex("b" * 64)), None),
        (None, None, "a" * 64),
        ((bytes.fromhex("b" * 64),), None, "a" * 64),
    ],
)
def test_marker_refuses_orphans_malformed_rows_and_changed_acknowledgments(
    monkeypatch, identity, tail, acknowledged
):
    with pytest.raises(runner.NativeRunRefusal):
        marker_run(monkeypatch, identity, tail, acknowledged).marker()


def test_native_opening_mismatch_cannot_bind_or_publish_the_capture(tmp_path, monkeypatch):
    run = object.__new__(runner.NativeRun)
    run.campaign = "81b979ee-a9c1-48fd-8835-06cbfe594675"
    run.policy_hash = "c" * 64
    run._foundation = None
    run.opening = None
    run.directory = tmp_path
    run.operation_lock = threading.RLock()
    calls = []
    run.verify_sources = lambda: None
    run.snapshot = lambda stage: calls.append(stage)
    run._capture = SimpleNamespace(bind_foundation=lambda _digest: calls.append("bound"))
    run.marker = lambda: memory.CampaignMemoryMarker(
        campaign=run.campaign,
        foundation_sha256="b" * 64,
        campaign_age_ticks=0,
        tick_content_hash=None,
    )
    record = SimpleNamespace(
        tick=0,
        tick_content_hash=None,
        opening=SimpleNamespace(
            campaign=run.campaign, foundation_sha256="a" * 64, policy_sha256=run.policy_hash
        ),
    )
    monkeypatch.setattr(runner, "read_record", lambda *_args: record)
    state = SimpleNamespace(
        campaign_id=run.campaign,
        foundation_sha256="a" * 64,
        durable_tick=0,
        tick_content_hash=None,
    )
    with pytest.raises(runner.NativeRunRefusal, match="independent committed identity"):
        run.on_boundary(state)
    assert run._foundation is None and run.opening is None and not calls
