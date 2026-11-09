"""Join native witnesses inside the existing national qualification evaluator.

This module neither drives the economy nor creates capture authority. The owned
supervisor produces the files. Original accepted commands, shared Rust accounting,
PostgreSQL/Archive evidence and combined-role capture must agree before admission.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from io import BytesIO
from itertools import pairwise
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID

from PIL import Image, PngImagePlugin
from pydantic import (
    AwareDatetime,
    Field,
    JsonValue,
    StrictBool,
    StrictInt,
    StrictStr,
    TypeAdapter,
    field_validator,
    model_validator,
)
from tools.devtools.national_storage_qualification import (
    AidPracticeEvidence,
    CombinedMemoryEvidence,
    EconomicBoundary,
    EconomicSummary,
    FixedPeriodMemory,
    FrozenRecord,
    MeasurementMode,
    NativeTimings,
    Nonnegative,
    PlayableBoundary,
    PlayableReport,
    Policy,
    Positive,
    ProductionRenewalEvidence,
    Sha256,
    Snapshot,
    TradeBoundary,
    TradeSummary,
    authenticate_combined_memory_capture,
    evaluate_combined_memory,
    strict_json_bytes,
    verify_economic_summary,
)
from tools.devtools.national_windowed_qualification import (
    ActionObservation,
    AidAllocation,
    Bytes32,
    CollectionAllocation,
    Command,
    Commitment,
    ControlsEvidence,
    ControlState,
    EssentialServices,
    FoodProvision,
    Observation,
    OpeningAssessment,
    ParticipationTime,
    PartnerReport,
    Preview,
    expected_event,
)
from tools.devtools.wayne_qualification_storage import PrivateEvidence, Reference, member_run

# Designed framing bounds, not alternative economic or save-growth policy.
MATERIAL_RECORD_BYTES = 4_194_304  # Matches the native record writer.
CONTROLS_RECORD_BYTES = 134_217_728
MANIFEST_BYTES = 1_048_576
U64 = Annotated[StrictInt, Field(ge=0, le=2**64 - 1)]


class NativeRecord(FrozenRecord):
    @field_validator("version", mode="before", check_fields=False)
    @classmethod
    def exact_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("native evidence version must be an exact integer")
        return value


class NativeFailureCause(NativeRecord):
    failure_type: StrictStr
    safe_reason: StrictStr | None


class NativeRunIncomplete(NativeRecord):
    version: Literal[3]
    failed_pair: Reference | None
    status: Literal["incomplete"]
    last_recorded_stage: StrictStr
    complete_boundary_records: Nonnegative
    authenticated_recoveries: Nonnegative
    failure_type: StrictStr
    failures: Annotated[tuple[NativeFailureCause, ...], Field(min_length=1)]


class Artifact(NativeRecord):
    name: Annotated[
        StrictStr,
        Field(
            pattern=r"^(native-controls|material-[0-9]+|advance-[0-9]+|archive-[0-9]+|recovery-[0-9]+-[0-9]+|aid-[0-9a-f]{64})\.json$"
        ),
    ]
    sha256: Sha256


class NativeRunEvidence(NativeRecord):
    version: Literal[5]
    scope: Literal["native_material_timing_recovery_join_v5"]
    measurement_mode: MeasurementMode
    started_monotonic_ns: Nonnegative
    completed_monotonic_ns: Positive
    inputs_sha256: Sha256
    status: Literal["incomplete", "completed"]
    policy_sha256: Sha256
    campaign: StrictStr
    foundation_sha256: Sha256
    graph_foundation_sha256: Sha256
    requested_periods: Positive
    ownership_record_sha256: Sha256
    source_manifest_sha256: Sha256
    executable_manifest_sha256: Sha256
    controls: Artifact
    opening: Artifact
    boundaries: tuple[Artifact, ...]
    advances: tuple[Artifact, ...]
    archives: tuple[Artifact, ...]
    recoveries: tuple[Artifact, ...]
    aid_originals: tuple[Artifact, ...]

    @model_validator(mode="after")
    def exact_roster(self) -> NativeRunEvidence:
        if str(UUID(self.campaign)) != self.campaign or UUID(self.campaign).int == 0:
            raise ValueError("native evidence requires a canonical nonzero campaign")
        rows = (
            self.controls,
            self.opening,
            *self.boundaries,
            *self.advances,
            *self.archives,
            *self.recoveries,
            *self.aid_originals,
        )
        if len({r.name for r in rows}) != len(rows):
            raise ValueError("native evidence artifact roster contains duplicates")
        if self.controls.name != "native-controls.json" or self.opening.name != "material-0.json":
            raise ValueError("native evidence requires its original opening and controls")
        return self


class Opening(NativeRecord):
    campaign: StrictStr
    foundation_sha256: Sha256
    policy_sha256: Sha256
    material_register_sha256: Sha256
    material_register_bytes: Positive


class PartnerSource(NativeRecord):
    actor_id: U64
    subject_id: U64
    source_actor_id: U64
    observed_period: U64
    acquired_period: U64
    observation_id: Bytes32
    receipt_id: Bytes32 | None
    mandate_id: Bytes32
    source_hash: Bytes32
    facts: Annotated[
        OpeningAssessment | FoodProvision | EssentialServices | ParticipationTime,
        Field(discriminator="basis"),
    ]


def validate_membership(
    observation: Observation, receipts: list[dict[str, Any]], actor: int
) -> None:
    if (
        observation.receipt_id is None
        or observation.actor_id != actor
        or len(
            [
                r
                for r in receipts
                if r["receipt_id"] == list(observation.receipt_id)
                and r["actor_id"] == actor
                and r["period"] == observation.acquired_period
                and r["observation_ids"].count(list(observation.observation_id)) == 1
            ]
        )
        != 1
    ):
        raise ValueError("dated report lacks its exact action receipt membership")


def verify_partner_source(
    row: PartnerSource,
    observation: Observation,
    *,
    actor: int,
    period: int,
    source_hash: str,
    grants: list[list[Any]],
) -> None:
    if (
        not isinstance(observation.report, PartnerReport)
        or row.receipt_id is not None
        or row.actor_id != actor
        or row.subject_id != row.source_actor_id
        or row.observed_period != period
        or row.acquired_period != period
        or (period == 0) != isinstance(row.facts, OpeningAssessment)
        or bytes(row.source_hash).hex() != source_hash
        or not any(row.mandate_id)
        or row.model_dump(exclude={"source_hash", "mandate_id", "facts"})
        != observation.model_dump(exclude={"report"})
        or row.facts != observation.report.facts
    ):
        raise ValueError(
            "partner report differs from the controlled reader, dated recipient or authenticated source quantities"
        )
    key = bytes(row.observation_id).hex()
    locator = f"source-actor/{row.source_actor_id}/observed-period/{row.observed_period}/acquired-period/{period}/observation/{key}/action-receipt/automatic-report"
    expected = [
        "organization",
        str(row.subject_id),
        "report-" + key,
        period,
        "derived-scoped-partner-report-v1",
        locator,
    ]
    if grants.count(expected) != 1:
        raise ValueError("dated partner report lacks its exact scoped Archive grant")


def has_later_retained_leg(practices: tuple[AidPracticeEvidence, ...]) -> bool:
    return any(
        first.cash_received_period == first.period
        and first.first_response_period == first.period
        and later.period > first.period
        and later.food_consumption_period == later.period
        and later.qualifying_received_support
        and later.outcome == "aid_response_retained"
        and later.first_response_receipt_id == first.practice_receipt_id
        and later.mandate == first.mandate
        and later.material_commitment_id == first.material_commitment_id
        for first in practices
        for later in practices
    )


class NativeOpening(Opening):
    partner_reports: tuple[PartnerSource, ...]
    graph_foundation_sha256: Sha256
    county_geoids: tuple[Annotated[StrictStr, Field(pattern=r"^[0-9]{5}$")], ...]
    county_roster_sha256: Sha256

    @model_validator(mode="after")
    def exact_roster(self) -> NativeOpening:
        if not self.county_geoids or self.county_geoids != tuple(sorted(set(self.county_geoids))):
            raise ValueError("native opening roster must be ordered, unique and nonempty")
        digest = hashlib.sha256(
            json.dumps(list(self.county_geoids), separators=(",", ":")).encode("ascii")
        ).hexdigest()
        if digest != self.county_roster_sha256:
            raise ValueError("native opening roster digest differs from its exact county set")
        return self


class BoundaryFacts(Opening):
    version: Literal[1]
    tick: Positive
    tick_content_hash: Sha256
    envelope_digest: Sha256
    canonical_receipt_sha256: Sha256
    nominal_world_hash: Sha256
    production_evidence_sha256: Sha256
    production_evidence_body_bytes: Positive
    county_roster_sha256: Sha256
    economic: EconomicBoundary
    trade: TradeBoundary
    production_renewal: ProductionRenewalEvidence | None


class AidBoundary(NativeRecord):
    version: Literal[3]
    partner_reports: tuple[PartnerSource, ...]
    period: Positive
    tick_content_hash: Sha256
    canonical_receipt_sha256: Sha256
    selected_aid: tuple[dict[str, JsonValue], ...]
    independent_practices: tuple[AidPracticeEvidence, ...]


class AidSummary(NativeRecord):
    cash_and_in_kind_postings: Literal["passed", "incomplete"]
    accepted_original_commands: Nonnegative
    time_partition_and_residual_bound: Literal["passed", "incomplete"]
    exact_final_contribution_debit_ledger: Literal["passed", "incomplete"]


class ArchiveFacts(NativeRecord):
    expected_tick: Positive
    durable_tick: Positive
    processed_tick: Positive
    pending_count: Nonnegative
    pending_scope: Literal["requested_prefix"]
    observation_mode: Literal["live_latest", "historical"]
    captured_tail_tick: Positive
    captured_tail_tick_content_hash: Sha256
    dossier_sha256: Sha256


class ArchiveRecord(NativeRecord):
    version: Literal[1]
    scope: Literal["authenticated_archive_dossiers_and_retained_foundation_headers_only"]
    campaign: StrictStr
    foundation_sha256: Sha256
    policy_sha256: Sha256
    graph_foundation_sha256: Sha256
    tick: Positive
    tick_content_hash: Sha256
    archive: ArchiveFacts
    archive_read_elapsed_ns: Nonnegative


class MaterialRecord(NativeRecord):
    version: Literal[5]
    scope: Literal["authenticated_native_material_and_aid_facts_only"]
    runtime_epoch: U64
    observation_generation: U64
    production_read_elapsed_ns: Nonnegative
    presentation_read_elapsed_ns: Nonnegative
    audit_elapsed_ns: Nonnegative
    tick: Nonnegative
    tick_content_hash: Sha256 | None
    opening: NativeOpening | None
    facts: BoundaryFacts | None
    aid: AidBoundary | None
    aid_practices: dict[str, JsonValue]
    economic_summary: EconomicSummary
    aid_summary: AidSummary
    trade_summary: TradeSummary


class RuntimeScope(NativeRecord):
    epoch: U64
    campaign_id: StrictStr


class Tail(NativeRecord):
    resolve_tick: Nonnegative
    tick_content_hash: Sha256 | None
    world_hash: Sha256 | None


class AdvanceRecord(NativeRecord):
    version: Literal[1]
    scope: Literal["native_enqueue_commit_archive_timing_v1"]
    clock: Literal["monotonic"]
    advance_measurement: Literal["client_enqueue_to_accepted_commit"]
    archive_measurement: Literal["accepted_commit_to_accepted_archive_completion"]
    request_id: Annotated[StrictInt, Field(gt=0, le=2**64 - 1)]
    runtime_scope: RuntimeScope
    foundation_sha256: Sha256
    policy_sha256: Sha256
    expected_tail: Tail
    committed_tail: Tail
    advance_elapsed_ns: U64
    archive_elapsed_ns: U64
    material_record_sha256: Sha256


class Review(NativeRecord):
    observation_generation: U64
    scope: RuntimeScope
    request_id: Positive
    command: Command
    admission: dict[str, JsonValue]
    before: dict[str, JsonValue]


class AidOriginal(NativeRecord):
    version: Literal[1]
    scope: Literal["actual_native_aid_acceptance_witness_only"]
    foundation_sha256: Sha256
    policy_sha256: Sha256
    tick_content_hash: Sha256 | None
    review: Review
    commitment: Commitment


class ContinuousDuration(NativeRecord):
    kind: Literal["continuous"]


class FiniteDuration(NativeRecord):
    kind: Literal["finite"]
    final_period: Positive


class RecoveryIdentity(NativeRecord):
    campaign: StrictStr
    foundation_sha256: Sha256
    tick: Positive
    tick_content_hash: Sha256
    nominal_world_hash: Sha256
    envelope_digest: Sha256
    material_register_sha256: Sha256
    material_register_bytes: Positive
    production_evidence_sha256: Sha256
    production_evidence_body_bytes: Positive
    duration: Annotated[ContinuousDuration | FiniteDuration, Field(discriminator="kind")]


class RecoveryRecord(NativeRecord):
    version: Literal[2]
    scope: Literal["authenticated_native_checkpoint_reopen_v2"]
    request_id: Positive
    previous_scope: RuntimeScope
    restored_scope: RuntimeScope
    policy_sha256: Sha256
    source: RecoveryIdentity
    original_organizer_sha256: Sha256
    cold_reopen_measurement: Literal["client_enqueue_to_installed_authenticated_read"]
    runtime_ready_elapsed_ns: U64
    cold_reopen_elapsed_ns: U64
    authenticated_read: MaterialRecord


def verify_mixed_recovery(
    before: ControlState,
    action: ActionObservation,
    boundary: MaterialRecord,
    recovery: RecoveryRecord,
    policy: Policy,
    policy_sha256: str,
    *,
    captured: bool = False,
) -> None:
    after = action.state
    facts = boundary.facts
    restored = recovery.authenticated_read
    source = recovery.source
    marker = (
        source.campaign,
        source.foundation_sha256,
        source.tick,
        source.tick_content_hash,
        source.nominal_world_hash,
    )
    if (
        action.action != "reopen"
        or action.event != "reopened_and_installed"
        or action.reason is not None
        or before.commitment is None
        or before.commitment.command.choice != "remote_aid"
        or before.commitment.resolves_period != 3
        or not isinstance(before.commitment.command.allocation, AidAllocation)
        or (
            before.commitment.command.allocation.aid.food_quantity,
            before.commitment.command.allocation.aid.cash_micros,
        )
        != (2, "280000000")
        or before.commitment != after.commitment
        or before.scope_epoch is None
        or after.scope_epoch != before.scope_epoch + 1
        or recovery.previous_scope
        != RuntimeScope(epoch=before.scope_epoch, campaign_id=before.campaign_id)
        or recovery.restored_scope
        != RuntimeScope(epoch=after.scope_epoch, campaign_id=after.campaign_id)
        or any(
            (
                state.campaign_id,
                state.foundation_sha256,
                state.durable_tick,
                state.tick_content_hash,
                state.world_hash,
            )
            != marker
            for state in (before, after)
        )
        or not (source.tick == boundary.tick == restored.tick == 2)
        or not (
            source.tick_content_hash == restored.tick_content_hash == boundary.tick_content_hash
        )
        or facts is None
        or source.model_dump(exclude={"duration"})
        != facts.model_dump(include=set(RecoveryIdentity.model_fields) - {"duration"})
        or (
            isinstance(source.duration, FiniteDuration)
            and source.tick > source.duration.final_period
        )
        or recovery.policy_sha256 != policy_sha256
        or facts.policy_sha256 != policy_sha256
        or restored.runtime_epoch != after.scope_epoch
        or not before.generation < restored.observation_generation <= after.generation
        or any(x is not None for x in (restored.opening, restored.facts, restored.aid))
        or restored.economic_summary != boundary.economic_summary
        or restored.trade_summary != boundary.trade_summary
        or recovery.cold_reopen_elapsed_ns
        < recovery.runtime_ready_elapsed_ns + restored.production_read_elapsed_ns
        or recovery.cold_reopen_elapsed_ns
        > action.completed_monotonic_ns - action.started_monotonic_ns
    ):
        raise ValueError(
            "mixed pending recovery differs from its actual dated source or installed action"
        )
    if not captured and (
        recovery.cold_reopen_elapsed_ns >= policy.maximum_cold_open_seconds * 1_000_000_000
        or restored.production_read_elapsed_ns
        > policy.maximum_production_read_seconds * 1_000_000_000
    ):
        raise ValueError("mixed pending recovery exceeded its reopen or production read budget")


def private_bytes(path: Path, maximum: int) -> bytes:
    """Bound allocation and reject redirection before opening private evidence."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("native evidence must be an owned private regular file")
        if not 0 < info.st_size <= maximum:
            raise ValueError("native evidence file exceeds its framing bound")
        with os.fdopen(descriptor, "rb", closefd=False) as source:
            raw = source.read(maximum + 1)
        after = os.fstat(descriptor)
        stable = ("st_dev", "st_ino", "st_mode", "st_uid", "st_size", "st_mtime_ns", "st_ctime_ns")
        if (
            len(raw) != info.st_size
            or len(raw) > maximum
            or any(getattr(after, field) != getattr(info, field) for field in stable)
        ):
            raise ValueError("native evidence file changed during capture")
        return raw
    finally:
        os.close(descriptor)


