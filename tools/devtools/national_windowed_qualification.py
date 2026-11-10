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
from contextlib import AbstractContextManager, ExitStack, nullcontext
from dataclasses import dataclass
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
from tools.devtools.wayne_qualification_storage import PrivateEvidence

Nonnegative = Annotated[StrictInt, Field(ge=0, le=2**64 - 1)]
Positive = Annotated[StrictInt, Field(gt=0, le=2**64 - 1)]
Sha256 = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]
UnitAction = Literal[
    "choose_collect",
    "inspect_subject_evidence",
    "draft_from_report",
    "archive_report",
    "status",
    "await_period_proof",
    "arm_one_play_advance",
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
    "period_proof_published",
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
    "await_period_proof": "period_proof_published",
    "reopen": "reopened_and_installed",
    "refresh": "refresh_requested",
    "quit": "quit_requested",
}
# Designed private wire bounds, equal to the native adapter. These are not new
# storage, economic, timing or memory qualification policy defaults.
INPUT_BYTES = 4096
OUTPUT_BYTES = 32_768
POLL_SECONDS = 0.25


ControlFailureReason = Literal[
    "control_refused",
    "cold_deadline",
    "wall_deadline",
    "readiness_deadline",
    "navigation_deadline",
    "send_deadline",
    "response_deadline",
    "response_ended",
    "transport_timeout",
    "transport_error",
    "driver_failure",
]
ControlPhase = Literal[
    "socket_admission",
    "initial_readiness",
    "opening_navigation",
    "organizer_readiness",
    "opening_boundary",
    "advance",
    "recovery",
    "finalization",
]


class ControlRefusal(ValueError):
    """A bounded reason identifies the failing operation without publishing transport text."""

    def __init__(self, message: str, *, reason: ControlFailureReason = "control_refused") -> None:
        super().__init__(message)
        self.reason = reason


def _failure_reason(error: BaseException) -> ControlFailureReason:
    if isinstance(error, ControlRefusal):
        return error.reason
    if isinstance(error, TimeoutError):
        return "transport_timeout"
    if isinstance(error, OSError):
        return "transport_error"
    return "driver_failure"


@dataclass(frozen=True)
class ColdControlWindow:
    started_ns: int
    maximum_seconds: int

    @property
    def deadline_ns(self) -> int:
        return self.started_ns + self.maximum_seconds * 1_000_000_000

    def clock_record(self) -> dict[str, int]:
        return {
            "version": 1,
            "cold_started_monotonic_ns": self.started_ns,
            "cold_deadline_monotonic_ns": self.deadline_ns,
        }


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
    version: Literal[5]

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


class Standing(FrozenRecord):
    partner_actor_id: Nonnegative
    authorized: StrictBool
    paused_reason: (
        Literal["explicit", "insufficient_committed_time", "insufficient_available_time"] | None
    )

    @model_validator(mode="after")
    def authorized_status(self) -> Self:
        if self.authorized != (self.paused_reason is None):
            raise ValueError("standing authorization disagrees with its installed pause reason")
        return self


class PendingFreight(FrozenRecord):
    original_commitment_id: Bytes32
    material_commitment_id: Bytes32
    mandate_id: Bytes32
    dispatch_period: Positive
    first_response_receipt_id: Bytes32 | None


class ResponseHistory(FrozenRecord):
    original_commitment_id: Bytes32
    period: Positive
    practice_receipt_id: Bytes32
    first_response_receipt_id: Bytes32 | None


class InstalledOrganizer(FrozenRecord):
    period: Nonnegative
    actor_id: Nonnegative
    authority_id: Bytes16
    content_digest: Bytes32
    resource_digest: Bytes32
    standing: Standing
    available_hours: Nonnegative
    contact_hours: Nonnegative
    hold_reviewable: StrictBool
    pause_reviewable: StrictBool
    resume_reviewable: StrictBool
    pending_freight: Annotated[tuple[PendingFreight, ...], Field(max_length=32)]
    aid_response_history: Annotated[tuple[ResponseHistory, ...], Field(max_length=32)]

    @model_validator(mode="after")
    def unique_authority(self) -> Self:
        if len({r.original_commitment_id for r in self.pending_freight}) != len(
            self.pending_freight
        ) or len({r.practice_receipt_id for r in self.aid_response_history}) != len(
            self.aid_response_history
        ):
            raise ValueError("installed organizer repeated an original or receipt")
        return self


