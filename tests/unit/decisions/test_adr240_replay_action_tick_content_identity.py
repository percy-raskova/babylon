"""Exact decision and live-boundary contract for PER-60 replay identity."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
DECISIONS_DIR = ROOT / "ai" / "decisions"
ADR_STEM = "ADR240_replay_action_tick_content_identity"
ADR_PATH = DECISIONS_DIR / f"{ADR_STEM}.yaml"
INDEX_PATH = DECISIONS_DIR / "index.yaml"
TICK_HASH_PATH = ROOT / "src" / "babylon" / "kernel" / "tick_hash.py"
DETERMINISM_PATH = ROOT / "docs" / "reference" / "determinism-contract.rst"
ARCHITECTURE_PATH = ROOT / "docs" / "concepts" / "architecture.rst"
DESIGN_PATH = (
    ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-08-26-per-60-replay-action-tick-content-hash-design.md"
)
PLAN_PATH = (
    ROOT
    / "docs"
    / "superpowers"
    / "plans"
    / "2026-08-26-per-60-replay-action-tick-content-hash-plan.md"
)
EXPECTED_TITLE = (
    "TickContentHashV1 owns canonical replay-tick identity while campaign "
    "durability and P27 evidence stay separate"
)


def _mapping(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_adr240_records_one_canonical_identity_and_exact_authority() -> None:
    decision = _mapping(ADR_PATH)[ADR_STEM]
    index = _mapping(INDEX_PATH)

    assert decision["status"] == "accepted"
    assert decision["date"] == "2026-08-26"
    assert decision["title"] == EXPECTED_TITLE
    assert decision["issue"] == "PER-60"
    assert decision["owners"] == {
        "replay_primitives_and_outer_hash": "babylon-kernel",
        "accepted_action_identity": "babylon-practice-contract",
        "stable_graph_identity": "babylon-graph",
        "bsl_identity_sections": "babylon-bsl",
        "replay_transaction_and_publication": "babylon-tick",
    }
    assert decision["canonical_contract"] == {
        "schema": "contracts/tick_content_hash_v1.yaml",
        "vectors": "contracts/tick_content_hash_v1_vectors.jsonl",
        "independent_verifier": "tools/verify_tick_content_hash_v1.py",
    }
    assert decision["runtime_action_boundary"] == {
        "accepted_batch": (
            "exact empty OrderedPracticeActionBatchV1 with matching replay session and resolve tick"
        ),
        "nonempty_batch": "structural contract evidence only",
        "execution": False,
    }
    assert (
        decision["persistence_identity_use"]
        == "direct owning kernel module paths only; no aliases or re-exports"
    )

    decision_text = " ".join(str(decision["decision"]).split())
    for required_text in (
        "one canonical `TickContentHashV1` path",
        "P27 bytes never enter `TickContentHashV1`",
        "no adapter, alias, fallback, or second resolver",
        "`ReplaySessionIdV1` and campaign identity remain separate typed inputs",
        "PostgreSQL I/O",
        "player-action execution",
    ):
        assert required_text in decision_text

    assert index["meta"]["version"] == "1.87.0"
    assert index["decisions"][ADR_STEM] == {
        "title": EXPECTED_TITLE,
        "status": "accepted",
        "date": "2026-08-26",
        "file": ADR_PATH.name,
    }


def test_adr240_corrects_only_live_identity_boundary_claims() -> None:
    module = _normalized(TICK_HASH_PATH)
    determinism = _normalized(DETERMINISM_PATH)
    architecture = _normalized(ARCHITECTURE_PATH)

    assert "frozen P27 reference serializer" in module
    assert "not an input or alternate path for `TickContentHashV1`" in module
    assert "required to produce the identical digest" not in module

    assert "``TickContentHashV1`` is implemented" in determinism
    assert "contracts/tick_content_hash_v1.yaml" in determinism
    assert "contracts/tick_content_hash_v1_vectors.jsonl" in determinism
    assert "P27 bytes do not enter ``TickContentHashV1``" in determinism

    assert "``ReplayTickSession`` publishes ``TickContentHashV1`` atomically" in architecture
    assert (
        "Replay identity and campaign durability identity are separate typed inputs" in architecture
    )
    assert "Gate 3 will add the complete content" not in architecture


def test_new_identity_types_have_one_public_owning_module_path() -> None:
    kernel = _normalized(ROOT / "rust" / "crates" / "babylon-kernel" / "src" / "lib.rs")
    practice = _normalized(
        ROOT / "rust" / "crates" / "babylon-practice-contract" / "src" / "lib.rs"
    )
    tick = _normalized(ROOT / "rust" / "crates" / "babylon-tick" / "src" / "lib.rs")
    design = _normalized(DESIGN_PATH)
    plan = _normalized(PLAN_PATH)

    assert "pub use replay::" not in kernel
    assert "pub use tick_content_hash::" not in kernel
    assert "pub use actor_v2::" not in practice
    assert "pub use ordered_action_v1::" not in practice
    assert "pub use replay_session::" not in tick
    assert "compatibility oracle" not in design
    assert "compatibility path" not in design
    assert "legacy TickSession" not in design
    assert "pub use babylon_kernel" not in plan
    assert "TypeId" not in plan
    assert (
        "use `babylon_kernel::tick_content_hash::{RefDigestV1, TickContentHashV1}` directly" in plan
    )
    assert "exposes no short identity name or re-export" in plan