def _artifact(directory: Path, artifact: Artifact, maximum: int) -> object:
    raw = private_bytes(directory / artifact.name, maximum)
    if hashlib.sha256(raw).hexdigest() != artifact.sha256:
        raise ValueError("native evidence artifact differs from its frozen manifest")
    return strict_json_bytes(raw)


def _stale_poll(action: ActionObservation) -> bool:
    return (
        action.action == "status"
        and action.event == "refused"
        and action.reason == "control_stale_or_unavailable"
    )


def _trace(
    controls: ControlsEvidence,
) -> tuple[tuple[ActionObservation, ...], tuple[ActionObservation, ...]]:
    prior: ActionObservation | None = None
    bound: ActionObservation | None = None
    steps: list[ActionObservation] = []
    reopens: list[ActionObservation] = []
    for action in controls.actions:
        current = action.state
        if (
            current.campaign_id != controls.campaign
            or action.completed_monotonic_ns < action.started_monotonic_ns
            or (
                prior is not None
                and (
                    action.sequence <= prior.sequence
                    or action.started_monotonic_ns < prior.completed_monotonic_ns
                )
            )
        ):
            raise ValueError("native control trace identity, sequence or clock differs")
        # Initial readiness polling may report transient unavailability. No
        # material action is admitted from that response.
        stale_poll = _stale_poll(action)
        if not stale_poll and (
            action.event != expected_event(action.action) or action.reason is not None
        ):
            raise ValueError("native control trace contains a refused material action")
        if bound is not None:
            old = bound.state
            advanced = action.action == "step"
            reopened = action.action == "reopen"
            if (
                current.foundation_sha256 != controls.foundation_sha256
                or old.scope_epoch is None
                or current.scope_epoch != old.scope_epoch + int(reopened)
                or current.durable_tick != old.durable_tick + int(advanced)
                or (not advanced and current.tick_content_hash != old.tick_content_hash)
                or current.generation < old.generation
                or (reopened and current.generation <= old.generation)
            ):
                raise ValueError(
                    "native trace changed epoch, generation or source without its admitted action"
                )
        if current.phase in {"Ready", "Complete"} and not stale_poll:
            if (
                current.scope_epoch is None
                or current.foundation_sha256 != controls.foundation_sha256
                or current.viewed_tick != current.durable_tick
                or (current.durable_tick == 0) != (current.tick_content_hash is None)
            ):
                raise ValueError("native installed state lacks exact source identity")
            if bound is None and current.durable_tick != controls.initial_tick:
                raise ValueError("native trace lacks its original opening")
            bound = action
        if action.action in {"step", "reopen"}:
            if (
                current.phase not in {"Ready", "Complete"}
                or current.archive_verified_tick != current.durable_tick
                or current.advance_pending
                or current.lifecycle_pending
                or current.organizer_pending
                or current.organizer_status_due
                or current.organizer_period != current.durable_tick
            ):
                raise ValueError("native boundary still has unresolved material or Archive work")
            (steps if action.action == "step" else reopens).append(action)
        prior = action
    if bound is None:
        raise ValueError("native trace has no authenticated installed opening")
    return tuple(steps), tuple(reopens)


@dataclass(frozen=True)
class ObservedPlayClose:
    started_monotonic_ns: int
    completed_monotonic_ns: int
    state: ControlState


def _walk_trace(
    controls: ControlsEvidence,
) -> tuple[tuple[ActionObservation | ObservedPlayClose, ...], tuple[ActionObservation, ...]]:
    """Verify observed ordinary UI traces including historical, refused, and automatic inputs."""
    previous: ActionObservation | None = None
    first_ready = False
    playing: ActionObservation | None = None
    settling = False
    arm: ActionObservation | None = None
    steps: list[ActionObservation | ObservedPlayClose] = []
    reopens: list[ActionObservation] = []
    for action in controls.actions:
        state = action.state
        if (
            state.campaign_id != controls.campaign
            or action.completed_monotonic_ns < action.started_monotonic_ns
            or (
                previous is not None
                and (
                    action.sequence <= previous.sequence
                    or action.started_monotonic_ns < previous.completed_monotonic_ns
                )
            )
        ):
            raise ValueError("walk trace is out of order or names a different campaign")
        stale = _stale_poll(action)
        old = previous.state if previous is not None else None
        refused_editor = (
            action.action in ("review", "confirm")
            and action.event == "refused"
            and action.reason in ("control_stale_or_unavailable", "ordinary_handler_refused")
            and state == old
            and state.allocation_error is not None
            and state.commitment is None
            and state.reviewed_command is None
            and state.preview is None
        )
        waiting_archive = (
            action.action == "open_archive_evidence"
            and action.event == "refused"
            and action.reason == "control_stale_or_unavailable"
            and state == old
        )
        refused_offer = (
            action.action == "review"
            and action.event == "refused"
            and action.reason == "ordinary_response_refused"
            and state.preview is not None
            and state.preview.refusal is not None
            and state.reviewed_command is not None
            and state.reviewed_command.allocation
            == state.preview.allocation
            == state.selected_allocation
            and state.reviewed_command.expected_period == state.durable_tick
            and state.commitment is None
        )
        if (
            not stale
            and not refused_editor
            and not waiting_archive
            and not refused_offer
            and (action.event != expected_event(action.action) or action.reason is not None)
        ):
            raise ValueError("walk trace contains an unexpected refusal or mismatched event")
        if first_ready and old is not None:
            changed = state.durable_tick - old.durable_tick
            reopened = action.action == "reopen" and action.event == "reopened_and_installed"
            if (
                old.scope_epoch is None
                or state.scope_epoch != old.scope_epoch + int(reopened)
                or state.perspective != old.perspective
                or state.generation < old.generation
                or (reopened and state.generation <= old.generation)
                or state.foundation_sha256 != controls.foundation_sha256
            ):
                raise ValueError("walk trace scope or installed foundation changed")
            if action.action == "arm_one_play_advance":
                lock = state.play_interlock
                if (
                    arm is not None
                    or lock is None
                    or lock.phase != "armed"
                    or lock.arm_sequence != action.sequence
                    or (
                        lock.campaign_id,
                        lock.scope_epoch,
                        lock.start_tick,
                        lock.start_generation,
                        lock.target_tick,
                    )
                    != (old.campaign_id, old.scope_epoch, 8, old.generation, 9)
                    or old.durable_tick != 8
                    or old.playing
                    or old.advance_pending
                ):
                    raise ValueError("walk arm differs from the actual P8 scope and generation")
                arm = action
            if action.action == "play":
                lock = state.play_interlock
                if (
                    playing is not None
                    or old.playing
                    or action.event != "applied"
                    or arm is None
                    or previous != arm
                    or lock is None
                    or arm.state.play_interlock is None
                    or lock.arm_identity() != arm.state.play_interlock.arm_identity()
                    or lock.phase == "paused_after_enqueue"
                    and lock.play_sequence != action.sequence
                    or (not state.playing and lock.phase != "paused_after_enqueue")
                ):
                    raise ValueError("walk Play is not a fresh armed ordinary admission")
                playing = action
            if changed:
                if changed != 1 or (
                    action.action != "step"
                    and not (playing is not None and action.action in ("play", "pause", "status"))
                ):
                    raise ValueError("walk closed outside a single admitted step or Play")
            elif (state.tick_content_hash, state.world_hash) != (
                old.tick_content_hash,
                old.world_hash,
            ):
                raise ValueError("walk material identity changed without a close")
            if state.playing and playing is None:
                raise ValueError("walk playback began without its ordinary Play event")
            if action.action == "pause" and playing is not None:
                lock = state.play_interlock
                if (
                    state.playing
                    or state.durable_tick not in (8, 9)
                    or lock is None
                    or lock.phase != "paused_after_enqueue"
                    or lock.target_tick != 9
                    or lock.play_sequence != playing.sequence
                    or arm is None
                    or arm.state.play_interlock is None
                    or lock.arm_identity() != arm.state.play_interlock.arm_identity()
                    or lock.scope_epoch != state.scope_epoch
                ):
                    raise ValueError("ordinary Pause lacks the exact P9 pending-at-enqueue witness")
                settling = True
            if (
                settling
                and state.durable_tick == 9
                and not any(
                    (
                        state.playing,
                        state.lifecycle_pending,
                        state.advance_pending,
                        state.organizer_pending,
                        state.organizer_status_due,
                    )
                )
                and state.organizer_period == 9
                and state.archive_verified_tick == 9
            ):
                if playing is None:
                    raise ValueError("final automatic close has no Play admission")
                steps.append(
                    ObservedPlayClose(
                        playing.started_monotonic_ns, action.completed_monotonic_ns, state
                    )
                )
                playing = None
                settling = False
            if state.viewed_tick != state.durable_tick:
                if state.viewed_tick != state.durable_tick - 1 or action.action not in (
                    "previous_period",
                    "status",
                ):
                    raise ValueError("walk history drifted outside its ordinary inspected period")
            if reopened:
                if state.commitment is None:
                    reopens.append(action)
                elif (
                    state.durable_tick != 2
                    or state.commitment.command.choice != "remote_aid"
                    or state.commitment != old.commitment
                ):
                    raise ValueError("extra walk reopen lacks its exact mixed pending original")
            if action.action == "step":
                if (
                    changed != 1
                    or state.playing
                    or state.advance_pending
                    or state.viewed_tick != state.durable_tick
                ):
                    raise ValueError("walk step did not install one period")
                steps.append(action)
        if state.phase in ("Ready", "Complete") and not stale:
            if state.scope_epoch is None or state.foundation_sha256 != controls.foundation_sha256:
                raise ValueError("walk installed state lacks its acknowledged identity")
            if not first_ready and state.durable_tick != controls.initial_tick:
                raise ValueError("walk started from a different checkpoint")
            first_ready = True
        previous = action
    if (
        not first_ready
        or playing is not None
        or settling
        or not controls.actions
        or (controls.actions[-1].action != "quit" or not controls.actions[-1].state.quit_requested)
    ):
        raise ValueError("walk segment lacks verified installation and ordinary close")
    return tuple(steps), tuple(reopens)


