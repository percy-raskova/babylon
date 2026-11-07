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
from typing import Annotated, Literal, Protocol, Self
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    ValidationError,
    field_validator,
    model_validator,
)
from tools import run_observer_session as launcher

Nonnegative = Annotated[StrictInt, Field(ge=0, le=2**64 - 1)]
Positive = Annotated[StrictInt, Field(gt=0, le=2**64 - 1)]
Sha256 = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]
UnitAction = Literal[
    "choose_collect",
    "inspect_subject_evidence",
    "draft_from_report",
    "archive_report",
    "status",
    "play",
    "pause",
    "speed",
    "world",
    "observer_campaigns",
    "circuit",
    "flow",
    "economy_network",
    "manufacturing_sector",
    "all_sectors",
    "select_first_county_cohort",
    "standard_interface",
    "larger_interface",
    "read_inquiry_report",
    "continue_warning",
    "continue_title",
    "open_organizer",
    "open_direction",
    "inspect_practices",
    "inspect_receipts",
    "open_relationships",
    "scene_places",
    "scene_relationships",
    "select_workplace_committee",
    "select_neighborhood_group",
    "inspect_evidence",
    "next_evidence",
    "previous_evidence",
    "archive_workplace",
    "archive_organization",
    "open_archive_evidence",
    "previous_period",
    "return_live",
    "capture_frame",
    "resize1366x768",
    "resize1920x1080",
    "close_inspector",
    "choose_remote_aid",
    "choose_local_aid",
    "choose_inquiry_work_lost",
    "choose_inquiry_maintenance_received",
    "choose_reinforce",
    "choose_hold",
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
    "frame_captured",
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
    "capture_frame": "frame_captured",
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


AmountField = Literal["contribution", "food", "cash"]


class FocusAmount(FrozenRecord):
    focus_amount: AmountField


class SelectAidPartner(FrozenRecord):
    select_aid_partner: Literal["local", "remote"]


class CharacterKey(FrozenRecord):
    character: Annotated[StrictStr, Field(min_length=1, max_length=1)]


class AmountKey(FrozenRecord):
    amount_key: Literal["home", "end", "delete", "backspace"] | CharacterKey


Action = UnitAction | FocusAmount | SelectAidPartner | AmountKey


def expected_event(action: Action) -> str:
    return EXPECTED.get(action, "applied") if isinstance(action, str) else "applied"


def _canonical_campaign(value: str) -> str:
    campaign = UUID(value)
    if campaign.int == 0 or str(campaign) != value:
        raise ValueError("native campaign must be a canonical nonzero UUID")
    return value


Campaign = Annotated[StrictStr, AfterValidator(_canonical_campaign)]


class ControlVersion(FrozenRecord):
    version: Literal[3]

    @field_validator("version", mode="before")
    @classmethod
    def exact_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("native control version must be an exact integer")
        return value


class StartupAdmission(ControlVersion):
    campaign_id: Campaign
    phase: Literal["capture_ready"]


class ControlInput(ControlVersion):
    sequence: Positive
    campaign_id: Campaign
    scope_epoch: Nonnegative | None
    expected_tick: Nonnegative
    expected_generation: Nonnegative
    action: Action


class InquiryChoice(FrozenRecord):
    inquiry: Literal["work_lost", "maintenance_received"]


UnitChoice = Literal[
    "collect", "local_aid", "remote_aid", "reinforce", "hold", "pause_standing", "resume_standing"
]


Choice = UnitChoice | InquiryChoice
Byte = Annotated[StrictInt, Field(ge=0, le=255)]
Bytes16 = Annotated[tuple[Byte, ...], Field(min_length=16, max_length=16)]
Bytes32 = Annotated[tuple[Byte, ...], Field(min_length=32, max_length=32)]


def _bounded_micros(value: str) -> str:
    if int(value) > 2**127 - 1:
        raise ValueError("allocation cash exceeds i128")
    return value


Micros = Annotated[
    StrictStr,
    Field(pattern=r"^(0|[1-9][0-9]{0,38})$"),
    AfterValidator(_bounded_micros),
]


class CollectionAmount(FrozenRecord):
    target_cash_micros: Micros


class CollectionAllocation(FrozenRecord):
    collection: CollectionAmount


class AidAmounts(FrozenRecord):
    food_quantity: Nonnegative
    cash_micros: Micros


class AidAllocation(FrozenRecord):
    aid: AidAmounts


Allocation = Literal["none"] | CollectionAllocation | AidAllocation


class SelectedAllocation(FrozenRecord):
    choice: Choice
    allocation: Allocation

    @model_validator(mode="after")
    def choice_matches_allocation(self) -> Self:
        if self.choice == "collect":
            valid = isinstance(self.allocation, CollectionAllocation) and (
                self.allocation.collection.target_cash_micros != "0"
            )
        elif self.choice in ("local_aid", "remote_aid"):
            valid = isinstance(self.allocation, AidAllocation) and (
                self.allocation.aid.food_quantity > 0 or self.allocation.aid.cash_micros != "0"
            )
        else:
            valid = self.allocation == "none"
        if not valid:
            raise ValueError("selected allocation cannot authorize this practice")
        return self


class Command(SelectedAllocation):
    campaign_id: Bytes16
    actor_id: Nonnegative
    authority_id: Bytes16
    expected_period: Nonnegative
    content_digest: Bytes32
    resource_digest: Bytes32
    nonce: Bytes16


class Commitment(FrozenRecord):
    command: Command
    resolves_period: Positive
    commitment_id: Bytes32


class ReportCommodity(FrozenRecord):
    good_id: Bytes32
    unit_id: Bytes32
    label: StrictStr
    unit_label: StrictStr


class OpeningAssessment(FrozenRecord):
    basis: Literal["opening_assessment"]
    commodity: ReportCommodity
    required: Nonnegative
    opening_stock: Nonnegative


class FoodProvision(FrozenRecord):
    basis: Literal["food_provision"]
    commodity: ReportCommodity
    required: Nonnegative
    consumed: Nonnegative
    unmet: Nonnegative
    closing: Nonnegative
    purchased: Nonnegative
    settled_micros: Micros


class ServiceReport(FrozenRecord):
    commodity: ReportCommodity
    required: Nonnegative
    performed: Nonnegative
    satisfied: Nonnegative
    unmet: Nonnegative
    unused: Nonnegative
    expired: Nonnegative
    settled_micros: Micros
    refunded_micros: Micros


class EssentialServices(FrozenRecord):
    basis: Literal["essential_services"]
    services: tuple[ServiceReport, ...]


class ParticipationTime(FrozenRecord):
    basis: Literal["participation_time"]
    labor_unit: Bytes32
    attended: Nonnegative
    protected: Nonnegative
    unpaid: Nonnegative
    contributed: Nonnegative
    remaining: Nonnegative


class PartnerReport(FrozenRecord):
    kind: Literal["partner"]
    evidence_class: Literal["Derived"]
    facts: Annotated[
        OpeningAssessment | FoodProvision | EssentialServices | ParticipationTime,
        Field(discriminator="basis"),
    ]


class ReducedWorkReport(FrozenRecord):
    kind: Literal["reduced_work"]
    previous_labor_hours: Nonnegative
    performed_labor_hours: Nonnegative


class WorkReport(FrozenRecord):
    kind: Literal["work"]
    performed_labor_hours: Nonnegative
    output_kg: Nonnegative
    previous_labor_hours: Nonnegative | None
    previous_output_kg: Nonnegative | None


class MaintenanceReport(FrozenRecord):
    kind: Literal["maintenance"]
    enabled_batches: Nonnegative
    consumed_batches: Nonnegative
    expired_batches: Nonnegative


class Observation(FrozenRecord):
    observation_id: Bytes32
    actor_id: Nonnegative
    subject_id: Nonnegative
    source_actor_id: Nonnegative
    observed_period: Nonnegative
    acquired_period: Nonnegative
    receipt_id: Bytes32 | None
    report: Annotated[
        PartnerReport | ReducedWorkReport | WorkReport | MaintenanceReport,
        Field(discriminator="kind"),
    ]


class Preview(SelectedAllocation):
    current_period: Nonnegative
    resolves_period: Nonnegative
    available_hours: Nonnegative
    required_hours: Nonnegative
    replaces_standing_work: StrictBool
    refusal: (
        Literal[
            "wrong_campaign",
            "wrong_authority",
            "stale_period",
            "content_changed",
            "resource_contract_changed",
            "insufficient_committed_time",
            "standing_work_paused",
            "standing_work_already_active",
            "invalid_command",
            "collection_unavailable",
            "collection_cash_refused",
            "aid_unavailable",
            "aid_receiving_refused",
            "pending_aid_conflict",
            "household_time_already_spent",
        ]
        | None
    )
    observations: tuple[Observation, ...]


class ControlState(FrozenRecord):
    campaign_id: Campaign
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
    choice: Choice
    reviewed_command: Command | None
    preview: Preview | None
    commitment: Commitment | None
    focused_amount: AmountField | None
    amount_text: StrictStr | None
    allocation_error: StrictStr | None
    collection_allocation: Literal["none"] | CollectionAllocation | None
    aid_allocation: Literal["none"] | AidAllocation | None
    quit_requested: StrictBool
    splash_visible: StrictBool
    menu_open: StrictBool
    opening_stage: Literal["Warning", "Production", "Title", "Game"]
    primary_view: StrictStr
    inspector: StrictStr
    playing: StrictBool
    periods_per_second: StrictFloat
    perspective: Literal["FullObserver", "PlayerKnowledge"]
    world_hash: Sha256 | None
    selected_subject: StrictStr | None
    menu_page: StrictStr
    selected_report_id: Sha256 | None
    selected_report_observed_period: Nonnegative | None
    selected_report_acquired_period: Nonnegative | None
    larger_interface: StrictBool
    road_layer: StrictStr
    network_sector: StrictStr
    selected_county: StrictStr | None
    selected_site: StrictStr | None
    production_details_open: StrictBool
    production_reading: StrictStr | None

    @field_validator("periods_per_second")
    @classmethod
    def supported_speed(cls, value: float) -> float:
        if value not in {1.0, 2.0, 5.0}:
            raise ValueError("native speed is not a supported scheduling setting")
        return value


class ControlResponse(ControlVersion):
    sequence: Positive
    event: Event
    reason: StrictStr | None
    state: ControlState


class ActionObservation(FrozenRecord):
    sequence: Positive
    action: Action
    started_monotonic_ns: Nonnegative
    completed_monotonic_ns: Nonnegative
    event: Event
    reason: StrictStr | None
    state: ControlState


class ControlsEvidence(ControlVersion):
    status: Literal["incomplete", "completed"]
    campaign: StrictStr
    initial_tick: Nonnegative
    foundation_sha256: Sha256 | None
    scope: Literal["native_ui_actions_only_not_accounting_or_memory_qualification"]
    actions: tuple[ActionObservation, ...]


class PlannedChoice(FrozenRecord):
    period: Positive
    choice: Literal[
        "remote_aid",
        "local_aid",
        "inquiry_work_lost",
        "inquiry_maintenance_received",
        "reinforce",
        "hold",
        "pause_standing",
        "resume_standing",
    ]


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
        self._playback_admitted = False
        self._settling_tick: int | None = None
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
        prior = self.state
        starts_playback = action == "play" and event == "applied" and current.playing
        automatic = action in {"status", "play", "pause"} and (
            self._playback_admitted or starts_playback or self._settling_tick is not None
        )
        if prior is not None and self.ready:
            if current.generation < prior.generation:
                raise ControlRefusal("native control generation moved backward")
            if current.perspective != prior.perspective:
                raise ControlRefusal("native control perspective changed")
            if action == "step" and event == "committed_and_installed":
                if current.durable_tick != prior.durable_tick + 1 or current.playing:
                    raise ControlRefusal("native control period does not match its own action")
            elif automatic:
                if current.durable_tick < prior.durable_tick or (
                    not self._playback_admitted
                    and not starts_playback
                    and self._settling_tick is not None
                    and current.durable_tick > self._settling_tick
                ):
                    raise ControlRefusal(
                        "native control automatic period exceeded admitted progress"
                    )
            elif current.durable_tick != prior.durable_tick:
                raise ControlRefusal("native control period does not match its own action")
            if current.durable_tick == prior.durable_tick and (
                current.tick_content_hash != prior.tick_content_hash
                or current.world_hash != prior.world_hash
            ):
                raise ControlRefusal("native control committed identity changed")
        if current.playing and not (self._playback_admitted or starts_playback):
            raise ControlRefusal("native control playback was not explicitly admitted")
        if starts_playback:
            self._playback_admitted = True
        if not current.playing:
            if self._playback_admitted:
                self._settling_tick = current.durable_tick + int(current.advance_pending)
            self._playback_admitted = False
            if (
                not current.advance_pending
                and not current.organizer_pending
                and not current.organizer_status_due
            ):
                self._settling_tick = None
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
        started = time.monotonic_ns()
        deadline = time.monotonic() + _duration(timeout)
        prior = self.state
        try:
            request = ControlInput(
                version=3,
                sequence=self.sequence + 1,
                campaign_id=self.campaign,
                scope_epoch=prior.scope_epoch if prior else None,
                expected_tick=prior.durable_tick if prior else self.initial_tick,
                expected_generation=prior.generation if prior else 0,
                action=action,
            )
        except ValidationError as error:
            raise ControlRefusal("unsupported native control input") from error
        action = request.action
        frame = request.model_dump_json().encode("utf-8") + b"\n"
        if len(frame) > INPUT_BYTES:
            raise ControlRefusal("native control input exceeds its byte bound")
        self.sequence = request.sequence
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
        if reply.event != expected_event(action) or reply.reason is not None:
            self.close()
            reason = f": {reply.reason}" if reply.reason is not None else ""
            raise ControlRefusal("ordinary native handler refused the requested action" + reason)
        if action == "step" and (
            reply.state.phase not in {"Ready", "Complete"}
            or reply.state.viewed_tick != reply.state.durable_tick
            or reply.state.advance_pending
        ):
            self.close()
            raise ControlRefusal("native period was not completely installed")
        if action == "inspect_practices" and reply.state.inspector != "Practices":
            self.close()
            raise ControlRefusal("native practice list did not open")
        choice = (
            {
                "choose_collect": "collect",
                "choose_remote_aid": "remote_aid",
                "choose_local_aid": "local_aid",
                "choose_inquiry_work_lost": InquiryChoice(inquiry="work_lost"),
                "choose_inquiry_maintenance_received": InquiryChoice(
                    inquiry="maintenance_received"
                ),
                "choose_reinforce": "reinforce",
                "choose_hold": "hold",
                "choose_pause_standing": "pause_standing",
                "choose_resume_standing": "resume_standing",
            }.get(action)
            if isinstance(action, str)
            else None
        )
        if choice is not None and reply.state.choice != choice:
            self.close()
            raise ControlRefusal("native handler applied a different choice")
        if action in ("play", "pause") and reply.state.playing != (action == "play"):
            self.close()
            raise ControlRefusal("native playback acknowledgment has the wrong scheduling state")
        if action == "review" and (
            reply.state.reviewed_command is None
            or reply.state.preview is None
            or reply.state.preview.refusal is not None
            or reply.state.choice != reply.state.reviewed_command.choice
            or bytes(reply.state.reviewed_command.campaign_id) != UUID(self.campaign).bytes
            or reply.state.reviewed_command.expected_period != reply.state.durable_tick
            or reply.state.preview.choice != reply.state.reviewed_command.choice
            or reply.state.preview.allocation != reply.state.reviewed_command.allocation
            or reply.state.preview.current_period != reply.state.reviewed_command.expected_period
        ):
            self.close()
            raise ControlRefusal("native preview lacks its reviewed command")
        if action == "confirm" and (
            prior is None
            or prior.reviewed_command is None
            or prior.preview is None
            or reply.state.commitment is None
            or reply.state.commitment.resolves_period != prior.preview.resolves_period
            or reply.state.commitment.command != prior.reviewed_command
        ):
            self.close()
            raise ControlRefusal("native acceptance has a different reviewed command")
        return reply.state


def write_observations(
    destination: Path, channel: ControlChannel, status: Literal["incomplete", "completed"]
) -> None:
    """Atomic evidence of local actions; never a named qualification result."""
    payload = ControlsEvidence(
        version=3,
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
        actions: dict[str, Action] = {
            "remote_aid": "choose_remote_aid",
            "local_aid": "choose_local_aid",
            "inquiry_work_lost": "choose_inquiry_work_lost",
            "inquiry_maintenance_received": "choose_inquiry_maintenance_received",
            "reinforce": "choose_reinforce",
            "hold": "choose_hold",
        }
        channel.perform("inspect_practices", timeout)
        channel.perform(actions[choice.choice], timeout)
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
                        StartupAdmission(
                            version=3,
                            campaign_id=str(initial_target.campaign),
                            phase="capture_ready",
                        )
                        .model_dump_json()
                        .encode("ascii")
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