class PlayInterlock(FrozenRecord):
    phase: Literal["armed", "paused_after_enqueue"]
    arm_sequence: Positive
    play_sequence: Positive | None
    campaign_id: Campaign
    scope_epoch: Nonnegative
    start_tick: Nonnegative
    start_generation: Nonnegative
    target_tick: Positive
    request_id: Positive | None
    pending_at_pause: StrictBool
    playing_after_pause: StrictBool | None

    def arm_identity(self) -> tuple[str, int, int, int, int, int]:
        return (
            self.campaign_id,
            self.scope_epoch,
            self.arm_sequence,
            self.start_tick,
            self.start_generation,
            self.target_tick,
        )

    @model_validator(mode="after")
    def exact_enqueue(self) -> Self:
        if self.target_tick != self.start_tick + 1:
            raise ValueError("play interlock must bind exactly one subsequent period")
        if self.phase == "armed":
            if (
                self.request_id is not None
                or self.play_sequence is not None
                or self.pending_at_pause
                or self.playing_after_pause is not None
            ):
                raise ValueError("armed playback cannot claim a completed enqueue")
        elif (
            self.play_sequence is None
            or self.play_sequence <= self.arm_sequence
            or self.request_id is None
            or not self.pending_at_pause
            or self.playing_after_pause is not False
        ):
            raise ValueError("one-close playback lacks its actual paused pending enqueue")
        return self


class PeriodProof(FrozenRecord):
    campaign_id: Campaign
    scope_epoch: Nonnegative
    foundation_sha256: Sha256
    policy_sha256: Sha256
    generation: Nonnegative
    tick: Positive
    tick_content_hash: Sha256
    world_hash: Sha256
    envelope_digest: Sha256
    request_id: Positive
    archive_verified_tick: Positive
    material_record_sha256: Sha256


class ControlState(FrozenRecord):
    advance_request_id: Positive | None
    period_proof: PeriodProof | None
    installed_organizer: InstalledOrganizer | None
    play_interlock: PlayInterlock | None
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

    @property
    def cold_organizer_ready(self) -> bool:
        return (
            self.phase in ("Ready", "Complete")
            and self.scope_epoch is not None
            and self.primary_view == "Organizer"
            and self.opening_stage == "Game"
            and not (
                self.splash_visible
                or self.menu_open
                or self.lifecycle_pending
                or self.advance_pending
                or self.organizer_pending
                or self.organizer_status_due
            )
            and self.viewed_tick == self.durable_tick == self.organizer_period
            and self.installed_organizer is not None
            and self.installed_organizer.period == self.durable_tick
        )

    @property
    def period_actionable(self) -> bool:
        return (
            self.cold_organizer_ready and self.perspective == "PlayerKnowledge" and not self.playing
        )

    def period_identity(self) -> tuple[object, ...]:
        return (
            self.campaign_id,
            self.scope_epoch,
            self.foundation_sha256,
            self.generation,
            self.durable_tick,
            self.viewed_tick,
            self.tick_content_hash,
            self.world_hash,
            self.advance_request_id,
        )

    @property
    def selected_allocation(self) -> Allocation | None:
        if self.allocation_error is not None:
            return None
        if self.choice == "collect":
            slot = self.collection_allocation
            return slot if isinstance(slot, CollectionAllocation) else None
        if self.choice in ("local_aid", "remote_aid"):
            aid = self.aid_allocation
            return aid if isinstance(aid, AidAllocation) else None
        return "none"

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
    allocation: Allocation
    choice: Literal[
        "collect",
        "remote_aid",
        "local_aid",
        "inquiry_work_lost",
        "inquiry_maintenance_received",
        "reinforce",
        "hold",
        "pause_standing",
        "resume_standing",
    ]

    @model_validator(mode="after")
    def offered_amount(self) -> Self:
        if self.choice.startswith("inquiry_"):
            if self.allocation != "none":
                raise ValueError("inquiry cannot authorize an allocation")
        else:
            SelectedAllocation.model_validate(
                {"choice": self.choice, "allocation": self.allocation}
            )
        return self

    def at_period(self, period: int) -> PlannedChoice:
        return PlannedChoice(period=period, choice=self.choice, allocation=self.allocation)


SMOKE_DECISIONS = (
    PlannedChoice(
        period=1,
        choice="remote_aid",
        allocation=AidAllocation(aid=AidAmounts(food_quantity=1, cash_micros="0")),
    ),
    PlannedChoice(period=2, choice="pause_standing", allocation="none"),
)
WALK_FIXED_DECISIONS = (
    PlannedChoice(
        period=1,
        choice="collect",
        allocation=CollectionAllocation(
            collection=CollectionAmount(target_cash_micros="1450000000")
        ),
    ),
    PlannedChoice(
        period=2,
        choice="local_aid",
        allocation=AidAllocation(aid=AidAmounts(food_quantity=1, cash_micros="0")),
    ),
    PlannedChoice(
        period=3,
        choice="remote_aid",
        allocation=AidAllocation(aid=AidAmounts(food_quantity=2, cash_micros="280000000")),
    ),
    SMOKE_DECISIONS[1].at_period(4),
)


