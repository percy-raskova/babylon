"""Structural contract for the v4 architecture and portfolio records."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Final

import pytest
import yaml

pytestmark = [pytest.mark.unit]

_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
_ARCHITECTURE: Final[Path] = _ROOT / "ai" / "architecture.yaml"
_STATE: Final[Path] = _ROOT / "ai" / "state.yaml"
_TUNING: Final[Path] = _ROOT / "ai" / "tuning-standard.yaml"
_ROADMAP: Final[Path] = _ROOT / "project" / "roadmap.md"
_ADR_INDEX: Final[Path] = _ROOT / "ai" / "decisions" / "index.yaml"
_PER_18_ADR: Final[Path] = (
    _ROOT / "ai" / "decisions" / "ADR223_whole_tick_atomicity_world_hash.yaml"
)
_PER_19_ADR: Final[Path] = (
    _ROOT / "ai" / "decisions" / "ADR224_bsl_causal_composition_contract.yaml"
)
_DETERMINISM_REFERENCE: Final[Path] = _ROOT / "docs" / "reference" / "determinism-contract.rst"

_LINEAR_PROJECT: Final[dict[str, str]] = {
    "id": "ebab3603-e391-4110-97e2-97422bc2037e",
    "url": (
        "https://linear.app/percy-raskova/project/"
        "babylon-v1-playable-political-economy-299b037e7feb"
    ),
}
_LINEAR_CHARTER: Final[dict[str, str]] = {
    "id": "4850c85c-1046-4a3d-8003-27cdbfebf5e0",
    "url": ("https://linear.app/percy-raskova/document/babylon-v4-roadmap-charter-2c67d2898306"),
}
_GATES: Final[tuple[tuple[str, str, str], ...]] = (
    ("G1", "Governance & portfolio", "2026-09-30"),
    ("G2", "Executable causality", "2026-11-30"),
    ("G3", "PostgreSQL, H3 & Archive slice", "2027-02-28"),
    ("G4", "COVID E0 emergence proof", "2027-04-30"),
    ("G5", "Player agency", "2027-06-30"),
    ("G6", "Productive & distributive circuit", "2027-10-31"),
    ("G7", "Full-circuit COVID", "2027-12-31"),
    ("G8", "Systemic credit & 2008", "2028-04-30"),
    ("G9", "Representative-world v1", "2028-09-30"),
)
_GATE_DELIVERY_ROOTS: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("G1", ("PER-5",)),
    ("G2", ("PER-6",)),
    ("G3", ("PER-7", "PER-12")),
    ("G4", ("PER-8",)),
    ("G5", ("PER-9",)),
    ("G6", ("PER-10", "PER-11", "PER-12")),
    ("G7", ("PER-8", "PER-10")),
    ("G8", ("PER-8", "PER-10")),
    ("G9", ("PER-13",)),
)
_PORT_DISPOSITIONS: Final[tuple[str, ...]] = ("Port", "Adapt", "Replace", "Retire")
_PROVENANCE_CLASSES: Final[tuple[str, ...]] = (
    "Observed",
    "Derived",
    "Calibrated",
    "Designed",
)
_VALIDATION_DIMENSIONS: Final[tuple[str, ...]] = (
    "conservation",
    "deterministic_replay",
    "control_shock_twins",
    "counterfactual_responsiveness",
    "mutation_tests",
    "heterogeneous_effects",
    "hysteresis",
    "direct_write_audits",
)
_CURRENT_COMPONENTS: Final[tuple[str, ...]] = (
    "rust_graph_hypergraph",
    "bsl_pipeline",
    "rust_tick_session",
    "canonical_graph_hash",
    "nominal_world_hash",
    "bevy_admin_viewer",
    "frozen_python_engine",
    "legacy_python_persistence",
    "partial_babylon_meta",
)
_CURRENT_EVIDENCE: Final[dict[str, tuple[str, ...]]] = {
    "rust_graph_hypergraph": ("rust/crates/babylon-graph/src/lib.rs",),
    "bsl_pipeline": (
        "rust/crates/babylon-bsl/src/lib.rs",
        "rust/crates/babylon-bsl/src/causal_contract.rs",
        "rust/crates/babylon-tick/src/lib.rs",
    ),
    "rust_tick_session": ("rust/crates/babylon-tick/src/session.rs",),
    "canonical_graph_hash": ("rust/crates/babylon-graph/src/state_hash.rs",),
    "nominal_world_hash": (
        "rust/crates/babylon-tick/src/world_hash.rs",
        "rust/crates/babylon-tick/src/session.rs",
    ),
    "bevy_admin_viewer": ("rust/crates/babylon-client/src/ui/admin.rs",),
    "frozen_python_engine": (
        "src/babylon/engine/simulation_engine.py",
        "src/babylon/engine/actions/__init__.py",
    ),
    "legacy_python_persistence": (
        "src/babylon/persistence/runtime_db.py",
        "src/babylon/persistence/envelope.py",
        "src/babylon/persistence/postgres_runtime/__init__.py",
    ),
    "partial_babylon_meta": ("src/babylon/persistence/migrations/0037_babylon_meta.sql",),
}
_H3_EVIDENCE: Final[tuple[str, ...]] = (
    "src/babylon/persistence/postgres_schema.py",
    "src/babylon/persistence/migrations/0011_dynamic_hex_state.sql",
    "src/babylon/persistence/migrations/0027_hex_spatial_map.sql",
    "src/babylon/persistence/migrations/0028_hex_spatial_map_session_scope.sql",
    "src/babylon/reference/schema.py",
    "src/babylon/models/snapshots.py",
    "src/babylon/models/entities/territory.py",
    "src/babylon/persistence/hex_state.py",
)
_GATE_2_STATUSES: Final[dict[str, str]] = {
    "PER-17": "implemented_current",
    "PER-18": "implemented_current",
    "PER-19": "implemented_current",
}
_GATE_2_COMPONENTS: Final[dict[str, str]] = {
    "PER-17": "executable_phase_anchor_total_order",
    "PER-18": (
        "whole_tick_working_copy_rollback_and_canonical_big_endian_"
        "auxiliary_register_combined_world_hashing"
    ),
    "PER-19": (
        "bsl_causal_composition_dual_attribution_provenance_direct_write_whitelist_and_"
        "negative_outcome_write_contracts"
    ),
}
_PER_18_EVIDENCE: Final[tuple[str, ...]] = (
    "rust/crates/babylon-graph/src/working_copy.rs",
    "rust/crates/babylon-tick/src/lib.rs",
    "rust/crates/babylon-tick/src/session.rs",
    "rust/crates/babylon-tick/src/world_hash.rs",
    "ai/decisions/ADR223_whole_tick_atomicity_world_hash.yaml",
)
_PER_19_EVIDENCE: Final[tuple[str, ...]] = (
    "rust/crates/babylon-bsl/src/causal_contract.rs",
    "rust/crates/babylon-bsl/src/same_tick_order.rs",
    "rust/crates/babylon-bsl/src/rule_pipeline.rs",
    "rust/crates/babylon-tick/src/lib.rs",
    "rust/crates/babylon-tick/tests/causal_contract_conformance.rs",
    "ai/decisions/ADR224_bsl_causal_composition_contract.yaml",
)
_GATE_3_ISSUES: Final[tuple[str, ...]] = (
    "PER-20",
    "PER-21",
    "PER-22",
    "PER-23",
    "PER-24",
)
_ACTIVE_REGIONS: Final[tuple[tuple[str, str], ...]] = (
    (
        "docs/superpowers/specs/2026-07-29-game-design-standard-design.md",
        "V4-GAME-DESIGN-ADDENDUM",
    ),
    ("ai/bsl-architecture-standard.md", "V4-BSL-ADDENDUM"),
    ("project/roadmap.md", "V4-ROADMAP-MIRROR"),
    ("project/README.md", "V4-PROJECT-CORPUS"),
)
_AFFIRMATIVE_STALE_CLAIMS: Final[tuple[str, ...]] = (
    "the shipped rust/ratatui skeleton stays",
    "gate: 34 systems green",
    "rust emits the envelope; python persists it",
    "project #8 is the sole board",
    "django/react is the v1 definition of done",
)
_RETIRED_STATUS_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?im)^(?:- )?(?:ratatui/tui|narrationenvelope|project #8|django/react)"
    r"[^\n]*status:\s*implemented_current\s*$"
)
_ROADMAP_GATE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^### (?P<id>G[1-9]) — (?P<name>[^\n]+)\n\n"
    r"- Target: (?P<target>\d{4}-\d{2}-\d{2})$",
    re.MULTILINE,
)
_ROADMAP_DELIVERY_ROOT_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^### (?P<id>G[1-9]) — [^\n]+\n\n"
    r"- Target: \d{4}-\d{2}-\d{2}\n"
    r"- Delivery roots: (?P<roots>PER-\d+(?:, PER-\d+)*)$",
    re.MULTILINE,
)
_POSTGRESQL_ADR: Final[str] = "ADR220_rust_owned_postgresql_persistence_boundary"
_PER_18_ADR_KEY: Final[str] = "ADR223_whole_tick_atomicity_world_hash"
_PER_18_ADR_TITLE: Final[str] = (
    "Rust adjudicates each weekly tick on a detached world, publishes graph, "
    "events, allocator state, and completed time only after total success, and "
    "names current in-memory identity with a versioned nominal world hash"
)
_PER_19_ADR_KEY: Final[str] = "ADR224_bsl_causal_composition_contract"
_PER_19_ADR_TITLE: Final[str] = (
    "BSL rules declare causal role and evidence, production attribution is "
    "independently governed, restricted effects and rank-aware composition "
    "refusals are live, and successful ticks publish identity-free "
    "event-then-write audit receipts"
)


def _yaml_document(path: Path) -> dict[str, Any]:
    """Load one required YAML mapping."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict), path
    return document


