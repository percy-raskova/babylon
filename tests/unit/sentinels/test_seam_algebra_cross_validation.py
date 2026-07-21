"""Cross-validation: the unified ∂L loses no coverage against its six legacy families.

T1.1 Unit 3 acceptance (design §4 U3): *"re-express >= 1 known construct per
family and prove the unified dL catches the same mutation each family already
catches (unification loses no coverage)."*

Each test below builds a small, SELF-CONTAINED fixture graph — real
``def_file``/``symbol``/``consumer_file`` values copied from that family's own
production registry (never a fictitious path) — with its own local
``entry_points`` (so the fixture does not need to chain into the family's real
:data:`~babylon.sentinels.seam_algebra.registry.PRODUCTION_ENTRY_POINTS`; that
transitivity is already proven for the ``inert`` family by the SHIPPED
registry itself, see ``test_seam_algebra.py::
test_build_live_set_finds_the_real_two_hop_chain``). Then it applies the SAME
kind of mutation that family's own efficacy test applies (swap the referenced
symbol for one verified absent from the real file, or delete the edge
entirely) and proves :func:`~babylon.sentinels.seam_algebra.checks.
check_disconnected_subsystems` reds on it too.

One family per test, named for the legacy sentinel it re-expresses:

- **inert** — re-uses the SHIPPED ``reification_buffer_producer`` construct
  directly (already proven live in ``test_seam_algebra.py``); this module
  proves ITS mutation instead (severing its edge), completing the six.
- **unconsumed** — ``reification_buffer``'s dict-key write (``ideology.py``)
  genuinely has NO production reader anywhere (the real, currently-exempted
  gap) — proven both ways: disconnected against a real file that does not
  mention it, and connected against one that does (sensitivity, not just a
  permanent red).
- **coupling** — the ``price_value`` opposition's ``market_balance`` symbol,
  produced by ``contradiction.py`` and read by ``domain/dialectics/instances/
  catalog.py``.
- **liveness** — ``price_divergence``, produced by ``market_scissors.py`` and
  read by ``web/game/engine_bridge.py``.
- **vocabulary** — ``NodeType.TERRITORY``, queried by
  ``engine/systems/territory.py``.
- **dangling** — ``persist_action_results``, the (already-fixed) founding
  specimen: ``protocols.py``'s real member, called from
  ``web/game/engine_bridge.py``; the MUTATION re-creates the historical bug
  (the SINGULAR ``persist_action_result``, verified absent as an exact name
  from the real file — it survives only as a substring inside an unrelated
  docstring, which does not count, see :func:`~babylon.sentinels._ast.
  referenced_names`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.sentinels.seam_algebra.checks import check_disconnected_subsystems
from babylon.sentinels.seam_algebra.registry import (
    CONSTRUCT_REGISTRY,
    EDGE_REGISTRY,
    ConstructNode,
    ExpectedConsumer,
)

pytestmark = pytest.mark.unit


def _only_finding(findings: list[str]) -> str:
    assert len(findings) == 1, findings
    return findings[0]


# ---------------------------------------------------------------------------
# inert — completes the six by mutating the SHIPPED construct's own edge
# ---------------------------------------------------------------------------


def test_inert_reification_buffer_producer_reds_when_its_edge_is_severed() -> None:
    """The inert family's founding case (`compute_reification_buffer`, real
    caller `ideology.py`) is already proven LIVE via the shipped registry
    (test_seam_algebra.py). Here: delete just its edge (mirrors inert's own
    efficacy test, which points a DeclaredProducer at a symbol with zero
    real references) and prove the unified check reds on it alone."""
    constructs = tuple(c for c in CONSTRUCT_REGISTRY if c.name == "reification_buffer_producer")
    edges_without_it = tuple(
        e for e in EDGE_REGISTRY if e.construct_name != "reification_buffer_producer"
    )
    findings = check_disconnected_subsystems(
        constructs=constructs,
        edges=edges_without_it,
        entry_points=("src/babylon/engine/systems/ideology.py",),
        exemptions=(),
    )
    finding = _only_finding(findings)
    assert "reification_buffer_producer" in finding
    assert "compute_reification_buffer" in finding


# ---------------------------------------------------------------------------
# unconsumed — reification_buffer's dict-key write has NO real reader
# ---------------------------------------------------------------------------


def test_unconsumed_reification_buffer_value_matches_its_real_disconnected_state() -> None:
    """The unconsumed family's own founding (and only, currently-exempted)
    row: `reification_buffer` is written every tick by `ideology.py` but read
    back by NOTHING in src/ or web/ -- the exact gap
    `babylon.sentinels.unconsumed.registry.UNCONSUMED_EXEMPTIONS` holds open.
    A real, unrelated production file (`territory.py`, verified to contain
    no mention of the string) reproduces that same disconnected verdict."""
    construct = ConstructNode(
        name="reification_buffer_value",
        def_file="src/babylon/engine/systems/ideology.py",
        symbol="reification_buffer",
        origin_family="unconsumed",
        material_relation=(
            "Re-expresses babylon.sentinels.unconsumed.registry."
            "DECLARED_COMPUTED_FIELDS's 'reification_buffer' row."
        ),
    )
    edge = ExpectedConsumer(
        construct_name="reification_buffer_value",
        consumer_file="src/babylon/engine/systems/territory.py",
        edge_kind="read",
    )
    findings = check_disconnected_subsystems(
        constructs=(construct,),
        edges=(edge,),
        entry_points=("src/babylon/engine/systems/territory.py",),
        exemptions=(),
    )
    finding = _only_finding(findings)
    assert "reification_buffer_value" in finding
    assert "reification_buffer" in finding


def test_unconsumed_check_is_sensitive_when_a_real_reader_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sensitivity control: the SAME construct against a file that DOES
    mention the key is connected -- proving the disconnected verdict above is
    a real read of the tree, not a check that is always red."""
    reader_file = tmp_path / "synthetic_reader.py"
    reader_file.write_text('value = record["reification_buffer"]\n', encoding="utf-8")

    construct = ConstructNode(
        name="reification_buffer_value",
        def_file="src/babylon/engine/systems/ideology.py",
        symbol="reification_buffer",
        origin_family="unconsumed",
        material_relation="fixture positive control",
    )
    edge = ExpectedConsumer(
        construct_name="reification_buffer_value",
        consumer_file="synthetic_reader.py",
        edge_kind="read",
    )
    monkeypatch.setattr("babylon.sentinels.seam_algebra.checks._REPO_ROOT", tmp_path)
    findings = check_disconnected_subsystems(
        constructs=(construct,),
        edges=(edge,),
        entry_points=("synthetic_reader.py",),
        exemptions=(),
    )
    assert findings == []


