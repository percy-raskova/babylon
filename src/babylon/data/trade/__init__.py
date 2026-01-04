"""Trade data module for imperial rent research.

Provides SQLAlchemy models and ingestion utilities for UN trade data.

Two ingestion paths are available:

1. **3NF Direct (recommended)**: Uses TradeLoader with DataLoader base class
   - Direct 3NF schema population (marxist-data-3NF.sqlite)
   - Parameterized via LoaderConfig (trade_years)
   - Parses Excel files from UN trade data

2. **Legacy**: Uses load_trade_data
   - Writes to research.sqlite
   - Requires local Excel files in data/imperial_rent/

Example (3NF Direct):
    from babylon.data.trade import TradeLoader
    from babylon.data.loader_base import LoaderConfig
    from babylon.data.normalize.database import get_normalized_session

    config = LoaderConfig(trade_years=[2020, 2021, 2022, 2023])
    loader = TradeLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=True)
        print(f"Loaded {stats.facts_loaded} trade observations")

Example (Legacy):
    from babylon.data.trade import load_trade_data
    from pathlib import Path

    xlsx_path = Path("data/imperial_rent/country.xlsx")
    stats = load_trade_data(xlsx_path, reset=True)
"""

from babylon.data.trade.loader import load_trade_data
from babylon.data.trade.loader_3nf import TradeLoader
from babylon.data.trade.schema import TradeAnnual, TradeCountry, TradeMonthly

__all__ = [
    # 3NF Loader (recommended)
    "TradeLoader",
    # Legacy schema models
    "TradeCountry",
    "TradeMonthly",
    "TradeAnnual",
    # Legacy loader
    "load_trade_data",
]
