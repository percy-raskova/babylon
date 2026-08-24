#!/usr/bin/env python3
"""Generate bounded language-neutral T3 evidence contract fixtures."""

import argparse
import hashlib
import os
import stat
import struct
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Final

import unicodedata2  # type: ignore[import-not-found]

SCHEMA_VERSION: Final = 1
MAX_ROWS: Final = 65_535
MAX_SAMPLES: Final = 157
MAX_COMPONENTS: Final = 64
MAX_VECTOR_BYTES: Final = 16_777_216
MAX_SYNTHETIC_DRIVER_BYTES: Final = 262_144
MAX_SYNTHETIC_DRIVER_CONTRACT_BYTES: Final = 4_096
MAX_NFC_SCALARS: Final = 256
UNICODE_DATA_VERSION: Final = "17.0.0"

ROOT: Final = Path(__file__).resolve().parents[1]
FIXTURE_ROOT: Final = ROOT / "rust" / "crates" / "babylon-evidence" / "tests" / "fixtures"
WIRE_PATH: Final = FIXTURE_ROOT / "sfs_wire_vectors_v1.txt"
CLASSIFIER_PATH: Final = FIXTURE_ROOT / "sfs_classifier_vectors_v1.txt"
MUTATION_PATH: Final = FIXTURE_ROOT / "sfs_identity_mutations_v1.txt"
SYNTHETIC_GOVERNED_MANIFEST_PATH: Final = FIXTURE_ROOT / "sfs_synthetic_governed_manifest_v1.txt"
SYNTHETIC_PROFILE_PATH: Final = FIXTURE_ROOT / "sfs_synthetic_profile_v1.txt"
DRIVER_SOURCE_PATH: Final = ROOT / "rust" / "crates" / "babylon-evidence" / "src" / "driver.rs"
SYNTHETIC_DRIVER_CONTRACT_PATH: Final = FIXTURE_ROOT / "sfs_synthetic_driver_contract_v1.txt"
SYNTHETIC_DRIVER_PATH: Final = FIXTURE_ROOT / "sfs_synthetic_driver_v1.txt"
BSL_PROFILE_ROOT: Final = (
    ROOT / "rust" / "crates" / "babylon-bsl" / "tests" / "fixtures" / "sfs_profile"
)
FORBIDDEN_MANIFEST_PATH: Final = BSL_PROFILE_ROOT / "sfs_forbidden_manifest_v1.txt"
AUDIT_SOURCE_MANIFEST_PATH: Final = BSL_PROFILE_ROOT / "sfs_audit_source_manifest_v1.txt"

SYNTHETIC_COMPONENT_SOURCE_DOMAIN: Final = b"babylon.sfs-synthetic-component-source.v1"
SYNTHETIC_GOVERNED_MANIFEST_DOMAIN: Final = b"babylon.sfs-synthetic-governed-manifest.v1"
SYNTHETIC_HOST_MANIFEST_DOMAIN: Final = b"babylon.sfs-synthetic-host-component-manifest.v1"
FORBIDDEN_CORPUS_DOMAIN: Final = b"babylon.sfs-forbidden-corpus-manifest.v1"
AUDIT_SOURCE_DOMAIN: Final = b"babylon.sfs-audit-source-manifest.v1"
SYNTHETIC_CARDINALITY_DIGEST: Final = hashlib.sha256(
    b"babylon.sfs-cardinality-ceilings.v1\0ceiling|EdgeType/SYNTHETIC_LINK|8\n"
).digest()
SYNTHETIC_INTRINSIC_COST_DIGEST: Final = hashlib.sha256(
    b"babylon.sfs-intrinsic-costs.v1\0"
).digest()

RUN_FIELD_NAMES: Final = (
    "session",
    "scenario",
    "prelude-declarations",
    "vocabulary",
    "rule-ast",
    "host-component-manifest",
    "defines",
    "intrinsic-cost-cap",
    "reference-manifest",
    "governed-footprint-manifest",
    "sfs-proof-profile",
    "sfs-preregistration",
    "initial-committed-envelope",
    "initial-nominal-world",
    "exogenous-input-ledger",
    "practice-attempt-ledger",
    "rng-algorithm-id",
    "graph-contract-id",
)


class UnicodeDataVersionError(RuntimeError):
    """The installed normalization tables differ from the frozen version."""

    def __init__(self, expected: str, actual: str) -> None:
        super().__init__(f"expected Unicode data {expected}, found {actual}")


class VectorIoError(RuntimeError):
    """One exact fixture I/O operation failed."""

    __slots__ = ("_operation", "_path")

    def __init__(self, path: Path, operation: str) -> None:
        self._path = path
        self._operation = operation
        super().__init__(f"{operation} failed for {path}")

    @property
    def path(self) -> Path:
        """Return the exact destination associated with the failure."""
        return self._path

    @property
    def operation(self) -> str:
        """Return the exact failed operation."""
        return self._operation


def _require_unicode_version() -> None:
    actual = unicodedata2.unidata_version
    if actual != UNICODE_DATA_VERSION:
        raise UnicodeDataVersionError(UNICODE_DATA_VERSION, actual)


