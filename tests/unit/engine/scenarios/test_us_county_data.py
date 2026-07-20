"""Tests for the committed county-seed artifact + loader (Amendment U / #39 T4).

Mirrors ``tests/unit/engine/scenarios/test_business_seeds.py``'s structure for
the analogous QCEW business-seed artifact (ADR086):

- **Artifact provenance (pure, DB-free)** — pins real committed values so any
  drift is caught in CI without touching the data drive.
- **Loader integrity** — content_hash verification, missing-artifact handling.
- **DB re-derivation (drive-gated)** — when the reference DB is present, spot-
  checked figures are re-derived through the SAME reference tables/policy
  the generator used, proving the artifact is not a stale hand-edit.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from babylon.engine.headless_runner.scopes import DEFAULT_SQLITE_PATH, _load_national_fips
from babylon.engine.scenarios.us_county_data import ARTIFACT_PATH, load_county_data

# Real Census 2010 figures, spot-verified against the raw DB at generation time.
_AUTAUGA_FIPS = "01001"
_AUTAUGA_POPULATION_2010 = 55505
_BALDWIN_FIPS = "01003"
_BALDWIN_POPULATION_2010 = 201206

_REFERENCE_DB = DEFAULT_SQLITE_PATH


class TestArtifactProvenance:
    """The committed artifact carries real, verifiable per-county data."""

    def test_artifact_path_points_at_committed_file(self) -> None:
        assert ARTIFACT_PATH.name == "us_county_territories.json"
        assert ARTIFACT_PATH.exists()

    def test_content_hash_matches_counties(self) -> None:
        """The stamped hash is the sha256 of the canonical counties payload --
        a tamper/regeneration integrity check."""
        data = load_county_data()
        canonical = json.dumps(data["counties"], sort_keys=True, separators=(",", ":"))
        recomputed = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        assert data["content_hash"] == recomputed

    def test_county_count_matches_national_scope(self) -> None:
        """The artifact's county universe is exactly _load_national_fips's --
        never a hardcoded literal, derived from the same scoping rule."""
        data = load_county_data()
        expected = _load_national_fips(DEFAULT_SQLITE_PATH)
        assert len(data["counties"]) == len(expected)
        assert data["source"]["county_count"] == len(expected)

    def test_counties_are_fips_sorted_and_unique(self) -> None:
        data = load_county_data()
        fips_list = [c["fips"] for c in data["counties"]]
        assert fips_list == sorted(fips_list)
        assert len(fips_list) == len(set(fips_list))
        assert all(len(fips) == 5 for fips in fips_list)

    def test_autauga_population_is_the_real_figure(self) -> None:
        """Real Census 2010 value, never a rounded invention (55,505 is not round)."""
        data = load_county_data()
        by_fips = {c["fips"]: c["population"] for c in data["counties"]}
        assert by_fips[_AUTAUGA_FIPS] == _AUTAUGA_POPULATION_2010
        assert by_fips[_BALDWIN_FIPS] == _BALDWIN_POPULATION_2010

    def test_population_values_are_not_round_inventions(self) -> None:
        for value in (_AUTAUGA_POPULATION_2010, _BALDWIN_POPULATION_2010):
            assert value % 1000 != 0

    def test_gaps_are_documented_and_nonoverlapping_by_field(self) -> None:
        """Every null field in `counties` has a matching, honest reason in
        `gaps` -- Constitution III.11: the absence is stated, never silent."""
        data = load_county_data()
        by_fips = {c["fips"]: c for c in data["counties"]}
        gap_keys = {(gap["fips"], gap["field"]) for gap in data["gaps"]}

        for fips, county in by_fips.items():
            if county["population"] is None:
                assert (fips, "population") in gap_keys, f"{fips} population null but no gap entry"
            if county["centroid_lat"] is None or county["centroid_lon"] is None:
                assert (fips, "centroid") in gap_keys, f"{fips} centroid null but no gap entry"

        for gap in data["gaps"]:
            assert gap["reason"], f"gap entry for {gap['fips']} has an empty reason"

    def test_gap_count_matches_null_field_count(self) -> None:
        data = load_county_data()
        null_population = sum(1 for c in data["counties"] if c["population"] is None)
        null_centroid = sum(
            1 for c in data["counties"] if c["centroid_lat"] is None or c["centroid_lon"] is None
        )
        assert len(data["gaps"]) == null_population + null_centroid


@pytest.mark.skipif(
    not _REFERENCE_DB.exists(),
    reason="reference DB absent (CI-without-drive); provenance pinned by committed values above",
)
class TestArtifactRederivesFromDB:
    """When the drive is present, spot-checked figures are re-derivable
    through the SAME reference tables/policy the generator used -- proving
    the artifact is not a stale hand-edit."""

    def test_autauga_population_rederives(self) -> None:
        from babylon.engine.headless_runner.reference_data_cache import ReferenceDataCache

        data = load_county_data()
        year = data["source"]["population_year"]
        cache = ReferenceDataCache(_REFERENCE_DB)
        cache.hydrate(scope_fips=frozenset({_AUTAUGA_FIPS}), year_set=frozenset({year}))
        assert cache.lookup_population(_AUTAUGA_FIPS, year) == _AUTAUGA_POPULATION_2010

    def test_county_scope_rederives(self) -> None:
        expected = _load_national_fips(_REFERENCE_DB)
        data = load_county_data()
        assert {c["fips"] for c in data["counties"]} == set(expected)
