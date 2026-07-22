"""Tests for the seam-algebra stub-vs-calculator check (T1.1 Unit 5).

Four tiers, mirroring ``test_seam_algebra_gate_satisfaction.py``'s own shape:

- **Registry shape teeth** — a malformed :class:`RegisteredCalculator`/
  :class:`StubConsumer` row fails loudly at construction (Constitution
  III.11), and a :class:`StubConsumer` naming an unknown calculator is
  rejected at collection time.
- **Grounding + stub semantics** (fixture files) — :func:`check_stub_vs_calculator`
  distinguishes a genuinely-live stub (the literal call site is really there,
  the cited calculator is really defined and really returns the declared
  type) from a stale registry row (the stub was fixed, the calculator was
  renamed, or the calculator's return type no longer matches) — the latter
  is always an infrastructure failure, never a silent pass. It also proves
  the anti-false-positive heuristic: a keyword bound to a variable/call is
  NEVER classified as a stub.
- **Mutation efficacy** — the two literal mutation tests the design names
  verbatim (§4 U5): (1) a fixture consumer fed a literal where a registered
  calculator exists reds; (2) reverting the ReproductionBalance disposition
  reds the REAL shipped registry.
- **Liveness + CLI wiring** — the real, shipped registry is clean (with the
  one dated exemption), and the family's CLI dispatch still exits 0.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.exemptions import SentinelExemption
from babylon.sentinels.seam_algebra import checks as checks_module
from babylon.sentinels.seam_algebra.checks import _REPO_ROOT, check_stub_vs_calculator
from babylon.sentinels.seam_algebra.registry import (
    CALCULATOR_REGISTRY,
    STUB_REGISTRY,
    STUB_VS_CALCULATOR_EXEMPTIONS,
    RegisteredCalculator,
    StubConsumer,
    _validate_stub_calculators_resolve,
)

pytestmark = pytest.mark.unit

_TOOL_PATH = Path(__file__).resolve().parents[3] / "tools" / "sentinel_check.py"


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Registry shape teeth
# ---------------------------------------------------------------------------


def test_registered_calculator_rejects_blank_name() -> None:
    with pytest.raises(ValidationError):
        RegisteredCalculator(name="", def_file="a.py", symbol="f", produces="X")


def test_registered_calculator_rejects_blank_symbol() -> None:
    with pytest.raises(ValidationError):
        RegisteredCalculator(name="x", def_file="a.py", symbol="", produces="X")


def test_registered_calculator_rejects_blank_produces() -> None:
    with pytest.raises(ValidationError):
        RegisteredCalculator(name="x", def_file="a.py", symbol="f", produces="")


def test_registered_calculator_rejects_non_py_def_file() -> None:
    with pytest.raises(ValidationError):
        RegisteredCalculator(name="x", def_file="a.txt", symbol="f", produces="X")


def test_registered_calculator_is_frozen() -> None:
    calc = RegisteredCalculator(name="x", def_file="a.py", symbol="f", produces="X")
    with pytest.raises(ValidationError):
        calc.name = "changed"  # type: ignore[misc]


def test_stub_consumer_rejects_blank_name() -> None:
    with pytest.raises(ValidationError):
        StubConsumer(
            name="",
            consumer_file="a.py",
            consumer_symbol="Thing",
            stub_field="k",
            calculator_name="c",
        )


def test_stub_consumer_rejects_blank_consumer_symbol() -> None:
    with pytest.raises(ValidationError):
        StubConsumer(
            name="x", consumer_file="a.py", consumer_symbol="", stub_field="k", calculator_name="c"
        )


def test_stub_consumer_rejects_blank_stub_field() -> None:
    with pytest.raises(ValidationError):
        StubConsumer(
            name="x",
            consumer_file="a.py",
            consumer_symbol="Thing",
            stub_field="",
            calculator_name="c",
        )


def test_stub_consumer_rejects_blank_calculator_name() -> None:
    with pytest.raises(ValidationError):
        StubConsumer(
            name="x",
            consumer_file="a.py",
            consumer_symbol="Thing",
            stub_field="k",
            calculator_name="",
        )


def test_stub_consumer_rejects_non_py_consumer_file() -> None:
    with pytest.raises(ValidationError):
        StubConsumer(
            name="x",
            consumer_file="a.txt",
            consumer_symbol="Thing",
            stub_field="k",
            calculator_name="c",
        )


def test_stub_consumer_is_frozen() -> None:
    stub = StubConsumer(
        name="x", consumer_file="a.py", consumer_symbol="Thing", stub_field="k", calculator_name="c"
    )
    with pytest.raises(ValidationError):
        stub.name = "changed"  # type: ignore[misc]


def test_validate_stub_calculators_resolve_passes_on_the_real_registry() -> None:
    """The real STUB_REGISTRY's calculator_name values all resolve -- proven
    already at import time by the module-level call; re-asserted here so a
    future regression fails a NAMED test, not just an import crash."""
    _validate_stub_calculators_resolve(CALCULATOR_REGISTRY, STUB_REGISTRY)


def test_validate_stub_calculators_resolve_rejects_a_stub_naming_an_unknown_calculator() -> None:
    calculators = (
        RegisteredCalculator(name="known", def_file="a.py", symbol="f", produces="Thing"),
    )
    stubs = (
        StubConsumer(
            name="x",
            consumer_file="a.py",
            consumer_symbol="Thing",
            stub_field="k",
            calculator_name="unknown_calculator",
        ),
    )
    with pytest.raises(ValueError, match="unknown calculator"):
        _validate_stub_calculators_resolve(calculators, stubs)


# ---------------------------------------------------------------------------
# Grounding + stub semantics (fixture files)
# ---------------------------------------------------------------------------


def _patch_repo_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Redirect the check module's ``_REPO_ROOT`` to ``tmp_path`` so a fixture
    row's ``consumer_file``/``def_file`` can be plain filenames resolved
    against the fixture tree, mirroring the gate-satisfaction test module's
    own ``_REPO_ROOT`` monkeypatch pattern."""
    monkeypatch.setattr("babylon.sentinels.seam_algebra.checks._REPO_ROOT", tmp_path)


