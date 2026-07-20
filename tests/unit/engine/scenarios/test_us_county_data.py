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

    def test_county_count_matches_national_scope_minus_dedup(self) -> None:
        """The artifact's county universe is _load_national_fips's scope MINUS
        the declared retired-FIPS exclusions (2026-07-19 scout finding + T4
        review finding I-1: raw `_load_national_fips` double-counts
        46113/46102 and 02270/02158 -- both 2015 renames -- and triple-counts
        02261/02063/02066, a 2019 split -- see `exclusions`) -- never a
        hardcoded literal, derived from the same scoping rule + the
        documented dedup."""
        data = load_county_data()
        raw_scope = _load_national_fips(DEFAULT_SQLITE_PATH)
        expected = len(raw_scope) - len(data["exclusions"])
        assert len(data["counties"]) == expected
        assert data["source"]["county_count"] == expected

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
        """Real non-null populations from the artifact are not a fabricated
        round-number template -- distinct counties carry distinct, non-round
        figures (T4 review finding M-1: the prior version of this test
        asserted over two module constants and never read the artifact, so
        it could never fail regardless of the data)."""
        data = load_county_data()
        populations = [c["population"] for c in data["counties"] if c["population"] is not None]
        assert len(populations) > 1
        assert len(set(populations)) > 1, (
            "all non-null populations are identical -- looks fabricated"
        )
        round_thousands = sum(1 for value in populations if value % 1000 == 0)
        assert round_thousands < len(populations), (
            "every non-null population is a round multiple of 1000 -- looks fabricated"
        )

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


class TestRetiredFipsDedup:
    """`dim_county` carries retired FIPS whose modern successor(s) are ALSO
    present as separate rows -- the same physical county/area double- or
    triple-counted. Two declared, cited forms (2026-07-19 scout finding;
    extended 2026-07-20, T4 review finding I-1):

    - Rename (one successor each): 46113 (Shannon County, SD, retired) ->
      46102 (Oglala Lakota County, SD, 2015 rename); 02270 (Wade Hampton
      Census Area, AK, retired) -> 02158 (Kusilvak Census Area, AK, 2015
      rename) -- the exact same class of duplicate as Shannon/Oglala Lakota.
    - Split (two successors): 02261 (Valdez-Cordova Census Area, AK,
      retired) -> 02063 (Chugach Census Area, AK) + 02066 (Copper River
      Census Area, AK), a 2019 dissolution.

    The generator drops a retired FIPS only when ALL of its successor(s) are
    present, citing the exclusion rather than silently dropping it."""

    def test_retired_fips_are_excluded(self) -> None:
        data = load_county_data()
        fips_list = {c["fips"] for c in data["counties"]}
        assert "46113" not in fips_list
        assert "02270" not in fips_list
        assert "02261" not in fips_list

    def test_rename_successors_are_present(self) -> None:
        data = load_county_data()
        by_fips = {c["fips"]: c for c in data["counties"]}
        assert "46102" in by_fips
        # QCEW fallback (Census absent for 46102 at 2010): int(3662 * 0.33).
        assert by_fips["46102"]["population"] == 1208
        # 02158's population is a documented gap (no Census/QCEW row at
        # 2010, the county didn't exist yet under this FIPS) -- see
        # TestArtifactProvenance's gap-coverage tests for that assertion.
        assert "02158" in by_fips

    def test_split_successors_are_present(self) -> None:
        data = load_county_data()
        by_fips = {c["fips"]: c for c in data["counties"]}
        assert "02063" in by_fips
        assert "02066" in by_fips

    def test_exclusions_are_documented_with_reasons(self) -> None:
        data = load_county_data()
        assert len(data["exclusions"]) == 3
        by_fips = {e["fips"]: e for e in data["exclusions"]}

        rename_46113 = by_fips["46113"]
        assert rename_46113["kind"] == "rename"
        assert rename_46113["successor_fips"] == "46102"
        assert rename_46113["reason"]

        rename_02270 = by_fips["02270"]
        assert rename_02270["kind"] == "rename"
        assert rename_02270["successor_fips"] == "02158"
        assert rename_02270["reason"]

        split_02261 = by_fips["02261"]
        assert split_02261["kind"] == "split"
        assert split_02261["successor_fips"] == ["02063", "02066"]
        assert split_02261["reason"]

    def test_no_retired_fips_gap_entry_remains(self) -> None:
        """Retired FIPS used to carry gap entries before dedup -- once
        excluded, none may linger in `gaps` (they have no `counties` row)."""
        data = load_county_data()
        gap_fips = {gap["fips"] for gap in data["gaps"]}
        assert gap_fips.isdisjoint({"46113", "02270", "02261"})


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
        """Raw `_load_national_fips` re-derives the artifact's scope PLUS the
        three declared retired-FIPS exclusions (46113, 02270, 02261) -- see
        TestRetiredFipsDedup for the dedup itself."""
        expected = _load_national_fips(_REFERENCE_DB)
        data = load_county_data()
        excluded = {e["fips"] for e in data["exclusions"]}
        assert {c["fips"] for c in data["counties"]} == set(expected) - excluded
