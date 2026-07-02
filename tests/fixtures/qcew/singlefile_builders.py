"""Builders for miniature BLS QCEW annual singlefile CSVs (spec-086 tests).

The header below was captured verbatim from
``/media/user/data/babylon-data/qcew/2010.annual.singlefile.csv`` on
2026-07-02 (research R1: byte-identical across 2010 and 2023). BLS quoting
convention: string fields quoted, numeric fields bare.

Suppression semantics reproduced exactly (research R1): a suppressed cell
has ``disclosure_code="N"`` with employment/wage magnitudes written as
literal ``0`` while ``annual_avg_estabs`` stays populated.

Aggregation levels emitted (county family):
``70`` county total (own ``0``, industry ``10``) · ``71`` county ×
ownership (industry ``10``) · ``74``–``77`` NAICS 2/3/4/5-digit subtotals ·
``78`` 6-digit leaves. ``10`` is the national Total-Covered row
(area ``US000``) used by the SC-005 national check.
"""

from __future__ import annotations

from pathlib import Path

SINGLEFILE_HEADER = (
    '"area_fips","own_code","industry_code","agglvl_code","size_code","year","qtr",'
    '"disclosure_code","annual_avg_estabs","annual_avg_emplvl","total_annual_wages",'
    '"taxable_annual_wages","annual_contributions","annual_avg_wkly_wage","avg_annual_pay",'
    '"lq_disclosure_code","lq_annual_avg_estabs","lq_annual_avg_emplvl",'
    '"lq_total_annual_wages","lq_taxable_annual_wages","lq_annual_contributions",'
    '"lq_annual_avg_wkly_wage","lq_avg_annual_pay","oty_disclosure_code",'
    '"oty_annual_avg_estabs_chg","oty_annual_avg_estabs_pct_chg",'
    '"oty_annual_avg_emplvl_chg","oty_annual_avg_emplvl_pct_chg",'
    '"oty_total_annual_wages_chg","oty_total_annual_wages_pct_chg",'
    '"oty_taxable_annual_wages_chg","oty_taxable_annual_wages_pct_chg",'
    '"oty_annual_contributions_chg","oty_annual_contributions_pct_chg",'
    '"oty_annual_avg_wkly_wage_chg","oty_annual_avg_wkly_wage_pct_chg",'
    '"oty_avg_annual_pay_chg","oty_avg_annual_pay_pct_chg"'
)


def _row(
    *,
    area_fips: str,
    own_code: str,
    industry_code: str,
    agglvl_code: int,
    year: int,
    disclosure_code: str,
    estabs: int,
    employment: int,
    wages: int,
    avg_wkly_wage: int = 0,
    avg_annual_pay: int = 0,
) -> str:
    """One singlefile line in BLS quoting convention (strings quoted, numerics bare)."""
    taxable = 0
    contributions = 0
    lq = '"",0,0,0,0,0,0,0'
    oty = '"",0,0.0,0,0.0,0,0.0,0,0.0,0,0.0,0,0.0,0,0.0'
    return (
        f'"{area_fips}","{own_code}","{industry_code}","{agglvl_code}","0",'
        f'"{year}","A","{disclosure_code}",'
        f"{estabs},{employment},{wages},{taxable},{contributions},"
        f"{avg_wkly_wage},{avg_annual_pay},{lq},{oty}"
    )


def leaf_row(
    fips: str,
    own_code: str,
    naics6: str,
    *,
    year: int = 2010,
    estabs: int,
    employment: int = 0,
    wages: int = 0,
    suppressed: bool = False,
) -> str:
    """Agglvl-78 county × 6-digit-NAICS × ownership leaf.

    ``suppressed=True`` reproduces BLS masking: disclosure ``N`` with
    employment/wages forced to literal 0 (establishments kept).
    """
    return _row(
        area_fips=fips,
        own_code=own_code,
        industry_code=naics6,
        agglvl_code=78,
        year=year,
        disclosure_code="N" if suppressed else "",
        estabs=estabs,
        employment=0 if suppressed else employment,
        wages=0 if suppressed else wages,
    )


def constraint_70_row(
    fips: str,
    *,
    year: int = 2010,
    estabs: int,
    employment: int,
    wages: int,
    suppressed: bool = False,
) -> str:
    """Agglvl-70 county Total Covered (own ``0``, industry ``10``)."""
    return _row(
        area_fips=fips,
        own_code="0",
        industry_code="10",
        agglvl_code=70,
        year=year,
        disclosure_code="N" if suppressed else "",
        estabs=estabs,
        employment=0 if suppressed else employment,
        wages=0 if suppressed else wages,
    )


def constraint_71_row(
    fips: str,
    own_code: str,
    *,
    year: int = 2010,
    estabs: int,
    employment: int,
    wages: int,
    suppressed: bool = False,
) -> str:
    """Agglvl-71 county × ownership total (industry ``10``)."""
    return _row(
        area_fips=fips,
        own_code=own_code,
        industry_code="10",
        agglvl_code=71,
        year=year,
        disclosure_code="N" if suppressed else "",
        estabs=estabs,
        employment=0 if suppressed else employment,
        wages=0 if suppressed else wages,
    )


def naics_constraint_row(
    fips: str,
    own_code: str,
    naics: str,
    *,
    year: int = 2010,
    estabs: int,
    employment: int,
    wages: int,
    suppressed: bool = False,
) -> str:
    """Agglvl-74..77 county × ownership × intermediate-NAICS subtotal.

    The agglvl code is derived from the NAICS string per the BLS county
    family: 2-digit (incl. range sectors like ``31-33``) → 74, 3-digit →
    75, 4-digit → 76, 5-digit → 77.
    """
    stripped = naics.replace("-", "")
    if "-" in naics or len(naics) == 2:
        agglvl = 74
    elif len(naics) == 3:
        agglvl = 75
    elif len(naics) == 4:
        agglvl = 76
    elif len(naics) == 5:
        agglvl = 77
    else:
        msg = f"not an intermediate NAICS code: {naics!r} (len {len(stripped)})"
        raise ValueError(msg)
    return _row(
        area_fips=fips,
        own_code=own_code,
        industry_code=naics,
        agglvl_code=agglvl,
        year=year,
        disclosure_code="N" if suppressed else "",
        estabs=estabs,
        employment=0 if suppressed else employment,
        wages=0 if suppressed else wages,
    )


def us_total_row(*, year: int = 2010, estabs: int, employment: int, wages: int) -> str:
    """Agglvl-10 national Total Covered row (area ``US000``) for SC-005."""
    return _row(
        area_fips="US000",
        own_code="0",
        industry_code="10",
        agglvl_code=10,
        year=year,
        disclosure_code="",
        estabs=estabs,
        employment=employment,
        wages=wages,
    )


def write_mini_singlefile(directory: Path, year: int, rows: list[str]) -> Path:
    """Write ``<year>.annual.singlefile.csv`` (real naming) with the exact header."""
    path = directory / f"{year}.annual.singlefile.csv"
    content = "\n".join([SINGLEFILE_HEADER, *rows]) + "\n"
    path.write_text(content, encoding="utf-8")
    return path
