"""BEA (Bureau of Economic Analysis) data loading infrastructure.

This module provides loaders and parsers for BEA GDP-by-industry data:
- National gross output, value added, and intermediate inputs by industry
- County-level GDP by industry (from bulk CSV downloads)
- NAICS-to-BEA industry concordance

The data enables construction of the Marxist value tensor T[territory, sector, {c, v, s}]
by providing:
- Constant capital ratios (intermediate_inputs / gross_output) at national level
- Value added components for decomposition into v and s
- Industry classification bridging between NAICS (QCEW) and BEA

Usage:
    from babylon.data.bea import BEANationalLoader
    from babylon.data import LoaderConfig
    from babylon.data.normalize.database import get_normalized_session_factory

    loader = BEANationalLoader()
    session_factory = get_normalized_session_factory()
    with session_factory() as session:
        stats = loader.load(session)
"""

from babylon.data.bea.loader_concordance import BEAConcordanceLoader, expand_naics_codes
from babylon.data.bea.loader_county import BEACountyGDPLoader
from babylon.data.bea.loader_national import BEANationalLoader
from babylon.data.bea.parser import BEAIndustryParser

__all__ = [
    "BEAConcordanceLoader",
    "BEACountyGDPLoader",
    "BEANationalLoader",
    "BEAIndustryParser",
    "expand_naics_codes",
]