def test_a_grounded_stub_with_a_real_calculator_reds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "calc.py", "def compute(a, b) -> Thing:\n    return Thing(k=a + b)\n")
    _write(tmp_path, "consumer.py", "value = Thing(k=True, other=1)\n")
    _patch_repo_root(monkeypatch, tmp_path)
    stub = StubConsumer(
        name="fixture_stub",
        consumer_file="consumer.py",
        consumer_symbol="Thing",
        stub_field="k",
        calculator_name="fixture_calc",
    )
    calc = RegisteredCalculator(
        name="fixture_calc", def_file="calc.py", symbol="compute", produces="Thing"
    )
    findings = check_stub_vs_calculator(stubs=(stub,), calculators=(calc,), exemptions=())
    assert len(findings) == 1
    assert "stub-vs-calculator" in findings[0]
    assert "Thing" in findings[0]
    assert "compute" in findings[0]


def test_an_exempted_stub_is_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(tmp_path, "calc.py", "def compute(a, b) -> Thing:\n    return Thing(k=a + b)\n")
    _write(tmp_path, "consumer.py", "value = Thing(k=True, other=1)\n")
    _patch_repo_root(monkeypatch, tmp_path)
    stub = StubConsumer(
        name="fixture_exempted_stub",
        consumer_file="consumer.py",
        consumer_symbol="Thing",
        stub_field="k",
        calculator_name="fixture_calc",
    )
    calc = RegisteredCalculator(
        name="fixture_calc", def_file="calc.py", symbol="compute", produces="Thing"
    )
    exemption = SentinelExemption(
        key=("stub", "fixture_exempted_stub"),
        reason="fixture exemption",
        owner="test",
        date="2026-07-21",
        tracking_task="#1",
    )
    findings = check_stub_vs_calculator(stubs=(stub,), calculators=(calc,), exemptions=(exemption,))
    assert findings == []