def _originals(
    evidence: NativeRunEvidence,
    directory: Path,
    controls: ControlsEvidence,
    playable: PlayableReport,
) -> int:
    accepted = {}
    reviewed: ActionObservation | None = None
    for action in controls.actions:
        if action.event == "refused":
            reviewed = None
            continue
        if action.action == "review":
            reviewed = action
        elif action.action == "confirm":
            commitment = Commitment.model_validate(action.state.commitment)
            if reviewed is None or reviewed.state.reviewed_command != commitment.command:
                raise ValueError("native acceptance has no original matching review")
            if commitment.command.choice in {"local_aid", "remote_aid"}:
                identity = bytes(commitment.commitment_id).hex()
                if identity in accepted:
                    raise ValueError("native trace repeats an accepted aid commitment")
                accepted[identity] = (reviewed, action, commitment)
            reviewed = None
    expected = {"aid-" + identity + ".json" for identity in accepted}
    if {r.name for r in evidence.aid_originals} != expected:
        raise ValueError("native original aid roster differs from actual accepted controls")
    posted = {}
    for row in playable.aid_periods:
        commitment = Commitment.model_validate(row.get("commitment"))
        identity = bytes(commitment.commitment_id).hex()
        if identity in posted:
            raise ValueError("material aid report repeats an original command")
        posted[identity] = (
            commitment,
            Preview.model_validate(row.get("preview")),
            row.get("period"),
        )
    if set(posted) != set(accepted):
        raise ValueError("native accepted aid differs from independent material accounting")
    for artifact in evidence.aid_originals:
        original = AidOriginal.model_validate(_artifact(directory, artifact, MATERIAL_RECORD_BYTES))
        identity = bytes(original.commitment.commitment_id).hex()
        if identity not in accepted or artifact.name != "aid-" + identity + ".json":
            raise ValueError("native original aid file does not name its accepted commitment")
        review, confirm, commitment = accepted[identity]
        posted_commitment, posted_preview, posted_period = posted[identity]
        admission = Preview.model_validate(original.review.admission)
        command = commitment.command
        epoch = review.state.scope_epoch
        view = original.review.before.get("view")
        if epoch is None or not isinstance(view, dict):
            raise ValueError("native original aid lacks its source runtime or organizer view")
        if (
            (original.policy_sha256, original.foundation_sha256)
            != (evidence.policy_sha256, evidence.foundation_sha256)
            or original.commitment != commitment
            or posted_commitment != commitment
            or original.review.command != command
            or bytes(command.campaign_id) != UUID(evidence.campaign).bytes
            or command.expected_period != review.state.durable_tick
            or commitment.resolves_period != command.expected_period + 1
            or original.tick_content_hash != review.state.tick_content_hash
            or original.review.scope != RuntimeScope(epoch=epoch, campaign_id=evidence.campaign)
            or original.review.observation_generation != review.state.generation
            or review.state.preview is None
            or admission != review.state.preview
            or view.get("period") != command.expected_period
            or admission.refusal is not None
            or confirm.state.durable_tick != command.expected_period
            or posted_preview != admission
            or type(posted_period) is not int
            or posted_period != commitment.resolves_period
        ):
            raise ValueError(
                "native original aid custody differs from review, acceptance or posting"
            )
    return len(accepted)


