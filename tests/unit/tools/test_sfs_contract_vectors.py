"""Independent behavioral contracts for the T3 cross-language vector oracle."""

import hashlib
import importlib.util
import os
import stat
import struct
import sys
from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).parents[3]
TOOL_PATH = ROOT / "tools" / "sfs_contract_vectors.py"
SPEC = importlib.util.spec_from_file_location("sfs_contract_vectors", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
exporter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = exporter
SPEC.loader.exec_module(exporter)

RUN_IDENTITY_HEX = (
    "626162796c6f6e2e72756e2d6964656e746974792e7631000001000001fa0006"
    "72756e2dc3a90100000000000000000000000000000000000000000000000000"
    "0000000000fe0200000000000000000000000000000000000000000000000000"
    "0000000000fd0300000000000000000000000000000000000000000000000000"
    "0000000000fc0400000000000000000000000000000000000000000000000000"
    "0000000000fb0500000000000000000000000000000000000000000000000000"
    "0000000000fa0600000000000000000000000000000000000000000000000000"
    "0000000000f90700000000000000000000000000000000000000000000000000"
    "0000000000f80800000000000000000000000000000000000000000000000000"
    "0000000000f70900000000000000000000000000000000000000000000000000"
    "0000000000f60a00000000000000000000000000000000000000000000000000"
    "0000000000f50b00000000000000000000000000000000000000000000000000"
    "0000000000f40c00000000000000000000000000000000000000000000000000"
    "0000000000f30d00000000000000000000000000000000000000000000000000"
    "0000000000f20e00000000000000000000000000000000000000000000000000"
    "0000000000f10f00000000000000000000000000000000000000000000000000"
    "0000000000f00006726e672d7631000867726170682d7631"
)
RUN_IDENTITY_SHA256 = "ded4b236aeb7cdbd093d007238a37725c700e22e67aa04222a332239129998d4"

WIRE_LABELS = [
    "causal-cone",
    "component-proof-profile",
    "intervention-delta",
    "persistence-comparison",
    "practice-attempt-ledger",
    "practice-candidate-schedule",
    "proof-profile",
    "run-identity",
    "sfs-preregistration",
    "sfs-sample",
    "sfs-trace",
]
MUTATION_FIELDS = sorted(
    [
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
    ]
)


def _line_parts(rows: Sequence[str]) -> list[list[str]]:
    parts: list[list[str]] = []
    for index in range(65_535):
        if index >= len(rows):
            break
        parts.append(rows[index].split("|"))
    return parts


def test_uniform_envelope_is_literal_bytes() -> None:
    payload = b"\xaa"
    expected = (
        b"babylon.sfs-sample.v1"
        + bytes([0])
        + struct.pack(">H", 1)
        + struct.pack(">I", 1)
        + payload
    )
    assert exporter._envelope(b"babylon.sfs-sample.v1", payload) == expected
    assert exporter._digest(expected) == hashlib.sha256(expected).digest()


def test_complete_asymmetric_run_identity_is_a_literal_contract() -> None:
    rows = _line_parts(exporter._wire_vectors())
    run: list[str] | None = None
    for index in range(11):
        if rows[index][1] == "run-identity":
            run = rows[index]
    assert run == [
        "wire",
        "run-identity",
        "babylon.run-identity.v1",
        RUN_IDENTITY_HEX,
        RUN_IDENTITY_SHA256,
    ]


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ((0, 1, 2, 5, 8, 10, 11), 2),
        ((0, 1, 2, 5, 8, 8, 8), 3),
        ((5, 5, 5, 5, 5, 5, 5), 0),
        ((0, 1, 2, 5, 8, 6, 4), 1),
        ((0, 1, 2, 3, 4, 5, 6), 4),
        ((0, 3, 6, 7, 8, 10, 12), 5),
        ((0, 1, 2, 5, 8, 0, 8), 5),
        ((0, 2, 2, 4, 4, 6, 6), 5),
    ],
)
def test_sfs_goldens(values: Sequence[int], expected: int) -> None:
    assert exporter._classify_sfs(2, tuple(map(float, values))) == expected


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ((2.0, 0.0, 0.0), 0),
        ((2.0, 1.0, -1.0), 1),
        ((2.0, 1.0, 0.5), 2),
        ((2.0, 0.0, 1.0), 3),
    ],
)
def test_persistence_goldens(values: Sequence[float], expected: int) -> None:
    assert exporter._classify_persistence(2, values) == expected


