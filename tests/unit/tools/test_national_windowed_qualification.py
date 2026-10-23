"""Bounded private control transport and exact native action observations."""

from __future__ import annotations

import json
import socket
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal, cast

import pytest
from tools.devtools import national_game_memory as memory
from tools.devtools import national_windowed_qualification as windowed

CAMPAIGN = "81b979ee-a9c1-48fd-8835-06cbfe594675"


def state(tick: int = 0) -> dict[str, Any]:
    return {
        "campaign_id": CAMPAIGN,
        "scope_epoch": 7,
        "durable_tick": tick,
        "viewed_tick": tick,
        "generation": 1,
        "phase": "Ready",
        "foundation_sha256": "a" * 64,
        "tick_content_hash": None if tick == 0 else "b" * 64,
        "archive_verified_tick": tick,
        "advance_pending": False,
        "lifecycle_pending": False,
        "organizer_pending": False,
        "organizer_status_due": False,
        "organizer_period": tick,
        "choice": "remote_aid",
        "reviewed_command": None,
        "preview": None,
        "commitment": None,
        "quit_requested": False,
        "splash_visible": False,
        "menu_open": False,
        "opening_stage": "Game",
        "primary_view": "Organizer",
        "inspector": "Closed",
    }


def response(sequence: int, event: str = "observed", **changes: Any) -> bytes:
    fields = state()
    fields.update(changes)
    return (
        json.dumps(
            {"version": 2, "sequence": sequence, "event": event, "reason": None, "state": fields}
        ).encode()
        + b"\n"
    )


def test_transport_preserves_fragmented_frames_and_exact_preconditions() -> None:
    parent, peer = socket.socketpair()
    channel = windowed.ControlChannel(parent, CAMPAIGN, 0)
    requests: list[dict[str, Any]] = []

    def reply() -> None:
        with peer, peer.makefile("rb") as source:
            requests.append(json.loads(source.readline()))
            raw = response(1)
            peer.sendall(raw[:13])
            peer.sendall(raw[13:])
            requests.append(json.loads(source.readline()))
            peer.sendall(response(2, "applied", choice="local_aid"))

    worker = threading.Thread(target=reply)
    worker.start()
    try:
        assert channel.observe(1).durable_tick == 0
        assert channel.perform("choose_local_aid", 1).choice == "local_aid"
    finally:
        channel.close()
        worker.join(2)
    assert not worker.is_alive()
    assert requests[0] == {
        "version": 2,
        "sequence": 1,
        "campaign_id": CAMPAIGN,
        "scope_epoch": None,
        "expected_tick": 0,
        "expected_generation": 0,
        "action": "status",
    }
    assert requests[1]["sequence"] == 2
    assert requests[1]["scope_epoch"] == 7
    assert requests[1]["expected_generation"] == 1
    assert channel.records[-1].event == "applied"


def test_exact_reopen_is_the_only_admitted_runtime_epoch_transition() -> None:
    parent, peer = socket.socketpair()
    channel = windowed.ControlChannel(parent, CAMPAIGN, 1)
    requests: list[dict[str, Any]] = []

    def reply() -> None:
        with peer, peer.makefile("rb") as source:
            requests.append(json.loads(source.readline()))
            peer.sendall(
                response(
                    1,
                    durable_tick=1,
                    viewed_tick=1,
                    tick_content_hash="b" * 64,
                    archive_verified_tick=1,
                    organizer_period=1,
                )
            )
            requests.append(json.loads(source.readline()))
            peer.sendall(
                response(
                    2,
                    "reopened_and_installed",
                    scope_epoch=8,
                    generation=4,
                    durable_tick=1,
                    viewed_tick=1,
                    tick_content_hash="b" * 64,
                    archive_verified_tick=1,
                    organizer_period=1,
                )
            )
            requests.append(json.loads(source.readline()))
            peer.sendall(
                response(
                    3,
                    "committed_and_installed",
                    scope_epoch=8,
                    generation=5,
                    durable_tick=2,
                    viewed_tick=2,
                    tick_content_hash="c" * 64,
                )
            )

    worker = threading.Thread(target=reply)
    worker.start()
    try:
        channel.observe(1)
        restored = channel.perform("reopen", 1)
        assert (restored.scope_epoch, restored.durable_tick) == (8, 1)
        assert channel.perform("step", 1).durable_tick == 2
    finally:
        channel.close()
        worker.join(2)
    assert not worker.is_alive()
    assert requests[1]["action"] == "reopen"
    assert requests[1]["scope_epoch"] == 7
    assert requests[2]["scope_epoch"] == 8