def _active_region(relative_path: str, marker: str) -> str:
    """Return one uniquely delimited current Markdown region."""
    text = (_ROOT / relative_path).read_text(encoding="utf-8")
    start = f"<!-- {marker}:START -->"
    end = f"<!-- {marker}:END -->"
    assert text.count(start) == 1, f"{relative_path}: expected one {start}"
    assert text.count(end) == 1, f"{relative_path}: expected one {end}"
    before_end, separator, _after_end = text.partition(end)
    assert separator
    _before_start, separator, region = before_end.partition(start)
    assert separator
    return region


def test_v4_yaml_records_are_mappings() -> None:
    """The three machine-readable Unit 2B records parse as mappings."""
    for path in (_ARCHITECTURE, _STATE, _TUNING):
        assert _yaml_document(path)


def test_architecture_records_current_components_and_gate_delivery_status() -> None:
    """Current evidence and per-issue gate status remain machine-readable."""
    architecture = _yaml_document(_ARCHITECTURE)
    status = architecture["implementation_status"]
    assert isinstance(status, dict)
    assert {"implemented_current", "gate_2_delivery", "planned_gate_3"} <= set(status)
    current = status["implemented_current"]
    assert isinstance(current, dict)
    for component in _CURRENT_COMPONENTS:
        record = current[component]
        assert record["status"] == "implemented_current"
        expected_evidence = _CURRENT_EVIDENCE[component]
        assert tuple(record["evidence"]) == expected_evidence
        assert all((_ROOT / evidence).is_file() for evidence in expected_evidence)
    gate_2 = status["gate_2_delivery"]
    gate_3 = status["planned_gate_3"]
    assert tuple(gate_2) == tuple(_GATE_2_STATUSES)
    assert tuple(gate_3) == _GATE_3_ISSUES
    assert {issue: gate_2[issue]["status"] for issue in _GATE_2_STATUSES} == _GATE_2_STATUSES
    assert {issue: gate_2[issue]["component"] for issue in _GATE_2_COMPONENTS} == _GATE_2_COMPONENTS
    assert tuple(gate_2["PER-18"]["evidence"]) == _PER_18_EVIDENCE
    assert all((_ROOT / evidence).is_file() for evidence in _PER_18_EVIDENCE)
    assert tuple(gate_2["PER-19"]["evidence"]) == _PER_19_EVIDENCE
    assert all((_ROOT / evidence).is_file() for evidence in _PER_19_EVIDENCE)
    assert all(gate_3[issue]["status"] == "planned" for issue in _GATE_3_ISSUES)


