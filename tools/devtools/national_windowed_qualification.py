"""Drive ordinary native controls; UI observations never qualify the economy.

The existing national supervisor admits the database, binaries and sole writer.
This module neither provisions a game nor admits that ownership from a pathname.
The launcher still connects the client/runtime directly through anonymous pipes.
"""

from __future__ import annotations

import json
import math
import os
import socket
import struct
import subprocess
import tempfile
import time
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path
from typing import Annotated, Literal, Protocol
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StrictBool,
    StrictInt,
    StrictStr,
    ValidationError,
    field_validator,
)
from tools import run_observer_session as launcher

Nonnegative = Annotated[StrictInt, Field(ge=0, le=2**64 - 1)]
Positive = Annotated[StrictInt, Field(gt=0, le=2**64 - 1)]
Sha256 = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]
Action = Literal[
    "status",
    "continue_warning",
    "continue_title",
    "open_organizer",
    "open_direction",
    "close_inspector",
    "choose_remote_aid",
    "choose_local_aid",
    "choose_pause_standing",
    "choose_resume_standing",
    "review",
    "confirm",
    "step",
    "reopen",
    "refresh",
    "quit",
]
Event = Literal[
    "observed",
    "applied",
    "preview_admitted",
    "acceptance_admitted",
    "committed_and_installed",
    "reopened_and_installed",
    "refresh_requested",
    "quit_requested",
    "refused",
]
EXPECTED: dict[str, str] = {
    "status": "observed",
    "review": "preview_admitted",
    "confirm": "acceptance_admitted",
    "step": "committed_and_installed",
    "reopen": "reopened_and_installed",
    "refresh": "refresh_requested",
    "quit": "quit_requested",
}
# Designed private wire bounds, equal to the native adapter. These are not new
# storage, economic, timing or memory qualification policy defaults.
INPUT_BYTES = 4096
OUTPUT_BYTES = 32_768
POLL_SECONDS = 0.25


class ControlRefusal(ValueError):
    """A bounded native-control failure, safe to display without credentials."""


class CaptureMonitor(Protocol):
    def check(self) -> None: ...

    def finish(self) -> None: ...


class FrozenRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ControlState(FrozenRecord):
    campaign_id: StrictStr
    scope_epoch: Nonnegative | None
    durable_tick: Nonnegative
    viewed_tick: Nonnegative
    generation: Nonnegative
    phase: Literal["Connecting", "Loading", "Ready", "Advancing", "Complete", "Failed", "Closed"]
    foundation_sha256: Sha256 | None
    tick_content_hash: Sha256 | None
    archive_verified_tick: Nonnegative
    advance_pending: StrictBool
    lifecycle_pending: StrictBool
    organizer_pending: StrictBool
    organizer_status_due: StrictBool
    organizer_period: Nonnegative | None
    choice: StrictStr
    reviewed_command: dict[str, JsonValue] | None
    preview: dict[str, JsonValue] | None
    commitment: dict[str, JsonValue] | None
    quit_requested: StrictBool
    splash_visible: StrictBool
    menu_open: StrictBool
    opening_stage: Literal["Warning", "Production", "Title", "Game"]
    primary_view: StrictStr
    inspector: StrictStr


class ControlResponse(FrozenRecord):
    version: Literal[2]
    sequence: Positive
    event: Event
    reason: StrictStr | None
    state: ControlState

    @field_validator("version", mode="before")
    @classmethod
    def exact_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("control version must be an exact integer")
        return value


class ActionObservation(FrozenRecord):
    sequence: Positive
    action: Action
    started_monotonic_ns: Nonnegative
    completed_monotonic_ns: Nonnegative
    event: Event
    reason: StrictStr | None
    state: ControlState


class ControlsEvidence(FrozenRecord):
    version: Literal[2]
    status: Literal["incomplete", "completed"]
    campaign: StrictStr
    initial_tick: Nonnegative
    foundation_sha256: Sha256 | None
    scope: Literal["native_ui_actions_only_not_accounting_or_memory_qualification"]
    actions: tuple[ActionObservation, ...]

    @field_validator("version", mode="before")
    @classmethod
    def exact_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("native controls evidence version must be an exact integer")
        return value


class PlannedChoice(FrozenRecord):
    period: Positive
    choice: Literal["remote_aid", "local_aid", "pause_standing", "resume_standing"]