def evaluate_native(
    policy: Policy,
    policy_sha256: str,
    evidence: NativeRunEvidence,
    directory: Path,
    playable: PlayableReport,
    timing: NativeTimings,
    opening: Snapshot,
    ticks: tuple[Snapshot, ...],
    material_result: dict[str, object],
    memory: CombinedMemoryEvidence | None,
    *,
    wayne_walk: bool = False,
) -> dict[str, object]:
    """Require real UI actions, exact source state and separate material proofs."""
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("native evidence directory is redirected or missing")
    folder = directory.stat()
    if folder.st_uid != os.getuid() or folder.st_mode & 0o077:
        raise ValueError("native evidence directory must be owned and private")
    if (
        (
            evidence.policy_sha256,
            evidence.campaign,
            evidence.foundation_sha256,
            evidence.requested_periods,
        )
        != (
            policy_sha256,
            playable.campaign,
            playable.foundation_sha256,
            playable.requested_periods,
        )
        or opening.campaign != evidence.campaign
        or timing.campaign != evidence.campaign
    ):
        raise ValueError("native run differs from frozen policy or material campaign")
    captured = evidence.measurement_mode == "memory_capture"
    if not captured and memory is not None:
        raise ValueError("normal native evidence cannot include a memory certificate")
    if PrivateEvidence(directory).reference("inputs.sha256").sha256 != evidence.inputs_sha256:
        raise ValueError("native captured input manifest differs")
    controls = ControlsEvidence.model_validate(
        _artifact(directory, evidence.controls, CONTROLS_RECORD_BYTES)
    )
    if (controls.campaign, controls.foundation_sha256, controls.initial_tick, controls.status) != (
        evidence.campaign,
        evidence.foundation_sha256,
        0,
        evidence.status,
    ):
        raise ValueError("native controls differ from original run admission")
    if (
        evidence.completed_monotonic_ns - evidence.started_monotonic_ns != timing.run.elapsed_ns
        or any(
            not evidence.started_monotonic_ns
            <= a.started_monotonic_ns
            <= a.completed_monotonic_ns
            <= evidence.completed_monotonic_ns
            for a in controls.actions
        )
        or memory is not None
        and not evidence.started_monotonic_ns
        <= memory.interval_start_monotonic_ns
        < memory.interval_end_monotonic_ns
        <= evidence.completed_monotonic_ns
    ):
        raise ValueError("native wall clock differs from its timing, controls or capture interval")
    steps, reopens = _walk_trace(controls) if wayne_walk else _trace(controls)
    actual = tuple(t.tick for t in ticks)
    if (
        tuple(a.state.durable_tick for a in steps) != actual
        or tuple(a.state.durable_tick for a in reopens) != actual
        or wayne_walk
        and [a.state.durable_tick for a in steps if isinstance(a, ObservedPlayClose)] != [9]
    ):
        raise ValueError("native advance/reopen trace must cover exact committed material periods")
    if tuple(a.name for a in evidence.boundaries) != tuple(
        f"material-{tick}.json" for tick in actual
    ):
        raise ValueError("native material roster differs from exact committed periods")
    if tuple(a.name for a in evidence.advances) != tuple(f"advance-{tick}.json" for tick in actual):
        raise ValueError("native timing roster differs from exact committed periods")
    if tuple(a.name for a in evidence.archives) != tuple(f"archive-{tick}.json" for tick in actual):
        raise ValueError("native Archive roster differs from exact committed periods")
    ordinary_names = tuple(
        f"recovery-{a.state.durable_tick}-{a.state.scope_epoch}.json" for a in reopens
    )
    mixed_actions = [
        (prior.state, action)
        for prior, action in pairwise(controls.actions)
        if wayne_walk and action.action == "reopen" and action.state.commitment is not None
    ]
    if len(mixed_actions) != int(wayne_walk):
        raise ValueError("mixed pending recovery requires exactly its separately observed reopen")
    extra_names = tuple(
        f"recovery-{a.state.durable_tick}-{a.state.scope_epoch}.json" for _, a in mixed_actions
    )
    if tuple(a.name for a in evidence.recoveries) != ordinary_names + extra_names:
        raise ValueError("native recovery roster differs from actual reopened epochs")
    initial = MaterialRecord.model_validate(
        _artifact(directory, evidence.opening, MATERIAL_RECORD_BYTES)
    )
    first = next(
        a.state
        for a in controls.actions
        if a.state.phase in {"Ready", "Complete"} and not _stale_poll(a)
    )
    if (
        initial.tick != 0
        or initial.tick_content_hash is not None
        or initial.opening is None
        or initial.facts is not None
        or initial.aid is not None
        or initial.runtime_epoch != first.scope_epoch
        or initial.observation_generation > first.generation
        or (
            initial.opening.campaign,
            initial.opening.foundation_sha256,
            initial.opening.graph_foundation_sha256,
            initial.opening.policy_sha256,
        )
        != (
            evidence.campaign,
            evidence.foundation_sha256,
            evidence.graph_foundation_sha256,
            evidence.policy_sha256,
        )
        or initial.opening.material_register_bytes > policy.maximum_material_register_bytes
        or initial.opening.county_geoids != playable.county_geoids
        or len(initial.opening.county_geoids) != policy.county_count
        or initial.opening.county_geoids != opening.county_geoids
        or initial.trade_summary.periods != 0
        or any(
            t.actual_rust_storage_package_claims[-1].opening_register_sha256
            != initial.opening.material_register_sha256
            for t in ticks
        )
    ):
        raise ValueError("native material opening differs from authenticated campaign foundation")
    verify_economic_summary([], initial.economic_summary)
    account_periods = playable.independent_account_posting_audit.get("periods")
    if not isinstance(account_periods, list) or len(account_periods) != len(ticks):
        raise ValueError("native join needs exact independent aid audit periods")
    production_times = {row.tick: row.elapsed_ns for row in timing.production_reads}
    cold_times = {row.tick: row.elapsed_ns for row in timing.cold_reopens}
    advance_times = {row.tick: row.elapsed_ns for row in timing.advances}
    archive_times = {row.tick: row.elapsed_ns for row in timing.archive_catchups}
    byte_limits = True
    phase_limits = (
        initial.production_read_elapsed_ns <= policy.maximum_production_read_seconds * 1_000_000_000
    )
    final_practices = initial.aid_practices
    final_renewal = None
    final_summary = initial
    mixed_measurement: dict[str, object] | None = None
    economic_prefix: list[EconomicBoundary] = []
    previous_hash = None
    previous_world_hash: str | None = None
    requests = set()
    for (
        artifact,
        advance_artifact,
        archive_artifact,
        recovery_artifact,
        step,
        reopen,
        boundary,
        tick,
        continuation,
        account,
    ) in zip(
        evidence.boundaries,
        evidence.advances,
        evidence.archives,
        evidence.recoveries[: len(reopens)],
        steps,
        reopens,
        playable.boundaries,
        ticks,
        playable.continuations,
        account_periods,
        strict=True,
    ):
        record = MaterialRecord.model_validate(
            _artifact(directory, artifact, MATERIAL_RECORD_BYTES)
        )
        facts = record.facts
        if facts is None or record.aid is None or record.opening is not None:
            raise ValueError("native committed material record lacks its independent facts")
        advance = AdvanceRecord.model_validate(
            _artifact(directory, advance_artifact, MATERIAL_RECORD_BYTES)
        )
        request = (advance.runtime_scope.epoch, advance.request_id)
        if isinstance(step, ObservedPlayClose):
            lock = step.state.play_interlock
            if (
                lock is None
                or lock.phase != "paused_after_enqueue"
                or (lock.scope_epoch, lock.request_id, lock.start_tick, lock.target_tick)
                != (
                    advance.runtime_scope.epoch,
                    advance.request_id,
                    advance.expected_tail.resolve_tick,
                    advance.committed_tail.resolve_tick,
                )
            ):
                raise ValueError(
                    "bounded Play does not match its actual enqueue request and committed tail"
                )
        if (
            advance.runtime_scope
            != RuntimeScope(epoch=record.runtime_epoch, campaign_id=evidence.campaign)
            or advance.foundation_sha256 != evidence.foundation_sha256
            or advance.policy_sha256 != policy_sha256
            or advance.expected_tail
            != Tail(
                resolve_tick=tick.tick - 1,
                tick_content_hash=previous_hash,
                world_hash=previous_world_hash,
            )
            or advance.committed_tail
            != Tail(
                resolve_tick=tick.tick,
                tick_content_hash=facts.tick_content_hash,
                world_hash=facts.nominal_world_hash,
            )
            or advance.material_record_sha256 != artifact.sha256
            or advance_times.get(tick.tick) != advance.advance_elapsed_ns
            or archive_times.get(tick.tick) != advance.archive_elapsed_ns
            or advance.advance_elapsed_ns + advance.archive_elapsed_ns
            > step.completed_monotonic_ns - step.started_monotonic_ns
            or request in requests
        ):
            raise ValueError(
                "native timing custody differs from request, commit, Archive or material publication"
            )
        requests.add(request)
        archive = ArchiveRecord.model_validate(
            _artifact(directory, archive_artifact, MATERIAL_RECORD_BYTES)
        )
        if (
            (
                archive.campaign,
                archive.foundation_sha256,
                archive.graph_foundation_sha256,
                archive.policy_sha256,
                archive.tick,
                archive.tick_content_hash,
            )
            != (
                evidence.campaign,
                evidence.foundation_sha256,
                evidence.graph_foundation_sha256,
                policy_sha256,
                tick.tick,
                facts.tick_content_hash,
            )
            or archive.archive.model_dump(
                include={
                    "expected_tick",
                    "durable_tick",
                    "processed_tick",
                    "pending_count",
                    "dossier_sha256",
                }
            )
            != boundary.archive.model_dump()
            or archive.archive.pending_scope != "requested_prefix"
            or archive.archive.observation_mode != "live_latest"
            or archive.archive.captured_tail_tick != tick.tick
            or archive.archive.captured_tail_tick_content_hash != facts.tick_content_hash
        ):
            raise ValueError(
                "native Archive artifact differs from its authenticated committed dossier"
            )
        previous_hash = facts.tick_content_hash
        previous_world_hash = facts.nominal_world_hash
        claim = tick.actual_rust_storage_package_claims[-1]
        if (
            record.tick != tick.tick
            or record.tick_content_hash != boundary.tick_content_hash
            or record.runtime_epoch != step.state.scope_epoch
            or record.observation_generation > step.state.generation
            or facts.county_roster_sha256 != initial.opening.county_roster_sha256
            or record.trade_summary.periods != tick.tick
            or (
                facts.campaign,
                facts.foundation_sha256,
                facts.policy_sha256,
                facts.tick,
                facts.tick_content_hash,
                facts.envelope_digest,
                facts.canonical_receipt_sha256,
                facts.nominal_world_hash,
                facts.material_register_sha256,
                facts.material_register_bytes,
                facts.production_evidence_sha256,
                facts.production_evidence_body_bytes,
                facts.county_roster_sha256,
            )
            != (
                playable.campaign,
                playable.foundation_sha256,
                policy_sha256,
                boundary.tick,
                boundary.tick_content_hash,
                boundary.envelope_digest,
                boundary.canonical_receipt_sha256,
                boundary.nominal_world_hash,
                claim.canonical_register_sha256,
                claim.canonical_register_bytes,
                boundary.production.snapshot_sha256,
                boundary.production.production_evidence_body_bytes,
                boundary.production.county_roster_sha256,
            )
            or step.state.tick_content_hash != facts.tick_content_hash
            or facts.economic.model_dump(mode="json") != boundary.economic.model_dump(mode="json")
            or facts.trade.model_dump(mode="json") != boundary.trade.model_dump(mode="json")
            or record.aid.model_dump(mode="json") != account
            or production_times.get(tick.tick) != record.production_read_elapsed_ns
        ):
            raise ValueError(
                "native material facts differ from storage, production or independent accounting"
            )
        economic_prefix.append(facts.economic)
        verify_economic_summary(economic_prefix, record.economic_summary)
        recovery = RecoveryRecord.model_validate(
            _artifact(directory, recovery_artifact, MATERIAL_RECORD_BYTES)
        )
        restored = recovery.authenticated_read
        identity = recovery.source
        if (
            recovery.policy_sha256 != policy_sha256
            or recovery.previous_scope
            != RuntimeScope(epoch=record.runtime_epoch, campaign_id=playable.campaign)
            or recovery.restored_scope
            != RuntimeScope(epoch=record.runtime_epoch + 1, campaign_id=playable.campaign)
            or recovery.restored_scope.epoch != reopen.state.scope_epoch
            or identity.model_dump(exclude={"duration"})
            != facts.model_dump(
                include={
                    "campaign",
                    "foundation_sha256",
                    "tick",
                    "tick_content_hash",
                    "nominal_world_hash",
                    "envelope_digest",
                    "material_register_sha256",
                    "material_register_bytes",
                    "production_evidence_sha256",
                    "production_evidence_body_bytes",
                }
            )
            or (
                isinstance(identity.duration, FiniteDuration)
                and identity.duration.final_period < tick.tick
            )
            or recovery.original_organizer_sha256 != continuation.get("organizer_snapshot_sha256")
            or cold_times.get(tick.tick) != recovery.cold_reopen_elapsed_ns
            or recovery.cold_reopen_elapsed_ns
            < recovery.runtime_ready_elapsed_ns + restored.production_read_elapsed_ns
            or recovery.cold_reopen_elapsed_ns
            > reopen.completed_monotonic_ns - reopen.started_monotonic_ns
            or restored.runtime_epoch != recovery.restored_scope.epoch
            or not record.observation_generation
            < restored.observation_generation
            <= reopen.state.generation
            or restored.tick != tick.tick
            or restored.tick_content_hash != facts.tick_content_hash
            or restored.opening is not None
            or restored.facts is not None
            or restored.aid is not None
            or restored.aid_practices != record.aid_practices
            or restored.economic_summary != record.economic_summary
            or restored.aid_summary != record.aid_summary
            or restored.trade_summary != record.trade_summary
        ):
            raise ValueError(
                "native checkpoint reopen differs from its original authenticated boundary"
            )
        if mixed_actions and tick.tick == 2:
            before, action = mixed_actions[0]
            extra = evidence.recoveries[-1]
            second = RecoveryRecord.model_validate(
                _artifact(directory, extra, MATERIAL_RECORD_BYTES)
            )
            verify_mixed_recovery(
                before, action, record, second, policy, policy_sha256, captured=captured
            )
            if second.previous_scope != recovery.restored_scope or second.source != recovery.source:
                raise ValueError(
                    "mixed pending recovery did not start from its preceding P2 restart"
                )
            mixed_measurement = {
                "receipt": extra.model_dump(),
                "epoch": second.restored_scope.epoch,
                "tick": tick.tick,
                "tick_content_hash": second.source.tick_content_hash,
                "cold_reopen_elapsed_ns": second.cold_reopen_elapsed_ns,
                "production_read_elapsed_ns": second.authenticated_read.production_read_elapsed_ns,
            }
        final_practices = record.aid_practices
        final_summary = record
        final_renewal = facts.production_renewal
        if final_renewal is not None and (
            final_renewal.through_period != tick.tick
            or final_renewal.through_tick_content_hash != facts.tick_content_hash
            or final_renewal.canonical_receipt_sha256 != facts.canonical_receipt_sha256
        ):
            raise ValueError("native production renewal witness differs from its material boundary")
        byte_limits &= (
            facts.material_register_bytes <= policy.maximum_material_register_bytes
            and facts.production_evidence_body_bytes
            <= policy.maximum_production_evidence_body_bytes
        )
        phase_limits &= (
            max(record.production_read_elapsed_ns, restored.production_read_elapsed_ns)
            <= policy.maximum_production_read_seconds * 1_000_000_000
            and recovery.cold_reopen_elapsed_ns < policy.maximum_cold_open_seconds * 1_000_000_000
            and advance.advance_elapsed_ns <= policy.maximum_advance_p95_seconds * 1_000_000_000
            and advance.archive_elapsed_ns <= policy.maximum_archive_catchup_seconds * 1_000_000_000
            and archive.archive_read_elapsed_ns
            <= policy.maximum_archive_catchup_seconds * 1_000_000_000
        )
    if (
        final_summary.economic_summary != playable.independent_economic_accounting
        or final_summary.trade_summary != playable.independent_trade_accounting
        or final_summary.aid_summary.model_dump(mode="json")
        != {
            key: value
            for key, value in playable.independent_account_posting_audit.items()
            if key != "periods"
        }
    ):
        raise ValueError("native terminal summaries differ from independently checked accounting")
    if final_practices != playable.independent_finite_aid_practice:
        raise ValueError(
            "native finite practice disclosure differs from independent aid accounting"
        )
    if (final_renewal.model_dump(mode="json") if final_renewal is not None else None) != (
        playable.independent_production_renewal.model_dump(mode="json")
        if playable.independent_production_renewal is not None
        else None
    ):
        raise ValueError("native production renewal differs from independent material evidence")
    originals = _originals(evidence, directory, controls, playable)
    memory_status: object = "incomplete" if captured else "not_measured"
    memory_observation: dict[str, object] | None = None
    if memory is not None:
        if (
            memory.ownership_record_sha256,
            memory.source_manifest_sha256,
        ) != (
            evidence.ownership_record_sha256,
            evidence.source_manifest_sha256,
        ):
            raise ValueError(
                "native source, executable or ownership admission differs from combined capture"
            )
        resource = evaluate_combined_memory(
            policy,
            policy_sha256,
            memory,
            playable.campaign,
            playable.foundation_sha256,
            tuple(t.marker_and_encoded_package_hashes[-1][1] for t in ticks),
        )
        memory_status = resource["status"]
        memory_observation = {
            key: resource[key]
            for key in (
                "sample_count",
                "maximum_unsampled_gap_ns",
                "observed_sample_peak_rss_upper_bound_bytes",
                "campaign_creation_coverage",
            )
        }
        if any(
            a.started_monotonic_ns < memory.interval_start_monotonic_ns
            or a.completed_monotonic_ns > memory.interval_end_monotonic_ns
            for a in controls.actions
            if a.action != "quit"
        ):
            raise ValueError("native action lies outside its combined-role capture interval")
    material_status = (
        material_result.get("operational_smoke_status")
        if evidence.requested_periods == policy.routine_smoke_periods
        else material_result.get("status")
    )
    completed = (
        evidence.status == "completed"
        and len(ticks) == evidence.requested_periods
        and bool(controls.actions)
        and controls.actions[-1].action == "quit"
        and controls.actions[-1].state.quit_requested
    )
    failed = (
        not byte_limits
        or (not captured and not phase_limits)
        or memory_status == "failed"
        or material_status == "failed"
    )
    qualified = (
        completed
        and (not captured or memory_status == "qualified")
        and material_status == "qualified"
    )
    return {
        "version": 5,
        "measurement_mode": evidence.measurement_mode,
        "graph_foundation_sha256": evidence.graph_foundation_sha256,
        "status": "failed" if failed else ("qualified" if qualified else "incomplete"),
        "actual_periods": len(ticks),
        "accepted_original_aid_commands": originals,
        "checkpoint_reopens": len(reopens),
        **({"mixed_pending_recovery": mixed_measurement} if wayne_walk else {}),
        "native_advance_timing_receipts": len(evidence.advances),
        "advance_measurement": "client_enqueue_to_accepted_commit",
        "archive_measurement": "accepted_commit_to_accepted_archive_completion",
        "cold_reopen_measurement": "client_enqueue_to_installed_authenticated_read",
        "combined_memory_status": memory_status,
        "main_interval_observation": memory_observation,
        "material_status": material_status,
        "separate_byte_budgets_passed": byte_limits,
        "native_read_and_reopen_budgets_passed": None if captured else phase_limits,
        "enjoyment_status": "unqualified",
        "scope": "Actual native action custody joined to authenticated material, Archive, storage and checkpoint recovery; scripted interaction does not establish enjoyment",
    }