def test_control_surface_routes_status_to_linear_and_delivery_to_github() -> None:
    """The architecture record mirrors authority without becoming a status board."""
    architecture = _yaml_document(_ARCHITECTURE)
    control = architecture["control_surface"]
    assert control["portfolio_authority"] == "Linear"
    assert control["linear"]["project"] == _LINEAR_PROJECT
    assert control["linear"]["charter"] == _LINEAR_CHARTER
    assert control["github"]["role"] == "delivery_and_history"
    assert tuple(control["github"]["frozen_migration_inputs"]) == (
        "Project #7",
        "Project #8",
    )


def test_architecture_inventories_the_legacy_h3_migration_source() -> None:
    """The positive-BIGINT plan remains visibly a migration from string identities."""
    architecture = _yaml_document(_ARCHITECTURE)
    current = architecture["implementation_status"]["implemented_current"]
    legacy = current["legacy_h3_text_keys"]
    assert legacy["status"] == "implemented_legacy"
    assert tuple(legacy["evidence"]) == _H3_EVIDENCE
    assert all((_ROOT / evidence).is_file() for evidence in _H3_EVIDENCE)
    inventory = legacy["inventory"]
    assert inventory["hex_cell"] == {
        "h3_index": "VARCHAR(15)",
        "res6_parent": "VARCHAR(15)",
        "res5_parent": "VARCHAR(15)",
    }
    assert inventory["hex_r8_reference"] == {
        "h3_index": "VARCHAR(17)",
        "parent_h3": "VARCHAR(15)",
    }
    assert inventory["hex_map"] == {"h3_index": "VARCHAR(16)"}
    assert inventory["hex_spatial_map"] == {
        "h3_index": "TEXT",
        "length_check": 15,
        "eventual_primary_key": ["session_id", "h3_index"],
        "migrations": ["0027", "0028"],
    }
    assert inventory["dynamic_hex_state"] == {
        "h3_index": "TEXT",
        "length_check": 15,
    }
    assert set(inventory["python_str_models"]) == {
        "reference",
        "snapshot",
        "entity",
        "persistence",
    }
    assert set(inventory["python_str_models"].values()) == {"str"}
    disposition = legacy["planned_disposition"]
    assert disposition["owner"] == "PER-21"
    assert disposition["target"] == "positive BIGINT H3CellId(u64)"
    assert tuple(disposition["migration_sequence"]) == (
        "add_keys",
        "backfill",
        "prove_count_hash_query_equivalence",
        "add_compatibility_views",
        "switch_readers_and_writers",
        "forbid_legacy_writes",
        "retire_duplicates",
    )