def _envelope(domain: bytes, payload: bytes) -> bytes:
    if not domain or len(domain) > 64 or b"\x00" in domain:
        raise ValueError("domain must contain 1 through 64 non-NUL ASCII bytes")
    try:
        domain.decode("ascii", "strict")
    except UnicodeDecodeError as error:
        raise ValueError("domain must be ASCII") from error
    if len(payload) > 0xFFFF_FFFF:
        raise ValueError("payload length exceeds u32")
    return (
        domain
        + b"\x00"
        + struct.pack(">H", SCHEMA_VERSION)
        + struct.pack(">I", len(payload))
        + payload
    )


def _digest(envelope: bytes) -> bytes:
    return hashlib.sha256(envelope).digest()


def _nfc_utf8(value: str, field: str, minimum: int, maximum: int) -> bytes:
    _require_unicode_version()
    scalar_count = 0
    for index in range(MAX_NFC_SCALARS):
        if index >= len(value):
            break
        scalar_count += 1
    if scalar_count != len(value):
        raise ValueError(f"{field} exceeds the 256 scalar limit")
    if unicodedata2.normalize("NFC", value) != value:
        raise ValueError(f"{field} must be NFC")
    encoded = value.encode("utf-8", "strict")
    if not minimum <= len(encoded) <= maximum:
        raise ValueError(f"{field} byte length must be in {minimum}..={maximum}")
    return encoded


def _ascii(value: str, field: str, minimum: int, maximum: int) -> bytes:
    try:
        encoded = value.encode("ascii", "strict")
    except UnicodeEncodeError as error:
        raise ValueError(f"{field} must be ASCII") from error
    if not minimum <= len(encoded) <= maximum:
        raise ValueError(f"{field} byte length must be in {minimum}..={maximum}")
    return encoded


def _finite_bits(value: float, non_negative: bool) -> bytes:
    if value != value or value == float("inf") or value == float("-inf"):
        raise ValueError("value must be finite")
    if non_negative and value < 0.0:
        raise ValueError("value must be non-negative")
    if value == 0.0:
        value = 0.0
    return struct.pack(">d", value)


def _normalized(values: Sequence[float], count: int, field: str) -> list[float]:
    if count > MAX_SAMPLES:
        raise ValueError(f"{field} exceeds the maximum sample count")
    output = [0.0] * count
    for index in range(MAX_SAMPLES):
        if index >= count:
            break
        value = values[index]
        if value != value or value == float("inf") or value == float("-inf"):
            raise ValueError(f"{field}[{index}] must be finite")
        output[index] = 0.0 if value == 0.0 else value
    return output


def _same_bits(values: Sequence[float], count: int, expected: bytes) -> bool:
    for index in range(MAX_SAMPLES):
        if index >= count:
            break
        if _finite_bits(values[index], False) != expected:
            return False
    return True


def _nonnegative_deltas(deltas: Sequence[float], count: int) -> bool:
    for index in range(156):
        if index >= count:
            break
        if deltas[index] < 0.0:
            return False
    return True


def _middle_positive_count(deltas: Sequence[float], width: int) -> int:
    count = 0
    for offset in range(52):
        if offset >= width:
            break
        if deltas[width + offset] > 0.0:
            count += 1
    return count


def _late_deltas_zero(deltas: Sequence[float], width: int) -> bool:
    for offset in range(52):
        if offset >= width:
            break
        if _finite_bits(deltas[width * 2 + offset], False) != b"\x00" * 8:
            return False
    return True


def _classify_sfs(window_width: int, masses: Sequence[float]) -> int:
    if not 2 <= window_width <= 52:
        raise ValueError("window_width must be in 2..=52")
    expected = window_width * 3 + 1
    if len(masses) != expected:
        raise ValueError(f"mass length must be {expected}")
    values = _normalized(masses, expected, "masses")
    deltas = [0.0] * 156
    for index in range(1, 157):
        if index >= expected:
            break
        delta = values[index] - values[index - 1]
        if delta != delta or delta == float("inf") or delta == float("-inf"):
            raise ValueError(f"delta[{index}] must be finite")
        deltas[index - 1] = 0.0 if delta == 0.0 else delta
    gains = [
        values[window_width] - values[0],
        values[window_width * 2] - values[window_width],
        values[window_width * 3] - values[window_width * 2],
    ]
    for index in range(3):
        if gains[index] != gains[index] or gains[index] in (float("inf"), float("-inf")):
            raise ValueError(f"window gain {index} must be finite")
        if gains[index] == 0.0:
            gains[index] = 0.0
    mass_bits = _finite_bits(values[0], False)
    if _same_bits(values, expected, mass_bits):
        return 0
    if gains[2] < 0.0:
        return 1
    nondecreasing = _nonnegative_deltas(deltas, expected - 1)
    middle_positive = _middle_positive_count(deltas, window_width)
    if (
        nondecreasing
        and gains[0] >= 0.0
        and gains[1] > gains[0]
        and gains[1] > gains[2] > 0.0
        and values[window_width * 3] > values[0]
        and middle_positive >= 2
    ):
        return 2
    late_zero = _late_deltas_zero(deltas, window_width)
    if (
        nondecreasing
        and gains[0] >= 0.0
        and gains[1] > gains[0]
        and values[window_width * 3] > values[0]
        and middle_positive >= 2
        and late_zero
    ):
        return 3
    delta_bits = _finite_bits(deltas[0], False)
    if deltas[0] > 0.0 and _same_bits(deltas, expected - 1, delta_bits):
        return 4
    return 5


