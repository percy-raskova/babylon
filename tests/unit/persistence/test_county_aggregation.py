"""Unit tests for spec-065 county_aggregation helpers.

Covers T037 (aggregate_survival_for_county),
T037a (aggregate_consciousness_for_county including bridge-mapping
corner tests),
T038 (fetch_population_for_county_at_tick),
T039 (fetch_employment_proxy_for_county_at_tick).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.engine.factories import create_bourgeoisie, create_proletariat
from babylon.models.entities.consciousness import TernaryConsciousness
from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.enums import SocialRole
from babylon.models.world_state import WorldState
from babylon.persistence.county_aggregation import (
    BridgeMappingError,
    ReferenceDataMissingError,
    _ideology_to_ternary,
    aggregate_consciousness_for_county,
    aggregate_survival_for_county,
    fetch_employment_proxy_for_county_at_tick,
    fetch_population_for_county_at_tick,
)

SQLITE_REF = Path("data/sqlite/marxist-data-3NF.sqlite")


def _make_entity(
    eid: str,
    *,
    county_fips: str | None,
    population: int = 100,
    p_acquiescence: float = 0.5,
    p_revolution: float = 0.3,
    class_consciousness: float = 0.5,
    national_identity: float = 0.5,
) -> SocialClass:
    """Build a SocialClass entity with the spec-065 attribution fields set."""
    return SocialClass(
        id=eid,
        name=f"Test {eid}",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=1.0,
        ideology=IdeologicalProfile(
            class_consciousness=class_consciousness,
            national_identity=national_identity,
        ),
        p_acquiescence=p_acquiescence,
        p_revolution=p_revolution,
        population=population,
        county_fips=county_fips,
    )


# ----------------------------------------------------------------------
# T037a: _ideology_to_ternary — bridge mapping corners
# ----------------------------------------------------------------------


class TestBridgeMappingCorners:
    """Verify the simplex mapping at each (cc, ni) corner per R10."""

    def test_pure_revolutionary(self) -> None:
        """(cc=1, ni=0) → (r=1, l=0, f=0)."""
        r, l_, f = _ideology_to_ternary(1.0, 0.0)
        assert r == pytest.approx(1.0)
        assert l_ == pytest.approx(0.0)
        assert f == pytest.approx(0.0)

    def test_pure_fascist(self) -> None:
        """(cc=0, ni=1) → (r=0, l=0, f=1)."""
        r, l_, f = _ideology_to_ternary(0.0, 1.0)
        assert r == pytest.approx(0.0)
        assert l_ == pytest.approx(0.0)
        assert f == pytest.approx(1.0)

    def test_pure_liberal_unorganized(self) -> None:
        """(cc=0, ni=0) → (r=0, l=1, f=0) — Jackson's unorganized default."""
        r, l_, f = _ideology_to_ternary(0.0, 0.0)
        assert r == pytest.approx(0.0)
        assert l_ == pytest.approx(1.0)
        assert f == pytest.approx(0.0)

    def test_jackson_midpoint(self) -> None:
        """(cc=0.5, ni=0.5) → (r=0.25, l=0.5, f=0.25) — liberal hegemony."""
        r, l_, f = _ideology_to_ternary(0.5, 0.5)
        assert r == pytest.approx(0.25)
        assert l_ == pytest.approx(0.5)
        assert f == pytest.approx(0.25)

    def test_national_revolutionary_routes_to_liberal(self) -> None:
        """(cc=1, ni=1) is degenerate; r=0, f=0 so l=1 — routes to liberal."""
        r, l_, f = _ideology_to_ternary(1.0, 1.0)
        assert r == pytest.approx(0.0)
        assert l_ == pytest.approx(1.0)
        assert f == pytest.approx(0.0)

    def test_simplex_invariant_arbitrary(self) -> None:
        """For 25 sample points, r + l + f sums to 1.0 within 1e-9."""
        import itertools

        for cc, ni in itertools.product(
            [0.0, 0.1, 0.3, 0.7, 0.9, 1.0],
            [0.0, 0.2, 0.5, 0.8, 1.0],
        ):
            r, l_, f = _ideology_to_ternary(cc, ni)
            assert abs(r + l_ + f - 1.0) < 1e-9, f"failed at cc={cc}, ni={ni}"

    def test_bridge_mapping_error_not_raised_in_practice(self) -> None:
        """The defensive BridgeMappingError check should never trip for
        well-formed inputs. This test asserts the error type exists."""
        assert issubclass(BridgeMappingError, RuntimeError)


