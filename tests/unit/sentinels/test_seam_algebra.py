"""Tests for the seam-algebra sentinel (T1.1 Unit 3): static Lawvere ∂L.

Four tiers:

- **Registry shape teeth** — malformed :class:`ConstructNode`/
  :class:`ExpectedConsumer` rows fail loudly at construction (Constitution
  III.11), and an :class:`ExpectedConsumer` naming an unknown construct is
  rejected at collection time.
- **Closure semantics** (fixture graphs) — :func:`build_live_set` is a real
  transitive fixed-point closure, not a one-hop membership test: deleting the
  bridge edge disconnects everything downstream of it too.
- **Mutation efficacy** — the two literal mutation tests the design names:
  (1) a declared construct whose only production edge is deleted in a fixture
  graph reds; (2) reverting F-EC-1's exemption reds the REAL shipped registry.
- **Liveness + CLI wiring** — the real, shipped registry is clean (with the
  one dated exemption), and the family dispatches through the CLI.
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
from babylon.sentinels.seam_algebra.checks import (
    _REPO_ROOT,
    build_live_set,
    check_disconnected_subsystems,
)
from babylon.sentinels.seam_algebra.registry import (
    CONSTRUCT_REGISTRY,
    EDGE_REGISTRY,
    ORIGIN_FAMILIES,
    PRODUCTION_ENTRY_POINTS,
    SEAM_ALGEBRA_EXEMPTIONS,
    ConstructNode,
    ExpectedConsumer,
    _validate_edges_resolve,
)

pytestmark = pytest.mark.unit

_TOOL_PATH = Path(__file__).resolve().parents[3] / "tools" / "sentinel_check.py"

# ---------------------------------------------------------------------------
# Registry shape teeth
# ---------------------------------------------------------------------------


def test_construct_node_rejects_blank_name() -> None:
    with pytest.raises(ValidationError):
        ConstructNode(
            name="",
            def_file="a.py",
            symbol="Thing",
            origin_family="native",
            material_relation="z",
        )


def test_construct_node_rejects_blank_symbol() -> None:
    with pytest.raises(ValidationError):
        ConstructNode(
            name="x",
            def_file="a.py",
            symbol="",
            origin_family="native",
            material_relation="z",
        )


def test_construct_node_rejects_blank_material_relation() -> None:
    with pytest.raises(ValidationError):
        ConstructNode(
            name="x", def_file="a.py", symbol="Thing", origin_family="native", material_relation=""
        )


def test_construct_node_rejects_non_py_def_file() -> None:
    with pytest.raises(ValidationError):
        ConstructNode(
            name="x",
            def_file="a.txt",
            symbol="Thing",
            origin_family="native",
            material_relation="z",
        )


def test_construct_node_rejects_unknown_origin_family() -> None:
    with pytest.raises(ValidationError):
        ConstructNode(
            name="x",
            def_file="a.py",
            symbol="Thing",
            origin_family="not_a_real_family",
            material_relation="z",
        )


def test_construct_node_accepts_every_declared_origin_family() -> None:
    """Positive control: each of the six legacy families plus 'native' is a
    valid tag, not just whatever happens to be seeded today."""
    for family in ORIGIN_FAMILIES:
        ConstructNode(
            name=f"probe_{family}",
            def_file="a.py",
            symbol="Thing",
            origin_family=family,
            material_relation="z",
        )


def test_construct_node_is_frozen() -> None:
    node = ConstructNode(
        name="x", def_file="a.py", symbol="Thing", origin_family="native", material_relation="z"
    )
    with pytest.raises(ValidationError):
        node.name = "changed"  # type: ignore[misc]


def test_expected_consumer_rejects_blank_construct_name() -> None:
    with pytest.raises(ValidationError):
        ExpectedConsumer(construct_name="", consumer_file="a.py", edge_kind="call")


def test_expected_consumer_rejects_non_py_consumer_file() -> None:
    with pytest.raises(ValidationError):
        ExpectedConsumer(construct_name="x", consumer_file="a.txt", edge_kind="call")


def test_expected_consumer_rejects_unknown_edge_kind() -> None:
    with pytest.raises(ValidationError):
        ExpectedConsumer(construct_name="x", consumer_file="a.py", edge_kind="teleport")


@pytest.mark.parametrize("edge_kind", ["read", "call", "import", "publish"])
def test_expected_consumer_accepts_every_declared_edge_kind(edge_kind: str) -> None:
    ExpectedConsumer(construct_name="x", consumer_file="a.py", edge_kind=edge_kind)


def test_expected_consumer_is_frozen() -> None:
    edge = ExpectedConsumer(construct_name="x", consumer_file="a.py", edge_kind="call")
    with pytest.raises(ValidationError):
        edge.edge_kind = "read"  # type: ignore[misc]


def test_validate_edges_resolve_passes_on_the_real_registry() -> None:
    """The real EDGE_REGISTRY's construct_name values all resolve -- proven
    already at import time by the module-level call; re-asserted here so a
    future regression fails a NAMED test, not just an import crash."""
    _validate_edges_resolve(CONSTRUCT_REGISTRY, EDGE_REGISTRY)


def test_validate_edges_resolve_rejects_an_edge_naming_an_unknown_construct() -> None:
    constructs = (
        ConstructNode(
            name="known",
            def_file="a.py",
            symbol="Thing",
            origin_family="native",
            material_relation="z",
        ),
    )
    edges = (
        ExpectedConsumer(
            construct_name="unknown_construct", consumer_file="a.py", edge_kind="call"
        ),
    )
    with pytest.raises(ValueError, match="unknown construct"):
        _validate_edges_resolve(constructs, edges)


# ---------------------------------------------------------------------------
# Closure semantics: build_live_set is real transitive reachability
# ---------------------------------------------------------------------------


def test_build_live_set_finds_the_real_two_hop_chain() -> None:
    """The shipped registry's one real chain: simulation_engine.py (entry) ->
    consciousness_system (import) -> reification_buffer_producer (call)."""
    live = build_live_set()
    assert live == frozenset({"consciousness_system", "reification_buffer_producer"})


def test_f_ec_1_is_not_in_the_live_set() -> None:
    """anisotropic_observation_error has NO edge -- it can never be live."""
    assert "anisotropic_observation_error" not in build_live_set()


def test_transitivity_is_load_bearing() -> None:
    """Deleting consciousness_system's OWN edge severs the chain: ideology.py
    never joins live_files, so reification_buffer_producer -- whose edge
    targets ideology.py, not an entry point directly -- goes disconnected
    too. Proves build_live_set does real transitive closure, not a check of
    each construct's edge against the literal PRODUCTION_ENTRY_POINTS set."""
    edges_without_bridge = tuple(
        edge for edge in EDGE_REGISTRY if edge.construct_name != "consciousness_system"
    )
    live = build_live_set(edges=edges_without_bridge)
    assert "consciousness_system" not in live
    assert "reification_buffer_producer" not in live


