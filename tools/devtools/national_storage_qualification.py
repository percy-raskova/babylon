"""Evaluate retained national storage snapshots; never access PostgreSQL."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from typing import Annotated, Literal, NotRequired, TypedDict
from uuid import UUID

from defusedxml import ElementTree as ET  # type: ignore[import-untyped]
from defusedxml.common import DefusedXmlException  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

Nonnegative = Annotated[StrictInt, Field(ge=0, le=2**63 - 1)]
RELATION_COLUMNS = (
    "schema",
    "relation",
    "base_heap_all_forks_bytes",
    "base_index_bytes",
    "toast_heap_and_index_bytes",
    "total_bytes",
    "estimated_rows",
)
Relation = tuple[str, str, Nonnegative, Nonnegative, Nonnegative, Nonnegative, float]
HashRow = tuple[Nonnegative, str, str, str, str]
ByteColumn = tuple[Nonnegative, Nonnegative, Nonnegative, tuple[str | None, ...]]


class FrozenRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


Positive = Annotated[StrictInt, Field(gt=0, le=2**63 - 1)]


class Policy(FrozenRecord):
    version: Literal[3]
    name: Literal["national_storage_qualification_v3"]
    evidence_class: Literal["Designed"]
    storage_charge_method: Literal["positive_growth_by_component_and_boundary_v1"]
    model_year_ticks: Literal[13]
    qualification_ticks: Literal[52]
    county_count: Literal[3144]
    maximum_tick_growth_bytes: Positive
    optimization_tick_growth_bytes: Positive
    maximum_total_save_bytes: Positive
    provisional_duration_years: Positive
    save_qualification_ticks: Positive
    advance_aim_min_seconds: Positive
    advance_aim_max_seconds: Positive
    maximum_advance_p95_seconds: Positive
    p95_minimum_samples: Positive
    maximum_cold_open_seconds: Positive
    maximum_archive_catchup_seconds: Positive
    maximum_production_read_seconds: Positive
    maximum_focused_control_seconds: Positive
    routine_smoke_periods: Positive
    maximum_routine_smoke_seconds: Positive
    preferred_qualification_seconds: Positive

    @field_validator(
        "version", "model_year_ticks", "qualification_ticks", "county_count", mode="before"
    )
    @classmethod
    def exact_integer_policy(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("policy numeric fields must be exact JSON integers")
        return value

    @model_validator(mode="after")
    def coherent_targets(self) -> Policy:
        if self.optimization_tick_growth_bytes > self.maximum_tick_growth_bytes:
            raise ValueError("optimization target must not exceed development ceiling")
        if (
            not self.advance_aim_min_seconds
            <= self.advance_aim_max_seconds
            <= self.maximum_advance_p95_seconds
        ):
            raise ValueError("advance aim must fit p95 ceiling")
        if self.p95_minimum_samples < 2:
            raise ValueError("empirical p95 requires at least two samples")
        if self.save_qualification_ticks != self.provisional_duration_years * self.model_year_ticks:
            raise ValueError("save horizon must equal duration times model-year ticks")
        if self.p95_minimum_samples > self.save_qualification_ticks:
            raise ValueError("p95 samples must fit the admitted save horizon")
        if self.routine_smoke_periods > self.save_qualification_ticks:
            raise ValueError("routine smoke must fit the admitted save horizon")
        if self.save_qualification_ticks < self.qualification_ticks:
            raise ValueError("save horizon must cover full correctness qualification")
        return self


class Marker(FrozenRecord):
    count: Nonnegative
    maximum_resolve_tick: Nonnegative

    @model_validator(mode="after")
    def contiguous(self) -> Marker:
        if self.count != self.maximum_resolve_tick:
            raise ValueError("marker count must equal maximum resolve tick")
        return self


Sha256 = Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
IndexDiagnostic = tuple[str, str, str, Nonnegative]
LookupHashRow = tuple[Nonnegative, Sha256]


class PackageClaim(FrozenRecord):
    storage_layout: Literal["period_local_lookup_v3"]
    state_storage_version: Literal[4]
    tick: Nonnegative
    register_storage_bytes: Nonnegative
    receipt_storage_bytes: Nonnegative
    lookup_delta_bytes: Nonnegative
    total_storage_package_bytes: Nonnegative
    canonical_register_bytes: Nonnegative
    canonical_register_sha256: Sha256
    canonical_receipt_bytes: Nonnegative
    canonical_receipt_sha256: Sha256
    receipt_period: Nonnegative
    opening_register_sha256: Sha256
    opening_lookup_entries: Nonnegative
    previous_lookup_chain_sha256: Sha256
    lookup_chain_sha256: Sha256
    state_lookup_entries: Nonnegative
    complete_lookup_entries: Nonnegative
    period_lookup_entries: Nonnegative
    lookup_packed_bytes: Nonnegative
    lookup_descriptor_bytes: Nonnegative
    lookup_descriptor_sha256: Sha256
    state_period_lookup_entries: Nonnegative
    receipt_period_lookup_entries: Nonnegative
    claim_qualification: Literal[
        "Header claims authenticated by actual Rust cold-open; Python does not replace codec/canonical validation."
    ]

    @field_validator("state_storage_version", mode="before")
    @classmethod
    def current_state_version(cls, value: object) -> object:
        if type(value) is not int or value != 4:
            raise ValueError("unsupported state storage evidence version")
        return value

    @model_validator(mode="after")
    def checked_headers(self) -> PackageClaim:
        if not self.tick or self.receipt_period != self.tick:
            raise ValueError("receipt header period must equal committed tick")
        if not (
            self.opening_lookup_entries
            <= self.state_lookup_entries
            <= self.complete_lookup_entries
            <= 2**32 - 1
        ):
            raise ValueError("lookup prefix counts must be ordered and representable")
        if (
            self.complete_lookup_entries - self.opening_lookup_entries != self.period_lookup_entries
            or self.state_lookup_entries - self.opening_lookup_entries
            != self.state_period_lookup_entries
            or self.complete_lookup_entries - self.state_lookup_entries
            != self.receipt_period_lookup_entries
            or self.lookup_packed_bytes != 4 + 33 * self.period_lookup_entries
        ):
            raise ValueError("lookup entry and packed byte claims disagree")
        if (
            not 4 + 5 * self.period_lookup_entries
            <= self.lookup_descriptor_bytes
            <= self.lookup_packed_bytes
        ):
            raise ValueError("descriptor length disagrees with logical entry count")
        if self.lookup_packed_bytes > 1_000_000_000:
            raise ValueError("lookup packed bytes exceed current Rust bound")
        limits = (
            (self.canonical_register_bytes, 1_000_000_000),
            (self.canonical_receipt_bytes, 872_612_528),
            (self.register_storage_bytes, 1_000_000_000 + 1_000_000_000 // 256 + 16_384),
            (
                self.receipt_storage_bytes,
                872_612_528 + len(b"BabylonReceiptStorageV2\0") + 88 + 36 * 59,
            ),
            (self.lookup_delta_bytes, 1_000_000_000 + 1_000_000_000 // 256 + 1024),
        )
        if any(not 0 < value <= maximum for value, maximum in limits):
            raise ValueError("package or canonical length exceeds current Rust bound")
        if (
            self.register_storage_bytes < len(b"babylon.state-storage.v4\0") + 142
            or self.receipt_storage_bytes < len(b"BabylonReceiptStorageV2\0") + 88 + 36 * 59
            or self.lookup_delta_bytes < len(b"BabylonPeriodLookupV3\0") + 162
        ):
            raise ValueError("storage package shorter than current header framing")
        if (
            self.total_storage_package_bytes
            != self.register_storage_bytes + self.receipt_storage_bytes + self.lookup_delta_bytes
        ):
            raise ValueError("storage package total disagrees with individual packages")
        return self


def package_claim_from_headers(
    tick: int,
    state_head: bytes,
    receipt_head: bytes,
    lookup_head: bytes,
    state_size: int,
    receipt_size: int,
    lookup_size: int,
) -> PackageClaim:
    """Read current headers; full body authentication belongs to the Rust reopen."""
    sd = b"babylon.state-storage.v4\0"
    rd = b"BabylonReceiptStorageV2\0"
    ld = b"BabylonPeriodLookupV3\0"
    for head, domain, fields in (
        (state_head, sd, 142),
        (receipt_head, rd, 88),
        (lookup_head, ld, 162),
    ):
        if not head.startswith(domain) or len(head) < len(domain) + fields:
            raise ValueError("unsupported or truncated current storage header")
    state, receipt, lookup = (
        state_head[len(sd) :],
        receipt_head[len(rd) :],
        lookup_head[len(ld) :],
    )
    if int.from_bytes(lookup[:2], "big") != 3:
        raise ValueError("unsupported period lookup version")
    opening = lookup[2:34]
    if state[:32] != opening or int.from_bytes(lookup[34:42], "big") != tick:
        raise ValueError("period lookup opening or tick disagrees with state context")
    packed_length = int.from_bytes(lookup[74:82], "big")
    if packed_length < 4 or (packed_length - 4) % 33:
        raise ValueError("lookup packed length is not a counted typed identity sequence")
    if int.from_bytes(lookup[154:162], "big") != lookup_size - len(ld) - 162:
        raise ValueError("lookup compressed length disagrees with stored package size")
    previous_chain = lookup[42:74]
    chain = hashlib.sha256(
        b"BabylonPeriodLookupChainV1\0" + opening + lookup[34:42] + previous_chain + lookup[82:114]
    ).digest()
    if state[64:96] != chain:
        raise ValueError("period lookup chain disagrees with state anchor")
    state_prefix = int.from_bytes(state[104:108], "big")
    receipt_prefix = int.from_bytes(receipt[48:56], "big")
    period_entries = (packed_length - 4) // 33
    opening_entries = receipt_prefix - period_entries
    return PackageClaim(
        storage_layout="period_local_lookup_v3",
        state_storage_version=4,
        tick=tick,
        register_storage_bytes=state_size,
        receipt_storage_bytes=receipt_size,
        lookup_delta_bytes=lookup_size,
        total_storage_package_bytes=state_size + receipt_size + lookup_size,
        canonical_register_bytes=int.from_bytes(state[96:104], "big"),
        canonical_register_sha256=state[32:64].hex(),
        canonical_receipt_bytes=int.from_bytes(receipt[:8], "big"),
        canonical_receipt_sha256=receipt[8:40].hex(),
        receipt_period=int.from_bytes(receipt[40:48], "big"),
        opening_register_sha256=opening.hex(),
        opening_lookup_entries=opening_entries,
        previous_lookup_chain_sha256=previous_chain.hex(),
        lookup_chain_sha256=chain.hex(),
        state_lookup_entries=state_prefix,
        complete_lookup_entries=receipt_prefix,
        period_lookup_entries=period_entries,
        lookup_packed_bytes=packed_length,
        lookup_descriptor_bytes=int.from_bytes(lookup[114:122], "big"),
        lookup_descriptor_sha256=lookup[122:154].hex(),
        state_period_lookup_entries=state_prefix - opening_entries,
        receipt_period_lookup_entries=receipt_prefix - state_prefix,
        claim_qualification="Header claims authenticated by actual Rust cold-open; Python does not replace codec/canonical validation.",
    )


class Snapshot(FrozenRecord):
    stage: str
    database: str
    campaign: str
    server: str
    database_bytes: Nonnegative
    relations_columns: tuple[str, ...]
    relations: tuple[Relation, ...]
    acknowledged_markers: dict[str, Marker]
    wal_lsn_container_wide: str
    bytea_columns_count_canonical_octets_column_storage_compression: dict[str, ByteColumn]
    county_geoids: tuple[str, ...]
    marker_and_encoded_package_hashes: tuple[HashRow, ...]
    actual_rust_storage_package_claims: tuple[PackageClaim, ...]
    index_diagnostics_not_additional_totals: tuple[IndexDiagnostic, ...]
    lookup_delta_hashes: tuple[LookupHashRow, ...] | None = None

    @field_validator("relations", mode="before")
    @classmethod
    def exact_estimates(cls, value: object) -> object:
        if not isinstance(value, (list, tuple)) or any(
            not isinstance(row, (list, tuple)) or len(row) != 7 or type(row[6]) not in (int, float)
            for row in value
        ):
            raise ValueError("estimated rows must be finite JSON numbers")
        return value

    @model_validator(mode="after")
    def evidence_shape(self) -> Snapshot:
        if not all((self.stage, self.database, self.campaign, self.server)):
            raise ValueError("snapshot identity and stage must be nonempty")
        self.check_relations()
        if set(self.acknowledged_markers) != {"tick_commit", "material_tick_v3"}:
            raise ValueError("both exact acknowledged marker families are required")
        if (
            self.acknowledged_markers["tick_commit"]
            != self.acknowledged_markers["material_tick_v3"]
        ):
            raise ValueError("material rows require matching committed markers")
        columns = self.bytea_columns_count_canonical_octets_column_storage_compression
        material_columns = {key for key in columns if key.startswith("material_tick_v3.")}
        if material_columns != {
            "material_tick_v3." + name
            for name in (
                "identity_bytes",
                "register_storage_bytes",
                "receipt_storage_bytes",
                "lookup_delta_bytes",
            )
        }:
            raise ValueError("only the four current encoded material byte columns are allowed")
        for column in (
            "identity_bytes",
            "register_storage_bytes",
            "receipt_storage_bytes",
            "lookup_delta_bytes",
        ):
            column_name = "material_tick_v3." + column
            if column_name not in columns or columns[column_name][0] != self.tick:
                raise ValueError("material tick byte columns must match acknowledged markers")
        if not re.fullmatch(r"[0-9A-Fa-f]+/[0-9A-Fa-f]{1,8}", self.wal_lsn_container_wide):
            raise ValueError("invalid container-wide WAL LSN")
        if tuple(sorted(set(self.county_geoids))) != self.county_geoids or any(
            not re.fullmatch(r"\d{5}", g) for g in self.county_geoids
        ):
            raise ValueError("county roster must be sorted unique five-digit GEOIDs")
        if len(self.marker_and_encoded_package_hashes) != self.tick or any(
            row[0] != index for index, row in enumerate(self.marker_and_encoded_package_hashes, 1)
        ):
            raise ValueError("authoritative hash rows must cover every acknowledged tick in order")
        if any(
            not re.fullmatch("[0-9a-f]{64}", h)
            for r in self.marker_and_encoded_package_hashes
            for h in r[1:]
        ):
            raise ValueError("authoritative hashes must be canonical lowercase SHA-256 hex")
        self.check_packages()
        return self

    def check_relations(self) -> None:
        if self.relations_columns != RELATION_COLUMNS:
            raise ValueError("unexpected relation column layout")
        keys = [(r[0], r[1]) for r in self.relations]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate parent relation")
        if any(
            schema not in {"babylon_state", "babylon_ref", "babylon_meta", "public"}
            for schema, _ in keys
        ):
            raise ValueError(
                "only ordinary game parent relations are allowed; TOAST belongs in parent totals"
            )
        if any(r[2] + r[3] + r[4] != r[5] for r in self.relations):
            raise ValueError("relation total must equal heap plus index plus parent TOAST bytes")
        if any(not math.isfinite(r[6]) for r in self.relations):
            raise ValueError("estimated rows must be finite")

    def check_packages(self) -> None:
        if len(self.actual_rust_storage_package_claims) != self.tick or any(
            claim.tick != index
            for index, claim in enumerate(self.actual_rust_storage_package_claims, 1)
        ):
            raise ValueError("package claims must cover every marked tick in order")
        for previous, current in zip(
            self.actual_rust_storage_package_claims,
            self.actual_rust_storage_package_claims[1:],
            strict=False,
        ):
            if (
                current.opening_register_sha256 != previous.opening_register_sha256
                or current.opening_lookup_entries != previous.opening_lookup_entries
            ):
                raise ValueError("period lookups must share the same immutable opening seed")
            if current.previous_lookup_chain_sha256 != previous.lookup_chain_sha256:
                raise ValueError("period lookup chain must match the preceding committed period")
        for column in ("register_storage_bytes", "receipt_storage_bytes", "lookup_delta_bytes"):
            if self.bytea_columns_count_canonical_octets_column_storage_compression[
                "material_tick_v3." + column
            ][1] != sum(getattr(c, column) for c in self.actual_rust_storage_package_claims):
                raise ValueError("wire package lengths disagree with byte-column octets")
        index_keys = [(r[0], r[1], r[2]) for r in self.index_diagnostics_not_additional_totals]
        if len(index_keys) != len(set(index_keys)) or any(
            (r[0], r[1]) not in [(r[0], r[1]) for r in self.relations]
            for r in self.index_diagnostics_not_additional_totals
        ):
            raise ValueError("index diagnostics must identify unique admitted parent indexes")
        for relation in self.relations:
            if (
                sum(
                    r[3]
                    for r in self.index_diagnostics_not_additional_totals
                    if r[:2] == relation[:2]
                )
                > relation[3]
            ):
                raise ValueError("index diagnostics exceed charged parent index bytes")
        if self.lookup_delta_hashes is not None and (
            len(self.lookup_delta_hashes) != self.tick
            or any(row[0] != index for index, row in enumerate(self.lookup_delta_hashes, 1))
        ):
            raise ValueError("lookup delta hashes must cover every marked tick in order")

    @property
    def authoritative_hashes(self) -> tuple[HashRow, ...]:
        return tuple(
            (
                row[0],
                row[1],
                row[2],
                claim.canonical_register_sha256,
                claim.canonical_receipt_sha256,
            )
            for row, claim in zip(
                self.marker_and_encoded_package_hashes,
                self.actual_rust_storage_package_claims,
                strict=True,
            )
        )

    @property
    def tick(self) -> int:
        return self.acknowledged_markers["tick_commit"].count


def lsn(value: str) -> int:
    high, low = value.split("/")
    return (int(high, 16) << 32) + int(low, 16)


def fraction(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


class Growth(TypedDict):
    database_delta_bytes: int
    relation_delta_bytes: dict[str, int]
    positive_parent_relation_growth_bytes: int
    unattributed_database_growth_bytes: int
    charged_growth_bytes: int
    wal_delta_bytes_container_wide: int
    restart_growth: NotRequired[Growth]
    tick: NotRequired[int]
    budget_passed: NotRequired[bool]
    optimization_target_met: NotRequired[bool]
    restart_verified: NotRequired[bool]


def growth(before: Snapshot, after: Snapshot) -> Growth:
    old = {(r[0], r[1]): r[5] for r in before.relations}
    new = {(r[0], r[1]): r[5] for r in after.relations}
    deltas = {
        f"{s}.{n}": new.get((s, n), 0) - old.get((s, n), 0)
        for s, n in sorted(old.keys() | new.keys())
    }
    positive = sum(max(0, d) for d in deltas.values())
    db_delta = after.database_bytes - before.database_bytes
    unattributed = db_delta - sum(deltas.values())
    return {
        "database_delta_bytes": db_delta,
        "relation_delta_bytes": deltas,
        "positive_parent_relation_growth_bytes": positive,
        "unattributed_database_growth_bytes": unattributed,
        "charged_growth_bytes": positive + max(0, unattributed),
        "wal_delta_bytes_container_wide": lsn(after.wal_lsn_container_wide)
        - lsn(before.wal_lsn_container_wide),
    }


def save_footprint(
    policy: Policy,
    baseline: Snapshot,
    opening: Snapshot,
    ticks: tuple[Snapshot, ...],
    reopens: tuple[Snapshot, ...],
    charged: int,
    lookup_authenticated: bool,
) -> dict[str, object]:
    """Charge PG opening and retained growth; projections never establish observation."""
    opening_charge = growth(baseline, opening)["charged_growth_bytes"]
    # Include the allocated schema once, even when campaign delta is smaller.
    opening_bytes = max(opening.database_bytes, opening_charge)
    allocated_peak = max(s.database_bytes for s in (opening, *ticks, *reopens))
    accumulated = max(opening_bytes + charged, allocated_peak)
    complete = (
        len(ticks) >= policy.save_qualification_ticks
        and len(reopens) == len(ticks)
        and lookup_authenticated
    )
    passed = accumulated <= policy.maximum_total_save_bytes
    projections = []
    for years in sorted({10, 25, 50, policy.provisional_duration_years}):
        horizon = years * policy.model_year_ticks
        projected = (
            Fraction(opening_bytes) + Fraction(charged * horizon, len(ticks)) if ticks else None
        )
        projections.append(
            {
                "years": years,
                "ticks": horizon,
                "projected_total_bytes": fraction(projected) if projected is not None else None,
                "projected_duration_ceiling_passed": projected <= policy.maximum_total_save_bytes
                if projected is not None and years == policy.provisional_duration_years
                else None,
                "projected_twenty_gb_boundary_reached": projected >= 20_000_000_000
                if projected is not None
                else None,
            }
        )
    return {
        "evidence_class": "Designed",
        "scope": "PostgreSQL only; external archives/storage are not qualified",
        "duration": "provisional agent duration; no campaign expiry",
        "required_ticks": policy.save_qualification_ticks,
        "maximum_total_save_bytes": policy.maximum_total_save_bytes,
        "opening_charged_growth_bytes": opening_charge,
        "opening_allocated_footprint_bytes": opening_bytes,
        "cumulative_charged_tick_bytes": charged,
        "observed_allocated_database_peak_bytes": allocated_peak,
        "accumulated_charged_footprint_bytes": accumulated,
        "observed_ticks": len(ticks),
        "budget_passed": passed,
        "status": "failed" if not passed else ("qualified" if complete else "incomplete"),
        "projection_basis": "exact average charged observed tick growth; not observed future growth",
        "projections": projections,
    }


def evaluate(
    policy: Policy,
    baseline: Snapshot,
    opening: Snapshot,
    ticks: tuple[Snapshot, ...],
    reopens: tuple[Snapshot, ...],
) -> dict[str, object]:
    identity = (baseline.database, baseline.campaign, baseline.server)
    if any((s.database, s.campaign, s.server) != identity for s in (opening, *ticks, *reopens)):
        raise ValueError("all snapshots must identify the same database, campaign and server")
    if baseline.tick or opening.tick:
        raise ValueError("baseline and opening must have zero acknowledged ticks")
    if len(opening.county_geoids) != policy.county_count:
        raise ValueError("opening must retain the exact national county count")
    if baseline.county_geoids and baseline.county_geoids != opening.county_geoids:
        raise ValueError("baseline county roster differs from opening")
    if tuple(s.tick for s in ticks) != tuple(range(1, len(ticks) + 1)):
        raise ValueError("tick snapshots must be consecutive without gaps or duplicates")
    reopen_map = {s.tick: s for s in reopens}
    if len(reopen_map) != len(reopens) or any(n < 1 or n > len(ticks) for n in reopen_map):
        raise ValueError("restart snapshots must uniquely match supplied committed ticks")
    if tuple(s.tick for s in reopens) != tuple(sorted(reopen_map)):
        raise ValueError("restart snapshots must be in committed tick order")
    previous = opening
    rows = []
    for s in ticks:
        if s.county_geoids != opening.county_geoids:
            raise ValueError("committed tick changed the retained county roster")
        if s.authoritative_hashes[:-1] != previous.authoritative_hashes:
            raise ValueError("previous authoritative tick hashes changed")
        if (
            s.marker_and_encoded_package_hashes[:-1] != previous.marker_and_encoded_package_hashes
            or s.actual_rust_storage_package_claims[:-1]
            != previous.actual_rust_storage_package_claims
            or (
                previous.tick > 0
                and previous.lookup_delta_hashes is not None
                and (
                    s.lookup_delta_hashes is None
                    or s.lookup_delta_hashes[:-1] != previous.lookup_delta_hashes
                )
            )
        ):
            raise ValueError("previous encoded package or lookup history changed")
        reopened = reopen_map.get(s.tick)
        if reopened is not None and (
            reopened.county_geoids != s.county_geoids
            or reopened.authoritative_hashes != s.authoritative_hashes
            or reopened.marker_and_encoded_package_hashes != s.marker_and_encoded_package_hashes
            or reopened.actual_rust_storage_package_claims != s.actual_rust_storage_package_claims
            or reopened.lookup_delta_hashes != s.lookup_delta_hashes
            or reopened.bytea_columns_count_canonical_octets_column_storage_compression
            != s.bytea_columns_count_canonical_octets_column_storage_compression
        ):
            raise ValueError("restart changed county, authoritative hash or byte-column evidence")
        row = growth(previous, s)
        if reopened is not None:
            restart_growth = growth(s, reopened)
            row["restart_growth"] = restart_growth
            row["charged_growth_bytes"] += restart_growth["charged_growth_bytes"]
        row["tick"] = s.tick
        row["budget_passed"] = row["charged_growth_bytes"] <= policy.maximum_tick_growth_bytes
        row["optimization_target_met"] = (
            row["charged_growth_bytes"] <= policy.optimization_tick_growth_bytes
        )
        row["restart_verified"] = reopened is not None
        rows.append(row)
        # Restart storage growth belongs to this committed tick.
        previous = reopened if reopened is not None else s
    charged = sum(int(r["charged_growth_bytes"]) for r in rows)
    budget = all(r["budget_passed"] for r in rows)
    lookup_authenticated = all(s.lookup_delta_hashes is not None for s in (*ticks, *reopens))
    complete = (
        lookup_authenticated
        and len(ticks) >= policy.qualification_ticks
        and len(reopen_map) == len(ticks)
    )
    annual = Fraction(charged * policy.model_year_ticks, len(ticks)) if ticks else None
    twelve = Fraction(charged * 12, len(ticks)) if ticks else None
    footprint = save_footprint(
        policy, baseline, opening, ticks, reopens, charged, lookup_authenticated
    )
    return {
        "policy": policy.model_dump(),
        "status": "failed" if not budget else ("qualified" if complete else "incomplete"),
        "committed_ticks": len(ticks),
        "lookup_delta_hashes_verified": lookup_authenticated,
        "authentication_gaps": []
        if lookup_authenticated
        else ["lookup_delta_bytes SHA-256 absent from recorder evidence"],
        "budget_passed": budget,
        "optimization_target_met": all(r["optimization_target_met"] for r in rows),
        "restart_verified_ticks": len(reopen_map),
        "opening": growth(baseline, opening),
        "save_footprint": footprint,
        "ticks": rows,
        "total_charged_growth_bytes": charged,
        "rolling_model_year_growth": [
            {
                "first_tick": last - policy.model_year_ticks + 1,
                "last_tick": last,
                "charged_growth_bytes": sum(
                    int(row["charged_growth_bytes"])
                    for row in rows[last - policy.model_year_ticks : last]
                ),
            }
            for last in range(policy.model_year_ticks, len(rows) + 1)
        ],
        "annualized_growth_bytes": fraction(annual) if annual is not None else None,
        "twelve_tick_comparison_bytes": fraction(twelve) if twelve is not None else None,
        "wal_scope": "container-wide; not campaign-attributable",
        "measurement": "decimal bytes; positive parent deltas plus positive unattributed database delta, charged separately at commit and recovery; parent totals include heap, indexes and TOAST; estimates do not determine charges",
    }


def strict_json(path: Path) -> object:
    return strict_json_bytes(path.read_bytes())


def strict_json_bytes(raw: bytes) -> object:
    """Reject ambiguous authoritative JSON before typed admission."""

    def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(token: str) -> object:
        raise ValueError(f"nonfinite JSON constant: {token}")

    return json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)


def exact_testcase_nanoseconds(text: str) -> int:
    try:
        seconds = Decimal(text)
    except InvalidOperation as error:
        raise ValueError("malformed executed testcase time") from error
    if not seconds.is_finite() or seconds < 0:
        raise ValueError("invalid executed testcase duration")
    if not seconds:
        return 0
    parts = seconds.as_tuple()
    # Trim exact trailing zeros before inspecting decimal scale: 1.0000000000
    # is valid, but 1e-999999999 must never construct an enormous denominator.
    last = len(parts.digits)
    while last and parts.digits[last - 1] == 0:
        last -= 1
    exponent = parts.exponent
    if not isinstance(exponent, int):
        raise ValueError("invalid executed testcase exponent")
    ns_exponent = exponent + len(parts.digits) - last + 9
    if ns_exponent < 0:
        raise ValueError("testcase duration exceeds nanosecond precision")
    if ns_exponent > 18 or last + ns_exponent > 19:
        raise ValueError("executed testcase duration exceeds signed nanoseconds")
    coefficient = 0
    for digit in parts.digits[:last]:
        coefficient = coefficient * 10 + digit
    value = coefficient
    for _ in range(ns_exponent):
        value *= 10
    if value > 2**63 - 1:
        raise ValueError("executed testcase duration exceeds signed nanoseconds")
    return value


class TimedTick(FrozenRecord):
    tick: Positive
    elapsed_ns: Nonnegative


class TimedRun(FrozenRecord):
    periods: Positive
    elapsed_ns: Nonnegative
    compilation_included: Literal[False]

    @field_validator("compilation_included", mode="before")
    @classmethod
    def excludes_compilation(cls, value: object) -> object:
        if value is not False:
            raise ValueError("native timing must exclude compilation")
        return value


class NativeTimings(FrozenRecord):
    version: Literal[2]
    source: Literal["authoritative_native_instants_v2"]
    clock: Literal["monotonic"]
    campaign: str
    advances: tuple[TimedTick, ...]
    cold_reopens: tuple[TimedTick, ...]
    archive_catchups: tuple[TimedTick, ...]
    production_reads: tuple[TimedTick, ...]
    run: TimedRun

    @field_validator("version", mode="before")
    @classmethod
    def exact_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("timing version must be an exact integer")
        return value

    @model_validator(mode="after")
    def exact_run(self) -> NativeTimings:
        if str(UUID(self.campaign)) != self.campaign:
            raise ValueError("timing campaign must be canonical UUID")
        if len(self.advances) != self.run.periods or any(
            row.tick != index for index, row in enumerate(self.advances, 1)
        ):
            raise ValueError("advances must be consecutive acknowledged periods")
        cold = tuple(row.tick for row in self.cold_reopens)
        if cold != tuple(sorted(set(cold))) or any(tick > self.run.periods for tick in cold):
            raise ValueError("cold reopens must be ordered unique committed periods")
        for phase in (self.archive_catchups, self.production_reads):
            phase_ticks = tuple(row.tick for row in phase)
            if phase_ticks != tuple(sorted(set(phase_ticks))) or any(
                tick > self.run.periods for tick in phase_ticks
            ):
                raise ValueError("playable phase timings must be ordered unique committed periods")
        if (
            sum(
                row.elapsed_ns
                for row in (
                    *self.advances,
                    *self.cold_reopens,
                    *self.archive_catchups,
                    *self.production_reads,
                )
            )
            > self.run.elapsed_ns
        ):
            raise ValueError("native phase timings exceed whole measured run")
        return self


def evaluate_timings(
    policy: Policy,
    timing: NativeTimings,
    ticks: tuple[Snapshot, ...],
    reopens: tuple[Snapshot, ...],
) -> dict[str, object]:
    if tuple(row.tick for row in ticks) != tuple(row.tick for row in timing.advances):
        raise ValueError("timings do not match actual storage ticks")
    if tuple(row.tick for row in reopens) != tuple(row.tick for row in timing.cold_reopens):
        raise ValueError("timings do not match verified storage reopens")
    if any(row.campaign != timing.campaign for row in (*ticks, *reopens)):
        raise ValueError("timing campaign differs from storage evidence")
    samples = sorted(row.elapsed_ns for row in timing.advances)
    # Exact nearest-rank empirical quantile, no interpolation or one-sample p95.
    enough = len(samples) >= policy.p95_minimum_samples
    p95 = samples[(95 * len(samples) + 99) // 100 - 1] if len(samples) >= 2 else None
    advance_pass = all(n <= policy.maximum_advance_p95_seconds * 1_000_000_000 for n in samples)
    p95_pass = p95 is not None and p95 <= policy.maximum_advance_p95_seconds * 1_000_000_000
    cold_pass = all(
        row.elapsed_ns < policy.maximum_cold_open_seconds * 1_000_000_000
        for row in timing.cold_reopens
    )
    cold_complete = len(timing.cold_reopens) == timing.run.periods
    smoke_applies = timing.run.periods == policy.routine_smoke_periods
    smoke_pass = timing.run.elapsed_ns <= policy.maximum_routine_smoke_seconds * 1_000_000_000
    hard_failed = (enough and not p95_pass) or not cold_pass or (smoke_applies and not smoke_pass)
    return {
        "status": "failed"
        if hard_failed
        else ("qualified" if enough and cold_complete else "incomplete"),
        "source": timing.source,
        "advance_samples": len(samples),
        "required_p95_samples": policy.p95_minimum_samples,
        "empirical_p95_ns": p95,
        "p95_status": "incomplete" if not enough else ("qualified" if p95_pass else "failed"),
        "individual_advance_compliance": advance_pass,
        "advance_aim_met": [
            policy.advance_aim_min_seconds * 1_000_000_000
            <= row.elapsed_ns
            <= policy.advance_aim_max_seconds * 1_000_000_000
            for row in timing.advances
        ],
        "cold_open_status": "failed"
        if not cold_pass
        else ("qualified" if cold_complete else "incomplete"),
        "smoke_status": ("qualified" if smoke_pass else "failed")
        if smoke_applies
        else "not_measured",
        "full_qualification_duration_preference_met": timing.run.elapsed_ns
        <= policy.preferred_qualification_seconds * 1_000_000_000
        if timing.run.periods == policy.qualification_ticks
        else None,
        "ui_responsiveness": "unqualified: separate native interaction/navigation evidence required",
    }


def evaluate_smoke(
    policy: Policy, storage: dict[str, object], timing: dict[str, object]
) -> dict[str, object]:
    """Gate observed routine work independently from full qualification."""
    failed = (
        storage["budget_passed"] is False
        or timing.get("individual_advance_compliance") is False
        or timing.get("cold_open_status") == "failed"
        or timing.get("smoke_status") == "failed"
    )
    complete = (
        storage["committed_ticks"] == policy.routine_smoke_periods
        and storage["restart_verified_ticks"] == policy.routine_smoke_periods
        and storage["lookup_delta_hashes_verified"] is True
        and timing.get("advance_samples") == policy.routine_smoke_periods
        and timing.get("individual_advance_compliance") is True
        and timing.get("cold_open_status") == "qualified"
        and timing.get("smoke_status") == "qualified"
    )
    return {
        "status": "failed" if failed else ("qualified" if complete else "incomplete"),
        "required_periods": policy.routine_smoke_periods,
        "scope": "Observed development storage, per-advance limit, cold recovery and whole routine duration only; not full52, p95, long-save, focused or UI qualification",
        "full_storage_status": storage["status"],
        "full_timing_status": timing["status"],
    }


def evaluate_focused(policy: Policy, path: Path) -> dict[str, object]:
    raw = path.read_bytes()

    try:
        root = ET.fromstring(raw, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except (ET.ParseError, DefusedXmlException) as error:
        raise ValueError("malformed or unsafe JUnit XML") from error
    if root.tag not in {"testsuites", "testsuite"}:
        raise ValueError("expected JUnit test suite")
    rows = []
    seen = set()
    for case in root.iter("testcase"):
        identity = (case.get("classname"), case.get("name"))
        if not all(identity) or identity in seen:
            raise ValueError("missing or duplicate fully qualified JUnit case identity")
        seen.add(identity)
        failed = case.find("failure") is not None or case.find("error") is not None
        if case.find("skipped") is not None:
            if failed:
                raise ValueError("JUnit testcase contradicts skipped and failed evidence")
            continue
        try:
            ns = exact_testcase_nanoseconds(case.attrib["time"])
        except KeyError as error:
            raise ValueError("missing executed testcase time") from error
        rows.append(
            {
                "classname": identity[0],
                "name": identity[1],
                "elapsed_ns": int(ns),
                "passed": not failed,
                "duration_passed": ns < policy.maximum_focused_control_seconds * 1_000_000_000,
            }
        )
    if not rows:
        raise ValueError("focused evidence needs at least one executed testcase")
    return {
        "status": "qualified"
        if all(row["passed"] and row["duration_passed"] for row in rows)
        else "failed",
        "policy": policy.model_dump(),
        "junit_sha256": hashlib.sha256(raw).hexdigest(),
        "executed_controls": rows,
        "scope": "operator-selected JUnit testcase durations excluding compilation; not UI/native-play qualification",
    }


class ArchiveBoundary(FrozenRecord):
    processed_tick: Nonnegative
    durable_tick: Nonnegative
    expected_tick: Positive
    pending_count: Nonnegative
    dossier_sha256: Sha256


class ProductionBoundary(FrozenRecord):
    tick: Positive
    nominal_world_hash: Sha256
    snapshot_sha256: Sha256
    county_roster_sha256: Sha256


class TradeDirectionEvidence(FrozenRecord):
    settled_deliveries: Nonnegative
    settled_cash_micros: str = Field(pattern=r"^(0|[1-9][0-9]{0,38})$")

    @model_validator(mode="after")
    def exact_positive_settlement(self) -> TradeDirectionEvidence:
        cash = int(self.settled_cash_micros)
        if cash > 2**127 - 1 or (cash > 0) != (self.settled_deliveries > 0):
            raise ValueError("trade delivery counts need exact positive signed-range cash")
        return self


def _foreign_production_counts(receipts: int, sites: int) -> None:
    if (receipts > 0) != (sites > 0) or sites > receipts:
        raise ValueError("foreign production needs actual receipts and productive sites")


class TradeBoundary(FrozenRecord):
    period: Positive
    tick_content_hash: Sha256
    canonical_receipt_sha256: Sha256
    imports: TradeDirectionEvidence
    exports: TradeDirectionEvidence
    positive_foreign_production_receipts: Nonnegative
    productive_foreign_sites: Nonnegative
    unresolved_trade_orders: Nonnegative

    @model_validator(mode="after")
    def coherent_foreign_production(self) -> TradeBoundary:
        _foreign_production_counts(
            self.positive_foreign_production_receipts, self.productive_foreign_sites
        )
        return self


class TradeSummary(FrozenRecord):
    version: Literal[1]
    status: Literal["passed", "incomplete"]
    periods: Nonnegative
    basis: Literal["committed_recurring_procurement_delivery_realization_and_exact_settlement"]
    imports: TradeDirectionEvidence
    exports: TradeDirectionEvidence
    positive_foreign_production_receipts: Nonnegative
    productive_foreign_sites: Nonnegative
    unresolved_trade_orders: Nonnegative

    @field_validator("version", mode="before")
    @classmethod
    def exact_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("trade version must be an exact integer")
        return value

    @model_validator(mode="after")
    def actual_execution_status(self) -> TradeSummary:
        _foreign_production_counts(
            self.positive_foreign_production_receipts, self.productive_foreign_sites
        )
        passed = (
            self.imports.settled_deliveries > 0
            and self.exports.settled_deliveries > 0
            and self.positive_foreign_production_receipts > 0
        )
        if (self.status == "passed") != passed:
            raise ValueError("trade status must follow actual settled execution")
        return self


class PlayableBoundary(FrozenRecord):
    tick: Positive
    campaign: str
    foundation_sha256: Sha256
    tick_content_hash: Sha256
    envelope_digest: Sha256
    register_storage_sha256: Sha256
    receipt_storage_sha256: Sha256
    lookup_storage_sha256: Sha256
    canonical_receipt_sha256: Sha256
    nominal_world_hash: Sha256
    archive: ArchiveBoundary
    production: ProductionBoundary
    trade: TradeBoundary


class PlayableReport(FrozenRecord):
    version: Literal[3]
    capture_mode: Literal["playable-aid"]
    policy_sha256: Sha256
    campaign: str
    foundation_sha256: Sha256
    requested_periods: Positive
    county_geoids: tuple[str, ...]
    aid_periods: tuple[dict[str, object], ...]
    continuations: tuple[dict[str, object], ...]
    boundaries: tuple[PlayableBoundary, ...]
    canonical_protocol_recovery: Literal["passed", "incomplete"]
    positive_aid_consequences: Literal["passed", "incomplete"]
    remote_consumed: bool
    local_consumed: bool
    independent_finite_aid_practice: dict[str, object]
    independent_account_posting_audit: dict[str, object]
    independent_trade_accounting: TradeSummary
    native_window_evidence: Literal["not_run"]

    @field_validator("version", mode="before")
    @classmethod
    def exact_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("playable version must be an exact integer")
        return value

    @field_validator("remote_consumed", "local_consumed", mode="before")
    @classmethod
    def exact_bool(cls, value: object) -> object:
        if type(value) is not bool:
            raise ValueError("playable consumption flags must be exact booleans")
        return value

    @model_validator(mode="after")
    def consistent_identity(self) -> PlayableReport:
        if str(UUID(self.campaign)) != self.campaign:
            raise ValueError("playable campaign must be canonical UUID")
        for index, boundary in enumerate(self.boundaries, 1):
            if boundary.tick != index or boundary.tick > self.requested_periods:
                raise ValueError("playable boundaries must be consecutive requested periods")
            if (
                boundary.campaign != self.campaign
                or boundary.foundation_sha256 != self.foundation_sha256
            ):
                raise ValueError("playable boundary campaign or foundation differs")
        return self


def _consistent_trade_summary(playable: PlayableReport) -> str:
    summary = playable.independent_trade_accounting
    facts = tuple(boundary.trade for boundary in playable.boundaries)
    if summary.periods != len(facts):
        raise ValueError("trade summary must cover each actual committed boundary")
    for direction in ("imports", "exports"):
        rows = tuple(getattr(fact, direction) for fact in facts)
        total = getattr(summary, direction)
        if total.settled_deliveries != sum(row.settled_deliveries for row in rows) or int(
            total.settled_cash_micros
        ) != sum(int(row.settled_cash_micros) for row in rows):
            raise ValueError("trade summary differs from committed settlements")
    if summary.positive_foreign_production_receipts != sum(
        fact.positive_foreign_production_receipts for fact in facts
    ):
        raise ValueError("trade summary differs from actual foreign production")
    site_counts = tuple(fact.productive_foreign_sites for fact in facts)
    if not max(site_counts, default=0) <= summary.productive_foreign_sites <= sum(site_counts):
        raise ValueError("productive foreign site count disagrees with committed evidence")
    pending = facts[-1].unresolved_trade_orders if facts else 0
    if summary.unresolved_trade_orders != pending:
        raise ValueError("trade summary differs from the current unresolved order set")
    return summary.status


def evaluate_playable(
    policy: Policy,
    policy_sha256: str,
    playable: PlayableReport,
    timing: NativeTimings,
    opening: Snapshot,
    ticks: tuple[Snapshot, ...],
    storage: dict[str, object],
    timing_report: dict[str, object],
    smoke: dict[str, object],
) -> dict[str, object]:
    """Admit actual material aid evidence; native interaction remains unqualified."""
    if playable.policy_sha256 != policy_sha256:
        raise ValueError("playable evidence uses a different frozen policy")
    if playable.campaign != timing.campaign or playable.campaign != opening.campaign:
        raise ValueError("playable campaign differs from storage/timing evidence")
    if playable.requested_periods < timing.run.periods:
        raise ValueError("playable requested periods differ from measured native run")
    expected = tuple(s.tick for s in ticks)
    for phase in (timing.archive_catchups, timing.production_reads):
        if tuple(row.tick for row in phase) != expected:
            raise ValueError("playable phase timings must match actual storage tick set")
    if tuple(b.tick for b in playable.boundaries) != expected:
        raise ValueError("playable boundaries must match actual storage tick set")
    if len(playable.continuations) != len(ticks):
        raise ValueError("playable continuations must cover actual storage ticks")
    if (
        playable.county_geoids != opening.county_geoids
        or len(playable.county_geoids) != policy.county_count
    ):
        raise ValueError("playable report lacks the complete national county roster")
    county_roster_sha256 = hashlib.sha256(
        json.dumps(list(playable.county_geoids), separators=(",", ":")).encode("ascii")
    ).hexdigest()
    incomplete = len(ticks) != playable.requested_periods
    for boundary, tick, continuation in zip(
        playable.boundaries, ticks, playable.continuations, strict=True
    ):
        marker = tick.marker_and_encoded_package_hashes[-1]
        if (
            boundary.tick,
            boundary.tick_content_hash,
            boundary.envelope_digest,
            boundary.register_storage_sha256,
            boundary.receipt_storage_sha256,
        ) != marker:
            raise ValueError("playable boundary differs from authoritative storage hashes")
        if tick.lookup_delta_hashes is None or tick.lookup_delta_hashes[-1] != (
            boundary.tick,
            boundary.lookup_storage_sha256,
        ):
            raise ValueError("playable lookup storage hash differs")
        if (
            tick.actual_rust_storage_package_claims[-1].canonical_receipt_sha256
            != boundary.canonical_receipt_sha256
        ):
            raise ValueError("playable canonical receipt hash differs")
        if (
            type(continuation.get("period")) is not int
            or continuation.get("period") != boundary.tick
            or continuation.get("nominal_world_hash") != boundary.nominal_world_hash
        ):
            raise ValueError("playable continuation period or world identity differs")
        tail = continuation.get("tail")
        if (
            not isinstance(tail, dict)
            or type(tail.get("resolve_tick")) is not int
            or (tail.get("resolve_tick"), tail.get("tick_content_hash")) != marker[:2]
        ):
            raise ValueError("playable recovered tail differs from committed marker")
        organizer_digest = continuation.get("organizer_snapshot_sha256")
        if not isinstance(organizer_digest, str) or not re.fullmatch(
            r"[0-9a-f]{64}", organizer_digest
        ):
            raise ValueError("playable recovery lacks organizer snapshot digest")
        latest = continuation.get("latest_marker")
        if not isinstance(latest, (list, tuple)) or tuple(latest) != marker[:3]:
            raise ValueError("playable continuation marker differs")
        production = boundary.production
        if (
            production.tick != boundary.tick
            or production.nominal_world_hash != boundary.nominal_world_hash
        ):
            raise ValueError("Production read period or world identity differs")
        if tick.county_geoids != playable.county_geoids:
            raise ValueError("playable roster differs from actual storage period roster")
        if production.county_roster_sha256 != county_roster_sha256:
            raise ValueError("Production read county roster digest differs")
        trade = boundary.trade
        if (
            trade.period,
            trade.tick_content_hash,
            trade.canonical_receipt_sha256,
        ) != (boundary.tick, boundary.tick_content_hash, boundary.canonical_receipt_sha256):
            raise ValueError("trade period or canonical receipt identity differs")
        archive = boundary.archive
        if archive.expected_tick != boundary.tick:
            raise ValueError("Archive expected period differs from boundary")
        if archive.processed_tick > boundary.tick or archive.durable_tick > boundary.tick:
            raise ValueError("Archive evidence refers to future work")
        incomplete |= not (
            archive.processed_tick == archive.durable_tick == archive.expected_tick
            and archive.pending_count == 0
        )
    trade_status = _consistent_trade_summary(playable)
    trade_required = playable.requested_periods >= policy.qualification_ticks
    incomplete |= trade_required and trade_status != "passed"
    audit = playable.independent_account_posting_audit
    required_audit = (
        "cash_and_in_kind_postings",
        "time_partition_and_residual_bound",
        "exact_final_contribution_debit_ledger",
    )
    incomplete |= any(audit.get(name) != "passed" for name in required_audit)
    incomplete |= (
        type(audit.get("accepted_original_commands")) is not int
        or audit.get("accepted_original_commands") != 2
    )
    facts = audit.get("periods")
    if not isinstance(facts, (list, tuple)) or len(facts) != len(ticks):
        raise ValueError("independent accounting must cover every actual storage period")

    def command_identity(value: object) -> tuple[int, ...]:
        if (
            not isinstance(value, (list, tuple))
            or len(value) != 32
            or any(type(byte) is not int or not 0 <= byte <= 255 for byte in value)
            or not any(value)
        ):
            raise ValueError("aid original command must be a nonzero 32-byte identity")
        return tuple(value)

    accepted_commands: set[tuple[int, ...]] = set()
    for row in playable.aid_periods:
        commitment = row.get("commitment")
        if not isinstance(commitment, dict):
            incomplete = True
            continue
        admitted_period = row.get("period")
        if (
            type(admitted_period) is not int
            or not 1 <= admitted_period <= playable.requested_periods
        ):
            raise ValueError("aid admission period must belong to requested run")
        command = command_identity(commitment.get("commitment_id"))
        if command in accepted_commands:
            raise ValueError("duplicate accepted original aid command")
        accepted_commands.add(command)
    incomplete |= len(accepted_commands) != 2
    positive_commands: set[tuple[int, ...]] = set()
    delivered_commands: set[tuple[int, ...]] = set()
    for boundary, fact in zip(playable.boundaries, facts, strict=True):
        if (
            not isinstance(fact, dict)
            or type(fact.get("period")) is not int
            or (
                fact.get("period"),
                fact.get("tick_content_hash"),
                fact.get("canonical_receipt_sha256"),
            )
            != (boundary.tick, boundary.tick_content_hash, boundary.canonical_receipt_sha256)
        ):
            raise ValueError("independent accounting period or receipt identity differs")
        selected = fact.get("selected_aid")
        practices = fact.get("independent_practices")
        if not isinstance(selected, (list, tuple)) or not isinstance(practices, (list, tuple)):
            raise ValueError("independent aid and practice evidence must be arrays")
        for row in selected:
            if not isinstance(row, dict):
                raise ValueError("independent selected aid must be records")
            quantity = row.get("quantity")
            if row.get("outcome") == "Granted" and type(quantity) is int and quantity > 0:
                delivered_commands.add(command_identity(row.get("original_commitment")))
        for row in practices:
            if not isinstance(row, dict):
                raise ValueError("independent practice must be records")
            hours = row.get("recipient_debited_hours")
            consumed = row.get("consumed_support")
            if (
                row.get("finite_practice_completed") is True
                and type(hours) is int
                and hours > 0
                and consumed is True
                and row.get("partner_response") == "participated"
                and row.get("outcome") == "aid_practice_completed"
            ):
                if type(row.get("period")) is not int or row.get("period") != boundary.tick:
                    raise ValueError("independent practice period differs from receipt")
                positive_commands.add(command_identity(row.get("original_commitment")))
    practice = playable.independent_finite_aid_practice
    completed = practice.get("completed_original_commands")
    completed_commands = (
        {command_identity(value) for value in completed}
        if isinstance(completed, (list, tuple))
        else set()
    )
    terminal = practice.get("terminal_original_commands")
    terminal_commands = (
        {command_identity(value) for value in terminal}
        if isinstance(terminal, (list, tuple))
        else set()
    )
    incomplete |= not (
        isinstance(terminal, (list, tuple))
        and len(terminal) == len(terminal_commands) == 2
        and terminal_commands == completed_commands
    )
    incomplete |= not (
        practice.get("status") == "passed"
        and practice.get("basis")
        == "actual_consumed_support_independent_partner_response_and_authenticated_finite_debits"
        and isinstance(completed, (list, tuple))
        and len(completed) == len(completed_commands) == 2
        and completed_commands == positive_commands
        and positive_commands <= delivered_commands
        and positive_commands == accepted_commands
    )
    incomplete |= not (
        playable.remote_consumed
        and playable.local_consumed
        and playable.positive_aid_consequences == "passed"
        and playable.canonical_protocol_recovery == "passed"
    )
    archive_pass = all(
        r.elapsed_ns <= policy.maximum_archive_catchup_seconds * 1_000_000_000
        for r in timing.archive_catchups
    )
    production_pass = all(
        r.elapsed_ns <= policy.maximum_production_read_seconds * 1_000_000_000
        for r in timing.production_reads
    )
    admission = (
        smoke
        if playable.requested_periods == policy.routine_smoke_periods
        else {
            "status": "qualified"
            if storage["status"] == timing_report["status"] == "qualified"
            else (
                "failed"
                if "failed" in (storage["status"], timing_report["status"])
                else "incomplete"
            )
        }
    )
    failed = not archive_pass or not production_pass or admission["status"] == "failed"
    incomplete |= admission["status"] != "qualified"
    return {
        "status": "failed" if failed else ("incomplete" if incomplete else "qualified"),
        "archive_catchup_status": "qualified" if archive_pass else "failed",
        "production_read_status": "qualified" if production_pass else "failed",
        "trade_accounting_status": "qualified" if trade_status == "passed" else "incomplete",
        "trade_required_for_run": trade_required,
        "native_window_status": "unqualified",
        "native_window_evidence": playable.native_window_evidence,
        "scope": "Actual material aid, independent accounting/practice, settled trade evidence, Archive, full Production read, storage and recovery; native interaction and fun remain unqualified",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--policy",
        type=Path,
        default=Path(__file__).resolve().parents[2]
        / "contracts/national_storage_qualification_v3.json",
    )
    p.add_argument("--baseline", type=Path)
    p.add_argument("--opening", type=Path)
    p.add_argument("--ticks", type=Path, nargs="+")
    p.add_argument("--reopens", type=Path, nargs="*")
    p.add_argument("--qualify", action="store_true")
    p.add_argument("--qualify-save", action="store_true")
    p.add_argument("--validate-policy", action="store_true")
    p.add_argument("--timings", type=Path)
    p.add_argument("--qualify-timing", action="store_true")
    p.add_argument("--qualify-smoke", action="store_true")
    p.add_argument("--playable-report", type=Path)
    p.add_argument("--qualify-playable", action="store_true")
    p.add_argument("--focused-junit", type=Path)
    p.add_argument("--qualify-focused", action="store_true")
    a = p.parse_args()
    try:
        policy_bytes = a.policy.read_bytes()
        policy_sha256 = hashlib.sha256(policy_bytes).hexdigest()
        policy = Policy.model_validate(strict_json_bytes(policy_bytes))
        if a.validate_policy:
            if (
                a.qualify
                or a.qualify_save
                or a.qualify_smoke
                or a.qualify_timing
                or a.qualify_focused
                or a.qualify_playable
                or any(
                    value is not None
                    for value in (
                        a.baseline,
                        a.opening,
                        a.ticks,
                        a.reopens,
                        a.timings,
                        a.focused_junit,
                        a.playable_report,
                    )
                )
            ):
                raise ValueError(
                    "validation-only mode cannot accept qualification flags or evidence"
                )
            print(
                json.dumps(
                    {
                        "policy": policy.model_dump(),
                        "policy_sha256": policy_sha256,
                    },
                    indent=2,
                )
            )
            return 0
        a.reopens = a.reopens or []
        if a.focused_junit is not None:
            if (
                a.qualify
                or a.qualify_save
                or a.qualify_timing
                or a.qualify_smoke
                or a.timings is not None
                or a.qualify_playable
                or a.playable_report is not None
            ):
                raise ValueError("focused qualification is separate from storage/native timing")
            result = evaluate_focused(policy, a.focused_junit)
            print(json.dumps(result, indent=2))
            return int(a.qualify_focused and result["status"] != "qualified")
        if a.qualify_focused:
            raise ValueError("focused qualification needs JUnit evidence")
        if any(value is None for value in (a.baseline, a.opening, a.ticks)):
            raise ValueError("storage evaluation requires baseline, opening, ticks and reopens")

        def load(path: Path) -> Snapshot:
            return Snapshot.model_validate(strict_json(path))

        result = evaluate(
            policy,
            load(a.baseline),
            load(a.opening),
            tuple(load(p) for p in a.ticks),
            tuple(load(p) for p in a.reopens),
        )
        if a.timings is not None:
            timing = NativeTimings.model_validate(strict_json(a.timings))
            timing_report = evaluate_timings(
                policy,
                timing,
                tuple(load(path) for path in a.ticks),
                tuple(load(path) for path in a.reopens),
            )
            result["timings"] = timing_report
            result["timings_sha256"] = hashlib.sha256(a.timings.read_bytes()).hexdigest()
        else:
            timing_report = {
                "status": "incomplete",
                "ui_responsiveness": "unqualified: separate native evidence required",
            }
            result["timings"] = timing_report
        smoke_report = evaluate_smoke(policy, result, timing_report)
        result["development_smoke"] = smoke_report
        result["policy_sha256"] = policy_sha256
        playable_report: dict[str, object] = {"status": "incomplete"}
        if a.playable_report is not None:
            if a.timings is None:
                raise ValueError("playable evaluation needs native timing evidence")
            playable_report = evaluate_playable(
                policy,
                policy_sha256,
                PlayableReport.model_validate(strict_json(a.playable_report)),
                timing,
                load(a.opening),
                tuple(load(path) for path in a.ticks),
                result,
                timing_report,
                smoke_report,
            )
            result["material_playable"] = playable_report
            result["playable_report_sha256"] = hashlib.sha256(
                a.playable_report.read_bytes()
            ).hexdigest()
        elif a.qualify_playable:
            raise ValueError("playable qualification needs a current playable aid report")
    except (ValueError, OSError, ET.ParseError) as error:
        p.error(str(error))
    print(json.dumps(result, indent=2))
    footprint = result["save_footprint"]
    if not isinstance(footprint, dict):
        raise ValueError("save footprint must be a typed report")
    return int(
        (a.qualify or a.qualify_save)
        and result["status"] != "qualified"
        or a.qualify_save
        and footprint["status"] != "qualified"
        or a.qualify_timing
        and timing_report["status"] != "qualified"
        or a.qualify_smoke
        and smoke_report["status"] != "qualified"
        or a.qualify_playable
        and playable_report["status"] != "qualified"
    )


if __name__ == "__main__":
    raise SystemExit(main())
