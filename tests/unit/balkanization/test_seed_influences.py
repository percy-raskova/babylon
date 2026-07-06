"""Tests for the INFLUENCES seed computation pipeline (T111/T112).

Covers:
- Schema validation against ``seed_influences.schema.json``.
- Byte-identical determinism on re-computation (SC-011 + FR-044).
- Edge coverage: every hex has 4 faction edges.
- Influence level constraints: all in [0, 1]; liberal-imperial clamped.
- Support type mapping per faction.
- The committed ``seed_influences.json`` artifact loads via the runtime
  loader and validates against the schema.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from babylon.data.game.balkanization import load_seed_influences
from babylon.data.game.balkanization.compute_seed_influences import (
    DEFAULT_LIBERAL_IMPERIAL_CAP,
    FIXTURE_COMPUTED_AT,
    FIXTURE_ELECTION_SOURCE,
    FIXTURE_ELECTION_YEAR,
    FIXTURE_NATURAL_EARTH_VERSION,
    FIXTURE_QCEW_VINTAGE,
    compute_seed_influences,
    write_seed_influences,
)

pytestmark = pytest.mark.unit

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "070-balkanization"
    / "contracts"
    / "seed_influences.schema.json"
)

_SEED_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "babylon"
    / "data"
    / "game"
    / "balkanization"
    / "seed_influences.json"
)


def _load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text())


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def test_compute_output_validates_against_schema() -> None:
    """The computed payload MUST validate against the JSON Schema."""
    payload = compute_seed_influences()
    schema = _load_schema()
    jsonschema.validate(payload, schema)


def test_committed_seed_file_validates_against_schema() -> None:
    """The committed ``seed_influences.json`` MUST validate against the schema."""
    assert _SEED_PATH.exists(), "seed_influences.json must be committed to the repo"
    payload = json.loads(_SEED_PATH.read_text())
    schema = _load_schema()
    jsonschema.validate(payload, schema)


# ---------------------------------------------------------------------------
# Determinism (SC-011 + FR-044)
# ---------------------------------------------------------------------------


def test_compute_is_byte_identical_on_recomputation() -> None:
    """Same parameters → byte-identical JSON output."""
    payload_a = compute_seed_influences()
    payload_b = compute_seed_influences()
    text_a = json.dumps(payload_a, indent=2, sort_keys=False)
    text_b = json.dumps(payload_b, indent=2, sort_keys=False)
    assert text_a == text_b


def test_compute_has_fixed_timestamp() -> None:
    """``computed_at_iso`` is fixed (not ``datetime.now()``) for determinism."""
    payload = compute_seed_influences()
    assert payload["computed_at_iso"] == FIXTURE_COMPUTED_AT


def test_committed_seed_matches_fresh_compute() -> None:
    """The committed file must match a fresh computation byte-identically."""
    assert _SEED_PATH.exists()
    committed = _SEED_PATH.read_text()
    fresh = compute_seed_influences()
    fresh_text = json.dumps(fresh, indent=2, sort_keys=False) + "\n"
    assert committed == fresh_text


# ---------------------------------------------------------------------------
# Edge coverage + structure
# ---------------------------------------------------------------------------


def test_every_hex_has_four_faction_edges() -> None:
    """Every territory hex gets exactly 4 edges (one per faction)."""
    payload = compute_seed_influences()
    edges = payload["edges"]
    territory_edges: dict[str, set[str]] = {}
    for edge in edges:
        territory_edges.setdefault(edge["territory_id"], set()).add(edge["faction_id"])
    factions = {
        "FAC_WORKERS_CONGRESS",
        "FAC_DECOLONIAL",
        "FAC_RESTORATIONIST",
        "FAC_LIBERAL_IMPERIAL",
    }
    for hex_id, facs in territory_edges.items():
        assert facs == factions, f"Hex {hex_id} missing factions: {factions - facs}"


def test_all_factions_present() -> None:
    """All 4 canonical factions are represented in the edge set."""
    payload = compute_seed_influences()
    present = {edge["faction_id"] for edge in payload["edges"]}
    assert present == {
        "FAC_WORKERS_CONGRESS",
        "FAC_DECOLONIAL",
        "FAC_RESTORATIONIST",
        "FAC_LIBERAL_IMPERIAL",
    }


def test_edge_count_is_multiple_of_four() -> None:
    """Edge count = 4 × hex_count (deterministic)."""
    payload = compute_seed_influences()
    assert len(payload["edges"]) % 4 == 0
    assert len(payload["edges"]) >= 4  # at least one hex


def test_all_influence_levels_in_unit_range() -> None:
    """Every influence_level ∈ [0.0, 1.0]."""
    payload = compute_seed_influences()
    for edge in payload["edges"]:
        assert 0.0 <= edge["influence_level"] <= 1.0, edge


def test_liberal_imperial_clamped_to_cap() -> None:
    """FAC_LIBERAL_IMPERIAL influence ≤ liberal_imperial_influence_cap."""
    payload = compute_seed_influences(liberal_imperial_cap=DEFAULT_LIBERAL_IMPERIAL_CAP)
    for edge in payload["edges"]:
        if edge["faction_id"] == "FAC_LIBERAL_IMPERIAL":
            assert edge["influence_level"] <= DEFAULT_LIBERAL_IMPERIAL_CAP, edge


def test_liberal_imperial_cap_respected_when_lowered() -> None:
    """Lowering the cap reduces liberal-imperial influence."""
    cap_low = 0.2
    payload = compute_seed_influences(liberal_imperial_cap=cap_low)
    for edge in payload["edges"]:
        if edge["faction_id"] == "FAC_LIBERAL_IMPERIAL":
            assert edge["influence_level"] <= cap_low, edge


# ---------------------------------------------------------------------------
# Support type mapping
# ---------------------------------------------------------------------------


def test_support_type_mapping() -> None:
    """Each faction has the correct support_type per data-model.md §8."""
    payload = compute_seed_influences()
    expected = {
        "FAC_WORKERS_CONGRESS": "labor",
        "FAC_DECOLONIAL": "ideological",
        "FAC_RESTORATIONIST": "electoral",
        "FAC_LIBERAL_IMPERIAL": "ideological",
    }
    for edge in payload["edges"]:
        assert edge["support_type"] == expected[edge["faction_id"]], edge


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def test_provenance_fields_present() -> None:
    """All 4 provenance fields are present and match fixture constants."""
    payload = compute_seed_influences()
    prov = payload["proxy_data_provenance"]
    assert prov["qcew_vintage"] == FIXTURE_QCEW_VINTAGE
    assert prov["natural_earth_version"] == FIXTURE_NATURAL_EARTH_VERSION
    assert prov["election_source"] == FIXTURE_ELECTION_SOURCE
    assert prov["election_year"] == FIXTURE_ELECTION_YEAR


def test_election_source_enum_constraint() -> None:
    """election_source must be MIT_ELECTION_LAB or CENSUS_BUREAU_FIXTURE."""
    payload = compute_seed_influences()
    assert payload["proxy_data_provenance"]["election_source"] in {
        "MIT_ELECTION_LAB",
        "CENSUS_BUREAU_FIXTURE",
    }


def test_version_is_semver() -> None:
    payload = compute_seed_influences()
    parts = payload["version"].split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


# ---------------------------------------------------------------------------
# Cadre / sympathizer counts
# ---------------------------------------------------------------------------


def test_cadre_and_sympathizer_non_negative() -> None:
    """cadre_count and sympathizer_count ≥ 0."""
    payload = compute_seed_influences()
    for edge in payload["edges"]:
        assert edge["cadre_count"] >= 0, edge
        assert edge["sympathizer_count"] >= 0, edge


def test_cadre_deterministic() -> None:
    """Same hex + faction → same cadre_count."""
    payload_a = compute_seed_influences()
    payload_b = compute_seed_influences()
    for a, b in zip(payload_a["edges"], payload_b["edges"], strict=True):
        assert a["cadre_count"] == b["cadre_count"]
        assert a["sympathizer_count"] == b["sympathizer_count"]


def test_established_tick_is_zero() -> None:
    """All seed edges have established_tick=0 (seed at game start)."""
    payload = compute_seed_influences()
    for edge in payload["edges"]:
        assert edge["established_tick"] == 0, edge


# ---------------------------------------------------------------------------
# write_seed_influences
# ---------------------------------------------------------------------------


def test_write_seed_influences_creates_valid_file(tmp_path: Path) -> None:
    """write_seed_influences produces a schema-valid JSON file."""
    out = write_seed_influences(output_path=tmp_path / "seed_influences.json")
    assert out.exists()
    payload = json.loads(out.read_text())
    schema = _load_schema()
    jsonschema.validate(payload, schema)


# ---------------------------------------------------------------------------
# Loader integration
# ---------------------------------------------------------------------------


def test_runtime_loader_reads_committed_seed() -> None:
    """load_seed_influences() reads the committed seed_influences.json."""
    assert _SEED_PATH.exists(), "seed_influences.json must be committed"
    edges = load_seed_influences()
    assert len(edges) > 0, "loader must return non-empty edge list"
    first = edges[0]
    assert "faction_id" in first
    assert "territory_id" in first
    assert "influence_level" in first
    assert "support_type" in first


def test_runtime_loader_edges_match_schema() -> None:
    """Loader-returned edge dicts have exactly the schema-required keys."""
    edges = load_seed_influences()
    expected_keys = {
        "faction_id",
        "territory_id",
        "influence_level",
        "support_type",
        "cadre_count",
        "sympathizer_count",
        "established_tick",
    }
    for edge in edges[:10]:
        assert set(edge.keys()) == expected_keys, edge


# ---------------------------------------------------------------------------
# Coverage invariant (SC-017 partial)
# ---------------------------------------------------------------------------


def test_every_hex_has_at_least_one_positive_influence() -> None:
    """SC-017: every in-scope territory has ≥1 edge with influence_level > 0."""
    payload = compute_seed_influences()
    territory_max: dict[str, float] = {}
    for edge in payload["edges"]:
        tid = edge["territory_id"]
        territory_max[tid] = max(territory_max.get(tid, 0.0), edge["influence_level"])
    for tid, max_inf in territory_max.items():
        assert max_inf > 0.0, f"Territory {tid} has no positive influence"
