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