def _unique_object(pairs: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]:
    result: dict[str, JsonValue] = {}
    for key, value in pairs:
        if key in result:
            raise ControlRefusal("native control response has duplicate fields")
        result[key] = value
    return result


def _nonfinite(_value: str) -> JsonValue:
    raise ControlRefusal("native control response has a nonfinite number")


def _duration(value: float) -> float:
    if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        raise ControlRefusal("native control requires a finite positive timeout")
    return value


class ControlChannel:
    """Exactly one outstanding UI input on the explicitly admitted private socket."""

    def __init__(
        self,
        connection: socket.socket,
        campaign: str,
        initial_tick: int,
        *,
        check_capture: Callable[[], None] | None = None,
    ) -> None:
        if str(UUID(campaign)) != campaign or UUID(campaign).int == 0:
            raise ControlRefusal("native control campaign must be a nonzero canonical UUID")
        if type(initial_tick) is not int or not 0 <= initial_tick <= 2**64 - 1:
            raise ControlRefusal("native control opening period invalid")
        self.connection = connection
        self.campaign = campaign
        self.initial_tick = initial_tick
        self.state: ControlState | None = None
        self.records: list[ActionObservation] = []
        self.sequence = 0
        self.foundation: str | None = None
        self.scope_epoch: int | None = None
        self.closed = False
        self.ready = False
        self._check_capture = check_capture

    def close(self) -> None:
        self.closed = True
        self.connection.close()

    def _receive(self, deadline: float) -> ControlResponse:
        raw = bytearray()
        while b"\n" not in raw:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ControlRefusal("native control response deadline exceeded")
            self.connection.settimeout(remaining)
            try:
                part = self.connection.recv(OUTPUT_BYTES + 1 - len(raw))
            except TimeoutError:
                raise ControlRefusal("native control response deadline exceeded") from None
            if time.monotonic() > deadline:
                raise ControlRefusal("native control response deadline exceeded")
            if not part:
                raise ControlRefusal("native control response ended before a complete frame")
            raw.extend(part)
            if len(raw) > OUTPUT_BYTES:
                raise ControlRefusal("native control response exceeds its byte bound")
        if raw[-1:] != b"\n" or raw.count(b"\n") != 1:
            raise ControlRefusal("native control response was pipelined")
        try:
            parsed = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_nonfinite)
            return ControlResponse.model_validate(parsed)
        except (ValueError, UnicodeError, ValidationError) as error:
            raise ControlRefusal(
                "native control response has unsupported or invalid fields"
            ) from error

    def _bind(self, current: ControlState, action: Action, event: Event) -> None:
        if current.campaign_id != self.campaign:
            raise ControlRefusal("native control campaign changed")
        if self.foundation is not None and current.foundation_sha256 != self.foundation:
            raise ControlRefusal("native control foundation changed")
        if action == "reopen":
            prior = self.state
            if (
                event != "reopened_and_installed"
                or prior is None
                or prior.scope_epoch is None
                or current.scope_epoch != prior.scope_epoch + 1
                or current.generation <= prior.generation
                or current.phase not in {"Ready", "Complete"}
                or current.durable_tick != prior.durable_tick
                or current.viewed_tick != current.durable_tick
                or current.tick_content_hash != prior.tick_content_hash
                or current.foundation_sha256 != prior.foundation_sha256
                or current.archive_verified_tick != current.durable_tick
                or current.advance_pending
                or current.lifecycle_pending
                or current.organizer_pending
                or current.organizer_status_due
                or current.organizer_period != current.durable_tick
            ):
                raise ControlRefusal("native reopen did not restore its exact installed boundary")
        elif self.scope_epoch is not None and current.scope_epoch != self.scope_epoch:
            raise ControlRefusal("native control runtime scope changed")
        if self.state is not None and self.ready:
            expected = self.state.durable_tick + (
                action == "step" and event == "committed_and_installed"
            )
            if current.durable_tick != expected:
                raise ControlRefusal("native control period does not match its own action")
            if action != "step" and current.tick_content_hash != self.state.tick_content_hash:
                raise ControlRefusal("native control committed identity changed")
        if current.phase in {"Ready", "Complete"}:
            if current.foundation_sha256 is None or current.scope_epoch is None:
                raise ControlRefusal("ready native control lacks foundation/runtime identity")
            if current.durable_tick > 0 and current.tick_content_hash is None:
                raise ControlRefusal("ready native control lacks committed period identity")
            if not self.ready and current.durable_tick != self.initial_tick:
                raise ControlRefusal("ready native control has a different opening period")
            self.ready = True
        if current.phase in {"Failed", "Closed"}:
            raise ControlRefusal("native runtime failed or closed")
        self.foundation = current.foundation_sha256 or self.foundation
        self.scope_epoch = (
            current.scope_epoch if current.scope_epoch is not None else self.scope_epoch
        )

    def _exchange(self, action: Action, timeout: float) -> ControlResponse:
        if self._check_capture is not None:
            self._check_capture()
        if self.closed:
            raise ControlRefusal("native control channel is closed after refusal")
        if action not in EXPECTED and action not in {
            "continue_warning",
            "continue_title",
            "open_organizer",
            "open_direction",
            "close_inspector",
            "choose_remote_aid",
            "choose_local_aid",
            "choose_pause_standing",
            "choose_resume_standing",
        }:
            raise ControlRefusal("unsupported native control action")
        started = time.monotonic_ns()
        deadline = time.monotonic() + _duration(timeout)
        self.sequence += 1
        prior = self.state
        frame = (
            json.dumps(
                {
                    "version": 2,
                    "sequence": self.sequence,
                    "campaign_id": self.campaign,
                    "scope_epoch": prior.scope_epoch if prior else None,
                    "expected_tick": prior.durable_tick if prior else self.initial_tick,
                    "expected_generation": prior.generation if prior else 0,
                    "action": action,
                },
                allow_nan=False,
            ).encode()
            + b"\n"
        )
        if len(frame) > INPUT_BYTES:
            raise ControlRefusal("native control input exceeds its byte bound")
        try:
            self.connection.settimeout(max(0.001, deadline - time.monotonic()))
            self.connection.sendall(frame)
            reply = self._receive(deadline)
            if reply.sequence != self.sequence:
                raise ControlRefusal("native control response sequence differs")
            self._bind(reply.state, action, reply.event)
            if not self.records or action != "status" or reply.state != self.records[-1].state:
                self.records.append(
                    ActionObservation(
                        sequence=self.sequence,
                        action=action,
                        started_monotonic_ns=started,
                        completed_monotonic_ns=time.monotonic_ns(),
                        event=reply.event,
                        reason=reply.reason,
                        state=reply.state,
                    )
                )
            self.state = reply.state
            return reply
        except (OSError, ControlRefusal) as error:
            self.close()
            raise ControlRefusal("native control exchange refused: " + str(error)) from error

    def observe(self, timeout: float) -> ControlState:
        reply = self._exchange("status", timeout)
        if reply.event != "observed" and not (
            reply.event == "refused" and reply.reason == "control_stale_or_unavailable"
        ):
            self.close()
            raise ControlRefusal("native status request refused")
        return reply.state

    def perform(self, action: Action, timeout: float) -> ControlState:
        prior = self.state
        reply = self._exchange(action, timeout)
        if reply.event != EXPECTED.get(action, "applied") or reply.reason is not None:
            self.close()
            raise ControlRefusal("ordinary native handler refused the requested action")
        if action == "step" and (
            reply.state.phase not in {"Ready", "Complete"}
            or reply.state.viewed_tick != reply.state.durable_tick
            or reply.state.advance_pending
        ):
            self.close()
            raise ControlRefusal("native period was not completely installed")
        choice = {
            "choose_remote_aid": "remote_aid",
            "choose_local_aid": "local_aid",
            "choose_pause_standing": "pause_standing",
            "choose_resume_standing": "resume_standing",
        }.get(action)
        if choice is not None and reply.state.choice != choice:
            self.close()
            raise ControlRefusal("native handler applied a different choice")
        if action == "review" and (
            reply.state.reviewed_command is None
            or reply.state.preview is None
            or reply.state.preview.get("refusal") is not None
        ):
            self.close()
            raise ControlRefusal("native preview lacks its reviewed command")
        if action == "confirm" and (
            prior is None
            or prior.reviewed_command is None
            or reply.state.commitment is None
            or reply.state.commitment.get("command") != prior.reviewed_command
        ):
            self.close()
            raise ControlRefusal("native acceptance has a different reviewed command")
        return reply.state