def _classify_persistence(post_width: int, separations: Sequence[float]) -> int:
    if not 2 <= post_width <= 52:
        raise ValueError("post_width must be in 2..=52")
    expected = post_width + 1
    if len(separations) != expected:
        raise ValueError(f"separation length must be {expected}")
    values = _normalized(separations, expected, "separations")
    if (
        _finite_bits(values[-2], False) == b"\x00" * 8
        and _finite_bits(values[-1], False) == b"\x00" * 8
    ):
        return 0
    if values[0] != 0.0 and values[-1] != 0.0 and (values[0] < 0.0) != (values[-1] < 0.0):
        return 1
    retained = values[0] != 0.0
    for index in range(53):
        if index >= expected:
            break
        if values[index] == 0.0 or (values[index] < 0.0) != (values[0] < 0.0):
            retained = False
    return 2 if retained else 3


def _tagged_digest(tag: int) -> bytes:
    if not 0 <= tag <= 255:
        raise ValueError("digest tag must fit u8")
    value = bytearray(32)
    value[0] = tag
    value[31] = tag ^ 0xFF
    return bytes(value)


def _framed_nfc(value: str, field: str, maximum: int) -> bytes:
    encoded = _nfc_utf8(value, field, 1, maximum)
    return struct.pack(">H", len(encoded)) + encoded


def _framed_ascii(value: str, field: str, maximum: int) -> bytes:
    encoded = _ascii(value, field, 1, maximum)
    return struct.pack(">H", len(encoded)) + encoded


def _run_identity_envelope(mutation_index: int = -1) -> bytes:
    session = "run-互助" if mutation_index == 0 else "run-é"
    payload = bytearray(_framed_nfc(session, "session", 256))
    for index in range(15):
        tag = index + 1
        if mutation_index == index + 1:
            tag += 128
        payload.extend(_tagged_digest(tag))
    rng = "rng-v2" if mutation_index == 16 else "rng-v1"
    graph = "graph-v2" if mutation_index == 17 else "graph-v1"
    payload.extend(_framed_ascii(rng, "rng_algorithm_id", 64))
    payload.extend(_framed_ascii(graph, "graph_contract_id", 64))
    return _envelope(b"babylon.run-identity.v1", bytes(payload))


def _sample_envelope(tick: int, first_tag: int, aggregate: float) -> bytes:
    payload = bytearray(struct.pack(">Q", tick))
    for index in range(3):
        payload.extend(_tagged_digest(first_tag + index))
    payload.extend(_finite_bits(aggregate, True))
    return _envelope(b"babylon.sfs-sample.v1", bytes(payload))


def _trace_envelope() -> bytes:
    masses = (0.0, 1.0, 2.0, 5.0, 8.0, 10.0, 11.0)
    payload = bytearray(_tagged_digest(24) + _tagged_digest(25))
    payload.extend(struct.pack(">QQHHH", 26, 100, 1, 2, 7))
    for index in range(7):
        payload.extend(_sample_envelope(100 + index, 40 + index * 3, masses[index]))
    payload.append(_classify_sfs(2, masses))
    return _envelope(b"babylon.sfs-trace.v1", bytes(payload))


def _candidate_bytes(tick: int, authority_tag: int, intent_tag: int) -> bytes:
    authority = _tagged_digest(authority_tag)
    intent = _tagged_digest(intent_tag)
    preimage = b"babylon.practice-attempt-row.v1\x00" + struct.pack(">Q", tick) + authority + intent
    return _digest(preimage) + struct.pack(">Q", tick) + authority + intent


def _candidate_rows() -> list[bytes]:
    rows = [_candidate_bytes(201, 70, 71), _candidate_bytes(200, 72, 73)]
    rows.sort(key=lambda row: (row[32:40], row[:32]))
    return rows


def _candidate_schedule_envelope() -> bytes:
    rows = _candidate_rows()
    return _envelope(
        b"babylon.practice-candidate-schedule.v1", struct.pack(">I", 2) + rows[0] + rows[1]
    )


def _preregistration_envelope() -> bytes:
    payload = bytearray(struct.pack(">QQ", 299, 300))
    for tag in range(80, 86):
        payload.extend(_tagged_digest(tag))
    payload.extend(struct.pack(">BBQHHB", 0, 0, 310, 3, 4, 2))
    payload.extend(_tagged_digest(86))
    payload.extend(struct.pack(">I", 87))
    payload.extend(_tagged_digest(88))
    return _envelope(b"babylon.sfs-preregistration.v1", bytes(payload))


