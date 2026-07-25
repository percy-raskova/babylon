"""Tests for the seam-algebra gate-satisfaction check (T1.1 Unit 4).

Four tiers, mirroring ``test_seam_algebra.py``'s own shape:

- **Registry shape teeth** — a malformed :class:`GatedInput` row fails loudly
  at construction (Constitution III.11).
- **Grounding + supply semantics** (fixture files) — :func:`check_gate_satisfaction`
  distinguishes a genuinely-satisfied gate (declared ``supplier_files`` really
  reference ``gated_input``) from an unsatisfied one (empty ``supplier_files``,
  or none of them reference it), and treats a stale registry row (the guard
  or the declared supplier no longer matches reality) as an infrastructure
  failure, never a silent pass.
- **Mutation efficacy** — the two literal mutation tests the design names
  verbatim (§4 U4): (1) a fixture ``if services.foo is None: return`` guard
  with no declared supplier reds; (2) reverting F-1/F-2's exemptions reds the
  REAL shipped registry.
- **Liveness + CLI wiring** — the real, shipped registry is clean (with the
  three dated F-1/F-2 exemptions), and the family's CLI dispatch still exits 0.
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
from babylon.sentinels.seam_algebra.checks import _REPO_ROOT, check_gate_satisfaction
from babylon.sentinels.seam_algebra.registry import (
    GATE_REGISTRY,
    GATE_SATISFACTION_EXEMPTIONS,
    GUARD_SHAPES,
    GatedInput,
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


def test_gated_input_rejects_blank_name() -> None:
    with pytest.raises(ValidationError):
        GatedInput(name="", guard_file="a.py", guard_shape="context_get", gated_input="k")


def test_gated_input_rejects_blank_gated_input() -> None:
    with pytest.raises(ValidationError):
        GatedInput(name="x", guard_file="a.py", guard_shape="context_get", gated_input="")


def test_gated_input_rejects_non_py_guard_file() -> None:
    with pytest.raises(ValidationError):
        GatedInput(name="x", guard_file="a.txt", guard_shape="context_get", gated_input="k")


def test_gated_input_rejects_unknown_guard_shape() -> None:
    with pytest.raises(ValidationError):
        GatedInput(name="x", guard_file="a.py", guard_shape="teleport", gated_input="k")


def test_gated_input_rejects_non_py_supplier_file() -> None:
    with pytest.raises(ValidationError):
        GatedInput(
            name="x",
            guard_file="a.py",
            guard_shape="context_get",
            gated_input="k",
            supplier_files=("a.txt",),
        )


@pytest.mark.parametrize("shape", sorted(GUARD_SHAPES))
def test_gated_input_accepts_every_declared_guard_shape(shape: str) -> None:
    """Positive control: each declared shape is valid, not just whatever
    happens to be seeded today."""
    GatedInput(name=f"probe_{shape}", guard_file="a.py", guard_shape=shape, gated_input="k")


def test_gated_input_is_frozen() -> None:
    gate = GatedInput(name="x", guard_file="a.py", guard_shape="context_get", gated_input="k")
    with pytest.raises(ValidationError):
        gate.name = "changed"  # type: ignore[misc]


def test_gated_input_defaults_to_no_supplier_files() -> None:
    gate = GatedInput(name="x", guard_file="a.py", guard_shape="context_get", gated_input="k")
    assert gate.supplier_files == ()


# ---------------------------------------------------------------------------
# Grounding + supply semantics (fixture files)
# ---------------------------------------------------------------------------


def _patch_repo_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Redirect the check module's ``_REPO_ROOT`` to ``tmp_path`` so a
    ``GatedInput`` row's ``guard_file``/``supplier_files`` can be plain
    filenames resolved against the fixture tree, mirroring
    ``test_defines_passthrough.py``'s own ``_REPO_ROOT`` monkeypatch pattern."""
    monkeypatch.setattr("babylon.sentinels.seam_algebra.checks._REPO_ROOT", tmp_path)


def test_a_satisfied_gate_with_a_real_supplier_is_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "guard.py", "def f(services):\n    if services.foo is None:\n        return\n")
    _write(tmp_path, "supplier.py", "make(foo=real_foo)\n")
    _patch_repo_root(monkeypatch, tmp_path)
    gate = GatedInput(
        name="fixture_satisfied",
        guard_file="guard.py",
        guard_shape="services_attr_none",
        gated_input="foo",
        supplier_files=("supplier.py",),
    )
    assert check_gate_satisfaction(gates=(gate,), exemptions=()) == []