class RecipientHours(NativeRecord):
    actor_id: U64
    contributor_id: U64
    hours: U64


class PracticeReceipt(NativeRecord):
    receipt_id: Bytes32
    commitment_id: Bytes32 | None
    period: U64
    actor_id: U64
    choice: StrictStr
    standing_work: StrictBool
    hours_spent: U64
    observation_ids: tuple[Bytes32, ...]
    contact_product_id: Bytes32 | None
    outcome: StrictStr
    partner_actor_id: U64 | None
    partner_response: StrictStr
    time_use: tuple[RecipientHours, ...]


def walk_response(
    original: tuple[int, ...],
    practices: tuple[AidPracticeEvidence, ...],
    sql_rows: list[dict[str, Any]],
    *,
    actor: int,
    choice: str,
) -> dict[str, Any]:
    """Join one actual gift's dated material legs and political responses to committed rows."""
    practice_kinds = {
        "aid_awaiting_support",
        "no_qualifying_support",
        "aid_response_retained",
        "aid_practice_completed",
        "aid_practice_uncompleted",
        "insufficient_time",
    }
    rows = [
        PracticeReceipt.model_validate(row)
        for row in sql_rows
        if row["commitment_id"] == list(original) and row["outcome"] in practice_kinds
    ]
    by_date = {row.period: row for row in rows}
    if len(rows) != len(by_date) or len({row.receipt_id for row in rows}) != len(rows):
        raise ValueError("original has duplicate recipient response rows")
    if [p.period for p in practices] != sorted(by_date):
        raise ValueError("recipient response dates differ from independent material accounting")
    first: PracticeReceipt | None = None
    for p in practices:
        r = by_date[p.period]
        if (
            p.original_commitment != original
            or r.actor_id != actor
            or r.choice != choice
            or p.practice_receipt_id != r.receipt_id
            or r.standing_work
            or (r.outcome, r.partner_actor_id, r.partner_response)
            != (p.outcome, p.partner_actor, p.partner_response)
            or sum(item.hours for item in r.time_use if item.actor_id == p.partner_actor)
            != p.recipient_debited_hours
        ):
            raise ValueError(
                "recipient, response or finite recipient hours differ from committed practice"
            )
        posted = [(v.actor_id, v.contributor_id, v.hours) for v in p.contribution_postings]
        if sorted(posted) != sorted(
            (v.actor_id, v.contributor_id, v.hours) for v in r.time_use
        ) or len({v.use_id for v in p.contribution_postings}) != len(posted):
            raise ValueError(
                "recipient contribution postings differ from the dated practice receipt"
            )
        for posting in p.contribution_postings:
            use = hashlib.sha256(
                b"babylon.organizer-household-contribution.v1\0"
                + bytes(r.receipt_id)
                + posting.actor_id.to_bytes(8, "big")
                + posting.contributor_id.to_bytes(8, "big")
            ).digest()
            if bytes(posting.use_id) != use:
                raise ValueError(
                    "recipient posting identity differs from the actual practice/contributor"
                )
        if p.outcome in ("aid_response_retained", "aid_awaiting_support", "no_qualifying_support"):
            if (
                r.time_use
                or r.hours_spent
                or p.recipient_debited_hours
                or r.partner_actor_id is not None
                or r.partner_response != "not_requested"
            ):
                raise ValueError("retained or absent response charged new recipient time")
            if p.outcome == "aid_response_retained" and (
                first is None
                or p.first_response_period != first.period
                or p.first_response_receipt_id != first.receipt_id
            ):
                raise ValueError(
                    "retained response does not name its unique earlier first response"
                )
        else:
            if (
                first is not None
                or not p.qualifying_received_support
                or p.first_response_period != p.period
                or p.first_response_receipt_id != r.receipt_id
                or p.partner_actor is None
            ):
                raise ValueError("recipient response lacks its unique first qualifying support")
            first = r
    return {
        "original_commitment": bytes(original).hex(),
        "first_response_receipt": first.model_dump(mode="json") if first else None,
        "material_practices": [p.model_dump(mode="json") for p in practices],
        "retained_without_second_debit": [
            p.period for p in practices if p.outcome == "aid_response_retained"
        ],
    }


class WalkStage(NativeRecord):
    utc: AwareDatetime
    monotonic_ns: Positive
    state: ControlState
    facts: dict[str, Any]


class ColdInstallation(NativeRecord):
    started_monotonic_ns: Nonnegative
    installed_monotonic_ns: Positive
    elapsed_ns: Positive
    processes: Annotated[
        tuple[tuple[Positive, Nonnegative, Sha256], ...], Field(min_length=2, max_length=2)
    ]
    state: ControlState
    ownership_sha256: Sha256
    source_head: Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{40}$")]


class WalkFrame(NativeRecord):
    utc: AwareDatetime
    started_monotonic_ns: Positive
    completed_monotonic_ns: Positive
    segment: Literal["opening", "walk", "completed"]
    sequence: Positive
    stage: Annotated[StrictStr, Field(pattern=r"^[a-z][a-z0-9-]+$")]
    role: Literal["organizer"]
    panel: StrictStr
    width: Positive
    height: Positive
    scale: StrictStr
    capture: Reference
    state: ControlState


def verify_frame_png(data: bytes, width: int, height: int) -> None:
    if (width, height) not in ((1366, 768), (1920, 1080)) or not data.endswith(
        bytes.fromhex("0000000049454e44ae426082")
    ):
        raise ValueError("native PNG extent or complete final chunk is absent")
    try:
        with Image.open(BytesIO(data), formats=("PNG",)) as image:
            if (
                not isinstance(image, PngImagePlugin.PngImageFile)
                or image.size != (width, height)
                or image.n_frames != 1
            ):
                raise ValueError("native PNG dimensions differ from the requested window")
            image.verify()
        with Image.open(BytesIO(data), formats=("PNG",)) as image:
            image.load()
    except (OSError, SyntaxError) as error:
        raise ValueError("native PNG pixels or checksums cannot be verified") from error


def _walk_frames(
    raw: Path, segments: dict[str, ControlsEvidence]
) -> tuple[dict[str, list[str]], int]:
    custody = PrivateEvidence(raw)
    actions = {
        name: {a.sequence: a for a in segment.actions if a.action == "capture_frame"}
        for name, segment in segments.items()
    }
    expected = {(key, seq) for key, mapping in actions.items() for seq in mapping}
    seen: set[tuple[str, int]] = set()
    sizes: dict[str, set[tuple[int, int, str]]] = {}
    artifacts: dict[str, list[str]] = {}
    screenshots: set[str] = set()
    elapsed_ns = 0
    for path in sorted(raw.glob("*.json")):
        f = WalkFrame.model_validate(
            strict_json_bytes(custody.read_reference(custody.reference(path.name)))
        )
        action = actions[f.segment].get(f.sequence)
        identity = (f.segment, f.sequence)
        name = f"{f.stage}-p{f.state.viewed_tick}-{f.width}x{f.height}-{f.scale}-seq{f.sequence}"
        if (
            identity in seen
            or action is None
            or action.event != "frame_captured"
            or action.reason is not None
            or f.state != action.state
            or f.panel != f.state.inspector
            or f.state.playing
            or f.state.perspective != "PlayerKnowledge"
            or f.started_monotonic_ns > action.started_monotonic_ns
            or action.completed_monotonic_ns > f.completed_monotonic_ns
            or (f.capture.path, path.name) != (name + ".png", name + ".json")
        ):
            raise ValueError("raw frame differs from its actual control, role, period or filename")
        data = custody.read_reference(f.capture, 32 * 1024 * 1024)
        verify_frame_png(data, f.width, f.height)
        layout = (f.width, f.height, f.scale)
        roster = sizes.setdefault(f.stage, set())
        if layout in roster or f.state.larger_interface != (f.scale in ("1.15", "1.4375")):
            raise ValueError("native frame has a duplicate or mismatched layout")
        roster.add(layout)
        artifacts.setdefault(f.stage, []).append(f.capture.path)
        elapsed_ns += f.completed_monotonic_ns - f.started_monotonic_ns
        seen.add(identity)
        screenshots.add(f.capture.path)
    expected_layout = {
        (1366, 768, "1.0"),
        (1366, 768, "1.15"),
        (1920, 1080, "1.25"),
        (1920, 1080, "1.4375"),
    }
    if (
        not seen
        or seen != expected
        or screenshots != {path.name for path in raw.glob("*.png")}
        or any(layouts != expected_layout for layouts in sizes.values())
    ):
        raise ValueError(
            "native frame sets do not cover each captured action in all four actual layouts"
        )
    return artifacts, elapsed_ns


def _walk_scope(evidence: PrivateEvidence, name: str) -> Any:
    return strict_json_bytes(
        evidence.read_reference(evidence.reference(name), CONTROLS_RECORD_BYTES)
    )


def _walk_checkpoint(
    evidence: PrivateEvidence,
    before: str,
    after: str,
    choice: str | None,
    period: int,
    controls: tuple[ControlsEvidence, ControlsEvidence],
) -> WalkStage:
    left, right = (
        WalkStage.model_validate(_walk_scope(evidence, name + ".json")) for name in (before, after)
    )
    if (
        left.facts != right.facts
        or left.monotonic_ns >= right.monotonic_ns
        or left.state.commitment != right.state.commitment
        or left.state.installed_organizer is None
        or left.state.installed_organizer != right.state.installed_organizer
    ):
        raise ValueError("restored draft, SQL, report or original differs across the checkpoint")
    if controls[0] is controls[1]:
        reopens = [
            action
            for action in controls[0].actions
            if action.action == "reopen"
            and action.event == "reopened_and_installed"
            and left.monotonic_ns
            <= action.started_monotonic_ns
            <= action.completed_monotonic_ns
            <= right.monotonic_ns
        ]
        if (
            len(reopens) != 1
            or left.state.scope_epoch is None
            or right.state.scope_epoch != left.state.scope_epoch + 1
            or right.state.generation <= left.state.generation
            or reopens[0].state.scope_epoch != right.state.scope_epoch
        ):
            raise ValueError(
                "checkpoint lacks the actual intervening installed reopen and new scope"
            )
    for stage, trace in zip((left, right), controls, strict=True):
        s = stage.state
        if (
            s.campaign_id != trace.campaign
            or s.durable_tick != period
            or s.viewed_tick != period
            or s.foundation_sha256 != trace.foundation_sha256
            or s.playing
            or s.organizer_pending
            or s.organizer_status_due
            or s.lifecycle_pending
            or s.advance_pending
            or s.installed_organizer is None
            or s.installed_organizer.period != period
            or not any(
                a.state == s and a.completed_monotonic_ns <= stage.monotonic_ns
                for a in trace.actions
            )
            or (s.commitment.command.choice if s.commitment else None) != choice
        ):
            raise ValueError("SQL checkpoint differs from its actual installed native control")
    return right