# ----------------------------------------------------------------------
# T037: aggregate_survival_for_county
# ----------------------------------------------------------------------


class TestAggregateSurvival:
    """Population-weighted survival aggregation per county."""

    def test_empty_county_returns_zeros(self) -> None:
        """No matching entities → (0.0, 0.0, 0). Caller should emit a warning."""
        state = WorldState(tick=0, entities={})
        p_acq, p_rev, pop = aggregate_survival_for_county(state, "26163")
        assert p_acq == 0.0
        assert p_rev == 0.0
        assert pop == 0

    def test_no_matching_county_fips(self) -> None:
        """Entities exist but none have the requested fips."""
        e1 = _make_entity("C001", county_fips="26099")
        e2 = _make_entity("C002", county_fips=None)
        state = WorldState(tick=0, entities={"C001": e1, "C002": e2})
        p_acq, p_rev, pop = aggregate_survival_for_county(state, "26163")
        assert (p_acq, p_rev, pop) == (0.0, 0.0, 0)

    def test_single_entity_mean(self) -> None:
        """Single entity → its own values."""
        e = _make_entity(
            "C001",
            county_fips="26163",
            population=1000,
            p_acquiescence=0.7,
            p_revolution=0.2,
        )
        state = WorldState(tick=0, entities={"C001": e})
        p_acq, p_rev, pop = aggregate_survival_for_county(state, "26163")
        assert p_acq == pytest.approx(0.7)
        assert p_rev == pytest.approx(0.2)
        assert pop == 1000

    def test_population_weighted_mean(self) -> None:
        """Two entities, weights are populations.

        Entity A: pop=300, p_acq=0.8
        Entity B: pop=100, p_acq=0.4
        Expected mean: (300*0.8 + 100*0.4) / 400 = 280/400 = 0.7
        """
        a = _make_entity("C001", county_fips="26163", population=300, p_acquiescence=0.8)
        b = _make_entity("C002", county_fips="26163", population=100, p_acquiescence=0.4)
        state = WorldState(tick=0, entities={"C001": a, "C002": b})
        p_acq, _p_rev, pop = aggregate_survival_for_county(state, "26163")
        assert p_acq == pytest.approx(0.7)
        assert pop == 400

    def test_zero_population_entities_skipped(self) -> None:
        """Entities with population=0 are excluded from the weighted mean."""
        a = _make_entity("C001", county_fips="26163", population=100, p_acquiescence=0.5)
        b = _make_entity("C002", county_fips="26163", population=0, p_acquiescence=0.9)
        state = WorldState(tick=0, entities={"C001": a, "C002": b})
        p_acq, _p_rev, pop = aggregate_survival_for_county(state, "26163")
        assert p_acq == pytest.approx(0.5)  # B excluded → A alone
        assert pop == 100

    def test_only_matching_county_entities_counted(self) -> None:
        """Other-county entities don't pollute the aggregate."""
        in_wayne = _make_entity("C001", county_fips="26163", population=200, p_revolution=0.6)
        in_macomb = _make_entity("C002", county_fips="26099", population=500, p_revolution=0.1)
        unattributed = _make_entity("C003", county_fips=None, population=1000, p_revolution=0.99)
        state = WorldState(
            tick=0,
            entities={"C001": in_wayne, "C002": in_macomb, "C003": unattributed},
        )
        _p_acq, p_rev, pop = aggregate_survival_for_county(state, "26163")
        assert p_rev == pytest.approx(0.6)
        assert pop == 200


