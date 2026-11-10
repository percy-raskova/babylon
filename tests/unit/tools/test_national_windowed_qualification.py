"""Bounded private control transport and exact native action observations."""

from __future__ import annotations

import json
import socket
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal, cast
from uuid import UUID

import pytest
from pydantic import ValidationError
from tools.devtools import national_game_memory as memory
from tools.devtools import national_windowed_qualification as windowed

CAMPAIGN = "81b979ee-a9c1-48fd-8835-06cbfe594675"


def state(tick: int = 0) -> dict[str, Any]:
    return {
        "campaign_id": CAMPAIGN,
        "scope_epoch": 7,
        "installed_organizer": None,
        "play_interlock": None,
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
        "focused_amount": None,
        "amount_text": None,
        "allocation_error": None,
        "collection_allocation": "none",
        "aid_allocation": {"aid": {"food_quantity": 1, "cash_micros": "0"}},
        "reviewed_command": None,
        "preview": None,
        "commitment": None,
        "quit_requested": False,
        "splash_visible": False,
        "menu_open": False,
        "opening_stage": "Game",
        "primary_view": "Organizer",
        "inspector": "Closed",
        "playing": False,
        "periods_per_second": 1.0,
        "perspective": "PlayerKnowledge",
        "world_hash": None if tick == 0 else "c" * 64,
        "selected_subject": None,
        "menu_page": "Home",
        "selected_report_id": None,
        "selected_report_observed_period": None,
        "selected_report_acquired_period": None,
        "larger_interface": False,
        "road_layer": "EconomyNetwork",
        "network_sector": "All",
        "selected_county": "26163",
        "selected_site": None,
        "production_details_open": False,
        "production_reading": None,
    }