def _walk_memory(
    policy: Policy,
    base: Path,
    native: NativeRunEvidence,
    main: CombinedMemoryEvidence | None,
    segments: dict[str, ControlsEvidence],
    markers: dict[int, str],
) -> list[dict[str, Any]]:
    if main is not None and (not main.samples or main.periods != 10):
        raise ValueError("national walk requires a complete ten-close main memory witness")
    identities: set[tuple[int, int, str]] = set()
    prior_end = 0
    source_head = private_bytes(base / "source-head", 64).decode().strip()
    reports = []
    for name, start_tick in (("opening", 0), ("walk", 0), ("completed", 10)):
        folder = base if name == "walk" else base / ("segment-" + name)
        cold = ColdInstallation.model_validate(
            _walk_scope(PrivateEvidence(base), "cold-installed-" + name + ".json")
        )
        trace = segments[name]
        if (
            cold.ownership_sha256 != native.ownership_record_sha256
            or cold.source_head != source_head
            or cold.state.durable_tick != start_tick
            or (
                main is None and cold.elapsed_ns >= policy.maximum_cold_open_seconds * 1_000_000_000
            )
            or not any(action.state == cold.state for action in trace.actions)
            or not trace.actions
            or trace.actions[0].started_monotonic_ns < prior_end
        ):
            raise ValueError(
                "process-cold installation lacks matching timed installed controls and owner"
            )
        native_pids = set(cold.processes)
        if len(native_pids) != 2 or identities & native_pids:
            raise ValueError("process-cold pair repeated an earlier owned process")
        identities.update(native_pids)
        if main is None:
            prior_end = trace.actions[-1].completed_monotonic_ns
            reports.append(
                {
                    "segment": name,
                    "initial_tick": start_tick,
                    "processes": cold.processes,
                    "cold_install_ns": cold.elapsed_ns,
                    "start_ns": trace.actions[0].started_monotonic_ns,
                    "end_ns": prior_end,
                }
            )
            continue
        segment: CombinedMemoryEvidence | FixedPeriodMemory = (
            main
            if name == "walk"
            else FixedPeriodMemory.model_validate(
                _walk_scope(PrivateEvidence(folder), "segment-memory.json")
            )
        )
        if (
            segment.campaign,
            segment.foundation_sha256,
            segment.boot_id,
            segment.policy_sha256,
            segment.source_manifest_sha256,
            segment.executable_manifest_sha256,
            segment.ownership_record_sha256,
            segment.capture_implementation_sha256,
        ) != (
            native.campaign,
            native.foundation_sha256,
            main.boot_id,
            native.policy_sha256,
            native.source_manifest_sha256,
            main.executable_manifest_sha256,
            native.ownership_record_sha256,
            main.capture_implementation_sha256,
        ):
            raise ValueError(
                "cold interval campaign, frozen source, executable, owner or boot differs"
            )
        authenticate_combined_memory_capture(segment, folder)
        prev = segment.interval_start_monotonic_ns
        peak = gap = 0
        ages = set()
        founded = False
        for i, sample in enumerate(segment.samples, 1):
            proc = {
                p.role: (p.pid, p.start_time_ticks, p.executable_sha256)
                for p in sample.processes
                if p.role in ("native-client", "engine-runtime")
            }
            if (
                sample.sequence != i
                or sample.monotonic_ns < prev
                or sample.monotonic_ns + sample.capture_duration_ns
                > segment.interval_end_monotonic_ns
                or sample.simultaneous_capture != "owned_game_group_stopped"
                or sample.roster_complete != "all_game_processes_in_owned_scope"
                or sample.native_client_mode != "windowed"
                or proc != {"engine-runtime": cold.processes[0], "native-client": cold.processes[1]}
                or not any(p.role == "game-postgresql" for p in sample.processes)
                or sample.foundation_sha256 not in (native.foundation_sha256, None)
                or (founded and sample.foundation_sha256 is None)
                or sample.tick_content_hash != markers.get(sample.campaign_age_ticks)
            ):
                raise ValueError(
                    "cold memory sample lacks the exact owned process and committed marker"
                )
            if sample.foundation_sha256 is not None:
                founded = True
            ages.add(sample.campaign_age_ticks)
            gap = max(gap, sample.monotonic_ns - prev)
            prev = sample.monotonic_ns + sample.capture_duration_ns
            peak = max(
                peak,
                sum(
                    p.rss_bytes + p.private_hugetlb_bytes + p.shared_hugetlb_bytes
                    for p in sample.processes
                ),
            )
        gap = max(gap, segment.interval_end_monotonic_ns - prev)
        if (
            not founded
            or segment.interval_start_monotonic_ns < prior_end
            or ages != (set(range(11)) if name == "walk" else {start_tick})
            or (isinstance(segment, FixedPeriodMemory) and segment.period != start_tick)
            or (segment.samples[0].foundation_sha256 is None) != (name == "opening")
            or peak > policy.maximum_combined_running_game_memory_bytes
            or gap > policy.maximum_combined_memory_sample_gap_seconds * 1_000_000_000
            or not all(
                segment.interval_start_monotonic_ns
                <= a.started_monotonic_ns
                <= a.completed_monotonic_ns
                <= segment.interval_end_monotonic_ns
                for a in trace.actions
                if a.action != "quit"
            )
        ):
            raise ValueError("cold interval coverage, memory budget or sampled cadence differs")
        prior_end = segment.interval_end_monotonic_ns
        reports.append(
            {
                "segment": name,
                "initial_tick": start_tick,
                "processes": cold.processes,
                "cold_install_ns": cold.elapsed_ns,
                "peak_combined_rss_upper_bound_bytes": peak,
                "maximum_sample_gap_ns": gap,
                "start_ns": segment.interval_start_monotonic_ns,
                "end_ns": segment.interval_end_monotonic_ns,
            }
        )
    return reports


def _walk_originals(segments: dict[str, ControlsEvidence]) -> dict[tuple[int, ...], Commitment]:
    all_commands = {}
    for controls in segments.values():
        review = None
        for action in controls.actions:
            state = action.state
            if action.action == "review" and action.event == "preview_admitted":
                ruling = state.preview
                command = state.reviewed_command
                if (
                    ruling is None
                    or command is None
                    or ruling.refusal is not None
                    or command.allocation != ruling.allocation
                    or command.choice != ruling.choice
                    or state.installed_organizer is None
                    or (
                        command.actor_id,
                        command.authority_id,
                        command.content_digest,
                        command.resource_digest,
                    )
                    != (
                        state.installed_organizer.actor_id,
                        state.installed_organizer.authority_id,
                        state.installed_organizer.content_digest,
                        state.installed_organizer.resource_digest,
                    )
                    or ruling.current_period != command.expected_period
                    or command.expected_period != state.durable_tick
                    or bytes(command.campaign_id) != UUID(controls.campaign).bytes
                ):
                    raise ValueError("walk admitted review differs from its actual selection")
                eligibility = {
                    "hold": state.installed_organizer.hold_reviewable,
                    "pause_standing": state.installed_organizer.pause_reviewable,
                    "resume_standing": state.installed_organizer.resume_reviewable,
                }
                if isinstance(command.choice, str) and not eligibility.get(command.choice, True):
                    raise ValueError(
                        "ordinary review contradicts the current installed choice eligibility"
                    )
                review = state
            elif action.action == "confirm" and action.event == "acceptance_admitted":
                original = state.commitment
                if (
                    review is None
                    or original is None
                    or original.command != review.reviewed_command
                    or original.resolves_period != state.durable_tick + 1
                    or original.commitment_id in all_commands
                ):
                    raise ValueError(
                        "walk original lacks its unique actual review and confirmation"
                    )
                all_commands[original.commitment_id] = original
                review = None
            elif (
                action.action not in ("status", "capture_frame")
                or action.event != expected_event(action.action)
                or state != review
            ):
                review = None
    return all_commands


def installed_walk_stages(
    evidence: PrivateEvidence,
    trace: ControlsEvidence,
    boundaries: tuple[PlayableBoundary, ...],
    actor: int,
    authority: tuple[int, ...],
) -> dict[int, WalkStage]:
    stages = {}
    for boundary in boundaries:
        tick = boundary.tick
        recovered = _walk_checkpoint(
            evidence,
            f"walk-p{tick}-committed",
            f"walk-p{tick}-installed",
            None,
            tick,
            (trace, trace),
        )
        view = recovered.state.installed_organizer
        if (
            view is None
            or (view.actor_id, view.authority_id, view.period) != (actor, authority, tick)
            or recovered.state.tick_content_hash != boundary.tick_content_hash
        ):
            raise ValueError("reopened marker differs from its controlled organizer authority")
        stages[tick] = recovered
    return stages


def remote_food_quantities(
    legs: list[dict[str, Any]], period: int, dispatch: int
) -> tuple[int, int]:
    """Return surviving freight and parcels accounted for at the dispatch decision."""
    dispatched = settled = undispatched = 0
    for leg in legs:
        if leg["period"] > period:
            continue
        outcome = leg["outcome"]
        if outcome not in ("Dispatched", "Granted", "Lost", "Unshipped", "FoodReceivingRefused"):
            continue
        quantity = leg["quantity"]
        if type(quantity) is not int or quantity <= 0 or leg["period"] < dispatch:
            raise ValueError("invalid dated freight quantity or period")
        if outcome in ("Granted", "Lost"):
            settled += quantity
        elif leg["period"] != dispatch:
            raise ValueError("mixed food dispatch or refusal occurred after its authorized close")
        elif outcome == "Dispatched":
            dispatched += quantity
        else:
            undispatched += quantity
    return dispatched - settled, dispatched + undispatched


def mixed_food_terminal(
    state: ControlState, boundaries: list[AidBoundary], mixed: Commitment
) -> bool:
    """Reconcile the selected parcels with dated material postings and the installed sender view."""
    view = state.installed_organizer
    allocation = mixed.command.allocation
    if (
        view is None
        or view.period != state.durable_tick
        or not isinstance(allocation, AidAllocation)
    ):
        raise ValueError("mixed food decision lacks its installed organizer or selected allocation")
    requested = allocation.aid.food_quantity
    if requested <= 0:
        raise ValueError("mixed food decision lacks selected parcels")
    legs = [
        {**leg, "period": boundary.period}
        for boundary in boundaries
        for leg in boundary.selected_aid
        if leg["original_commitment"] == list(mixed.commitment_id)
    ]
    outstanding, accounted = remote_food_quantities(legs, state.durable_tick, mixed.resolves_period)
    pending = [
        row for row in view.pending_freight if row.original_commitment_id == mixed.commitment_id
    ]
    if outstanding < 0 or accounted > requested or len(pending) != int(outstanding > 0):
        raise ValueError("installed mixed freight disagrees with its dated material quantities")
    return outstanding == 0 and accounted == requested


def verify_mixed_follow_up(
    trace: ControlsEvidence,
    stages: dict[int, WalkStage],
    boundaries: list[AidBoundary],
    mixed: Commitment,
) -> None:
    for action in trace.actions:
        state = action.state
        allocation = state.aid_allocation
        if (
            action.action == "review"
            and state.choice == "local_aid"
            and isinstance(allocation, AidAllocation)
            and allocation.aid.food_quantity == 0
            and int(allocation.aid.cash_micros) > 0
            and not mixed_food_terminal(stages[state.durable_tick].state, boundaries, mixed)
        ):
            raise ValueError("local cash follow-up preceded the reconciled remote food result")


def verify_freight_reopens(
    stages: dict[int, WalkStage],
    legs: list[dict[str, Any]],
    original: tuple[int, ...],
    mandate: tuple[int, ...],
    dispatch: int,
    material: tuple[int, ...] | None,
    first: dict[str, Any] | None,
    *,
    remote: bool,
) -> list[int]:
    pending = []
    for period, stage in sorted(stages.items()):
        outstanding = remote_food_quantities(legs, period, dispatch)[0] if remote else 0
        view = stage.state.installed_organizer
        if view is None:
            raise ValueError("installed recipient authority absent")
        freight = [f for f in view.pending_freight if f.original_commitment_id == original]
        if outstanding < 0 or len(freight) != int(outstanding > 0):
            raise ValueError(
                "installed pending freight differs from its outstanding dated material quantity"
            )
        if freight:
            current_first = (
                tuple(first["receipt_id"]) if first and first["period"] <= period else None
            )
            if (
                freight[0].mandate_id,
                freight[0].dispatch_period,
                freight[0].first_response_receipt_id,
                freight[0].material_commitment_id,
            ) != (mandate, dispatch, current_first, material):
                raise ValueError(
                    "in-transit receipt, first response or admitted freight differs after reopen"
                )
            pending.append(period)
    return pending