# ----------------------------------------------------------------------
# T037a: aggregate_consciousness_for_county
# ----------------------------------------------------------------------


class TestAggregateConsciousness:
    """Bridge-mapped, population-weighted ternary consciousness."""

    def test_empty_county_returns_substrate_default(self) -> None:
        """No matching entities → TernaryConsciousness defaults (0.3, 0.6, 0.1)."""
        state = WorldState(tick=0, entities={})
        tc = aggregate_consciousness_for_county(state, "26163")
        assert tc.r == pytest.approx(0.3)
        assert tc.l == pytest.approx(0.6)
        assert tc.f == pytest.approx(0.1)

    def test_pure_revolutionary_county(self) -> None:
        """One entity, (cc=1, ni=0) → output approximately (1, 0, 0)."""
        e = _make_entity(
            "C001",
            county_fips="26163",
            population=100,
            class_consciousness=1.0,
            national_identity=0.0,
        )
        state = WorldState(tick=0, entities={"C001": e})
        tc = aggregate_consciousness_for_county(state, "26163")
        assert tc.r == pytest.approx(1.0)
        assert tc.l == pytest.approx(0.0)
        assert tc.f == pytest.approx(0.0)

    def test_pure_fascist_county(self) -> None:
        """One entity, (cc=0, ni=1) → output approximately (0, 0, 1)."""
        e = _make_entity(
            "C001",
            county_fips="26163",
            population=100,
            class_consciousness=0.0,
            national_identity=1.0,
        )
        state = WorldState(tick=0, entities={"C001": e})
        tc = aggregate_consciousness_for_county(state, "26163")
        assert tc.r == pytest.approx(0.0)
        assert tc.l == pytest.approx(0.0)
        assert tc.f == pytest.approx(1.0)

    def test_jackson_midpoint_county(self) -> None:
        """One entity at (0.5, 0.5) → (r=0.25, l=0.5, f=0.25)."""
        e = _make_entity(
            "C001",
            county_fips="26163",
            population=100,
            class_consciousness=0.5,
            national_identity=0.5,
        )
        state = WorldState(tick=0, entities={"C001": e})
        tc = aggregate_consciousness_for_county(state, "26163")
        assert tc.r == pytest.approx(0.25)
        assert tc.l == pytest.approx(0.5)
        assert tc.f == pytest.approx(0.25)

    def test_population_weighted_average_of_two(self) -> None:
        """Two entities; check the weighted mix is computed correctly.

        Entity C001: pop=300, (cc=1, ni=0) → mapped (r=1, l=0, f=0)
        Entity C002: pop=100, (cc=0, ni=1) → mapped (r=0, l=0, f=1)
        Expected aggregate: (r=0.75, l=0, f=0.25).
        """
        a = _make_entity(
            "C001",
            county_fips="26163",
            population=300,
            class_consciousness=1.0,
            national_identity=0.0,
        )
        b = _make_entity(
            "C002",
            county_fips="26163",
            population=100,
            class_consciousness=0.0,
            national_identity=1.0,
        )
        state = WorldState(tick=0, entities={"C001": a, "C002": b})
        tc = aggregate_consciousness_for_county(state, "26163")
        assert tc.r == pytest.approx(0.75)
        assert tc.l == pytest.approx(0.0)
        assert tc.f == pytest.approx(0.25)

    def test_simplex_invariant_preserved(self) -> None:
        """For an arbitrary mix, r + l + f ≈ 1 within tight tolerance."""
        entities = {
            f"C{i:03d}": _make_entity(
                f"C{i:03d}",
                county_fips="26163",
                population=10 + i,
                class_consciousness=(i % 10) / 10.0,
                national_identity=((i * 3) % 7) / 7.0,
            )
            for i in range(20)
        }
        state = WorldState(tick=0, entities=entities)
        tc = aggregate_consciousness_for_county(state, "26163")
        assert abs(tc.r + tc.l + tc.f - 1.0) < 1e-9

    def test_unattributed_entities_excluded(self) -> None:
        """Entities with county_fips=None do not affect Wayne's aggregate."""
        in_wayne = _make_entity(
            "C001",
            county_fips="26163",
            population=100,
            class_consciousness=1.0,
            national_identity=0.0,
        )
        unattributed = _make_entity(
            "C002",
            county_fips=None,
            population=10000,
            class_consciousness=0.0,
            national_identity=1.0,
        )
        state = WorldState(tick=0, entities={"C001": in_wayne, "C002": unattributed})
        tc = aggregate_consciousness_for_county(state, "26163")
        # C002 is unattributed; C001 alone drives the aggregate.
        assert tc.r == pytest.approx(1.0)
        assert tc.f == pytest.approx(0.0)

    def test_result_is_ternary_consciousness_instance(self) -> None:
        """Return value type is the spec-034 TernaryConsciousness model."""
        e = _make_entity("C001", county_fips="26163")
        state = WorldState(tick=0, entities={"C001": e})
        tc = aggregate_consciousness_for_county(state, "26163")
        assert isinstance(tc, TernaryConsciousness)