@pytest.mark.parametrize(
    "changes",
    [
        {"scope_epoch": 9},
        {"scope_epoch": 7},
        {"generation": 1},
        {"durable_tick": 2, "viewed_tick": 2},
        {"tick_content_hash": "c" * 64},
        {"foundation_sha256": "c" * 64},
        {"phase": "Loading"},
        {"lifecycle_pending": True},
        {"organizer_pending": True},
        {"archive_verified_tick": 0},
    ],
)
def test_reopen_refuses_changed_or_incomplete_restored_identity(changes: dict[str, Any]) -> None:
    parent, peer = socket.socketpair()
    channel = windowed.ControlChannel(parent, CAMPAIGN, 1)
    peer.sendall(
        response(
            1,
            durable_tick=1,
            viewed_tick=1,
            tick_content_hash="b" * 64,
            archive_verified_tick=1,
            organizer_period=1,
        )
    )
    try:
        channel.observe(1)
        restored: dict[str, Any] = {
            "scope_epoch": 8,
            "generation": 4,
            "durable_tick": 1,
            "viewed_tick": 1,
            "tick_content_hash": "b" * 64,
            "archive_verified_tick": 1,
            "organizer_period": 1,
        }
        restored.update(changes)
        peer.sendall(response(2, "reopened_and_installed", **restored))
        with pytest.raises(windowed.ControlRefusal):
            channel.perform("reopen", 1)
        assert channel.closed
    finally:
        channel.close()
        peer.close()


@pytest.mark.parametrize(
    "raw",
    [
        response(2),
        response(1).replace(b'"version": 2', b'"version": 1'),
        response(1).replace(b'"version": 2', b'"version": true'),
        response(1).replace(b'"version": 2', b'"version": 2, "version": 2'),
        response(1, campaign_id="b4fcf361-af16-489f-83a6-3d9815a73844"),
        response(1, durable_tick=True),
        response(1, foundation_sha256="A" * 64),
        response(1).replace(b'"generation": 1', b'"generation": NaN'),
        b"x" * 32_768 + b"\n",
        response(1)[:-1],
        b"",
    ],
)
def test_invalid_peer_frame_cannot_become_action_evidence(raw: bytes) -> None:
    parent, peer = socket.socketpair()
    channel = windowed.ControlChannel(parent, CAMPAIGN, 0)
    peer.sendall(raw)
    peer.shutdown(socket.SHUT_WR)
    try:
        with pytest.raises(windowed.ControlRefusal):
            channel.observe(1)
        assert not channel.records
    finally:
        channel.close()
        peer.close()


def test_slow_fragments_cannot_reset_the_overall_response_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FragmentPeer:
        def __init__(self) -> None:
            self.clock = 0.0
            self.closed = False
            self.timeouts: list[float] = []
            self.fragments = iter(response(1))

        def settimeout(self, timeout: float) -> None:
            self.timeouts.append(timeout)

        def sendall(self, raw: bytes) -> None:
            assert json.loads(raw)["action"] == "status"

        def recv(self, maximum: int) -> bytes:
            assert maximum > 0
            self.clock += 0.02
            return bytes([next(self.fragments)])

        def close(self) -> None:
            self.closed = True

    peer = FragmentPeer()
    monkeypatch.setattr(windowed.time, "monotonic", lambda: peer.clock)
    channel = windowed.ControlChannel(cast(socket.socket, peer), CAMPAIGN, 0)
    with pytest.raises(windowed.ControlRefusal, match="deadline"):
        channel.observe(0.05)
    assert not channel.records
    assert peer.closed
    assert peer.timeouts == pytest.approx([0.05, 0.05, 0.03, 0.01])