def verify_contribution_history(boundaries: list[AidBoundary]) -> None:
    seen: set[tuple[int, ...]] = set()
    for boundary in boundaries:
        for practice in boundary.independent_practices:
            uses = {posting.use_id for posting in practice.contribution_postings}
            uses.update(practice.absent_contribution_use_ids)
            if seen.intersection(uses):
                raise ValueError("dated positive or absent contribution identity was reused")
            seen.update(uses)


def verify_first_receipt_prefix(
    stages: dict[int, WalkStage], first: dict[str, Any], digest: bytes
) -> None:
    key = bytes(first["receipt_id"]).hex()
    for period, stage in stages.items():
        if period < first["period"]:
            continue
        raw = bytes.fromhex(stage.facts["receipt_bytes"][key])
        if (
            hashlib.sha256(raw).digest() != digest
            or strict_json_bytes(raw) != first
            or [r for r in stage.facts["receipts"] if r["receipt_id"] == first["receipt_id"]]
            != [first]
        ):
            raise ValueError("first response content changed under the same receipt identity")


def verify_standing_period(stage: WalkStage, actor: int, paused: bool) -> None:
    view = stage.state.installed_organizer
    if view is None or view.actor_id != actor:
        raise ValueError("standing directive lost its controlled actor")
    if paused and (view.standing.authorized or view.standing.paused_reason != "explicit"):
        raise ValueError("quiet standing routine resumed before its actor's explicit Resume")
    if not paused and (
        not view.standing.authorized
        or view.standing.paused_reason is not None
        or view.resume_reviewable
    ):
        raise ValueError("Resume outcome disagrees with the installed routine and eligibility")


def verify_directives(
    originals: list[Commitment],
    stages: dict[int, WalkStage],
    actor: int,
    authority: tuple[int, ...],
    missing: list[str],
) -> None:
    outcomes = {"pause_standing": "standing_paused", "resume_standing": "standing_resumed"}
    directives = sorted(
        (
            (choice, c)
            for c in originals
            if isinstance(choice := c.command.choice, str) and choice in outcomes
        ),
        key=lambda item: item[1].resolves_period,
    )
    choices = [choice for choice, _ in directives]
    if len(set(choices)) != len(choices):
        raise ValueError("duplicate standing directive for the same actor")
    if choices != ["pause_standing", "resume_standing"]:
        missing.append("ordinary actor-bound Pause and Resume standing")
    applied = {}
    for choice, directive in directives:
        stage = stages[directive.resolves_period]
        matches = [
            r
            for r in stage.facts["receipts"]
            if r["actor_id"] == actor
            and r["period"] == directive.resolves_period
            and r["commitment_id"] == list(directive.commitment_id)
            and r["choice"] == choice
            and r["standing_work"] is False
        ]
        if (
            directive.command.actor_id != actor
            or directive.command.authority_id != authority
            or len(matches) != 1
        ):
            raise ValueError("standing directive lacks the receipt of its exact actor and original")
        if matches[0]["outcome"] != outcomes[choice]:
            missing.append(f"observed {choice} outcome {matches[0]['outcome']}")
            continue
        applied[choice] = directive.resolves_period
        verify_standing_period(stage, actor, choice == "pause_standing")
    if "pause_standing" in applied:
        end = applied.get("resume_standing", max(stages) + 1)
        if end <= applied["pause_standing"]:
            raise ValueError("standing Resume precedes the actual Pause")
        for tick in range(applied["pause_standing"], end):
            verify_standing_period(stages[tick], actor, True)
            if any(
                r["period"] == tick
                and r["actor_id"] == actor
                and r["standing_work"]
                and r["outcome"] != "no_authorized_practice"
                for r in stages[tick].facts["receipts"]
            ):
                raise ValueError("standing work executed while the controlled actor had paused it")


def verify_walk_disclosures(
    opening: NativeOpening,
    ordered: list[AidBoundary],
    stages: dict[int, WalkStage],
    actor: int,
    source_digest: str,
) -> tuple[dict[str, Any], dict[str, PartnerSource]]:
    disclosed = {}
    sources = {}
    for period, rows in [
        (0, opening.partner_reports),
        *((b.period, b.partner_reports) for b in ordered),
    ]:
        stage = stages[period]
        expected = {
            key
            for key, raw in stage.facts["reports"].items()
            if raw["acquired_period"] == period and raw["report"]["kind"] == "partner"
        }
        if (
            len(rows) != len(expected)
            or tuple(r.observation_id for r in rows)
            != tuple(sorted(r.observation_id for r in rows))
            or {bytes(row.observation_id).hex() for row in rows} != expected
        ):
            raise ValueError(
                "recipient source roster differs from the dated SQL partner observations"
            )
        for key, raw in stage.facts["reports"].items():
            obs = Observation.model_validate(raw)
            if bytes(obs.observation_id).hex() != key or obs.actor_id != actor:
                raise ValueError(
                    "dated report key or controlled reader differs from the SQL projection"
                )
            if obs.receipt_id is not None and obs.acquired_period == period:
                validate_membership(obs, stage.facts["receipts"], actor)
        for row in rows:
            key = bytes(row.observation_id).hex()
            observation = Observation.model_validate(stage.facts["reports"][key])
            verify_partner_source(
                row,
                observation,
                actor=actor,
                period=period,
                source_hash=source_digest,
                grants=stage.facts["grants"],
            )
            disclosed[key] = observation.model_dump(mode="json")
            sources[key] = row
        for key, raw in disclosed.items():
            if stage.facts["reports"].get(key) != raw:
                raise ValueError("reopened SQL reports changed from original dated disclosure")
    return disclosed, sources


