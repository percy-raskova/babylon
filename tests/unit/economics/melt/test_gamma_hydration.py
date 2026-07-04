"""Unit tests for SQLiteGammaHydrationSource (spec-102 gamma hydration).

Kills the hardcoded seam in ``basket_visibility.py`` (MVP_ALPHA=0.25,
MVP_GAMMA_IMPORT=0.35) by hydrating both coefficients per calendar year:

- alpha: Sigma(fact_bilateral_trade_annual.imports_usd_millions) /
  Sigma(fact_bea_final_demand_annual.total_final_uses_millions), same
  annual time_id.
- gamma_import: 1 / fact_hickel_erdi_annual.erdi for (year, scale_type).

TDD RED phase: SQLiteGammaHydrationSource does not exist yet.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session, sessionmaker

from babylon.reference.schema import (
    DimBEAIndustry,
    DimCountry,
    DimTime,
    FactBEAFinalDemandAnnual,
    FactBilateralTradeAnnual,
    FactHickelERDIAnnual,
)


@pytest.fixture
def seeded_session_factory(
    reference_sqlite_session_factory: sessionmaker[Session],
) -> Iterator[sessionmaker[Session]]:
    """In-memory reference DB seeded with 2012 trade/BEA/Hickel fixtures.

    2012 real Hickel Intensive ERDI = 7.86 (per babylon_hickel_final.csv,
    verified directly — see specs/102-gamma-shocks/research.md R1).
    Trade + BEA final-demand values are synthetic but proportioned to
    produce a plausible ~0.25 import share.
    """
    with reference_sqlite_session_factory() as session:
        t2012 = DimTime(year=2012, is_annual=True)
        session.add(t2012)
        session.flush()

        # Two trading partners: imports sum to 2_500_000 (USD millions).
        china = DimCountry(cty_code="CHN", country_name="China")
        canada = DimCountry(cty_code="CAN", country_name="Canada")
        session.add_all([china, canada])
        session.flush()
        session.add_all(
            [
                FactBilateralTradeAnnual(
                    time_id=t2012.time_id,
                    country_id=china.country_id,
                    imports_usd_millions=1_500_000,
                    exports_usd_millions=500_000,
                    total_trade_usd_millions=2_000_000,
                ),
                FactBilateralTradeAnnual(
                    time_id=t2012.time_id,
                    country_id=canada.country_id,
                    imports_usd_millions=1_000_000,
                    exports_usd_millions=900_000,
                    total_trade_usd_millions=1_900_000,
                ),
            ]
        )

        # Two BEA commodities: final uses sum to 10_000_000 (USD millions).
        # -> alpha = 2_500_000 / 10_000_000 = 0.25
        farms = DimBEAIndustry(bea_code="111", industry_name="Farms", bea_level=3)
        motor = DimBEAIndustry(bea_code="336", industry_name="Motor vehicles", bea_level=3)
        session.add_all([farms, motor])
        session.flush()
        session.add_all(
            [
                FactBEAFinalDemandAnnual(
                    time_id=t2012.time_id,
                    bea_industry_id=farms.bea_industry_id,
                    total_final_uses_millions=4_000_000,
                ),
                FactBEAFinalDemandAnnual(
                    time_id=t2012.time_id,
                    bea_industry_id=motor.bea_industry_id,
                    total_final_uses_millions=6_000_000,
                ),
            ]
        )

        session.add(
            FactHickelERDIAnnual(
                time_id=t2012.time_id,
                scale_type="Intensive",
                erdi=7.86,
                annual_drain_usd_billions=11250.0,
                alpha=0.9295392953929539,
                core_gain_per_capita_usd=9000.0,
                is_anchor_year=False,
                china_inflection=False,
                cumulative_drain=280000.0,
                source="Hickel_Sullivan_Zoomkawala_2021",
            )
        )
        session.commit()

    yield reference_sqlite_session_factory


@pytest.mark.unit
class TestGetAlpha:
    def test_hydrated_year_returns_import_share(
        self, seeded_session_factory: sessionmaker[Session]
    ) -> None:
        from babylon.economics.melt.gamma_hydration import SQLiteGammaHydrationSource

        source = SQLiteGammaHydrationSource(seeded_session_factory)

        alpha = source.get_alpha(2012)

        assert alpha is not None
        assert alpha == pytest.approx(0.25)

    def test_year_without_trade_data_returns_none(
        self, seeded_session_factory: sessionmaker[Session]
    ) -> None:
        from babylon.economics.melt.gamma_hydration import SQLiteGammaHydrationSource

        source = SQLiteGammaHydrationSource(seeded_session_factory)

        assert source.get_alpha(2020) is None

    def test_year_without_final_demand_data_returns_none(
        self, reference_sqlite_session_factory: sessionmaker[Session]
    ) -> None:
        """Trade data present but no BEA final-demand rows -> None (no div-by-zero)."""
        from babylon.economics.melt.gamma_hydration import SQLiteGammaHydrationSource

        with reference_sqlite_session_factory() as session:
            t2013 = DimTime(year=2013, is_annual=True)
            session.add(t2013)
            session.flush()
            china = DimCountry(cty_code="CHN", country_name="China")
            session.add(china)
            session.flush()
            session.add(
                FactBilateralTradeAnnual(
                    time_id=t2013.time_id,
                    country_id=china.country_id,
                    imports_usd_millions=1_000_000,
                    exports_usd_millions=500_000,
                    total_trade_usd_millions=1_500_000,
                )
            )
            session.commit()

        source = SQLiteGammaHydrationSource(reference_sqlite_session_factory)
        assert source.get_alpha(2013) is None


@pytest.mark.unit
class TestGetGammaImport:
    def test_hydrated_year_returns_inverse_erdi(
        self, seeded_session_factory: sessionmaker[Session]
    ) -> None:
        from babylon.economics.melt.gamma_hydration import SQLiteGammaHydrationSource

        source = SQLiteGammaHydrationSource(seeded_session_factory)

        gamma_import = source.get_gamma_import(2012)

        assert gamma_import is not None
        assert gamma_import == pytest.approx(1.0 / 7.86)
        # Dimensionally required: must land in (0, 1] for the harmonic
        # gamma_basket formula.
        assert 0.0 < gamma_import <= 1.0

    def test_year_outside_hickel_coverage_returns_none(
        self, seeded_session_factory: sessionmaker[Session]
    ) -> None:
        """2020 has no fact_hickel_erdi_annual row (data gap, spec.md FR-102-2)."""
        from babylon.economics.melt.gamma_hydration import SQLiteGammaHydrationSource

        source = SQLiteGammaHydrationSource(seeded_session_factory)

        assert source.get_gamma_import(2020) is None

    def test_wrong_scale_type_returns_none(
        self, seeded_session_factory: sessionmaker[Session]
    ) -> None:
        """Only 'Intensive' is seeded for 2012 -> 'Extensive' lookup misses."""
        from babylon.economics.melt.gamma_hydration import SQLiteGammaHydrationSource

        source = SQLiteGammaHydrationSource(seeded_session_factory)

        assert source.get_gamma_import(2012, scale_type="Extensive") is None

    def test_default_scale_type_is_intensive(
        self, seeded_session_factory: sessionmaker[Session]
    ) -> None:
        from babylon.economics.melt.gamma_hydration import SQLiteGammaHydrationSource

        source = SQLiteGammaHydrationSource(seeded_session_factory)

        explicit = source.get_gamma_import(2012, scale_type="Intensive")
        default = source.get_gamma_import(2012)

        assert explicit == default