def test_failed_evidence_write_still_closes_and_preserves_original_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, peer = socket.socketpair()
    channel = windowed.ControlChannel(parent, CAMPAIGN, 0)
    original = windowed.ControlRefusal("original response refusal")

    def refuse(*_args: Any) -> None:
        raise OSError("evidence directory unavailable")

    monkeypatch.setattr(windowed, "write_observations", refuse)
    try:
        with pytest.raises(BaseExceptionGroup) as failure:
            windowed.finish_observations(
                tmp_path / "controls.json", channel, "incomplete", original
            )
        assert failure.value.exceptions == (original, failure.value.exceptions[1])
        assert isinstance(failure.value.exceptions[1], OSError)
        assert channel.closed and parent.fileno() == -1
    finally:
        channel.close()
        peer.close()


def test_failed_mutation_is_not_retried_or_credited() -> None:
    parent, peer = socket.socketpair()
    channel = windowed.ControlChannel(parent, CAMPAIGN, 0)
    peer.sendall(response(1))
    channel.observe(1)
    peer.sendall(response(2, "refused").replace(b'"reason": null', b'"reason": "unavailable"'))
    try:
        with pytest.raises(windowed.ControlRefusal, match="refused"):
            channel.perform("step", 1)
        assert channel.records[-1].event == "refused"
        with pytest.raises(windowed.ControlRefusal, match="closed"):
            channel.perform("step", 1)
    finally:
        channel.close()
        peer.close()


def test_later_unsolicited_age_cannot_be_credited_to_our_step() -> None:
    parent, peer = socket.socketpair()
    channel = windowed.ControlChannel(parent, CAMPAIGN, 0)
    peer.sendall(response(1))
    channel.observe(1)
    peer.sendall(response(2, "committed_and_installed", durable_tick=2, tick_content_hash="b" * 64))
    try:
        with pytest.raises(windowed.ControlRefusal, match="period"):
            channel.perform("step", 1)
    finally:
        channel.close()
        peer.close()


def test_changed_foundation_cannot_be_credited() -> None:
    parent, peer = socket.socketpair()
    channel = windowed.ControlChannel(parent, CAMPAIGN, 0)
    peer.sendall(response(1))
    channel.observe(1)
    peer.sendall(response(2, foundation_sha256="c" * 64))
    try:
        with pytest.raises(windowed.ControlRefusal, match="foundation"):
            channel.observe(1)
    finally:
        channel.close()
        peer.close()


@pytest.mark.parametrize(
    ("action", "event", "before", "after"),
    [
        ("choose_local_aid", "applied", {}, {"choice": "remote_aid"}),
        ("review", "preview_admitted", {}, {"reviewed_command": None, "preview": {}}),
        (
            "confirm",
            "acceptance_admitted",
            {"reviewed_command": {"nonce": "original"}},
            {"commitment": {"command": {"nonce": "different"}}},
        ),
    ],
)
def test_handler_event_alone_cannot_credit_a_different_choice_or_command(
    action: windowed.Action, event: str, before: dict[str, Any], after: dict[str, Any]
) -> None:
    parent, peer = socket.socketpair()
    channel = windowed.ControlChannel(parent, CAMPAIGN, 0)
    peer.sendall(response(1, **before))
    channel.observe(1)
    peer.sendall(response(2, event, **after))
    try:
        with pytest.raises(windowed.ControlRefusal):
            channel.perform(action, 1)
    finally:
        channel.close()
        peer.close()