def test_primitive_bounds_signed_zero_and_nonfinite_values_are_closed() -> None:
    with pytest.raises(ValueError, match="domain"):
        exporter._envelope(b"", b"")
    with pytest.raises(ValueError, match="domain"):
        exporter._envelope(b"bad\x00domain", b"")
    with pytest.raises(ValueError, match="domain"):
        exporter._envelope(b"d" * 65, b"")
    with pytest.raises(ValueError, match="ASCII"):
        exporter._envelope("é".encode(), b"")
    assert exporter._finite_bits(-0.0, True) == struct.pack(">d", 0.0)
    with pytest.raises(ValueError, match="finite"):
        exporter._finite_bits(float("nan"), False)
    with pytest.raises(ValueError, match="negative"):
        exporter._finite_bits(-1.0, True)
    with pytest.raises(ValueError, match="window_width"):
        exporter._classify_sfs(1, [0.0] * 4)
    with pytest.raises(ValueError, match="length"):
        exporter._classify_sfs(2, [0.0] * 6)
    with pytest.raises(ValueError, match="post_width"):
        exporter._classify_persistence(53, [0.0] * 54)
    maximum_masses: list[float] = []
    for _index in range(157):
        maximum_masses.append(0.0)
    assert exporter._classify_sfs(52, maximum_masses) == 0
    maximum_separations: list[float] = []
    for _index in range(53):
        maximum_separations.append(0.0)
    assert exporter._classify_persistence(52, maximum_separations) == 0


def test_unicode_17_witnesses_and_scalar_byte_bounds_are_exact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    witnesses = ("café", "Ā", "مساعدة", "互助", "\U00010000")
    for index in range(5):
        encoded = exporter._nfc_utf8(witnesses[index], "witness", 1, 256)
        assert encoded == witnesses[index].encode("utf-8")
    assert exporter._nfc_utf8("a", "witness", 1, 1) == b"a"
    assert exporter._nfc_utf8("a" * 256, "witness", 1, 256) == b"a" * 256
    with pytest.raises(ValueError, match="NFC"):
        exporter._nfc_utf8("cafe\N{COMBINING ACUTE ACCENT}", "witness", 1, 256)
    with pytest.raises(ValueError, match="scalar"):
        exporter._nfc_utf8("a" * 257, "witness", 1, 512)
    with pytest.raises(ValueError, match="ASCII"):
        exporter._ascii("é", "identifier", 1, 64)

    monkeypatch.setattr(exporter.unicodedata2, "unidata_version", "16.0.0")
    with pytest.raises(
        exporter.UnicodeDataVersionError,
        match="expected Unicode data 17.0.0, found 16.0.0",
    ):
        exporter._nfc_utf8("café", "witness", 1, 256)
    with pytest.raises(exporter.UnicodeDataVersionError):
        exporter._wire_vectors()
    with pytest.raises(exporter.UnicodeDataVersionError):
        exporter.main(["--check"])


def test_string_set_sorts_raw_nfc_bytes_before_framing_and_rejects_duplicates() -> None:
    assert exporter._string_set(("z", "aa"), 96) == b"\x00\x02\x00\x02aa\x00\x01z"
    with pytest.raises(ValueError, match="duplicate profile set entry"):
        exporter._string_set(("z", "z"), 96)


