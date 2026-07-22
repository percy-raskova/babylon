"""Tests for the INFLUENCES seed computation pipeline (T111/T112; county grain
per P25 U6/ADR132).

Covers:
- Schema validation against ``seed_influences.schema.json``.
- Byte-identical determinism on re-computation (SC-011 + FR-044).
- County-FIPS keying: territory_ids are exactly the Detroit tri-county FIPS
  (Wayne 26163, Oakland 26125, Macomb 26099) — the res-7 H3 keying was
  retired with the Amendment-U substrate (county_fips is the sole spatial
  key the engine reads).
- The FR-039 electoral component is REAL: FAC_RESTORATIONIST influence equals
  the committed MIT Election Lab 2024 Republican vote share per county
  (data-artifacts.yaml ``mit_countypres_rep_share``), not a radius-band proxy.
- Influence level constraints: all in [0, 1]; liberal-imperial clamped.
- Support type mapping per faction.
- The committed ``seed_influences.json`` artifact loads via the runtime
  loader and validates against the schema.
"""

from __future__ import annotations

import csv
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
    TRI_COUNTY_FIPS,
    compute_seed_influences,
    write_seed_influences,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_PATH = (
    _REPO_ROOT / "specs" / "070-balkanization" / "contracts" / "seed_influences.schema.json"
)
_SEED_PATH = (
    _REPO_ROOT / "src" / "babylon" / "data" / "game" / "balkanization" / "seed_influences.json"
)
_ELECTION_ARTIFACT = (
    _REPO_ROOT
    / "src"
    / "babylon"
    / "data"
    / "reference"
    / "election"
    / "mit_countypres_rep_share.csv"
)

_ALL_FACTIONS = {
    "FAC_WORKERS_CONGRESS",
    "FAC_DECOLONIAL",
    "FAC_RESTORATIONIST",
    "FAC_LIBERAL_IMPERIAL",
}


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
# County-FIPS keying (P25 U6 re-key: the Amendment-U substrate contract)
# ---------------------------------------------------------------------------


def test_territory_ids_are_the_tri_county_fips() -> None:
    """Every territory_id is a Detroit tri-county 5-digit county FIPS."""
    payload = compute_seed_influences()
    territory_ids = {edge["territory_id"] for edge in payload["edges"]}
    assert territory_ids == set(TRI_COUNTY_FIPS)
    assert territory_ids == {"26163", "26125", "26099"}
    for tid in territory_ids:
        assert len(tid) == 5 and tid.isdigit()


def test_edge_count_is_three_counties_times_four_factions() -> None:
    """County grain: exactly 3 counties × 4 factions = 12 edges."""
    payload = compute_seed_influences()
    assert len(payload["edges"]) == 12


def test_every_county_has_four_faction_edges() -> None:
    """Every county gets exactly 4 edges (one per faction)."""
    payload = compute_seed_influences()
    territory_edges: dict[str, set[str]] = {}
    for edge in payload["edges"]:
        territory_edges.setdefault(edge["territory_id"], set()).add(edge["faction_id"])
    for county_fips, facs in territory_edges.items():
        assert facs == _ALL_FACTIONS, f"County {county_fips} missing {_ALL_FACTIONS - facs}"


def test_all_factions_present() -> None:
    """All 4 canonical factions are represented in the edge set."""
    payload = compute_seed_influences()
    present = {edge["faction_id"] for edge in payload["edges"]}
    assert present == _ALL_FACTIONS


# ---------------------------------------------------------------------------
# The real electoral component (FR-039 via ADR049: MIT Election Lab)
# ---------------------------------------------------------------------------


def _artifact_rep_share() -> dict[str, float]:
    with _ELECTION_ARTIFACT.open(newline="", encoding="utf-8") as handle:
        return {row["county_fips"]: float(row["rep_vote_share"]) for row in csv.DictReader(handle)}


def test_restorationist_influence_is_the_real_republican_vote_share() -> None:
    """FAC_RESTORATIONIST influence == the committed MIT Election Lab 2024
    Republican vote share per county (rounded to the pipeline's 4 decimal
    places) — the data-driven replacement for the radius-band fixture."""
    shares = _artifact_rep_share()
    payload = compute_seed_influences()
    checked = 0
    for edge in payload["edges"]:
        if edge["faction_id"] != "FAC_RESTORATIONIST":
            continue
        expected = round(shares[edge["territory_id"]], 4)
        assert edge["influence_level"] == expected, edge
        checked += 1
    assert checked == 3


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
    """All 4 provenance fields are present and match the module constants."""
    payload = compute_seed_influences()
    prov = payload["proxy_data_provenance"]
    assert prov["qcew_vintage"] == FIXTURE_QCEW_VINTAGE
    assert prov["natural_earth_version"] == FIXTURE_NATURAL_EARTH_VERSION
    assert prov["election_source"] == FIXTURE_ELECTION_SOURCE
    assert prov["election_year"] == FIXTURE_ELECTION_YEAR


def test_election_source_is_mit_election_lab() -> None:
    """The electoral component is data-driven (ADR049 ratified): the pipeline
    declares MIT_ELECTION_LAB / 2024, never the retired radius-band fixture."""
    payload = compute_seed_influences()
    prov = payload["proxy_data_provenance"]
    assert prov["election_source"] == "MIT_ELECTION_LAB"
    assert prov["election_year"] == 2024


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
    """Same county + faction → same cadre_count."""
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


def test_every_county_has_at_least_one_positive_influence() -> None:
    """SC-017: every in-scope territory has ≥1 edge with influence_level > 0."""
    payload = compute_seed_influences()
    territory_max: dict[str, float] = {}
    for edge in payload["edges"]:
        tid = edge["territory_id"]
        territory_max[tid] = max(territory_max.get(tid, 0.0), edge["influence_level"])
    for tid, max_inf in territory_max.items():
        assert max_inf > 0.0, f"Territory {tid} has no positive influence"