def test_transcript_is_atomic_observation_not_qualification(tmp_path: Path) -> None:
    parent, peer = socket.socketpair()
    channel = windowed.ControlChannel(parent, CAMPAIGN, 0)
    peer.sendall(response(1))
    try:
        channel.observe(1)
        destination = tmp_path / "native-controls.json"
        windowed.write_observations(destination, channel, "incomplete")
        saved = json.loads(destination.read_bytes())
        assert saved["status"] == "incomplete"
        assert saved["scope"] == "native_ui_actions_only_not_accounting_or_memory_qualification"
        assert saved["actions"][0]["action"] == "status"
        assert saved["campaign"] == CAMPAIGN
        assert not list(tmp_path.glob("*.partial"))
    finally:
        channel.close()
        peer.close()


def test_driver_uses_actual_owned_children_and_private_socket(tmp_path: Path) -> None:
    """Real subprocess/socket IO with stand-ins, never a window or game proof."""
    runtime = tmp_path / "runtime-standin"
    client = tmp_path / "client-standin"
    runtime.write_text(f"#!{sys.executable}\nimport sys\nsys.stdin.buffer.read()\n")
    client.write_text(
        f"#!{sys.executable}\n"
        "import json,socket,sys\n"
        "connection=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)\n"
        "connection.connect(sys.argv[sys.argv.index('--qualification-control')+1])\n"
        f"state={state()!r}\n"
        "with connection,connection.makefile('rb') as source:\n"
        "    admission=json.loads(source.readline())\n"
        f"    assert admission=={{'version':2,'campaign_id':{CAMPAIGN!r},'phase':'capture_ready'}}\n"
        f"    __import__('pathlib').Path({str(tmp_path / 'startup-admitted')!r}).write_text('admitted')\n"
        "    for line in source:\n"
        "        request=json.loads(line)\n"
        "        quitting=request['action']=='quit'\n"
        "        state['quit_requested']=quitting\n"
        "        reply={'version':2,'sequence':request['sequence'],'event':'quit_requested' if quitting else 'observed','reason':None,'state':state}\n"
        "        connection.sendall(json.dumps(reply).encode()+b'\\n')\n"
        "        if quitting: break\n"
    )
    runtime.chmod(0o700)
    client.chmod(0o700)
    processes: list[tuple[int, int]] = []
    boundaries: list[windowed.ControlState] = []
    capture_events: list[str] = []

    class Monitor:
        def check(self) -> None:
            pass

        def finish(self) -> None:
            capture_events.append("capture_finished_before_quit")

    def started(runtime: Any, client: Any) -> None:
        assert runtime.poll() is None and client.poll() is None
        processes.append((runtime.pid, client.pid))

    @contextmanager
    def capture_lifecycle(runtime: Any, client: Any) -> Any:
        # A real exact-child barrier, with subprocess stand-ins. This does not
        # supply PostgreSQL/marker admission or establish game qualification.
        with memory.OwnedNativePair(
            runtime,
            client,
            runtime_sha256=memory.executable_digest(Path(f"/proc/{runtime.pid}/exe")),
            client_sha256=memory.executable_digest(Path(f"/proc/{client.pid}/exe")),
        ) as scope:
            with scope.quiescent(timeout=2):
                capture_events.append("exact_pair_stopped")
            assert not (tmp_path / "startup-admitted").exists()
            yield Monitor()
            capture_events.append("scope_finished_before_reap")

    assert (
        windowed.drive_pair(
            runtime,
            client,
            tmp_path,
            {},
            {},
            defines_path=tmp_path / "unused-defines.toml",
            initial_target=windowed.launcher.OpenCampaignTarget(windowed.UUID(CAMPAIGN)),
            initial_tick=0,
            periods=0,
            directory=tmp_path,
            operation_timeout=2,
            on_started=started,
            on_boundary=boundaries.append,
            on_recovery=lambda _state: None,
            capture_lifecycle=capture_lifecycle,
        )
        == 0
    )
    assert len(processes) == len(boundaries) == 1
    assert (tmp_path / "startup-admitted").read_text() == "admitted"
    assert processes[0][0] != processes[0][1]
    assert capture_events == [
        "exact_pair_stopped",
        "capture_finished_before_quit",
        "scope_finished_before_reap",
    ]
    saved = json.loads((tmp_path / "native-controls.json").read_bytes())
    assert saved["status"] == "completed"
    assert saved["actions"][-1]["event"] == "quit_requested"
    assert saved["scope"] == "native_ui_actions_only_not_accounting_or_memory_qualification"