def walk_cash(period: int) -> PlannedChoice:
    return PlannedChoice(
        period=period,
        choice="local_aid",
        allocation=AidAllocation(aid=AidAmounts(food_quantity=0, cash_micros="1000000000")),
    )


def walk_resume(period: int) -> PlannedChoice:
    return PlannedChoice(period=period, choice="resume_standing", allocation="none")


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


def remaining_control_time(
    deadline: float,
    wall_deadline: float | None,
    on_wall_expired: Callable[[], None] | None,
) -> float:
    now = time.monotonic()
    if wall_deadline is not None:
        if wall_deadline <= now:
            if on_wall_expired is not None:
                on_wall_expired()
            raise ControlRefusal("smoke wall deadline exceeded", reason="wall_deadline")
        deadline = min(deadline, wall_deadline)
    return deadline - now


class ControlChannel:
    """Exactly one outstanding UI input on the explicitly admitted private socket."""

    def __init__(
        self,
        connection: socket.socket,
        campaign: str,
        initial_tick: int,
        *,
        check_capture: Callable[[], None] | None = None,
        on_refusal: Callable[[BaseException], None] | None = None,
        on_observed: Callable[[ControlState], None] | None = None,
        wall_deadline: float | None = None,
        on_wall_expired: Callable[[], None] | None = None,
    ) -> None:
        if str(UUID(campaign)) != campaign or UUID(campaign).int == 0:
            raise ControlRefusal("native control campaign must be a nonzero canonical UUID")
        if type(initial_tick) is not int or not 0 <= initial_tick <= 2**64 - 1:
            raise ControlRefusal("native control opening period invalid")
        self.connection = connection
        self.campaign = campaign
        self.initial_tick = initial_tick
        self.state: ControlState | None = None
        self.last_response: ControlResponse | None = None
        self.response_bytes = bytearray()
        self.records: list[ActionObservation] = []
        self._review_witness: ControlState | None = None
        self.sequence = 0
        self.foundation: str | None = None
        self.scope_epoch: int | None = None
        self.closed = False
        self.ready = False
        self._playback_admitted = False
        self._settling_tick: int | None = None
        self._on_refusal = on_refusal
        self._check_capture = check_capture
        self._on_observed = on_observed
        self._wall_deadline = wall_deadline
        self._on_wall_expired = on_wall_expired

    def close(self) -> None:
        self.closed = True
        self.connection.close()

    def _refuse(
        self, message: str, *, reason: ControlFailureReason = "control_refused"
    ) -> ControlRefusal:
        failure = ControlRefusal(message, reason=reason)
        try:
            if self._on_refusal is not None:
                self._on_refusal(failure)
        finally:
            self.close()
        return failure

    def _receive(self, deadline: float) -> ControlResponse:
        raw = self.response_bytes
        while b"\n" not in raw:
            if self._check_capture is not None:
                self._check_capture()
            remaining = remaining_control_time(deadline, self._wall_deadline, self._on_wall_expired)
            if remaining <= 0:
                raise ControlRefusal(
                    "native control response deadline exceeded", reason="response_deadline"
                )
            self.connection.settimeout(min(remaining, 0.25) if self._check_capture else remaining)
            try:
                part = self.connection.recv(OUTPUT_BYTES + 1 - len(raw))
            except TimeoutError:
                remaining = remaining_control_time(
                    deadline, self._wall_deadline, self._on_wall_expired
                )
                if self._check_capture is not None and remaining > 0:
                    continue
                raise ControlRefusal(
                    "native control response deadline exceeded", reason="response_deadline"
                ) from None
            raw.extend(part)
            if remaining_control_time(deadline, self._wall_deadline, self._on_wall_expired) < 0:
                raise ControlRefusal(
                    "native control response deadline exceeded", reason="response_deadline"
                )
            if not part:
                raise ControlRefusal(
                    "native control response ended before a complete frame", reason="response_ended"
                )
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
        if action == "await_period_proof" and event == "period_proof_published":
            proof = current.period_proof
            if (
                prior is None
                or not prior.period_actionable
                or prior.period_proof is not None
                or prior.advance_request_id is None
                or current.period_identity() != prior.period_identity()
                or not current.period_actionable
                or current.archive_verified_tick != current.durable_tick
                or proof is None
                or (
                    proof.campaign_id,
                    proof.scope_epoch,
                    proof.foundation_sha256,
                    proof.generation,
                    proof.tick,
                    proof.tick,
                    proof.tick_content_hash,
                    proof.world_hash,
                    proof.request_id,
                )
                != current.period_identity()
                or proof.archive_verified_tick != current.durable_tick
            ):
                raise ControlRefusal(
                    "native period proof differs from its actionable original close"
                )
        lock = current.play_interlock
        old_lock = prior.play_interlock if prior is not None else None
        if (
            action == "arm_one_play_advance"
            and event == "applied"
            and (
                lock is None
                or prior is None
                or lock.phase != "armed"
                or lock.arm_sequence != self.sequence
                or (lock.campaign_id, lock.scope_epoch, lock.start_tick, lock.start_generation)
                != (prior.campaign_id, prior.scope_epoch, prior.durable_tick, prior.generation)
                or lock.play_sequence is not None
                or prior.playing
                or prior.advance_pending
            )
        ):
            raise ControlRefusal("arm acknowledgement differs from its exact installed scope")
        if (
            action == "play"
            and old_lock is not None
            and old_lock.phase == "armed"
            and (
                lock is None
                or lock.arm_identity() != old_lock.arm_identity()
                or lock.phase == "paused_after_enqueue"
                and lock.play_sequence != self.sequence
            )
        ):
            raise ControlRefusal("ordinary Play lost its exact arm and sequence")
        synchronous = (
            lock is not None
            and lock.phase == "paused_after_enqueue"
            and lock.play_sequence == self.sequence
        )
        starts_playback = (
            action == "play" and event == "applied" and (current.playing or synchronous)
        )
        automatic = action in {"status", "play", "pause"} and (
            self._playback_admitted or starts_playback or self._settling_tick is not None
        )
        if prior is not None and self.ready:
            if current.generation < prior.generation:
                raise ControlRefusal("native control generation moved backward")
            if action in ("review", "confirm") and (
                current.generation != prior.generation
                or current.viewed_tick != prior.viewed_tick
                or current.viewed_tick != current.durable_tick
                or current.phase != "Ready"
            ):
                raise ControlRefusal("native organizer review context changed")
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
                self._settling_tick = (
                    lock.target_tick
                    if lock is not None and lock.phase == "paused_after_enqueue"
                    else current.durable_tick + int(current.advance_pending)
                )
            self._playback_admitted = False
            if (
                not current.advance_pending
                and not current.organizer_pending
                and not current.organizer_status_due
                and (self._settling_tick is None or current.durable_tick >= self._settling_tick)
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

    def _exchange(
        self, action: Action, timeout: float, *, retain_ready: bool = False
    ) -> ControlResponse:
        if self._check_capture is not None:
            self._check_capture()
        if self.closed:
            raise ControlRefusal("native control channel is closed after refusal")
        started = time.monotonic_ns()
        deadline = time.monotonic() + _duration(timeout)
        prior = self.state
        try:
            request = ControlInput(
                version=5,
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
        try:
            remaining = remaining_control_time(deadline, self._wall_deadline, self._on_wall_expired)
            if remaining <= 0:
                raise ControlRefusal(
                    "native control send deadline exceeded", reason="send_deadline"
                )
            self.connection.settimeout(remaining)
            self.sequence = request.sequence
            self.last_response = None
            self.response_bytes.clear()
            try:
                self.connection.sendall(frame)
            except TimeoutError:
                remaining_control_time(deadline, self._wall_deadline, self._on_wall_expired)
                raise
            reply = self._receive(deadline)
            self.last_response = reply
            if reply.sequence != self.sequence:
                raise ControlRefusal("native control response sequence differs")
            if self._on_observed is not None:
                self._on_observed(reply.state)
            self._bind(reply.state, action, reply.event)
            if (
                not self.records
                or action != "status"
                or reply.state != self.records[-1].state
                or retain_ready
                and reply.event == "observed"
                and reply.state.cold_organizer_ready
            ):
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
            if (
                action not in ("status", "capture_frame")
                or reply.event != expected_event(action)
                or reply.reason is not None
                or reply.state != self._review_witness
            ):
                self._review_witness = None
            self.state = reply.state
            return reply
        except (OSError, ControlRefusal) as error:
            raise self._refuse(
                "native control exchange refused: " + str(error), reason=_failure_reason(error)
            ) from error

    def observe(self, timeout: float, *, retain_ready: bool = False) -> ControlState:
        reply = self._exchange("status", timeout, retain_ready=retain_ready)
        if reply.event != "observed" and not (
            reply.event == "refused" and reply.reason == "control_stale_or_unavailable"
        ):
            raise self._refuse("native status request refused")
        return reply.state

    def witness_blocked_editor(self, action: Literal["review", "confirm"], timeout: float) -> None:
        """Record an actual refused ordinary action for this exact invalid draft."""
        prior = self.state
        if (
            prior is None
            or prior.phase != "Ready"
            or prior.organizer_period != prior.viewed_tick
            or prior.viewed_tick != prior.durable_tick
            or prior.allocation_error is None
            or prior.reviewed_command is not None
            or prior.preview is not None
            or prior.commitment is not None
        ):
            raise ControlRefusal("expected refusal requires the installed invalid draft")
        reply = self._exchange(action, timeout)
        if (
            reply.event != "refused"
            or reply.reason not in ("ordinary_handler_refused", "control_stale_or_unavailable")
            or reply.state != prior
        ):
            raise self._refuse("invalid allocation action changed state or escaped refusal")

    def perform(
        self, action: Action, timeout: float, *, allow_review_refusal: bool = False
    ) -> ControlState:
        prior = self.state
        if action == "review" and (
            prior is None or prior.phase != "Ready" or prior.selected_allocation is None
        ):
            raise self._refuse("native review requires a valid current selection")
        if action == "confirm" and (self._review_witness is None or self._review_witness != prior):
            raise self._refuse("native confirmation requires this channel's current review")
        reply = self._exchange(action, timeout)
        observed_refusal = (
            allow_review_refusal
            and action == "review"
            and reply.event == "refused"
            and reply.reason == "ordinary_response_refused"
            and reply.state.preview is not None
            and reply.state.preview.refusal is not None
        )
        if not observed_refusal and (
            reply.event != expected_event(action) or reply.reason is not None
        ):
            reason = f": {reply.reason}" if reply.reason is not None else ""
            raise self._refuse("ordinary native handler refused the requested action" + reason)
        if action == "step" and (
            reply.state.phase not in {"Ready", "Complete"}
            or reply.state.viewed_tick != reply.state.durable_tick
            or reply.state.advance_pending
        ):
            raise self._refuse("native period was not completely installed")
        if action == "inspect_practices" and reply.state.inspector != "Practices":
            raise self._refuse("native practice list did not open")
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
            raise self._refuse("native handler applied a different choice")
        bounded_play = (
            action == "play"
            and reply.state.play_interlock is not None
            and reply.state.play_interlock.phase == "paused_after_enqueue"
            and reply.state.play_interlock.play_sequence == self.sequence
        )
        if action in ("play", "pause") and reply.state.playing != (
            action == "play" and not bounded_play
        ):
            raise self._refuse("native playback acknowledgment has the wrong scheduling state")
        if action == "review":
            command = reply.state.reviewed_command
            preview = reply.state.preview
            if (
                prior is None
                or command is None
                or preview is None
                or (preview.refusal is not None) != observed_refusal
                or prior.choice != command.choice
                or prior.selected_allocation != command.allocation
                or reply.state.choice != command.choice
                or reply.state.selected_allocation != command.allocation
                or bytes(command.campaign_id) != UUID(self.campaign).bytes
                or command.expected_period != reply.state.durable_tick
                or preview.choice != command.choice
                or preview.allocation != command.allocation
                or preview.current_period != command.expected_period
                or preview.resolves_period != command.expected_period + 1
            ):
                raise self._refuse("native preview differs from its selected original")
            self._review_witness = None if observed_refusal else reply.state
        if action == "confirm" and (
            prior is None
            or prior.preview is None
            or reply.state.reviewed_command is not None
            or reply.state.preview is not None
            or reply.state.commitment is None
            or reply.state.commitment.resolves_period != prior.preview.resolves_period
            or reply.state.commitment.command != prior.reviewed_command
        ):
            raise self._refuse("native acceptance failed to consume its reviewed original")
        return reply.state


def write_observations(
    destination: Path, channel: ControlChannel, status: Literal["incomplete", "completed"]
) -> None:
    """Atomic evidence of local actions; never a named qualification result."""
    payload = ControlsEvidence(
        version=5,
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


def whole_dollars(micros: str) -> str:
    units, remainder = divmod(int(micros), 1_000_000)
    if remainder:
        raise ControlRefusal("ordinary organizer editor accepts whole dollars")
    return str(units)


def edit_amount(
    channel: ControlChannel,
    field: AmountField,
    target: str,
    timeout: float,
    *,
    witness_refusal: bool = False,
) -> None:
    current = channel.perform(FocusAmount(focus_amount=field), timeout)
    if current.focused_amount != field or current.amount_text is None:
        raise ControlRefusal("ordinary amount editor did not expose its focused text")
    raw = current.amount_text

    def key(value: AmountKey, expected: str, *, mutation: bool) -> ControlState:
        state = channel.perform(value, timeout)
        if state.focused_amount != field or state.amount_text != expected:
            raise ControlRefusal("ordinary amount editor readback differs from the key")
        if mutation and (state.preview is not None or state.reviewed_command is not None):
            raise ControlRefusal("editing allocation preserved an obsolete review")
        return state

    key(AmountKey(amount_key="home"), raw, mutation=False)
    while raw:
        raw = raw[1:]
        key(AmountKey(amount_key="delete"), raw, mutation=True)
    if witness_refusal:
        channel.witness_blocked_editor("review", timeout)
        key(AmountKey(amount_key=CharacterKey(character="-")), "-", mutation=True)
        channel.witness_blocked_editor("confirm", timeout)
        key(AmountKey(amount_key="backspace"), "", mutation=True)
    for char in target:
        raw += char
        key(AmountKey(amount_key=CharacterKey(character=char)), raw, mutation=True)


def submit_choice(
    channel: ControlChannel,
    choice: PlannedChoice,
    timeout: float,
    *,
    exercise_editor: bool = False,
    on_stage: Callable[[str, ControlState], None] | None = None,
    allow_review_refusal: bool = False,
) -> ControlState | None:
    """Submit the selected amount through a fresh witnessed Review and Confirm."""
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
            "collect": "choose_collect",
            "remote_aid": "choose_remote_aid",
            "local_aid": "choose_local_aid",
            "inquiry_work_lost": "choose_inquiry_work_lost",
            "inquiry_maintenance_received": "choose_inquiry_maintenance_received",
            "reinforce": "choose_reinforce",
            "hold": "choose_hold",
        }
        channel.perform("inspect_practices", timeout)
        channel.perform(actions[choice.choice], timeout)
    selected = channel.state
    if selected is None:
        raise ControlRefusal("ordinary practice selection lost its current state")
    if exercise_editor or selected.selected_allocation != choice.allocation:
        if isinstance(choice.allocation, CollectionAllocation):
            if exercise_editor:
                channel.perform("review", timeout)
                channel.perform("close_inspector", timeout)
            edit_amount(
                channel,
                "contribution",
                whole_dollars(choice.allocation.collection.target_cash_micros),
                timeout,
                witness_refusal=exercise_editor,
            )
        elif isinstance(choice.allocation, AidAllocation):
            food, cash = choice.allocation.aid.food_quantity, choice.allocation.aid.cash_micros
            if exercise_editor:
                edit_amount(channel, "food", "0", timeout)
                edit_amount(channel, "cash", "0", timeout)
                channel.witness_blocked_editor("review", timeout)
            edit_amount(channel, "food", str(food), timeout)
            edit_amount(channel, "cash", whole_dollars(cash), timeout)
    if channel.state is None or channel.state.selected_allocation != choice.allocation:
        raise ControlRefusal("ordinary selection differs from the requested allocation")
    if on_stage is not None:
        on_stage("selected", channel.state)
    reviewed = (
        channel.perform("review", timeout, allow_review_refusal=True)
        if allow_review_refusal
        else channel.perform("review", timeout)
    )
    if reviewed.preview is not None and reviewed.preview.refusal is not None:
        if on_stage is not None:
            on_stage("refused", reviewed)
        return reviewed
    if on_stage is not None:
        on_stage("reviewed", reviewed)
    accepted = channel.perform("confirm", timeout)
    if on_stage is not None:
        on_stage("confirmed", accepted)
    wait_ready(channel, timeout, organizer=True)
    return None


def wait_ready(
    channel: ControlChannel,
    timeout: float,
    *,
    organizer: bool,
    cold: bool = False,
    period_proof: bool = False,
) -> ControlState:
    deadline = time.monotonic() + _duration(timeout)
    while time.monotonic() < deadline:
        current = channel.observe(
            max(0.001, deadline - time.monotonic()), retain_ready=cold or period_proof
        )
        if (
            not organizer
            and current.scope_epoch is not None
            and current.splash_visible
            and current.opening_stage == "Warning"
        ):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            current = channel.perform("continue_warning", remaining)
        if (
            current.phase in {"Ready", "Complete"}
            and (
                not (cold or period_proof)
                or current.cold_organizer_ready
                and channel.last_response is not None
                and channel.last_response.event == "observed"
                and channel.last_response.reason is None
            )
            and (
                not period_proof or current.perspective == "PlayerKnowledge" and not current.playing
            )
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
    raise ControlRefusal("native control readiness deadline exceeded", reason="readiness_deadline")


def wait_period_ready(channel: ControlChannel, timeout: float) -> ControlState:
    """Retain the accepted ordinary actionable endpoint before requesting private proof."""
    return wait_ready(channel, timeout, organizer=True, period_proof=True)


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
    on_installed: Callable[[ControlChannel, Path, ControlState], None] | None = None,
    play_penultimate_close: bool = False,
    on_opened: Callable[[ActionObservation], None] | None = None,
    on_observed: Callable[[ControlState], None] | None = None,
    cold_window: ColdControlWindow | None = None,
    wall_deadline: float | None = None,
    on_wall_expired: Callable[[], None] | None = None,
    on_spawned: Callable[[Literal["runtime", "client"], subprocess.Popen[bytes]], None]
    | None = None,
    on_stopped: Callable[[], None] | None = None,
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
    cold_deadline = None
    if cold_window is not None:
        cold_deadline = cold_window.deadline_ns / 1e9
        PrivateEvidence(directory).publish_json(
            "native-cold-clock.json", cold_window.clock_record()
        )

    phase: ControlPhase = "socket_admission"
    attempted_diagnostic = False

    def diagnose(error: BaseException) -> None:
        nonlocal attempted_diagnostic
        if cold_window is None or attempted_diagnostic:
            return
        attempted_diagnostic = True
        try:
            PrivateEvidence(directory).publish_json(
                "native-control-failure.json",
                {
                    **cold_window.clock_record(),
                    "failed_monotonic_ns": time.monotonic_ns(),
                    "phase": phase,
                    "reason": _failure_reason(error),
                },
            )
        except BaseException as publication:
            raise BaseExceptionGroup(
                "native control and diagnostic publication failed", [error, publication]
            ) from None

    def expired_wall() -> None:
        # Only remaining_control_time's observed wall expiry invokes this callback.
        # Save that cause before the runner publishes its divergence and raises.
        diagnostic_failure: BaseException | None = None
        try:
            diagnose(ControlRefusal("smoke wall deadline exceeded", reason="wall_deadline"))
        except BaseException as error:
            diagnostic_failure = error
        try:
            if on_wall_expired is not None:
                on_wall_expired()
        except BaseException as budget:
            if diagnostic_failure is not None:
                raise BaseExceptionGroup(
                    "smoke budget and control diagnostic failed", [budget, diagnostic_failure]
                ) from None
            raise
        if diagnostic_failure is not None:
            raise diagnostic_failure

    with ExitStack() as resources:
        temporary = tempfile.TemporaryDirectory(prefix="babylon-q-", dir="/tmp", delete=False)
        release_directory = True

        def cleanup() -> None:
            if release_directory:
                temporary.cleanup()

        def spawned(role: Literal["runtime", "client"], child: subprocess.Popen[bytes]) -> None:
            nonlocal release_directory
            if on_stopped is not None:
                release_directory = False
            if on_spawned is not None:
                on_spawned(role, child)

        def stopped() -> None:
            nonlocal release_directory
            if on_stopped is not None:
                on_stopped()
            release_directory = True

        resources.callback(cleanup)
        endpoint = Path(temporary.name) / "control.sock"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:

            def opening_timeout() -> float:
                if cold_deadline is None and wall_deadline is None:
                    return operation_timeout
                deadline = time.monotonic() + operation_timeout
                if cold_deadline is not None:
                    deadline = min(deadline, cold_deadline)
                remaining = remaining_control_time(deadline, wall_deadline, expired_wall)
                if remaining <= 0:
                    raise ControlRefusal(
                        "process-cold installation deadline exceeded", reason="cold_deadline"
                    )
                return min(operation_timeout, remaining)

            try:
                listener.bind(str(endpoint))
                endpoint.chmod(0o600)
                listener.listen(1)
                listener.settimeout(opening_timeout())
            except BaseException as error:
                diagnose(error)
                raise

            def admit_channel(
                client: subprocess.Popen[bytes], capture: CaptureMonitor | None
            ) -> ControlChannel:
                listener.settimeout(opening_timeout())
                try:
                    connection, _address = listener.accept()
                except TimeoutError:
                    opening_timeout()
                    raise
                try:
                    _pid, uid, _gid = struct.unpack(
                        "3i",
                        connection.getsockopt(
                            socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")
                        ),
                    )
                    if uid != os.getuid() or _pid != client.pid:
                        raise ControlRefusal(
                            "native control socket peer is not the exact owned client"
                        )
                    if capture is not None:
                        capture.check()
                    connection.settimeout(opening_timeout())
                    # App construction waits here before connecting the runtime
                    # pipe. The capture context has already finished its first
                    # authenticated sample before yielding to this driver.
                    connection.sendall(
                        StartupAdmission(
                            version=5,
                            campaign_id=str(initial_target.campaign),
                            phase="capture_ready",
                        )
                        .model_dump_json()
                        .encode("ascii")
                        + b"\n"
                    )
                    return ControlChannel(
                        connection,
                        str(initial_target.campaign),
                        initial_tick,
                        check_capture=capture.check if capture is not None else None,
                        on_refusal=diagnose,
                        on_observed=on_observed,
                        wall_deadline=wall_deadline,
                        on_wall_expired=expired_wall,
                    )
                except BaseException as error:
                    try:
                        diagnose(error)
                    finally:
                        connection.close()
                    if isinstance(error, TimeoutError):
                        opening_timeout()
                    raise

            def controlled(client: subprocess.Popen[bytes], capture: CaptureMonitor | None) -> None:
                nonlocal phase
                try:
                    channel = admit_channel(client, capture)
                except BaseException as error:
                    diagnose(error)
                    raise
                phase = "initial_readiness"
                result: Literal["incomplete", "completed"] = "incomplete"
                failure: BaseException | None = None
                try:
                    current = wait_ready(channel, opening_timeout(), organizer=False)
                    phase = "opening_navigation"
                    opening_deadline = time.monotonic() + opening_timeout()
                    while current.splash_visible or current.menu_open:
                        remaining = opening_deadline - time.monotonic()
                        if remaining <= 0:
                            raise ControlRefusal(
                                "native opening navigation deadline exceeded",
                                reason="navigation_deadline",
                            )
                        if current.splash_visible and current.opening_stage == "Warning":
                            channel.perform("continue_warning", remaining)
                        elif current.opening_stage == "Title":
                            channel.perform("continue_title", remaining)
                        time.sleep(min(POLL_SECONDS, max(0, opening_deadline - time.monotonic())))
                        remaining = opening_deadline - time.monotonic()
                        if remaining <= 0:
                            raise ControlRefusal(
                                "native opening navigation deadline exceeded",
                                reason="navigation_deadline",
                            )
                        current = channel.observe(remaining)
                        if time.monotonic() > opening_deadline:
                            raise ControlRefusal(
                                "native opening navigation deadline exceeded",
                                reason="navigation_deadline",
                            )
                    if current.primary_view != "Organizer":
                        channel.perform("open_organizer", opening_timeout())
                    phase = "organizer_readiness"
                    current = wait_ready(
                        channel, opening_timeout(), organizer=True, cold=on_opened is not None
                    )
                    phase = "opening_boundary"
                    if on_opened is not None:
                        on_opened(channel.records[-1])
                    on_boundary(current)
                    if on_installed is not None:
                        on_installed(channel, endpoint.parent, current)
                    for offset in range(periods):
                        phase = "advance"
                        if planned := schedule.get(current.durable_tick + 1):
                            submit_choice(channel, planned, operation_timeout)
                        before = current.durable_tick
                        if play_penultimate_close and offset + 2 == periods:
                            arm = channel.perform(
                                "arm_one_play_advance", operation_timeout
                            ).play_interlock
                            if arm is None or arm.phase != "armed" or arm.start_tick != before:
                                raise ControlRefusal("ordinary Play lacks its one-close interlock")
                            channel.perform("play", operation_timeout)
                            play_sequence = channel.sequence
                            deadline = time.monotonic() + operation_timeout
                            while True:
                                observed = channel.state
                                if observed is None:
                                    raise ControlRefusal("lost the admitted playback state")
                                witness = observed.play_interlock
                                if (
                                    witness is None
                                    or witness.arm_identity() != arm.arm_identity()
                                    or observed.durable_tick > arm.target_tick
                                ):
                                    raise ControlRefusal(
                                        "ordinary Play lost its specific one-close interlock"
                                    )
                                if (
                                    witness.phase == "paused_after_enqueue"
                                    and witness.play_sequence == play_sequence
                                ):
                                    break
                                remaining = deadline - time.monotonic()
                                if remaining <= 0 or not observed.playing:
                                    raise ControlRefusal(
                                        "ordinary Play stopped without its admitted enqueue"
                                    )
                                time.sleep(min(POLL_SECONDS, remaining))
                                channel.observe(max(0.001, deadline - time.monotonic()))
                            paused = channel.perform(
                                "pause", max(0.001, deadline - time.monotonic())
                            )
                            if paused.play_interlock != witness:
                                raise ControlRefusal(
                                    "ordinary Pause changed its frozen request receipt"
                                )
                        else:
                            channel.perform("step", operation_timeout)
                        qualified = "BABYLON_QUALIFICATION_MATERIAL_DIRECTORY" in client_environment
                        current = (
                            wait_period_ready(channel, operation_timeout)
                            if qualified
                            else wait_ready(channel, operation_timeout, organizer=True)
                        )
                        if current.durable_tick != before + 1 or current.playing:
                            raise ControlRefusal(
                                "ordinary advance installed outside the requested single close"
                            )
                        if qualified:
                            current = channel.perform("await_period_proof", operation_timeout)
                        on_boundary(current)
                        phase = "recovery"
                        current = channel.perform("reopen", operation_timeout)
                        current = wait_ready(channel, operation_timeout, organizer=True)
                        on_recovery(current)
                        if on_installed is not None:
                            on_installed(channel, endpoint.parent, current)
                        write_observations(
                            directory / "native-controls.json", channel, "incomplete"
                        )
                    phase = "finalization"
                    if capture is not None:
                        capture.finish()
                    channel.perform("quit", operation_timeout)
                    result = "completed"
                except BaseException as error:
                    failure = error
                    try:
                        diagnose(error)
                    except BaseException as diagnostic_failure:
                        failure = diagnostic_failure
                        raise
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
                on_spawned=spawned if on_spawned is not None or on_stopped is not None else None,
                on_stopped=stopped if on_stopped is not None else None,
            )