# ----------------------------------------------------------------------
# T038: fetch_population_for_county_at_tick — integration with SQLite
# ----------------------------------------------------------------------


@pytest.mark.requires_reference_db
@pytest.mark.skipif(
    not SQLITE_REF.exists(),
    reason=f"SQLite reference DB missing at {SQLITE_REF}",
)
class TestFetchPopulation:
    """Integration tests against the real SQLite reference DB."""

    def test_wayne_2010_within_plausible_range(self) -> None:
        """Wayne County 2010 population should be in the millions.

        Actual ACS 2010 population: ~1.82M. Our proxy via Census income
        SUM gives ~1.77M (verified during reconciliation). Accept any
        value in [1.5M, 2.5M] as plausible.
        """
        pop = fetch_population_for_county_at_tick(SQLITE_REF, "26163", tick=0, start_year=2010)
        assert 1_500_000 <= pop <= 2_500_000, f"Wayne 2010 pop out of range: {pop}"

    def test_tick_maps_to_year_via_weekly_cadence(self) -> None:
        """tick=52 with start_year=2010 should resolve to year 2011."""
        pop_at_year_2011 = fetch_population_for_county_at_tick(
            SQLITE_REF, "26163", tick=52, start_year=2010
        )
        # Should still be a Wayne population, not zero
        assert pop_at_year_2011 > 1_000_000

    def test_unknown_fips_raises(self) -> None:
        """A bogus FIPS code raises ReferenceDataMissingError."""
        with pytest.raises(ReferenceDataMissingError):
            fetch_population_for_county_at_tick(SQLITE_REF, "99999", tick=0, start_year=2010)

    def test_missing_sqlite_path_raises(self, tmp_path: Path) -> None:
        """A non-existent SQLite path raises FileNotFoundError."""
        missing = tmp_path / "nonexistent.sqlite"
        with pytest.raises(FileNotFoundError):
            fetch_population_for_county_at_tick(missing, "26163", tick=0, start_year=2010)


# ----------------------------------------------------------------------
# T039: fetch_employment_proxy_for_county_at_tick — integration with SQLite
# ----------------------------------------------------------------------