def test_failed_capture_stops_controls_before_another_request() -> None:
    parent, peer = socket.socketpair()
    failure = memory.CaptureRefusal("independent memory sampler refused")

    def refuse() -> None:
        raise failure

    channel = windowed.ControlChannel(parent, CAMPAIGN, 0, check_capture=refuse)
    try:
        with pytest.raises(memory.CaptureRefusal) as result:
            channel.perform("step", 1)
        assert result.value is failure
        assert channel.sequence == 0 and not channel.records
    finally:
        channel.close()
        peer.close()


def test_driver_reviews_and_confirms_the_three_period_aid_schedule(tmp_path: Path) -> None:
    """Control transport only; stand-ins cannot establish aid accounting."""
    runtime = tmp_path / "runtime-standin"
    client = tmp_path / "client-standin"
    runtime.write_text(f"#!{sys.executable}\nimport sys\nsys.stdin.buffer.read()\n")
    client.write_text(
        f"#!{sys.executable}\n"
        "import json,socket,sys\n"
        "connection=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)\n"
        "connection.connect(sys.argv[sys.argv.index('--qualification-control')+1])\n"
        f"state={state()!r}\n"
        "with connection,connection.makefile('rb') as source:\n"
        "    admission=json.loads(source.readline())\n"
        f"    assert admission=={{'version':2,'campaign_id':{CAMPAIGN!r},'phase':'capture_ready'}}\n"
        "    for line in source:\n"
        "        request=json.loads(line); action=request['action']; event='applied'\n"
        "        if action=='status': event='observed'\n"
        "        elif action=='open_direction': state['inspector']='Direction'\n"
        "        elif action.startswith('choose_'):\n"
        "            state['choice']=action.removeprefix('choose_'); state['inspector']='Closed'\n"
        "        elif action=='review':\n"
        "            state['reviewed_command']={'nonce':request['sequence'],'choice':state['choice']}\n"
        "            state['preview']={'refusal':None}; event='preview_admitted'\n"
        "        elif action=='confirm':\n"
        "            state['commitment']={'command':state['reviewed_command']}; event='acceptance_admitted'\n"
        "        elif action=='step':\n"
        "            state['durable_tick']+=1; state['generation']+=1\n"
        "            state['viewed_tick']=state['organizer_period']=state['archive_verified_tick']=state['durable_tick']\n"
        "            state['tick_content_hash']='b'*64; event='committed_and_installed'\n"
        "        elif action=='reopen':\n"
        "            state['scope_epoch']+=1; state['generation']+=3; event='reopened_and_installed'\n"
        "        elif action=='quit': state['quit_requested']=True; event='quit_requested'\n"
        "        reply={'version':2,'sequence':request['sequence'],'event':event,'reason':None,'state':state}\n"
        "        connection.sendall(json.dumps(reply).encode()+b'\\n')\n"
        "        if action=='quit': break\n"
    )
    runtime.chmod(0o700)
    client.chmod(0o700)
    boundaries: list[windowed.ControlState] = []
    recoveries: list[windowed.ControlState] = []
    plan = tuple(
        windowed.PlannedChoice(period=period, choice=choice)
        for period, choice in [(1, "remote_aid"), (2, "pause_standing"), (3, "local_aid")]
    )
    assert (
        windowed.drive_pair(
            runtime,
            client,
            tmp_path,
            {},
            {},
            defines_path=tmp_path / "unused-defines.toml",
            initial_target=windowed.launcher.OpenCampaignTarget(windowed.UUID(CAMPAIGN)),
            initial_tick=0,
            periods=3,
            directory=tmp_path,
            operation_timeout=2,
            on_started=lambda _runtime, _client: None,
            on_boundary=boundaries.append,
            on_recovery=recoveries.append,
            choices=plan,
        )
        == 0
    )
    assert [boundary.durable_tick for boundary in boundaries] == [0, 1, 2, 3]
    assert [(r.durable_tick, r.scope_epoch) for r in recoveries] == [(1, 8), (2, 9), (3, 10)]
    saved = json.loads((tmp_path / "native-controls.json").read_bytes())
    applied = [entry["action"] for entry in saved["actions"] if entry["action"] != "status"]
    assert applied == [
        "choose_remote_aid",
        "review",
        "confirm",
        "step",
        "reopen",
        "open_direction",
        "choose_pause_standing",
        "review",
        "confirm",
        "step",
        "reopen",
        "choose_local_aid",
        "review",
        "confirm",
        "step",
        "reopen",
        "quit",
    ]


