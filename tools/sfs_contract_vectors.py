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
MAX_NFC_SCALARS: Final = 256
UNICODE_DATA_VERSION: Final = "17.0.0"

ROOT: Final = Path(__file__).resolve().parents[1]
FIXTURE_ROOT: Final = ROOT / "rust" / "crates" / "babylon-evidence" / "tests" / "fixtures"
WIRE_PATH: Final = FIXTURE_ROOT / "sfs_wire_vectors_v1.txt"
CLASSIFIER_PATH: Final = FIXTURE_ROOT / "sfs_classifier_vectors_v1.txt"
MUTATION_PATH: Final = FIXTURE_ROOT / "sfs_identity_mutations_v1.txt"

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
    args = parser.parse_args(argv)
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