@pytest.mark.requires_reference_db
@pytest.mark.skipif(
    not SQLITE_REF.exists(),
    reason=f"SQLite reference DB missing at {SQLITE_REF}",
)
class TestFetchEmploymentProxy:
    """Integration tests against the real SQLite reference DB."""

    def test_wayne_2010_returns_positive_float(self) -> None:
        """Wayne County 2010 annual-average employment > 0.

        Post spec-067 normalization: SUM over canonical leaves
        (``naics_level=6 AND own_code in {'1','2','3','5'}``). QCEW
        suppresses 6-digit cells for employer confidentiality, so the
        leaf SUM is systematically ~10-30 % below the BLS Total Covered
        rollup value (Wayne 2010 BLS-published ~660K → post-067 SUM
        ~561K). This test verifies the band [400K, 900K] which
        accommodates both the original rollup target and the post-067
        suppression-aware floor.
        """
        emp = fetch_employment_proxy_for_county_at_tick(
            SQLITE_REF, "26163", tick=0, start_year=2010
        )
        assert emp > 0
        assert 400_000 < emp < 900_000, f"Wayne 2010 emp out of band: {emp}"

    def test_tick_maps_to_year_via_weekly_cadence(self) -> None:
        """tick=104 with start_year=2010 should resolve to year 2012."""
        emp_at_year_2012 = fetch_employment_proxy_for_county_at_tick(
            SQLITE_REF, "26163", tick=104, start_year=2010
        )
        assert emp_at_year_2012 > 0

    def test_unknown_fips_raises(self) -> None:
        """A bogus FIPS code raises ReferenceDataMissingError."""
        with pytest.raises(ReferenceDataMissingError):
            fetch_employment_proxy_for_county_at_tick(SQLITE_REF, "99999", tick=0, start_year=2010)


# ----------------------------------------------------------------------
# Cross-county variation smoke test (integration)
# ----------------------------------------------------------------------


@pytest.mark.requires_reference_db
@pytest.mark.skipif(
    not SQLITE_REF.exists(),
    reason=f"SQLite reference DB missing at {SQLITE_REF}",
)
class TestCrossCountyVariation:
    """Demonstrates the helpers produce non-uniform per-county values
    (which is the whole point of the spec-065 reconciliation — kill
    the uniform-county problem identified in the spec-064 audit)."""

    def test_wayne_vs_macomb_have_different_populations(self) -> None:
        """Wayne (26163) and Macomb (26099) should have distinct pop values."""
        wayne = fetch_population_for_county_at_tick(SQLITE_REF, "26163", tick=0, start_year=2010)
        macomb = fetch_population_for_county_at_tick(SQLITE_REF, "26099", tick=0, start_year=2010)
        # Both should be in the millions but distinct
        assert wayne != macomb
        # Wayne should be bigger (Detroit metro core)
        assert wayne > macomb

    def test_wayne_vs_macomb_have_different_employment(self) -> None:
        """Wayne and Macomb should have distinct QCEW employment."""
        wayne = fetch_employment_proxy_for_county_at_tick(
            SQLITE_REF, "26163", tick=0, start_year=2010
        )
        macomb = fetch_employment_proxy_for_county_at_tick(
            SQLITE_REF, "26099", tick=0, start_year=2010
        )
        assert wayne != macomb
        assert wayne > macomb


# ----------------------------------------------------------------------
# Factory integration: spec-065 uses factories to build per-county entities
# ----------------------------------------------------------------------


class TestFactoryIntegration:
    """Verify the factories pass county_fips through correctly so the
    aggregators see real attribution."""

    def test_factory_built_entities_aggregate_correctly(self) -> None:
        """create_proletariat + create_bourgeoisie with county_fips set
        produce entities the aggregator can sum over."""
        prole = create_proletariat(
            id="C001",
            county_fips="26163",
            p_acquiescence=0.6,
            p_revolution=0.4,
        )
        # Bourgeoisie typically has bigger population in some models;
        # use realistic small ratio (1:10).
        bourg = create_bourgeoisie(
            id="C002",
            county_fips="26163",
            p_acquiescence=0.9,
            p_revolution=0.05,
        )
        # Tag populations explicitly via model_copy since factory doesn't
        # expose population (SocialClass default is 1).
        prole = prole.model_copy(update={"population": 800})
        bourg = bourg.model_copy(update={"population": 200})

        state = WorldState(tick=0, entities={"C001": prole, "C002": bourg})
        p_acq, p_rev, pop = aggregate_survival_for_county(state, "26163")
        assert pop == 1000
        # Weighted: (800 * 0.6 + 200 * 0.9) / 1000 = (480 + 180) / 1000 = 0.66
        assert p_acq == pytest.approx(0.66)
        # Weighted: (800 * 0.4 + 200 * 0.05) / 1000 = (320 + 10) / 1000 = 0.33
        assert p_rev == pytest.approx(0.33)
