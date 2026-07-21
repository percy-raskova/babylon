"""Formula-registration sentinel: a registered formula must be USED, not just named.

Instance of the Sentinel pattern guarding a failure mode :mod:`babylon.
sentinels.inert` cannot see: a formula registered in
:class:`~babylon.engine.formula_registry.FormulaRegistry` (hot-swappable
surface, implied public API) whose own registration call
(``registry.register("key", formulas.symbol)``) is the ONLY reference to it
anywhere in the codebase. ``inert``'s producer-reachability rule counts that
registration line itself as a satisfied reference — this sentinel scans the
same production tree with that one file explicitly excluded.

Founding incident (Vol I value-production program recon, §2d):
``calculate_labor_aristocracy_ratio``, ``is_labor_aristocracy``, and
``calculate_consciousness_drift`` were all formula-registry-registered with
zero call sites outside registration/tests. Vol I's U2 (ADR109) wired the
first two into
:func:`~babylon.domain.dialectics.instances.value_form.compute_fundamental_theorem`;
the third remains a real, open gap held GREEN via one recorded exemption.
"""

from babylon.sentinels.formula_registration.checks import (
    formula_reference_sites,
    formulas_without_production_caller,
    is_test_source,
)
from babylon.sentinels.formula_registration.registry import (
    DECLARED_FORMULAS,
    FORMULA_EXEMPTIONS,
    FORMULA_REGISTRY_FILE,
    PRODUCTION_ROOTS,
    DeclaredFormula,
)

__all__ = [
    "DECLARED_FORMULAS",
    "FORMULA_EXEMPTIONS",
    "FORMULA_REGISTRY_FILE",
    "PRODUCTION_ROOTS",
    "DeclaredFormula",
    "formula_reference_sites",
    "formulas_without_production_caller",
    "is_test_source",
]