def evaluate_wayne_walk(
    policy: Policy,
    native: NativeRunEvidence,
    base: Path,
    material: PlayableReport,
    timing: NativeTimings,
    memory: CombinedMemoryEvidence | None,
    native_result: dict[str, object],
    storage: dict[str, object],
) -> dict[str, Any]:
    if (
        base != member_run("walk-01", native.measurement_mode) / "evidence"
        or (memory is None) != (native.measurement_mode == "normal_play")
        or native.requested_periods != 10
        or native.status != "completed"
    ):
        raise ValueError(
            "Wayne walkthrough needs its exact disposable media run and ten-close admission"
        )
    evidence = PrivateEvidence(base)
    owner = evidence.read_reference(evidence.reference("ownership"), 4096).decode().splitlines()
    if (
        len(owner) != 21
        or owner[0] != "national-storage-runner-media-v2"
        or owner[10] != str(base)
        or owner[11] != "walk-01"
    ):
        raise ValueError("walk evidence names a different native owner")
    segments = {
        name: ControlsEvidence.model_validate(
            _walk_scope(evidence, prefix + "native-controls.json")
        )
        for name, prefix in (
            ("opening", "segment-opening/"),
            ("walk", ""),
            ("completed", "segment-completed/"),
        )
    }
    for label, trace in segments.items():
        if (trace.foundation_sha256, trace.campaign, trace.initial_tick, trace.status) != (
            native.foundation_sha256,
            native.campaign,
            10 if label == "completed" else 0,
            "completed",
        ):
            raise ValueError("process-cold trace names a different terminal or campaign")
        steps, reopens = _walk_trace(trace)
        if label != "walk" and (steps or reopens):
            raise ValueError("fixed-period cold segment performed an extra advance or reopen")
    pending = _walk_checkpoint(
        evidence,
        "pending-before-cold",
        "pending-after-cold",
        "collect",
        0,
        (segments["opening"], segments["walk"]),
    )
    mixed = _walk_checkpoint(
        evidence,
        "mixed-pending-before-reopen",
        "mixed-pending-after-reopen",
        "remote_aid",
        2,
        (segments["walk"], segments["walk"]),
    )
    terminal = _walk_checkpoint(
        evidence,
        "completed-before-cold",
        "completed-after-cold",
        None,
        10,
        (segments["walk"], segments["completed"]),
    )
    if (
        not pending.facts["draft"]["sha256"]
        or pending.facts["campaign_identity"] != terminal.facts["campaign_identity"]
        or mixed.facts["campaign_identity"] != terminal.facts["campaign_identity"]
    ):
        raise ValueError("pending and completed drafts or installed national identities are absent")
    frames, capture_wall_ns = _walk_frames(base.parent / "raw", segments)
    originals = _walk_originals(segments)
    sql_originals = {
        Commitment.model_validate(row["commitment"]).commitment_id: Commitment.model_validate(
            row["commitment"]
        )
        for row in terminal.facts["commands"]
        if row["consumed_period"] == row["commitment"]["resolves_period"]
    }
    if (
        sql_originals != originals
        or pending.state.commitment not in originals.values()
        or mixed.state.commitment not in originals.values()
    ):
        raise ValueError("accepted native originals differ from the settled SQL command roster")
    if (
        pending.state.commitment is None
        or not isinstance(pending.state.commitment.command.allocation, CollectionAllocation)
        or pending.state.commitment.command.allocation.collection.target_cash_micros != "1450000000"
    ):
        raise ValueError("pending cold checkpoint lacks the exact accepted collection")
    if not any(
        a.action == "review"
        and a.event == "preview_admitted"
        and isinstance(a.state.selected_allocation, CollectionAllocation)
        and a.state.selected_allocation.collection.target_cash_micros == "280000000"
        for a in segments["opening"].actions
    ):
        raise ValueError("walk lacks the original opening proposal before editing")
    history_before = WalkStage.model_validate(
        _walk_scope(evidence, "before-history-archive-return.json")
    )
    history_after = WalkStage.model_validate(
        _walk_scope(evidence, "after-history-archive-return.json")
    )
    if history_before.facts != history_after.facts or history_after.facts != terminal.facts:
        raise ValueError(
            "history or Archive Return changed authoritative reports, receipts or the draft"
        )
    actor = pending.state.commitment.command.actor_id
    authority = pending.state.commitment.command.authority_id
    stages = installed_walk_stages(
        evidence, segments["walk"], material.boundaries, actor, authority
    )
    stages[0] = pending
    if terminal.state.installed_organizer != stages[10].state.installed_organizer:
        raise ValueError("completed cold Open changed the controlled organizer and standing state")
    period_rows = material.independent_account_posting_audit.get("periods")
    if not isinstance(period_rows, list):
        raise ValueError("walk lacks its versioned independent aid boundaries")
    ordered = [AidBoundary.model_validate(row) for row in period_rows]
    verify_contribution_history(ordered)
    initial = MaterialRecord.model_validate(_artifact(base, native.opening, MATERIAL_RECORD_BYTES))
    if initial.opening is None:
        raise ValueError("walk lacks its authenticated opening partner foundation")
    inputs = evidence.read_reference(evidence.reference("inputs.sha256")).decode().splitlines()
    source = [
        m[1]
        for line in inputs
        if (m := re.fullmatch(r"([0-9a-f]{64})  content/scenarios/national/defines\.toml", line))
    ]
    if len(source) != 1:
        raise ValueError("national run lacks the captured game policy for its recipient grants")
    disclosed, sources = verify_walk_disclosures(initial.opening, ordered, stages, actor, source[0])
    for trace in segments.values():
        for a in trace.actions:
            s = a.state
            if (
                a.action
                not in ("inspect_subject_evidence", "next_evidence", "open_archive_evidence")
                or a.event == "refused"
            ):
                continue
            raw = disclosed.get(s.selected_report_id or "")
            if (
                raw is None
                or (
                    s.selected_subject,
                    s.selected_report_observed_period,
                    s.selected_report_acquired_period,
                )
                != (
                    f"AidPartner({raw['subject_id']})",
                    raw["observed_period"],
                    raw["acquired_period"],
                )
                or raw["acquired_period"] > s.viewed_tick
            ):
                raise ValueError("displayed report differs from its subject and period grant")
    if [b.period for b in ordered] != list(range(1, 11)):
        raise ValueError("ten actual aid boundaries required for the national walk")
    details = []
    missing = []
    expected_allocations = {
        "local-food": ("local_aid", 1, "0"),
        "remote-mixed": ("remote_aid", 2, "280000000"),
        "local-cash": ("local_aid", 0, "1000000000"),
    }
    for label, (choice, food, cash) in expected_allocations.items():
        choices = [
            c
            for c in originals.values()
            if c.command.choice == choice
            and isinstance(c.command.allocation, AidAllocation)
            and (c.command.allocation.aid.food_quantity, c.command.allocation.aid.cash_micros)
            == (food, cash)
        ]
        if not choices:
            missing.append(label + " original")
            continue
        if len(choices) != 1:
            raise ValueError("walk repeats an intended aid original")
        c = choices[0]
        practices = tuple(
            p
            for row in ordered
            for p in row.independent_practices
            if p.original_commitment == c.commitment_id
        )
        proof = walk_response(
            c.commitment_id,
            practices,
            terminal.facts["receipts"],
            actor=c.command.actor_id,
            choice=choice,
        )
        proof["selection"] = label
        proof["material_legs"] = [
            {**leg, "period": b.period}
            for b in ordered
            for leg in b.selected_aid
            if leg["original_commitment"] == list(c.commitment_id)
        ]
        admitted = AidOriginal.model_validate(
            _artifact(
                base,
                next(
                    a
                    for a in native.aid_originals
                    if a.name == "aid-" + bytes(c.commitment_id).hex() + ".json"
                ),
                MATERIAL_RECORD_BYTES,
            )
        )
        if len({p.material_commitment_id for p in practices}) > 1:
            raise ValueError("material commitment identity changed across admitted original legs")
        origin = admitted.review.before
        offer = origin.get("aid")
        treasury = origin.get("collection")
        if (
            not isinstance(offer, list)
            or not isinstance(treasury, dict)
            or not isinstance(treasury.get("organization_cash_micros"), str)
        ):
            raise ValueError("accepted aid original lacks its actual treasury and material offers")
        kind = "remote" if choice == "remote_aid" else "local"
        admitted_offers = [
            row for row in offer if isinstance(row, dict) and row.get("kind") == kind
        ]
        if (
            len(admitted_offers) != 1
            or admitted_offers[0].get("period") != c.command.expected_period
        ):
            raise ValueError("native aid original does not bind its current recipient offer")
        proof["admitted_offer"] = admitted_offers[0]
        proof["organization_cash_before_micros"] = treasury["organization_cash_micros"]
        confirmations = [
            a
            for a in segments["walk"].actions
            if a.action == "confirm"
            and a.state.commitment == c
            and a.event == "acceptance_admitted"
        ]
        if len(confirmations) != 1:
            raise ValueError("walk acceptance lacks one observed timestamp")
        proof["accepted_monotonic_ns"] = confirmations[0].completed_monotonic_ns
        for row in proof["material_legs"]:
            installed = WalkStage.model_validate(
                _walk_scope(evidence, f"walk-p{row['period']}-installed.json")
            )
            if (
                installed.state.durable_tick != row["period"]
                or installed.state.tick_content_hash
                != material.boundaries[row["period"] - 1].tick_content_hash
            ):
                raise ValueError("dated material leg differs from installed period and marker")
            row["observed_utc"] = installed.utc.isoformat()
            row["observed_monotonic_ns"] = installed.monotonic_ns
        recipient = admitted_offers[0]["recipient_actor_id"]
        mandate = TypeAdapter(Bytes32).validate_python(admitted_offers[0]["mandate_id"])
        if any(
            leg["mandate"] != list(mandate) or leg["dispatch_period"] != c.resolves_period
            for leg in proof["material_legs"]
        ):
            raise ValueError("material leg differs from the actual offer mandate or dispatch")
        if c.command.actor_id != actor or c.command.authority_id != authority:
            raise ValueError("aid command names another actor or authority")
        first = proof["first_response_receipt"]
        if first is not None:
            first_digests = {
                p.first_response_receipt_sha256
                for p in practices
                if p.first_response_period is not None
            }
            if len(first_digests) != 1 or None in first_digests:
                raise ValueError("full first response hash changed in the retained practice")
            digest = next(d for d in first_digests if d is not None)
            verify_first_receipt_prefix(stages, first, bytes(digest))
            verify_first_receipt_prefix({10: terminal}, first, bytes(digest))
        for p in practices:
            stage = stages[p.period]
            receipt_rows = stage.facts["receipts"]
            current = [r for r in receipt_rows if r["receipt_id"] == list(p.practice_receipt_id)]
            final = [
                r
                for r in terminal.facts["receipts"]
                if r["receipt_id"] == list(p.practice_receipt_id)
            ]
            view = stage.state.installed_organizer
            if (
                p.mandate != mandate
                or p.dispatch_period != c.resolves_period
                or len(current) != 1
                or current != final
                or p.partner_actor not in (None, recipient)
                or view is None
            ):
                raise ValueError(
                    "dated receipt, admitted mandate or partner changed across close and restore"
                )
            history = [
                h
                for h in view.aid_response_history
                if h.original_commitment_id == c.commitment_id and h.period == p.period
            ]
            if len(history) != 1 or (
                history[0].practice_receipt_id,
                history[0].first_response_receipt_id,
            ) != (p.practice_receipt_id, p.first_response_receipt_id):
                raise ValueError(
                    "installed aid history differs from the dated practice and first response"
                )
        if label == "remote-mixed":
            verify_mixed_follow_up(segments["walk"], stages, ordered, c)
        pending_periods = verify_freight_reopens(
            stages,
            proof["material_legs"],
            c.commitment_id,
            mandate,
            c.resolves_period,
            practices[0].material_commitment_id if practices else None,
            first,
            remote=choice == "remote_aid",
        )
        proof["in_transit_reopened_periods"] = pending_periods
        if label == "remote-mixed" and has_later_retained_leg(practices):
            if not pending_periods:
                missing.append("installed in-transit mixed freight through actual reopen")
            completed_view = terminal.state.installed_organizer
            if (
                completed_view is None
                or first is None
                or not any(
                    h.original_commitment_id == c.commitment_id
                    and h.first_response_receipt_id == tuple(first["receipt_id"])
                    for h in completed_view.aid_response_history
                )
            ):
                missing.append("completed process-cold installed mixed first response")
        proof["recipient_reports"] = [
            r
            for key, r in disclosed.items()
            if r["subject_id"] == recipient
            and sources[key].mandate_id == mandate
            and c.command.expected_period <= r["observed_period"]
        ]
        topics = {
            r["report"]["facts"]["basis"]
            for r in proof["recipient_reports"]
            if r["observed_period"] >= c.resolves_period
        }
        if not {"food_provision", "essential_services", "participation_time"}.issubset(topics):
            missing.append(label + " dated recipient food, services and time disclosures")
        if label == "local-cash":
            following = [
                r
                for r in proof["recipient_reports"]
                if r["observed_period"] == c.resolves_period + 1
            ]
            food_rows = [r for r in following if r["report"]["facts"]["basis"] == "food_provision"]
            service_rows = [
                r for r in following if r["report"]["facts"]["basis"] == "essential_services"
            ]
            if food_rows and "cash-following-purchase" in frames:
                allowed = {bytes(r["observation_id"]).hex() for r in food_rows}
                for image in frames["cash-following-purchase"]:
                    frame = WalkFrame.model_validate(
                        _walk_scope(
                            PrivateEvidence(base.parent / "raw"),
                            Path(image).with_suffix(".json").name,
                        )
                    )
                    if (
                        frame.state.selected_report_id not in allowed
                        or frame.state.selected_subject != f"AidPartner({recipient})"
                        or frame.state.viewed_tick != c.resolves_period + 1
                    ):
                        raise ValueError(
                            "following purchase frame does not display the actual dated recipient food report"
                        )
            if not food_rows or not service_rows:
                missing.append(
                    "following dated recipient food purchasing and service settlement disclosures"
                )
            proof["following_ordinary_purchasing"] = [
                r["report"]["facts"] for r in food_rows + service_rows
            ]
        if label == "local-food":
            collection = origin.get("collection_resolutions")
            if not isinstance(collection, list):
                raise ValueError(
                    "local food admission lacks the preceding authoritative collection resolution"
                )
            rows = [
                row
                for row in collection
                if isinstance(row, dict)
                and row.get("commitment") == pending.state.commitment.model_dump(mode="json")
            ]
            if len(rows) != 1:
                raise ValueError("first collection outcome does not bind the pending cold original")
            fact = rows[0].get("fact")
            if not isinstance(fact, dict):
                raise ValueError("first collection resolution lacks its material fact")
            if fact.get("requested_cash_micros") != "1450000000" or fact.get("period") != 1:
                raise ValueError("collection outcome differs from its accepted amount and period")
            proof["prior_collection_fact"] = fact
            if fact.get("collected_cash_micros") != "1450000000":
                missing.append("full requested initial collection")
        if sum(p.food_consumed_quantity for p in practices) != food or sum(
            int(p.cash_received_micros) for p in practices
        ) != int(cash):
            missing.append(label + " full requested material outcome")
        details.append(proof)
        if proof["first_response_receipt"] is None:
            missing.append(label + " first recipient response")
        if label == "remote-mixed" and not has_later_retained_leg(practices):
            missing.append("distinct remote material legs and retained first response")
        if label == "local-cash" and not any(p.cash_received_period for p in practices):
            missing.append("actual local cash transfer")
    basic = {
        "opening",
        "opening-local-report",
        "opening-remote-report",
        "dispatch",
        "answer-report",
        "return",
        "archive-report",
        "restored-completed",
        "cash-following-purchase",
    }
    cash_label = "local-cash-retry" if "local-cash-retry-confirmed" in frames else "local-cash"
    for choice_label in (
        "collection",
        "local-food",
        "remote-mixed",
        "pause-standing",
        cash_label,
        "resume-standing",
    ):
        basic.update(choice_label + "-" + s for s in ("selected", "reviewed", "confirmed"))
    missing.extend("raw frames " + stage for stage in sorted(basic - frames.keys()))
    verify_directives(list(originals.values()), stages, actor, authority, missing)
    if not all(
        material.independent_account_posting_audit.get(key) == "passed"
        for key in (
            "cash_and_in_kind_postings",
            "time_partition_and_residual_bound",
            "exact_final_contribution_debit_ledger",
        )
    ):
        missing.append("authenticated material and finite-hours accounting")
    process_memory = _walk_memory(
        policy,
        base,
        native,
        memory,
        segments,
        {b.tick: b.tick_content_hash for b in material.boundaries},
    )
    if (
        native_result["status"] == "failed"
        or not native_result["separate_byte_budgets_passed"]
        or native_result["native_read_and_reopen_budgets_passed"] is False
        or storage["status"] == "failed"
    ):
        raise ValueError("walk exceeded an unchanged material, storage, read or native phase limit")
    wall = _walk_scope(evidence, "walk-wall.json")
    if (
        wall["campaign"] != native.campaign
        or not (
            wall["start_ns"]
            <= process_memory[0]["start_ns"]
            < process_memory[-1]["end_ns"]
            <= wall["end_ns"]
        )
        or wall["end_ns"] - wall["start_ns"] > timing.run.elapsed_ns
    ):
        raise ValueError("walk wall clock does not cover all cold restarts and verification")
    return {
        "status": "incomplete" if missing else "qualified",
        "missing": missing,
        "actual_periods": 10,
        "process_segments": process_memory,
        "full_walk_elapsed_ns": wall["end_ns"] - wall["start_ns"],
        "native_operation_elapsed_ns": timing.run.elapsed_ns,
        "peak_combined_rss_upper_bound_bytes": max(
            s["peak_combined_rss_upper_bound_bytes"] for s in process_memory
        )
        if memory is not None
        else None,
        "pending_process_cold": "collect",
        "pending_in_process": "remote_mixed",
        "mixed_pending_recovery": native_result["mixed_pending_recovery"],
        "completed_process_cold_period": 10,
        "native_aid_timelines": details,
        "granted_recipient_reports": disclosed,
        "raw_frames": frames,
        "layout_and_capture_elapsed_ns": capture_wall_ns,
        "opening_treasury_display": "requires inspection of retained opening frames",
        "recipient_manufactured_purchase_quantities": "unverified by this native audit reader",
        "recipient_purchase_funding_source": "unattributed",
        "user_enjoyment": "unqualified",
    }
