"""Volume II circulation/reproduction-schema coefficients (spec 023-capital-volume-ii).

Thresholds for the reproduction-schema balance checks that feed
:func:`~babylon.domain.economics.circulation.crisis.assess_circulation_crisis` —
extracted to player-editable ``defines.yaml`` per the Paradox Pattern rather
than hardcoded at the Volume II tick call site
(``domain/economics/tick/system/__init__.py::_compute_county_circulation_state``,
U3 wiring, 2026-07-21 vol2-circulation-engine program).

U7 (defines sweep, same program) extracted the remaining live hardcoded
coefficients discovered by re-auditing the circulation estate: the two
``assess_circulation_crisis`` crisis thresholds (previously module-level
``Final`` constants in ``circulation/types/_legacy.py``, now function
parameters), the two ``InventoryDiagnosis``/``ReplacementCyclePosition``
threshold groups consumed inside frozen-model ``computed_field`` properties
(migrated to ``GameDefines``-backed accessor functions mirroring
``capital_vol3``'s ``distribution_epsilon()`` convention — a computed
property cannot take a call-time parameter), and three calibration
fallbacks hardcoded directly at the Volume II tick call site. Deliberately
EXCLUDED from this sweep: ``REALIZATION_RATE_NORMAL/SLOWDOWN/RECESSION``
(``RealizationCrisis.crisis_severity``) — ``compute_realization_metrics``,
the sole production constructor of ``RealizationCrisis``, has zero
production callers (program prompt §2c), so extracting these now would
repeat the pre-U5 ``debt_spiral_threshold`` "NOT YET READ" anti-pattern
this sweep exists to avoid. Also excluded: ``_CONSERVATION_REL_TOL``
(``engine/systems/vol2_circulation.py``) and ``_MAX_INDUSTRIES``/
``_MAX_ELAPSED_DAYS`` (``circulation/turnover.py``/``circulation/circuit.py``)
— IEEE-754 slack and Power-of-10-rule-2 static loop bounds respectively,
not player-facing game-balance knobs (mirrors ``capital_vol3``'s own
``_WEIGHT_SUM_TOLERANCE``, which stayed a private module constant for the
same reason). Also excluded: the per-NAICS ``DEFAULT_TURNOVER_PROFILES``/
``FALLBACK_PROFILE`` tables in ``circulation/defaults.py`` — structured
reference data (one ``TurnoverProfile`` per sector), not a scalar
coefficient; migrating it would mean a nested per-sector defines schema,
out of scope for this sweep.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CapitalVolumeIIDefines(BaseModel):
    """Volume II (circulation / reproduction schema) coefficients."""

    model_config = ConfigDict(frozen=True)

    reproduction_tolerance: float = Field(
        default=0.01,
        gt=0.0,
        description=(
            "Maximum absolute I(v+s) - IIc gap (labor-hours) still "
            "considered BALANCED simple reproduction. Passed as the "
            "tolerance argument to check_simple_reproduction() from "
            "_compute_reproduction_state (Volume II tick wiring, U3). "
            "Matches the calculator's own pre-existing tested default "
            "(Feature 023 T047, tests/unit/economics/circulation/"
            "test_reproduction.py)."
        ),
    )
    dept_i_share_required: float = Field(
        default=0.6667,
        gt=0.0,
        lt=1.0,
        description=(
            "Theoretically required Department I (means of production) "
            "share of combined Dept I + Dept II output for balanced "
            "reproduction. Passed to compute_disproportionality() from "
            "_compute_reproduction_state (Volume II tick wiring, U3). "
            "Derived from Marx's own simple-reproduction numerical "
            "illustration (Capital Vol. II, Ch. 20 SS II): "
            "I = 4000c+1000v+1000s = 6000, II = 2000c+500v+500s = 3000, "
            "dept I share = 6000/9000 = 0.6667."
        ),
    )
    commodity_overhang_threshold: float = Field(
        default=0.3,
        gt=0.0,
        lt=1.0,
        description=(
            "Commodity-capital share of the circuit (M-C-P-C'-M') above "
            "which the realization phase (C'-M') is diagnosed as "
            "stalling. Passed as the commodity_overhang_threshold "
            "argument to assess_circulation_crisis() from "
            "_compute_county_circulation_state (Volume II tick wiring, "
            "U3/U7). Derived from Marx Capital II Ch. 16-17: above ~30% "
            "commodity-form capital, the circuit is structurally unable "
            "to convert produced commodities back into money capital. "
            "U7 (defines sweep): migrated off the module-level "
            "COMMODITY_OVERHANG_CRISIS Final constant in "
            "circulation/types/_legacy.py."
        ),
    )
    liquidity_crisis_ratio: float = Field(
        default=0.1,
        gt=0.0,
        lt=1.0,
        description=(
            "Money-capital share of the circuit below which a liquidity "
            "crisis is diagnosed (insufficient means of payment to "
            "purchase labor power and means of production for the next "
            "cycle). Passed as the liquidity_crisis_ratio argument to "
            "assess_circulation_crisis() from "
            "_compute_county_circulation_state (Volume II tick wiring, "
            "U3/U7). Derived from Marx Capital II Ch. 15. U7 (defines "
            "sweep): migrated off the module-level LIQUIDITY_CRISIS_RATIO "
            "Final constant in circulation/types/_legacy.py."
        ),
    )
    supply_crisis_days_threshold: float = Field(
        default=7.0,
        gt=0.0,
        description=(
            "Raw-materials days-of-inventory floor below which "
            "InventoryState.inventory_problem (circulation/types/"
            "_legacy.py) diagnoses InventoryDiagnosis.SUPPLY_CRISIS — "
            "read via the supply_crisis_days_threshold() GameDefines-"
            "backed accessor (a computed_field property cannot take a "
            "call-time parameter, mirroring capital_vol3's "
            "distribution_epsilon() convention). Live in production via "
            "assess_circulation_crisis()'s SUPPLY_CHAIN_CRISIS "
            "vulnerability check and graph_bridge.py's "
            "tick_inventory_problem publication. Derived from standard "
            "JIT manufacturing minimum-buffer practice (Toyota Production "
            "System benchmarks; BLS lead-time data ~5-10 days). U7 "
            "(defines sweep): migrated off the module-level "
            "SUPPLY_CRISIS_DAYS_THRESHOLD Final constant."
        ),
    )
    overproduction_days_threshold: float = Field(
        default=60.0,
        gt=0.0,
        description=(
            "Finished-goods days-of-inventory ceiling above which "
            "InventoryState.inventory_problem (circulation/types/"
            "_legacy.py) diagnoses InventoryDiagnosis.OVERPRODUCTION — "
            "read via the overproduction_days_threshold() GameDefines-"
            "backed accessor (same convention as "
            "supply_crisis_days_threshold above). Live in production via "
            "graph_bridge.py's tick_inventory_problem publication. "
            "Derived from Census M3 inventory-to-shipments ratios (~1.3 "
            "months normal; 60 days is a ~1.5x conservative buffer). U7 "
            "(defines sweep): migrated off the module-level "
            "OVERPRODUCTION_DAYS_THRESHOLD Final constant."
        ),
    )
    replacement_boom_ratio: float = Field(
        default=1.5,
        gt=0.0,
        description=(
            "Replacement-expenditure / annual-depreciation-flow ratio "
            "above which DepreciationFundState.replacement_cycle_position "
            "(circulation/types/_legacy.py) classifies "
            "ReplacementCyclePosition.INVESTMENT_BOOM — read via the "
            "replacement_boom_ratio() GameDefines-backed accessor "
            "(computed_field property, same convention as "
            "supply_crisis_days_threshold). Live in production via "
            "graph_bridge.py's tick_replacement_cycle publication. "
            "Derived from BEA Fixed Asset Tables historical correlation. "
            "Must exceed replacement_expansion_ratio. U7 (defines sweep): "
            "migrated off the module-level REPLACEMENT_BOOM_RATIO Final "
            "constant."
        ),
    )
    replacement_expansion_ratio: float = Field(
        default=1.0,
        gt=0.0,
        description=(
            "Replacement-expenditure / annual-depreciation-flow ratio "
            "above which DepreciationFundState.replacement_cycle_position "
            "classifies ReplacementCyclePosition.EXPANSION (investment = "
            "depreciation = simple reproduction of fixed capital, or "
            "better) — read via the replacement_expansion_ratio() "
            "accessor. Must lie strictly between "
            "replacement_maintenance_ratio and replacement_boom_ratio. "
            "U7 (defines sweep): migrated off the module-level "
            "REPLACEMENT_EXPANSION_RATIO Final constant."
        ),
    )
    replacement_maintenance_ratio: float = Field(
        default=0.7,
        gt=0.0,
        description=(
            "Replacement-expenditure / annual-depreciation-flow ratio "
            "above which DepreciationFundState.replacement_cycle_position "
            "classifies ReplacementCyclePosition.MAINTENANCE rather than "
            "DISINVESTMENT (active capital destruction) — read via the "
            "replacement_maintenance_ratio() accessor. Must be strictly "
            "below replacement_expansion_ratio. U7 (defines sweep): "
            "migrated off the module-level REPLACEMENT_MAINTENANCE_RATIO "
            "Final constant."
        ),
    )
    national_employment: float = Field(
        default=155_000_000.0,
        gt=0.0,
        description=(
            "US national civilian employment total (persons), used as "
            "the denominator of county_share = county.employment / "
            "national_employment in _compute_county_circulation_state "
            "(Volume II tick wiring) to scale national inventory/"
            "depreciation/investment aggregates down to each county. BLS "
            "civilian employment level, approximate order of magnitude "
            "circa the simulation's modeled period. U7 (defines sweep): "
            "migrated off a hardcoded literal at the tick call site."
        ),
    )
    fallback_days_inventory: float = Field(
        default=30.0,
        gt=0.0,
        description=(
            "Days-of-inventory value substituted for days_inventory_raw "
            "and days_inventory_finished in _compute_county_circulation_"
            "state (Volume II tick wiring) when the national inventory "
            "data source (FRED-backed, services.inventory_data_source) "
            "is unwired or returns None for the simulation year. A "
            "neutral midpoint between supply_crisis_days_threshold (7) "
            "and overproduction_days_threshold (60), so InventoryState."
            "inventory_problem reads NORMAL rather than fabricating a "
            "crisis diagnosis from absent data. U7 (defines sweep): "
            "migrated off a hardcoded literal at the tick call site."
        ),
    )
    min_annual_depreciation_floor: float = Field(
        default=1.0,
        gt=0.0,
        description=(
            "Minimum annual_depreciation_flow (dollars) enforced in "
            "_compute_county_circulation_state (Volume II tick wiring) "
            "when the national depreciation data source is unwired or "
            "returns None/zero for the county-year, since "
            "DepreciationFundState.annual_depreciation_flow is a live "
            "divisor (fund_adequacy = accumulated_depreciation / "
            "annual_depreciation_flow) that the model schema itself "
            "requires strictly positive (gt=0). U7 (defines sweep): "
            "migrated off a hardcoded literal at the tick call site."
        ),
    )

    @model_validator(mode="after")
    def verify_replacement_ratio_ordering(self) -> CapitalVolumeIIDefines:
        """Reject an ordering where boom <= expansion or expansion <= maintenance.

        ``DepreciationFundState.replacement_cycle_position``
        (``circulation/types/_legacy.py``) tests the ratio against these
        three thresholds as a strict descending cascade (boom > expansion >
        maintenance); an inverted or collapsed ordering from a modded
        ``defines.yaml`` would make one or more ``ReplacementCyclePosition``
        classifications unreachable with no diagnostic (Constitution III.11
        — fails loudly at config-load time instead, mirroring
        ``capital_vol3``'s ``verify_interest_share_ordering``).
        """
        if not (
            self.replacement_maintenance_ratio
            < self.replacement_expansion_ratio
            < self.replacement_boom_ratio
        ):
            raise ValueError(
                "capital_vol2 replacement ratios must satisfy "
                f"replacement_maintenance_ratio ({self.replacement_maintenance_ratio!r}) < "
                f"replacement_expansion_ratio ({self.replacement_expansion_ratio!r}) < "
                f"replacement_boom_ratio ({self.replacement_boom_ratio!r}) — check "
                "defines.yaml"
            )
        return self


__all__ = ["CapitalVolumeIIDefines"]
