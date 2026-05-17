"""Shaikh (2016) empirical c/v bands per BEA-summary industry (spec-068 US4).

Source: Shaikh, Anwar. *Capitalism: Competition, Conflict, Crises*.
Oxford University Press, 2016.
  - Table 6.1: Manufacturing c/v decompositions, US 1947-2010.
  - Table 6.3: Broad sector measures (services, trade, FIRE, etc.).
  - Appendix 6.6: Per-industry detail for agriculture, mining, etc.

The bands below capture modern (2000-2020) US capitalism. They are the
spec-068 SC-006 calibration target with ±50 % tolerance to admit the
between-county-within-industry heterogeneity that real BEA + QCEW data
produces.

Industries not listed below use the economy-wide median band of
``[0.4, 1.2]`` (``c/v ≈ 0.8``) per Shaikh's broad-aggregate estimate;
the audit script flags any industry that ends up using this fallback.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

# BEA-summary codes (from dim_bea_industry.bea_code).
# Band format: (c_v_lower, c_v_upper) — inclusive bounds.
SHAIKH_BANDS: dict[str, tuple[float, float]] = {
    # Agriculture, forestry, fishing
    "111CA": (2.0, 5.0),  # Farms (high capital intensity)
    "113FF": (1.5, 4.0),  # Forestry, fishing
    # Mining
    "211": (2.5, 6.0),  # Oil and gas extraction (very high C)
    "212": (2.5, 6.0),  # Mining, except oil/gas
    "213": (1.5, 4.0),  # Support activities for mining
    # Utilities
    "22": (2.0, 4.5),  # Utilities (high fixed capital)
    # Construction
    "23": (1.0, 2.5),  # Construction (medium capital intensity)
    # Manufacturing (Shaikh Tbl 6.1)
    "311FT": (1.5, 3.0),  # Food, beverage, tobacco
    "313TT": (1.5, 3.0),  # Textiles, apparel
    "321": (1.5, 3.0),  # Wood products
    "322": (2.0, 3.5),  # Paper
    "323": (1.5, 3.0),  # Printing
    "324": (2.5, 5.0),  # Petroleum and coal products
    "325": (2.0, 4.0),  # Chemicals
    "326": (1.5, 3.0),  # Plastics and rubber
    "327": (1.5, 3.0),  # Nonmetallic mineral products
    "331": (2.0, 4.0),  # Primary metals
    "332": (1.5, 3.0),  # Fabricated metal products
    "333": (1.5, 3.0),  # Machinery
    "334": (1.5, 3.0),  # Computer and electronic products
    "335": (1.5, 3.0),  # Electrical equipment
    "3361MV": (1.5, 3.0),  # Motor vehicles
    "3364OT": (1.5, 3.0),  # Other transportation equipment
    "337": (1.5, 3.0),  # Furniture
    "339": (1.0, 2.5),  # Misc manufacturing
    # Wholesale + Retail trade (Shaikh Tbl 6.3)
    "42": (0.5, 1.2),  # Wholesale
    "441": (0.5, 1.2),  # Motor vehicle dealers
    "445": (0.5, 1.2),  # Food and beverage retail
    "452": (0.5, 1.2),  # General merchandise
    "4A0": (0.5, 1.2),  # Other retail
    # Transportation
    "481": (1.5, 3.0),  # Air transport
    "482": (2.0, 4.0),  # Rail transport
    "483": (2.0, 4.0),  # Water transport
    "484": (1.0, 2.5),  # Truck transport
    "485": (1.0, 2.5),  # Transit and ground passenger
    "486": (2.5, 5.0),  # Pipeline transport
    "487OS": (1.0, 2.5),  # Other transport
    "493": (1.0, 2.5),  # Warehousing and storage
    # Information
    "511": (0.5, 1.2),  # Publishing (software, news)
    "512": (1.0, 2.0),  # Motion pictures
    "513": (1.5, 3.0),  # Broadcasting and telecommunications
    "514": (1.5, 3.0),  # Data processing, hosting, ISP
    # FIRE — low capital intensity, paper flows (Shaikh Tbl 6.3)
    "521CI": (0.4, 0.9),  # Federal Reserve, credit intermediation
    "523": (0.3, 0.8),  # Securities, commodity contracts
    "524": (0.4, 1.0),  # Insurance
    "525": (0.3, 0.8),  # Funds, trusts
    "HS": (0.3, 0.8),  # Housing (BEA-summary)
    "ORE": (0.4, 1.0),  # Other real estate
    "532RL": (0.4, 1.0),  # Rental and leasing
    # Professional services
    "5411": (0.3, 0.8),  # Legal services
    "5415": (0.3, 0.8),  # Computer systems design
    "5412OP": (0.3, 0.8),  # Other professional services
    # Management
    "55": (0.3, 0.8),  # Management of companies
    # Admin support
    "561": (0.3, 1.0),  # Administrative and support
    "562": (0.5, 1.2),  # Waste management
    # Education
    "61": (0.3, 0.8),  # Educational services
    # Health
    "621": (0.3, 0.8),  # Ambulatory health care
    "622": (0.5, 1.2),  # Hospitals
    "623": (0.3, 0.8),  # Nursing and residential care
    "624": (0.3, 0.8),  # Social assistance
    # Arts, entertainment, recreation
    "711AS": (0.5, 1.2),  # Performing arts, spectator sports
    "713": (0.5, 1.2),  # Amusement, gambling, recreation
    # Accommodation, food
    "721": (0.5, 1.2),  # Accommodation
    "722": (0.3, 1.0),  # Food services and drinking places
    # Other services
    "81": (0.3, 0.8),  # Other services (except government)
    # Government
    "GFE": (0.5, 1.5),  # Federal enterprises
    "GFG": (0.3, 1.0),  # Federal general government
    "GSLE": (0.5, 1.5),  # State/local enterprises
    "GSLG": (0.3, 1.0),  # State/local general government
}

_ECONOMY_WIDE_FALLBACK_BAND: tuple[float, float] = (0.4, 1.2)


class ShaikhBand(BaseModel):
    """One Shaikh empirical c/v band for a BEA industry."""

    model_config = ConfigDict(frozen=True)

    bea_code: str
    lower: float
    upper: float
    is_fallback: bool


class ShaikhBandViolation(BaseModel):
    """A BEA industry whose measured c/v falls outside its Shaikh band."""

    model_config = ConfigDict(frozen=True)

    bea_code: str
    bea_industry_id: int
    measured_c_v: float
    band_lower: float
    band_upper: float


def lookup_shaikh_band(bea_code: str) -> ShaikhBand:
    """Return the Shaikh c/v band for ``bea_code``, or the economy-wide fallback.

    Args:
        bea_code: BEA-summary industry code as it appears in
            ``dim_bea_industry.bea_code`` (e.g., ``"111CA"``, ``"22"``,
            ``"5411"``).

    Returns:
        :class:`ShaikhBand` with ``is_fallback=True`` if the code is
        not in the explicit table (uses economy-wide median band).
    """
    if bea_code in SHAIKH_BANDS:
        lower, upper = SHAIKH_BANDS[bea_code]
        return ShaikhBand(bea_code=bea_code, lower=lower, upper=upper, is_fallback=False)
    lower, upper = _ECONOMY_WIDE_FALLBACK_BAND
    return ShaikhBand(bea_code=bea_code, lower=lower, upper=upper, is_fallback=True)