def _attempt_ledger_envelope() -> bytes:
    rows = _candidate_rows()
    payload = bytearray(_tagged_digest(90) + struct.pack(">I", 2))
    payload.extend(rows[0] + bytes([0]) + _tagged_digest(91))
    payload.extend(rows[1] + bytes([1]) + _tagged_digest(92))
    return _envelope(b"babylon.practice-attempt-ledger.v1", bytes(payload))


def _string_set(values: Sequence[str], maximum: int) -> bytes:
    if len(values) > MAX_COMPONENTS:
        raise ValueError("profile set exceeds 64 entries")
    encoded: list[bytes] = []
    for index in range(MAX_COMPONENTS):
        if index >= len(values):
            break
        encoded.append(_nfc_utf8(values[index], "profile_set", 1, maximum))
    encoded.sort()
    payload = bytearray(struct.pack(">H", len(encoded)))
    for index in range(MAX_COMPONENTS):
        if index >= len(encoded):
            break
        if index > 0 and encoded[index] == encoded[index - 1]:
            raise ValueError("duplicate profile set entry")
        payload.extend(struct.pack(">H", len(encoded[index])))
        payload.extend(encoded[index])
    return bytes(payload)


def _component_envelope() -> bytes:
    payload = bytearray(_framed_nfc("component-Ā", "component_id", 256))
    payload.extend(bytes([1]) + _tagged_digest(100))
    sets = (
        ("field-a", "مساعدة"),
        ("edge-a",),
        ("x" * 96,),
        ("q",),
        ("op",),
        ("intrinsic",),
        ("clamp",),
        ("effect", "互助"),
    )
    for index in range(8):
        payload.extend(_string_set(sets[index], 96))
    return _envelope(b"babylon.sfs-component-proof-profile.v1", bytes(payload))


def _proof_profile_envelope() -> bytes:
    payload = bytearray(_tagged_digest(110) + _tagged_digest(111))
    payload.extend(_framed_ascii("babylon.sfs.audit.v1", "audit_semantics_id", 64))
    payload.extend(_tagged_digest(112) + _tagged_digest(113))
    payload.extend(struct.pack(">H", 1) + _component_envelope())
    return _envelope(b"babylon.sfs-proof-profile.v1", bytes(payload))


def _causal_cone_envelope() -> bytes:
    payload = bytearray(_string_set(("z", "aa", "\U00010000"), 256))
    payload.extend(_string_set(("café",), 256))
    payload.extend(_string_set(("Ā", "互助"), 256))
    return _envelope(b"babylon.sfs-causal-cone.v1", bytes(payload))


def _intervention_envelope() -> bytes:
    zero = bytes(32)
    rows = [
        bytes([0]) + _tagged_digest(120) + zero + _tagged_digest(121),
        bytes([1]) + _tagged_digest(122) + _tagged_digest(123) + zero,
        bytes([2]) + _tagged_digest(124) + _tagged_digest(125) + _tagged_digest(126),
    ]
    rows.sort(key=lambda row: row[1:33])
    payload = bytes([1]) + struct.pack(">I", 3) + rows[0] + rows[1] + rows[2]
    return _envelope(b"babylon.intervention-delta.v1", payload)


def _persistence_envelope() -> bytes:
    separations = (2.0, 1.0, 0.5)
    payload = bytearray(_tagged_digest(130) + _tagged_digest(131) + bytes([1]))
    payload.extend(_tagged_digest(132) + _tagged_digest(133) + _tagged_digest(134))
    payload.extend(struct.pack(">QHH", 135, 2, 3))
    for index in range(3):
        payload.extend(_finite_bits(separations[index], False))
    payload.append(_classify_persistence(2, separations))
    return _envelope(b"babylon.persistence-comparison.v1", bytes(payload))


def _wire_row(label: str, envelope: bytes) -> str:
    domain = envelope.split(b"\x00", 1)[0].decode("ascii", "strict")
    return f"wire|{label}|{domain}|{envelope.hex()}|{_digest(envelope).hex()}"


def _wire_vectors() -> list[str]:
    _require_unicode_version()
    rows = [
        _wire_row("run-identity", _run_identity_envelope()),
        _wire_row("sfs-sample", _sample_envelope(7, 21, 3.5)),
        _wire_row("sfs-trace", _trace_envelope()),
        _wire_row("sfs-preregistration", _preregistration_envelope()),
        _wire_row("practice-candidate-schedule", _candidate_schedule_envelope()),
        _wire_row("practice-attempt-ledger", _attempt_ledger_envelope()),
        _wire_row("component-proof-profile", _component_envelope()),
        _wire_row("proof-profile", _proof_profile_envelope()),
        _wire_row("causal-cone", _causal_cone_envelope()),
        _wire_row("intervention-delta", _intervention_envelope()),
        _wire_row("persistence-comparison", _persistence_envelope()),
    ]
    rows.sort(key=lambda row: row.split("|", 3)[1])
    return rows


def _bits_csv(values: Sequence[float], count: int) -> str:
    bits: list[str] = []
    for index in range(MAX_SAMPLES):
        if index >= count:
            break
        bits.append(_finite_bits(values[index], False).hex())
    return ",".join(bits)


