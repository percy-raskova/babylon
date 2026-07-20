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
from babylon.engine.scenarios.us_county_data import (
    ARTIFACT_PATH,
    _verify_content_hash,
    _verify_schema_version,
    load_county_data,
)

# Real Census 2010 figures, spot-verified against the raw DB at generation time.
_AUTAUGA_FIPS = "01001"
_AUTAUGA_POPULATION_2010 = 55505
_BALDWIN_FIPS = "01003"
_BALDWIN_POPULATION_2010 = 201206

# fact_state_minerals(AL).value_millions=2210 allocated to Autauga/Baldwin by
# dim_county_geometry.area_sq_km share (#39 T6), spot-verified at generation time.
_AUTAUGA_RAW_MATERIAL_MILLIONS = 25.479854048273463
_BALDWIN_RAW_MATERIAL_MILLIONS = 85.46863199358724

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

    @pytest.mark.requires_reference_db
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
            if county["raw_material_value_millions"] is None:
                assert (fips, "raw_material_value_millions") in gap_keys, (
                    f"{fips} raw_material_value_millions null but no gap entry"
                )

        for gap in data["gaps"]:
            assert gap["reason"], f"gap entry for {gap['fips']} has an empty reason"

    def test_gap_count_matches_null_field_count(self) -> None:
        data = load_county_data()
        null_population = sum(1 for c in data["counties"] if c["population"] is None)
        null_centroid = sum(
            1 for c in data["counties"] if c["centroid_lat"] is None or c["centroid_lon"] is None
        )
        null_raw_material = sum(
            1 for c in data["counties"] if c["raw_material_value_millions"] is None
        )
        assert len(data["gaps"]) == null_population + null_centroid + null_raw_material


class TestSchemaVersionValidation:
    """#39 T6 M1 / LOW-2: the loader validates ``schema_version`` explicitly --
    ``content_hash`` alone cannot catch a stale/mismatched schema, since it's
    computed the same way regardless of version (self-consistent even over a
    stale v1 artifact)."""

    def test_committed_artifact_passes(self) -> None:
        """The real committed artifact validates cleanly (schema_version 2)."""
        data = load_county_data()
        _verify_schema_version(data)  # must not raise

    def test_wrong_schema_version_fails_loud(self) -> None:
        data = {**load_county_data(), "schema_version": 1}
        with pytest.raises(ValueError, match="schema_version mismatch"):
            _verify_schema_version(data)

    def test_missing_schema_version_fails_loud(self) -> None:
        data = {k: v for k, v in load_county_data().items() if k != "schema_version"}
        with pytest.raises(ValueError, match="schema_version mismatch"):
            _verify_schema_version(data)

    def test_error_names_the_regeneration_command(self) -> None:
        data = {**load_county_data(), "schema_version": 1}
        with pytest.raises(ValueError, match="tools/generate_us_county_territories.py"):
            _verify_schema_version(data)

    def test_wrong_schema_version_does_not_trip_the_content_hash_check(self) -> None:
        """A version-only mismatch (content otherwise byte-identical) still
        passes content_hash -- proving schema_version needs its OWN guard,
        not just a stronger hash."""
        data = {**load_county_data(), "schema_version": 1}
        _verify_content_hash(data)  # must not raise: hash is version-agnostic


class TestRawMaterialValueMillions:
    """#39 T6: fact_state_minerals allocated to counties by area_sq_km share
    (schema_version 2). Mirrors TestArtifactProvenance's population tests."""

    def test_schema_version_bumped(self) -> None:
        data = load_county_data()
        assert data["schema_version"] == 2

    def test_autauga_and_baldwin_are_the_real_allocated_figures(self) -> None:
        """Not round inventions -- an area-weighted share of a real USGS total."""
        data = load_county_data()
        by_fips = {c["fips"]: c["raw_material_value_millions"] for c in data["counties"]}
        assert by_fips[_AUTAUGA_FIPS] == pytest.approx(_AUTAUGA_RAW_MATERIAL_MILLIONS)
        assert by_fips[_BALDWIN_FIPS] == pytest.approx(_BALDWIN_RAW_MATERIAL_MILLIONS)

    def test_values_are_not_round_inventions(self) -> None:
        data = load_county_data()
        values = [
            c["raw_material_value_millions"]
            for c in data["counties"]
            if c["raw_material_value_millions"] is not None
        ]
        assert len(values) > 1
        assert len(set(values)) > 1, "all non-null values are identical -- looks fabricated"

    def test_values_are_nonnegative(self) -> None:
        data = load_county_data()
        for county in data["counties"]:
            value = county["raw_material_value_millions"]
            if value is not None:
                assert value >= 0.0, f"{county['fips']} has a negative raw_material_value_millions"

    def test_dc_and_pr_states_are_unseedable(self) -> None:
        """DC has no fact_state_minerals row (USGS covers the 50 states only);
        PR is out of the national scope entirely (_load_national_fips)."""
        data = load_county_data()
        by_fips = {c["fips"]: c for c in data["counties"]}
        assert by_fips["11001"]["raw_material_value_millions"] is None
        assert not any(fips.startswith("72") for fips in by_fips)

    def test_state_shares_sum_to_the_state_total(self) -> None:
        """Every seeded county's share, summed within its state, reconstructs
        the state's fact_state_minerals value (allocation conserves the total)."""
        data = load_county_data()
        by_state: dict[str, float] = {}
        for county in data["counties"]:
            value = county["raw_material_value_millions"]
            if value is not None:
                state_fips = county["fips"][:2]
                by_state[state_fips] = by_state.get(state_fips, 0.0) + value
        # Alabama (01): fact_state_minerals value_millions = 2210, fully
        # covered by geometry (no gaps for AL raw_material_value_millions).
        assert by_state["01"] == pytest.approx(2210.0)
        # Connecticut (09): value_millions = 259, allocated across the 9
        # modern planning regions (the 8 pre-2022 counties have no geometry).
        assert by_state["09"] == pytest.approx(259.0)


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

    def test_raw_material_value_millions_rederives_from_fact_state_minerals(self) -> None:
        """#39 T6: allocated state totals reconstruct fact_state_minerals --
        shares sum to 1 per state over the counties the artifact could seed
        (i.e. covered by dim_county_geometry -- the generator's own scope)."""
        from tools.generate_us_county_territories import (
            _allocate_raw_material_values,
            _load_county_geo_rows,
            _load_state_minerals,
        )

        from babylon.reference.database import get_normalized_session_factory

        data = load_county_data()
        scope_fips = frozenset(c["fips"] for c in data["counties"])
        session_factory = get_normalized_session_factory()
        geo_rows = _load_county_geo_rows(session_factory)
        state_minerals = _load_state_minerals(session_factory)
        areas = {fips: geo_rows[fips][4] for fips in scope_fips if fips in geo_rows}

        values, _gap_reasons = _allocate_raw_material_values(scope_fips, areas, state_minerals)
        by_fips = {c["fips"]: c["raw_material_value_millions"] for c in data["counties"]}
        for fips in scope_fips:
            assert values[fips] == pytest.approx(by_fips[fips], abs=1e-6), (
                f"{fips} raw_material_value_millions does not re-derive from "
                "the reference DB -- artifact is stale"
            )

        # Alabama's fully-covered total re-derives exactly.
        al_total = sum(v for fips, v in values.items() if fips.startswith("01") and v is not None)
        assert al_total == pytest.approx(state_minerals["01"])
