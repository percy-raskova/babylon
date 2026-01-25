"""Concordance loaders for mapping between classification systems.

This module provides loaders for concordance tables that bridge between
different industry, geographic, and product classification systems.

Modules:
    loader_naics_bea: NAICS to BEA industry concordance loader.
"""

from babylon.data.concordance.loader_naics_bea import (
    NAICSBEAConcordanceLoader,
    expand_naics_codes,
)

__all__ = [
    "NAICSBEAConcordanceLoader",
    "expand_naics_codes",
]