def test_a_stale_stub_call_site_raises_instead_of_reading_as_grounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A registry row citing a literal call that no longer exists in
    consumer_file is an infrastructure failure -- never a silent clean pass."""
    _write(tmp_path, "calc.py", "def compute(a, b) -> Thing:\n    return Thing(k=a + b)\n")
    _write(tmp_path, "consumer.py", "value = Thing(k=compute(1, 2))\n")
    _patch_repo_root(monkeypatch, tmp_path)
    stub = StubConsumer(
        name="fixture_stale_stub",
        consumer_file="consumer.py",
        consumer_symbol="Thing",
        stub_field="k",
        calculator_name="fixture_calc",
    )
    calc = RegisteredCalculator(
        name="fixture_calc", def_file="calc.py", symbol="compute", produces="Thing"
    )
    with pytest.raises(SentinelCheckError, match="registry row is stale"):
        check_stub_vs_calculator(stubs=(stub,), calculators=(calc,), exemptions=())


def test_a_stale_calculator_reference_raises_instead_of_reading_as_grounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A registry row citing a calculator function that has since been
    renamed/deleted is an infrastructure failure -- never a silent clean pass."""
    _write(tmp_path, "calc.py", "def renamed(a, b) -> Thing:\n    return Thing(k=a + b)\n")
    _write(tmp_path, "consumer.py", "value = Thing(k=True)\n")
    _patch_repo_root(monkeypatch, tmp_path)
    stub = StubConsumer(
        name="fixture_stub",
        consumer_file="consumer.py",
        consumer_symbol="Thing",
        stub_field="k",
        calculator_name="fixture_calc",
    )
    calc = RegisteredCalculator(
        name="fixture_calc", def_file="calc.py", symbol="compute", produces="Thing"
    )
    with pytest.raises(SentinelCheckError, match="registry row is stale"):
        check_stub_vs_calculator(stubs=(stub,), calculators=(calc,), exemptions=())


def test_a_calculator_returning_a_different_type_raises_instead_of_reading_as_grounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A registry row claiming ``produces="Thing"`` for a calculator that
    actually returns something else is a stale/ungrounded positive claim."""
    _write(
        tmp_path, "calc.py", "def compute(a, b) -> OtherThing:\n    return OtherThing(k=a + b)\n"
    )
    _write(tmp_path, "consumer.py", "value = Thing(k=True)\n")
    _patch_repo_root(monkeypatch, tmp_path)
    stub = StubConsumer(
        name="fixture_stub",
        consumer_file="consumer.py",
        consumer_symbol="Thing",
        stub_field="k",
        calculator_name="fixture_calc",
    )
    calc = RegisteredCalculator(
        name="fixture_calc", def_file="calc.py", symbol="compute", produces="Thing"
    )
    with pytest.raises(SentinelCheckError, match="registry row is stale"):
        check_stub_vs_calculator(stubs=(stub,), calculators=(calc,), exemptions=())


def test_stub_naming_an_unresolvable_calculator_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even though STUB_REGISTRY's own collection-time validator forbids this,
    the check function is defensive against a directly-injected fixture pair
    that skips it -- never trusts the caller."""
    _write(tmp_path, "consumer.py", "value = Thing(k=True)\n")
    _patch_repo_root(monkeypatch, tmp_path)
    stub = StubConsumer(
        name="fixture_stub",
        consumer_file="consumer.py",
        consumer_symbol="Thing",
        stub_field="k",
        calculator_name="does_not_exist",
    )
    with pytest.raises(SentinelCheckError, match="unknown calculator"):
        check_stub_vs_calculator(stubs=(stub,), calculators=(), exemptions=())


# ---------------------------------------------------------------------------
# Anti-false-positive heuristic: a computed keyword is never a stub
# ---------------------------------------------------------------------------