def test_architecture_and_roadmap_publish_the_same_gate_triples() -> None:
    """Both repository mirrors preserve Linear's exact gate order and dates."""
    architecture = _yaml_document(_ARCHITECTURE)
    milestones = architecture["roadmap"]["milestones"]
    assert len(milestones) == 9
    architecture_gates = tuple(
        (
            milestones[index]["id"],
            milestones[index]["name"],
            milestones[index]["target"],
        )
        for index in range(9)
    )
    assert architecture["roadmap"]["dates_are_provisional"] is True
    assert architecture_gates == _GATES
    architecture_delivery_roots = tuple(
        (
            milestones[index]["id"],
            tuple(milestones[index]["delivery_roots"]),
        )
        for index in range(9)
    )
    assert all("owner" not in milestones[index] for index in range(9))
    assert architecture_delivery_roots == _GATE_DELIVERY_ROOTS
    roadmap_region = _active_region("project/roadmap.md", "V4-ROADMAP-MIRROR")
    roadmap_gates = tuple(_ROADMAP_GATE_PATTERN.findall(roadmap_region))
    assert roadmap_gates == _GATES
    delivery_root_matches = _ROADMAP_DELIVERY_ROOT_PATTERN.findall(roadmap_region)
    assert len(delivery_root_matches) == 9
    roadmap_delivery_roots = tuple(
        (
            delivery_root_matches[index][0],
            tuple(delivery_root_matches[index][1].split(", ")),
        )
        for index in range(9)
    )
    assert roadmap_delivery_roots == _GATE_DELIVERY_ROOTS


