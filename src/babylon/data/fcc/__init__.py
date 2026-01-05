"""FCC Broadband Data Collection (BDC) data loaders.

Provides tools for downloading and ingesting FCC BDC broadband availability
data into the Babylon 3NF schema.

The FCC BDC Public Data API provides county-level broadband coverage metrics:
- Percent of locations with 25/3 Mbps service
- Percent of locations with 100/20 Mbps service
- Percent of locations with 1000/100 Mbps service
- Provider count

Data Source:
    https://broadbandmap.fcc.gov/data-download/nationwide-data

Usage:
    # Download data first (requires FCC_USERNAME and FCC_API_KEY env vars)
    from babylon.data.fcc import download_state_summaries
    download_state_summaries("06", Path("data/fcc/downloads"))

    # Then ingest from downloaded files
    from babylon.data.fcc import FCCBroadbandLoader
    loader = FCCBroadbandLoader()
    stats = loader.load(session)
"""

from babylon.data.fcc.downloader import (
    FCCAPIError,
    FCCBDCClient,
    FCCFileInfo,
    download_national_summaries,
    download_state_hexagons,
    download_state_summaries,
)

__all__ = [
    "FCCAPIError",
    "FCCBDCClient",
    "FCCFileInfo",
    "download_national_summaries",
    "download_state_hexagons",
    "download_state_summaries",
]