def _classifier_vectors() -> list[str]:
    sfs = (
        ("constant-rate", (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0)),
        ("continuing", (0.0, 1.0, 2.0, 5.0, 8.0, 10.0, 11.0)),
        ("flat-plateau", (5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0)),
        ("late-plateau", (0.0, 1.0, 2.0, 5.0, 8.0, 8.0, 8.0)),
        ("other-alternating", (0.0, 2.0, 2.0, 4.0, 4.0, 6.0, 6.0)),
        ("other-late-gap", (0.0, 1.0, 2.0, 5.0, 8.0, 0.0, 8.0)),
        ("other-shape", (0.0, 3.0, 6.0, 7.0, 8.0, 10.0, 12.0)),
        ("reversal", (0.0, 1.0, 2.0, 5.0, 8.0, 6.0, 4.0)),
    )
    persistence = (
        ("mixed", (2.0, 0.0, 1.0)),
        ("persistent", (2.0, 1.0, 0.5)),
        ("reconverged", (2.0, 0.0, 0.0)),
        ("reversed", (2.0, 1.0, -1.0)),
    )
    rows: list[str] = []
    for index in range(8):
        label, sfs_values = sfs[index]
        rows.append(
            f"classifier|{label}|2|{_bits_csv(sfs_values, 7)}|{_classify_sfs(2, sfs_values)}"
        )
    for index in range(4):
        label, persistence_values = persistence[index]
        rows.append(
            f"persistence|{label}|2|{_bits_csv(persistence_values, 3)}|"
            f"{_classify_persistence(2, persistence_values)}"
        )
    rows.sort()
    return rows


def _identity_mutations() -> list[str]:
    _require_unicode_version()
    rows: list[str] = []
    for index in range(18):
        envelope = _run_identity_envelope(index)
        rows.append(
            f"mutation|run-identity|{RUN_FIELD_NAMES[index]}|{envelope.hex()}|{_digest(envelope).hex()}"
        )
    rows.sort(key=lambda row: row.split("|", 4)[2])
    return rows


