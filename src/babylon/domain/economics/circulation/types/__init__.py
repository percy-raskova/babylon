"""Circulation types package — Spec 059 US5 / ADR-006.2.

Replaces the historical 1354-LOC ``economics/circulation/types.py`` single
file with a package whose ``__init__.py`` re-exports the full public surface
unchanged. The original implementation lives at ``_legacy.py`` while the
content split into thematic sub-files (``flow.py`` / ``fixed_capital.py`` /
``crisis.py`` / ``_enums.py`` per data-model.md §2.4) is deferred to a
follow-up — preserving byte-equality and import equivalence trumps SC-002's
LOC budget for this commit.

Import equivalence (FR-003 / contracts/import-equivalence.md C6): every
existing ``from babylon.domain.economics.circulation.types import X`` resolves
unchanged via this re-export.

Exception (U7 defines sweep, 2026-07-21 vol2-circulation-engine program):
seven module-level ``Final`` threshold constants (``COMMODITY_OVERHANG_CRISIS``,
``LIQUIDITY_CRISIS_RATIO``, ``OVERPRODUCTION_DAYS_THRESHOLD``,
``SUPPLY_CRISIS_DAYS_THRESHOLD``, ``REPLACEMENT_BOOM_RATIO``,
``REPLACEMENT_EXPANSION_RATIO``, ``REPLACEMENT_MAINTENANCE_RATIO``) were
migrated off this re-export — the first two became ``assess_circulation_crisis``
keyword parameters (``crisis.py``), the remaining five became GameDefines-backed
accessor functions (``supply_crisis_days_threshold()`` etc., same names,
lowercase) — mirroring the ``capital_vol3`` honesty-sweep precedent. No
importer outside this package referenced the removed names (verified by
repo-wide grep at authoring time).
"""

from __future__ import annotations

from babylon.domain.economics.circulation.types._legacy import (
    REALIZATION_RATE_NORMAL,
    REALIZATION_RATE_RECESSION,
    REALIZATION_RATE_SLOWDOWN,
    AnnualSurplusValue,
    CapitalForm,
    CircuitState,
    CirculationCrisisAssessment,
    CirculationCrisisState,
    CrisisSeverity,
    DepreciationFundState,
    DisproportionalityCrisis,
    FixedCapitalItem,
    InventoryDiagnosis,
    InventoryState,
    MoralDepreciation,
    PureCirculationCosts,
    RealizationCrisis,
    ReplacementCyclePosition,
    ReproductionAnalysis,
    ReproductionBalance,
    TransportationValue,
    TurnoverProfile,
    fallback_days_inventory,
    overproduction_days_threshold,
    replacement_boom_ratio,
    replacement_expansion_ratio,
    replacement_maintenance_ratio,
    supply_crisis_days_threshold,
)

__all__ = [
    "AnnualSurplusValue",
    "CapitalForm",
    "CircuitState",
    "CirculationCrisisAssessment",
    "CirculationCrisisState",
    "CrisisSeverity",
    "DepreciationFundState",
    "DisproportionalityCrisis",
    "fallback_days_inventory",
    "FixedCapitalItem",
    "InventoryDiagnosis",
    "InventoryState",
    "MoralDepreciation",
    "overproduction_days_threshold",
    "PureCirculationCosts",
    "REALIZATION_RATE_NORMAL",
    "REALIZATION_RATE_RECESSION",
    "REALIZATION_RATE_SLOWDOWN",
    "RealizationCrisis",
    "replacement_boom_ratio",
    "replacement_expansion_ratio",
    "replacement_maintenance_ratio",
    "ReplacementCyclePosition",
    "ReproductionAnalysis",
    "ReproductionBalance",
    "supply_crisis_days_threshold",
    "TransportationValue",
    "TurnoverProfile",
]