def write_observations(
    destination: Path, channel: ControlChannel, status: Literal["incomplete", "completed"]
) -> None:
    """Atomic evidence of local actions; never a named qualification result."""
    payload = ControlsEvidence(
        version=2,
        status=status,
        campaign=channel.campaign,
        initial_tick=channel.initial_tick,
        foundation_sha256=channel.foundation,
        scope="native_ui_actions_only_not_accounting_or_memory_qualification",
        actions=tuple(channel.records),
    ).model_dump(mode="json")
    descriptor, name = tempfile.mkstemp(
        prefix=destination.name + ".", suffix=".partial", dir=destination.parent
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(payload, output, allow_nan=False, separators=(",", ":"))
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def finish_observations(
    destination: Path,
    channel: ControlChannel,
    status: Literal["incomplete", "completed"],
    failure: BaseException | None,
) -> None:
    try:
        write_observations(destination, channel, status)
    except Exception as persistence_error:
        if failure is not None:
            raise BaseExceptionGroup(
                "native drive and evidence publication both failed", [failure, persistence_error]
            ) from None
        raise
    finally:
        channel.close()


def submit_choice(channel: ControlChannel, choice: PlannedChoice, timeout: float) -> None:
    """Review and confirm through the ordinary UI, including standing controls."""
    if channel.state is None or channel.state.durable_tick + 1 != choice.period:
        raise ControlRefusal("native choice plan does not match the next actual period")
    if choice.choice in {"pause_standing", "resume_standing"}:
        channel.perform("open_direction", timeout)
        selected = channel.perform(
            "choose_pause_standing"
            if choice.choice == "pause_standing"
            else "choose_resume_standing",
            timeout,
        )
        if selected.inspector != "Closed":
            channel.perform("close_inspector", timeout)
    else:
        channel.perform(
            "choose_remote_aid" if choice.choice == "remote_aid" else "choose_local_aid", timeout
        )
    channel.perform("review", timeout)
    channel.perform("confirm", timeout)
    wait_ready(channel, timeout, organizer=True)


def wait_ready(channel: ControlChannel, timeout: float, *, organizer: bool) -> ControlState:
    deadline = time.monotonic() + _duration(timeout)
    while time.monotonic() < deadline:
        current = channel.observe(max(0.001, deadline - time.monotonic()))
        if (
            current.phase in {"Ready", "Complete"}
            and not current.lifecycle_pending
            and not current.advance_pending
            and (
                not organizer
                or (
                    current.organizer_period == current.durable_tick
                    and not current.organizer_pending
                    and not current.organizer_status_due
                )
            )
        ):
            return current
        time.sleep(min(POLL_SECONDS, max(0, deadline - time.monotonic())))
    raise ControlRefusal("native control readiness deadline exceeded")


def drive_pair(
    runtime_binary: Path,
    client_binary: Path,
    root: Path,
    runtime_environment: Mapping[str, str],
    client_environment: Mapping[str, str],
    *,
    defines_path: Path,
    initial_target: launcher.NewCampaignTarget | launcher.OpenCampaignTarget,
    initial_tick: int,
    periods: int,
    directory: Path,
    operation_timeout: float,
    on_started: Callable[[subprocess.Popen[bytes], subprocess.Popen[bytes]], None],
    on_boundary: Callable[[ControlState], None],
    on_recovery: Callable[[ControlState], None],
    choices: tuple[PlannedChoice, ...] = (),
    capture_lifecycle: Callable[
        [subprocess.Popen[bytes], subprocess.Popen[bytes]],
        AbstractContextManager[CaptureMonitor | None],
    ]
    | None = None,
) -> int:
    """Use one actual windowed pair and ordinary controls under runner admission.

    Callbacks receive exact owned Popen handles and UI boundaries. Independent
    committed-state readers must authenticate those boundaries; their presence
    never upgrades local UI observations into an accounting or memory result.
    """
    if (
        type(periods) is not int
        or not 0 <= periods <= 2**64 - 1
        or type(initial_tick) is not int
        or not 0 <= initial_tick <= 2**64 - 1
        or initial_tick + periods > 2**64 - 1
    ):
        raise ControlRefusal("native drive requires nonnegative actual period counts")
    _duration(operation_timeout)
    schedule = {choice.period: choice for choice in choices}
    if len(schedule) != len(choices) or any(
        not initial_tick < period <= initial_tick + periods for period in schedule
    ):
        raise ControlRefusal("native choice schedule duplicates or exceeds the actual horizon")
    if not directory.is_dir() or directory.is_symlink():
        raise ControlRefusal("native drive requires its existing evidence directory")
    with tempfile.TemporaryDirectory(prefix="babylon-q-", dir="/tmp") as name:
        endpoint = Path(name) / "control.sock"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(endpoint))
            endpoint.chmod(0o600)
            listener.listen(1)
            listener.settimeout(operation_timeout)

            def controlled(client: subprocess.Popen[bytes], capture: CaptureMonitor | None) -> None:
                connection, _address = listener.accept()
                _pid, uid, _gid = struct.unpack(
                    "3i",
                    connection.getsockopt(
                        socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")
                    ),
                )
                if uid != os.getuid() or _pid != client.pid:
                    connection.close()
                    raise ControlRefusal("native control socket peer is not the exact owned client")
                try:
                    if capture is not None:
                        capture.check()
                    connection.settimeout(operation_timeout)
                    # App construction waits here before connecting the runtime
                    # pipe. The capture context has already finished its first
                    # authenticated sample before yielding to this driver.
                    connection.sendall(
                        json.dumps(
                            {
                                "version": 2,
                                "campaign_id": str(initial_target.campaign),
                                "phase": "capture_ready",
                            },
                            separators=(",", ":"),
                        ).encode("ascii")
                        + b"\n"
                    )
                    channel = ControlChannel(
                        connection,
                        str(initial_target.campaign),
                        initial_tick,
                        check_capture=capture.check if capture is not None else None,
                    )
                except BaseException:
                    connection.close()
                    raise
                result: Literal["incomplete", "completed"] = "incomplete"
                failure: BaseException | None = None
                try:
                    current = wait_ready(channel, operation_timeout, organizer=False)
                    opening_deadline = time.monotonic() + operation_timeout
                    while current.splash_visible or current.menu_open:
                        remaining = opening_deadline - time.monotonic()
                        if remaining <= 0:
                            raise ControlRefusal("native opening navigation deadline exceeded")
                        if current.opening_stage == "Warning":
                            channel.perform("continue_warning", remaining)
                        elif current.opening_stage == "Title":
                            channel.perform("continue_title", remaining)
                        time.sleep(min(POLL_SECONDS, max(0, opening_deadline - time.monotonic())))
                        remaining = opening_deadline - time.monotonic()
                        if remaining <= 0:
                            raise ControlRefusal("native opening navigation deadline exceeded")
                        current = channel.observe(remaining)
                        if time.monotonic() > opening_deadline:
                            raise ControlRefusal("native opening navigation deadline exceeded")
                    if current.primary_view != "Organizer":
                        channel.perform("open_organizer", operation_timeout)
                    current = wait_ready(channel, operation_timeout, organizer=True)
                    on_boundary(current)
                    for _period in range(periods):
                        if planned := schedule.get(current.durable_tick + 1):
                            submit_choice(channel, planned, operation_timeout)
                        current = channel.perform("step", operation_timeout)
                        current = wait_ready(channel, operation_timeout, organizer=True)
                        on_boundary(current)
                        current = channel.perform("reopen", operation_timeout)
                        current = wait_ready(channel, operation_timeout, organizer=True)
                        on_recovery(current)
                        write_observations(
                            directory / "native-controls.json", channel, "incomplete"
                        )
                    if capture is not None:
                        capture.finish()
                    channel.perform("quit", operation_timeout)
                    result = "completed"
                except BaseException as error:
                    failure = error
                    raise
                finally:
                    finish_observations(
                        directory / "native-controls.json", channel, result, failure
                    )

            def started(runtime: subprocess.Popen[bytes], client: subprocess.Popen[bytes]) -> None:
                on_started(runtime, client)
                # The supervisor supplies exact capture admission. Its context
                # starts before native loading is awaited and ends before the
                # launcher reaps the children, including every refusal path.
                context = (
                    capture_lifecycle(runtime, client)
                    if capture_lifecycle is not None
                    else nullcontext()
                )
                with context as finish_capture:
                    controlled(client, finish_capture)

            return launcher.run_pair(
                runtime_binary,
                client_binary,
                root,
                runtime_environment,
                client_environment,
                defines_path=defines_path,
                initial_target=initial_target,
                qualification_control=endpoint,
                on_started=started,
            )
