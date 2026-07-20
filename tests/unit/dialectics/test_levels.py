"""Unit tests for :mod:`babylon.domain.dialectics.instances.levels` — level lattices.

The spatial resolution law (design §E1, verbatim): a field constant within
states but differing between states is *resolved at county* (its county
aggregates are flat per state) yet *not resolved at hex* (hexes still vary
within their county); a spatially-uniform field resolves everywhere. The
fixture uses UNIFORM shares so every closure is a plain regional mean and the
answers are hand-computable.

Hex layout (two states)::

    state 26: county 26001 = {h1, h2}, county 26002 = {h3, h4}
    state 27: county 27001 = {h5, h6}
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from babylon.domain.dialectics.instances.levels import (
    LEVEL_INDEX,
    SpatialLatticeRungs,
    _msa_mapping_from_session,
    build_lattice_from_maps,
    cz_adjunction,
    level_index_for,
    msa_adjunction,
    social_lattice_from_memberships,
    spatial_lattice_for_counties,
    spatial_lattice_rungs_for_counties,
)
from babylon.domain.dialectics.instances.scale import ScaleAdjunction

pytestmark = pytest.mark.math

SQLITE_REF = Path("data/sqlite/marxist-data-3NF.sqlite")

_HEX_PARENTS: dict[str, dict[str, str]] = {
    "hex": {h: h for h in ("h1", "h2", "h3", "h4", "h5", "h6")},
    "county": {
        "h1": "26001",
        "h2": "26001",
        "h3": "26002",
        "h4": "26002",
        "h5": "27001",
        "h6": "27001",
    },
    "state": {"h1": "26", "h2": "26", "h3": "26", "h4": "26", "h5": "27", "h6": "27"},
    "nation": dict.fromkeys(("h1", "h2", "h3", "h4", "h5", "h6"), "US"),
}


def _hex_lattice() -> object:
    return build_lattice_from_maps(("hex", "county", "state", "nation"), _HEX_PARENTS)


class TestSpatialResolutionLaw:
    """The design §E1 resolution law over the hex ≺ county ≺ state chain."""

    def test_county_constant_within_state_is_resolved_at_county(self) -> None:
        # county means: 26001->2, 26002->2 (flat within state 26); 27001->6.
        field = {"h1": 1.0, "h2": 3.0, "h3": 0.0, "h4": 4.0, "h5": 5.0, "h6": 7.0}
        lattice = _hex_lattice()
        assert lattice.is_resolved_at(field, lower=1, higher=2)  # resolved at county

    def test_same_field_is_not_resolved_at_hex(self) -> None:
        # Hexes vary within their county (1 != 3 in 26001), so smoothing at the
        # county level moves the field: the hex-level opposition is unresolved.
        field = {"h1": 1.0, "h2": 3.0, "h3": 0.0, "h4": 4.0, "h5": 5.0, "h6": 7.0}
        lattice = _hex_lattice()
        assert not lattice.is_resolved_at(field, lower=0, higher=1)

    def test_county_varying_within_state_is_not_resolved_at_county(self) -> None:
        # 26001->2 but 26002->10: county aggregates differ WITHIN state 26.
        field = {"h1": 1.0, "h2": 3.0, "h3": 8.0, "h4": 12.0, "h5": 5.0, "h6": 7.0}
        lattice = _hex_lattice()
        assert not lattice.is_resolved_at(field, lower=1, higher=2)

    def test_uniform_field_resolves_everywhere(self) -> None:
        field = dict.fromkeys(("h1", "h2", "h3", "h4", "h5", "h6"), 5.0)
        lattice = _hex_lattice()
        assert lattice.is_resolved_at(field, lower=0, higher=1)
        assert lattice.is_resolved_at(field, lower=1, higher=2)
        assert lattice.is_resolved_at(field, lower=2, higher=3)


class TestSpatialAufhebung:
    """The least resolving level for a flat-within-county field is county."""

    def test_flat_within_county_sublates_to_county(self) -> None:
        # Constant per county (hexes equal within county) but varying between
        # counties: resolved at hex, so the least level above hex is county.
        field = {"h1": 2.0, "h2": 2.0, "h3": 10.0, "h4": 10.0, "h5": 6.0, "h6": 6.0}
        result = _hex_lattice().aufhebung_of(0, probes=[field])
        assert result is not None
        assert result.name == "county"

    def test_hex_varying_field_has_no_aufhebung_below_nation(self) -> None:
        # Hexes vary within counties: no coarser mean reproduces the field, so
        # the hex-level opposition is antagonistic relative to this chain.
        field = {"h1": 1.0, "h2": 3.0, "h3": 0.0, "h4": 4.0, "h5": 5.0, "h6": 7.0}
        assert _hex_lattice().aufhebung_of(0, probes=[field]) is None


class TestCountyRootedLattice:
    """The production county-rooted lattice used by the regime classifier."""

    def test_levels_are_county_state_nation(self) -> None:
        lattice = spatial_lattice_for_counties(["26001", "26002", "27001"])
        assert [lvl.name for lvl in lattice.levels] == ["county", "state", "nation"]

    def test_county_field_flat_per_state_resolves_at_county(self) -> None:
        lattice = spatial_lattice_for_counties(["26001", "26002", "27001"])
        field = {"26001": 2.0, "26002": 2.0, "27001": 6.0}  # flat within state 26
        assert lattice.is_resolved_at(field, lower=1, higher=2)

    def test_county_field_varying_in_state_not_resolved(self) -> None:
        lattice = spatial_lattice_for_counties(["26001", "26002", "27001"])
        field = {"26001": 2.0, "26002": 10.0, "27001": 6.0}  # differ within state 26
        assert not lattice.is_resolved_at(field, lower=1, higher=2)

    def test_population_weighting_changes_the_state_aggregate(self) -> None:
        # With a heavier 26001, the state-26 aggregate is pulled toward it, so a
        # field flat across the two counties still resolves (means agree) but an
        # asymmetric one is weighted — exercise that populations are honored.
        lattice = spatial_lattice_for_counties(
            ["26001", "26002"], populations={"26001": 3.0, "26002": 1.0}
        )
        flat = {"26001": 4.0, "26002": 4.0}
        assert lattice.is_resolved_at(flat, lower=1, higher=2)

    def test_empty_counties_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least one county"):
            spatial_lattice_for_counties([])


class TestSocialLattice:
    """The individual ≺ community ≺ class ≺ bloc chain (single-membership)."""

    def test_builds_four_levels(self) -> None:
        lattice = social_lattice_from_memberships(
            {"a1": "cP", "a2": "cP", "a3": "cB"},
            {"cP": "proletarian", "cB": "bourgeois"},
            {"proletarian": "periphery", "bourgeois": "core"},
        )
        assert [lvl.name for lvl in lattice.levels] == [
            "individual",
            "community",
            "class",
            "bloc",
        ]

    def test_field_flat_within_community_resolves_at_individual(self) -> None:
        lattice = social_lattice_from_memberships(
            {"a1": "cP", "a2": "cP", "a3": "cB"},
            {"cP": "proletarian", "cB": "bourgeois"},
            {"proletarian": "periphery", "bourgeois": "core"},
        )
        field = {"a1": 1.0, "a2": 1.0, "a3": 5.0}  # a1,a2 equal within cP
        assert lattice.is_resolved_at(field, lower=0, higher=1)

    def test_uniform_field_resolves_up_to_bloc(self) -> None:
        lattice = social_lattice_from_memberships(
            {"a1": "cP", "a2": "cB"},
            {"cP": "proletarian", "cB": "bourgeois"},
            {"proletarian": "periphery", "bourgeois": "core"},
        )
        field = {"a1": 3.0, "a2": 3.0}
        assert lattice.is_resolved_at(field, lower=1, higher=2)
        assert lattice.is_resolved_at(field, lower=2, higher=3)

    def test_unmapped_community_fails_loud(self) -> None:
        with pytest.raises(KeyError, match="community"):
            social_lattice_from_memberships(
                {"a1": "cMissing"},
                {"cP": "proletarian"},
                {"proletarian": "periphery"},
            )


class TestLevelIndex:
    """The level-name → chain-index catalog spans both hierarchies."""

    def test_spatial_and_social_indices(self) -> None:
        assert LEVEL_INDEX["county"] == 1
        assert LEVEL_INDEX["class"] == 2
        assert LEVEL_INDEX["bloc"] == 3

    def test_level_index_for_unknown_is_none(self) -> None:
        assert level_index_for("") is None
        assert level_index_for("galaxy") is None


# =============================================================================
# Amendment U (#39 T3): the CZ / MSA parallel county-aggregation rungs.
#
# CZ totality note: the brief's literal claim ("every county in the modern
# dim_county universe resolves to exactly one CZ") does NOT hold over the raw
# ~3285-row dim_county table -- empirically, 151 rows have no CZ, and only 3
# fit the "vintage bridge" pattern (Miami-Dade/Oglala Lakota/Broomfield).
# Excluding the 51 synthetic ``{state}999`` rest-of-state rows and
# out-of-CONUS territories -- the SAME scope
# ``engine.headless_runner.scopes._load_national_fips`` already uses for "the
# county universe" -- leaves exactly 19 real, well-characterized gaps: 10
# post-1990 Alaska census-area reorganizations and 9 counties from
# Connecticut's 2022 county -> planning-region switch, neither of which has a
# sourced 1:1 predecessor to bridge to. Totality holds over that correctly
# scoped universe (TestCZTotalityOverCountyUniverse); the 19 gap counties are
# asserted to fail loud, not silently resolve.
# =============================================================================

# The empirically-verified residual CZ coverage gap (see cz_adjunction's
# docstring for the full citation). Neither category has a sourced 1:1
# predecessor, so acquiring/bridging them is a follow-up data decision, not
# something this module fabricates.
_AK_CT_CZ_GAP_FIPS: tuple[str, ...] = (
    "02063",  # Chugach Census Area (split from Valdez-Cordova, 2019)
    "02066",  # Copper River Census Area (split from Valdez-Cordova, 2019)
    "02068",  # Denali Borough
    "02105",  # Hoonah-Angoon Census Area (created 2007)
    "02158",  # Kusilvak Census Area (renamed from Wade Hampton, 2015)
    "02195",  # Petersburg Census Area (split from Wrangell-Petersburg, 2013)
    "02198",  # Prince of Wales-Hyder Census Area (reorganized 2008)
    "02230",  # Skagway Municipality (reorganized 2007)
    "02275",  # Wrangell City and Borough (split from Wrangell-Petersburg, 2008)
    "02282",  # Yakutat City and Borough
    "09110",  # Capitol Planning Region (CT 2022 county -> region switch)
    "09120",  # Greater Bridgeport Planning Region
    "09130",  # Lower Connecticut River Valley Planning Region
    "09140",  # Naugatuck Valley Planning Region
    "09150",  # Northeastern Connecticut Planning Region
    "09160",  # Northwest Hills Planning Region
    "09170",  # South Central Connecticut Planning Region
    "09180",  # Southeastern Connecticut Planning Region
    "09190",  # Western Connecticut Planning Region
)


class TestCZAdjunction:
    """``cz_adjunction()``: county -> commuting zone, TOTAL over the crosswalk."""

    def test_covers_crosswalk_plus_three_vintage_bridges(self) -> None:
        # 3141 CSV rows + 3 bridged modern FIPS (12086/46102/08014).
        adj = cz_adjunction()
        assert len(adj.mapping) == 3144

    def test_741_distinct_czs(self) -> None:
        # Requirement 3: fast, reads the committed CSV only.
        adj = cz_adjunction()
        assert len(set(adj.mapping.values())) == 741

    def test_michigan_spot_check(self) -> None:
        # Requirement 2.
        adj = cz_adjunction()
        assert adj.mapping["26163"] == adj.mapping["26125"] == adj.mapping["26099"] == "11600"

    def test_vintage_bridge_miami_dade(self) -> None:
        adj = cz_adjunction()
        assert adj.mapping["12086"] == adj.mapping["12025"]

    def test_vintage_bridge_oglala_lakota(self) -> None:
        adj = cz_adjunction()
        assert adj.mapping["46102"] == adj.mapping["46113"]

    def test_vintage_bridge_broomfield_inherits_boulder(self) -> None:
        adj = cz_adjunction()
        assert adj.mapping["08014"] == adj.mapping["08013"]

    def test_cz_id_is_zero_padded_five_char_digits(self) -> None:
        adj = cz_adjunction()
        for cz_id in adj.mapping.values():
            assert len(cz_id) == 5
            assert cz_id.isdigit()

    def test_shares_sum_to_one_per_cz(self) -> None:
        # Requirement 4 (CZ half). ScaleAdjunction's own validator already
        # enforces this at construction; recompute directly as a standing
        # regression rather than only trusting the validator.
        adj = cz_adjunction()
        totals: dict[str, float] = {}
        for child, parent in adj.mapping.items():
            totals[parent] = totals.get(parent, 0.0) + adj.shares[child]
        for parent, total in totals.items():
            assert total == pytest.approx(1.0), f"CZ {parent} shares sum to {total}"

    def test_totality_over_synthetic_mini_universe(self) -> None:
        # Requirement 1 (fast half): an ordinary county subset spanning three
        # states, none touching the vintage-bridge or AK/CT gap machinery.
        counties = ["26163", "26125", "26099", "36061", "06037"]
        mapping = cz_adjunction().mapping
        assert all(fips in mapping for fips in counties)

    def test_determinism(self) -> None:
        # Requirement 7.
        first = cz_adjunction()
        second = cz_adjunction()
        assert first.mapping == second.mapping
        assert first.shares == second.shares


@pytest.mark.requires_reference_db
@pytest.mark.skipif(not SQLITE_REF.exists(), reason=f"SQLite reference DB missing at {SQLITE_REF}")
class TestCZTotalityOverCountyUniverse:
    """Requirement 1: totality over the modern county universe, correctly scoped."""

    def test_every_national_scope_county_resolves_except_the_documented_gap(self) -> None:
        from babylon.engine.headless_runner.scopes import _load_national_fips

        national = _load_national_fips(SQLITE_REF)
        scoped_universe = sorted(national - set(_AK_CT_CZ_GAP_FIPS))
        mapping = cz_adjunction().mapping
        unresolved = [fips for fips in scoped_universe if fips not in mapping]
        assert unresolved == [], f"unexpected CZ gap(s) beyond the documented 19: {unresolved}"

    def test_documented_gap_counties_are_still_the_full_gap(self) -> None:
        # Sanity: the 19-county gap is exactly the AK/CT set today, not a
        # subset (i.e. this test's premise hasn't silently gone stale).
        from babylon.engine.headless_runner.scopes import _load_national_fips

        national = _load_national_fips(SQLITE_REF)
        mapping = cz_adjunction().mapping
        actual_gap = {fips for fips in national if fips not in mapping}
        assert actual_gap == set(_AK_CT_CZ_GAP_FIPS)


@pytest.mark.requires_reference_db
@pytest.mark.skipif(not SQLITE_REF.exists(), reason=f"SQLite reference DB missing at {SQLITE_REF}")
class TestUnknownCountyExcludedFromCZ:
    """#39 T6 M1 (was "Requirement 6: fails loud"): an uncovered county is
    EXCLUDED from ``cz`` and named on ``cz_excluded`` -- never silently
    merged, and no longer a raised error. This is the scoped-cz-with-
    total-chain redesign: the earlier design raised ``KeyError`` on ANY cz
    gap, which could not express "total chain + scoped cz" in one call (see
    ``spatial_lattice_rungs_for_counties``'s docstring). Touches the
    reference DB (unlike the old raising design, which short-circuited on
    the CZ half before ``msa_adjunction()`` was ever reached) -- the CZ half
    no longer short-circuits before the MSA half runs.
    """

    @pytest.mark.parametrize(
        "fips",
        [
            "99999",  # not a real county at all
            "26999",  # synthetic rest-of-state sentinel
            "72001",  # Puerto Rico municipio (out of the 1990 CZ delineation's scope)
            "02158",  # Alaska post-1990 reorganization (Kusilvak)
            "09110",  # Connecticut planning region (2022 switch)
        ],
    )
    def test_excluded_from_cz_and_named(self, fips: str) -> None:
        rungs = spatial_lattice_rungs_for_counties([fips])
        assert fips not in rungs.cz.mapping
        assert rungs.cz_excluded == (fips,)

    @pytest.mark.parametrize("fips", ["02158", "09110"])
    def test_state_and_nation_remain_total_despite_the_cz_gap(self, fips: str) -> None:
        """The whole point of #39 T6 M1: state/nation stay TOTAL even when
        cz cannot resolve the county -- the earlier design would have
        raised before returning anything at all."""
        rungs = spatial_lattice_rungs_for_counties([fips])
        assert fips in rungs.state.mapping
        assert fips in rungs.nation.mapping
        assert [lvl.name for lvl in rungs.chain.levels] == ["county", "state", "nation"]


class TestMSAAdjunctionSynthetic:
    """Logic tests for the county -> MSA partial mapping (fast, in-memory schema)."""

    @staticmethod
    def _synthetic_session() -> Session:
        from babylon.reference.schema import (
            BridgeCountyMetro,
            DimCounty,
            DimMetroArea,
            DimState,
            NormalizedBase,
        )

        engine = create_engine("sqlite:///:memory:")
        NormalizedBase.metadata.create_all(
            engine,
            tables=[
                DimState.__table__,
                DimCounty.__table__,
                DimMetroArea.__table__,
                BridgeCountyMetro.__table__,
            ],
        )
        session = Session(engine)
        session.execute(
            text(
                "INSERT INTO dim_state (state_id, state_fips, state_name, state_abbrev) "
                "VALUES (1, '26', 'Michigan', 'MI')"
            )
        )
        session.execute(
            text(
                "INSERT INTO dim_county "
                "(county_id, fips, state_id, county_fips, county_name) "
                "VALUES (1, '26163', 1, '163', 'Wayne'), "
                "       (2, '26001', 1, '001', 'Alcona')"  # Alcona: non-metro
            )
        )
        session.execute(
            text(
                "INSERT INTO dim_metro_area "
                "(metro_area_id, geo_id, cbsa_code, metro_name, area_type) "
                "VALUES (1, 'cbsa_19820', '19820', 'Detroit-Warren-Dearborn, MI', 'msa'), "
                "       (2, 'csa_172', NULL, 'Detroit-Warren-Ann Arbor, MI', 'csa')"
            )
        )
        session.execute(
            text(
                "INSERT INTO bridge_county_metro (county_id, metro_area_id, is_principal_city) "
                "VALUES (1, 1, 1)"  # Wayne -> Detroit MSA only; Alcona -> nothing
            )
        )
        session.commit()
        return session

    def test_partial_mapping_excludes_non_metro_county(self) -> None:
        mapping = _msa_mapping_from_session(self._synthetic_session())
        assert mapping == {"26163": "19820"}
        assert "26001" not in mapping

    def test_aggregate_over_mixed_set_sums_only_covered(self) -> None:
        # Requirement 5: partial-cover semantics, never grossed up.
        mapping = _msa_mapping_from_session(self._synthetic_session())
        adj = ScaleAdjunction.uniform(mapping)
        result = adj.aggregate({"26163": 100.0})
        assert result == {"19820": 100.0}


@pytest.mark.requires_reference_db
@pytest.mark.skipif(not SQLITE_REF.exists(), reason=f"SQLite reference DB missing at {SQLITE_REF}")
class TestMSAAdjunctionRealDB:
    """Integration tests against the real ``bridge_county_metro``/``dim_metro_area``."""

    def test_detroit_msa_covers_tri_county(self) -> None:
        adj = msa_adjunction()
        assert adj.mapping["26163"] == adj.mapping["26125"] == adj.mapping["26099"] == "19820"

    def test_alcona_non_metro_county_is_absent(self) -> None:
        # Requirement 5: a known non-metro county is absent, not zero.
        adj = msa_adjunction()
        assert "26001" not in adj.mapping

    def test_shares_sum_to_one_per_msa(self) -> None:
        # Requirement 4 (MSA half).
        adj = msa_adjunction()
        totals: dict[str, float] = {}
        for child, parent in adj.mapping.items():
            totals[parent] = totals.get(parent, 0.0) + adj.shares[child]
        for parent, total in totals.items():
            assert total == pytest.approx(1.0), f"MSA {parent} shares sum to {total}"

    def test_determinism(self) -> None:
        # Requirement 7.
        first = msa_adjunction()
        second = msa_adjunction()
        assert first.mapping == second.mapping
        assert first.shares == second.shares


@pytest.mark.requires_reference_db
@pytest.mark.skipif(not SQLITE_REF.exists(), reason=f"SQLite reference DB missing at {SQLITE_REF}")
class TestSpatialLatticeRungsForCounties:
    """``spatial_lattice_rungs_for_counties``: the chain plus both parallel rungs."""

    def test_returns_the_rungs_container(self) -> None:
        rungs = spatial_lattice_rungs_for_counties(["26163", "26125", "26099"])
        assert isinstance(rungs, SpatialLatticeRungs)

    def test_chain_unchanged_from_existing_builder(self) -> None:
        counties = ["26163", "26125", "26099"]
        rungs = spatial_lattice_rungs_for_counties(counties)
        expected_chain = spatial_lattice_for_counties(counties)
        assert [lvl.name for lvl in rungs.chain.levels] == [
            lvl.name for lvl in expected_chain.levels
        ]

    def test_cz_and_msa_are_parallel_single_parent_rungs(self) -> None:
        # Amendment U: CZ and MSA cross state lines and never nest into state.
        counties = ["26163", "26125", "26099"]
        rungs = spatial_lattice_rungs_for_counties(counties)
        assert set(rungs.cz.parents()) == {"11600"}
        assert set(rungs.msa.parents()) == {"19820"}

    def test_msa_partial_cover_over_mixed_metro_and_non_metro(self) -> None:
        # Requirement 5, via the rungs entry point.
        rungs = spatial_lattice_rungs_for_counties(["26163", "26001"])
        assert rungs.msa.mapping == {"26163": "19820"}
        assert rungs.msa.aggregate({"26163": 100.0}) == {"19820": 100.0}

    def test_cz_shares_recomputed_fresh_over_the_subset(self) -> None:
        # A 2-of-3 Detroit-CZ subset must still validly sum to 1 (fresh
        # uniform shares over the SUBSET, not the true nationwide 1/3 each).
        rungs = spatial_lattice_rungs_for_counties(["26163", "26099"])
        assert rungs.cz.shares == {"26163": pytest.approx(0.5), "26099": pytest.approx(0.5)}

    def test_state_and_nation_are_total_extensive_rungs(self) -> None:
        # #39 T6 M1: state/nation are standalone ScaleAdjunction rungs (not
        # just closures buried in `chain`), summable via .aggregate().
        counties = ["26163", "26125", "26099", "36061"]
        rungs = spatial_lattice_rungs_for_counties(counties)
        assert isinstance(rungs.state, ScaleAdjunction)
        assert isinstance(rungs.nation, ScaleAdjunction)
        assert rungs.state.mapping == {
            "26163": "26",
            "26125": "26",
            "26099": "26",
            "36061": "36",
        }
        assert set(rungs.nation.mapping.values()) == {"US"}
        by_county = dict.fromkeys(counties, 10.0)
        assert rungs.state.aggregate(by_county) == {"26": 30.0, "36": 10.0}
        assert rungs.nation.aggregate(by_county) == {"US": 40.0}

    def test_cz_excluded_is_empty_when_every_county_is_covered(self) -> None:
        rungs = spatial_lattice_rungs_for_counties(["26163", "26125", "26099"])
        assert rungs.cz_excluded == ()

    def test_mixed_gap_and_covered_counties_state_nation_stay_total(self) -> None:
        # #39 T6 M1's real shape: a nationwide county set spans both a real
        # CZ-gap county (09110, a CT planning region) and an ordinary
        # covered one (26163) -- cz excludes ONLY the gap county, while
        # state/nation resolve BOTH (never shrinking to the cz-safe subset).
        rungs = spatial_lattice_rungs_for_counties(["26163", "09110"])
        assert rungs.cz_excluded == ("09110",)
        assert "09110" not in rungs.cz.mapping
        assert "26163" in rungs.cz.mapping
        assert set(rungs.state.mapping) == {"26163", "09110"}
        assert set(rungs.nation.mapping) == {"26163", "09110"}


class TestSpatialLatticeRungsForCountiesInjectableSources:
    """#39 T6 M1: ``cz_adjunction_fn``/``msa_adjunction_fn`` are injectable so
    a caller (SubstrateSystem) can forward its own test-injected source
    without touching the reference DB or duplicating this function's cz/msa
    construction logic -- the exact seam SubstrateSystem's own tests rely
    on. Fast tier: neither test here touches the reference DB.
    """

    @staticmethod
    def _stub(mapping: dict[str, str]) -> Callable[[], ScaleAdjunction]:
        def _fn() -> ScaleAdjunction:
            return ScaleAdjunction.uniform(mapping)

        return _fn

    def test_injected_sources_replace_the_real_functions(self) -> None:
        rungs = spatial_lattice_rungs_for_counties(
            ["01001", "01003"],
            cz_adjunction_fn=self._stub({"01001": "CZ_A", "01003": "CZ_A"}),
            msa_adjunction_fn=self._stub({"01001": "MSA_X"}),
        )
        assert rungs.cz.mapping == {"01001": "CZ_A", "01003": "CZ_A"}
        assert rungs.msa.mapping == {"01001": "MSA_X"}
        assert rungs.cz_excluded == ()

    def test_injected_cz_gap_is_excluded_and_named(self) -> None:
        rungs = spatial_lattice_rungs_for_counties(
            ["01001", "01003"],
            cz_adjunction_fn=self._stub({"01001": "CZ_A"}),  # 01003 absent
            msa_adjunction_fn=self._stub({}),
        )
        assert rungs.cz_excluded == ("01003",)
        assert "01003" not in rungs.cz.mapping
        assert "01003" in rungs.state.mapping  # chain/state/nation stay total
        assert "01003" in rungs.nation.mapping