def admission_fields(
    choice: str | dict[str, str],
    period: int,
    nonce: int = 42,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    # An explicit Designed command for the socket stand-ins. Frozen producer
    # bytes below separately exercise the real Rust shapes.
    allocation = (
        {"aid": {"food_quantity": 1, "cash_micros": "0"}}
        if choice in ("remote_aid", "local_aid")
        else "none"
    )
    command = {
        "choice": choice,
        "allocation": allocation,
        "nonce": [nonce] * 16,
        "campaign_id": list(UUID(CAMPAIGN).bytes),
        "authority_id": [2] * 16,
        "actor_id": 101,
        "expected_period": period,
        "content_digest": [3] * 32,
        "resource_digest": [4] * 32,
    }
    preview = {
        "choice": choice,
        "allocation": allocation,
        "current_period": period,
        "resolves_period": period + 1,
        "available_hours": 4,
        "required_hours": 2,
        "replaces_standing_work": True,
        "refusal": None,
        "observations": [],
    }
    commitment = {"command": command, "commitment_id": [nonce] * 32, "resolves_period": period + 1}
    return command, preview, commitment


def response(sequence: int, event: str = "observed", **changes: Any) -> bytes:
    fields = state()
    fields.update(changes)
    return (
        json.dumps(
            {"version": 4, "sequence": sequence, "event": event, "reason": None, "state": fields}
        ).encode()
        + b"\n"
    )


def installed_opening_view() -> dict[str, Any]:
    return {
        "period": 0,
        "actor_id": 1,
        "authority_id": [1] * 16,
        "content_digest": [1] * 32,
        "resource_digest": [2] * 32,
        "standing": {"authorized": True, "partner_actor_id": 10, "paused_reason": None},
        "available_hours": 2,
        "contact_hours": 0,
        "hold_reviewable": True,
        "pause_reviewable": True,
        "resume_reviewable": False,
        "pending_freight": [],
        "aid_response_history": [],
    }


def test_cold_endpoint_retains_its_actual_ready_poll_after_an_identical_state() -> None:
    sock, peer = socket.socketpair()
    with sock, peer:
        channel = windowed.ControlChannel(sock, CAMPAIGN, 0)
        view = installed_opening_view()
        peer.sendall(response(1, installed_organizer=view))
        first = channel.observe(1)
        peer.sendall(response(2, installed_organizer=view))
        installed = windowed.wait_ready(channel, 1, organizer=True, cold=True)
        assert installed == first
        assert [(r.sequence, r.action, r.event) for r in channel.records] == [
            (1, "status", "observed"),
            (2, "status", "observed"),
        ]


def test_operator_controls_have_a_distinct_completed_frame_event() -> None:
    from typing import get_args

    actions = set(get_args(windowed.UnitAction))
    assert {
        "inspect_practices",
        "inspect_receipts",
        "open_relationships",
        "archive_workplace",
        "open_archive_evidence",
        "previous_period",
        "return_live",
        "capture_frame",
        "scene_places",
        "scene_relationships",
        "select_workplace_committee",
        "select_neighborhood_group",
        "inspect_evidence",
        "next_evidence",
        "previous_evidence",
        "archive_organization",
        "resize1366x768",
        "resize1920x1080",
    } <= actions
    assert "capture_desktop" not in actions
    assert windowed.EXPECTED["capture_frame"] == "frame_captured"
    assert "frame_captured" in get_args(windowed.Event)


@pytest.mark.parametrize(
    "action",
    [
        "open_relationships",
        "open_archive_evidence",
        "scene_places",
        "scene_relationships",
        "select_workplace_committee",
        "select_neighborhood_group",
        "inspect_evidence",
        "next_evidence",
        "previous_evidence",
        "archive_organization",
        "resize1366x768",
        "resize1920x1080",
    ],
)
def test_private_control_sends_the_bounded_action(action: windowed.Action) -> None:
    parent, peer = socket.socketpair()
    channel = windowed.ControlChannel(parent, CAMPAIGN, 0)
    requests: list[dict[str, Any]] = []

    def reply() -> None:
        with peer, peer.makefile("rb") as source:
            line = source.readline()
            if line:
                requests.append(json.loads(line))
                peer.sendall(
                    response(requests[0]["sequence"], "applied", inspector="Relationships")
                )

    worker = threading.Thread(target=reply)
    worker.start()
    try:
        assert channel.perform(action, 5).inspector == "Relationships"
    finally:
        channel.close()
        worker.join(timeout=5)
    assert not worker.is_alive()
    assert requests[0]["action"] == action
    assert requests[0]["campaign_id"] == CAMPAIGN


@pytest.mark.parametrize("event", ["applied", "frame_captured"])
def test_capture_frame_requires_completed_event(event: str) -> None:
    parent, peer = socket.socketpair()
    channel = windowed.ControlChannel(parent, CAMPAIGN, 0)

    def reply() -> None:
        with peer, peer.makefile("rb") as source:
            request = json.loads(source.readline())
            assert request["action"] == "capture_frame"
            peer.sendall(response(request["sequence"], event))

    worker = threading.Thread(target=reply)
    worker.start()
    try:
        if event == "frame_captured":
            assert channel.perform("capture_frame", 5).campaign_id == CAMPAIGN
        else:
            with pytest.raises(windowed.ControlRefusal):
                channel.perform("capture_frame", 5)
    finally:
        channel.close()
        worker.join(timeout=5)
    assert not worker.is_alive()


def test_capture_refusal_preserves_specific_reason_and_trace() -> None:
    parent, peer = socket.socketpair()
    channel = windowed.ControlChannel(parent, CAMPAIGN, 0)

    def reply() -> None:
        with peer, peer.makefile("rb") as source:
            request = json.loads(source.readline())
            fields = state()
            peer.sendall(
                json.dumps(
                    {
                        "version": 4,
                        "sequence": request["sequence"],
                        "event": "refused",
                        "reason": "capture_image_invalid",
                        "state": fields,
                    }
                ).encode()
                + b"\n"
            )

    worker = threading.Thread(target=reply)
    worker.start()
    try:
        with pytest.raises(windowed.ControlRefusal, match="capture_image_invalid"):
            channel.perform("capture_frame", 5)
        assert channel.records[-1].reason == "capture_image_invalid"
    finally:
        channel.close()
        worker.join(timeout=5)


@pytest.mark.parametrize("inquiry", ["work_lost", "maintenance_received"])
def test_native_inquiry_choice_wire_is_accepted(inquiry: str) -> None:
    fields = state()
    fields["choice"] = {"inquiry": inquiry}
    parsed = windowed.ControlState.model_validate(fields)
    assert parsed.model_dump()["choice"] == {"inquiry": inquiry}


@pytest.mark.parametrize(
    "choice",
    [
        "collect",
        "local_aid",
        "remote_aid",
        "reinforce",
        "hold",
        "pause_standing",
        "resume_standing",
    ],
)
def test_native_unit_choice_wire_is_accepted(choice: str) -> None:
    fields = state()
    fields["choice"] = choice
    assert windowed.ControlState.model_validate(fields).choice == choice


@pytest.mark.parametrize(
    "choice",
    [
        "inquiry_work_lost",
        "unknown",
        True,
        None,
        {},
        {"inquiry": True},
        {"inquiry": "unknown"},
        {"inquiry": "work_lost", "extra": 1},
        {"other": "work_lost"},
        ["work_lost"],
    ],
)
def test_native_choice_wire_rejects_unknown_shapes(choice: Any) -> None:
    fields = state()
    fields["choice"] = choice
    with pytest.raises(ValidationError):
        windowed.ControlState.model_validate(fields)


@pytest.mark.parametrize(
    ("choice", "wire"),
    [
        ("inquiry_work_lost", {"inquiry": "work_lost"}),
        ("inquiry_maintenance_received", {"inquiry": "maintenance_received"}),
        ("reinforce", "reinforce"),
        ("hold", "hold"),
    ],
)
@pytest.mark.parametrize("mismatched", [False, True])
def test_new_choice_reviews_confirms_and_checks_exact_readback(
    choice: str, wire: Any, mismatched: bool
) -> None:
    parent, peer = socket.socketpair()
    channel = windowed.ControlChannel(parent, CAMPAIGN, 0)
    fields = state()
    command, preview, commitment = admission_fields(wire, 0)
    requested: list[str] = []

    def reply() -> None:
        with peer, peer.makefile("rb") as source:
            for line in source:
                action = json.loads(line)["action"]
                requested.append(action)
                event = "applied"
                if action == "status":
                    event = "observed"
                elif action == "inspect_practices":
                    fields["inspector"] = "Practices"
                elif action == "choose_" + choice:
                    assert fields["inspector"] == "Practices"
                    fields["inspector"] = "Closed"
                    fields["choice"] = "collect" if mismatched else wire
                elif action == "review":
                    fields["reviewed_command"] = command
                    fields["preview"] = preview
                    event = "preview_admitted"
                elif action == "confirm":
                    fields["commitment"] = commitment
                    fields["reviewed_command"] = fields["preview"] = None
                    event = "acceptance_admitted"
                peer.sendall(
                    json.dumps(
                        {
                            "version": 4,
                            "sequence": len(requested),
                            "event": event,
                            "reason": None,
                            "state": fields,
                        }
                    ).encode()
                    + b"\n"
                )

    worker = threading.Thread(target=reply)
    worker.start()
    try:
        channel.observe(1)
        planned = windowed.PlannedChoice.model_validate(
            {"period": 1, "choice": choice, "allocation": "none"}
        )
        if mismatched:
            with pytest.raises(windowed.ControlRefusal, match="different choice"):
                windowed.submit_choice(channel, planned, 1)
        else:
            windowed.submit_choice(channel, planned, 1)
            assert (
                channel.state is not None
                and channel.state.commitment == windowed.Commitment.model_validate(commitment)
            )
    finally:
        channel.close()
        worker.join(2)
    assert not worker.is_alive()
    assert requested == ["status", "inspect_practices", "choose_" + choice] + (
        [] if mismatched else ["review", "confirm", "status"]
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
        "version": 4,
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
        response(1).replace(b'"version": 4', b'"version": 1'),
        response(1).replace(b'"version": 4', b'"version": true'),
        response(1).replace(b'"version": 4', b'"version": 4, "version": 4'),
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


@pytest.mark.parametrize(
    ("initial_phase", "organizer", "outcome", "warning_visible", "menu_open"),
    [
        ("Loading", False, "ready", True, False),
        ("Ready", False, "ready", True, False),
        ("Loading", False, "refused", True, False),
        ("Loading", False, "late", True, False),
        ("Loading", True, "ready", True, False),
        ("Ready", True, "ready", True, False),
        ("Ready", False, "ready", False, False),
        ("Ready", False, "ready", False, True),
    ],
)
def test_opening_warning_uses_fresh_scoped_loading_status(
    monkeypatch: pytest.MonkeyPatch,
    initial_phase: str,
    organizer: bool,
    outcome: str,
    warning_visible: bool,
    menu_open: bool,
) -> None:
    clock = [100.0]
    monkeypatch.setattr(windowed.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(windowed.time, "monotonic_ns", lambda: int(clock[0] * 1e9))
    monkeypatch.setattr(
        windowed.time, "sleep", lambda delay: clock.__setitem__(0, clock[0] + delay)
    )

    class OpeningPeer:
        def __init__(self) -> None:
            self.requests: list[dict[str, Any]] = []
            self.timeouts: list[tuple[float, float]] = []
            self.reply = b""
            self.statuses = 0
            self.continued = False
            self.closed = False

        def settimeout(self, timeout: float) -> None:
            self.timeouts.append((clock[0], timeout))

        def sendall(self, frame: bytes) -> None:
            request = json.loads(frame)
            self.requests.append(request)
            fields = state()
            fields.update(
                phase="Loading",
                foundation_sha256=None,
                lifecycle_pending=True,
                organizer_period=None,
                splash_visible=warning_visible,
                menu_open=menu_open,
                opening_stage="Warning",
                generation=3,
            )
            event, reason = "observed", None
            if request["action"] == "status":
                self.statuses += 1
                if self.statuses == 1:
                    fields.update(scope_epoch=None, generation=0)
                elif self.statuses == 2:
                    event, reason = "refused", "control_stale_or_unavailable"
                    if initial_phase == "Ready":
                        fields = state() | {
                            "generation": 3,
                            "splash_visible": warning_visible,
                            "menu_open": menu_open,
                            "opening_stage": "Warning",
                        }
                else:
                    # Ready arrives independently of clearing the warning.
                    fields = state() | {
                        "generation": 4,
                        "splash_visible": warning_visible,
                        "menu_open": menu_open,
                        "opening_stage": "Title" if self.continued else "Warning",
                    }
            else:
                assert request["action"] == "continue_warning"
                event = "refused" if outcome == "refused" else "applied"
                reason = "control_stale_or_unavailable" if outcome == "refused" else None
                self.continued = outcome != "refused"
                if initial_phase == "Ready":
                    fields = state() | {"generation": 3, "splash_visible": True}
                fields["opening_stage"] = "Production" if self.continued else "Warning"
            clock[0] += 10 if outcome == "late" and request["action"] == "continue_warning" else 0.1
            self.reply = (
                json.dumps(
                    {
                        "version": 4,
                        "sequence": request["sequence"],
                        "event": event,
                        "reason": reason,
                        "state": fields,
                    }
                ).encode()
                + b"\n"
            )

        def recv(self, size: int) -> bytes:
            part, self.reply = self.reply[:size], self.reply[size:]
            return part

        def close(self) -> None:
            self.closed = True

    peer = OpeningPeer()
    channel = windowed.ControlChannel(cast(socket.socket, peer), CAMPAIGN, 0)
    try:
        if outcome == "ready":
            ready = windowed.wait_ready(channel, 1, organizer=organizer)
            assert ready.phase == "Ready"
            if organizer or not warning_visible:
                assert ready.opening_stage == "Warning"
                assert all(row["action"] == "status" for row in peer.requests)
            elif initial_phase == "Loading":
                assert ready.opening_stage == "Title"
                assert [row["action"] for row in peer.requests] == [
                    "status",
                    "status",
                    "continue_warning",
                    "status",
                ]
                assert channel.records[2].state.phase == "Loading"
                assert channel.records[3].state.phase == "Ready"
            else:
                assert ready.opening_stage == "Production"
                assert [row["action"] for row in peer.requests] == [
                    "status",
                    "status",
                    "continue_warning",
                ]
        else:
            with pytest.raises(windowed.ControlRefusal) as failed:
                windowed.wait_ready(channel, 1, organizer=organizer)
            assert [row["action"] for row in peer.requests] == [
                "status",
                "status",
                "continue_warning",
            ]
            assert peer.closed and not channel.ready
            assert (
                failed.value.reason
                == {
                    "late": "response_deadline",
                    "refused": "control_refused",
                }[outcome]
            )
        if not organizer and warning_visible:
            continued = peer.requests[2]
            assert continued["campaign_id"] == CAMPAIGN
            assert (
                continued["scope_epoch"],
                continued["expected_tick"],
                continued["expected_generation"],
            ) == (7, 0, 3)
        assert peer.requests[0]["scope_epoch"] is None
        assert peer.requests[1]["scope_epoch"] is None
        assert [at + timeout for at, timeout in peer.timeouts] == pytest.approx(
            [101.0] * len(peer.timeouts)
        )
    finally:
        channel.close()


def test_listener_bind_failure_is_diagnosed_before_first_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = PermissionError("private transport detail")
    seen: list[dict[str, Any] | None] = []

    class Listener(socket.socket):
        def bind(self, _address: str) -> None:
            raise original

        def close(self) -> None:
            path = tmp_path / "native-control-failure.json"
            seen.append(json.loads(path.read_bytes()) if path.is_file() else None)
            super().close()

    monkeypatch.setattr(windowed.socket, "socket", Listener)
    with pytest.raises(PermissionError) as failed:
        windowed.drive_pair(
            tmp_path / "runtime",
            tmp_path / "client",
            tmp_path,
            {},
            {},
            defines_path=tmp_path / "defines",
            initial_target=windowed.launcher.OpenCampaignTarget(UUID(CAMPAIGN)),
            initial_tick=0,
            periods=0,
            directory=tmp_path,
            operation_timeout=2,
            on_started=lambda *_args: None,
            on_boundary=lambda _state: None,
            on_recovery=lambda _state: None,
            cold_window=windowed.ColdControlWindow(time.monotonic_ns(), 180),
        )
    assert failed.value is original
    assert len(seen) == 1 and seen[0] is not None
    assert (seen[0]["phase"], seen[0]["reason"]) == ("socket_admission", "transport_error")
    assert "private transport detail" not in json.dumps(seen[0])


def first_reply_standins(tmp_path: Path) -> tuple[Path, Path]:
    runtime = tmp_path / "runtime"
    client = tmp_path / "client"
    runtime.write_text(f"#!{sys.executable}\nimport sys\nsys.stdin.buffer.read()\n")
    client.write_text(
        f"#!{sys.executable}\nimport sys,socket\n"
        "s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)\n"
        "s.connect(sys.argv[sys.argv.index('--qualification-control')+1])\n"
        "r=s.makefile('rb'); r.readline(); r.readline(); s.close()\n"
    )
    runtime.chmod(0o700)
    client.chmod(0o700)
    return runtime, client


@pytest.mark.parametrize("phase", ["socket_admission", "initial_readiness"])
def test_real_smoke_budget_refusal_keeps_wall_diagnosis_and_divergence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    from tools.devtools import national_native_runner as runner

    run = object.__new__(runner.NativeRun)
    run.directory = tmp_path
    run.mode = "normal_play"
    run.wayne_profile = "smoke-01"
    diagnoses: list[dict[str, Any] | None] = []
    refusals: list[runner.NativeRunRefusal] = []

    def expired() -> None:
        path = tmp_path / "native-control-failure.json"
        diagnoses.append(json.loads(path.read_bytes()) if path.is_file() else None)
        try:
            run.check_budget("smoke-wall", 900_000_000_000, 900, None, strict=True)
        except runner.NativeRunRefusal as error:
            refusals.append(error)
            raise

    runtime, client = first_reply_standins(tmp_path)
    start = time.monotonic_ns()
    wall = start / 1e9
    if phase == "initial_readiness":
        wall += 900
        receive = windowed.ControlChannel._receive

        def expire_on_first_reply(channel: windowed.ControlChannel, deadline: float):
            with monkeypatch.context() as clock:
                clock.setattr(windowed.time, "monotonic", lambda: wall)
                return receive(channel, deadline)

        monkeypatch.setattr(windowed.ControlChannel, "_receive", expire_on_first_reply)
    with pytest.raises(runner.NativeRunRefusal) as failed:
        windowed.drive_pair(
            runtime,
            client,
            tmp_path,
            {},
            {},
            defines_path=tmp_path / "defines",
            initial_target=windowed.launcher.OpenCampaignTarget(UUID(CAMPAIGN)),
            initial_tick=0,
            periods=0,
            directory=tmp_path,
            operation_timeout=2,
            on_started=lambda *_args: None,
            on_boundary=lambda _state: None,
            on_recovery=lambda _state: None,
            cold_window=windowed.ColdControlWindow(start, 180),
            wall_deadline=wall,
            on_wall_expired=expired,
        )
    assert refusals == [failed.value]
    divergence = json.loads((tmp_path / "first-budget-divergence.json").read_bytes())
    assert (
        divergence["stage"] == "smoke-wall" and divergence["elapsed_ns"] == divergence["ceiling_ns"]
    )
    final = json.loads((tmp_path / "native-control-failure.json").read_bytes())
    assert final["reason"] == "wall_deadline" and final["phase"] == phase
    assert diagnoses == [final]


def test_cold_first_reply_failure_is_private_and_precedes_capture_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started_ns = time.monotonic_ns()
    runtime, client = first_reply_standins(tmp_path)
    seen = []
    diagnosis_before_close: list[bool] = []
    original_close = windowed.ControlChannel.close

    def close(channel: windowed.ControlChannel) -> None:
        diagnosis_before_close.append((tmp_path / "native-control-failure.json").is_file())
        original_close(channel)

    monkeypatch.setattr(windowed.ControlChannel, "close", close)

    @contextmanager
    def monitor(*_children):
        try:
            yield None
        finally:
            path = tmp_path / "native-control-failure.json"
            seen.append(json.loads(path.read_bytes()))
            assert path.stat().st_mode & 0o077 == 0

    with pytest.raises(windowed.ControlRefusal):
        windowed.drive_pair(
            runtime,
            client,
            tmp_path,
            {},
            {},
            defines_path=tmp_path / "d",
            initial_target=windowed.launcher.OpenCampaignTarget(windowed.UUID(CAMPAIGN)),
            initial_tick=0,
            periods=0,
            directory=tmp_path,
            operation_timeout=2,
            on_started=lambda *_args: None,
            on_boundary=lambda _state: None,
            on_recovery=lambda _state: None,
            capture_lifecycle=monitor,
            cold_window=windowed.ColdControlWindow(started_ns, 180),
        )
    assert diagnosis_before_close and all(diagnosis_before_close)
    assert len(seen) == 1
    failed = seen[0]
    assert failed.pop("failed_monotonic_ns") >= started_ns
    assert failed == {
        "version": 1,
        "phase": "initial_readiness",
        "reason": "response_ended",
        "cold_started_monotonic_ns": started_ns,
        "cold_deadline_monotonic_ns": started_ns + 180_000_000_000,
    }


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
            {
                "reviewed_command": admission_fields("local_aid", 0)[0],
                "preview": admission_fields("local_aid", 0)[1],
            },
            {"commitment": admission_fields("local_aid", 0, nonce=43)[2]},
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
        f"    assert admission=={{'version':4,'campaign_id':{CAMPAIGN!r},'phase':'capture_ready'}}\n"
        f"    __import__('pathlib').Path({str(tmp_path / 'startup-admitted')!r}).write_text('admitted')\n"
        "    for line in source:\n"
        "        request=json.loads(line)\n"
        "        quitting=request['action']=='quit'\n"
        "        state['quit_requested']=quitting\n"
        "        reply={'version':4,'sequence':request['sequence'],'event':'quit_requested' if quitting else 'observed','reason':None,'state':state}\n"
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
    admissions = [
        admission_fields("remote_aid", 0),
        admission_fields("pause_standing", 1),
        admission_fields("local_aid", 2),
    ]
    client.write_text(
        f"#!{sys.executable}\n"
        "import json,socket,sys\n"
        "connection=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)\n"
        "connection.connect(sys.argv[sys.argv.index('--qualification-control')+1])\n"
        f"state={state()!r}\nadmissions={admissions!r}\n"
        "with connection,connection.makefile('rb') as source:\n"
        "    admission=json.loads(source.readline())\n"
        f"    assert admission=={{'version':4,'campaign_id':{CAMPAIGN!r},'phase':'capture_ready'}}\n"
        "    for line in source:\n"
        "        request=json.loads(line); action=request['action']; event='applied'\n"
        "        if action=='status': event='observed'\n"
        "        elif action=='open_direction': state['inspector']='Direction'\n"
        "        elif action=='inspect_practices': state['inspector']='Practices'\n"
        "        elif action.startswith('choose_'):\n"
        "            assert state['inspector'] in ('Direction', 'Practices')\n"
        "            state['choice']=action.removeprefix('choose_'); state['inspector']='Closed'\n"
        "        elif action=='review':\n"
        "            state['reviewed_command'],state['preview'],accepted=admissions[state['durable_tick']]\n"
        "            event='preview_admitted'\n"
        "        elif action=='confirm':\n"
        "            state['commitment']=accepted; state['reviewed_command']=state['preview']=None; event='acceptance_admitted'\n"
        "        elif action=='step':\n"
        "            state['durable_tick']+=1; state['generation']+=1\n"
        "            state['viewed_tick']=state['organizer_period']=state['archive_verified_tick']=state['durable_tick']\n"
        "            state['tick_content_hash']='b'*64; event='committed_and_installed'\n"
        "        elif action=='reopen':\n"
        "            state['scope_epoch']+=1; state['generation']+=3; event='reopened_and_installed'\n"
        "        elif action=='quit': state['quit_requested']=True; event='quit_requested'\n"
        "        reply={'version':4,'sequence':request['sequence'],'event':event,'reason':None,'state':state}\n"
        "        connection.sendall(json.dumps(reply).encode()+b'\\n')\n"
        "        if action=='quit': break\n"
    )
    runtime.chmod(0o700)
    client.chmod(0o700)
    boundaries: list[windowed.ControlState] = []
    recoveries: list[windowed.ControlState] = []
    plan = tuple(
        windowed.PlannedChoice.model_validate(
            {
                "period": period,
                "choice": choice,
                "allocation": admission_fields(choice, period - 1)[0]["allocation"],
            }
        )
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
        "inspect_practices",
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
        "inspect_practices",
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
    command, preview, commitment = admission_fields(choice, 1)
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
                    fields["preview"] = preview
                    event = "preview_admitted"
                elif action == "confirm":
                    fields["commitment"] = commitment
                    fields["reviewed_command"] = fields["preview"] = None
                    event = "acceptance_admitted"
                else:
                    event, reason = "refused", "control_stale_or_unavailable"
                peer.sendall(
                    json.dumps(
                        {
                            "version": 4,
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
        windowed.submit_choice(
            channel, windowed.PlannedChoice(period=2, choice=choice, allocation="none"), 1
        )
        assert channel.state is not None
        assert channel.state.commitment == windowed.Commitment.model_validate(commitment)
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
    entry = windowed.PlannedChoice.model_validate(
        {
            "period": 1,
            "choice": "remote_aid",
            "allocation": admission_fields("remote_aid", 0)[0]["allocation"],
        }
    )
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


def test_automatic_progress_requires_admitted_playback_and_settles_once() -> None:
    parent, peer = socket.socketpair()
    channel = windowed.ControlChannel(parent, CAMPAIGN, 0)
    try:
        peer.sendall(response(1))
        channel.observe(1)
        peer.sendall(response(2, "applied", playing=True))
        channel.perform("play", 1)
        peer.sendall(
            response(
                3,
                durable_tick=1,
                viewed_tick=1,
                generation=2,
                organizer_period=1,
                playing=True,
                tick_content_hash="b" * 64,
                world_hash="c" * 64,
            )
        )
        assert channel.observe(1).durable_tick == 1
        peer.sendall(
            response(
                4,
                "applied",
                durable_tick=1,
                viewed_tick=1,
                generation=2,
                organizer_period=1,
                playing=False,
                advance_pending=True,
                tick_content_hash="b" * 64,
                world_hash="c" * 64,
            )
        )
        channel.perform("pause", 1)
        peer.sendall(
            response(
                5,
                durable_tick=2,
                viewed_tick=2,
                generation=3,
                organizer_period=2,
                tick_content_hash="d" * 64,
                world_hash="e" * 64,
            )
        )
        assert channel.observe(1).durable_tick == 2
        peer.sendall(
            response(
                6,
                durable_tick=3,
                viewed_tick=3,
                generation=4,
                organizer_period=3,
                tick_content_hash="f" * 64,
                world_hash="0" * 64,
            )
        )
        with pytest.raises(windowed.ControlRefusal, match="period"):
            channel.observe(1)
    finally:
        channel.close()
        peer.close()


@pytest.mark.parametrize(
    "changes",
    [
        {"campaign_id": "b56caf73-d034-491c-a837-901fa40b1577"},
        {"scope_epoch": 8},
        {"foundation_sha256": "d" * 64},
        {"tick_content_hash": "d" * 64},
        {"world_hash": "e" * 64},
        {"generation": 0},
    ],
)
def test_playback_keeps_campaign_scope_and_stationary_identity(changes: dict[str, Any]) -> None:
    parent, peer = socket.socketpair()
    channel = windowed.ControlChannel(parent, CAMPAIGN, 1)
    try:
        peer.sendall(response(1, **state(1)))
        channel.observe(1)
        peer.sendall(response(2, "applied", **(state(1) | {"playing": True})))
        channel.perform("play", 1)
        peer.sendall(response(3, **(state(1) | {"playing": True} | changes)))
        with pytest.raises(windowed.ControlRefusal):
            channel.observe(1)
    finally:
        channel.close()
        peer.close()


@pytest.mark.parametrize("delta", [0, 1, 2])
def test_paused_manual_step_keeps_its_exact_single_period_contract(delta: int) -> None:
    parent, peer = socket.socketpair()
    channel = windowed.ControlChannel(parent, CAMPAIGN, 1)
    try:
        peer.sendall(response(1, **state(1)))
        channel.observe(1)
        peer.sendall(response(2, "committed_and_installed", **state(1 + delta)))
        if delta == 1:
            assert channel.perform("step", 1).durable_tick == 2
        else:
            with pytest.raises(windowed.ControlRefusal, match="period"):
                channel.perform("step", 1)
    finally:
        channel.close()
        peer.close()


def test_stationary_inspection_cannot_credit_automatic_progress() -> None:
    parent, peer = socket.socketpair()
    channel = windowed.ControlChannel(parent, CAMPAIGN, 0)
    try:
        peer.sendall(response(1))
        channel.observe(1)
        peer.sendall(response(2, "applied", playing=True))
        channel.perform("play", 1)
        peer.sendall(response(3, "applied", **state(1)))
        with pytest.raises(windowed.ControlRefusal, match="period"):
            channel.perform("inspect_evidence", 1)
    finally:
        channel.close()
        peer.close()


@pytest.mark.parametrize(
    "action",
    [
        windowed.FocusAmount(focus_amount="cash"),
        windowed.AmountKey(amount_key="home"),
        windowed.AmountKey(amount_key=windowed.CharacterKey(character="3")),
        windowed.SelectAidPartner(select_aid_partner="remote"),
    ],
)
def test_tagged_action_socket_encodes_exact_variant_and_records_it(
    action: windowed.FocusAmount | windowed.AmountKey | windowed.SelectAidPartner,
) -> None:
    parent, peer = socket.socketpair()
    channel = windowed.ControlChannel(parent, CAMPAIGN, 0)
    try:
        with peer, peer.makefile("rb") as reader:
            with pytest.raises(windowed.ControlRefusal):
                channel.perform(cast("windowed.Action", "unknown"), 1)
            peer.sendall(response(1, event="applied"))
            channel.perform(action, 1)
            sent = json.loads(reader.readline())
            assert sent["sequence"] == 1
            assert sent["action"] == action.model_dump(mode="json")
            assert channel.records[-1].action == action
    finally:
        channel.close()


OrganizerChannel = tuple[windowed.ControlChannel, socket.socket]


@pytest.fixture
def organizer_channel() -> Iterator[OrganizerChannel]:
    local, peer = socket.socketpair()
    channel = windowed.ControlChannel(local, CAMPAIGN, 0)
    with peer:
        try:
            yield channel, peer
        finally:
            channel.close()


@pytest.mark.parametrize("choice", ["local_aid", "collect"])
@pytest.mark.parametrize(
    "fault", ["matching", "changed_amount", "changed_choice", "invalid_edit", "missing_slot"]
)
def test_review_matches_prior_applicable_selection(
    organizer_channel: OrganizerChannel, choice: str, fault: str
) -> None:
    channel, peer = organizer_channel
    # Both persisted slots exist independently of the selected practice.
    selected = state()
    selected.update(
        choice=choice, collection_allocation={"collection": {"target_cash_micros": "280000000"}}
    )
    applicable = "collection_allocation" if choice == "collect" else "aid_allocation"
    receipt_choice = "remote_aid" if fault == "changed_choice" else choice
    command, preview, _ = admission_fields(receipt_choice, 0)
    if receipt_choice == "collect":
        allocation = {
            "collection": {
                "target_cash_micros": "290000000" if fault == "changed_amount" else "280000000"
            }
        }
    else:
        allocation = {
            "aid": {"food_quantity": 2 if fault == "changed_amount" else 1, "cash_micros": "0"}
        }
    command["allocation"] = preview["allocation"] = allocation
    receipt_slot = "collection_allocation" if receipt_choice == "collect" else "aid_allocation"
    reviewed = {
        **selected,
        "choice": receipt_choice,
        receipt_slot: allocation,
        "reviewed_command": command,
        "preview": preview,
    }
    if fault == "invalid_edit":
        selected.update(
            focused_amount="contribution" if choice == "collect" else "food",
            amount_text="1-",
            allocation_error="invalid quantity",
        )
    if fault == "missing_slot":
        selected[applicable] = None
    peer.sendall(response(1, **selected))
    channel.observe(1)
    peer.sendall(response(2, "preview_admitted", **reviewed))
    if fault == "matching":
        assert channel.perform("review", 1).reviewed_command == windowed.Command.model_validate(
            command
        )
    else:
        with pytest.raises(windowed.ControlRefusal):
            channel.perform("review", 1)
        assert channel.sequence == (1 if fault in ("invalid_edit", "missing_slot") else 2)


@pytest.mark.parametrize(
    "fault",
    [
        "status_only",
        "changed_then_restored",
        "generation",
        "cleared_review",
        "consumed",
        "matching",
    ],
)
def test_only_witnessed_unchanged_review_can_send_confirm(
    organizer_channel: OrganizerChannel, fault: str
) -> None:
    channel, peer = organizer_channel
    command, preview, commitment = admission_fields("local_aid", 0)
    reviewed = {"choice": "local_aid", "reviewed_command": command, "preview": preview}
    peer.sendall(response(1, **(reviewed if fault == "status_only" else {"choice": "local_aid"})))
    channel.observe(1)
    if fault != "status_only":
        peer.sendall(response(2, "preview_admitted", **reviewed))
        channel.perform("review", 1)
    if fault == "changed_then_restored":
        changed = {**reviewed, "aid_allocation": {"aid": {"food_quantity": 2, "cash_micros": "0"}}}
        peer.sendall(response(3, **changed))
        channel.observe(1)
        peer.sendall(response(4, **reviewed))
        channel.observe(1)
    if fault == "generation":
        peer.sendall(response(3, **reviewed, generation=2))
        channel.observe(1)
    if fault == "cleared_review":
        peer.sendall(response(3, choice="local_aid"))
        channel.observe(1)
    if fault in ("matching", "consumed"):
        peer.sendall(response(3, **reviewed))
        channel.observe(1)
        peer.sendall(response(4, "acceptance_admitted", choice="local_aid", commitment=commitment))
        assert channel.perform("confirm", 1).commitment == windowed.Commitment.model_validate(
            commitment
        )
        if fault == "matching":
            return
        peer.sendall(response(5, **reviewed))
        channel.observe(1)
    sequence = channel.sequence
    with pytest.raises(windowed.ControlRefusal, match="requires this channel's current review"):
        channel.perform("confirm", 1)
    assert channel.sequence == sequence


@pytest.mark.parametrize(
    "fault",
    [
        "uncleared_command",
        "uncleared_preview",
        "changed_nonce",
        "changed_resolves_period",
        "changed_generation",
    ],
)
def test_witnessed_acceptance_must_clear_and_match_original(
    organizer_channel: OrganizerChannel, fault: str
) -> None:
    channel, peer = organizer_channel
    command, preview, commitment = admission_fields("local_aid", 0)
    peer.sendall(response(1, choice="local_aid"))
    channel.observe(1)
    peer.sendall(
        response(
            2, "preview_admitted", choice="local_aid", reviewed_command=command, preview=preview
        )
    )
    channel.perform("review", 1)
    accepted = {"choice": "local_aid", "commitment": commitment}
    if fault == "uncleared_command":
        accepted["reviewed_command"] = command
    elif fault == "uncleared_preview":
        accepted["preview"] = preview
    elif fault == "changed_nonce":
        commitment["command"]["nonce"] = [98] * 16
    elif fault == "changed_resolves_period":
        commitment["resolves_period"] += 1
    else:
        accepted["generation"] = 2
    peer.sendall(response(3, "acceptance_admitted", **accepted))
    with pytest.raises(windowed.ControlRefusal):
        channel.perform("confirm", 1)
    assert channel.sequence == 3


@pytest.mark.parametrize("case", ["matching", "changed", "unwitnessed", "refused"])
def test_capture_preserves_only_its_witnessed_review(
    organizer_channel: OrganizerChannel, case: str
) -> None:
    channel, peer = organizer_channel
    command, preview, commitment = admission_fields("local_aid", 0, nonce=87)
    reviewed = {"choice": "local_aid", "reviewed_command": command, "preview": preview}
    peer.sendall(response(1, **(reviewed if case == "unwitnessed" else {"choice": "local_aid"})))
    channel.observe(1)
    if case != "unwitnessed":
        peer.sendall(response(2, "preview_admitted", **reviewed))
        channel.perform("review", 1)
    sequence = channel.sequence + 1
    if case == "refused":
        frame = json.loads(response(sequence, "refused", **reviewed))
        frame["reason"] = "capture_image_invalid"
        peer.sendall(json.dumps(frame).encode() + b"\n")
        with pytest.raises(windowed.ControlRefusal, match="capture_image_invalid"):
            channel.perform("capture_frame", 1)
    else:
        captured = {**reviewed, "generation": 2} if case == "changed" else reviewed
        peer.sendall(response(sequence, "frame_captured", **captured))
        pictured = channel.perform("capture_frame", 1)
        if case == "matching":
            peer.sendall(
                response(
                    sequence + 1, "acceptance_admitted", choice="local_aid", commitment=commitment
                )
            )
            accepted = channel.perform("confirm", 1).commitment
            assert accepted == windowed.Commitment.model_validate(commitment)
            assert accepted is not None and accepted.command == pictured.reviewed_command
            with peer.makefile("rb") as requests:
                assert [
                    json.loads(requests.readline())["action"] for _ in range(channel.sequence)
                ] == ["status", "review", "capture_frame", "confirm"]
            # Replaying the pictured readback cannot revive the consumed Review.
            peer.sendall(response(channel.sequence + 1, **reviewed))
            channel.observe(1)
    last_sent = channel.sequence
    with pytest.raises(windowed.ControlRefusal, match="requires this channel's current review"):
        channel.perform("confirm", 1)
    assert channel.sequence == last_sent


def test_collected_plan_requires_an_exact_positive_allocation() -> None:
    with pytest.raises(ValueError):
        windowed.PlannedChoice.model_validate({"period": 1, "choice": "remote_aid"})
    with pytest.raises(ValueError):
        windowed.PlannedChoice.model_validate(
            {
                "period": 1,
                "choice": "collect",
                "allocation": {"aid": {"food_quantity": 1, "cash_micros": "0"}},
            }
        )
    plan = windowed.PlannedChoice.model_validate(
        {
            "period": 1,
            "choice": "collect",
            "allocation": {"collection": {"target_cash_micros": "1450000000"}},
        }
    )
    assert isinstance(plan.allocation, windowed.CollectionAllocation)
    assert windowed.whole_dollars(plan.allocation.collection.target_cash_micros) == "1450"
    with pytest.raises(windowed.ControlRefusal):
        windowed.whole_dollars("1500000")


def test_editor_refuses_a_mutation_that_preserves_the_review() -> None:
    parent, peer = socket.socketpair()
    channel = windowed.ControlChannel(parent, CAMPAIGN, 0)
    fields = state()
    command, preview, _ = admission_fields("hold", 0)
    fields.update(
        focused_amount="contribution", amount_text="2", reviewed_command=command, preview=preview
    )

    def reply() -> None:
        with peer, peer.makefile("rb") as source:
            for raw in source:
                request = json.loads(raw)
                if request["action"] == {"amount_key": "delete"}:
                    fields["amount_text"] = ""
                peer.sendall(
                    json.dumps(
                        {
                            "version": 4,
                            "sequence": request["sequence"],
                            "event": "applied",
                            "reason": None,
                            "state": fields,
                        }
                    ).encode()
                    + b"\n"
                )

    worker = threading.Thread(target=reply)
    worker.start()
    try:
        with pytest.raises(windowed.ControlRefusal, match="obsolete review"):
            windowed.edit_amount(channel, "contribution", "1450", 1)
    finally:
        channel.close()
        worker.join(2)
    assert not worker.is_alive()


def test_observed_unavailable_offer_never_arms_confirmation(
    organizer_channel: OrganizerChannel,
) -> None:
    channel, peer = organizer_channel
    command, preview, _ = admission_fields("local_aid", 0)
    selected = state()
    selected.update(choice="local_aid", aid_allocation=command["allocation"])
    peer.sendall(response(1, **selected))
    channel.observe(1)
    refused = json.loads(
        response(
            2,
            "refused",
            **{
                **selected,
                "reviewed_command": command,
                "preview": {**preview, "refusal": "aid_unavailable"},
            },
        )
    )
    refused["reason"] = "ordinary_response_refused"
    peer.sendall(json.dumps(refused).encode() + b"\n")
    result = channel.perform("review", 1, allow_review_refusal=True)
    assert result.preview is not None and result.preview.refusal == "aid_unavailable"
    assert channel.records[-1].event == "refused"
    with pytest.raises(windowed.ControlRefusal, match="current review"):
        channel.perform("confirm", 1)
    assert channel.sequence == 2


@pytest.mark.parametrize("raced_tick", [8, 9])
def test_delayed_one_play_acknowledgement_preserves_authenticated_pending(raced_tick):
    start = state(8)
    arm = {
        "phase": "armed",
        "arm_sequence": 2,
        "play_sequence": None,
        "campaign_id": CAMPAIGN,
        "scope_epoch": 7,
        "start_tick": 8,
        "start_generation": 1,
        "target_tick": 9,
        "request_id": None,
        "pending_at_pause": False,
        "playing_after_pause": None,
    }
    stopped = {
        **arm,
        "phase": "paused_after_enqueue",
        "play_sequence": 3,
        "request_id": 41,
        "pending_at_pause": True,
        "playing_after_pause": False,
    }
    frames = [
        (1, "observed", start),
        (2, "applied", {**start, "play_interlock": arm}),
        (3, "applied", {**state(raced_tick), "play_interlock": stopped}),
        (4, "applied", {**state(9), "play_interlock": stopped}),
    ]
    left, right = socket.socketpair()
    with left, right:
        channel = windowed.ControlChannel(left, CAMPAIGN, 8)
        for seq, event, body in frames:
            right.sendall(
                (
                    json.dumps(
                        {
                            "version": 4,
                            "sequence": seq,
                            "event": event,
                            "reason": None,
                            "state": {"installed_organizer": None, "play_interlock": None, **body},
                        }
                    )
                    + "\n"
                ).encode()
            )
            if seq == 1:
                channel.observe(1)
            else:
                channel.perform(("arm_one_play_advance", "play", "pause")[seq - 2], 1)
        assert channel.state.play_interlock.request_id == 41


@pytest.mark.parametrize("crossing", ["between_requests", "while_waiting"])
def test_smoke_clock_bounds_next_send_and_outstanding_reply(crossing, monkeypatch):
    import time

    stream, peer = socket.socketpair()
    try:
        deadline = time.monotonic() + 0.1
        channel = windowed.ControlChannel(stream, CAMPAIGN, 0, wall_deadline=deadline)
        peer.sendall(response(1, "observed", **state()))
        installed = channel.observe(2)
        assert json.loads(peer.recv(4096))["sequence"] == 1
        if crossing == "between_requests":
            monkeypatch.setattr(windowed.time, "monotonic", lambda: deadline + 1)
        with pytest.raises(windowed.ControlRefusal, match="smoke wall"):
            channel.observe(2)
        assert channel.state == installed
        peer.setblocking(False)
        remaining = peer.recv(4096)
        assert (
            remaining == b""
            if crossing == "between_requests"
            else json.loads(remaining)["sequence"] == 2
        )
    finally:
        stream.close()
        peer.close()