def test_an_unsatisfied_gate_with_no_supplier_reds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "guard.py", "def f(services):\n    if services.foo is None:\n        return\n")
    _patch_repo_root(monkeypatch, tmp_path)
    gate = GatedInput(
        name="fixture_unsatisfied",
        guard_file="guard.py",
        guard_shape="services_attr_none",
        gated_input="foo",
        supplier_files=(),
    )
    findings = check_gate_satisfaction(gates=(gate,), exemptions=())
    assert len(findings) == 1
    assert "gate-blindness" in findings[0]
    assert "foo" in findings[0]


def test_an_exempted_unsatisfied_gate_is_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "guard.py", "def f(services):\n    if services.foo is None:\n        return\n")
    _patch_repo_root(monkeypatch, tmp_path)
    gate = GatedInput(
        name="fixture_exempted",
        guard_file="guard.py",
        guard_shape="services_attr_none",
        gated_input="foo",
        supplier_files=(),
    )
    exemption = SentinelExemption(
        key=("gate", "fixture_exempted"),
        reason="fixture exemption",
        owner="test",
        date="2026-07-21",
        tracking_task="#1",
    )
    assert check_gate_satisfaction(gates=(gate,), exemptions=(exemption,)) == []


def test_a_stale_guard_raises_instead_of_reading_as_satisfied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A registry row citing a guard that no longer exists in guard_file is
    an infrastructure failure -- never a silent clean pass."""
    _write(tmp_path, "guard.py", "def f(services):\n    return 1\n")
    _patch_repo_root(monkeypatch, tmp_path)
    gate = GatedInput(
        name="fixture_stale_guard",
        guard_file="guard.py",
        guard_shape="services_attr_none",
        gated_input="foo",
        supplier_files=(),
    )
    with pytest.raises(SentinelCheckError, match="registry row is stale"):
        check_gate_satisfaction(gates=(gate,), exemptions=())


def test_a_stale_supplier_claim_raises_instead_of_reading_as_satisfied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A declared supplier_files entry that does NOT actually reference
    gated_input is an ungrounded positive claim -- infrastructure failure,
    never a silent clean pass."""
    _write(tmp_path, "guard.py", "def f(services):\n    if services.foo is None:\n        return\n")
    _write(tmp_path, "supplier.py", "make(bar=real_bar)\n")
    _patch_repo_root(monkeypatch, tmp_path)
    gate = GatedInput(
        name="fixture_stale_supplier",
        guard_file="guard.py",
        guard_shape="services_attr_none",
        gated_input="foo",
        supplier_files=("supplier.py",),
    )
    with pytest.raises(SentinelCheckError, match="do not reference"):
        check_gate_satisfaction(gates=(gate,), exemptions=())


def test_context_get_shape_is_grounded_correctly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "guard.py", 'def f(context):\n    return context.get("vol2_step")\n')
    _patch_repo_root(monkeypatch, tmp_path)
    gate = GatedInput(
        name="fixture_context_get",
        guard_file="guard.py",
        guard_shape="context_get",
        gated_input="vol2_step",
        supplier_files=(),
    )
    findings = check_gate_satisfaction(gates=(gate,), exemptions=())
    assert len(findings) == 1


def test_context_hasattr_shape_is_grounded_correctly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        tmp_path,
        "guard.py",
        'def f(context):\n    return context.x if hasattr(context, "session_id") else None\n',
    )
    _patch_repo_root(monkeypatch, tmp_path)
    gate = GatedInput(
        name="fixture_context_hasattr",
        guard_file="guard.py",
        guard_shape="context_hasattr",
        gated_input="session_id",
        supplier_files=(),
    )
    findings = check_gate_satisfaction(gates=(gate,), exemptions=())
    assert len(findings) == 1


# ---------------------------------------------------------------------------
# Mutation efficacy — the two mutation tests the design names verbatim
# ---------------------------------------------------------------------------


