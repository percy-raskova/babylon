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
        failed_pair=None,
        boundaries=[object()],
        recoveries=[],
        run=fail,
        publish_verification_diagnostics=lambda: None,
    )
    monkeypatch.setenv("BABYLON_STORAGE_REPORT_DIRECTORY", str(tmp_path))
    monkeypatch.setattr(runner, "NativeRun", lambda _root, _directory: run)
    assert runner.main() == 1
    data = (tmp_path / "native-run-incomplete.json").read_text()
    evidence = json.loads(data)
    assert evidence == {
        "version": 3,
        "failed_pair": None,
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


@pytest.mark.parametrize("version", [1, 2, "3", True])
def test_failure_reader_refuses_unsupported_and_noninteger_versions(version):
    with pytest.raises(ValueError):
        NativeRunIncomplete.model_validate(
            {
                "version": version,
                "failed_pair": None,
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
    run.policy = SimpleNamespace(maximum_production_read_seconds=180)
    run.mode = "normal_play"
    run._foundation = None
    run.opening = None
    run.directory = tmp_path
    run.operation_lock = threading.RLock()
    run.verification_spans = []
    run.verification_dropped = 0
    run.verification_sequence = 0
    run.verification_state = None
    run.verification_published = False
    run.segment = None
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
        production_read_elapsed_ns=1,
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
        scope_epoch=0,
        generation=0,
        tick_content_hash=None,
    )
    run.stage = "opening"
    with pytest.raises(runner.NativeRunRefusal, match="independent committed identity"):
        run.on_boundary(state)
    assert run._foundation is None and run.opening is None and not calls


@pytest.mark.parametrize("change", ["duplicate", "later-debit", "invented-actor"])
def test_walk_practice_requires_one_first_response_with_its_actual_recipient_hours(change):
    import hashlib

    from tools.devtools import national_native_evidence as evidence
    from tools.devtools.national_storage_qualification import AidPracticeEvidence

    original = (1,) * 32
    use = hashlib.sha256(
        b"babylon.organizer-household-contribution.v1\0"
        + bytes([3] * 32)
        + (42).to_bytes(8, "big")
        + (8).to_bytes(8, "big")
    ).digest()
    first = AidPracticeEvidence.model_validate(
        {
            "original_commitment": original,
            "material_commitment_id": [5] * 32,
            "practice_receipt_id": [3] * 32,
            "first_response_receipt_id": [3] * 32,
            "first_response_receipt_sha256": [6] * 32,
            "absent_contribution_use_ids": [[9] * 32],
            "contribution_postings": [
                {"use_id": list(use), "actor_id": 42, "contributor_id": 8, "hours": 2}
            ],
            "mandate": [2] * 32,
            "dispatch_period": 3,
            "period": 3,
            "qualifying_received_support": True,
            "food_consumed": False,
            "food_consumed_quantity": 0,
            "food_consumption_period": None,
            "cash_received_micros": "280000000",
            "cash_received_period": 3,
            "first_response_period": 3,
            "partner_actor": 42,
            "partner_response": "participated",
            "outcome": "aid_practice_completed",
            "recipient_debited_hours": 2,
            "finite_practice_completed": True,
        }
    )
    retained = AidPracticeEvidence.model_validate(
        {
            **first.model_dump(),
            "practice_receipt_id": [4] * 32,
            "absent_contribution_use_ids": [[8] * 32],
            "contribution_postings": [],
            "period": 4,
            "food_consumed": True,
            "food_consumed_quantity": 2,
            "food_consumption_period": 4,
            "cash_received_micros": "0",
            "cash_received_period": None,
            "outcome": "aid_response_retained",
            "partner_actor": None,
            "partner_response": "not_requested",
            "recipient_debited_hours": 0,
            "finite_practice_completed": False,
        }
    )

    def receipt(period, outcome, hours):
        return {
            "receipt_id": [period] * 32,
            "commitment_id": list(original),
            "period": period,
            "partner_actor_id": 42 if hours else None,
            "partner_response": "participated" if hours else "not_requested",
            "outcome": outcome,
            "choice": "remote_aid",
            "actor_id": 1,
            "standing_work": False,
            "hours_spent": hours,
            "observation_ids": [],
            "contact_product_id": None,
            "time_use": [{"actor_id": 42, "contributor_id": 8, "hours": hours}] if hours else [],
        }

    rows = [receipt(3, first.outcome, 2), receipt(4, retained.outcome, 0)]
    assert evidence.walk_response(original, (first, retained), rows, actor=1, choice="remote_aid")[
        "retained_without_second_debit"
    ] == [4]
    if change == "duplicate":
        rows.append({**rows[0], "receipt_id": [5] * 32})
    elif change == "later-debit":
        rows[1]["time_use"] = [{"actor_id": 42, "contributor_id": 8, "hours": 1}]
    else:
        rows[0]["partner_actor_id"] = 41
    with pytest.raises(ValueError, match="recipient|response"):
        evidence.walk_response(original, (first, retained), rows, actor=1, choice="remote_aid")


def test_frame_header_and_original_extent_cannot_hide_truncated_png() -> None:
    from io import BytesIO

    from PIL import Image
    from tools.devtools import national_native_evidence as evidence

    buffer = BytesIO()
    Image.new("RGB", (1366, 768)).save(buffer, format="PNG")
    raw = buffer.getvalue()
    for damaged in (raw[:33], raw[:-12], raw + b"extra"):
        with pytest.raises(ValueError, match="PNG"):
            evidence.verify_frame_png(damaged, 1366, 768)
    evidence.verify_frame_png(raw, 1366, 768)


def test_wait_uses_actual_campaign_citation_after_autosave(tmp_path, monkeypatch):
    run = SimpleNamespace(directory=tmp_path / "evidence", campaign="c", timeout=2)
    run.directory.mkdir(mode=0o700)
    walk = runner.WayneWalk(run)
    path = tmp_path / "xdg/state/babylon/organizer-drafts/c.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(b'{"schema":4,"campaign":"other","references":[]}')
    path.chmod(0o600)
    prior = path.read_bytes()
    ref = [12] * 32

    def autosave(_seconds):
        path.write_text(
            json.dumps(
                {
                    "schema": 4,
                    "campaign": "c",
                    "workplace": 7,
                    "choice": "hold",
                    "notes": "",
                    "collection_allocation": "none",
                    "aid_allocation": "none",
                    "references": [ref],
                    "selected_reference": ref,
                }
            )
        )

    monkeypatch.setattr(runner.time, "sleep", autosave)
    walk.wait_citation(bytes(ref).hex(), 1)
    assert (run.directory / "citation-prior-00.json").read_bytes() == prior


def boundary_run(tmp_path):
    from tools.devtools.national_windowed_qualification import ControlState

    from tests.unit.tools.test_national_storage_qualification import native_join_evidence, policy

    manifest, _report, _timing, _memory, _opening, ticks, records = native_join_evidence(tmp_path)
    state = ControlState.model_validate(
        next(
            row["state"]
            for row in records["native-controls.json"]["actions"]
            if row["action"] == "await_period_proof"
        )
    )
    run = object.__new__(runner.NativeRun)
    run.directory = tmp_path
    run.campaign = manifest["campaign"]
    run.stage = "walk"
    run._foundation = manifest["foundation_sha256"]
    run.policy_hash = manifest["policy_sha256"]
    run.mode = "normal_play"
    run.wayne_profile = "walk-01"
    run.boundaries = []
    run.material = []
    run.advances = []
    run.snapshots = []
    run.started = 0
    run.verification_spans = []
    run.verification_dropped = 0
    run.verification_sequence = 0
    run.verification_state = None
    run.verification_published = False
    run.segment = None
    run.policy = policy()
    run.verify_sources = lambda: None
    run.progress = lambda *_args: None
    calls = []

    def archive(_record):
        calls.append("archive")
        raw = records["archive-1.json"]["archive"]
        return runner.ArchiveBoundary.model_validate(
            {
                key: raw[key]
                for key in (
                    "expected_tick",
                    "durable_tick",
                    "processed_tick",
                    "pending_count",
                    "dossier_sha256",
                )
            }
        )

    def snapshot(_stage):
        calls.append("storage")
        return ticks[0]

    run.archive = archive
    run.snapshot = snapshot
    return run, state, calls, records


@pytest.mark.parametrize("fault", [None, "missing", "substituted"])
def test_actual_boundary_checks_follow_matching_published_proof(tmp_path, fault):
    from tools.devtools.national_windowed_qualification import ControlState

    run, state, calls, _records = boundary_run(tmp_path)
    if fault:
        raw = state.model_dump(mode="json")
        if fault == "missing":
            raw["period_proof"] = None
        else:
            raw["period_proof"]["material_record_sha256"] = "de" * 32
        with pytest.raises(runner.NativeRunRefusal, match="proof"):
            run.on_boundary(ControlState.model_validate(raw))
        assert calls == []
    else:
        run.on_boundary(state)
        assert calls == ["archive", "storage"] and len(run.boundaries) == 1


@pytest.mark.parametrize(
    "field", ["campaign", "epoch", "foundation", "policy", "tick", "marker", "world"]
)
def test_live_boundary_rejects_foreign_advance_before_independent_callbacks(tmp_path, field):
    run, state, calls, records = boundary_run(tmp_path)
    advance = records["advance-1.json"]
    if field == "campaign":
        advance["runtime_scope"]["campaign_id"] = "00000000-0000-4000-8000-000000000001"
    elif field == "epoch":
        advance["runtime_scope"]["epoch"] += 1
    elif field in ("foundation", "policy"):
        advance[field + "_sha256"] = "fe" * 32
    elif field == "tick":
        advance["committed_tail"]["resolve_tick"] += 1
    else:
        advance["committed_tail"]["tick_content_hash" if field == "marker" else "world_hash"] = (
            "fe" * 32
        )
    (tmp_path / "advance-1.json").write_text(json.dumps(advance))
    with pytest.raises(runner.NativeRunRefusal, match="proof|Advance"):
        run.on_boundary(state)
    assert calls == []


def test_over_budget_boundary_records_and_aborts_before_archive(tmp_path):
    run, state, _calls, records = boundary_run(tmp_path)
    records["advance-1.json"]["advance_elapsed_ns"] = 121_000_000_000
    (tmp_path / "advance-1.json").write_text(json.dumps(records["advance-1.json"]))
    run.archive = lambda *_: pytest.fail("over-budget close advanced to Archive")
    with pytest.raises(runner.NativeRunRefusal, match="advance"):
        run.on_boundary(state)
    failed = json.loads((tmp_path / "first-budget-divergence.json").read_bytes())
    assert (failed["elapsed_ns"], failed["state"]["durable_tick"]) == (121_000_000_000, 1)


def test_corrupt_frame_survives_temporary_socket_cleanup(tmp_path):
    run = SimpleNamespace(directory=tmp_path / "evidence", campaign="c")
    walk = runner.WayneWalk(run)
    walk.raw.path.mkdir(mode=0o700)
    socket = tmp_path / "frames"
    socket.mkdir(mode=0o700)
    (socket / "frame-7.png").write_bytes(b"broken")
    (socket / "frame-7.png").chmod(0o600)
    state = SimpleNamespace(model_dump=lambda **_kw: {"campaign_id": "c"})
    channel = SimpleNamespace(
        sequence=6,
        records=[],
        state=state,
        last_response=None,
        response_bytes=b"broken acknowledgement\n",
    )

    def captured(_action, _timeout):
        channel.sequence = 7
        channel.records.append(
            SimpleNamespace(sequence=7, event="frame_captured", model_dump=lambda **_kw: {})
        )
        return state

    channel.perform = captured
    walk.run.timeout = 1
    with pytest.raises(ValueError):
        walk.capture_frame(channel, socket, "opening", state, 12, 8)
    assert list(walk.raw.path.glob("*incomplete*.png"))[0].read_bytes() == b"broken"
    assert list(walk.raw.path.glob("*-response.bin"))[0].read_bytes() == b"broken acknowledgement\n"
    # The writer completes during launcher shutdown after the immediate copy.
    final = b"pixels written after immediate refusal"
    (socket / "frame-7.png").write_bytes(final)
    walk.retain_stopped_frame()
    final_record = json.loads(next(walk.raw.path.glob("*-stopped.json")).read_bytes())
    assert final_record["original_byte_length"] == len(final)
    assert (walk.raw.path / final_record["capture"]["path"]).read_bytes() == final


@pytest.mark.parametrize(
    "mutation", ["purchased", "settlement", "actor", "membership", "grant", "period"]
)
def test_dated_recipient_disclosure_matches_its_source_and_grant(mutation):
    import copy

    from tools.devtools import national_native_evidence as e

    actor, subject = 10, 20
    rid, obs = [3] * 32, [9] * 32
    facts = {
        "basis": "food_provision",
        "commodity": {
            "good_id": [7] * 32,
            "unit_id": [6] * 32,
            "label": "Food",
            "unit_label": "units",
        },
        "required": 5,
        "consumed": 2,
        "unmet": 3,
        "closing": 0,
        "purchased": 2,
        "settled_micros": "42",
    }
    source = {
        "actor_id": actor,
        "subject_id": subject,
        "source_actor_id": subject,
        "observed_period": 4,
        "acquired_period": 4,
        "observation_id": obs,
        "receipt_id": None,
    }
    witness = e.PartnerSource.model_validate(
        {**source, "source_hash": [8] * 32, "mandate_id": [5] * 32, "facts": facts}
    )
    data = {
        **source,
        "report": {"kind": "partner", "evidence_class": "Derived", "facts": copy.deepcopy(facts)},
    }
    key = bytes(obs).hex()
    locator = f"source-actor/20/observed-period/4/acquired-period/4/observation/{key}/action-receipt/automatic-report"
    grants = [
        ["organization", "20", "report-" + key, 4, "derived-scoped-partner-report-v1", locator]
    ]

    def verify():
        e.verify_partner_source(
            witness,
            runner.Observation.model_validate(data),
            actor=actor,
            period=4,
            source_hash=bytes([8] * 32).hex(),
            grants=grants,
        )

    verify()
    if mutation == "purchased":
        data["report"]["facts"]["purchased"] = 3
    elif mutation == "settlement":
        data["report"]["facts"]["settled_micros"] = "41"
    elif mutation == "actor":
        data["source_actor_id"] = 21
    elif mutation == "membership":
        data["receipt_id"] = rid
    elif mutation == "period":
        data["observed_period"] = 2
    else:
        grants[0][1] = "21"
    with pytest.raises(ValueError, match="recipient|report"):
        verify()


def test_reopened_quiet_period_cannot_replace_first_recipient_receipt_under_same_id():
    from tools.devtools import national_native_evidence as e

    original = {
        "receipt_id": [7] * 32,
        "actor_id": 31,
        "partner_response": "participated",
        "time_use": [{"actor_id": 7, "contributor_id": 3, "hours": 2}],
        "period": 3,
    }
    import hashlib

    raw = json.dumps(original).encode()
    digest = hashlib.sha256(raw).digest()
    key = bytes(original["receipt_id"]).hex()
    stages = {
        p: SimpleNamespace(facts={"receipts": [original.copy()], "receipt_bytes": {key: raw.hex()}})
        for p in (3, 4, 5)
    }
    e.verify_first_receipt_prefix(stages, original, digest)
    stages[4].facts["receipts"][0] = {**original, "time_use": []}
    with pytest.raises(ValueError, match="first response"):
        e.verify_first_receipt_prefix(stages, original, digest)


def test_quiet_active_routine_refuses_even_without_any_standing_work_receipt():
    from tools.devtools import national_native_evidence as e

    view = SimpleNamespace(
        actor_id=7,
        standing=SimpleNamespace(authorized=True, paused_reason=None),
        resume_reviewable=False,
    )
    stage = SimpleNamespace(state=SimpleNamespace(installed_organizer=view), facts={"receipts": []})
    with pytest.raises(ValueError, match="resumed"):
        e.verify_standing_period(stage, 7, True)


def test_nonqualifying_retained_practice_cannot_prove_separate_mixed_leg():
    from tools.devtools import national_native_evidence as e

    first = SimpleNamespace(
        period=3,
        cash_received_period=3,
        food_consumption_period=3,
        first_response_period=3,
        practice_receipt_id=(3,) * 32,
        first_response_receipt_id=(3,) * 32,
        qualifying_received_support=True,
        outcome="aid_practice_completed",
        mandate=(1,) * 32,
        material_commitment_id=(2,) * 32,
    )
    later = SimpleNamespace(
        **{
            **vars(first),
            "period": 4,
            "cash_received_period": None,
            "food_consumption_period": None,
            "outcome": "aid_response_retained",
            "practice_receipt_id": (4,) * 32,
            "qualifying_received_support": False,
        }
    )
    assert not e.has_later_retained_leg((first, later))
    later.food_consumption_period = 4
    later.qualifying_received_support = True
    assert e.has_later_retained_leg((first, later))
    later.first_response_receipt_id = (8,) * 32
    assert not e.has_later_retained_leg((first, later))


def test_full_first_response_digest_binds_original_sql_bytes_across_every_later_marker():
    import hashlib

    from tools.devtools import national_native_evidence as e

    first = {"receipt_id": [7] * 32, "period": 3, "actor_id": 41, "time_use": []}
    raw = json.dumps(first, separators=(",", ":")).encode()
    key = bytes(first["receipt_id"]).hex()
    stages = {
        p: SimpleNamespace(facts={"receipts": [first], "receipt_bytes": {key: raw.hex()}})
        for p in (3, 4, 5)
    }
    e.verify_first_receipt_prefix(stages, first, hashlib.sha256(raw).digest())
    stages[4].facts["receipt_bytes"][key] = json.dumps(first).encode().hex()
    with pytest.raises(ValueError, match="first response"):
        e.verify_first_receipt_prefix(stages, first, hashlib.sha256(raw).digest())


@pytest.mark.parametrize("field", ["contribution_postings", "absent_contribution_use_ids"])
def test_later_material_boundary_cannot_reissue_a_prior_positive_or_absent_use(field):
    from tools.devtools import national_native_evidence as e

    earlier = SimpleNamespace(
        contribution_postings=[SimpleNamespace(use_id=(1,) * 32)],
        absent_contribution_use_ids=[(2,) * 32],
    )
    later = SimpleNamespace(contribution_postings=[], absent_contribution_use_ids=[(3,) * 32])
    boundaries = [
        SimpleNamespace(independent_practices=[earlier]),
        SimpleNamespace(independent_practices=[]),
        SimpleNamespace(independent_practices=[later]),
    ]
    e.verify_contribution_history(boundaries)
    setattr(
        later,
        field,
        [SimpleNamespace(use_id=(2,) * 32)] if field == "contribution_postings" else [(1,) * 32],
    )
    with pytest.raises(ValueError, match="contribution"):
        e.verify_contribution_history(boundaries)


def test_action_observation_requires_exact_current_actor_receipt_membership():
    from tools.devtools import national_native_evidence as e

    obs = runner.Observation.model_validate(
        {
            "observation_id": [6] * 32,
            "actor_id": 20,
            "subject_id": 5,
            "source_actor_id": 8,
            "observed_period": 2,
            "acquired_period": 3,
            "receipt_id": [4] * 32,
            "report": {
                "kind": "maintenance",
                "enabled_batches": 1,
                "consumed_batches": 0,
                "expired_batches": 0,
            },
        }
    )
    rows = [{"receipt_id": [4] * 32, "actor_id": 20, "period": 3, "observation_ids": [[6] * 32]}]
    e.validate_membership(obs, rows, 20)
    rows[0]["observation_ids"] = []
    with pytest.raises(ValueError, match="membership"):
        e.validate_membership(obs, rows, 20)


def test_process_cold_failed_before_install_keeps_actual_segment_first_and_latest_marker(
    tmp_path, monkeypatch
):
    run = SimpleNamespace(
        root=tmp_path,
        directory=tmp_path,
        owner_fields=(),
        mode="memory_capture",
        cold_seconds=lambda: 900,
        capture=lambda *_args, **_kw: object(),
        boundaries=[SimpleNamespace(tick=9, tick_content_hash="a" * 64)],
    )
    walk = runner.WayneWalk(run)
    monkeypatch.setattr(runner, "reauthenticate_native_owner", lambda *_: None)
    clock = iter((50, 70))
    monkeypatch.setattr(runner.time, "monotonic_ns", lambda: next(clock))

    def failed(*_):
        run.pair_identity = [(101, 51, "b" * 64), (102, 53, "c" * 64)]
        walk.first_observed = SimpleNamespace(model_dump=lambda **_kw: {"phase": "Opening"})
        walk.latest_observed = SimpleNamespace(model_dump=lambda **_kw: {"phase": "Loading"})
        raise runner.NativeRunRefusal("installation deadline")

    walk.drive_segment = failed
    with pytest.raises(runner.NativeRunRefusal, match="deadline"):
        walk.pair("completed", None, 10, 0, {}, {})
    failure = json.loads((tmp_path / "pair-incomplete-completed.json").read_bytes())
    assert failure["elapsed_ns"] == 20 and failure["stage"] == "cold-completed"
    assert failure["authenticated_processes"] == [[101, 51, "b" * 64], [102, 53, "c" * 64]]
    assert failure["first_observation"] == {"phase": "Opening"} and failure[
        "latest_observation"
    ] == {"phase": "Loading"}
    assert failure["last_accepted_marker"] == [9, "a" * 64]
    assert run.failed_pair.path == "pair-incomplete-completed.json"
    assert not (tmp_path / "cold-installed-completed.json").exists()


def test_missing_resume_preserves_quiet_authority_requirement_until_terminal():
    from tools.devtools import national_native_evidence as e

    actor, authority, cid = 14, (3,) * 16, (7,) * 32
    command = SimpleNamespace(actor_id=actor, authority_id=authority, choice="pause_standing")
    directive = SimpleNamespace(command=command, commitment_id=cid, resolves_period=4)
    receipt = {
        "actor_id": actor,
        "period": 4,
        "choice": "pause_standing",
        "standing_work": False,
        "outcome": "standing_paused",
        "commitment_id": list(cid),
    }

    def stage(authorized):
        standing = SimpleNamespace(
            authorized=authorized, paused_reason=None if authorized else "explicit"
        )
        return SimpleNamespace(
            state=SimpleNamespace(
                installed_organizer=SimpleNamespace(actor_id=actor, standing=standing)
            ),
            facts={"receipts": [receipt]},
        )

    missing = []
    e.verify_directives([directive], {4: stage(False), 5: stage(False)}, actor, authority, missing)
    assert missing
    with pytest.raises(ValueError, match="resumed"):
        e.verify_directives([directive], {4: stage(False), 5: stage(True)}, actor, authority, [])


def test_bool_citation_ids_do_not_authenticate_the_same_integer_byte(tmp_path):
    run = SimpleNamespace(directory=tmp_path / "evidence", campaign="owned")
    run.directory.mkdir(mode=0o700)
    walk = runner.WayneWalk(run)
    path = walk.draft_path()
    path.parent.mkdir(parents=True)
    raw = json.dumps(
        {
            "schema": 4,
            "campaign": "owned",
            "workplace": 7,
            "choice": "hold",
            "notes": "",
            "collection_allocation": "none",
            "aid_allocation": "none",
            "references": [[True] * 32],
            "selected_reference": [True] * 32,
        }
    ).encode()
    path.write_bytes(raw)
    path.chmod(0o600)
    with pytest.raises(runner.NativeRunRefusal, match="exact campaign citation"):
        walk.wait_citation("01" * 32, 0.001)
    assert (run.directory / "citation-prior-00.json").read_bytes() == raw


@pytest.mark.parametrize(
    ("fault", "expected", "stage"),
    [
        ("second-spawn", [["runtime", 701]], "spawn-client"),
        ("source", [["runtime", 701], ["client", 702]], "verify-sources"),
    ],
)
def test_cold_failure_uses_actual_partial_spawn_roster(
    tmp_path, monkeypatch, fault, expected, stage
):
    from uuid import UUID

    from tools.devtools import national_windowed_qualification as w

    run = SimpleNamespace(
        root=tmp_path,
        directory=tmp_path,
        owner_fields=(),
        mode="memory_capture",
        cold_seconds=lambda: 900,
        runtime=tmp_path / "runtime",
        client=tmp_path / "client",
        timeout=1,
        policy=SimpleNamespace(maximum_cold_open_seconds=180),
        boundaries=[],
        capture=lambda *_args, **_kwargs: SimpleNamespace(lifecycle=None),
        verify_live=lambda: None,
    )

    def refuse():
        raise runner.NativeRunRefusal("source witness refused")

    run.verify_sources = refuse

    class Child:
        def __init__(self, args, **kw):
            self.pid = 701 if args[0] == str(run.runtime) else 702
            if self.pid == 702 and fault == "second-spawn":
                raise OSError("second spawn")

        def wait(self, timeout=None):
            return 0

        def poll(self):
            return 0

    monkeypatch.setattr(w.launcher.subprocess, "Popen", Child)
    monkeypatch.setattr(runner, "reauthenticate_native_owner", lambda *_: None)
    walk = runner.WayneWalk(run)
    with pytest.raises((runner.NativeRunRefusal, w.launcher.ObserverLaunchError)):
        walk.pair("opening", w.launcher.OpenCampaignTarget(UUID(int=13)), 0, 0, {}, {})
    packet = json.loads((tmp_path / "pair-incomplete-opening.json").read_bytes())
    assert packet["launch_stage"] == stage
    assert packet["attempted_processes"] == expected
    assert packet["authenticated_processes"] == []


@pytest.mark.parametrize("initial", [None, b"", b"partial"])
def test_launcher_retains_delayed_frame_only_after_held_children_stop(
    tmp_path, monkeypatch, initial
):
    from uuid import UUID

    from tools.devtools import national_windowed_qualification as w

    run = SimpleNamespace(directory=tmp_path / "evidence", timeout=1)
    run.directory.mkdir(mode=0o700)
    walk = runner.WayneWalk(run)
    walk.raw.path.mkdir(mode=0o700)
    handles = []
    frames = []
    final = b"completed write during shutdown"

    class Child:
        def __init__(self, args, **kwargs):
            self.pid = 101 + len(handles)
            self.code = None
            handles.append(self)
            if "--qualification-control" in args:
                frames.append(Path(args[-1]).parent / "frame-1.png")

        def poll(self):
            return self.code

        def terminate(self):
            if self.pid == 102:
                frames[0].write_bytes(final)
                frames[0].chmod(0o600)

        def wait(self, timeout=None):
            self.code = 0
            return self.code

    monkeypatch.setattr(w.launcher.subprocess, "Popen", Child)
    state = SimpleNamespace(model_dump=lambda **_: {})
    channel = SimpleNamespace(
        sequence=0, state=state, records=[], last_response=None, response_bytes=b""
    )

    def capture(*args):
        channel.sequence += 1
        if initial is not None:
            frames[0].write_bytes(initial)
            frames[0].chmod(0o600)
        raise w.ControlRefusal("sample failure")

    channel.perform = capture

    def started(*_handles):
        walk.capture_frame(channel, frames[0].parent, "opening", state, 1366, 768)

    def stopped():
        assert all(h.poll() is not None for h in handles) and frames[0].parent.exists()
        walk.retain_stopped_frame()

    with pytest.raises(w.ControlRefusal, match="sample failure"):
        w.drive_pair(
            tmp_path / "runtime",
            tmp_path / "client",
            tmp_path,
            {},
            {},
            defines_path=tmp_path / "d",
            initial_target=w.launcher.OpenCampaignTarget(UUID(int=3)),
            initial_tick=0,
            periods=0,
            directory=tmp_path,
            operation_timeout=1,
            on_started=started,
            on_stopped=stopped,
            on_boundary=lambda _: None,
            on_recovery=lambda _: None,
        )
    assert not frames[0].parent.exists()
    after = json.loads(next(walk.raw.path.glob("*-stopped.json")).read_bytes())
    immediate = json.loads((walk.raw.path / after["immediate"]).read_bytes())
    assert immediate["frame_state"] == (
        "absent" if initial is None else "empty" if not initial else "partial_or_invalid_png"
    )
    if initial is not None:
        assert (walk.raw.path / immediate["capture"]["path"]).read_bytes() == initial
    assert after["original_byte_length"] == len(final)
    assert (walk.raw.path / after["capture"]["path"]).read_bytes() == final


def test_mixed_confirm_reopen_stops_before_p3_on_its_own_slow_receipt(tmp_path):
    from tools.devtools import national_native_evidence as e
    from tools.devtools.national_windowed_qualification import ControlState

    from tests.unit.tools.test_national_storage_qualification import native_join_evidence, policy

    _, _, _, _, _, _, records = native_join_evidence(tmp_path)
    base = next(
        a["state"]
        for a in records["native-controls.json"]["actions"]
        if a["action"] == "reopen" and a["state"]["durable_tick"] == 2
    )
    c = next(
        a["state"]["commitment"]
        for a in records["native-controls.json"]["actions"]
        if a["action"] == "confirm"
    )
    c["resolves_period"] = 3
    c["command"].update(
        expected_period=2,
        choice="remote_aid",
        allocation={"aid": {"food_quantity": 2, "cash_micros": "280000000"}},
    )
    current = ControlState.model_validate({**base, "commitment": c})
    after = ControlState.model_validate(
        {
            **current.model_dump(),
            "scope_epoch": current.scope_epoch + 1,
            "generation": current.generation + 1,
        }
    )
    packet = records[f"recovery-2-{current.scope_epoch}.json"]
    packet["cold_reopen_elapsed_ns"] = 181_000_000_000
    packet["previous_scope"]["epoch"] = current.scope_epoch
    packet["restored_scope"]["epoch"] = after.scope_epoch
    packet["authenticated_read"]["runtime_epoch"] = after.scope_epoch
    packet["authenticated_read"]["observation_generation"] = after.generation
    run = object.__new__(runner.NativeRun)
    run.mode = "normal_play"
    run.directory, run.wayne_profile, run.policy, run.timeout = tmp_path, "walk-01", policy(), 900
    run.policy_hash = "ab" * 32
    run.material = [e.MaterialRecord.model_validate(records["material-2.json"])]
    walk = runner.WayneWalk(run)
    walk.evidence.publish_json(f"recovery-2-{after.scope_epoch}.json", packet)
    walk.submit = lambda *_args, **_kwargs: None
    events = []

    def stage(state, label):
        events.append(label)
        return {}

    walk.capture_stage = stage

    def perform(action, timeout):
        events.append(action)
        return after

    observation = SimpleNamespace(
        action="reopen",
        event="reopened_and_installed",
        reason=None,
        state=after,
        started_monotonic_ns=1,
        completed_monotonic_ns=190_000_000_001,
    )
    channel = SimpleNamespace(state=current, perform=perform, records=[observation])
    with pytest.raises(runner.NativeRunRefusal, match="mixed-pending-reopen"):
        walk.installed(channel, tmp_path, current)
    assert events == ["walk-p2-installed", "mixed-pending-before-reopen", "reopen"]
    failed = json.loads((tmp_path / "first-budget-divergence.json").read_bytes())
    assert (
        failed["elapsed_ns"] == 181_000_000_000
        and failed["state"]["scope_epoch"] == after.scope_epoch
    )


@pytest.mark.parametrize(
    ("postings", "pending", "should_follow"),
    [
        ([(3, "Unshipped", 1), (3, "Dispatched", 1)], True, False),
        ([(3, "Dispatched", 2), (4, "Lost", 1)], True, False),
        ([(3, "Unshipped", 1), (3, "Dispatched", 1), (4, "Granted", 1)], False, True),
        ([(3, "Dispatched", 2), (4, "Lost", 1), (4, "Lost", 1)], False, True),
        ([(3, "FoodReceivingRefused", 2)], False, True),
        ([(3, "Unshipped", 2)], False, True),
        ([(3, "CashGranted", 0)], False, False),
        ([(3, "Dispatched", 2), (4, "Lost", 1)], False, None),
        ([(3, "Unshipped", 2)], True, None),
    ],
)
def test_walk_cash_follow_up_waits_for_reconciled_mixed_food(
    tmp_path, postings, pending, should_follow
):
    from tools.devtools.national_windowed_qualification import AidAllocation, AidAmounts

    original = (1,) * 32
    run = SimpleNamespace(
        directory=tmp_path,
        periods=10,
        material=[
            SimpleNamespace(
                aid=SimpleNamespace(
                    period=period,
                    selected_aid=[
                        {
                            "original_commitment": list(original),
                            "outcome": outcome,
                            "quantity": quantity,
                        }
                        for at, outcome, quantity in postings
                        if at == period
                    ],
                )
            )
            for period in (3, 4)
        ],
    )
    walk = runner.WayneWalk(run)
    walk.originals["remote-mixed"] = SimpleNamespace(
        commitment_id=original,
        resolves_period=3,
        command=SimpleNamespace(
            allocation=AidAllocation(aid=AidAmounts(food_quantity=2, cash_micros="280000000"))
        ),
    )
    walk.capture_stage = lambda *_args: {}
    proposals = []
    walk.submit = lambda _channel, _root, choice, label, **_kwargs: proposals.append(
        (choice.period, label)
    )
    held = [SimpleNamespace(original_commitment_id=original)] if pending else []
    state = SimpleNamespace(
        durable_tick=4, installed_organizer=SimpleNamespace(period=4, pending_freight=held)
    )
    if should_follow is None:
        with pytest.raises(ValueError, match="installed mixed freight"):
            walk.installed(None, tmp_path, state)
        assert not proposals
    else:
        walk.installed(None, tmp_path, state)
        assert proposals == ([(5, "local-cash")] if should_follow else [])


@pytest.mark.parametrize("mode", ["normal_play", "memory_capture"])
def test_walk_uses_all_three_cold_segments_and_only_constructs_requested_sampler(
    tmp_path, monkeypatch, mode
):
    import uuid

    segments = []
    captures = []

    def capture(directory, *, fixed_period):
        captures.append((directory, fixed_period))
        return SimpleNamespace(lifecycle="designed memory monitor")

    run = SimpleNamespace(
        root=tmp_path,
        directory=tmp_path,
        mode=mode,
        owner_fields=(),
        runtime=tmp_path / "runtime",
        client=tmp_path / "client",
        timeout=900,
        campaign=str(uuid.uuid4()),
        capture=capture,
        cold_seconds=lambda: 180 if mode == "normal_play" else 900,
        verify_live=lambda: None,
        verify_sources=lambda: None,
        on_recovery=lambda _s: None,
    )

    def drive(*_args, **kwargs):
        segments.append(
            (
                kwargs["initial_tick"],
                kwargs["periods"],
                kwargs["play_penultimate_close"],
                kwargs["cold_window"].maximum_seconds,
                kwargs["capture_lifecycle"],
            )
        )
        assert all(
            callable(kwargs[key])
            for key in ("on_opened", "on_installed", "on_boundary", "on_recovery")
        )
        return 0

    monkeypatch.setattr(runner, "drive_pair", drive)
    monkeypatch.setattr(runner, "reauthenticate_native_owner", lambda *_a: None)
    runner.WayneWalk(run).drive({}, {})
    assert [s[:3] for s in segments] == [(0, 0, False), (0, 10, True), (10, 0, False)]
    if mode == "normal_play":
        assert not captures and all(s[3:] == (180, None) for s in segments)
    else:
        assert [p for _, p in captures] == [0, None, 10]
        assert all(s[3:] == (900, "designed memory monitor") for s in segments)


@pytest.mark.parametrize(
    "mode,focused,remaining", [("normal_play", 60, 1), ("memory_capture", 900, 721)]
)
def test_terminal_archive_retries_share_deadline_and_return_uses_mode_limit(
    tmp_path, monkeypatch, mode, focused, remaining
):
    state = SimpleNamespace(
        durable_tick=10, viewed_tick=10, selected_subject="partner", selected_report_id="report"
    )
    calls = []

    def perform(action, limit):
        calls.append((action, limit))
        if action == "previous_period":
            return SimpleNamespace(durable_tick=10, viewed_tick=9)
        return state

    replies = iter((("refused", "control_stale_or_unavailable"), ("applied", None)))

    def exchange(action, limit):
        calls.append((action, limit))
        event, reason = next(replies)
        return SimpleNamespace(event=event, reason=reason)

    # The acknowledged report completed at t=10. The second attempt starts
    # 179 seconds later, irrespective of time spent inside earlier requests.
    now = iter((11, 189))
    monkeypatch.setattr(
        runner, "time", SimpleNamespace(monotonic=lambda: next(now), sleep=lambda _: None)
    )
    channel = SimpleNamespace(
        state=state,
        records=[SimpleNamespace(completed_monotonic_ns=10**10)],
        perform=perform,
        _exchange=exchange,
    )
    walk = SimpleNamespace(
        run=SimpleNamespace(
            mode=mode,
            timeout=900,
            policy=SimpleNamespace(
                maximum_archive_catchup_seconds=180, maximum_focused_control_seconds=60
            ),
        ),
        draft=lambda: {},
        capture_stage=lambda *_: {},
        frame=lambda *_: None,
    )
    runner.WayneWalk.terminal_navigation(walk, channel, tmp_path)
    assert calls[-4:] == [
        ("archive_report", focused),
        ("open_archive_evidence", min(899 if mode == "memory_capture" else 179, focused)),
        ("open_archive_evidence", remaining),
        ("open_organizer", focused),
    ]


@pytest.mark.parametrize("fault", [None, "source", "client"])
def test_verification_diagnostics_preserve_authentication_order_and_refusals(
    tmp_path, monkeypatch, fault
):
    run = object.__new__(runner.NativeRun)
    run.root = tmp_path
    run.directory = tmp_path
    run.campaign = "81b979ee-a9c1-48fd-8835-06cbfe594675"
    run.mode = "memory_capture"
    run.stage = "committed"
    run.segment = "smoke"
    run.supervisor = {"PRIVATE": PRIVATE}
    run.verification_spans = []
    run.verification_dropped = 0
    run.verification_sequence = 0
    run.verification_state = None
    run.verification_published = False
    run.binaries = {tmp_path / name: name for name in ("runtime", "client", "audit")}
    calls = []

    def shell(arguments, **options):
        calls.append("source")
        assert arguments[2] == 'source "$1"; national_verify_source_capture'
        assert options == {
            "env": run.supervisor,
            "cwd": tmp_path,
            "capture_output": True,
            "timeout": 60,
            "check": False,
        }
        return SimpleNamespace(returncode=int(fault == "source"))

    def digest(path):
        calls.append(path.name)
        return "changed" if fault == path.name else path.name

    monkeypatch.setattr(runner.subprocess, "run", shell)
    monkeypatch.setattr(memory, "executable_digest", digest)
    clock = iter(range(100, 1000, 10))
    cpu = iter(range(1, 100))
    monkeypatch.setattr(runner.time, "monotonic_ns", lambda: next(clock))
    monkeypatch.setattr(runner.time, "thread_time_ns", lambda: next(cpu))
    usage_calls = []

    def usage(scope):
        usage_calls.append(scope)
        return SimpleNamespace(
            ru_utime=len(usage_calls) / 100,
            ru_stime=len(usage_calls) / 200,
            ru_inblock=len(usage_calls) * 2,
            ru_oublock=len(usage_calls) * 3,
        )

    monkeypatch.setattr(runner.resource, "getrusage", usage)
    writes = []
    original_publish = runner.publish

    def write(path, value):
        writes.append(path.name)
        original_publish(path, value)

    monkeypatch.setattr(runner, "publish", write)
    if fault:
        with pytest.raises(runner.NativeRunRefusal, match="source capture|executable changed"):
            run.verify_sources()
    else:
        run.verify_sources()
    assert calls == (
        ["source"]
        if fault == "source"
        else ["source", "runtime", "client"]
        if fault
        else ["source", "runtime", "client", "audit"]
    )
    assert writes == []
    run.publish_verification_diagnostics()
    assert writes == ["verification-diagnostics.json"]
    data = json.loads((tmp_path / writes[0]).read_bytes())
    assert data["version"] == 1 and data["purpose"] == "diagnostics_only"
    assert data["mode"] == "memory_capture" and data["dropped_spans"] == 0
    spans = data["spans"]
    assert [row["phase"] for row in spans] == [
        "source-shell",
        *["executable-" + name for name in calls[1:]],
    ]
    assert [row["sequence"] for row in spans] == list(range(1, len(spans) + 1))
    for row in spans:
        assert row["segment"] == "smoke" and row["stage"] == "committed"
        assert row["tick"] is None and row["scope_epoch"] is None
        assert row["end_monotonic_ns"] > row["start_monotonic_ns"]
        assert row["thread_cpu_ns"] == 1
        assert row["thread_inblock_operations"] > 0 and row["thread_oublock_operations"] > 0
    assert spans[0]["reaped_children_cpu_ns"] == 15000000
    assert spans[0]["reaped_children_inblock_operations"] == 2
    assert spans[0]["reaped_children_oublock_operations"] == 3
    assert all(row["reaped_children_cpu_ns"] is None for row in spans[1:])
    assert all(row["completed"] for row in spans[:-1])
    assert spans[-1]["completed"] == (fault is None)
    assert PRIVATE not in json.dumps(data)
    assert set(usage_calls) == {runner.resource.RUSAGE_THREAD, runner.resource.RUSAGE_CHILDREN}


def test_boundary_diagnostics_bind_callback_scope_and_keep_progress_inside_the_tail(
    tmp_path, monkeypatch
):
    run, state, calls, _records = boundary_run(tmp_path)
    run.segment = "smoke"
    run.verification_spans = []
    run.verification_dropped = 0
    run.verification_sequence = 0
    run.verification_state = None
    run.verification_published = False
    # Exercise actual progress publication; all other boundary evidence uses the existing fixture.
    run.progress = runner.NativeRun.progress.__get__(run)
    run.on_boundary(state)
    assert calls == ["archive", "storage"]
    assert not (tmp_path / "verification-diagnostics.json").exists()
    run.publish_verification_diagnostics()
    spans = json.loads((tmp_path / "verification-diagnostics.json").read_bytes())["spans"]
    boundary = next(row for row in spans if row["phase"] == "boundary-callback")
    tail = next(row for row in spans if row["phase"] == "progress-production")
    binding = next(row for row in spans if row["phase"] == "advance-proof-binding")
    first = next(row for row in spans if row["phase"] == "progress-committed")
    assert boundary["start_monotonic_ns"] <= binding["start_monotonic_ns"]
    assert binding["end_monotonic_ns"] <= first["start_monotonic_ns"]
    assert first["end_monotonic_ns"] <= tail["start_monotonic_ns"]
    assert tail["end_monotonic_ns"] <= boundary["end_monotonic_ns"]
    assert all(
        (row["tick"], row["scope_epoch"], row["generation"])
        == (state.durable_tick, state.scope_epoch, state.generation)
        for row in spans
    )
    assert run.verification_state is None


@pytest.mark.parametrize("publication_fault", [False, True])
def test_authentic_boundary_failure_retains_diagnostics_and_publication_faults(
    tmp_path, monkeypatch, publication_fault
):
    run, state, _calls, _records = boundary_run(tmp_path)
    run.failed_pair = None
    run.recoveries = []
    original = runner.NativeRunRefusal("national source capture changed during the native run")

    def refuse():
        raise original

    run.verify_sources = refuse
    run.run = lambda: run.on_boundary(state)
    monkeypatch.setenv("BABYLON_STORAGE_REPORT_DIRECTORY", str(tmp_path))
    monkeypatch.setattr(runner, "NativeRun", lambda *_args: run)
    original_publish = runner.publish
    failed_publication = OSError("private diagnostic write failed")

    def publish(path, data):
        if publication_fault and path.name == "verification-diagnostics.json":
            raise failed_publication
        original_publish(path, data)

    monkeypatch.setattr(runner, "publish", publish)
    if publication_fault:
        with pytest.raises(BaseExceptionGroup) as caught:
            runner.main()
        assert caught.value.exceptions == (original, failed_publication)
        assert not (tmp_path / "native-run-incomplete.json").exists()
    else:
        assert runner.main() == 1
        data = json.loads((tmp_path / "verification-diagnostics.json").read_bytes())
        assert len(data["spans"]) == 1
        assert data["spans"][0]["phase"] == "boundary-callback"
        assert data["spans"][0]["completed"] is False
        failure = NativeRunIncomplete.model_validate_json(
            (tmp_path / "native-run-incomplete.json").read_bytes()
        )
        assert failure.failures[0].safe_reason == str(original)


def test_ordinary_drive_strips_audit_only_on_copies_and_reuses_existing_owned_launcher(
    tmp_path, monkeypatch
):
    """The companion keeps the qualified originals and process-custody callbacks."""
    audit = {
        "BABYLON_QUALIFICATION_POLICY": "policy",
        "BABYLON_QUALIFICATION_POLICY_SHA256": "a" * 64,
        "BABYLON_QUALIFICATION_PERIODS": "10",
        "BABYLON_QUALIFICATION_MATERIAL_DIRECTORY": "material",
    }
    writer = {**audit, "BABYLON_POSTGRES_URL": "writer", "BABYLON_WRITER_SCOPE": "retained"}
    reader = {**audit, "BABYLON_POSTGRES_URL": "reader", "BABYLON_READER_SCOPE": "retained"}
    originals = dict(writer), dict(reader)
    run = SimpleNamespace(
        root=tmp_path,
        directory=tmp_path / "evidence",
        timeout=12,
        runtime=tmp_path / "runtime",
        client=tmp_path / "client",
        campaign="81b979ee-a9c1-48fd-8835-06cbfe594675",
    )
    companion = runner.OrdinaryWarmPrefix(run)

    def started(*_args):
        return None

    calls = []

    def drive(runtime, client, root, runtime_environment, client_environment, **options):
        calls.append(options)
        assert (runtime, client, root) == (run.runtime, run.client, tmp_path)
        assert not any(
            key in environment
            for key in audit
            for environment in (runtime_environment, client_environment)
        )
        assert runtime_environment == {
            key: value for key, value in writer.items() if key not in audit
        }
        assert client_environment == {
            key: value for key, value in reader.items() if key not in audit
        }
        assert options["periods"] == 0 and options["choices"] == ()
        assert options["capture_lifecycle"] is None and options["on_installed"] is companion
        assert options["on_started"] is started
        assert options["on_stopped"] == companion.walk.retain_stopped_frame
        assert options["initial_tick"] == 0
        assert options["initial_target"].campaign == runner.UUID(run.campaign)
        return 0

    monkeypatch.setattr(runner, "drive_pair", drive)
    assert companion.drive(writer, reader, on_started=started) == 0
    assert (writer, reader) == originals and len(calls) == 1