def test_per_48_records_the_accepted_one_way_writer_cutover() -> None:
    """Gate 3 mirrors the accepted PostgreSQL boundary without a dual-writer era."""
    architecture = _yaml_document(_ARCHITECTURE)
    writer = architecture["persistence_writer"]
    assert writer["status"] == "accepted_cutover_law"
    assert writer["decision"] == {
        "issue": "PER-48",
        "adr": _POSTGRESQL_ADR,
        "completion_commit": "9b4c9b2e",
    }
    assert writer["before_cutover"] == {
        "authoritative_writer": "Python",
        "authority": "sole_live_writer",
    }
    assert writer["cutover"] == {
        "direction": "one_way",
        "order": [
            "disable_python_migrations_and_runtime_writes",
            "enable_rust_authoritative_writer",
        ],
        "dual_writes": "forbidden",
    }
    assert writer["after_cutover"]["authoritative_writer"] == "Rust"
    assert tuple(writer["after_cutover"]["owns"]) == (
        "game_managed_postgresql_connections",
        "migrations",
        "typed_tick_transaction",
        "checkpoint_hydration",
        "runtime_writes",
        "h3_codecs",
        "compatibility_views",
    )
    assert tuple(writer["surviving_python_roles"]) == (
        "deterministic_data_acquisition_and_reference_builds",
        "external_api_adapters",
        "ai_and_document_periphery",
        "cli_periphery",
        "read_only_transition_observers",
    )
    assert writer["transition_observers"] == {
        "access": "versioned_views_only",
        "writes": "forbidden",
        "ddl": "forbidden",
    }
    gate_3 = architecture["implementation_status"]["planned_gate_3"]
    per_20 = gate_3["PER-20"]
    assert "blocked_by" not in per_20
    assert per_20["writer_boundary"] == {
        "issue": "PER-48",
        "status": "resolved",
        "adr": _POSTGRESQL_ADR,
    }
    assert tuple(per_20["schemas"]) == ("babylon_ref", "babylon_state", "babylon_meta")
    assert "persistence_writer" not in gate_3
    assert gate_3["PER-24"] == {
        "status": "planned",
        "gate": "G3",
        "owner": "PER-24",
        "component": "DecisionSurfaceContract",
    }


def test_attributed_membership_payload_is_research_not_current_behavior() -> None:
    """Only membership identity is live until PER-44 lands a real payload consumer."""
    architecture = _yaml_document(_ARCHITECTURE)
    status = architecture["implementation_status"]
    graph_scope = tuple(status["implemented_current"]["rust_graph_hypergraph"]["scope"])
    assert graph_scope == (
        "native_graph_elements",
        "native_hyperedges",
        "base_membership_identity",
        "canonical_state_sections",
    )
    assert status["planned_research"]["PER-44"] == {
        "status": "planned",
        "horizon": "Research",
        "component": "attributed_membership_payload",
        "current_truth": {
            "payload_shape": "empty",
            "canonical_hash_covered": False,
            "production_writer": False,
            "production_consumer": False,
        },
        "activation_requires": {
            "named_mechanic_consumer": True,
            "production_payload_write": True,
            "canonical_hash_coverage": True,
        },
    }


def test_slice_ports_and_kimi_intake_have_explicit_activation_law() -> None:
    """Playable causal slices pull ports and data fields through named consumers."""
    architecture = _yaml_document(_ARCHITECTURE)
    assert tuple(architecture["port_policy"]["dispositions"]) == _PORT_DISPOSITIONS
    assert architecture["port_policy"]["selection"] == "playable_causal_slice"
    kimi = architecture["data_intake"]["kimi"]
    assert kimi["status"] == "Research"
    assert kimi["owner"] == "PER-43"
    assert kimi["activation_requires"] == {
        "named_mechanic": True,
        "named_field_consumer": True,
    }