@pytest.mark.parametrize("choice", ["pause_standing", "resume_standing"])
@pytest.mark.parametrize("selected_inspector", ["Closed", "Direction"])
def test_standing_choice_uses_the_acknowledged_inspector_state(
    choice: Literal["pause_standing", "resume_standing"], selected_inspector: str
) -> None:
    """The ordinary choice handler may already close its Direction inspector."""
    parent, peer = socket.socketpair()
    channel = windowed.ControlChannel(parent, CAMPAIGN, 1)
    fields = state(1)
    command = {"choice": choice, "nonce": 42}
    requested: list[str] = []

    def reply() -> None:
        with peer, peer.makefile("rb") as source:
            for line in source:
                request = json.loads(line)
                action = request["action"]
                requested.append(action)
                event, reason = "applied", None
                if action == "status":
                    event = "observed"
                elif action == "open_direction":
                    fields["inspector"] = "Direction"
                elif action == "choose_" + choice:
                    fields["choice"] = choice
                    fields["inspector"] = selected_inspector
                elif action == "close_inspector":
                    if fields["inspector"] == "Closed":
                        event, reason = "refused", "control_stale_or_unavailable"
                    else:
                        fields["inspector"] = "Closed"
                elif action == "review":
                    fields["reviewed_command"] = command
                    fields["preview"] = {"refusal": None}
                    event = "preview_admitted"
                elif action == "confirm":
                    fields["commitment"] = {"command": command}
                    event = "acceptance_admitted"
                else:
                    event, reason = "refused", "control_stale_or_unavailable"
                peer.sendall(
                    json.dumps(
                        {
                            "version": 2,
                            "sequence": request["sequence"],
                            "event": event,
                            "reason": reason,
                            "state": fields,
                        }
                    ).encode()
                    + b"\n"
                )

    worker = threading.Thread(target=reply)
    worker.start()
    try:
        channel.observe(1)
        windowed.submit_choice(channel, windowed.PlannedChoice(period=2, choice=choice), 1)
        assert channel.state is not None
        assert channel.state.commitment == {"command": command}
        assert all(record.event != "refused" for record in channel.records)
    finally:
        channel.close()
        worker.join(2)
    assert not worker.is_alive()
    assert requested == [
        "status",
        "open_direction",
        "choose_" + choice,
        *(["close_inspector"] if selected_inspector != "Closed" else []),
        "review",
        "confirm",
        "status",
    ]


def test_duplicate_choice_schedule_refuses_before_launch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    launched: list[object] = []
    monkeypatch.setattr(
        windowed.launcher, "run_pair", lambda *args, **_kwargs: launched.append(args)
    )
    entry = windowed.PlannedChoice(period=1, choice="remote_aid")
    with pytest.raises(windowed.ControlRefusal, match="schedule"):
        windowed.drive_pair(
            tmp_path / "runtime",
            tmp_path / "client",
            tmp_path,
            {},
            {},
            defines_path=tmp_path / "defines.toml",
            initial_target=windowed.launcher.OpenCampaignTarget(windowed.UUID(CAMPAIGN)),
            initial_tick=0,
            periods=1,
            directory=tmp_path,
            operation_timeout=2,
            on_started=lambda _runtime, _client: None,
            on_boundary=lambda _state: None,
            on_recovery=lambda _state: None,
            choices=(entry, entry),
        )
    assert not launched