def test_vector_collections_are_exact_closed_sorted_ascii_lf_rows() -> None:
    wire = exporter._wire_vectors()
    classifier = exporter._classifier_vectors()
    mutations = exporter._identity_mutations()
    wire_parts = _line_parts(wire)
    wire_labels: list[str] = []
    for index in range(11):
        wire_labels.append(wire_parts[index][1])
    assert wire_labels == WIRE_LABELS
    assert len(classifier) == 12
    classifier_count = 0
    persistence_count = 0
    for index in range(12):
        if classifier[index].startswith("classifier|"):
            classifier_count += 1
        elif classifier[index].startswith("persistence|"):
            persistence_count += 1
    assert classifier_count == 8
    assert persistence_count == 4
    mutation_parts = _line_parts(mutations)
    mutation_fields: list[str] = []
    for index in range(18):
        mutation_fields.append(mutation_parts[index][2])
    assert mutation_fields == MUTATION_FIELDS
    assert len(mutations) == 18
    collections = (wire, classifier, mutations)
    for index in range(3):
        rendered = exporter._render(collections[index])
        assert rendered.endswith(b"\n")
        assert rendered.decode("ascii").splitlines() == collections[index]
        assert len(rendered) <= exporter.MAX_VECTOR_BYTES

    duplicate = wire[0].replace("|" + wire[0].split("|")[3], "|00", 1)
    with pytest.raises(ValueError, match="unique and sorted"):
        exporter._render([wire[0], duplicate])


def test_fixture_row_maximum_succeeds_and_plus_one_preflights() -> None:
    rows: list[str] = []
    for index in range(65_536):
        rows.append(f"wire|row-{index:05}|d|00|00")
    maximum = exporter._render(rows[:65_535])
    assert maximum.count(b"\n") == 65_535
    with pytest.raises(ValueError, match="row count"):
        exporter._render(rows)


def test_each_identity_mutation_changes_literal_bytes_and_digest() -> None:
    base = bytes.fromhex(RUN_IDENTITY_HEX)
    base_digest = bytes.fromhex(RUN_IDENTITY_SHA256)
    rows = _line_parts(exporter._identity_mutations())
    for index in range(18):
        parts = rows[index]
        mutated = bytes.fromhex(parts[3])
        mutated_digest = bytes.fromhex(parts[4])
        assert mutated != base
        assert mutated_digest != base_digest
        assert exporter._digest(mutated) == mutated_digest


def test_check_rejects_bad_descriptor_metadata_before_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Fixture:
        def __enter__(self) -> "Fixture":
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def fileno(self) -> int:
            return 41

        def read(self, _: int = -1) -> bytes:
            raise AssertionError("metadata-rejected fixture must not be read")

    class FixturePath:
        def open(self, *_: object, **__: object) -> "Fixture":
            return Fixture()

        def stat(self, *_: object, **__: object) -> object:
            raise AssertionError("check must use the opened descriptor")

        def __str__(self) -> str:
            return "sfs-vectors.txt"

    def fake_fstat(descriptor: int) -> SimpleNamespace:
        assert descriptor == 41
        return SimpleNamespace(
            st_mode=stat.S_IFREG,
            st_size=exporter.MAX_VECTOR_BYTES + 1,
        )

    monkeypatch.setattr(os, "fstat", fake_fstat)
    assert not exporter._check(FixturePath(), b"expected")


def test_check_uses_one_bounded_read_from_the_opened_descriptor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reads: list[int] = []

    class Fixture:
        def __enter__(self) -> "Fixture":
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def fileno(self) -> int:
            return 42

        def read(self, amount: int = -1) -> bytes:
            reads.append(amount)
            return b"expected"

    class FixturePath:
        def open(self, *_: object, **__: object) -> "Fixture":
            return Fixture()

        def __str__(self) -> str:
            return "sfs-vectors.txt"

    monkeypatch.setattr(
        os,
        "fstat",
        lambda _descriptor: SimpleNamespace(st_mode=stat.S_IFREG, st_size=8),
    )
    assert exporter._check(FixturePath(), b"expected")
    assert reads == [9]


def test_atomic_replace_failure_preserves_old_file_and_removes_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "vectors.txt"
    destination.write_bytes(b"old-complete")

    def fail_replace(_: object, __: object) -> None:
        raise OSError("replace refused")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(exporter.VectorIoError) as caught:
        exporter._write_atomic(destination, b"new-complete")
    assert str(caught.value) == f"replace failed for {destination}"
    assert caught.value.path == destination
    assert caught.value.operation == "replace"
    assert isinstance(caught.value.__cause__, OSError)
    with pytest.raises(AttributeError):
        caught.value.path = tmp_path
    with pytest.raises(AttributeError):
        caught.value.operation = "write"
    assert destination.read_bytes() == b"old-complete"
    entries = tmp_path.iterdir()
    assert next(entries) == destination
    with pytest.raises(StopIteration):
        next(entries)