def test_build_live_set_raises_on_missing_consumer_file() -> None:
    """A live entry-point file that does not exist is an infrastructure
    failure the moment something actually tries to read it -- never a silent
    empty result."""
    fixture_constructs = (
        ConstructNode(
            name="fixture",
            def_file="src/babylon/formulas/consciousness_routing.py",
            symbol="whatever_zzz",
            origin_family="native",
            material_relation="fixture for the infra-failure proof",
        ),
    )
    missing_file = "src/babylon/engine/this_file_does_not_exist_zzz.py"
    fixture_edges = (
        ExpectedConsumer(construct_name="fixture", consumer_file=missing_file, edge_kind="call"),
    )
    with pytest.raises(SentinelCheckError):
        build_live_set(
            constructs=fixture_constructs,
            edges=fixture_edges,
            entry_points=(missing_file,),
        )


# ---------------------------------------------------------------------------
# Mutation efficacy — the two mutation tests the design names verbatim
# ---------------------------------------------------------------------------


def test_mutation_deleting_a_constructs_only_edge_disconnects_it() -> None:
    """MUTATION (design §4 U3): 'add a declared construct whose only
    production edge is deleted in a fixture graph (nonempty core severed
    from L) -> assert dL reports it disconnected (red)'."""
    fixture_constructs = (
        ConstructNode(
            name="fixture_construct",
            def_file="src/babylon/formulas/consciousness_routing.py",
            symbol="compute_reification_buffer",
            origin_family="native",
            material_relation="fixture for the mutation proof",
        ),
    )
    entry_points = ("src/babylon/engine/systems/ideology.py",)
    connected_edges = (
        ExpectedConsumer(
            construct_name="fixture_construct",
            consumer_file="src/babylon/engine/systems/ideology.py",
            edge_kind="call",
        ),
    )
    # BEFORE the mutation: the edge is real and verifiable -- clean.
    assert (
        check_disconnected_subsystems(
            constructs=fixture_constructs,
            edges=connected_edges,
            entry_points=entry_points,
            exemptions=(),
        )
        == []
    )
    # MUTATION: delete the construct's only production edge.
    findings = check_disconnected_subsystems(
        constructs=fixture_constructs,
        edges=(),
        entry_points=entry_points,
        exemptions=(),
    )
    assert len(findings) == 1
    assert "disconnected-subsystem" in findings[0]
    assert "fixture_construct" in findings[0]
    assert "compute_reification_buffer" in findings[0]


