"""Integration tests for MELT national-level SQLite adapters (spec-098 fix).

``SQLiteQCEWNationalEmploymentSource`` is a sibling of
``babylon.domain.economics.throughput.adapters.SQLiteQCEWCountyNAICSSource`` that was
NOT patched during the spec-086 QCEW-schema-drift remediation: it still reads
``fact_qcew_annual`` with ``own_code='0'`` + ``naics_code='10'`` (the pre-086
"total" row convention), but spec-086 normalized ``fact_qcew_annual`` to
6-digit leaves only and moved the county Total-Covered figure to
``fact_qcew_county_rollup``. The old query therefore matches zero rows for
every year, so ``get_national_employment`` always returns ``None`` — which is
the same bug class the throughput adapters were fixed for, manifesting here
via the MELT path (this is what causes the 3 ``test_detroit_wiring.py``
failures: ``DefaultMELTCalculator.get_melt`` reports "Employment data
unavailable" for every year).

Feature: 098-qcew-adapter-fix (review finding #2)
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.melt.adapters import (
    SQLiteBEANationalGDPSource,
    SQLiteQCEWNationalEmploymentSource,
)
from babylon.reference.database import get_normalized_session_factory

# Needs the reference SQLite DB — excluded on CI until the item-40 subset artifact lands.
pytestmark = [pytest.mark.integration, pytest.mark.requires_reference_db]

TEST_YEAR = 2022

# National employment is ~146M for 2022 (SUM across ~3200 counties in
# fact_qcew_county_rollup, own_code='0' Total). Loose bounds — this is a
# schema-drift regression guard, not a data-accuracy assertion.
NATIONAL_EMP_LOWER_BOUND = 100_000_000
NATIONAL_EMP_UPPER_BOUND = 200_000_000


@pytest.fixture(scope="module")
def session_factory():
    """Get the normalized database session factory."""
    return get_normalized_session_factory()


@pytest.fixture(scope="module")
def qcew_national_source(session_factory):
    """Create the national QCEW employment adapter."""
    return SQLiteQCEWNationalEmploymentSource(session_factory)


class TestSQLiteQCEWNationalEmploymentSource:
    """Regression tests for the post-spec-086 rollup-table read."""

    def test_get_national_employment_returns_real_total(
        self, qcew_national_source: SQLiteQCEWNationalEmploymentSource
    ):
        """National employment must be read from the rollup, not fact_qcew_annual.

        Pre-fix, this returned None for every year because own_code='0' +
        naics_code='10' no longer exist in the leaf-only fact_qcew_annual.
        """
        emp = qcew_national_source.get_national_employment(TEST_YEAR)

        assert emp is not None, (
            "National employment should be available for 2022 — "
            "same spec-086 schema-drift bug as the throughput adapters"
        )
        assert isinstance(emp, int)
        assert NATIONAL_EMP_LOWER_BOUND < emp < NATIONAL_EMP_UPPER_BOUND, (
            f"National employment {emp:,} outside sanity bounds "
            f"[{NATIONAL_EMP_LOWER_BOUND:,}, {NATIONAL_EMP_UPPER_BOUND:,}]"
        )

    def test_get_national_employment_unavailable_year_returns_none(
        self, qcew_national_source: SQLiteQCEWNationalEmploymentSource
    ):
        """A year outside the loaded data range should still return None."""
        emp = qcew_national_source.get_national_employment(1900)
        assert emp is None


class TestSQLiteBEANationalGDPSourceStillWorks:
    """Sanity check that the BEA sibling (not part of this bug) is unaffected."""

    def test_get_gdp_returns_real_total(self, session_factory):
        bea = SQLiteBEANationalGDPSource(session_factory)
        gdp = bea.get_gdp(TEST_YEAR)
        assert gdp is not None
        assert gdp > 1_000_000_000_000  # > $1T sanity floor


# Wayne County scenario year — this is the year that has no pre-aggregated
# ``fact_bea_national_industry`` row and no ``fact_qcew_county_rollup`` short
# circuit, so both sources fall through to their expensive
# SUM-across-all-US-counties fallback query on every call. Real-loop.spec.ts's
# "Step resolves the tick" (and the two other tick-resolving e2e specs) call
# ``DefaultThroughputCalculator.compute_commuter_adjusted_metrics`` once per
# territory (81 for wayne_county), and each call reaches
# ``DefaultMELTCalculator.get_melt(WAYNE_COUNTY_SCENARIO_YEAR)`` — before the
# per-year cache below, that is 81 redundant fallback SUM queries per tick,
# empirically ~300s wall-clock (see e2e regression 2026-07-15), blowing every
# 30s resolve-tick test timeout. Caching per year turns 81 queries into 1.
WAYNE_COUNTY_SCENARIO_YEAR = 2010


class TestSQLiteBEANationalGDPSourceCachesPerYear:
    """Regression guard for the 2026-07-15 ~300s resolve-tick hang.

    ``get_gdp`` must not re-hit the database for a year it has already
    resolved (the "All industries" id was already cached this way — the GDP
    value itself was not, and its fallback branch is the expensive one).
    """

    def test_second_call_same_year_does_not_requery(self, session_factory):
        calls = 0

        def counting_factory():
            nonlocal calls
            calls += 1
            return session_factory()

        bea = SQLiteBEANationalGDPSource(counting_factory)

        first = bea.get_gdp(WAYNE_COUNTY_SCENARIO_YEAR)
        calls_after_first = calls
        assert calls_after_first > 0, "the first call must open at least one session"

        second = bea.get_gdp(WAYNE_COUNTY_SCENARIO_YEAR)

        assert second == first
        assert calls == calls_after_first, (
            "a second get_gdp() call for an already-resolved year must not "
            "open another session — this is the per-territory redundant "
            "query the 2026-07-15 ~300s resolve-tick regression traced to"
        )

    def test_different_years_each_query_independently(self, session_factory):
        """The cache must be keyed by year, not a blanket "already asked once" flag."""
        bea = SQLiteBEANationalGDPSource(session_factory)

        gdp_2010 = bea.get_gdp(2010)
        gdp_2022 = bea.get_gdp(TEST_YEAR)

        assert gdp_2010 is not None
        assert gdp_2022 is not None
        assert gdp_2010 != gdp_2022


class TestSQLiteQCEWNationalEmploymentSourceCachesPerYear:
    """Same per-year caching contract as the BEA GDP sibling above."""

    def test_second_call_same_year_does_not_requery(self, session_factory):
        calls = 0

        def counting_factory():
            nonlocal calls
            calls += 1
            return session_factory()

        qcew = SQLiteQCEWNationalEmploymentSource(counting_factory)

        first = qcew.get_national_employment(WAYNE_COUNTY_SCENARIO_YEAR)
        calls_after_first = calls
        assert calls_after_first > 0, "the first call must open at least one session"

        second = qcew.get_national_employment(WAYNE_COUNTY_SCENARIO_YEAR)

        assert second == first
        assert calls == calls_after_first, (
            "a second get_national_employment() call for an already-resolved "
            "year must not open another session"
        )
