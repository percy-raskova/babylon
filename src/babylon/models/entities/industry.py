from pydantic import BaseModel, ConfigDict, Field

from babylon.models.types import Currency


class IndustryHyperedge(BaseModel):
    """Pydantic representation of an ECONOMIC_SECTOR hyperedge in XGI."""

    model_config = ConfigDict(frozen=True)

    naics_2digit: str = Field(..., description="The 2-digit NAICS code (e.g., '62', '31-33')")
    naics_label: str = Field(..., description="Human-readable sector title")
    department_weights: dict[str, float] = Field(
        ..., description="End-use mappings (e.g., {'dept_I': 0.7, 'dept_IIa': 0.3})"
    )

    # Topology Memberships
    member_business_ids: frozenset[str] = Field(default_factory=frozenset)
    member_worker_block_ids: frozenset[str] = Field(default_factory=frozenset)
    county_fips: frozenset[str] = Field(default_factory=frozenset)

    # Derived Economic State (Aggregated during Layer 0 tick)
    total_employment: int = Field(default=0)
    total_wages: Currency = Field(default=0.0, description="Variable capital (v) across sector")
    profit_rate: float = Field(default=0.0, description="Derived from BEA/QCEW ratio")
    occ: float = Field(default=0.0, description="Organic Composition of Capital (c/v)")