def test_mutation_injecting_an_unsupplied_services_none_guard_reds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION (design §4 U4): 'inject a fixture `if services.foo is None:
    return` with no production supplier -> check reds'."""
    _write(
        tmp_path,
        "guard.py",
        "def step(self, graph, services, context):\n    if services.foo is None:\n        return\n",
    )
    _patch_repo_root(monkeypatch, tmp_path)
    gate = GatedInput(
        name="mutation_witness",
        guard_file="guard.py",
        guard_shape="services_attr_none",
        gated_input="foo",
        supplier_files=(),
    )
    findings = check_gate_satisfaction(gates=(gate,), exemptions=())
    assert len(findings) == 1
    assert "gate-blindness" in findings[0]
    assert "mutation_witness" in findings[0]
    assert "foo" in findings[0]


def test_mutation_removing_f2_exemption_reds_the_real_registry() -> None:
    """MUTATION (design §4 U4): 'remove F-2's exemption row -> real run reds.'

    With ALL exemptions removed, the REAL shipped GATE_REGISTRY must red on
    exactly the three F-1/F-2 witnesses -- and NOT on the melt_calculator
    positive control, which is genuinely, unconditionally wired.
    """
    findings = check_gate_satisfaction(exemptions=())
    assert len(findings) == 3
    joined = "\n".join(findings)
    assert "session_id" in joined
    assert "distribution_calculator" in joined
    assert "vol2_step" in joined
    assert "melt_calculator" not in joined


def test_removing_only_the_f2_distribution_calculator_exemption_reds_just_that_one() -> None:
    """Narrower form of the same mutation: dropping ONE exemption row reds
    exactly that gate, proving the exemptions are independently load-bearing."""
    remaining = tuple(
        exemption
        for exemption in GATE_SATISFACTION_EXEMPTIONS
        if exemption.key != ("gate", "financial_layer_distribution_calculator")
    )
    assert len(remaining) == len(GATE_SATISFACTION_EXEMPTIONS) - 1
    findings = check_gate_satisfaction(exemptions=remaining)
    assert len(findings) == 1
    assert "distribution_calculator" in findings[0]


def test_exemption_does_not_leak_across_unrelated_gate_names() -> None:
    """The kind-tagged exemption key (`("gate", name)`) must not clear a
    DIFFERENT unsatisfied gate sharing no name with the exempted row."""
    guard_file_a = "src/babylon/domain/economics/tick/system/__init__.py"
    gate = GatedInput(
        name="unrelated_unsatisfied",
        guard_file=guard_file_a,
        guard_shape="services_attr_none",
        gated_input="melt_calculator",
        supplier_files=(),  # deliberately NOT the real supplier -- fixture only
    )
    exemption = SentinelExemption(
        key=("gate", "financial_layer_distribution_calculator"),
        reason="an exemption for a DIFFERENT gate",
        owner="test",
        date="2026-07-21",
        tracking_task="#1",
    )
    findings = check_gate_satisfaction(gates=(gate,), exemptions=(exemption,))
    assert len(findings) == 1
    assert "unrelated_unsatisfied" in findings[0]
    assert "melt_calculator" in findings[0]


# ---------------------------------------------------------------------------
# Liveness: the real, shipped registry against the current tree
# ---------------------------------------------------------------------------


def test_real_registry_is_clean_with_the_shipped_exemptions() -> None:
    assert check_gate_satisfaction() == []


def test_shipped_exemptions_hold_exactly_f1_and_f2() -> None:
    keys = {exemption.key for exemption in GATE_SATISFACTION_EXEMPTIONS}
    assert keys == {
        ("gate", "run_audit_session_id"),
        ("gate", "financial_layer_distribution_calculator"),
        ("gate", "vol2_circulation_vol2_step"),
    }


def test_the_positive_control_gate_needs_no_exemption() -> None:
    """tick_dynamics_melt_calculator is genuinely, unconditionally wired --
    proves the check recognizes a satisfied gate, not just a red-everything
    scanner."""
    melt_gate = next(gate for gate in GATE_REGISTRY if gate.name == "tick_dynamics_melt_calculator")
    assert check_gate_satisfaction(gates=(melt_gate,), exemptions=()) == []


def test_repo_root_resolves_to_the_real_repository_root() -> None:
    for gate in GATE_REGISTRY:
        assert (_REPO_ROOT / gate.guard_file).is_file(), gate.guard_file
        for supplier_file in gate.supplier_files:
            assert (_REPO_ROOT / supplier_file).is_file(), supplier_file


# ---------------------------------------------------------------------------
# run_sensor exit-code contract — through main(), not direct calls
# ---------------------------------------------------------------------------


def test_check_gate_satisfaction_is_registered_in_gating_checks() -> None:
    """WIRING: the check function sits in the tuple ``main()`` actually
    iterates -- a deleted or mistyped ``_GATING_CHECKS`` entry must fail this
    test even though the direct-call tests above stay green."""
    wired_checks = [check for _, check in checks_module._GATING_CHECKS]
    assert check_gate_satisfaction in wired_checks


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def test_cli_entry_point_is_still_clean_with_gate_satisfaction_wired() -> None:
    """``sentinel_check.py seam-algebra --check`` exits 0 with BOTH gating
    checks (disconnected-subsystem + gate-satisfaction) now wired."""
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
