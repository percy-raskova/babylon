"""Trade data module for imperial rent research.

Provides SQLAlchemy models and ingestion utilities for UN trade data.
Data is stored in the unified research.sqlite database alongside census data.

Usage:
    from babylon.data.trade import load_trade_data, TradeCountry, TradeAnnual

    # Load data from Excel
    xlsx_path = Path("data/imperial_rent/country.xlsx")
    stats = load_trade_data(xlsx_path, reset=True)

    # Query data
    from babylon.data.census.database import get_census_db
    db = next(get_census_db())
    countries = db.query(TradeCountry).all()
"""

from babylon.data.trade.loader import load_trade_data
from babylon.data.trade.schema import TradeAnnual, TradeCountry, TradeMonthly

__all__ = [
    "TradeCountry",
    "TradeMonthly",
    "TradeAnnual",
    "load_trade_data",
]
