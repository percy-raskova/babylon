#!/usr/bin/env python3
"""Ingest BEA 'Use of Imports' matrices.

Extracts the 'Use of Imports' matrix from the BEA MAKE-USE-IMPORTS zip archive
(`ImportMatrices_Before_Redefinitions_Summary.xlsx`), parses the coefficients,
and saves them as `FactBEAIOCoefficient` records with `table_type='IMPORT_USE'`.

Usage:
    poetry run python tools/ingest_bea_imports.py
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from io import BytesIO

import pandas as pd
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from babylon.reference.database import NormalizedBase
from babylon.reference.schema import (
    DimBEAIndustry,
    DimBEAIOTableType,
    DimTime,
    FactBEAIOCoefficient,
)

BEA_ZIP_PATTERN = "/media/user/data/babylon-data/bea/MAKE-USE-IMPORTS*.zip"
XLSX_FILENAME = "ImportMatrices_Before_Redefinitions_Summary.xlsx"
DB_URL = "sqlite:///marxist-data-3NF.sqlite"


def get_or_create_time(session: Session, year: int) -> DimTime:
    """Get or create DimTime entry."""
    time_entry = session.execute(
        select(DimTime).where(DimTime.year == year, DimTime.is_annual == True)  # noqa: E712
    ).scalar_one_or_none()

    if not time_entry:
        time_entry = DimTime(year=year, is_annual=True)
        session.add(time_entry)
        session.flush()

    return time_entry


def get_or_create_table_type(session: Session, type_name: str) -> DimBEAIOTableType:
    """Get or create DimBEAIOTableType."""
    tt = session.execute(
        select(DimBEAIOTableType).where(DimBEAIOTableType.table_type == type_name)
    ).scalar_one_or_none()

    if not tt:
        tt = DimBEAIOTableType(table_type=type_name)
        session.add(tt)
        session.flush()

    return tt


def get_industry_cache(session: Session) -> dict[str, int]:
    """Load all BEA industries into a code->id map."""
    rows = session.execute(select(DimBEAIndustry)).scalars().all()
    cache = {row.bea_code: row.bea_industry_id for row in rows}

    # If cache is empty, we must be running before the primary BEA loader.
    if not cache:
        print(
            "Warning: DimBEAIndustry is empty. Please run main BEA ingest first.", file=sys.stderr
        )

    return cache


def parse_and_ingest_sheet(
    session: Session, df: pd.DataFrame, year: int, table_type_id: int, ind_cache: dict[str, int]
) -> int:
    """Parse one year's sheet representing the Import matrix."""
    time_entry = get_or_create_time(session, year)
    time_id = time_entry.time_id

    count = 0
    # Usually the BEA matrix has commodity/industry codes on the first row and column.
    # The exact format needs to align with the actual parser in the real io_loader.
    # Here we assume standard square matrix with codes in index/columns after dropna.
    df = df.dropna(how="all").dropna(axis=1, how="all")

    # Basic attempt to read if the first column contains row codes and headers are col codes.
    # We will iterate over columns (target_industries) and rows (source_industries/commodities).
    col_codes = df.columns
    row_codes = df.iloc[:, 0].values

    for row_idx, source_code in enumerate(row_codes):
        code_str = str(source_code).strip()
        if code_str not in ind_cache:
            continue

        source_id = ind_cache[code_str]

        for col_idx, col_code in enumerate(col_codes):
            if col_idx == 0:
                continue  # Skip the label column

            col_str = str(col_code).strip()
            if col_str not in ind_cache:
                continue

            target_id = ind_cache[col_str]
            val = df.iloc[row_idx, col_idx]

            try:
                coeff = float(val)
                # Ignore 0s and NaNs to save space
                if coeff == 0.0 or pd.isna(coeff):
                    continue

                fact = FactBEAIOCoefficient(
                    time_id=time_id,
                    table_type_id=table_type_id,
                    source_industry_id=source_id,
                    target_industry_id=target_id,
                    coefficient=coeff,
                )
                session.add(fact)
                count += 1
            except (ValueError, TypeError):
                pass

    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest BEA Use of Imports")
    parser.add_argument("--db-url", default=DB_URL, help="Database URL")
    args = parser.parse_args(argv)

    engine = create_engine(args.db_url)
    NormalizedBase.metadata.create_all(engine)

    import glob

    zip_files = glob.glob(BEA_ZIP_PATTERN)
    if not zip_files:
        print(f"No zip files found matching: {BEA_ZIP_PATTERN}", file=sys.stderr)
        return 1

    target_zip = zip_files[0]
    print(f"Reading from {target_zip}...")

    with Session(engine) as session:
        try:
            table_type = get_or_create_table_type(session, "IMPORT_USE")
            ind_cache = get_industry_cache(session)
            if not ind_cache:
                return 1

            total_inserted = 0
            with zipfile.ZipFile(target_zip, "r") as z:
                if XLSX_FILENAME not in z.namelist():
                    print(f"Error: {XLSX_FILENAME} not found in zip.", file=sys.stderr)
                    return 1

                with z.open(XLSX_FILENAME) as f:
                    file_bytes = BytesIO(f.read())
                    xl = pd.ExcelFile(file_bytes)

                    for sheet_name in xl.sheet_names:
                        # Assuming sheet names are "2017", "2018", etc.
                        if sheet_name.isdigit():
                            year = int(sheet_name)
                            df = pd.read_excel(xl, sheet_name=sheet_name)
                            n = parse_and_ingest_sheet(session, df, year, table_type.id, ind_cache)
                            print(f"  Ingested {n} import use coefficients for {year}")
                            total_inserted += n

            session.commit()
            print(f"Successfully ingested {total_inserted} total coefficients.")

        except Exception as e:
            session.rollback()
            print(f"Error ingesting data: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
