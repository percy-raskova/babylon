"""Join native witnesses inside the existing national qualification evaluator.

This module neither drives the economy nor creates capture authority. The owned
supervisor produces the files. Original accepted commands, shared Rust accounting,
PostgreSQL/Archive evidence and combined-role capture must agree before admission.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, JsonValue, StrictInt, StrictStr, field_validator, model_validator
from tools.devtools.national_storage_qualification import (
    CombinedMemoryEvidence,
    EconomicBoundary,
    EconomicSummary,
    FrozenRecord,
    NativeTimings,
    Nonnegative,
    PlayableReport,
    Policy,
    Positive,
    ProductionRenewalEvidence,
    Sha256,
    Snapshot,
    TradeBoundary,
    TradeSummary,
    evaluate_combined_memory,
    strict_json_bytes,
    verify_economic_summary,
)
from tools.devtools.national_windowed_qualification import (
    EXPECTED,
    ActionObservation,
    ControlsEvidence,
)

# Designed framing bounds, not alternative economic or save-growth policy.
MATERIAL_RECORD_BYTES = 4_194_304  # Matches the native record writer.
CONTROLS_RECORD_BYTES = 134_217_728
MANIFEST_BYTES = 1_048_576
Byte = Annotated[StrictInt, Field(ge=0, le=255)]
Bytes16 = Annotated[tuple[Byte, ...], Field(min_length=16, max_length=16)]
Bytes32 = Annotated[tuple[Byte, ...], Field(min_length=32, max_length=32)]
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
    version: Literal[2]
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
    version: Literal[4]
    scope: Literal["native_material_timing_recovery_join_v4"]
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


class NativeOpening(Opening):
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
    version: Literal[1]
    period: Positive
    tick_content_hash: Sha256
    canonical_receipt_sha256: Sha256
    selected_aid: tuple[dict[str, JsonValue], ...]
    independent_practices: tuple[dict[str, JsonValue], ...]


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
    version: Literal[4]
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


class Command(NativeRecord):
    campaign_id: Bytes16
    actor_id: U64
    authority_id: Bytes16
    expected_period: Nonnegative
    content_digest: Bytes32
    resource_digest: Bytes32
    nonce: Bytes16
    choice: Literal["local_aid", "remote_aid", "pause_standing", "resume_standing"]


class Commitment(NativeRecord):
    command: Command
    resolves_period: Positive
    commitment_id: Bytes32


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
            action.event != EXPECTED.get(action.action, "applied") or action.reason is not None
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


def _originals(
    evidence: NativeRunEvidence,
    directory: Path,
    controls: ControlsEvidence,
    playable: PlayableReport,
) -> int:
    accepted = {}
    reviewed: ActionObservation | None = None
    for action in controls.actions:
        if action.action == "review":
            reviewed = action
        elif action.action == "confirm":
            commitment = Commitment.model_validate(action.state.commitment)
            if reviewed is None or reviewed.state.reviewed_command != commitment.command.model_dump(
                mode="json"
            ):
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
        posted[identity] = row
    if set(posted) != set(accepted):
        raise ValueError("native accepted aid differs from independent material accounting")
    for artifact in evidence.aid_originals:
        original = AidOriginal.model_validate(_artifact(directory, artifact, MATERIAL_RECORD_BYTES))
        identity = bytes(original.commitment.commitment_id).hex()
        if identity not in accepted or artifact.name != "aid-" + identity + ".json":
            raise ValueError("native original aid file does not name its accepted commitment")
        review, confirm, commitment = accepted[identity]
        command = commitment.command
        epoch = review.state.scope_epoch
        view = original.review.before.get("view")
        if epoch is None or not isinstance(view, dict):
            raise ValueError("native original aid lacks its source runtime or organizer view")
        if (
            (original.policy_sha256, original.foundation_sha256)
            != (evidence.policy_sha256, evidence.foundation_sha256)
            or original.commitment != commitment
            or original.review.command != command
            or bytes(command.campaign_id) != UUID(evidence.campaign).bytes
            or command.expected_period != review.state.durable_tick
            or commitment.resolves_period != command.expected_period + 1
            or original.tick_content_hash != review.state.tick_content_hash
            or original.review.scope != RuntimeScope(epoch=epoch, campaign_id=evidence.campaign)
            or original.review.observation_generation != review.state.generation
            or original.review.admission != review.state.preview
            or view.get("period") != command.expected_period
            or original.review.admission.get("refusal") is not None
            or confirm.state.durable_tick != command.expected_period
            or posted[identity].get("preview") != original.review.admission
            or posted[identity].get("period") != commitment.resolves_period
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
    steps, reopens = _trace(controls)
    actual = tuple(t.tick for t in ticks)
    if (
        tuple(a.state.durable_tick for a in steps) != actual
        or tuple(a.state.durable_tick for a in reopens) != actual
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
    if tuple(a.name for a in evidence.recoveries) != tuple(
        f"recovery-{a.state.durable_tick}-{a.state.scope_epoch}.json" for a in reopens
    ):
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
    economic_prefix: list[EconomicBoundary] = []
    previous_hash = None
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
        evidence.recoveries,
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
        if (
            advance.runtime_scope
            != RuntimeScope(epoch=record.runtime_epoch, campaign_id=evidence.campaign)
            or advance.foundation_sha256 != evidence.foundation_sha256
            or advance.policy_sha256 != policy_sha256
            or advance.expected_tail
            != Tail(resolve_tick=tick.tick - 1, tick_content_hash=previous_hash)
            or advance.committed_tail
            != Tail(resolve_tick=tick.tick, tick_content_hash=facts.tick_content_hash)
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
            or record.aid.model_dump(mode="json", exclude={"version"}) != account
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
    memory_status: object = "incomplete"
    if memory is not None:
        if (
            memory.ownership_record_sha256,
            memory.source_manifest_sha256,
            memory.executable_manifest_sha256,
        ) != (
            evidence.ownership_record_sha256,
            evidence.source_manifest_sha256,
            evidence.executable_manifest_sha256,
        ):
            raise ValueError(
                "native source, executable or ownership admission differs from combined capture"
            )
        memory_status = evaluate_combined_memory(
            policy,
            policy_sha256,
            memory,
            playable.campaign,
            playable.foundation_sha256,
            tuple(t.marker_and_encoded_package_hashes[-1][1] for t in ticks),
        )["status"]
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
    failed = not byte_limits or not phase_limits or material_status == "failed"
    qualified = completed and memory_status == "qualified" and material_status == "qualified"
    return {
        "version": 4,
        "graph_foundation_sha256": evidence.graph_foundation_sha256,
        "status": "failed" if failed else ("qualified" if qualified else "incomplete"),
        "actual_periods": len(ticks),
        "accepted_original_aid_commands": originals,
        "checkpoint_reopens": len(reopens),
        "native_advance_timing_receipts": len(evidence.advances),
        "advance_measurement": "client_enqueue_to_accepted_commit",
        "archive_measurement": "accepted_commit_to_accepted_archive_completion",
        "cold_reopen_measurement": "client_enqueue_to_installed_authenticated_read",
        "combined_memory_status": memory_status,
        "material_status": material_status,
        "separate_byte_budgets_passed": byte_limits,
        "native_read_and_reopen_budgets_passed": phase_limits,
        "enjoyment_status": "unqualified",
        "scope": "Actual native action custody joined to authenticated material, Archive, storage and checkpoint recovery; scripted interaction does not establish enjoyment",
    }