def test_state_is_one_historical_ledger_not_a_status_authority() -> None:
    """The chronology stays intact while stable metadata routes current work to Linear."""
    raw_state = _STATE.read_text(encoding="utf-8")
    assert len(re.findall(r"^meta:\s*$", raw_state, re.MULTILINE)) == 1
    state = _yaml_document(_STATE)
    meta = state["meta"]
    assert meta["role"] == "historical_implementation_ledger"
    assert meta["history_policy"] == "append_or_prepend_only"
    authority = meta["current_work_authority"]
    assert authority["system"] == "Linear"
    assert authority["project"] == _LINEAR_PROJECT
    assert authority["charter"] == _LINEAR_CHARTER
    snapshot = meta["v4_governance_snapshot"]
    assert snapshot["as_of"] == "2026-08-23"
    assert snapshot["implementation_truth"] == "ai/architecture.yaml"
    assert snapshot["lower_entries"] == "dated_snapshots_only"
    assert snapshot["current_status_queries"] == "Linear"
    assert snapshot["persistence_boundary"] == {
        "status": "accepted_cutover_law",
        "issue": "PER-48",
        "adr": _POSTGRESQL_ADR,
        "completion_commit": "9b4c9b2e",
    }
    assert snapshot["bsl_phase_order"] == {
        "status": "implemented_on_dev",
        "issue": "PER-17",
        "adr": "ADR222_executable_bsl_phase_order",
        "merge_commit": "5a0ef2a9",
    }
    assert snapshot["whole_tick_atomicity"] == {
        "status": "implemented_on_dev",
        "issue": "PER-18",
        "adr": _PER_18_ADR_KEY,
        "merge_commit": "9182ec25",
        "scope": "in_memory_only",
    }
    assert snapshot["bsl_causal_composition"] == {
        "status": "implemented_on_PER-19_branch",
        "issue": "PER-19",
        "adr": _PER_19_ADR_KEY,
        "branch": "codex/per-19-bsl-causal-composition",
        "production_classification": {
            "mechanic_derived": 58,
            "recognizer_derived": 2,
            "external_event": 0,
            "intent": 0,
        },
        "attribution_governance": {
            "manifest": "causal_contract::GOVERNED_RULE_ATTRIBUTIONS",
            "known_id_drift": ("uncoded_typed_ContractError_GovernedAttributionMismatch"),
            "production_corpus_completeness": "ci_sentinel",
            "unknown_mod_and_fixture_ids": "self_declared",
        },
        "gate_2_status": "complete_in_checkout",
        "durable_boundary": "planned_gate_3",
    }
    assert snapshot["attributed_membership_payload"] == {
        "status": "planned",
        "horizon": "Research",
        "issue": "PER-44",
        "current_truth": "empty_unhashed_unwritten_unconsumed",
    }
    history = " ".join(meta["truth_status"].split())
    assert (
        "(2026-08-23 GATE 2 — PER-17 EXECUTABLE BSL PHASE ORDER IMPLEMENTED, REVIEW/PR PENDING)"
    ) in history


def test_per_18_adr_and_catalog_are_exact() -> None:
    """The accepted decision and catalog row cannot pass as an empty placeholder."""
    catalog = _yaml_document(_ADR_INDEX)
    assert catalog["meta"] == {
        "version": "1.86.0",
        "updated": "2026-08-26",
        "description": "Architecture Decision Records Index",
        "format": "See individual ADR files in this directory",
    }
    assert catalog["decisions"][_PER_18_ADR_KEY] == {
        "title": _PER_18_ADR_TITLE,
        "status": "accepted",
        "date": "2026-08-23",
        "file": "ADR223_whole_tick_atomicity_world_hash.yaml",
    }
    document = _yaml_document(_PER_18_ADR)
    assert tuple(document) == (_PER_18_ADR_KEY,)
    decision = document[_PER_18_ADR_KEY]
    assert decision["status"] == "accepted"
    assert decision["date"] == "2026-08-23"
    assert decision["title"] == _PER_18_ADR_TITLE
    assert tuple(decision["related"]) == (
        "ADR179_topology_spine_director_rulings",
        _POSTGRESQL_ADR,
        "ADR221_game_first_refoundation_v4",
        "ADR222_executable_bsl_phase_order",
    )


def test_per_19_adr_and_catalog_are_exact() -> None:
    """The causal-composition law and catalog row stay synchronized."""
    catalog = _yaml_document(_ADR_INDEX)
    assert catalog["decisions"][_PER_19_ADR_KEY] == {
        "title": _PER_19_ADR_TITLE,
        "status": "accepted",
        "date": "2026-08-23",
        "file": "ADR224_bsl_causal_composition_contract.yaml",
    }
    document = _yaml_document(_PER_19_ADR)
    assert tuple(document) == (_PER_19_ADR_KEY,)
    decision = document[_PER_19_ADR_KEY]
    assert decision["status"] == "accepted"
    assert decision["date"] == "2026-08-23"
    assert decision["title"] == _PER_19_ADR_TITLE
    assert tuple(decision["supersedes"]) == (
        "ADR222_executable_bsl_phase_order",
        "ADR223_whole_tick_atomicity_world_hash",
    )


def test_determinism_reference_uses_v4_authority_and_honest_scope() -> None:
    """Current hash guidance cannot cite superseded law or promise missing layouts."""
    reference = _DETERMINISM_REFERENCE.read_text(encoding="utf-8")
    index = (_ROOT / "docs" / "reference" / "index.rst").read_text(encoding="utf-8")
    assert "Determinism Contract (Constitution Article V)" in index
    assert "Current constitutional authority is Article V" in reference
    assert "outer ``NominalWorldHash`` composition" in reference
    assert "no byte layout is implemented or specified" in reference
    assert "CONSTITUTION.md:250" not in reference
    combined = " ".join(f"{reference}\n{index}".lower().split())
    stale_clause = re.search(r"(?<!historical v3 clause )\b[IVX]+\.\d+(?:\.\d+)?\b", combined)
    assert stale_clause is None, stale_clause.group() if stale_clause else ""