def test_mutation_reverting_f_ec_1_exemption_reds_the_real_registry() -> None:
    """MUTATION (design §4 U3): 'revert F-EC-1's disposition -> assert the
    real run reds.' Proves the exemption is load-bearing, not vacuous: with
    it removed, the REAL shipped CONSTRUCT_REGISTRY/EDGE_REGISTRY must red on
    exactly anisotropic_observation_error and nothing else."""
    findings = check_disconnected_subsystems(exemptions=())
    assert len(findings) == 1
    assert "disconnected-subsystem" in findings[0]
    assert "anisotropic_observation_error" in findings[0]


def test_exemption_does_not_leak_across_unrelated_construct_names() -> None:
    """The kind-tagged exemption key (`("construct", name)`) must not clear a
    DIFFERENT disconnected construct sharing no name with the exempted row."""
    fixture_constructs = (
        ConstructNode(
            name="unrelated_disconnected",
            def_file="src/babylon/formulas/consciousness_routing.py",
            symbol="this_symbol_has_no_edge_zzz",
            origin_family="native",
            material_relation="fixture for the exemption-scoping proof",
        ),
    )
    exemption = SentinelExemption(
        key=("construct", "anisotropic_observation_error"),
        reason="an exemption for a DIFFERENT construct",
        owner="test",
        date="2026-07-21",
        tracking_task="#1",
    )
    findings = check_disconnected_subsystems(
        constructs=fixture_constructs,
        edges=(),
        entry_points=PRODUCTION_ENTRY_POINTS,
        exemptions=(exemption,),
    )
    assert len(findings) == 1
    assert "unrelated_disconnected" in findings[0]


# ---------------------------------------------------------------------------
# Liveness: the real, shipped registry against the current tree
# ---------------------------------------------------------------------------


def test_real_registry_is_clean_with_the_shipped_exemption() -> None:
    assert check_disconnected_subsystems() == []


def test_shipped_exemptions_hold_exactly_f_ec_1() -> None:
    keys = {exemption.key for exemption in SEAM_ALGEBRA_EXEMPTIONS}
    assert keys == {("construct", "anisotropic_observation_error")}


def test_repo_root_resolves_to_the_real_repository_root() -> None:
    """Sanity: _REPO_ROOT must actually point at a checkout containing the
    entry-point files the shipped registry names."""
    for entry_point in PRODUCTION_ENTRY_POINTS:
        assert (_REPO_ROOT / entry_point).is_file(), entry_point


# ---------------------------------------------------------------------------
# run_sensor exit-code contract (0/1/2) — through main(), not direct calls
# ---------------------------------------------------------------------------


def test_check_disconnected_subsystems_is_registered_in_gating_checks() -> None:
    """WIRING: the check function sits in the tuple ``main()`` actually iterates
    -- a deleted or mistyped ``_GATING_CHECKS`` entry must fail this test even
    though the check function and its direct-call tests above stay green."""
    wired_checks = [check for _, check in checks_module._GATING_CHECKS]
    assert check_disconnected_subsystems in wired_checks


def test_main_reds_through_run_sensor_when_a_violation_is_wired(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit-code contract, tier 1: ``main() -> run_sensor -> _GATING_CHECKS``
    actually returns 1 and prints the finding to stderr when a violation
    exists -- the invocation proof the direct-call tests above cannot give:
    they call ``check_disconnected_subsystems`` themselves and would stay
    green even if the sensor's own dispatch to it were severed."""

    def stub_check() -> list[str]:
        return ["[disconnected-subsystem] PhantomThing @ a.py — wiring proof | REMEDY: n/a"]

    monkeypatch.setattr(checks_module, "_GATING_CHECKS", (("disconnected-subsystem", stub_check),))
    exit_code = checks_module.main([])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "[disconnected-subsystem] PhantomThing" in captured.err


def test_main_exits_two_on_infrastructure_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit-code contract, tier 2: a ``SentinelCheckError`` raised inside a
    gating check is an infrastructure failure (exit 2) -- never swallowed
    into a false pass."""

    def stub_check() -> list[str]:
        raise SentinelCheckError("synthetic infra failure for the contract proof")

    monkeypatch.setattr(checks_module, "_GATING_CHECKS", (("disconnected-subsystem", stub_check),))
    exit_code = checks_module.main([])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "SEAM-ALGEBRA ERROR" in captured.err


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def test_cli_entry_point_is_clean() -> None:
    """``sentinel_check.py seam-algebra --check`` exits 0 today, mirroring
    every sibling family's own CLI-wiring test."""
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


def test_cli_rejects_unknown_sensor_name() -> None:
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, trusted path
        [sys.executable, str(_TOOL_PATH), "no_such_sensor_zzz"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "invalid choice" in result.stderr