def _read_exact_manifest(path: Path, maximum: int) -> bytes:
    with path.open("rb") as source:
        metadata = os.fstat(source.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > maximum:
            raise ValueError(f"{path.name} is not one bounded regular file")
        value = source.read(maximum + 1)
    if b"\r" in value or not value.endswith(b"\n") or value.endswith(b"\n\n"):
        raise ValueError(f"{path.name} must use exact LF framing")
    return value


def _lower_hex(value: str, field: str, maximum_bytes: int) -> bytes:
    if not value or len(value) % 2 or value.lower() != value:
        raise ValueError(f"{field} must be nonempty lowercase even hex")
    try:
        decoded = bytes.fromhex(value)
    except ValueError as error:
        raise ValueError(f"{field} must be lowercase hex") from error
    if len(decoded) > maximum_bytes or decoded.hex() != value:
        raise ValueError(f"{field} exceeds its exact bound")
    return decoded


def _nfc_hex(value: str, field: str, maximum_bytes: int) -> tuple[str, bytes]:
    decoded = _lower_hex(value, field, maximum_bytes)
    try:
        text = decoded.decode("utf-8", "strict")
    except UnicodeDecodeError as error:
        raise ValueError(f"{field} must decode as UTF-8") from error
    if unicodedata2.normalize("NFC", text) != text:
        raise ValueError(f"{field} must decode to NFC")
    return text, decoded


def _verify_source_manifests(forbidden_path: Path, audit_path: Path) -> tuple[bytes, bytes]:
    forbidden = _read_exact_manifest(forbidden_path, 131_072)
    audit = _read_exact_manifest(audit_path, 4_096)
    forbidden_rows = forbidden.decode("ascii", "strict").splitlines()
    if forbidden_rows != sorted(forbidden_rows) or len(forbidden_rows) != 18:
        raise ValueError("forbidden manifest rows must be exact and sorted")
    for index in range(18):
        parts = forbidden_rows[index].split("|")
        if len(parts) != 5:
            raise ValueError("forbidden manifest row malformed")
        source = BSL_PROFILE_ROOT / parts[1]
        if not source.is_file() or len(_lower_hex(parts[2], "forbidden source digest", 32)) != 32:
            raise ValueError("forbidden source row mismatch")
    audit_rows = audit.decode("ascii", "strict").splitlines()
    if audit_rows != sorted(audit_rows) or len(audit_rows) != 2:
        raise ValueError("audit source manifest rows must be exact and sorted")
    source_root = ROOT / "rust" / "crates" / "babylon-bsl" / "src"
    for index in range(2):
        name, digest = audit_rows[index].split("|")
        if hashlib.sha256((source_root / name).read_bytes()).hexdigest() != digest:
            raise ValueError("audit source digest mismatch")
    return forbidden, audit


def _parse_synthetic_manifest(path: Path) -> tuple[bytes, list[dict[str, object]]]:
    raw = _read_exact_manifest(path, 1_048_576)
    rows = raw.decode("ascii", "strict").splitlines()
    if rows != sorted(rows) or len(rows) > 36_992:
        raise ValueError("governed manifest rows must be complete-row sorted")
    parsed: list[dict[str, object]] = []
    for index in range(36_992):
        if index >= len(rows):
            break
        parts = rows[index].split("|")
        kind = parts[0]
        if kind == "component" and len(parts) == 6:
            component_id, _ = _nfc_hex(parts[1], "component id", 256)
            source_payload = _lower_hex(parts[4], "source payload", 65_535)
            source_digest = _lower_hex(parts[5], "source digest", 32)
            if len(source_digest) != 32:
                raise ValueError("component source digest must be 32 bytes")
            mode = parts[3]
            if mode == "canonical-bsl":
                expected = hashlib.sha256(source_payload).digest()
            elif mode == "synthetic-descriptor":
                expected = hashlib.sha256(
                    SYNTHETIC_COMPONENT_SOURCE_DOMAIN + b"\0" + source_payload
                ).digest()
            else:
                raise ValueError("unknown component source mode")
            if source_digest != expected:
                raise ValueError("component source digest mismatch")
            parsed.append(
                {
                    "row": rows[index],
                    "kind": kind,
                    "id": component_id,
                    "code": int(parts[2]),
                    "mode": mode,
                    "payload": source_payload,
                    "digest": source_digest,
                }
            )
        elif kind == "profile" and len(parts) == 4:
            component_id, _ = _nfc_hex(parts[1], "profile component", 256)
            entry, _ = _nfc_hex(parts[3], "profile entry", 96)
            if parts[2] not in {
                "field_reads",
                "edge_reads",
                "constant_reads",
                "queries",
                "operators",
                "intrinsics",
                "comparison_clamp_contexts",
                "effects",
            }:
                raise ValueError("unknown profile set")
            parsed.append(
                {
                    "row": rows[index],
                    "kind": kind,
                    "id": component_id,
                    "set": parts[2],
                    "entry": entry,
                }
            )
        elif kind == "bound" and len(parts) == 6:
            component_id, _ = _nfc_hex(parts[1], "bound component", 256)
            if parts[2:4] != ["128", "31"]:
                raise ValueError("bound row differs from the frozen audit")
            cardinality = _lower_hex(parts[4], "cardinality digest", 32)
            intrinsic = _lower_hex(parts[5], "intrinsic cost digest", 32)
            if cardinality != SYNTHETIC_CARDINALITY_DIGEST:
                raise ValueError("cardinality digest differs from the frozen audit")
            if intrinsic != SYNTHETIC_INTRINSIC_COST_DIGEST:
                raise ValueError("intrinsic cost digest differs from the frozen audit")
            parsed.append({"row": rows[index], "kind": kind, "id": component_id})
        elif kind == "edge" and len(parts) == 5:
            producer, _ = _nfc_hex(parts[1], "edge producer", 256)
            consumer, _ = _nfc_hex(parts[2], "edge consumer", 256)
            channel, _ = _nfc_hex(parts[4], "edge channel", 96)
            code = int(parts[3])
            if not 0 <= code <= 5:
                raise ValueError("edge channel kind outside V1")
            parsed.append(
                {
                    "row": rows[index],
                    "kind": kind,
                    "producer": producer,
                    "consumer": consumer,
                    "code": code,
                    "channel": channel,
                }
            )
        else:
            raise ValueError(f"governed manifest row {index + 1} malformed")
    return raw, parsed


def _profile_set_bytes(entries: Sequence[str]) -> bytes:
    ordered = sorted(entries, key=lambda entry: entry.encode("utf-8"))
    return _string_set(ordered, 96)


def _synthetic_component_envelope(
    component: dict[str, object], rows: list[dict[str, object]]
) -> bytes:
    component_id = str(component["id"])
    payload = bytearray(_framed_nfc(component_id, "component_id", 256))
    payload.append(int(component["code"]))
    payload.extend(bytes(component["digest"]))
    set_names = (
        "field_reads",
        "edge_reads",
        "constant_reads",
        "queries",
        "operators",
        "intrinsics",
        "comparison_clamp_contexts",
        "effects",
    )
    for set_name in set_names:
        entries = [
            str(row["entry"])
            for row in rows
            if row["kind"] == "profile" and row["id"] == component_id and row["set"] == set_name
        ]
        payload.extend(_profile_set_bytes(entries))
    return _envelope(b"babylon.sfs-component-proof-profile.v1", bytes(payload))


def _synthetic_profile_vectors(
    governed_manifest_path: Path,
    forbidden_manifest_path: Path,
    audit_source_manifest_path: Path,
) -> list[str]:
    """Return the three component, one cone, and one proof-profile rows."""
    raw, rows = _parse_synthetic_manifest(governed_manifest_path)
    forbidden, audit = _verify_source_manifests(forbidden_manifest_path, audit_source_manifest_path)
    components = [row for row in rows if row["kind"] == "component"]
    if [(row["id"], row["code"], row["mode"]) for row in components] != [
        ("membership-reducer", 2, "synthetic-descriptor"),
        ("post-commit-producer", 3, "synthetic-descriptor"),
        ("scoped-bsl-rule", 0, "canonical-bsl"),
    ]:
        raise ValueError("synthetic component registry mismatch")
    profiles = [_synthetic_component_envelope(component, rows) for component in components]
    cone_payload = (
        _string_set(["scoped-bsl-rule"], 256)
        + _string_set(["post-commit-producer"], 256)
        + _string_set([str(row["id"]) for row in components], 256)
    )
    cone = _envelope(b"babylon.sfs-causal-cone.v1", cone_payload)
    governed_digest = hashlib.sha256(SYNTHETIC_GOVERNED_MANIFEST_DOMAIN + b"\0" + raw).digest()
    proof_payload = bytearray(governed_digest)
    proof_payload.extend(hashlib.sha256(FORBIDDEN_CORPUS_DOMAIN + b"\0" + forbidden).digest())
    proof_payload.extend(_framed_ascii("babylon.sfs.audit.v1", "audit_semantics_id", 64))
    proof_payload.extend(hashlib.sha256(AUDIT_SOURCE_DOMAIN + b"\0" + audit).digest())
    proof_payload.extend(hashlib.sha256(cone).digest())
    proof_payload.extend(struct.pack(">H", len(profiles)))
    for envelope in profiles:
        proof_payload.extend(envelope)
    proof = _envelope(b"babylon.sfs-proof-profile.v1", bytes(proof_payload))
    output = [
        f"component|{components[index]['id']}|babylon.sfs-component-proof-profile.v1|"
        f"{profiles[index].hex()}|{hashlib.sha256(profiles[index]).hexdigest()}"
        for index in range(3)
    ]
    output.extend(
        [
            f"cone|synthetic-chain|babylon.sfs-causal-cone.v1|{cone.hex()}|{hashlib.sha256(cone).hexdigest()}",
            f"proof-profile|synthetic-chain|babylon.sfs-proof-profile.v1|{proof.hex()}|"
            f"{hashlib.sha256(proof).hexdigest()}",
        ]
    )
    output.sort(key=lambda row: row.encode("ascii"))
    return output


def _synthetic_driver_vectors(driver_source_path: Path) -> tuple[bytes, list[str]]:
    """Return the complete source-bound contract and its two independent rows."""
    source = _read_regular_bytes(driver_source_path, 262_144)
    source_domain = b"babylon.sfs-driver-source.v1"
    contract_domain = b"babylon.sfs-synthetic-driver-contract.v1"
    source_digest = hashlib.sha256(source_domain + b"\0" + source).hexdigest()
    contract = (
        b"schema|1\n"
        b"predicate|candidate-projection|1\n"
        b"predicate|cumulative-driver-shape|1\n"
        b"predicate|persistence-comparison-identity|1\n"
        b"predicate|aligned-material-sequence|1\n"
        b"predicate|twin-identity-difference|1\n"
        + f"source|driver.rs|{source_digest}\n".encode("ascii")
    )
    if len(contract) > MAX_SYNTHETIC_DRIVER_CONTRACT_BYTES or len(contract.splitlines()) != 7:
        raise ValueError("synthetic driver contract exceeds its exact bounds")
    contract_digest = hashlib.sha256(contract_domain + b"\0" + contract).hexdigest()
    rows = [
        f"driver-contract|{contract_domain.decode()}|{contract.hex()}|{contract_digest}",
        f"driver-source|{source_domain.decode()}|{source.hex()}|{source_digest}",
    ]
    rows.sort(key=lambda row: row.encode("ascii"))
    vector_bytes = len(rows[0].encode("ascii")) + len(rows[1].encode("ascii")) + 2
    if vector_bytes > MAX_SYNTHETIC_DRIVER_BYTES:
        raise ValueError("synthetic driver vector bytes exceed the exact bound")
    return contract, rows


def _read_regular_bytes(path: Path, maximum: int) -> bytes:
    with path.open("rb") as source:
        metadata = os.fstat(source.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > maximum:
            raise ValueError(f"{path.name} is not one bounded regular file")
        value = source.read(maximum + 1)
    if len(value) != metadata.st_size:
        raise ValueError(f"{path.name} changed during its bounded read")
    return value


def _stage_atomic(path: Path, expected: bytes) -> Path:
    descriptor = -1
    staged: Path | None = None
    handle = None
    try:
        descriptor, staged_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        staged = Path(staged_name)
        handle = os.fdopen(descriptor, "wb")
        descriptor = -1
        if handle.write(expected) != len(expected):
            raise OSError("short fixture write")
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        return staged
    except OSError as error:
        if descriptor >= 0:
            os.close(descriptor)
        if handle is not None:
            handle.close()
        if staged is not None:
            _remove_stage(staged)
        raise VectorIoError(path, "stage") from error


def _write_driver_pair(contract: bytes, vectors: bytes) -> None:
    staged_contract = _stage_atomic(SYNTHETIC_DRIVER_CONTRACT_PATH, contract)
    try:
        staged_vectors = _stage_atomic(SYNTHETIC_DRIVER_PATH, vectors)
    except VectorIoError:
        _remove_stage(staged_contract)
        raise
    try:
        os.replace(staged_contract, SYNTHETIC_DRIVER_CONTRACT_PATH)
        os.replace(staged_vectors, SYNTHETIC_DRIVER_PATH)
    except OSError as error:
        _remove_stage(staged_contract)
        _remove_stage(staged_vectors)
        raise VectorIoError(SYNTHETIC_DRIVER_PATH, "replace-pair") from error


def _row_key(row: str) -> str:
    kind, remainder = row.split("|", 1)
    label, remainder = remainder.split("|", 1)
    if kind != "mutation":
        return f"{kind}|{label}"
    field, _remainder = remainder.split("|", 1)
    return f"{kind}|{label}|{field}"


def _render(rows: Sequence[str]) -> bytes:
    if len(rows) > MAX_ROWS:
        raise ValueError("fixture row count exceeds 65535")
    output = bytearray()
    previous_key = ""
    for index in range(MAX_ROWS):
        if index >= len(rows):
            break
        row = rows[index]
        key = _row_key(row)
        if index > 0 and key <= previous_key:
            raise ValueError("fixture rows must be unique and sorted")
        try:
            encoded = row.encode("ascii", "strict")
        except UnicodeEncodeError as error:
            raise ValueError("fixture rows must be ASCII") from error
        if len(encoded) + 1 > MAX_VECTOR_BYTES:
            raise ValueError("single vector row exceeds maximum vector bytes")
        if len(output) + len(encoded) + 1 > MAX_VECTOR_BYTES:
            raise ValueError("combined output exceeds maximum vector bytes")
        output.extend(encoded)
        output.append(0x0A)
        previous_key = key
    return bytes(output)


def _fixture_outputs() -> tuple[tuple[Path, bytes], ...]:
    return (
        (WIRE_PATH, _render(_wire_vectors())),
        (CLASSIFIER_PATH, _render(_classifier_vectors())),
        (MUTATION_PATH, _render(_identity_mutations())),
    )


def _check(path: Path, expected: bytes) -> bool:
    try:
        with path.open("rb") as fixture:
            metadata = os.fstat(fixture.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != len(expected):
                return False
            actual = fixture.read(len(expected) + 1)
    except OSError as error:
        raise VectorIoError(path, "check") from error
    return actual == expected


def _remove_stage(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        return


def _write_atomic(path: Path, expected: bytes) -> None:
    if len(expected) > MAX_VECTOR_BYTES:
        raise ValueError("vector bytes exceed maximum")
    descriptor = -1
    staged: Path | None = None
    handle = None
    operation = "stage"
    try:
        descriptor, staged_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        staged = Path(staged_name)
        operation = "open"
        handle = os.fdopen(descriptor, "wb")
        descriptor = -1
        operation = "write"
        if handle.write(expected) != len(expected):
            raise OSError("short fixture write")
        operation = "flush"
        handle.flush()
        operation = "fsync"
        os.fsync(handle.fileno())
        operation = "close"
        handle.close()
        operation = "replace"
        os.replace(staged, path)
    except OSError as error:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if handle is not None:
            try:
                handle.close()
            except OSError:
                pass
        if staged is not None:
            _remove_stage(staged)
        raise VectorIoError(path, operation) from error


def main(argv: Sequence[str] | None = None) -> int:
    _require_unicode_version()
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write-synthetic-profile", action="store_true")
    mode.add_argument("--check-synthetic-profile", action="store_true")
    mode.add_argument("--write-synthetic-driver", action="store_true")
    mode.add_argument("--check-synthetic-driver", action="store_true")
    args = parser.parse_args(argv)
    if args.write_synthetic_driver or args.check_synthetic_driver:
        contract, rows = _synthetic_driver_vectors(DRIVER_SOURCE_PATH)
        vectors = _render(rows)
        if args.write_synthetic_driver:
            _write_driver_pair(contract, vectors)
            return 0
        if not _check(SYNTHETIC_DRIVER_CONTRACT_PATH, contract) or not _check(
            SYNTHETIC_DRIVER_PATH, vectors
        ):
            print(SYNTHETIC_DRIVER_PATH, file=sys.stderr)
            return 1
        return 0
    if args.write_synthetic_profile or args.check_synthetic_profile:
        expected = _render(
            _synthetic_profile_vectors(
                SYNTHETIC_GOVERNED_MANIFEST_PATH,
                FORBIDDEN_MANIFEST_PATH,
                AUDIT_SOURCE_MANIFEST_PATH,
            )
        )
        if args.write_synthetic_profile:
            _write_atomic(SYNTHETIC_PROFILE_PATH, expected)
            return 0
        if not _check(SYNTHETIC_PROFILE_PATH, expected):
            print(SYNTHETIC_PROFILE_PATH, file=sys.stderr)
            return 1
        return 0
    outputs = _fixture_outputs()
    for index in range(3):
        path, expected = outputs[index]
        try:
            if args.write:
                _write_atomic(path, expected)
            elif not _check(path, expected):
                print(path, file=sys.stderr)
                return 1
        except VectorIoError as error:
            print(error, file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
