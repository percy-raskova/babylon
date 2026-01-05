"""Trade data module for imperial rent research.

Provides SQLAlchemy models and ingestion utilities for UN trade data.

Uses TradeLoader with DataLoader base class for direct 3NF schema
population (marxist-data-3NF.sqlite). Parameterized via LoaderConfig.

Usage:
    from babylon.data.trade import TradeLoader
    from babylon.data.loader_base import LoaderConfig
    from babylon.data.normalize.database import get_normalized_session

    config = LoaderConfig(trade_years=[2020, 2021, 2022, 2023])
    loader = TradeLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=True)
        print(f"Loaded {stats.facts_loaded} trade observations")
"""

from babylon.data.trade.loader_3nf import TradeLoader
from babylon.data.trade.schema import TradeAnnual, TradeCountry, TradeMonthly

__all__ = [
    # 3NF Loader (recommended)
    "TradeLoader",
    # Schema models
    "TradeCountry",
    "TradeMonthly",
    "TradeAnnual",
]
