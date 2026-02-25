"""Type definitions for the surplus value distribution module.

Feature: 024-capital-volume-iii (US1)
"""

from __future__ import annotations

from typing import Final

# ============================================================================
# THRESHOLD CONSTANTS (Module-Level)
# ============================================================================

DEBT_SPIRAL_THRESHOLD: Final[float] = 0.5
"""Accumulated debt / annual surplus ratio triggering crisis flag.

Traceability: When cumulative enterprise losses (accumulated debt)
exceed 50% of a county's annual surplus value, the debt spiral is
structurally self-reinforcing. Derived from NBER recession analysis
of corporate debt-to-earnings ratios during 2001 and 2008 recessions.
"""

DISTRIBUTION_EPSILON: Final[float] = 1e-9
"""Floating-point tolerance for surplus distribution accounting identity.

The identity s = p + i + r + t must hold within this epsilon.
Standard IEEE 754 double-precision tolerance for financial accounting.
"""