# ---------------------------------------------------------------------------
# coupling — price_value's market_balance (contradiction.py -> catalog.py)
# ---------------------------------------------------------------------------


def test_coupling_market_balance_is_connected_then_reds_when_symbol_is_swapped() -> None:
    """Re-expresses babylon.sentinels.coupling.registry's `price_value` row
    (`market_balance`, producer `contradiction.py`, read by
    `domain/dialectics/instances/catalog.py`). Mirrors the coupling family's
    own `check_declared_edges_are_grounded` mutation shape: point the edge at
    a symbol with zero real references in the target file."""
    consumer_file = "src/babylon/domain/dialectics/instances/catalog.py"
    connected = ConstructNode(
        name="price_value_market_balance",
        def_file="src/babylon/engine/systems/contradiction.py",
        symbol="market_balance",
        origin_family="coupling",
        material_relation="Re-expresses coupling.registry's price_value row.",
    )
    connected_edge = ExpectedConsumer(
        construct_name="price_value_market_balance", consumer_file=consumer_file, edge_kind="read"
    )
    assert (
        check_disconnected_subsystems(
            constructs=(connected,),
            edges=(connected_edge,),
            entry_points=(consumer_file,),
            exemptions=(),
        )
        == []
    )

    # MUTATION: swap the symbol for one verified absent from catalog.py.
    mutated = connected.model_copy(update={"symbol": "market_balance_phantom_zzz"})
    findings = check_disconnected_subsystems(
        constructs=(mutated,),
        edges=(connected_edge,),
        entry_points=(consumer_file,),
        exemptions=(),
    )
    finding = _only_finding(findings)
    assert "market_balance_phantom_zzz" in finding


# ---------------------------------------------------------------------------
# liveness — price_divergence (market_scissors.py -> web/game/engine_bridge.py)
# ---------------------------------------------------------------------------