def test_project_corpus_publishes_the_bounded_catchup_path() -> None:
    """The project README routes readers through law, status, truth, and history."""
    region = _active_region("project/README.md", "V4-PROJECT-CORPUS")
    route = (
        "../CONSTITUTION.md",
        "../NORTH_STAR.md",
        "babylon-v1-playable-political-economy-299b037e7feb",
        "roadmap.md",
        "../ai/architecture.yaml",
        "../ai/state.yaml",
    )
    positions = tuple(region.find(reference) for reference in route)
    assert all(position >= 0 for position in positions)
    assert positions == tuple(sorted(positions))


def test_tuning_encodes_behavioral_validation_without_predestination() -> None:
    """Tuning classifies evidence and tests causal behavior, not a mandated ending."""
    tuning = _yaml_document(_TUNING)
    assert tuple(tuning["provenance_classes"]) == _PROVENANCE_CLASSES
    assert tuning["outcome_policy"] == {
        "predetermined_outcomes": "forbidden",
        "historical_trajectory": "not_prescribed",
        "stable_or_surviving_run": "valid_if_causally_produced",
    }
    assert tuple(tuning["validation_contract"]["dimensions"]) == _VALIDATION_DIMENSIONS
    covid = tuning["benchmark_horizons"]["covid_e0"]
    assert covid["status"] == "planned"
    assert covid["gate"] == "G4"
    assert covid["weeks"] == 104
    assert tuple(covid["runs"]) == (
        "no_shock_control",
        "historical_envelope_shock",
        "strong_capacity_counterfactual",
        "weak_capacity_counterfactual",
    )


def test_active_markdown_regions_are_bounded_and_reject_old_live_claims() -> None:
    """Current addenda classify old artifacts without rewriting historical bodies."""
    for relative_path, marker in _ACTIVE_REGIONS:
        region = _active_region(relative_path, marker)
        folded = " ".join(region.lower().split())
        found = tuple(claim for claim in _AFFIRMATIVE_STALE_CLAIMS if claim in folded)
        assert found == (), f"{relative_path} retains {found}"
        assert _RETIRED_STATUS_PATTERN.search(region) is None, relative_path


def test_standard_addenda_classify_current_and_superseded_surfaces() -> None:
    """The two preserved standards give every disputed surface an explicit v4 status."""
    game_design = _active_region(
        "docs/superpowers/specs/2026-07-29-game-design-standard-design.md",
        "V4-GAME-DESIGN-ADDENDUM",
    )
    bsl = _active_region("ai/bsl-architecture-standard.md", "V4-BSL-ADDENDUM")
    for phrase in (
        "Bevy client status: implemented_current",
        "Ratatui/TUI status: retired",
        "Article V vocabulary authority status: superseded",
        "NarrationEnvelope status: superseded_proposal",
        "In-memory whole-tick rollback status: implemented_current_PER-18",
        "CommittedTickEnvelope status: planned",
        "DecisionSurfaceContract executable status: planned",
        "Persistence writer status: accepted_cutover_law",
        "PER-48 status: Done",
        _POSTGRESQL_ADR,
        "Attributed membership identity status: implemented_current",
        "Attributed membership payload status: planned_research_PER-44",
    ):
        assert phrase in game_design
    for phrase in (
        "S-11 whole-tick rollback status: implemented_current_PER-18",
        "S-25 renderer requirement status: retired",
        "S-32 writer assignment status: superseded",
        "D5/D16 phase-ordering status: implemented_executable_PER-17",
        "PER-18 rollback and combined-world-hash status: implemented_current",
        "PER-19 causal-composition and outcome-write-contract status: implemented_current",
        "Persistence writer status: accepted_cutover_law",
        "PER-48 status: Done",
        _POSTGRESQL_ADR,
        "Attributed membership identity status: implemented_current",
        "Attributed membership payload status: planned_research_PER-44",
    ):
        assert phrase in bsl

    roadmap = _active_region("project/roadmap.md", "V4-ROADMAP-MIRROR")
    for phrase in (
        "Persistence writer status: accepted_cutover_law",
        "PER-48 status: Done",
        _POSTGRESQL_ADR,
    ):
        assert phrase in roadmap
