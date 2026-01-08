"""Unit tests for employment industry loader."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from babylon.data.employment_industry import EmploymentIndustryLoader
from babylon.data.loader_base import LoaderConfig
from babylon.data.normalize import schema as _schema  # noqa: F401
from babylon.data.normalize.database import NormalizedBase
from babylon.data.normalize.schema import (
    DimCounty,
    DimEmploymentArea,
    DimIndustry,
    DimOwnership,
    DimState,
    FactEmploymentIndustryAnnual,
)


def _make_session() -> Session:
    engine = create_engine("duckdb:///:memory:")
    NormalizedBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    return session_factory()


def test_employment_industry_loader_ingests_area_file(tmp_path: Path) -> None:
    session = _make_session()
    try:
        state = DimState(state_fips="01", state_name="Alabama", state_abbrev="AL")
        session.add(state)
        session.flush()
        county = DimCounty(
            fips="01029",
            state_id=state.state_id,
            county_fips="029",
            county_name="Cleburne County",
        )
        session.add(county)
        session.commit()

        data_dir = tmp_path / "employment_industry" / "2024.annual.by_area"
        data_dir.mkdir(parents=True)
        file_path = data_dir / "2024.annual 01029 Cleburne County, Alabama.csv"
        file_path.write_text(
            '"area_fips","own_code","industry_code","agglvl_code","size_code","year","qtr",'
            '"disclosure_code","area_title","own_title","industry_title","agglvl_title",'
            '"size_title","annual_avg_estabs_count","annual_avg_emplvl","total_annual_wages",'
            '"taxable_annual_wages","annual_contributions","annual_avg_wkly_wage","avg_annual_pay",'
            '"lq_disclosure_code","lq_annual_avg_estabs_count","lq_annual_avg_emplvl",'
            '"lq_total_annual_wages","lq_taxable_annual_wages","lq_annual_contributions",'
            '"lq_annual_avg_wkly_wage","lq_avg_annual_pay","oty_disclosure_code",'
            '"oty_annual_avg_estabs_count_chg","oty_annual_avg_estabs_count_pct_chg",'
            '"oty_annual_avg_emplvl_chg","oty_annual_avg_emplvl_pct_chg","oty_total_annual_wages_chg",'
            '"oty_total_annual_wages_pct_chg","oty_taxable_annual_wages_chg","oty_taxable_annual_wages_pct_chg",'
            '"oty_annual_contributions_chg","oty_annual_contributions_pct_chg",'
            '"oty_annual_avg_wkly_wage_chg","oty_annual_avg_wkly_wage_pct_chg",'
            '"oty_avg_annual_pay_chg","oty_avg_annual_pay_pct_chg"\n'
            '"01029","0","10","70","0","2024","A","","Cleburne County, Alabama",'
            '"Total Covered","10 Total, all industries","County, Total Covered",'
            '"All establishment sizes",289,2721,149178424,21431529,118954,1054,54823,'
            '"",1.00,1.00,1.00,1.00,1.00,1.00,1.00,'
            '"",3,1.0,155,6.0,7568752,5.3,799722,3.9,-31768,-21.1,-7,-0.7,-357,-0.6\n',
            encoding="utf-8",
        )

        loader = EmploymentIndustryLoader(LoaderConfig())
        stats = loader.load(session, reset=True, verbose=False, data_path=data_dir.parent)

        assert stats.facts_loaded.get("employment_industry_annual") == 1
        area = session.execute(select(DimEmploymentArea)).scalar_one()
        assert area.area_code == "01029"
        assert area.area_type == "county"
        assert area.county_id == county.county_id

        industry = session.execute(select(DimIndustry)).scalar_one()
        ownership = session.execute(select(DimOwnership)).scalar_one()
        fact = session.execute(select(FactEmploymentIndustryAnnual)).scalar_one()
        assert fact.area_id == area.area_id
        assert fact.industry_id == industry.industry_id
        assert fact.ownership_id == ownership.ownership_id
        assert fact.annual_avg_emplvl == 2721
    finally:
        session.close()