def test_liveness_price_divergence_is_connected_then_reds_when_edge_is_deleted() -> None:
    """Re-expresses babylon.sentinels.liveness.registry's `price_divergence`
    row. Mirrors liveness's own
    `test_efficacy_reds_when_the_declared_consumer_does_not_read_the_output`
    mutation shape (there: point at a symbol absent from the file; here:
    delete the edge outright -- an equally valid instance of 'the consumer
    no longer reads it')."""
    consumer_file = "web/game/engine_bridge.py"
    construct = ConstructNode(
        name="price_divergence",
        def_file="src/babylon/engine/systems/market_scissors.py",
        symbol="price_divergence",
        origin_family="liveness",
        material_relation="Re-expresses liveness.registry's price_divergence row.",
    )
    connected_edge = ExpectedConsumer(
        construct_name="price_divergence", consumer_file=consumer_file, edge_kind="read"
    )
    assert (
        check_disconnected_subsystems(
            constructs=(construct,),
            edges=(connected_edge,),
            entry_points=(consumer_file,),
            exemptions=(),
        )
        == []
    )

    # MUTATION: delete the edge (the consumer no longer reads it).
    findings = check_disconnected_subsystems(
        constructs=(construct,), edges=(), entry_points=(consumer_file,), exemptions=()
    )
    finding = _only_finding(findings)
    assert "price_divergence" in finding


# ---------------------------------------------------------------------------
# vocabulary — NodeType.TERRITORY (engine/systems/territory.py)
# ---------------------------------------------------------------------------


def test_vocabulary_territory_node_type_is_connected_then_reds_when_symbol_is_swapped() -> None:
    """Re-expresses the vocabulary family's node-type production/query
    closure for `NodeType.TERRITORY` (queried via `graph.query_nodes(node_type
    =NodeType.TERRITORY)` in `engine/systems/territory.py`). Mutation mirrors
    the vocabulary sentinel's own "invented string" rule: a node-type-shaped
    symbol with zero real occurrences."""
    consumer_file = "src/babylon/engine/systems/territory.py"
    connected = ConstructNode(
        name="territory_node_type",
        def_file="src/babylon/models/enums/topology.py",
        symbol="TERRITORY",
        origin_family="vocabulary",
        material_relation="Re-expresses the vocabulary family's NodeType.TERRITORY closure.",
    )
    connected_edge = ExpectedConsumer(
        construct_name="territory_node_type", consumer_file=consumer_file, edge_kind="read"
    )
    assert (
        check_disconnected_subsystems(
            constructs=(connected,),
            edges=(connected_edge,),
            entry_points=(consumer_file,),
            exemptions=(),
        )
        == []
    )

    # MUTATION: an invented node-type string with zero real occurrences.
    mutated = connected.model_copy(update={"symbol": "TERRITORY_PHANTOM_ZZZ"})
    findings = check_disconnected_subsystems(
        constructs=(mutated,),
        edges=(connected_edge,),
        entry_points=(consumer_file,),
        exemptions=(),
    )
    finding = _only_finding(findings)
    assert "TERRITORY_PHANTOM_ZZZ" in finding


# ---------------------------------------------------------------------------
# dangling — persist_action_results (protocols.py -> web/game/engine_bridge.py)
# ---------------------------------------------------------------------------


def test_dangling_persist_action_results_is_connected_then_reds_on_the_historical_singular_bug() -> (
    None
):
    """Re-expresses the dangling family's founding specimen: a
    `getattr(persistence, "persist_action_result", None)` (SINGULAR) call
    against a protocol that only ever declares `persist_action_results`
    (PLURAL). That bug is fixed in production today (a direct
    `.persist_action_results(...)` call, verified in the module docstring),
    so the CONNECTED case reproduces the current, fixed state; the MUTATION
    recreates the historical SINGULAR bug by swapping the symbol back --
    verified absent as an exact name from `engine_bridge.py` (it survives
    only as a substring inside an unrelated docstring sentence, which
    :func:`~babylon.sentinels._ast.referenced_names` does not count)."""
    consumer_file = "web/game/engine_bridge.py"
    connected = ConstructNode(
        name="persist_action_results_method",
        def_file="src/babylon/persistence/protocols.py",
        symbol="persist_action_results",
        origin_family="dangling",
        material_relation="Re-expresses the dangling family's founding specimen (now fixed).",
    )
    connected_edge = ExpectedConsumer(
        construct_name="persist_action_results_method",
        consumer_file=consumer_file,
        edge_kind="call",
    )
    assert (
        check_disconnected_subsystems(
            constructs=(connected,),
            edges=(connected_edge,),
            entry_points=(consumer_file,),
            exemptions=(),
        )
        == []
    )

    # MUTATION: the historical SINGULAR dangling-reference bug.
    mutated = connected.model_copy(update={"symbol": "persist_action_result"})
    findings = check_disconnected_subsystems(
        constructs=(mutated,),
        edges=(connected_edge,),
        entry_points=(consumer_file,),
        exemptions=(),
    )
    finding = _only_finding(findings)
    assert "persist_action_result" in finding