def test_atomic_write_failure_survives_handle_close_cleanup_and_unlinks_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "vectors.txt"
    destination.write_bytes(b"old-complete")

    class FailingHandle:
        def write(self, _: bytes) -> int:
            raise OSError("write refused")

        def close(self) -> None:
            raise OSError("close cleanup refused")

    def fake_fdopen(descriptor: int, mode: str) -> FailingHandle:
        assert mode == "wb"
        os.close(descriptor)
        return FailingHandle()

    monkeypatch.setattr(os, "fdopen", fake_fdopen)
    with pytest.raises(exporter.VectorIoError) as caught:
        exporter._write_atomic(destination, b"new-complete")
    assert caught.value.operation == "write"
    assert str(caught.value.__cause__) == "write refused"
    assert destination.read_bytes() == b"old-complete"
    assert list(tmp_path.iterdir()) == [destination]


def test_atomic_open_failure_survives_descriptor_close_cleanup_and_unlinks_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "vectors.txt"
    destination.write_bytes(b"old-complete")
    real_close = os.close

    def fail_fdopen(_: int, __: str) -> None:
        raise OSError("open refused")

    def close_then_fail(descriptor: int) -> None:
        real_close(descriptor)
        raise OSError("descriptor cleanup refused")

    monkeypatch.setattr(os, "fdopen", fail_fdopen)
    monkeypatch.setattr(os, "close", close_then_fail)
    with pytest.raises(exporter.VectorIoError) as caught:
        exporter._write_atomic(destination, b"new-complete")
    assert caught.value.operation == "open"
    assert str(caught.value.__cause__) == "open refused"
    assert destination.read_bytes() == b"old-complete"
    assert list(tmp_path.iterdir()) == [destination]


def test_atomic_failure_preserves_original_when_exact_stage_unlink_cleanup_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "vectors.txt"
    destination.write_bytes(b"old-complete")
    staged_paths: list[Path] = []
    real_unlink = Path.unlink

    def fail_replace(_: object, __: object) -> None:
        raise OSError("replace refused")

    def fail_stage_unlink(path: Path, *args: object, **kwargs: object) -> None:
        staged_paths.append(path)
        raise OSError("unlink cleanup refused")

    monkeypatch.setattr(os, "replace", fail_replace)
    monkeypatch.setattr(Path, "unlink", fail_stage_unlink)
    with pytest.raises(exporter.VectorIoError) as caught:
        exporter._write_atomic(destination, b"new-complete")
    assert caught.value.operation == "replace"
    assert str(caught.value.__cause__) == "replace refused"
    assert len(staged_paths) == 1
    assert staged_paths[0].parent == tmp_path
    assert staged_paths[0].name.startswith(f".{destination.name}.")
    assert destination.read_bytes() == b"old-complete"
    real_unlink(staged_paths[0])


def test_command_reports_the_exact_later_fixture_replace_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    wire = tmp_path / "wire.txt"
    classifier = tmp_path / "classifier.txt"
    mutations = tmp_path / "mutations.txt"
    monkeypatch.setattr(exporter, "WIRE_PATH", wire)
    monkeypatch.setattr(exporter, "CLASSIFIER_PATH", classifier)
    monkeypatch.setattr(exporter, "MUTATION_PATH", mutations)
    real_replace = os.replace
    calls = 0

    def fail_second_replace(
        source: str | os.PathLike[str],
        destination: str | os.PathLike[str],
    ) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("second replacement refused")
        real_replace(source, destination)

    monkeypatch.setattr(os, "replace", fail_second_replace)
    assert exporter.main(["--write"]) == 1
    assert capsys.readouterr().err.strip() == f"replace failed for {classifier}"
    assert wire.is_file()
    assert not classifier.exists()
    assert not mutations.exists()


def test_oversized_atomic_output_refuses_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        exporter.tempfile,
        "mkstemp",
        lambda **_: pytest.fail("oversized output must refuse before staging"),
    )
    with pytest.raises(ValueError, match="vector bytes"):
        exporter._write_atomic(
            tmp_path / "vectors.txt",
            b"x" * (exporter.MAX_VECTOR_BYTES + 1),
        )