def test_a_variable_keyword_is_not_a_literal_stub(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Grounding itself fails (never a false-positive red) when the cited
    field is fed a NAME, not a bare constant -- the check cannot even ground
    the registry row against reality, so it raises loud rather than either
    silently passing or silently reporting a nonexistent stub."""
    _write(tmp_path, "calc.py", "def compute(a, b) -> Thing:\n    return Thing(k=a + b)\n")
    _write(tmp_path, "consumer.py", "real_value = compute(1, 2)\nvalue = Thing(k=real_value)\n")
    _patch_repo_root(monkeypatch, tmp_path)
    stub = StubConsumer(
        name="fixture_not_a_stub",
        consumer_file="consumer.py",
        consumer_symbol="Thing",
        stub_field="k",
        calculator_name="fixture_calc",
    )
    calc = RegisteredCalculator(
        name="fixture_calc", def_file="calc.py", symbol="compute", produces="Thing"
    )
    with pytest.raises(SentinelCheckError, match="registry row is stale"):
        check_stub_vs_calculator(stubs=(stub,), calculators=(calc,), exemptions=())


# ---------------------------------------------------------------------------
# Mutation efficacy — the two mutation tests the design names verbatim
# ---------------------------------------------------------------------------


def test_mutation_pointing_a_fixture_consumer_at_a_literal_reds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION (design §4 U5): 'point a fixture consumer at a literal where
    a registered calculator exists -> check reds'."""
    _write(
        tmp_path,
        "calc.py",
        "def check_condition(a, b) -> Verdict:\n    return Verdict(met=a == b)\n",
    )
    _write(tmp_path, "consumer.py", "verdict = Verdict(met=True, note='default')\n")
    _patch_repo_root(monkeypatch, tmp_path)
    stub = StubConsumer(
        name="mutation_witness",
        consumer_file="consumer.py",
        consumer_symbol="Verdict",
        stub_field="met",
        calculator_name="mutation_calc",
    )
    calc = RegisteredCalculator(
        name="mutation_calc", def_file="calc.py", symbol="check_condition", produces="Verdict"
    )
    findings = check_stub_vs_calculator(stubs=(stub,), calculators=(calc,), exemptions=())
    assert len(findings) == 1
    assert "stub-vs-calculator" in findings[0]
    assert "Verdict" in findings[0]
    assert "check_condition" in findings[0]


def test_retired_founding_stub_leaves_the_real_registry_vacuously_clean() -> None:
    """The founding ReproductionBalance stub was RETIRED at the v1-cascade
    merge (Vol II U3/ADR122 wired the real check_simple_reproduction call;
    the grounding check itself forced the retirement — a stale row is loud).
    The shipped registry is now empty, so the real run is clean even with
    ZERO exemptions — the mutation witness for the check's red path lives in
    test_a_grounded_stub_with_a_real_calculator_reds (synthetic fixture)."""
    assert check_stub_vs_calculator(exemptions=()) == []


def test_exemption_does_not_leak_across_unrelated_stub_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The kind-tagged exemption key (`("stub", name)`) must not clear a
    DIFFERENT stub sharing no name with the exempted row."""
    _write(tmp_path, "calc.py", "def compute(a, b) -> Thing:\n    return Thing(k=a + b)\n")
    _write(tmp_path, "consumer.py", "value = Thing(k=True, other=1)\n")
    _patch_repo_root(monkeypatch, tmp_path)
    stub = StubConsumer(
        name="unrelated_stub",
        consumer_file="consumer.py",
        consumer_symbol="Thing",
        stub_field="k",
        calculator_name="fixture_calc",
    )
    calc = RegisteredCalculator(
        name="fixture_calc", def_file="calc.py", symbol="compute", produces="Thing"
    )
    exemption = SentinelExemption(
        key=("stub", "some_other_stub_name"),
        reason="an exemption for a DIFFERENT stub row",
        owner="test",
        date="2026-07-21",
        tracking_task="#1",
    )
    findings = check_stub_vs_calculator(stubs=(stub,), calculators=(calc,), exemptions=(exemption,))
    assert len(findings) == 1
    assert "Thing" in findings[0]


# ---------------------------------------------------------------------------
# Liveness: the real, shipped registry against the current tree
# ---------------------------------------------------------------------------


def test_real_registry_is_clean_with_the_shipped_exemption() -> None:
    assert check_stub_vs_calculator() == []


def test_shipped_exemptions_are_empty_since_the_founding_stub_retired() -> None:
    """Both the stub row and its exemption retired together (v1-cascade
    merge): an exemption without a row would be a vacuous hold-open."""
    assert STUB_VS_CALCULATOR_EXEMPTIONS == ()


def test_repo_root_resolves_to_the_real_repository_root() -> None:
    for stub in STUB_REGISTRY:
        assert (_REPO_ROOT / stub.consumer_file).is_file(), stub.consumer_file
    for calc in CALCULATOR_REGISTRY:
        assert (_REPO_ROOT / calc.def_file).is_file(), calc.def_file


# ---------------------------------------------------------------------------
# run_sensor exit-code contract — through main(), not direct calls
# ---------------------------------------------------------------------------


def test_check_stub_vs_calculator_is_registered_in_gating_checks() -> None:
    """WIRING: the check function sits in the tuple ``main()`` actually
    iterates -- a deleted or mistyped ``_GATING_CHECKS`` entry must fail this
    test even though the direct-call tests above stay green."""
    wired_checks = [check for _, check in checks_module._GATING_CHECKS]
    assert check_stub_vs_calculator in wired_checks


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def test_cli_entry_point_is_still_clean_with_stub_vs_calculator_wired() -> None:
    """``sentinel_check.py seam-algebra --check`` exits 0 with ALL THREE
    gating checks (disconnected-subsystem + gate-satisfaction +
    stub-vs-calculator) now wired."""
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, trusted path
        [sys.executable, str(_TOOL_PATH), "seam-algebra", "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "SEAM-ALGEBRA sensor reds against the shipped registry:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "Seam-algebra clean" in result.stdout
    assert "stub-vs-calculator site(s)" in result.stdout
